# Print a 1 ms-resolution amplitude envelope (dBFS) around given times. Usage: env_peek.py file t1 [t2 ...]
import sys, subprocess, numpy as np
SR=48000
raw=subprocess.run(['ffmpeg','-v','error','-i',sys.argv[1],'-ac','1','-ar',str(SR),'-f','f32le','-'],capture_output=True,check=True).stdout
x=np.frombuffer(raw,dtype=np.float32).astype(np.float64)
for t in map(float,sys.argv[2:]):
    row=[]
    for ms in range(-10,31,2):
        a=int((t+ms/1000)*SR); seg=x[a:a+int(0.002*SR)]
        row.append(f'{20*np.log10(np.abs(seg).max()+1e-9):5.0f}')
    print(f'{t:8.3f} [-10..+30ms, 2ms steps]:',' '.join(row))
