import bpy, sys, os
ROOT=os.getcwd(); sys.path.insert(0, os.path.join(ROOT,'tools')); import common as C
sc = C.reset()
cam = bpy.data.cameras.new('c'); cam.dof.aperture_fstop = 900; print('FSTOP', cam.dof.aperture_fstop)
print('DOFPROPS', [p.identifier for p in cam.dof.bl_rna.properties])
e = sc.eevee
print('EEVEE', [p.identifier for p in e.bl_rna.properties])
try: print('RTO', [p.identifier for p in e.ray_tracing_options.bl_rna.properties])
except Exception as ex: print('rto err', ex)
ng = bpy.data.node_groups.new('Comp', 'CompositorNodeTree')
for t in ['CompositorNodeGlare','CompositorNodeEllipseMask','CompositorNodeBlur','CompositorNodeMixRGB','ShaderNodeMix','CompositorNodeLensdist','CompositorNodeHueSat','CompositorNodeMath','ShaderNodeMath','CompositorNodeImageCoordinates','CompositorNodeVignette','CompositorNodeDefocus','CompositorNodeCurveRGB','CompositorNodeColorBalance','CompositorNodeBrightContrast','CompositorNodeExposure']:
    try:
        n = ng.nodes.new(t); print('NODE', t, [i.name for i in n.inputs], '->', [o.name for o in n.outputs])
        if t=='CompositorNodeGlare':
            for i in n.inputs:
                if i.name in ('Type','Quality'):
                    try: print('  ENUM', i.name, [x.identifier for x in i.bl_rna.properties['default_value'].enum_items])
                    except Exception as ex: print('  enum err', ex)
        if t=='CompositorNodeEllipseMask' or t=='CompositorNodeBlur':
            print('  PROPS', [p.identifier for p in n.bl_rna.properties if p.identifier not in ('rna_type',)][-12:])
    except Exception as ex: print('NODE_BAD', t, ex)
l = bpy.data.lights.new('a','AREA'); print('LIGHT', [p.identifier for p in l.bl_rna.properties][-40:])
ob = bpy.data.objects.new('o', bpy.data.meshes.new('m')); print('VIS', [p for p in ['visible_camera','visible_shadow','visible_diffuse','visible_glossy','visible_transmission','visible_volume_scatter'] if hasattr(ob,p)])
cu = bpy.data.curves.new('t','FONT'); print('FONT', [p for p in ['follow_curve','space_character','offset_x','align_x','size','extrude','bevel_depth'] if hasattr(cu,p)])
m = bpy.data.materials.new('x'); m.use_nodes=True; b=m.node_tree.nodes['Principled BSDF']; print('PBSDF', [i.name for i in b.inputs])
print('MATPROPS', [p.identifier for p in m.bl_rna.properties if 'eevee' in p.identifier or 'thick' in p.identifier or 'blend' in p.identifier or 'surface' in p.identifier or 'ray' in p.identifier])
bpy.ops.object.lightprobe_add(type='SPHERE'); lp=bpy.context.object; print('PROBE', lp.data.type, [p.identifier for p in lp.data.bl_rna.properties][-30:])
print('BAKEOPS', [o for o in dir(bpy.ops.object) if 'probe' in o or 'bake' in o])
md = ob.modifiers.new('b','BEVEL'); print('BEVEL', [p.identifier for p in md.bl_rna.properties][-30:])
print('WORLDPROPS', [p.identifier for p in bpy.data.worlds.new('w').bl_rna.properties][-20:])
print('TANGENT', [o for o in ['RADIAL','UV_MAP'] ])
tn = m.node_tree.nodes.new('ShaderNodeTangent'); print('TANG', tn.direction_type, tn.axis)
print('VIEWLOOKS', [l.name for l in bpy.types.ColorManagedViewSettings.bl_rna.properties['look'].enum_items] if False else '')
print('PROBE_DONE')
