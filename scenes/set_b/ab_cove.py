"""A/B helper (test renders only, nothing saved): run after build.py in the same session.
Renders the given frames with the cyc's probe-reflection dimming disabled (cove_refl_k = 1) for comparison."""
import bpy, os, sys
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
tag = argv[0] if argv else 'ab'
FR = [217, 256]
sc = bpy.context.scene
for n in bpy.data.materials['M_Cove'].node_tree.nodes:
    if n.label == 'cove_refl_k': n.outputs[0].default_value = 1.0
sc.render.resolution_percentage = 50; sc.eevee.taa_render_samples = 16
for f in FR:
    sc.frame_set(f); sc.render.filepath = os.path.join(os.getcwd(), 'renders', 'tests', 'set_b', f'{tag}_nocovek_{f:04d}.png')
    bpy.ops.render.render(write_still=True); print('FRAME_AB', f, flush=True)
