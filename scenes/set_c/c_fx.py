"""Set C FX point sets (stable point IDs built once in numpy, all motion analytic in GN from the scene frame,
never Distribute-per-frame, never Realize, sprites cast no shadows, scale-to-0 outside their life):
KickPuffs, FloatGrains, FrontWall (the drop's towering dust wall), FrontEngulf (lens engulf), FrontGrains,
TouchdownSkirt / TouchdownDust / TouchdownSpray / TouchdownGrains, plus the dust curtains riding the front."""
import bpy, math
import numpy as np
from c_common import *
from c_nodes import NB
from c_terrain import ground_h

CAM4 = (1120.0, 0.0)   # S4 locked-off camera (r, y)
CAMDIR6 = [0.63, -0.776]   # set by build(): unit xy from L toward the S6 end camera
G = 9.81


def points_obj(name, coll, P, attrs):
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(P)); me.vertices.foreach_set('co', np.asarray(P, np.float32).ravel())
    for k, v in attrs.items():
        v = np.asarray(v, np.float32)
        if v.ndim == 2:
            a = me.attributes.new(k, 'FLOAT_VECTOR', 'POINT'); a.data.foreach_set('vector', v.ravel())
        else:
            a = me.attributes.new(k, 'FLOAT', 'POINT'); a.data.foreach_set('value', v)
    me.update()
    o = bpy.data.objects.new(name, me); coll.objects.link(o)
    return o


# ---------------------------------------------------------------- materials
def _clear(nt):
    for n in list(nt.nodes):
        if n.type != 'OUTPUT_MATERIAL':
            nt.nodes.remove(n)
    return next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL')


SHADE_STOPS = [(0.0, C.hex2lin('#2E1060')), (0.18, C.hex2lin('#55206E')), (0.32, C.hex2lin('#8E2470')),
               (0.45, C.hex2lin('#E0307A')), (0.57, C.hex2lin('#FF7A40')), (0.68, ND.lin('saffron')),
               (0.86, C.hex2lin('#FFC870')), (1.0, C.hex2lin('#FFDDB0'))]
SUN = np.array([0.0, math.cos(math.radians(SUN_ELEV)), math.sin(math.radians(SUN_ELEV))])


def sun_shade(rel, hfrac, uy, rng, n, w=(0.35, 0.4, 0.25), jit=0.08):
    """per-sprite shade: sunward lobes high (chalk), cores mid (saffron), lee / low low (magenta-violet)."""
    rn = rel / np.maximum(np.linalg.norm(rel, axis=1, keepdims=True), 1e-6)
    sd = 0.5 + 0.5 * (rn @ SUN)
    raw = w[0] * hfrac + w[1] * sd + w[2] * (0.5 + 0.5 * uy) + rng.uniform(-jit, jit, n)
    return np.clip(0.52 + (raw - 0.5) * 1.9, 0.0, 1.0)          # stretched: real violet lee + chalk crowns


