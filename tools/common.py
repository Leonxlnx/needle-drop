"""Shared helpers for every scene script (Blender 5.2.2, headless).

Import from a scene script with:
    import sys, os; sys.path.insert(0, os.path.join(ROOT, 'tools')); import common as C
"""
import bpy, os, json, math, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, 'assets')
UA = {'User-Agent': 'Mozilla/5.0 (blender-film-build)'}


# ---------------------------------------------------------------- scene / render

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    return bpy.context.scene


def setup_render(sc, res=(1920, 1080), samples=32, fps=24, motion_blur=True, raytrace=True):
    sc.render.engine = 'BLENDER_EEVEE'
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.fps = fps
    e = sc.eevee
    e.taa_render_samples = samples
    e.use_raytracing = raytrace
    e.use_shadows = True
    e.shadow_ray_count = 2
    e.shadow_step_count = 8
    e.use_fast_gi = True
    e.volumetric_tile_size = '8'
    e.volumetric_samples = 64
    e.use_volumetric_shadows = True
    sc.render.use_motion_blur = motion_blur
    sc.render.motion_blur_shutter = 0.5
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGB'
    sc.render.image_settings.color_depth = '8'
    sc.render.film_transparent = False
    color(sc)


def color(sc, look='AgX - Medium High Contrast', exposure=0.0, gamma=1.0):
    vs = sc.view_settings
    vs.view_transform = 'AgX'
    vs.look = look   # valid: 'None', 'AgX - Punchy', 'AgX - Medium High Contrast', 'AgX - High Contrast', 'AgX - Very High Contrast', ...
    vs.exposure = exposure
    vs.gamma = gamma


def compositor(sc, bloom=0.35, bloom_threshold=1.0, bloom_size=0.6, dispersion=0.004, saturation=1.08):
    """Bloom (Glare) + slight chromatic dispersion + saturation. 5.x compositor = node group."""
    ng = bpy.data.node_groups.new('Comp', 'CompositorNodeTree')
    sc.compositing_node_group = ng
    ng.interface.new_socket('Image', in_out='OUTPUT', socket_type='NodeSocketColor')
    N, L = ng.nodes, ng.links
    rl = N.new('CompositorNodeRLayers')
    last = rl.outputs['Image']
    if bloom > 0:
        gl = N.new('CompositorNodeGlare')
        gl.inputs['Type'].default_value = 'Bloom'
        gl.inputs['Threshold'].default_value = bloom_threshold
        gl.inputs['Strength'].default_value = bloom
        gl.inputs['Size'].default_value = bloom_size
        L.new(last, gl.inputs['Image']); last = gl.outputs['Image']
    if saturation != 1.0:
        hs = N.new('CompositorNodeHueSat')
        hs.inputs['Saturation'].default_value = saturation
        L.new(last, hs.inputs['Image']); last = hs.outputs['Image']
    if dispersion > 0:
        ld = N.new('CompositorNodeLensdist')
        ld.inputs['Dispersion'].default_value = dispersion
        L.new(last, ld.inputs['Image']); last = ld.outputs['Image']
    out = N.new('NodeGroupOutput')
    L.new(last, out.inputs[0])
    return ng


def render_still(sc, path, frame=None):
    if frame is not None:
        sc.frame_set(frame)
    sc.render.filepath = os.path.abspath(path)
    bpy.ops.render.render(write_still=True)


# ---------------------------------------------------------------- materials

def principled(name, base=(0.8, 0.8, 0.8), rough=0.5, metal=0.0, emission=None, emit_strength=0.0, alpha=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*base, 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    if emission is not None:
        b.inputs['Emission Color'].default_value = (*emission, 1)
        b.inputs['Emission Strength'].default_value = emit_strength
    if alpha < 1:
        b.inputs['Alpha'].default_value = alpha
    return m


def hex2lin(h):
    """'#RRGGBB' -> linear RGB tuple."""
    h = h.lstrip('#')
    def c(v):
        v = int(v, 16) / 255
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    return (c(h[0:2]), c(h[2:4]), c(h[4:6]))


# ---------------------------------------------------------------- Poly Haven (CC0)

def _get(url, dest):
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return dest
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=120) as r, open(dest + '.part', 'wb') as f:
        f.write(r.read())
    os.replace(dest + '.part', dest)
    return dest


def ph_files(slug):
    req = urllib.request.Request(f'https://api.polyhaven.com/files/{slug}', headers=UA)
    return json.loads(urllib.request.urlopen(req, timeout=60).read())


