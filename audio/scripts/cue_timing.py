# Cue peak timing check: for each cue (rendered as the master places it: rate, dur, gain, at + latency compensation) print
# the time of its loudest 5 ms and of its loudest 50 ms (RMS), with the film frame (floor(t*24)+1).
# Usage (project root as cwd): python -I audio/scripts/cue_timing.py [name ...]   (default: the hero cues)
import sys, json, subprocess, numpy as np
SR = 48000
cfg = json.load(open('audio/cues.json')); LAT = cfg.get('latency_compensation_s', 0)
names = sys.argv[1:] or ['drop_crack', 'drop_sub_kick', 'drop_sub_boom', 'drop_explosion', 'roar', 'front_whoosh_impact', 'front_pass_wind',
                         'disc_grind', 'disc_spinup', 'arm_servo', 'arm_creak', 'arm_hydraulic', 'touchdown_crackle_swell', 'touchdown_needle',
                         'touchdown_sub_kick', 'touchdown_boom', 'air_rush', 'needle_thunk', 'needle_tick_0']
def dec(p):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', p, '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-'], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64)
for c in cfg['sfx']:
    if c['name'] not in names: continue
    x = dec(c['file']).mean(1); r = c.get('rate', 1) or 1
    n = int(len(x) / r); y = np.interp(np.arange(n) * r, np.arange(len(x)), x) if r != 1 else x
    if c.get('dur') is not None: y = y[:int(c['dur'] * SR)]
    y = y.copy(); tt = np.arange(len(y)) / SR       # cue-level fades (linear, as afade's default 'tri')
    if c.get('fade_in'): y *= np.clip(tt / c['fade_in'], 0, 1)
    if c.get('fade_out') and c.get('dur') is not None: y *= np.clip((c['dur'] - tt) / c['fade_out'], 0, 1)
    at = c['at'] + (LAT if c['at'] > 0 else 0)
    out = []
    for w in (0.005, 0.05):
        k = int(w * SR); e = np.sqrt(np.convolve(y ** 2, np.ones(k) / k, mode='valid'))
        i = int(np.argmax(e)); t = at + (i + k / 2) / SR
        out.append(f'loudest {w*1000:.0f} ms centred {t:7.3f} s (f{int(np.floor(t*24))+1})')
    print(f"{c['name']:24s} {at:7.3f}-{at + len(y)/SR:7.3f}  " + ' | '.join(out))
