"""SET C build: the Desert Record (S3-S6, global frames 289-708). Rebuilds blend/set_c.blend from scratch.
Run:  tools/brun.sh --threads 6 -- --python scenes/set_c/build.py
Optional args after '--':  --nofx  --notrees  --out <path.blend>
"""
import bpy, sys, os, time, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from c_common import *          # noqa
import c_terrain, c_look, c_cam, c_props, c_fx

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = os.path.join(ROOT, 'blend', 'set_c.blend')
if '--out' in argv:
    OUT = os.path.abspath(argv[argv.index('--out') + 1])
T0 = time.time()


def log(*a):
    print(f'[setc {time.time()-T0:6.1f}s]', *a, flush=True)


sc = C.reset()
sc.name = 'SetC'
c_look.render_settings(sc)
bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'
coll = bpy.data.collections.new('SetC'); sc.collection.children.link(coll)
fxc = bpy.data.collections.new('SetC_FX'); sc.collection.children.link(fxc)

c_look.world(sc); sun = c_look.sun(sc); c_look.compositor(sc)
log('look')
disc, patch, outer, live, ground = c_terrain.build(coll)
log('terrain')
cam, path, alts = c_cam.bake_camera(sc, ground)
log('camera')

# ---------------------------------------------------------------- RecordLive inputs (node-tree keys)
frames = list(range(F0, F1 + 1)) + [c_cam.CUT - 0.01, c_cam.CUT + 0.01]
frames.sort()
fr_arr = np.array(frames, float)
bands = band_series(fr_arr)
KS = [(tk, s) for tk, s in kicks() if 12.0 <= tk < 17.5]
V_RING = 220.0


def ring_r0(tk):
    pos = path.s3(f_of(tk), ease=False)[0]          # qafix: un-eased descent, so ring timing/positions stay as before
    alt = pos[2] - path.gx(pos[0])
    return pos[0] - (35.0 + 210.0 * min(1.0, alt / 380.0))


R0 = [ring_r0(tk) for tk, _ in KS]
# qafix (QA must-fix 1): in the S3 skim (t >= 16.0: lens ~7 m over the sand, pitch -3 deg) a kick ring born ~39 m behind
# the lens crossed the bottom third in ~1 frame (220 m/s) -> one-frame washed-out flash (f392/404/416). The ring amplitude
# now fades to zero within RING_NEAR[0] m (3D) of the lens and is untouched beyond RING_NEAR[1] m: rings rise ahead and
# travel out as before, the 17.5-18.0 hang ring (~50 m ahead) is unchanged, descent kicks (t < 16) are unchanged.
RING_NEAR = (16.0, 48.0)


def ring_near_fade(t, kr, cpos, calt):
    if t < 16.0:
        return 1.0
    return float(smoothstep(RING_NEAR[0], RING_NEAR[1], math.hypot(kr - math.hypot(cpos[0], cpos[1]), calt)))


nodes = live.nodes
SN = bpy.data.materials['M_Sand'].node_tree.nodes
for fi, f in enumerate(frames):
    t = t_of(f); ta = float(tau(t))
    vals = {'front': float(front_r(t))}
    for s in range(3):
        vals[f'kr{s}'] = -500.0; vals[f'ka{s}'] = 0.0
    if t < 18.0:
        cpos, _h, _p, _r, _l, calt = path.s3(f)
        for i, (tk, st) in enumerate(KS):
            s = i % 3
            age = ta - tk
            if age < 0:
                continue
            A = (0.6 + 0.6 * float(smoothstep(14.0, 17.5, tk))) * st
            env = (1 - math.exp(-age / 0.03)) * math.exp(-age / 0.7) * (1 - float(smoothstep(1.0, 1.45, age)))
            vals[f'kr{s}'] = R0[i] + V_RING * age
            vals[f'ka{s}'] = A * env * ring_near_fade(t, vals[f'kr{s}'], cpos, calt)
    for b in range(8):
        vals[f'b{b}'] = float(bands[fi, b])
    vals['pulse_amp'] = float(smoothstep(20.0, 20.6, t))
    for k, v in vals.items():
        sock = nodes[k].outputs[0]
        sock.default_value = v
        sock.keyframe_insert('default_value', frame=f)
    # adr2: ring pulses live in the M_Sand shader (zone + keyed bands) for both the live and the static disc
    for b in range(8):
        sk = SN[f'sb{b}'].outputs[0]; sk.default_value = vals[f'b{b}']; sk.keyframe_insert('default_value', frame=f)
    sk = SN['spa'].outputs[0]; sk.default_value = vals['pulse_amp']; sk.keyframe_insert('default_value', frame=f)
