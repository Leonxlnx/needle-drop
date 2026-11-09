# NEEDLE DROP SFX prep + cue sheet (bible 6.2 / 6.3).
# Usage (project root as cwd): python -I audio/scripts/build_cues.py [--no-latency-comp]
# 1. Prepares every SFX clip with ffmpeg into audio/sfx/prep/<cue>.wav (trim, reverse, filters, baked volume automation, fades).
#    Clips are pre-trimmed so cues.json never needs "offset" (tools/mix.js misplaces clips that use offset>0 together with at>0
#    under ffmpeg 8.0.1: atrim start>0 + asetpts + adelay + atrim drops the delay; verified with a test cue).
# 2. Levels every clip to a target loudness (EBU R128 integrated for beds/whooshes, 400 ms RMS peak for hits).
# 3. Writes audio/cues.json for tools/mix.js (music stem + all SFX with at / gain / fades / rate for pitch-down / pan).
# v2 (art-director round 1):
#  - crackle bed = REAL vinyl surface noise (freesound CC0 #637931 "vinyl record crackle nice stereo", kyles) plus a
#    revolution tick every 1.8 s (one turn at 33 1/3 rpm) cut from a locked-groove recording (freesound CC0 #838458
#    "Vinyl Crackle Infinite Groove 03", hardcore scm); replaces the campfire/radio-static stand-in.
#  - impact group (drop, front pass, touchdown) -5 dB; every impact layer except the two sub booms high-passed at 140 Hz
#    (4-pole); the sub booms are fed from ONE channel (no decorrelated / anti-phase low end, mono-safe) with +3 dB make-up;
#    front_whoosh_impact keeps its stereo top but its low band (<140 Hz) is fed from one channel.
#  - 12.0 transition (reverse_cymbal, cut_thump) -4 dB; front_pass_wind +0.30 s; drop_crack trimmed to its loudest
#    transient so the crack lands on 18.000; sand_hiss audible (grows 12 -> 17.4 s) and fires only on validated kicks.
# v3 (art-director round 2):
#  - HERO HITS: every sub layer is polarity- and time-aligned to the Pitbull kick it lands on (align_low: searches
#    polarity +-1 and +-5 ms for the largest 30-120 Hz RMS over [t, t+0.15] of music + layers); a real sub drum
#    (Mixkit #2294 "Drum bass hit", pitched Eb1 = the key's root) doubles the kick on 18.0 and 29.0; both booms +6/+5 dB.
#  - drop_crack = Mixkit #2599 "Heavy electric shockwave impact" (silence before a bright crack) trimmed so its loudest
#    5 ms lands on 18.000-18.010; roar re-trimmed so its peak lands on 18.95-19.00, hard-cut at 19.05 (30 ms fade).
#  - build vacuum: sub_rumble gets the music's 30 -> 250 Hz 4-pole high-pass sweep over 16.0-17.5 (the sub drains away).
#  - touchdown: arm servo/creak stop at 28.75, the hydraulic downwash swells and hard-stops at 28.99 (20 ms), a reversed
#    vinyl-crackle swell ends at 28.995 (the music is silent 28.75-28.998).
#  - crackle bed narrowed in M/S (side x0.3) and the revolution tick is mono (centre): mono-safe on a phone speaker.
#  - LEVELS were set against the master limiter (hero_check.py): raising the booms +6 dB as asked put 7 dB of limiting on the
#    drop and flattened it; the aligned sub drum carries the punch, the boom sits 1 dB under v2 (now ADDING, not cancelling),
#    the crack -5 dB / explosion -2 dB (their highs rode on the kick's peak), the touchdown 1 dB under the drop.
#  - hook: an already-moving low air rush from 0.0 (Mixkit #1484 -5 st, LPF 2 kHz) and a sub thunk under the needle (#2294).
#  - disc_grind swells to ~25.0 and is gone by 26.0; disc_spinup gone by 26.0 (shadow_drone owns 26-27).
import os, sys, json, subprocess, re, numpy as np

SR = 48000
MK = 'audio/sfx/mixkit/mixkit_sfx_{}.wav'
FS = 'audio/sfx/freesound/fs_{}.mp3'          # freesound CC0 HQ previews (downloadable without login)
HP140 = 'highpass=f=140,highpass=f=140'       # impact layers: the sub belongs to the two booms only
MONO = 'pan=stereo|c0=c0|c1=c0'               # single-channel feed (avoids comb cancellation of an L+R sum)
NARROW = 'pan=stereo|c0=0.65*c0+0.35*c1|c1=0.35*c0+0.65*c1'   # M/S: mid x1, side x0.3 (crackle: mono-safe, corr > +0.3)
CENTRE = 'pan=stereo|c0=0.5*c0+0.5*c1|c1=0.5*c0+0.5*c1'   # mono, centre
INVERT = "aeval='-val(0)|-val(1)'"
HALFWIDE = 'pan=stereo|c0=0.75*c0+0.25*c1|c1=0.25*c0+0.75*c1'   # M/S side x0.5 (touchdown sand burst: mono-safer top end)
PREP = 'audio/sfx/prep'
os.makedirs(PREP, exist_ok=True)
st = lambda semis: round(2 ** (semis / 12), 6)      # semitones -> rate

def decode(path):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-ac', '2', '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64)

def loud_I(path):
    eb = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', path, '-af', 'ebur128', '-f', 'null', '-'], capture_output=True, text=True).stderr
    v = re.findall(r'I:\s+(-?[\d.]+|-inf) LUFS', eb)
    return float(v[-1]) if v and v[-1] != '-inf' else -70.0

