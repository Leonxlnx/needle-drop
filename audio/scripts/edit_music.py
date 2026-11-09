# NEEDLE DROP music edit (v2): cut the real recording (Mixkit "Pitbull", 120.000 BPM, Eb minor) at bar boundaries with ffmpeg,
# layer the hybrid-cinematic elements (Mixkit "Epical Drums 02" percussion groove + hit, Mixkit SFX "Orchestra triumphant
# trumpets" chopped into a brass power-chord stab) and apply the POV filter automation (bible 6.1).
# Usage (project root as cwd): python -I audio/scripts/edit_music.py [--no-latency-comp]
# Outputs: audio/music_edit.wav          48 kHz stereo 24-bit: analysis + picture-sync master, no ducking. THE music master.
#          audio/_work/music_ducked.wav  music_edit.wav + the bible's ducks (Pitbull above 150 Hz only): THE MIX INPUT (master_linear.py)
#          audio/_work/music_stem_mixjs.wav  the ducked music ADVANCED 240 samples: input for tools/mix.js ONLY
#                                        (cancels its 5 ms limiter latency). Never mux or VSE-load this file.
#          audio/music_edit_map.json     segment table (out times, source times, fx, gains) - used by audio_analyze.py to
#                                        validate kicks against the dry source.
# v2 changes (art-director round 1): build = gain ramp (+2.5 -> +6 dB, replaces the static +5 dB echo make-up) with a
# 30 -> 250 Hz 4-pole high-pass sweep over the last bar (16.0-17.5) so the bass returns on 18.0; drop + lift +2 dB;
# Epical layer = its 8-bar percussion groove after the 58 s hit under 18-26 at -9 dB (hit -6 dB), high-passed at 140 Hz
# so only the Pitbull 808 owns the sub; brass stab (Eb5 on 18.0 and 29.0, Bb4 on 24.0, the bass note there).
# v3 changes (art-director round 2):
#  - stabs re-pitched with rubberband (formant preserved, crisp transients) instead of asetrate (no 'sampler' formant shift);
#    the -2 st stab is Bb4 (C5 - 2 st), not Bb5.
#  - touchdown = the drop's twin: final-hit slice +2 dB (= drop), 29.0 stab at the 18.0 stab level, Epical hit -7 dB;
#    pre-hit VACUUM: the lift high-passes 30 -> 300 Hz over 28.25-28.75 (the push), then the music cuts at 28.75 and
#    stays silent until the 28.998 touchdown (echoes the 17.5 stop). Lift +1 dB (was +2).
#  - the bible's 3 dB ducks at 18.0 / 29.0 now act on the Pitbull track ABOVE 150 Hz only (zero-phase complementary
#    shelf, per-sample gain, cosine recovery): the kick, the 808 and the hybrid layers (stab, Epical hit) are never ducked.
#    music_edit.wav stays unducked (analysis + picture master); audio/_work/music_ducked.wav is the mix input.
import subprocess, json, os, sys, numpy as np
ADV = 0 if '--no-latency-comp' in sys.argv else 240   # samples the mix.js stem is advanced (tools/mix.js limiter latency)

SRC = 'audio/music/mixkit/mixkit_1008.mp3'      # Pitbull (Michael Ramir C.)
HIT = 'audio/music/mixkit/mixkit_677.mp3'       # Epical Drums 02 (Grigoriy Nuzhny)
BRASS = 'audio/sfx/mixkit/mixkit_sfx_2285.wav'  # Orchestra triumphant trumpets (C5 power chord: C+G, no third)
SR = 48000
D = 30.0
XF = 0.050      # splice crossfade (s), ends 5 ms before the bar line so downbeat transients stay intact
PRE = 0.005
EPI_RATE = 0.9972   # Epical Drums 02 runs at 120.3 BPM (onset regression after the 58 s hit: period 0.4985-0.4987 s); resampled (asetrate, no time-stretch artefacts) to 120.000
os.makedirs('audio/_work', exist_ok=True)

def load(path, ch=1):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-ac', str(ch), '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True, check=True).stdout
    x = np.frombuffer(raw, dtype=np.float32).astype(np.float64)
    return x if ch == 1 else x.reshape(-1, ch)

