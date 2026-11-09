"""Mesas, far plane, label lettering, quiver trees, boulders, tonearm (asset or placeholder) for Set C."""
import bpy, math, os
import numpy as np
from mathutils import Vector, Matrix
from c_common import *
from c_nodes import NB
from c_terrain import outer_height, make_mesh, ground_h, build_polar, TEX

MODELS = os.path.join(ROOT, 'assets', 'c')
SHORT = {'quiver_tree_01': 'q1', 'quiver_tree_02': 'q2', 'dead_quiver_trunk': 'dq', 'namaqualand_boulder_02': 'b2', 'namaqualand_boulder_03': 'b3', 'namaqualand_boulder_04': 'b4'}


# ---------------------------------------------------------------- mesas
def mesa_mesh(name, seed, H, R0, tiers):
    rng = np.random.RandomState(seed)
    # lathe profile (radius factor, z)
    za = 0.30 * H                                   # talus apron top
    run = za / math.tan(math.radians(31.0)) / R0    # 31 deg scree slope
    prof = [(1.0 + run + 0.10, -8.0), (1.0 + run * 0.55, 0.12 * za), (1.06, 0.85 * za), (1.01, za)]
    fr = np.sort(rng.uniform(0.55, 0.75, tiers - 1)); zs = list(fr * H) + [H]
    sc = [1.0]
    for i in range(tiers - 1):
        sc.append(sc[-1] * rng.uniform(0.84, 0.92))
    z0 = za
    for j in range(tiers):
        top = zs[j] - (5.0 if j == tiers - 1 else 0.0)
        hh = top - z0
        prof += [(sc[j] * 0.995, z0 + 0.15 * hh), (sc[j] * 0.95, top - 1.0)]          # ~80 deg eroded cliff
        if j < tiers - 1:
            ledge = sc[j + 1] + 0.035
            prof += [(sc[j] * 0.935, top), (ledge + 0.06, top + 3.0), (ledge, top + 6.0)]
            z0 = top + 6.0
    cap = sc[-1] * 1.04
    prof += [(sc[-1] * 0.95, H - 5.5), (cap, H - 4.0), (cap, H - 0.6), (cap * 0.985, H + 0.4)]
    P = np.array(prof)
    seg = np.sqrt(np.diff(P[:, 0] * R0) ** 2 + np.diff(P[:, 1]) ** 2)
    s = np.concatenate([[0], np.cumsum(seg)])
    ss_ = np.linspace(0, s[-1], int(s[-1] / 1.8) + 2)
    pr = np.interp(ss_, s, P[:, 0]); pz = np.interp(ss_, s, P[:, 1])
    na = 192
    th = np.arange(na) * 2 * np.pi / na
    outline = 1 + rng.uniform(0.15, 0.35) * np.cos(2 * (th - rng.uniform(0, 3)))
    for k in range(3, 9):
        outline += rng.uniform(0.03, 0.10) / math.sqrt(k) * np.cos(k * th + rng.uniform(0, 6.28))
    gul = np.zeros((len(pz), na))
    for m in range(9, 48, 3):
        ph = rng.uniform(0, 6.28); amp = 32.0 / m ** 0.75
        gul += amp * np.cos(m * th[None, :] + ph + 0.06 * pz[:, None] * rng.uniform(-1, 1))
    gul *= (0.7 + 0.3 * np.sin(pz[:, None] / 9.0 + th[None, :] * 2))
    gul = -np.abs(gul) * 0.9 + 0.35 * gul               # V-gullies cut in, rounded buttresses between
    # irregular caprock overhang
    capn = 1.0 + 0.06 * np.cos(5 * th + rng.uniform(0, 6.28)) + 0.04 * np.cos(11 * th + rng.uniform(0, 6.28))
    gul = gul + (pz[:, None] > H - 4.5) * (capn[None, :] - 1.0) * R0
    wob = np.ones((len(pz), na))
    for k in (3, 5, 7):
        wob += 0.05 * np.sin(k * th[None, :] + rng.uniform(0, 6.28) + pz[:, None] / rng.uniform(15, 40))
    Rm = R0 * pr[:, None] * outline[None, :] * wob + gul * np.clip((pz[:, None] + 8.0) / (0.30 * H), 0.25, 1.0)
    X = Rm * np.cos(th)[None, :]; Y = Rm * np.sin(th)[None, :]
    Z = np.repeat(pz[:, None], na, 1) + 0.6 * np.sin(th[None, :] * 7 + pz[:, None])
    nr = len(pz)
    co = np.stack([X.ravel(), Y.ravel()], 1)
    z = Z.ravel()
    # top centre
    co = np.vstack([co, [[0, 0]]]); z = np.concatenate([z, [H + 0.8]])
    ii, jj = np.meshgrid(np.arange(nr - 1), np.arange(na), indexing='ij')
    a = ii * na + jj; b = ii * na + (jj + 1) % na; c = (ii + 1) * na + (jj + 1) % na; d = (ii + 1) * na + jj
    tris = np.concatenate([np.stack([a.ravel(), b.ravel(), c.ravel()], 1), np.stack([a.ravel(), c.ravel(), d.ravel()], 1)])
    top0 = (nr - 1) * na; j = np.arange(na)
    tris = np.concatenate([tris, np.stack([top0 + j, top0 + (j + 1) % na, np.full(na, nr * na)], 1)]).astype(np.int32)
    return make_mesh(name, co, z, tris)


