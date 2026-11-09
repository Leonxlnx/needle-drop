# NEEDLE DROP audio data pipeline (bible 4.3), numpy only.
# Usage (project root as cwd): python -I audio/scripts/audio_analyze.py [audio/music_edit.wav]
# Writes data/beats.json, data/bands.json, updates data/timing.json (frames snapped to detected beats, max +-2 frames).
# v2 (art-director round 1):
#  - kicks = 30-150 Hz spectral-flux candidates in the edit, each VALIDATED against the dry Pitbull source at its mapped
#    source time (audio/music_edit_map.json): 40-110 Hz 35 ms RMS >= -20 dBFS and >= +6 dB over the preceding 35 ms.
#    Rejects snares, bass notes and noise that the old local-median detector let through.
#  - kick time = sample where the 2 ms Hilbert envelope of the edit's 30-150 Hz band crosses 50 % of its local peak
#    (searched 60 ms before .. 40 ms after the flux peak); removes the ~16 ms STFT-centre lag.
#  - kick strength is GLOBAL: the kick's 40-110 Hz 35 ms RMS peak in the edit (what is heard) mapped linearly from
#    STRENGTH_DB[0] -> 0 to STRENGTH_DB[1] -> 1 dBFS over the whole film (never relative to a local median).
#  - kick frame = floor(t*24)+1 (frame n shows [(n-1)/24, n/24)); sets need not round.
#  - bands.json: gate[720] (0 in the 17.5-18.0 silence f421-432 and after the 29.5 cut f709-720); all channels read 0 there;
#    the anti-strobe clamp is released at gate edges so the hard stop (f421) and the drop (f433) are frame-exact;
#    bands_raw = unclamped, unsmoothed per-frame copies for frame-accurate hits.
# v3 (art-director round 2):
#  - kicks must ALSO be audible in the edit: 40-110 Hz 35 ms RMS >= -30 dBFS (at the round-1 edit level) and >= +3 dB over the
#    preceding 35 ms in music_edit.wav (drops e.g. 3.301, which only passed on the dry source). Kicks inside the build's
#    30 -> 250 Hz high-pass sweep (16.0-17.5) are exempt: the sweep drains their sub on purpose, their attack stays audible.
#  - strength thresholds follow the edit's normalisation gain, so unchanged material keeps its round-1 strength.
#  - gate dip f691-696 (the touchdown vacuum: the music is silent 28.75-28.998); clamp released at its edges.
#  - broadband-flux fields renamed so nobody mistakes them for kick times: beats_detail[].flux_onset_t_bb, grid_xcorr_bb.
import sys, os, json, subprocess, numpy as np

WAV = sys.argv[1] if len(sys.argv) > 1 else 'audio/music_edit.wav'
SR = 48000; FPS = 24; NF = 720; BPM = 120.0; DROP = 18.0
NFFT = 2048; HOP = 512          # bible STFT (bands)
HOP_FINE = 240                  # 5 ms hop for onset candidates
SUB_MIN_DB = -20.0              # dry-source 40-110 Hz 35 ms RMS a real kick must reach
SUB_RISE_DB = 6.0               # ... and its rise over the preceding 35 ms
EDIT_MIN_DB = -30.0             # edit-side audibility: 40-110 Hz 35 ms RMS (at the round-1 edit level, see NORM_REF_DB)
EDIT_RISE_DB = 3.0              # ... and its rise over the preceding 35 ms
NORM_REF_DB = -2.72             # round-1 music_edit.wav normalisation gain: dB thresholds are shifted by (gain - this)
STRENGTH_DB = (-30.0, -10.0)    # edit 40-110 Hz kick level mapped to strength 0..1 (global, at the round-1 edit level)
SWEEP = (16.0, 17.5)            # build HPF sweep: kicks here are rated at their pre-sweep (unfiltered) edit level

def load(path):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).astype(np.float64)

