import bpy
sc = bpy.context.scene
def tryn(tree, ids):
    for i in ids:
        try:
            n = tree.nodes.new(i); print('NODE_OK', i, '| in:', [s.name for s in n.inputs], '| out:', [s.name for s in n.outputs]); 
        except Exception as ex: print('NODE_BAD', i, ex)
cg = bpy.data.node_groups.new('C', 'CompositorNodeTree')
tryn(cg, ['ShaderNodeMix','CompositorNodeMixRGB','CompositorNodeEllipseMask','CompositorNodeBlur','ShaderNodeMapRange','ShaderNodeMath','CompositorNodeMath','CompositorNodeMapRange','CompositorNodeRGB','CompositorNodeGlare','CompositorNodeLensdist','CompositorNodeHueSat','CompositorNodeImageCoordinates','CompositorNodeImageInfo','ShaderNodeRGB','CompositorNodeRLayers','ShaderNodeSeparateXYZ','ShaderNodeVectorMath'])
gl = cg.nodes.new('CompositorNodeGlare')
try: print('GLARE_TYPES', [e.identifier for e in gl.inputs['Type'].bl_rna.properties['default_value'].enum_items])
except Exception as ex: print('GT', ex)
gg = bpy.data.node_groups.new('G', 'GeometryNodeTree')
tryn(gg, ['GeometryNodeIndexSwitch','ShaderNodeFloatCurve','GeometryNodeInputSceneTime','GeometryNodeInputNamedAttribute','GeometryNodeStoreNamedAttribute','GeometryNodeSetPosition','ShaderNodeVectorRotate','ShaderNodeTexNoise','GeometryNodeInstanceOnPoints','GeometryNodeMeshIcoSphere','GeometryNodeSetShadeSmooth','FunctionNodeRandomValue','GeometryNodeInputID','GeometryNodeObjectInfo','GeometryNodeCollectionInfo','GeometryNodeSwitch'])
isw = gg.nodes.new('GeometryNodeIndexSwitch')
print('ISW props', [p.identifier for p in isw.bl_rna.properties][-12:])
try:
    isw.data_type = 'FLOAT'; print('isw items', len(isw.index_switch_items)); isw.index_switch_items.new(); print('isw items2', len(isw.index_switch_items), [s.name for s in isw.inputs])
except Exception as ex: print('ISW err', ex)
e = sc.eevee
print('EEVEE', [p.identifier for p in e.bl_rna.properties if not p.identifier.startswith('bl_')])
r = sc.render
print('RENDER_MB', [p for p in ['motion_blur_shutter','motion_blur_position','use_motion_blur'] if hasattr(r,p)], [p.identifier for p in r.bl_rna.properties if 'motion' in p.identifier or 'filter' in p.identifier or 'compositor' in p.identifier])
m = bpy.data.materials.new('x'); print('MAT', [p.identifier for p in m.bl_rna.properties if 'render' in p.identifier or 'shadow' in p.identifier or 'blend' in p.identifier or 'thick' in p.identifier or 'displacement' in p.identifier])
w = bpy.data.worlds.new('w'); print('MIST', [p.identifier for p in w.mist_settings.bl_rna.properties])
bpy.ops.mesh.primitive_cube_add(); o = bpy.context.object
print('OBJVIS', [p.identifier for p in o.bl_rna.properties if p.identifier.startswith('visible') or 'hide' in p.identifier])
bpy.ops.object.light_add(type='SUN'); l = bpy.context.object.data
print('SUN', [p.identifier for p in l.bl_rna.properties if 'shadow' in p.identifier or 'angle' in p.identifier or 'resolution' in p.identifier])
print('VL', [p.identifier for p in sc.view_layers[0].bl_rna.properties if 'pass' in p.identifier][:40])
print('CAM', [p.identifier for p in bpy.data.cameras.new('c').bl_rna.properties if 'clip' in p.identifier or 'sensor' in p.identifier])
print('FONTS_OK')