def transient(x, t):
    """Attack start near t: first sample where the 1 ms envelope rises 25% of the way from the pre level to the peak."""
    k = int(0.001 * SR)
    env = np.convolve(np.abs(x[int((t - 0.08) * SR):int((t + 0.08) * SR)]), np.ones(k) / k, mode='same')
    t0 = t - 0.08
    i_pre = slice(int(0.02 * SR), int(0.05 * SR))
    i_win = slice(int(0.05 * SR), int(0.13 * SR))
    pre = np.median(env[i_pre]); pk = env[i_win].max()
    thr = pre + 0.25 * (pk - pre)
    j = int(0.05 * SR) + np.argmax(env[i_win] > thr)
    return t0 + j / SR

xs = load(SRC); xh = load(HIT)
T_DROP = transient(xs, 74.0)
T_HIT = transient(xh, 58.0)
d = T_DROP - 74.0          # grid offset of the source: bar lines at 2m + d
print(f'source drop transient {T_DROP:.4f}s (grid offset {d*1000:+.1f} ms); epical hit transient {T_HIT:.4f}s')

def S(t):
    return t + d  # grid time -> source time

# ------------------------------------------------------------------ brass stab: chop the sustained C5 power chord, pitch it
# with rubberband (formant preserved: the brass keeps its body) to Eb5 (+3 st) / Bb4 (-2 st), high-pass 180 Hz (the sub
# belongs to the 808), 8 ms attack (brass, not a click), 0.12 s hold, 0.4 s decay. rubberband keeps the timing (tempo 1).
xb = load(BRASS)
kb = int(0.005 * SR); eb_ = np.sqrt(np.convolve(xb ** 2, np.ones(kb) / kb, mode='same'))
ref = np.sqrt(np.mean(xb[int(0.75 * SR):int(1.05 * SR)] ** 2))
B0 = (int(0.55 * SR) + int(np.argmax(eb_[int(0.55 * SR):int(0.9 * SR)] > ref * 0.71))) / SR   # main chord within 3 dB of its body
STAB_LEN = 0.62
HALFWIDE = 'pan=stereo|c0=0.75*c0+0.25*c1|c1=0.25*c0+0.75*c1'   # M/S side x0.5: the hero-hit layers stay punchy in mono
def make_stab(semis, out):
    r = 2 ** (semis / 12)
    af = (f'aresample={SR},rubberband=pitch={r:.6f}:formant=preserved:transients=crisp,atrim=start={B0:.5f}:duration={STAB_LEN:.5f},asetpts=N/SR/TB,'
          f'{HALFWIDE},highpass=f=180,highpass=f=180,afade=t=in:st=0:d=0.008,'
          f"volume='if(lt(t,0.12),1,exp(-(t-0.12)/0.13))':eval=frame,afade=t=out:st={STAB_LEN - 0.06:.3f}:d=0.06")
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', BRASS, '-af', af, '-ac', '2', '-ar', str(SR), '-c:a', 'pcm_f32le', out], check=True)
    return out
STAB_EB = make_stab(+3, 'audio/_work/stab_eb5.wav')
STAB_BB = make_stab(-2, 'audio/_work/stab_bb4.wav')
for _old in ('audio/_work/stab_bb5.wav',):
    if os.path.exists(_old): os.remove(_old)
print(f'brass stab chopped at source {B0:.3f}s -> Eb5 (+3 st) / Bb4 (-2 st), rubberband formant-preserved')

def rms_db(x, a, b):
    s = x[int(a * SR):int(b * SR)]; return 20 * np.log10(np.sqrt(np.mean(s ** 2)) + 1e-12)
# stab level: 300 ms RMS sits 6 dB under the music it lands on (drop downbeat source window + drop gain)
xst = load(STAB_EB)
DROP_GAIN = 2.0
TD_SHELF_DB = -2.5  # final-hit slice below ~120 Hz (the slice is +2 dB like the drop; its sub sits under the drop's)
LIFT_GAIN = 2.0     # lift +2 dB (its energy is in the mids; its sub is shelved -3.5 dB so the touchdown out-punches 26.0 / 28.0)
stab_gain = (rms_db(xs, T_DROP, T_DROP + 0.3) + DROP_GAIN - 6.0) - rms_db(xst, 0, 0.3)
print(f'stab gain {stab_gain:+.1f} dB')