log('live keys')

# ---------------------------------------------------------------- disc spin from 24.0 s (0 -> 3 deg/s by 25.0)
tt = np.linspace(24.0, 30.0, 6001)
om = 3.0 * smoothstep(24.0, 25.0, tt)
ang = np.concatenate([[0], np.cumsum(0.5 * (om[1:] + om[:-1]) * np.diff(tt))])
for f in range(570, F1 + 1):
    t = t_of(f)
    disc.rotation_euler.z = math.radians(float(np.interp(t, tt, ang)) if t > 24.0 else 0.0)
    disc.keyframe_insert('rotation_euler', index=2, frame=f)

# ---------------------------------------------------------------- view cull for the record (GN Delete Geometry)
from mathutils import Vector
CULL = '--nocull' not in argv


def footprint(f):
    # qafix: cull keys from the un-eased path so every 12-frame cull block stays bit-identical; the eased descent
    # (f308-329, at most ~30 m higher) stays inside the +200 m dmax margin (checked by scenes/set_c/qafix_patch.py)
    pos, hd, pt, rl, lens, alt = path.at(f, ease=False)
    q = c_cam.quat(hd, pt, rl)
    tw = 18.0 / lens * 1.12; th = tw * 9 / 16 * 1.12 / 1.0
    C0 = Vector(pos); pts = []
    for u in np.linspace(-1, 1, 9):
        for v in np.linspace(-1, 1, 7):
            d = q @ Vector((u * tw, v * th, -1.0)); d.normalize()
            if d.z < -1e-4:
                tt_ = (C0.z - 0.0) / -d.z
                tt_ = min(tt_, 3200.0)
            else:
                tt_ = 3200.0
            p = C0 + d * tt_
            pts.append((p.x, p.y))
    return np.array(pts), np.array(pos[:2]), alt


def spin_at(f):
    t = t_of(f)
    return math.radians(float(np.interp(t, tt, ang))) if t > 24.0 else 0.0


