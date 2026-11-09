#!/usr/bin/env bash
# Verify an encoded film against renders/master: frame count, and PSNR of sampled decoded frames vs the master PNG
# at the SAME index (a wrong/missing frame shows up as low PSNR). Usage: tools/verify_encode.sh <file.mp4>
F="$1"; T=$(mktemp -d)
nf=$(ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of csv=p=0 "$F" | tr -d '\r')
echo "frames: $nf (expect 720)"
for k in 10 100 121 160 240 285 289 300 315 400 433 470 560 650 697 708; do
  ffmpeg -y -v error -i "$F" -vf "select=eq(n\,$((k-1))),scale=640:360" -frames:v 1 "$T/e.png"
  ffmpeg -y -v error -i renders/master/f_$(printf %04d $k).png -vf "scale=640:360" "$T/m.png"
  p=$(ffmpeg -hide_banner -i "$T/e.png" -i "$T/m.png" -lavfi psnr -f null - 2>&1 | grep -o "average:[0-9.inf]*" | cut -d: -f2)
  echo "frame $k psnr $p"
done
ffmpeg -y -v error -i "$F" -vf "select=eq(n\,714),signalstats,metadata=print:key=lavfi.signalstats.YAVG" -f null - 2>&1 | grep -o "YAVG=[0-9.]*" | sed 's/^/frame 715 (tail) /'
rm -rf "$T"
