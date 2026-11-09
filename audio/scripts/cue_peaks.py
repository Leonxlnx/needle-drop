# Per-cue peak contribution (dBFS, before master gain) inside time windows. Usage: cue_peaks.py a:b [a:b ...]
import sys, json, subprocess, numpy as np
SR = 48000
cfg = json.load(open('audio/cues.json')); LAT = cfg.get('latency_compensation_s', 0)
def dec(p):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', p, '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-'], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64)
wins = [tuple(map(float, w.split(':'))) for w in sys.argv[1:]]
cache = {}
for c in cfg['sfx']:
    if c['file'] not in cache: cache[c['file']] = np.abs(dec(c['file'])).max(1)
    a = cache[c['file']]; r = c.get('rate', 1) or 1
    n = int(len(a) / r); idx = np.minimum((np.arange(n) * r).astype(int), len(a) - 1); y = a[idx]
    if c.get('dur') is not None: y = y[:int(c['dur'] * SR)]
    y = y * 10 ** (c['gain_db'] / 20); at = c['at'] + LAT
    out = []
    for a0, b0 in wins:
        i0 = max(0, int((a0 - at) * SR)); i1 = int((b0 - at) * SR)
        v = y[i0:i1].max() if i1 > i0 and i0 < len(y) else 0
        out.append(20 * np.log10(v + 1e-12))
    if max(out) > -30: print(f"{c['name']:22s} " + '  '.join(f'{v:6.1f}' for v in out))