def rms400_max(x):
    m = x.mean(1); w = int(0.4 * SR)
    if len(m) < w: return 20 * np.log10(np.sqrt((m ** 2).mean()) + 1e-12)
    c = np.cumsum(np.concatenate([[0], m ** 2]))
    r = (c[w:] - c[:-w]) / w
    return 10 * np.log10(r.max() + 1e-12)

def prep(name, src, start=0.0, end=None, reverse=False, af='', fade_in=0.0, fade_out=0.0, extra=None, mono_low=None, invert=False):
    """Trim [start,end) of src (seconds, original speed), optional reverse, filters, fades -> 48 kHz stereo 24-bit.
    mono_low=fc: Linkwitz-Riley (2x2-pole) split at fc; the low band is fed from the left channel only, the top stays stereo."""
    out = f'{PREP}/{name}.wav'
    f = [f'aresample={SR}', 'aformat=sample_fmts=fltp:channel_layouts=stereo']
    f.append(f'atrim=start={start:.6f}' + (f':end={end:.6f}' if end is not None else ''))
    f.append('asetpts=N/SR/TB')
    if reverse: f.append('areverse')
    if af: f.append(af)
    if extra: f.append(extra)
    if invert: f.append(INVERT)
    x = decode(src)
    dur = (end if end is not None else len(x) / SR) - start
    g = []
    if fade_in: g.append(f'afade=t=in:st=0:d={fade_in:.4f}')
    if fade_out: g.append(f'afade=t=out:st={max(0, dur - fade_out):.6f}:d={fade_out:.4f}')
    if mono_low:
        fc = mono_low
        graph = (f'[0:a]{",".join(f)},asplit=2[a][b];[a]lowpass=f={fc},lowpass=f={fc},{MONO}[l];[b]highpass=f={fc},highpass=f={fc}[h];'
                 f'[l][h]amix=inputs=2:normalize=0' + (',' + ','.join(g) if g else '') + '[o]')
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', src, '-filter_complex', graph, '-map', '[o]', '-ar', str(SR), '-ac', '2', '-c:a', 'pcm_s24le', out], check=True)
    else:
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', src, '-af', ','.join(f + g), '-ar', str(SR), '-ac', '2', '-c:a', 'pcm_s24le', out], check=True)
    return out

def attack(src, t_guess, win=0.06):
    """Attack start near t_guess (first ms within 24 dB of the local peak)."""
    x = decode(src).mean(1)
    a = max(0, int((t_guess - win) * SR)); seg = x[a:int((t_guess + win) * SR)]
    k = int(0.001 * SR); env = 20 * np.log10(np.sqrt(np.convolve(seg ** 2, np.ones(k) / k, mode='same')) + 1e-12)
    j = int(np.argmax(env > env.max() - 24))
    return (a + j) / SR

# ---- low-end alignment (hero hits): render cues as the master does (rate, dur, gain, sample delay) into a mono timeline
def lowband(x, lo=30.0, hi=120.0):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR); X[(f < lo) | (f >= hi)] = 0
    return np.fft.irfft(X, len(x))
_MUS = {}
def music_mono():
    if 'x' not in _MUS: _MUS['x'] = decode('audio/music_edit.wav').mean(1)
    return _MUS['x']
def render(c, a, b, dt=0.0, pol=1.0):
    x = decode(c['file']).mean(1); r = c.get('rate', 1) or 1
    n = int(len(x) / r); y = np.interp(np.arange(n) * r, np.arange(len(x)), x) if r != 1 else x.copy()
    if c.get('dur') is not None: y = y[:int(c['dur'] * SR)]
    y = y * 10 ** (c['gain_db'] / 20) * pol
    out = np.zeros(int(round((b - a) * SR))); st = int(round((c['at'] + LAT + dt - a) * SR))
    i0 = max(0, -st); i1 = min(len(y), len(out) - st)
    if i1 > i0: out[st + i0:st + i1] = y[i0:i1]
    return out
def low_rms(sig, a, t0, w=0.15):
    i = int(round((t0 - a) * SR)); s = sig[i:i + int(w * SR)]; return 10 * np.log10(np.mean(s ** 2) + 1e-20)
def best50(sig, a, t0):
    i0 = int(round((t0 - 0.02 - a) * SR)); W = int(0.05 * SR)
    return max(10 * np.log10(np.mean(sig[i:i + W] ** 2) + 1e-20) for i in range(i0, i0 + int(0.22 * SR), 24))
