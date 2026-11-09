"""RecordDisc / RecordPatch / OuterDesert meshes, the RecordLive GN morph, M_Sand / M_OuterSand."""
import bpy, math, os, time
import numpy as np
from c_common import *
from c_nodes import NB

TEX = os.path.join(ROOT, 'assets', 'c')   # short-path copies (Windows MAX_PATH)
PATCH_R = (940.0, 1200.0)
PATCH_TH = 7.5            # +- degrees about bearing 0
PATCH_DR = 0.30
HOP_H = 18.0
HOP_W = 95.0
KICK_SIGMA = 14.0


# ---------------------------------------------------------------- numpy geometry
def polar_rings(zones):
    radii, nsegs = [], []
    r = 0.0
    for (r_end, dr, ns) in zones:
        n = max(1, int(round((r_end - r) / dr)))
        radii += list(np.linspace(r, r_end, n + 1)[1:]); nsegs += [ns] * n
        r = r_end
    return np.array(radii), np.array(nsegs, dtype=np.int64)


def build_polar(radii, nsegs, centre=True):
    offs, cos_ = [], []
    vi = 0
    if centre:
        cos_.append(np.zeros((1, 2))); vi = 1
    for r, n in zip(radii, nsegs):
        offs.append(vi)
        th = np.arange(n) * (2 * np.pi / n)
        cos_.append(np.stack([r * np.cos(th), r * np.sin(th)], 1))
        vi += n
    co = np.concatenate(cos_)
    tris = []
    if centre:
        n0 = nsegs[0]; j = np.arange(n0)
        tris.append(np.stack([np.zeros(n0, np.int64), offs[0] + j, offs[0] + (j + 1) % n0], 1))
    for i in range(len(radii) - 1):
        na, nb = int(nsegs[i]), int(nsegs[i + 1]); a0, b0 = offs[i], offs[i + 1]
        if na == nb:
            j = np.arange(na); jn = (j + 1) % na
            tris.append(np.stack([a0 + j, b0 + j, b0 + jn], 1)); tris.append(np.stack([a0 + j, b0 + jn, a0 + jn], 1))
        elif nb > na:
            k = nb // na; assert nb == k * na
            jb = np.arange(nb); ia = jb // k
            tris.append(np.stack([a0 + ia, b0 + jb, b0 + (jb + 1) % nb], 1))
            ii = np.arange(na)
            tris.append(np.stack([a0 + ii, b0 + ((ii + 1) * k) % nb, a0 + (ii + 1) % na], 1))
        else:
            k = na // nb; assert na == k * nb
            ja = np.arange(na); ib = ja // k
            tris.append(np.stack([a0 + ja, b0 + ib, a0 + (ja + 1) % na], 1))
            ii = np.arange(nb)
            tris.append(np.stack([b0 + ii, b0 + (ii + 1) % nb, a0 + ((ii + 1) * k) % na], 1))
    return co, np.concatenate(tris).astype(np.int32), offs


def make_mesh(name, co2, z, tris):
    me = bpy.data.meshes.new(name)
    nv = len(co2)
    co = np.zeros((nv, 3), np.float32); co[:, :2] = co2; co[:, 2] = z
    me.vertices.add(nv); me.vertices.foreach_set('co', co.ravel())
    nf = len(tris)
    me.loops.add(nf * 3); me.loops.foreach_set('vertex_index', tris.ravel())
    me.polygons.add(nf); me.polygons.foreach_set('loop_start', np.arange(0, nf * 3, 3, dtype=np.int32))
    me.update(calc_edges=True)
    me.shade_smooth()
    return me


def set_attr(me, name, arr, typ='FLOAT'):
    a = me.attributes.get(name) or me.attributes.new(name, typ, 'POINT')
    a.data.foreach_set('value', np.ascontiguousarray(arr, dtype=np.int32 if typ == 'INT' else np.float32).ravel())


# ---------------------------------------------------------------- analytic heights
CRATER_R = 38.0
SPOKE_W = 0.24     # spoke half-width in cos(8 theta) units: constant ANGULAR width -> rays widening outward (~30 m at r 1000)


def label_mesa(r):
    # two 20 m terraces with 12 m wide sloped walls (strata read from above), a wide 30 m deep spindle crater with
    # a raised lit rim
    h = 20.0 * (1 - smoothstep(250, 262, r)) + 20.0 * (1 - smoothstep(234, 246, r))
    h = h - 30.0 * (1 - smoothstep(12, CRATER_R, r)) + 3.5 * np.exp(-((r - CRATER_R - 5.0) / 5.0) ** 2)
    return h


def spoke_mask(r, th):
    return np.exp(-(np.cos(8 * th) / SPOKE_W) ** 2)


def groove_window(r):
    return smoothstep(R_GROOVE0, R_GROOVE0 + 25, r) * (1 - smoothstep(R_GROOVE1 - 25, R_GROOVE1, r))


