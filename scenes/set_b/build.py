"""SET B - THE MACHINE (S2, global frames 121-288). Rebuilds blend/set_b.blend from scratch.

Also writes blend/tonearm_asset.blend (collection 'TonearmAsset', metres, origin = arm pivot)
and data/handoff.json key 'S2_end' (record-space point / up / width under the f288 camera).

Run:  tools/brun.sh --threads 6 -- --python scenes/set_b/build.py
"""
import bpy, bmesh, os, sys, math, json
import numpy as np
from mathutils import Vector, Matrix, Quaternion

ROOT = os.getcwd(); sys.path.insert(0, os.path.join(ROOT, 'tools'))
import common as C, nd_lib as ND

F0, F1 = 121, 288
FPS = 24
MARBLE_SCALE = 12.0           # marble field input = record object coords (m) * MARBLE_SCALE
MARBLE_FREQ_REC = 4.4         # band frequency of the record's CLOSE-UP field (= the S2_end handoff field):
                              # same swirl shapes, 2x more combed bands -> filigree at the f288 match cut
MARBLE_FREQ_LO = 2.2          # shared ND default: bold legible swirls at mid/hold range (director 02:05 note)
LOD_NEAR, LOD_FAR = 0.085, 0.20   # camera view distance (m): <= near -> freq 4.4 field, >= far -> freq 2.2 field
VEIN_EMIT = []                # ShaderNodeValue multipliers of the chalk-vein emission (keyed on in the capture)
COVE_REFL_K = 0.35            # cyc emission multiplier for non-camera rays (probe reflections)
COVE_K = []
COVE_STRENGTH = []
EXPO_END = -0.56              # f280-288 exposure (S3 f289 mean V 0.542: match within 5%)
VEIN_EMIT_E = 2.5             # chalk-vein emission at the close-up (white point)
STREAK_E, STREAK_ROT = 2.0, 25.0   # VinylStreak power (W) and azimuth offset of its solve point (deg)
GLINT_E = 0.02
LABELKICK_E = 9.0           # W; label kick spot (label paper + ink only)
COATCUE_AMP = 0.12            # peak coat-cue emission at the left frame edge (f283-288)
COATCUE_VALS = []
VINYL_BASE_SPEC = 0.12        # base-layer specular of the vinyl (rough, groove-tilted): kept weak
COAT_GRAZE_MIN = 0.45         # coat weight at grazing view (facing >= 0.85)
RPM_DEG = 200.0               # 33 1/3 rpm in deg/s
# light positions needed by the vinyl's analytic groove-sheen (radial 'bowtie') term
RIM_LOC = (0.55, 0.78, 0.30)
BACK_LOC = (0.50, 0.95, 0.62)
POOL_XY = (0.62, 0.80)         # cyc light-pool centre (world xy, metres)
TAU = 2 * math.pi
L = ND.lin

sc = C.reset()
C.setup_render(sc, res=(2560, 1440), samples=24)
sc.render.image_settings.color_depth = '16'   # QA: S2 frames were 8-bit (PNG RGB 16-bit like S1/S3)
C.color(sc, 'AgX - Punchy', exposure=-0.5)
sc.frame_start, sc.frame_end = F0, F1
sc.render.motion_blur_shutter = 0.25
sc.render.filter_size = 1.5
e = sc.eevee
e.motion_blur_steps = 1
try: e.motion_blur_max = 96
except Exception: pass
e.use_raytracing = True
e.ray_tracing_method = 'SCREEN'
rto = e.ray_tracing_options
for k, v in (('resolution_scale', '2'), ('use_denoise', True), ('denoise_spatial', True), ('denoise_temporal', True),
             ('denoise_bilateral', True), ('trace_max_roughness', 0.5)):
    try: setattr(rto, k, v)
    except Exception as ex: print('RTO_SKIP', k, ex)
e.use_fast_gi = True
try: e.fast_gi_resolution = '2'
except Exception: pass
e.shadow_ray_count = 1; e.shadow_step_count = 6; e.shadow_resolution_scale = 1.0
e.clamp_surface_indirect = 10.0
e.bokeh_max_size = 100.0; e.use_bokeh_jittered = False
e.use_overscan = True; e.overscan_size = 3.0
try: e.gi_cubemap_resolution = '512'
except Exception: pass

COL_TT = bpy.data.collections.new('Turntable'); sc.collection.children.link(COL_TT)
COL_ARM = bpy.data.collections.new('TonearmAsset'); sc.collection.children.link(COL_ARM)
COL_STUDIO = bpy.data.collections.new('Studio'); sc.collection.children.link(COL_STUDIO)

# ------------------------------------------------------------------ helpers

def link(ob, coll):
    coll.objects.link(ob); return ob


def new_obj(name, data, coll, mats=(), parent=None, loc=(0, 0, 0), rot=None):
    ob = bpy.data.objects.new(name, data); coll.objects.link(ob)
    if data is not None and hasattr(data, 'materials'):
        for m in mats: data.materials.append(m)
    if parent is not None: ob.parent = parent
    ob.location = loc
    if rot is not None:
        if isinstance(rot, Quaternion): ob.rotation_mode = 'QUATERNION'; ob.rotation_quaternion = rot
        else: ob.rotation_euler = rot
    return ob


def empty(name, coll, loc=(0, 0, 0), parent=None, size=0.02):
    ob = bpy.data.objects.new(name, None); coll.objects.link(ob)
    ob.empty_display_size = size; ob.location = loc
    if parent is not None: ob.parent = parent
    return ob


def mesh(name, verts, faces, smooth=True, mat_idx=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(map(float, v)) for v in verts], [], [tuple(int(i) for i in f) for f in faces])
    me.validate(); me.update()
    if smooth: me.shade_smooth()
    if mat_idx is not None:
        me.polygons.foreach_set('material_index', np.asarray(mat_idx, dtype=np.int32))
    return me


def hard(ob, w=0.0008, segs=3, angle=35.0, harden=True, wn=True):
    b = ob.modifiers.new('Bevel', 'BEVEL')
    b.width = w; b.segments = segs; b.limit_method = 'ANGLE'; b.angle_limit = math.radians(angle)
    b.use_clamp_overlap = True; b.harden_normals = harden
    try: b.miter_outer = 'MITER_ARC'
    except Exception: pass
    if wn:
        m = ob.modifiers.new('WeightedNormal', 'WEIGHTED_NORMAL'); m.keep_sharp = True; m.weight = 50
    return ob


def rrect(w, d, r, n=8):
    pts = []
    r = min(r, w / 2 - 1e-6, d / 2 - 1e-6)
    for cx, cy, a0 in ((w / 2 - r, d / 2 - r, 0), (-w / 2 + r, d / 2 - r, 90), (-w / 2 + r, -d / 2 + r, 180), (w / 2 - r, -d / 2 + r, 270)):
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n); pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def circle(r, n):
    return [(r * math.cos(TAU * i / n), r * math.sin(TAU * i / n)) for i in range(n)]


def prism(name, outline, z0, z1):
    n = len(outline)
    verts = [(x, y, z0) for x, y in outline] + [(x, y, z1) for x, y in outline]
    faces = [tuple(reversed(range(n))), tuple(range(n, 2 * n))] + [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    return mesh(name, verts, faces)


def cyl(name, r, h, n=48, z0=0.0):
    return prism(name, circle(r, n), z0, z0 + h)


def lathe(name, prof, n=256, mats=None):
    """Revolve a closed (axis-to-axis) profile [(r,z),...] about Z."""
    bm = bmesh.new(); rows = []
    for (r, z) in prof:
        if r < 1e-9:
            v = bm.verts.new((0, 0, z)); rows.append([v] * n)
        else:
            rows.append([bm.verts.new((r * math.cos(TAU * k / n), r * math.sin(TAU * k / n), z)) for k in range(n)])
    for j in range(len(prof) - 1):
        A, B = rows[j], rows[j + 1]
        for k in range(n):
            k2 = (k + 1) % n; u = []
            for v in (A[k], A[k2], B[k2], B[k]):
                if v not in u: u.append(v)
            if len(u) >= 3:
                f = bm.faces.new(u); f.smooth = True
                f.material_index = mats[j] if mats else 0
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); return me


def frame_from(t, up=Vector((0, 0, 1))):
    t = t.normalized(); a = up.cross(t)
    if a.length < 1e-6: a = Vector((1, 0, 0)).cross(t)
    a.normalize(); b = t.cross(a)
    return a, b


def sweep(name, pts, section, closed_section=True):
    """Sweep a 2D section [(x,y)] along 3D points (parallel transport frames)."""
    pts = [Vector(p) for p in pts]; n = len(section); verts = []; faces = []
    tan_prev = None; a = b = None
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        if a is None:
            a, b = frame_from(t)
        else:
            rot = tan_prev.rotation_difference(t); a = rot @ a; b = rot @ b
        tan_prev = t
        for (x, y) in section: verts.append(p + a * x + b * y)
    for i in range(len(pts) - 1):
        for k in range(n if closed_section else n - 1):
            k2 = (k + 1) % n
            faces.append((i * n + k, i * n + k2, (i + 1) * n + k2, (i + 1) * n + k))
    faces.append(tuple(reversed(range(n)))); faces.append(tuple(range((len(pts) - 1) * n, len(pts) * n)))
    me = mesh(name, verts, faces)
    bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    return me


def bezier_curve(name, pts, handles, radius, coll, mat, parent=None, res=24, bres=6):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'
    cu.resolution_u = res; cu.bevel_mode = 'ROUND'; cu.bevel_depth = radius; cu.bevel_resolution = bres
    cu.use_fill_caps = True
    sp = cu.splines.new('BEZIER'); sp.bezier_points.add(len(pts) - 1)
    for bp, p, (hl, hr) in zip(sp.bezier_points, pts, handles):
        bp.handle_left_type = bp.handle_right_type = 'FREE'
        bp.co = p; bp.handle_left = hl; bp.handle_right = hr
    ob = new_obj(name, cu, coll, [mat], parent=parent)
    return ob


FONT = bpy.data.fonts.load('C:/Windows/Fonts/ariblk.ttf')


def text_mesh(name, body, size, extrude=0.0, align='CENTER'):
    cu = bpy.data.curves.new(name, 'FONT'); cu.body = body; cu.font = FONT; cu.size = size
    cu.align_x = align; cu.align_y = 'CENTER'; cu.extrude = extrude; cu.resolution_u = 8
    ob = bpy.data.objects.new(name + '_tmp', cu); sc.collection.objects.link(ob)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    bpy.data.objects.remove(ob); bpy.data.curves.remove(cu)
    me.name = name
    return me

# ------------------------------------------------------------------ materials


def nodes(m):
    return m.node_tree.nodes, m.node_tree.links, m.node_tree.nodes['Principled BSDF']


def add_bump(m, height_socket, strength, distance=0.001, target='Normal'):
    N, Lk, b = nodes(m)
    bu = N.new('ShaderNodeBump'); bu.inputs['Strength'].default_value = strength; bu.inputs['Distance'].default_value = distance
    Lk.new(height_socket, bu.inputs['Height']); Lk.new(bu.outputs['Normal'], b.inputs[target])
    return bu


def mat_lacquer():
    m = ND.simple('M_VermilionLacquer', 'vermilion', rough=0.32, coat=1.0, coat_rough=0.04)
    N, Lk, b = nodes(m)
    tc = N.new('ShaderNodeTexCoord'); nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 1500.0
    nz.inputs['Detail'].default_value = 2.0
    Lk.new(tc.outputs['Object'], nz.inputs['Vector'])
    fd = N.new('ShaderNodeGroup'); fd.node_tree = ND.ng_fade_by_distance()
    fd.inputs['near'].default_value = 0.12; fd.inputs['far'].default_value = 0.5
    mul = N.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'
    Lk.new(nz.outputs['Fac'], mul.inputs[0]); Lk.new(fd.outputs['Fac'], mul.inputs[1])
    add_bump(m, mul.outputs[0], 0.03, 0.0005, 'Coat Normal')
    return m


def mat_brushed(name, hexname, rough, metal=1.0, mode='axial_z', scale=(3000, 3000, 40), strength=0.08):
    m = ND.simple(name, hexname, rough=rough, metal=metal)
    N, Lk, b = nodes(m)
    tc = N.new('ShaderNodeTexCoord')
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Detail'].default_value = 4.0; nz.inputs['Roughness'].default_value = 0.6
    if mode == 'radial':
        # concentric brushing: noise of radius only
        sep = N.new('ShaderNodeSeparateXYZ'); Lk.new(tc.outputs['Object'], sep.inputs[0])
        vl = N.new('ShaderNodeVectorMath'); vl.operation = 'LENGTH'
        cmb = N.new('ShaderNodeCombineXYZ'); Lk.new(sep.outputs['X'], cmb.inputs['X']); Lk.new(sep.outputs['Y'], cmb.inputs['Y'])
        Lk.new(cmb.outputs[0], vl.inputs[0])
        nz.noise_dimensions = '1D'; nz.inputs['Scale'].default_value = scale[0]
        Lk.new(vl.outputs['Value'], nz.inputs['W'])
    else:
        mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = scale
        Lk.new(tc.outputs['Object'], mp.inputs['Vector']); Lk.new(mp.outputs['Vector'], nz.inputs['Vector'])
    add_bump(m, nz.outputs['Fac'], strength, 0.0002)
    # roughness breakup
    rmr = N.new('ShaderNodeMapRange'); rmr.inputs['To Min'].default_value = rough * 0.75; rmr.inputs['To Max'].default_value = rough * 1.35
    Lk.new(nz.outputs['Fac'], rmr.inputs['Value']); Lk.new(rmr.outputs['Result'], b.inputs['Roughness'])
    return m


def mat_chrome(name='M_Chrome', rough=0.06):
    m = ND.simple(name, 'chrome', rough=rough, metal=1.0)
    N, Lk, b = nodes(m)
    tc = N.new('ShaderNodeTexCoord'); nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 900.0
    nz.inputs['Detail'].default_value = 6.0
    Lk.new(tc.outputs['Object'], nz.inputs['Vector'])
    rmr = N.new('ShaderNodeMapRange'); rmr.inputs['To Min'].default_value = 0.04; rmr.inputs['To Max'].default_value = 0.09
    Lk.new(nz.outputs['Fac'], rmr.inputs['Value']); Lk.new(rmr.outputs['Result'], b.inputs['Roughness'])
    return m


def mat_felt():
    m = ND.simple('M_Felt', 'ultramarine', rough=1.0, sheen=1.0)
    N, Lk, b = nodes(m)
    b.inputs['Sheen Roughness'].default_value = 0.3
    b.inputs['Sheen Tint'].default_value = (*C.hex2lin('#9AA6FF'), 1)
    tc = N.new('ShaderNodeTexCoord'); nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 2500.0
    nz.inputs['Detail'].default_value = 8.0
    Lk.new(tc.outputs['Object'], nz.inputs['Vector'])
    add_bump(m, nz.outputs['Fac'], 0.2, 0.0003)
    return m


def mat_label():
    # 0.65x saffron albedo, satin paper: reads as true Saffron (hue ~40 deg) under the near-neutral key
    # (green nudged +17% so the warm key + AgX land the paper on Saffron's 40-ish deg hue instead of 35)
    m = ND.simple('M_LabelPaper', rgb=(0.78, 0.78 * 0.53, 0.005), rough=0.45)
    N, Lk, b = nodes(m)
    tc = N.new('ShaderNodeTexCoord'); nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 4000.0
    nz.inputs['Detail'].default_value = 6.0
    Lk.new(tc.outputs['Object'], nz.inputs['Vector'])
    # paper fibres (0.25 mm) are ~2 px at the hold and rotate with the record: fade them out by camera distance so
    # they only appear in the capture close-ups (no crawl on the spinning label)
    fd = N.new('ShaderNodeGroup'); fd.node_tree = ND.ng_fade_by_distance()
    fd.inputs['near'].default_value = 0.06; fd.inputs['far'].default_value = 0.16
    mu = N.new('ShaderNodeMath'); mu.operation = 'MULTIPLY'
    Lk.new(nz.outputs['Fac'], mu.inputs[0]); Lk.new(fd.outputs['Fac'], mu.inputs[1])
    add_bump(m, mu.outputs[0], 0.05, 0.0002)
    return m


