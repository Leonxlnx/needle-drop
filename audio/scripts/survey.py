# Survey candidate music files: tempo, spectral balance, intro sparseness, biggest energy jump (drop).
# Usage: python -I audio/scripts/survey.py file1.mp3 file2.mp3 ...   (numpy only; ffmpeg decodes)
import sys, subprocess, numpy as np, os, json

SR = 22050
HOP = 512
NFFT = 2048

def load(path, sr=SR):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-ac', '1', '-ar', str(sr), '-f', 'f32le', '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).astype(np.float64)

def stft_mag(x):
    w = np.hanning(NFFT)
    n = 1 + (len(x) - NFFT) // HOP
    idx = np.arange(NFFT)[None, :] + HOP * np.arange(n)[:, None]
    fr = x[idx] * w
    return np.abs(np.fft.rfft(fr, axis=1))  # (frames, bins)

def onset_env(M, lo=None, hi=None):
    freqs = np.fft.rfftfreq(NFFT, 1 / SR)
    sel = np.ones_like(freqs, bool)
    if lo is not None: sel &= freqs >= lo
    if hi is not None: sel &= freqs < hi
    L = np.log1p(100 * M[:, sel])
    d = np.diff(L, axis=0, prepend=L[:1])
    return np.maximum(d, 0).sum(1)

def tempo(env, fps):
    e = env - np.convolve(env, np.ones(32) / 32, mode='same')
    e = np.maximum(e, 0); e = e - e.mean()
    n = len(e)
    f = np.fft.rfft(e, 2 * n)
    acf = np.fft.irfft(f * np.conj(f))[:n]
    acf /= acf[0]
    lags = np.arange(n)
    out = []
    for bpm in np.arange(60, 200, 0.02):
        L = 60 * fps / bpm
        v = np.interp(L, lags, acf) + 0.5 * np.interp(2 * L, lags, acf) + 0.5 * np.interp(4 * L, lags, acf) + 0.25 * np.interp(8 * L, lags, acf)
        out.append((bpm, v))
    return np.array(out)

def analyse(path):
    x = load(path)
    dur = len(x) / SR
    M = stft_mag(x)
    fps = SR / HOP
    env = onset_env(M)
    s = tempo(env, fps)
    i = np.argmax(s[:, 1])
    bpm = s[i, 0]
    # top 3 distinct tempo peaks
    order = np.argsort(-s[:, 1])
    peaks = []
    for j in order:
        b = s[j, 0]
        if all(abs(b - p) > 3 for p, _ in peaks): peaks.append((float(b), float(s[j, 1])))
        if len(peaks) == 3: break
    freqs = np.fft.rfftfreq(NFFT, 1 / SR)
    P = M ** 2
    low = P[:, (freqs >= 30) & (freqs < 150)].sum(1)
    mid = P[:, (freqs >= 150) & (freqs < 2000)].sum(1)
    high = P[:, freqs >= 2000].sum(1)
    tot = low + mid + high + 1e-12
    # 1 s energy curve in dB
    spf = int(round(fps))
    nsec = len(tot) // spf
    E = 10 * np.log10(tot[:nsec * spf].reshape(nsec, spf).mean(1) + 1e-12)
    El = 10 * np.log10(low[:nsec * spf].reshape(nsec, spf).mean(1) + 1e-12)
    Emax = np.percentile(E, 95)
    E -= Emax; El -= Emax
    # biggest jump: mean(next 4 s) - mean(prev 4 s)
    jumps = [(t, E[t:t + 4].mean() - E[t - 4:t].mean(), El[t:t + 4].mean() - El[t - 4:t].mean()) for t in range(4, nsec - 4)]
    jumps.sort(key=lambda r: -(r[1] + 0.5 * r[2]))
    bal = (low.sum() / tot.sum(), mid.sum() / tot.sum(), high.sum() / tot.sum())
    return dict(file=os.path.basename(path), dur=round(dur, 1), bpm=round(float(bpm), 2), bpm120=round(float(s[(s[:,0]>=100)&(s[:,0]<=145)][np.argmax(s[(s[:,0]>=100)&(s[:,0]<=145)][:,1]),0]),2), tempo_peaks=[(round(b, 2), round(v, 2)) for b, v in peaks],
                bal=[round(float(b), 3) for b in bal], intro8=round(float(E[:8].mean()), 1), jumps=[(int(t), round(float(a), 1), round(float(b), 1)) for t, a, b in jumps[:3]],
                curve=''.join(' .:-=+*#%@'[max(0, min(9, int((v + 30) / 3)))] for v in E))

if __name__ == '__main__':
    out = []
    for p in sys.argv[1:]:
        try:
            r = analyse(p)
        except Exception as ex:
            print('ERR', p, ex); continue
        out.append(r)
        print(f"{r['file']:18s} {r['dur']:6.1f}s bpm={r['bpm']:7.2f} best100-145={r['bpm120']:7.2f} peaks={r['tempo_peaks']} bal(L/M/H)={r['bal']} intro8={r['intro8']}dB jumps(t,dE,dLow)={r['jumps']}")
        print('   ', r['curve'])
        sys.stdout.flush()