def h_record(x, y):
    r = np.hypot(x, y); th = np.arctan2(y, x)
    win = groove_window(r)
    rr = r + 2.5 * np.cos(16 * th) * win
    xg = np.pi * (rr - R_GROOVE0) / RING_PITCH
    eps = 0.2
    s = np.sqrt(np.sin(xg) ** 2 + eps * eps) - eps
    c = np.clip(1 - s / (math.sqrt(1 + eps * eps) - eps), 0, 1)
    spk = spoke_mask(r, th) * win
    crest = CREST_H * c ** 1.4 * win * (1 - 0.8 * spk)          # ridges flatten into broad smooth spoke channels
    spoke = -2.5 * spk
    trench = -18.0 * smoothstep(1170, 1177, r) * (1 - smoothstep(1193, 1200, r))
    k = np.floor((rr - R_GROOVE0) / RING_PITCH + 0.5)
    zone = np.clip(np.floor(k * 8 / 23.0), 0, 7).astype(np.int32)
    return label_mesa(r) + crest + spoke + trench, crest, zone


def dune_weight(r):
    return smoothstep(262, 340, r) * (1 - smoothstep(1135, 1198, r))


def outer_height(x, y):
    """Apricot outer dunes (numpy): elongated ridged sines, grows from 0 at the rim."""
    r = np.hypot(x, y)
    rng = np.random.RandomState(7)
    h = np.zeros_like(x); asum = 0.0
    wx = 0.0018 * np.sin(x * 0.0021 + 1.3) + 0.0011 * np.sin(y * 0.0017 + 0.4)
    warp = 140 * np.sin(x * 0.0013 + 2.0) * np.sin(y * 0.0011 + 0.7) + 90 * np.sin((x + y) * 0.0024)
    for i in range(6):
        ang = 1.35 + rng.uniform(-0.35, 0.35)
        lam = rng.uniform(150, 420)
        amp = rng.uniform(2.5, 6.5) * (lam / 300.0)
        u = (x * math.cos(ang) + y * math.sin(ang) + warp * (0.6 + 0.4 * i / 5)) * (2 * np.pi / lam) + rng.uniform(0, 6.28)
        h += amp * (0.5 + 0.5 * np.sin(u + 0.6 * np.sin(u)))
        asum += 0.5 * amp
    h = (h - asum) * 1.1 + 0.5
    h = h * (0.5 + 0.5 * smoothstep(1200, 1500, r))
    g = smoothstep(1200, 1420, r)
    return h * g + 0.0 * wx


# ---------------------------------------------------------------- GN: dune bake
def _marble_vec(nb, pos):
    S, ang, O, _fq = marble_mapping()
    x, y, _ = nb.sep(pos)
    v = nb.comb(x, y, 0.0)
    v = nb.vmath('SCALE', v, scale=S)
    if abs(ang) > 1e-9:
        n = nb.N.new('ShaderNodeVectorRotate'); n.rotation_type = 'Z_AXIS'
        nb._in(n.inputs['Vector'], v); n.inputs['Angle'].default_value = ang
        v = n.outputs[0]
    return nb.vmath('ADD', v, tuple(O))


def dune_profile(nb, m):
    """asymmetric dune: rounded windward rise to the crest at 0.71 (chalk vein), sharp lee drop."""
    c = 0.71
    w = nb.math('DIVIDE', m, c, clamp=True)
    hw = nb.sub(0.5, nb.mul(0.5, nb.math('COSINE', nb.mul(w, math.pi))))
    s = nb.math('DIVIDE', nb.sub(m, c), 1 - c, clamp=True)
    hl = nb.math('POWER', nb.sub(1.0, s), 2.0)
    lt = nb.math('LESS_THAN', m, c)
    return nb.add(nb.mul(lt, hw), nb.mul(nb.sub(1.0, lt), hl))