def mat_cove():
    m = bpy.data.materials.new('M_Cove'); m.use_nodes = True
    N, Lk, b = nodes(m)
    b.inputs['Base Color'].default_value = (*[c * 0.6 for c in L('night')], 1)
    b.inputs['Roughness'].default_value = 0.38
    b.inputs['Coat Weight'].default_value = 0.6; b.inputs['Coat Roughness'].default_value = 0.12
    geo = N.new('ShaderNodeNewGeometry'); sep = N.new('ShaderNodeSeparateXYZ'); Lk.new(geo.outputs['Position'], sep.inputs[0])
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 800.0; Lk.new(geo.outputs['Position'], nz.inputs['Vector'])
    add = N.new('ShaderNodeMath'); add.operation = 'MULTIPLY_ADD'
    Lk.new(nz.outputs['Fac'], add.inputs[0]); add.inputs[1].default_value = 0.02; Lk.new(sep.outputs['Z'], add.inputs[2])
    ramp = N.new('ShaderNodeValToRGB'); cr = ramp.color_ramp; cr.interpolation = 'EASE'
    cr.elements[0].position = 0.0; cr.elements[0].color = (*L('night'), 1)
    cr.elements[1].position = 1.0; cr.elements[1].color = (*L('night'), 1)
    e1 = cr.elements.new(0.18); e1.color = (*[c * 1.4 for c in L('night')], 1)
    e2 = cr.elements.new(0.42); e2.color = (*L('ultramarine'), 1)
    e3 = cr.elements.new(0.70); e3.color = (*L('violet'), 1)
    mr = N.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = 0.0; mr.inputs['From Max'].default_value = 0.65
    Lk.new(add.outputs[0], mr.inputs['Value']); Lk.new(mr.outputs['Result'], ramp.inputs['Fac'])
    # soft magenta -> ultramarine light pool on the cyc behind the turntable (as seen from the hold camera)
    pc = N.new('ShaderNodeCombineXYZ'); pc.inputs['X'].default_value = POOL_XY[0]; pc.inputs['Y'].default_value = POOL_XY[1]
    pxy = N.new('ShaderNodeCombineXYZ'); Lk.new(sep.outputs['X'], pxy.inputs['X']); Lk.new(sep.outputs['Y'], pxy.inputs['Y'])
    dd = N.new('ShaderNodeVectorMath'); dd.operation = 'DISTANCE'; Lk.new(pxy.outputs[0], dd.inputs[0]); Lk.new(pc.outputs[0], dd.inputs[1])
    g1 = N.new('ShaderNodeMath'); g1.operation = 'DIVIDE'; Lk.new(dd.outputs['Value'], g1.inputs[0]); g1.inputs[1].default_value = 0.62
    g2 = N.new('ShaderNodeMath'); g2.operation = 'POWER'; Lk.new(g1.outputs[0], g2.inputs[0]); g2.inputs[1].default_value = 2.0
    g3 = N.new('ShaderNodeMath'); g3.operation = 'MULTIPLY'; Lk.new(g2.outputs[0], g3.inputs[0]); g3.inputs[1].default_value = -1.0
    g4 = N.new('ShaderNodeMath'); g4.operation = 'EXPONENT'; Lk.new(g3.outputs[0], g4.inputs[0])
    pr = N.new('ShaderNodeValToRGB'); pcr = pr.color_ramp; pcr.interpolation = 'EASE'
    pcr.elements[0].position = 0.0; pcr.elements[0].color = (0, 0, 0, 1)
    pcr.elements[1].position = 1.0; pcr.elements[1].color = (*[c * 1.5 for c in L('magenta')], 1)
    e_ = pcr.elements.new(0.35); e_.color = (*[c * 0.9 for c in L('ultramarine')], 1)
    e_ = pcr.elements.new(0.70); e_.color = (*[c * 1.1 for c in L('violet')], 1)
    Lk.new(g4.outputs[0], pr.inputs['Fac'])
    ad_ = N.new('ShaderNodeMix'); ad_.data_type = 'RGBA'; ad_.blend_type = 'ADD'; ad_.inputs['Factor'].default_value = 1.0
    Lk.new(ramp.outputs['Color'], ad_.inputs[6]); Lk.new(pr.outputs['Color'], ad_.inputs[7])
    Lk.new(ad_.outputs[2], b.inputs['Emission Color'])
    # camera sees the full cyc; non-camera rays (sphere-probe capture -> off-screen reflections on the vinyl coat)
    # see it dimmed, so the far half of the record reflects a dark violet room instead of a milky lilac wall
    lp = N.new('ShaderNodeLightPath')
    kv_ = N.new('ShaderNodeValue'); kv_.outputs[0].default_value = COVE_REFL_K; kv_.label = 'cove_refl_k'
    one_m = N.new('ShaderNodeMath'); one_m.operation = 'SUBTRACT'; one_m.inputs[0].default_value = 1.0; Lk.new(kv_.outputs[0], one_m.inputs[1])
    fac_ = N.new('ShaderNodeMath'); fac_.operation = 'MULTIPLY_ADD'
    Lk.new(lp.outputs['Is Camera Ray'], fac_.inputs[0]); Lk.new(one_m.outputs[0], fac_.inputs[1]); Lk.new(kv_.outputs[0], fac_.inputs[2])
    st_ = N.new('ShaderNodeMath'); st_.operation = 'MULTIPLY'; Lk.new(fac_.outputs[0], st_.inputs[0]); st_.inputs[1].default_value = 0.40
    COVE_STRENGTH.append(st_.inputs[1])
    Lk.new(st_.outputs[0], b.inputs['Emission Strength'])
    COVE_K.append(kv_)
    return m


def mat_emit(name, hexname, strength, rgb=None):
    m = bpy.data.materials.new(name); m.use_nodes = True
    N, Lk, b = nodes(m)
    c = rgb if rgb is not None else L(hexname)
    b.inputs['Base Color'].default_value = (*c, 1); b.inputs['Roughness'].default_value = 0.2
    b.inputs['Emission Color'].default_value = (*c, 1); b.inputs['Emission Strength'].default_value = strength
    b.inputs['Coat Weight'].default_value = 1.0; b.inputs['Coat Roughness'].default_value = 0.05
    return m


SHEEN_VALS = {}     # ShaderNodeValue nodes (strength multipliers of the bowtie terms) to keyframe later


def mat_vinyl(name, grooved=True):
    """Marbled vinyl in record object space. Zones by radius; analytic groove normals (no bump derivatives).
    Colour = ND banded marble field at MARBLE_SCALE with band frequency MARBLE_FREQ_REC (identical field to the
    S2_end handoff), plus a chalk-vein overlay whose width grows with camera distance (>= ~2 px at the hold,
    identical to the shared ramp up close). Groove sheen = analytic radial bowtie highlight of the rim and back
    lights (anisotropic groove reflection, faked without aliasing) in the programme area."""
    m = bpy.data.materials.new(name); m.use_nodes = True
    N, Lk, b = nodes(m)
    tc = N.new('ShaderNodeTexCoord')

    def M(op, a, bv=None, c=None):
        n = N.new('ShaderNodeMath'); n.operation = op
        for i, x in enumerate((a, bv, c)):
            if x is None: continue
            if isinstance(x, (int, float)): n.inputs[i].default_value = x
            else: Lk.new(x, n.inputs[i])
        return n.outputs[0]

    def VM(op, a, bv=None, scale=None):
        n = N.new('ShaderNodeVectorMath'); n.operation = op
        Lk.new(a, n.inputs[0])
        if bv is not None: Lk.new(bv, n.inputs[1])
        if scale is not None:
            if isinstance(scale, (int, float)): n.inputs['Scale'].default_value = scale
            else: Lk.new(scale, n.inputs['Scale'])
        return n

    def vconst(x, y, z):
        n = N.new('ShaderNodeCombineXYZ'); n.inputs['X'].default_value = x; n.inputs['Y'].default_value = y; n.inputs['Z'].default_value = z
        return n.outputs[0]

    # Marble LOD: ONE warped field (shared noise), two band frequencies. freq 2.2 (bold swirls) at mid/hold range,
    # freq 4.4 (= the S2_end handoff field, identical to build_marble_field(freq=4.4) since raw = X*freq) up close.
    # Colour + chalk vein are computed per field and only the final colours are cross-faded by camera distance.
    F = ND.build_marble_field(m.node_tree, tc.outputs['Object'], scale=MARBLE_SCALE, freq=MARBLE_FREQ_LO)
    m_hi = M('FRACT', M('MULTIPLY', F['raw'], MARBLE_FREQ_REC / MARBLE_FREQ_LO))
    ramp_hi = N.new('ShaderNodeValToRGB'); crh = ramp_hi.color_ramp; crh.interpolation = 'EASE'
    while len(crh.elements) > 1: crh.elements.remove(crh.elements[-1])
    crh.elements[0].position, crh.elements[0].color = ND.MARBLE_STOPS[0][0], (*L(ND.MARBLE_STOPS[0][1]), 1)
    for pos_, nm_ in ND.MARBLE_STOPS[1:]:
        e_ = crh.elements.new(pos_); e_.color = (*L(nm_), 1)
    Lk.new(m_hi, ramp_hi.inputs['Fac'])
    # distance-widened chalk vein
    fdv = N.new('ShaderNodeGroup'); fdv.node_tree = ND.ng_fade_by_distance()
    fdv.inputs['near'].default_value = 0.07; fdv.inputs['far'].default_value = 0.40
    w = M("MULTIPLY_ADD", M("SUBTRACT", 1.0, fdv.outputs["Fac"]), 0.016, 0.014)

    def veined(mm, col):
        vd = M('DIVIDE', M('ABSOLUTE', M('SUBTRACT', mm, ND.MARBLE_VEIN_POS)), w)
        vein = M('POWER', M('MAXIMUM', M('SUBTRACT', 1.0, vd), 0.0), 1.5)
        mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MIX'
        Lk.new(vein, mx.inputs['Factor']); Lk.new(col, mx.inputs[6]); mx.inputs[7].default_value = (*L('chalk'), 1)
        return mx.outputs[2], vein
    col_lo, vein_lo = veined(F['m'], F['color'])
    col_hi, vein_hi = veined(m_hi, ramp_hi.outputs['Color'])
    lod = N.new('ShaderNodeGroup'); lod.node_tree = ND.ng_fade_by_distance()
    lod.inputs['near'].default_value = LOD_NEAR; lod.inputs['far'].default_value = LOD_FAR
    mxl = N.new('ShaderNodeMix'); mxl.data_type = 'RGBA'; mxl.blend_type = 'MIX'
    Lk.new(lod.outputs['Fac'], mxl.inputs['Factor']); Lk.new(col_lo, mxl.inputs[6]); Lk.new(col_hi, mxl.inputs[7])
    vein = M('ADD', M('MULTIPLY', vein_lo, M('SUBTRACT', 1.0, lod.outputs['Fac'])), M('MULTIPLY', vein_hi, lod.outputs['Fac']))
    base_col = mxl.outputs[2]
    b.inputs['Coat Weight'].default_value = 1.0; b.inputs['Coat Roughness'].default_value = 0.03
    b.inputs["Specular IOR Level"].default_value = VINYL_BASE_SPEC
    lw_ = N.new('ShaderNodeLayerWeight'); lw_.inputs['Blend'].default_value = 0.5
    gz_ = N.new('ShaderNodeMapRange'); gz_.interpolation_type = 'SMOOTHSTEP'
    gz_.inputs['From Min'].default_value = 0.50; gz_.inputs['From Max'].default_value = 0.85
    gz_.inputs['To Min'].default_value = 1.0; gz_.inputs['To Max'].default_value = COAT_GRAZE_MIN
    Lk.new(lw_.outputs['Facing'], gz_.inputs['Value']); Lk.new(gz_.outputs['Result'], b.inputs['Coat Weight'])
    # chalk veins become the white point of the close-up (keyed on in the capture only)
    ve_ = N.new('ShaderNodeValue'); ve_.outputs[0].default_value = 0.0; ve_.label = 'vein_emit'
    VEIN_EMIT.append(ve_)
    vein_em = VM('SCALE', vconst(*L('chalk')), scale=M('MULTIPLY', vein, ve_.outputs[0])).outputs[0]
    if not grooved:
        Lk.new(base_col, b.inputs['Base Color'])
        b.inputs['Roughness'].default_value = 0.10
        Lk.new(vein_em, b.inputs['Emission Color']); b.inputs['Emission Strength'].default_value = 1.0
        return m
    sep = N.new('ShaderNodeSeparateXYZ'); Lk.new(tc.outputs['Object'], sep.inputs[0])
    cxy = N.new('ShaderNodeCombineXYZ'); Lk.new(sep.outputs['X'], cxy.inputs['X']); Lk.new(sep.outputs['Y'], cxy.inputs['Y'])
    ln = N.new('ShaderNodeVectorMath'); ln.operation = 'LENGTH'; Lk.new(cxy.outputs[0], ln.inputs[0])
    r = ln.outputs['Value']
    nrm = N.new('ShaderNodeVectorMath'); nrm.operation = 'NORMALIZE'; Lk.new(cxy.outputs[0], nrm.inputs[0])

    def band(lo, hi, soft):
        n1 = N.new('ShaderNodeMapRange'); n1.interpolation_type = 'SMOOTHSTEP'
        n1.inputs['From Min'].default_value = lo - soft; n1.inputs['From Max'].default_value = lo + soft
        Lk.new(r, n1.inputs['Value'])
        n2 = N.new('ShaderNodeMapRange'); n2.interpolation_type = 'SMOOTHSTEP'
        n2.inputs['From Min'].default_value = hi + soft; n2.inputs['From Max'].default_value = hi - soft
        Lk.new(r, n2.inputs['Value'])
        return M('MULTIPLY', n1.outputs['Result'], n2.outputs['Result'])
    prog = band(0.0985, 0.1458, 0.0012)
    gaps = None
    for gr in (0.137, 0.128, 0.119, 0.108):
        gb = band(gr - 0.0007, gr + 0.0007, 0.00015)        # 1.4 mm matte track gaps
        gaps = gb if gaps is None else M('ADD', gaps, gb)
    groove = M('MULTIPLY', prog, M('SUBTRACT', 1.0, gaps))
    # gaps read as darker matte rings that break the coat streak
    gdk = N.new('ShaderNodeMix'); gdk.data_type = 'RGBA'; gdk.blend_type = 'MULTIPLY'
    Lk.new(gaps, gdk.inputs['Factor']); Lk.new(base_col, gdk.inputs[6]); gdk.inputs[7].default_value = (0.55, 0.55, 0.55, 1)
    Lk.new(gdk.outputs[2], b.inputs['Base Color'])
    Lk.new(M('MULTIPLY_ADD', gaps, 0.30, 0.03), b.inputs['Coat Roughness'])
    # micro grooves: 0.1 mm pitch V-canyons (rounded square-wave wall tilt, ~40 deg walls), faded by camera distance
    fd = N.new('ShaderNodeGroup'); fd.node_tree = ND.ng_fade_by_distance()
    fd.inputs['near'].default_value = 0.006; fd.inputs['far'].default_value = 0.035
    sv = M('SINE', M('MULTIPLY', r, TAU / 0.0001))
    vwall = M('MINIMUM', M('MAXIMUM', M('MULTIPLY', sv, 2.5), -1.0), 1.0)
    micro = M('MULTIPLY', M('MULTIPLY', vwall, fd.outputs['Fac']), 0.85)
    # track sheen: radial 1D noise (~2-4 mm bands), concentric rings readable at the hold
    tn = N.new('ShaderNodeTexNoise'); tn.noise_dimensions = '1D'; tn.inputs['Scale'].default_value = 350.0
    tn.inputs['Detail'].default_value = 3.0; Lk.new(r, tn.inputs['W'])
    sheen = M('MULTIPLY', M('SUBTRACT', tn.outputs['Fac'], 0.5), 0.25)
    tilt = N.new('ShaderNodeMath'); tilt.operation = 'MULTIPLY'
    Lk.new(M('ADD', micro, sheen), tilt.inputs[0]); Lk.new(groove, tilt.inputs[1])
    vs = N.new('ShaderNodeVectorMath'); vs.operation = 'SCALE'; Lk.new(nrm.outputs[0], vs.inputs[0]); Lk.new(tilt.outputs[0], vs.inputs['Scale'])
    up = N.new('ShaderNodeCombineXYZ'); up.inputs['Z'].default_value = 1.0
    va = N.new('ShaderNodeVectorMath'); va.operation = 'ADD'; Lk.new(vs.outputs[0], va.inputs[0]); Lk.new(up.outputs[0], va.inputs[1])
    vn = N.new('ShaderNodeVectorMath'); vn.operation = 'NORMALIZE'; Lk.new(va.outputs[0], vn.inputs[0])
    vt = N.new('ShaderNodeVectorTransform'); vt.vector_type = 'NORMAL'; vt.convert_from = 'OBJECT'; vt.convert_to = 'WORLD'
    Lk.new(vn.outputs[0], vt.inputs[0]); Lk.new(vt.outputs[0], b.inputs['Normal'])
    # roughness: run-out 0.09 (close to the programme so no hard reflection edge), programme 0.13, matte gaps 0.38
    rough = M('ADD', M('ADD', 0.09, M('MULTIPLY', groove, 0.04)), M('MULTIPLY', gaps, 0.46))
    Lk.new(rough, b.inputs['Roughness'])
    # ---- analytic radial groove highlight (bowtie): the groove walls tilt the normal radially, so a light is
    # reflected along the radial line where the half vector lies in the radial-vertical plane.
    geo = N.new('ShaderNodeNewGeometry')
    rw = N.new('ShaderNodeVectorTransform'); rw.vector_type = 'VECTOR'; rw.convert_from = 'OBJECT'; rw.convert_to = 'WORLD'
    Lk.new(nrm.outputs[0], rw.inputs[0])
    rho = VM('NORMALIZE', rw.outputs[0]).outputs[0]
    Zc = vconst(0, 0, 1)
    tau = VM('CROSS_PRODUCT', Zc, rho).outputs[0]
    acc = None
    for key_, pos, rgb, sig in (('rim', RIM_LOC, L('magenta'), 0.05), ('back', BACK_LOC, L('violet'), 0.07)):
        Lv = VM('NORMALIZE', VM('SUBTRACT', vconst(*pos), geo.outputs['Position']).outputs[0]).outputs[0]
        H = VM('NORMALIZE', VM('ADD', Lv, geo.outputs['Incoming']).outputs[0]).outputs[0]
        ht = VM('DOT_PRODUCT', H, tau).outputs['Value']
        hr = VM('DOT_PRODUCT', H, rho).outputs['Value']
        hz = VM('DOT_PRODUCT', H, Zc).outputs['Value']
        g = M('EXPONENT', M('MULTIPLY', M('POWER', M('DIVIDE', ht, sig), 2.0), -1.0))
        kk = M('DIVIDE', M('ABSOLUTE', hr), M('MAXIMUM', hz, 0.05))
        win = N.new('ShaderNodeMapRange'); win.interpolation_type = 'SMOOTHSTEP'
        win.inputs['From Min'].default_value = 0.20; win.inputs['From Max'].default_value = 0.36
        win.inputs['To Min'].default_value = 1.0; win.inputs['To Max'].default_value = 0.0
        Lk.new(kk, win.inputs['Value'])
        sv_ = N.new('ShaderNodeValue'); sv_.outputs[0].default_value = 1.0; sv_.label = 'sheen_' + key_
        SHEEN_VALS.setdefault(key_, []).append(sv_)
        s_ = M('MULTIPLY', M('MULTIPLY', g, win.outputs['Result']), sv_.outputs[0])
        col = VM('SCALE', vconst(*rgb), scale=s_).outputs[0]
        acc = col if acc is None else VM('ADD', acc, col).outputs[0]
    near_off = M('SUBTRACT', 1.0, fd.outputs['Fac'])
    mask = M('MULTIPLY', groove, near_off)
    em = VM('SCALE', acc, scale=mask).outputs[0]
    # coat cue (f279-288 only): a very soft violet-white sheen gradient over the left of the still close-up frame,
    # as if a big softbox were mirrored in the coat (camera-space, so it stays put while the record co-rotates)
    cc_ = N.new('ShaderNodeValue'); cc_.outputs[0].default_value = 0.0; cc_.label = 'coat_cue'; COATCUE_VALS.append(cc_)
    vtp = N.new('ShaderNodeVectorTransform'); vtp.vector_type = 'POINT'; vtp.convert_from = 'WORLD'; vtp.convert_to = 'CAMERA'
    Lk.new(geo.outputs['Position'], vtp.inputs[0])
    spc = N.new('ShaderNodeSeparateXYZ'); Lk.new(vtp.outputs[0], spc.inputs[0])
    # QA fix (hard seam at the frame centre f280-288): shader 'Camera' space has +Z FORWARD (EEVEE inverts z to match
    # Cycles), so the old max(-Z, 1e-4) clamped to 1e-4 and the gradient became a step at X=0. |Z| is convention-proof.
    ndc = M('DIVIDE', M('DIVIDE', spc.outputs['X'], M('MAXIMUM', M('ABSOLUTE', spc.outputs['Z']), 1e-4)), 18.0 / 28.0)
    gmr = N.new('ShaderNodeMapRange'); gmr.interpolation_type = 'SMOOTHSTEP'
    # full-width soft gradient: left edge = the approved left-half level, frame-mean cue unchanged (0.5 * amp)
    gmr.inputs['From Min'].default_value = 1.0; gmr.inputs['From Max'].default_value = -1.0
    Lk.new(ndc, gmr.inputs['Value'])
    cue_rgb = [0.55 * a + 0.45 * b_ for a, b_ in zip(L('violet'), L('chalk'))]
    cue = VM('SCALE', vconst(*cue_rgb), scale=M('MULTIPLY', gmr.outputs['Result'], cc_.outputs[0])).outputs[0]
    Lk.new(VM('ADD', VM('ADD', em, vein_em).outputs[0], cue).outputs[0], b.inputs['Emission Color']); b.inputs['Emission Strength'].default_value = 1.0
    return m


