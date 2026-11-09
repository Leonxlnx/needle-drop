# Periodicity of transient envelope (locked-groove / revolution tick detection). Usage: periodicity.py file [t0 t1]
import sys, subprocess, numpy as np
SR = 48000
p = sys.argv[1]
raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', p, '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True, check=True).stdout
m = np.frombuffer(raw, np.float32).astype(np.float64)
if len(sys.argv) > 3: m = m[int(float(sys.argv[2]) * SR):int(float(sys.argv[3]) * SR)]
for lo_hz, name in [(1500, 'hf>1.5k'), (20, 'broad')]:
    X = np.fft.rfft(m); f = np.fft.rfftfreq(len(m), 1 / SR); X[f < lo_hz] = 0; h = np.fft.irfft(X, len(m))
    hop = 240; e = np.sqrt(np.add.reduceat(h ** 2, np.arange(0, len(h), hop)) / hop)
    e = np.log(e + 1e-9); d = np.maximum(0, np.diff(e)); d -= d.mean()
    ac = np.correlate(d, d, 'full')[len(d) - 1:]; ac /= ac[0]
    fr = SR / hop
    lags = np.arange(len(ac)) / fr
    sel = (lags > 0.4) & (lags < 3.0)
    top = np.argsort(ac[sel])[::-1][:5]
    print(name, 'len %.1fs' % (len(m) / SR), ' '.join(f'{lags[sel][i]:.3f}s:{ac[sel][i]:.3f}' for i in top))
