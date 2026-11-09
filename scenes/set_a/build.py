"""NEEDLE DROP / SET A: THE GROOVE (S1, global frames 1-120).
Rebuilds blend/set_a.blend from scratch, deterministic.
Run:  tools/brun.sh --threads 6 -- --python scenes/set_a/build.py

Round-1 refine (AD r1): trench-run camera (design.py), bible M_Vinyl gloss on the walls with a bright horizon band to
reflect, light aerial haze, cut-gem spire with camera-invisible reflection cards, neutral brushed aluminium lit by
narrow strips, a fibrous lilac lint bundle, clustered chalk-lilac dust, crisp chatter notches, low shutter.
"""
import sys, os, math, json, time
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix, Quaternion

ROOT = os.getcwd()
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'scenes', 'set_a'))
import common as C, nd_lib as ND
import design as D
import assets_a as A

T0 = time.time()
RNG = np.random.default_rng(20261109)


def log(*a):
    print('[SETA %6.1fs]' % (time.time() - T0), *a, flush=True)


def safe_set(obj, attr, val):
    try:
        setattr(obj, attr, val)
        return True
    except Exception as ex:
        log('WARN set', type(obj).__name__, attr, '=', val, '->', ex)
        return False


def lin(name):
    return ND.lin(name)


def hexlin(h):
    return C.hex2lin(h)


# =============================================================== scene
sc = C.reset()
sc.name = 'SetA'
C.setup_render(sc, res=(2560, 1440), samples=32)
C.color(sc, 'AgX - Punchy', exposure=0.2)
sc.frame_start, sc.frame_end = D.F0, D.F1
sc.frame_current = 1
sc.render.fps = 24
e = sc.eevee
safe_set(e, 'use_raytracing', True)
safe_set(e, 'ray_tracing_method', 'SCREEN')
rto = getattr(e, 'ray_tracing_options', None)
if rto is not None:
    safe_set(rto, 'resolution_scale', '2')
    safe_set(rto, 'use_denoise', True)
    safe_set(rto, 'denoise_spatial', True)
    safe_set(rto, 'denoise_temporal', True)
    safe_set(rto, 'denoise_bilateral', True)
    safe_set(rto, 'trace_max_roughness', 0.5)
safe_set(e, 'use_fast_gi', True)
safe_set(e, 'fast_gi_resolution', '2')
safe_set(e, 'fast_gi_distance', 60.0)
safe_set(e, 'shadow_ray_count', 1)
safe_set(e, 'shadow_step_count', 6)
safe_set(e, 'shadow_resolution_scale', 0.75)
safe_set(e, 'use_overscan', True)
safe_set(e, 'overscan_size', 0.03)
safe_set(e, 'clamp_surface_indirect', 10.0)
safe_set(e, 'motion_blur_steps', 1)
safe_set(e, 'use_volumetric_shadows', False)
safe_set(e, 'gi_cubemap_resolution', '1024')
safe_set(sc.render, 'filter_size', 1.5)
sc.render.use_motion_blur = True
safe_set(sc.render, 'motion_blur_position', 'CENTER')
# shutter: low on the close flight so the vanishing point stays crisp; a touch more for the climb; low on the whip
for f_, v_ in ((1, 0.22), (96, 0.22), (98, 0.30), (111, 0.30), (114, 0.22), (122, 0.22)):
    sc.render.motion_blur_shutter = v_
    sc.render.keyframe_insert('motion_blur_shutter', frame=f_)
sc.render.image_settings.file_format = 'PNG'
sc.render.image_settings.color_mode = 'RGB'
sc.render.image_settings.color_depth = '16'
safe_set(sc.render.image_settings, 'compression', 15)
sc.render.use_overwrite = False
sc.render.use_placeholder = True
sc.render.filepath = os.path.join(ROOT, 'renders', 'frames', 'f_')
vl = sc.view_layers[0]
vl.use_pass_mist = True
vl.use_pass_z = True
safe_set(vl, 'use_pass_environment', True)

data = D.load_data(ROOT)
envf = D.env_low_fn(data)
data['envf'] = envf
kicks = data['kicks']
log('kicks', len(kicks), 'bands', data['bands'] is not None, 'events', data['events'].get('lint_pass'), data['events'].get('spire_visible'))
log('spire', round(D.X_SP, 1), round(D.Y_SP, 1), 'psi', D.PSI_DEG, 'L', round(D.L_PATH, 1))
cp = D.camera_path(data, frames=np.arange(D.F0, D.F1 + 3))
CAM_PTS = cp['pos']


def new_coll(name, parent=None):
    c = bpy.data.collections.new(name)
    (parent or sc.collection).children.link(c)
    return c


CG = new_coll('A_Groove'); CS = new_coll('A_Stylus'); CL = new_coll('A_Lights'); CD = new_coll('A_Dust')
CLIB = bpy.data.collections.new('A_RockLib')   # not linked to the scene (instanced only)


def mesh_from_np(name, co, quads, coll, uv=None):
    me = bpy.data.meshes.new(name)
    nv = len(co); nf = len(quads)
    me.vertices.add(nv)
    me.vertices.foreach_set('co', np.ascontiguousarray(co, dtype=np.float32).ravel())
    me.loops.add(nf * 4)
    me.loops.foreach_set('vertex_index', np.ascontiguousarray(quads, dtype=np.int32).ravel())
    me.polygons.add(nf)
    me.polygons.foreach_set('loop_start', np.arange(0, nf * 4, 4, dtype=np.int32))
    try:
        me.polygons.foreach_set('loop_total', np.full(nf, 4, dtype=np.int32))
    except Exception:
        pass
    me.update(calc_edges=True)
    if uv is not None:
        uvl = me.uv_layers.new(name='UVMap')
        uvl.data.foreach_set('uv', np.ascontiguousarray(uv[np.asarray(quads).ravel()], dtype=np.float32).ravel())
    me.validate(verbose=False)
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    return ob


def grid_quads(R, Cc):
    r = np.arange(R - 1)[:, None]; c = np.arange(Cc - 1)[None, :]
    a = r * Cc + c
    return np.stack([a, a + 1, a + Cc + 1, a + Cc], -1).reshape(-1, 4)


# =============================================================== chatter notches (data-driven)
def cam_at_t(tk):
    f = 1.0 + tk * D.FPS
    c1 = D.camera_path(data, frames=np.array([f - 0.5, f, f + 0.5]))
    return c1['pos'][1], c1['yaw'][1]


NOTCHES = []
for (tk, st) in kicks:
    if tk < 0 or tk > 4.0:
        continue
    p_, yw = cam_at_t(tk)
    if p_[2] < 0:            # in the trench: notch at the camera (sweeps past the lens on the kick)
        q = p_[:2]
    else:                    # over the lands: notch in the groove the camera is about to cross (bottom of frame)
        q = p_[:2] + 30.0 * np.array([math.cos(math.radians(yw)), math.sin(math.radians(yw))])
    g = int(np.round((q[1] - float(D.B(q[0]))) / D.PITCH))
    NOTCHES.append((g, float(q[0]), float(st)))
log('notches', [(g, round(x, 1)) for g, x, _ in NOTCHES])

# =============================================================== groove mesh
log('groove mesh')
xs = np.concatenate([np.arange(-6000, -1600, 200.0), np.arange(-1600, -160, 10.0), np.arange(-160, -40, 2.0),
                     np.arange(-40, 340, 0.4), np.arange(340, 900, 2.0), np.arange(900, 3200, 8.0), np.arange(3200, 6001, 200.0)])
R = len(xs)
GR = list(range(-6, 15))
s2 = math.sqrt(2.0)
bev_c = (-(abs(D.Z_APEX)) - D.BEVEL_R * math.tan(math.radians(22.5)), -D.BEVEL_R)  # fillet centre
bev = [(bev_c[0] + D.BEVEL_R * math.cos(math.radians(a)), bev_c[1] + D.BEVEL_R * math.sin(math.radians(a))) for a in (90, 75, 60, 45)]
arc_c = (0.0, D.Z_APEX + D.ARC_R * s2)
arc = [(arc_c[0] + D.ARC_R * math.cos(math.radians(a)), arc_c[1] + D.ARC_R * math.sin(math.radians(a))) for a in np.linspace(-135, -90, 5)]
w0 = np.array(bev[-1]); w1 = np.array(arc[0]); wd = (w1 - w0) / np.linalg.norm(w1 - w0)
wall = [tuple(w0 + wd * 0.3), tuple(w1 - wd * 0.3)]
half = bev + wall + arc
prof = half + [(-u, z) for (u, z) in half[-2::-1]]
prof = np.array(prof)
NP = len(prof)
side = np.sign(prof[:, 0]); side[np.abs(prof[:, 0]) < 1e-6] = 0
is_arc = np.zeros(NP, bool); is_arc[6:15] = True
LAND_N = 3
centers = np.stack([D.groove_center(g, xs, envf, True) for g in GR], 0)
# floor depth modulation on the camera groove (+-1 m) from the music (stand-in for L-R)
depth_mod = 1.0 * np.sin(2 * np.pi * (D.t_of_x(xs) * 0.9)) * (envf(D.t_of_x(xs) + 0.4) - 0.4) * D.smoothstep(-20, 20, xs) * (1 - D.smoothstep(150, 220, xs))
cols_y = []; cols_z = []; cols_n = []
OUT_W = 6000.0
zero = np.zeros(R)
for f in [-OUT_W, -OUT_W * 0.6, -OUT_W * 0.3, -150.0, -80.0]:
    cols_y.append(centers[0] + f + prof[0, 0]); cols_z.append(zero); cols_n.append(zero)
for gi, g in enumerate(GR):
    c = centers[gi]
    n = D.notch_offsets(NOTCHES, g, xs)
    nl = np.zeros(R)
    for (gg, xk, st) in NOTCHES:
        if gg == g:
            nl = np.maximum(nl, np.exp(-((xs - xk) / 0.25) ** 2))
    dm = depth_mod if g == 0 else zero
    for j in range(NP):
        u, z = prof[j]
        y = c + u + side[j] * n
        zz = z + (dm if is_arc[j] else 0.0) * (1.0 if 7 <= j <= 13 else 0.5)
        cols_y.append(y); cols_z.append(np.broadcast_to(zz, (R,)).astype(float))
        cols_n.append(nl if 1 <= j <= NP - 2 else zero)
    if gi < len(GR) - 1:
        yr = c + prof[-1, 0]
        yl = centers[gi + 1] + prof[0, 0]
        for k in range(1, LAND_N + 1):
            a = k / (LAND_N + 1)
            cols_y.append(yr * (1 - a) + yl * a); cols_z.append(zero); cols_n.append(zero)
for f in [80.0, 150.0, OUT_W * 0.3, OUT_W * 0.6, OUT_W]:
    cols_y.append(centers[-1] + prof[-1, 0] + f); cols_z.append(zero); cols_n.append(zero)
Y = np.stack(cols_y, 1); Z = np.stack(cols_z, 1); NL = np.stack(cols_n, 1)
Cc = Y.shape[1]
X = np.broadcast_to(xs[:, None], Y.shape)
co = np.stack([X, Y, Z], -1).reshape(-1, 3)
quads = grid_quads(R, Cc)
groove = mesh_from_np('Groove', co, quads, CG)
groove.data.shade_smooth()
att = groove.data.attributes.new('notch', 'FLOAT', 'POINT')
att.data.foreach_set('value', NL.reshape(-1).astype(np.float32))
log('groove verts', len(co), 'faces', len(quads), 'cols', Cc, 'rows', R)


# =============================================================== materials
def node(nt, typ, loc=None, **inputs):
    n = nt.nodes.new(typ)
    for k, v in inputs.items():
        try:
            n.inputs[k].default_value = v
        except Exception as ex:
            log('WARN input', typ, k, ex)
    return n


def fade_group(nt, near, far):
    g = nt.nodes.new('ShaderNodeGroup'); g.node_tree = ND.ng_fade_by_distance()
    g.inputs['near'].default_value = near; g.inputs['far'].default_value = far
    return g.outputs['Fac']