def m_mesa():
    m = bpy.data.materials.new('M_Mesa'); m.use_nodes = True
    nt = m.node_tree; nb = NB(nt)
    b = nt.nodes['Principled BSDF']
    geo = nb.N.new('ShaderNodeNewGeometry')
    tc = nb.N.new('ShaderNodeTexCoord')
    wx, wy, wz = nb.sep(geo.outputs['Position'])
    n = nb.noise(nb.vmath('SCALE', nb.comb(wx, wy, 0.0), scale=1 / 80.0), 1.0, 2.0, 0.5)
    # adr2: strata coordinate warped at two scales (no layer cake): big 1/80 sway + 1/8 m 3D chatter
    n3 = nb.noise(nb.vmath('SCALE', geo.outputs['Position'], scale=1 / 8.0), 1.0, 3.0, 0.6)
    zz = nb.add(nb.add(wz, nb.mul(nb.sub(n, 0.5), 36.0)), nb.add(nb.mul(wx, 0.052), nb.mul(wy, 0.021)))
    zz = nb.add(zz, nb.mul(nb.sub(n3, 0.5), 7.0))
    strata = nb.ramp(nb.math('FRACT', nb.mul(zz, 1 / 61.0)), [
        (0.00, C.hex2lin('#C8321E')), (0.10, C.hex2lin('#E8895A')), (0.15, C.hex2lin('#C8321E')),
        (0.33, C.hex2lin('#55174A')), (0.42, C.hex2lin('#D9452A')), (0.58, C.hex2lin('#F09A60')),
        (0.63, C.hex2lin('#FF3A1C')), (0.80, C.hex2lin('#55174A')), (0.86, C.hex2lin('#C8321E'))], 'CONSTANT')
    # thin uneven sub-bands (second, independent warp) modulate value so band thickness varies
    n4 = nb.noise(nb.vmath('SCALE', nb.comb(wx, wy, 0.0), scale=1 / 60.0), 1.0, 2.0, 0.5)
    fine = nb.math('FRACT', nb.add(nb.add(nb.mul(wz, 1 / 9.0), nb.mul(n4, 0.9)), nb.mul(n3, 0.3)))
    fm = nb.ramp(fine, [(0.0, (1.0, 1.0, 1.0)), (0.42, (0.80, 0.78, 0.82)), (0.5, (1.07, 1.04, 1.0)), (0.78, (0.9, 0.88, 0.92))], 'CONSTANT')
    strata = nb.mixc(1.0, strata, fm, 'MULTIPLY')
    vec = nb.vmath('SCALE', tc.outputs['Object'], scale=1 / 6.0)
    ao = nb.N.new('ShaderNodeTexImage'); ao.image = bpy.data.images.load(os.path.join(TEX, 'rock_ao.jpg'))
    ao.image.colorspace_settings.name = 'Non-Color'; ao.projection = 'BOX'; ao.projection_blend = 0.2
    nb._in(ao.inputs['Vector'], vec)
    aov = nb.sep(ao.outputs['Color'])[0]
    col = nb.mixc(0.85, strata, nb.mixc(1.0, strata, ao.outputs['Color'], 'MULTIPLY'))
    _, _, nz = nb.sep(geo.outputs['Normal'])
    top = nb.ss(0.72, 0.9, nz)
    col = nb.mixc(nb.mul(top, 0.7), col, C.hex2lin('#F0B48A'))
    col = nb.mixc(nb.ss(9.0, 1.0, wz), col, ND.lin('outer_sand'))
    nb.L.new(col, b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.86
    b.inputs['Specular IOR Level'].default_value = 0.3
    cr = nb.N.new('ShaderNodeTexImage'); cr.image = bpy.data.images.load(os.path.join(TEX, 'crack_ao.jpg'))
    cr.image.colorspace_settings.name = 'Non-Color'
    nb._in(cr.inputs['Vector'], nb.vmath('SCALE', tc.outputs['Object'], scale=1 / 8.0))
    big = nb.noise(nb.vmath('SCALE', tc.outputs['Object'], scale=1 / 14.0), 1.0, 5.0, 0.6)
    h = nb.add(nb.add(aov, nb.mul(big, 1.4)), nb.mul(nb.sep(cr.outputs['Color'])[0], nb.mul(top, 0.8)))
    h = nb.add(h, nb.mul(nb.ss(0.4, 0.5, fine), 0.9))          # adr2: chipped ledge on each sub-band
    bump = nb.N.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.65; bump.inputs['Distance'].default_value = 0.8
    nb._in(bump.inputs['Height'], h)
    nb.L.new(bump.outputs['Normal'], b.inputs['Normal'])
    return m


def mesas(coll):
    mat = m_mesa()
    rng = np.random.RandomState(11)
    meshes = []
    for i in range(6):
        me = mesa_mesh(f'MesaMesh_{i}', 100 + i, H=rng.uniform(80, 170), R0=rng.uniform(70, 150), tiers=1 + (i % 2))
        me.materials.append(mat); meshes.append(me)
    bearings = [-38, -14, 9, 27, 50, 74, 96, 116, 178, 203, 228, 258, 292, 322]
    radii = [2050, 1680, 2350, 1820, 2500, 1900, 3900, 3500, 2400, 1750, 2150, 2550, 1700, 2300]
    big = {6: 2.1, 7: 1.9}
    objs = []
    for k, (bd, rr) in enumerate(zip(bearings, radii)):
        o = bpy.data.objects.new(f'Mesa_{k:02d}', meshes[k % 6]); coll.objects.link(o)
        x, y, _ = pol(rr, bd)
        o.location = (x, y, float(outer_height(np.array([x]), np.array([y]))[0]) - 6.0)
        s = rng.uniform(0.75, 1.25) * big.get(k, 1.0)
        o.scale = (s, s * rng.uniform(0.85, 1.15), rng.uniform(0.8, 1.2) * big.get(k, 1.0))
        o.rotation_euler.z = rng.uniform(0, 6.28)
        objs.append(o)
    return objs


def far_plane(coll):
    radii = np.array([8990.0, 20000.0, 90000.0]); segs = np.array([450, 450, 450])
    co, tris, _ = build_polar(radii, segs, centre=False)
    me = make_mesh('FarPlane', co, -3.0, tris)
    m = bpy.data.materials.new('M_Horizon'); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*ND.lin('outer_sand'), 1)
    b.inputs['Roughness'].default_value = 0.95
    b.inputs['Emission Color'].default_value = (*C.hex2lin('#FF9A5A'), 1)
    b.inputs['Emission Strength'].default_value = 0.35
    me.materials.append(m)
    o = bpy.data.objects.new('FarPlane', me); coll.objects.link(o)
    o.visible_shadow = False
    return o