def mat_strip():
    """Emissive strip panel (hidden from camera, seen in reflections) with soft ends and edges: no hard rectangle."""
    m = bpy.data.materials.new('M_StripEmit'); m.use_nodes = True
    N, Lk, b = nodes(m)
    b.inputs['Base Color'].default_value = (0, 0, 0, 1)
    b.inputs['Emission Color'].default_value = (1.0, 0.93, 0.86, 1)
    tc = N.new('ShaderNodeTexCoord'); sp = N.new('ShaderNodeSeparateXYZ'); Lk.new(tc.outputs['Object'], sp.inputs[0])

    def soft(sock, a0, a1):
        ab = N.new('ShaderNodeMath'); ab.operation = 'ABSOLUTE'; Lk.new(sock, ab.inputs[0])
        mr = N.new('ShaderNodeMapRange'); mr.interpolation_type = 'SMOOTHSTEP'
        mr.inputs['From Min'].default_value = a0; mr.inputs['From Max'].default_value = a1
        mr.inputs['To Min'].default_value = 1.0; mr.inputs['To Max'].default_value = 0.0
        Lk.new(ab.outputs[0], mr.inputs['Value']); return mr.outputs['Result']
    mu = N.new('ShaderNodeMath'); mu.operation = 'MULTIPLY'
    Lk.new(soft(sp.outputs['X'], 0.7, 1.45), mu.inputs[0]); Lk.new(soft(sp.outputs['Y'], 0.012, 0.055), mu.inputs[1])
    sv_ = N.new('ShaderNodeValue'); sv_.outputs[0].default_value = 25.0; sv_.label = 'strip_strength'
    mu2 = N.new('ShaderNodeMath'); mu2.operation = 'MULTIPLY'; Lk.new(mu.outputs[0], mu2.inputs[0]); Lk.new(sv_.outputs[0], mu2.inputs[1])
    Lk.new(mu2.outputs[0], b.inputs['Emission Strength'])
    return m, sv_


MAT = {}
MAT['lacquer'] = mat_lacquer()
MAT['anod'] = mat_brushed('M_AnodisedViolet', 'anodised', 0.35, scale=(4000, 60, 4000), strength=0.05)
# plinth top plate: same anodised family, lifted so it reads violet (not near-black) under the back card
MAT['plate'] = mat_brushed('M_TopPlateViolet', 'anodised', 0.28, metal=0.85, scale=(4000, 60, 4000), strength=0.06)
# headshell: same anodised violet, lifted a touch and brushed AXIALLY (local X = cartridge forward)
MAT['anod_hs'] = mat_brushed('M_HeadshellViolet', 'anodised', 0.30, scale=(60, 5000, 5000), strength=0.10)
MAT['anod_hs'].node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (*[c * 1.6 for c in L('anodised')], 1)
MAT['plate'].node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (*[c * 2.6 for c in L('anodised')], 1)
MAT['chrome'] = mat_chrome()
MAT['alu_axial'] = mat_brushed('M_BrushedAlu', 'alu', 0.18, scale=(20000, 20000, 300), strength=0.08)
# cantilever: own brushed-alu material with a keyed 'macro tint' (f121-131) that paints S1's three spire streaks
# (magenta left flank, saffron/cream crest, ultramarine right flank, dark gaps) by camera-space normal: the hidden
# cut from S1 f120 continues colour-for-colour. Tint 0 after f131 -> plain brushed aluminium (and in the asset).
MAT['cant'] = mat_brushed('M_CantileverAlu', 'alu', 0.18, scale=(20000, 20000, 300), strength=0.08)
CANT_TINT = []


def add_macro_tint(m):
    N, Lk, b = nodes(m)
    geo = N.new('ShaderNodeNewGeometry')
    vt = N.new('ShaderNodeVectorTransform'); vt.vector_type = 'NORMAL'; vt.convert_from = 'WORLD'; vt.convert_to = 'CAMERA'
    Lk.new(geo.outputs['Normal'], vt.inputs[0])
    sp = N.new('ShaderNodeSeparateXYZ'); Lk.new(vt.outputs[0], sp.inputs[0])
    mr = N.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = -0.85; mr.inputs['From Max'].default_value = 0.85
    Lk.new(sp.outputs['X'], mr.inputs['Value'])
    rp = N.new('ShaderNodeValToRGB'); cr = rp.color_ramp; cr.interpolation = 'EASE'
    stops = [(0.0, L('night')), (0.10, L('magenta')), (0.30, L('magenta')), (0.38, [c * 0.25 for c in L('violet')]),
             (0.45, L('saffron')), (0.50, C.hex2lin('#FFE6B8')), (0.55, L('saffron')), (0.62, [c * 0.25 for c in L('violet')]),
             (0.70, L('ultramarine')), (0.90, L('ultramarine')), (1.0, L('night'))]
    while len(cr.elements) > 1: cr.elements.remove(cr.elements[-1])
    cr.elements[0].position, cr.elements[0].color = stops[0][0], (*stops[0][1], 1)
    for pos_, c_ in stops[1:]:
        e_ = cr.elements.new(pos_); e_.color = (*c_, 1)
    Lk.new(mr.outputs['Result'], rp.inputs['Fac'])
    kv = N.new('ShaderNodeValue'); kv.outputs[0].default_value = 0.0; kv.label = 'macro_tint'; CANT_TINT.append(kv)
    mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MIX'
    Lk.new(kv.outputs[0], mx.inputs['Factor']); mx.inputs[6].default_value = b.inputs['Base Color'].default_value
    Lk.new(rp.outputs['Color'], mx.inputs[7]); Lk.new(mx.outputs[2], b.inputs['Base Color'])
    Lk.new(rp.outputs['Color'], b.inputs['Emission Color'])
    em = N.new('ShaderNodeMath'); em.operation = 'MULTIPLY'; Lk.new(kv.outputs[0], em.inputs[0]); em.inputs[1].default_value = CANT_TINT_EMIT
    Lk.new(em.outputs[0], b.inputs['Emission Strength'])


CANT_TINT_EMIT = 2.0
add_macro_tint(MAT['cant'])
MAT['alu_platter'] = mat_brushed('M_BrushedAluPlatter', 'alu', 0.18, mode='radial', scale=(9000, 0, 0), strength=0.06)
MAT['felt'] = mat_felt()
MAT['label'] = mat_label()
MAT["ink"] = ND.simple("M_Ink", "night", rough=0.6)
MAT['ink_mag'] = ND.simple('M_InkMagenta', 'magenta', rough=0.3)
MAT['rubber'] = ND.simple('M_RubberViolet', 'anodised', rough=0.75)
MAT['rubber_blk'] = ND.simple('M_RubberBlack', 'night', rough=0.55)
MAT['chalk'] = ND.simple('M_ChalkPaint', 'chalk', rough=0.4)
MAT['saffron_paint'] = ND.simple('M_SaffronPaint', 'saffron', rough=0.35, coat=0.5)
MAT['ultra_knob'] = ND.simple('M_UltraKnob', 'ultramarine', rough=0.22, coat=1.0)
MAT['diamond'] = ND.black_diamond()
MAT['wires'] = [ND.simple('M_LeadWire_%d' % i, h, rough=0.25, coat=0.5) for i, h in enumerate(('magenta', 'saffron', 'ultramarine', 'vermilion'))]
MAT['cove'] = mat_cove()
MAT['strobe_win'] = mat_emit('M_StrobeWindow', 'vermilion', 30.0)
MAT['led_saf'] = mat_emit('M_LED_Saffron', 'saffron', 40.0)
MAT['led_mag'] = mat_emit('M_LED_Magenta', 'magenta', 30.0)
MAT['strip'], STRIP_VAL = mat_strip()
MAT['vinyl'] = mat_vinyl('M_Vinyl', grooved=True)
MAT['vinyl_plain'] = mat_vinyl('M_VinylEdge', grooved=False)
MAT['dots'] = ND.simple('M_StrobeDots', 'chrome', rough=0.05, metal=1.0)

# ------------------------------------------------------------------ world

hdri = os.path.join(ROOT, 'assets', 'polyhaven', 'hdri', 'studio_small_09_2k.exr')
if not os.path.exists(hdri):
    hdri = C.ph_hdri('studio_small_09', '2k')
C.world_hdri(sc, hdri, strength=0.12, rotation_z=math.radians(30))

# ------------------------------------------------------------------ layout constants
SX, SY = -0.055, -0.010                # spindle axis (10 mm margin shift for a balanced plinth)
Z_FEET = 0.012
Z_PL_TOP = 0.077                       # plinth top
Z_PLATE = Z_PL_TOP - 0.0006            # top plate surface (recessed 0.6 mm)
Z_PB = Z_PLATE + 0.0015                # platter bottom
Z_PT = Z_PB + 0.020                    # platter top
Z_MAT = Z_PT + 0.003                   # slipmat top = record bottom
Z_REC0 = Z_MAT
REC_TOP = 0.0015                       # programme surface (object z)
REC_LABEL_TOP = 0.00155                 # 0.05 mm label plateau (paper sits flush; no dark "puck" wall in the dive)
Z_REC = Z_REC0 + REC_TOP               # world z of the vinyl surface
PIV = Vector((SX + 0.165, SY + 0.138))   # arm pivot xy (0.2151 m from spindle)
ARM_L = 0.235
Z_PIV = Z_REC + 0.0202
R_PLAY = 0.113

# stylus position: circle(PIV, ARM_L) ∩ circle(S, R_PLAY), front side
S2D = Vector((SX, SY))
D = (PIV - S2D).length
ca = (R_PLAY ** 2 + D ** 2 - ARM_L ** 2) / (2 * R_PLAY * D)
ang_sp = math.atan2(PIV.y - S2D.y, PIV.x - S2D.x)
ang_sty = ang_sp - math.acos(ca)
STY2 = S2D + R_PLAY * Vector((math.cos(ang_sty), math.sin(ang_sty)))
# groove velocity (record turns clockwise seen from above): tangent = (sin a, -cos a)
F_WORLD = Vector((math.sin(ang_sty), -math.cos(ang_sty), 0.0))
ARM_DIR = (STY2 - PIV).normalized()
PSI = math.atan2(ARM_DIR.y, ARM_DIR.x) + math.pi / 2     # rotation so local -Y -> ARM_DIR
R_ARM = Matrix.Rotation(PSI, 3, 'Z')
F_LOCAL = (R_ARM.inverted() @ F_WORLD).normalized()
OFFSET_DEG = math.degrees(math.acos(max(-1, min(1, F_WORLD.dot(ARM_DIR.to_3d())))))
print('LAYOUT stylus', tuple(round(v, 4) for v in STY2), 'offset angle', round(OFFSET_DEG, 2), 'F_LOCAL', tuple(round(v, 3) for v in F_LOCAL))

# ------------------------------------------------------------------ studio cove (360 cyc)

