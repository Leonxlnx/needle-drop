#!/usr/bin/env bash
# NEEDLE DROP audio stage: rebuild everything from the downloaded recordings, in order. Run from the project root:
#   bash audio/scripts/build_audio.sh
# Deterministic. Uses Blender's bundled Python in isolated mode (-I) for numpy; ffmpeg/ffprobe and node from PATH.
# THE DELIVERY MIX IS audio/mix.wav (bible 5.6). audio/_work/mixjs_reference.wav is a reference render only: never mux it.
set -e
PY="${ND_PY:-/e/experimentswithclaude/tools/blender/blender-5.2.2-windows-x64/5.2/python/bin/python.exe}"
"$PY" -I audio/scripts/edit_music.py          # -> audio/music_edit.wav, audio/_work/music_ducked.wav (+ _work/music_stem_mixjs.wav, music_edit_map.json)
"$PY" -I audio/scripts/audio_analyze.py       # -> data/beats.json, data/bands.json, data/timing.json (snapped from audio/_work/timing_orig.json)
"$PY" -I audio/scripts/build_cues.py          # -> audio/sfx/prep/*.wav, audio/cues.json (sand hiss reads the validated kicks; sub layers aligned to the kicks)
node tools/mix.js audio/cues.json audio/_work/mixjs_reference.wav   # literal tools/mix.js render: REFERENCE ONLY (its loudnorm is an AGC)
"$PY" -I audio/scripts/master_linear.py       # -> audio/mix.wav  (THE DELIVERY MIX)
"$PY" -I audio/scripts/write_credits.py > /dev/null   # -> audio/credits.txt
"$PY" -I audio/scripts/measure.py audio/mix.wav --arc --json audio/_work/measure_v3.json
"$PY" -I audio/scripts/check_details.py audio/mix.wav
"$PY" -I audio/scripts/hero_check.py audio/mix.wav --json audio/_work/hero_check.json
echo AUDIO_BUILD_OK
