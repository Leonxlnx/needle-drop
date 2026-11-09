# Scan SFX files: per-0.25 s window level, spectral centroid, flatness, HF click rate, tonal peakiness.
# Usage: python -I audio/scripts/sfx_scan.py file.wav [win_s]
import sys, subprocess, numpy as np
SR = 48000
p = sys.argv[1]; W = float(sys.argv[2]) if len(sys.argv) > 2 else 0.25
raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', p, '-ac', '2', '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True, check=True).stdout
x = np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64); m = x.mean(1)
db = lambda v: 20 * np.log10(v + 1e-12)
# HF click detector: highpass via FFT >2.5 kHz, 0.5 ms envelope, peaks > 4x local median
X = np.fft.rfft(m); f = np.fft.rfftfreq(len(m), 1 / SR); X[f < 2500] = 0; h = np.fft.irfft(X, len(m))
k = int(0.0005 * SR); env = np.sqrt(np.convolve(h ** 2, np.ones(k) / k, mode='same'))
print(f'{p}: {len(m)/SR:.2f}s peak {db(np.abs(x).max()):.1f} dBFS  L/R corr {np.corrcoef(x[:,0],x[:,1])[0,1]:+.2f}')
n = int(W * SR)
for s in range(0, len(m) - n + 1, n):
    seg = m[s:s + n]; S = np.abs(np.fft.rfft(seg * np.hanning(n))) ** 2; ff = np.fft.rfftfreq(n, 1 / SR)
    cen = (S * ff).sum() / (S.sum() + 1e-20)
    sel = (ff > 100) & (ff < 8000)
    flat = np.exp(np.mean(np.log(S[sel] + 1e-20))) / (np.mean(S[sel]) + 1e-20)
    e = env[s:s + n]; med = np.median(e) + 1e-12
    pk = (e[1:-1] > e[:-2]) & (e[1:-1] >= e[2:]) & (e[1:-1] > 4 * med)
    # tonal: fraction of energy in top 1% bins (100-4000 Hz)
    sel2 = (ff > 80) & (ff < 4000); Ss = np.sort(S[sel2])[::-1]; ton = Ss[:max(1, len(Ss) // 100)].sum() / (Ss.sum() + 1e-20)
    lo = S[(ff > 30) & (ff < 200)].sum() / (S.sum() + 1e-20)
    print(f'{s/SR:6.2f} rms {db(np.sqrt(np.mean(seg**2))):6.1f}  hf {db(np.sqrt(np.mean(h[s:s+n]**2))):6.1f}  cen {cen:6.0f}  flat {flat:.3f}  ton {ton:.2f}  low {lo:.2f}  clicks/s {pk.sum()/W:5.0f}')
