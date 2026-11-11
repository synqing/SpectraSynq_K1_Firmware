#!/usr/bin/env bash
# Camera A/B on the Main RPL (K1-FE-SHOW lead session 5, 12 Nov 2026): the plate filmed by the Sony a7S III
# live view while Loreen 75-155 s plays at 10 dB under the Captain's volume (player --gain-db -10; Mac volume
# never touched). Same audio path as bench_ab.sh; no rtrace, no telemetry (the port is only used for the
# switch commands, each through k1_bench.py's identity check).
# Usage: cam_ab.sh <run name> <command> [command ...]     e.g. cam_ab.sh m14_off :set_mode=14 :k1_afe_spec=off
set -u
NAME=$1; shift
T=/Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/20261111-k1-fe-show-s5/tools
L=/Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/k1-fe-show-m1_20261109/lane-d
OUT=/Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/20261111-k1-fe-show-s5/camera/$NAME
PY=/opt/homebrew/opt/python@3.13/bin/python3.13
PPY=$L/../lane-c-emu/.venv/bin/python
PLAYER=$L/../lane-c-emu/player/show_player.py
ASSET=/Users/spectrasynq/Downloads/Loreen-My-Heart-Is-Refusing-Me.mp3
export K1_UNIT=rpl
mkdir -p "$OUT"; cd "$L" || exit 2
if pgrep -x afplay >/dev/null; then echo "REFUSED: other audio playing"; exit 2; fi
i=0
for c in "$@"; do i=$((i+1)); $PY k1_bench.py cmd "$OUT/set$i.txt" "$c" || { echo "command $c failed"; exit 3; }; done
$PY -u $T/cam_capture.py "$OUT" 88 > "$OUT/cam.out" 2>&1 &
CP=$!
sleep 3
( cd "$L/../lane-c-emu" && $PPY "$PLAYER" --stream stream/loreen_75_155_120hz_v2.prsm --asset "$ASSET" \
  --start-delay-s 1 --audio-only --gain-db -10 --log "$OUT/player.jsonl" ) > "$OUT/player.out" 2>&1
echo "player rc=$?" >> "$OUT/player.out"
wait $CP
pgrep -lx afplay || echo "no afplay running" >> "$OUT/player.out"
echo "DONE $NAME $(cat $OUT/cam.out | tail -1)"