def ph_hdri(slug, res='4k'):
    """Download a Poly Haven HDRI (.exr) -> local path."""
    f = ph_files(slug)['hdri'][res]['exr']
    return _get(f['url'], os.path.join(ASSETS, 'polyhaven', 'hdri', f'{slug}_{res}.exr'))


def ph_texture(slug, res='2k', maps=('Diffuse', 'nor_gl', 'Rough', 'Displacement', 'AO')):
    """Download PBR maps (jpg/png) -> dict map->path."""
    f = ph_files(slug)
    out = {}
    for m in maps:
        if m not in f:
            continue
        entry = f[m][res]
        fmt = 'jpg' if 'jpg' in entry else ('png' if 'png' in entry else list(entry)[0])
        url = entry[fmt]['url']
        out[m] = _get(url, os.path.join(ASSETS, 'polyhaven', 'tex', slug, os.path.basename(url)))
    return out


def ph_model(slug, res='2k'):
    """Download a Poly Haven model as .blend (with its textures) -> path of the .blend."""
    f = ph_files(slug)
    entry = f['blend'][res]['blend']
    d = os.path.join(ASSETS, 'polyhaven', 'models', slug)
    blend = _get(entry['url'], os.path.join(d, os.path.basename(entry['url'])))
    for rel, inc in entry.get('include', {}).items():
        _get(inc['url'], os.path.join(d, rel))
    return blend


def append_objects(blend_path, collection_name=None, link_to=None):
    """Append all objects from a .blend; returns list of new objects (not linked to scene unless link_to)."""
    with bpy.data.libraries.load(blend_path, link=False) as (src, dst):
        dst.objects = list(src.objects)
    objs = [o for o in dst.objects if o is not None]
    if link_to is not None:
        for o in objs:
            link_to.objects.link(o)
    bpy.ops.file.make_paths_absolute() if False else None
    return objs


def world_hdri(sc, path, strength=1.0, rotation_z=0.0):
    w = bpy.data.worlds.new('World'); sc.world = w
    w.use_nodes = True
    nt = w.node_tree; N = nt.nodes
    bg = N['Background']
    env = N.new('ShaderNodeTexEnvironment'); env.image = bpy.data.images.load(path)
    mp = N.new('ShaderNodeMapping'); tc = N.new('ShaderNodeTexCoord')
    mp.inputs['Rotation'].default_value[2] = rotation_z
    nt.links.new(tc.outputs['Generated'], mp.inputs['Vector'])
    nt.links.new(mp.outputs['Vector'], env.inputs['Vector'])
    nt.links.new(env.outputs['Color'], bg.inputs['Color'])
    bg.inputs['Strength'].default_value = strength
    return w


def pbr_material(name, maps, scale=1.0, disp_scale=0.0, tint=None):
    """Material from ph_texture() maps; box-projected via object coords is left to caller (uses UV)."""
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; N, L = nt.nodes, nt.links
    b = N['Principled BSDF']
    tc = N.new('ShaderNodeTexCoord'); mp = N.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (scale, scale, scale)
    L.new(tc.outputs['UV'], mp.inputs['Vector'])

    def img(key, non_color=False):
        t = N.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(maps[key])
        if non_color:
            t.image.colorspace_settings.name = 'Non-Color'
        L.new(mp.outputs['Vector'], t.inputs['Vector'])
        return t
    if 'Diffuse' in maps:
        d = img('Diffuse')
        if tint:
            mix = N.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'
            mix.inputs['Factor'].default_value = 1.0
            L.new(d.outputs['Color'], mix.inputs['A']); mix.inputs['B'].default_value = (*tint, 1)
            L.new(mix.outputs['Result'], b.inputs['Base Color'])
        else:
            L.new(d.outputs['Color'], b.inputs['Base Color'])
    if 'Rough' in maps:
        L.new(img('Rough', True).outputs['Color'], b.inputs['Roughness'])
    if 'nor_gl' in maps:
        nm = N.new('ShaderNodeNormalMap')
        L.new(img('nor_gl', True).outputs['Color'], nm.inputs['Color'])
        L.new(nm.outputs['Normal'], b.inputs['Normal'])
    if disp_scale and 'Displacement' in maps:
        dn = N.new('ShaderNodeDisplacement'); dn.inputs['Scale'].default_value = disp_scale
        L.new(img('Displacement', True).outputs['Color'], dn.inputs['Height'])
        L.new(dn.outputs['Displacement'], N['Material Output'].inputs['Displacement'])
        m.displacement_method = 'BOTH'
    return m
