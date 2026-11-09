#!/usr/bin/env bash
# Build renders/master/f_0001..0708.png for the encode:
#  - hardlinks to renders/final/ (no copies), overridden by re-rendered frames in renders/fix/ when present
#  - S1->S2 whip smear f119-122; S2->S3 match cut: f289-305 dissolve from f288's colour into the S3 opening (geometry already matches,
#    so this reads as a seamless colour transition, not a visible dissolve)
# Never writes through a hardlink: every replaced frame is unlinked first, so renders/final stays untouched.
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"
M=renders/master
rm -rf "$M"; mkdir -p "$M"
n_fix=0
for f in $(seq 1 708); do
  n=$(printf %04d $f); src=renders/final/f_$n.png
  if [ -s renders/fix/f_$n.png ]; then src=renders/fix/f_$n.png; n_fix=$((n_fix+1)); fi
  [ -s "$src" ] || { echo "MISSING $src"; exit 1; }
  ln "$src" "$M/f_$n.png"
done
srcof() { local n=$(printf %04d $1); [ -s renders/fix/f_$n.png ] && echo renders/fix/f_$n.png || echo renders/final/f_$n.png; }
# S1->S2 cut: vertical whip smear (camera rises along the cantilever) + slight lift, hides the hard luma jump
for p in "119 6 0.00" "120 22 0.03" "121 22 0.03" "122 8 0.00"; do
  set -- $p; n=$(printf %04d $1); src=$(srcof $1)
  rm -f "$M/f_$n.png"
  ffmpeg -y -hide_banner -loglevel error -i "$src" \
    -vf "format=gbrp16le,gblur=sigma=0.5:sigmaV=$2:steps=3,eq=brightness=$3,format=rgb48be" -frames:v 1 "$M/f_$n.png"
done
# S2->S3 match cut: f289-305 are a static hold on the same marble, so a 17-frame dissolve from f288's grade
# reads as a slow colour shift (no visible pop on the downbeat)
A=$(srcof 288)
for k in $(seq 289 305); do
  n=$(printf %04d $k); w=$(awk "BEGIN{printf \"%.4f\", (306-$k)/18}")
  B=$( [ -s renders/fix/f_$n.png ] && echo renders/fix/f_$n.png || echo renders/final/f_$n.png )
  rm -f "$M/f_$n.png"
  ffmpeg -y -hide_banner -loglevel error -i "$A" -i "$B" -filter_complex \
    "[0]format=gbrp16le[a];[1]format=gbrp16le[b];[a][b]blend=all_expr='A*${w}+B*(1-${w})',format=rgb48be" \
    -frames:v 1 "$M/f_$n.png"
done
echo "MASTER_OK 708 frames, $n_fix from renders/fix, whip f119-122, match-cut grade blend f289-305"