# ---------------------------------------------------------------- label lettering
def _text_mesh(name, body, size, align='CENTER', extrude=0.3):
    font = bpy.data.fonts.get('ariblk.ttf') or bpy.data.fonts.load('C:/Windows/Fonts/ariblk.ttf')
    cu = bpy.data.curves.new(name, 'FONT'); cu.body = body; cu.font = font
    cu.size = size; cu.align_x = align; cu.align_y = 'CENTER'; cu.extrude = extrude; cu.resolution_u = 6
    ob = bpy.data.objects.new(name + '_tmp', cu); bpy.context.scene.collection.objects.link(ob)
    dg = bpy.context.evaluated_depsgraph_get(); dg.update()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    bpy.data.objects.remove(ob); bpy.data.curves.remove(cu)
    me.name = name
    return me


def label_text(coll, disc):
    """S2's label typography scaled to the 240 m label mesa (k = 240/0.0499): NEEDLE over DROP, ring text wrapped at
    0.81 R, magenta print rings at 0.94 R and 0.705 R. Cap height 1.2x S2's (~40 m) so it reads >= 35 px in S5."""
    ink = ND.simple('M_Ink', 'night', rough=0.3)
    inkm = ND.simple('M_InkMagenta', 'magenta', rough=0.35)
    K = R_LABEL / 0.0499
    cap = 0.007 * K * 1.2
    objs = []
    for body, yy in (('NEEDLE', 0.0195 * K), ('DROP', -0.0195 * K)):
        me = _text_mesh('Txt_' + body, body, cap / 0.716)
        me.materials.clear(); me.materials.append(ink)
        o = bpy.data.objects.new('Label_' + body, me); coll.objects.link(o)
        o.location = (0, yy, MESA_H - 0.1); o.parent = disc
        objs.append(o)
    # ring text (SIDE B instead of S2's SIDE A), wrapped around r = 0.81 R
    rme = _text_mesh('Txt_Ring', 'SIDE B \u00b7 33 1/3 RPM \u00b7 STEREO \u00b7 SIDE B \u00b7 33 1/3 RPM \u00b7 STEREO \u00b7 ', 1.0, align='LEFT', extrude=0.3)
    co = np.empty(len(rme.vertices) * 3); rme.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
    RR = 0.81 * R_LABEL
    xmin, xmax = co[:, 0].min(), co[:, 0].max()
    k = (2 * math.pi * RR * 0.985) / (xmax - xmin)
    x = (co[:, 0] - xmin) * k; yv = co[:, 1] * k
    ang = math.pi / 2 - x / RR
    rad = RR + yv - 0.0012 * K
    co2 = np.stack([rad * np.cos(ang), rad * np.sin(ang), co[:, 2] * 1.0], 1)
    rme.vertices.foreach_set('co', co2.ravel()); rme.update()
    rme.materials.clear(); rme.materials.append(ink)
    o = bpy.data.objects.new('Label_RingText', rme); coll.objects.link(o)
    o.location = (0, 0, MESA_H - 0.1); o.parent = disc; objs.append(o)
    print('LABEL ring text scale', k, 'cap', cap)
    for rr, w in ((0.0468, 0.0007), (0.0352, 0.0005)):
        r0 = rr * K; w_ = w * K
        co, tris, _ = build_polar(np.array([r0, r0 + w_]), np.array([720, 720]), centre=False)
        me = make_mesh(f'LabelRing_{int(r0)}', co, MESA_H + 0.12, tris); me.materials.append(inkm)
        o = bpy.data.objects.new(f'LabelRing_{int(r0)}', me); coll.objects.link(o); o.parent = disc
        objs.append(o)
    return objs