def m_dust(name='M_DustSprite', edge=1.0, emit=0.07, trans=0.5, opacity=0.85, stops=None, lobes=1.15, soft_n=0.55):
    """Soft billow sprite (dithered): alpha falls off over most of the radius and is broken into wispy lobes by
    per-instance noise, so overlapping sprites build a volume instead of reading as balls. Shading normal is bent
    toward +Z (soft terminator, lit tops) and half translucent. Instance attrs: alpha, tint (colour ramp), shade."""
    m = bpy.data.materials.new(name); m.use_nodes = True
    m.surface_render_method = 'DITHERED'
    try:
        m.use_transparent_shadow = True
    except Exception:
        pass
    nt = m.node_tree; nb = NB(nt); N = nt.nodes
    out = _clear(nt)
    lw = N.new('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = 0.5
    face = nb.sub(1.0, lw.outputs['Facing'])                  # ~|N.V|: 1 at the centre, 0 at the silhouette
    tc = N.new('ShaderNodeTexCoord')
    rnd = nb.attr('tint', inst=True)
    v = nb.vmath('ADD', tc.outputs['Object'], nb.comb(nb.mul(rnd, 13.1), nb.mul(rnd, 7.7), nb.mul(rnd, 3.3)))
    nz = nb.noise(nb.vmath('SCALE', v, scale=1.25), 1.0, 5.0, 0.6)
    soft = nb.ss(0.12, edge, nb.add(nb.mul(face, 1.0), nb.mul(nb.sub(nz, 0.5), lobes)))
    a = nb.mul(nb.mul(soft, nb.attr('alpha', inst=True)), opacity)
    stops = stops or SHADE_STOPS
    sh = nb.attr('shade', inst=True)
    shv = nb.add(sh, nb.mul(nb.sub(rnd, 0.5), 0.10))
    # denser noise cores sit a little lower on the ramp (soft self-shadow toward magenta, never brown)
    shv = nb.sub(shv, nb.mul(nb.ss(0.5, 0.85, nz), 0.12))
    col = nb.ramp(shv, stops)
    geo = N.new('ShaderNodeNewGeometry')
    nrm = nb.vmath('NORMALIZE', nb.vmath('ADD', nb.vmath('SCALE', geo.outputs['Normal'], scale=soft_n), (0.0, 0.0, 1.0 - soft_n)))
    dif = N.new('ShaderNodeBsdfDiffuse'); nb._in(dif.inputs['Color'], col); nb._in(dif.inputs['Normal'], nrm)
    tr = N.new('ShaderNodeBsdfTranslucent'); nb._in(tr.inputs['Color'], col); nb._in(tr.inputs['Normal'], nrm)
    mx = N.new('ShaderNodeMixShader'); mx.inputs[0].default_value = trans
    nt.links.new(dif.outputs[0], mx.inputs[1]); nt.links.new(tr.outputs[0], mx.inputs[2])
    em = N.new('ShaderNodeEmission'); nb._in(em.inputs['Color'], col); em.inputs['Strength'].default_value = emit
    ad = N.new('ShaderNodeAddShader'); nt.links.new(mx.outputs[0], ad.inputs[0]); nt.links.new(em.outputs[0], ad.inputs[1])
    tp = N.new('ShaderNodeBsdfTransparent')
    mx2 = N.new('ShaderNodeMixShader'); nb._in(mx2.inputs[0], nb.clamp01(a))
    nt.links.new(tp.outputs[0], mx2.inputs[1]); nt.links.new(ad.outputs[0], mx2.inputs[2])
    nt.links.new(mx2.outputs[0], out.inputs['Surface'])
    return m


def m_dust_q(name='M_DustQ', emit=0.25, trans=0.5, opacity=0.85, stops=None, lobes=1.2, nscale=2.2, up=(0.0, 0.25, 1.0),
             floor=0.0, shift=0.0):
    """adr2 camera-facing QUAD sprite (GN stores the grid UV as 'uvq'): alpha = radial falloff x fbm (detail 2, no
    facing term) so overlapping sprites build one soft volume instead of reading as balls. Diffuse uses a fixed
    up-and-sunward normal (all sprites lit alike, variation from the per-sprite 'shade' ramp), translucency uses the
    camera-facing geometry normal (backlit dust glows), plus an emission floor so lee dust stays coloured, never navy."""
    m = bpy.data.materials.new(name); m.use_nodes = True
    m.surface_render_method = 'DITHERED'
    try:
        m.use_backface_culling = False
    except Exception:
        pass
    nt = m.node_tree; nb = NB(nt); N = nt.nodes
    out = _clear(nt)
    uv = nb.attr('uvq', 'VECTOR')
    rnd = nb.attr('tint', inst=True)
    ln = N.new('ShaderNodeVectorMath'); ln.operation = 'LENGTH'
    nt.links.new(nb.vmath('SUBTRACT', uv, (0.5, 0.5, 0.0)), ln.inputs[0])
    rad = nb.sub(1.0, nb.mul(ln.outputs['Value'], 2.0))
    ux, uy, _ = nb.sep(uv)
    v = nb.comb(nb.add(nb.mul(ux, nscale), nb.mul(rnd, 13.1)), nb.add(nb.mul(uy, nscale), nb.mul(rnd, 7.7)), nb.mul(rnd, 3.3))
    nz = nb.noise(v, 1.0, 2.0, 0.55)
    soft = nb.ss(0.04, 0.72, nb.sub(nb.add(nb.mul(rad, 1.2), nb.mul(nb.sub(nz, 0.5), lobes)), 0.12))
    a = nb.mul(nb.mul(soft, nb.attr('alpha', inst=True)), opacity)
    stops = stops or SHADE_STOPS
    sh = nb.attr('shade', inst=True)
    shv = nb.add(sh, nb.mul(nb.sub(rnd, 0.5), 0.08))
    shv = nb.sub(shv, nb.mul(nb.ss(0.55, 0.85, nz), 0.08))
    if shift:
        shv = nb.sub(shv, shift)
    if floor > 0:
        shv = nb.math('MAXIMUM', shv, floor)
    col = nb.ramp(shv, stops)
    geo = N.new('ShaderNodeNewGeometry')
    L_ = math.sqrt(sum(c * c for c in up))
    dif = N.new('ShaderNodeBsdfDiffuse'); nb._in(dif.inputs['Color'], col)
    nb._in(dif.inputs['Normal'], nb.comb(*(c / L_ for c in up)))      # unlinked Normal sockets are ignored: link it
    tr = N.new('ShaderNodeBsdfTranslucent'); nb._in(tr.inputs['Color'], col); nt.links.new(geo.outputs['Normal'], tr.inputs['Normal'])
    mx = N.new('ShaderNodeMixShader'); mx.inputs[0].default_value = trans
    nt.links.new(dif.outputs[0], mx.inputs[1]); nt.links.new(tr.outputs[0], mx.inputs[2])
    em = N.new('ShaderNodeEmission'); nb._in(em.inputs['Color'], col); em.inputs['Strength'].default_value = emit
    ad = N.new('ShaderNodeAddShader'); nt.links.new(mx.outputs[0], ad.inputs[0]); nt.links.new(em.outputs[0], ad.inputs[1])
    tp = N.new('ShaderNodeBsdfTransparent')
    mx2 = N.new('ShaderNodeMixShader'); nb._in(mx2.inputs[0], nb.clamp01(a))
    nt.links.new(tp.outputs[0], mx2.inputs[1]); nt.links.new(ad.outputs[0], mx2.inputs[2])
    nt.links.new(mx2.outputs[0], out.inputs['Surface'])
    return m


def m_grain(name='M_Grain', glint=0.25, emit=0.15):
    """Sand grains: marble-sand palette (chalk / saffron / apricot / a little magenta), glinting in the low sun."""
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; nb = NB(nt); b = nt.nodes['Principled BSDF']
    col = nb.ramp(nb.attr('tint', inst=True), [(0.0, ND.lin('chalk')), (0.3, C.hex2lin('#FFD08A')), (0.55, ND.lin('saffron')),
                                                 (0.8, ND.lin('apricot')), (0.92, ND.lin('magenta')), (1.0, ND.lin('magenta'))])
    nb.L.new(col, b.inputs['Base Color']); b.inputs['Roughness'].default_value = glint
    try:
        nb.L.new(col, b.inputs['Emission Color']); b.inputs['Emission Strength'].default_value = emit
    except Exception:
        pass
    return m


# ---------------------------------------------------------------- GN group factory
def fx_group(name, body, mat, ico_sub=2, ico_r=1.0, extra=None, quad=None, aniso=(1.0, 1.0), roll=0.25):
    """body(nb, t, tau) -> (offset vec, scale float|vec, alpha float[, {attr: value}]).
    adr2: quad=(x,y,z) -> camera-facing cylindrical billboards (Y up, Z toward that point, aniso = (tangent, vertical)
    scale), 2 tris per sprite instead of 320, grid UV stored as 'uvq' for the quad sprite shader."""
    ng = bpy.data.node_groups.new(name, 'GeometryNodeTree')
    ng.interface.new_socket('Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    ng.interface.new_socket('Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    nb = NB(ng, 'GEO')
    gi = nb.node('NodeGroupInput'); go = nb.node('NodeGroupOutput')
    st = nb.node('GeometryNodeInputSceneTime')
    t = nb.mul(nb.sub(st.outputs['Frame'], 1.0), 1 / 24.0)
    tau = nb.sub(t, nb.math('MINIMUM', nb.math('MAXIMUM', nb.sub(t, 17.5), 0.0), 0.5))
    res = body(nb, t, tau)
    off, scale, alpha = res[:3]
    more = res[3] if len(res) > 3 else {}
    sp = nb.node('GeometryNodeSetPosition')
    nb.L.new(gi.outputs[0], sp.inputs['Geometry']); nb.L.new(off, sp.inputs['Offset'])
    if quad is None:
        ico = nb.node('GeometryNodeMeshIcoSphere'); ico.inputs['Radius'].default_value = ico_r; ico.inputs['Subdivisions'].default_value = ico_sub
        sm = nb.node('GeometryNodeSetShadeSmooth'); nb.L.new(ico.outputs['Mesh'], sm.inputs[0])
        src = sm.outputs[0]
    else:
        gr = nb.node('GeometryNodeMeshGrid')
        gr.inputs['Size X'].default_value = 2.0 * ico_r; gr.inputs['Size Y'].default_value = 2.0 * ico_r
        gr.inputs['Vertices X'].default_value = 2; gr.inputs['Vertices Y'].default_value = 2
        su = nb.node('GeometryNodeStoreNamedAttribute'); su.data_type = 'FLOAT_VECTOR'; su.domain = 'CORNER'
        su.inputs['Name'].default_value = 'uvq'
        nb.L.new(gr.outputs['Mesh'], su.inputs['Geometry']); nb.L.new(gr.outputs['UV Map'], su.inputs['Value'])
        src = su.outputs[0]
    sm2 = nb.node('GeometryNodeSetMaterial'); sm2.inputs['Material'].default_value = mat
    nb.L.new(src, sm2.inputs['Geometry'])
    iop = nb.node('GeometryNodeInstanceOnPoints')
    nb.L.new(sp.outputs[0], iop.inputs['Points']); nb.L.new(sm2.outputs[0], iop.inputs['Instance'])
    if quad is None:
        nb.L.new(scale, iop.inputs['Scale'])
        rv = nb.node('FunctionNodeRandomValue'); rv.data_type = 'FLOAT_VECTOR'
        try:
            rv.inputs[1].default_value = (6.3, 6.3, 6.3)
        except Exception:
            pass
        nb.L.new(rv.outputs[0], iop.inputs['Rotation'])
    else:
        nb.L.new(nb.comb(nb.mul(scale, aniso[0]), nb.mul(scale, aniso[1]), scale), iop.inputs['Scale'])
        a1 = nb.node('FunctionNodeAlignRotationToVector'); a1.axis = 'Y'
        a1.inputs['Vector'].default_value = (0.0, 0.0, 1.0)
        pos_ = nb.node('GeometryNodeInputPosition').outputs[0]
        a2 = nb.node('FunctionNodeAlignRotationToVector'); a2.axis = 'Z'; a2.pivot_axis = 'Y'
        nb.L.new(a1.outputs[0], a2.inputs['Rotation'])
        nb.L.new(nb.vmath('SUBTRACT', tuple(quad), pos_), a2.inputs['Vector'])
        rv = nb.node('FunctionNodeRandomValue'); rv.data_type = 'FLOAT'
        fin = [sk for sk in rv.inputs if sk.type == 'VALUE' and sk.name in ('Min', 'Max') and sk.enabled]
        fin[0].default_value = -roll; fin[1].default_value = roll
        fout = next(sk for sk in rv.outputs if sk.type == 'VALUE' and sk.enabled)
        rr = nb.node('FunctionNodeRotateRotation'); rr.rotation_space = 'LOCAL'
        nb.L.new(a2.outputs[0], rr.inputs['Rotation'])
        nb.L.new(nb.comb(0.0, 0.0, fout), rr.inputs['Rotate By'])
        nb.L.new(rr.outputs[0], iop.inputs['Rotation'])
    geo = iop.outputs[0]
    vals = {'alpha': alpha, 'tint': nb.attr('rnd')}
    vals.update(more)
    for nm, val in vals.items():
        s = nb.node('GeometryNodeStoreNamedAttribute'); s.data_type = 'FLOAT'; s.domain = 'INSTANCE'
        s.inputs['Name'].default_value = nm
        nb.L.new(geo, s.inputs['Geometry']); nb.L.new(val, s.inputs['Value']); geo = s.outputs[0]
    nb.L.new(geo, go.inputs[0])
    return ng


def _gate(nb, a, a0, a1):
    return nb.mul(nb.math('GREATER_THAN', a, a0), nb.math('LESS_THAN', a, a1))


def _expo(nb, a, tau_):
    """1 - exp(-max(a,0)/tau) with tau a socket or float."""
    a0 = nb.math('MAXIMUM', a, 0.0)
    return nb.sub(1.0, nb.math('EXPONENT', nb.mul(nb.div(a0, tau_), -1.0)))


def _radial(nb):
    pos = nb.node('GeometryNodeInputPosition').outputs[0]
    rx, ry, _ = nb.sep(pos)
    rl = nb.math('MAXIMUM', nb.math('SQRT', nb.add(nb.mul(rx, rx), nb.mul(ry, ry))), 1e-3)
    return nb.div(rx, rl), nb.div(ry, rl)


CAM4Z = [14.0]   # set by build(): S4 camera height (14 m above the pre-drop ground at r=1120)


def _guard(nb, off, rclear):
    """0 near the locked-off S4 lens, 1 beyond ~2.2x rclear: sprites shrink before their faces can cut the lens."""
    pos = nb.node('GeometryNodeInputPosition').outputs[0]
    p = nb.vmath('ADD', pos, off)
    d = nb.vmath('DISTANCE', p, (CAM4[0], CAM4[1], CAM4Z[0]))
    return nb.ss(0.0, 1.0, nb.div(nb.sub(d, rclear), rclear))


def _mod(o, ng):
    mod = o.modifiers.new('fx', 'NODES'); mod.node_group = ng
    o.visible_shadow = False
    return o


# ---------------------------------------------------------------- the drop: a towering wall of sand racing at the lens
def front_wall(coll, rng, mat):
    """adr1 layer split. BILLOWS on rings r 245..1135 about the disc centre launch 0.2-0.38 s AFTER the front passes
    (less near the lens), so a clear band of freshly snapped ridges stays visible between the racing leading sheet and
    the rising wall. They lean back (top further from the lens), surge, billow, then thin. Shade per sprite by sun side:
    sunward lobes chalk/#FFC870, cores saffron, lee and low sprites magenta-violet."""
    n = 30000
    cx = CAM4[0]
    dp = np.exp(rng.uniform(np.log(70.0), np.log(1000.0), n))      # log-uniform in (distance + 70)
    d = dp - 70.0 - 15.0
    r = cx - d
    keep = (r > 246) & (r < 1135)
    r, d = r[keep], d[keep]; n = len(r)
    w = 0.95 * np.maximum(d, 5.0) + 55.0
    thmax = np.where(r <= w, np.pi, np.arcsin(np.clip(w / r, 0, 1)))
    th = rng.uniform(-1, 1, n) * thmax
    x = r * np.cos(th); y = r * np.sin(th)
    incone = np.abs(np.degrees(np.arctan2(y, cx - x))) < 50.0          # only what the locked-off S4 lens can see
    sel = np.where(incone)[0][:14000]
    r, d, th, x, y = r[sel], d[sel], th[sel], x[sel], y[sel]; n = len(sel)
    dist = np.hypot(x - cx, y)
    U = rng.rand(n)
    # adr2: a LOW racing wall (bible: 15-25 m crest, 40 m plume), ~5 % stragglers to 90 m
    H = 10.0 + 75.0 * U ** 1.6
    strag = rng.rand(n) < 0.08
    H = np.where(strag, 70.0 + 60.0 * rng.rand(n), H)
    H *= np.clip(0.3 + dist / 160.0, 0.3, 1.0)
    sz = 1.25 * np.clip(0.03 * dist + 2.5, 3.0, 30.0) * np.clip(rng.lognormal(0.0, 0.35, n), 0.5, 2.2) * (0.75 + 0.5 * H / H.max())
    dl = np.interp(dist, [0.0, 90.0, 300.0], [0.03, 0.06, 0.12]) + np.where(dist > 200, rng.uniform(0.0, 0.12, n), rng.uniform(0.0, 0.04, n))
    t0 = 18.0 + (r - 240.0) / 880.0 + dl
    life = 0.30 + 1.0 * np.clip((dist - 30.0) / 800.0, 0, 1) + rng.uniform(0, 0.14, n)
    D = rng.uniform(-14.0, 10.0, n) + 0.35 * H                       # adr2: lean FORWARD, over toward the lens
    lat = rng.uniform(-1, 1, n)
    ux, uy = np.cos(th), np.sin(th)
    rad_rel = (D - 0.35 * H + 2.0) / 12.0
    rel = np.stack([ux * rad_rel - uy * lat, uy * rad_rel + ux * lat,
                    (H - 0.55 * H.max() * np.clip(dist / 400, 0.3, 1)) / 60.0 + rng.normal(0, 0.6, n)], 1)
    shade = sun_shade(rel, (H / H.max()) ** 0.6, uy, rng, n)
    attrs = {'t0': t0, 'sz': sz, 'rnd': rng.rand(n), 'H': H, 'tu': rng.uniform(0.16, 0.42, n),
             'cn': 1.0 - smoothstep(250.0, 700.0, dist), 'cd': rng.uniform(0.0, 0.25, n),
             'D': D, 'life': life, 'shade': shade, 'lat': lat}
    o = points_obj('FrontWall', coll, np.stack([x, y, np.full(n, -3.0)], 1), attrs)

    def body(nb, t, tau):
        a = nb.sub(t, nb.attr('t0'))
        eu = _expo(nb, a, nb.attr('tu'))
        er = _expo(nb, a, 0.2)
        ux_, uy_ = _radial(nb)
        dr = nb.add(nb.mul(nb.attr('D'), er), nb.mul(_expo(nb, a, 0.35), 120.0))   # adr2: keeps racing outward
        z = nb.mul(nb.attr('H'), eu)
        lat_ = nb.mul(nb.mul(nb.attr('lat'), 9.0), er)
        vis = _gate(nb, a, 0.0, nb.attr('life'))
        ox = nb.sub(nb.mul(ux_, dr), nb.mul(uy_, lat_)); oy = nb.add(nb.mul(uy_, dr), nb.mul(ux_, lat_))
        off = nb.comb(nb.mul(ox, vis), nb.mul(oy, vis), nb.mul(z, vis))
        grow = nb.madd(_expo(nb, a, 0.32), 0.7, 0.55)
        sc0 = nb.mul(nb.attr('sz'), grow)
        rc = nb.madd(sc0, 1.3, 4.0)
        sc = nb.mul(nb.mul(sc0, vis), _guard(nb, off, rc))
        fade = nb.sub(1.0, nb.ss(0.0, 1.0, nb.div(nb.sub(a, nb.mul(nb.attr('life'), 0.35)), nb.mul(nb.attr('life'), 0.65))))
        # smooth clear around the lens after the pass: gradient over 250-700 m + per-sprite delay (no tunnel shape)
        c0 = nb.add(nb.attr('cd'), 19.04)
        clear = nb.sub(1.0, nb.mul(nb.attr('cn'), nb.ss(0.0, 1.0, nb.div(nb.sub(t, c0), 0.22))))
        # young billows stay thin near the ground so the fresh ridges read between the sheet and the wall
        al = nb.mul(nb.mul(nb.mul(nb.ss(0.0, 0.05, a), fade), clear), _guard(nb, off, nb.mul(rc, 2.0)))
        return off, sc, al, {'shade': nb.attr('shade')}
    return _mod(o, fx_group('GN_FrontWall', body, mat, quad=(CAM4[0], CAM4[1], CAM4Z[0]), aniso=(2.5, 1.0), roll=0.12))


def front_sheet(coll, rng, mat):
    """adr1 LEADING SHEET: small high-alpha sprites that ride the front (r = front +- 10 m, H 8-25 m, 0.15-0.3 s life),
    so the shock reads as a crisp bright arc hugging the ground that curves away to both horizons."""
    n = 6000
    cx = CAM4[0]
    u = rng.rand(n)
    r0 = 246.0 + (1125.0 - 246.0) * (1 - (1 - u) ** 1.6)       # more sprites where the front is close
    th = rng.uniform(-1, 1, n) * np.radians(80.0)
    x = r0 * np.cos(th); y = r0 * np.sin(th)
    dist = np.hypot(x - cx, y)
    H = 2.0 + 16.0 * rng.rand(n) ** 1.6
    life = rng.uniform(0.15, 0.30, n)
    sz = np.clip(0.0016 * dist + 0.3, 0.3, 1.5) * rng.uniform(0.7, 1.3, n)      # adr2: 0.3-1.5 m grains
    shade = np.clip(0.58 + 0.3 * (H - 8.0) / 17.0 + 0.14 * np.sin(th) + rng.uniform(-0.08, 0.08, n), 0.45, 0.95)
    attrs = {'t0': 18.0 + (r0 - 240.0) / 880.0, 'sz': sz, 'rnd': rng.rand(n), 'H': H, 'life': life,
             'dr': rng.uniform(-10.0, 6.0, n), 'shade': shade}
    o = points_obj('FrontSheet', coll, np.stack([x, y, np.full(n, -1.0)], 1), attrs)

    def body(nb, t, tau):
        a = nb.sub(t, nb.attr('t0'))
        a0 = nb.math('MAXIMUM', a, 0.0)
        ux_, uy_ = _radial(nb)
        dr = nb.add(nb.mul(a0, 880.0), nb.attr('dr'))            # rides the front
        z = nb.mul(nb.attr('H'), _expo(nb, a, 0.05))
        vis = _gate(nb, a, 0.0, nb.attr('life'))
        off = nb.comb(nb.mul(nb.mul(ux_, dr), vis), nb.mul(nb.mul(uy_, dr), vis), nb.mul(z, vis))
        sc0 = nb.mul(nb.attr('sz'), nb.madd(_expo(nb, a, 0.08), 0.6, 0.6))
        rc = nb.madd(sc0, 1.5, 6.0)
        sc = nb.mul(nb.mul(sc0, vis), _guard(nb, off, rc))
        al = nb.mul(nb.mul(nb.ss(0.0, 0.02, a), nb.sub(1.0, nb.ss(0.5, 1.0, nb.div(a, nb.attr('life'))))), _guard(nb, off, nb.mul(rc, 2.5)))
        return off, sc, al, {'shade': nb.attr('shade')}
    return _mod(o, fx_group('GN_FrontSheet', body, mat, quad=(CAM4[0], CAM4[1], CAM4Z[0]), aniso=(1.0, 1.0), roll=3.1))


def engulf_streaks(coll, rng, mat):
    """adr1: ~2k near-lens grains blasting radially out of the vanishing point during the engulf (true motion blur)."""
    n = 2200
    cx = CAM4[0]; zc = CAM4Z[0]
    d0 = 12.0 + 150.0 * rng.rand(n) ** 1.5
    ah = rng.uniform(-0.62, 0.62, n); av = rng.uniform(-0.36, 0.30, n)
    y = d0 * np.tan(ah); z = zc + d0 * np.tan(av - math.radians(3.0))
    off_ax = np.hypot(y, z - zc)
    keep = off_ax > 1.6
    d0, y, z = d0[keep], y[keep], z[keep]; n = len(d0)
    x = cx - d0
    v = rng.uniform(140.0, 320.0, n)
    attrs = {'t0': rng.uniform(18.93, 19.12, n), 'sz': 0.035 + 0.13 * rng.rand(n) ** 2, 'rnd': 0.6 * rng.rand(n),
             'v': v, 'T': (d0 + 6.0) / v, 'sy': y / np.maximum(d0, 1) * 0.25, 'sz2': (z - zc) / np.maximum(d0, 1) * 0.25}
    o = points_obj('EngulfStreaks', coll, np.stack([x, y, z], 1), attrs)

    def body(nb, t, tau):
        a = nb.sub(t, nb.attr('t0'))
        a0 = nb.math('MAXIMUM', a, 0.0)
        dx = nb.mul(nb.attr('v'), a0)
        vis = _gate(nb, a, 0.0, nb.attr('T'))
        off = nb.comb(nb.mul(dx, vis), nb.mul(nb.mul(dx, nb.attr('sy')), vis), nb.mul(nb.mul(dx, nb.attr('sz2')), vis))
        return off, nb.mul(nb.mul(nb.attr('sz'), vis), _guard(nb, off, 0.9)), vis
    return _mod(o, fx_group('GN_EngulfStreaks', body, mat, 1))


def front_engulf(coll, rng, mat):
    """Dense close billows that swallow the lens for ~6 frames as the front passes the camera (f456-462)."""
    n = 1100
    cx = CAM4[0]
    r = rng.uniform(1030.0, 1136.0, n)
    y = rng.uniform(-1, 1, n) * (12.0 + 0.6 * (cx - r + 20.0))
    x = np.sqrt(np.maximum(r ** 2 - y ** 2, 0))
    H = 2.0 + 46.0 * rng.rand(n) ** 1.3
    core = rng.rand(n) < 0.38
    shade = np.where(core, rng.uniform(0.04, 0.3, n), np.clip(0.5 + 0.45 * rng.rand(n) ** 0.7 + 0.25 * np.clip(y / 40.0, -1, 1), 0.35, 1.0))
    attrs = {'t0': 18.0 + (r - 240.0) / 880.0 + rng.uniform(0, 0.02, n), 'sz': rng.uniform(1.4, 4.6, n), 'rnd': rng.rand(n),
             'H': H, 'tu': rng.uniform(0.25, 0.6, n), 'D': rng.uniform(8.0, 55.0, n), 'life': rng.uniform(0.14, 0.28, n),
             'shade': shade}
    o = points_obj('FrontEngulf', coll, np.stack([x, y, np.full(n, -1.0)], 1), attrs)

    def body(nb, t, tau):
        a = nb.sub(t, nb.attr('t0'))
        ux, uy = _radial(nb)
        dr = nb.mul(nb.attr('D'), _expo(nb, a, 0.12))
        z = nb.mul(nb.attr('H'), _expo(nb, a, nb.attr('tu')))
        vis = _gate(nb, a, 0.0, nb.attr('life'))
        off = nb.comb(nb.mul(nb.mul(ux, dr), vis), nb.mul(nb.mul(uy, dr), vis), nb.mul(z, vis))
        sc0 = nb.mul(nb.attr('sz'), nb.madd(_expo(nb, a, 0.2), 0.9, 0.4))
        sc = nb.mul(nb.mul(sc0, vis), _guard(nb, off, nb.madd(sc0, 1.3, 5.0)))
        al = nb.mul(nb.mul(nb.ss(0.0, 0.03, a), nb.sub(1.0, nb.ss(0.0, 1.0, nb.div(a, nb.attr('life'))))), nb.sub(1.0, nb.ss(19.04, 19.17, t)))
        return off, sc, al, {'shade': nb.attr('shade')}
    return _mod(o, fx_group('GN_FrontEngulf', body, mat, quad=(CAM4[0], CAM4[1], CAM4Z[0]), aniso=(1.6, 1.0), roll=0.4))


def drop_geyser(coll, rng, mat):
    """adr2: the f433 downbeat must HIT: a 40 m saffron geyser bursts all round the label-mesa base at 17.98 s
    (visible on f433-436 already), then sinks back while the front races out of it."""
    # scfix: was one uniform ring of equal-height posts (a cream 'picket fence'). Now ~26 ragged JETS of very different
    # heights (16-90 m), each leaning (tangential + outward), widening into a plume head, staggered in time, over a low
    # skirt that ties them together; shade runs magenta/vermilion at the base -> saffron at the heads (GEYSER_STOPS).
    n = 2200
    # keep the SHARED rng stream exactly as before (FrontEngulf / grains / touchdown downstream must not change):
    # replay the old geyser's draws in their old order, then use a private stream for the new jets
    rng.uniform(0, 2 * np.pi, n); rng.rand(n); rng.normal(0.0, 0.9, n); rng.uniform(244.0, 275.0, n)
    rng.rand(n); rng.rand(n); rng.uniform(-0.1, 0.1, n)
    rng.uniform(0.0, 0.03, n); rng.uniform(4.0, 11.0, n); rng.rand(n); rng.uniform(0.05, 0.12, n); rng.uniform(4.0, 40.0, n)
    rng = np.random.RandomState(4330)
    NJ = 26
    jang =np.concatenate([rng.normal(0.0, 0.85, 17), rng.uniform(0, 2 * np.pi, NJ - 17)])
    jH = 16.0 + 74.0 * rng.rand(NJ) ** 1.7
    jlt = rng.uniform(-0.55, 0.55, NJ)            # tangential lean (offset per metre of height)
    jlr = rng.uniform(0.08, 0.45, NJ)             # outward lean
    jw = rng.uniform(0.6, 1.7, NJ)                # plume width
    jt = rng.uniform(0.0, 0.04, NJ)               # stagger
    skirt = rng.rand(n) < 0.3
    j = rng.randint(0, NJ, n)
    u = rng.rand(n) ** 0.75                       # height fraction along the jet
    ang = np.where(skirt, np.where(rng.rand(n) < 0.6, rng.normal(0.0, 0.9, n), rng.uniform(0, 2 * np.pi, n)),
                   jang[j] + rng.normal(0.0, 0.010, n) * jw[j])
    r0 = np.where(skirt, rng.uniform(256.0, 276.0, n), rng.uniform(254.0, 266.0, n))
    H = np.where(skirt, rng.uniform(4.0, 14.0, n), jH[j] * u)
    tx_, ty_ = -np.sin(ang), np.cos(ang)
    rx_, ry_ = np.cos(ang), np.sin(ang)
    spr_t = rng.normal(0.0, 1.0, n) * (2.0 + 8.0 * u * jw[j])
    spr_r = rng.normal(0.0, 1.0, n) * (1.5 + 4.0 * u)
    lt = np.where(skirt, 0.0, jlt[j] * H + spr_t)
    lr = np.where(skirt, 0.0, jlr[j] * H + spr_r)
    lx = tx_ * lt + rx_ * lr
    ly = ty_ * lt + ry_ * lr
    sz = np.where(skirt, rng.uniform(5.0, 12.0, n), 3.0 + (4.0 + 9.0 * rng.rand(n)) * u * jw[j] + 2.5 * rng.rand(n))
    tu = np.where(skirt, rng.uniform(0.04, 0.08, n), 0.04 + 0.10 * u + rng.uniform(0.0, 0.03, n))
    t0 = 17.975 + np.where(skirt, rng.uniform(0.0, 0.02, n), jt[j] + rng.uniform(0.0, 0.012, n))
    dr = np.where(skirt, rng.uniform(6.0, 30.0, n), rng.uniform(1.0, 8.0, n))
    shade = np.where(skirt, rng.uniform(0.22, 0.48, n), 0.30 + 0.55 * u + rng.uniform(-0.08, 0.08, n))
    shade = np.clip(shade + 0.07 * np.sin(ang), 0.12, 0.97)
    o = points_obj('DropGeyser', coll, np.stack([r0 * np.cos(ang), r0 * np.sin(ang), np.full(n, 18.0)], 1),
                   {'t0': t0, 'sz': sz, 'rnd': rng.rand(n), 'H': H, 'tu': tu, 'dr': dr, 'lx': lx, 'ly': ly, 'shade': shade})

    def body(nb, t, tau):
        a = nb.sub(t, nb.attr('t0'))
        ux_, uy_ = _radial(nb)
        ez = _expo(nb, a, nb.attr('tu'))
        z = nb.mul(nb.attr('H'), nb.sub(ez, nb.mul(nb.ss(0.15, 0.6, a), 0.55)))
        dr = nb.mul(nb.attr('dr'), _expo(nb, a, 0.15))
        vis = _gate(nb, a, 0.0, 0.7)
        ox = nb.add(nb.mul(ux_, dr), nb.mul(nb.attr('lx'), ez))
        oy = nb.add(nb.mul(uy_, dr), nb.mul(nb.attr('ly'), ez))
        off = nb.comb(nb.mul(ox, vis), nb.mul(oy, vis), nb.mul(z, vis))
        sc = nb.mul(nb.mul(nb.attr('sz'), nb.madd(_expo(nb, a, 0.1), 0.9, 0.4)), vis)
        al = nb.mul(nb.ss(0.0, 0.015, a), nb.sub(1.0, nb.ss(0.2, 0.7, a)))
        return off, sc, al, {'shade': nb.attr('shade')}
    return _mod(o, fx_group('GN_DropGeyser', body, mat, quad=(CAM4[0], CAM4[1], CAM4Z[0]), aniso=(1.0, 1.25), roll=0.6))


# scfix: saturated eruption ramp (plum -> magenta -> vermilion -> orange -> saffron), no cream / chalk at the top
GEYSER_STOPS = [(0.0, C.hex2lin('#4A1450')), (0.18, C.hex2lin('#A81C62')), (0.36, ND.lin('magenta')),
                (0.52, ND.lin('vermilion')), (0.70, C.hex2lin('#FF6A12')), (0.86, ND.lin('saffron')), (1.0, C.hex2lin('#FFB52A'))]


def front_grains(coll, rng, mat):
    """Ballistic sand grains (real g) launched by the front around the S4 camera: they blast past the lens,
    hang ~2-3 s and fall back onto the fresh rings."""
    n = 14000
    cx = CAM4[0]
    r = cx - 230.0 * rng.rand(n) ** 1.4 + 40.0 * rng.rand(n) * (rng.rand(n) < 0.15)
    y = rng.uniform(-1, 1, n) * (14.0 + 0.75 * np.abs(cx - r))
    x = np.sqrt(np.maximum(r ** 2 - y ** 2, 0))
    vu = rng.uniform(5.0, 26.0, n)
    attrs = {'t0': 18.0 + (r - 240.0) / 880.0 + rng.uniform(0, 0.04, n), 'sz': 0.02 + 0.12 * rng.rand(n) ** 2.2,
             'rnd': 0.3 + 0.62 * rng.rand(n), 'vu': vu, 'vr': 8.0 + 55.0 * rng.rand(n) ** 1.6, 'vl': rng.uniform(-6, 6, n),
             'T': 2.0 * vu / G + 0.05}
    o = points_obj('FrontGrains', coll, np.stack([x, y, np.full(n, 0.3)], 1), attrs)

    def body(nb, t, tau):
        a = nb.sub(t, nb.attr('t0'))
        a0 = nb.math('MAXIMUM', a, 0.0)
        ux, uy = _radial(nb)
        # air drag on the horizontal throw (heavy grains: slows to ~40% over 1 s)
        hr = nb.mul(nb.attr('vr'), nb.mul(_expo(nb, a, 0.9), 0.9))
        lat = nb.mul(nb.attr('vl'), a0)
        zz = nb.sub(nb.mul(nb.attr('vu'), a0), nb.mul(nb.mul(a0, a0), 0.5 * G))
        vis = _gate(nb, a, 0.0, nb.attr('T'))
        ox = nb.sub(nb.mul(ux, hr), nb.mul(uy, lat)); oy = nb.add(nb.mul(uy, hr), nb.mul(ux, lat))
        off = nb.comb(nb.mul(ox, vis), nb.mul(oy, vis), nb.mul(zz, vis))
        out_ = nb.sub(1.0, nb.ss(20.3, 20.75, t))          # adr2: shrink out before the f500 visibility cut (no pop)
        return off, nb.mul(nb.mul(nb.mul(nb.attr('sz'), vis), _guard(nb, off, 1.2)), out_), vis
    o = _mod(o, fx_group('GN_FrontGrains', body, mat, 1))
    return o


# ---------------------------------------------------------------- S3 FX
def kick_puffs(coll, rng, path, mat):
    ks = [(tk, s) for tk, s in kicks() if 12.0 <= tk < 17.5]
    P, t0, sz, rnd = [], [], [], []
    for tk, s in ks:
        pos = path.s3(f_of(tk))[0]
        cr = pos[0]; alt = pos[2] - path.gx(cr)
        r0 = cr - (40 + 200 * min(1.0, alt / 380.0))
        n = 90
        far = 260.0
        rr = cr + 45 + (min(cr + far, 1192) - cr - 45) * rng.rand(n) ** 0.8
        lat = rng.uniform(-1, 1, n) * (20 + 0.75 * (rr - cr))
        x = np.sqrt(np.maximum(rr ** 2 - lat ** 2, 0)); y = lat
        z = ground_h(path.g, x, y)
        P.append(np.stack([x, y, z], 1)); t0.append(tk + (np.hypot(x, y) - r0) / 220.0)
        sz.append(rng.uniform(0.8, 2.2, n) * (1 + 0.4 * s) * (1 + (rr - cr) / 200.0)); rnd.append(rng.rand(n))
    if not P:
        return None
    P = np.concatenate(P)
    nn = len(P)
    o = points_obj('KickPuffs', coll, P, {'t0': np.concatenate(t0), 'sz': np.concatenate(sz), 'rnd': np.concatenate(rnd),
                                          'shade': rng.uniform(0.7, 1.0, nn)})

    def body(nb, t, tau):
        a = nb.sub(tau, nb.attr('t0'))
        rise = nb.mul(_expo(nb, a, 0.4), 1.2)
        vis = _gate(nb, a, 0.0, 0.9)
        off = nb.comb(0.0, 0.0, nb.mul(rise, vis))
        s1 = nb.mul(nb.mul(nb.mul(nb.attr('sz'), nb.ss(0.0, 0.1, a)), nb.madd(a, 1.3, 1.0)), vis)
        sc = nb.comb(nb.mul(s1, 1.6), nb.mul(s1, 1.6), nb.mul(s1, 0.45))     # low wisps hugging the ring, not balls
        al = nb.mul(nb.math('POWER', nb.math('SUBTRACT', 1.0, nb.div(a, 0.9), clamp=True), 1.6), 0.3)
        return off, sc, al, {'shade': nb.attr('shade')}
    return _mod(o, fx_group('GN_KickPuffs', body, mat, 1))


def float_grains(coll, rng, path, mat):
    """adr1: ~4k grains (6-30 cm) inside the S3 hang view cone, 5-60 m from the lens, lift off the dunes from 17.0 s
    and hang motionless through the 17.5-18.0 silence: a few hundred floating jewels, not noise."""
    cam, hd, pt, rl, lens, alt = path.s3(f_of(17.75))
    n = 26000
    d = 3.0 + 57.0 * rng.rand(n) ** 1.6
    ah = rng.uniform(-0.62, 0.62, n); av = rng.uniform(-0.36, 0.30, n) + math.radians(pt)
    x = cam[0] + d * np.cos(ah) * np.cos(av); y = cam[1] + d * np.sin(ah) * np.cos(av); zt = cam[2] + d * np.sin(av)
    g = ground_h(path.g, x, y)
    lift = zt - g
    ok = (lift > 0.1) & (lift < 9.0)
    # clear tube around the still-moving S3 camera path (17.0-17.5)
    camz = np.array([path.s3(f_of(17.0 + 0.5 * k / 20))[0] for k in range(21)])
    zc = np.interp(x, camz[:, 0], camz[:, 2]); yc = np.interp(x, camz[:, 0], camz[:, 1])
    ok &= np.hypot(zt - zc, y - yc) > 1.6
    idx = np.where(ok)[0][:6500]
    x, y, g, lift, d = x[idx], y[idx], g[idx], lift[idx], d[idx]; n = len(idx)
    # adr2: many small 1-5 cm sparks + ~40 large hero grains (not popcorn)
    szs = (0.01 + 0.035 * rng.rand(n) ** 2.0) * np.clip(d / 25.0, 0.5, 1.6)
    hero = rng.rand(n) < (40.0 / max(n, 1))
    szs = np.where(hero, rng.uniform(0.09, 0.18, n), szs)
    o = points_obj('FloatGrains', coll, np.stack([x, y, g], 1),
                   {'sz': szs, 'rnd': rng.rand(n), 'lift': lift,
                    'ts': rng.uniform(0.0, 0.25, n), 'ph': rng.uniform(0, 6.283, n)})
    print('FLOATGRAINS', n)

    def body(nb, t, tau):
        a = nb.sub(nb.sub(tau, 17.0), nb.attr('ts'))
        up = nb.mul(nb.ss(0.0, 0.5, a), nb.attr('lift'))
        ph = nb.attr('ph')
        drift = nb.ss(0.0, 0.6, a)
        dx = nb.mul(nb.math('SINE', nb.add(nb.mul(tau, 1.3), ph)), nb.mul(drift, 0.18))
        dy = nb.mul(nb.math('COSINE', nb.add(nb.mul(tau, 1.1), nb.mul(ph, 1.7))), nb.mul(drift, 0.18))
        off = nb.comb(dx, dy, up)
        sc = nb.mul(nb.attr('sz'), nb.ss(-0.05, 0.3, a))
        return off, sc, nb.add(a, 1.0)
    return _mod(o, fx_group('GN_FloatGrains', body, mat, 1))


def m_jewel(name='M_FloatGrain'):
    """bright grains (value floor 0.5) that glint only on their sun-facing side."""
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; nb = NB(nt); b = nt.nodes['Principled BSDF']
    col = nb.ramp(nb.attr('tint', inst=True), [(0.0, ND.lin('chalk')), (0.3, C.hex2lin('#FFD08A')), (0.6, ND.lin('saffron')),
                                                 (0.85, C.hex2lin('#FF9A5A')), (1.0, C.hex2lin('#FF7AB0'))])
    nb.L.new(col, b.inputs['Base Color']); b.inputs['Roughness'].default_value = 0.25
    geo = nt.nodes.new('ShaderNodeNewGeometry')
    sd = nb.math('MAXIMUM', nb.vmath('DOT_PRODUCT', geo.outputs['Normal'], tuple(SUN)), 0.0)
    nb.L.new(col, b.inputs['Emission Color'])
    nb.L.new(nb.mul(nb.math('POWER', sd, 3.0), 2.2), b.inputs['Emission Strength'])
    return m


# ---------------------------------------------------------------- touchdown (world space at L, does not spin)
Q6 = [890.0, 530.0, 45.0]   # set by build.py: S6 end camera (touchdown quads face it)
PATH = [None]               # scfix: set by build(): the camera Path (cartridge keep-clear test)
OCC_FRAMES = (700, 702, 704, 706, 708)
_CART = {}


def _cart_box():
    """scfix: world bbox corners of cartridge / nose / fill / cantilever / stylus at the touchdown pose (the arm keys end
    on the f697+ pose, so the current property values are that pose). No depsgraph update needed."""
    from mathutils import Vector

    def wm(o):
        return o.matrix_basis.copy() if o.parent is None else wm(o.parent) @ o.matrix_parent_inverse @ o.matrix_basis
    pts = []
    for o in bpy.data.objects:
        if o.type == 'MESH' and o.name.startswith(('Cartridge', 'CartNose', 'CartFill', 'Stylus', 'Cantilever', 'CantDamper')):
            M = wm(o)
            pts += [tuple(M @ Vector(c)) for c in o.bound_box]
    return np.array(pts, float) if pts else None


def _cam(f):
    import c_cam
    pos, hd, pt, rl, lens, alt = PATH[0].at(f)
    R = np.array(c_cam.quat(hd, pt, rl).to_matrix())
    tw = 18.0 / lens
    return np.array(pos, float), R, tw, tw * 9.0 / 16.0


def _proj(P, cam):
    C0, R, tw, th = cam
    loc = (P - C0) @ R
    d = np.maximum(-loc[:, 2], 1e-3)
    return loc[:, 0] / d / tw, loc[:, 1] / d / th, d


def _occluders(pos_fn):
    """scfix: bool per sprite: on any of OCC_FRAMES its (soft) quad overlaps the cartridge+stylus screen box while lying
    in front of the cartridge's mid-depth. pos_fn(t) -> (P (n,3), visible half-extent (n,), 0 when not alive)."""
    if '_box' not in _CART:
        _CART['_box'] = _cart_box()
    box = _CART['_box']
    if box is None or PATH[0] is None:
        return None
    occ = None
    for f in OCC_FRAMES:
        cam = _cam(f)
        bu, bv, bd = _proj(box, cam)
        P, rs = pos_fn(t_of(f))
        u, v, d = _proj(P, cam)
        ru = rs / d / cam[2]; rv = rs / d / cam[3]
        hit = ((rs > 0) & (u + ru > bu.min()) & (u - ru < bu.max()) & (v + rv > bv.min()) & (v - rv < bv.max())
               & (d - 0.5 * rs < bd.mean()))
        occ = hit if occ is None else (occ | hit)
    return occ


def _thin(occ, n, seed, keep=0.25, a_keep=0.25):
    """occ mask -> per-sprite alpha factor: occluders mostly removed, a few kept as a faint veil."""
    if occ is None:
        return np.ones(n)
    r = np.random.RandomState(seed).rand(n)
    return np.where(occ, np.where(r < keep, a_keep, 0.0), 1.0)


def _ex(a, tau_):
    return 1.0 - np.exp(-np.maximum(a, 0.0) / tau_)


def _occ_t(nb, t):
    """GN alpha factor: the keep-clear thinning ramps in over f697-700 (frames before touchdown unchanged)."""
    return nb.sub(1.0, nb.mul(nb.sub(1.0, nb.attr('occ')), nb.ss(29.0, 29.125, t)))


def touchdown(coll, rng, mat_d, mat_g, mat_s=None):
    L = pol(*L_LAND)
    global Q6
    Q6 = tuple(Q6)
    tx, ty = -math.sin(math.radians(L_LAND[1])), math.cos(math.radians(L_LAND[1]))   # disc rotation direction (CCW)
    objs = {}
    # (a) downwash skirt from 28.7 s: low swirling sheet under the descending cartridge
    n = 900
    ang = rng.uniform(0, 2 * np.pi, n); rho = rng.uniform(8.0, 70.0, n)
    P_ = np.stack([L[0] + np.cos(ang) * rho, L[1] + np.sin(ang) * rho, np.full(n, -2.0)], 1)
    A_ = {'cf': 1.0 - 0.8 * smoothstep(0.05, 0.55, np.cos(ang) * CAMDIR6[0] + np.sin(ang) * CAMDIR6[1]),
          't0': 28.67 + 0.25 * rng.rand(n) * (rho / 70.0), 'sz': rng.uniform(7.0, 18.0, n), 'rnd': 0.3 + 0.7 * rng.rand(n),
          'ang': ang, 'rho': rho, 'H': rng.uniform(2.0, 18.0, n), 'shade': np.clip(0.55 + 0.3 * np.sin(ang) + rng.uniform(-0.1, 0.1, n), 0.2, 1.0)}

    def _pos_skirt(t):
        a = t - A_['t0']; e = _ex(a, 0.6)
        rad = rho + 35.0 * e; an = ang + 0.35 * e
        P = np.stack([L[0] + np.cos(an) * rad, L[1] + np.sin(an) * rad, -2.0 + A_['H'] * e], 1)
        return P, 0.75 * 1.8 * A_['sz'] * (0.35 + 0.8 * e) * ((a > 0) & (a < 9.0))
    A_['occ'] = _thin(_occluders(_pos_skirt), n, 6971)
    o = points_obj('TouchdownSkirt', coll, P_, A_)

    def body(nb, t, tau):
        a = nb.sub(t, nb.attr('t0'))
        e = _expo(nb, a, 0.6)
        rad = nb.add(nb.attr('rho'), nb.mul(e, 35.0))
        an = nb.add(nb.attr('ang'), nb.mul(e, 0.35))
        ox = nb.sub(nb.mul(nb.math('COSINE', an), rad), nb.mul(nb.math('COSINE', nb.attr('ang')), nb.attr('rho')))
        oy = nb.sub(nb.mul(nb.math('SINE', an), rad), nb.mul(nb.math('SINE', nb.attr('ang')), nb.attr('rho')))
        vis = _gate(nb, a, 0.0, 9.0)
        off = nb.comb(nb.mul(ox, vis), nb.mul(oy, vis), nb.mul(nb.mul(nb.attr('H'), e), vis))
        sc = nb.mul(nb.mul(nb.attr('sz'), nb.madd(e, 0.8, 0.35)), vis)
        al = nb.mul(nb.mul(nb.mul(nb.ss(0.0, 0.25, a), 0.55), nb.attr('cf')), _occ_t(nb, t))
        return off, sc, al, {'shade': nb.attr('shade')}
    objs['TouchdownSkirt'] = _mod(o, fx_group('GN_TouchSkirt', body, mat_d, quad=Q6, aniso=(1.8, 1.0)))
    # (b) the burst at 29.0: base-surge ring racing out to ~150 m hugging the ground + a crown that rises to ~60 m
    n = 6000
    ang = rng.uniform(0, 2 * np.pi, n)
    crown = rng.rand(n) < 0.5
    cdir = np.array(CAMDIR6)                                     # L -> S6 end camera (unit, xy)
    # adr2: crown is a 360 deg DOME round and behind the stylus (150-250 m), so the cartridge stands in silhouette
    # against glowing dust; the half facing the lens stays lower and thinner so the needle is never buried
    front_ = (np.cos(ang) * cdir[0] + np.sin(ang) * cdir[1])
    R1 = np.where(crown, rng.uniform(30.0, 200.0, n), 120.0 + 230.0 * rng.rand(n) ** 0.7)
    H = np.where(crown, (150.0 + 100.0 * rng.rand(n) ** 1.2) * np.where(front_ > 0.2, 0.2, 1.0),
                 6.0 + 34.0 * rng.rand(n) ** 1.5)
    A_ = {'t0': 28.97 + rng.uniform(0, 0.05, n), 'sz': np.where(crown, rng.uniform(16, 36, n) * np.where(front_ > 0.2, 0.5, 1.0), rng.uniform(9, 24, n)),
          'rnd': 0.25 + 0.75 * rng.rand(n), 'ang': ang, 'R1': R1, 'H': H, 'tr': rng.uniform(0.14, 0.3, n),
          'tz': rng.uniform(0.2, 0.42, n), 'cf': 1.0 - 0.8 * smoothstep(0.05, 0.55, front_),
          'shade': np.maximum(sun_shade(np.stack([np.cos(ang), np.sin(ang), (H - 30.0) / 30.0], 1), np.clip(H / 150.0, 0, 1), np.sin(ang), rng, n, w=(0.3, 0.45, 0.25), jit=0.1), 0.5)}

    def _pos_dust(t):
        a = t - A_['t0']; e = _ex(a, A_['tr'])
        rad = A_['R1'] * e + 6.0; an = A_['ang'] + 0.12 * e
        P = np.stack([L[0] + np.cos(an) * rad, L[1] + np.sin(an) * rad, -2.0 + A_['H'] * _ex(a, A_['tz'])], 1)
        return P, 0.75 * 1.3 * A_['sz'] * (0.3 + 1.1 * e) * ((a > 0) & (a < 6.0))
    # scfix: crown sprites that would sit in front of the cartridge / stylus on f700-708 are MOVED behind it (dome mass
    # kept: the cartridge stands in silhouette against the dust), the rest of the occluders thinned to a faint veil
    occ = _occluders(_pos_dust)
    if occ is not None:
        r2 = np.random.RandomState(6972)
        mv = occ & crown
        k = int(mv.sum())
        back = math.atan2(-cdir[1], -cdir[0])
        A_['ang'] = np.where(mv, back + r2.uniform(-1.25, 1.25, n), A_['ang'])
        A_['R1'] = np.where(mv, 110.0 + 120.0 * r2.rand(n), A_['R1'])
        A_['H'] = np.where(mv, 120.0 + 120.0 * r2.rand(n) ** 1.2, A_['H'])
        A_['sz'] = np.where(mv, r2.uniform(18.0, 36.0, n), A_['sz'])
        fr2 = np.cos(A_['ang']) * cdir[0] + np.sin(A_['ang']) * cdir[1]
        A_['cf'] = np.where(mv, 1.0 - 0.8 * smoothstep(0.05, 0.55, fr2), A_['cf'])
        occ2 = _occluders(_pos_dust)
        A_['occ'] = _thin(occ2, n, 6973, keep=0.2, a_keep=0.3)
        print('SCFIX touchdown dust: occluders', int(occ.sum()), 'crown moved behind', k, 'still occluding', int(occ2.sum()), flush=True)
    else:
        A_['occ'] = np.ones(n)
        print('SCFIX touchdown dust: no keep-clear test (no cartridge / path)', flush=True)
    ang = A_['ang']
    o = points_obj('TouchdownDust', coll, np.stack([L[0] + np.cos(ang) * 6, L[1] + np.sin(ang) * 6, np.full(n, -2.0)], 1), A_)

    def body(nb, t, tau):
        a = nb.sub(t, nb.attr('t0'))
        e = _expo(nb, a, nb.attr('tr'))
        rad = nb.add(nb.mul(nb.attr('R1'), e), 6.0)
        an = nb.add(nb.attr('ang'), nb.mul(e, 0.12))
        ox = nb.sub(nb.mul(nb.math('COSINE', an), rad), nb.mul(nb.math('COSINE', nb.attr('ang')), 6.0))
        oy = nb.sub(nb.mul(nb.math('SINE', an), rad), nb.mul(nb.math('SINE', nb.attr('ang')), 6.0))
        oz = nb.mul(nb.attr('H'), _expo(nb, a, nb.attr('tz')))
        vis = _gate(nb, a, 0.0, 6.0)
        off = nb.comb(nb.mul(ox, vis), nb.mul(oy, vis), nb.mul(oz, vis))
        sc = nb.mul(nb.mul(nb.attr('sz'), nb.madd(e, 1.1, 0.3)), vis)
        al = nb.mul(nb.mul(nb.mul(nb.ss(0.0, 0.03, a), nb.sub(1.0, nb.mul(nb.ss(0.5, 3.0, a), 0.6))), nb.attr('cf')), _occ_t(nb, t))
        return off, sc, al, {'shade': nb.attr('shade')}
    objs['TouchdownDust'] = _mod(o, fx_group('GN_TouchdownDust', body, mat_d, quad=Q6, aniso=(1.3, 1.0), roll=0.5))
    # (c) spray along the disc rotation: a sheet of sand flung tangentially (ballistic, real g)
    n = 1400
    s = rng.rand(n)
    vt = 60.0 + 170.0 * s; vu = rng.uniform(16.0, 48.0, n)
    P_ = np.stack([L[0] + rng.uniform(-8, 8, n), L[1] + rng.uniform(-8, 8, n), np.full(n, 1.0)], 1)
    A_ = {'t0': 28.97 + rng.uniform(0, 0.08, n), 'sz': rng.uniform(5.0, 16.0, n), 'rnd': 0.3 + 0.7 * rng.rand(n),
          'vt': vt, 'vu': vu, 'vs': rng.uniform(-14, 14, n), 'shade': rng.uniform(0.55, 1.0, n)}

    def _pos_spray(t):
        a = t - A_['t0']; a0 = np.maximum(a, 0.0)
        ht = vt * 0.8 * _ex(a, 0.8); hs = A_['vs'] * a0
        z = np.maximum(vu * a0 - 0.5 * G * a0 * a0, 0.0)
        P = np.stack([P_[:, 0] + ht * tx - hs * ty, P_[:, 1] + ht * ty + hs * tx, P_[:, 2] + z], 1)
        return P, 0.75 * 1.5 * A_['sz'] * (0.3 + 1.2 * _ex(a, 0.4)) * ((a > 0) & (a < 6.0))
    A_['occ'] = _thin(_occluders(_pos_spray), n, 6974)
    o = points_obj('TouchdownSpray', coll, P_, A_)

    def body(nb, t, tau):
        a = nb.sub(t, nb.attr('t0'))
        a0 = nb.math('MAXIMUM', a, 0.0)
        ht = nb.mul(nb.attr('vt'), nb.mul(_expo(nb, a, 0.8), 0.8))
        hs = nb.mul(nb.attr('vs'), a0)
        z = nb.math('MAXIMUM', nb.sub(nb.mul(nb.attr('vu'), a0), nb.mul(nb.mul(a0, a0), 0.5 * G)), 0.0)
        vis = _gate(nb, a, 0.0, 6.0)
        off = nb.comb(nb.mul(nb.add(nb.mul(ht, tx), nb.mul(hs, -ty)), vis), nb.mul(nb.add(nb.mul(ht, ty), nb.mul(hs, tx)), vis), nb.mul(z, vis))
        sc = nb.mul(nb.mul(nb.attr('sz'), nb.madd(_expo(nb, a, 0.4), 1.2, 0.3)), vis)
        al = nb.mul(nb.mul(nb.mul(nb.ss(0.0, 0.05, a), nb.sub(1.0, nb.mul(nb.ss(0.6, 3.0, a), 0.7))), 0.5), _occ_t(nb, t))
        return off, sc, al, {'shade': nb.attr('shade')}
    objs['TouchdownSpray'] = _mod(o, fx_group('GN_TouchdownSpray', body, mat_d, quad=Q6, aniso=(1.5, 1.0), roll=0.6))
    # (d) crown grains: giant-scale debris (0.6-2.6 m) thrown out ballistically
    n = 2600
    ang = rng.uniform(0, 2 * np.pi, n)
    vu = rng.uniform(15.0, 58.0, n)
    o = points_obj('TouchdownGrains', coll, np.stack([L[0] + np.cos(ang) * 10, L[1] + np.sin(ang) * 10, np.full(n, 1.0)], 1),
                   {'t0': 28.97 + rng.uniform(0, 0.06, n), 'sz': 1.0 + 3.0 * rng.rand(n) ** 2, 'rnd': rng.rand(n), 'ang': ang,
                    'vr': 30.0 + 90.0 * rng.rand(n), 'vu': vu, 'T': 2 * vu / G})

    def body(nb, t, tau):
        a = nb.sub(t, nb.attr('t0'))
        a0 = nb.math('MAXIMUM', a, 0.0)
        hr = nb.mul(nb.attr('vr'), a0)
        z = nb.sub(nb.mul(nb.attr('vu'), a0), nb.mul(nb.mul(a0, a0), 0.5 * G))
        vis = _gate(nb, a, 0.0, nb.attr('T'))
        off = nb.comb(nb.mul(nb.mul(nb.math('COSINE', nb.attr('ang')), hr), vis), nb.mul(nb.mul(nb.math('SINE', nb.attr('ang')), hr), vis), nb.mul(z, vis))
        return off, nb.mul(nb.attr('sz'), vis), vis
    objs['TouchdownGrains'] = _mod(o, fx_group('GN_TouchdownGrains', body, mat_g, 1))
    # (e) adr1 base-surge FRONT: dense small sprites riding the expanding ring (0 -> ~120 m by f700), alpha 0.9 at the front
    n = 3000
    ang = rng.uniform(0, 2 * np.pi, n)
    A_ = {'t0': 28.97 + rng.uniform(0, 0.02, n), 'sz': rng.uniform(4.5, 11.0, n), 'rnd': rng.rand(n), 'ang': ang,
          'lag': rng.uniform(0.0, 1.0, n) ** 2, 'H': rng.uniform(3.0, 22.0, n),
          'shade': np.clip(0.66 + 0.3 * np.sin(ang) + rng.uniform(-0.1, 0.1, n), 0.5, 1.0)}

    def _pos_surge(t):
        a = t - A_['t0']; a0 = np.maximum(a, 0.0)
        Rf = 140.0 * _ex(a, 0.07) + 22.0 * a0
        rad = Rf * (1.0 - 0.35 * A_['lag']) + 4.0
        P = np.stack([L[0] + np.cos(ang) * rad, L[1] + np.sin(ang) * rad, -1.0 + A_['H'] * _ex(a, 0.1)], 1)
        return P, 0.75 * 2.0 * A_['sz'] * (0.5 + 1.2 * _ex(a, 0.2)) * ((a > 0) & (a < 6.0))
    A_['occ'] = _thin(_occluders(_pos_surge), n, 6975, keep=0.3, a_keep=0.3)
    print('SCFIX surge occluders', int((A_['occ'] < 1).sum()), 'of', n, flush=True)
    o = points_obj('TouchSurge', coll, np.stack([L[0] + np.cos(ang) * 4, L[1] + np.sin(ang) * 4, np.full(n, -1.0)], 1), A_)

    def body(nb, t, tau):
        a = nb.sub(t, nb.attr('t0'))
        a0 = nb.math('MAXIMUM', a, 0.0)
        Rf = nb.add(nb.mul(_expo(nb, a, 0.07), 140.0), nb.mul(a0, 22.0))
        rad = nb.add(nb.mul(Rf, nb.sub(1.0, nb.mul(nb.attr('lag'), 0.35))), 4.0)
        ox = nb.mul(nb.math('COSINE', nb.attr('ang')), nb.sub(rad, 4.0)); oy = nb.mul(nb.math('SINE', nb.attr('ang')), nb.sub(rad, 4.0))
        vis = _gate(nb, a, 0.0, 6.0)
        oz = nb.mul(nb.attr('H'), _expo(nb, a, 0.1))
        off = nb.comb(nb.mul(ox, vis), nb.mul(oy, vis), nb.mul(oz, vis))
        sc = nb.mul(nb.mul(nb.attr('sz'), nb.madd(_expo(nb, a, 0.2), 1.2, 0.5)), vis)
        al = nb.mul(nb.mul(nb.mul(nb.ss(0.0, 0.02, a), nb.sub(1.0, nb.mul(nb.attr('lag'), 0.75))), nb.sub(1.0, nb.mul(nb.ss(0.3, 1.5, a), 0.7))), _occ_t(nb, t))
        return off, sc, al, {'shade': nb.attr('shade')}
    objs['TouchSurge'] = _mod(o, fx_group('GN_TouchSurge', body, mat_s or mat_d, quad=Q6, aniso=(2.0, 1.0), roll=0.3))
    # (f) adr1 fan of chalk-glinting debris (6-15 m at giant scale) thrown along the disc rotation
    n = 900
    spread = rng.uniform(-0.45, 0.45, n)
    ca, sa = np.cos(spread), np.sin(spread)
    fx_ = tx * ca - ty * sa; fy_ = tx * sa + ty * ca
    vu = rng.uniform(25.0, 75.0, n)
    o = points_obj('TouchFan', coll, np.stack([L[0] + rng.uniform(-6, 6, n), L[1] + rng.uniform(-6, 6, n), np.full(n, 2.0)], 1),
                   {'t0': 28.97 + rng.uniform(0, 0.06, n), 'sz': 2.0 + 5.0 * rng.rand(n) ** 1.5, 'rnd': 0.55 * rng.rand(n),
                    'fx': fx_, 'fy': fy_, 'vh': rng.uniform(70.0, 230.0, n), 'vu': vu, 'T': 2 * vu / G})

    def body(nb, t, tau):
        a = nb.sub(t, nb.attr('t0'))
        a0 = nb.math('MAXIMUM', a, 0.0)
        hh = nb.mul(nb.attr('vh'), nb.mul(_expo(nb, a, 1.2), 1.2))
        z = nb.sub(nb.mul(nb.attr('vu'), a0), nb.mul(nb.mul(a0, a0), 0.5 * G))
        vis = _gate(nb, a, 0.0, nb.attr('T'))
        off = nb.comb(nb.mul(nb.mul(nb.attr('fx'), hh), vis), nb.mul(nb.mul(nb.attr('fy'), hh), vis), nb.mul(z, vis))
        return off, nb.mul(nb.attr('sz'), vis), vis
    objs['TouchFan'] = _mod(o, fx_group('GN_TouchFan', body, m_jewel('M_TouchJewel'), 1))
    # glint source on the diamond tip at touchdown (drives the Streaks glare exactly at f697)
    import bmesh
    me = bpy.data.meshes.new('TipGlint'); bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=2, radius=3.0)
    bm.to_mesh(me); bm.free()
    gm = bpy.data.materials.new('M_TipGlint'); gm.use_nodes = True
    gn = gm.node_tree.nodes; out_ = _clear(gm.node_tree)
    em = gn.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (*C.hex2lin('#FFF0D8'), 1.0)
    gm.node_tree.links.new(em.outputs[0], out_.inputs['Surface'])
    me.materials.append(gm)
    go_ = bpy.data.objects.new('TipGlint', me); coll.objects.link(go_)
    go_.location = (L[0] + 18.0 * CAMDIR6[0], L[1] + 18.0 * CAMDIR6[1], 13.0)
    go_.visible_shadow = False
    for f, e in ((694, 0.0), (696, 0.0), (697, 400.0), (698, 150.0), (700, 0.0)):
        em.inputs['Strength'].default_value = e; em.inputs['Strength'].keyframe_insert('default_value', frame=f)
    objs['TipGlint'] = go_
    # point light inside the burst (bible: warm glow in the dust)
    ld = bpy.data.lights.new('TouchdownGlow', 'POINT'); ld.energy = 0.0; ld.color = C.hex2lin('#FFB30F'); ld.shadow_soft_size = 30
    try:
        ld.use_shadow = False
    except Exception:
        pass
    lo = bpy.data.objects.new('TouchdownGlow', ld); coll.objects.link(lo)
    # scfix: glow sits BEHIND the stylus (away from the S6 lens) so the dome backlights the cartridge silhouette
    lo.location = (L[0] - 90.0 * CAMDIR6[0], L[1] - 90.0 * CAMDIR6[1], 70.0)
    for f, e in ((690, 0.0), (696, 0.0), (697, 1.2e6), (699, 2.5e6), (708, 1.2e6)):     # b3: 6e6 blew the dome white
        ld.energy = e; ld.keyframe_insert('energy', frame=f)
    objs['TouchdownGlow'] = lo
    return objs


def build(coll, ground, path):
    rng = np.random.RandomState(3)
    CAM4Z[0] = 17.0 + max(path.g1120, 0.0)
    PATH[0] = path
    # adr2: quad sprites (no facing term, no balls); wall shading carried by translucency + emission
    mw = m_dust_q('M_DustWall', emit=0.3, trans=0.55, opacity=0.92, lobes=1.2, nscale=2.0, shift=0.12)
    ms = m_dust_q('M_DustSheet', emit=1.4, trans=0.4, opacity=0.95, lobes=0.6, nscale=1.0)
    mg = m_grain('M_Grain', glint=0.35, emit=0.12)
    mf = m_jewel('M_FloatGrain')
    mstreak = m_grain('M_StreakGrain', glint=0.3, emit=1.6)
    objs = {}
    # adr1: KickPuffs dropped (they read as translucent ghost smears); the kick rings read through the sand hop + glow
    objs['FloatGrains'] = float_grains(coll, rng, path, mf)
    objs['FrontDust'] = front_wall(coll, rng, mw)
    objs['FrontSheet'] = front_sheet(coll, rng, ms)
    mgy = m_dust_q('M_DustGeyser', emit=0.6, trans=0.5, opacity=0.95, lobes=1.35, stops=GEYSER_STOPS)   # scfix: was emit 1.3 / cream floor
    objs['DropGeyser'] = drop_geyser(coll, rng, mgy)
    me_ = m_dust_q('M_DustEngulf', emit=0.3, trans=0.6, opacity=0.5, lobes=1.3)
    objs['FrontEngulf'] = front_engulf(coll, rng, me_)
    objs['EngulfStreaks'] = engulf_streaks(coll, rng, mstreak)
    objs['FrontGrains'] = front_grains(coll, rng, mg)
    mt = m_dust_q('M_DustTouch', emit=0.55, trans=0.7, opacity=0.7, lobes=1.3, floor=0.5, up=(0.0, 0.3, 1.0))
    msurge = m_dust_q('M_DustSurge', emit=0.45, trans=0.7, opacity=0.42, lobes=1.2, floor=0.64, up=(0.0, 0.3, 1.0))   # b3: saffron, not a red lava band
    objs.update(touchdown(coll, rng, mt, mg, msurge))
    return objs


def key_visibility(obj, ranges, f0=F0, f1=F1):
    """ranges: list of (first_visible, last_visible) global frames."""
    vis_prev = None
    for f in range(f0 - 1, f1 + 2):
        v = any(a <= f <= b for a, b in ranges)
        if v != vis_prev:
            obj.hide_render = not v; obj.keyframe_insert('hide_render', frame=f)
            obj.hide_viewport = not v; obj.keyframe_insert('hide_viewport', frame=f)
            vis_prev = v


# ---------------------------------------------------------------- dust curtains riding the front
def m_curtain(name='M_DustCurtain', emit=0.45, lit_base=0.6, erode=0.0, lip=0.0, face=None):
    """Dust wall shader for the drop front: world-space 4D noise, billowing (large-noise) top silhouette,
    lit-top / shadowed-base gradient, saffron->chalk, dithered."""
    m = bpy.data.materials.new(name); m.use_nodes = True
    m.surface_render_method = 'DITHERED'
    try:
        m.use_backface_culling = False
    except Exception:
        pass
    nt = m.node_tree; nb = NB(nt); N = nt.nodes
    out = _clear(nt)
    geo = N.new('ShaderNodeNewGeometry'); tc = N.new('ShaderNodeTexCoord')
    _, _, hz = nb.sep(tc.outputs['Generated'])           # 0 bottom .. 1 top
    w = nb.value(0.0, 'curtain_w')
    nz = N.new('ShaderNodeTexNoise'); nz.noise_dimensions = '4D'
    nb._in(nz.inputs['Vector'], nb.vmath('SCALE', geo.outputs['Position'], scale=1 / 22.0))
    nb._in(nz.inputs['W'], w)
    nz.inputs['Detail'].default_value = 6.0; nz.inputs['Roughness'].default_value = 0.62
    fac = nz.outputs['Fac'] if 'Fac' in nz.outputs else nz.outputs['Factor']
    big = N.new('ShaderNodeTexNoise'); big.noise_dimensions = '4D'
    nb._in(big.inputs['Vector'], nb.vmath('SCALE', geo.outputs['Position'], scale=1 / 85.0))
    nb._in(big.inputs['W'], nb.mul(w, 0.5))
    big.inputs['Detail'].default_value = 3.0; big.inputs['Roughness'].default_value = 0.5
    bfac = big.outputs['Fac'] if 'Fac' in big.outputs else big.outputs['Factor']
    billow = nb.ss(0.3, 0.7, fac)
    hfade = nb.math('POWER', nb.sub(1.0, hz), 0.9)
    edge = nb.add(nb.mul(nb.ss(0.3, 0.7, bfac), 0.85), nb.mul(fac, 0.12))       # billowing top line
    top = nb.mul(nb.ss(0.0, 0.3, nb.sub(edge, hz)), nb.ss(0.0, 0.1, hz))
    amp = nb.value(0.0, 'curtain_alpha')
    a = nb.mul(nb.mul(nb.mul(billow, hfade), top), amp)
    if erode > 0:
        # adr2: noise-eroded top (no ruler-straight edge): theta-driven fbm so the crest line breaks into plumes
        ox, oy, _ = nb.sep(tc.outputs['Object'])
        th = nb.math('ARCTAN2', oy, ox)
        en = nb.noise(nb.comb(nb.mul(th, 60.0), nb.mul(hz, 3.0), nb.mul(w, 0.7)), 1.0, 3.0, 0.6)
        a = nb.mul(a, nb.sub(1.0, nb.ss(0.35, 1.0, nb.add(hz, nb.mul(nb.sub(en, 0.5), erode)))))
    if face is not None:
        # scfix (touchdown ring only): the half of the ring wall between the lens and the stylus fades out
        fx_, fy_, _ = nb.sep(tc.outputs['Object'])
        fl_ = nb.math('MAXIMUM', nb.math('SQRT', nb.add(nb.mul(fx_, fx_), nb.mul(fy_, fy_))), 1e-4)
        dotf = nb.div(nb.add(nb.mul(fx_, float(face[0])), nb.mul(fy_, float(face[1]))), fl_)
        a = nb.mul(a, nb.sub(1.0, nb.mul(nb.ss(-0.1, 0.45, dotf), 0.9)))
    a = nb.math('MULTIPLY', a, 2.4, clamp=True)
    col = nb.mixc(nb.ss(0.4, 0.9, fac), ND.lin('saffron'), C.hex2lin('#FFC870'))
    # lit top; the base of the back walls sinks into magenta-violet shadow (3 palette colours, not one orange)
    col = nb.mixc(nb.mul(nb.ss(0.55, 0.0, hz), 1.0 - lit_base), col, C.hex2lin('#6B1F5C'))
    dif = N.new('ShaderNodeBsdfDiffuse'); nb._in(dif.inputs['Color'], col)
    tr = N.new('ShaderNodeBsdfTranslucent'); nb._in(tr.inputs['Color'], col)
    em = N.new('ShaderNodeEmission'); nb._in(em.inputs['Color'], col); em.inputs['Strength'].default_value = emit
    if lip > 0:
        lipm = nb.ss(0.22, 0.02, hz)
        nb._in(em.inputs['Color'], nb.mixc(lipm, col, C.hex2lin('#FFC870')))
        nb._in(em.inputs['Strength'], nb.add(emit, nb.mul(lipm, lip)))
    mx = N.new('ShaderNodeMixShader'); mx.inputs[0].default_value = 0.5
    nt.links.new(dif.outputs[0], mx.inputs[1]); nt.links.new(tr.outputs[0], mx.inputs[2])
    ad = N.new('ShaderNodeAddShader'); nt.links.new(mx.outputs[0], ad.inputs[0]); nt.links.new(em.outputs[0], ad.inputs[1])
    tp = N.new('ShaderNodeBsdfTransparent')
    mx2 = N.new('ShaderNodeMixShader'); nb._in(mx2.inputs[0], a)
    nt.links.new(tp.outputs[0], mx2.inputs[1]); nt.links.new(ad.outputs[0], mx2.inputs[2])
    nt.links.new(mx2.outputs[0], out.inputs['Surface'])
    return m


def _ring_mesh(name, na, nh, flare=None):
    th = np.arange(na) * 2 * np.pi / na
    hh = np.linspace(0, 1, nh)
    fl = np.ones((nh, na)) if flare is None else flare(hh[:, None], th[None, :])
    X = np.cos(th)[None, :] * fl; Y = np.sin(th)[None, :] * fl; Z = hh[:, None] * np.ones(na)[None, :]
    co = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1).astype(np.float32)
    ii, jj = np.meshgrid(np.arange(nh - 1), np.arange(na), indexing='ij')
    a = ii * na + jj; b = ii * na + (jj + 1) % na; c = (ii + 1) * na + (jj + 1) % na; d = (ii + 1) * na + jj
    tris = np.concatenate([np.stack([a.ravel(), b.ravel(), c.ravel()], 1), np.stack([a.ravel(), c.ravel(), d.ravel()], 1)]).astype(np.int32)
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(co)); me.vertices.foreach_set('co', co.ravel())
    me.loops.add(len(tris) * 3); me.loops.foreach_set('vertex_index', tris.ravel())
    me.polygons.add(len(tris)); me.polygons.foreach_set('loop_start', np.arange(0, len(tris) * 3, 3, dtype=np.int32))
    me.update(calc_edges=True); me.shade_smooth()
    return me


