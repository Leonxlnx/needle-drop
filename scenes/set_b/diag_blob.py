"""Diagnostic (test renders only, nothing saved): source of the lilac reflection blob at f262-266 (cumulative
switch-offs), plus a consecutive 50% strip f206-213 for the shimmer check.
tools/brun.sh --render -- blend/set_b.blend --python scenes/set_b/diag_blob.py -- <tag>"""
import bpy, os, sys
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
tag = argv[0] if argv else 'db'
sc = bpy.context.scene
sc.render.resolution_percentage = 50; sc.eevee.taa_render_samples = 16
out = os.path.join(os.getcwd(), 'renders', 'tests', 'set_b')
for f in range(206, 214):
    sc.frame_set(f); sc.render.filepath = os.path.join(out, f'{tag}_strip_{f:04d}.png')
    bpy.ops.render.render(write_still=True); print('STRIP', f, flush=True)


def off(name):
    ob = bpy.data.objects.get(name)
    if ob is None: return
    if ob.type == 'LIGHT':
        if ob.data.animation_data: ob.data.animation_data_clear()
        ob.data.energy = 0.0
    else:
        ob.hide_render = True
for v, names in (('base', []), ('nokick', ['LabelKick']), ('norim', ['RimMagenta']), ('nofill', ['FillUltra']),
                 ('noprobe', ['PlatterProbe']), ('nokeystrobe', ['Key', 'StrobePoint'])):
    for n in names: off(n)
    sc.frame_set(266); sc.render.filepath = os.path.join(out, f'{tag}_{v}_0266.png')
    bpy.ops.render.render(write_still=True); print('DIAG', v, flush=True)
