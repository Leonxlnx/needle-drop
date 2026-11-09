#!/usr/bin/env bash
# Encode a PNG frame sequence + mixed audio into the final film.
# Usage: tools/encode.sh <frames_glob_pattern e.g. renders/final/f_%04d.png> <audio.wav> <out.mp4> [fps=24] [grain=3]
# Runs ffmpeg at below-normal priority with capped threads so the laptop stays usable.
set -e
FR="$1"; AU="$2"; OUT="$3"; FPS="${4:-24}"; GRAIN="${5:-3}"
VF="noise=c0s=${GRAIN}:c0f=t+u:c1s=0:c2s=0,format=yuv420p"
nice -n 10 ffmpeg -y -hide_banner -loglevel error -framerate "$FPS" -i "$FR" -i "$AU" \
  -map 0:v -map 1:a -vf "$VF" -c:v libx264 -preset slow -crf 14 -tune film -profile:v high -threads 8 \
  -color_primaries bt709 -color_trc bt709 -colorspace bt709 -movflags +faststart \
  -c:a aac -b:a 320k -ar 48000 -shortest "$OUT"
ffprobe -v error -show_entries format=duration,bit_rate:stream=codec_name,width,height,r_frame_rate -of compact "$OUT"
