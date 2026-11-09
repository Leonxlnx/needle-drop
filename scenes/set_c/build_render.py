"""Build blend/set_c.blend from scratch (scenes/set_c/build.py) and then render test frames in the SAME process
(saves one 560 MB reload and one GPU queue wait). Run through brun with --render:
  tools/brun.sh --threads 6 --render -- --python scenes/set_c/build_render.py -- --frames 420,456 --pct 33 --samples 16 --rout renders/tests/set_c/r11_
Build options (--nofx --notrees --nocull) pass through to build.py. Render overrides are applied after the save,
so the stored blend keeps the final settings."""
import bpy, sys, os, time, runpy
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
opts = {'full': '', 'frames': '', 'pct': None, 'samples': None, 'rout': os.path.join('renders', 'tests', 'set_c', 'br_'), 'nomb': False}
keep = []
i = 0
while i < len(argv):
    a = argv[i]
    if a == '--frames': opts['frames'] = argv[i + 1]; i += 2
    elif a == '--full': opts['full'] = argv[i + 1]; i += 2
    elif a == '--pct': opts['pct'] = int(argv[i + 1]); i += 2
    elif a == '--samples': opts['samples'] = int(argv[i + 1]); i += 2
    elif a == '--rout': opts['rout'] = argv[i + 1]; i += 2
    elif a == '--nomb': opts['nomb'] = True; i += 1
    else: keep.append(a); i += 1
here = os.path.dirname(os.path.abspath(__file__))
sys.argv = [sys.argv[0], '--'] + keep
runpy.run_path(os.path.join(here, 'build.py'), run_name='__main__')
sc = bpy.context.scene
# --full: timing frames at the STORED final settings (100%, keyed samples, motion blur) before any test override
outf = os.path.abspath(opts['rout'])
for part in [p for p in opts['full'].split(',') if p.strip()]:
    f = int(part); t = time.time()
    sc.frame_set(f); sc.render.filepath = f'{outf}full_{f:04d}.png'
    bpy.ops.render.render(write_still=True)
    print(f'FULLFRAME {f} {time.time() - t:.1f} samples={sc.eevee.taa_render_samples} pct={sc.render.resolution_percentage}', flush=True)
frames = []
for part in opts['frames'].split(','):
    if '-' in part:
        a, b = part.split('-'); frames += list(range(int(a), int(b) + 1))
    elif part.strip():
        frames.append(int(part))
if opts['pct']: sc.render.resolution_percentage = opts['pct']
if opts['samples'] and sc.animation_data is not None and sc.animation_data.action is not None:
    # test only (blend already saved): drop ONLY the per-shot sample keys (keep shutter keys etc.)
    ad = sc.animation_data
    try:
        fcs = ad.action.fcurves
    except Exception:
        from bpy_extras import anim_utils
        fcs = anim_utils.action_get_channelbag_for_slot(ad.action, ad.action_slot).fcurves
    for fc in [fc for fc in fcs if 'taa_render_samples' in fc.data_path]:
        fcs.remove(fc)
if opts['samples']: sc.eevee.taa_render_samples = opts['samples']
if opts['nomb']: sc.render.use_motion_blur = False
out = os.path.abspath(opts['rout'])
os.makedirs(os.path.dirname(out), exist_ok=True)
for f in frames:
    t = time.time()
    sc.frame_set(f)
    if opts['samples']:
        sc.eevee.taa_render_samples = opts['samples']
    sc.render.filepath = f'{out}{f:04d}.png'
    bpy.ops.render.render(write_still=True)
    print(f'FRAME {f} {time.time() - t:.1f}', flush=True)
print('RENDER_DONE', flush=True)