# ---------------------------------------------------------------- Poly Haven models
def load_model(slug, ratio=1.0):
    d = os.path.join(MODELS, SHORT.get(slug, slug))
    blends = [f for f in os.listdir(d) if f.endswith('.blend')] if os.path.isdir(d) else []
    if not blends:
        return None
    path = os.path.join(d, blends[0])
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        dst.objects = list(src.objects)
    objs = [o for o in dst.objects if o is not None and o.type == 'MESH']
    col = bpy.data.collections.new('SRC_' + slug)
    for o in objs:
        col.objects.link(o)
        o.location = (0, 0, 0) if o.parent is None else o.location
    if ratio < 1.0:   # decimate heavy scan meshes (instanced many times, seen from >30 m)
        sc = bpy.context.scene
        sc.collection.children.link(col)
        for o in objs:
            if len(o.data.polygons) * ratio < 400:
                continue
            md = o.modifiers.new('dec', 'DECIMATE'); md.ratio = ratio
        dg = bpy.context.evaluated_depsgraph_get(); dg.update()
        for o in objs:
            if o.modifiers:
                me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
                o.modifiers.clear(); old = o.data; o.data = me
        sc.collection.children.unlink(col)
        print('DECIMATED', slug, sum(len(o.data.polygons) for o in objs))
    return col


def _bbox(col):
    pts = []
    for o in col.objects:
        for v in o.bound_box:
            pts.append(o.matrix_world @ Vector(v))
    P = np.array(pts)
    return P.min(0), P.max(0)


def tint_materials(col, mode):
    done = set()
    for o in col.objects:
        for slot in o.material_slots:
            m = slot.material
            if m is None or m.name in done or not m.use_nodes:
                continue
            done.add(m.name)
            nt = m.node_tree; nb = NB(nt)
            bsdf = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
            if bsdf is None:
                continue
            lk = bsdf.inputs['Base Color'].links
            src = lk[0].from_socket if lk else None
            leaf = ('leaf' in m.name.lower() or 'leaves' in m.name.lower()) and mode == 'tree'
            if src is None:
                continue
            if leaf:
                bw = nb.N.new('ShaderNodeRGBToBW'); nb.L.new(src, bw.inputs[0])
                v = nb.math('POWER', bw.outputs[0], 0.8)
                col_ = nb.mixc(1.0, C.hex2lin('#6A55D8'), nb.comb(nb.mul(v, 1.9), nb.mul(v, 1.9), nb.mul(v, 1.9)), 'MULTIPLY')
            elif mode == 'tree':
                col_ = nb.mixc(0.75, src, nb.mixc(1.0, src, C.hex2lin('#F6CDA8'), 'MULTIPLY'))
                col_ = nb.mixc(1.0, col_, (1.35, 1.25, 1.15, 1.0), 'MULTIPLY')
            else:   # boulders -> warm plum/vermilion rock
                bw = nb.N.new('ShaderNodeRGBToBW'); nb.L.new(src, bw.inputs[0])
                v = nb.mul(bw.outputs[0], 2.2)
                col_ = nb.mixc(1.0, C.hex2lin('#C8503A'), nb.comb(v, v, v), 'MULTIPLY')
            nb.L.new(col_, bsdf.inputs['Base Color'])


def trees(coll):
    rng = np.random.RandomState(5)
    srcs = {}
    for slug in ('quiver_tree_01', 'quiver_tree_02', 'dead_quiver_trunk'):
        c = load_model(slug, {'quiver_tree_01': 0.12, 'quiver_tree_02': 0.18, 'dead_quiver_trunk': 0.6}[slug])
        if c is not None:
            tint_materials(c, 'tree'); srcs[slug] = c
    if not srcs:
        print('WARN no quiver trees'); return []
    out = []
    # adr2: the Poly Haven quiver trees read as PALMS in the S3 skim (banned) and the bare trunks as fence posts:
    # no trees in the S3/S4 view sector (bearing -45..45), no dead trunks at all; the rest stay as rim scale cues
    plan = [('quiver_tree_01', 12), ('quiver_tree_02', 12)]
    k = 0
    for slug, n in plan:
        if slug not in srcs:
            continue
        lo, hi = _bbox(srcs[slug]); h0 = max(hi[2] - lo[2], 0.1)
        for i in range(n):
            # 60 % in the S3 view sector (bearing -32..32), rest around the rim
            bd = rng.uniform(50, 310); rr = rng.uniform(1232, 1500)
            x, y, _ = pol(rr, bd)
            e = bpy.data.objects.new(f'QT_{k:02d}', None); coll.objects.link(e)
            e.instance_type = 'COLLECTION'; e.instance_collection = srcs[slug]
            target = rng.uniform(6.5, 10.5) if 'dead' not in slug else rng.uniform(4.0, 6.5)
            s = target / h0
            e.scale = (s, s, s); e.rotation_euler.z = rng.uniform(0, 6.28)
            e.location = (x, y, float(outer_height(np.array([x]), np.array([y]))[0]) - 0.25)
            out.append(e); k += 1
    return out


