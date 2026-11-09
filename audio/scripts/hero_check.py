# Hero-hit acceptance checks (art-director round 2): downbeat punch, build sub vacuum, touchdown, crackle phase.
# Usage (project root as cwd): python -I audio/scripts/hero_check.py [audio/mix.wav] [--json out.json]
#  - low50  : strongest 50 ms RMS of the 30-120 Hz band whose window starts in [t-0.02, t+0.2] (dBFS)
#  - full50 : same, full band;  low150: 30-120 Hz RMS over [t, t+0.15]
#  - Mmax   : max momentary loudness (400 ms, ebur128) with window end in (a, b]
#  - sub vacuum: 25-80 Hz RMS 17.0-17.5 vs 18.0-18.5
#  - crackle-only windows: L/R correlation and mono fold-down loss
import sys, re, json, subprocess, numpy as np
SR = 48000
P = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('--') else 'audio/mix.wav'
def dec(p):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', p, '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-'], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64)
def band(x, lo, hi):
    X = np.fft.rfft(x, axis=0); f = np.fft.rfftfreq(len(x), 1 / SR); X[(f < lo) | (f >= hi)] = 0
    return np.fft.irfft(X, len(x), axis=0)
db = lambda v: 20 * np.log10(v + 1e-12)
x = dec(P); m = x.mean(1)
lo = band(m, 30, 120); sub = band(m, 25, 80)
c_lo = np.concatenate([[0], np.cumsum(lo ** 2)]); c_fu = np.concatenate([[0], np.cumsum(m ** 2)])
W = int(0.05 * SR)
def best50(c2, t):
    a = int((t - 0.02) * SR); b = int((t + 0.2) * SR)
    s = np.arange(a, b, 24)
    return db(np.sqrt(((c2[s + W] - c2[s]) / W).max()))
def rms_c(c2, a, b):
    i, j = int(a * SR), int(b * SR); return db(np.sqrt((c2[j] - c2[i]) / (j - i)))
eb = subprocess.run(['ffmpeg', '-hide_banner', '-v', 'verbose', '-nostats', '-i', P, '-af', 'ebur128=framelog=verbose', '-f', 'null', '-'],
                    capture_output=True, text=True, errors='replace').stderr
Mt = np.array([(float(a), float(b)) for a, b in re.findall(r't:\s*([\d.]+)\s+TARGET:\S+ LUFS\s+M:\s*(-?[\d.]+)', eb)])
def Mmax(a, b):
    s = (Mt[:, 0] > a) & (Mt[:, 0] <= b + 1e-6); return float(Mt[s, 1].max())
def Mat(t): return float(Mt[np.argmin(np.abs(Mt[:, 0] - t)), 1])
res = dict(file=P, downbeats={})
print(f'{P}')
print(' t      low50  full50 low150')
for t in [2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 29]:
    r = dict(low50=round(best50(c_lo, t), 2), full50=round(best50(c_fu, t), 2), low150=round(rms_c(c_lo, t, t + 0.15), 2))
    res['downbeats'][str(t)] = r
    print(f'{t:5.1f}  {r["low50"]:6.1f} {r["full50"]:6.1f} {r["low150"]:6.1f}')
later = [res['downbeats'][str(t)] for t in [20, 22, 24, 26, 28, 29]]
d18 = res['downbeats']['18']; d29 = res['downbeats']['29']
full_all = max(v['full50'] for k, v in res['downbeats'].items() if k != '18')
res['accept'] = dict(
    drop_low50_ge_m10=d18['low50'] >= -10.0,
    drop_low50_1db_over_later=all(d18['low50'] >= v['low50'] + 1.0 for v in later),
    drop_full50_largest=d18['full50'] >= full_all,
    touch_low50_1db_over_26_28=d29['low50'] >= max(res['downbeats']['26']['low50'], res['downbeats']['28']['low50']) + 1.0)
res['Mmax_18_185'] = Mmax(18.0, 18.6); res['Mmax_29_295'] = Mmax(29.0, 29.5); res['Mmax_film'] = float(Mt[:, 1].max())
res['Mmax_film_t'] = float(Mt[np.argmax(Mt[:, 1]), 0]); res['M_17.4'] = Mat(17.4)
res['accept']['touch_M_ge_m10.5'] = res['Mmax_29_295'] >= -10.5
res['accept']['drop_loudest_M'] = res['Mmax_18_185'] >= Mmax(19.0, 29.5) - 1e-6 or res['Mmax_18_185'] >= Mmax(20.0, 29.5)
s17 = rms_c(np.concatenate([[0], np.cumsum(sub ** 2)]), 17.0, 17.5); s18 = rms_c(np.concatenate([[0], np.cumsum(sub ** 2)]), 18.0, 18.5)
res['sub_17_175'] = round(s17, 2); res['sub_18_185'] = round(s18, 2)
res['accept']['build_sub_le_m32'] = s17 <= -32.0; res['accept']['build_sub_12db_under'] = s18 - s17 >= 12.0
print(f'Mmax 18.0-18.6 {res["Mmax_18_185"]:.1f} | 29.0-29.5 {res["Mmax_29_295"]:.1f} | film max {res["Mmax_film"]:.1f} @ {res["Mmax_film_t"]:.1f} s | M(17.4) {res["M_17.4"]:.1f}')
print(f'25-80 Hz RMS 17.0-17.5 {s17:.1f} dBFS, 18.0-18.5 {s18:.1f} dBFS (contrast {s18 - s17:.1f} dB)')
res['crackle'] = {}
for a, b in [(0.05, 0.4), (29.5, 29.75), (29.5, 30.0), (29.75, 30.0)]:
    s = band(x[int(a * SR):int(b * SR)], 300, 20000); L, R = s[:, 0], s[:, 1]
    c = float(np.corrcoef(L, R)[0, 1]); st = (np.mean(L ** 2) + np.mean(R ** 2)) / 2; mo = np.mean(((L + R) / 2) ** 2)
    loss = float(10 * np.log10(st / mo)); res['crackle'][f'{a}-{b}'] = dict(r=round(c, 3), mono_loss=round(loss, 2))
    print(f'crackle {a:5.2f}-{b:5.2f} (>300 Hz): r {c:+.2f}, mono loss {loss:.1f} dB')
res['accept']['crackle_phase'] = all(v['r'] >= 0.3 and v['mono_loss'] <= 1.5 for k, v in res['crackle'].items() if k != '0.05-0.4')
for k, v in res['accept'].items(): print(f'  {"PASS" if v else "FAIL"}  {k}')
res['accept'] = {k: bool(v) for k, v in res['accept'].items()}
if '--json' in sys.argv: json.dump(res, open(sys.argv[sys.argv.index('--json') + 1], 'w'), indent=1)