def stft_mag(x, nfft, hop):
    w = np.hanning(nfft)
    xp = np.concatenate([np.zeros(nfft // 2), x, np.zeros(nfft // 2)])   # frame k centred at k*hop
    n = 1 + (len(xp) - nfft) // hop
    out = np.empty((n, nfft // 2 + 1))
    for s in range(0, n, 4096):
        e = min(n, s + 4096)
        idx = np.arange(nfft)[None, :] + hop * np.arange(s, e)[:, None]
        out[s:e] = np.abs(np.fft.rfft(xp[idx] * w, axis=1))
    return out

def flux(M, freqs, lo, hi, lag=1):
    sel = (freqs >= lo) & (freqs < hi)
    L = np.log1p(1000 * M[:, sel])
    d = np.zeros_like(L); d[lag:] = L[lag:] - L[:-lag]
    return np.maximum(d, 0).sum(1)

def moving_median(v, w):
    h = w // 2
    p = np.pad(v, h, mode='edge')
    from numpy.lib.stride_tricks import sliding_window_view as swv
    return np.median(swv(p, w), axis=-1)[:len(v)]

def bandpass(x, lo, hi):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    g = np.clip(np.minimum((f - lo * 0.8) / (lo * 0.2), (hi * 1.25 - f) / (hi * 0.25)), 0, 1)   # short linear skirts (less ringing)
    return np.fft.irfft(X * g, len(x))

def hilbert_env(x):
    n = len(x); X = np.fft.fft(x); h = np.zeros(n); h[0] = 1
    if n % 2 == 0: h[n // 2] = 1; h[1:n // 2] = 2
    else: h[1:(n + 1) // 2] = 2
    return np.abs(np.fft.ifft(X * h))

def rms_win(c2, a, b):   # RMS from a cumulative sum of squares, sample indices
    a = max(0, a); b = max(a + 1, b)
    return np.sqrt((c2[b] - c2[a]) / (b - a))

dB = lambda v: 20 * np.log10(v + 1e-12)
x = load(WAV)
T = len(x) / SR
_norm = json.load(open('audio/music_edit_map.json')).get('normalise_gain_db', NORM_REF_DB)
LVL_SHIFT = _norm - NORM_REF_DB          # +dB the edit is hotter than in round 1
STRENGTH_DB = (STRENGTH_DB[0] + LVL_SHIFT, STRENGTH_DB[1] + LVL_SHIFT)
EDIT_MIN_DB += LVL_SHIFT
print(f'edit normalisation {_norm:+.2f} dB -> level thresholds shifted {LVL_SHIFT:+.2f} dB')
freqs = np.fft.rfftfreq(NFFT, 1 / SR)

# ---------------------------------------------------------------- fine onset functions (5 ms)
Mf = stft_mag(x, NFFT, HOP_FINE)
fr = SR / HOP_FINE
tf = np.arange(len(Mf)) / fr
on_all = flux(Mf, freqs, 30, 16000, lag=2)
on_low = flux(Mf, freqs, 30, 150, lag=2)
# flux at frame k (centred window) rises ~ half a window before the attack; calibrate the lag on a synthetic click
_c = np.zeros(SR); _c[SR // 2:] = np.random.default_rng(0).standard_normal(SR // 2) * np.exp(-np.arange(SR // 2) / 4000)
_Mc = stft_mag(_c, NFFT, HOP_FINE); _o = flux(_Mc, freqs, 30, 16000, lag=2)
LAG_CAL = 0.5 - np.argmax(_o) / fr       # seconds the flux peak precedes the true attack
print(f'onset calibration: flux peak precedes attack by {LAG_CAL*1000:.1f} ms (corrected)')

def peak_time(env, t_guess, win=0.04):
    a = max(0, int((t_guess - win) * fr)); b = int((t_guess + win) * fr)
    k = a + int(np.argmax(env[a:b]))
    if 0 < k < len(env) - 1:
        y0, y1, y2 = env[k - 1], env[k], env[k + 1]
        den = y0 - 2 * y1 + y2
        off = 0.5 * (y0 - y2) / den if den != 0 else 0
    else:
        off = 0
    return (k + off) / fr + LAG_CAL, env[k]

# ---------------------------------------------------------------- drop verification (attack-start + flux based)
def attack_start(t_guess):
    a = int((t_guess - 0.05) * SR); seg = np.abs(x[a:a + int(0.1 * SR)])
    k = int(0.0005 * SR); env = np.convolve(seg, np.ones(k) / k, mode='same')
    pre = np.median(env[:int(0.02 * SR)]); pk = env.max()
    j = np.argmax(env > pre + 0.1 * (pk - pre))
    return (a + j) / SR

t_drop_flux, _ = peak_time(on_all, DROP)
t_drop_att = attack_start(DROP)
print(f'DROP measured: flux-onset {t_drop_flux:.4f} s, attack start {t_drop_att:.4f} s (target 18.000)')

# ---------------------------------------------------------------- grid check: cross-correlate onset env with the 120 BPM grid per section
P = 60 / BPM
grid = DROP + P * np.arange(-36, 24)
grid = grid[(grid >= 0) & (grid < T - 0.01)]
sections = [(0, 6, 'intro (filtered)'), (6, 12, 'groove A'), (12, 17.5, 'build'), (18, 26, 'drop'), (26, 29, 'lift'), (29, 29.5, 'final hit')]
grid_report = []
e = on_all / (np.percentile(on_all, 99) + 1e-9)
for a, b, name in sections:
    gs = grid[(grid >= a) & (grid < b)]
    best = None
    for off in np.arange(-0.06, 0.0605, 0.001):
        v = np.interp(gs + off - LAG_CAL, tf, e).sum()
        if best is None or v > best[1]: best = (off, v)
    grid_report.append(dict(section=name, start=a, end=b, best_offset_ms=round(best[0] * 1000, 1), frames=round(best[0] * FPS, 2)))
    print(f'  grid xcorr {name:18s} best offset {best[0]*1000:+6.1f} ms ({best[0]*FPS:+.2f} frames)')

# ---------------------------------------------------------------- beats: grid beats with detected onset strength
beats = []
thr_on = np.percentile(on_all, 75)
for b in grid:
    tp, v = peak_time(on_all, b, win=0.035)
    beats.append(dict(t=round(float(b), 4), frame=int(np.floor(b * FPS + 1e-6)) + 1, flux_onset_t_bb=round(float(tp), 4),
                      onset_strength=round(float(min(1.0, v / np.percentile(on_all, 99))), 3),
                      detected=bool(v > thr_on and not (17.5 <= b < 18.0))))
downbeats = [round(float(b), 4) for b in grid if abs(((b - DROP) / (4 * P)) - round((b - DROP) / (4 * P))) < 1e-6]

# ---------------------------------------------------------------- kicks
# 1) candidates: peaks of 30-150 Hz flux above an adaptive median threshold (bible 4.3), deliberately permissive
med = moving_median(on_low, int(0.8 * fr) | 1)
p99 = np.percentile(on_low, 99)
cand = []
for k in range(2, len(on_low) - 2):
    v = on_low[k]
    if v < 0.08 * p99 or v < 1.5 * med[k]: continue
    a = max(0, k - int(0.06 * fr)); b = min(len(on_low), k + int(0.06 * fr) + 1)
    if v < on_low[a:b].max(): continue
    cand.append((k / fr + LAG_CAL, v))
# 2) timing: 2 ms Hilbert envelope of the edit's 30-150 Hz band, 50 % crossing before the local peak
low_edit = bandpass(x, 30, 150)
env_e = hilbert_env(low_edit); kk = int(0.002 * SR); env_e = np.convolve(env_e, np.ones(kk) / kk, mode='same')
K5 = int(0.005 * SR)
def refine(tc):
    """The kick's attack = steepest 5 ms rise of the low-band envelope in [tc-60 ms, tc+40 ms]; its local peak = max of the
    30 ms after that rise; time = the 50 % crossing walking back from the rise. (Picking the window maximum instead would
    lock onto the 808's second, later envelope peak ~50 ms after the attack.)"""
    # tc already carries the +15 ms flux calibration, so the raw flux peak is tc-15 ms: search [raw-60, raw+40] ms and weight
    # rises by their distance from the raw peak (Gaussian, 25 ms) so an earlier bass-note swell cannot win.
    t_raw = tc - LAG_CAL
    a = max(0, int((t_raw - 0.06) * SR)); b = min(len(env_e) - K5, int((t_raw + 0.04) * SR))
    seg = env_e[a:b + K5]
    rise = seg[K5:] - seg[:-K5]
    tt = (a + np.arange(b - a)) / SR
    j = int(np.argmax(rise[:b - a] * np.exp(-((tt - t_raw) / 0.025) ** 2)))
    half = 0.5 * seg[j:j + K5 + int(0.03 * SR)].max()
    i = j + K5
    while i > 0 and seg[i - 1] >= half: i -= 1
    return (a + i) / SR
# 3) validation on the DRY source (unfiltered intro, no echo, no layers) via the edit map
emap = json.load(open('audio/music_edit_map.json'))
pit = [s for s in emap['segments'] if s['input'] == 'Pitbull']
xs = load(emap['source'])
sub_src = bandpass(xs, 40, 110); c2s = np.concatenate([[0], np.cumsum(sub_src ** 2)])
sub_ed = bandpass(x, 40, 110); c2e = np.concatenate([[0], np.cumsum(sub_ed ** 2)])
W35 = int(0.035 * SR)
def to_src(t):
    best = None
    for s in pit:
        o0, o1 = s['out']
        if o0 <= t < o1:
            m_ = min(t - o0, o1 - t)
            if best is None or m_ > best[0]: best = (m_, s)
    if best is None: return None, None
    s = best[1]; return s['src_start'] + (t - s['out'][0]), s['label']
def sub_level(c2, t):
    """(peak 35 ms RMS in the 60 ms after the attack, RMS of the 35 ms before it) in dBFS."""
    i = int(t * SR)
    post = max(rms_win(c2, i + o, i + o + W35) for o in range(-int(0.005 * SR), int(0.06 * SR), int(0.0025 * SR)))
    pre = rms_win(c2, i - int(0.005 * SR) - W35, i - int(0.005 * SR))
    return dB(post), dB(pre)
kicks, rejected = [], []
for tc, v in cand:
    if 17.45 <= tc < 18.0 or tc >= 29.5: continue
    t = refine(tc)
    if 17.5 <= t < 17.998 or t >= 29.5: continue
    ts, seg = to_src(t)
    if ts is None: rejected.append((t, 'no source')); continue
    lv, pre = sub_level(c2s, ts)
    ok = lv >= SUB_MIN_DB and lv - pre >= SUB_RISE_DB
    rec = dict(t=t, src_t=ts, seg=seg, src_sub_db=lv, src_rise_db=lv - pre, flux=v)
    if not ok: rejected.append((t, f'src sub {lv:.1f} dBFS rise {lv-pre:+.1f}')); continue
    # edit-side audibility (before the duplicate merge, so an inaudible early twin cannot shadow the real kick):
    # the 35 ms right after the attack vs the 35 ms right before it, in music_edit.wav
    i_ = int(t * SR); e_post = dB(rms_win(c2e, i_, i_ + W35)); e_pre = dB(rms_win(c2e, i_ - W35, i_))
    rec['edit_post_db'] = e_post; rec['edit_pre_db'] = e_pre
    if not (SWEEP[0] <= t < SWEEP[1]) and not (e_post >= EDIT_MIN_DB and e_post - e_pre >= EDIT_RISE_DB):
        rejected.append((t, f'edit sub {e_post:.1f} dBFS rise {e_post - e_pre:+.1f} (inaudible in the edit)')); continue
    if kicks and t - kicks[-1]['t'] < 0.15:      # duplicate of the same hit: keep the one louder IN THE EDIT (what is heard)
        if e_post > kicks[-1]['edit_post_db']: kicks[-1] = rec
        continue
    kicks.append(rec)
for k in kicks: k['edit_db'] = sub_level(c2e, k['t'])[0]
print(f"edit-side check rejected: {', '.join(f'{t:.3f}' for t, why in rejected if 'inaudible' in why) or 'none'}")
# kicks inside the build's 30->250 Hz high-pass sweep would read artificially weak (the sweep drains the sub on purpose);
# rate them at their source level + the build segment's measured edit/source offset (from the build's unswept kicks)
offs = [k['edit_db'] - k['src_sub_db'] for k in kicks if 12.0 <= k['t'] < SWEEP[0]]
b_off = float(np.median(offs)) if offs else 0.0
kick_list = []
for k in kicks:
    lv_e = k['edit_db']
    if SWEEP[0] <= k['t'] < SWEEP[1]: lv_e = k['src_sub_db'] + b_off
    st = float(np.clip((lv_e - STRENGTH_DB[0]) / (STRENGTH_DB[1] - STRENGTH_DB[0]), 0, 1))
    near = grid[np.argmin(np.abs(grid - k['t']))]
    kick_list.append(dict(t=round(float(k['t']), 4), frame=int(np.floor(k['t'] * FPS)) + 1, strength=round(st, 3),
                          edit_sub_db=round(lv_e, 1), edit_rise_db=round(k['edit_post_db'] - k['edit_pre_db'], 1), src_t=round(float(k['src_t']), 4), src_sub_db=round(k['src_sub_db'], 1),
                          src_rise_db=round(k['src_rise_db'], 1), beat=round(float(near), 3), off_beat_ms=round(float((k['t'] - near) * 1000), 1),
                          on_beat=bool(abs(k['t'] - near) < 0.03), section=k['seg']))
print(f'kick candidates {len(cand)} -> validated {len(kick_list)} (rejected {len(rejected)})')

# ---------------------------------------------------------------- bands.json (frames 1..720)
M = stft_mag(x, NFFT, HOP)
tc_ = np.arange(len(M)) * HOP / SR              # frame centres
fidx = np.floor(tc_ * FPS).astype(int)          # video frame index (0-based): frame n covers [(n-1)/24, n/24)
P2 = M ** 2
edges = 30 * (16000 / 30) ** (np.arange(9) / 8)
gate = np.ones(NF)
gate[420:432] = 0      # f421-432: 17.500-18.000 total silence
gate[708:] = 0         # f709-720: black after the 29.5 cut
gate[690:696] = 0      # f691-696: the touchdown vacuum (music silent 28.75-28.998)

def per_frame(power_rows):
    out = np.zeros(NF)
    for n in range(NF):
        sel = fidx == n
        out[n] = np.sqrt(power_rows[sel].mean()) if sel.any() else 0.0
    return out

def shape(v):
    v = v * gate
    y = np.zeros_like(v); r = np.exp(-1 / 6)          # 1-frame attack, 6-frame release
    for i in range(len(v)):
        prev = y[i - 1] if i else 0.0
        y[i] = v[i] if v[i] >= prev else max(v[i], prev * r)
        if gate[i] == 0: y[i] = 0.0
    p95 = np.percentile(y[y > 0], 95) if (y > 0).any() else 1.0
    y = np.clip(y / p95, 0, 1)
    z = np.zeros_like(y)                             # anti-strobe: |dy| <= 0.25 / frame, except at gate edges (hard stop / drop)
    for i in range(len(y)):
        prev = z[i - 1] if i else 0.0
        edge = gate[i] == 0 or (i and gate[i - 1] == 0)
        z[i] = y[i] if edge else prev + np.clip(y[i] - prev, -0.25, 0.25)
    raw = np.clip(v / p95, 0, 1) * gate
    return z, raw

band_pw = [per_frame(P2[:, (freqs >= edges[i]) & (freqs < edges[i + 1])].sum(1)) for i in range(8)]
sh = [shape(b) for b in band_pw]
bands = [s[0] for s in sh]; bands_raw = [s[1] for s in sh]
env_low, env_low_raw = shape(per_frame(P2[:, (freqs >= 30) & (freqs < 150)].sum(1)))
rms, rms_raw = shape(per_frame(P2.sum(1)))
r4 = lambda a: [round(float(v), 4) for v in a]
bands_json = dict(fps=FPS, frames=NF, frame_convention='index i -> global frame i+1, covering [i/24, (i+1)/24) s',
                  source=WAV, band_edges_hz=[round(float(e_), 1) for e_ in edges],
                  method=('STFT n_fft 2048 hop 512 @48k, per-frame RMS, 1-frame attack / 6-frame release, /95th pct, clamp 0..1, '
                          '|d|<=0.25/frame except at gate edges; gate=0 in f421-432 (17.5-18.0 silence), f691-696 (touchdown vacuum, music silent 28.75-29.0) and f709-720 (black), all channels 0 there. '
                          'bands_raw/env_low_raw/rms_raw: same normalisation, no attack/release, no clamp (frame-accurate hits).'),
                  gate=[int(g) for g in gate],
                  bands={f'b{i}': r4(bands[i]) for i in range(8)},
                  band_matrix=[[round(float(bands[i][n]), 4) for i in range(8)] for n in range(NF)],
                  bands_raw={f'b{i}': r4(bands_raw[i]) for i in range(8)},
                  env_low=r4(env_low), low=r4(env_low), rms=r4(rms), env_low_raw=r4(env_low_raw), rms_raw=r4(rms_raw))
json.dump(bands_json, open('data/bands.json', 'w'))

beats_json = dict(default=False, bpm=BPM, source=WAV, drop=DROP,
                  drop_measured=dict(flux_onset=round(float(t_drop_flux), 4), attack_start=round(float(t_drop_att), 4)),
                  beats=[b['t'] for b in beats], downbeats=downbeats,
                  kicks=[dict(t=k['t'], frame=k['frame'], strength=k['strength']) for k in kick_list],
                  beats_detail=beats, kicks_detail=kick_list, grid_xcorr_bb=grid_report,
                  fields_note=('beats_detail[].flux_onset_t_bb and grid_xcorr_bb come from the BROADBAND spectral flux (+15 ms calibrated) and are '
                               'informational only (grid check). They are not kick times: use kicks[].t / kicks[].frame.'),
                  kick_method=dict(candidates='30-150 Hz spectral-flux peaks (5 ms hop) above an adaptive median threshold',
                                   validation=(f'dry Pitbull source at the mapped time: 40-110 Hz 35 ms RMS >= {SUB_MIN_DB} dBFS and >= +{SUB_RISE_DB} dB over the preceding 35 ms; '
                                               f'AND audible in the edit: 40-110 Hz 35 ms RMS >= {EDIT_MIN_DB:.1f} dBFS and >= +{EDIT_RISE_DB} dB over the preceding 35 ms '
                                               '(kicks inside the 16.0-17.5 high-pass sweep exempt)'),
                                   time='50 % crossing of the 2 ms Hilbert envelope of the edit 30-150 Hz band (search -60..+40 ms around the flux peak)',
                                   frame='floor(t*24)+1',
                                   strength=f'global: edit 40-110 Hz 35 ms RMS peak mapped {STRENGTH_DB[0]} dBFS -> 0, {STRENGTH_DB[1]} dBFS -> 1 (kicks in the 16.0-17.5 HPF sweep rated at their unfiltered level)'),
                  note=('Detected from audio/music_edit.wav (120.000 BPM grid anchored on the 18.000 s drop). Every kick is a real, audible '
                        'Pitbull kick (validated on the dry source); use them all, no threshold needed. No kicks inside the 17.5-18.0 silence '
                        'or after 29.5. Kicks after 18.0 come from the Pitbull drums only (the Epical layer is high-passed at 140 Hz).'))
json.dump(beats_json, open('data/beats.json', 'w'), indent=1)

# ---------------------------------------------------------------- timing.json snap (keep keys/structure; frames move by <= 2)
tm = json.load(open('audio/_work/timing_orig.json' if os.path.exists('audio/_work/timing_orig.json') else 'data/timing.json'))  # always snap from the director's original grid
det = [b for b in beats if b['detected']]
snaps = []
for name, ev in tm['events'].items():
    f0 = ev['frame']
    best = None
    for b in det + [dict(t=d_) for d_ in downbeats]:
        fb = int(round(b['t'] * FPS)) + 1
        if abs(fb - f0) <= 2 and (best is None or abs(fb - f0) < abs(best - f0)): best = fb
    if best is not None and best != f0:
        snaps.append((name, f0, best))
        ev['frame'] = best; ev['t'] = round((best - 1) / FPS, 4)
tm['note'] = ('Event frames snapped by the audio stage to detected beats of audio/music_edit.wav (120.000 BPM, drop downbeat measured at '
              f'{t_drop_att:.3f} s). frame = round(t*24)+1. Snapped: ' + (', '.join(f'{n} {a}->{b}' for n, a, b in snaps) or 'none') + '.')
json.dump(tm, open('data/timing.json', 'w'), indent=1)
print('timing snaps:', snaps)

# ---------------------------------------------------------------- report
def seg_db(a, b):
    s = x[int(a * SR):int(b * SR)]
    return dB(np.sqrt(np.mean(s ** 2)))
print('silence 17.50-17.995 RMS %.1f dBFS, peak %.1f dBFS' % (seg_db(17.5, 17.995), dB(np.abs(x[int(17.5 * SR):int(17.995 * SR)]).max())))
for a, b in [(0, 6), (6, 12), (12, 17.5), (18, 26), (26, 29), (29, 29.5)]:
    nk = sum(1 for k in kick_list if a <= k['t'] < b)
    print(f'  RMS {a:5.1f}-{b:5.1f}: {seg_db(a, b):6.1f} dBFS   kicks {nk}')
print('kicks (t, frame, strength, src sub dB, rise, off-beat ms):')
for k in kick_list:
    print(f"  {k['t']:7.3f} f{k['frame']:3d} s={k['strength']:.2f} edit {k['edit_sub_db']:6.1f}  src {k['src_sub_db']:6.1f} rise {k['src_rise_db']:+5.1f}  {k['off_beat_ms']:+6.1f} ms")
print('rejected:', ', '.join(f'{t:.3f} ({why})' for t, why in rejected))
# possible kicks the critique flagged (6-11 dB 40-110 Hz rises on the grid): show why each was rejected
for tq in (7.5, 9.5, 21.25, 25.75, 28.25):
    near = [(t, why) for t, why in rejected if abs(t - tq) < 0.06]
    print(f'  check {tq:6.2f}:', '; '.join(f'{t:.3f} {why}' for t, why in near) if near else 'no candidate within 60 ms')
print('ANALYZE_OK')