def boulders(coll, ground):
    rng = np.random.RandomState(9)
    srcs = []
    for slug in ('namaqualand_boulder_02', 'namaqualand_boulder_03', 'namaqualand_boulder_04'):
        c = load_model(slug, 0.02)
        if c is not None:
            tint_materials(c, 'rock'); srcs.append(c)
    out = []
    if not srcs:
        return out
    for i in range(30):
        rr = rng.uniform(975, 1185); bd = rng.uniform(-6.0, 6.0)
        if i < 12:   # near the S3 skim line and S4 camera
            bd = rng.uniform(-1.8, 1.8)
        x, y, _ = pol(rr, bd)
        c = srcs[i % len(srcs)]
        lo, hi = _bbox(c); d0 = max((hi - lo).max(), 0.1)
        size = rng.uniform(1.2, 3.6)
        e = bpy.data.objects.new(f'Boulder_{i:02d}', None); coll.objects.link(e)
        e.instance_type = 'COLLECTION'; e.instance_collection = c
        s = size / d0
        e.scale = (s, s, s * rng.uniform(0.7, 1.0)); e.rotation_euler = (0, 0, rng.uniform(0, 6.28))
        z0 = float(ground_h(ground, np.array([x]), np.array([y]))[0]) - 0.18 * size
        e.location = (x, y, z0)
        e['r'] = float(rr); e['size'] = size; e['z0'] = z0
        out.append(e)
    return out


def key_boulders(bs):
    for e in bs:
        r, size, z0 = e['r'], e['size'], e['z0']
        for f in range(430, 470):
            t = t_of(f)
            m = float(morph_curve((float(front_r(t)) - r) / 60.0))
            e.location.z = z0 - 1.25 * size * min(m, 1.05)
            e.keyframe_insert('location', index=2, frame=f)


# ---------------------------------------------------------------- tonearm
def chrome(name='M_ChromeGiant'):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; nb = NB(nt); b = nt.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*ND.lin('chrome'), 1); b.inputs['Metallic'].default_value = 1.0
    tc = nb.N.new('ShaderNodeTexCoord')
    n = nb.noise(nb.vmath('SCALE', tc.outputs['Object'], scale=1 / 3.0), 1.0, 4.0, 0.6)
    nb.L.new(nb.maprange(n, 0.3, 0.7, 0.07, 0.12), b.inputs['Roughness'])
    return m


def _tube(name, pts, radius, mat, coll, parent):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'
    sp = cu.splines.new('BEZIER'); sp.bezier_points.add(len(pts) - 1)
    for bp, p in zip(sp.bezier_points, pts):
        bp.co = p; bp.handle_left_type = bp.handle_right_type = 'AUTO'
    cu.bevel_depth = radius; cu.bevel_resolution = 6; cu.resolution_u = 24; cu.use_fill_caps = True
    o = bpy.data.objects.new(name, cu); coll.objects.link(o); o.parent = parent
    cu.materials.append(mat)
    return o


def _box(name, size, loc, mat, coll, parent, rot=(0, 0, 0), bevel=0.12):
    import bmesh
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); coll.objects.link(o); o.parent = parent
    o.location = loc; o.rotation_euler = rot
    me.materials.append(mat)
    bv = o.modifiers.new('bevel', 'BEVEL'); bv.width = min(size) * bevel; bv.segments = 3; bv.limit_method = 'NONE'
    me.shade_smooth()
    try:
        o.modifiers.new('wn', 'WEIGHTED_NORMAL')
    except Exception:
        pass
    return o


def _cyl(name, r, depth, loc, mat, coll, parent, rot=(0, 0, 0), verts=64):
    import bmesh
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=verts, radius1=r, radius2=r, depth=depth)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); coll.objects.link(o); o.parent = parent
    o.location = loc; o.rotation_euler = rot
    me.materials.append(mat)
    bv = o.modifiers.new('bevel', 'BEVEL'); bv.width = min(r, depth) * 0.08; bv.segments = 3
    me.shade_smooth()
    return o


PIVOT_H = 215.0
# bible 4.6/9 contact cheat (on top of x8000): diamond x6 (~14 m), cantilever thickness x3 and a bit longer.
# The cartridge is NOT scaled x6 (at 8000x that would be a 860 m box and the arm would stop reading as the S2 arm).
ARM_CHEAT = {'Stylus': ((9.0, 9.0, 9.0), 'tip'), 'Cantilever': ((4.5, 4.5, 1.5), 'axis'), 'CantDamper': ((2.6, 2.6, 1.5), 'axis')}


