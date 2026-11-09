# Precise beat-grid fit and per-downbeat hit strength for a 120 BPM track.
# Usage: python -I audio/scripts/downbeats.py file [bpm] [grid0_guess]
import sys, subprocess, numpy as np
SR = 48000

def load(path):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).astype(np.float64)

def onset_env(x, hop=48, nfft=1024, lo=20, hi=16000):
    w = np.hanning(nfft)
    xp = np.concatenate([np.zeros(nfft // 2), x, np.zeros(nfft // 2)])
    n = 1 + (len(xp) - nfft) // hop
    freqs = np.fft.rfftfreq(nfft, 1 / SR)
    sel = (freqs >= lo) & (freqs < hi)
    env = np.zeros(n)
    prev = None
    for s in range(0, n, 8192):
        e = min(n, s + 8192)
        idx = np.arange(nfft)[None, :] + hop * np.arange(s, e)[:, None]
        L = np.log1p(100 * np.abs(np.fft.rfft(xp[idx] * w, axis=1))[:, sel])
        if prev is not None: L = np.vstack([prev, L])
        d = np.maximum(np.diff(L, axis=0), 0).sum(1)
        env[s + (0 if prev is not None else 1):e] = d if prev is not None else d
        prev = L[-1:]
    return env, SR / hop

if __name__ == '__main__':
    path = sys.argv[1]
    bpm = float(sys.argv[2]) if len(sys.argv) > 2 else 120.0
    x = load(path)
    env, fps = onset_env(x)
    P = 60 / bpm
    t = np.arange(len(env)) / fps
    # fit phase at 1 ms resolution
    phs = np.arange(0, P, 0.001)
    nb = int((t[-1] - 1) / P) - 1
    best = None
    for ph in phs:
        pos = ((ph + P * np.arange(nb)) * fps).astype(int)
        v = env[pos].sum()
        if best is None or v > best[0]: best = (v, ph)
    ph = best[1]
    # per-beat local refinement: max of env within +-25 ms of grid
    beats = ph + P * np.arange(nb)
    dev = []
    for b in beats:
        a = int((b - 0.025) * fps); c = int((b + 0.025) * fps)
        if a < 0 or c >= len(env): continue
        k = a + np.argmax(env[a:c])
        if env[k] > np.percentile(env, 90): dev.append((b, k / fps - b))
    dev = np.array(dev)
    # linear fit of deviations vs time -> tempo correction
    A = np.vstack([dev[:, 0], np.ones(len(dev))]).T
    slope, icpt = np.linalg.lstsq(A, dev[:, 1], rcond=None)[0]
    print(f'phase {ph:.3f}s; strong-beat deviations: median {np.median(dev[:,1])*1000:.1f} ms, MAD {np.median(np.abs(dev[:,1]-np.median(dev[:,1])))*1000:.1f} ms; drift {slope*1e3*60:.2f} ms/min -> true bpm ~ {bpm/(1+slope):.3f}')
    if len(sys.argv) > 3:
        g0 = float(sys.argv[3])
        g0 = ph + P * round((g0 - ph) / P)
        print('downbeat grid anchored at', round(g0, 3))
        for i in range(int(len(x) / SR / (4 * P))):
            d = g0 + 4 * P * (i - int(g0 / (4 * P)))
            if d < 0.05 or d > len(x) / SR - 0.3: continue
            a = int(d * SR)
            pre = np.sqrt(np.mean(x[max(0, a - int(0.15 * SR)):a] ** 2) + 1e-12)
            post = np.sqrt(np.mean(x[a:a + int(0.15 * SR)] ** 2) + 1e-12)
            pk = np.max(np.abs(x[a:a + int(0.1 * SR)]))
            k0 = int((d - 0.03) * fps); k = k0 + np.argmax(env[k0:int((d + 0.03) * fps)])
            print(f'  bar@{d:7.3f}  onset {k/fps:7.3f}  post150ms {20*np.log10(post):6.1f} dB  pre {20*np.log10(pre):6.1f} dB  jump {20*np.log10(post/pre):5.1f}  peak {20*np.log10(pk):5.1f} dBFS  flux {env[k]:.0f}')
