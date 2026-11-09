# Chroma (bass 40-300 Hz and mid 300-2500 Hz) of a file at given windows. Usage: chroma_at.py file t0:t1 t0:t1 ...
import sys, subprocess, numpy as np
SR = 48000
NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', sys.argv[1], '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True, check=True).stdout
m = np.frombuffer(raw, np.float32).astype(np.float64)
def chroma(seg, lo, hi):
    # average of 0.19 s frames (resolution 5 Hz) to keep bass pitch resolution
    n = 8192; acc = 0
    for s in range(0, max(1, len(seg) - n), n // 2):
        S = np.abs(np.fft.rfft(seg[s:s + n] * np.hanning(len(seg[s:s + n])), n)) ** 2; acc = acc + S
    f = np.fft.rfftfreq(n, 1 / SR); sel = (f >= lo) & (f < hi)
    pc = np.round(69 + 12 * np.log2(f[sel] / 440)).astype(int) % 12
    C = np.array([acc[sel][pc == k].sum() for k in range(12)]); return C / C.sum()
for w in sys.argv[2:]:
    a, b = map(float, w.split(':'))
    seg = m[int(a * SR):int(b * SR)]
    out = []
    for lo, hi, nm in [(40, 300, 'bass'), (300, 2500, 'mid')]:
        C = chroma(seg, lo, hi); o = np.argsort(C)[::-1][:4]
        out.append(nm + ' ' + ' '.join(f'{NAMES[i]}{C[i]:.2f}' for i in o))
    print(f'{a:6.2f}-{b:6.2f}: ' + ' | '.join(out))
