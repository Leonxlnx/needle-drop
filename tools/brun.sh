#!/usr/bin/env bash
# Resource-safe Blender runner. ALL pipeline Blender launches go through this.
# Usage: tools/brun.sh [--threads N] [--minfree GB] [--render] -- <blender args...>
#   --render : this job renders on the GPU -> waits (max BRUN_MAXWAIT s, default 600) while the user's own Blender is heavy on the GPU.
# Guarantees:
# - Only one pipeline Blender at a time (lock dir). Never touches Blender processes we did not start.
# - Waits until free RAM >= minfree before starting.
# - If the user's own Blender is busy: we drop to 4 threads; render jobs also wait (max 10 min) while it uses >30% of the GPU.
# - Runs at BelowNormal priority with capped render threads.
# - Watchdog kills ONLY this job if free RAM drops under 5 GB.
B="/e/experimentswithclaude/tools/blender/blender-5.2.2-windows-x64/blender.exe"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOCK="$ROOT/logs/.blender.lock"
OURS="$ROOT/logs/our_pids.txt"
LOG="$ROOT/logs/brun.log"
THREADS=8; MINFREE=${BRUN_MINFREE:-16}; RENDER=0
while [ "$1" != "--" ] && [ -n "$1" ]; do
  case "$1" in --threads) THREADS="$2"; shift 2;; --minfree) MINFREE="$2"; shift 2;; --render) RENDER=1; shift;; *) shift;; esac
done
shift
mkdir -p "$ROOT/logs"; touch "$OURS"
log() { echo "[$(date +%H:%M:%S)] $*" >> "$LOG"; echo "[brun] $*" >&2; }
freegb() { powershell -NoProfile -Command "[math]::Floor((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB)" 2>/dev/null | tr -d '\r'; }
foreign() { powershell -NoProfile -ExecutionPolicy Bypass -File "$(cygpath -w "$ROOT/tools/foreign.ps1")" -OursFile "$(cygpath -w "$OURS")" 2>/dev/null | tr -d '\r'; }
gpu_of() { echo "$1" | sed -n 's/.*gpu3d=\([0-9]*\).*/\1/p'; }
# acquire lock (stale lock if holder pid gone)
while ! mkdir "$LOCK" 2>/dev/null; do
  holder=$(cat "$LOCK/pid" 2>/dev/null)
  if [ -n "$holder" ] && ! powershell -NoProfile -Command "if(Get-Process -Id $holder -ErrorAction SilentlyContinue){exit 0}else{exit 1}" >/dev/null 2>&1; then
    age=$(( $(date +%s) - $(stat -c %Y "$LOCK" 2>/dev/null || date +%s) ))
    if [ "$age" -gt 60 ]; then rm -rf "$LOCK"; continue; fi
  fi
  sleep 5
done
MYPID=$(cat /proc/$$/winpid 2>/dev/null); echo "$MYPID" > "$LOCK/pid"   # live pid of this waiting shell, so waits never look stale
trap 'h=$(cat "$LOCK/pid" 2>/dev/null); if [ "$h" = "$MYPID" ] || [ "$h" = "$wpid" ]; then rm -rf "$LOCK"; fi' EXIT
while :; do f=$(freegb); [ -n "$f" ] && [ "$f" -ge "$MINFREE" ] && break; log "waiting: free RAM ${f}GB < ${MINFREE}GB"; sleep 20; done
fs=$(foreign)
if [[ "$fs" == BUSY* ]]; then
  if [ "$RENDER" = 1 ]; then
    waited=0
    while [[ "$fs" == BUSY* ]] && [ "$(gpu_of "$fs")" -gt 30 ] 2>/dev/null && [ $waited -lt ${BRUN_MAXWAIT:-600} ]; do
      log "user Blender heavy on GPU ($fs) - render waiting"; sleep 60; waited=$((waited+60)); fs=$(foreign)
    done
  fi
  if [[ "$fs" == BUSY* ]]; then BT=${BRUN_BUSY_THREADS:-8}; THREADS=$(( THREADS < BT ? THREADS : BT )); log "user Blender busy ($fs) - running with $THREADS threads"; fi
fi
"$B" -b --factory-startup -noaudio -t "$THREADS" "$@" &
mpid=$!
wpid=$(cat /proc/$mpid/winpid 2>/dev/null)
echo "$wpid" > "$LOCK/pid"; echo "$wpid" >> "$OURS"
powershell -NoProfile -Command "try{(Get-Process -Id $wpid).PriorityClass='BelowNormal'}catch{}" >/dev/null 2>&1
( while kill -0 $mpid 2>/dev/null; do
    f=$(freegb)
    if [ -n "$f" ] && [ "$f" -lt 5 ]; then log "WATCHDOG: free RAM ${f}GB, killing our Blender $wpid"; taskkill //PID "$wpid" //T //F >/dev/null 2>&1; break; fi
    sleep 10
  done ) &
wait $mpid; rc=$?
exit $rc
