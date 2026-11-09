# Tonal / percussive character: HPSS (median filtering) harmonic share, chroma key estimate, centroid.
# Usage: python -I audio/scripts/tonal.py a.mp3 b.mp3 ...
import sys, subprocess, numpy as np
from numpy.lib.stride_tricks import sliding_window_view as swv
SR = 22050; NFFT = 2048; HOP = 512

def load(path):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).astype(np.float64)

def stft(x):
    w = np.hanning(NFFT); n = 1 + (len(x) - NFFT) // HOP
    idx = np.arange(NFFT)[None, :] + HOP * np.arange(n)[:, None]
    return np.abs(np.fft.rfft(x[idx] * w, axis=1)).astype(np.float32)

NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
MAJ = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
MIN = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])

for p in sys.argv[1:]:
    x = load(p)
    M = stft(x)
    freqs = np.fft.rfftfreq(NFFT, 1 / SR)
    keep = freqs < 8000
    S = M[:, keep]
    # HPSS by median filters (17 frames in time, 17 bins in freq)
    pad_t = np.pad(S, ((8, 8), (0, 0)), mode='edge')
    H = np.median(swv(pad_t, 17, axis=0), axis=-1)
    pad_f = np.pad(S, ((0, 0), (8, 8)), mode='edge')
    P = np.median(swv(pad_f, 17, axis=1), axis=-1)
    mh = H ** 2 / (H ** 2 + P ** 2 + 1e-12)
    Hp = (S ** 2) * mh; Pp = (S ** 2) * (1 - mh)
    hshare = Hp.sum() / (Hp.sum() + Pp.sum())
    # harmonic share in 150-4000 Hz (melodic instruments) vs below
    f = freqs[keep]
    sel = (f >= 150) & (f < 4000)
    hshare_mid = Hp[:, sel].sum() / (Hp[:, sel].sum() + Pp[:, sel].sum())
    # chroma from harmonic part
    selc = (f >= 80) & (f < 2000)
    midi = 69 + 12 * np.log2(f[selc] / 440)
    pc = np.round(midi).astype(int) % 12
    C = np.zeros(12)
    hsum = Hp[:, selc].sum(0)
    for k in range(12): C[k] = hsum[pc == k].sum()
    C /= C.sum()
    best = max([(np.corrcoef(np.roll(MAJ, k), C)[0, 1], NAMES[k] + ' maj') for k in range(12)] + [(np.corrcoef(np.roll(MIN, k), C)[0, 1], NAMES[k] + ' min') for k in range(12)])
    ent = -(C * np.log2(C + 1e-12)).sum()
    cent = (S.sum(0) * f).sum() / S.sum()
    print(f'{p.split("/")[-1]:18s} harmonic_share={hshare:.2f} harmonic_share_150-4k={hshare_mid:.2f} chroma_entropy={ent:.2f}/3.58 key~{best[1]} (r={best[0]:.2f}) centroid={cent:.0f}Hz')
