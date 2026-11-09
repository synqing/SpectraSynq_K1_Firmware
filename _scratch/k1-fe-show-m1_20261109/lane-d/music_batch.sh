#!/usr/bin/env bash
# Lane D music-in-room runs (Captain-approved 9 Nov: both conditions; Bose speaker at CURRENT volume).
# Live baseline (music only), three prepared runs, one rejected (hz0) run. Each: LED capture + a7S III.
# The player refuses if other audio is playing; it never changes volume and stops audio on exit.
set -u
cd "$(dirname "$0")"
PY=/opt/homebrew/opt/python@3.13/bin/python3.13
D=$PWD/runs
STREAM=stream/loreen_75_155_120hz_v2.prsm
ASSET=/Users/spectrasynq/Downloads/Loreen-My-Heart-Is-Refusing-Me.mp3
COMMON=(--stream "$STREAM" --asset "$ASSET" --allow-line "[AP]" --start-delay-s 1)
run() {  # name, extra player args...
  local name=$1; shift
  if pgrep -x afplay >/dev/null; then echo "$name SKIPPED: other audio playing"; return; fi
  $PY run_one.py "$name" 92 -- "${COMMON[@]}" --log "$D/$name/player.jsonl" "$@" > "$D/.$name.out" 2>&1
  echo "$name rc=$?"
  tail -c 400 "$D/$name/player.stdout.txt" 2>/dev/null | tail -3
  $PY -c "import json;d=json.load(open('$D/$name/dump.npz.json'));print({k:d[k] for k in ['frames_decoded','missing_indices','crc_ok','modes','mean_luma']})" 2>&1 | tail -1
  sleep 3
}
run M0_m32_live_music --audio-only
run M1_m32_authored_music --port /dev/cu.usbmodem11301
run M2_m32_authored_music --port /dev/cu.usbmodem11301
run M3_m32_authored_music --port /dev/cu.usbmodem11301
run M4_m32_rejected_hz0_music --port /dev/cu.usbmodem11301 --rejected hz0
pgrep -lx afplay || echo "no afplay running"
echo BATCH_DONE
