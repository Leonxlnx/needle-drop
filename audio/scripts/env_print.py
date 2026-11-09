# Print a coarse RMS envelope (dBFS) of a file. Usage: env_print.py file step_s [t0 t1]
import sys, subprocess, numpy as np
SR = 48000
raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', sys.argv[1], '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True, check=True).stdout
m = np.frombuffer(raw, np.float32).astype(np.float64)
st = float(sys.argv[2]); a = float(sys.argv[3]) if len(sys.argv) > 3 else 0; b = float(sys.argv[4]) if len(sys.argv) > 4 else len(m) / SR
n = int(st * SR); out = []
for s in np.arange(a, b, st):
    seg = m[int(s * SR):int(s * SR) + n]
    if len(seg): out.append(f'{s:.2f}:{20*np.log10(np.sqrt(np.mean(seg**2))+1e-12):.0f}')
print(sys.argv[1].split('/')[-1], ' '.join(out))
