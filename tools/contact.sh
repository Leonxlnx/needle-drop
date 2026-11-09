#!/usr/bin/env bash
# Contact sheet from PNGs (in the given order), each tile labelled with its filename.
# Usage: tools/contact.sh <out.png> <cols> <tile_width> <img1.png> [img2.png ...]
OUT="$(realpath -m "$1")"; COLS="$2"; TW="$3"; shift 3
N=$#; ROWS=$(( (N + COLS - 1) / COLS ))
TMP=$(mktemp -d)
cp /c/Windows/Fonts/arial.ttf "$TMP/f.ttf"
i=0
for f in "$@"; do
  src="$(realpath "$f")"; name=$(basename "$f" .png)
  ( cd "$TMP" && ffmpeg -y -hide_banner -loglevel error -i "$src" -vf "scale=${TW}:-2,drawtext=fontfile=f.ttf:text='${name}':x=8:y=8:fontsize=18:fontcolor=white:box=1:boxcolor=black@0.6" "$(printf %04d $i).png" )
  i=$((i+1))
done
ffmpeg -y -hide_banner -loglevel error -framerate 1 -i "$TMP/%04d.png" -vf "tile=${COLS}x${ROWS}:padding=4:color=black" -frames:v 1 "$OUT"
rm -rf "$TMP"
echo "CONTACT $OUT"
