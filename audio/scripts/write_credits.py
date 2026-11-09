# Write audio/credits.txt from cues.json, the Mixkit listing metadata and the SFX search logs.
# Usage (project root as cwd): python -I audio/scripts/write_credits.py
import json, os, re, glob

meta = json.load(open('audio/_work/music_meta.json'))
titles = {}
for f in glob.glob('audio/_work/sfx_search*.txt'):
    for line in open(f, encoding='utf-8', errors='replace'):
        m = re.match(r'(\d+) \| (.+?) \| ([0-9:]+) \|', line)
        if m: titles[m.group(1)] = (m.group(2), m.group(3))
cues = json.load(open('audio/cues.json'))
emap = json.load(open('audio/music_edit_map.json'))

L = []
L.append('NEEDLE DROP - audio credits and licences')
L.append('=' * 60)
L.append('All music and sound effects are real recordings downloaded without login from Mixkit and (vinyl surface noise only)')
L.append('freesound.org CC0 sounds. Nothing is synthesised;')
L.append('the audio stage only cut, crossfaded, filtered, reversed, pitch-shifted (asetrate / rubberband), layered and levelled them.')
L.append('Mixkit Stock Music Free License: https://mixkit.co/license/#musicFree  (free for commercial and personal use, no attribution required)')
L.append('Mixkit Sound Effects Free License: https://mixkit.co/license/#sfxFree   (free for commercial and personal use, no attribution required)')
L.append('freesound.org CC0 sounds: Creative Commons 0 (public domain dedication, no attribution required): https://creativecommons.org/publicdomain/zero/1.0/')
L.append('Credit is given below anyway as good practice. No CC-BY material is used, so no mandatory credit text applies.')
L.append('')
L.append('MUSIC USED IN THE FILM')
L.append('-' * 60)
for mid, role in [('1008', 'main track: all music bars of the 30 s edit (intro, groove, build, drop, lift, final hit)'),
                  ('677', 'hybrid-cinematic layer: its 58.0 s hit + the 8-bar percussion groove after it (resampled 120.3 -> 120 BPM, HPF 140 Hz) under the 18.0-26.0 drop, and the hit again on the 29.0 final hit')]:
    m = meta.get(mid, {})
    L.append(f'"{m.get("name", "?")}" by {m.get("artist", "unknown")} ({m.get("genre", "")}), Mixkit Stock Music Free License')
    L.append(f'  URL: https://assets.mixkit.co/music/{mid}/{mid}.mp3   local: audio/music/mixkit/mixkit_{mid}.mp3')
    L.append(f'  Role: {role}')
L.append('"Orchestra triumphant trumpets" (0:04), Mixkit sound effect #2285, author not listed by Mixkit, Mixkit Sound Effects Free License')
L.append('  URL: https://assets.mixkit.co/active_storage/sfx/2285/2285.wav   local: audio/sfx/mixkit/mixkit_sfx_2285.wav')
L.append('  Role: brass stab in the music edit: its sustained C5 power chord chopped and pitched (rubberband, formant preserved) to Eb5 (18.0, 29.0) and Bb4 (24.0)')
L.append('  Edit map: audio/music_edit_map.json; result audio/music_edit.wav (48 kHz stereo 24-bit, 120.000 BPM, drop downbeat at 18.000 s)')
L.append('')
L.append('SOUND EFFECTS USED IN THE MIX (audio/cues.json)')
L.append('-' * 60)
used = {}
for c in cues['sfx']:
    src = c.get('note', '')
    # find the Mixkit id from the prep chain: notes name the Mixkit title; map via prep file -> source id table below
    used.setdefault(c['file'], []).append(c['name'])
