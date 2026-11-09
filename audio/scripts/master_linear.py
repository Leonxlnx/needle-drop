# Linear master of the cue sheet: THE DELIVERY MIX.
# Usage (project root as cwd): python -I audio/scripts/master_linear.py [audio/cues.json] [audio/mix.wav]
# v3: writes audio/mix.wav (THE DELIVERY MIX, the bible 5.6 name). Music input = audio/_work/music_ducked.wav (edit_music.py:
#     the bible's ducks on the Pitbull track above 150 Hz only, per-sample); 17.500-17.998 is forced to digital zero after
#     the master chain (the IIR M/S high-pass and SFX filter tails would otherwise ring ~20 ms into the stop).
# Same per-clip processing as tools/mix.js (aresample, asetrate pitch, dur trim, fades, gain, pan, delay), but:
#  - timestamp-safe chain (asetpts=N/SR/TB, apad whole_len, atrim end_sample) and exact sample delays;
#  - no 5 ms limiter latency (cue times restored by +latency_compensation_s; music from audio/_work/music_ducked.wav);
#  - M/S low-end safety net: the side channel is high-passed at 150 Hz (4-pole), so everything below ~150 Hz is mono;
#  - LINEAR loudness: one static gain to -14 LUFS integrated + a latency-compensated peak limiter for TP <= -1 dBTP,
#    instead of mix.js's single-pass (dynamic/AGC) loudnorm, which lifts the quiet filtered intro and flattens the drop;
#  - loop seam: the film loops 30.0 -> 0.0; the last 2 ms are crossfaded towards the first sample value so the wrap is
#    click-free (the crackle bed itself is continuous across the seam by construction).
# Reports limiter gain reduction at the hero moments and writes audio/_work/master_report.json.
import sys, json, re, subprocess, numpy as np

CUES = sys.argv[1] if len(sys.argv) > 1 else 'audio/cues.json'
OUT = sys.argv[2] if len(sys.argv) > 2 else 'audio/mix.wav'
MUSIC = 'audio/_work/music_ducked.wav'
SR = 48000
cfg = json.load(open(CUES))
D = cfg['duration']; N = int(D * SR)
LAT = cfg.get('latency_compensation_s', 0.0)
MS_HP = ('pan=stereo|c0=0.5*c0+0.5*c1|c1=0.5*c0-0.5*c1,highpass=f=150:channels=FR,highpass=f=150:channels=FR,'
         'pan=stereo|c0=c0+c1|c1=c0-c1')

inputs, chains = [], []
def clip(c, label, music=False):
    inputs.extend(['-i', c['file'] if not music else MUSIC])
    i = len(inputs) // 2 - 1
    f = [f'aresample={SR}', 'aformat=sample_fmts=fltp:channel_layouts=stereo']
    r = c.get('rate', 1) or 1
    if r != 1: f += [f'asetrate={round(SR * r)}', f'aresample={SR}']
    if c.get('dur') is not None: f.append(f"atrim=start=0:duration={c['dur']}")
    f.append('asetpts=N/SR/TB')
    if c.get('fade_in'): f.append(f"afade=t=in:st=0:d={c['fade_in']}")
    if c.get('fade_out') and c.get('dur') is not None: f.append(f"afade=t=out:st={max(0, c['dur'] - c['fade_out'])}:d={c['fade_out']}")
    if c.get('gain_db'): f.append(f"volume={c['gain_db']}dB")
    p = c.get('pan') or 0
    if p:
        l, rr = min(1, 1 - p), min(1, 1 + p)
        f.append(f'pan=stereo|c0={l:.3f}*c0|c1={rr:.3f}*c1')
    at = (c.get('at') or 0) + (0 if music else LAT if (c.get('at') or 0) > 0 or c.get('name') in ('crackle_head',) else 0)
    if c.get('name') == 'crackle_head': at = 0.0   # head was pre-advanced for mix.js; restore by starting it 5 ms later in the source
    ds = int(round(at * SR))
    if ds > 0: f.append(f'adelay=delays={ds}S:all=1')
    f += [f'apad=whole_len={N}', f'atrim=end_sample={N}']
    chains.append(f'[{i}:a]' + ','.join(f) + f'[{label}]')
    return f'[{label}]'

