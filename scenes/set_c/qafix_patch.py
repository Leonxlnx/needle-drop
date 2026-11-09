"""qafix (QA must-fix 1 kick-ring flashes + must-fix 2 descent jolt), ONE Blender process, blend/set_c.blend is
opened read-only (never saved over):
  1. render BEFORE test frames from the untouched scene (test overrides: muted sample keys + pct, nothing saved),
  2. patch ONLY the keys the fixes change, with the same functions build.py / c_cam.py now use:
       CamC location.z + CamC clip_start keys of the eased descent (c_cam.desc_exponent, f308-329),
       RecordLive ka0..ka2 keys in the S3 skim (build.py ring_near_fade, RING_NEAR),
     verify the eased camera footprint stays inside the stored view-cull keys, save as blend/set_c_fix.blend,
  3. render AFTER test frames from the patched scene.
tools/brun.sh --threads 6 --render -- blend/set_c.blend --python scenes/set_c/qafix_patch.py -- \
    --before 306,331 --after 306,331 --pct 33 --samples 16 --out renders/tests/qafix/r1_
"""
import bpy, sys, os, time, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from c_common import *          # noqa
import c_cam
from mathutils import Vector

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
o = {'before': '', 'after': '', 'pct': 33, 'samples': 16, 'out': 'renders/tests/qafix/r1_', 'save': 'blend/set_c_fix.blend'}
i = 0
while i < len(argv):
    k = argv[i].lstrip('-')
    if k in o:
        o[k] = int(argv[i + 1]) if k in ('pct', 'samples') else argv[i + 1]; i += 2
    else:
        i += 1
FIX = os.path.abspath(o['save'])
assert os.path.basename(FIX) not in ('set_a.blend', 'set_b.blend', 'set_c.blend'), FIX
OUT = os.path.abspath(o['out'])
assert 'final' not in OUT.replace('\\', '/').split('/'), OUT
os.makedirs(os.path.dirname(OUT), exist_ok=True)
RING_NEAR = (16.0, 48.0)
assert 'RING_NEAR = (16.0, 48.0)' in open(os.path.join(HERE, 'build.py'), encoding='utf-8').read()


def log(*a):
    print('[qafix]', *a, flush=True)


def frames_of(s):
    out = []
    for p in s.split(','):
        p = p.strip()
        if '-' in p:
            a, b = p.split('-'); out += list(range(int(a), int(b) + 1))
        elif p:
            out.append(int(p))
    return out


def fcurves(idb):
    ad = idb.animation_data
    if ad is None or ad.action is None:
        return []
    try:
        return list(ad.action.fcurves)
    except Exception:
        from bpy_extras import anim_utils
        return list(anim_utils.action_get_channelbag_for_slot(ad.action, ad.action_slot).fcurves)


def fc_get(idb, path, index=0):
    for fc in fcurves(idb):
        if fc.data_path == path and fc.array_index == index:
            return fc
    raise KeyError((idb.name, path, index))


def set_key(fc, f, v):
    for kp in fc.keyframe_points:
        if abs(kp.co.x - f) < 1e-3:
            dy = v - kp.co.y
            kp.co.y = v; kp.handle_left.y += dy; kp.handle_right.y += dy
            return dy
    raise KeyError((fc.data_path, f))


sc = bpy.context.scene
cam = bpy.data.objects['CamC']; cd = cam.data
log('motion blur', sc.render.use_motion_blur, 'position', getattr(sc.render, 'motion_blur_position', '?'))
smp_fcs = [fc for fc in fcurves(sc) if 'taa_render_samples' in fc.data_path]
PCT0, SMP0 = sc.render.resolution_percentage, sc.eevee.taa_render_samples


def overrides(on):
    for fc in smp_fcs:
        fc.mute = on
    sc.render.resolution_percentage = o['pct'] if on else PCT0
    sc.eevee.taa_render_samples = o['samples'] if on else SMP0


