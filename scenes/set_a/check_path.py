"""Offline check of the S1 camera path (no Blender): spire + cantilever visibility per frame (groove surface AND
the lint bundle as occluders), wall clearance, speeds, angular rates.
Run: <blender python> -I scenes/set_a/check_path.py <project_root>"""
import sys, os, math
root = sys.argv[1]
sys.path.insert(0, os.path.join(root, 'scenes', 'set_a'))
import numpy as np
import design as D

data = D.load_data(root)
data['envf'] = D.env_low_fn(data)
cp = D.camera_path(data)
fwd, up = D.basis(cp['yaw'], cp['pitch'], cp['roll'])
right = np.cross(fwd, up)
f_lint = data['events'].get('lint_pass', 49)
x_l = float(cp['pos'][f_lint - 1, 0])
# spire + cantilever sample points
pts = []
for zz in np.linspace(-10, D.SPIRE_TOP, 12):
    for a in np.radians(np.arange(0, 360, 22.5)):
        r = D.ARRIS_R if zz > 5 else 16.0
        pts.append((D.X_SP + r * math.cos(a), D.Y_SP + r * math.sin(a), zz))
nsp = len(pts)
ax = np.array([D.T_DIR[0] * math.cos(D.TUBE_ANG), D.T_DIR[1] * math.cos(D.TUBE_ANG), math.sin(D.TUBE_ANG)])
p0 = np.array([D.X_SP + D.TUBE_S0 * D.T_DIR[0], D.Y_SP + D.TUBE_S0 * D.T_DIR[1],
               D.SPIRE_TOP + D.TUBE_R / math.cos(D.TUBE_ANG) - 2.5 + D.TUBE_S0 * math.tan(D.TUBE_ANG)])
for s in np.linspace(0, 400, 21):
    for a in np.radians(np.arange(0, 360, 45)):
        e1 = D.TB_DIR; e2 = np.cross(ax, e1)
        pts.append(tuple(p0 + ax * s + D.TUBE_R * (math.cos(a) * e1 + math.sin(a) * e2)))
pts = np.array(pts)
tanh = 1.0 * 1.03
tanv = 9 / 16 * 1.03


def lint_dist(q):
    # lint ~ tube along y at x=x_l; centre z: sag in groove 0, lying on lands elsewhere
    yy = q[:, 1]
    zc = np.maximum(np.maximum(D.surface_z(np.full_like(yy, x_l), yy) + 4.0, -3.5 + 0.0015 * yy ** 2), -30)
    return np.hypot(q[:, 0] - x_l, q[:, 2] - zc)


print('X_SP %.1f Y_SP %.1f PSI %.1f L %.1f TURN1 %.1f lint x %.1f' % (D.X_SP, D.Y_SP, D.PSI_DEG, D.L_PATH, D.TURN1, x_l))
prev = None; prevyaw = None
for i, f in enumerate(cp['frames']):
    p = cp['pos'][i]
    d = pts - p
    zc = d @ fwd[i]; xc = d @ right[i]; yc = d @ up[i]
    inframe = (zc > 1) & (np.abs(xc / np.maximum(zc, 1e-6)) < tanh) & (np.abs(yc / np.maximum(zc, 1e-6)) < tanv)
    vis_s = 0; vis_t = 0
    for j in np.where(inframe)[0]:
        q = p[None, :] + d[j][None, :] * np.linspace(0.02, 0.97, 200)[:, None]
        sz = D.surface_z(q[:, 0], q[:, 1])
        if np.all(q[:, 2] > sz + 0.05) and np.all(lint_dist(q) > 3.6):
            if j < nsp: vis_s += 1
            else: vis_t += 1
    sp = 0 if prev is None else np.linalg.norm(p - prev) * 24
    yr = 0 if prevyaw is None else cp['yaw'][i] - prevyaw
    prev = p; prevyaw = cp['yaw'][i]
    yy = p[1] - D.B(p[0]); g = round(yy / D.PITCH); yy -= g * D.PITCH
    hz = p[2] - D.Z_APEX
    clr = (hz - abs(yy)) / math.sqrt(2) if p[2] < 0 else p[2]
    ld = float(lint_dist(p[None, :])[0])
    if f % 3 == 1 or f in (44, 46, 47, 48, 49, 50, 56, 57, 58, 59, 60, 62, 63, 64, 96, 97, 115, 118, 119, 120):
        print('f%3d x%7.1f y%7.1f z%7.1f yaw%6.1f(%+4.1f) pit%6.1f rol%5.1f spd%6.1f clr%5.1f lint%6.1f spire%3d/%3d tube%3d' % (
            f, p[0], p[1], p[2], cp['yaw'][i], yr, cp['pitch'][i], cp['roll'][i], sp, clr, ld, vis_s, inframe[:nsp].sum(), vis_t))