def curtains(coll):
    """adr1: concentric dust walls riding the drop front (object scale = front radius). Curtain 0 is the bright low
    LEADING SHEET at the front; 1-2 are the tall back walls BEHIND the clear band of fresh ridges."""
    objs = []
    spec = ((0.0, 20.0, 0.7, 0.3, 0.8, 0.7, 2.6), (200.0, 60.0, 0.45, 0.25, 0.5, 0.5, 0.0), (280.0, 42.0, 0.38, 0.25, 0.4, 0.5, 0.0))
    for k, (lag, H, amp, emit, lit_base, ero, lip) in enumerate(spec):
        mat = m_curtain(f'M_DustCurtain_{k}', emit=emit, lit_base=lit_base, erode=ero, lip=lip)
        me = _ring_mesh(f'DustCurtain_{k}', 1440, 12, lambda hh, th: 1.0 + 0.0 * hh * th)
        me.materials.append(mat)
        o = bpy.data.objects.new(f'DustCurtain_{k}', me); coll.objects.link(o)
        o.visible_shadow = False
        t_pass = 18.0 + (CAM4[0] + lag - 240.0) / 880.0
        fr_ = [f for f in range(431, 560)] + [432.49, 432.51]
        for f in fr_:
            t = t_of(f)
            fr = 240.0 + 880.0 * (t - 18.0) - lag
            rr = min(max(fr, 1.0), 1260.0)
            o.scale = (rr, rr, H * (0.3 + 0.7 * float(smoothstep(18.0, 18.3 + lag / 880.0, t))))
            o.location.z = -2.0
            o.keyframe_insert('scale', frame=f); o.keyframe_insert('location', index=2, frame=f)
        nodes = mat.node_tree.nodes
        for f in range(431, 560):
            t = t_of(f)
            nodes['curtain_w'].outputs[0].default_value = t * 0.9
            nodes['curtain_w'].outputs[0].keyframe_insert('default_value', frame=f)
            al = amp * float(smoothstep(18.0 + lag / 880.0, 18.06 + lag / 880.0, t)) * (1.0 - float(smoothstep(t_pass - 0.16, t_pass - 0.03, t)))
            nodes['curtain_alpha'].outputs[0].default_value = al
            nodes['curtain_alpha'].outputs[0].keyframe_insert('default_value', frame=f)
        objs.append(o)
    return objs


