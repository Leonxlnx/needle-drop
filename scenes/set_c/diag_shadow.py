"""adr2 diagnostic: why the S5 top-down shows no arm / mesa shadow. Renders f630 in variants."""
import bpy, os, time
sc = bpy.context.scene
sc.render.resolution_percentage = 25
ad = sc.animation_data
out = os.path.abspath('renders/tests/set_c/dg_')
sun = bpy.data.objects['Sun'].data
def strip(path):
    if ad and ad.action:
        try:
            fcs = ad.action.fcurves
        except Exception:
            from bpy_extras import anim_utils
            fcs = anim_utils.action_get_channelbag_for_slot(ad.action, ad.action_slot).fcurves
        for fc in [fc for fc in fcs if path in fc.data_path]:
            fcs.remove(fc)
strip('taa_render_samples')
sun.animation_data_clear()
sc.eevee.taa_render_samples = 16
cam = sc.camera
print('CAM clip', cam.data.clip_start, cam.data.clip_end)
print('SUNPROPS', [p.identifier for p in sun.bl_rna.properties if 'shadow' in p.identifier])
cam.data.animation_data_clear() if False else None
def clipf():
    fc = cam.data.animation_data
    cam.data.clip_end = 9000.0
def reset():
    sc.eevee.shadow_pool_size = '1024'; sun.use_shadow_jitter = False; cam.data.clip_end = 120000.0
for tag, fn in (('pool', lambda: setattr(sc.eevee, 'shadow_pool_size', '2048')),
                ('clip', clipf),
                ('jit', lambda: setattr(sun, 'use_shadow_jitter', True))):
    reset(); fn()
    t = time.time(); sc.frame_set(630)
    sc.render.filepath = f'{out}{tag}_0630.png'
    bpy.ops.render.render(write_still=True)
    print('DIAG', tag, round(time.time() - t, 1), flush=True)
print('RENDER_DONE')