ALIGN_LOG = []
def align_low(c, t0, base_cues=(), search_ms=5.0, prep_args=None, t_min=None):
    """Choose polarity and a +-search_ms nudge of cue c so the 30-120 Hz RMS over [t0, t0+0.15] of music + base_cues + c is
    maximal (the layers ADD to the kick instead of cancelling it). Re-preps the clip inverted if needed; returns c."""
    a, b = t0 - 0.5, t0 + 0.7
    i0 = int(round(a * SR)); base = music_mono()[i0:i0 + int(round((b - a) * SR))].copy()
    for bc in base_cues: base += render(bc, a, b)
    lb = lowband(base); ref = low_rms(lb, a, t0)
    y0 = lowband(render(c, a, b))
    best = None
    for pol in (1.0, -1.0):
        lo_ms = -search_ms if t_min is None else max(-search_ms, (t_min - (c['at'] + LAT)) * 1000)
        for dt in np.arange(lo_ms, search_ms + 1e-9, 0.25) / 1000:
            k = int(round(dt * SR)); y = np.roll(y0, k) * pol
            v = low_rms(lb + y, a, t0)
            if best is None or v > best[0]: best = (v, pol, dt)
    v0 = low_rms(lb + y0, a, t0); own = low_rms(y0, a, t0)
    psum = 10 * np.log10(10 ** (ref / 10) + 10 ** (own / 10))
    _, pol, dt = best
    if pol < 0 and prep_args is not None:
        prep(**prep_args, invert=True)
    elif pol < 0:
        raise RuntimeError('inversion needs prep_args')
    c['at'] = round(c['at'] + dt, 6)
    yb = np.roll(y0, int(round(dt * SR))) * pol
    rec = dict(cue=c['name'], t0=t0, polarity=int(pol), nudge_ms=round(dt * 1000, 2), base_low150=round(ref, 2), layer_low150=round(own, 2),
               power_sum=round(psum, 2), as_was=round(v0, 2), aligned=round(best[0], 2),
               base_best50=round(best50(lb, a, t0), 2), aligned_best50=round(best50(lb + yb, a, t0), 2))
    c['_align'] = rec; ALIGN_LOG.append(rec)
    print(f"align {c['name']:18s} @{t0}: polarity {int(pol):+d}, nudge {dt*1000:+.2f} ms | 30-120 Hz 150 ms: base {ref:.1f}, layer {own:.1f}, "
          f"power sum {psum:.1f}, unaligned {v0:.1f} -> aligned {best[0]:.1f} dB | best 50 ms {rec['base_best50']:.1f} -> {rec['aligned_best50']:.1f}")
    return c

beats = json.load(open('data/beats.json'))
kicks = beats['kicks']
cues = []

def cue(name, file, at, target, mode='I', rate=1.0, fade_in=0.0, fade_out=0.0, dur=None, pan=0.0, note=''):
    """target: dB (LUFS-I if mode=='I', 400 ms RMS peak dBFS if mode=='hit'). Gain is measured on the prepared clip."""
    x = decode(file)
    if mode == 'abs': lvl = 0.0
    else: lvl = loud_I(file) if mode == 'I' else rms400_max(x) if mode == 'hit' else 20 * np.log10(np.abs(x).max() + 1e-12)
    if mode == 'I' and lvl <= -69: lvl = rms400_max(x); mode = 'hit'
    g = round(target - lvl, 2)
    at_in = max(0.0, at - LAT)
    c = dict(name=name, file=file.replace('\\', '/'), at=round(at_in, 5), offset=0, dur=dur, gain_db=g, fade_in=fade_in, fade_out=fade_out, pan=pan, rate=rate)
    c['_level'] = dict(mode=mode, measured=round(lvl, 2), target=target)
    if note: c['note'] = note
    cues.append(c)
    return c

LAT = 0.0 if '--no-latency-comp' in sys.argv else 240 / SR   # pass --no-latency-comp once tools/mix.js uses alimiter latency=1; tools/mix.js alimiter adds 5 ms latency (240 samples, measured by cross-correlation); every cue is placed 5 ms early
PRE = 0.001   # pre-roll kept before each hit's attack (seconds, original speed)

# ------------------------------------------------------------------ 0.0 needle drop + crackle bed (loops seamlessly 30.0 -> 0.0)
# crackle bed = real vinyl surface noise (freesound CC0 #637931, kyles, recorded in stereo), rumble removed (HPF 300 Hz),
# + one revolution tick every 1.8 s (33 1/3 rpm) cut from a locked-groove recording (freesound CC0 #838458, hardcore scm:
# its groove repeats every 1.724 s; revolution 12's tick at 21.766 s has 12 dB contrast). Ticks peak 5 dB above the bed's
# capped pops, at loop times 0.75 + 1.8 n -> film 29.75 (in the black), 1.55, 3.35, 5.15, 6.95, 8.75, 10.55.
for _f in ('_crackle_pops', '_crackle_hiss'):
    if os.path.exists(f'{PREP}/{_f}.wav'): os.remove(f'{PREP}/{_f}.wav')   # v1 stand-in (campfire / radio static)
bed0 = prep('_crackle_bed_raw', FS.format(637931), 2.0, 15.4, af='highpass=f=300,highpass=f=300,lowpass=f=12000,' + NARROW)
_xb = decode(bed0); G_BED = -30.0 - 20 * np.log10(np.sqrt(np.mean(_xb ** 2)))
# de-pop: the recording has rare pops ~35 dB over its surface noise (they hit the master limiter); cap every click at
# 18 dB over the bed RMS (bed normalised to -30 dBFS RMS, 0.1 ms-attack limiter at -12 dBFS): crisp, never glitchy
bed = prep('_crackle_bed', bed0, 0.0, None, af=f'volume={G_BED:.2f}dB,alimiter=limit=0.25:attack=0.1:release=8:level=false:latency=1')
T_TICK = 21.766
tick = prep('_rev_tick', FS.format(838458), T_TICK - 0.04, T_TICK + 0.08, af='highpass=f=400,highpass=f=400,' + CENTRE, fade_in=0.004, fade_out=0.03)
def env1ms(x):
    m = x.mean(1); k = int(0.001 * SR); return np.sqrt(np.convolve(m ** 2, np.ones(k) / k, mode='same'))
