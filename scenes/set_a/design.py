"""SET A design math (pure numpy, no bpy): groove field, meander, notches, camera path, spire placement.
Used by build.py inside Blender and by check_path.py outside (bundled python -I).
Units metres. Lands top z=0. Groove floor z=-30. Grooves run along +X, groove g centred at y = 100 g + B(x).

Round-1 refine (AD r1): the S1 path is a classic trench run. The camera flies centred in the upper third of a
near-straight V (z ~ -5, pitch ~ -3 deg) so the walls converge to a hazy vanishing point at frame centre; dips under
the lint at f49; then climbs out of the groove and banks LEFT across the lands toward the spire, which stands in
groove +2 out of the 90-degree frame (bearing > 53 deg) until the bank swings it in around f58-63.
The vault / cantilever live in a local frame aligned with the final approach heading PSI.

Round-2 refine (AD r2): establish ABOVE the lands (z +15, pitch -10) at 28-70 m/s (~100 m by f45), dive into groove 0,
pass under the lint at f49, climb out by f58 while one long even yaw turn (<=2.7 deg/frame, roll <=3 deg) brings the spire
(groove +4, x 300) in from the left ~420 m away at f60-63; cruise ~260 m/s over the lands aiming at the spire's upper half;
vault up the tapered facet face at ~10 m standoff (pitch 30-46), then the key frame rotates 32 deg from the approach axis
to the cantilever axis (TUBE_PSI) over f100-117 so the camera crests the crown and rides the tube (f115-120 unchanged
relative to the tube).
"""
import os, json, math
import numpy as np

FPS = 24
F0, F1 = 1, 120
DEPTH = 30.0
HALF_TOP = 30.0
ARC_R = 2.0
BEVEL_R = 0.6
PITCH = 100.0
Z_APEX = -DEPTH - ARC_R * (math.sqrt(2) - 1)   # virtual apex of the 45 deg walls


def t_of(f):
    return (np.asarray(f, float) - 1.0) / FPS


# ------------------------------------------------------------------ data

def load_data(root):
    d = {'kicks': [], 'events': {}, 'bands': None}
    try:
        b = json.load(open(os.path.join(root, 'data', 'beats.json')))
        d['kicks'] = [(float(k['t']), float(k.get('strength', 1.0))) for k in b.get('kicks', [])]
    except Exception as ex:
        print('SETA beats.json missing/bad:', ex)
    try:
        tm = json.load(open(os.path.join(root, 'data', 'timing.json')))
        d['events'] = {k: v['frame'] for k, v in tm['events'].items()}
    except Exception as ex:
        print('SETA timing.json missing/bad:', ex)
    try:
        d['bands'] = json.load(open(os.path.join(root, 'data', 'bands.json')))
    except Exception:
        d['bands'] = None
    return d


def env_low_fn(data):
    """Low-band envelope e(t) in 0..1. From bands.json if present, else synthesised from kicks."""
    bd = data.get('bands')
    if bd:
        try:
            fps = float(bd.get('fps', 24))
            for key in ('low', 'bass', 'sub', 'lows'):
                if key in bd:
                    arr = np.asarray(bd[key], float)
                    break
            else:
                arr = np.asarray(bd['bands']['low'], float)
            arr = (arr - arr.min()) / max(1e-6, arr.max() - arr.min())
            tt = np.arange(len(arr)) / fps
            k = max(1, int(fps * 0.25)); ker = np.ones(k) / k
            arr = np.convolve(arr, ker, mode='same')
            return lambda t: np.interp(t, tt, arr)
        except Exception as ex:
            print('SETA bands.json unusable, falling back:', ex)
    kicks = data.get('kicks') or [(i * 0.5, 1.0) for i in range(60)]
    kt = np.array([k[0] for k in kicks]); ks = np.array([k[1] for k in kicks])

    def e(t):
        t = np.asarray(t, float)[..., None]
        dt = t - kt
        v = np.where(dt >= 0, ks * np.exp(-dt / 0.35), ks * np.exp(dt / 0.08))
        return np.clip(v.sum(-1) / 1.6, 0, 1)
    return e


# ------------------------------------------------------------------ smooth helpers

def smoothstep(a, b, x):
    u = np.clip((np.asarray(x, float) - a) / (b - a), 0, 1)
    return u * u * (3 - 2 * u)


def smootherstep(a, b, x):
    u = np.clip((np.asarray(x, float) - a) / (b - a), 0, 1)
    return u * u * u * (u * (u * 6 - 15) + 10)


