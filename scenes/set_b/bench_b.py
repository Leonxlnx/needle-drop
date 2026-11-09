"""Profile render cost of set_b settings on one frame (run on blend/set_b.blend). Test-only; never saves."""
import bpy, time, os, sys
sc = bpy.context.scene; e = sc.eevee
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
fr = int(argv[0]) if argv else 217
pct = int(argv[1]) if len(argv) > 1 else 50
sc.render.resolution_percentage = pct
out = os.path.join(os.getcwd(), 'renders', 'tests', 'set_b', 'bench_')
sc.frame_set(fr)
def run(tag):
    t = time.time(); sc.render.filepath = out + tag + '.png'; bpy.ops.render.render(write_still=True)
    print('BENCH', tag, round(time.time() - t, 1), flush=True)
run('warm')
e.taa_render_samples = 64; run('base64')
sc.render.use_compositing = False; run('nocomp64'); sc.render.use_compositing = True
e.use_raytracing = False; run('nort64'); e.use_raytracing = True
e.use_bokeh_jittered = False; run('nojit64'); e.use_bokeh_jittered = True
sc.render.use_motion_blur = False; run('nomb64'); sc.render.use_motion_blur = True
e.taa_render_samples = 32; run('base32')
e.use_bokeh_jittered = False; e.taa_render_samples = 32; run('nojit32')
print('BENCH_DONE')
