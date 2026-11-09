# Mix/music measurement: EBU R128 (I, LRA, TP), momentary-loudness arc, section stats, crest factor,
# low-end stereo correlation + mono fold-down loss at the hero hits, silence window, loop seam.
# Usage (project root as cwd): python -I audio/scripts/measure.py file.wav [--arc] [--json out.json]
import sys, re, json, subprocess, numpy as np
SR = 48000
p = sys.argv[1]
eb = subprocess.run(['ffmpeg', '-hide_banner', '-v', 'verbose', '-nostats', '-i', p, '-af', 'ebur128=framelog=verbose:peak=true', '-f', 'null', '-'],
                    capture_output=True, text=True, errors='replace').stderr
Mt = [(float(a), float(b)) for a, b in re.findall(r't:\s*([\d.]+)\s+TARGET:\S+ LUFS\s+M:\s*(-?[\d.]+)', eb)]
I = float(re.findall(r'I:\s+(-?[\d.]+) LUFS', eb)[-1]); LRA = float(re.findall(r'LRA:\s+(-?[\d.]+) LU', eb)[-1])
TP = float(re.findall(r'Peak:\s+(-?[\d.]+) dBFS', eb)[-1])
raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', p, '-ac', '2', '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True, check=True).stdout
x = np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64); m = x.mean(1)
db = lambda v: 20 * np.log10(v + 1e-12)
rms = lambda s: np.sqrt(np.mean(s ** 2))
res = dict(file=p, I=I, LRA=LRA, TP=TP)
print(f'{p}: I {I:.1f} LUFS  LRA {LRA:.1f} LU  TP {TP:.1f} dBTP  sample peak {db(np.abs(x).max()):.2f} dBFS  clipped {(np.abs(x) >= 0.99999).sum()}')
tM = np.array([a for a, _ in Mt]); vM = np.array([b for _, b in Mt])
def Mmax(a, b):  # max momentary loudness with window END in (a, b]
    s = (tM > a) & (tM <= b + 1e-6); return float(vM[s].max()) if s.any() else -99
def Mmean(a, b):  # mean momentary (energy) over windows fully inside [a,b]
    s = (tM - 0.4 >= a - 1e-6) & (tM <= b + 1e-6); return float(10 * np.log10(np.mean(10 ** (vM[s] / 10)))) if s.any() else -99
if '--arc' in sys.argv:
    print('momentary loudness (LUFS, 400 ms window ending at t):')
    line = []
    for t in np.arange(0.5, 30.01, 0.5):
        k = np.argmin(np.abs(tM - t)); line.append(f'{t:4.1f}:{vM[k]:6.1f}')
        if len(line) == 8: print('  ' + '  '.join(line)); line = []
    if line: print('  ' + '  '.join(line))
secs = [(0.3, 6), (6, 12), (12, 14), (14, 16), (16, 17.5), (18, 20), (20, 26), (21, 26), (26, 29), (29, 29.5)]
res['sections'] = {}
print('section  mean-M  max-M   RMS dBFS  crest dB')
for a, b in secs:
    s = m[int(a * SR):int(b * SR)]; cr = db(np.abs(s).max()) - db(rms(s))
    res['sections'][f'{a}-{b}'] = dict(Mmean=round(Mmean(a, b), 2), Mmax=round(Mmax(a, b), 2), rms=round(db(rms(s)), 2), crest=round(cr, 2))
    print(f'{a:5.1f}-{b:4.1f}  {Mmean(a, b):6.1f}  {Mmax(a, b):6.1f}  {db(rms(s)):8.1f}  {cr:7.1f}')
for a, b in [(18.0, 18.5), (29.0, 29.5), (20.0, 26.0)]:
    s = m[int(a * SR):int(b * SR)]; res[f'crest_{a}'] = round(db(np.abs(s).max()) - db(rms(s)), 2)
# low-end stereo: L/R correlation and mono fold-down loss ((L+R)/2 vs stereo power) per band
def bandpass(sig, lo, hi):
    X = np.fft.rfft(sig, axis=0); f = np.fft.rfftfreq(len(sig), 1 / SR); X[(f < lo) | (f >= hi)] = 0
    return np.fft.irfft(X, len(sig), axis=0)
res['stereo'] = {}
for a, b in [(18.0, 18.9), (19.0, 19.5), (24.0, 24.5), (29.0, 29.5)]:
    seg = x[int(a * SR):int(b * SR)]; out = []
    for lo, hi in [(20, 150), (20, 120), (120, 500), (500, 20000)]:
        s = bandpass(seg, lo, hi); L, R = s[:, 0], s[:, 1]
        c = float(np.corrcoef(L, R)[0, 1]); st = (np.mean(L ** 2) + np.mean(R ** 2)) / 2; mo = np.mean(((L + R) / 2) ** 2)
        loss = float(10 * np.log10(st / (mo + 1e-20))); out.append(f'{lo}-{hi}: r {c:+.2f} mono-loss {loss:4.1f} dB')
        res['stereo'][f'{a}_{lo}-{hi}'] = dict(r=round(c, 3), mono_loss=round(loss, 2))
    print(f'stereo {a:.1f}-{b:.1f}: ' + ' | '.join(out))
w = m[int(17.5 * SR):int(17.998 * SR)]
res['silence_peak'] = float(db(np.abs(w).max())); res['silence_nonzero'] = int((np.abs(w) > 1e-6).sum())
print(f'silence 17.500-17.998: peak {db(np.abs(w).max()):.1f} dBFS, nonzero samples {(np.abs(w) > 1e-6).sum()}')
def attack(t, win=0.03):
    # steepest 2 ms rise of the 1 ms envelope within +-win, then walk back to where that rise starts (robust to a pre-swell,
    # e.g. the touchdown vacuum's hiss + crackle swell, which a fixed pre-level threshold would mistake for the attack)
    a = max(0, int((t - win) * SR)); seg = m[a:int((t + win) * SR)]
    k = int(0.001 * SR); env = 20 * np.log10(np.sqrt(np.convolve(seg ** 2, np.ones(k) / k, mode='same')) + 1e-12)
    d = int(0.002 * SR); rise = env[d:] - env[:-d]; j = int(np.argmax(rise))
    i = j + d
    while i > j and env[i - 1] > env[j] + 0.5 * rise[j]: i -= 1
    return (a + i) / SR
res['attacks'] = {}
for name, t in [('needle', 0.02), ('drop', 18.0), ('touchdown', 29.0)]:
    res['attacks'][name] = round(attack(t), 4)
print('attacks: ' + ', '.join(f'{k} {v:.4f}s' for k, v in res['attacks'].items()))
jump = abs(x[-1] - x[0]).max(); res['seam_jump'] = float(jump)
print(f'loop seam: sample jump {jump:.4f}; last/first 0.25 s RMS {db(rms(m[-int(0.25*SR):])):.1f}/{db(rms(m[:int(0.25*SR)])):.1f} dBFS; 29.5-30 RMS {db(rms(m[int(29.5*SR):])):.1f}')
if '--json' in sys.argv: json.dump(res, open(sys.argv[sys.argv.index('--json') + 1], 'w'), indent=1)
