"""Run right after build.py in the same Blender session (test renders only; nothing is saved).
  tools/brun.sh --render -- --python scenes/set_b/build.py --python scenes/set_b/final_check.py -- <tag> [quick|full] [frames]
Renders S2 check frames at 50%/16 samples, runs the palette hue check on f217 and f288
(bible: magenta (hue 290-345) >= 25% and red-orange (345-28) <= 10% of the frame; teal < 0.5%; f288 mean V ~0.5-0.55),
and in 'full' mode times two frames at the stored final settings (100%).
Also usable on a saved blend:  tools/brun.sh --render -- blend/set_b.blend --python scenes/set_b/final_check.py -- <tag> quick"""
import bpy, os, sys, time
import numpy as np
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
tag = argv[0] if argv else 'rf'
mode = argv[1] if len(argv) > 1 else 'quick'
FR = [int(x) for x in argv[2].split(',')] if len(argv) > 2 else \
    [121, 125, 131, 138, 145, 160, 181, 200, 217, 229, 240, 248, 255, 262, 268, 274, 282, 288]
sc = bpy.context.scene; e = sc.eevee
out = os.path.join(os.getcwd(), 'renders', 'tests', 'set_b', tag + '_')
pct0, smp0 = sc.render.resolution_percentage, e.taa_render_samples


def r(f, label):
    t = time.time(); sc.frame_set(f); sc.render.filepath = f'{out}{label}{f:04d}.png'
    bpy.ops.render.render(write_still=True); print('FRAME', label, f, round(time.time() - t, 1), flush=True)
    return sc.render.filepath


def hue_stats(path):
    img = bpy.data.images.load(path); img.colorspace_settings.name = 'Non-Color'
    px = np.array(img.pixels[:], dtype=np.float32).reshape(-1, 4)[:, :3]
    bpy.data.images.remove(img)
    mx = px.max(1); mn = px.min(1); d = mx - mn
    s = np.where(mx > 1e-6, d / np.maximum(mx, 1e-6), 0.0)
    rr, gg, bb = px[:, 0], px[:, 1], px[:, 2]
    h = np.zeros_like(mx); m = d > 1e-6
    ir = m & (mx == rr); ig = m & ~ir & (mx == gg); ib = m & ~ir & ~ig
    h[ir] = ((gg - bb)[ir] / d[ir]) % 6.0
    h[ig] = (bb - rr)[ig] / d[ig] + 2.0
    h[ib] = (rr - gg)[ib] / d[ib] + 4.0
    h *= 60.0
    col = (s > 0.25) & (mx > 0.15)
    mag = (col & (h >= 290) & (h < 345)).mean()
    ro = (col & ((h >= 345) | (h < 28))).mean()
    ul = (col & (h >= 210) & (h < 290)).mean()
    saf = col & (h >= 28) & (h < 60) & (s > 0.5)
    teal = ((h >= 160) & (h <= 200) & (s > 0.30) & (mx > 0.20)).mean()
    saf_h = float(np.median(h[saf])) if saf.any() else -1
    saf_s = float(np.median(s[saf])) if saf.any() else -1
    return dict(magenta=round(float(mag), 3), redorange=round(float(ro), 3), ultra_violet=round(float(ul), 3),
                saffron_px=round(float(saf.mean()), 3), saffron_med_hue=round(saf_h, 1), saffron_med_sat=round(saf_s, 2),
                teal=round(float(teal), 4), meanV=round(float(mx.mean()), 3))


sc.render.resolution_percentage = 50; e.taa_render_samples = 16
paths = {}
for f in FR:
    paths[f] = r(f, '')
ok = True
for f in (217, 288):
    if f in paths:
        st = hue_stats(paths[f])
        good = st['teal'] < 0.005
        if f == 288:
            good = good and st['magenta'] >= 0.25 and st['redorange'] <= 0.10
        if f == 217:
            good = good and st['magenta'] >= st['redorange']
        ok = ok and good
        print('HUECHECK', f, 'PASS' if good else 'FAIL', st, flush=True)
for f in FR:
    if f not in (217, 288):
        print('HUESTAT', f, hue_stats(paths[f]), flush=True)
print('HUECHECK_ALL', 'PASS' if ok else 'FAIL')
sc.render.resolution_percentage = pct0; e.taa_render_samples = smp0
if mode == 'full':
    for f in (121, 217, 262):
        r(f, 'full')
print('FINAL_CHECK_DONE', pct0, smp0)