bed_p = 20 * np.log10(np.percentile(env1ms(decode(bed)), 99.5)); tick_p = 20 * np.log10(env1ms(decode(tick)).max())
tick_sp = 20 * np.log10(np.abs(decode(tick)).max())
g_tick = -5.0 - tick_sp     # tick sample peak 7 dB above the capped pops (the loudest, regular click = the revolution; mono, centre)
TICKS = [0.75 + 1.8 * n for n in range(7)]
loop = 'audio/sfx/prep/_crackle_loop.wav'
ins = ['-i', bed] + sum([['-i', tick] for _ in TICKS], [])
gr = ''.join(f'[{i + 1}:a]volume={g_tick:.2f}dB,adelay=delays={int(round(t * SR))}S:all=1[t{i}];' for i, t in enumerate(TICKS))
gr += '[0:a]' + ''.join(f'[t{i}]' for i in range(len(TICKS))) + f'amix=inputs={len(TICKS) + 1}:normalize=0:duration=first[o]'
subprocess.run(['ffmpeg', '-y', '-v', 'error', *ins, '-filter_complex', gr, '-map', '[o]', '-c:a', 'pcm_s24le', loop], check=True)
print(f'crackle bed: 99.5th pct click {bed_p:.1f} dBFS, revolution tick gain {g_tick:+.1f} dB')
# film 29.0-30.0 uses loop[0,1); film 0.0-12.0 uses loop[1,13): the black at 30.0 runs straight into frame 1.
# Bible: "crackle bed loops at about -30 LUFS, dips at 6.0, gone by 12.0" -> baked volume automation (6.0: -6 dB over 0.25 s, fade to 0 by 12.0)
head = prep('crackle_head_0_12', loop, 1.0 + LAT, 13.0 + LAT,
            extra="volume='if(lt(t,5.9),1,if(lt(t,6.15),1-0.5*(t-5.9)/0.25,0.5*max(0,(12-t)/5.85)))':eval=frame")
tail = prep('crackle_tail_29_30', loop, 0.0, 1.0)
cue('crackle_head', head, 0.0, -30.5, note='vinyl surface noise + 1.8 s revolution tick, 0-12 s (dips at 6.0, gone by 12.0); continuous with crackle_tail across the loop')
cue('crackle_tail', tail, 29.0, -30.5 + 0.0, note='crackle through the black (29.0-30.0); loop[0,1) -> head starts at loop[1,..)')
cues[-1]['gain_db'] = cues[-2]['gain_db']   # identical gain on both halves of the loop (seamless)
a701 = attack(MK.format(701), 0.036)
needle = prep('needle_drop', MK.format(701), a701 - PRE, None)
cue('needle_tick_0', needle, 0.0, -7.0, mode='peak', note='Mixkit "Record player needle drop on vinyl"; this exact file returns at 29.0 pitched -12 st')
# hook (frame 1 must land on a muted social feed too): a sub thunk under the needle (real sub drum, Eb1 = the key's root,
# 15 dB under the needle tick) and an already-moving low air rush from 0.0 (the camera is doing 12 m/s on frame 1)
a2294 = attack(MK.format(2294), 0.01)
thunk = prep('needle_thunk', MK.format(2294), a2294 - PRE, a2294 + 0.9, fade_out=0.4)
cue('needle_thunk', thunk, 0.0, -22.0, mode='peak', note='Mixkit "Drum bass hit" (Eb1): sub body under the 0.00 needle drop')
cue('air_rush', prep('air_rush', MK.format(1484), 0.50, 2.05, af='lowpass=f=2000,lowpass=f=2000,highpass=f=50', fade_in=0.03), 0.0, -26.0,
    rate=st(-5), fade_out=0.7, dur=2.05, note='Mixkit "Speeding swoosh" from its loudest point, -5 st, LPF 2 kHz: already moving on frame 1, hands over to the canyon wind / lint whoosh')
# ... carried by a long sweeping air swoosh (-5 st, LPF 2 kHz) that peaks ~1.35 s and hands over to the lint whoosh (peak 2.0)
cue('air_swoosh', prep('air_swoosh', MK.format(167), 0.2, 1.75, af='lowpass=f=2000,lowpass=f=2000,highpass=f=50', fade_in=0.25, fade_out=0.35), 0.15, -27.0,
    rate=st(-5), note='Mixkit "Long sweeping air swoosh" -5 st, LPF 2 kHz: keeps the 12 m/s flight audible 0.4-1.8 s')

# ------------------------------------------------------------------ S1 groove canyon
cue('canyon_wind', prep('canyon_wind', MK.format(1267), 3.0, 8.4, af='lowpass=f=2000,lowpass=f=2000,highpass=f=40'), 0.0, -33.0,
    fade_in=0.4, fade_out=0.45, dur=5.4, note='deep canyon wind, LPF 2 kHz; ends on the 5.0 hidden cut')
# lint pass-under whoosh (-5 st), peak on the lint pass (timing.json lint_pass)
tm = json.load(open('data/timing.json'))['events']
t_lint = (tm['lint_pass']['frame'] - 1) / 24
lw = prep('lint_whoosh', MK.format(2604), 0.0, 2.2, fade_out=0.6)
cue('lint_whoosh', lw, t_lint - 0.488 / st(-5), -28.0, rate=st(-5), note='Mixkit "Deep air woosh" -5 st, peak on lint_pass')
# crystal resonance swell (-12 st): reversed crystal chime, its attack lands exactly on the 4.0 vault downbeat
a3108 = attack(MK.format(3108), 0.067)
cs = prep('crystal_swell_rev', MK.format(3108), a3108 - PRE, 2.0, reverse=True, fade_in=0.3)
L = 2.0 - (a3108 - PRE)
cue('crystal_swell', cs, 4.0 - (L - PRE) / st(-12), -25.0, rate=st(-12), note='Mixkit "Crystal chime" reversed, -12 st: swells 0.6-4.0 s into the vault')
cue('metal_scrape', prep('metal_scrape', MK.format(809), 0.0, 1.0, fade_out=0.35), 3.30, -29.0, rate=st(-12), note='Mixkit "Metal Scrape" -12 st')
# big rising whoosh (the vault), crest at 4.75
cue('vault_whoosh', prep('vault_whoosh', MK.format(2623), 1.75, 3.2, fade_in=0.15, fade_out=0.45), 4.0 - 0.1, -24.0,
    note='Mixkit "Ghostly whoosh passing" rising section, peak ~4.75 (crest)')
