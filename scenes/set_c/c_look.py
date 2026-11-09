"""Set C look: procedural sky world, low sun, EEVEE settings, compositor (mist tint, bloom, streaks, CA, vignette)."""
import bpy, math
from c_common import *
from c_nodes import NB

SUN_STRENGTH = 11.0
SKY_GAIN = 0.7
MIST_K = 0.26


def world(sc):
    w = bpy.data.worlds.new('W_Desert'); sc.world = w; w.use_nodes = True
    nt = w.node_tree; nb = NB(nt)
    bg = nt.nodes['Background']
    tc = nb.N.new('ShaderNodeTexCoord')
    d = nb.vmath('NORMALIZE', tc.outputs['Generated'])
    _, _, dz = nb.sep(d)
    fac = nb.madd(dz, 0.5, 0.5)
    # adr1: steeper ramp -- apricot only in a thin horizon band, #9A6BEA by ~4 deg, #3646F0 by ~15 deg (no mauve mud)
    sky = nb.ramp(fac, [
        (0.0, C.hex2lin('#FFC48A')), (0.47, C.hex2lin('#FFC48A')), (0.5, C.hex2lin('#FF9A5A')),
        (0.511, C.hex2lin('#FF8A6A')), (0.535, C.hex2lin('#9A6BEA')), (0.63, C.hex2lin('#3646F0')), (1.0, C.hex2lin('#24127A'))])
    # lighting-only sky (what the sand 'sees'): more saturated ultramarine/violet, no sun glow -> violet shadows
    sky_l = nb.ramp(fac, [
        (0.0, C.hex2lin('#B0507A')), (0.47, C.hex2lin('#B0507A')), (0.5, C.hex2lin('#D0607A')),
        (0.53, C.hex2lin('#7B2BFF')), (0.62, C.hex2lin('#3A2AF0')), (1.0, C.hex2lin('#2A128A'))])
    e = math.radians(SUN_ELEV)
    sd = (0.0, math.cos(e), math.sin(e))
    dot = nb.math('MAXIMUM', nb.vmath('DOT_PRODUCT', d, sd), 0.0)
    g1 = nb.math('POWER', dot, 64.0)
    g2 = nb.math('POWER', dot, 6.0)
    glow = nb.add(nb.mul(g1, 2.2), nb.mul(g2, 0.35))
    gcol = nb.mixc(glow, (0, 0, 0, 1), C.hex2lin('#FFB070'))
    g3 = nb.mul(nb.math('POWER', dot, 4000.0), 40.0)                       # the sun disc itself (bloom / streak source)
    sky = nb.mixc(1.0, sky, gcol, 'ADD')
    sky = nb.mixc(1.0, sky, nb.mixc(g3, (0, 0, 0, 1), C.hex2lin('#FFE2B0')), 'ADD')
    # adr2: thin high cirrus streaks (camera sky only, keyed 'cirrus' on for S6) lit apricot underneath, pink away
    # from the sun, so the S6 upper sky is not an empty gradient
    dx_, dy_, _ = nb.sep(d)
    inv = nb.div(1.0, nb.math('MAXIMUM', dz, 0.03))
    cu, cv = nb.mul(dx_, inv), nb.mul(dy_, inv)
    rotc = nb.N.new('ShaderNodeVectorRotate'); rotc.rotation_type = 'Z_AXIS'; rotc.inputs['Angle'].default_value = 0.5
    nb._in(rotc.inputs['Vector'], nb.comb(cu, cv, 0.0))
    ru, rv, _ = nb.sep(rotc.outputs[0])
    warp = nb.noise(nb.comb(nb.mul(ru, 0.8), nb.mul(rv, 0.8), 0.0), 1.0, 2.0, 0.5)
    cn = nb.noise(nb.comb(nb.mul(ru, 0.35), nb.add(nb.mul(rv, 5.5), nb.mul(warp, 2.5)), 1.7), 1.0, 4.0, 0.62)
    cmask = nb.mul(nb.mul(nb.ss(0.56, 0.74, cn), nb.ss(0.03, 0.10, dz)), nb.sub(1.0, nb.ss(0.30, 0.62, dz)))
    cir = nb.value(0.0, 'cirrus')
    ccol = nb.mixc(nb.ss(0.2, 0.9, dot), C.hex2lin('#F07AB8'), C.hex2lin('#FFB070'))
    sky = nb.mixc(nb.mul(cmask, nb.mul(cir, 0.55)), sky, ccol)
    # +-0.5 % dither against banding
    nz = nb.noise(nb.vmath('SCALE', d, scale=900.0), 1.0, 0.0, 0.5)
    dith = nb.madd(nz, 0.01, 0.995)
    sky = nb.mixc(1.0, sky, nb.comb(dith, dith, dith), 'MULTIPLY')
    lp = nt.nodes.new('ShaderNodeLightPath')
    sky_l = nb.mixc(1.0, sky_l, nb.comb(dith, dith, dith), 'MULTIPLY')
    sky = nb.mixc(lp.outputs['Is Camera Ray'], sky_l, sky)
    nb.L.new(sky, bg.inputs['Color'])
    bg.inputs['Strength'].default_value = SKY_GAIN
    ms = w.mist_settings
    ms.start = 300.0; ms.depth = 6000.0; ms.falloff = 'LINEAR'
    return w