def build_cove():
    prof = [(0.0, 0.0)]
    R_FLOOR, R_FIL = 0.95, 0.6
    for i in range(0, 13):
        prof.append((R_FLOOR * i / 12.0, 0.0)) if i else None
    for i in range(1, 17):
        a = math.radians(-90 + 90 * i / 16)
        prof.append((R_FLOOR + R_FIL * math.cos(a), R_FIL + R_FIL * math.sin(a)))
    for z in (0.9, 1.4, 2.0, 2.6, 3.0):
        prof.append((R_FLOOR + R_FIL, z))
    prof.append((0.0, 3.0))
    me = lathe('Cove', prof, n=160)
    # flip normals inward (we see the inside)
    for p in me.polygons: p.flip()
    me.update()
    ob = new_obj('Cove', me, COL_STUDIO, [MAT['cove']], loc=(SX, SY + 0.05, 0.0))
    return ob


build_cove()

# ------------------------------------------------------------------ plinth

pl_out = rrect(0.45, 0.36, 0.022, 10)
plinth = new_obj('Plinth', prism('Plinth', pl_out, Z_FEET, Z_PL_TOP), COL_TT, [MAT['lacquer']])
cut = new_obj('PlinthPocketCutter', prism('Cut', rrect(0.43, 0.34, 0.014, 10), Z_PLATE - 0.002, Z_PL_TOP + 0.01), COL_TT)
cut.hide_render = True; cut.hide_viewport = True; cut.display_type = 'WIRE'
bo = plinth.modifiers.new('Pocket', 'BOOLEAN'); bo.object = cut; bo.operation = 'DIFFERENCE'; bo.solver = 'EXACT'
hard(plinth, w=0.004, segs=4, angle=40)
plate = new_obj('TopPlate', prism('TopPlate', rrect(0.4296, 0.3396, 0.0138, 10), Z_PLATE - 0.002, Z_PLATE), COL_TT, [MAT['plate']])
hard(plate, w=0.0006, segs=2)
for i, (fx, fy) in enumerate(((0.18, 0.13), (-0.18, 0.13), (0.18, -0.13), (-0.18, -0.13))):
    ft = new_obj('FootRubber%d' % i, cyl('FootR', 0.03, 0.0062, 64, 0.0), COL_TT, [MAT['rubber']], loc=(fx, fy, 0))
    hard(ft, w=0.002, segs=3)
    fr = new_obj('FootRing%d' % i, cyl('FootC', 0.0285, Z_FEET - 0.0062 + 0.001, 64, 0.0062), COL_TT, [MAT['chrome']], loc=(fx, fy, 0))
    hard(fr, w=0.0008, segs=2)

# ------------------------------------------------------------------ platter group (rotating)

platter_rot = empty('PlatterRot', COL_TT, loc=(SX, SY, 0.0))
prof = [(0.0, Z_PT), (0.1440, Z_PT)]
for i in range(1, 9):             # rolled rim
    a = math.radians(90 - 90 * i / 8)
    prof.append((0.1440 + 0.0065 * math.cos(a) * 0.95 + 0.0, Z_PT - 0.0065 + 0.0065 * math.sin(a)))
prof += [(0.1505, Z_PT - 0.0065), (0.1505, Z_PB + 0.0015), (0.1490, Z_PB), (0.1360, Z_PB), (0.1360, Z_PB + 0.004),
         (0.0300, Z_PB + 0.004), (0.0300, Z_PB), (0.0, Z_PB)]
platter = new_obj('Platter', lathe('Platter', prof, n=320), COL_TT, [MAT['alu_platter']], parent=platter_rot)
hard(platter, w=0.0006, segs=2, angle=40)
slip = new_obj('Slipmat', lathe('Slipmat', [(0.0, Z_PT), (0.148, Z_PT), (0.148, Z_MAT - 0.0004), (0.1476, Z_MAT), (0.0, Z_MAT)], n=256),
               COL_TT, [MAT['felt']], parent=platter_rot)

# record: object origin on the spindle axis at the record bottom
rp = [(0.0036, REC_LABEL_TOP), (0.050, REC_LABEL_TOP), (0.0508, REC_LABEL_TOP - 0.00002), (0.0526, REC_TOP + 0.00002),
      (0.0540, REC_TOP), (0.1478, REC_TOP), (0.1490, REC_TOP + 0.0003), (0.1500, REC_TOP + 0.0002), (0.1505, REC_TOP - 0.0002),
      (0.1505, 0.0003), (0.1502, 0.0), (0.0036, 0.0)]
rp_closed = rp + [rp[0]]
mats_idx = [1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1]
# build as an annulus (hole): revolve the closed loop
def lathe_loop(name, loop, n, mats):
    bm = bmesh.new(); rows = []
    for (r, z) in loop[:-1]:
        rows.append([bm.verts.new((r * math.cos(TAU * k / n), r * math.sin(TAU * k / n), z)) for k in range(n)])
    m = len(rows)
    for j in range(m):
        A, B = rows[j], rows[(j + 1) % m]
        for k in range(n):
            k2 = (k + 1) % n
            f = bm.faces.new((A[k], A[k2], B[k2], B[k])); f.smooth = True; f.material_index = mats[j]
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); return me
record = new_obj('Record', lathe_loop('Record', rp_closed, 384, mats_idx), COL_TT, [MAT['vinyl'], MAT['vinyl_plain']],
                 parent=platter_rot, loc=(0, 0, Z_REC0))
hard(record, w=0.00015, segs=2, angle=50)

# label + typography (children of the record so they share its object space)
lab_z = REC_LABEL_TOP
label = new_obj('Label', lathe_loop('Label', [(0.0037, lab_z), (0.0499, lab_z), (0.0499, lab_z + 0.00003), (0.0037, lab_z + 0.00003), (0.0037, lab_z)], 256, [0, 1, 0, 1]),
                COL_TT, [MAT['label'], MAT['vinyl_plain']], parent=record)
TXT_Z = lab_z + 0.00003


def place_text(name, body, size, y, mat):
    me = text_mesh(name, body, size, extrude=0.00002)
    ob = new_obj(name, me, COL_TT, [mat], parent=record, loc=(0, y, TXT_Z + 0.000005))
    return ob


cap = 0.007 / 0.716
place_text('Txt_NEEDLE', 'NEEDLE', cap, 0.0195, MAT['ink'])
place_text('Txt_DROP', 'DROP', cap, -0.0195, MAT['ink'])

# ring text wrapped around r = 0.0405
ring_body = 'SIDE A \u00b7 33 1/3 RPM \u00b7 STEREO \u00b7 SIDE A \u00b7 33 1/3 RPM \u00b7 STEREO \u00b7 '
rme = text_mesh('Txt_Ring', ring_body, 1.0, extrude=0.00002, align='LEFT')
co = np.empty(len(rme.vertices) * 3); rme.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
R_RING = 0.0405
xmin, xmax = co[:, 0].min(), co[:, 0].max()
k = (TAU * R_RING * 0.985) / (xmax - xmin)
x = (co[:, 0] - xmin) * k; yv = co[:, 1] * k
ang = math.pi / 2 - x / R_RING
rad = R_RING + yv - 0.0012
co2 = np.stack([rad * np.cos(ang), rad * np.sin(ang), co[:, 2] * 0 + co[:, 2]], 1)
rme.vertices.foreach_set('co', co2.ravel()); rme.update()
new_obj('Txt_Ring', rme, COL_TT, [MAT['ink']], parent=record, loc=(0, 0, TXT_Z + 0.000005))
for rr, w in ((0.0468, 0.0007), (0.0352, 0.0005)):
    ring = lathe_loop('LabRing', [(rr, 0), (rr + w, 0), (rr + w, 0.00002), (rr, 0.00002), (rr, 0)], 256, [0, 0, 0, 0])
    new_obj('LabelRing', ring, COL_TT, [MAT['ink_mag']], parent=record, loc=(0, 0, TXT_Z + 0.000005))

# vinyl dust motes around the playing radius (macro scale cues; echo of S1's boulders). One mesh, rotates with the record.
_rng = np.random.default_rng(7)
_bm = bmesh.new()
for _i in range(70):
    rr_ = 0.1045 + _rng.random() * 0.018; aa_ = _rng.random() * TAU
    sz = 0.00003 + _rng.random() ** 2 * 0.00009
    _tmp = bmesh.new(); bmesh.ops.create_icosphere(_tmp, subdivisions=1, radius=1.0)
    for vv_ in _tmp.verts:
        n_ = 0.75 + 0.5 * _rng.random()
        vv_.co = Vector((vv_.co.x * sz * n_ * 1.3, vv_.co.y * sz * n_, max(vv_.co.z, -0.2) * sz * 0.55 * n_))
    _rot = Matrix.Rotation(_rng.random() * TAU, 4, 'Z')
    bmesh.ops.transform(_tmp, matrix=Matrix.Translation((rr_ * math.cos(aa_), rr_ * math.sin(aa_), REC_TOP + sz * 0.05)) @ _rot, verts=_tmp.verts)
    _me = bpy.data.meshes.new('tmpdust'); _tmp.to_mesh(_me); _tmp.free(); _bm.from_mesh(_me); bpy.data.meshes.remove(_me)
_dme = bpy.data.meshes.new('VinylDust'); _bm.to_mesh(_dme); _bm.free(); _dme.shade_smooth()
MAT['dust'] = ND.simple('M_VinylDust', rgb=C.hex2lin('#CFC6DA'), rough=0.6, sheen=0.4)
DUST = new_obj('VinylDust', _dme, COL_TT, [MAT['dust']], parent=record)
for _fr, _h in ((F0 - 2, False), (170, False), (171, True)):
    DUST.hide_render = _h; DUST.keyframe_insert('hide_render', frame=_fr)   # macro-only: sub-pixel at the hold

# spindle (static; rotationally symmetric)
sp_prof = [(0.0, Z_PT - 0.002), (0.00355, Z_PT - 0.002), (0.00355, Z_PT + 0.0115), (0.0030, Z_PT + 0.0135), (0.0018, Z_PT + 0.0148), (0.0, Z_PT + 0.0152)]
spindle = new_obj('Spindle', lathe('Spindle', sp_prof, 64), COL_TT, [MAT['chrome']], loc=(SX, SY, 0))
hard(spindle, w=0.0003, segs=3, angle=30)

# strobe rows: hemispheres on the platter rim, each row rotates at its aliased apparent rate
def hemis_row(name, N_, z, rdot=0.0009, R=0.1505):
    nu, nv = 10, 4
    tv, tf = [], []
    for j in range(nv + 1):
        th = (math.pi / 2) * j / nv
        for i in range(nu):
            ph = TAU * i / nu
            tv.append((rdot * math.sin(th) * 0 + rdot * math.cos(th) * 0, 0, 0))
    # explicit construction in local dot frame: radial axis = +X
    tv = []
    for j in range(nv):
        th = (math.pi / 2) * j / nv
        for i in range(nu):
            ph = TAU * i / nu
            tv.append((rdot * math.sin(th) - 0.0002, rdot * math.cos(th) * math.cos(ph), rdot * math.cos(th) * math.sin(ph)))
    tv.append((rdot - 0.0002, 0, 0))
    tv = np.array(tv)
    tf = []
    for j in range(nv - 1):
        for i in range(nu):
            i2 = (i + 1) % nu
            tf.append((j * nu + i, j * nu + i2, (j + 1) * nu + i2, (j + 1) * nu + i))
    top = nv * nu
    for i in range(nu):
        tf.append(((nv - 1) * nu + i, (nv - 1) * nu + (i + 1) % nu, top))
    tf.append(tuple(reversed(range(nu))))
    verts, faces = [], []
    for kk in range(N_):
        a = TAU * kk / N_
        ca_, sa_ = math.cos(a), math.sin(a)
        off = len(verts)
        for (vx, vy, vz) in tv:
            rx = R + vx
            verts.append((rx * ca_ - vy * sa_, rx * sa_ + vy * ca_, z + vz))
        faces += [tuple(off + q for q in f) for f in tf]
    me = mesh(name, verts, faces)
    bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    return me


STROBE = []
dps = RPM_DEG / FPS
for ii, (N_, z) in enumerate(((216, Z_PB + 0.0120), (212, Z_PB + 0.0090), (220, Z_PB + 0.0060), (224, Z_PB + 0.0030))):
    sp_ = 360.0 / N_
    m_ = dps % sp_
    if m_ > sp_ / 2: m_ -= sp_
    apparent = -m_ * FPS          # deg/s (clockwise sign convention like the platter)
    ob = new_obj('StrobeRow_%d' % N_, hemis_row('StrobeRow_%d' % N_, N_, z), COL_TT, [MAT['dots']], loc=(SX, SY, 0))
    STROBE.append((ob, apparent))
    print('STROBE', N_, 'apparent deg/s', round(apparent, 3))

# ------------------------------------------------------------------ controls & strobe lamp (turntable, world space)
def knob(name, x, y, w, d, h, cap_mat, ring_mat=None):
    if ring_mat is not None:
        rg = new_obj(name + 'Ring', prism(name + 'Ring', rrect(w + 0.004, d + 0.004, 0.004, 6), Z_PLATE - 0.001, Z_PLATE + 0.0015), COL_TT, [ring_mat], loc=(x, y, 0))
        hard(rg, w=0.0006, segs=2)
    cp = new_obj(name, prism(name, rrect(w, d, 0.003, 6), Z_PLATE, Z_PLATE + h), COL_TT, [cap_mat], loc=(x, y, 0))
    hard(cp, w=0.0012, segs=3)
    return cp


knob('StartStop', -0.175, -0.150, 0.034, 0.022, 0.006, MAT['anod'], MAT['chrome'])
knob('Btn33', -0.120, -0.155, 0.018, 0.012, 0.004, MAT['anod'], MAT['chrome'])
knob('Btn45', -0.096, -0.155, 0.018, 0.012, 0.004, MAT['anod'], MAT['chrome'])
led = new_obj('PowerLED', cyl('PowerLED', 0.0015, 0.0012, 24, Z_PLATE), COL_TT, [MAT['led_mag']], loc=(-0.202, -0.150, 0))
hard(led, w=0.0004, segs=2)
# pitch slider
slot = new_obj('PitchSlot', prism('PitchSlot', rrect(0.006, 0.105, 0.003, 6), Z_PLATE - 0.0004, Z_PLATE + 0.0003), COL_TT, [MAT['rubber_blk']], loc=(0.185, -0.075, 0))
sld = new_obj('PitchKnob', prism('PitchKnob', rrect(0.018, 0.011, 0.003, 6), Z_PLATE, Z_PLATE + 0.009), COL_TT, [MAT['chrome']], loc=(0.185, -0.088, 0))
hard(sld, w=0.0015, segs=3)
pled = new_obj('PitchLED', cyl('PitchLED', 0.001, 0.0012, 24, Z_PLATE), COL_TT, [MAT['led_saf']], loc=(0.2055, -0.125, 0))
for t_ in range(9):
    tk = new_obj('PitchTick%d' % t_, prism('Tick', rrect(0.005 if t_ % 4 else 0.008, 0.0008, 0.0003, 2), Z_PLATE, Z_PLATE + 0.00025), COL_TT, [MAT['chalk']],
                 loc=(0.170 - (0.0015 if t_ % 4 == 0 else 0), -0.120 + t_ * 0.0115, 0))
    hard(tk, w=0.0001, segs=2, angle=40)
# strobe lamp housing at the platter front-left
a_l = math.radians(232)
lx, ly = SX + 0.169 * math.cos(a_l), SY + 0.169 * math.sin(a_l)
hous = new_obj('StrobeLamp', cyl('StrobeLamp', 0.012, 0.024, 48, Z_PLATE), COL_TT, [MAT['anod']], loc=(lx, ly, 0))
hard(hous, w=0.002, segs=3)
hcap = new_obj('StrobeLampCap', cyl('StrobeLampCap', 0.0125, 0.002, 48, Z_PLATE + 0.024), COL_TT, [MAT['chrome']], loc=(lx, ly, 0))
hard(hcap, w=0.0008, segs=2)
win = new_obj('StrobeWindow', prism('StrobeWindow', rrect(0.004, 0.012, 0.0015, 4), -0.0005, 0.0005), COL_TT, [MAT['strobe_win']])
to_c = Vector((SX - lx, SY - ly, 0)).normalized()
win.location = (lx + to_c.x * 0.0118, ly + to_c.y * 0.0118, Z_PLATE + 0.014)
win.rotation_euler = (0, math.radians(90), math.atan2(to_c.y, to_c.x))
pl = bpy.data.lights.new('StrobePoint', 'POINT'); pl.energy = 0.5; pl.color = L('vermilion'); pl.shadow_soft_size = 0.003
STROBE_PT = new_obj('StrobePoint', pl, COL_TT, loc=(lx + to_c.x * 0.016, ly + to_c.y * 0.016, Z_PLATE + 0.014))

