#!/usr/bin/env bash
# Chunked, resumable sequence render through the safe runner.
# Usage: tools/render_seq.sh <blend> <first> <last> <out_prefix> [chunk=24] [extra render_frames.py args...]
#   e.g. tools/render_seq.sh blend/set_b.blend 121 288 renders/final/f_ 24
#        tools/render_seq.sh blend/set_c.blend 289 708 renders/previz/f_ 48 --pct 37 --samples 6 --nomb
# - Each chunk is one Blender run (brun --render): the lock is released between chunks so other jobs can interleave.
# - Frames that already exist are skipped (resume after a crash/kill costs at most one chunk).
# - Per-frame times go to logs/render_seq.log.
BLEND="$1"; S="$2"; E="$3"; OUT="$4"; CH="${5:-24}"; shift 5
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"
mkdir -p "$(dirname "$OUT")" logs
LOG=logs/render_seq.log
echo "[$(date +%H:%M:%S)] START $BLEND $S-$E -> $OUT chunk=$CH $*" >> "$LOG"
for ((a=S; a<=E; a+=CH)); do
  b=$((a+CH-1)); [ $b -gt $E ] && b=$E
  missing=0
  for ((f=a; f<=b; f++)); do [ -s "${OUT}$(printf %04d $f).png" ] || { missing=1; break; }; done
  [ $missing = 0 ] && continue
  tools/brun.sh --threads 8 --render -- "$BLEND" --python tools/render_frames.py -- \
      --frames "$a-$b" --out "$OUT" --skip-existing "$@" 2>&1 \
    | grep --line-buffered -E "^FRAME|RENDER_DONE|Error|Traceback|brun" \
    | sed -u "s#^#[$(date +%H:%M:%S)] $(basename "$BLEND") #" >> "$LOG"
  sleep 8
done
n=0; for ((f=S; f<=E; f++)); do [ -s "${OUT}$(printf %04d $f).png" ] && n=$((n+1)); done
echo "[$(date +%H:%M:%S)] END $BLEND $S-$E: $n/$((E-S+1)) frames present" >> "$LOG"
echo "SEQ_DONE $BLEND $n/$((E-S+1))"