a1485 = attack(MK.format(1485), 0.018)
cue('metal_swish', prep('metal_swish', MK.format(1485), a1485 - PRE, None, af='highpass=f=400'), 4.80 - PRE, -29.0, mode='I',
    note='Mixkit "Metal hit woosh", quiet, on the cantilever')
# reverse air pull 5.0-6.0, peaks into the 6.0 filter-open downbeat
rp = prep('reverse_pull', MK.format(1471), 0.0, 1.45, reverse=True, fade_in=0.2)
cue('reverse_pull', rp, 6.0 - (1.45 - 0.433) - 0.02, -24.0, dur=1.05, fade_out=0.05, note='Mixkit "Cinematic wind swoosh" reversed: air pulls back into the 6.0 downbeat')

# ------------------------------------------------------------------ S2 machine
cue('motor_hum', prep('motor_hum', MK.format(1837), 4.0, 10.2, af='highpass=f=40,lowpass=f=1800'), 6.0, -38.0, fade_in=0.25, fade_out=0.5, dur=6.0,
    note='Mixkit "Refrigerator hum" as the turntable motor, very low and dry')
cue('neon_buzz', prep('neon_buzz', MK.format(2132), 2.0, 8.2, af='highpass=f=120,lowpass=f=6000'), 6.0, -42.0, fade_in=0.4, fade_out=0.5, dur=6.0,
    note='Mixkit "Low electricity humming" as the strobe lamp buzz')
cue('vortex', prep('vortex', MK.format(2667), 0.3, 2.3, fade_in=1.4, fade_out=0.04), 10.0, -27.0, note='Mixkit "Intense swell phasing spinning": the capture spin, rising into 12.0')
# reverse "cymbal": the bright decay of Mixkit "Epic impact afar explosion" reversed, high-passed; its (reversed) attack ends exactly at 12.0
a2782 = attack(MK.format(2782), 0.0, win=0.03)
rc = prep('reverse_cymbal', MK.format(2782), a2782, a2782 + 2.2, reverse=True, af='highpass=f=900,highpass=f=900', fade_in=0.8)
cue('reverse_cymbal', rc, 12.0 - 2.2, -29.0, note='reverse crash swell ending exactly on the 12.0 match cut')

# ------------------------------------------------------------------ S3 desert
a498 = attack(MK.format(498), 0.042)
cue('cut_thump', prep('cut_thump', MK.format(498), a498 - PRE, a498 + 2.4, af='lowpass=f=900', fade_out=0.8), 12.0 - PRE, -25.0, mode='hit',
    note='Mixkit "Deep heartbeat impact", soft deep thump on the 12.0 cut')
cue('desert_wind', prep('desert_wind', MK.format(2490), 2.0, 7.6, af='highpass=f=60,lowpass=f=5000'), 12.0, -31.0, fade_in=0.6, fade_out=0.03, dur=5.5,
    note='Mixkit "Wind in a desolate world"; hard stop at 17.5')
# sand hiss on every detected kick 12.0-17.5 (-20 dB under the music), growing with the riser from 14.0
a1494 = attack(MK.format(1494), 0.006)
sh = prep('sand_hiss', MK.format(1494), a1494 - PRE, a1494 + 0.42, af='highpass=f=1500,lowpass=f=9000,lowpass=f=9000', fade_out=0.25)   # LPF: grainy sand, not air (and no intersample overs)
n = 0
for k in kicks:
    t = k['t']
    if not (12.0 <= t < 17.4): continue
    grow = 0.0 if t < 14.0 else 6.0 * (t - 14.0) / 3.4
    c = cue(f'sand_hiss_{n:02d}', sh, t - PRE, -25.0 + 4 * (k['strength'] - 0.8) + grow, dur=min(0.42, 17.5 - t), fade_out=0.03 if t > 17.0 else 0,
            pan=round(float(np.sin(n * 2.4)) * 0.35, 2), note=f'kick ring {t:.3f}s strength {k["strength"]}')
    n += 1
# the music's build sweep (edit_music.py): 4-pole high-pass 30 -> 250 Hz (exponential) over 16.0-17.5, so the rumble's sub
# drains away with the music's and the bass only comes back on the 18.0 drop (clip time 0 = film 14.0)
_rs = ';'.join(f'{2.0 + k * 0.01:.3f} highpass@rha f {30.0 * (250.0 / 30.0) ** (k / 150):.1f}, highpass@rhb f {30.0 * (250.0 / 30.0) ** (k / 150):.1f}' for k in range(151))
RUMBLE_SWEEP = f"asendcmd=c='{_rs}',highpass@rha=f=20,highpass@rhb=f=20"
cue('sub_rumble', prep('sub_rumble', MK.format(1718), 2.0, 5.6, af='lowpass=f=300,lowpass=f=300', extra=RUMBLE_SWEEP), 14.0, -25.0, fade_in=3.0, fade_out=0.02, dur=3.5,
    note='Mixkit "Rocket rumble in the distance", LPF, swells under the riser 14.0-16.0, then the 30 -> 250 Hz HPF sweep drains its sub over 16.0-17.5 (with the music); hard stop at 17.5')
