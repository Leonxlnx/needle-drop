"""Post-build check for the f256-272 shutter fix (prints only; saves nothing).
tools/brun.sh --threads 6 -- --python scenes/set_b/build.py --python scenes/set_b/mbfix_check.py"""
import bpy
sc = bpy.context.scene
r = sc.render
fc = None
if sc.animation_data and sc.animation_data.action:
    for c in getattr(sc.animation_data.action, 'fcurves', []):
        if c.data_path == 'render.motion_blur_shutter': fc = c
if fc is None:
    try:
        from bpy_extras import anim_utils
        cb = anim_utils.action_get_channelbag_for_slot(sc.animation_data.action, sc.animation_data.action_slot)
        fc = cb.fcurves.find('render.motion_blur_shutter')
    except Exception as ex:
        print('MBCHK_FC_ERR', ex)
print('MBCHK_KEYS', [(round(k.co[0], 2), round(k.co[1], 4), k.interpolation, k.handle_left_type) for k in fc.keyframe_points] if fc else None)
for f in range(250, 279):
    print('MBCHK_SHUTTER', f, repr(fc.evaluate(f)) if fc else None)
print('MBCHK_SETTINGS', r.resolution_x, r.resolution_y, r.resolution_percentage, sc.eevee.taa_render_samples,
      r.use_motion_blur, sc.frame_start, sc.frame_end, sc.view_settings.view_transform, sc.view_settings.look,
      round(sc.view_settings.exposure, 4), r.fps, bpy.data.filepath)