def pchip(xk, yk, x):
    """Monotone cubic (Fritsch-Carlson) interpolation, clamped outside."""
    xk = np.asarray(xk, float); yk = np.asarray(yk, float); x = np.asarray(x, float)
    h = np.diff(xk); d = np.diff(yk) / h
    m = np.zeros_like(yk)
    for i in range(1, len(xk) - 1):
        if d[i - 1] * d[i] > 0:
            w1 = 2 * h[i] + h[i - 1]; w2 = h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])
    m[0] = d[0]; m[-1] = d[-1]
    xc = np.clip(x, xk[0], xk[-1])
    i = np.clip(np.searchsorted(xk, xc) - 1, 0, len(h) - 1)
    u = (xc - xk[i]) / h[i]
    h00 = 2 * u ** 3 - 3 * u ** 2 + 1; h10 = u ** 3 - 2 * u ** 2 + u
    h01 = -2 * u ** 3 + 3 * u ** 2; h11 = u ** 3 - u ** 2
    return h00 * yk[i] + h10 * h[i] * m[i] + h01 * yk[i + 1] + h11 * h[i] * m[i + 1]


# ------------------------------------------------------------------ meander (shared by all grooves)
# Near-straight groove field: a very long, very gentle sine (record grooves at this scale are almost straight),
# so the trench vanishing point sits at frame centre and the far canyon melts into the haze.

def B(x):
    x = np.asarray(x, float)
    return 6.0 * (np.sin(2 * np.pi * x / 1500.0 + 0.4) - math.sin(0.4))


def Bslope(x):
    x = np.asarray(x, float)
    return 6.0 * 2 * np.pi / 1500.0 * np.cos(2 * np.pi * x / 1500.0 + 0.4)


def groove_center(g, x, envf=None, with_music=True):
    y = PITCH * g + B(x)
    if with_music and envf is not None:
        # adjacent grooves carry the music one revolution (1.8 s) earlier/later
        tx = t_of_x(x)
        y = y + 1.6 * (envf(tx + 1.8 * g) - 0.5) * smoothstep(-10, 30, x)
    return y


# ------------------------------------------------------------------ trench speed (phase A, f1-49)
V_T = [0.0, 0.6, 1.2, 1.7, 2.0, 2.4]
V_V = [28., 32., 40., 52., 62., 70.]   # r2: ~100 m by f45, real parallax


def x_trench(t):
    ts = np.linspace(0, 2.4, 2401)
    v = pchip(V_T, V_V, ts)
    xs = np.concatenate([[0], np.cumsum(0.5 * (v[1:] + v[:-1]) * (ts[1] - ts[0]))])
    return np.interp(t, ts, xs)


_TS = np.linspace(-2, 2.4, 4401)
_XS = None


def t_of_x(x):
    global _XS
    if _XS is None:
        _XS = np.where(_TS < 0, _TS * 15.0, x_trench(np.clip(_TS, 0, 2.4)))
    return np.interp(x, _XS, _TS, left=-2, right=2.4)


# ------------------------------------------------------------------ path geometry (XY), spire placement

SPIRE_G = 4                     # r2: spire stands in groove +4, ~450 m from the trench exit (revealed far ahead)
X_SP = 300.0                    # bearing from the f1 camera ~53 deg: outside the 90-deg frame while above the lands
SHANK_R = 35.0                  # octagon apothem at the girdle
ARRIS_R = SHANK_R / math.cos(math.radians(22.5))
STANDOFF = 22.0                 # bible: face 22 m ahead of the camera at 4.0 s
SPIRE_TOP = 110.0               # 140 m above the groove floor
TUBE_R = 18.0
TUBE_ANG = math.radians(20.0)
TUBE_LEN = 700.0
TUBE_S0 = 2.0                   # front end of the tube, tube-local s (r2: sits on the back half of the crown table)
T_SPLIT = 2.15                  # end of the straight trench run (s), the climb-out curve starts here
Y_SP = float(PITCH * SPIRE_G + B(X_SP))
_s0 = float(x_trench(T_SPLIT))
PSI_DEG = float(np.degrees(np.arctan2(Y_SP - B(_s0), X_SP - _s0))) + 6.0   # final approach heading (deg, 0=+X, CCW)
A_DIR = np.array([math.cos(math.radians(PSI_DEG)), math.sin(math.radians(PSI_DEG)), 0.0])
B_DIR = np.array([-A_DIR[1], A_DIR[0], 0.0])          # left of the approach axis
# r2: the cantilever heads 40 deg LEFT of the approach so it is seen in profile during the approach (needle silhouette)
TUBE_DT = 32.0
TURN_F0, TURN_F1 = 100.0, 117.0
TUBE_PSI = PSI_DEG + TUBE_DT
T_DIR = np.array([math.cos(math.radians(TUBE_PSI)), math.sin(math.radians(TUBE_PSI)), 0.0])
TB_DIR = np.array([-T_DIR[1], T_DIR[0], 0.0])