sm = prep('grain_shimmer', MK.format(869), 0.5, 1.45, af='highpass=f=600', fade_in=0.5)
cue('grain_shimmer', sm, 17.5 - 0.95 / st(-7), -31.0, rate=st(-7), fade_out=0.02, dur=0.95 / st(-7) - 0.001,
    note='Mixkit "Fairy sparkle whoosh" -7 st, quiet, as the grains lift; cut at 17.5')

# ------------------------------------------------------------------ 17.5-18.0 TOTAL SILENCE (every clip above ends <= 17.5)
# ------------------------------------------------------------------ S4 DROP 18.0
a1686 = attack(MK.format(1686), 0.008)
a2777 = attack(MK.format(2777), 0.001, win=0.03)
a1273 = attack(MK.format(1273), 0.013)
IMP = -5.0      # impact-group trim (limiter was taking 6-7 dB at 18.0 / 29.0)
MAKEUP = 3.0    # single-channel sub booms: measured mono level reads ~3 dB hotter than the old decorrelated stereo
# the drop's sub stack, aligned to the Pitbull kick: (1) a real sub drum doubling the kick (Eb1, the key's root), level-matched
# to the kick's own 50 ms low-band punch; (2) the boom (+6 dB vs v2) for the weight after it
SUBK = dict(name='drop_sub_kick', src=MK.format(2294), start=a2294 - PRE, end=a2294 + 1.2, af=MONO, fade_out=0.5)
sk = cue('drop_sub_kick', prep(**SUBK), 18.0 - PRE, 0.0, mode='abs', note='Mixkit "Drum bass hit" (Eb1 sub drum): doubles the Pitbull drop kick (polarity/time aligned)')
_lb = lowband(music_mono()[int(17.5 * SR):int(18.7 * SR)]); _lk = lowband(render(sk, 17.5, 18.7))
sk['gain_db'] = round(best50(_lb, 17.5, 18.0) - best50(_lk, 17.5, 18.0) - 1.5, 2)   # 50 ms punch 1.5 dB under the kick's (limiter budget)
align_low(sk, 18.0, prep_args=SUBK, t_min=17.998)
BOOM = dict(name='drop_sub_boom', src=MK.format(1686), start=a1686 - PRE, end=None, af='lowpass=f=1200,' + MONO)
bm = cue('drop_sub_boom', prep(**BOOM), 18.0 - PRE / st(-2), -19.0 + IMP + MAKEUP - 1.0, mode='hit', rate=st(-2),
         note='Mixkit "Underground explosion impact echo" -2 st: sub boom (single-channel feed, polarity/time aligned to the kick + sub drum)')
align_low(bm, 18.0, base_cues=[sk], prep_args=BOOM, t_min=17.998)
cue('drop_explosion', prep('drop_explosion', MK.format(2777), a2777 - PRE, a2777 + 4.0, af=HP140 + ",volume='if(lt(t,0.12),1,exp(-(t-0.12)/0.45))':eval=frame", fade_out=1.5), 18.0 - PRE, -24.5 + IMP, mode='hit',
    note='Mixkit "Masive explosion in battle": sand explosion body + debris (HPF 140; its flat 2 s body shaped to decay, tau 0.45 s, so the drop punches instead of droning)')
# the crack: Mixkit #2599 "Heavy electric shockwave impact" (true silence, then a bright crack). Trimmed 4 ms before the loudest
# 5 ms of its 140 Hz high-passed signal, so the clip opens on a hard edge and its loudest 5 ms lands on 18.0015-18.0065.
_x2599 = lowband(decode(MK.format(2599)).mean(1), 140.0, 24000.0); _k5 = int(0.005 * SR)
_e2599 = np.sqrt(np.convolve(_x2599 ** 2, np.ones(_k5) / _k5, mode='same'))
_i0 = int(3.5 * SR); a2599_pk = (_i0 + int(np.argmax(_e2599[_i0:int(4.0 * SR)]))) / SR
cue('drop_crack', prep('drop_crack', MK.format(2599), a2599_pk - 0.004, a2599_pk + 1.6, af=HP140 + ",volume='if(lt(t,0.06),1,exp(-(t-0.06)/0.30))':eval=frame", fade_in=0.001, fade_out=1.0), 18.0, -24.0 + IMP, mode='hit',
    note=f'Mixkit "Heavy electric shockwave impact" from 4 ms before its loudest 5 ms ({a2599_pk:.4f} s): trailer impact crack, loudest at 18.000-18.010 (HPF 140)')
cue('drop_grit', prep('drop_grit', MK.format(1273), a1273 - PRE, None, af=HP140), 18.0 - PRE, -10.0 + IMP, mode='peak', pan=-0.2,
    note='Mixkit "Gravel stones small avalanche": sand grit (HPF 140)')
# roar: the rising section re-trimmed so its peak (source ~3.88 s) lands on 18.97, just before the front crosses the lens
# (f456-462), then hard-cut at 19.05 (30 ms fade) so front_whoosh_impact / front_pass_wind own the pass
cue('roar', prep('roar', MK.format(2408), 2.91, 3.96, af=HP140, fade_in=0.35, fade_out=0.03), 18.0, -22.0 + IMP, mode='I',
    note='Mixkit "Storm coming whoosh" rising section: the approaching front, peak 18.97, hard cut 19.05 (HPF 140)')