# ------------------------------------------------------------------ TONEARM (local frame: pivot at origin, arm -> -Y)
arm_root = empty('ArmPivot', COL_ARM, size=0.03)
zT = Z_REC - Z_PIV                          # record surface, local z
Z_BASE0 = Z_PLATE - Z_PIV                    # plinth plate, local z
T_loc = Vector((0.0, -ARM_L, zT))
f = Vector((F_LOCAL.x, F_LOCAL.y, 0.0)).normalized()
v = Vector((-f.y, f.x, 0.0))                 # left of forward (outward radial at the stylus)
Z = Vector((0, 0, 1))
A_ARM = []                                    # (name, obj) for asset bookkeeping


def arm_obj(name, data, mats, loc=(0, 0, 0), rot=None):
    ob = new_obj(name, data, COL_ARM, mats, parent=arm_root, loc=loc, rot=rot)
    A_ARM.append(ob); return ob


def basis_obj_rot(xa, ya, za):
    m = Matrix((xa, ya, za)).transposed()
    return m.to_quaternion()


# base, pillar, gimbal
b0 = arm_obj('ArmBase', cyl('ArmBase', 0.030, 0.025, 96, Z_BASE0), [MAT['anod']]); hard(b0, w=0.002, segs=3)
b1 = arm_obj('ArmBaseRing', cyl('ArmBaseRing', 0.0306, 0.003, 96, Z_BASE0 + 0.010), [MAT['chrome']]); hard(b1, w=0.0006, segs=2)
b2 = arm_obj('ArmBaseCap', cyl('ArmBaseCap', 0.0175, 0.003, 64, Z_BASE0 + 0.025), [MAT['chrome']]); hard(b2, w=0.0008, segs=2)
pil = arm_obj('ArmPillar', cyl('ArmPillar', 0.0095, (-0.0125) - (Z_BASE0 + 0.028), 48, Z_BASE0 + 0.028), [MAT['chrome']]); hard(pil, w=0.0006, segs=2)
yb = arm_obj('GimbalYokeBase', prism('YokeBase', rrect(0.032, 0.020, 0.006, 8), -0.0135, -0.0100), [MAT['anod']]); hard(yb, w=0.0009, segs=3)
for sgn in (-1, 1):
    pl_ = prism('YokePlate', rrect(0.020, 0.022, 0.007, 8), -0.00125, 0.00125)
    yp = arm_obj('GimbalPlate%+d' % sgn, pl_, [MAT['anod']], loc=(sgn * 0.0135, 0.0, -0.002),
                 rot=basis_obj_rot(Vector((0, 1, 0)), Vector((0, 0, 1)), Vector((1, 0, 0))))
    hard(yp, w=0.0006, segs=3)
    pin = arm_obj('GimbalPin%+d' % sgn, cyl('Pin', 0.0024, 0.004, 32, -0.002), [MAT['chrome']], loc=(sgn * 0.0160, 0, 0.0),
                  rot=basis_obj_rot(Vector((0, 1, 0)), Vector((0, 0, 1)), Vector((1, 0, 0))))
    hard(pin, w=0.0005, segs=2)
bh = arm_obj('BearingHousing', cyl('BearingHousing', 0.0068, 0.0235, 48, -0.01175), [MAT['chrome']],
             rot=basis_obj_rot(Vector((0, 1, 0)), Vector((0, 0, 1)), Vector((1, 0, 0))))
hard(bh, w=0.0008, segs=3)
vc = arm_obj('BearingCollar', cyl('BearingCollar', 0.0085, 0.006, 48, -0.0045), [MAT['anod']])
hard(vc, w=0.0008, segs=2)

# cantilever / stylus / cartridge / headshell along f
stylus_h = 0.00055
E_tip = T_loc + Vector((0, 0, stylus_h))
dir_c = (f * math.cos(math.radians(20)) - Z * math.sin(math.radians(20))).normalized()
R0 = E_tip - dir_c * 0.006
CF = Vector((R0.x, R0.y, 0)) - f * 0.0003           # cartridge front face reference (xy)
z_cb = zT + 0.0022                                  # cartridge bottom
z_hb = -0.0012                                      # headshell bottom / cartridge top
cart_rot = basis_obj_rot(f, v, Z)


def hs_point(u, vv, z):
    return Vector((CF.x, CF.y, 0)) + f * u + v * vv + Vector((0, 0, z))


cart_c = hs_point(-0.009, 0.0, 0)
cart = arm_obj('Cartridge', prism('Cartridge', rrect(0.018, 0.017, 0.0022, 6), z_cb, z_hb), [MAT['lacquer']],
               loc=(cart_c.x, cart_c.y, 0), rot=cart_rot)
hard(cart, w=0.0004, segs=2, angle=30)      # crisp 0.4 mm chamfer: every edge catches a highlight line
# printed branding on both cartridge sides: chalk 'ND' monogram + saffron 'MC-1' (thin pad-print decals)
for sgn in (-1, 1):
    _rot = basis_obj_rot(-sgn * f, Z, sgn * v)
    for nm_, body_, cap_, zc_, mat_ in (('CartLogoND', 'ND', 0.0040, -0.0050, MAT['chalk']),
                                        ('CartLogoMC', 'MC-1', 0.0012, -0.0128, MAT['saffron_paint'])):
        _me = text_mesh(nm_ + '%+d' % sgn, body_, cap_ / 0.716, extrude=0.00002)
        _p = cart_c + v * (sgn * 0.00853) + f * (-0.0004 if nm_ == 'CartLogoND' else 0.0)
        arm_obj(nm_ + '%+d' % sgn, _me, [mat_], loc=(_p.x, _p.y, zc_), rot=_rot)
# front face (the face the f145 downbeat looks at): chalk monogram above the nose block
_pf = cart_c + f * 0.00903
arm_obj('CartLogoFront', text_mesh('CartLogoFront', 'ND', 0.0034 / 0.716, extrude=0.00002), [MAT['chalk']],
        loc=(_pf.x, _pf.y, -0.0060), rot=basis_obj_rot(v, Z, f))
_ms = text_mesh('CartLogoFrontMC', 'MC-1', 0.0011 / 0.716, extrude=0.00002)
arm_obj('CartLogoFrontMC', _ms, [MAT['saffron_paint']], loc=(_pf.x, _pf.y, -0.0092), rot=basis_obj_rot(v, Z, f))
# chalk pinstripes inlaid on both cartridge sides (reads as a designed product at f141-150)
for sgn in (-1, 1):
    zs_ = (z_cb + z_hb) / 2 + 0.0012
    stp = arm_obj('CartStripe%+d' % sgn, prism('CartStripe', rrect(0.0135, 0.00024, 0.0001, 2), zs_ - 0.00045, zs_ + 0.00045), [MAT['chalk']],
                  loc=tuple(cart_c + v * (sgn * 0.00852))[:2] + (0,), rot=cart_rot)
    stp2 = arm_obj('CartStripeS%+d' % sgn, prism('CartStripeS', rrect(0.0135, 0.00024, 0.0001, 2), zs_ - 0.0021, zs_ - 0.0017), [MAT['saffron_paint']],
                   loc=tuple(cart_c + v * (sgn * 0.00852))[:2] + (0,), rot=cart_rot)
# chamfered nose block under the front
nose = arm_obj('CartNose', prism('CartNose', rrect(0.005, 0.009, 0.0015, 4), z_cb - 0.0004, z_cb + 0.004), [MAT['rubber_blk']],
               loc=tuple(hs_point(-0.002, 0, 0))[:2] + (0,), rot=cart_rot)
hard(nose, w=0.0006, segs=2)
# cantilever (tube r 0.25 mm), damper, stylus
can_mid = (R0 + E_tip) / 2
def frustum(name, r_bot, r_top, h, n, z0):
    verts = [(r_bot * math.cos(TAU * i / n), r_bot * math.sin(TAU * i / n), z0) for i in range(n)] +             [(r_top * math.cos(TAU * i / n), r_top * math.sin(TAU * i / n), z0 + h) for i in range(n)]
    faces = [tuple(reversed(range(n))), tuple(range(n, 2 * n))] + [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    return mesh(name, verts, faces)


CANT_R_BACK, CANT_R_TIP = 0.00030, 0.00019      # tapered tube (local +z = toward the stylus tip)
can = arm_obj('Cantilever', frustum('Cantilever', CANT_R_BACK, CANT_R_TIP, 0.0062, 32, -0.0031), [MAT['cant']], loc=can_mid,
              rot=basis_obj_rot(*frame_from(dir_c), dir_c))
hard(can, w=0.00006, segs=2, angle=40)
dmp = arm_obj('CantDamper', cyl('Damper', 0.0007, 0.0008, 24, -0.0004), [MAT['rubber_blk']], loc=R0 - dir_c * 0.0002,
              rot=basis_obj_rot(*frame_from(dir_c), dir_c))
hard(dmp, w=0.0001, segs=2)
# octagonal faceted black diamond: prism + pyramid tip (flat shaded)
oc = []
r_d = 0.00020          # 0.4 mm octagonal black diamond (legible at the f145 downbeat)
for kk in range(8):
    a = TAU * (kk + 0.5) / 8; oc.append((r_d * math.cos(a), r_d * math.sin(a)))
dv = [(x_, y_, 0.00012) for x_, y_ in oc] + [(x_, y_, stylus_h + 0.00008) for x_, y_ in oc] + [(0, 0, 0.0)]
dfc = [(i, (i + 1) % 8, 8 + (i + 1) % 8, 8 + i) for i in range(8)] + [tuple(range(15, 7, -1))] + [((i + 1) % 8, i, 16) for i in range(8)]
dme = mesh('Stylus', dv, dfc, smooth=False)
bm = bmesh.new(); bm.from_mesh(dme); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(dme); bm.free()
sty = arm_obj('Stylus', dme, [MAT['diamond']], loc=T_loc, rot=basis_obj_rot(f, v, Z))
bv = sty.modifiers.new('Bevel', 'BEVEL'); bv.width = 0.000012; bv.segments = 1; bv.harden_normals = True; bv.limit_method = 'ANGLE'

# headshell plate (50 mm) + collar + finger lift + screws
hs_c = hs_point(-0.021, 0.0, 0)
hs = arm_obj('Headshell', prism('Headshell', rrect(0.050, 0.019, 0.0035, 8), z_hb, z_hb + 0.0026), [MAT['anod_hs']],
             loc=(hs_c.x, hs_c.y, 0), rot=cart_rot)
hard(hs, w=0.0007, segs=3)
col_c = hs_point(-0.051, 0.0, 0.0)
collar = arm_obj('HeadshellCollar', cyl('Collar', 0.0058, 0.012, 48, -0.006), [MAT['chrome']], loc=col_c, rot=basis_obj_rot(v, Z, f))
hard(collar, w=0.0008, segs=3)
lockring = arm_obj('CollarLockRing', cyl('LockRing', 0.0063, 0.003, 48, -0.0015), [MAT['anod']], loc=hs_point(-0.0585, 0, 0), rot=basis_obj_rot(v, Z, f))
hard(lockring, w=0.0006, segs=2)
fl_base = hs_point(-0.006, 0.0085, z_hb + 0.0013)
fl_pts = [fl_base + v * (0.016 * t) + Z * (0.009 * t ** 2.2) + f * (0.003 * t) for t in np.linspace(0, 1, 18)]
fl_sec = [(0.0005 * math.cos(a) * 1.0, 0.0021 * math.sin(a)) for a in np.linspace(0, TAU, 20, endpoint=False)]
fl_sec = [(0.0031 * math.cos(a), 0.0006 * math.sin(a)) for a in np.linspace(0, TAU, 24, endpoint=False)]
arm_obj('FingerLift', sweep('FingerLift', fl_pts, fl_sec), [MAT['chrome']])
for sgn in (-1, 1):
    sp_ = hs_point(-0.009, sgn * 0.00635, z_hb + 0.0026)
    slot = arm_obj('HeadshellSlot%+d' % sgn, prism('HSlot', rrect(0.0085, 0.0024, 0.00119, 8), -0.00001, 0.00003), [MAT['rubber_blk']],
                   loc=hs_point(-0.0095, sgn * 0.00635, z_hb + 0.0026), rot=cart_rot)     # overhang-adjust mounting slot
    scr = arm_obj('Screw%+d' % sgn, cyl('Screw', 0.0014, 0.0011, 32, 0.0), [MAT['chrome']], loc=sp_)
    hard(scr, w=0.0004, segs=3)
    sk = arm_obj('ScrewSocket%+d' % sgn, cyl('Socket', 0.0006, 0.0003, 6, 0.0009), [MAT['rubber_blk']], loc=sp_)
# lead wires: cartridge rear pins -> headshell rear
wire_z = (z_cb + z_hb) / 2
pins = [(-0.0035, 0.0035), (0.0035, 0.0035), (-0.0035, -0.0035), (0.0035, -0.0035)]
for i, (pv, pz) in enumerate(pins):
    p0 = hs_point(-0.0185, pv, wire_z + pz)
    pinob = arm_obj('Pin%d' % i, cyl('PinC', 0.0005, 0.002, 16, -0.001), [MAT['chrome']], loc=p0, rot=basis_obj_rot(v, Z, f))
    p0b = p0 - f * 0.0012
    p1 = hs_point(-0.043, pv * 0.6, z_hb - 0.0009)
    sag = 0.0022 + 0.0006 * i
    h0 = (p0b + f * 0.002, p0b - f * 0.006 + Z * (-sag))
    h1 = (p1 + f * 0.009 + Z * (-sag * 0.8), p1 - f * 0.002)
    w = bezier_curve('LeadWire%d' % i, [p0b, p1], [h0, h1], 0.0004, COL_ARM, MAT['wires'][i], parent=arm_root, res=24, bres=4)
    A_ARM.append(w)

# S-arm tube: pivot -> collar end (3-point Bezier)
P0 = Vector((0, 0, 0)); Pe = hs_point(-0.054, 0, 0); Pe.z = 0.0
mid = (P0 + Pe) / 2
chord = (Pe - P0).normalized()
arm_pts = [P0, mid, Pe]
arm_h = [(P0 + Vector((0, 0.03, 0)), P0 + Vector((0, -0.055, 0))),
         (mid - chord * 0.04, mid + chord * 0.04),
         (Pe - f * 0.055, Pe + f * 0.004)]
armtube = bezier_curve('ArmTube', arm_pts, arm_h, 0.004, COL_ARM, MAT['chrome'], parent=arm_root, res=48, bres=8)
A_ARM.append(armtube)
stub = arm_obj('RearStub', cyl('RearStub', 0.0040, 0.068, 48, 0.0), [MAT['chrome']], rot=basis_obj_rot(Vector((1, 0, 0)), Vector((0, 0, -1)), Vector((0, 1, 0))))
hard(stub, w=0.0008, segs=3)
stubcap = arm_obj('RearStubCap', cyl('StubCap', 0.0046, 0.004, 48, 0.068), [MAT['anod']], rot=basis_obj_rot(Vector((1, 0, 0)), Vector((0, 0, -1)), Vector((0, 1, 0))))
hard(stubcap, w=0.0010, segs=3)

# counterweight with knurled band (diamond lattice pyramids, geometry)
CW_Y0, CW_LEN, CW_R = 0.028, 0.030, 0.017
cwrot = basis_obj_rot(Vector((1, 0, 0)), Vector((0, 0, -1)), Vector((0, 1, 0)))   # local z -> +Y
cw = arm_obj('Counterweight', lathe('Counterweight', [(0.0, 0.0), (CW_R - 0.001, 0.0), (CW_R, 0.0012), (CW_R, CW_LEN - 0.0012), (CW_R - 0.001, CW_LEN),
                                                       (0.0062, CW_LEN), (0.0062, CW_LEN + 0.002), (0.0, CW_LEN + 0.002)], 128),
             [MAT['chrome']], loc=(0, CW_Y0, 0), rot=cwrot)
hard(cw, w=0.0006, segs=3, angle=30)
cwring = arm_obj('CounterweightRing', lathe('CWRing', [(0.0, 0.0), (CW_R + 0.0003, 0.0), (CW_R + 0.0003, 0.004), (0.0, 0.004)], 128), [MAT['anod']],
                 loc=(0, CW_Y0 - 0.0003, 0), rot=cwrot)
hard(cwring, w=0.0005, segs=2)
tickm = arm_obj('CWIndex', prism('CWIndex', rrect(0.0008, 0.0035, 0.0002, 2), 0, 0.00012), [MAT['saffron_paint']],
                loc=(0, CW_Y0 + 0.0017, CW_R + 0.0003))
# knurl
nu_k, pitch_a = 108, 0.00095
band0, band1 = 0.0075, 0.0235
rows_k = int((band1 - band0) / (pitch_a / 2))
kv, kf = [], []
hk = 0.00034
for jr in range(rows_k):
    yk = band0 + jr * pitch_a / 2
    off = 0.5 * (jr % 2)
    for ik in range(nu_k):
        a = TAU * (ik + off) / nu_k
        da = TAU / nu_k / 2 * 0.98
        dy = pitch_a / 2 * 0.98
        base = len(kv)
        pts4 = [(a - da, yk), (a, yk - dy), (a + da, yk), (a, yk + dy)]
        for (aa, yy) in pts4:
            kv.append(((CW_R - 0.00005) * math.cos(aa), yy, (CW_R - 0.00005) * math.sin(aa)))
        kv.append(((CW_R + hk) * math.cos(a), yk, (CW_R + hk) * math.sin(a)))
        for q in range(4):
            kf.append((base + q, base + (q + 1) % 4, base + 4))
kme = mesh('Knurl', kv, kf, smooth=False)
bm = bmesh.new(); bm.from_mesh(kme)
for fc in bm.faces:
    c_ = fc.calc_center_median(); radial = Vector((c_.x, 0, c_.z)).normalized()
    if fc.normal.dot(radial) < 0: fc.normal_flip()
bm.to_mesh(kme); bm.free()
knurl = arm_obj('Knurl', kme, [MAT['chrome']], loc=(0, CW_Y0, 0))
print('KNURL pyramids', rows_k * nu_k)

# anti-skate dial with 30 ticks + saffron index
AS = Vector((0.040, -0.026, Z_BASE0))
asd = arm_obj('AntiSkateDial', cyl('AntiSkate', 0.012, 0.0075, 96, 0.0), [MAT['anod']], loc=AS); hard(asd, w=0.0012, segs=3)
asr = arm_obj('AntiSkateSkirt', cyl('AntiSkateSkirt', 0.0124, 0.0025, 96, 0.0), [MAT['chrome']], loc=AS); hard(asr, w=0.0005, segs=2)
tv_, tf_ = [], []
for kk in range(30):
    a = TAU * kk / 30; ca_, sa_ = math.cos(a), math.sin(a)
    r0_, r1_ = (0.0088 if kk % 5 == 0 else 0.0095), 0.0112
    wv = 0.00022
    base = len(tv_)
    for (rr, ww) in ((r0_, -wv), (r1_, -wv), (r1_, wv), (r0_, wv)):
        tv_.append((rr * ca_ - ww * sa_, rr * sa_ + ww * ca_, 0.0))
    tf_.append((base, base + 1, base + 2, base + 3))
arm_obj('AntiSkateTicks', mesh('ASTicks', tv_, tf_, smooth=False), [MAT['chalk']], loc=AS + Vector((0, 0, 0.00752)))
idx_ = arm_obj('AntiSkateIndex', prism('ASIndex', rrect(0.0075, 0.0011, 0.0004, 2), 0, 0.00006), [MAT['saffron_paint']],
               loc=AS + Vector((0.0036, 0, 0.0075)))
asknob = arm_obj('AntiSkateKnob', cyl('ASKnob', 0.0035, 0.003, 48, 0.0075), [MAT['chrome']], loc=AS); hard(asknob, w=0.0006, segs=2)

# stylus-tip bookkeeping on the pivot empty (for Set C)
arm_root['stylus_tip_local'] = list(T_loc)
arm_root['cartridge_forward_local'] = list(f)
arm_root['arm_effective_length_m'] = ARM_L
arm_root['plinth_plate_local_z'] = Z_BASE0
arm_root['note'] = 'Origin = horizontal gimbal pivot. Arm points along local -Y; stylus tip at stylus_tip_local. Real scale metres.'

# ---- write the asset file now (pivot at origin, identity)
asset_path = os.path.join(ROOT, 'blend', 'tonearm_asset.blend')
os.makedirs(os.path.dirname(asset_path), exist_ok=True)
bpy.data.libraries.write(asset_path, {COL_ARM}, fake_user=True, compress=True)
print('ASSET_WRITTEN', asset_path, len(COL_ARM.objects), 'objects')

# place the arm on the turntable
arm_root.location = (PIV.x, PIV.y, Z_PIV)
arm_root.rotation_euler = (0, 0, PSI)
bpy.context.view_layer.update()
STY_W = arm_root.matrix_world @ T_loc
HEAD_W = arm_root.matrix_world @ hs_point(-0.012, 0, -0.004)
CART_W = arm_root.matrix_world @ hs_point(-0.009, 0, (z_cb + z_hb) / 2)
CANT_W = arm_root.matrix_world @ (E_tip * 0.6 + R0 * 0.4)
print('STYLUS_WORLD', tuple(round(c, 5) for c in STY_W), 'expected xy', tuple(round(c, 5) for c in STY2))

# arm rest + cue lever (turntable)
ar = PIV + Vector((0.030, -0.105))
post = new_obj('ArmRestPost', cyl('ArmRestPost', 0.0042, Z_PIV - Z_PLATE - 0.008, 48, Z_PLATE), COL_TT, [MAT['chrome']], loc=(ar.x, ar.y, 0)); hard(post, w=0.0006, segs=2)
cr_ = new_obj('ArmRestCradle', prism('Cradle', rrect(0.010, 0.016, 0.003, 6), Z_PIV - 0.008, Z_PIV - 0.0035), COL_TT, [MAT['rubber']], loc=(ar.x, ar.y, 0)); hard(cr_, w=0.0008, segs=2)
cl = PIV + Vector((0.040, 0.008))
cpost = new_obj('CuePost', cyl('CuePost', 0.006, 0.014, 48, Z_PLATE), COL_TT, [MAT['chrome']], loc=(cl.x, cl.y, 0)); hard(cpost, w=0.0008, segs=2)
lever_pts = [Vector((cl.x, cl.y, Z_PLATE + 0.012)), Vector((cl.x + 0.006, cl.y - 0.012, Z_PLATE + 0.014)), Vector((cl.x + 0.010, cl.y - 0.026, Z_PLATE + 0.017))]
new_obj('CueLever', sweep('CueLever', lever_pts, [(0.0016 * math.cos(a), 0.0016 * math.sin(a)) for a in np.linspace(0, TAU, 16, endpoint=False)]), COL_TT, [MAT['chrome']])
kb = bpy.data.meshes.new('CueKnob'); bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=0.0042); bm.to_mesh(kb); bm.free(); kb.shade_smooth()
new_obj('CueKnob', kb, COL_TT, [MAT['ultra_knob']], loc=lever_pts[-1])