def _append_asset_arm(asset, coll, yaw, lift, parts):
    """Append the LATEST blend/tonearm_asset.blend 'TonearmAsset' as real objects (so per-part cheats are possible),
    hang its ArmPivot on our lift hinge, scale x8000 (ARM_LEN / effective length)."""
    with bpy.data.libraries.load(asset, link=False) as (src, dst):
        dst.collections = [c for c in src.collections if c == 'TonearmAsset']
    ta = dst.collections[0]
    ta.name = 'TonearmGiant'
    coll.children.link(ta)
    objs = list(ta.all_objects)
    piv = next(o for o in objs if 'stylus_tip_local' in o.keys())
    tip = Vector(piv['stylus_tip_local'])
    SCL = ARM_LEN / max(abs(tip.y), 1e-4)
    yaw.location.z = -tip.z * SCL               # the diamond touches the ground when lift = 0
    piv.parent = lift
    piv.matrix_parent_inverse = Matrix.Identity(4)
    piv.location = (0.0, 0.0, 0.0)
    piv.rotation_mode = 'XYZ'; piv.rotation_euler = (0.0, 0.0, math.radians(90.0))   # asset arm points -Y, rig points +X
    piv.scale = (SCL,) * 3
    # per-part cheats, done on (copied) mesh data in pivot space
    for o in objs:
        if o.type != 'MESH' or o.name not in ARM_CHEAT:
            continue
        S, mode = ARM_CHEAT[o.name]
        Mrel = o.matrix_parent_inverse @ o.matrix_basis
        o.data = o.data.copy()
        vs = [Mrel @ v.co for v in o.data.vertices]
        cx = sum(v.x for v in vs) / len(vs); cy = sum(v.y for v in vs) / len(vs)
        anchor = tip.copy() if mode == 'tip' else Vector((cx, cy, tip.z))
        A = (Mrel.inverted() @ Matrix.Translation(anchor) @ Matrix.Diagonal((*S, 1.0)) @ Matrix.Translation(-anchor) @ Mrel)
        o.data.transform(A); o.data.update()
        print('TONEARM cheat', o.name, S, mode)
    # giant chrome: roughness +0.03 (bible), keep everything else Set B's
    for mat in {s.material for o in objs for s in getattr(o, 'material_slots', []) if s.material}:
        if 'Chrome' not in mat.name or not mat.use_nodes:
            continue
        b = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if b is None:
            continue
        ri = b.inputs['Roughness']
        if ri.is_linked:
            lk = ri.links[0]; src_ = lk.from_socket
            add = mat.node_tree.nodes.new('ShaderNodeMath'); add.operation = 'ADD'; add.inputs[1].default_value = 0.03
            mat.node_tree.links.new(src_, add.inputs[0]); mat.node_tree.links.new(add.outputs[0], ri)
        else:
            ri.default_value = ri.default_value + 0.03
    # giant-scale bevels so cartridge / headshell / finger-lift edges catch thin highlights (~1 m at 8000x)
    bpy.context.view_layer.update()
    for o in objs:
        if o.type != 'MESH' or not any(k in o.name for k in ('Cartridge', 'Headshell', 'Finger', 'Shell', 'Cart')):
            continue
        ws = max(o.matrix_world.to_scale()[0], 1e-6)
        bv = o.modifiers.new('giant_bevel', 'BEVEL'); bv.width = 1.0 / ws; bv.segments = 3
        bv.limit_method = 'ANGLE'; bv.angle_limit = math.radians(35)
        try:
            bv.harden_normals = True
        except Exception:
            pass
        print('TONEARM bevel', o.name, 'local width', bv.width)
    # adr2: fill the dark 'garage door' opening at the cartridge base: a body-coloured block in the lower 30 % of
    # the largest Cart* body mesh (local bbox, inset 3 %), parented to it
    cands = [o for o in objs if o.type == 'MESH' and o.name.startswith('Cart')
             and not any(k in o.name for k in ('Logo', 'Stripe', 'Nose', 'Screw', 'Badge'))]
    if cands:
        def _vol(o):
            bb = [Vector(c) for c in o.bound_box]
            d = Vector((max(v.x for v in bb) - min(v.x for v in bb), max(v.y for v in bb) - min(v.y for v in bb),
                        max(v.z for v in bb) - min(v.z for v in bb)))
            return d.x * d.y * d.z
        body = max(cands, key=_vol)
        bb = [Vector(c) for c in body.bound_box]
        x0, x1 = min(v.x for v in bb), max(v.x for v in bb); y0, y1 = min(v.y for v in bb), max(v.y for v in bb)
        z0, z1 = min(v.z for v in bb), max(v.z for v in bb)
        ix, iy = 0.03 * (x1 - x0), 0.03 * (y1 - y0)
        X0, X1, Y0, Y1, Z0, Z1 = x0 + ix, x1 - ix, y0 + iy, y1 - iy, z0 + 0.002 * (z1 - z0), z0 + 0.3 * (z1 - z0)
        vv = [(X0, Y0, Z0), (X1, Y0, Z0), (X1, Y1, Z0), (X0, Y1, Z0), (X0, Y0, Z1), (X1, Y0, Z1), (X1, Y1, Z1), (X0, Y1, Z1)]
        ff = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        fm = bpy.data.meshes.new('CartFillGiant'); fm.from_pydata(vv, [], ff); fm.update()
        if body.data.materials:
            fm.materials.append(body.data.materials[0])
        fo = bpy.data.objects.new('CartFillGiant', fm); coll.objects.link(fo)
        fo.parent = body; fo.matrix_parent_inverse = Matrix.Identity(4)
        objs.append(fo)
        print('TONEARM cart fill under', body.name, (x1 - x0, y1 - y0, z1 - z0))
        # scfix: the dark 'garage door' is Set B's black-rubber CartNose block (9 x 4.4 mm, 0.5 mm proud of the cartridge
        # front face, 0.4 mm below its base = a 70 x 35 m black opening at giant scale): give it the body's lacquer
        if body.data.materials and body.data.materials[0] is not None:
            for o in objs:
                if o.type == 'MESH' and o.name.startswith('CartNose'):
                    for sl in o.material_slots:
                        sl.material = body.data.materials[0]
                    print('SCFIX CartNose material ->', body.data.materials[0].name, flush=True)
    # adr2: the four coloured lead wires read at giant scale: thicken x3 (displace along normals by 2 r)
    for o in objs:
        if o.type == 'CURVE' and 'Lead' in o.name:          # Set B's LeadWire0-3 are bevelled Bezier curves
            o.data = o.data.copy(); o.data.bevel_depth *= 3.0
            print('TONEARM thicken curve', o.name, o.data.bevel_depth)
            continue
        if o.type == 'MESH' and any(k in o.name for k in ('Lead', 'Wire', 'wire', 'lead')):
            d = sorted(o.dimensions)[0]
            if d <= 0:
                continue
            dp = o.modifiers.new('giant_thick', 'DISPLACE'); dp.direction = 'NORMAL'; dp.mid_level = 0.0
            dp.strength = d          # dims are local*scale-free here (object scale 1 in the asset) -> +2 r = x3 radius
            print('TONEARM thicken', o.name, d)
        if o.type == 'MESH' and o.name.startswith('Stylus'):
            for sl in o.material_slots:
                if sl.material is None:
                    continue
                mt = sl.material.copy(); mt.name = 'M_StylusGlintGiant'; sl.material = mt
                if mt.use_nodes:
                    bb = next((n for n in mt.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
                    if bb is not None:
                        bb.inputs['Emission Color'].default_value = (*C.hex2lin('#FFF0D8'), 1.0)
                        bb.inputs['Emission Strength'].default_value = 0.0     # b4: any steady glow read as a lit door; TipGlint fires on f697
            print('TONEARM stylus glint', o.name)
    for o in objs:
        o.visible_shadow = True
        parts.append(o)
    print('TONEARM: appended blend/tonearm_asset.blend as objects:', len(objs), 'scale', SCL, 'pivot h', yaw.location.z, 'tip', tuple(tip))
    return True


def tonearm(coll):
    """Returns (yaw_empty, lift_empty, parts, used_asset_flag)."""
    P = pol(*P_PIVOT)
    yaw = bpy.data.objects.new('ArmYaw', None); coll.objects.link(yaw)
    yaw.location = (P[0], P[1], PIVOT_H)
    lift = bpy.data.objects.new('ArmLift', None); coll.objects.link(lift); lift.parent = yaw
    parts = []
    viol = ND.simple('M_AnodisedVioletGiant', 'anodised', rough=0.35, metal=1.0)
    verm = ND.simple('M_VermilionGiant', 'vermilion', rough=0.32, coat=1.0, coat_rough=0.04)
    chr_ = chrome()
    diam = ND.black_diamond('M_BlackDiamondGiant')
    asset = os.path.join(ROOT, 'blend', 'tonearm_asset.blend')
    used = False
    # tower + base always ours (asset is the arm itself)
    if os.path.exists(asset):
        try:
            used = _append_asset_arm(asset, coll, yaw, lift, parts)
        except Exception as ex:
            import traceback; traceback.print_exc()
            print('WARN tonearm asset failed, placeholder', ex)
            for o in parts:
                try:
                    bpy.data.objects.remove(o)
                except Exception:
                    pass
            parts.clear(); used = False
    if not used:
        # placeholder S-arm along local +X, stylus tip at (ARM_LEN, 0, -PIVOT_H)
        L_ = ARM_LEN
        pts = [(-120, 0, 0), (250, 0, 0), (780, 0, 6), (1130, 95, 2), (1430, 40, -6), (1600, -10, -12), (1700, -14, -16)]
        parts.append(_tube('ArmTube', pts, 30.0, chr_, coll, lift))
        parts.append(_cyl('ArmCounterweight', 125.0, 230.0, (-330, 0, 0), chr_, coll, lift, rot=(0, math.radians(90), 0)))
        parts.append(_cyl('ArmCWRing', 132.0, 30.0, (-230, 0, 0), viol, coll, lift, rot=(0, math.radians(90), 0)))
        parts.append(_cyl('ArmGimbal', 90.0, 120.0, (0, 0, 0), viol, coll, lift))
        parts.append(_cyl('ArmGimbalAxle', 26.0, 260.0, (0, 0, 0), chr_, coll, lift, rot=(math.radians(90), 0, 0)))
        hs = _box('Headshell', (300.0, 150.0, 26.0), (L_ - 95, -10, -40), viol, coll, lift, rot=(0, 0, math.radians(-12)))
        parts.append(hs)
        parts.append(_box('FingerLift', (140.0, 22.0, 14.0), (L_ - 60, -110, -30), chr_, coll, lift, rot=(0, math.radians(-20), math.radians(-80))))
        parts.append(_box('Cartridge', (190.0, 110.0, 120.0), (L_ - 70, 0, -115), verm, coll, lift, rot=(0, 0, math.radians(-12))))
        # cantilever (x6 cheat) + diamond
        cl = _tube('Cantilever', [(L_ - 40, 0, -170), (L_ - 10, 0, -192), (L_, 0, -206)], 5.5, chr_, coll, lift)
        parts.append(cl)
        import bmesh
        me = bpy.data.meshes.new('Diamond'); bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=0.1, radius2=7.0, depth=14.0)
        bm.to_mesh(me); bm.free(); me.materials.append(diam)
        dmo = bpy.data.objects.new('Diamond', me); coll.objects.link(dmo); dmo.parent = lift
        dmo.location = (L_, 0, -PIVOT_H + 7.0); parts.append(dmo)
        wires = ['magenta', 'saffron', 'ultramarine', 'vermilion']
        for i, wname in enumerate(wires):
            wm = ND.simple(f'M_LeadWireGiant_{wname}', wname, rough=0.25, coat=0.5)
            yo = -36 + 24 * i
            pts_w = [(L_ - 165, yo, -95), (L_ - 210, yo * 1.2, -60), (L_ - 235, yo * 1.1, -38)]
            parts.append(_tube(f'LeadWire_{wname}', pts_w, 6.0, wm, coll, lift))
    ph = yaw.location.z
    tb = ND.simple('M_TowerBaseGiant', 'violet', rough=0.3, metal=0.6)
    tbo = _cyl('ArmTowerBase', 150.0, 40.0, (P[0], P[1], 20.0), tb, coll, None)
    bv = tbo.modifiers.new('bevel', 'BEVEL'); bv.width = 6.0; bv.segments = 4; bv.limit_method = 'ANGLE'
    parts.append(tbo)
    # adr2: chrome needs a hot highlight: a long specular-only strip light above/behind the arm (sun side), parallel to
    # the arm at its rest-over-L pose; it never lights the sand (diffuse 0)
    Lp = pol(*L_LAND)
    ax = Vector((Lp[0] - P[0], Lp[1] - P[1], 0.0)).normalized()
    mid = Vector(((P[0] + Lp[0]) / 2, (P[1] + Lp[1]) / 2, 260.0))
    side = Vector((-ax.y, ax.x, 0.0))            # left of the arm axis = away from the S6 lens (sun side, +Y)
    hl = bpy.data.lights.new('ChromeStrip', 'AREA'); hl.shape = 'RECTANGLE'; hl.size = 2200.0; hl.size_y = 160.0
    hl.color = C.hex2lin('#FFC890'); hl.energy = 2.2e7
    try:
        hl.diffuse_factor = 0.0; hl.specular_factor = 1.0; hl.volume_factor = 0.0; hl.use_shadow = False
    except Exception as ex:
        print('WARN strip light', ex)
    ho = bpy.data.objects.new('ChromeStrip', hl); coll.objects.link(ho)
    ho.location = mid + side * 650.0 + Vector((0, 0, 420.0))
    dvec = (mid - ho.location).normalized()
    q = dvec.to_track_quat('-Z', 'Y')
    ho.rotation_mode = 'QUATERNION'; ho.rotation_quaternion = q
    # rectangle long side along the arm axis
    from mathutils import Quaternion
    xl = q @ Vector((1, 0, 0))
    ang = math.atan2(xl.cross(ax).dot(dvec), xl.dot(ax))
    ho.rotation_quaternion = q @ Quaternion((0, 0, 1), ang)
    parts.append(ho)
    parts.append(_cyl('ArmTower', 55.0, ph - 60.0, (P[0], P[1], 40 + (ph - 60.0) / 2 - 20), viol, coll, None))
    return yaw, lift, parts, used


def key_tonearm(yaw, lift):
    P = np.array(pol(*P_PIVOT)[:2]); L = np.array(pol(*L_LAND)[:2])
    phi_L = math.degrees(math.atan2(L[1] - P[1], L[0] - P[0]))
    phi_rest = 92.0
    a_up = -math.degrees(math.asin(190.0 / ARM_LEN))
    for f in range(585, F1 + 1):
        t = t_of(f)
        # ease-OUT swing (the start is off-screen): the shadow tip enters the S5 frame top-left at ~25.6 s and the
        # arm settles over L by 26.75 s
        s_ = min(max((t - 25.25) / 1.5, 0.0), 1.0)
        u = 1.0 - (1.0 - s_) ** 2.2
        yaw.rotation_euler.z = math.radians(phi_rest + (phi_L - phi_rest) * u)
        yaw.keyframe_insert('rotation_euler', index=2, frame=f)
        # lift: ease-out, last 40 m slow: height fraction
        v = np.clip((t - 26.75) / 2.25, 0, 1)
        hfrac = 1.0 - (0.79 * float(smootherstep(min(1.0, v / 0.62))) + 0.21 * float(smoothstep(0.62, 1.0, v)))
        lift.rotation_euler.y = math.radians(a_up * hfrac) if hfrac > 0 else 0.0
        lift.keyframe_insert('rotation_euler', index=1, frame=f)
    return phi_L