def _build_path():
    s0 = float(x_trench(T_SPLIT))
    xs0 = np.arange(-40.0, s0 + 1e-9, 0.25)
    pts = [np.stack([xs0, B(xs0)], -1)]
    P0 = np.array([s0, float(B(s0))]); T0 = np.array([1.0, float(Bslope(s0))]); T0 /= np.linalg.norm(T0)
    V = np.array([X_SP, Y_SP]) - (STANDOFF + ARRIS_R) * A_DIR[:2]
    ch = np.linalg.norm(V - P0)
    k0, k1 = 1.05 * ch, 0.95 * ch
    u = np.linspace(0, 1, 4001)[1:, None]
    h00 = 2 * u ** 3 - 3 * u ** 2 + 1; h10 = u ** 3 - 2 * u ** 2 + u; h01 = -2 * u ** 3 + 3 * u ** 2; h11 = u ** 3 - u ** 2
    pts.append(h00 * P0 + h10 * k0 * T0 + h01 * V + h11 * k1 * A_DIR[:2])
    # straight extension past V along PSI (motion-blur look-ahead only)
    ext = np.arange(1.0, 120.0, 1.0)[:, None]
    pts.append(V + ext * A_DIR[:2])
    P = np.concatenate(pts, 0)
    sl = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]) + xs0[0]
    sV = float(np.interp(0, [0], [0]))
    iv = len(xs0) + 4000 - 1
    return sl, P[:, 0], P[:, 1], float(sl[iv]), s0


_PS, _PX, _PY, L_PATH, S_SPLIT = _build_path()
# phase B speed (relative profile, scaled so the camera reaches the vault point exactly at f97)
VB_T = [T_SPLIT, 2.35, 2.55, 2.85, 3.2, 3.5, 3.8, 4.0]
VB_V = [72., 170., 235., 240., 232., 212., 185., 165.]
_TB = np.linspace(T_SPLIT, 4.0, 2001)
_vb = pchip(VB_T, VB_V, _TB)
_SB = np.concatenate([[0], np.cumsum(0.5 * (_vb[1:] + _vb[:-1]) * (_TB[1] - _TB[0]))])
# keep the entry speed, scale the rest so that s(4.0) == L_PATH
_need = L_PATH - S_SPLIT
_SB = _SB * (_need / _SB[-1])
TURN1 = 0.0


def s_of_t(t):
    t = np.asarray(t, float)
    sA = x_trench(np.clip(t, 0, T_SPLIT))
    sB = S_SPLIT + np.interp(t, _TB, _SB)
    return np.where(t <= T_SPLIT, sA, sB)


def path_xy(s):
    return np.interp(s, _PS, _PX), np.interp(s, _PS, _PY)


def path_heading(s):
    s = np.asarray(s, float)
    x1, y1 = path_xy(s - 1.0); x2, y2 = path_xy(s + 1.0)
    return np.degrees(np.arctan2(y2 - y1, x2 - x1))


def tube_to_world(sl, l, z):
    """Cantilever-local (s along the tube heading, l to its left, z) -> world."""
    sl = np.asarray(sl, float); l = np.asarray(l, float)
    return X_SP + sl * T_DIR[0] + l * TB_DIR[0], Y_SP + sl * T_DIR[1] + l * TB_DIR[1], np.asarray(z, float) + 0 * sl


def local_to_world(sl, l, z):
    """Spire-local (s along approach axis, l to the left, z) -> world."""
    sl = np.asarray(sl, float); l = np.asarray(l, float)
    x = X_SP + sl * A_DIR[0] + l * B_DIR[0]
    y = Y_SP + sl * A_DIR[1] + l * B_DIR[1]
    return x, y, np.asarray(z, float) + 0 * x


# ------------------------------------------------------------------ notches (per groove)

def notch_list(kicks, cam_pos_fn):
    """Chatter notches: for each kick t<=4.0 put a notch in the groove nearest the camera's ground point,
    at the camera's x. Returns list of (groove g, x_k, strength)."""
    out = []
    for (tk, s) in kicks:
        if tk < 0.0 or tk > 4.0:
            continue
        p = cam_pos_fn(tk)
        g = int(np.round((p[1] - B(p[0])) / PITCH))
        out.append((g, float(p[0]), float(s)))
    return out