# ------------------------------------------------------------------ lights

def aim(ob, target):
    d = Vector(target) - ob.location
    ob.rotation_mode = 'QUATERNION'; ob.rotation_quaternion = d.to_track_quat('-Z', 'Y')


def light(name, typ, energy, loc, target, color=None, size=None, size_y=None, temp=None, spot=None, diffuse=1.0, specular=1.0,
          shadow=True, soft=None):
    ld = bpy.data.lights.new(name, typ); ld.energy = energy
    if color is not None: ld.color = color
    if temp is not None:
        ld.use_temperature = True; ld.temperature = temp
    if typ == 'AREA':
        if size_y is not None: ld.shape = 'RECTANGLE'; ld.size = size; ld.size_y = size_y
        else: ld.shape = 'SQUARE'; ld.size = size
    if typ == 'SPOT':
        ld.spot_size = math.radians(spot); ld.spot_blend = 0.6; ld.shadow_soft_size = 0.05
    if soft is not None: ld.shadow_soft_size = soft
    ld.diffuse_factor = diffuse; ld.specular_factor = specular
    ld.use_shadow = shadow
    try: ld.shadow_maximum_resolution = 0.0003
    except Exception: pass
    ob = new_obj(name, ld, COL_STUDIO, loc=loc); aim(ob, target)
    return ob


CENTER = Vector((SX + 0.045, 0.0, Z_REC))
# Key: near-neutral warm (#FFE6CC) so Magenta stays magenta and the label stays Saffron; cross-fades to #F4EEFF
# in the capture. 30 deg elevation (60 deg from vertical): its coat reflection stays outside the top-down
# f283-288 frustum (half-diagonal 36 deg) for every co-rotation angle.
KEY_HOLD, KEY_END = C.hex2lin('#FFE6CC'), C.hex2lin('#F4EEFF')
KEY_E, KEY_E_END = 32.0, 27.0
kdir = Vector((-0.73, -0.62, 0.0)).normalized()
KEY_LOC = CENTER + kdir * 1.15 + Vector((0, 0, 0.66))
key = light('Key', 'AREA', KEY_E, KEY_LOC, CENTER, color=KEY_HOLD, size=0.6)
rim = light('RimMagenta', 'SPOT', 38.0, RIM_LOC, Vector((PIV.x - 0.03, PIV.y - 0.02, Z_PIV)), color=L('magenta'), spot=30, specular=0.6)   # back-rims arm + plinth (label excluded via light linking)
fill = light('FillUltra', 'AREA', 10.0, (0.92, -0.30, 0.45), CENTER, color=L('ultramarine'), size=0.5)
# back card: large violet softbox behind the turntable (as seen from the hold camera): mostly specular, so the
# anodised plate, the chrome and the vinyl coat pick up a coloured reflection instead of black.
back = light('BackViolet', 'AREA', 26.0, BACK_LOC, CENTER, color=tuple(0.6 * a + 0.4 * b_ for a, b_ in zip(L('violet'), L('ultramarine'))),
             size=0.9, size_y=0.40, diffuse=0.30, specular=1.0)
STRIPS = []
for i, y0 in enumerate((-0.20, 0.22)):
    s_ = light('Strip%d' % i, 'AREA', 15.0, (CENTER.x, y0, 0.78), (CENTER.x, y0, 0.0), temp=5600, size=2.6, size_y=0.06, diffuse=0.12)   # streak-makers: mostly specular so the marble is not flooded pastel
    s_.rotation_mode = 'XYZ'; s_.rotation_euler = (0, 0, 0)
    pe = new_obj('StripPanel%d' % i, prism('StripPanel', rrect(3.0, 0.12, 0.01, 3), 0.0, 0.002), COL_STUDIO, [MAT['strip']], loc=(CENTER.x, y0, 0.783))
    pe.visible_camera = False; pe.visible_shadow = False
    STRIPS.append((s_, pe, y0))

# macro accents (f121-160): two tiny coloured specular-only glints by the stylus so the black-diamond facets flash
# ultramarine / magenta, and a warm kicker that draws a saffron line along the cantilever top (echo of S1's spire).
F_W = (arm_root.matrix_world.to_3x3() @ f).normalized()
V_W = (arm_root.matrix_world.to_3x3() @ v).normalized()
DC_W = (arm_root.matrix_world.to_3x3() @ dir_c).normalized()
ETIP_W = arm_root.matrix_world @ E_tip
R0_W = arm_root.matrix_world @ R0
ZW = Vector((0, 0, 1))
MACRO_LIGHTS = []
for nm, col, off, en in (('GlintUltra', L('ultramarine'), F_W * 0.0035 + V_W * 0.0030 + ZW * 0.0022, 0.005),
                         ('GlintMagenta', L('magenta'), F_W * 0.0030 - V_W * 0.0032 + ZW * 0.0012, 0.005)):
    ld = bpy.data.lights.new(nm, 'POINT'); ld.energy = en; ld.color = col; ld.shadow_soft_size = 0.0003
    ld.diffuse_factor = 0.0; ld.use_shadow = False
    MACRO_LIGHTS.append((new_obj(nm, ld, COL_STUDIO, loc=ETIP_W + off), en))

# reflection probe at the platter
lpd = bpy.data.lightprobes.new('PlatterProbe', 'SPHERE')
try:
    lpd.influence_distance = 0.4; lpd.clip_start = 0.002
except Exception as ex: print('probe props', ex)
new_obj('PlatterProbe', lpd, COL_STUDIO, loc=(SX, SY, Z_REC + 0.08))

# ------------------------------------------------------------------ animation: platter, strobe rows, strips, lights

def key_linear(ob, path, idx, pairs):
    for fr, val in pairs:
        if idx is None: setattr(ob, path, val); ob.keyframe_insert(path, frame=fr)
        else:
            getattr(ob, path)[idx] = val; ob.keyframe_insert(path, index=idx, frame=fr)
    ad = ob.animation_data
    for fc in _fcurves(ad):
        for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
        try: fc.extrapolation = 'LINEAR'
        except Exception: pass


def _fcurves(ad):
    act = ad.action
    if hasattr(act, 'fcurves'):
        try: return list(act.fcurves)
        except Exception: pass
    out = []
    try:
        for lay in act.layers:
            for st in lay.strips:
                for cb in st.channelbags: out += list(cb.fcurves)
    except Exception as ex: print('fcurve access', ex)
    return out


def kf(owner, path, pairs):
    """Bezier keys of a scalar/vector property: pairs = [(frame, value), ...]."""
    for fr, val in pairs:
        setattr(owner, path, val); owner.keyframe_insert(path, frame=fr)


PLATTER_PHASE = math.radians(17.0)
def platter_angle(fr):
    return PLATTER_PHASE - math.radians(RPM_DEG) * (fr - F0) / FPS


key_linear(platter_rot, 'rotation_euler', 2, [(F0 - 20, platter_angle(F0 - 20)), (F1 + 20, platter_angle(F1 + 20))])
for ob, app in STROBE:
    ph0 = math.radians(0.37 * len(ob.name))
    key_linear(ob, 'rotation_euler', 2, [(F0 - 20, ph0 + math.radians(app) * (-20) / FPS), (F1 + 20, ph0 + math.radians(app) * (F1 + 20 - F0) / FPS)])
for s_, pe, y0 in STRIPS:
    for ob in (s_, pe):
        key_linear(ob, 'location', 1, [(F0, y0 - 0.15), (F1, y0 + 0.15)])
# capture: everything world-fixed that could sweep through the still frames fades out before the lock
for s_, pe, y0 in STRIPS:
    kf(s_.data, 'energy', [(238, 15.0), (251, 0.0)])
# panels only seed soft chrome reflections (via the sphere probe); at 25 their probe reflection drew a pale bar on the vinyl
kf(STRIP_VAL.outputs[0], 'default_value', [(238, 5.0), (251, 0.0)])
kf(rim.data, 'energy', [(252, 45.0), (268, 0.0)])
kf(back.data, 'energy', [(252, 26.0), (268, 0.0)])
SHEEN_HOLD = {'rim': 2.5, 'back': 2.0}
for key_ in ('rim', 'back'):
    for sv_ in SHEEN_VALS.get(key_, []):
        # low through the macro/downbeat (no magenta glare next to the cartridge), full radial sheen in the hold
        kf(sv_.outputs[0], 'default_value', [(F0, 0.3), (160, 0.3), (182, SHEEN_HOLD[key_]), (244, SHEEN_HOLD[key_]), (255, 0.0)])
# chalk veins -> white point of the close-up
for cc_ in COATCUE_VALS:
    kf(cc_.outputs[0], 'default_value', [(279, 0.0), (283, COATCUE_AMP)])
for ve_ in VEIN_EMIT:
    kf(ve_.outputs[0], 'default_value', [(262, 0.0), (278, VEIN_EMIT_E)])
# exposure lift for the close-up (key specular is already 0 by f256: no wash risk)
kf(sc.view_settings, 'exposure', [(262, -0.5), (280, EXPO_END)])
kf(key.data, 'color', [(250, KEY_HOLD), (275, KEY_END)])
kf(key.data, 'energy', [(250, KEY_E), (275, KEY_E_END)])
# the key's coat reflection must not sweep the run-out as the co-rotating camera passes opposite it (f262-288)
kf(key.data, 'specular_factor', [(226, 1.0), (240, 0.35), (256, 0.0)])
# dim the HDRI during the capture: at the grazing dive angles its white softboxes washed the far vinyl
_bgs = sc.world.node_tree.nodes['Background'].inputs['Strength']
kf(_bgs, 'default_value', [(246, 0.12), (262, 0.035)])
# the studio dims as the capture dives in: less bright cyc mirrored in the far half of the record at f250-266
for _cs in COVE_STRENGTH:
    kf(_cs, 'default_value', [(244, 0.40), (262, 0.22)])
