# Top onsets in SFX files (attack start, 1 ms resolution) + level at onset. Usage: sfx_onsets.py files...
import sys, subprocess, numpy as np
SR = 48000
for p in sys.argv[1:]:
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', p, '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True).stdout
    x = np.frombuffer(raw, np.float32).astype(np.float64)
    k = int(0.002 * SR)
    env = np.sqrt(np.convolve(x ** 2, np.ones(k) / k, mode='same') + 1e-12)
    db = 20 * np.log10(env)
    h = int(0.001 * SR)
    d = db[::h]
    # rise over 10 ms vs the previous 30 ms max
    rise = np.array([d[i + 10] - d[max(0, i - 30):i + 1].max() for i in range(len(d) - 10)])
    picks = []
    for i in np.argsort(-rise):
        if rise[i] < 6: break
        if all(abs(i - j) > 150 for j, _ in picks): picks.append((i, rise[i]))
        if len(picks) == 3: break
    out = []
    for i, r in sorted(picks):
        # attack start: first ms where level within 30 dB of the local peak (next 50 ms)
        pk = d[i:i + 60].max()
        a = i + int(np.argmax(d[i:i + 60] > pk - 24))
        out.append(f'{a/1000:.3f}s(+{r:.0f}dB, pk {pk:.0f}dBFS)')
    print(f"{p.split('/')[-1]:24s} dur={len(x)/SR:6.2f} max@{np.argmax(np.abs(x))/SR:.3f}s onsets: {' '.join(out)}")
