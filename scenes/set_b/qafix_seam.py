"""QA fix for the f280-288 centre seam (Set B, S2 close-up) + 16-bit output. Writes ONLY blend/set_b_fix.blend.

Cause: the vinyl 'coat cue' (M_Vinyl emission, keyed 0 at f279 -> 0.12 at f283) builds a camera-space gradient as
    ndc = X / max(-Z, 1e-4) / (18/28)
assuming the Vector Transform 'Camera' space looks down -Z. It does not: Blender's shader camera space has +Z forward
(EEVEE inverts z to match Cycles), so -Z < 0 for every visible point, the max() clamps to 1e-4, ndc = X * 1.56e4 and the
intended soft gradient collapses into a hard step at X = 0 = the exact frame centre: left half = full violet-chalk cue
(milky haze), right half = 0. Fixed on screen because it is camera space.
Fix (patched in memory on a copy of blend/set_b.blend, nothing else touched):
  * depth = |Z| (convention-proof)  -> MULTIPLY(-1) node switched to ABSOLUTE
  * gradient = smoothstep over the full frame width (ndc +1 -> -1): left edge = the approved left-half level (0.12),
    frame-mean added emission unchanged (0.5 * amp) so the f288 brightness/colour for the S3 match cut is kept, no seam.
  * image output colour depth 16-bit.
Then A/B test renders (orig vs fix) with in-session overrides only.
Usage: tools/brun.sh --threads 8 --render -- --python scenes/set_b/qafix_seam.py -- <pct> <spp> <frames,comma>
"""
import bpy, os, sys, time, json, struct, subprocess, math
import numpy as np

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
PCT = int(argv[0]) if argv else 33
SPP = int(argv[1]) if len(argv) > 1 else 16
FRAMES = [int(x) for x in (argv[2] if len(argv) > 2 else '279,280,282,288').split(',')]
ROOT = os.getcwd()
SRC = os.path.join(ROOT, 'blend', 'set_b.blend')
FIX = os.path.join(ROOT, 'blend', 'set_b_fix.blend')
OUT = os.path.join(ROOT, 'renders', 'tests', 'qafix')
os.makedirs(OUT, exist_ok=True)
assert os.path.basename(FIX) == 'set_b_fix.blend'
src_mtime = os.path.getmtime(SRC)


def P(*a):
    print('QAFIX', *a, flush=True)


def cue_chains():
    """coat_cue Value -> MULTIPLY(gmr, cue); gmr.Value <- DIVIDE(d1, 18/28); d1 = DIVIDE(X, mx); mx = MAXIMUM(neg, 1e-4);
    neg = MULTIPLY(Z, -1) (or ABSOLUTE(Z) once patched); Z/X from SeparateXYZ of VectorTransform(WORLD->CAMERA)."""
    out = []
    for mat in bpy.data.materials:
        nt = mat.node_tree
        if nt is None: continue
        for nd in nt.nodes:
            if nd.bl_idname != 'ShaderNodeValue' or nd.label != 'coat_cue': continue
            mul = nd.outputs[0].links[0].to_node
            gmr = mul.inputs[0].links[0].from_node
            d2 = gmr.inputs['Value'].links[0].from_node
            d1 = d2.inputs[0].links[0].from_node
            mx = d1.inputs[1].links[0].from_node
            neg = mx.inputs[0].links[0].from_node
            sep = neg.inputs[0].links[0].from_node
            vt = sep.inputs[0].links[0].from_node
            ok = (mul.bl_idname == 'ShaderNodeMath' and mul.operation == 'MULTIPLY' and gmr.bl_idname == 'ShaderNodeMapRange'
                  and d2.operation == 'DIVIDE' and abs(d2.inputs[1].default_value - 18.0 / 28.0) < 1e-5
                  and d1.operation == 'DIVIDE' and d1.inputs[0].links[0].from_socket.name == 'X'
                  and mx.operation == 'MAXIMUM' and neg.inputs[0].links[0].from_socket.name == 'Z'
                  and sep.bl_idname == 'ShaderNodeSeparateXYZ' and vt.bl_idname == 'ShaderNodeVectorTransform'
                  and vt.convert_to == 'CAMERA')
            out.append(dict(mat=mat, cue=nd, gmr=gmr, neg=neg, ok=ok))
    return out


def describe(tag):
    sc = bpy.context.scene
    ch = cue_chains()
    for c in ch:
        P(tag, 'chain', c['mat'].name, 'ok', c['ok'], 'depth_op', c['neg'].operation, 'neg_b', round(c['neg'].inputs[1].default_value, 4),
          'from', round(c['gmr'].inputs['From Min'].default_value, 3), round(c['gmr'].inputs['From Max'].default_value, 3))
    P(tag, 'image', sc.render.image_settings.file_format, sc.render.image_settings.color_mode, sc.render.image_settings.color_depth,
      'res', sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage, 'range', sc.frame_start, sc.frame_end,
      'mb', sc.render.use_motion_blur)
    f0 = sc.frame_current
    rows = []
    for f in range(276, 289):
        sc.frame_set(f)
        rows.append((f, round(ch[0]['cue'].outputs[0].default_value, 5) if ch else None, sc.eevee.taa_render_samples,
                     round(sc.view_settings.exposure, 4), round(sc.camera.data.lens, 3), round(sc.render.motion_blur_shutter, 3)))
    sc.frame_set(f0)
    for r in rows: P(tag, 'frame', *r, '(f, cue, spp, expo, lens, shutter)')
    return ch