# strobe lamp flares as the capture swings past the platter rim (row 216 hangs frozen against drifting rows)
sw = MAT['strobe_win'].node_tree.nodes['Principled BSDF'].inputs['Emission Strength']
kf(sw, 'default_value', [(238, 30.0), (245, 140.0), (253, 140.0), (260, 30.0)])
kf(STROBE_PT.data, 'energy', [(170, 0.5), (184, 3.0), (238, 3.0), (245, 5.0), (253, 5.0), (260, 3.0)])
for ob, en in MACRO_LIGHTS:
    kf(ob.data, 'energy', [(127, en), (137, 0.0)])
for kv in CANT_TINT:
    kf(kv.outputs[0], 'default_value', [(F0 - 2, 1.0), (125, 1.0), (131, 0.0)])
# shutter: crisp macro open (fast surface), product-film 0.25 from the reveal on
try:
    kf(sc.render, 'motion_blur_shutter', [(F0, 0.08), (138, 0.08), (158, 0.25)])
    # NOTE (09:30 mb-fix attempt): a 0.08 shutter keyed over f256-272 did NOT remove the lilac veil in the lower
    # middle of f258-270 (renders/tests/set_b/mb1_ab_*.png: identical veil before/after) -> it is a glossy-coat
    # reflection, not motion blur. Reverted to the 0.25 shutter; fix the reflection source instead.
except Exception as ex:
    print('SHUTTER_KF_FAIL', ex)

# ------------------------------------------------------------------ camera rig + baked S2 move

rig = empty('SpinRig', COL_STUDIO, loc=(SX, SY, 0.0), size=0.05)
camd = bpy.data.cameras.new('CamS2'); camd.sensor_fit = 'HORIZONTAL'; camd.sensor_width = 36.0
camd.dof.use_dof = True; camd.dof.aperture_blades = 7; camd.dof.aperture_rotation = math.radians(10)
cam = new_obj('CamS2', camd, COL_STUDIO, parent=rig); sc.camera = cam
cam.rotation_mode = 'QUATERNION'
camd.clip_end = 8.0


def sstep(x):
    x = min(1.0, max(0.0, x)); return x * x * (3 - 2 * x)


def sstep5(x):
    x = min(1.0, max(0.0, x)); return x * x * x * (x * (x * 6 - 15) + 10)


def pchip(ts, ys, t, d0=0.0, d1=0.0):
    """Monotone cubic (Fritsch-Carlson) through (ts, ys); end slopes d0/d1 (units per second)."""
    ts = np.asarray(ts, float); ys = np.asarray(ys, float); n = len(ts)
    if t <= ts[0]: return float(ys[0] + d0 * (t - ts[0])) if d0 and t > ts[0] - 0.2 else float(ys[0])
    if t >= ts[-1]: return float(ys[-1])
    h = np.diff(ts); dl = np.diff(ys) / h
    d = np.zeros(n); d[0] = d0; d[-1] = d1
    for k in range(1, n - 1):
        if dl[k - 1] * dl[k] > 0:
            w1 = 2 * h[k] + h[k - 1]; w2 = h[k] + 2 * h[k - 1]
            d[k] = (w1 + w2) / (w1 / dl[k - 1] + w2 / dl[k])
    k = int(min(n - 2, max(0, np.searchsorted(ts, t) - 1)))
    s = (t - ts[k]) / h[k]
    h00 = 2 * s ** 3 - 3 * s ** 2 + 1; h10 = s ** 3 - 2 * s ** 2 + s; h01 = -2 * s ** 3 + 3 * s ** 2; h11 = s ** 3 - s ** 2
    return float(h00 * ys[k] + h10 * h[k] * d[k] + h01 * ys[k + 1] + h11 * h[k] * d[k + 1])


# rig angular velocity (deg/s, negative = clockwise, same as the record). The capture spins the rig to -150 deg/s
# by f258 while the camera is still high (the studio, plinth and arm wheel round the frame), -200 (= record) by f270.
T_W1, T_W2 = (258 - F0) / FPS, (270 - F0) / FPS
def omega(t):
    if t < 1.5: return 0.0
    if t < 2.5: return -10.0 * sstep((t - 1.5) / 1.0)
    if t < 5.0: return -10.0
    if t < T_W1: return -10.0 - 140.0 * sstep((t - 5.0) / (T_W1 - 5.0))
    if t < T_W2: return -150.0 - 50.0 * sstep((t - T_W1) / (T_W2 - T_W1))
    return -RPM_DEG


_tt = np.linspace(-0.2, 7.2, 7401)
_om = np.array([omega(t) for t in _tt])
_th = np.concatenate([[0.0], np.cumsum((_om[1:] + _om[:-1]) * 0.5 * np.diff(_tt))])
_th -= np.interp(0.0, _tt, _th)
def rig_angle(t):          # radians
    return math.radians(float(np.interp(t, _tt, _th)))


def rotz(a):
    return Matrix.Rotation(a, 3, 'Z')


S3 = Vector((SX, SY, 0.0))
def to_local(pw, t):
    """world point -> rig local (rig at S, rotated by rig_angle)."""
    return rotz(-rig_angle(t)) @ (Vector(pw) - S3)


def dirv(el, az):
    el, az = math.radians(el), math.radians(az)
    return Vector((-math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))


def look_quat(c, target, up):
    fw = (target - c).normalized()
    x = fw.cross(up)
    if x.length < 1e-8: x = fw.cross(Vector((0, 1, 0)))
    x.normalize(); y = x.cross(fw)
    return Matrix((x, y, -fw)).transposed().to_quaternion()


# ---- phase A (f121-180): macro open looking back along the cantilever (a bright alu wedge rising from the black
# diamond toward the top of frame = S1's spire), rise + pull back over the front of the cartridge to a clean 3/4
# profile at the f145 downbeat, then out to the high three-quarter hold.
LABEL_W = Vector((SX, SY, Z_REC0 + REC_LABEL_TOP)) + Vector((0.0, 0.016, 0))
T_HOLD_L = (Vector((SX, SY, 0)) + (HEAD_W - Vector((SX, SY, 0))) * 0.55 - S3)
T_HOLD_L.z = Z_REC + 0.018
D1 = 0.43
EL1, AZ1 = 28.0, 30.0
LENS0, LENS1, LENS_END = 28.0, 40.0, 28.0
# f121 = S1 f120 match: camera rides 0.38 mm above the cantilever axis, 1 mm back from the tip, looking back along
# the tube pitched 24 deg below its axis (= 4 deg below horizontal, horizon ~1/3 from the top like S1). The tapered
# tube runs out of the frame bottom ~65% wide and converges to an apex at the top edge (S1's spire cone).
A_W = (-DC_W).normalized()                                    # tip -> back, rising 20 deg
NRM_W = (F_W * math.sin(math.radians(20)) + ZW * math.cos(math.radians(20))).normalized()
MAC_S0, MAC_H, MAC_BETA = 0.0010, 0.00038, math.radians(24.0)
_Q = ETIP_W + A_W * MAC_S0
MAC_C = _Q + NRM_W * MAC_H
_vd = (A_W * math.cos(MAC_BETA) - NRM_W * math.sin(MAC_BETA)).normalized()
MAC_T = MAC_C + _vd * 0.003
CANT_FOCUS_W = _Q + A_W * 0.0012                             # tube point ~1.2 mm ahead of the lens (whole tube in focus)
_o = MAC_C - MAC_T
AZ0 = math.degrees(math.atan2(-_o.x, -_o.y)); EL0 = math.degrees(math.asin(_o.z / _o.length)); D0 = _o.length
CANT_MID_W = arm_root.matrix_world @ (E_tip * 0.45 + R0 * 0.55)
TGT145_W = arm_root.matrix_world @ (E_tip * 0.45 + hs_point(-0.008, 0, z_cb + 0.007) * 0.55)
A_T = [0.0, 0.30, 1.0, 1.65, 2.5]
A_LOGD = [math.log(D0), math.log(0.0075), math.log(0.072), math.log(0.20), math.log(D1)]
A_EL = [EL0, 12.0, 22.0, 25.0, EL1]
A_AZ = [AZ0, AZ0 - 10.0, 12.0, 22.0, AZ1]
A_LENS = [28.0, 28.0, 30.0, 35.0, 40.0]
print('PHASEA start az/el/d', round(AZ0, 1), round(EL0, 1), round(D0, 5))


def phaseA(t):
    """t in [0,2.5]: returns (cam_local, target_local, up, lens, focus_point_local)."""
    pts = [to_local(MAC_T, t), to_local(CANT_MID_W, t), to_local(TGT145_W, t),
           to_local(TGT145_W, t).lerp(T_HOLD_L, 0.55), T_HOLD_L]
    tgt = Vector([pchip(A_T, [p[i] for p in pts], t) for i in range(3)])
    d = math.exp(pchip(A_T, A_LOGD, t, d0=2.2))
    el = pchip(A_T, A_EL, t, d0=18.0)
    az = pchip(A_T, A_AZ, t)
    c = tgt + dirv(el, az) * d
    lens = pchip(A_T, A_LENS, t)
    return c, tgt, Vector((0, 0, 1)), lens, tgt


C_HOLD, T_HOLD, _, _, _ = phaseA(2.5)
C_HOLD = C_HOLD.copy()
DOLLY = 0.060     # slow push during the hold (m)
HOLD_RISE = math.radians(6.0)   # elevation drift during the hold (parallax: blurred counterweight slides on the cyc)


def hold_pose(t):
    u = (t - 2.5) / 2.5
    k = sstep(u) if t < 5.0 else 1.0
    off = C_HOLD - T_HOLD
    ax = off.cross(Vector((0, 0, 1))).normalized()
    off = Matrix.Rotation(HOLD_RISE * k, 3, ax) @ off     # + = crane up
    dvec = (-off).normalized()
    return T_HOLD + off + dvec * (DOLLY * k), T_HOLD


# ---- phase C (f241-282): the capture. Waypoints in rig-local cylindrical coords around the spindle.
R_END, H_END = 0.074, 0.050
t_cap0, t_cap1 = 5.0, (282 - F0) / FPS
_c0, _ = hold_pose(5.0)
r0_ = math.hypot(_c0.x, _c0.y); a0_ = math.atan2(_c0.y, _c0.x); h0_ = _c0.z - Z_REC
CAP_SWING = -36.421    # deg; pinned so the f288 record-space frame (S2_end handoff) is unchanged by hold tweaks
alpha_end = a0_ + math.radians(CAP_SWING)
Q_L = Vector((R_END * math.cos(alpha_end), R_END * math.sin(alpha_end), Z_REC))
C_END = Q_L + Vector((0, 0, H_END))
U_END = Vector((-math.cos(alpha_end), -math.sin(alpha_end), 0.0))     # top of frame points to the spindle
C_T = [t_cap0, (254 - F0) / FPS, (264 - F0) / FPS, (273 - F0) / FPS, t_cap1]
C_R = [r0_, 0.30, 0.21, 0.115, R_END]
C_H = [h0_, 0.200, 0.135, 0.075, H_END]
C_A = [0.0, -8.0, -16.0, -26.0, CAP_SWING]
C_RT = [0.0, 0.0, 0.060, 0.072, R_END]
C_LENS = [40.0, 35.0, 31.0, 28.5, 28.0]
print('CAPTURE start r/h', round(r0_, 3), round(h0_, 3))


def phaseC(t):
    u = min(1.0, max(0.0, (t - t_cap0) / (t_cap1 - t_cap0)))
    if u >= 1.0:
        return C_END.copy(), Q_L.copy(), U_END.copy(), LENS_END, 1.0
    r = pchip(C_T, C_R, t); h = pchip(C_T, C_H, t); a = a0_ + math.radians(pchip(C_T, C_A, t))
    rt = pchip(C_T, C_RT, t)
    c = Vector((r * math.cos(a), r * math.sin(a), Z_REC + h))
    tp = Vector((rt * math.cos(a), rt * math.sin(a), Z_REC))
    tgt = T_HOLD.lerp(tp, sstep((t - t_cap0) / 0.55))
    fw = (tgt - c).normalized()
    pitch = math.degrees(math.asin(max(-1.0, min(1.0, -fw.z))))
    su = sstep((pitch - 50.0) / 35.0)
    ua = Vector((-math.cos(a), -math.sin(a), 0.0))
    up = (Vector((0, 0, 1)) * (1 - su) + ua * su).normalized()
    lens = pchip(C_T, C_LENS, t)
    return c, tgt, up, lens, u


def cam_state(fr):
    t = (fr - F0) / FPS
    if t <= 2.5:
        c, tgt, up, lens, fpt = phaseA(t); mode = 'A'
    elif t <= 5.0:
        c, tgt = hold_pose(t); up = Vector((0, 0, 1)); lens = LENS1; mode = 'B'; fpt = None
    else:
        c, tgt, up, lens, u = phaseC(t); mode = 'C'; fpt = None
    q = look_quat(c, tgt, up)
    fw = (tgt - c).normalized()
    # focus
    if mode == 'A':
        fpt_ = to_local(CANT_FOCUS_W, t).lerp(fpt, sstep((t - 0.10) / 0.45))
        fdist = max(2e-4, (fpt_ - c).dot(fw))
    elif mode == 'B':
        fh = (to_local(HEAD_W, t) - c).dot(fw)
        fl = (to_local(LABEL_W, t) - c).dot(fw)
        rk = sstep(((fr - 217) / 12.0))
        fdist = 1.0 / ((1 - rk) / fh + rk / fl)
    else:
        c5, _t5 = hold_pose(5.0)
        lab = (to_local(LABEL_W, 5.0) - c5).dot((_t5 - c5).normalized())
        ftg = (tgt - c).dot(fw)
        k_ = sstep((t - 5.0) / 0.4)
        fdist = 1.0 / ((1 - k_) / lab + k_ / ftg)
    # aperture: blur ratio (aperture diameter / focus distance)
    if mode == 'A':
        # tack-sharp cut from S1 (DOF off there), shallow product DOF arrives during the pull-out
        t132 = (132 - F0) / FPS
        if t < 0.25: ratio = 0.002
        elif t < t132: ratio = 0.002 + (0.030 - 0.002) * sstep((t - 0.25) / (t132 - 0.25))
        else: ratio = 0.030 + (0.024 - 0.030) * sstep((fr - 132) / 13.0)
    elif mode == 'B':
        ratio = 0.024
    else:
        ratio = 0.024 + (0.010 - 0.024) * sstep((t - 5.0) / 0.8) + (0.008 - 0.010) * sstep((t - 5.8) / 0.9)
    fstop = (lens * 0.001) / max(1e-6, ratio * fdist)
    near = min(fdist, c.z - Z_REC + 0.0004)
    clip = max(1.5e-5, 0.04 * near)
    return c, q, lens, fdist, fstop, clip, mode


qprev = None
LOG = []
for fr in range(F0 - 2, F1 + 3):
    t = (fr - F0) / FPS
    c, q, lens, fdist, fstop, clip, mode = cam_state(fr)
    if qprev is not None and q.dot(qprev) < 0: q.negate()
    qprev = q.copy()
    cam.location = c; cam.rotation_quaternion = q
    cam.keyframe_insert('location', frame=fr); cam.keyframe_insert('rotation_quaternion', frame=fr)
    camd.lens = lens; camd.keyframe_insert('lens', frame=fr)
    camd.dof.focus_distance = fdist; camd.dof.keyframe_insert('focus_distance', frame=fr)
    camd.dof.aperture_fstop = fstop; camd.dof.keyframe_insert('aperture_fstop', frame=fr)
    camd.clip_start = clip; camd.keyframe_insert('clip_start', frame=fr)
    rig.rotation_euler[2] = rig_angle(t); rig.keyframe_insert('rotation_euler', index=2, frame=fr)
    LOG.append((fr, mode, tuple(round(x, 4) for x in c), round(lens, 1), round(fdist, 4), round(fstop, 1), round(clip, 6)))
for fc in _fcurves(rig.animation_data):
    for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
for fr_, mode, c, lens, fd, fs, cl in LOG[::6]:
    print('CAM', fr_, mode, c, 'lens', lens, 'focus', fd, 'f/', fs, 'clip', cl)

