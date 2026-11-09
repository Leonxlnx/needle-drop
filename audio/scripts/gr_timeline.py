# Limiter gain-reduction timeline: premaster (x static gain) vs master. Usage: gr_timeline.py [premaster] [master] [gain_db]
import sys, json, subprocess, numpy as np
from numpy.lib.stride_tricks import sliding_window_view as swv
SR = 48000
pre = sys.argv[1] if len(sys.argv) > 1 else 'audio/_work/premaster.wav'
out = sys.argv[2] if len(sys.argv) > 2 else 'audio/mix_v2_linear.wav'
g = float(sys.argv[3]) if len(sys.argv) > 3 else json.load(open('audio/_work/master_report.json'))['static_gain_db']
def dec(p):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', p, '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-'], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64)
a = dec(pre) * 10 ** (g / 20); b = dec(out)
k = int(0.002 * SR)
ea = np.concatenate([swv(np.abs(a).max(1), k).max(-1), np.zeros(k - 1)]); eb = np.concatenate([swv(np.abs(b).max(1), k).max(-1), np.zeros(k - 1)])
gr = 20 * np.log10(np.maximum(ea, 1e-9) / np.maximum(eb, 1e-9)); gr[ea < 0.01] = 0; gr[-int(0.005 * SR):] = 0   # loop-seam crossfade
W = int(0.25 * SR)
row = []
for s in range(0, len(gr) - W + 1, W):
    v = gr[s:s + W].max()
    if v > 0.3: row.append(f'{s/SR:5.2f}:{v:.1f}')
print('GR > 0.3 dB per 0.25 s window:', ' '.join(row))