labels = [clip(c, f'm{k}', music=True) for k, c in enumerate(cfg['music'])]
labels += [clip(c, f's{k}') for k, c in enumerate(cfg['sfx'])]
graph = ';'.join(chains) + ';' + ''.join(labels) + f'amix=inputs={len(labels)}:normalize=0,atrim=end_sample={N},{MS_HP}[pre]'
pre = 'audio/_work/premaster.wav'
subprocess.run(['ffmpeg', '-y', '-v', 'error', *inputs, '-filter_complex', graph, '-map', '[pre]', '-c:a', 'pcm_f32le', pre], check=True)

def meas(path):
    eb = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', path, '-af', 'ebur128=peak=true', '-f', 'null', '-'], capture_output=True, text=True).stderr
    I = float(re.findall(r'I:\s+(-?[\d.]+) LUFS', eb)[-1]); TP = float(re.findall(r'Peak:\s+(-?[\d.]+) dBFS', eb)[-1])
    LRA = float(re.findall(r'LRA:\s+(-?[\d.]+) LU', eb)[-1])
    return I, TP, LRA

def decode(path):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-'], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64)

# ---- kick window (sidechain-style): for the first ~45 ms of the two hero kicks (the sub peaks at +16 / +38 ms) the
# premaster's content above 150 Hz is pulled down KICK_DB, so the limiter spends its gain reduction on the mids/highs of
# that instant instead of flattening the kick + sub stack; the highs then return over 85 ms (dB-domain raised cosine, so
# they swell back in instead of re-attacking). The drop crack's loudest 5 ms (18.0015-18.0065) and the needle
# click at 29.0 sit before the window and pass untouched. Zero-phase complementary split (LR4 magnitude), per-sample gain.
KICK_DB = float(cfg.get('kick_window_db', 7.0))
xk = decode(pre)
tt = np.arange(len(xk)) / SR; kw = np.ones(len(xk)); KG = 10 ** (-KICK_DB / 20)
KW_ATT, KW_HOLD, KW_REL = [float(v) for v in cfg.get('kick_window_shape', [0.003, 0.040, 0.085])]   # s: attack, hold, release
for t0 in (18.008, 29.008):
    # 3 ms raised-cosine in, hold, then a slow raised-cosine release in the dB domain (no re-attack / flam when the highs return)
    r = (tt >= t0) & (tt < t0 + KW_ATT); kw[r] = 10 ** (-KICK_DB * 0.5 * (1 - np.cos(np.pi * (tt[r] - t0) / KW_ATT)) / 20)
    r = (tt >= t0 + KW_ATT) & (tt < t0 + KW_ATT + KW_HOLD); kw[r] = KG
    t2 = t0 + KW_ATT + KW_HOLD
    r = (tt >= t2) & (tt < t2 + KW_REL); kw[r] = 10 ** (-KICK_DB * 0.5 * (1 + np.cos(np.pi * (tt[r] - t2) / KW_REL)) / 20)
Fk = np.fft.rfftfreq(len(xk), 1 / SR); Hk = (Fk / 150.0) ** 4 / (1 + (Fk / 150.0) ** 4)
xk = xk + (kw - 1)[:, None] * np.fft.irfft(np.fft.rfft(xk, axis=0) * Hk[:, None], len(xk), axis=0)
subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', '-', '-c:a', 'pcm_f32le', pre],
               input=xk.astype('<f4').tobytes(), check=True)
I0, TP0, LRA0 = meas(pre)
xp = decode(pre)
print(f'pre-master: I {I0:.2f} LUFS, TP {TP0:.2f} dBTP, LRA {LRA0:.1f} LU, sample peak {20*np.log10(np.abs(xp).max()):+.2f} dBFS')
TARGET_I = -14.3   # bible: -14 LUFS +-0.5; -14.3 buys 0.3 dB less limiting at the hits and keeps 0.2 LU margin
gain = TARGET_I - I0; lim = -1.4
tmp = 'audio/_work/master_tmp.wav'
for it in range(6):
    af = f'volume={gain:.3f}dB,alimiter=limit={10 ** (lim / 20):.5f}:attack=1:release=60:level=false:latency=1'
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', pre, '-af', af, '-ar', str(SR), '-c:a', 'pcm_f32le', tmp], check=True)
    I, TP, LRA = meas(tmp)
    print(f'  iter {it}: gain {gain:+.2f} dB, limit {lim:.2f} dBFS -> I {I:.2f} LUFS, TP {TP:.2f} dBTP, LRA {LRA:.1f} LU')
    ok_i = abs(I - TARGET_I) <= 0.05; ok_tp = TP <= -1.05
    if ok_i and ok_tp: break
    if not ok_tp: lim -= (TP + 1.05) + 0.1
    gain += TARGET_I - I