# arm specular line card: a long thin warm-white light parallel to the S-arm, placed (for the mid-hold camera)
# so the mirror condition holds along the tube's upper camera-side flank -> one continuous crisp line.
sc.frame_set(210); bpy.context.view_layer.update()
CAM_HOLD_W = cam.matrix_world.translation.copy()
ARM_A = arm_root.matrix_world @ Vector((0, -0.02, 0)); ARM_B = arm_root.matrix_world @ hs_point(-0.056, 0, 0)
ARM_M = (ARM_A + ARM_B) / 2; ARM_AX = (ARM_B - ARM_A).normalized()
Vv = (CAM_HOLD_W - ARM_M).normalized()
perp = (Vv - ARM_AX * Vv.dot(ARM_AX)).normalized()
nrm_ = (ZW * 0.85 + perp * 0.55); nrm_ = (nrm_ - ARM_AX * nrm_.dot(ARM_AX)).normalized()
Ldir = (nrm_ * (2 * nrm_.dot(Vv)) - Vv).normalized()
ARM_CARD_LOC = ARM_M + Ldir * 0.42
armcard = light('ArmLineCard', 'AREA', 7.0, ARM_CARD_LOC, ARM_M, color=C.hex2lin('#FFF1E2'), size=0.02, size_y=0.55,
                diffuse=0.0, shadow=False)
# orient the long side (local Y) parallel to the arm axis while facing the arm
zc_ = (ARM_CARD_LOC - ARM_M).normalized()
yc_ = (ARM_AX - zc_ * ARM_AX.dot(zc_)).normalized(); xc_ = yc_.cross(zc_)
armcard.rotation_quaternion = Matrix((xc_, yc_, zc_)).transposed().to_quaternion()
kf(armcard.data, 'energy', [(150, 0.0), (172, 7.0), (250, 7.0), (262, 0.0)])
print('ARM_CARD', tuple(round(x, 3) for x in ARM_CARD_LOC))


def link_light(light_ob, objs, state):
    """EEVEE light linking: INCLUDE = only these receive the light; EXCLUDE = everything but these."""
    try:
        coll = bpy.data.collections.new(light_ob.name + '_Receivers')
        for o in objs: coll.objects.link(o)
        light_ob.light_linking.receiver_collection = coll
        for co in coll.collection_objects:
            co.light_linking.link_state = state
        print('LIGHTLINK', light_ob.name, state, len(objs))
    except Exception as ex:
        print('LIGHTLINK_FAIL', light_ob.name, ex)


# the arm card must only draw the line on the arm (its coat reflection made a white radial streak across the vinyl);
# the violet back card colours the plate/chrome/plinth but must not wash the marble with a lilac sheet.
link_light(armcard, [o for o in COL_ARM.objects if o.type in ('MESH', 'CURVE')], 'INCLUDE')
_vinyl_objs = [record] + [o for o in record.children if o.type == 'MESH']
link_light(back, _vinyl_objs, 'EXCLUDE')
# the magenta rim rakes the vinyl but must not tint the Saffron label paper
link_light(rim, [label] + [o for o in record.children if o.name.startswith(('Txt_', 'LabelRing'))], 'EXCLUDE')
# strips draw streaks on the chrome and lacquer only: on the vinyl their sheen-stretched reflection was a hard white radial bar
link_light(STRIPS[0][0], [record] + [o for o in record.children if o.type == 'MESH'], 'EXCLUDE')
link_light(STRIPS[1][0], [record] + [o for o in record.children if o.type == 'MESH'], 'EXCLUDE')
# keep the rim's grazing vinyl glare out of the macro/downbeat frames
kf(rim.data, 'specular_factor', [(F0, 0.0), (160, 0.0), (180, 0.6)])     # no grazing magenta glare by the cartridge
# macro glints only flash the diamond facets (they drew pink blobs on the cantilever / record before)
for ob, en in MACRO_LIGHTS:
    link_light(ob, [sty], 'INCLUDE')


def reflect_dir(P, camp, n):
    """unit direction from surface point P toward where a light must be for the camera at camp to see it mirrored at P."""
    V = (camp - P).normalized()
    return (n * (2 * n.dot(V)) - V).normalized()


def orient_rect(ob, target, long_axis):
    zc = (ob.location - target).normalized()
    yc = (long_axis - zc * long_axis.dot(zc)).normalized(); xc = yc.cross(zc)
    ob.rotation_mode = 'QUATERNION'; ob.rotation_quaternion = Matrix((xc, yc, zc)).transposed().to_quaternion()


# (1) VinylStreak: one thin crisp coat reflection crossing the far programme area in the hold (mirror-solved for the
# mid-hold camera, plane normal +Z), sliding as the camera orbits. Linked to the record only.
sc.frame_set(205); bpy.context.view_layer.update()
_camL = cam.location.copy()                                   # rig-local camera position at f205
_dfar = -_camL.copy(); _dfar.z = 0; _dfar.normalize()
_pd = Matrix.Rotation(math.radians(STREAK_ROT), 3, 'Z') @ _dfar
STREAK_P = Vector((0, 0, Z_REC)) + _pd * 0.12
_ld = reflect_dir(STREAK_P, _camL, Vector((0, 0, 1)))
_a = Vector((0, 0, 1)).cross(_ld).normalized(); _b = _ld.cross(_a)
_u = _a * math.cos(math.radians(40)) + _b * math.sin(math.radians(40))
vstreak = light('VinylStreak', 'AREA', STREAK_E, STREAK_P + _ld * 0.65, STREAK_P, color=C.hex2lin('#FFF1E2'), size=0.005, size_y=0.9,
                diffuse=0.0, shadow=False)
vstreak.parent = rig; vstreak.location = STREAK_P + _ld * 0.65
orient_rect(vstreak, STREAK_P, _u)
kf(vstreak.data, 'energy', [(150, 0.0), (176, STREAK_E), (250, STREAK_E), (262, 0.0)])
link_light(vstreak, [record], 'INCLUDE')
print('VINYL_STREAK', tuple(round(x, 3) for x in vstreak.location))

# (2) StylusGlint: tiny point light mirror-solved on the most camera-facing diamond facet at the f145 downbeat
sc.frame_set(145); bpy.context.view_layer.update()
_cam145 = cam.matrix_world.translation.copy()
_best = None
for poly in sty.data.polygons:
    nW = (sty.matrix_world.to_3x3() @ poly.normal).normalized(); cW = sty.matrix_world @ poly.center
    sc_ = nW.dot((_cam145 - cW).normalized())
    if abs(nW.z) < 0.5 and (_best is None or sc_ > _best[0]): _best = (sc_, nW, cW)
_gd = reflect_dir(_best[2], _cam145, _best[1])
gl_ = bpy.data.lights.new('StylusGlint', 'POINT'); gl_.energy = 0.0; gl_.color = C.hex2lin('#E8ECFF'); gl_.shadow_soft_size = 0.0004
gl_.diffuse_factor = 0.0; gl_.use_shadow = False
sglint = new_obj('StylusGlint', gl_, COL_STUDIO, loc=_best[2] + _gd * 0.006)
kf(gl_, 'energy', [(134, 0.0), (140, GLINT_E), (151, GLINT_E), (157, 0.0)])
link_light(sglint, [sty], 'INCLUDE')
print('STYLUS_GLINT facet dot', round(_best[0], 3), 'at', tuple(round(x, 4) for x in sglint.location))

# (3) LabelKick: soft spot from the camera side, riding on SpinRig (follows the orbit and the capture dive) so the
# Saffron label is the brightest warm patch and never browns out. Linked to the label paper + its ink only.
_lab_objs = [label] + [o for o in record.children if o.name.startswith(('Txt_', 'LabelRing'))]
lk_d = bpy.data.lights.new('LabelKick', 'SPOT'); lk_d.energy = LABELKICK_E; lk_d.color = C.hex2lin('#FFE6CC')
lk_d.spot_size = math.radians(25); lk_d.spot_blend = 0.5; lk_d.shadow_soft_size = 0.02; lk_d.specular_factor = 0.2
lkick = new_obj('LabelKick', lk_d, COL_STUDIO, parent=rig, loc=C_HOLD + Vector((0, 0, 0.12)))
aim(lkick, Vector((0, 0, Z_REC)))
link_light(lkick, _lab_objs, 'INCLUDE')

sc.frame_set(F0)

# ------------------------------------------------------------------ collision check (camera vs arm, plinth, record)
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
samples = []
for ob in A_ARM:
    ev = ob.evaluated_get(dg)
    try:
        me_ = ev.to_mesh()
        mw = ob.matrix_world
        n_ = len(me_.vertices); step = max(1, n_ // 400)
        samples += [mw @ me_.vertices[i].co for i in range(0, n_, step)]
        ev.to_mesh_clear()
    except Exception:
        pass
samples = np.array([tuple(p) for p in samples])
worst = (1e9, None)
for fr in range(F0, F1 + 1):
    sc.frame_set(fr)
    cw_ = np.array(tuple(cam.matrix_world.translation))
    dmin = float(np.min(np.linalg.norm(samples - cw_, axis=1)))
    hz = cw_[2] - Z_REC
    if dmin < worst[0]: worst = (dmin, fr)
    if fr in (121, 135, 150, 181, 217, 241, 250, 260, 270, 276, 282, 288):
        print('CHK', fr, 'cam', tuple(round(x, 4) for x in cw_), 'arm_dist', round(dmin, 4), 'h_above_vinyl', round(hz, 4))
print('ARM_MIN_DIST', worst)

# ------------------------------------------------------------------ compositor

def compositor():
    ng = bpy.data.node_groups.new('Comp_SetB', 'CompositorNodeTree'); sc.compositing_node_group = ng
    ng.interface.new_socket('Image', in_out='OUTPUT', socket_type='NodeSocketColor')
    N, Lk = ng.nodes, ng.links
    rl = N.new('CompositorNodeRLayers'); last = rl.outputs['Image']
    gl = N.new('CompositorNodeGlare'); gl.inputs['Type'].default_value = 'Bloom'
    gl.inputs['Threshold'].default_value = 1.2; gl.inputs['Strength'].default_value = 0.18; gl.inputs['Size'].default_value = 0.6
    Lk.new(last, gl.inputs['Image']); last = gl.outputs['Image']
    try:
        st = N.new('CompositorNodeGlare'); st.inputs['Type'].default_value = 'Streaks'
        st.inputs['Threshold'].default_value = 6.0; st.inputs['Strength'].default_value = 0.10
        st.inputs['Streaks'].default_value = 4; st.inputs['Fade'].default_value = 0.85
        st.inputs['Streaks Angle'].default_value = math.radians(45)
        Lk.new(last, st.inputs['Image']); last = st.outputs['Image']
    except Exception as ex: print('streaks skipped', ex)
    ld = N.new('CompositorNodeLensdist'); ld.inputs['Dispersion'].default_value = 0.004
    Lk.new(last, ld.inputs['Image']); last = ld.outputs['Image']
    hs_ = N.new('CompositorNodeHueSat'); hs_.inputs['Saturation'].default_value = 1.10
    Lk.new(last, hs_.inputs['Image']); last = hs_.outputs['Image']
    try:
        em = N.new('CompositorNodeEllipseMask')
        em.inputs['Size'].default_value = (0.9, 0.9)
        bl = N.new('CompositorNodeBlur')
        try: bl.inputs['Size'].default_value = (220, 220)
        except Exception: bl.inputs['Size'].default_value = 220
        Lk.new(em.outputs['Mask'], bl.inputs['Image'])
        mr = N.new('ShaderNodeMapRange'); mr.inputs['To Min'].default_value = 0.86; mr.inputs['To Max'].default_value = 1.0
        Lk.new(bl.outputs['Image'], mr.inputs['Value'])
        mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'
        mx.inputs['Factor'].default_value = 1.0
        Lk.new(last, mx.inputs[6]); Lk.new(mr.outputs['Result'], mx.inputs[7])
        last = mx.outputs[2]
    except Exception as ex: print('vignette skipped', ex)
    out = N.new('NodeGroupOutput'); Lk.new(last, out.inputs[0])


compositor()

# ------------------------------------------------------------------ handoff (S2_end)
sc.frame_set(F1)
bpy.context.view_layer.update()
cmw = cam.matrix_world; rmw = record.matrix_world; rinv = rmw.inverted()
o = rinv @ cmw.translation
dv_ = (rinv.to_3x3() @ (cmw.to_3x3() @ Vector((0, 0, -1)))).normalized()
upv = (rinv.to_3x3() @ (cmw.to_3x3() @ Vector((0, 1, 0)))).normalized()
tt = (REC_TOP - o.z) / dv_.z
pt = o + dv_ * tt
depth = tt
width = 2 * depth * (camd.sensor_width / 2) / camd.lens
sc.frame_set(F1 - 1); bpy.context.view_layer.update()
o2 = record.matrix_world.inverted() @ cam.matrix_world.translation
drift = (o2 - o).length
s2_end = {
    'frame': F1,
    'record_object': 'Record',
    'point_record_space_m': [round(pt.x, 6), round(pt.y, 6), round(pt.z, 6)],
    'point_radius_m': round(math.hypot(pt.x, pt.y), 6),
    'point_angle_deg': round(math.degrees(math.atan2(pt.y, pt.x)), 4),
    'cam_up_record_space': [round(upv.x, 6), round(upv.y, 6), round(upv.z, 6)],
    'cam_view_dir_record_space': [round(dv_.x, 6), round(dv_.y, 6), round(dv_.z, 6)],
    'visible_width_record_m': round(width, 6),
    'visible_height_record_m': round(width * 1440 / 2560, 6),
    'camera_height_above_vinyl_m': round(depth, 6),
    'lens_mm': camd.lens, 'sensor_width_mm': camd.sensor_width,
    'marble_scale': MARBLE_SCALE,
    'marble_freq': MARBLE_FREQ_REC,
    'marble_field_input': 'ND.build_marble_field(tree, vec, scale=marble_scale, freq=marble_freq) with vec = Record object coords (m) '
                          '(Texture Coordinate Object of the Record; z of the vinyl surface = point z). NOTE freq is NOT the ND default 2.2.',
    'record_rotation': 'clockwise seen from above, 200 deg/s; the S2 camera co-rotates exactly from f282 so f283-288 are still',
    'cam_drift_last_frame_m': round(drift, 8),
}
# ready-made desert mapping in Set C's convention (c_common.marble_mapping: field = rotZ(angle)*(x,y,0)*scale + offset,
# S3 f289 camera top-down at desert (880,0), screen-up +X, frame 488.6 m wide). Requires Set C to also pass
# freq=marble_freq to build_marble_field. Published under its own key (not 'set_c_marble') so Set C's look only
# changes when they adopt the freq too.
_k = width / 488.6
_S = MARBLE_SCALE * _k
_ang = math.atan2(upv.y, upv.x)
_U = Vector((math.cos(_ang), math.sin(_ang), 0.0))
_O = Vector((pt.x, pt.y, pt.z)) * MARBLE_SCALE - _U * (_S * 880.0)
s2_end['set_c_marble_match'] = {'scale': round(_S, 9), 'angle': round(_ang, 6), 'offset': [round(_O.x, 6), round(_O.y, 6), round(_O.z, 6)],
                                'freq': MARBLE_FREQ_REC, 'record_m_per_desert_m': round(_k, 10),
                                'note': 'drop-in for handoff key set_c_marble once Set C passes freq=freq to ND.build_marble_field'}
hp = os.path.join(ROOT, 'data', 'handoff.json')
try:
    with open(hp) as fh: H = json.load(fh)
except Exception:
    H = {}
H['S2_end'] = s2_end
sc.frame_set(F0); bpy.context.view_layer.update()
cmw0 = cam.matrix_world
H['S2_start'] = {
    'frame': F0, 'note': 'S2 first frame (world, set B metres). Camera rides 0.38 mm above the cantilever axis, 1 mm back from '
                         'the stylus tip, looking back along the tapered tube (4 deg below horizontal; vinyl horizon ~1/3 from the top). '
                         'The tube runs out of the frame bottom ~65% wide and converges toward the top edge like the S1 f120 spire, '
                         'painted with the three S1 streaks (magenta left flank, saffron/cream crest, ultramarine right flank; keyed '
                         'macro tint f121-125 fading out by f131). Nearly deep focus at the cut; the camera then rises + pulls back.',
    'cam_forward_world': [round(x, 5) for x in (cmw0.to_3x3() @ Vector((0, 0, -1))).normalized()],
    'cam_up_world': [round(x, 5) for x in (cmw0.to_3x3() @ Vector((0, 1, 0))).normalized()],
    'lens_mm': 28.0,
}
with open(hp + '.tmp', 'w') as fh: json.dump(H, fh, indent=1)
os.replace(hp + '.tmp', hp)
print('HANDOFF', json.dumps(s2_end))

# ------------------------------------------------------------------ save
sc.frame_set(F0)
out = os.path.join(ROOT, 'blend', 'set_b.blend')
bpy.ops.wm.save_as_mainfile(filepath=out, compress=True)
print('SAVED', out)
