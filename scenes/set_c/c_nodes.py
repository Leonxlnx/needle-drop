"""Tiny node-building helper usable in shader, geometry and compositor trees."""
import bpy


class NB:
    def __init__(self, nt, kind='SHADER'):
        self.nt, self.N, self.L, self.kind = nt, nt.nodes, nt.links, kind

    def _in(self, sock, v):
        if v is None:
            return
        if isinstance(v, bpy.types.NodeSocket):
            self.L.new(v, sock)
        else:
            sock.default_value = v

    def node(self, typ, **props):
        n = self.N.new(typ)
        for k, v in props.items():
            setattr(n, k, v)
        return n

    def math(self, op, a, b=None, c=None, clamp=False):
        n = self.N.new('ShaderNodeMath'); n.operation = op; n.use_clamp = clamp
        self._in(n.inputs[0], a)
        if b is not None: self._in(n.inputs[1], b)
        if c is not None: self._in(n.inputs[2], c)
        return n.outputs[0]

    # sugar
    def add(self, a, b): return self.math('ADD', a, b)
    def sub(self, a, b): return self.math('SUBTRACT', a, b)
    def mul(self, a, b): return self.math('MULTIPLY', a, b)
    def div(self, a, b): return self.math('DIVIDE', a, b)
    def clamp01(self, a): return self.math('ADD', a, 0.0, clamp=True)

    def madd(self, a, b, c):
        return self.math('MULTIPLY_ADD', a, b, c)

    def vmath(self, op, a, b=None, scale=None):
        n = self.N.new('ShaderNodeVectorMath'); n.operation = op
        self._in(n.inputs[0], a)
        if b is not None: self._in(n.inputs[1], b)
        if scale is not None: self._in(n.inputs['Scale'], scale)
        out = n.outputs['Value'] if op in ('LENGTH', 'DOT_PRODUCT', 'DISTANCE') else n.outputs['Vector']
        return out

    def sep(self, v):
        n = self.N.new('ShaderNodeSeparateXYZ'); self._in(n.inputs[0], v)
        return n.outputs['X'], n.outputs['Y'], n.outputs['Z']

    def comb(self, x, y, z):
        n = self.N.new('ShaderNodeCombineXYZ')
        self._in(n.inputs['X'], x); self._in(n.inputs['Y'], y); self._in(n.inputs['Z'], z)
        return n.outputs[0]

    def ss(self, e0, e1, x):
        """smoothstep(e0, e1, x) (works for e0 > e1 too)."""
        n = self.N.new('ShaderNodeMapRange'); n.interpolation_type = 'SMOOTHSTEP'; n.clamp = True
        self._in(n.inputs['Value'], x)
        if e0 <= e1:
            n.inputs['From Min'].default_value = e0; n.inputs['From Max'].default_value = e1
            n.inputs['To Min'].default_value = 0.0; n.inputs['To Max'].default_value = 1.0
        else:
            n.inputs['From Min'].default_value = e1; n.inputs['From Max'].default_value = e0
            n.inputs['To Min'].default_value = 1.0; n.inputs['To Max'].default_value = 0.0
        return n.outputs['Result']

    def maprange(self, x, a, b, c, d, clamp=True):
        n = self.N.new('ShaderNodeMapRange'); n.clamp = clamp
        self._in(n.inputs['Value'], x)
        for k, v in zip(('From Min', 'From Max', 'To Min', 'To Max'), (a, b, c, d)):
            self._in(n.inputs[k], v)
        return n.outputs['Result']

    def mixc(self, fac, a, b, blend='MIX'):
        n = self.N.new('ShaderNodeMix'); n.data_type = 'RGBA'; n.blend_type = blend
        n.clamp_factor = True
        self._in(n.inputs['Factor'], fac)
        ia = [s for s in n.inputs if s.identifier == 'A_Color'][0]
        ib = [s for s in n.inputs if s.identifier == 'B_Color'][0]
        self._in(ia, a if not isinstance(a, tuple) or len(a) == 4 else (*a, 1.0))
        self._in(ib, b if not isinstance(b, tuple) or len(b) == 4 else (*b, 1.0))
        return [s for s in n.outputs if s.identifier == 'Result_Color'][0]

    def mixf(self, fac, a, b):
        n = self.N.new('ShaderNodeMix'); n.data_type = 'FLOAT'; n.clamp_factor = False
        self._in(n.inputs['Factor'], fac)
        ia = [s for s in n.inputs if s.identifier == 'A_Float'][0]
        ib = [s for s in n.inputs if s.identifier == 'B_Float'][0]
        self._in(ia, a); self._in(ib, b)
        return [s for s in n.outputs if s.identifier == 'Result_Float'][0]

    def attr(self, name, typ='FLOAT', inst=False):
        if self.kind == 'GEO':
            n = self.N.new('GeometryNodeInputNamedAttribute'); n.data_type = typ
            n.inputs['Name'].default_value = name
            return n.outputs['Attribute']
        n = self.N.new('ShaderNodeAttribute'); n.attribute_name = name
        n.attribute_type = 'INSTANCER' if inst else 'GEOMETRY'
        if typ == 'FLOAT':
            return n.outputs['Fac'] if 'Fac' in n.outputs else n.outputs['Factor']
        return n.outputs['Vector']

    def value(self, v, label=None):
        n = self.N.new('ShaderNodeValue'); n.outputs[0].default_value = v
        if label:
            n.name = label; n.label = label
        return n.outputs[0]

    def rgb(self, col):
        return tuple(col) + (1.0,) if len(col) == 3 else tuple(col)

    def noise(self, vec, scale, detail=2.0, rough=0.5, dims='3D', out='Fac'):
        n = self.N.new('ShaderNodeTexNoise'); n.noise_dimensions = dims
        self._in(n.inputs['Vector'], vec)
        self._in(n.inputs['Scale'], scale)
        n.inputs['Detail'].default_value = detail; n.inputs['Roughness'].default_value = rough
        key = out
        if out == 'Fac':
            key = 'Fac' if 'Fac' in n.outputs else 'Factor'
        return n.outputs[key]

    def ramp(self, fac, stops, interp='LINEAR'):
        n = self.N.new('ShaderNodeValToRGB'); cr = n.color_ramp; cr.interpolation = interp
        while len(cr.elements) > 1:
            cr.elements.remove(cr.elements[-1])
        cr.elements[0].position = stops[0][0]; cr.elements[0].color = self.rgb(stops[0][1])
        for p, c in stops[1:]:
            e = cr.elements.new(p); e.color = self.rgb(c)
        self._in(n.inputs['Fac'], fac)
        return n.outputs['Color']
