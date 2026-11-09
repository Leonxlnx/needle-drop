# Detail checks on the delivery mix: sand-hiss audibility vs music (2-8 kHz), crackle head/tail continuity across the loop,
# revolution tick prominence, kick-time accuracy vs the time-domain attack, kick/beat alignment.
# Usage (project root as cwd): python -I audio/scripts/check_details.py [audio/mix.wav]
import sys, json, subprocess, numpy as np
SR = 48000
MIX = sys.argv[1] if len(sys.argv) > 1 else 'audio/mix.wav'
def dec(p):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', p, '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-'], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64)
def band(x, lo, hi):
    X = np.fft.rfft(x, axis=0); f = np.fft.rfftfreq(len(x), 1 / SR); X[(f < lo) | (f >= hi)] = 0
    return np.fft.irfft(X, len(x), axis=0)
db = lambda v: 20 * np.log10(v + 1e-12)
rms = lambda v: np.sqrt(np.mean(v ** 2))
mix = dec(MIX).mean(1); mus = dec('audio/music_edit.wav').mean(1)
cfg = json.load(open('audio/cues.json')); LAT = cfg['latency_compensation_s']
rep = json.load(open('audio/_work/master_report.json')); g = 10 ** (rep['static_gain_db'] / 20)
# --- sand hiss vs music in 2-8 kHz, 150 ms after each hiss onset
hb = band(mix, 2000, 10000); mb = band(mus, 2000, 10000) * g
print('sand hiss (2-10 kHz, 150 ms after onset): mix vs music-alone level (dB) -> the hiss adds:')
row = []
for c in cfg['sfx']:
    if c['name'].startswith('sand_hiss'):
        t = c['at'] + LAT; s = slice(int(t * SR), int((t + 0.15) * SR))
        row.append(f"{t:.2f}:{db(rms(hb[s])) - db(rms(mb[s])):+.1f}")
print('  ' + ' '.join(row))
# --- crackle continuity across the loop (2-12 kHz, mix): last 0.4 s vs first 0.4 s excluding the needle tick
cb = band(mix, 2000, 12000)
print(f'crackle 2-12 kHz: 29.6-30.0 {db(rms(cb[int(29.6*SR):])):.1f} dBFS | 0.05-0.45 {db(rms(cb[int(0.05*SR):int(0.45*SR)])):.1f} dBFS (incl. filtered music)')
# --- revolution ticks: peak at each tick vs the bed's 99th pct 1 ms peak in the surrounding 1 s
k = int(0.001 * SR); env = np.sqrt(np.convolve(cb ** 2, np.ones(k) / k, mode='same'))
for t in [1.55, 3.35, 5.15, 6.95, 8.75, 10.55, 29.75]:
    i = int(t * SR); w = env[i - 2400:i + 4800]; j = int(np.argmax(w)); ctx = np.percentile(env[i - SR // 2:i + SR // 2], 99)
    print(f'  tick ~{t:5.2f}: peak at {(i - 2400 + j)/SR:.3f} s, {db(w[j]) - db(ctx):+.1f} dB over the local 99th pct 1 ms crackle peak')
# --- kicks: JSON time vs broadband time-domain attack (1 ms envelope, 25 % of the way from the pre level to the local peak)
b = json.load(open('data/beats.json'))
def attack(x, t):
    a = int((t - 0.04) * SR); seg = np.abs(x[a:a + int(0.08 * SR)])
    e = np.convolve(seg, np.ones(k) / k, mode='same'); pre = np.median(e[:int(0.02 * SR)]); pk = e[int(0.02 * SR):].max()
    return (a + int(0.02 * SR) + int(np.argmax(e[int(0.02 * SR):] > pre + 0.25 * (pk - pre)))) / SR
lowm = band(mus, 30, 150)
d = np.array([kk['t'] - attack(lowm, kk['t']) for kk in b['kicks']])
print(f"kicks: {len(b['kicks'])}; JSON t minus low-band (30-150 Hz) time-domain attack: median {np.median(d)*1000:+.1f} ms, p90 |d| {np.percentile(np.abs(d), 90)*1000:.1f} ms")
fr_ok = sum(1 for kk in b['kicks'] if kk['frame'] == int(np.floor(kk['t'] * 24)) + 1)
print(f"kick frame field = floor(t*24)+1 for {fr_ok}/{len(b['kicks'])}; downbeat kicks: " +
      ', '.join(f"{kk['t']:.3f}->f{kk['frame']}" for kk in b['kicks'] if abs(kk['t'] - round(kk['t'] / 2) * 2) < 0.03))
