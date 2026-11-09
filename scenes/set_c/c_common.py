"""Set C shared constants, timing and small helpers (Desert Record, S3-S6, global frames 289-708)."""
import os, sys, json, math
import numpy as np

ROOT = os.getcwd()
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import common as C   # noqa: E402
import nd_lib as ND  # noqa: E402

DATA = os.path.join(ROOT, 'data')
F0, F1 = 289, 708
FPS = 24.0

# ---------------------------------------------------------------- layout (metres)
R_CRATER = 25.0
R_LABEL = 240.0
R_GROOVE0 = 270.0
R_GROOVE1 = 1160.0
R_LEADIN = 1170.0
R_RIM = 1200.0          # disc mesh ends exactly here, OuterDesert starts here (3600 shared ring)
RING_PITCH = 40.0
CREST_H = 11.0         # adr1: taller, broader ridges so the low sun carves real relief (bible 6 m read flat)
MESA_H = 40.0
SUN_ELEV = 9.0
P_PIVOT = (1720.0, 145.0)   # r, bearing deg
L_LAND = (1150.0, 66.0)
ARM_LEN = 1880.0

# marble mapping for the desert (field = rotZ(ang) * (x, y, 0) * S + O). Override from data/handoff.json
MARBLE_S = 0.0042
MARBLE_ANG = 0.0
MARBLE_O = (7.31, 2.17, 0.37)


def pol(r, bearing_deg, z=0.0):
    a = math.radians(bearing_deg)
    return (r * math.cos(a), r * math.sin(a), z)


def t_of(f):
    """frame n covers (n-1)/24 .. n/24; we sample at the frame start."""
    return (f - 1.0) / FPS


def f_of(t):
    return t * FPS + 1.0


def smoothstep(a, b, x):
    u = np.clip((np.asarray(x, dtype=float) - a) / (b - a), 0.0, 1.0)
    return u * u * (3 - 2 * u)


def smootherstep(u):
    u = np.clip(np.asarray(u, dtype=float), 0.0, 1.0)
    return u * u * u * (u * (6 * u - 15) + 10)


def tau(t):
    """Frozen time for the half-beat of silence 17.5-18.0 (grains and kick rings hang)."""
    t = np.asarray(t, dtype=float)
    return np.where(t < 17.5, t, np.where(t < 18.0, 17.5, t - 0.5))


def load_json(name):
    p = os.path.join(DATA, name)
    if os.path.exists(p):
        try:
            with open(p) as f:
                return json.load(f)
        except Exception as ex:
            print('WARN json', name, ex)
    return None


def marble_mapping():
    """Return (S, ang, O, freq) for the desert marble. adr2: Set B publishes the match-cut mapping as
    handoff.json["S2_end"]["set_c_marble_match"] {scale, angle, offset, freq}; also accepted at top level as
    "set_c_marble". field = rotZ(ang) * (x, y, 0) * S + O -> ND.build_marble_field(scale=1, freq=freq)."""
    h = load_json('handoff.json') or {}
    m = (h.get('S2_end') or {}).get('set_c_marble_match') or h.get('set_c_marble')
    if m:
        return (float(m['scale']), float(m.get('angle', 0.0)), tuple(m.get('offset', MARBLE_O)),
                float(m.get('freq', ND.MARBLE_FREQ)))
    print('WARN marble mapping: no handoff key, fallback scale')
    return MARBLE_S, MARBLE_ANG, MARBLE_O, ND.MARBLE_FREQ


def kicks():
    b = load_json('beats.json') or {}
    ks = b.get('kicks') or [{'t': 0.5 * i, 'strength': 1.0} for i in range(60)]
    out = []
    for k in ks:
        if isinstance(k, dict):
            out.append((float(k.get('t', 0)), float(k.get('strength', 1.0))))
        else:
            out.append((float(k), 1.0))
    return out


def beats():
    b = load_json('beats.json') or {}
    return [float(x) for x in b.get('beats', [0.5 * i for i in range(60)])]


