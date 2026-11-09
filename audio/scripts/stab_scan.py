# Orchestral/brass stab candidates: strongest attacks, chroma just after each attack, D-minor fit, best triad.
# Usage: python -I audio/scripts/stab_scan.py a.wav b.wav ...
import sys, subprocess, numpy as np
SR = 48000
NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
def load(p):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', p, '-ac', '2', '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64)
def chroma(seg):
    n = len(seg); S = np.abs(np.fft.rfft(seg * np.hanning(n))) ** 2; f = np.fft.rfftfreq(n, 1 / SR)
    sel = (f >= 70) & (f < 2500); midi = 69 + 12 * np.log2(f[sel] / 440); pc = np.round(midi).astype(int) % 12
    C = np.array([S[sel][pc == k].sum() for k in range(12)]); return C / (C.sum() + 1e-20)
def templ(root, kind):
    t = np.zeros(12); iv = {'maj': [0, 4, 7], 'min': [0, 3, 7], '5': [0, 7]}[kind]
    for i in iv: t[(root + i) % 12] = 1
    return t
DMIN_KEY = np.zeros(12)
for i in [2, 4, 5, 7, 9, 10, 0]: DMIN_KEY[i] = 1   # D natural minor scale
for p in sys.argv[1:]:
    x = load(p); m = x.mean(1)
    k = int(0.005 * SR); env = np.sqrt(np.convolve(m ** 2, np.ones(k) / k, mode='same'))
    e = 20 * np.log10(env + 1e-9)
    hop = int(0.01 * SR); ed = e[::hop]; d = np.diff(ed)
    cand = np.argsort(d)[::-1]
    picks = []
    for c in cand:
        if d[c] < 6: break
        if all(abs(c - q) > 25 for q in picks): picks.append(c)
        if len(picks) >= 4: break
    print(f'== {p.split("/")[-1]} dur {len(m)/SR:.2f}s peak {20*np.log10(np.abs(x).max()):.1f} dBFS, LR corr {np.corrcoef(x[:,0],x[:,1])[0,1]:+.2f}')
    for c in sorted(picks):
        t = (c + 1) * hop / SR
        a = int(t * SR)
        seg = m[a + int(0.05 * SR):a + int(0.45 * SR)]
        if len(seg) < int(0.2 * SR): continue
        C = chroma(seg)
        fits = sorted([(float(C @ templ(r, kd) / templ(r, kd).sum()), NAMES[r] + kd) for r in range(12) for kd in ('maj', 'min', '5')])[::-1][:3]
        inkey = float(C @ DMIN_KEY)
        top3 = ' '.join(NAMES[i] for i in np.argsort(C)[::-1][:4])
        lvl = 20 * np.log10(np.sqrt(np.mean(m[a:a + int(0.3 * SR)] ** 2)) + 1e-12)
        # decay: time until env drops 20 dB below the post-attack peak
        pk = e[a:a + int(0.2 * SR)].max(); tail = e[a:]; below = np.where(tail < pk - 20)[0]
        dec = (below[below > int(0.02 * SR)][0] / SR) if (below > int(0.02 * SR)).any() else len(tail) / SR
        print(f'  attack {t:6.2f}s jump {d[c]:+.0f} dB  rms300 {lvl:6.1f}  decay-20dB {dec:.2f}s  pcs [{top3}]  D-minor-scale share {inkey:.2f}  best {fits[0][1]}({fits[0][0]:.2f}) {fits[1][1]}({fits[1][0]:.2f})')
