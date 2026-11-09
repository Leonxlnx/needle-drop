"""NEEDLE DROP shared look library: palette, signature marble, shared materials.

Every set imports this so the vinyl (S2), the groove walls (S1) and the desert (S3) share
one marble. Do not fork NG_Marble per set: the S2->S3 match cut depends on it being identical.
"""
import bpy
from common import hex2lin

PAL = {
    'magenta': '#FF1F8E', 'saffron': '#FFB30F', 'ultramarine': '#2236FF', 'violet': '#7B2BFF',
    'vermilion': '#FF3A1C', 'night': '#1B0A3F', 'anodised': '#2B1660', 'apricot': '#FF9A5A',
    'chalk': '#F6EFE3', 'plum': '#6B1F5C', 'cream': '#F3DFC1', 'outer_sand': '#E8895A',
    'diamond': '#0B0A14', 'chrome': '#E6E6EC', 'alu': '#C9CBD3', 'mesa_rock': '#D9452A',
}


def lin(name):
    return hex2lin(PAL[name])


# Paper-marbling bands: colour = ramp(fract(warped.x * FREQ)). Chalk vein sits at 0.70.
MARBLE_STOPS = [
    (0.00, 'night'), (0.12, 'ultramarine'), (0.30, 'ultramarine'), (0.40, 'violet'),
    (0.50, 'magenta'), (0.66, 'magenta'), (0.70, 'chalk'), (0.72, 'saffron'),
    (0.80, 'saffron'), (0.86, 'magenta'), (1.00, 'night'),
]
MARBLE_WARP, MARBLE_FREQ, MARBLE_D1, MARBLE_D2 = 3.2, 2.2, 1.0, 1.7
MARBLE_VEIN_POS = 0.70


def _sock(ng, name, io, typ, default=None):
    s = ng.interface.new_socket(name, in_out=io, socket_type=typ)
    if default is not None and hasattr(s, 'default_value'):
        s.default_value = default
    return s


def build_marble_field(nt, vec, scale=1.0, warp=None, freq=None, scale_socket=None):
    """Build the banded marble field inside ANY node tree (shader or geometry nodes).
    vec: input vector socket. Returns dict(m=fract band value 0..1, color=ramp colour, vein=0..1).
    Uses only nodes that exist in both tree types, so GN dunes follow the shader swirls exactly."""
    warp = MARBLE_WARP if warp is None else warp
    freq = MARBLE_FREQ if freq is None else freq
    N, L = nt.nodes, nt.links

    def vm(op, a, b=None, s=None, s_sock=None):
        n = N.new("ShaderNodeVectorMath"); n.operation = op
        L.new(a, n.inputs[0])
        if b is not None: L.new(b, n.inputs[1])
        if s is not None: n.inputs["Scale"].default_value = s
        if s_sock is not None: L.new(s_sock, n.inputs["Scale"])
        return n.outputs[0]

    def noise(v, sc_, det, r):
        n = N.new("ShaderNodeTexNoise"); n.noise_dimensions = "3D"
        n.inputs["Scale"].default_value = sc_; n.inputs["Detail"].default_value = det
        n.inputs["Roughness"].default_value = r
        L.new(v, n.inputs["Vector"])
        return n

    def math(op, a, bval):
        n = N.new("ShaderNodeMath"); n.operation = op
        L.new(a, n.inputs[0]); n.inputs[1].default_value = bval
        return n.outputs[0]

    half = N.new("ShaderNodeCombineXYZ")
    for k in "XYZ": half.inputs[k].default_value = 0.5
    p = vm("SCALE", vec, s_sock=scale_socket) if scale_socket is not None else vm("SCALE", vec, s=scale)
    n1 = noise(p, MARBLE_D1, 2.0, 0.5)
    q = vm("ADD", p, vm("SCALE", vm("SUBTRACT", n1.outputs["Color"], half.outputs[0]), s=warp))
    n2 = noise(q, MARBLE_D2, 3.0, 0.55)
    q2 = vm("ADD", q, vm("SCALE", vm("SUBTRACT", n2.outputs["Color"], half.outputs[0]), s=warp * 0.6))
    sep = N.new("ShaderNodeSeparateXYZ"); L.new(q2, sep.inputs[0])
    raw = math("MULTIPLY", sep.outputs["X"], freq)   # continuous band coordinate (use sin(2*pi*raw) for smooth heights)
    m = math("FRACT", raw, 0.0)
    ramp = N.new("ShaderNodeValToRGB"); cr = ramp.color_ramp; cr.interpolation = "EASE"
    while len(cr.elements) > 1: cr.elements.remove(cr.elements[-1])
    cr.elements[0].position, cr.elements[0].color = MARBLE_STOPS[0][0], (*lin(MARBLE_STOPS[0][1]), 1)
    for pos, nm in MARBLE_STOPS[1:]:
        e = cr.elements.new(pos); e.color = (*lin(nm), 1)
    L.new(m, ramp.inputs["Fac"])
    # vein: 1 at MARBLE_VEIN_POS, 0 beyond +-0.02
    vein = math("MAXIMUM", math("SUBTRACT", math("MULTIPLY", math("ABSOLUTE", math("SUBTRACT", m, MARBLE_VEIN_POS), 0.0), -50.0), -1.0), 0.0)
    return {"m": m, "raw": raw, "color": ramp.outputs["Color"], "vein": vein}