# ------------------------------------------------------------------ segments
# (out_start, out_end, src_start, label, fx, gain_db | gain_expr, fade_in, fade_out, input)
segs = []
LP = 'lowpass=f=650,lowpass=f=650'  # 2x 2-pole = 4-pole 650 Hz ("inside the groove"); bible: lowpass=f=650
# 0-6: intro bars (half-time sparse drums + bass), POV filtered -4 dB
segs.append(dict(out=(0.0, 6.0 - PRE), src=S(0.0), label='intro filtered (src 0-6)', fx=LP, gain=-4.0, fin=0.0, fout=0.25, inp=0))
# filter "snaps open": 6-frame crossfade (0.25 s) to the dry copy of the same intro material, landing on the 6.0 downbeat
segs.append(dict(out=(6.0 - 0.25 - PRE, 6.0 - PRE), src=S(6.0 - 0.25), label='intro dry (filter opening)', fx='', gain=0.0, fin=0.25 - XF, fout=XF, inp=0))
# 6-12: main groove A (src 18-24, the groove right after the track's first build)
segs.append(dict(out=(6.0 - PRE - XF, 12.0 - PRE), src=S(18.0) - PRE - XF, label='groove A (src 18-24)', fx='', gain=-2.0, fin=XF, fout=XF, inp=0))
# 12-17.5: the track's own 4-bar build (src 12-17.5), every-beat hits + rising sub, desert-space echo (bible 6.1 aecho; its
# 0.48 output gain is made up inside the ramp). Gain ramps +2.5 -> +6 dB across the build; over the last bar a 4-pole
# high-pass sweeps 30 -> 250 Hz (exponential) so the bass drains away and returns on the 18.0 drop.
B_OUT0 = 12.0 - PRE - XF
sweep = []
for k in range(151):
    tt = 16.0 + k * 0.01
    fc = 30.0 * (250.0 / 30.0) ** min(1.0, k / 150)
    sweep.append(f'{tt - B_OUT0:.3f} highpass@hpa f {fc:.1f}, highpass@hpb f {fc:.1f}')
BUILD_FX = ('aecho=0.8:0.6:60|120:0.2|0.12,asendcmd=c=\'' + ';'.join(sweep) + '\',highpass@hpa=f=20,highpass@hpb=f=20')
BUILD_GAIN = "volume='pow(10,(2.5+3.5*min(1,t/5.5))/20)':eval=frame"
segs.append(dict(out=(B_OUT0, 17.5), src=S(12.0) - PRE - XF, label='build (src 12-17.5) + aecho + gain ramp + HPF sweep', fx=BUILD_FX,
                 gain=0.0, gexpr=BUILD_GAIN, fin=XF, fout=0.02, inp=0))
# 17.5-18.0 silence
# 18-26: DROP (src 74-82: bass returns after the track's breakdown), +2 dB
segs.append(dict(out=(18.0 - 0.002, 26.0 - PRE), src=T_DROP - 0.002, label='DROP (src 74-82)', fx='', gain=DROP_GAIN, fin=0.002, fout=XF, inp=0))
# 26-29: lift (src 90-93, the track's loudest final section), +2 dB
# (its first downbeat carries a crash + kick that peaks 3.5 dB above any other bar of the edit: a 0.5 ms-attack limiter on
#  this segment shaves that one transient by ~4 dB so it does not set the whole edit's normalisation or hit the master limiter)
# touchdown VACUUM: over the push (28.25-28.75) a 4-pole high-pass sweeps 30 -> 300 Hz (exponential), then the music cuts at
# 28.75 (15 ms fade) and stays silent until the touchdown: 6 frames (f691-696) of held breath, like the 17.5 stop.
L_OUT0 = 26.0 - PRE - XF
VAC = (28.25, 28.75)
lsweep = []
for k in range(51):
    tt = VAC[0] + k * 0.01
    fc = 30.0 * (300.0 / 30.0) ** (k / 50)
    lsweep.append(f'{tt - L_OUT0:.3f} highpass@lha f {fc:.1f}, highpass@lhb f {fc:.1f}')