def bake_group():
    ng = bpy.data.node_groups.new('GN_BakeDune', 'GeometryNodeTree')
    ng.interface.new_socket('Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    ng.interface.new_socket('Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    nb = NB(ng, 'GEO')
    gi = nb.node('NodeGroupInput'); go = nb.node('NodeGroupOutput')
    pos = nb.node('GeometryNodeInputPosition').outputs[0]
    V = _marble_vec(nb, pos)
    S, _a, _o, FQ = marble_mapping()
    d = 0.0025
    f0 = ND.build_marble_field(ng, V, scale=1.0, freq=FQ)
    fx = ND.build_marble_field(ng, nb.vmath('ADD', V, (d, 0, 0)), scale=1.0, freq=FQ)
    fy = ND.build_marble_field(ng, nb.vmath('ADD', V, (0, d, 0)), scale=1.0, freq=FQ)
    gx = nb.sub(fx['raw'], f0['raw']); gy = nb.sub(fy['raw'], f0['raw'])
    g = nb.div(nb.math('SQRT', nb.add(nb.mul(gx, gx), nb.mul(gy, gy))), d * S)  # raw per metre
    width = nb.div(1.0, nb.math('MAXIMUM', g, 1e-4))                           # band width (m)
    amp = nb.math('MINIMUM', nb.math('MAXIMUM', nb.mul(width, 0.19), 0.8), 15.0)
    x, y, _ = nb.sep(pos)
    p2 = nb.comb(x, y, 0.0)
    var = nb.noise(nb.vmath('SCALE', p2, scale=1 / 420.0), 1.0, 1.0, 0.5)
    amp = nb.mul(amp, nb.madd(var, 0.9, 0.35))
    prof = dune_profile(nb, f0['m'])
    fbm = nb.mul(nb.sub(nb.noise(nb.vmath('SCALE', p2, scale=1 / 160.0), 1.0, 3.0, 0.55), 0.5), 5.0)
    h = nb.add(nb.mul(prof, amp), fbm)
    st = nb.node('GeometryNodeStoreNamedAttribute'); st.data_type = 'FLOAT'; st.domain = 'POINT'
    st.inputs['Name'].default_value = 'h_bake'
    nb.L.new(gi.outputs[0], st.inputs['Geometry']); nb.L.new(h, st.inputs['Value'])
    nb.L.new(st.outputs[0], go.inputs[0])
    return ng


def bake_dunes(obj, ng):
    mod = obj.modifiers.new('bake', 'NODES'); mod.node_group = ng
    dg = bpy.context.evaluated_depsgraph_get(); dg.update()
    ev = obj.evaluated_get(dg)
    me = ev.data
    arr = np.zeros(len(me.vertices), np.float32)
    me.attributes['h_bake'].data.foreach_get('value', arr)
    obj.modifiers.remove(mod)
    return arr


# ---------------------------------------------------------------- GN: RecordLive
LIVE_INPUTS = ['front', 'kr0', 'kr1', 'kr2', 'ka0', 'ka1', 'ka2'] + [f'b{i}' for i in range(8)] + ['pulse_amp']
CULL_INPUTS = ['c_x', 'c_y', 'c_hx', 'c_hy', 'c_cos', 'c_dmax', 'c_near']


def live_group():
    ng = bpy.data.node_groups.new('RecordLive', 'GeometryNodeTree')
    ng.interface.new_socket('Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    ng.interface.new_socket('Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    nb = NB(ng, 'GEO')
    gi = nb.node('NodeGroupInput'); go = nb.node('NodeGroupOutput')
    V = {k: nb.value(0.0, k) for k in LIVE_INPUTS}
    V['front'].node.outputs[0].default_value = -200.0
    # ---- view cull (keyed per 12-frame block, constant interpolation): keep a wedge + near circle
    CV = {k: nb.value(0.0, k) for k in CULL_INPUTS}
    CV['c_dmax'].node.outputs[0].default_value = 1e6; CV['c_near'].node.outputs[0].default_value = 1e6
    cpos = nb.node('GeometryNodeInputPosition').outputs[0]
    qx, qy, _ = nb.sep(cpos)
    vx = nb.sub(qx, CV['c_x']); vy = nb.sub(qy, CV['c_y'])
    dd = nb.math('SQRT', nb.add(nb.mul(vx, vx), nb.mul(vy, vy)))
    ca = nb.div(nb.add(nb.mul(vx, CV['c_hx']), nb.mul(vy, CV['c_hy'])), nb.math('MAXIMUM', dd, 1e-3))
    keep = nb.math('MAXIMUM', nb.math('LESS_THAN', dd, CV['c_near']),
                   nb.mul(nb.math('LESS_THAN', dd, CV['c_dmax']), nb.math('GREATER_THAN', ca, CV['c_cos'])))
    dl = nb.node('GeometryNodeDeleteGeometry'); dl.domain = 'POINT'
    nb.L.new(gi.outputs[0], dl.inputs['Geometry']); nb.L.new(nb.math('LESS_THAN', keep, 0.5), dl.inputs['Selection'])
    geo_in = dl.outputs[0]
    r = nb.attr('r'); hd = nb.attr('h_dune'); hr = nb.attr('h_rec'); hc = nb.attr('h_crest')
    pl = nb.attr('patch_lower'); zone = nb.attr('zone', 'INT')
    fr = nb.sub(V['front'], r)
    u = nb.math('MULTIPLY', fr, 1 / 60.0, clamp=True)
    fc = nb.node('ShaderNodeFloatCurve')
    mp = fc.mapping; mp.use_clip = False
    cv = mp.curves[0]
    cv.points[0].location = (0.0, 0.0); cv.points[1].location = (1.0, 1.0)
    cv.points.new(0.55, 1.10); cv.points.new(0.78, 0.96)
    mp.update()
    fc.inputs['Factor'].default_value = 1.0
    nb.L.new(u, fc.inputs['Value'])
    morph = fc.outputs[0]
    hop = nb.mul(nb.mul(nb.math('POWER', nb.math('SINE', nb.mul(nb.math('MULTIPLY', fr, 1 / HOP_W, clamp=True), math.pi)), 1.4), HOP_H), nb.maprange(r, 930.0, 1090.0, 1.0, 0.22))
    ks = None
    for i in range(3):
        d = nb.mul(nb.sub(r, V[f'kr{i}']), 1.0 / KICK_SIGMA)
        k = nb.mul(nb.math('EXPONENT', nb.mul(nb.mul(d, d), -1.0)), V[f'ka{i}'])
        ks = k if ks is None else nb.add(ks, k)
    m1 = nb.math('MINIMUM', morph, 1.0)
    ks = nb.mul(ks, nb.sub(1.0, m1))
    isw = nb.node('GeometryNodeIndexSwitch'); isw.data_type = 'FLOAT'
    while len(isw.index_switch_items) < 8:
        isw.index_switch_items.new()
    nb.L.new(zone, isw.inputs['Index'])
    for i in range(8):
        nb.L.new(V[f'b{i}'], isw.inputs[str(i)])
    pulse = nb.mul(isw.outputs[0], V['pulse_amp'])
    hrp = hr        # adr2: no geometric pulse (shader glow only) -> f517+ uses the static baked RecordStatic
    h = nb.add(hd, nb.mul(nb.sub(hrp, hd), morph))
    h = nb.sub(nb.add(nb.add(h, hop), ks), pl)
    pos = nb.node('GeometryNodeInputPosition').outputs[0]
    x, y, _ = nb.sep(pos)
    sp = nb.node('GeometryNodeSetPosition')
    nb.L.new(geo_in, sp.inputs['Geometry']); nb.L.new(nb.comb(x, y, h), sp.inputs['Position'])
    geo = sp.outputs[0]
    for name, val in (('morph', nb.clamp01(morph)), ('pulse', pulse), ('kick', ks), ('hop', hop)):
        st = nb.node('GeometryNodeStoreNamedAttribute'); st.data_type = 'FLOAT'; st.domain = 'POINT'
        st.inputs['Name'].default_value = name
        nb.L.new(geo, st.inputs['Geometry']); nb.L.new(val, st.inputs['Value'])
        geo = st.outputs[0]
    nb.L.new(geo, go.inputs[0])
    return ng


# ---------------------------------------------------------------- materials
def _img(nb, path, vec, interp='Linear'):
    t = nb.N.new('ShaderNodeTexImage')
    t.image = bpy.data.images.load(path, check_existing=True)
    t.image.colorspace_settings.name = 'Non-Color'
    t.interpolation = interp
    nb._in(t.inputs['Vector'], vec)
    return t.outputs['Color']


def fade(nb, near, far):
    g = nb.N.new('ShaderNodeGroup'); g.node_tree = ND.ng_fade_by_distance()
    g.inputs['near'].default_value = near; g.inputs['far'].default_value = far
    return g.outputs['Fac']


def sand_normal(nb, p, strength=1.0):
    """World-ish tangent perturbation from Poly Haven normal maps (no UVs needed) + wind ripples bump."""
    x, y, _ = nb.sep(p)
    p2 = nb.comb(x, y, 0.0)
    geo = nb.N.new('ShaderNodeNewGeometry')
    n1 = _img(nb, os.path.join(TEX, 'sand_n.jpg'), nb.vmath('SCALE', p2, scale=1.0))
    n2 = _img(nb, os.path.join(TEX, 'aer_n.jpg'), nb.vmath('SCALE', p2, scale=1 / 40.0))
    mask = nb.ss(0.35, 0.65, nb.noise(nb.vmath('SCALE', p2, scale=1 / 300.0), 1.0, 2.0, 0.5))
    k1 = nb.mul(fade(nb, 0.0, 60.0), 0.9 * strength)
    k2 = nb.mul(nb.mul(fade(nb, 60.0, 900.0), nb.madd(mask, 0.6, 0.4)), 0.8 * strength)
    a1 = nb.vmath('SUBTRACT', nb.vmath('SCALE', n1, scale=2.0), (1, 1, 1))
    a2 = nb.vmath('SUBTRACT', nb.vmath('SCALE', n2, scale=2.0), (1, 1, 1))
    a1x, a1y, _ = nb.sep(a1); a2x, a2y, _ = nb.sep(a2)
    px = nb.add(nb.mul(a1x, k1), nb.mul(a2x, k2)); py = nb.add(nb.mul(a1y, k1), nb.mul(a2y, k2))
    Np = nb.vmath('NORMALIZE', nb.vmath('ADD', geo.outputs['Normal'], nb.comb(px, py, 0.0)))
    # wind ripples: 0.35 m bands, direction warped by noise, fade 5..90 m
    rot = nb.N.new('ShaderNodeVectorRotate'); rot.rotation_type = 'Z_AXIS'
    nb._in(rot.inputs['Vector'], p2)
    nb._in(rot.inputs['Angle'], nb.madd(nb.noise(nb.vmath('SCALE', p2, scale=1 / 35.0), 1.0, 1.0, 0.5), 1.6, 0.2))
    wv = nb.N.new('ShaderNodeTexWave'); wv.wave_type = 'BANDS'; wv.bands_direction = 'X'; wv.wave_profile = 'SIN'
    nb._in(wv.inputs['Vector'], rot.outputs[0])
    wv.inputs['Scale'].default_value = 1.8; wv.inputs['Distortion'].default_value = 2.0
    wv.inputs['Detail'].default_value = 1.5; wv.inputs['Detail Scale'].default_value = 1.0
    wfac = wv.outputs['Fac'] if 'Fac' in wv.outputs else wv.outputs['Factor']
    bump = nb.N.new('ShaderNodeBump')
    bump.inputs['Distance'].default_value = 0.04
    nb._in(bump.inputs['Strength'], nb.mul(fade(nb, 5.0, 150.0), 0.5 * strength))
    nb._in(bump.inputs['Height'], wfac)
    nb._in(bump.inputs['Normal'], Np)
    return bump.outputs['Normal']


def m_sand():
    m = bpy.data.materials.new('M_Sand'); m.use_nodes = True
    nt = m.node_tree; nb = NB(nt)
    bsdf = nt.nodes['Principled BSDF']
    tc = nb.N.new('ShaderNodeTexCoord')
    p = tc.outputs['Object']
    x, y, z = nb.sep(p)
    r = nb.math('SQRT', nb.add(nb.mul(x, x), nb.mul(y, y)))
    th = nb.math('ARCTAN2', y, x)
    # ---------- pre: marble sand
    V = _marble_vec(nb, p)
    f = ND.build_marble_field(nt, V, scale=1.0, freq=marble_mapping()[3])
    hs = nb.N.new('ShaderNodeHueSaturation')
    hs.inputs['Saturation'].default_value = 0.97; hs.inputs['Value'].default_value = 0.9
    nb._in(hs.inputs['Color'], f['color'])
    pre = hs.outputs['Color']
    pre = nb.mixc(nb.mul(f['vein'], 0.8), pre, ND.lin('chalk'))
    prof = dune_profile(nb, f['m'])
    pre = nb.mixc(1.0, pre, nb.comb(*(nb.madd(prof, 0.16, 0.84),) * 3), 'MULTIPLY')
    pre = nb.mixc(nb.ss(1150, 1198, r), pre, ND.lin('outer_sand'))
    # ---------- post: analytic record
    win = nb.mul(nb.ss(R_GROOVE0, R_GROOVE0 + 25, r), nb.sub(1.0, nb.ss(R_GROOVE1 - 25, R_GROOVE1, r)))
    rr = nb.add(r, nb.mul(nb.mul(nb.math('COSINE', nb.mul(th, 16.0)), 2.5), win))
    xg = nb.mul(nb.sub(rr, R_GROOVE0), math.pi / RING_PITCH)
    sn = nb.math('SINE', xg)
    s = nb.sub(nb.math('SQRT', nb.add(nb.mul(sn, sn), 0.04)), 0.2)
    c = nb.math('DIVIDE', s, math.sqrt(1.04) - 0.2)
    c = nb.math('SUBTRACT', 1.0, c, clamp=True)
    crest = nb.mul(nb.math('POWER', c, 1.4), win)
    cw = nb.mul(c, win)
    # magenta troughs -> saffron flanks/crests (>=30 % of the band) -> broad chalk crest line (~5 m)
    post = nb.mixc(nb.ss(0.10, 0.30, cw), nb.mixc(0.35, ND.lin('magenta'), ND.lin('violet')), ND.lin('magenta'))
    post = nb.mixc(nb.ss(0.35, 0.60, cw), post, ND.lin('saffron'))
    post = nb.mixc(nb.ss(0.96, 0.985, cw), post, ND.lin('chalk'))          # adr2: narrow chalk line (was 0.935-0.972)
    # spokes: broad converging rays (constant angular width): magenta halo, ultramarine core
    c8 = nb.math('COSINE', nb.mul(th, 8.0))
    c8n = nb.div(c8, SPOKE_W)
    spc = nb.mul(nb.math('EXPONENT', nb.mul(nb.mul(c8n, c8n), -0.45)), win)
    post = nb.mixc(nb.ss(0.18, 0.45, spc), post, ND.lin('magenta'))
    post = nb.mixc(nb.ss(0.62, 0.85, spc), post, ND.lin('ultramarine'))
    # lead-in land: deep ultramarine run-out band; trench: strata by depth
    lead = nb.mul(nb.ss(1156, 1161, r), nb.sub(1.0, nb.ss(1169, 1172, r)))
    post = nb.mixc(lead, post, tuple(v * 0.55 for v in ND.lin('ultramarine')))
    strata = nb.ramp(nb.math('FRACT', nb.mul(z, 1 / 9.0)), [
        (0.0, ND.lin('mesa_rock')), (0.3, ND.lin('cream')), (0.5, ND.lin('plum')), (0.75, ND.lin('mesa_rock'))], 'CONSTANT')
    trench = nb.mul(nb.ss(1169, 1172, r), nb.sub(1.0, nb.ss(1199.0, 1200.5, r)))
    post = nb.mixc(trench, post, strata)
    morph = nb.attr('morph')
    col = nb.mixc(morph, pre, post)
    # ---------- label mesa (both states): saffron paper, terraces with vermilion strata, night crater
    lab_strata = nb.ramp(nb.math('FRACT', nb.mul(z, 1 / 6.5)), [
        (0.0, ND.lin('saffron')), (0.55, ND.lin('vermilion')), (0.7, ND.lin('saffron'))], 'CONSTANT')
    lab_strata = nb.ramp(nb.math('FRACT', nb.mul(z, 1 / 7.0)), [
        (0.0, ND.lin('vermilion')), (0.3, ND.lin('saffron')), (0.55, ND.lin('plum')), (0.72, ND.lin('vermilion'))], 'CONSTANT')
    lab = nb.mixc(nb.ss(233, 236, r), ND.lin('saffron'), lab_strata)
    # darker bevelled lip on the top edge, terraces read as stepped strata from above
    lab = nb.mixc(nb.mul(nb.ss(222, 230, r), nb.ss(236, 231, r)), lab, tuple(v * 0.55 for v in ND.lin('vermilion')))
    lab = nb.mixc(nb.ss(CRATER_R + 2.0, CRATER_R - 6.0, r), lab, ND.lin('night'))
    lab = nb.mixc(nb.mul(nb.ss(CRATER_R + 1.0, CRATER_R + 4.0, r), nb.ss(CRATER_R + 10.0, CRATER_R + 6.0, r)), lab, ND.lin('chalk'))
    lab_mask = nb.ss(266, 258, r)
    col = nb.mixc(lab_mask, col, lab)
    # kick ring dust tint
    kick = nb.attr('kick')
    kmask = nb.ss(0.4, 0.95, kick)
    col = nb.mixc(nb.mul(kmask, 0.6), col, (1.0, 0.62, 0.22))
    hopv = nb.attr('hop')
    col = nb.mixc(nb.math('MULTIPLY', hopv, 0.07, clamp=True), col, (1.0, 0.55, 0.12))
    nb.L.new(col, bsdf.inputs['Base Color'])
    # pulse glow on crests (post only)
    zone_ = nb.attr('zone')
    pulse = None
    for i in range(8):
        cmpv = nb.math('COMPARE', zone_, float(i), 0.5)
        term = nb.mul(cmpv, nb.value(0.0, f'sb{i}'))
        pulse = term if pulse is None else nb.add(pulse, term)
    pulse = nb.mul(pulse, nb.value(0.0, 'spa'))
    glow = nb.mul(nb.mul(nb.ss(0.80, 0.97, crest), pulse), morph)
    ecol = nb.mixc(nb.ss(0.93, 0.99, crest), ND.lin('saffron'), ND.lin('chalk'))
    labtop = nb.mul(nb.ss(243.0, 238.0, r), nb.ss(24.0, 28.0, r))   # label paper glows a touch: Saffron Pop reads at grazing sun
    ecol = nb.mixc(nb.math('MAXIMUM', kmask, labtop), ecol, ND.lin('saffron'))
    # the drop's shock crest: the leaping sand wave glows like a racing ring of light (energy of the needle drop)
    hm = nb.ss(0.80, 0.97, nb.mul(hopv, 1.0 / HOP_H))
    ecol = nb.mixc(hm, ecol, C.hex2lin('#FFC870'))
    nb.L.new(ecol, bsdf.inputs['Emission Color'])
    # adr2: crest pulse glow 3.5 -> 0.8 so the disc reads as sculpted sand, not a neon vector graphic
    nb.L.new(nb.add(nb.add(nb.add(nb.mul(glow, 0.8), nb.mul(kmask, 0.7)), nb.mul(labtop, 0.22)), nb.mul(hm, 0.9)), bsdf.inputs['Emission Strength'])
    # adr2: keyed hot rings on the sand: (1) the f433 DROP flash at the label-mesa base, (2) the touchdown shock ring
    # racing out from L across the ridges toward the S6 lens (world space: the disc spins at 29 s)
    gpos = nb.N.new('ShaderNodeNewGeometry').outputs['Position']
    gx, gy, _ = nb.sep(gpos)
    Lx, Ly, _ = pol(*L_LAND)
    dl = nb.math('SQRT', nb.add(nb.mul(nb.sub(gx, Lx), nb.sub(gx, Lx)), nb.mul(nb.sub(gy, Ly), nb.sub(gy, Ly))))
    td_r = nb.value(0.0, 'td_r'); td_e = nb.value(0.0, 'td_e'); fl = nb.value(0.0, 'flash433')
    td_r.node.name = 'td_r'; td_e.node.name = 'td_e'; fl.node.name = 'flash433'
    edge = nb.mul(nb.ss(-26.0, 0.0, nb.sub(dl, td_r)), nb.ss(6.0, 0.0, nb.sub(dl, td_r)))    # hot leading edge, soft trailing glow
    tde = nb.mul(nb.mul(edge, td_e), nb.madd(crest, 0.6, 0.4))
    emx = nb.N.new('ShaderNodeEmission'); emx.inputs['Color'].default_value = (*C.hex2lin('#FFC870'), 1.0)
    nb._in(emx.inputs['Strength'], tde)
    # scfix: the f433 DROP flash is a thin saturated shockwave racing out over the sand (keyed radius 'flash_r'):
    # hot saffron-orange leading line + magenta wake, masked off the label-mesa walls (they read as a white UFO disc)
    flr = nb.value(272.0, 'flash_r')
    dfl = nb.sub(r, flr)
    lead = nb.mul(nb.ss(-18.0, 0.0, dfl), nb.ss(6.0, 0.0, dfl))           # ~20 m hot line (grazing view needs width)
    trail = nb.mul(nb.ss(-95.0, -22.0, dfl), nb.ss(0.0, -20.0, dfl))      # ~80 m magenta wake
    offm = nb.mul(nb.ss(256.0, 266.0, r), fl)
    efl = nb.N.new('ShaderNodeEmission'); efl.inputs['Color'].default_value = (*C.hex2lin('#FF8A12'), 1.0)
    nb._in(efl.inputs['Strength'], nb.mul(lead, offm))
    emg = nb.N.new('ShaderNodeEmission'); emg.inputs['Color'].default_value = (*ND.lin('magenta'), 1.0)
    nb._in(emg.inputs['Strength'], nb.mul(nb.mul(trail, offm), 0.7))
    outn = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL')
    adds = nb.N.new('ShaderNodeAddShader')
    nt.links.new(bsdf.outputs[0], adds.inputs[0]); nt.links.new(emx.outputs[0], adds.inputs[1])
    add2 = nb.N.new('ShaderNodeAddShader')
    nt.links.new(efl.outputs[0], add2.inputs[0]); nt.links.new(emg.outputs[0], add2.inputs[1])
    add3 = nb.N.new('ShaderNodeAddShader')
    nt.links.new(adds.outputs[0], add3.inputs[0]); nt.links.new(add2.outputs[0], add3.inputs[1])
    nt.links.new(add3.outputs[0], outn.inputs['Surface'])
    rough = nb.mixc(lab_mask, (0.95, 0.95, 0.95), (0.6, 0.6, 0.6))
    nb.L.new(nb.sep(rough)[0], bsdf.inputs['Roughness'])
    bsdf.inputs['Sheen Weight'].default_value = 0.12
    bsdf.inputs['Sheen Tint'].default_value = (1.0, 0.8, 0.9, 1.0)
    bsdf.inputs['Specular IOR Level'].default_value = 0.08
    nb.L.new(sand_normal(nb, p), bsdf.inputs['Normal'])
    return m


def m_outer_sand():
    m = bpy.data.materials.new('M_OuterSand'); m.use_nodes = True
    nt = m.node_tree; nb = NB(nt)
    bsdf = nt.nodes['Principled BSDF']
    tc = nb.N.new('ShaderNodeTexCoord'); p = tc.outputs['Object']
    x, y, z = nb.sep(p)
    p2 = nb.comb(x, y, 0.0)
    n = nb.noise(nb.vmath('SCALE', p2, scale=1 / 90.0), 1.0, 4.0, 0.6)
    v = nb.madd(n, 0.16, 0.92)
    base = ND.lin('outer_sand')
    col = nb.mixc(1.0, base, nb.comb(v, v, v), 'MULTIPLY')
    # crest lightening, trough rose-violet shading (sorting)
    col = nb.mixc(nb.ss(2.0, 9.0, z), nb.mixc(nb.mul(nb.ss(1.0, -6.0, z), 0.8), col, tuple(v * 0.75 for v in ND.lin('outer_sand'))), ND.lin('apricot'))      # adr2: saturated crests, not pale peach
    nb.L.new(col, bsdf.inputs['Base Color'])
    bsdf.inputs['Roughness'].default_value = 0.9
    bsdf.inputs['Sheen Weight'].default_value = 0.12
    bsdf.inputs['Specular IOR Level'].default_value = 0.15
    nb.L.new(sand_normal(nb, p), bsdf.inputs['Normal'])
    return m


# ---------------------------------------------------------------- build
def build(coll):
    t0 = time.time()
    # ---- disc
    radii, nsegs = polar_rings([(10, 0.6, 100), (60, 0.6, 400), (300, 0.75, 1200), (1150, 1.5, 3600), (1200, 0.75, 3600)])
    co, tris, offs = build_polar(radii, nsegs, centre=True)
    x, y = co[:, 0], co[:, 1]
    r = np.hypot(x, y); th = np.arctan2(y, x)
    hrec, hcrest, zone = h_record(x, y)
    inpatch = (r > PATCH_R[0] + 0.5) & (r < PATCH_R[1] - 0.5) & (np.abs(np.degrees(th)) < PATCH_TH - 0.05)
    me = make_mesh('RecordDisc', co, 0.0, tris)
    disc = bpy.data.objects.new('RecordDisc', me); coll.objects.link(disc)
    print(f'disc verts {len(co)} tris {len(tris)}  {time.time()-t0:.1f}s', flush=True)
    # ---- patch (polar sector, with 2 m skirts)
    nr = int(round((PATCH_R[1] - PATCH_R[0]) / PATCH_DR))
    rad = np.linspace(PATCH_R[0], PATCH_R[1], nr + 1)
    nt_ = int(round(math.radians(2 * PATCH_TH) * 1070 / PATCH_DR))
    ths = np.radians(np.linspace(-PATCH_TH, PATCH_TH, nt_ + 1))
    radx = np.concatenate([[rad[0]], rad, [rad[-1]]]); thx = np.concatenate([[ths[0]], ths, [ths[-1]]])
    RR, TT = np.meshgrid(radx, thx, indexing='ij')
    pco = np.stack([RR * np.cos(TT), RR * np.sin(TT)], -1).reshape(-1, 2)
    I, J = len(radx), len(thx)
    skirt = np.zeros((I, J)); skirt[0, :] = skirt[-1, :] = skirt[:, 0] = skirt[:, -1] = 2.0
    ii, jj = np.meshgrid(np.arange(I - 1), np.arange(J - 1), indexing='ij')
    a = (ii * J + jj).ravel(); b = ((ii + 1) * J + jj).ravel(); c_ = ((ii + 1) * J + jj + 1).ravel(); d = (ii * J + jj + 1).ravel()
    ptris = np.concatenate([np.stack([a, b, c_], 1), np.stack([a, c_, d], 1)]).astype(np.int32)
    pme = make_mesh('RecordPatch', pco, 0.0, ptris)
    sk = skirt.ravel() > 0
    sf = pme.attributes.new('sharp_face', 'BOOLEAN', 'FACE')
    sf.data.foreach_set('value', sk[ptris].any(axis=1))
    patch = bpy.data.objects.new('RecordPatch', pme); coll.objects.link(patch)
    print(f'patch verts {len(pco)}  {time.time()-t0:.1f}s', flush=True)
    # ---- bake marble dunes on both
    bng = bake_group()
    hb_d = bake_dunes(disc, bng)
    hb_p = bake_dunes(patch, bng)
    print(f'baked dunes {time.time()-t0:.1f}s', flush=True)
    hdune = label_mesa(r) + hb_d * dune_weight(r)
    px, py = pco[:, 0], pco[:, 1]; pr = np.hypot(px, py)
    p_hrec, p_hcrest, p_zone = h_record(px, py)
    p_hdune = label_mesa(pr) + hb_p * dune_weight(pr)
    for o, mesh, rr_, hd, hr, hc, zn, pl in ((disc, me, r, hdune, hrec, hcrest, zone, np.where(inpatch, 0.15, 0.0)),
                                              (patch, pme, pr, p_hdune, p_hrec, p_hcrest, p_zone, skirt.ravel())):
        set_attr(mesh, 'r', rr_); set_attr(mesh, 'h_dune', hd); set_attr(mesh, 'h_rec', hr)
        set_attr(mesh, 'h_crest', hc); set_attr(mesh, 'zone', zn, 'INT'); set_attr(mesh, 'patch_lower', pl)
        cov = np.zeros(len(mesh.vertices) * 3, np.float32); mesh.vertices.foreach_get('co', cov)
        cov = cov.reshape(-1, 3); cov[:, 2] = hd - pl; mesh.vertices.foreach_set('co', cov.ravel()); mesh.update()
    bpy.data.node_groups.remove(bng)
    live = live_group()
    for o in (disc, patch):
        md = o.modifiers.new('RecordLive', 'NODES'); md.node_group = live
    ms = m_sand()
    me.materials.append(ms); pme.materials.append(ms)
    patch.parent = disc
    # adr2 budget: from f517 the morph is 1 everywhere -> a STATIC copy of the disc with the record heights baked
    # (no per-frame GN on 3.6M verts); parented to the disc so it spins with it
    sme = me.copy(); sme.name = 'RecordStatic'
    for a in ('h_dune', 'h_rec', 'h_crest', 'patch_lower', 'r'):
        if a in sme.attributes:
            sme.attributes.remove(sme.attributes[a])
    cov = np.zeros(len(sme.vertices) * 3, np.float32); sme.vertices.foreach_get('co', cov)
    cov = cov.reshape(-1, 3); cov[:, 2] = hrec - np.where(inpatch, 0.15, 0.0)
    sme.vertices.foreach_set('co', cov.ravel())
    set_attr(sme, 'morph', np.ones(len(cov), np.float32))
    sme.update()
    static = bpy.data.objects.new('RecordStatic', sme); coll.objects.link(static)
    static.parent = disc
    disc['static'] = static.name
    # ---- outer desert
    rads = [R_RIM]; dr = 0.75
    while rads[-1] < 9000:
        rr_ = rads[-1]
        dr = min(30.0, max(0.75, 1.0 * (rr_ / 1200.0) ** 3.0)) if rr_ > 1215 else 0.75
        rads.append(rr_ + dr)
    rads = np.array(rads)
    segs = np.where(rads < 1215, 3600, np.where(rads < 2600, 1800, np.where(rads < 5000, 900, 450)))
    oco, otris, _ = build_polar(rads, segs, centre=False)
    oh = outer_height(oco[:, 0], oco[:, 1])
    ome = make_mesh('OuterDesert', oco, oh, otris)
    outer = bpy.data.objects.new('OuterDesert', ome); coll.objects.link(outer)
    ome.materials.append(m_outer_sand())
    print(f'outer verts {len(oco)}  {time.time()-t0:.1f}s', flush=True)
    # sampling helpers for props/fx/cameras (pre-drop ground)
    ground = {'patch': (rad, ths, p_hdune.reshape(I, J)[1:-1, 1:-1]),
              'disc': (radii, nsegs, offs, hdune)}
    return disc, patch, outer, live, ground


def ground_h(ground, x, y):
    """Pre-drop ground height at world points (nearest-vertex on patch, else disc, else outer)."""
    x = np.asarray(x, float); y = np.asarray(y, float)
    r = np.hypot(x, y); th = np.arctan2(y, x)
    out = outer_height(x, y)
    radii, nsegs, offs, hd = ground['disc']
    ri = np.clip(np.searchsorted(radii, r), 0, len(radii) - 1)
    ri = np.where((ri > 0) & (np.abs(radii[np.maximum(ri - 1, 0)] - r) < np.abs(radii[ri] - r)), ri - 1, ri)
    ns = nsegs[ri]; offs = np.asarray(offs)
    si = np.round((th % (2 * np.pi)) / (2 * np.pi) * ns).astype(np.int64) % ns
    hdisc = hd[offs[ri] + si]
    rad, ths, hp = ground['patch']
    inp = (r > rad[0]) & (r < rad[-1]) & (np.abs(th) < ths[-1])
    # bilinear on the patch
    fr = np.clip((r - rad[0]) / (rad[1] - rad[0]), 0, len(rad) - 1.001)
    ft = np.clip((th - ths[0]) / (ths[1] - ths[0]), 0, len(ths) - 1.001)
    i0 = fr.astype(int); j0 = ft.astype(int); di = fr - i0; dj = ft - j0
    hpv = (hp[i0, j0] * (1 - di) * (1 - dj) + hp[i0 + 1, j0] * di * (1 - dj) + hp[i0, j0 + 1] * (1 - di) * dj + hp[i0 + 1, j0 + 1] * di * dj)
    return np.where(r < R_RIM, np.where(inp, hpv, hdisc), out)