def ng_marble():
    """Shader node group NG_Marble(Vector, Scale) -> Color, m, vein (banded paper-marbling)."""
    if "NG_Marble" in bpy.data.node_groups:
        return bpy.data.node_groups["NG_Marble"]
    ng = bpy.data.node_groups.new("NG_Marble", "ShaderNodeTree")
    _sock(ng, "Vector", "INPUT", "NodeSocketVector")
    _sock(ng, "Scale", "INPUT", "NodeSocketFloat", 1.0)
    _sock(ng, "Color", "OUTPUT", "NodeSocketColor")
    _sock(ng, "m", "OUTPUT", "NodeSocketFloat")
    _sock(ng, "vein", "OUTPUT", "NodeSocketFloat")
    gi = ng.nodes.new("NodeGroupInput"); go = ng.nodes.new("NodeGroupOutput")
    f = build_marble_field(ng, gi.outputs["Vector"], scale_socket=gi.outputs["Scale"])
    ng.links.new(f["color"], go.inputs["Color"]); ng.links.new(f["m"], go.inputs["m"]); ng.links.new(f["vein"], go.inputs["vein"])
    return ng


def ng_fade_by_distance():
    """NG_FadeByDistance(near, far) -> Fac (1 near camera, 0 beyond far)."""
    if 'NG_FadeByDistance' in bpy.data.node_groups:
        return bpy.data.node_groups['NG_FadeByDistance']
    ng = bpy.data.node_groups.new('NG_FadeByDistance', 'ShaderNodeTree')
    _sock(ng, 'near', 'INPUT', 'NodeSocketFloat', 10.0)
    _sock(ng, 'far', 'INPUT', 'NodeSocketFloat', 80.0)
    _sock(ng, 'Fac', 'OUTPUT', 'NodeSocketFloat')
    N, L = ng.nodes, ng.links
    gi = N.new('NodeGroupInput'); go = N.new('NodeGroupOutput')
    cam = N.new('ShaderNodeCameraData')
    mr = N.new('ShaderNodeMapRange'); mr.clamp = True
    L.new(cam.outputs['View Distance'], mr.inputs['Value'])
    L.new(gi.outputs['near'], mr.inputs['From Min'])
    L.new(gi.outputs['far'], mr.inputs['From Max'])
    mr.inputs['To Min'].default_value = 1.0; mr.inputs['To Max'].default_value = 0.0
    L.new(mr.outputs['Result'], go.inputs['Fac'])
    return ng


def marble_material(name='M_Vinyl', scale=1.0, coord='Object', rough=0.1, coat=1.0,
                    coat_rough=0.03, value_mul=1.0):
    """Glossy marbled vinyl (or matte sand variant via rough/coat). coord: 'Object'|'Generated'|'UV'."""
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; N, L = nt.nodes, nt.links
    b = N['Principled BSDF']
    tc = N.new('ShaderNodeTexCoord')
    g = N.new('ShaderNodeGroup'); g.node_tree = ng_marble()
    g.inputs['Scale'].default_value = scale
    L.new(tc.outputs[coord], g.inputs['Vector'])
    col = g.outputs['Color']
    if value_mul != 1.0:
        hsv = N.new('ShaderNodeHueSaturation'); hsv.inputs['Value'].default_value = value_mul
        L.new(col, hsv.inputs['Color']); col = hsv.outputs['Color']
    L.new(col, b.inputs['Base Color'])
    # roughness breakup 0.08-0.15
    rn = N.new('ShaderNodeTexNoise'); rn.inputs['Scale'].default_value = 3.0 * scale
    L.new(tc.outputs[coord], rn.inputs['Vector'])
    rmr = N.new('ShaderNodeMapRange')
    rmr.inputs['To Min'].default_value = rough * 0.75; rmr.inputs['To Max'].default_value = rough * 1.4
    L.new(rn.outputs['Fac'], rmr.inputs['Value']); L.new(rmr.outputs['Result'], b.inputs['Roughness'])
    b.inputs['Coat Weight'].default_value = coat
    b.inputs['Coat Roughness'].default_value = coat_rough
    return m


def simple(name, hexname=None, rgb=None, rough=0.4, metal=0.0, coat=0.0, coat_rough=0.03,
           emission=None, emit=0.0, sheen=0.0, aniso=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    c = rgb if rgb is not None else lin(hexname)
    b.inputs['Base Color'].default_value = (*c, 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    b.inputs['Coat Weight'].default_value = coat
    b.inputs['Coat Roughness'].default_value = coat_rough
    if sheen:
        b.inputs['Sheen Weight'].default_value = sheen
    if aniso:
        b.inputs['Anisotropic'].default_value = aniso
    if emission:
        b.inputs['Emission Color'].default_value = (*lin(emission), 1)
        b.inputs['Emission Strength'].default_value = emit
    return m


def black_diamond(name='M_BlackDiamond'):
    """Black faceted high-IOR dielectric; facing -> ultramarine, grazing -> magenta specular tint."""
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; N, L = nt.nodes, nt.links
    b = N['Principled BSDF']
    b.inputs['Base Color'].default_value = (*lin('diamond'), 1)
    b.inputs['IOR'].default_value = 2.42
    b.inputs['Roughness'].default_value = 0.015
    lw = N.new('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = 0.4
    ramp = N.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = (*lin('ultramarine'), 1)
    ramp.color_ramp.elements[1].color = (*lin('magenta'), 1)
    L.new(lw.outputs['Facing'], ramp.inputs['Fac'])
    L.new(ramp.outputs['Color'], b.inputs['Specular Tint'])
    return m
