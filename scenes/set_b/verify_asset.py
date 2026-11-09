"""Check blend/tonearm_asset.blend appends cleanly (collection TonearmAsset)."""
import bpy, os
from mathutils import Vector
p = os.path.join(os.getcwd(), 'blend', 'tonearm_asset.blend')
bpy.ops.wm.read_factory_settings(use_empty=True)
with bpy.data.libraries.load(p, link=False) as (src, dst):
    print('ASSET_COLLECTIONS', list(src.collections)); dst.collections = ['TonearmAsset']
col = dst.collections[0]; bpy.context.scene.collection.children.link(col)
bpy.context.view_layer.update()
mn = Vector((1e9,) * 3); mx = Vector((-1e9,) * 3)
for o in col.objects:
    for c in o.bound_box:
        w = o.matrix_world @ Vector(c); mn = Vector(map(min, mn, w)); mx = Vector(map(max, mx, w))
mats = sorted({m.name for o in col.objects if o.data is not None and hasattr(o.data, 'materials') for m in o.data.materials if m})
piv = bpy.data.objects.get('ArmPivot')
print('ASSET_OBJECTS', len(col.objects), 'bbox_min', tuple(round(v, 4) for v in mn), 'bbox_max', tuple(round(v, 4) for v in mx))
print('ASSET_MATERIALS', mats)
print('ASSET_PIVOT', tuple(piv.location), dict(piv.items()) if piv else None)
