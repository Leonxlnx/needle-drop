"""Probe blend/tonearm_asset.blend: list TonearmAsset objects (name, type, parent, loc, dims, mats, custom props)."""
import bpy, os
p = os.path.join(os.getcwd(), 'blend', 'tonearm_asset.blend')
with bpy.data.libraries.load(p, link=False) as (src, dst):
    print('COLLS', list(src.collections)); print('OBJS', len(src.objects))
    dst.collections = [c for c in src.collections if c == 'TonearmAsset']
ta = dst.collections[0]
print('CHILD COLLS', [c.name for c in ta.children])
for o in sorted(ta.all_objects, key=lambda o: o.name):
    mats = [s.material.name for s in o.material_slots if s.material] if hasattr(o, 'material_slots') else []
    mods = [m.type for m in o.modifiers]
    nv = len(o.data.vertices) if o.type == 'MESH' else (o.type)
    print('OBJ', o.name, o.type, 'par=', o.parent.name if o.parent else None, 'loc=', tuple(round(v, 4) for v in o.location),
          'rot=', tuple(round(v, 3) for v in o.rotation_euler), 'scl=', tuple(round(v, 3) for v in o.scale),
          'dim=', tuple(round(v, 4) for v in o.dimensions), 'nv=', nv, 'mats=', mats, 'mods=', mods,
          'props=', {k: (list(o[k]) if hasattr(o[k], '__len__') and not isinstance(o[k], str) else o[k]) for k in o.keys()})
print('PROBE_DONE')
