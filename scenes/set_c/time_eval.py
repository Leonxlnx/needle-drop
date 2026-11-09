"""Measure depsgraph (GN) evaluation time vs render time for chosen frames.
tools/brun.sh --render -- blend/set_c.blend --python scenes/set_c/time_eval.py -- 320,450,600"""
import bpy, sys, time, os
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
frames = [int(x) for x in (argv[0] if argv else '320,450,600').split(',')]
sc = bpy.context.scene
for f in frames:
    t = time.time(); sc.frame_set(f); te = time.time() - t
    t = time.time(); sc.frame_set(f + 1); te2 = time.time() - t
    print(f'EVAL f{f} {te:.2f}s  f{f+1} {te2:.2f}s', flush=True)
sc.render.resolution_percentage = 50; sc.eevee.taa_render_samples = 16
out = os.path.join(os.getcwd(), 'renders', 'tests', 'set_c', 'te_')
for f in frames[:2]:
    for mb in (False, True):
        sc.render.use_motion_blur = mb
        sc.frame_set(f); sc.render.filepath = f'{out}{f:04d}_{int(mb)}.png'
        t = time.time(); bpy.ops.render.render(write_still=True)
        print(f'RENDER f{f} mb={mb} {time.time()-t:.1f}s', flush=True)
print('TIME_DONE')