# front passes the lens at 19.0 (timing.json front_passes_lens)
t_front = (tm['front_passes_lens']['frame'] - 1) / 24
a2918 = attack(MK.format(2918), 3.029)
cue('front_whoosh_impact', prep('front_whoosh_impact', MK.format(2918), a2918 - 0.6, a2918 + 3.5, fade_in=0.1, fade_out=1.5, mono_low=140), t_front - 0.6, -18.0 + IMP, mode='hit',
    note='Mixkit "Epic movie trailer whoosh impact": impact on the front pass (low band <140 Hz single-channel, top stereo)')
cue('front_pass_wind', prep('front_pass_wind', MK.format(1167), 1.0, 4.2, fade_in=0.3, fade_out=1.2), t_front - 0.45, -24.0, pan=0.0,
    note='Mixkit "Swoosh wind passing": its two peaks (clip 0.3 / 0.64 s) land on 18.85 / 19.19, straddling the front pass over the lens (18.95-19.20)')
a2498 = attack(MK.format(2498), 0.144)
cue('front_sand_blast_L', prep('front_sand_blast', MK.format(2498), a2498 - PRE, None, af=HP140), t_front - PRE + 0.02, -29.0 + IMP, mode='hit', pan=-0.6,
    note='Mixkit "Body impact falling into the sand", left (HPF 140)')
cue('front_sand_grit_R', prep('drop_grit', MK.format(1273), a1273 - PRE, None, af=HP140), t_front - PRE + 0.05, -12.0 + IMP, mode='peak', pan=0.6,
    note='Mixkit "Gravel stones small avalanche", right (wide stereo)')
cue('sand_rain', prep('sand_rain', MK.format(2494), 0.2, 5.4, af='highpass=f=800'), 19.1, -29.0, fade_in=0.4, fade_out=0.9, dur=2.4,
    note='Mixkit "Sand in the desert": grains settling 19.1-21.5')
a756 = attack(MK.format(756), 0.038)
cue('sand_rain_hit', prep('sand_rain_hit', MK.format(756), a756 - PRE, None, af='highpass=f=500', fade_out=0.3), 19.9, -31.0, mode='hit', pan=0.3,
    note='Mixkit "Falling hit on gravel": a heavy clump landing')

# ------------------------------------------------------------------ S5 side B
cue('altitude_wind', prep('altitude_wind', MK.format(1154), 6.0, 10.8, af='lowpass=f=3500,highpass=f=80'), 21.5, -32.0, fade_in=1.0, fade_out=0.8, dur=4.6,
    note='Mixkit "Arctic winds": high-altitude wind for the crane')
# disc spin-up at 24.0: reversed "Vinyl record slow down" (= spin-up) -24 st + projector mechanism -24 st (stone grind)
spin = prep('disc_spinup_rev', MK.format(711), 0.0, 9.4, reverse=True, af='highpass=f=30')
# take the reversed file from 7.4 s (fast end of the spin-up); at rate 0.25 0.75 s of source = 3.0 s
spin2 = prep('disc_spinup', spin, 7.4, 8.3, fade_in=0.05, fade_out=0.15)
cue('disc_spinup', spin2, 24.0, -24.0, rate=st(-24), dur=2.0, fade_out=0.7, note='Mixkit "Vinyl record slow down" reversed (= spin-up), -24 st; gone by 26.0')
# grind swells to its peak around 25.0 (the disc reaches 3 deg/s) and is gone by 26.0, so shadow_drone owns 26.0-27.0
cue('disc_grind', prep('disc_grind', MK.format(1444), 2.0, 2.9, af='highpass=f=200', fade_in=0.2), 24.05, -30.0, rate=st(-24), dur=1.95, fade_out=0.95,
    note='Mixkit "Antique movie projector spinning" -24 st: colossal stone/motor grind, swell to ~25.0, gone by 26.0')

# ------------------------------------------------------------------ S6 needle
t_shadow = (tm['shadow_enters']['frame'] - 1) / 24
cue('shadow_drone', prep('shadow_drone', MK.format(2615), 0.6, 4.4, af='lowpass=f=2500', fade_in=0.4, fade_out=0.8), t_shadow - 0.25, -24.0, rate=st(-5), dur=2.6, fade_out=0.8,
    note='Mixkit "Mighty mysterious swoosh" -5 st: dark air-pressure pass of the arm shadow')
# the arm lands at 29.0: servo and creak stop at 28.75 where the music cuts (the vacuum, f691-696), leaving only the downwash
cue('arm_servo', prep('arm_servo', MK.format(1814), 6.0, 7.05, af='highpass=f=150', fade_in=0.15, fade_out=0.3), 27.0, -30.0, rate=st(-12), dur=1.75, fade_out=0.02,
    note='Mixkit "Electric whisk stops" -12 st: servo; stops at 28.75')
cue('arm_creak', prep('arm_creak', MK.format(2799), 0.0, 1.17, fade_out=0.3), 27.4, -29.0, rate=st(-12), dur=1.35, fade_out=0.02,
    note='Mixkit "Metallic sword scrape" -12 st: metal creak; stops at 28.75')