def notch_offsets(notches, g, x):
    """Outward wall offset of groove g along x: the wall tapers OUT over 16 m before x_k then steps back IN over
    1 m at x_k, so the step face looks back at the camera and catches the raking sun as a bright line."""
    x = np.asarray(x, float)
    out = np.zeros_like(x)
    for (gg, xk, s) in notches:
        if gg != g:
            continue
        d = x - xk
        amp = 1.6 * min(1.0, 0.65 + 0.35 * s)
        ramp = smoothstep(-17.0, -1.0, d) * (1 - smoothstep(-0.6, 0.4, d))
        out = np.maximum(out, amp * ramp)
    return out


# ------------------------------------------------------------------ camera path

def h_trench(f, f_lint):
    """Camera z in the trench (upper third of the V), dip under the lint, climb out after it."""
    fk = [1, 16, 26, 38, f_lint - 4, f_lint, f_lint + 5, f_lint + 9, f_lint + 13, f_lint + 20, f_lint + 30, 90, 97]
    zk = [15.0, 13.0, 5.0, -5.0, -11.6, -12.8, -7.5, 1.5, 8.0, 15.5, 19.5, 20.0, 20.0]
    return pchip(fk, zk, f)


VAULT_F = [97, 100, 103, 106, 109, 112, 115, 118, 120, 122]
VAULT_S = [None, -44.0, -39.0, -34.0, -30.0, -26.0, -4.0, 10.0, 19.0, 28.0]   # approach frame <=101, tube frame >=117
VAULT_Z = [None, 33.0, 58.0, 86.0, 116.0, 142.0, 155.8, 161.8, 165.3, 168.8]
VAULT_L = [0.0, 1.0, 1.5, 1.5, 1.0, 0.5, 0.0, 0.0, 0.0, 0.0]
VAULT_YAW = [0.0, 2.0, 3.0, 3.0, 2.0, 1.0, 0.0, 0.0, 0.0, 0.0]
VAULT_PIT = [None, 30.0, 40.0, 44.0, 34.0, 14.0, 2.0, -6.0, -8.0, -8.5]
VAULT_TUBE_F = 115


