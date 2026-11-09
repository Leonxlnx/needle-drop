"""Set C camera (S3-S6) computed in numpy and baked one key per frame (+ half-frame keys around the
S3->S4 smash cut so motion blur never straddles the cut). Also returns per-frame altitude for mist/clip."""
import bpy, math
import numpy as np
from mathutils import Matrix, Quaternion, Euler
from c_common import *
from c_terrain import ground_h

CUT = 432.5
YAW4, Y4 = 16.0, -80.0   # adr2: S4 push yaw (deg) + lateral drift (m), carried into the S5 crane
DX_DESC = 65.0   # S3 descent travel (880 -> 945): the skim stays inside the marble field
# S6 end (adr1): the arm RECEDES in depth. Camera over the outer grooves at E, 45 m up, heading 145, 26 mm: headshell +
# cartridge right of centre ~670 m away, the chrome tube S-bends away to the left toward counterweight / gimbal / tower
# at P (~2.3 km, hazed); the low sun (+Y) is ~55 deg right of the axis (off-frame) so the chrome gets a hard rim.
E6 = (890.0, 530.0)
PITCH6 = 1.5     # adr2: horizon higher, ridges lead into the cartridge (was +4)
ALT6 = 45.0
HEAD6 = 145.0
LENS6 = 26.0
_L = pol(*L_LAND)
PHI6 = math.degrees(math.atan2(_L[1] - E6[1], _L[0] - E6[0]))
D6 = math.hypot(_L[0] - E6[0], _L[1] - E6[1])
Z4 = 17.0      # S4 lens height (bible 14 m; 11 m ridges + the hop wave would wall the lens off)
A4 = 110.0     # S4 end altitude (rises faster so ring arcs + spoke convergence read by f500)
# S6 dive (adr1): rotation dominates. A: hold high (1750 -> 1150 m) while pitching -89.5 -> -38 (the arm swings into view
# from above against the rings); B: log-altitude descent to E (horizontal travel tied to altitude drop); C: slow push.
TA0, TA1, TB1 = 26.75, 27.4, 28.6
S1POS = (152.0, -316.0, 1150.0); S1HEAD, S1PITCH = 105.0, -38.0


# qafix (QA must-fix 2): the S3 descent exponent e(u) = 0.45u + 0.55*smoothstep(u) has slope 0.45 at u=0, so the zoom
# jumped from 0 to ~2.3 %/frame at f308. For u < DESC_U1 (f330) a quartic ease-in replaces it: e(0)=0, e'(0)=0, and it
# rejoins the original at DESC_U1 with the same value, slope AND curvature (C2), with a monotonically rising zoom rate.
# Frames from f330 on are untouched (keys 308-329 change; rendered change 307-330 incl. motion blur).
DESC_U1 = ((330 - 1.0) / 24.0 - 12.75) / 3.25


def _desc_e0(u):
    return 0.45 * u + 0.55 * (3 * u * u - 2 * u ** 3)


def desc_exponent(u, ease=True):
    if not ease or u >= DESC_U1 or u <= 0.0:
        return _desc_e0(u)
    T = DESC_U1
    p1 = _desc_e0(T)
    v1 = (0.45 + 3.3 * T * (1 - T)) * T            # e'(T) * T
    a1 = (0.55 * (6.0 - 12.0 * T)) * T * T          # e''(T) * T^2
    # p(s) = a s^2 + b s^3 + c s^4 with p(1)=p1, p'(1)=v1, p''(1)=a1
    c = (a1 - 2 * p1 - 4 * (v1 - 2 * p1)) / 2.0
    b = (v1 - 2 * p1) - 2 * c
    a = p1 - b - c
    s = u / T
    return a * s * s + b * s ** 3 + c * s ** 4


