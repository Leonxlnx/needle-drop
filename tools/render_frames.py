"""Render selected frames of an opened .blend with optional quality overrides.

Run through the safe runner, e.g.:
  tools/brun.sh --render -- blend/set_b.blend --python tools/render_frames.py -- \
      --frames 121,200,288 --pct 50 --samples 16 --out renders/tests/set_b/v3_
  --frames  comma list and/or ranges: "121,130-140,288" (global frame numbers)
  --step N  with a range, render every Nth frame
  --pct     resolution percentage override (default: keep)
  --samples EEVEE TAA render samples override (default: keep)
  --nomb    disable motion blur for speed
  --out     output prefix; files are <out><frame:04d>.png
  --skip-existing  do not re-render frames whose file exists (final-render chunking)
Prints 'FRAME <n> <seconds>' per frame and 'RENDER_DONE'.
"""
import bpy, sys, os, time

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
opts = {'frames': None, 'step': 1, 'pct': None, 'samples': None, 'nomb': False, 'out': None, 'skip': False}
i = 0
while i < len(argv):
    a = argv[i]
    if a == '--frames': opts['frames'] = argv[i + 1]; i += 2
    elif a == '--step': opts['step'] = int(argv[i + 1]); i += 2
    elif a == '--pct': opts['pct'] = int(argv[i + 1]); i += 2
    elif a == '--samples': opts['samples'] = int(argv[i + 1]); i += 2
    elif a == '--nomb': opts['nomb'] = True; i += 1
    elif a == '--out': opts['out'] = argv[i + 1]; i += 2
    elif a == '--skip-existing': opts['skip'] = True; i += 1
    else: i += 1

sc = bpy.context.scene
frames = []
for part in (opts['frames'] or f'{sc.frame_start}-{sc.frame_end}').split(','):
    if '-' in part:
        a, b = part.split('-'); frames += list(range(int(a), int(b) + 1, opts['step']))
    elif part.strip():
        frames.append(int(part))
if opts['pct']: sc.render.resolution_percentage = opts['pct']
if opts['samples']: sc.eevee.taa_render_samples = opts['samples']
if opts['nomb']: sc.render.use_motion_blur = False
out = os.path.abspath(opts['out'] or os.path.join(os.getcwd(), 'renders', 'tests', 'frame_'))
os.makedirs(os.path.dirname(out), exist_ok=True)
import json
OVR = os.path.join(os.getcwd(), 'logs', 'render_override.json')
ovr = []
if os.path.exists(OVR):
    try: ovr = json.load(open(OVR))['ranges']
    except Exception as ex: print('override unreadable:', ex)
if (opts['samples'] or ovr) and sc.animation_data is not None and sc.animation_data.action is not None:
    # keyed per-shot samples would be re-evaluated at render time and win; drop them in this session only (blend not saved)
    ad = sc.animation_data
    try:
        fcs = ad.action.fcurves
    except Exception:
        from bpy_extras import anim_utils
        fcs = anim_utils.action_get_channelbag_for_slot(ad.action, ad.action_slot).fcurves
    for fc in [fc for fc in fcs if 'taa_render_samples' in fc.data_path]:
        fcs.remove(fc)
for f in frames:
    path = f'{out}{f:04d}.png'
    if opts['skip'] and os.path.exists(path) and os.path.getsize(path) > 0:
        continue
    t = time.time()
    sc.frame_set(f)   # may evaluate keyed settings (e.g. per-shot samples), so overrides go after it
    if opts['samples']: sc.eevee.taa_render_samples = opts['samples']
    for a, b, smp in ovr:   # hot per-range sample override (director): logs/render_override.json {"ranges": [[first,last,samples],...]}
        if a <= f <= b: sc.eevee.taa_render_samples = smp
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print(f'FRAME {f} {time.time() - t:.1f} s{sc.eevee.taa_render_samples}', flush=True)
print('RENDER_DONE', flush=True)
