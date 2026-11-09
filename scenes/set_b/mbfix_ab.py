"""A/B test renders for the f256-272 shutter fix (test overrides only; nothing is saved).
Renders the same frames from the pre-fix blend (set_b.blend1) and the rebuilt blend, dumps the shutter curve of
both for f121-288 and prints lower-middle colour stats (lilac-blob metric).
tools/brun.sh --render -- --python scenes/set_b/mbfix_ab.py -- <tag> <pct> <samples> <frames,comma>"""
import bpy, os, sys, json
import numpy as np
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
tag = argv[0] if argv else 'mb1'
pct = int(argv[1]) if len(argv) > 1 else 33
spp = int(argv[2]) if len(argv) > 2 else 16
frames = [int(x) for x in (argv[3] if len(argv) > 3 else '258,262,266,270').split(',')]
which = argv[4].split(',') if len(argv) > 4 else ['before', 'after']
ROOT = os.getcwd()
OUT = os.path.join(ROOT, 'renders', 'tests', 'set_b')
SRC = {'before': os.path.join(ROOT, 'blend', 'set_b.blend1'), 'after': os.path.join(ROOT, 'blend', 'set_b.blend')}


def shutter_curve(sc):
    vals = {}
    for f in range(121, 289):
        sc.frame_set(f); vals[f] = sc.render.motion_blur_shutter
    return vals


PIX = {}


def stats(path, key):
    im = bpy.data.images.load(path)
    w, h = im.size
    px = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)[..., :3]   # row 0 = bottom
    bpy.data.images.remove(im)
    PIX[key] = px
    mx = px.max(-1); mn = px.min(-1); sat = np.where(mx > 1e-4, (mx - mn) / np.maximum(mx, 1e-4), 0)
    r, g, b = px[..., 0], px[..., 1], px[..., 2]
    # lilac: bright, low-mid saturation, blue/red over green (pastel violet-pink)
    lilac = (mx > 0.55) & (sat > 0.08) & (sat < 0.45) & (g < r) & (g < b) & (b > 0.5)
    reg = (slice(0, int(h * 0.45)), slice(int(w * 0.25), int(w * 0.75)))   # lower middle
    return {'sat_all': float(sat.mean()), 'sat_lowmid': float(sat[reg].mean()), 'val_lowmid': float(mx[reg].mean()),
            'lilac_lowmid_pct': float(100 * lilac[reg].mean()), 'lilac_all_pct': float(100 * lilac.mean())}


curves = {}
for w in which:
    bpy.ops.wm.open_mainfile(filepath=SRC[w])
    sc = bpy.context.scene
    print('AB_OPEN', w, bpy.data.filepath, 'res', sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage,
          'spp', sc.eevee.taa_render_samples, 'mb', sc.render.use_motion_blur, 'range', sc.frame_start, sc.frame_end, flush=True)
    curves[w] = shutter_curve(sc)
    sc.render.resolution_percentage = pct; sc.eevee.taa_render_samples = spp
    for f in frames:
        p = os.path.join(OUT, f'{tag}_{w}_{f:04d}.png')
        sc.frame_set(f); sc.render.filepath = p
        bpy.ops.render.render(write_still=True)
        print('AB_FRAME', w, f, 'shutter', round(sc.render.motion_blur_shutter, 4), json.dumps(stats(p, (w, f))), flush=True)
    for f in ([int(x) for x in argv[5].split(',')] if len(argv) > 5 else []):   # same frames with motion blur OFF
        sc.render.use_motion_blur = False
        p = os.path.join(OUT, f'{tag}_{w}_nomb_{f:04d}.png')
        sc.frame_set(f); sc.render.filepath = p
        bpy.ops.render.render(write_still=True)
        print('AB_NOMB', w, f, json.dumps(stats(p, (w + '_nomb', f))), flush=True)
        sc.render.use_motion_blur = True
if 'before' in curves and 'after' in curves:
    diff = [f for f in range(121, 289) if curves['before'][f] != curves['after'][f]]
    print('AB_SHUTTER_DIFF_FRAMES', diff, flush=True)
    for f in frames:
        d = np.abs(PIX[('before', f)] - PIX[('after', f)])
        print('AB_PIXDIFF', f, 'mean', float(d.mean()), 'max', float(d.max()), flush=True)
    for f in range(254, 275):
        print('AB_SHUTTER', f, repr(curves['before'][f]), repr(curves['after'][f]), flush=True)
print('AB_DONE', flush=True)