def render(frames, tag):
    overrides(True)
    for f in frames:
        t = time.time()
        sc.frame_set(f)
        sc.eevee.taa_render_samples = o['samples']
        sc.render.filepath = f'{OUT}{tag}_{f:04d}.png'
        bpy.ops.render.render(write_still=True)
        log(f'FRAME {tag} {f} {time.time() - t:.1f}s')
    overrides(False)


# ---------------------------------------------------------------- cull coverage check (view cull keys are NOT changed)
ng = None
for g in bpy.data.node_groups:
    if g.nodes.get('ka0') is not None and g.nodes.get('c_dmax') is not None and g.animation_data is not None:
        ng = g
log('live node group', ng.name)
CK = {k: fc_get(ng, f'nodes["{k}"].outputs[0].default_value') for k in ('c_x', 'c_y', 'c_hx', 'c_hy', 'c_cos', 'c_dmax', 'c_near')}


def cull_margin(f):
    sc.frame_set(f)
    M = cam.matrix_world; C0 = M.translation.copy(); R = M.to_3x3()
    tw = 18.0 / cd.lens * 1.12; th = tw * 9 / 16 * 1.12
    k = {n: fc.evaluate(f) for n, fc in CK.items()}
    worst = 1e9
    for u in np.linspace(-1, 1, 9):
        for v in np.linspace(-1, 1, 7):
            d = R @ Vector((u * tw, v * th, -1.0)); d.normalize()
            tt_ = min(C0.z / -d.z, 3200.0) if d.z < -1e-4 else 3200.0
            p = C0 + d * tt_
            vx, vy = p.x - k['c_x'], p.y - k['c_y']; dd = math.hypot(vx, vy)
            ca = (vx * k['c_hx'] + vy * k['c_hy']) / max(dd, 1e-3)
            m = max(k['c_near'] - dd, min(k['c_dmax'] - dd, 1e3 * (ca - k['c_cos'])))
            worst = min(worst, m)
    return worst, C0.z


def snapshot():
    """every keyframe value of every animated datablock (+ its node tree), for an exhaustive before/after key diff"""
    snap = {}
    for coll in (bpy.data.objects, bpy.data.cameras, bpy.data.lights, bpy.data.materials, bpy.data.node_groups,
                 bpy.data.scenes, bpy.data.worlds, bpy.data.meshes):
        for idb in coll:
            for d in (idb, getattr(idb, 'node_tree', None)):
                if d is None:
                    continue
                for fc in fcurves(d):
                    snap[(type(d).__name__, d.name, fc.data_path, fc.array_index)] = [tuple(kp.co) for kp in fc.keyframe_points]
    return snap


# ---------------------------------------------------------------- 1. BEFORE
render(frames_of(o['before']), 'before')
log('BEFORE_DONE')
SNAP0 = snapshot()
log('snapshot fcurves', len(SNAP0), 'keys', sum(len(v) for v in SNAP0.values()))

# ---------------------------------------------------------------- 2a. descent ease-in (camera z + clip_start)
fz = fc_get(cam, 'location', 2); fclip = fc_get(cd, 'clip_start', 0)
cam_changed, before_m = [], {}
rows = []
for f in range(F0, 433):
    t = t_of(f)
    if not (12.75 < t < 16.0):
        continue
    u = (t - 12.75) / 3.25
    e0, e1 = c_cam.desc_exponent(u, False), c_cam.desc_exponent(u, True)
    if abs(e1 - e0) < 1e-12:
        continue
    before_m[f] = cull_margin(f)
    a0, a1 = 380.0 * (7.0 / 380.0) ** e0, 380.0 * (7.0 / 380.0) ** e1
    clip_old = fclip.evaluate(f)
    if abs(clip_old - float(np.clip(0.05 * a0, 0.08, 40.0))) > 1e-3:
        log('WARN clip key mismatch', f, clip_old, a0)
    set_key(fz, f, fz.evaluate(f) + (a1 - a0))
    set_key(fclip, f, float(np.clip(0.05 * a1, 0.08, 40.0)))
    cam_changed.append(f); rows.append((f, a0, a1))