def mat_vinyl_walls():
    """Bible M_Vinyl on the canyon (r2): NG_Marble field (exact S2 stops) with low warp so each wall shows 3-5 bold,
    cleanly shaped bands; a crisp chalk vein at every band boundary (faint emission so it reads in the shadow wall too);
    roughness 0.08-0.15, coat 1.0 / 0.03 (coat fades out with distance so the vanishing point stays a calm glow);
    lathe striations in the coat normal (faded 10-60 m); lands are a calmer, brighter satin with larger swirls."""
    m = bpy.data.materials.new('M_Vinyl_Groove'); m.use_nodes = True
    nt = m.node_tree; N, L = nt.nodes, nt.links
    b = N['Principled BSDF']
    tc = node(nt, 'ShaderNodeTexCoord')
    sep = node(nt, 'ShaderNodeSeparateXYZ'); L.new(tc.outputs['Object'], sep.inputs[0])

    def mathn(op, a, bb=None):
        n = N.new('ShaderNodeMath'); n.operation = op
        if isinstance(a, (int, float)): n.inputs[0].default_value = a
        else: L.new(a, n.inputs[0])
        if bb is not None:
            if isinstance(bb, (int, float)): n.inputs[1].default_value = bb
            else: L.new(bb, n.inputs[1])
        return n.outputs[0]
    # land mask (flat tops)
    gm = node(nt, 'ShaderNodeNewGeometry')
    sn = node(nt, 'ShaderNodeSeparateXYZ'); L.new(gm.outputs['Normal'], sn.inputs[0])
    land = node(nt, 'ShaderNodeMapRange'); land.inputs['From Min'].default_value = 0.93; land.inputs['From Max'].default_value = 0.99
    L.new(sn.outputs['Z'], land.inputs['Value'])
    lnd = land.outputs['Result']
    # band coordinate mostly along height (strata run along the canyon), mild stretch along the groove
    nx = mathn('ADD', sep.outputs['Z'], mathn('MULTIPLY', sep.outputs['Y'], 0.12))
    ny = mathn('MULTIPLY', sep.outputs['X'], 0.3)
    nz = mathn('MULTIPLY', sep.outputs['Y'], 0.3)
    cmb = N.new('ShaderNodeCombineXYZ'); L.new(nx, cmb.inputs[0]); L.new(ny, cmb.inputs[1]); L.new(nz, cmb.inputs[2])
    # lands: half the frequency (calm satin plain with occasional bold swirls)
    vs = N.new('ShaderNodeVectorMath'); vs.operation = 'SCALE'; L.new(cmb.outputs[0], vs.inputs[0])
    L.new(mathn('SUBTRACT', 1.0, mathn('MULTIPLY', lnd, 0.65)), vs.inputs['Scale'])
    fld = ND.build_marble_field(nt, vs.outputs[0], scale=0.05, warp=1.3)
    col = fld['color']
    col.node.color_ramp.interpolation = 'LINEAR'
    # boundary vein: (1-|sin(pi raw)|)^12, plus the stop vein of the ND field
    bv = mathn('POWER', mathn('SUBTRACT', 1.0, mathn('ABSOLUTE', mathn('SINE', mathn('MULTIPLY', fld['raw'], math.pi)))), 12.0)
    vfade = fade_group(nt, 60.0, 260.0)
    vein = mathn('MINIMUM', mathn('ADD', mathn('MULTIPLY', bv, vfade), mathn('MULTIPLY', fld['vein'], 1.2)), 0.92)
    mix = N.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MIX'
    L.new(vein, mix.inputs['Factor']); L.new(col, mix.inputs['A'])
    mix.inputs['B'].default_value = (*lin('chalk'), 1)
    hs = N.new('ShaderNodeHueSaturation'); hs.inputs['Saturation'].default_value = 1.08
    L.new(mathn('ADD', 0.92, mathn('MULTIPLY', lnd, 0.25)), hs.inputs['Value'])
    L.new(mix.outputs['Result'], hs.inputs['Color'])
    L.new(hs.outputs['Color'], b.inputs['Base Color'])
    # vein glow (legible on the shadow wall), faded with distance
    b.inputs['Emission Color'].default_value = (*lin('chalk'), 1)
    L.new(mathn('MULTIPLY', mathn('MULTIPLY', bv, vfade), 0.3), b.inputs['Emission Strength'])
    # coat tinted slightly toward the base (no beige wash)
    ct = N.new('ShaderNodeMix'); ct.data_type = 'RGBA'; ct.inputs['Factor'].default_value = 0.25
    ct.inputs['A'].default_value = (1, 1, 1, 1); L.new(hs.outputs['Color'], ct.inputs['B'])
    L.new(ct.outputs['Result'], b.inputs['Coat Tint'])
    # roughness breakup 0.08-0.15 (walls), ~0.4 (lands); far field rougher (calm vanishing point)
    rn = node(nt, 'ShaderNodeTexNoise', Scale=0.15, Detail=3.0)
    L.new(tc.outputs['Object'], rn.inputs['Vector'])
    rmr = node(nt, 'ShaderNodeMapRange'); rmr.inputs['To Min'].default_value = 0.08; rmr.inputs['To Max'].default_value = 0.15
    L.new(rn.outputs['Fac'], rmr.inputs['Value'])
    far = fade_group(nt, 250.0, 900.0)
    rl = mathn('ADD', mathn('ADD', rmr.outputs['Result'], mathn('MULTIPLY', lnd, 0.30)), mathn('MULTIPLY', mathn('SUBTRACT', 1.0, far), 0.2))
    L.new(rl, b.inputs['Roughness'])
    L.new(mathn('MULTIPLY', mathn('SUBTRACT', 1.0, mathn('MULTIPLY', lnd, 0.6)), mathn('ADD', 0.25, mathn('MULTIPLY', far, 0.75))), b.inputs['Coat Weight'])
    L.new(mathn('ADD', 0.03, mathn('MULTIPLY', lnd, 0.2)), b.inputs['Coat Roughness'])
    b.inputs['Specular IOR Level'].default_value = 0.5
    # lathe striations along the groove, 0.4 m pitch, faded 10-60 m, into BOTH normals so the coat highlight breaks up
    wv = N.new('ShaderNodeTexWave'); wv.wave_type = 'BANDS'; wv.bands_direction = 'Z'
    wv.inputs['Scale'].default_value = 2.5; wv.inputs['Distortion'].default_value = 0.0; wv.inputs['Detail'].default_value = 0.0
    L.new(tc.outputs['Object'], wv.inputs['Vector'])
    hgt = mathn('MULTIPLY', mathn('MULTIPLY', wv.outputs['Fac'], fade_group(nt, 10.0, 60.0)), mathn('SUBTRACT', 1.0, lnd))
    un = node(nt, 'ShaderNodeTexNoise', Scale=0.03, Detail=2.0)
    L.new(tc.outputs['Object'], un.inputs['Vector'])
    h2 = mathn('MULTIPLY', mathn('MULTIPLY', un.outputs['Fac'], fade_group(nt, 40.0, 500.0)), 6.0)
    bmp2 = N.new('ShaderNodeBump'); bmp2.inputs['Strength'].default_value = 0.03; bmp2.inputs['Distance'].default_value = 1.0
    L.new(h2, bmp2.inputs['Height'])
    bmp = N.new('ShaderNodeBump'); bmp.inputs['Strength'].default_value = 0.2; bmp.inputs['Distance'].default_value = 0.05
    L.new(hgt, bmp.inputs['Height']); L.new(bmp2.outputs['Normal'], bmp.inputs['Normal'])
    L.new(bmp.outputs['Normal'], b.inputs['Normal'])
    L.new(bmp.outputs['Normal'], b.inputs['Coat Normal'])
    return m


M_VINYL = mat_vinyl_walls()
groove.data.materials.append(M_VINYL)


def mat_lint():
    m = ND.simple('M_Lint', rgb=hexlin('#E2D4F0'), rough=0.62, sheen=1.0)
    b = m.node_tree.nodes['Principled BSDF']
    nt = m.node_tree
    b.inputs['Sheen Roughness'].default_value = 0.3
    b.inputs['Sheen Tint'].default_value = (*hexlin('#FF9AD2'), 1)
    b.inputs['Subsurface Weight'].default_value = 0.3
    b.inputs['Subsurface Radius'].default_value = (1.0, 0.35, 0.8)
    b.inputs['Subsurface Scale'].default_value = 0.15
    # per-strand tone variation (chalk -> lilac) from the random per-object/curve attribute
    nz = node(nt, 'ShaderNodeTexNoise', Scale=0.5, Detail=2.0)
    rp = nt.nodes.new('ShaderNodeValToRGB')
    rp.color_ramp.elements[0].color = (*hexlin('#A88FD6'), 1); rp.color_ramp.elements[1].color = (*hexlin('#E9E0F0'), 1)
    nt.links.new(nz.outputs['Fac'], rp.inputs['Fac']); nt.links.new(rp.outputs['Color'], b.inputs['Base Color'])
    nz2 = node(nt, 'ShaderNodeTexNoise', Scale=6.0, Detail=4.0)
    bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.25
    nt.links.new(nz2.outputs['Fac'], bp.inputs['Height']); nt.links.new(bp.outputs['Normal'], b.inputs['Normal'])
    b.inputs['Sheen Weight'].default_value = 1.0
    tr = nt.nodes.new('ShaderNodeBsdfTranslucent'); tr.inputs['Color'].default_value = (*hexlin('#FFB8DC'), 1)
    ms = nt.nodes.new('ShaderNodeMixShader'); ms.inputs['Fac'].default_value = 0.38
    out_ = nt.nodes['Material Output']
    nt.links.new(b.outputs[0], ms.inputs[1]); nt.links.new(tr.outputs[0], ms.inputs[2]); nt.links.new(ms.outputs[0], out_.inputs['Surface'])
    return m


def mat_dust(maps):
    m = bpy.data.materials.new('M_VinylDust'); m.use_nodes = True
    nt = m.node_tree; N, L = nt.nodes, nt.links
    b = N['Principled BSDF']
    uv = N.new('ShaderNodeTexCoord')
    base = (*hexlin('#E6DDF0'), 1)
    if maps.get('diff'):
        ti = N.new('ShaderNodeTexImage'); ti.image = maps['diff']; L.new(uv.outputs['UV'], ti.inputs['Vector'])
        bw = N.new('ShaderNodeRGBToBW'); L.new(ti.outputs['Color'], bw.inputs[0])
        mr = node(nt, 'ShaderNodeMapRange'); mr.inputs['From Min'].default_value = 0.05; mr.inputs['From Max'].default_value = 0.3
        mr.inputs['To Min'].default_value = 0.35; mr.inputs['To Max'].default_value = 1.0
        L.new(bw.outputs[0], mr.inputs['Value'])
        mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MIX'
        L.new(mr.outputs['Result'], mx.inputs['Factor'])
        mx.inputs['A'].default_value = (*hexlin('#6A4FB8'), 1); mx.inputs['B'].default_value = (*hexlin('#EFE6FA'), 1)
        L.new(mx.outputs['Result'], b.inputs['Base Color'])
    else:
        b.inputs['Base Color'].default_value = base
    if maps.get('nor'):
        tn = N.new('ShaderNodeTexImage'); tn.image = maps['nor']; tn.image.colorspace_settings.name = 'Non-Color'
        L.new(uv.outputs['UV'], tn.inputs['Vector'])
        nm = N.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = 1.2
        L.new(tn.outputs['Color'], nm.inputs['Color']); L.new(nm.outputs['Normal'], b.inputs['Normal'])
    if maps.get('rough'):
        tr = N.new('ShaderNodeTexImage'); tr.image = maps['rough']; tr.image.colorspace_settings.name = 'Non-Color'
        L.new(uv.outputs['UV'], tr.inputs['Vector'])
        rr = node(nt, 'ShaderNodeMapRange'); rr.inputs['To Min'].default_value = 0.55; rr.inputs['To Max'].default_value = 0.95
        L.new(tr.outputs['Color'], rr.inputs['Value']); L.new(rr.outputs['Result'], b.inputs['Roughness'])
    else:
        b.inputs['Roughness'].default_value = 0.8
    b.inputs['Sheen Weight'].default_value = 0.5
    b.inputs['Sheen Tint'].default_value = (*hexlin('#FFD9F0'), 1)
    return m