def touchdown_ring(coll):
    """Low base-surge ring at L (soft top) under the touchdown sprites."""
    mat = m_curtain('M_DustTouchdown', face=tuple(CAMDIR6))
    L = pol(*L_LAND)
    me = _ring_mesh('TouchRing', 256, 8, lambda hh, th: (1.0 + 0.55 * hh ** 1.5) * (1.0 + 0.12 * np.sin(th * 7.0) * hh))
    me.materials.append(mat)
    objs = []
    for k, (r1, H, dl) in enumerate(((250.0, 55.0, 0.0), (160.0, 38.0, 0.05))):
        o = bpy.data.objects.new(f'TouchRing_{k}', me); coll.objects.link(o); o.visible_shadow = False
        o.location = (L[0], L[1], -3.0)
        for f in range(690, F1 + 1):
            t = t_of(f); aa = max(t - 28.97 - dl, 0.0)
            e = 1 - math.exp(-aa / 0.22)
            rr = 12.0 + (r1 - 12.0) * e
            o.scale = (rr, rr, 4.0 + (H - 4.0) * (1 - math.exp(-aa / 0.3)))
            o.keyframe_insert('scale', frame=f)
        objs.append(o)
    nodes = mat.node_tree.nodes
    for f in range(688, F1 + 1):
        t = t_of(f)
        nodes['curtain_w'].outputs[0].default_value = t * 1.4
        nodes['curtain_w'].outputs[0].keyframe_insert('default_value', frame=f)
        al = 0.45 * float(smoothstep(28.97, 29.0, t)) * (1.0 - 0.35 * float(smoothstep(29.2, 29.5, t)))
        nodes['curtain_alpha'].outputs[0].default_value = al
        nodes['curtain_alpha'].outputs[0].keyframe_insert('default_value', frame=f)
    return objs


