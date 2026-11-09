#!/usr/bin/env bash
# Assemble NEEDLE DROP: frames 1-708 + 12 black frames (709-720), 6-frame fade-in, mux audio/mix.wav.
# Usage: tools/assemble.sh [frames_prefix=renders/final/f_] [outdir=delivery] [first=1] [count=708]
# Outputs: <outdir>/NEEDLE_DROP_1440p.mp4  (H.264 High, grain)    — main upload file
#          <outdir>/NEEDLE_DROP_4K.mp4     (H.264, Lanczos 3840x2160 + mild sharpen, grain)
#          <outdir>/NEEDLE_DROP_4K_HEVC10.mp4 (H.265 10-bit, same picture as 4K)
# ffmpeg runs at low priority with 8 threads so the laptop stays usable.
set -e
FR="${1:-renders/final/f_}"; OUT="${2:-delivery}"; FIRST="${3:-1}"; COUNT="${4:-708}"
mkdir -p "$OUT"
DUR=$(awk "BEGIN{print ($COUNT+12)/24}")
PAD="trim=end_frame=${COUNT},setpts=PTS-STARTPTS,fade=t=in:st=0:d=0.25,tpad=stop=12:color=black"
GRAIN="noise=c0s=3:c0f=t+u,setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709"
TAGS="-color_primaries bt709 -color_trc bt709 -colorspace bt709"
AUDIO=audio/mix_final.wav; [ -s "$AUDIO" ] || AUDIO=audio/mix.wav
# -reinit_filter 0: the sequence mixes 8-bit and 16-bit PNGs; without it ffmpeg rebuilds the graph at each
# pixel-format change, setpts restarts at 0 and the CFR output silently drops frames (lost 278 of 720 once).
IN=(-framerate 24 -start_number "$FIRST" -reinit_filter 0 -i "${FR}%04d.png" -i "$AUDIO")
nice -n 10 ffmpeg -y -hide_banner -loglevel error "${IN[@]}" \
  -filter_complex "[0:v]${PAD},${GRAIN},format=yuv420p[v]" -map "[v]" -map 1:a -t "$DUR" \
  -c:v libx264 -preset slow -crf 16 -tune film -profile:v high -threads 8 $TAGS -movflags +faststart \
  -c:a aac -b:a 320k -ar 48000 "$OUT/NEEDLE_DROP_1440p.mp4"
nice -n 10 ffmpeg -y -hide_banner -loglevel error "${IN[@]}" \
  -filter_complex "[0:v]${PAD},scale=3840:2160:flags=lanczos,unsharp=5:5:0.35:5:5:0,${GRAIN},format=yuv420p[v]" -map "[v]" -map 1:a -t "$DUR" \
  -c:v libx264 -preset medium -crf 18 -tune film -profile:v high -level 5.1 -threads 8 $TAGS -movflags +faststart \
  -c:a aac -b:a 320k -ar 48000 "$OUT/NEEDLE_DROP_4K.mp4"
nice -n 10 ffmpeg -y -hide_banner -loglevel error "${IN[@]}" \
  -filter_complex "[0:v]${PAD},scale=3840:2160:flags=lanczos,unsharp=5:5:0.35:5:5:0,${GRAIN},format=yuv420p10le[v]" -map "[v]" -map 1:a -t "$DUR" \
  -c:v libx265 -preset fast -crf 17 -tag:v hvc1 -x265-params "log-level=error:pools=8" $TAGS -movflags +faststart \
  -c:a aac -b:a 320k -ar 48000 "$OUT/NEEDLE_DROP_4K_HEVC10.mp4"
for f in "$OUT"/NEEDLE_DROP_*.mp4; do
  echo "== $f"; ffprobe -v error -show_entries format=duration,size,bit_rate:stream=codec_name,width,height,pix_fmt,r_frame_rate -of compact "$f"
done
echo ASSEMBLE_OK
# hard check: every file must have exactly COUNT+12 video frames
bad=0
for f in "$OUT"/NEEDLE_DROP_*.mp4; do
  nf=$(ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of csv=p=0 "$f" | tr -d '\r')
  echo "FRAMES $f $nf"; [ "$nf" = "$((COUNT+12))" ] || bad=1
done
[ $bad = 0 ] && echo FRAMECHECK_OK || { echo FRAMECHECK_FAILED; exit 1; }