cull_keys = {}
if CULL:
    for b0 in range(F0, F1 + 1, 12):
        blk = [f for f in range(b0 - 1, min(b0 + 12, F1 + 1) + 1)]
        allp, cams, alts_ = [], [], []
        for f in blk:
            p, c, a = footprint(f)
            s_ = spin_at(f); cs, sn = math.cos(-s_), math.sin(-s_)
            R = np.array([[cs, -sn], [sn, cs]])
            allp.append(p @ R.T); cams.append(R @ c); alts_.append(a)
        P = np.concatenate(allp); Cs = np.array(cams)
        cen = Cs[len(Cs) // 2]
        mv = np.abs(Cs - cen).max() if len(Cs) else 0
        near = max(160.0, 0.35 * max(alts_)) + mv
        V_ = P - cen; dist = np.hypot(V_[:, 0], V_[:, 1])
        fwd = V_[dist > 1].mean(axis=0) if (dist > 1).any() else np.array([1.0, 0.0])
        h = fwd / max(np.linalg.norm(fwd), 1e-6)
        ang_ = np.degrees(np.arccos(np.clip((V_ @ h) / np.maximum(dist, 1e-3), -1, 1)))
        far = dist > near * 0.8
        amax = (ang_[far].max() if far.any() else 0.0) + 16.0
        cosA = math.cos(math.radians(amax)) if amax < 178 else -2.0
        dmax = dist.max() + 200.0
        if (dist < 1).any() or amax >= 178:
            cosA = -2.0
        for f in range(b0, min(b0 + 12, F1 + 1)):
            cull_keys[f] = dict(c_x=float(cen[0]), c_y=float(cen[1]), c_hx=float(h[0]), c_hy=float(h[1]), c_cos=float(cosA),
                                c_dmax=float(dmax), c_near=float(near))
    bpy.context.preferences.edit.keyframe_new_interpolation_type = 'CONSTANT'
    prev = None
    for f in range(F0, F1 + 1):
        k = cull_keys[f]
        if k != prev or f == F0:
            for nm, v in k.items():
                sock = nodes[nm].outputs[0]; sock.default_value = v
                sock.keyframe_insert('default_value', frame=f)
            prev = k
    bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'
    log('cull keys', len(set(tuple(sorted(v.items())) for v in cull_keys.values())))

# ---------------------------------------------------------------- props
c_props.label_text(coll, disc)
c_props.mesas(coll)
c_props.far_plane(coll)
if '--notrees' not in argv:
    c_props.trees(coll)
    bs = c_props.boulders(coll, ground)
    c_props.key_boulders(bs)
yaw, lift, arm_parts, used_asset = c_props.tonearm(coll)
c_props.key_tonearm(yaw, lift)
log('props')

# ---------------------------------------------------------------- FX + LOD
_L = pol(*L_LAND)
_d = math.hypot(c_cam.E6[0] - _L[0], c_cam.E6[1] - _L[1])
c_fx.CAMDIR6[:] = [(c_cam.E6[0] - _L[0]) / _d, (c_cam.E6[1] - _L[1]) / _d]
c_fx.Q6[:] = [c_cam.E6[0], c_cam.E6[1], c_cam.ALT6]
fx = {} if '--nofx' in argv else c_fx.build(fxc, ground, path)
if '--nofx' not in argv:
    for i, o in enumerate(c_fx.curtains(fxc)):
        fx[f'Curtain{i}'] = o
    for i, o in enumerate(c_fx.touchdown_ring(fxc)):
        fx[f'TouchRing{i}'] = o
vis = {
    'FloatGrains': [(405, 432)], 'FrontDust': [(433, 505)], 'FrontSheet': [(433, 460)], 'FrontEngulf': [(445, 470)],
    'EngulfStreaks': [(452, 464)], 'FrontGrains': [(433, 500)], 'Curtain0': [(433, 460)], 'Curtain1': [(433, 470)],
    'DropGeyser': [(433, 450)],
    'Curtain2': [(433, 472)],
    'TouchdownSkirt': [(688, F1)], 'TouchdownDust': [(696, F1)], 'TouchdownSpray': [(696, F1)], 'TouchdownGrains': [(696, F1)],
    'TouchSurge': [(696, F1)], 'TouchFan': [(696, F1)], 'TipGlint': [(694, 704)],
    'TouchRing0': [(696, F1)], 'TouchRing1': [(696, F1)],
}
for k, rg in vis.items():
    if k in fx:
        c_fx.key_visibility(fx[k], rg)
c_fx.key_visibility(patch, [(F0, 541)])
c_fx.key_visibility(disc, [(F0, 516)])                     # adr2: live GN disc only while it morphs
c_fx.key_visibility(bpy.data.objects[disc['static']], [(517, F1)])
for p in arm_parts + [yaw, lift]:
    c_fx.key_visibility(p, [(589, F1)])
# adr2: camera-only sun-shadow proxies for the S5 top-down (arm S-shadow + label-mesa shadow)
for o in c_fx.shadow_proxy(coll, [p for p in arm_parts if getattr(p, 'type', '') == 'MESH']):
    c_fx.key_visibility(o, [(570, 650)])
# adr2: keyed hot rings in M_Sand: f433 drop flash at the label-mesa base, touchdown shock ring from L (f697-708)
_sn = bpy.data.materials['M_Sand'].node_tree.nodes
# scfix: 12 -> 4 peak (saturated, never white), ring radius keyed ~30 m ahead of the dust front (visibly expands)
for f, v in ((432, 0.0), (433, 4.0), (434, 3.8), (436, 3.0), (438, 2.0), (440, 1.0), (442, 0.3), (444, 0.0)):
    _sn['flash433'].outputs[0].default_value = v; _sn['flash433'].outputs[0].keyframe_insert('default_value', frame=f)
for f in range(432, 445):
    _sn['flash_r'].outputs[0].default_value = max(272.0, float(front_r(t_of(f))) + 30.0)
    _sn['flash_r'].outputs[0].keyframe_insert('default_value', frame=f)
for f in range(694, F1 + 1):
    a = max(t_of(f) - 28.97, 0.0)
    rr = 400.0 * (1 - math.exp(-a / 0.22)) + 20.0 * a
    ee = 0.0 if f < 697 else 3.0 * math.exp(-a / 0.28)
    _sn['td_r'].outputs[0].default_value = rr; _sn['td_r'].outputs[0].keyframe_insert('default_value', frame=f)
    _sn['td_e'].outputs[0].default_value = ee; _sn['td_e'].outputs[0].keyframe_insert('default_value', frame=f)
log('fx')

# ---------------------------------------------------------------- mist + samples per shot
w = sc.world
for f in range(F0, F1 + 1):
    alt = alts[f][0]
    w.mist_settings.start = float(max(0.8 * alt, 2.0)) if f < 643 else float(max(0.8 * alt, 2.0)) * (1 - 0.6 * float(smoothstep(643, 679, f)))
    if f < 517:   # adr2: S3/S4 mid-distance outer desert stays saturated; mist only does the kilometre fade
        w.mist_settings.start = float(max(0.8 * alt, 900.0))
    w.mist_settings.keyframe_insert('start', frame=f)
    w.mist_settings.depth = 6000.0 - 3600.0 * float(smoothstep(643, 679, f))
    w.mist_settings.keyframe_insert('depth', frame=f)
try:
    for f, s in ((F0, 48), (432, 48), (433, 48), (517, 48)):          # adr1 budget: no 56-sample block in S4
        sc.eevee.taa_render_samples = s
        sc.eevee.keyframe_insert('taa_render_samples', frame=f)
except Exception as ex:
    print('WARN samples not animatable', ex)
    sc.eevee.taa_render_samples = 48
try:
    for f, v in ((F0, 0.5), (322, 0.5), (332, 0.25), (384, 0.25), (392, 0.3), (424, 0.3), (432, 0.45), (433, 0.5),
                 (638, 0.5), (644, 0.25), (684, 0.25), (690, 0.4), (F1, 0.4)):
        sc.render.motion_blur_shutter = v
        sc.render.keyframe_insert('motion_blur_shutter', frame=f)
except Exception as ex:
    print('WARN shutter not animatable', ex)
# S3 hold: the low sun sinks 14 -> 9 deg over f289-330 so dune shadows slowly reveal relief (bible S3)
for f, e in ((F0, 14.0), (330, SUN_ELEV)):
    sun.rotation_euler.x = math.radians(-(90.0 - e)); sun.keyframe_insert('rotation_euler', index=0, frame=f)
# soft jittered sun shadows for the S5/S6 sculpted relief + arm shadow (costly: only from f556)
try:
    sl = sun.data
    for f, v in ((F0, False), (F1, False)):      # adr1: jitter measured at ~3x S6 cost (f702 23 -> 73 s): off; filter radius only
        sl.use_shadow_jitter = v
        sl.keyframe_insert('use_shadow_jitter', frame=f)
except Exception as ex:
    print('WARN jitter not animatable', ex)
# NOTE (adr1): ray_tracing_options.resolution_scale is NOT animatable in 5.2, so a per-shot quarter-res raytrace for the
# S4 dust (f433-500) must be done as a render-time override by the director (render_frames.py), not keyed here.
# stronger aerial perspective for the colossal S6 reveal
mk = sc.compositing_node_group.nodes.get('MistK')
if mk is not None:
    for f, v in ((F0, c_look.MIST_K), (640, c_look.MIST_K), (679, 0.3), (F1, 0.3)):
        mk.inputs[1].default_value = v
        mk.inputs[1].keyframe_insert('default_value', frame=f)
_cn = sc.world.node_tree.nodes.get('cirrus')
if _cn is not None:
    for f, v in ((F0, 0.0), (640, 0.0), (660, 1.0), (F1, 1.0)):
        _cn.outputs[0].default_value = v; _cn.outputs[0].keyframe_insert('default_value', frame=f)
# streak glare only on the touchdown glint
st = sc.compositing_node_group.nodes.get('Streaks')
if st is not None:
    for f, v in ((F0, 0.0), (432, 0.0), (433, 0.15), (435, 0.15), (436, 0.0), (694, 0.0), (696, 0.0), (697, 0.16), (699, 0.1),
                 (702, 0.08), (F1, 0.04)):
        st.inputs['Strength'].default_value = v
        st.inputs['Strength'].keyframe_insert('default_value', frame=f)

write_layout({'tonearm_asset_used': used_asset,
              'tonearm_rig': {'append': 'blend/tonearm_asset.blend collection TonearmAsset, appended as real objects (renamed TonearmGiant), '
                                        'ArmPivot parented to ArmLift, rot Z +90 deg, scale ARM_LEN/0.235 = 8000',
                              'pivot_height_m': yaw.location.z, 'cheats': {k: v[0] for k, v in c_props.ARM_CHEAT.items()},
                              'yaw_swing_s': [25.25, 26.75], 'yaw_ease': 'ease-out 1-(1-s)^2.2', 'lift_s': [26.75, 29.0],
                              'touchdown_frame': 697},
              'fx': {k: (len(o.data.vertices) if getattr(o, 'type', '') == 'MESH' else o.type) for k, o in fx.items()},
              's6_end_camera': {'pos_xy': list(c_cam.E6), 'alt': c_cam.ALT6, 'heading': c_cam.HEAD6,
                                'pitch': c_cam.PITCH6, 'lens': c_cam.LENS6, 'phi_d': [c_cam.PHI6, c_cam.D6]}})
sc.frame_set(F0)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=OUT, compress=False)
log('saved', OUT)
print('BUILD_DONE')