def mat_alu():
    """Neutral brushed aluminium #C9CBD3, axial anisotropy, legible brushing (stretched-noise roughness 0.12-0.35)."""
    m = bpy.data.materials.new('M_BrushedAlu'); m.use_nodes = True
    nt = m.node_tree; N, L = nt.nodes, nt.links
    b = N['Principled BSDF']
    b.inputs['Base Color'].default_value = (*lin('alu'), 1)
    b.inputs['Metallic'].default_value = 1.0
    b.inputs['Anisotropic'].default_value = 0.8
    tg = N.new('ShaderNodeTangent'); tg.direction_type = 'UV_MAP'; tg.uv_map = 'UVMap'
    L.new(tg.outputs['Tangent'], b.inputs['Tangent'])
    tc = N.new('ShaderNodeTexCoord')
    mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1.0, 260.0, 1.0)
    L.new(tc.outputs['UV'], mp.inputs['Vector'])
    nz = node(nt, 'ShaderNodeTexNoise', Scale=5.0, Detail=5.0)
    L.new(mp.outputs['Vector'], nz.inputs['Vector'])
    rr = node(nt, 'ShaderNodeMapRange'); rr.inputs['From Min'].default_value = 0.3; rr.inputs['From Max'].default_value = 0.7
    rr.inputs['To Min'].default_value = 0.12; rr.inputs['To Max'].default_value = 0.35
    L.new(nz.outputs['Fac'], rr.inputs['Value']); L.new(rr.outputs['Result'], b.inputs['Roughness'])
    hm = N.new('ShaderNodeMath'); hm.operation = 'MULTIPLY'
    L.new(nz.outputs['Fac'], hm.inputs[0]); L.new(fade_group(nt, 20.0, 60.0), hm.inputs[1])
    bp = N.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.15; bp.inputs['Distance'].default_value = 0.01
    L.new(hm.outputs[0], bp.inputs['Height']); L.new(bp.outputs['Normal'], b.inputs['Normal'])
    return m


def mat_alu_end(p0_, ax_):
    """fix3: lathe-turned cantilever end. Brushed aluminium, circumferential tangent about the tube axis, concentric
    turning marks in roughness / bump / a touch of value (faded with camera distance so the far approach shots do not
    shimmer). Replaces the glossy black epoxy end disc that read as a 'disco ball / helmet' in f104-110."""
    m = bpy.data.materials.new('M_AluEnd'); m.use_nodes = True
    nt = m.node_tree; N, L = nt.nodes, nt.links
    b = N['Principled BSDF']
    b.inputs['Metallic'].default_value = 1.0
    b.inputs['Anisotropic'].default_value = 0.6

    def mth(op, a, c=None):
        n = N.new('ShaderNodeMath'); n.operation = op
        for i_, v_ in enumerate((a, c)):
            if v_ is None: continue
            if isinstance(v_, (int, float)): n.inputs[i_].default_value = v_
            else: L.new(v_, n.inputs[i_])
        return n.outputs[0]
    geo = N.new('ShaderNodeNewGeometry')
    rel = N.new('ShaderNodeVectorMath'); rel.operation = 'SUBTRACT'
    L.new(geo.outputs['Position'], rel.inputs[0]); rel.inputs[1].default_value = tuple(float(c) for c in p0_)
    crs = N.new('ShaderNodeVectorMath'); crs.operation = 'CROSS_PRODUCT'
    crs.inputs[0].default_value = tuple(float(c) for c in ax_); L.new(rel.outputs[0], crs.inputs[1])
    tnn = N.new('ShaderNodeVectorMath'); tnn.operation = 'NORMALIZE'; L.new(crs.outputs[0], tnn.inputs[0])
    L.new(tnn.outputs[0], b.inputs['Tangent'])
    rad = N.new('ShaderNodeVectorMath'); rad.operation = 'LENGTH'; L.new(crs.outputs[0], rad.inputs[0])
    r_ = rad.outputs['Value']
    fine = mth('SINE', mth('MULTIPLY', r_, 2 * math.pi / 0.32))
    broad = mth('SINE', mth('MULTIPLY', r_, 2 * math.pi / 2.7))
    fd = fade_group(nt, 25.0, 90.0)
    rough = mth('ADD', mth('MULTIPLY', mth('ADD', mth('MULTIPLY', fine, 0.05), mth('MULTIPLY', broad, 0.015)), fd), 0.22)
    L.new(rough, b.inputs['Roughness'])
    val = N.new('ShaderNodeMix'); val.data_type = 'RGBA'
    L.new(mth('ADD', mth('MULTIPLY', broad, 0.5), 0.5), val.inputs['Factor'])
    val.inputs['A'].default_value = (*[c * 0.95 for c in lin('alu')], 1); val.inputs['B'].default_value = (*lin('alu'), 1)
    L.new(val.outputs['Result'], b.inputs['Base Color'])
    bp = N.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.3; bp.inputs['Distance'].default_value = 0.01
    L.new(mth('MULTIPLY', fine, fd), bp.inputs['Height']); L.new(bp.outputs['Normal'], b.inputs['Normal'])
    return m


M_LINT = mat_lint(); M_ALU = mat_alu()
M_EPOXY = ND.simple('M_Epoxy', 'diamond', rough=0.08, coat=1.0, coat_rough=0.02)
M_DIAMOND = ND.black_diamond('M_BlackDiamond')
for n_ in M_DIAMOND.node_tree.nodes:
    if n_.type == 'VALTORGB':
        n_.color_ramp.elements[0].color = (*hexlin('#2236FF'), 1)
        n_.color_ramp.elements[1].color = (*hexlin('#FFB30F'), 1)
        _e = n_.color_ramp.elements.new(0.5); _e.color = (*hexlin('#FF1F8E'), 1)
_bd = M_DIAMOND.node_tree.nodes['Principled BSDF']
_bd.inputs['Coat Weight'].default_value = 0.6; _bd.inputs['Coat Roughness'].default_value = 0.01
_bd.inputs['Specular IOR Level'].default_value = 1.0
_tc = M_DIAMOND.node_tree.nodes.new('ShaderNodeTexCoord')
_nz = M_DIAMOND.node_tree.nodes.new('ShaderNodeTexNoise'); _nz.inputs['Scale'].default_value = 0.06; _nz.inputs['Detail'].default_value = 4.0
M_DIAMOND.node_tree.links.new(_tc.outputs['Object'], _nz.inputs['Vector'])
_mr = M_DIAMOND.node_tree.nodes.new('ShaderNodeMapRange'); _mr.inputs['To Min'].default_value = 0.01; _mr.inputs['To Max'].default_value = 0.05
M_DIAMOND.node_tree.links.new(_nz.outputs['Fac'], _mr.inputs['Value']); M_DIAMOND.node_tree.links.new(_mr.outputs['Result'], _bd.inputs['Roughness'])


def add_height_fog(mat, strength=0.65, h=45.0, near=80.0, far=1000.0, col='#B98CF2', bright=0.9):
    """Low ground mist baked into the surface: mix toward a lilac haze by distance x exp(-z/h), so the base of a
    tall object is hazier than its top (aerial perspective that reads kilometres)."""
    nt_ = mat.node_tree; Nn, Ln = nt_.nodes, nt_.links
    out_ = [n_ for n_ in Nn if n_.type == 'OUTPUT_MATERIAL'][0]
    src = out_.inputs['Surface'].links[0].from_socket
    gm_ = Nn.new('ShaderNodeNewGeometry'); sz_ = Nn.new('ShaderNodeSeparateXYZ'); Ln.new(gm_.outputs['Position'], sz_.inputs[0])
    ex_ = Nn.new('ShaderNodeMath'); ex_.operation = 'MULTIPLY'; Ln.new(sz_.outputs['Z'], ex_.inputs[0]); ex_.inputs[1].default_value = -1.0 / h
    ex2 = Nn.new('ShaderNodeMath'); ex2.operation = 'EXPONENT'; Ln.new(ex_.outputs[0], ex2.inputs[0])
    ex3 = Nn.new('ShaderNodeMath'); ex3.operation = 'MINIMUM'; Ln.new(ex2.outputs[0], ex3.inputs[0]); ex3.inputs[1].default_value = 1.0
    cam_ = Nn.new('ShaderNodeCameraData')
    mr_ = Nn.new('ShaderNodeMapRange'); mr_.inputs['From Min'].default_value = near; mr_.inputs['From Max'].default_value = far
    Ln.new(cam_.outputs['View Distance'], mr_.inputs['Value'])
    f1 = Nn.new('ShaderNodeMath'); f1.operation = 'MULTIPLY'; Ln.new(mr_.outputs['Result'], f1.inputs[0]); Ln.new(ex3.outputs[0], f1.inputs[1])
    f2 = Nn.new('ShaderNodeMath'); f2.operation = 'MULTIPLY'; Ln.new(f1.outputs[0], f2.inputs[0]); f2.inputs[1].default_value = strength
    em_ = Nn.new('ShaderNodeEmission'); em_.inputs['Color'].default_value = (*hexlin(col), 1); em_.inputs['Strength'].default_value = bright
    ms_ = Nn.new('ShaderNodeMixShader'); Ln.new(f2.outputs[0], ms_.inputs['Fac'])
    Ln.new(src, ms_.inputs[1]); Ln.new(em_.outputs[0], ms_.inputs[2]); Ln.new(ms_.outputs[0], out_.inputs['Surface'])


add_height_fog(M_DIAMOND)

# =============================================================== lint fibre bundle
log('lint')
f_lint = data['events'].get('lint_pass', 49)
i_l = f_lint - D.F0
x_l = float(cp['pos'][i_l, 0])
psi = math.atan(float(D.Bslope(x_l)))
nrm = np.array([-math.sin(psi), math.cos(psi)])
c0 = np.array([x_l, float(D.groove_center(0, x_l, envf, True))])
us = np.arange(-240.0, 240.0, 0.5)
P2 = c0[None, :] + us[:, None] * nrm[None, :]


def surf(xq, yq):
    best = np.full(np.shape(xq), 0.0)
    for gi, g in enumerate(GR):
        cg = np.interp(xq, xs, centers[gi])
        best = np.minimum(best, D.profile_z(yq - cg))
    return best


RB = 2.2
offs = [(dx, dy) for dx in np.linspace(-RB, RB, 9) for dy in np.linspace(-RB, RB, 9) if dx * dx + dy * dy <= RB * RB]
zreq = np.full(len(us), -1e9)
for dx, dy in offs:
    zz = surf(P2[:, 0] + dx, P2[:, 1] + dy) + math.sqrt(max(0.0, RB * RB - dx * dx - dy * dy))
    zreq = np.maximum(zreq, zz)
sag = np.full(len(us), 30.0)
for gi, g in enumerate(GR):
    dd = us - (100.0 * g) * math.cos(psi)
    depth = -3.8 if g == 0 else (-8.0 - 3.0 * ((g * 7) % 3))
    sag = np.minimum(sag, depth + 0.0075 * dd ** 2)
sag = np.minimum(sag, 2.2)
zl = np.maximum(zreq, sag)
for it in range(4):
    k = np.exp(-0.5 * (np.arange(-24, 25) / 6.0) ** 2); k /= k.sum()
    zl = np.convolve(np.pad(zl, 24, mode='edge'), k, mode='valid')
    zl = np.maximum(zl, zreq)
P = np.stack([P2[:, 0], P2[:, 1], zl], -1)
T = np.gradient(P, axis=0); T /= np.linalg.norm(T, axis=1)[:, None]
Nf = np.zeros_like(T); ref = np.array([0, 0, 1.0])
n0 = ref - T[0] * (T[0] @ ref); Nf[0] = n0 / np.linalg.norm(n0)
for i in range(1, len(T)):
    v = Nf[i - 1] - T[i] * (T[i] @ Nf[i - 1]); Nf[i] = v / np.linalg.norm(v)
