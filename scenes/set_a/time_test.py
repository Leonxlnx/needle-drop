"""Timing probe for set_a.blend at final resolution (run via brun --render). Writes nothing into the blend."""
import bpy, time, os, sys
sc = bpy.context.scene
out = os.path.join(os.getcwd(), 'renders', 'tests', 'set_a', 'tt_')
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
frame = int(argv[0]) if argv else 40


def go(tag):
    sc.frame_set(frame)
    sc.render.filepath = f'{out}{tag}_{frame:04d}.png'
    t = time.time(); bpy.ops.render.render(write_still=True)
    print(f'TIME {tag} {time.time() - t:.1f}', flush=True)


print('compositor_device', getattr(sc.render, 'compositor_device', '?'), 'precision', getattr(sc.render, 'compositor_precision', '?'))
go('warm')
go('base')
sc.render.use_compositing = False
go('nocomp')
sc.render.use_compositing = True
try:
    sc.render.compositor_device = 'GPU'
    go('compgpu')
except Exception as ex:
    print('no gpu comp', ex)
sc.render.use_motion_blur = False
go('nomb')
print('TT_DONE')