# hydraulic downwash: its zoom peaks at 28.95 and hard-stops at 28.99 (20 ms) - the only sound of the vacuum with the crackle swell
cue('arm_hydraulic', prep('arm_hydraulic', MK.format(2608), 0.0, 1.0, af='highpass=f=300', fade_out=0.2), 28.05, -26.0, rate=st(-12), dur=0.94, fade_out=0.02,
    note='Mixkit "Air zoom vacuum" -12 st: hydraulic hiss / downwash swelling into the touchdown, hard stop 28.99')
# reversed vinyl-crackle swell (the needle approaching the groove) ending exactly at 28.995: the vacuum's suck-in
rsw = prep('touchdown_crackle_swell', bed, 4.0, 4.5, reverse=True, af="volume='pow(10,(-24+24*pow(t/0.5,2))/20)':eval=frame", fade_out=0.003)
cue('touchdown_crackle_swell', rsw, 28.995 - 0.5, -31.0, mode='hit', note='vinyl surface noise (the 0.00 bed) reversed, exponential swell into 28.995')
# TOUCHDOWN 29.0: the 0.00 needle file -12 st + sub boom + sand burst; everything but the crackle hard-cuts at 29.5 (cut to black)
cue('touchdown_needle', needle, 29.0 - PRE / st(-12), -13.0 + IMP, mode='peak', rate=st(-12), dur=0.5, fade_out=0.03, note='the 0.00 needle-drop file, -12 st')
tdn = cues[-1]
SUBK2 = dict(name='touchdown_sub_kick', src=MK.format(2294), start=a2294 - PRE, end=a2294 + 0.6, af=MONO)
sk2 = cue('touchdown_sub_kick', prep(**SUBK2), 29.0 - PRE, 0.0, mode='abs', dur=0.5 - PRE, fade_out=0.03,
          note='Mixkit "Drum bass hit" (Eb1 sub drum): doubles the final-hit kick (polarity/time aligned), hard cut at 29.5')
_lb = lowband(music_mono()[int(28.5 * SR):int(29.7 * SR)]); _lk = lowband(render(sk2, 28.5, 29.7))
sk2['gain_db'] = round(best50(_lb, 28.5, 29.0) - best50(_lk, 28.5, 29.0) - 8.0, 2)   # a touch: the touchdown's sub is the boom's
align_low(sk2, 29.0, base_cues=[tdn], prep_args=SUBK2)
sk2['dur'] = round(29.5 - (sk2['at'] + LAT), 5)
TBOOM = dict(name='touchdown_boom', src=MK.format(1686), start=a1686 - PRE, end=None, af='lowpass=f=900,' + MONO)
tb = cue('touchdown_boom', prep(**TBOOM), 29.0 + 0.006 - PRE / st(-3), -21.0 + IMP + MAKEUP + 4.0, mode='hit', rate=st(-3),
         dur=0.5 - 0.0065, fade_out=0.03, note='sub boom -3 st (single-channel feed, polarity/time aligned to the kick + sub drum), hard cut at 29.5')
align_low(tb, 29.0, base_cues=[tdn, sk2], prep_args=TBOOM)
tb['dur'] = round(29.5 - (tb['at'] + LAT), 5)
cue('touchdown_sand', prep('touchdown_sand', MK.format(2777), a2777 - PRE, a2777 + 0.6, af=HP140 + ',' + HALFWIDE), 29.0 - PRE, -22.0 + IMP, mode='hit', dur=0.5 - PRE, fade_out=0.03,
    note='sand burst (HPF 140), hard cut at 29.5')
cue('touchdown_grit', prep('drop_grit', MK.format(1273), a1273 - PRE, None, af=HP140), 29.0 - PRE + 0.03, -11.0 + IMP, mode='peak', pan=0.35, dur=0.46, fade_out=0.03)

# ------------------------------------------------------------------ write cues.json (tools/mix.js format)
mix = dict(duration=30,
           latency_compensation_s=LAT,
           kick_window_db=7.0,   # master_linear.py: content above 150 Hz -7 dB from 18.008 / 29.008 (hero kick windows)
           kick_window_shape=[0.003, 0.040, 0.085],   # attack / hold / release (s); the release is a dB-domain raised cosine (no re-attack)
           music=[dict(file='audio/_work/music_stem_mixjs.wav', at=0, offset=0, dur=None, gain_db=0.0, fade_in=0, fade_out=0,
                       note='audio/_work/music_ducked.wav (music_edit.wav + the bible 6.1 ducks, Pitbull above 150 Hz only, -3 dB at 18.0 and 29.0) advanced by 240 samples to cancel the mix.js limiter latency (mix.js input only; master_linear.py uses audio/_work/music_ducked.wav)')],
           sfx=cues, duck=dict(enabled=False), master=dict(lufs=-14, tp=-1.0),
           note='Generated by audio/scripts/build_cues.py. All SFX are pre-trimmed in audio/sfx/prep (offset always 0); rate = 2^(semitones/12) pitch-down via asetrate. Gains are measured on the prepared clip against the per-cue target in _level (mode abs = set directly). _align = polarity/time alignment of the sub layers to the kick.')
json.dump(mix, open('audio/cues.json', 'w'), indent=1)
json.dump(ALIGN_LOG, open('audio/_work/align_log.json', 'w'), indent=1)
# sanity: nothing may sound inside 17.5-18.0
for c in cues:
    x = decode(c['file']); L = len(x) / SR / c['rate']
    if c['dur'] is not None: L = min(L, c['dur'])
    if c['at'] + LAT < 17.9979 and c['at'] + LAT + L > 17.5001:
        print('WARNING overlaps the silence:', c['name'], c['at'], c['at'] + L)
print(f'{len(cues)} sfx cues written')