PREP_SRC = {  # prepared clip -> Mixkit SFX id(s) it was made from
    'crackle_head_0_12': ['fs637931', 'fs838458'], 'crackle_tail_29_30': ['fs637931', 'fs838458'], 'needle_drop': ['701'], 'canyon_wind': ['1267'],
    'lint_whoosh': ['2604'], 'crystal_swell_rev': ['3108'], 'metal_scrape': ['809'], 'vault_whoosh': ['2623'], 'metal_swish': ['1485'],
    'reverse_pull': ['1471'], 'motor_hum': ['1837'], 'neon_buzz': ['2132'], 'vortex': ['2667'], 'reverse_cymbal': ['2782'],
    'cut_thump': ['498'], 'desert_wind': ['2490'], 'sand_hiss': ['1494'], 'sub_rumble': ['1718'], 'grain_shimmer': ['869'],
    'drop_sub_boom': ['1686'], 'drop_explosion': ['2777'], 'drop_crack': ['2599'], 'drop_grit': ['1273'], 'roar': ['2408'],
    'drop_sub_kick': ['2294'], 'touchdown_sub_kick': ['2294'], 'needle_thunk': ['2294'], 'air_rush': ['1484'], 'air_swoosh': ['167'],
    'touchdown_crackle_swell': ['fs637931'],
    'front_whoosh_impact': ['2918'], 'front_pass_wind': ['1167'], 'front_sand_blast': ['2498'], 'sand_rain': ['2494'],
    'sand_rain_hit': ['756'], 'altitude_wind': ['1154'], 'disc_spinup': ['711'], 'disc_grind': ['1444'], 'shadow_drone': ['2615'],
    'arm_servo': ['1814'], 'arm_creak': ['2799'], 'arm_hydraulic': ['2608'], 'touchdown_boom': ['1686'], 'touchdown_sand': ['2777']}
ids_used = {}
for f, names in used.items():
    key = os.path.splitext(os.path.basename(f))[0]
    for sid in PREP_SRC.get(key, ['?']):
        ids_used.setdefault(sid, []).extend(names)
fsm = json.load(open('audio/sfx/freesound/meta.json'))
for sid in sorted(ids_used, key=lambda s: int(s) if s.isdigit() else 0):
    if sid.startswith('fs'):
        m = fsm[sid[2:]]
        L.append(f'"{m["title"]}" by {m["author"]}, freesound.org sound #{sid[2:]}, {m["license"]}')
        L.append(f'  Page: {m["page"]}   file: {m["file_url"]} (HQ preview, no login)   local: audio/sfx/freesound/fs_{sid[2:]}.mp3')
        L.append(f'  Used as: {", ".join(sorted(set(ids_used[sid])))}' + (' (vinyl surface noise bed)' if sid == 'fs637931' else ' (one locked-groove revolution tick, repeated every 1.8 s = 33 1/3 rpm)'))
        continue
    t, d = titles.get(sid, ('?', '?'))
    nm = sorted(set(ids_used[sid]))
    if len(nm) > 4: nm = nm[:3] + [f'... ({len(nm)} cues)']
    L.append(f'"{t}" ({d}), Mixkit sound effect #{sid}, author not listed by Mixkit, Mixkit Sound Effects Free License')
    L.append(f'  URL: https://assets.mixkit.co/active_storage/sfx/{sid}/{sid}.wav   local: audio/sfx/mixkit/mixkit_sfx_{sid}.wav')
    L.append(f'  Used as: {", ".join(nm)}')
L.append('')
L.append('DOWNLOADED FOR ANALYSIS BUT NOT USED (same licences; listed for completeness)')
L.append('-' * 60)
for f in sorted(glob.glob('audio/music/mixkit/mixkit_*.mp3')):
    mid = re.findall(r'mixkit_(\d+)\.mp3', f)[0]
    if mid in ('1008', '677'): continue
    m = meta.get(mid, {})
    L.append(f'music  "{m.get("name", "?")}" by {m.get("artist", "unknown")} - https://assets.mixkit.co/music/{mid}/{mid}.mp3 - Mixkit Stock Music Free License')
for f in sorted(glob.glob('audio/sfx/mixkit/mixkit_sfx_*.wav')):
    sid = re.findall(r'mixkit_sfx_(\d+)\.wav', f)[0]
    if sid in ids_used or sid == '2285': continue
    t, d = titles.get(sid, ('?', '?'))
    L.append(f'sfx    "{t}" ({d}) - https://assets.mixkit.co/active_storage/sfx/{sid}/{sid}.wav - Mixkit Sound Effects Free License')
for k, m in fsm.items():
    if not m['used']:
        L.append(f'sfx    "{m["title"]}" by {m["author"]} - {m["page"]} - {m["license"]}')
import os
if os.path.exists('audio/sfx/opengameart/oga_vinylstart.mp3'):
    L.append('sfx    "Vinyl" (vinylstart.mp3) by Aidan_Walker - https://opengameart.org/content/vinyl - CC0')
open('audio/credits.txt', 'w', encoding='utf-8').write('\n'.join(L) + '\n')
print('\n'.join(L[:40]))
print('...', len(L), 'lines')