# ---------------------------------------------------------------- adr2: S5 top-down sun-shadow proxies
SH_MUL = (0.36, 0.33, 0.50)    # violet multiply (#2B1660 at ~55 %), what the low sun's shadow does to the sand


def _m_shadow(name, layers):
    """Blended Transparent-BSDF multiply (backface culled: a flattened closed mesh renders exactly one layer).
    'shf' (0..1) fades it in/out."""
    m = bpy.data.materials.new(name); m.use_nodes = True
    m.surface_render_method = 'BLENDED'
    m.use_backface_culling = True
    try:
        m.use_transparency_overlap = True
    except Exception:
        pass
    nt = m.node_tree; nb = NB(nt); N = nt.nodes
    out = _clear(nt)
    shf = nb.value(0.0, 'shf')
    k = tuple(c ** (1.0 / layers) for c in SH_MUL)
    col = nb.mixc(shf, (1.0, 1.0, 1.0), k)
    tp = N.new('ShaderNodeBsdfTransparent'); nb._in(tp.inputs['Color'], col)
    nt.links.new(tp.outputs[0], out.inputs['Surface'])
    return m


def shadow_proxy(coll, parts, zg=13.0):
    """The EEVEE sun shadow of the 215-400 m high arm and the 40 m label mesa does not register in the 1750 m top-down
    (diag adr2: pool 2048, clip_end 9 km, jitter on: no change). Camera-only proxies: the arm's evaluated meshes are
    projected along the sun onto z = zg (3 layers with +-0.3 deg sun offsets = soft penumbra) + the mesa's stadium."""
    objs = []
    ng = bpy.data.node_groups.new('GN_ArmShadow', 'GeometryNodeTree')
    ng.interface.new_socket('Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    ng.interface.new_socket('Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    nb = NB(ng, 'GEO')
    go = nb.node('NodeGroupOutput')
    j = nb.node('GeometryNodeJoinGeometry')
    for o in parts:
        if getattr(o, 'type', '') != 'MESH':
            continue
        oi = nb.node('GeometryNodeObjectInfo'); oi.transform_space = 'RELATIVE'
        oi.inputs['Object'].default_value = o
        nb.L.new(oi.outputs['Geometry'], j.inputs[0])
    rl = nb.node('GeometryNodeRealizeInstances'); nb.L.new(j.outputs[0], rl.inputs[0])
    mat = _m_shadow('M_ArmShadowProxy', 3)
    j2 = nb.node('GeometryNodeJoinGeometry')
    for de, da in ((0.0, 0.0), (0.3, 0.2), (-0.25, -0.3)):
        el = math.radians(SUN_ELEV + de); az = math.radians(da)
        Ls = (math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el))
        pos = nb.node('GeometryNodeInputPosition').outputs[0]
        px, py, pz = nb.sep(pos)
        k = nb.div(nb.sub(pz, zg), Ls[2])
        sp = nb.node('GeometryNodeSetPosition')
        nb.L.new(rl.outputs[0], sp.inputs['Geometry'])
        nb.L.new(nb.comb(nb.sub(px, nb.mul(k, Ls[0])), nb.sub(py, nb.mul(k, Ls[1])), zg), sp.inputs['Position'])
        nb.L.new(sp.outputs[0], j2.inputs[0])
    sm = nb.node('GeometryNodeSetMaterial'); sm.inputs['Material'].default_value = mat
    nb.L.new(j2.outputs[0], sm.inputs['Geometry']); nb.L.new(sm.outputs[0], go.inputs[0])
    me = bpy.data.meshes.new('ArmShadowProxy')
    o = bpy.data.objects.new('ArmShadowProxy', me); coll.objects.link(o)
    md = o.modifiers.new('proj', 'NODES'); md.node_group = ng
    objs.append(o)
    # label mesa: stadium = hull(circle r 250 @ 0, circle r 250 @ -252 in y) (sun from +Y)
    R, off = 250.0, MESA_H / math.tan(math.radians(SUN_ELEV))
    th = np.linspace(0, np.pi, 97)
    up_ = np.stack([R * np.cos(th), R * np.sin(th)], 1)
    th2 = np.linspace(np.pi, 2 * np.pi, 97)
    lo_ = np.stack([R * np.cos(th2), -off + R * np.sin(th2)], 1)
    ring = np.concatenate([up_, lo_])
    co = np.concatenate([[[0.0, -off / 2]], ring])
    nr = len(ring)
    tris = np.array([[0, 1 + i, 1 + (i + 1) % nr] for i in range(nr)], np.int32)
    mm = bpy.data.meshes.new('MesaShadowProxy')
    co3 = np.zeros((len(co), 3), np.float32); co3[:, :2] = co; co3[:, 2] = zg
    mm.vertices.add(len(co3)); mm.vertices.foreach_set('co', co3.ravel())
    mm.loops.add(len(tris) * 3); mm.loops.foreach_set('vertex_index', tris.ravel())
    mm.polygons.add(len(tris)); mm.polygons.foreach_set('loop_start', np.arange(0, len(tris) * 3, 3, dtype=np.int32))
    mm.update(calc_edges=True)
    mm.materials.append(_m_shadow('M_MesaShadowProxy', 1))
    mo = bpy.data.objects.new('MesaShadowProxy', mm); coll.objects.link(mo)
    objs.append(mo)
    for ob in objs:
        ob.visible_shadow = False
        for a in ('visible_diffuse', 'visible_glossy', 'visible_transmission', 'visible_volume_scatter'):
            try:
                setattr(ob, a, False)
            except Exception:
                pass
    # fade: in over the crane f572-590, out over the dive start f644-650
    for ob in objs:
        nd = ob.data.materials[0].node_tree.nodes['shf'] if ob.data.materials else ob.modifiers[0].node_group and mat.node_tree.nodes['shf']
        for f, v in ((570, 0.0), (590, 1.0), (643, 1.0), (650, 0.0)):
            nd.outputs[0].default_value = v; nd.outputs[0].keyframe_insert('default_value', frame=f)
    return objs
