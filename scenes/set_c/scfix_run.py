"""scfix (last-mile fix): in ONE Blender process (one lock wait):
  1. optionally render BEFORE frames from the blend opened on the command line (test overrides, never saved),
  2. rebuild blend/set_c.blend from scratch via build.py (saves the FINAL settings),
  3. render AFTER frames with test overrides (applied after the save, never saved).
  tools/brun.sh --threads 6 --render -- blend/set_c.blend --python scenes/set_c/scfix_run.py -- \
      --before 433,436 --after 433,436 --pct 33 --samples 16 --bout renders/tests/set_c/scfix_before_ --aout renders/tests/set_c/scfix1_
  (omit the .blend and --before to only rebuild + render after)."""
import bpy, sys, os, time, runpy

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
o = {'before': '', 'after': '', 'pct': 33, 'samples': 16, 'bout': 'renders/tests/set_c/scfix_before_', 'aout': 'renders/tests/set_c/scfix_'}
i = 0
while i < len(argv):
    k = argv[i].lstrip('-')
    if k in o:
        o[k] = argv[i + 1] if k not in ('pct', 'samples') else int(argv[i + 1]); i += 2
    else:
        i += 1


def frames_of(s):
    out = []
    for p in s.split(','):
        p = p.strip()
        if '-' in p:
            a, b = p.split('-'); out += list(range(int(a), int(b) + 1))
        elif p:
            out.append(int(p))
    return out


def render(frames, prefix):
    if not frames:
        return
    sc = bpy.context.scene
    sc.render.resolution_percentage = o['pct']
    ad = sc.animation_data
    if ad is not None and ad.action is not None:
        try:
            fcs = ad.action.fcurves
        except Exception:
            from bpy_extras import anim_utils
            fcs = anim_utils.action_get_channelbag_for_slot(ad.action, ad.action_slot).fcurves
        for fc in [fc for fc in fcs if 'taa_render_samples' in fc.data_path]:
            fcs.remove(fc)
    out = os.path.abspath(prefix)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    for f in frames:
        t = time.time()
        sc.frame_set(f)
        sc.eevee.taa_render_samples = o['samples']
        sc.render.filepath = f'{out}{f:04d}.png'
        bpy.ops.render.render(write_still=True)
        print(f'FRAME {prefix} {f} {time.time() - t:.1f}', flush=True)


render(frames_of(o['before']), o['bout'])
print('BEFORE_DONE', flush=True)
here = os.path.dirname(os.path.abspath(__file__))
sys.argv = [sys.argv[0], '--']
runpy.run_path(os.path.join(here, 'build.py'), run_name='__main__')
render(frames_of(o['after']), o['aout'])
print('RENDER_DONE', flush=True)