# ---- the stop: 17.500-17.998 is digital zero (2 ms cosine fade ending at 17.500; the drop attack starts at 17.998)
y = decode(tmp)
i_a, i_b, nf = int(17.5 * SR), int(17.998 * SR), int(0.002 * SR)
y[i_a - nf:i_a] *= (0.5 * (1 + np.cos(np.pi * np.arange(1, nf + 1) / nf)))[:, None]
y[i_a:i_b] = 0.0
# ---- loop seam: crossfade the last 2 ms towards the first sample (the wrap 30.0 -> 0.0 must not click)
n = int(0.002 * SR); w = (np.arange(n) / (n - 1)) ** 2
y[-n:] = y[-n:] * (1 - w)[:, None] + y[0][None, :] * w[:, None]
# also ease the first 0.5 ms in from the seam value (the head starts with the needle tick's 1 ms pre-roll)
m = int(0.0005 * SR); v = np.arange(m) / m
y[:m] = y[0][None, :] * 0 + y[:m] * v[:, None] + y[-1][None, :] * (1 - v)[:, None]
pcm = np.clip(np.round(y * 8388607), -8388608, 8388607).astype('<i4')
b = pcm.reshape(-1).astype('<i4').view(np.uint8).reshape(-1, 4)[:, :3].tobytes()
subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 's24le', '-ar', str(SR), '-ac', '2', '-i', '-', '-c:a', 'pcm_s24le', OUT], input=b, check=True)
I, TP, LRA = meas(OUT)

# ---- limiter gain reduction (static-gain premaster vs output, 2 ms peak envelopes; the limiter is latency-compensated)
g_lin = 10 ** (gain / 20)
def penv(x):
    a = np.abs(x).max(1); k = int(0.002 * SR)
    from numpy.lib.stride_tricks import sliding_window_view as swv
    return np.concatenate([swv(a, k).max(-1), np.full(k - 1, a[-1])])
ep = penv(xp * g_lin); eo = penv(y)
gr = 20 * np.log10(np.maximum(ep, 1e-9) / np.maximum(eo, 1e-9))
gr[ep < 10 ** (-40 / 20)] = 0
gr[-int(0.005 * SR):] = 0     # the last 5 ms are the loop-seam crossfade, not limiting
gr[int(17.498 * SR):int(17.998 * SR)] = 0   # forced stop, not limiting
rep = dict(file=OUT, I=I, TP=TP, LRA=LRA, static_gain_db=round(gain, 2), limit_dbfs=round(lim, 2), premaster_peak_dbfs=round(20 * np.log10(np.abs(xp).max()), 2), gr={})
for name, a, b_ in [('drop 18.0', 17.99, 18.4), ('19.0 front', 18.95, 19.4), ('26.0 lift', 25.95, 26.4), ('touchdown 29.0', 28.99, 29.5), ('whole film', 0, 30)]:
    s = gr[int(a * SR):int(b_ * SR)]
    rep['gr'][name] = round(float(s.max()), 2)
over = gr > 1.0
rep['gr_over_1db_s'] = round(float(over.sum() / SR), 3)
print(f'MASTER {OUT}: I {I:.2f} LUFS, TP {TP:.2f} dBTP, LRA {LRA:.1f} LU; static gain {gain:+.2f} dB, limiter ceiling {lim:.2f} dBFS')
print('  limiter GR max (dB): ' + ', '.join(f'{k} {v:.2f}' for k, v in rep['gr'].items()) + f'; time with GR > 1 dB: {rep["gr_over_1db_s"]:.3f} s')
print(f'  loop seam jump {abs(y[-1] - y[0]).max():.5f}')
json.dump(rep, open('audio/_work/master_report.json', 'w'), indent=1)
print('MASTER_OK', OUT)