Bf = np.cross(T, Nf)
arc_len = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
NSTR = 8
cu = bpy.data.curves.new('LintCurve', 'CURVE'); cu.dimensions = '3D'
cu.bevel_depth = 1.0; cu.bevel_resolution = 1; cu.resolution_u = 1
cu.use_fill_caps = True
cuf = bpy.data.curves.new('LintFine', 'CURVE'); cuf.dimensions = '3D'
cuf.bevel_depth = 1.0; cuf.bevel_resolution = 0; cuf.resolution_u = 1
NFINE = 260
for s_ in range(NSTR + NFINE):
    core = s_ < NSTR
    r0 = math.sqrt(RNG.uniform(0.0, 1.0)) * ((RB - 1.2) if core else (RB - 0.15))
    a0 = RNG.uniform(0, 2 * np.pi)
    step = 1 if core else 2
    Pq = P[::step]; Nq = Nf[::step]; Bq = Bf[::step]; al = arc_len[::step]
    tw = a0 + 2 * np.pi * 2.0 * al / 100.0
    wob = 0.18 * np.sin(al / RNG.uniform(6, 14) + s_) + 0.10 * np.sin(al / RNG.uniform(1.5, 3.0) + 2 * s_)
    rr = np.clip(r0 + wob, 0, RB)
    pts = Pq + (np.cos(tw) * rr)[:, None] * Nq + (np.sin(tw) * rr)[:, None] * Bq
    sp = (cu if core else cuf).splines.new('POLY'); sp.points.add(len(pts) - 1)
    sp.points.foreach_set('co', np.concatenate([pts, np.ones((len(pts), 1))], 1).astype(np.float32).ravel())
    w0 = RNG.uniform(0.16, 0.26) if core else RNG.uniform(0.025, 0.07)
    rad = w0 * (0.8 + 0.2 * np.sin(al / 3.0 + s_))
    sp.points.foreach_set('radius', rad.astype(np.float32))
    sp.use_smooth = True
# flyaway fibres: thousands of short curly hairs, dense near the camera crossing, sparse far away
cu2 = bpy.data.curves.new('LintFibrils', 'CURVE'); cu2.dimensions = '3D'
cu2.bevel_depth = 1.0; cu2.bevel_resolution = 0; cu2.resolution_u = 2
nfly = 0
for k in range(2600):
    ui = RNG.normal(0, 70.0)
    if abs(ui) > 235: continue
    i0 = int(np.clip(np.searchsorted(us, ui), 2, len(P) - 3))
    a0 = RNG.uniform(0, 2 * np.pi)
    rad0 = RB * RNG.uniform(0.7, 1.0)
    dirv = math.cos(a0) * Nf[i0] + math.sin(a0) * Bf[i0]
    base = P[i0] + rad0 * dirv
    d = dirv * 0.8 + T[i0] * RNG.uniform(-0.8, 0.8); d[2] -= 0.25; d /= np.linalg.norm(d)
    L0 = RNG.uniform(0.8, 3.2); nseg = 7
    pts = [base]
    for j in range(nseg):
        d = d + RNG.normal(0, 0.45, 3); d[2] -= 0.08; d /= np.linalg.norm(d)
        pts.append(pts[-1] + d * L0 / nseg)
    pts = np.array(pts)
    sp = cu2.splines.new('NURBS'); sp.points.add(len(pts) - 1)
    sp.points.foreach_set('co', np.concatenate([pts, np.ones((len(pts), 1))], 1).astype(np.float32).ravel())
    sp.points.foreach_set('radius', np.linspace(1.0, 0.4, len(pts)).astype(np.float32) * RNG.uniform(0.035, 0.065))
    sp.use_endpoint_u = True; sp.order_u = 3
    nfly += 1
lint = bpy.data.objects.new('Lint', cu); CG.objects.link(lint); cu.materials.append(M_LINT)
lintf = bpy.data.objects.new('LintFine', cuf); CG.objects.link(lintf); cuf.materials.append(M_LINT)
fib = bpy.data.objects.new('LintFibrils', cu2); CG.objects.link(fib); cu2.materials.append(M_LINT)
log('lint at x', round(x_l, 1), 'min z', round(zl.min(), 1), 'strands', NSTR, 'flyaways', nfly)

# =============================================================== rocks (vinyl dust)
log('rocks')
rock_meshes = []; hero_meshes = []
dust_maps = {}
for i in range(1, 8):
    slug = f'moon_rock_0{i}'
    try:
        pth = A.rock_blend(slug)
    except Exception as ex:
        log('WARN rock fetch failed', slug, ex); continue
    with bpy.data.libraries.load(pth, link=False) as (src, dst):
        dst.objects = [o for o in src.objects]
    objs = [o for o in dst.objects if o is not None and o.type == 'MESH']
    objs.sort(key=lambda o: o.name)
    tri = {o.name: sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs}
    pick = None
    for o in sorted(objs, key=lambda o: -tri[o.name]):
        if tri[o.name] <= 2600:
            pick = o; break
    if pick is None:
        pick = min(objs, key=lambda o: tri[o.name])
    hero = max(objs, key=lambda o: tri[o.name])
    for o, lst, lim in ((pick, rock_meshes, None), (hero, hero_meshes, 20000)):
        me = o.data.copy(); me.name = f'{slug}_{"hero" if lim else "lod"}'
        v = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get('co', v); v = v.reshape(-1, 3)
        v = v @ np.array(o.matrix_world.to_3x3()).T
        cmin, cmax = v.min(0), v.max(0)
        ctr = (cmin + cmax) / 2; ctr[2] = cmin[2] + (cmax[2] - cmin[2]) * 0.18
        v = (v - ctr) / max(1e-6, float((cmax - cmin).max()))
        me.vertices.foreach_set('co', v.ravel())
        me.update()
        if lim and tri[o.name] > lim:
            tmp = bpy.data.objects.new('tmp_dec', me); sc.collection.objects.link(tmp)
            dm = tmp.modifiers.new('dec', 'DECIMATE'); dm.ratio = lim / tri[o.name]
            dg = bpy.context.evaluated_depsgraph_get()
            me2 = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg)); me2.name = me.name
            bpy.data.objects.remove(tmp); me = me2
        me.materials.clear()
        lst.append(me)
    if not dust_maps:
        for im in bpy.data.images:
            n = im.name.lower()
            if slug in n:
                if 'nor_gl' in n: dust_maps['nor'] = im
                elif 'rough' in n: dust_maps['rough'] = im
                elif 'diff' in n: dust_maps['diff'] = im
    for o in objs:
        if o.users == 0 or o.name not in sc.objects:
            try: bpy.data.objects.remove(o)
            except Exception: pass
M_DUST = mat_dust(dust_maps)
add_height_fog(M_DUST, strength=0.5)
for me in rock_meshes + hero_meshes:
    me.materials.append(M_DUST)
    for p in me.polygons: p.use_smooth = True
log('rock lods', len(rock_meshes), 'heroes', len(hero_meshes), 'maps', list(dust_maps))

lib_objs = []
for i, me in enumerate(rock_meshes):
    o = bpy.data.objects.new(f'RockLib_{i}', me); CLIB.objects.link(o); lib_objs.append(o)
# clustered scatter on the lands (numpy, deterministic): groups of rocks with bare gaps, culled by projected size
ph = RNG.uniform(0, 2 * np.pi, 8)


def cluster_mask(x, y):
    m = (np.sin(x / 41.0 + ph[0]) * np.sin(y / 29.0 + ph[1]) + 0.6 * np.sin(x / 17.0 + y / 23.0 + ph[2])
         + 0.4 * np.sin(x / 9.0 - y / 11.0 + ph[3]))
    return 0.5 + 0.5 * m / 2.0


land_lo = 30.83 + 2.0; land_hi = 69.17 - 2.0
cand = []
xq = np.arange(-500, 1600, 3.0)
for gi in range(len(GR) - 1):
    for xx in xq:
        x0 = xx + RNG.uniform(0, 3.0, 2)
        cg = np.interp(x0, xs, centers[gi]); cg1 = np.interp(x0, xs, centers[gi + 1])
        y0 = RNG.uniform(cg + land_lo, cg1 - land_lo)
        for a_, b_, l_, h_ in zip(x0, y0, cg + land_lo, cg1 - land_lo):
            cand.append((a_, b_, min(b_ - l_, h_ - b_)))
cand = np.array(cand)
# extra big-rock candidates flanking the over-land approach (f58-96)
extra = []
for f_ in range(58, 97):
    p_ = CAM_PTS[f_ - 1]
    for k_ in range(10):
        q_ = p_[:2] + RNG.normal(0, 90.0, 2)
        g_ = int(np.round((q_[1] - float(D.B(q_[0]))) / D.PITCH))
        u_ = q_[1] - float(D.groove_center(g_, q_[0]))
        if abs(u_) < land_lo + 4: continue
        extra.append((q_[0], q_[1], abs(u_) - 30.83))
extra = np.array(extra) if extra else np.zeros((0, 3))
n_extra0 = len(cand)
cand = np.vstack([cand, extra])
msk = cluster_mask(cand[:, 0], cand[:, 1])
keep_p = D.smoothstep(0.55, 0.78, msk) * 0.85 + 0.02
keep_p[n_extra0:] = 0.55
keep = RNG.uniform(size=len(cand)) < keep_p
isx = np.zeros(len(cand), bool); isx[n_extra0:] = True; isx = isx[keep]
cand = cand[keep]
n_c = len(cand)
sz = 0.5 + 3.5 * RNG.pareto(2.2, n_c)
sz = np.clip(sz, 0.5, 10.0)
giants = RNG.uniform(size=n_c) < 0.006
sz[giants] = RNG.uniform(12.0, 16.0, giants.sum())
sz[isx] = RNG.uniform(6.0, 20.0, isx.sum())
sz = np.minimum(sz, cand[:, 2] * 1.4 + 1.0)
pts3 = np.stack([cand[:, 0], cand[:, 1], -0.12 * sz], -1)
# distance to the camera path (all frames) -> projected size cull + keep clear of the lens
dmin = np.full(n_c, 1e9)
for p_ in CAM_PTS[::2]:
    dmin = np.minimum(dmin, np.linalg.norm(pts3 - p_[None, :], axis=1))
