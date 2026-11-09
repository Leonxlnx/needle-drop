# Where do the master's peaks come from? premaster vs music (with the 18.0/29.0 ducks) vs SFX (= premaster - music).
# Usage: peak_sources.py [premaster] ; prints sample peaks (dBFS, before the static master gain) per window.
import sys, json, subprocess, numpy as np
SR = 48000
def dec(p):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', p, '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-'], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64)
pre = dec(sys.argv[1] if len(sys.argv) > 1 else 'audio/_work/premaster.wav')
mus = dec('audio/music_edit.wav')[:len(pre)]
t = np.arange(len(mus)) / SR
duck = np.where((t >= 17.9) & (t <= 18.5), 0.708, np.where((t > 18.5) & (t < 18.65), 0.708 + 0.292 * (t - 18.5) / 0.15, np.where((t >= 28.98) & (t <= 29.5), 0.708, 1.0)))
mus = mus * duck[:, None]
sfx = pre - mus
g = json.load(open('audio/_work/master_report.json'))['static_gain_db']; lim = json.load(open('audio/_work/master_report.json'))['limit_dbfs']
db = lambda v: 20 * np.log10(v + 1e-12)
print(f'static gain {g:+.2f} dB, ceiling {lim:.2f} dBFS -> anything above {lim - g:+.2f} dBFS here is limited')
for a, b in [(0.5, 6), (6, 12), (12, 17.5), (17.99, 18.25), (18.25, 18.75), (18.75, 19.25), (19.25, 20), (20, 24), (24, 24.3), (24.3, 26), (26, 26.3), (26.3, 29), (29, 29.5)]:
    s = slice(int(a * SR), int(b * SR))
    pp, pm, ps = np.abs(pre[s]).max(), np.abs(mus[s]).max(), np.abs(sfx[s]).max()
    print(f'{a:6.2f}-{b:5.2f}: premaster {db(pp):6.1f}  music {db(pm):6.1f}  sfx {db(ps):6.1f}')