def band_series(frames):
    """8 band energies (0..1) per frame. Uses data/bands.json if present (several layouts tolerated),
    otherwise a synthetic beat-locked pattern (bass on beats, highs on off-beats)."""
    frames = np.asarray(frames, dtype=float)
    b = load_json('bands.json')
    try:
        if b is not None:
            fps = float(b.get('fps', 24)) if isinstance(b, dict) else 24.0
            arr = None
            if isinstance(b, dict):
                for key in ('bands', 'frames', 'values', 'energy', 'data'):
                    if key in b:
                        arr = b[key]; break
            elif isinstance(b, list):
                arr = b
            if isinstance(arr, dict):   # {"0":[...], ...}
                arr = [arr[k] for k in sorted(arr, key=lambda s: int(s) if str(s).isdigit() else s)]
                arr = np.asarray(arr, dtype=float).T
            arr = np.asarray(arr, dtype=float)
            if arr.ndim == 2 and arr.shape[1] != 8 and arr.shape[0] == 8:
                arr = arr.T
            if arr.ndim == 2 and arr.shape[1] >= 8:
                arr = arr[:, :8]
                mx = np.maximum(arr.max(axis=0), 1e-6)
                arr = arr / mx
                idx = np.clip(((frames - 1) / 24.0 * fps).astype(int), 0, len(arr) - 1)
                print('BANDS from bands.json', arr.shape)
                return arr[idx]
    except Exception as ex:
        print('WARN bands.json unreadable, synthetic bands', ex)
    t = (frames - 1) / 24.0
    out = np.zeros((len(t), 8))
    bt = np.array(beats())
    for i in range(8):
        lag = 0.0 if i < 4 else 0.25          # highs on the off-beat
        dec = 0.22 - 0.015 * i
        acc = np.zeros_like(t)
        for tb in bt:
            d = t - (tb + lag)
            acc = np.maximum(acc, np.where(d >= 0, np.exp(-d / dec), 0.0))
        out[:, i] = acc * (0.75 + 0.25 * np.sin(1.3 * i + t * (0.7 + 0.1 * i)))
    return np.clip(out, 0, 1)


def front_r(t):
    """Drop front radius. Before 18.0 it is far inside the label (no morph)."""
    t = np.asarray(t, dtype=float)
    fr = 240.0 + 880.0 * (t - 18.0)
    fr = np.where(t < 18.0, -200.0, fr)
    return np.where(t > 19.2, 1300.0, np.minimum(fr, 1300.0))


def morph_curve(u):
    """Spring-overshoot morph: points (0,0) (0.55,1.10) (0.78,0.96) (1,1) (smooth)."""
    xs = np.array([0.0, 0.55, 0.78, 1.0]); ys = np.array([0.0, 1.10, 0.96, 1.0])
    u = np.clip(u, 0, 1)
    return np.interp(u, xs, ys)


def write_layout(extra=None):
    S, ang, O, FQ = marble_mapping()
    d = {
        'units': 'metres', 'centre': [0, 0, 0], 'sun': {'from': '+Y', 'elevation_deg': SUN_ELEV, 'angle_deg': 0.6},
        'bearing_s3_s4_deg': 0.0,
        'radii': {'crater': R_CRATER, 'label': R_LABEL, 'groove': [R_GROOVE0, R_GROOVE1], 'leadin': [R_GROOVE1, R_LEADIN],
                  'trench': [R_LEADIN, R_RIM], 'disc_mesh_end': R_RIM},
        'ring_pitch': RING_PITCH, 'crest_h': CREST_H, 'label_mesa_h': MESA_H,
        'tonearm': {'pivot_r_bearing': P_PIVOT, 'landing_r_bearing': L_LAND, 'arm_len': ARM_LEN,
                    'pivot_xy': pol(*P_PIVOT)[:2], 'landing_xy': pol(*L_LAND)[:2]},
        'desert_marble': {'field_vector': 'rotZ(angle) * (x_obj, y_obj, 0) * scale + offset  -> nd_lib.build_marble_field(scale=1)',
                          'scale': S, 'angle': ang, 'offset': list(O), 'freq': FQ,
                          'note': 'S2 match cut: set B may publish data/handoff.json {"set_c_marble": {...}} and set C rebuilds to match.'},
        's3_first_frame': {'frame': 289, 'cam': [880, 0, 380], 'look': 'straight down', 'screen_up_world': '+X', 'screen_right_world': '-Y',
                           'lens_mm': 28, 'frame_width_m': 488.6},
    }
    if extra:
        d.update(extra)
    with open(os.path.join(DATA, 'layout_c.json'), 'w') as f:
        json.dump(d, f, indent=1)