def drop_sample_keys(sc):   # same as tools/render_frames.py (session only, never saved)
    ad = sc.animation_data
    if ad is None or ad.action is None: return
    try:
        fcs = ad.action.fcurves
    except Exception:
        from bpy_extras import anim_utils
        fcs = anim_utils.action_get_channelbag_for_slot(ad.action, ad.action_slot).fcurves
    for fc in [fc for fc in fcs if 'taa_render_samples' in fc.data_path]:
        fcs.remove(fc)


def load_png(p):
    with open(p, 'rb') as fh: hdr = fh.read(33)
    w, h = struct.unpack('>II', hdr[16:24]); bd = hdr[24]
    r = subprocess.run(['ffmpeg', '-v', 'error', '-i', p, '-f', 'rawvideo', '-pix_fmt', 'rgb48le', '-'], capture_output=True)
    a = np.frombuffer(r.stdout, '<u2').reshape(h, w, 3).astype(np.float64) / 257.0   # 8-bit scale
    return a, bd


def metrics(a):
    L = a @ np.array([0.2126, 0.7152, 0.0722])
    col = L.mean(0); W = len(col); c = W // 2
    st = lambda i: col[i - 3:i - 1].mean() - col[i + 1:i + 3].mean()
    steps = np.array([st(i) for i in range(3, W - 3)])
    step = st(c)
    mad = float(np.median(np.abs(steps - np.median(steps))))
    rows = (L[:, c - 2] - L[:, c + 1])
    return dict(seam_step=round(float(step), 3), seam_z=round(float(abs(step - np.median(steps)) / max(mad, 1e-6)), 1),
                baseline_mad=round(mad, 3), rows_left_brighter=round(float((rows > 0).mean()), 3),
                mean_rgb=[round(float(x), 3) for x in a.reshape(-1, 3).mean(0)], mean_luma=round(float(L.mean()), 3),
                left_luma=round(float(L[:, :c].mean()), 3), right_luma=round(float(L[:, c:].mean()), 3))


def psnr(a, b):
    mse = float(((a - b) ** 2).mean())
    return 99.0 if mse <= 1e-12 else round(10 * math.log10(255.0 ** 2 / mse), 2)


def render(tag, frames, cue_off=False):
    sc = bpy.context.scene
    drop_sample_keys(sc)
    sc.render.resolution_percentage = PCT
    if cue_off:
        for c in cue_chains():
            nt = c['mat'].node_tree
            if nt.animation_data and nt.animation_data.action:
                try:
                    fcs = nt.animation_data.action.fcurves
                except Exception:
                    from bpy_extras import anim_utils
                    fcs = anim_utils.action_get_channelbag_for_slot(nt.animation_data.action, nt.animation_data.action_slot).fcurves
                for fc in [fc for fc in fcs if c['cue'].name in fc.data_path]: fcs.remove(fc)
            c['cue'].outputs[0].default_value = 0.0
    res = {}
    for f in frames:
        p = os.path.join(OUT, f'{tag}_{f:04d}.png')
        sc.frame_set(f); sc.eevee.taa_render_samples = SPP; sc.render.filepath = p
        t = time.time(); bpy.ops.render.render(write_still=True)
        a, bd = load_png(p); m = metrics(a); res[f] = a
        P('FRAME', tag, f, 'sec', round(time.time() - t, 1), 'bitdepth', bd, json.dumps(m))
    return res


# ---- 1. original: inspect, patch in memory, save the copy (before any test override touches the session)
bpy.ops.wm.open_mainfile(filepath=SRC, load_ui=False)
ch = describe('ORIG')
assert ch and all(c['ok'] for c in ch), 'coat-cue node chain not as expected'
f_keep = bpy.context.scene.frame_current
for c in ch:
    c['neg'].operation = 'ABSOLUTE'          # depth = |Z| whatever the camera-space z convention
    c['neg'].label = 'qafix_abs_depth'
    c['gmr'].inputs['From Min'].default_value = 1.0    # right frame edge -> 0
    c['gmr'].inputs['From Max'].default_value = -1.0   # left frame edge -> 1 (= old left-half level); mean = 0.5*amp (unchanged)
for s in bpy.data.scenes:
    s.render.image_settings.color_depth = '16'
bpy.context.scene.frame_set(f_keep)
bpy.ops.wm.save_as_mainfile(filepath=FIX, compress=True, copy=True)
P('SAVED', FIX, 'src_untouched', os.path.getmtime(SRC) == src_mtime)

# ---- 2. original renders (session overrides only, never saved)
bpy.ops.wm.open_mainfile(filepath=SRC, load_ui=False)
A = render('orig', FRAMES)

# ---- 3. fix blend: re-open from disk, verify, render
bpy.ops.wm.open_mainfile(filepath=FIX, load_ui=False)
chf = describe('FIX')
B = render('fix', FRAMES)
for f in FRAMES:
    P('COMPARE', f, 'psnr_orig_vs_fix_dB', psnr(A[f], B[f]),
      'max_abs_diff', round(float(np.abs(A[f] - B[f]).max()), 2), 'mean_abs_diff', round(float(np.abs(A[f] - B[f]).mean()), 4))
last = max(FRAMES)
if metrics(B[last])['seam_z'] > 8:     # fix did not remove it: is the cue the cause at all?
    bpy.ops.wm.open_mainfile(filepath=SRC, load_ui=False)
    D = render('diag_cueoff', [last], cue_off=True)
    P('DIAG cue_off psnr vs orig', psnr(A[last], D[last]))
P('SRC_UNTOUCHED', os.path.getmtime(SRC) == src_mtime)
P('DONE')