LIFT_FX = ('alimiter=limit=0.6:attack=0.5:release=40:level=false:latency=1,asendcmd=c=\'' + ';'.join(lsweep) +
           '\',highpass@lha=f=20,highpass@lhb=f=20')
segs.append(dict(out=(L_OUT0, VAC[1]), src=S(90.0) - PRE - XF, label='lift (src 90-92.75) + 30->300 Hz HPF sweep 28.25-28.75, cut at 28.75 (vacuum)',
                 fx=LIFT_FX, gain=LIFT_GAIN, fin=XF, fout=0.015, inp=0))
# 29.0-29.5: final hit = 0.5 s slice of the drop downbeat at the drop's own gain, hard cut at 29.5 (the drop stays the film's
# peak through its bigger SFX stack, not by turning the touchdown down)
segs.append(dict(out=(29.0 - 0.002, 29.5), src=T_DROP - 0.002, label='final hit (drop downbeat slice)', fx='', gain=DROP_GAIN, fin=0.002, fout=0.03, inp=0))
# Epical Drums 02: 58 s hit + its 8-bar percussion groove under the whole drop. HPF 140 Hz (4-pole): the sub belongs to the 808.
EPI_HP = 'highpass=f=140,highpass=f=140'
segs.append(dict(out=(18.0 - 0.002, 26.0 - PRE), src=T_HIT - 0.002 * EPI_RATE, label='epical hit + percussion groove (src 58-66) @18-26',
                 fx=EPI_HP, rate=EPI_RATE, gain=0.0, gexpr="volume='pow(10,(-5-4*min(1,max(0,(t-0.5)/0.5)))/20)':eval=frame",
                 fin=0.002, fout=XF, inp=1))
segs.append(dict(out=(29.0 - 0.002, 29.5), src=T_HIT - 0.002 * EPI_RATE, label='epical hit @29', fx=EPI_HP + ',' + HALFWIDE, rate=EPI_RATE, gain=-9.0,
                 fin=0.002, fout=0.03, inp=1))
# brass stabs (attack on the grid; the stab file starts with its 2 ms fade-in)
segs.append(dict(out=(18.0 - 0.002, 18.0 - 0.002 + STAB_LEN), src=0.0, label='brass stab Eb5 @18.0', fx='', gain=round(stab_gain, 2), fin=0, fout=0, inp=2))
segs.append(dict(out=(24.0 - 0.002, 24.0 - 0.002 + STAB_LEN), src=0.0, label='brass stab Bb4 @24.0 (disc spin)', fx='', gain=round(stab_gain - 2.5, 2), fin=0, fout=0, inp=3))
segs.append(dict(out=(29.0 - 0.002, 29.5), src=0.0, label='brass stab Eb5 @29.0 (= the 18.0 stab level)', fx='', gain=round(stab_gain, 2), fin=0, fout=0.03, inp=2))
INPUTS = [SRC, HIT, STAB_EB, STAB_BB]
NAMES = ['Pitbull', 'Epical Drums 02', 'Orchestra triumphant trumpets (Eb5 stab)', 'Orchestra triumphant trumpets (Bb4 stab)']

def build(segs, out_path, dry=False):
    chains = []
    for i, s in enumerate(segs):
        o0, o1 = s['out']
        dur = o1 - o0
        src0 = s['src']
        delay = o0
        if src0 < 0:
            delay -= src0; dur += src0; src0 = 0.0
        r = s.get('rate', 1.0)
        f = [f'atrim=start={src0:.6f}:duration={dur * r:.6f}', 'asetpts=N/SR/TB']
        if r != 1.0: f += [f'asetrate={round(SR * r)}', f'aresample={SR}', 'asetpts=N/SR/TB']
        if s['fx'] and not dry: f.append(s['fx']); f.append(f'atrim=duration={dur:.6f}')
        if s['fin'] > 0: f.append(f'afade=t=in:st=0:d={s["fin"]:.4f}')
        if s['fout'] > 0: f.append(f'afade=t=out:st={dur - s["fout"]:.6f}:d={s["fout"]:.4f}')
        if not dry:
            if s.get('gexpr'): f.append(s['gexpr'])
            if s['gain']: f.append(f'volume={s["gain"]}dB')
        ds = int(round(delay * SR))
        if ds > 0: f.append(f'adelay=delays={ds}S:all=1')
        f.append(f'apad=whole_len={int(D*SR)}'); f.append(f'atrim=end_sample={int(D*SR)}')
        f.insert(0, f'aresample={SR},aformat=sample_fmts=fltp:channel_layouts=stereo')
        chains.append(f'[{i}:a]' + ','.join(f) + f'[s{i}]')
    inputs = []
    for s_ in segs: inputs += ['-i', INPUTS[s_['inp']]]
    graph = ';'.join(chains) + ';' + ''.join(f'[s{i}]' for i in range(len(segs))) + f'amix=inputs={len(segs)}:normalize=0:duration=longest,atrim=end_sample={int(D*SR)}[out]'
    subprocess.run(['ffmpeg', '-y', '-v', 'error', *inputs, '-filter_complex', graph, '-map', '[out]', '-ar', str(SR), '-c:a', 'pcm_f32le', out_path], check=True)
    return graph

