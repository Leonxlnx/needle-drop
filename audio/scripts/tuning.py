# Tuning estimate: harmonic-peak frequencies in a window, cents offset from A440 equal temperament.
# Usage: tuning.py file t0 t1 [fmin fmax]
import sys, subprocess, numpy as np
SR = 48000
NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
p = sys.argv[1]; a = float(sys.argv[2]); b = float(sys.argv[3])
lo = float(sys.argv[4]) if len(sys.argv) > 4 else 60; hi = float(sys.argv[5]) if len(sys.argv) > 5 else 2000
raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', p, '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True, check=True).stdout
m = np.frombuffer(raw, np.float32).astype(np.float64)[int(a * SR):int(b * SR)]
n = 1 << 16; acc = 0
for s in range(0, max(1, len(m) - n + 1), n // 4):
    seg = m[s:s + n]; acc = acc + np.abs(np.fft.rfft(seg * np.hanning(len(seg)), n * 2)) ** 2
f = np.fft.rfftfreq(n * 2, 1 / SR)
sel = (f >= lo) & (f < hi); S = acc[sel]; F = f[sel]
pk = np.where((S[1:-1] > S[:-2]) & (S[1:-1] > S[2:]))[0] + 1
pk = pk[np.argsort(S[pk])[::-1][:12]]
cents_w = []
for i in sorted(pk, key=lambda i: F[i]):
    y0, y1, y2 = np.log(S[i - 1:i + 2]); off = 0.5 * (y0 - y2) / (y0 - 2 * y1 + y2)
    fr = F[i] + off * (F[1] - F[0]); midi = 69 + 12 * np.log2(fr / 440); nr = int(round(midi))
    c = (midi - nr) * 100; cents_w.append((c, S[i]))
    print(f'  {fr:8.2f} Hz  {NAMES[nr % 12]}{nr // 12 - 1}  {c:+5.0f} c  {10*np.log10(S[i]/S[pk].max()):6.1f} dB')
cw = np.array(cents_w); ang = np.angle(np.sum(cw[:, 1] * np.exp(2j * np.pi * cw[:, 0] / 100)))
print(f'weighted tuning offset: {ang / (2 * np.pi) * 100:+.0f} cents')