def sun(sc):
    ld = bpy.data.lights.new('Sun', 'SUN')
    ld.energy = SUN_STRENGTH; ld.color = C.hex2lin('#FFC890'); ld.angle = math.radians(0.6)
    try:
        ld.use_shadow_jitter = False
        ld.shadow_filter_radius = 1.6
    except Exception:
        pass
    o = bpy.data.objects.new('Sun', ld); sc.collection.objects.link(o)
    o.rotation_euler = (math.radians(-(90.0 - SUN_ELEV)), 0.0, 0.0)
    return o


def render_settings(sc):
    C.setup_render(sc, res=(2560, 1440), samples=48)
    C.color(sc, 'AgX - Punchy', exposure=0.2)
    e = sc.eevee
    e.shadow_ray_count = 1; e.shadow_step_count = 6
    e.shadow_resolution_scale = 1.0
    try:
        e.shadow_pool_size = '1024'
    except Exception as ex:
        print('WARN pool', ex)
    e.use_raytracing = True
    try:
        e.ray_tracing_method = 'SCREEN'
        ro = e.ray_tracing_options
        ro.resolution_scale = '2'; ro.trace_max_roughness = 0.5
        ro.use_denoise = True; ro.denoise_spatial = True; ro.denoise_temporal = True; ro.denoise_bilateral = True
    except Exception as ex:
        print('WARN rt opts', ex)
    e.use_fast_gi = True
    try:
        e.fast_gi_resolution = '2'
    except Exception:
        pass
    e.clamp_surface_indirect = 10.0
    e.use_overscan = True; e.overscan_size = 0.03
    e.motion_blur_steps = 1
    sc.render.motion_blur_shutter = 0.5; sc.render.motion_blur_position = 'CENTER'
    sc.render.filter_size = 1.5
    sc.render.image_settings.color_depth = '16'
    sc.render.image_settings.compression = 15
    sc.view_layers[0].use_pass_mist = True
    sc.view_layers[0].use_pass_z = True
    sc.frame_start, sc.frame_end = F0, F1
    sc.render.fps = 24


def compositor(sc):
    ng = bpy.data.node_groups.new('Comp_C', 'CompositorNodeTree')
    sc.compositing_node_group = ng
    ng.interface.new_socket('Image', in_out='OUTPUT', socket_type='NodeSocketColor')
    nb = NB(ng, 'COMP')
    rl = nb.N.new('CompositorNodeRLayers')
    img = rl.outputs['Image']
    mist = rl.outputs['Mist'] if 'Mist' in rl.outputs else None
    if mist is not None:
        z = rl.outputs['Depth'] if 'Depth' in rl.outputs else None
        fac = nb.mul(mist, MIST_K); fac.node.name = 'MistK'
        if z is not None:
            fac = nb.mul(fac, nb.math('LESS_THAN', z, 100000.0))
            far = nb.maprange(z, 1500.0, 4000.0, 0.0, 1.0)
            mcol = nb.mixc(far, (*C.hex2lin('#FF9A5A'), 1.0), (*C.hex2lin('#D98CC0'), 1.0))
            img = nb.mixc(fac, img, mcol)
        else:
            img = nb.mixc(fac, img, (*C.hex2lin('#FF9A5A'), 1.0))
    gl = nb.N.new('CompositorNodeGlare'); gl.name = 'Bloom'
    gl.inputs['Type'].default_value = 'Bloom'
    gl.inputs['Threshold'].default_value = 1.2
    gl.inputs['Strength'].default_value = 0.35
    gl.inputs['Size'].default_value = 0.7
    nb._in(gl.inputs['Image'], img); img = gl.outputs['Image']
    st = nb.N.new('CompositorNodeGlare'); st.name = 'Streaks'
    st.inputs['Type'].default_value = 'Streaks'
    st.inputs['Threshold'].default_value = 6.0
    st.inputs['Strength'].default_value = 0.0
    try:
        st.inputs['Streaks'].default_value = 4; st.inputs['Fade'].default_value = 0.85
    except Exception:
        pass
    nb._in(st.inputs['Image'], img); img = st.outputs['Image']
    ld = nb.N.new('CompositorNodeLensdist')
    ld.inputs['Dispersion'].default_value = 0.004
    nb._in(ld.inputs['Image'], img); img = ld.outputs['Image']
    hs = nb.N.new('CompositorNodeHueSat')
    hs.inputs['Saturation'].default_value = 1.06
    nb._in(hs.inputs['Image'], img); img = hs.outputs['Image']
    ic = nb.N.new('CompositorNodeImageCoordinates')
    nb._in(ic.inputs['Image'], img)
    x, y, _ = nb.sep(ic.outputs['Normalized'])
    u = nb.mul(nb.sub(x, 0.5), 2.0); v = nb.mul(nb.sub(y, 0.5), 2.0)
    dd = nb.mul(nb.math('SQRT', nb.add(nb.mul(u, u), nb.mul(v, v))), 0.7071)
    vig = nb.sub(1.0, nb.mul(nb.ss(0.45, 1.0, dd), 0.12))
    img = nb.mixc(1.0, img, vig, 'MULTIPLY')
    out = nb.N.new('NodeGroupOutput')
    nb.L.new(img, out.inputs[0])
    return ng