# two stems: the Pitbull track (gets the above-150 Hz duck) and the hybrid layers (Epical, brass stabs: never ducked)
raw_p = 'audio/_work/music_edit_raw_pitbull.wav'; raw_l = 'audio/_work/music_edit_raw_layers.wav'
graph = build([s for s in segs if s['inp'] == 0], raw_p)
graph_l = build([s for s in segs if s['inp'] != 0], raw_l)
open('audio/_work/music_edit_graph.txt', 'w').write(graph.replace(';', ';\n') + '\n\n# layers\n' + graph_l.replace(';', ';\n'))
if os.path.exists('audio/_work/music_edit_raw.wav'): os.remove('audio/_work/music_edit_raw.wav')   # v2 single-stem name
def dec2(p):
    y = subprocess.run(['ffmpeg', '-v', 'error', '-i', p, '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-'], capture_output=True, check=True).stdout
    return np.frombuffer(y, dtype=np.float32).reshape(-1, 2).astype(np.float64)
yp = dec2(raw_p); yl = dec2(raw_l)
# HERO-HIT CONTRAST (zero-phase low shelf on the Pitbull track, below ~120 Hz): the drop bar (18.0-18.6) and the touchdown
# slice keep the full 808 + kick; the rest of the drop groove sits 1.5 dB lower in the sub and the lift 2.5 dB lower, so the
# drop and touchdown downbeats are the heaviest low end of the film (the master limiter caps how loud they can get, so the
# contrast has to come from the groove around them). Raised-cosine transitions, per sample; applied to music_edit.wav too.
def shelf_curve(n):
    t = np.arange(n) / SR; c = np.ones(n); G1 = 10 ** (-1.5 / 20); G2 = 10 ** (-3.5 / 20)
    def ramp(a, b, g0, g1):
        r = (t >= a) & (t < b); c[r] = g0 + (g1 - g0) * 0.5 * (1 - np.cos(np.pi * (t[r] - a) / (b - a)))
    ramp(18.6, 18.9, 1.0, G1); c[(t >= 18.9) & (t < 25.9)] = G1
    ramp(25.9, 25.99, G1, G2); c[(t >= 25.99) & (t < 28.9)] = G2
    c[t >= 28.9] = 10 ** (TD_SHELF_DB / 20)   # touchdown slice: its sub is carried by the touchdown boom (the needle landing), not the callback
    return c
