# SFX survey: format, loudness (ebur128 I, true peak), sample peak, envelope sketch, centroid, attack/peak time.
# Usage: python -I audio/scripts/sfx_survey.py files...
import sys, subprocess, re, numpy as np
SR = 48000
for p in sys.argv[1:]:
    pr = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'stream=sample_rate,channels,bits_per_sample,duration', '-of', 'csv=p=0', p], capture_output=True, text=True).stdout.strip()
    eb = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', p, '-af', 'ebur128=peak=true', '-f', 'null', '-'], capture_output=True, text=True).stderr
    I = re.findall(r'I:\s+(-?[\d.]+|-inf) LUFS', eb); TP = re.findall(r'Peak:\s+(-?[\d.]+|-inf) dBFS', eb)
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', p, '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True).stdout
    x = np.frombuffer(raw, np.float32).astype(np.float64)
    if len(x) == 0: print(p, 'EMPTY'); continue
    hop = int(0.05 * SR); n = len(x) // hop
    r = np.sqrt((x[:n * hop].reshape(n, hop) ** 2).mean(1) + 1e-12); db = 20 * np.log10(r)
    pkt = np.argmax(db) * 0.05
    att = np.argmax(db > db.max() - 20) * 0.05
    # sketch: 24 chars over the file
    m = 24; idx = np.linspace(0, n, m + 1).astype(int)
    sk = ''.join(' .:-=+*#%@'[max(0, min(9, int((db[idx[i]:max(idx[i]+1, idx[i+1])].max() - db.max() + 40) / 4)))] for i in range(m))
    X = np.abs(np.fft.rfft(x[:min(len(x), SR * 10)])); f = np.fft.rfftfreq(min(len(x), SR * 10), 1 / SR)
    cen = (X * f).sum() / X.sum()
    lo = (X[f < 150] ** 2).sum() / (X ** 2).sum()
    print(f"{p.split('/')[-1]:24s} {pr:28s} I={I[-1] if I else '?':>6s} TP={TP[-1] if TP else '?':>6s} att={att:4.2f}s pk@{pkt:5.2f}s cen={cen:5.0f}Hz low={lo:.2f} |{sk}|")