fz.update(); fclip.update()
log('CAM keys changed:', cam_changed[0] if cam_changed else None, '-', cam_changed[-1] if cam_changed else None, len(cam_changed))
for f in range(305, 333):
    t = t_of(f); u = max((t - 12.75) / 3.25, 0.0)
    al = [380.0 * (7.0 / 380.0) ** c_cam.desc_exponent(uu, ez) for uu in (u, max((t_of(f + 1) - 12.75) / 3.25, 0.0)) for ez in (False, True)]
    log(f'ZOOM f{f} alt old {al[0]:7.2f} new {al[1]:7.2f}  rate/frame old {100 * (1 - al[2] / al[0]):5.2f}% new {100 * (1 - al[3] / al[1]):5.2f}%')
worst = 1e9
for f in cam_changed:
    m1, z1 = cull_margin(f)
    worst = min(worst, m1)
    log(f'CULL f{f} margin before {before_m[f][0]:7.1f} m (z {before_m[f][1]:.1f}) after {m1:7.1f} m (z {z1:.1f})')
log('CULL worst margin after (must be > 0):', round(worst, 1), 'OK' if worst > 0 else 'CULL_FAIL')

# ---------------------------------------------------------------- 2b. kick-ring near-lens fade (S3 skim, t >= 16.0)
fx_, fy_ = fc_get(cam, 'location', 0), fc_get(cam, 'location', 1)
ring_changed = set()
for s in range(3):
    fkr = fc_get(ng, f'nodes["kr{s}"].outputs[0].default_value')
    fka = fc_get(ng, f'nodes["ka{s}"].outputs[0].default_value')
    for kp in list(fka.keyframe_points):
        f = kp.co.x; t = t_of(f)
        # f > CUT: the 432.51 half-frame key belongs to the S4 camera (build.py evaluates path.s3 there -> g = 1)
        if t < 16.0 or t >= 18.0 or f > c_cam.CUT or kp.co.y == 0.0:
            continue
        kr = fkr.evaluate(f)
        rc = math.hypot(fx_.evaluate(f), fy_.evaluate(f))
        calt = 7.0 - 0.8 * math.sin(2 * math.pi * (t - 16.0) / 1.5)       # c_cam.Path.s3 alt for t >= 16.0
        g = float(smoothstep(RING_NEAR[0], RING_NEAR[1], math.hypot(kr - rc, calt)))
        new = kp.co.y * g
        if abs(new - kp.co.y) > 1e-7:
            log(f'RING f{f:.2f} slot{s} d_ahead {kr - rc:6.1f} ka {kp.co.y:.3f} -> {new:.3f}')
            set_key(fka, f, new)
            ring_changed.add(f)
    fka.update()
rc_ = sorted(ring_changed)
log('RING keys changed:', rc_)
SNAP1 = snapshot()
allf = set()
assert set(SNAP0) == set(SNAP1), 'fcurve set changed'
for k in sorted(SNAP0):
    a, b = SNAP0[k], SNAP1[k]
    assert [p[0] for p in a] == [p[0] for p in b], ('key frames moved', k)
    fr = [p[0] for p, q in zip(a, b) if p[1] != q[1]]
    if fr:
        allf.update(fr)
        log(f'KEYDIFF {k[0]} {k[1]} {k[2]}[{k[3]}]: {len(fr)} keys, frames {min(fr):.2f}-{max(fr):.2f}')
log('KEYDIFF all changed key frames:', sorted(allf))

# ---------------------------------------------------------------- save the fix blend (final settings intact)
overrides(False)
sc.frame_set(F0)
bpy.ops.wm.save_as_mainfile(filepath=FIX, compress=False, copy=True)
log('SAVED', FIX)

# ---------------------------------------------------------------- 3. AFTER
render(frames_of(o['after']), 'after')
log('RENDER_DONE')