F = np.fft.rfftfreq(len(yp), 1 / SR)
LP120 = 1 / (1 + (F / 120.0) ** 4)
lowp = np.fft.irfft(np.fft.rfft(yp, axis=0) * LP120[:, None], len(yp), axis=0)
yp = yp + (shelf_curve(len(yp)) - 1)[:, None] * lowp
y = yp + yl
# peak-normalise to -1.0 dBFS sample peak (keeps all dynamics), write 24-bit
pk = float(np.abs(y).max())
g = -1.0 - 20 * np.log10(pk)
print(f'raw peak {20*np.log10(pk):+.2f} dBFS -> gain {g:+.2f} dB')
def write24(arr, path):
    pcm = np.clip(np.round(arr * 8388607), -8388608, 8388607).astype('<i4')
    b = pcm.reshape(-1).view(np.uint8).reshape(-1, 4)[:, :3].tobytes()
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 's24le', '-ar', str(SR), '-ac', '2', '-i', '-', '-c:a', 'pcm_s24le', path], input=b, check=True)
gl = 10 ** (g / 20)
write24(y * gl, 'audio/music_edit.wav')
# the bible's -3 dB ducks under the 18.0 and 29.0 impacts, on the Pitbull track ABOVE 150 Hz only:
#   ducked = pit + (d(t) - 1) * HP150(pit) + layers,  HP150 = zero-phase 4th-order (LR4 magnitude) high-pass via FFT,
#   d(t) = 0.708 over 17.998-18.5 then a 150 ms raised-cosine recovery; -4.5 dB over 28.998-29.5 (the music cuts at 29.5).
# Below ~100 Hz the gain stays within 0.2 dB of unity and the phase is untouched (the kick and the 808 keep full weight).
def duck_curve(n):
    t = np.arange(n) / SR; d = np.ones(n); DK = 10 ** (-3 / 20)
    d[(t >= 17.998) & (t < 18.5)] = DK
    r = (t >= 18.5) & (t < 18.65); d[r] = DK + (1 - DK) * 0.5 * (1 - np.cos(np.pi * (t[r] - 18.5) / 0.15))
    d[(t >= 28.998) & (t < 29.5)] = 10 ** (-4.5 / 20)   # touchdown: 4.5 dB, so the drop stays the loudest moment
    return d
H = (F / 150.0) ** 4 / (1 + (F / 150.0) ** 4)
hp = np.fft.irfft(np.fft.rfft(yp, axis=0) * H[:, None], len(yp), axis=0)
dk = duck_curve(len(yp))
yd = (yp + (dk - 1)[:, None] * hp + yl) * gl
write24(yd, 'audio/_work/music_ducked.wav')
# mix.js stem: the same ducked music, advanced by 240 samples: tools/mix.js's alimiter delays its output by 5 ms (latency not
# compensated), so the stem is shifted early to land on time
yd_adv = np.concatenate([yd[ADV:], np.zeros((ADV, 2))])
write24(yd_adv, 'audio/_work/music_stem_mixjs.wav')
if os.path.exists('audio/music_stem_mixjs.wav'): os.replace('audio/music_stem_mixjs.wav', 'audio/_work/v2/music_stem_mixjs.wav')   # round-2 location (wrong-file risk next to mix.wav)
if os.path.exists('audio/music_stem.wav'): os.remove('audio/music_stem.wav')   # v1 name (renamed: it is advanced 240 samples, mix.js only)
json.dump(dict(source=SRC, layer=HIT, brass=BRASS, bpm=120.0, key='Eb minor (bass/mid chroma peak D#; stabs Eb5 / Bb4 power chords, rubberband formant-preserved)',
               duck='Pitbull track above 150 Hz only: -3 dB 17.998-18.5 (+150 ms cosine recovery) and -4.5 dB 28.998-29.5; layers never ducked; in audio/_work/music_ducked.wav (mix input) only',
               vacuum='lift HPF 30->300 Hz over 28.25-28.75, music silent 28.75-28.998',
               low_shelf='Pitbull below ~120 Hz (zero-phase): 0 dB to 18.6, -1.5 dB 18.9-25.9, -3.5 dB 26.0-28.9 (lift, +2 dB overall), -2.5 dB final hit (its sub comes from the touchdown boom)',
               grid_offset_s=d, src_drop_transient=T_DROP, hit_transient=T_HIT, epical_rate=EPI_RATE, brass_chop_s=B0, normalise_gain_db=g,
               segments=[dict(label=s['label'], out=[round(s['out'][0], 4), round(s['out'][1], 4)], src_start=round(s['src'], 4), rate=s.get('rate', 1.0),
                              fx=('aecho + 30->250 Hz HPF sweep 16.0-17.5' if s['fx'] == BUILD_FX else 'alimiter (26.0 crash) + 30->300 Hz HPF sweep 28.25-28.75' if s['fx'] == LIFT_FX else s['fx']), gain_db=s['gain'], gain_expr=s.get('gexpr', ''),
                              input=NAMES[s['inp']], input_file=INPUTS[s['inp']]) for s in segs]),
          open('audio/music_edit_map.json', 'w'), indent=1)
print('EDIT_OK')