sp_xy = np.array([D.X_SP, D.Y_SP])
dsp = np.linalg.norm(pts3[:, :2] - sp_xy[None, :], axis=1)
ok = (sz / dmin > 0.003) & (dmin > 18.0 + sz) & (dsp > D.ARRIS_R + 12 + sz)
pts3 = pts3[ok]; sz = sz[ok]
n_c = len(sz)
rot = np.stack([RNG.uniform(-0.3, 0.3, n_c), RNG.uniform(-0.3, 0.3, n_c), RNG.uniform(0, 2 * np.pi, n_c)], -1)
idx = RNG.integers(0, len(lib_objs), n_c).astype(np.int32)
log('dust points', n_c, 'from', len(keep), 'cand')
pme = bpy.data.meshes.new('DustPoints'); pme.vertices.add(n_c); pme.vertices.foreach_set('co', pts3.astype(np.float32).ravel())
a_s = pme.attributes.new('dscale', 'FLOAT', 'POINT'); a_s.data.foreach_set('value', sz.astype(np.float32))
a_r = pme.attributes.new('drot', 'FLOAT_VECTOR', 'POINT'); a_r.data.foreach_set('vector', rot.astype(np.float32).ravel())
a_i = pme.attributes.new('didx', 'INT', 'POINT'); a_i.data.foreach_set('value', idx)
pme.update()
dust = bpy.data.objects.new('VinylDust', pme); CD.objects.link(dust)
ng = bpy.data.node_groups.new('GN_DustScatter', 'GeometryNodeTree')
ng.interface.new_socket('Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
ng.interface.new_socket('Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
GN, GL = ng.nodes, ng.links
gi_ = GN.new('NodeGroupInput'); go_ = GN.new('NodeGroupOutput')
ci = GN.new('GeometryNodeCollectionInfo'); ci.inputs['Collection'].default_value = CLIB
ci.inputs['Separate Children'].default_value = True; ci.inputs['Reset Children'].default_value = True
ci.transform_space = 'ORIGINAL'
iop = GN.new('GeometryNodeInstanceOnPoints')
iop.inputs['Pick Instance'].default_value = True
na_s = GN.new('GeometryNodeInputNamedAttribute'); na_s.data_type = 'FLOAT'; na_s.inputs['Name'].default_value = 'dscale'
na_r = GN.new('GeometryNodeInputNamedAttribute'); na_r.data_type = 'FLOAT_VECTOR'; na_r.inputs['Name'].default_value = 'drot'
na_i = GN.new('GeometryNodeInputNamedAttribute'); na_i.data_type = 'INT'; na_i.inputs['Name'].default_value = 'didx'
GL.new(gi_.outputs[0], iop.inputs['Points']); GL.new(ci.outputs[0], iop.inputs['Instance'])
GL.new(na_i.outputs['Attribute'], iop.inputs['Instance Index'])
GL.new(na_r.outputs['Attribute'], iop.inputs['Rotation']); GL.new(na_s.outputs['Attribute'], iop.inputs['Scale'])
GL.new(iop.outputs[0], go_.inputs[0])
mod = dust.modifiers.new('Scatter', 'NODES'); mod.node_group = ng

# hero boulders: on the lands flanking the approach (f63-96), 30-60 m off the ground track, with contact shadows
hero_t = [2.75, 2.95, 3.15, 3.35, 3.55, 3.72]
for k, tk in enumerate(hero_t):
    me = hero_meshes[k % len(hero_meshes)] if hero_meshes else None
    if me is None: break
    p_, yw = cam_at_t(tk)
    side_ = 1 if k % 2 == 0 else -1
    yr_ = math.radians(yw)
    fwd2 = np.array([math.cos(yr_), math.sin(yr_)]); lft = np.array([-fwd2[1], fwd2[0]])
    q = p_[:2] + fwd2 * RNG.uniform(60, 110) + lft * side_ * RNG.uniform(32, 55)
    gq = int(np.round((q[1] - float(D.B(q[0]))) / D.PITCH))
    yc = float(D.groove_center(gq, q[0])); half_l = 100.0 / 2
    # snap onto the land strip centre band
    landc = yc + (half_l if q[1] > yc else -half_l)
    q[1] = landc + np.clip(q[1] - landc, -12, 12)
    if np.linalg.norm(q - sp_xy) < D.ARRIS_R + 30: continue
    hs = RNG.uniform(10.0, 18.0)
    o = bpy.data.objects.new(f'HeroDust_{k}', me); CD.objects.link(o)
    o.location = (q[0], q[1], -0.15 * hs); o.scale = (hs, hs, hs * 0.85)
    o.rotation_euler = (0.2 * k, -0.15 * k, 1.3 * k)

pile = [(-30.0, 62.0, 30.0), (-8.0, -66.0, 34.0), (30.0, 70.0, 24.0), (52.0, -50.0, 28.0), (-45.0, -95.0, 18.0),
        (-55.0, 92.0, 16.0), (75.0, 30.0, 22.0), (10.0, 105.0, 15.0), (-20.0, -125.0, 14.0)]
for k, (sl_, ll_, hs) in enumerate(pile):
    if not hero_meshes: break
    xw, yw_, _ = D.local_to_world(sl_, ll_, 0.0)
    zg = float(D.surface_z(np.array([float(xw)]), np.array([float(yw_)]))[0])
    o = bpy.data.objects.new(f'SpirePile_{k}', hero_meshes[(k + 2) % len(hero_meshes)]); CD.objects.link(o)
    o.location = (float(xw), float(yw_), zg - 0.15 * hs); o.scale = (hs, hs, hs * 0.8)
    o.rotation_euler = (0.25 * k, -0.2 * k, 0.9 * k + 0.4)

# =============================================================== stylus spire (cut black diamond)
log('spire')
# r2: 16-sided brilliant: every band an antiprism (alternate half-step), 4 deg twist per band, extra shank rings,
# crown = upper girdle + star facets + table. No emissive edges: the bevel carries the diamond material.
NS = 16; STEP = 360.0 / NS
th0 = math.radians(D.PSI_DEG + 180.0)          # an arris points straight back at the approaching camera
rings = [(-24.0, 1.8), (-21.0, 7.0), (-15.0, 15.2), (-8.0, 21.6), (0.0, 29.2), (5.0, 33.4), (10.0, 35.0)]
for zz_ in np.linspace(17.0, 90.0, 10):
    rings.append((float(zz_), float(35.0 - 13.0 * ((zz_ - 10.0) / 80.0) ** 1.2)))
rings += [(95.0, 20.6), (99.5, 18.6), (103.5, 16.6), (107.0, 14.6), (D.SPIRE_TOP, 13.0)]
bm = bmesh.new()
vr = []
for i_r, (z, r) in enumerate(rings):
    ring = []
    rot_ = i_r % 2
    tw = math.radians(4.0 * i_r)
    for k in range(NS):
        a = th0 + tw + math.radians(STEP * k + 0.5 * STEP * rot_)
        rv = r / math.cos(math.radians(STEP / 2))
        ring.append(bm.verts.new((rv * math.cos(a), rv * math.sin(a), z)))
    vr.append(ring)
for i in range(len(vr) - 1):
    A_, B_ = vr[i], vr[i + 1]
    if (i % 2) == 0:   # B is rotated +half step (and twisted) relative to A: antiprism band
        for k in range(NS):
            bm.faces.new((A_[k], A_[(k + 1) % NS], B_[k]))
            bm.faces.new((B_[k], A_[(k + 1) % NS], B_[(k + 1) % NS]))
    else:              # A rotated +half step relative to B
        for k in range(NS):
            bm.faces.new((A_[k], B_[(k + 1) % NS], B_[k]))
            bm.faces.new((A_[k], A_[(k + 1) % NS], B_[(k + 1) % NS]))
bm.faces.new(vr[-1])
tipv = bm.verts.new((0, 0, -25.5))
for k in range(NS):
    bm.faces.new((vr[0][(k + 1) % NS], vr[0][k], tipv))
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
sme = bpy.data.meshes.new('Spire'); bm.to_mesh(sme); bm.free()
spire = bpy.data.objects.new('StylusSpire', sme); CS.objects.link(spire)
spire.location = (D.X_SP, D.Y_SP, 0)
bv = spire.modifiers.new('Bevel', 'BEVEL'); bv.width = 0.35; bv.segments = 2
bv.limit_method = 'ANGLE'; bv.angle_limit = math.radians(6); bv.harden_normals = True
sme.materials.append(M_DIAMOND)
for p in sme.polygons: p.use_smooth = False
log('spire faces', len(sme.polygons))

# =============================================================== cantilever tube (brushed aluminium) + epoxy sleeve
log('cantilever')
A2 = D.A_DIR; T2 = D.T_DIR
ax = np.array([T2[0] * math.cos(D.TUBE_ANG), T2[1] * math.cos(D.TUBE_ANG), math.sin(D.TUBE_ANG)])
TUBE_Z0 = D.SPIRE_TOP + D.TUBE_R / math.cos(D.TUBE_ANG) - 2.5 + D.TUBE_S0 * math.tan(D.TUBE_ANG)
p0 = np.array([D.X_SP + D.TUBE_S0 * T2[0], D.Y_SP + D.TUBE_S0 * T2[1], TUBE_Z0])
seg = 160
# fix3: machined end profile (s along the axis, r radius), from the centre outward: shallow counterbore floor (s=0.8,
# r<10) -> step wall -> faced annulus (s=0) -> 45 deg chamfer (2.4 m) -> barrel. Every corner gets a tight radius
# (two rings ~0.1 m apart) plus a flat guard ring, so smooth shading gives crisp highlight lines and flat faces.
R_T = D.TUBE_R; CH_T = 2.4; RC_T = 10.0; SB_T = 0.8
END_PROF = [(SB_T, RC_T - 0.4), (SB_T, RC_T - 0.1), (SB_T - 0.1, RC_T), (0.1, RC_T), (0.0, RC_T + 0.1), (0.0, RC_T + 0.35),
            (0.0, R_T - CH_T - 0.35), (0.0, R_T - CH_T - 0.1), (0.07, R_T - CH_T + 0.07), (0.25, R_T - CH_T + 0.25),
            (CH_T - 0.25, R_T - 0.25), (CH_T - 0.07, R_T - 0.07), (CH_T + 0.1, R_T), (CH_T + 0.35, R_T)]
N_END = len(END_PROF) - 2          # quad rings 0..N_END-1 (up to the barrel-side chamfer radius) use the turned-end material
prof_t = END_PROF + [(float(s), R_T) for s in np.concatenate([np.arange(4.0, 160, 2.0), np.arange(160, D.TUBE_LEN + 1, 10.0)])]
ang = np.linspace(0, 2 * np.pi, seg + 1)[:-1]
e1 = np.array(D.TB_DIR, float); e2 = np.cross(ax, e1)
verts = []; uvs = []
for (s, rr) in prof_t:
    for a in ang:
        verts.append(p0 + ax * s + rr * (math.cos(a) * e1 + math.sin(a) * e2)); uvs.append((s / 60.0, a / (2 * np.pi)))
verts = np.array(verts); uvs = np.array(uvs)
nr = len(prof_t)
qs = []
for i in range(nr - 1):
    for k in range(seg):
        a0 = i * seg + k; a1 = i * seg + (k + 1) % seg
        qs.append((a0, a1, a1 + seg, a0 + seg))
cap_c = len(verts)
verts = np.vstack([verts, (p0 + ax * SB_T)[None, :]]); uvs = np.vstack([uvs, [[0, 0]]])
tube = mesh_from_np('Cantilever', verts, np.array(qs), CS, uv=uvs)
bm = bmesh.new(); bm.from_mesh(tube.data); bm.verts.ensure_lookup_table()
capv = bm.verts[cap_c]
for k in range(seg):
    bm.faces.new((bm.verts[(k + 1) % seg], bm.verts[k], capv))
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bm.to_mesh(tube.data); bm.free()
tube.data.shade_smooth()
# fix3: the whole end (counterbore, faced annulus, chamfer) is lathe-turned aluminium; the flat glossy black epoxy disc
# read as a 'disco ball / helmet' when it filled the frame in f104-110. Faces are planar, so smooth shading is safe.
_pf = np.zeros(len(tube.data.polygons), bool); _pf[:N_END * seg] = True; _pf[-seg:] = True
tube.data.materials.append(M_ALU)
M_ALU_END = mat_alu_end(p0, ax)
tube.data.materials.append(M_ALU_END)
tube.data.polygons.foreach_set('material_index', _pf.astype(np.int32))
tube.data.update()
# glossy black epoxy sleeve where the diamond meets the tube (bevelled cylinder, not a saucer)
bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=15.0, depth=5.0, location=(D.X_SP, D.Y_SP, D.SPIRE_TOP + 1.0))
slv = bpy.context.object; slv.name = 'EpoxySleeve'
for c in slv.users_collection: c.objects.unlink(slv)
CS.objects.link(slv); slv.data.materials.append(M_EPOXY)
bvs = slv.modifiers.new('Bevel', 'BEVEL'); bvs.width = 1.2; bvs.segments = 4; bvs.limit_method = 'ANGLE'
slv.data.shade_smooth()
try:
    slv.modifiers.new('Smooth', 'WEIGHTED_NORMAL').keep_sharp = False
except Exception as ex:
    log('WARN sleeve normals', ex)

# =============================================================== world: violet blue-hour sky with a bright horizon band
log('world + lights')
w = bpy.data.worlds.new('W_Groove'); sc.world = w; w.use_nodes = True
nt = w.node_tree; N, L = nt.nodes, nt.links
bg = N['Background']
tc = N.new('ShaderNodeTexCoord')
SUN_EL = math.radians(9.0); SUN_AZ = math.radians(-25.0)   # light travels toward heading -25 deg (from back-left of the trench)
sun_to = np.array([-math.cos(SUN_AZ) * math.cos(SUN_EL), -math.sin(SUN_AZ) * math.cos(SUN_EL), math.sin(SUN_EL)])
nrmv = N.new('ShaderNodeVectorMath'); nrmv.operation = 'NORMALIZE'; L.new(tc.outputs['Generated'], nrmv.inputs[0])
dirv = nrmv.outputs['Vector']
sepw = N.new('ShaderNodeSeparateXYZ'); L.new(dirv, sepw.inputs[0])


def wmath(op, a, b=None):
    n = N.new('ShaderNodeMath'); n.operation = op
    if isinstance(a, (int, float)): n.inputs[0].default_value = a
    else: L.new(a, n.inputs[0])
    if b is not None:
        if isinstance(b, (int, float)): n.inputs[1].default_value = b
        else: L.new(b, n.inputs[1])
    return n.outputs[0]


def wmix(fac, a, b, blend='MIX'):
    m = N.new('ShaderNodeMix'); m.data_type = 'RGBA'; m.blend_type = blend
    if isinstance(fac, (int, float)): m.inputs['Factor'].default_value = fac
    else: L.new(fac, m.inputs['Factor'])
    for sock, v in ((m.inputs['A'], a), (m.inputs['B'], b)):
        if isinstance(v, tuple): sock.default_value = v
        else: L.new(v, sock)
    return m.outputs['Result']


def wdot(vec):
    n = N.new('ShaderNodeVectorMath'); n.operation = 'DOT_PRODUCT'; L.new(dirv, n.inputs[0]); n.inputs[1].default_value = tuple(vec)
    return n.outputs['Value']


zc = sepw.outputs['Z']
rz = N.new('ShaderNodeValToRGB'); L.new(wmath('ADD', wmath('MULTIPLY', zc, 0.5), 0.5), rz.inputs['Fac'])
cr = rz.color_ramp; cr.interpolation = 'B_SPLINE'
cr.elements[0].position = 0.0; cr.elements[0].color = (*hexlin('#1B0A3F'), 1)
cr.elements[1].position = 1.0; cr.elements[1].color = (*hexlin('#24127A'), 1)
for pos, hx in ((0.40, '#3A2280'), (0.47, '#7A4FD8'), (0.50, '#B88AF0'), (0.52, '#8A5FE6'), (0.57, '#5A48E8'),
                (0.64, '#3646F0'), (0.75, '#3030C0'), (0.88, '#2A1892')):
    el = cr.elements.new(pos); el.color = (*hexlin(hx), 1)
sky = rz.outputs['Color']
hz = wmath('POWER', wmath('MAXIMUM', wmath('SUBTRACT', 1.0, wmath('MULTIPLY', wmath('ABSOLUTE', zc), 3.2)), 0.0), 2.0)
# forward (trench +X through the approach heading) magenta glow on the horizon
fwd_h = np.array([math.cos(math.radians(D.PSI_DEG)), math.sin(math.radians(D.PSI_DEG)), 0.0])
fx = wmath('POWER', wmath('MAXIMUM', wdot(fwd_h), 0.0), 1.3)
sky = wmix(wmath('MULTIPLY', wmath('MULTIPLY', hz, fx), 0.55), sky, (*hexlin('#FF3F9E'), 1))
anti = np.array([-sun_to[0], -sun_to[1], 0.0]); anti /= np.linalg.norm(anti)
ax_ = wmath('POWER', wmath('MAXIMUM', wdot(anti), 0.0), 2.0)
hzn = wmath('POWER', wmath('MAXIMUM', wmath('SUBTRACT', 1.0, wmath('MULTIPLY', wmath('ABSOLUTE', wmath('SUBTRACT', zc, 0.035)), 9.0)), 0.0), 2.0)
sky = wmix(wmath('MULTIPLY', wmath('MULTIPLY', hzn, ax_), 0.8), sky, (*hexlin('#FF6FB8'), 1))
# sun-side apricot glow + disc
sg = wmath('MAXIMUM', wdot(sun_to), 0.0)
sky = wmix(wmath('MULTIPLY', wmath('MULTIPLY', wmath('ADD', hz, 0.15), wmath('POWER', sg, 6.0)), 0.95), sky, (*hexlin('#FF9A5A'), 1))
sky = wmix(wmath('POWER', sg, 300.0), sky, (*hexlin('#FFE2B0'), 1), 'ADD')
# brightness: horizon band ~2x, zenith dark
br = wmath('ADD', wmath('ADD', 0.78, wmath('MULTIPLY', hz, 0.7)), wmath('MULTIPLY', hzn, 0.7))
# high cirrus: noise on the ray direction stretched along one horizontal axis, masked to 4-30 deg elevation,
# warm (magenta/apricot) toward the sun, violet away from it
cz = wmath('MAXIMUM', zc, 0.02)
cdir = N.new('ShaderNodeVectorMath'); cdir.operation = 'DIVIDE'; L.new(dirv, cdir.inputs[0])
cdc = N.new('ShaderNodeCombineXYZ'); L.new(cz, cdc.inputs[0]); L.new(cz, cdc.inputs[1]); L.new(cz, cdc.inputs[2])
L.new(cdc.outputs[0], cdir.inputs[1])
cmap = N.new('ShaderNodeMapping'); cmap.inputs['Scale'].default_value = (0.08, 1.0, 1.0)
cmap.inputs['Rotation'].default_value = (0.0, 0.0, math.radians(30.0))
L.new(cdir.outputs[0], cmap.inputs['Vector'])
cn = N.new('ShaderNodeTexNoise'); cn.inputs['Scale'].default_value = 0.9; cn.inputs['Detail'].default_value = 6.0
cn.inputs['Roughness'].default_value = 0.62; L.new(cmap.outputs[0], cn.inputs['Vector'])
cth = N.new('ShaderNodeMapRange'); cth.inputs['From Min'].default_value = 0.5; cth.inputs['From Max'].default_value = 0.78
L.new(cn.outputs['Fac'], cth.inputs['Value'])
cmask = wmath('MULTIPLY', wmath('MULTIPLY', cth.outputs['Result'],
              wmath('SUBTRACT', 1.0, wmath('POWER', wmath('MAXIMUM', wmath('SUBTRACT', 1.0, wmath('MULTIPLY', zc, 14.0)), 0.0), 2.0))),
              wmath('MAXIMUM', wmath('SUBTRACT', 1.0, wmath('MULTIPLY', zc, 2.0)), 0.0))
cwarm = wmath('MINIMUM', wmath('ADD', wmath('MULTIPLY', wdot(sun_to), 0.8), 0.45), 1.0)
ccol = wmix(wmath('MAXIMUM', cwarm, 0.0), (*hexlin('#8E5BFF'), 1), (*hexlin('#FF6FA8'), 1))
sky = wmix(wmath('MULTIPLY', cmask, 0.45), sky, ccol)
sky = wmix(1.0, sky, (1, 1, 1, 1), 'MULTIPLY')
skym = N.new('ShaderNodeVectorMath'); skym.operation = 'SCALE'; L.new(sky, skym.inputs[0]); L.new(br, skym.inputs['Scale'])
L.new(skym.outputs[0], bg.inputs['Color'])
bg.inputs['Strength'].default_value = 1.0
w.mist_settings.start = 40.0
w.mist_settings.depth = 1360.0
w.mist_settings.falloff = 'LINEAR'

# sun (#FFC46A, strength 4): rakes along the trench from back-left -> right wall lit, left wall violet shadow
sd = bpy.data.lights.new('Sun', 'SUN'); sd.energy = 7.0; sd.color = hexlin('#FFD39A'); sd.angle = math.radians(0.5)
safe_set(sd, 'use_shadow_jitter', False)
sun = bpy.data.objects.new('Sun', sd); CL.objects.link(sun)
sun.rotation_euler = Vector(tuple(-sun_to)).to_track_quat('-Z', 'Y').to_euler()
try:
    LX = bpy.data.collections.new('A_SunExclude'); LX.objects.link(lint); LX.objects.link(fib); LX.objects.link(lintf)
    sun.light_linking.receiver_collection = LX
    for co_ in LX.collection_objects:
        co_.light_linking.link_state = 'EXCLUDE'
except Exception as ex:
    log('WARN sun light linking', ex)
# soft lilac key on the lint only (sky-like, from above-front) so it reads chalk-lilac, not khaki
ld_ = bpy.data.lights.new('LintFill', 'AREA'); ld_.shape = 'DISK'; ld_.size = 120.0; ld_.energy = 1.4e5; ld_.color = hexlin('#E8D8FF')
lfo = bpy.data.objects.new('LintFill', ld_); CL.objects.link(lfo)
lfo.location = (x_l - 60.0, 0.0, 90.0)
lfo.rotation_euler = (Vector((x_l, 0.0, 0.0)) - lfo.location).to_track_quat('-Z', 'Y').to_euler()
try:
    LI = bpy.data.collections.new('A_LintOnly'); LI.objects.link(lint); LI.objects.link(fib); LI.objects.link(lintf)
    lfo.light_linking.receiver_collection = LI
except Exception as ex:
    log('WARN lint light linking', ex)
lbd = bpy.data.lights.new('LintBack', 'SPOT'); lbd.energy = 2.2e6; lbd.color = hexlin('#FF6F9A'); lbd.spot_size = math.radians(70)
lbd.spot_blend = 0.6; safe_set(lbd, 'shadow_soft_size', 8.0)
lbo = bpy.data.objects.new('LintBack', lbd); CL.objects.link(lbo)
lbo.location = (x_l + 160.0, float(c0[1]) - 40.0, 34.0)
lbo.rotation_euler = (Vector((x_l, float(c0[1]), -2.0)) - lbo.location).to_track_quat('-Z', 'Y').to_euler()
try:
    lbo.light_linking.receiver_collection = LI
except Exception as ex:
    log('WARN lint back linking', ex)
# magenta spot from beyond the spire (opposite the approach), back-rimming facets; ignites on the reveal beat
spd = bpy.data.lights.new('MagentaRim', 'SPOT'); spd.energy = 6.0e6; spd.color = lin('magenta'); spd.spot_size = math.radians(40); spd.spot_blend = 0.35
safe_set(spd, 'shadow_soft_size', 6.0)
spot = bpy.data.objects.new('MagentaRim', spd); CL.objects.link(spot)
rim_pos = np.array([D.X_SP, D.Y_SP, 0]) + A2 * 420.0 + np.array([0, 0, 95.0]) + D.B_DIR * 60.0
spot.location = Vector(tuple(rim_pos))
tgt = Vector((D.X_SP - A2[0] * 90.0, D.Y_SP - A2[1] * 90.0, 30.0))
spot.rotation_euler = (tgt - spot.location).to_track_quat('-Z', 'Y').to_euler()
for f_, v_ in ((1, 4.0e6), (60, 4.0e6), (64, 1.5e7), (80, 1.1e7), (122, 1.1e7)):
    spd.energy = v_; spd.keyframe_insert('energy', frame=f_)
# a second, cooler magenta rim down the trench (back-rims the walls' far end and the lint)
spd2 = bpy.data.lights.new('TrenchRim', 'SPOT'); spd2.energy = 3.0e6; spd2.color = hexlin('#FF3FB0'); spd2.spot_size = math.radians(25); spd2.spot_blend = 0.5
spot2 = bpy.data.objects.new('TrenchRim', spd2); CL.objects.link(spot2)
spot2.location = (900.0, float(D.groove_center(0, 900.0)) + 40.0, 60.0)
spot2.rotation_euler = (Vector((40.0, 0.0, -12.0)) - spot2.location).to_track_quat('-Z', 'Y').to_euler()
GRV = bpy.data.collections.new('A_GrooveOnly'); GRV.objects.link(groove)
for nm_, col_, yo_, en_ in (('StreakMagenta', lin('magenta'), 46.0, 2.6e5), ('StreakCream', hexlin('#FFE6C8'), -46.0, 2.0e5)):
    d_ = bpy.data.lights.new(nm_, 'AREA'); d_.shape = 'RECTANGLE'; d_.size = 2600.0; d_.size_y = 3.0
    d_.energy = en_; d_.color = col_
    safe_set(d_, 'diffuse_factor', 0.0); safe_set(d_, 'volume_factor', 0.0); safe_set(d_, 'use_shadow', False)
    o_ = bpy.data.objects.new(nm_, d_); CL.objects.link(o_)
    o_.location = (1200.0, float(D.groove_center(0, 1200.0)) + yo_, 52.0)
    o_.rotation_euler = (0.0, 0.0, 0.0)      # emits straight down (-Z), long axis along +X
    try:
        o_.light_linking.receiver_collection = GRV
    except Exception as ex:
        log('WARN streak linking', ex)
# ultramarine area high-right (fill, 15 %), no specular
ad = bpy.data.lights.new('UltraFill', 'AREA'); ad.shape = 'SQUARE'; ad.size = 300.0; ad.energy = 0.9e6; ad.color = lin('ultramarine')
safe_set(ad, 'specular_factor', 0.0)
area = bpy.data.objects.new('UltraFill', ad); CL.objects.link(area)
area.location = (60.0, -420.0, 380.0)
area.rotation_euler = (Vector((120.0, 60.0, -20.0)) - area.location).to_track_quat('-Z', 'Y').to_euler()
# cantilever whip: narrow strip lights (specular only, linked to the tube) -> thin saffron streak + magenta counter
WC = bpy.data.collections.new('A_WhipReceivers'); WC.objects.link(tube)


def strip(name, col, size, size_y, energy, s_loc, l_loc, z_loc):
    d_ = bpy.data.lights.new(name, 'AREA'); d_.shape = 'RECTANGLE'; d_.size = size; d_.size_y = size_y
    d_.energy = energy; d_.color = col
    safe_set(d_, 'diffuse_factor', 0.0); safe_set(d_, 'volume_factor', 0.0)
    o_ = bpy.data.objects.new(name, d_); CL.objects.link(o_)
    x_, y_, z_ = D.tube_to_world(s_loc, l_loc, z_loc)
    o_.location = (float(x_), float(y_), float(z_))
    tgt_ = Vector(tuple(p0 + ax * 80.0))
    q_ = (tgt_ - o_.location).to_track_quat('-Z', 'Y')
    # long axis (local X) along the tube direction
    o_.rotation_euler = q_.to_euler()
    m_ = o_.rotation_euler.to_matrix(); lx = m_ @ Vector((1, 0, 0))
    ang_ = lx.angle(Vector(tuple(ax)))
    try:
        ll_ = o_.light_linking
        ll_.receiver_collection = WC
    except Exception as ex:
        log('WARN light linking', ex)
    return o_


ws1 = strip('WhipCream', hexlin('#FFE6C8'), 30.0, 1400.0, 4.0e6, 520.0, 0.0, 620.0)
ws2 = strip('WhipMagenta', lin('magenta'), 20.0, 1400.0, 2.5e6, 380.0, 260.0, 420.0)
ws3 = strip('WhipUltra', hexlin('#5A6BFF'), 20.0, 1400.0, 1.5e6, 380.0, -260.0, 420.0)
for o_ in (ws1, ws2, ws3):
    # orient the strip's long axis (local Y) along the tube direction
    zz = Vector(tuple(p0 + ax * 100.0)) - o_.location; zz.normalize()
    yy = Vector(tuple(ax)); yy = (yy - zz * yy.dot(zz)); yy.normalize()
    xx = yy.cross(-zz)
    o_.rotation_euler = Matrix((xx, yy, -zz)).transposed().to_euler()

# spire reflection cards: camera-invisible emissive gradient strips that the facets mirror (via the sphere probe)


def card(name, c1, c2, w_, h_, s_loc, l_loc, z_loc, strength):
    me = bpy.data.meshes.new(name)
    me.from_pydata([(-w_ / 2, 0, -h_ / 2), (w_ / 2, 0, -h_ / 2), (w_ / 2, 0, h_ / 2), (-w_ / 2, 0, h_ / 2)], [], [(0, 1, 2, 3)])
    me.uv_layers.new(name='UVMap')
    for i_, lp in enumerate(me.loops):
        v_ = me.vertices[lp.vertex_index].co
        me.uv_layers[0].data[i_].uv = ((v_.x / w_) + 0.5, (v_.z / h_) + 0.5)
    m = bpy.data.materials.new('M_' + name); m.use_nodes = True
    nt_ = m.node_tree; Nn = nt_.nodes
    for n_ in list(Nn):
        if n_.type == 'BSDF_PRINCIPLED': Nn.remove(n_)
    em = Nn.new('ShaderNodeEmission')
    uvn = Nn.new('ShaderNodeTexCoord'); sx = Nn.new('ShaderNodeSeparateXYZ'); nt_.links.new(uvn.outputs['UV'], sx.inputs[0])
    wv_ = Nn.new('ShaderNodeTexWave'); wv_.wave_type = 'BANDS'; wv_.bands_direction = 'X'; wv_.inputs['Scale'].default_value = 1.5
    wv_.inputs['Distortion'].default_value = 0.0; wv_.inputs['Detail'].default_value = 0.0
    nt_.links.new(uvn.outputs['UV'], wv_.inputs['Vector'])
    mr_ = Nn.new('ShaderNodeMapRange'); mr_.inputs['From Min'].default_value = 0.6; mr_.inputs['From Max'].default_value = 0.85
    mr_.inputs['To Min'].default_value = 0.04 * strength; mr_.inputs['To Max'].default_value = strength
    nt_.links.new(wv_.outputs['Fac'], mr_.inputs['Value']); nt_.links.new(mr_.outputs['Result'], em.inputs['Strength'])
    rp = Nn.new('ShaderNodeValToRGB'); rp.color_ramp.elements[0].color = (*c1, 1); rp.color_ramp.elements[1].color = (*c2, 1)
    nt_.links.new(sx.outputs['X'], rp.inputs['Fac']); nt_.links.new(rp.outputs['Color'], em.inputs['Color'])
    nt_.links.new(em.outputs[0], Nn['Material Output'].inputs['Surface'])
    me.materials.append(m)
    o_ = bpy.data.objects.new(name, me); CL.objects.link(o_)
    x_, y_, z_ = D.local_to_world(s_loc, l_loc, z_loc)
    o_.location = (float(x_), float(y_), float(z_))
    tg_ = Vector((D.X_SP, D.Y_SP, 55.0))
    o_.rotation_euler = (tg_ - o_.location).to_track_quat('Y', 'Z').to_euler()
    o_.rotation_euler.rotate_axis('Z', math.radians(180))
    safe_set(o_, 'visible_camera', False); safe_set(o_, 'visible_shadow', False)
    safe_set(o_, 'visible_diffuse', False); safe_set(o_, 'visible_volume_scatter', False)
    return o_




def gem_card(name, col, w_, h_, pos, strength):
    me = bpy.data.meshes.new(name)
    me.from_pydata([(-w_ / 2, 0, -h_ / 2), (w_ / 2, 0, -h_ / 2), (w_ / 2, 0, h_ / 2), (-w_ / 2, 0, h_ / 2)], [], [(0, 1, 2, 3)])
    m = bpy.data.materials.new('M_' + name); m.use_nodes = True
    Nn = m.node_tree.nodes
    for n_ in list(Nn):
        if n_.type == 'BSDF_PRINCIPLED': Nn.remove(n_)
    em = Nn.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (*col, 1); em.inputs['Strength'].default_value = strength
    m.node_tree.links.new(em.outputs[0], Nn['Material Output'].inputs['Surface'])
    me.materials.append(m)
    o_ = bpy.data.objects.new(name, me); CL.objects.link(o_)
    o_.location = Vector(pos)
    o_.rotation_euler = (Vector((D.X_SP, D.Y_SP, 60.0)) - o_.location).to_track_quat('Y', 'Z').to_euler()
    safe_set(o_, 'visible_camera', False); safe_set(o_, 'visible_shadow', False)
    safe_set(o_, 'visible_diffuse', False); safe_set(o_, 'visible_volume_scatter', False)
    return o_


CARD_COLS = [lin('magenta'), lin('ultramarine'), lin('saffron'), lin('chalk'), lin('violet'), lin('magenta'), hexlin('#5A6BFF')]
rng_c = np.random.default_rng(77)
for k in range(20):
    az = math.radians(D.PSI_DEG + 180.0) + rng_c.uniform(-1.9, 1.9) if k < 14 else rng_c.uniform(0, 2 * np.pi)
    el = math.radians(rng_c.uniform(4.0, 55.0))
    dist = rng_c.uniform(170.0, 260.0)
    pos = (D.X_SP + dist * math.cos(el) * math.cos(az), D.Y_SP + dist * math.cos(el) * math.sin(az), 60.0 + dist * math.sin(el))
    sz_ = rng_c.uniform(28.0, 60.0)
    col = CARD_COLS[k % len(CARD_COLS)]
    stn = 7.0 if col is not CARD_COLS[3] else 4.0
    gem_card(f'GemCard{k:02d}', col, sz_, sz_ * rng_c.uniform(0.5, 1.2), pos, stn)

# fix3 (director: f97-108 too dark, mean luma 0.13-0.15): keyed "jewel" softboxes, specular only, no shadow, light-linked
# to the spire, energy 0 outside f95-110 (keys 94:0 -> 97:on -> 108:on -> 111:0). Placed where the facets seen during the
# vault mirror to (behind/above the climbing camera, el 15-60 deg, az +-90 deg about the approach axis; checked offline by
# ray-casting the facets from the camera path), so facets ignite magenta / ultramarine / saffron with dark seams between.
# energy = 4 * area * radiance (radiance ~ gem-card brightness, kept moderate so AgX keeps the colours saturated). The
# facets' specular tint (ultramarine facing -> magenta -> saffron grazing) multiplies the light colour, so the 'magenta'
# box is violet-magenta (#FF26E0): it reads magenta on mid-angle facets and ultramarine on facing ones.
JEWEL_GAIN = 1.0
JR = bpy.data.collections.new('A_JewelReceivers'); JR.objects.link(spire)
for nm_, col_, az_d, el_d, w_, h_, rad_ in (('JewelMagenta', hexlin('#FF26E0'), -62.0, 34.0, 220.0, 260.0, 4.5),
                                             ('JewelSaffron', lin('saffron'), 62.0, 34.0, 220.0, 260.0, 4.5),
                                             ('JewelUltra', lin('ultramarine'), 0.0, 40.0, 190.0, 240.0, 7.5),
                                             ('JewelSaffron2', lin('saffron'), -125.0, 40.0, 120.0, 160.0, 4.5)):
    az_, el_ = math.radians(az_d), math.radians(el_d)
    dv_ = (-A2 * math.cos(az_) + D.B_DIR * math.sin(az_)) * math.cos(el_) + np.array([0.0, 0.0, 1.0]) * math.sin(el_)
    jd = bpy.data.lights.new(nm_, 'AREA'); jd.shape = 'RECTANGLE'; jd.size = w_; jd.size_y = h_; jd.color = col_
    safe_set(jd, 'diffuse_factor', 0.0); safe_set(jd, 'volume_factor', 0.0); safe_set(jd, 'use_shadow', False)
    jo = bpy.data.objects.new(nm_, jd); CL.objects.link(jo)
    jo.location = Vector(tuple(np.array([D.X_SP, D.Y_SP, 70.0]) + dv_ * 300.0))
    zz_ = Vector(tuple(dv_)).normalized()                       # local +Z away from the spire -> emits (-Z) at it
    xx_ = Vector((0.0, 0.0, 1.0)).cross(zz_).normalized()       # width horizontal
    yy_ = zz_.cross(xx_)
    jo.rotation_euler = Matrix((xx_, yy_, zz_)).transposed().to_euler()
    try:
        jo.light_linking.receiver_collection = JR
    except Exception as ex:
        log('WARN jewel linking', ex)
    P_ = 4.0 * w_ * h_ * rad_ * JEWEL_GAIN
    for f_, v_ in ((94, 0.0), (97, P_), (108, P_), (111, 0.0)):
        jd.energy = v_; jd.keyframe_insert('energy', frame=f_)
    log('jewel light', nm_, 'P %.3g' % P_, 'at', [round(c, 1) for c in jo.location])

# sphere probes: along the canyon, over the approach, and a high-res one at the spire face
probes = [((0.0, float(D.groove_center(0, 0.0)), -12.0), 140.0), ((140.0, float(D.groove_center(0, 140.0)), -12.0), 140.0),
          ((290.0, float(D.groove_center(0, 290.0)), -12.0), 160.0)]
for _sl in (-330.0, -190.0):
    _x, _y, _ = D.local_to_world(_sl, 0.0, 0.0)
    probes.append(((float(_x), float(_y), 25.0), 120.0))
xf, yf, _ = D.local_to_world(-80.0, 0.0, 0.0)
probes.append(((float(xf), float(yf), 60.0), 200.0))
xf2, yf2, _ = D.local_to_world(-45.0, 0.0, 0.0)
probes.append(((float(xf2), float(yf2), 95.0), 70.0))   # climb probe close to the face (facet reflections during the vault)
for i, (loc, infl) in enumerate(probes):
    try:
        pr = bpy.data.lightprobes.new(f'Probe{i}', 'SPHERE')
        pro = bpy.data.objects.new(f'Probe{i}', pr); CL.objects.link(pro)
        pro.location = loc
        safe_set(pr, 'influence_distance', infl)
        safe_set(pr, 'clip_end', 3000.0)
    except Exception as ex:
        log('WARN probe', ex)

# =============================================================== camera
log('camera')
camd = bpy.data.cameras.new('CamS1'); camd.lens = 18.0; camd.sensor_fit = 'HORIZONTAL'; camd.sensor_width = 36.0
camd.dof.use_dof = False; camd.clip_end = 9000.0; camd.clip_start = 0.3
cam = bpy.data.objects.new('CamS1', camd); sc.collection.objects.link(cam); sc.camera = cam
cam.rotation_mode = 'QUATERNION'
fwd, up = D.basis(cp['yaw'], cp['pitch'], cp['roll'])
prevq = None
for i, f in enumerate(cp['frames']):
    F = Vector(fwd[i]); U = Vector(up[i]); Rr = F.cross(U)
    m3 = Matrix((Rr, U, -F)).transposed()
    q = m3.to_quaternion()
    if prevq is not None and prevq.dot(q) < 0: q.negate()
    prevq = q
    cam.location = Vector(cp['pos'][i]); cam.rotation_quaternion = q
    cam.keyframe_insert('location', frame=int(f)); cam.keyframe_insert('rotation_quaternion', frame=int(f))
try:
    for fc in cam.animation_data.action.fcurves:
        for kp in fc.keyframe_points: kp.interpolation = 'BEZIER'
except Exception:
    pass

# =============================================================== compositor
log('compositor')
cng = bpy.data.node_groups.new('Comp_SetA', 'CompositorNodeTree')
sc.compositing_node_group = cng
cng.interface.new_socket('Image', in_out='OUTPUT', socket_type='NodeSocketColor')
CN, CLk = cng.nodes, cng.links
rl = CN.new('CompositorNodeRLayers')
last = rl.outputs['Image']


def cmix(a_sock, b_val_or_sock, fac_sock=None, fac=1.0, blend='MIX'):
    mx = CN.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = blend
    A_, B_, F_ = mx.inputs['A'], mx.inputs['B'], mx.inputs['Factor']; out = mx.outputs['Result']
    CLk.new(a_sock, A_)
    if isinstance(b_val_or_sock, tuple): B_.default_value = b_val_or_sock
    else: CLk.new(b_val_or_sock, B_)
    if fac_sock is not None: CLk.new(fac_sock, F_)
    else: F_.default_value = fac
    return out


def cmath(op, a, b):
    n = CN.new('ShaderNodeMath'); n.operation = op
    for i_, v_ in enumerate((a, b)):
        if isinstance(v_, (int, float)): n.inputs[i_].default_value = v_
        else: CLk.new(v_, n.inputs[i_])
    return n.outputs[0]


try:
    # aerial perspective: light lilac haze on geometry only (sky keeps its own gradient)
    geo = cmath('LESS_THAN', rl.outputs['Depth'], 2.0e4)
    fac = cmath('MULTIPLY', rl.outputs['Mist'], geo)
    env_ = None
    for nm_ in ('Env', 'Environment'):
        if nm_ in rl.outputs:
            env_ = rl.outputs[nm_]; break
    if env_ is not None:
        # the Env pass is black under geometry: inpaint the sky down into the covered pixels, so far ground
        # dissolves into the exact sky colour just above it (no seam, no constant-colour band)
        sa = CN.new('CompositorNodeSetAlpha')
        try:
            sa.inputs['Type'].default_value = 'Replace Alpha'
        except Exception:
            try:
                sa.mode = 'REPLACE_ALPHA'
            except Exception as ex:
                log('WARN setalpha mode', ex)
        CLk.new(env_, sa.inputs['Image'])
        CLk.new(cmath('SUBTRACT', 1.0, geo), sa.inputs['Alpha'])
        ip = CN.new('CompositorNodeInpaint')
        ok_ = False
        for k_ in ('Size', 'Distance'):
            if k_ in ip.inputs:
                ip.inputs[k_].default_value = 420; ok_ = True; break
        if not ok_:
            try:
                ip.distance = 420
            except Exception as ex:
                log('WARN inpaint distance', ex)
        CLk.new(sa.outputs[0], ip.inputs['Image'])
        hb = CN.new('CompositorNodeBlur')
        try:
            hb.inputs['Size'].default_value = (70.0, 90.0)
        except Exception as ex:
            log('WARN haze blur size', ex)
        CLk.new(ip.outputs[0], hb.inputs[0])
        last = cmix(last, hb.outputs[0], fac_sock=fac)
        log('haze -> inpainted environment pass', [i.name for i in ip.inputs], [i.name for i in sa.inputs])
    else:
        log('WARN no Env output; constant haze')
        last = cmix(last, (*[c * 1.55 for c in hexlin('#9A6BEA')], 1), fac_sock=fac)
except Exception as ex:
    log('WARN mist comp', ex)
gl = CN.new('CompositorNodeGlare')
safe_set(gl.inputs['Type'], 'default_value', 'Bloom')
for k, v in (('Threshold', 1.2), ('Strength', 0.12), ('Size', 0.6)):
    try: gl.inputs[k].default_value = v
    except Exception as ex: log('WARN glare', k, ex)
CLk.new(last, gl.inputs['Image']); last = gl.outputs['Image']
# 4-point star glints on the facets during the reveal / approach (keyed mix)
try:
    gs = CN.new('CompositorNodeGlare')
    safe_set(gs.inputs['Type'], 'default_value', 'Streaks')
    for k, v in (('Threshold', 6.0), ('Strength', 0.0), ('Streaks', 4), ('Fade', 0.85)):
        try: gs.inputs[k].default_value = v
        except Exception as ex: log('WARN streak', k, ex)
    CLk.new(last, gs.inputs['Image']); last = gs.outputs['Image']
    for f_, v_ in ((1, 0.0), (120, 0.0)):
        gs.inputs['Strength'].default_value = v_
        gs.inputs['Strength'].keyframe_insert('default_value', frame=f_)
except Exception as ex:
    log('WARN streak glare', ex)
ld = CN.new('CompositorNodeLensdist')
try: ld.inputs['Dispersion'].default_value = 0.006
except Exception as ex: log('WARN lensdist', ex)
CLk.new(last, ld.inputs['Image']); last = ld.outputs['Image']
hs = CN.new('CompositorNodeHueSat')
hs.inputs['Saturation'].default_value = 1.12
CLk.new(last, hs.inputs['Image']); last = hs.outputs['Image']
try:
    em = CN.new('CompositorNodeEllipseMask')
    for k, v in (('Width', 0.9), ('Height', 0.9)):
        try: em.inputs[k].default_value = v
        except Exception: setattr(em, k.lower(), v)
    bl = CN.new('CompositorNodeBlur')
    try:
        bl.inputs['Size'].default_value = (0.25 * 2560 * 0.5, 0.25 * 1440 * 0.5)
    except Exception as ex:
        log('WARN blur size input', ex)
    CLk.new(em.outputs[0], bl.inputs[0])
    mr = CN.new('ShaderNodeMapRange')
    mr.inputs['To Min'].default_value = 0.88; mr.inputs['To Max'].default_value = 1.0
    CLk.new(bl.outputs[0], mr.inputs['Value'])
    mul = CN.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs['Factor'].default_value = 1.0
    CLk.new(last, mul.inputs['A'])
    CLk.new(mr.outputs['Result'], mul.inputs['B']); last = mul.outputs['Result']
except Exception as ex:
    log('WARN vignette', ex)
out = CN.new('NodeGroupOutput'); CLk.new(last, out.inputs[0])

# =============================================================== handoff.json (S1_end)
log('handoff')
from bpy_extras.object_utils import world_to_camera_view
handoff_frames = []
for f in (118, 119, 120):
    sc.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get()
    mw = cam.matrix_world.copy()
    F = -(mw.to_3x3() @ Vector((0, 0, 1))); U = mw.to_3x3() @ Vector((0, 1, 0))
    hit, loc, nrm_, fi, ob, _ = sc.ray_cast(dg, mw.translation, F)
    target = loc if hit else mw.translation + F * 100.0
    sc.frame_set(f + 1)
    p1 = world_to_camera_view(sc, cam, target)
    sc.frame_set(f)
    p0_ = world_to_camera_view(sc, cam, target)
    vel = (p1.x - p0_.x, p1.y - p0_.y)
    handoff_frames.append({'frame': f, 'forward': [round(c, 5) for c in F], 'up': [round(c, 5) for c in U],
                           'position': [round(c, 3) for c in mw.translation],
                           'centre_hit': ob.name if hit else None, 'centre_dist_m': round((target - mw.translation).length, 2),
                           'screen_velocity_per_frame': [round(vel[0], 5), round(vel[1], 5)]})
sc.frame_set(1)
hp = os.path.join(ROOT, 'data', 'handoff.json')
try:
    hd = json.load(open(hp)) if os.path.exists(hp) else {}
except Exception:
    hd = {}
hd['S1_end'] = {
    'note': 'Set A camera, last 3 frames (118-120). forward/up are world unit vectors in Set A space (Z up, +X along the groove; '
            'the cantilever axis heads %.0f deg CCW from +X). screen_velocity_per_frame = motion of the world point under '
            'frame centre, in normalised frame units (x right, y up) per frame. Camera rides just above and behind the front of the '
            'brushed-aluminium cantilever looking along it (pitched ~8 deg down, rising with it); the tube is a bright neutral-silver '
            'wedge rising from bottom-centre with a thin cream streak and magenta / ultramarine side streaks.' % D.TUBE_PSI,
    'lens_mm': 18.0, 'fps': 24, 'frames': handoff_frames,
}
if os.environ.get('SETA_OUT'):
    log('test build (SETA_OUT): handoff not written', hd['S1_end']['frames'])
else:
    with open(hp, 'w') as fh:
        json.dump(hd, fh, indent=1)
    log('handoff written', hd['S1_end']['frames'])

# =============================================================== pack + save
for im in bpy.data.images:
    if im.source == 'FILE' and not im.packed_file:
        try: im.pack()
        except Exception as ex: log('WARN pack', im.name, ex)
os.makedirs(os.path.join(ROOT, 'blend'), exist_ok=True)
out_path = os.environ.get('SETA_OUT') or os.path.join(ROOT, 'blend', 'set_a.blend')   # SETA_OUT: scratch test builds
bpy.ops.wm.save_as_mainfile(filepath=out_path, compress=True)
log('SAVED', out_path)
print('BUILD_OK', flush=True)
