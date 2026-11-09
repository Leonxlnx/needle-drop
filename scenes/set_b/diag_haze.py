"""Diagnostic (test renders only, nothing saved): which component makes the milky haze on the vinyl?
tools/brun.sh --render -- blend/set_b.blend --python scenes/set_b/diag_haze.py -- <tag> <frames>"""
import bpy, os, sys
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
tag = argv[0] if argv else 'dg'
FR = [int(x) for x in argv[1].split(',')] if len(argv) > 1 else [217]
sc = bpy.context.scene
sc.render.resolution_percentage = 50; sc.eevee.taa_render_samples = 16
vin = bpy.data.materials['M_Vinyl'].node_tree
bsdf = vin.nodes['Principled BSDF']


def strip_anim(idblock):
    if idblock.animation_data: idblock.animation_data_clear()


def variant(name):
    if name == 'nosheen':
        strip_anim(vin)
        for n in vin.nodes:
            if n.label.startswith('sheen_'): n.outputs[0].default_value = 0.0
    elif name == 'nostreak':
        ob = bpy.data.objects['VinylStreak']; strip_anim(ob.data); ob.data.energy = 0.0
    elif name == 'nobasespec':
        bsdf.inputs['Specular IOR Level'].default_value = 0.0
    elif name == 'nocoat':
        bsdf.inputs['Coat Weight'].default_value = 0.0
    elif name == 'nolights':
        for ob in bpy.data.objects:
            if ob.type == 'LIGHT' and ob.name not in ('Key',):
                strip_anim(ob.data); ob.data.energy = 0.0


for v in ['base'] + argv[2].split(',') if len(argv) > 2 else ['base', 'nosheen', 'nostreak', 'nobasespec', 'nocoat']:
    if v != 'base':
        bpy.ops.wm.revert_mainfile() if False else None
    variant(v)
    for f in FR:
        sc.frame_set(f)
        sc.render.filepath = os.path.join(os.getcwd(), 'renders', 'tests', 'set_b', f'{tag}_{v}_{f:04d}.png')
        bpy.ops.render.render(write_still=True); print('DIAG', v, f, flush=True)
    # restore cumulative changes are NOT undone: variants are cumulative in the order given