def camera_path(data, frames=None):
    """Returns dict of arrays per frame: pos (N,3), yaw, pitch, roll (deg)."""
    f = np.arange(F0, F1 + 1) if frames is None else np.asarray(frames)
    fv = np.asarray(f, float)
    t = t_of(fv)
    ev = data.get('events', {})
    f_lint = ev.get('lint_pass', 49); f_vault = ev.get('vault_start', 97); f_crest = ev.get('crest', 115)
    s = s_of_t(np.minimum(t, 4.0))
    x, y = path_xy(s)
    ef = data.get('envf')
    # in the trench ride the music-shifted groove centre exactly
    if ef is not None:
        ym = groove_center(0, x, ef, True)
        w_tr = 1 - smoothstep(S_SPLIT - 5, S_SPLIT + 25, s)
        y = y + (ym - groove_center(0, x, None, False)) * w_tr
    z = h_trench(fv, f_lint)
    # ---- vault (local frame of the spire): continuous with the approach at f97
    vault = fv >= f_vault
    s97 = -(STANDOFF + ARRIS_R)
    vs = list(VAULT_S); vs[0] = s97
    vz = list(VAULT_Z); vz[0] = float(h_trench(np.array([f_vault]), f_lint)[0])
    # pre-roll knot so the pchip enters with the approach velocity
    s96 = s97 - float(s_of_t(4.0) - s_of_t(4.0 - 1 / FPS))
    kf = [f_vault - 1] + VAULT_F; ks = [s96] + vs; kz = [float(h_trench(np.array([f_vault - 1]), f_lint)[0])] + vz
    kl = [0.0] + list(VAULT_L)
    kx, ky = [], []
    for f_, s_, l_ in zip(kf, ks, kl):
        # key frame rotates with the crest turn: approach axis -> cantilever axis (smooth arc around the crown)
        ang = math.radians(PSI_DEG + TUBE_DT * float(smootherstep(TURN_F0, TURN_F1, f_)))
        dv = np.array([math.cos(ang), math.sin(ang)]); lv = np.array([-dv[1], dv[0]])
        kx.append(float(X_SP + s_ * dv[0] + l_ * lv[0])); ky.append(float(Y_SP + s_ * dv[1] + l_ * lv[1]))
    xv = pchip(kf, kx, fv); yv = pchip(kf, ky, fv); zv = pchip(kf, kz, fv)
    x = np.where(vault, xv, x); y = np.where(vault, yv, y); z = np.where(vault, zv, z)
    # ---- yaw: groove look-ahead in the trench, path heading + lead in the bank, spire bearing on approach
    hd = np.degrees(np.arctan(Bslope(x)))          # trench axis (groove is near-straight)
    bear = np.degrees(np.arctan2(Y_SP - y, X_SP - x))
    w = smoothstep(44, 86, fv)                      # one long even turn: <= ~2.3 deg/frame
    yaw = hd * (1 - w) + bear * w
    yaw_v = PSI_DEG + pchip(VAULT_F, VAULT_YAW, fv) + TUBE_DT * smootherstep(TURN_F0, TURN_F1, fv)
    yaw = np.where(vault, yaw_v, yaw)
    # pitch: look DOWN on the canyon field at the open, ease to level for the dive under the lint, then aim at the
    # spire's upper half so the whole jewel (crown included) is in frame during the approach
    pk_f = [1, 16, 30, 40, f_lint, f_lint + 6]
    pk_v = [-10.0, -9.5, -7.0, -4.5, -3.0, 0.5]
    pitch = pchip(pk_f, pk_v, fv)
    hdist = np.hypot(X_SP - x, Y_SP - y)
    aim = np.degrees(np.arctan2(52.0 - z, np.maximum(hdist, 1.0)))
    wa = smoothstep(f_lint + 6, f_lint + 18, fv)
    pitch = pitch * (1 - wa) + aim * wa
    p97 = float(np.interp(f_vault, fv, pitch)) if (fv.min() <= f_vault <= fv.max()) else None
    if p97 is None:
        xa, ya = path_xy(s_of_t(4.0)); p97 = float(np.degrees(np.arctan2(52.0 - 20.0, np.hypot(X_SP - xa, Y_SP - ya))))
    vp = list(VAULT_PIT); vp[0] = p97
    pitch = np.where(vault, pchip(VAULT_F, vp, fv), pitch)
    # needle-in-the-groove jolt on every kick (0.1-0.25 deg, decays in ~3 frames)
    for (tk, st) in data.get('kicks', []):
        if 0.0 <= tk <= 4.0:
            dt = t - tk
            j = np.where(dt >= 0, np.exp(-dt / 0.07), 0.0) * (0.1 + 0.15 * min(1.0, st))
            pitch = pitch - j
            yaw = yaw + 0.5 * j * np.sin(dt * 60.0)
    # bank into the turn (left turn -> positive roll), from the yaw rate; small, capped
    yr = np.gradient(np.unwrap(np.radians(yaw)))
    cap = 3.0 + 2.0 * (1 - smoothstep(54, 58, fv))
    roll = np.clip(np.degrees(yr) * 1.6, -cap, cap) * (1 - smoothstep(f_vault - 4, f_vault + 2, fv))
    # piloted, not dollied: slow roll drift and a gentle weave in the opening
    roll = roll + 1.2 * np.sin(fv / 13.0 + 0.6) * (1 - smoothstep(40, 52, fv))
    yaw = yaw + 0.6 * np.sin(fv / 17.0) * (1 - smoothstep(36, 50, fv))
    roll = roll + pchip([f_crest - 2, f_crest + 2, 120, 122], [0., 0., -4., -5.], fv) * (fv > f_crest - 2)
    pos = np.stack([x, y, z], -1)
    return dict(frames=f, t=t, pos=pos, yaw=yaw, pitch=pitch, roll=roll, s=s)


def cam_pos_at_t(data, tk):
    f = 1 + tk * FPS
    cp = camera_path(data, frames=np.array([f - 0.5, f, f + 0.5]))
    return cp['pos'][1]


def basis(yaw, pitch, roll):
    """Camera forward/up vectors from yaw (about Z, 0=+X), pitch (up +), roll (deg)."""
    ya, pa, ra = np.radians(yaw), np.radians(pitch), np.radians(roll)
    fwd = np.stack([np.cos(pa) * np.cos(ya), np.cos(pa) * np.sin(ya), np.sin(pa)], -1)
    left0 = np.stack([-np.sin(ya), np.cos(ya), np.zeros_like(ya)], -1)
    up0 = np.cross(fwd, left0)
    up = up0 * np.cos(ra)[..., None] + left0 * np.sin(ra)[..., None]
    return fwd, up


# ------------------------------------------------------------------ analytic surface (for checks)

def profile_z(u):
    a = np.abs(u)
    zw = Z_APEX + a
    zc = Z_APEX + ARC_R * math.sqrt(2) - np.sqrt(np.clip(ARC_R ** 2 - a ** 2, 0, None))
    z = np.where(a < ARC_R / math.sqrt(2), zc, zw)
    return np.minimum(z, 0.0)


def surface_z(x, y):
    yy = np.asarray(y, float) - B(x)
    g = np.round(yy / PITCH)
    return profile_z(yy - PITCH * g)
