# Detailed analysis of a candidate: precise tempo, beat phase, per-bar band energies, drop downbeat.
# Usage: python -I audio/scripts/detail.py file.mp3 [bpm_lo bpm_hi]
import sys, subprocess, numpy as np

SR = 22050
NFFT = 2048
HOP = 128

def load(path, sr=SR):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-ac', '1', '-ar', str(sr), '-f', 'f32le', '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).astype(np.float64)

def stft_mag(x, nfft=NFFT, hop=HOP):
    w = np.hanning(nfft)
    xp = np.concatenate([np.zeros(nfft // 2), x, np.zeros(nfft // 2)])  # centred frames: frame k centred at k*hop
    n = 1 + (len(xp) - nfft) // hop
    out = np.empty((n, nfft // 2 + 1), np.float32)
    for s in range(0, n, 4096):
        e = min(n, s + 4096)
        idx = np.arange(nfft)[None, :] + hop * np.arange(s, e)[:, None]
        out[s:e] = np.abs(np.fft.rfft(xp[idx] * w, axis=1))
    return out

def flux(M, freqs, lo, hi):
    sel = (freqs >= lo) & (freqs < hi)
    L = np.log1p(100 * M[:, sel].astype(np.float64))
    d = np.diff(L, axis=0, prepend=L[:1])
    return np.maximum(d, 0).sum(1)

def main():
    path = sys.argv[1]
    lo = float(sys.argv[2]) if len(sys.argv) > 2 else 112
    hi = float(sys.argv[3]) if len(sys.argv) > 3 else 128
    x = load(path)
    M = stft_mag(x)
    fps = SR / HOP
    freqs = np.fft.rfftfreq(NFFT, 1 / SR)
    env = flux(M, freqs, 20, 11000)
    envL = flux(M, freqs, 30, 150)
    e = env - np.convolve(env, np.ones(64) / 64, mode='same'); e = np.maximum(e, 0)
    t = np.arange(len(e)) / fps
    # fine tempo + phase by comb over the whole track (beat-level), score = mean onset at grid points (interp)
    best = (0, 0, 0)
    res = []
    for bpm in np.arange(lo, hi, 0.01):
        P = 60.0 / bpm
        nb = int((t[-1] - 1) / P) - 1
        phs = np.arange(0, P, 0.004)
        pos = (phs[:, None] + P * np.arange(nb)[None, :]) * fps
        v = np.interp(pos, np.arange(len(e)), e).mean(1)
        k = np.argmax(v)
        res.append((bpm, v[k], phs[k]))
        if v[k] > best[1]: best = (bpm, v[k], phs[k])
    res = np.array(res)
    bpm, sc, ph = best
    print(f'precise tempo {bpm:.2f} BPM (score {sc:.3f}, median {np.median(res[:,1]):.3f}), beat phase {ph:.3f}s')
    # top tempo values
    o = np.argsort(-res[:, 1])[:5]
    print('  top:', [(round(res[i,0],2), round(res[i,1],3)) for i in o])
    P = 60 / bpm
    # band energies per beat
    P2 = M.astype(np.float64) ** 2
    bands = {'sub': (30, 90), 'low': (90, 250), 'mid': (250, 2000), 'hi': (2000, 11000)}
    BE = {k: P2[:, (freqs >= a) & (freqs < b)].sum(1) for k, (a, b) in bands.items()}
    tot = sum(BE.values())
    ref = np.percentile(tot, 95)
    nbeats = int((t[-1] - ph) / P)
    beats = ph + P * np.arange(nbeats)
    # downbeat phase: which of the 4 beat offsets has the strongest low-band flux on average
    bl = np.array([envL[int(b * fps):int(b * fps) + 4].max() if int(b * fps) + 4 < len(envL) else 0 for b in beats])
    off = int(np.argmax([bl[k::4].mean() for k in range(4)]))
    print('  low-flux by beat-in-bar offset:', [round(bl[k::4].mean(), 1) for k in range(4)], '-> downbeat offset', off)
    bars = beats[off::4]
    print(f'  bar  start   tot   sub   low   mid   hi  | lowflux per beat  | onset density')
    rows = []
    for i, b0 in enumerate(bars[:-1]):
        a, bb = int(b0 * fps), int((b0 + 4 * P) * fps)
        db = lambda arr: 10 * np.log10(arr[a:bb].mean() / ref + 1e-12)
        lf = [envL[int((b0 + k * P) * fps):int((b0 + k * P) * fps) + 4].max() for k in range(4)]
        dens = (e[a:bb] > np.percentile(e, 80)).mean()
        rows.append((i, b0, db(tot), db(BE['sub']), db(BE['low']), db(BE['mid']), db(BE['hi'])))
        print(f'  {i:3d} {b0:7.2f} {db(tot):5.1f} {db(BE["sub"]):5.1f} {db(BE["low"]):5.1f} {db(BE["mid"]):5.1f} {db(BE["hi"]):5.1f} | ' + ' '.join(f'{v:4.0f}' for v in lf) + f' | {dens:.2f}')
    rows = np.array(rows)
    # drop candidates: bar-level jump (bar i vs mean of bars i-2,i-1)
    jumps = []
    for i in range(2, len(rows)):
        j = rows[i, 2] - rows[i-2:i, 2].mean()
        jl = (rows[i, 3] + rows[i, 4]) / 2 - (rows[i-2:i, 3].mean() + rows[i-2:i, 4].mean()) / 2
        jumps.append((j + 0.5 * jl, i, rows[i, 1], j, jl))
    jumps.sort(reverse=True)
    print('  drop candidates (score, bar, time, dTot, dLow):', [(round(a,1), int(b), round(c,3), round(d,1), round(f,1)) for a,b,c,d,f in jumps[:4]])

main()
