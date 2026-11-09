"""Test-only: camera smoothness on blend/set_b.blend (no render). Prints per-frame world speed (mm/frame),
view-direction turn rate (deg/frame) and flags jerks (speed or turn-rate jumps > 35% between frames above a floor)."""
import bpy, math
sc = bpy.context.scene; cam = sc.camera
prev = None; rows = []
for f in range(sc.frame_start - 1, sc.frame_end + 1):
    sc.frame_set(f)
    m = cam.matrix_world.copy(); p = m.translation.copy(); d = (m.to_3x3() @ __import__('mathutils').Vector((0, 0, -1))).normalized()
    if prev is not None:
        sp = (p - prev[0]).length * 1000.0
        tr = math.degrees(math.acos(max(-1.0, min(1.0, d.dot(prev[1])))))
        rows.append((f, sp, tr))
    prev = (p, d)
for i, (f, sp, tr) in enumerate(rows):
    flag = ''
    if i > 0:
        sp0, tr0 = rows[i - 1][1], rows[i - 1][2]
        if max(sp, sp0) > 0.5 and abs(sp - sp0) / max(sp, sp0) > 0.35: flag += ' SPEEDJUMP'
        if max(tr, tr0) > 0.4 and abs(tr - tr0) / max(tr, tr0) > 0.35: flag += ' TURNJUMP'
    if f % 4 == 0 or flag:
        print('MOTION %d speed_mm %.2f turn_deg %.3f%s' % (f, sp, tr, flag))
print('MOTION_DONE')
