# Verify a mix: silence window, drop/touchdown onsets, loudness arc (0.5 s RMS), loop seam. Usage: verify_mix.py mix.wav
import sys, subprocess, numpy as np
SR = 48000
p = sys.argv[1]
raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', p, '-ac', '2', '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True, check=True).stdout
x = np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64); m = x.mean(1)
db = lambda s: 20 * np.log10(np.sqrt(np.mean(s ** 2)) + 1e-12)
pk = lambda s: 20 * np.log10(np.abs(s).max() + 1e-12)
w = m[int(17.5 * SR):int(17.998 * SR)]
print(f'silence 17.500-17.998: RMS {db(w):.1f} dBFS, peak {pk(w):.1f} dBFS, nonzero samples {int((np.abs(w) > 1e-6).sum())}')
w2 = m[int(17.5 * SR):int(18.0 * SR)]
print(f'silence 17.500-18.000: peak {pk(w2):.1f} dBFS')
def attack(t, win=0.03):
    a = max(0, int((t - win) * SR)); seg = m[a:int((t + win) * SR)]
    k = int(0.0005 * SR); env = np.sqrt(np.convolve(seg ** 2, np.ones(k) / k, mode='same'))
    pre = np.median(env[:int(0.01 * SR)]); top = env.max()
    j = np.argmax(env > pre + 0.1 * (top - pre))
    return (a + j) / SR
for name, t in [('needle 0.0', 0.02), ('filter open 6.0', 6.0), ('cut 12.0', 12.0), ('DROP 18.0', 18.0), ('front 19.0', 19.0), ('touchdown 29.0', 29.0)]:
    ta = attack(t)
    print(f'  {name:16s} attack start {ta:.4f} s  (frame {ta*24+1:.2f}); 100 ms after: RMS {db(m[int(ta*SR):int((ta+0.1)*SR)]):.1f} dBFS, before 100 ms: {db(m[max(0,int((ta-0.1)*SR)):int(ta*SR)]):.1f}')
print('0.5 s RMS arc (dBFS):')
for s in np.arange(0, 30, 0.5):
    print(f'{s:4.1f}:{db(m[int(s*SR):int((s+0.5)*SR)]):6.1f}', end='  ' if (s * 2 + 1) % 6 else '\n')
print(f'\nloop seam: last 0.25 s RMS {db(m[-int(0.25*SR):]):.1f} dBFS, first 0.25 s RMS {db(m[:int(0.25*SR)]):.1f} dBFS; sample jump at seam {abs(m[-1]-m[0]):.4f}')
print(f'29.5-30.0 (black) RMS {db(m[int(29.5*SR):]):.1f}, peak {pk(m[int(29.5*SR):]):.1f}')
