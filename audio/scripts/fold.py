# Fold an HF transient envelope at a period to find the revolution tick. Usage: fold.py file period [t0 t1]
import sys, subprocess, numpy as np
SR = 48000
p = sys.argv[1]; P = float(sys.argv[2])
t0 = float(sys.argv[3]) if len(sys.argv) > 3 else 0; t1 = float(sys.argv[4]) if len(sys.argv) > 4 else None
raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', p, '-ac', '2', '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True, check=True).stdout
x = np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64)
x = x[int(t0 * SR):int(t1 * SR) if t1 else None]
m = x.mean(1)
X = np.fft.rfft(m); f = np.fft.rfftfreq(len(m), 1 / SR)
def band(lo, hi):
    Y = X.copy(); Y[(f < lo) | (f >= hi)] = 0; return np.fft.irfft(Y, len(m))
h = band(1500, 20000)
k = int(0.002 * SR); env = np.sqrt(np.convolve(h ** 2, np.ones(k) / k, mode='same'))
# refine period by maximizing fold contrast
best = None
for PP in np.arange(P - 0.03, P + 0.03, 0.0005):
    n = int(len(env) / SR / PP)
    if n < 2: break
    L = int(PP * SR); fold = np.zeros(L)
    for i in range(n):
        s = int(round(i * PP * SR)); seg = env[s:s + L]
        if len(seg) == L: fold += seg
    c = fold.max() / np.median(fold)
    if best is None or c > best[1]: best = (PP, c, fold / n)
PP, c, fold = best
j = int(np.argmax(fold))
print(f'{p}: refined period {PP:.4f} s ({60/PP:.2f} rpm), fold peak/median {c:.1f} at phase {j/SR:.4f} s')
# individual tick levels at each revolution
L = int(PP * SR)
lv = []
for i in range(int(len(env) / SR / PP)):
    s = int(round(i * PP * SR)) + j
    if s + 2400 < len(env): lv.append(20 * np.log10(env[max(0, s - 480):s + 480].max() + 1e-12))
print('tick peaks dB:', ' '.join(f'{v:.0f}' for v in lv[:30]))
print('env median dB %.1f, p99 %.1f' % (20 * np.log10(np.median(env)), 20 * np.log10(np.percentile(env, 99))))
for lo, hi in [(20, 150), (150, 600), (600, 1500), (1500, 5000), (5000, 20000)]:
    b = band(lo, hi); print(f'  band {lo}-{hi}: {20*np.log10(np.sqrt(np.mean(b**2))+1e-12):.1f} dBFS')
L_, R_ = x[:, 0], x[:, 1]
for lo, hi in [(20, 300), (300, 20000)]:
    XL = np.fft.rfft(L_); XR = np.fft.rfft(R_); ff = np.fft.rfftfreq(len(L_), 1 / SR)
    XL[(ff < lo) | (ff >= hi)] = 0; XR[(ff < lo) | (ff >= hi)] = 0
    a = np.fft.irfft(XL, len(L_)); b = np.fft.irfft(XR, len(R_))
    print(f'  L/R corr {lo}-{hi}: {np.corrcoef(a, b)[0,1]:+.2f}')