def _hermite(p0, p1, v0, v1, T, u):
    h00 = 2 * u**3 - 3 * u**2 + 1; h10 = u**3 - 2 * u**2 + u; h01 = -2 * u**3 + 3 * u**2; h11 = u**3 - u**2
    return h00 * p0 + h10 * T * v0 + h01 * p1 + h11 * T * v1


class Path:
    def __init__(self, ground):
        self.g = ground
        # S3 x(t): integrate a velocity profile on a fine grid
        tt = np.arange(12.0, 18.0 + 1e-9, 1 / 480.0)
        v = np.ones_like(tt)
        uB = np.clip((tt - 12.75) / 3.25, 0, 1)
        altB = 380.0 * (7.0 / 380.0) ** (0.45 * uB + 0.55 * smoothstep(0, 1, uB))
        shape = (altB / 380.0) * np.sin(np.pi * uB)
        base = 1 + 24 * uB ** 2
        need = DX_DESC - np.trapezoid(np.where(tt >= 12.75, base, 0) * (tt <= 16.0), tt)
        A = need / np.trapezoid(np.where((tt >= 12.75) & (tt <= 16.0), shape, 0), tt)
        vB = base + A * shape
        v = np.where(tt >= 12.75, vB, v)
        v = np.where(tt >= 16.0, 25.0, v)
        uD = np.clip((tt - 17.5) / 0.5, 0, 1)
        v = np.where(tt >= 17.5, 25 + (3 - 25) * smootherstep(uD), v)
        x = 880.0 + np.concatenate([[0], np.cumsum(0.5 * (v[1:] + v[:-1]) * np.diff(tt))])
        self.tt3, self.x3 = tt, x
        # smoothed, look-ahead ground along y=0 for S3
        xs = np.arange(700, 1260, 0.5)
        gh = ground_h(ground, xs, np.zeros_like(xs))
        k = np.exp(-0.5 * (np.arange(-40, 41) / 14.0) ** 2); k /= k.sum()
        ghs = np.convolve(np.pad(gh, 40, mode='edge'), k, mode='valid')
        # look-ahead max (avoid clipping crests just ahead)
        la = np.array([ghs[i:i + 50].max() for i in range(len(ghs))])
        self.xs, self.gs = xs, np.maximum(ghs, la - 1.0)
        self.g1120 = float(ground_h(ground, np.array([1120.0]), np.array([0.0]))[0])

    def gx(self, x):
        return float(np.interp(x, self.xs, self.gs))

    # ---- returns pos(3), heading deg, pitch deg, roll deg, lens mm, alt above ground
    def s3(self, f, ease=True):
        t = t_of(f)
        x = float(np.interp(t, self.tt3, self.x3))
        y = 0.0
        if t < 12.75:
            alt = 380.0; pitch = -90.0; lens = 28.0
        elif t < 16.0:
            u = (t - 12.75) / 3.25
            alt = 380.0 * (7.0 / 380.0) ** desc_exponent(u, ease)     # qafix: eased start (see DESC_U1)
            pitch = -90.0 + 87.0 * float(smootherstep((u - 0.22) / 0.78))
            lens = 28.0 - 4.0 * float(smootherstep(u))
        else:
            alt = 7.0 - 0.8 * math.sin(2 * math.pi * (t - 16.0) / 1.5)
            pitch = -3.0
            lens = 24.0
        roll = 0.0
        if t >= 15.6:
            w = float(smoothstep(15.6, 16.2, t)) * (1 - float(smoothstep(17.3, 17.9, t)))
            ph = 2 * math.pi * (t - 15.6) / 1.9
            y = 7.0 * math.sin(ph) * w
            roll = -5.0 * math.sin(ph) * w      # bank into the weave
        ground = self.gx(x)
        z = ground + alt
        return (x, y, z), 0.0, pitch, roll, lens, alt

    def s4(self, f):
        t = t_of(f)
        gz = max(self.g1120, 0.0)
        x, z = 1120.0, Z4 + gz
        pitch, roll, heading = -3.0, 0.0, 180.0
        y = 0.0
        # adr2: 2-frame camera KICK on the f433 downbeat
        if 18.0 <= t < 18.0 + 3 / 24.0:
            k = (t - 18.0) / (3 / 24.0)
            pitch += 0.4 * math.cos(math.pi * k * 1.5) * (1 - k)
        if t > 19.2:
            tt = np.linspace(19.2, t, 200)
            v = 15 * smoothstep(19.2, 19.5, tt) + 25 * smoothstep(19.5, 21.5, tt)
            x -= float(np.trapezoid(v, tt)) if hasattr(np, 'trapezoid') else float(np.trapz(v, tt))
            w = float(smootherstep((t - 19.2) / 2.3)) ** 0.7
            z = Z4 + gz * (1 - w) + (A4 - Z4) * w
            pitch = -3.0 + (self.p4e() + 3.0) * float(smootherstep((t - 19.4) / 1.4))
            # adr2: yaw off the radial line + lateral drift so the rings read as ARCS sweeping to the label mesa
            w2 = float(smoothstep(19.15, 21.3, t))          # b2 review: start the yaw earlier (rings curve from ~f472)
            heading = 180.0 - YAW4 * w2
            y = Y4 * w2
        # 6-frame shake as the front passes (f456-462): 0 -> 0.6 deg -> 0
        # adr2: tilt up ~2.5 deg through the engulf so the straight near-ridge strip leaves the bottom of frame
        if 18.83 < t < 19.45:
            pitch += 2.5 * math.sin(math.pi * (t - 18.83) / 0.62)
        sh = 0.0
        if 18.9 < t < 19.35:
            sh = math.sin(math.pi * (t - 18.9) / 0.45)
        sx = 0.6 * sh * (math.sin(t * 71.0) * 0.6 + math.sin(t * 113.0 + 1.3) * 0.4)
        sy = 0.6 * sh * (math.sin(t * 83.0 + 0.7) * 0.6 + math.sin(t * 131.0 + 2.1) * 0.4)
        # residual roll settling after the pass
        if t > 19.0:
            roll = 2.2 * math.exp(-(t - 19.0) / 0.6) * math.sin((t - 19.0) * 5.0)
        return (x, y, z), heading + sy, pitch + sx, roll + sx * 0.5, 20.0, z - gz

    def x_end4(self):
        tt = np.linspace(19.2, 21.5, 400)
        v = 15 * smoothstep(19.2, 19.5, tt) + 25 * smoothstep(19.5, 21.5, tt)
        return 1120.0 - float(np.trapezoid(v, tt))

    def p4e(self):
        return math.degrees(math.atan2(-320.0 - A4, abs(-300.0 - self.x_end4())))

    def s5(self, f):
        t = t_of(f)
        x_end4 = self.x_end4()
        if t < 24.5:
            u = (t - 21.5) / 3.0
            s = float(smootherstep(u))
            se = float(smoothstep(0, 1, u))
            alt = A4 * (1750.0 / A4) ** se
            x = x_end4 * (1 - s)
            y = Y4 * (1 - s)
            T = (-300.0 * (1 - s), 0.0, -320.0 * (1 - s))
            dx, dz = T[0] - x, T[2] - alt
            pitch = max(-89.5, math.degrees(math.atan2(dz, abs(dx) + 1e-6)))
            pitch = min(pitch, -8.0)
            heading = (180.0 - YAW4) - (90.0 - YAW4) * float(smootherstep((u - 0.5) / 0.5))
            lens = 20.0 + 4.0 * float(smootherstep(u))
            return (x, y, alt), heading, pitch, 0.0, lens, alt
        return (0.0, 0.0, 1750.0), 90.0, -89.5, 0.0, 24.0, 1750.0

    def s6(self, f):
        t = t_of(f)
        L = np.array(pol(*L_LAND)[:2])
        E = np.array(E6)
        if t < TA0:
            return (0.0, 0.0, 1750.0), 90.0, -89.5, 0.0, 24.0, 1750.0
        if t < TA1:
            u = (t - TA0) / (TA1 - TA0)
            s = float(smootherstep(u))
            se = float(smoothstep(0, 1, u))
            alt = 1750.0 * (S1POS[2] / 1750.0) ** se
            xy = np.array(S1POS[:2]) * s
            pitch = -89.5 + (S1PITCH + 89.5) * s
            head = 90.0 + (S1HEAD - 90.0) * s
            return (xy[0], xy[1], alt), head, pitch, 0.0, 24.0, alt
        if t < TB1:
            u = (t - TA1) / (TB1 - TA1)
            se = float(smoothstep(0, 1, u)); s = float(smootherstep(u))
            A1 = S1POS[2]
            alt = A1 * (ALT6 / A1) ** se
            g = (A1 - alt) / (A1 - ALT6)                     # horizontal travel tied to the altitude drop
            xy = np.array(S1POS[:2]) + (E - np.array(S1POS[:2])) * g
            pitch = S1PITCH + (PITCH6 - S1PITCH) * s
            head = S1HEAD + (HEAD6 - S1HEAD) * s
            lens = 24.0 + (LENS6 - 24.0) * s
            return (xy[0], xy[1], alt), head, pitch, 0.0, lens, alt
        # slow 2 %/s push toward L, 3-frame micro-shake on touchdown (f697)
        k = 1.0 - 0.02 * (t - TB1)
        C = np.array([E[0], E[1], ALT6]); Lp = np.array([L[0], L[1], 0.0])
        P = Lp + (C - Lp) * k
        P[2] = ALT6
        sh = 0.0
        if 29.0 <= t < 29.0 + 3 / 24.0:
            sh = 0.35 * math.sin(math.pi * (t - 29.0) / (3 / 24.0)) * math.sin(t * 157.0)
        return (P[0], P[1], P[2]), HEAD6 + sh * 0.6, PITCH6 + sh, sh * 0.4, LENS6, P[2]

    def at(self, f, ease=True):
        if f < CUT: return self.s3(f, ease)
        if f < 516.5: return self.s4(f)
        if f < 624.5: return self.s5(f)
        return self.s6(f)


def quat(heading, pitch, roll):
    M = (Matrix.Rotation(math.radians(heading - 90.0), 4, 'Z') @ Matrix.Rotation(math.radians(90.0 + pitch), 4, 'X')
         @ Matrix.Rotation(math.radians(roll), 4, 'Z'))
    return M.to_quaternion()


def bake_camera(sc, ground):
    bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'
    cd = bpy.data.cameras.new('CamC'); cd.sensor_fit = 'HORIZONTAL'; cd.sensor_width = 36.0
    cd.clip_end = 120000.0; cd.dof.use_dof = False
    cam = bpy.data.objects.new('CamC', cd); sc.collection.objects.link(cam); sc.camera = cam
    cam.rotation_mode = 'QUATERNION'
    path = Path(ground)
    frames = list(range(F0, F1 + 1)) + [CUT - 0.01, CUT + 0.01]
    frames.sort()
    prev = None
    alts = {}
    for f in frames:
        pos, hd, pt, rl, lens, alt = path.at(f)
        q = quat(hd, pt, rl)
        if prev is not None and prev.dot(q) < 0:
            q.negate()
        prev = q
        cam.location = pos; cam.rotation_quaternion = q
        cd.lens = lens
        cd.clip_start = float(np.clip(0.05 * alt, 0.08, 40.0))
        cam.keyframe_insert('location', frame=f); cam.keyframe_insert('rotation_quaternion', frame=f)
        cd.keyframe_insert('lens', frame=f); cd.keyframe_insert('clip_start', frame=f)
        alts[f] = (alt, pos)
    return cam, path, alts
