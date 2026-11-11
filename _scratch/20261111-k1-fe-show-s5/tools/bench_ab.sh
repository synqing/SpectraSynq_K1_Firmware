#!/usr/bin/env bash
# Bench A/B on the Main RPL (K1-FE-SHOW lead session 4, 11 Nov 2026; session 5 copy writes under 20261111-k1-fe-show-s5). Same steps as session 3's B_M1 runs:
#   one switch command, :rtrace_arm=92,6, read-only telemetry for 88 s, Loreen 75-155 s on the speaker at
#   10 dB under the Captain's volume (player --gain-db -10; Mac volume never touched), then :rtrace_dump.
# Usage: bench_ab.sh <run name> <switch command, e.g. :k1_afe_silence=off> [extra command]
# Refuses if any other audio is playing. Each step opens and closes the port (k1_bench.py identity check).
set -u
NAME=$1; shift
L=/Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/k1-fe-show-m1_20261109/lane-d
OUT=/Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/20261111-k1-fe-show-s5/bench/$NAME
PY=/opt/homebrew/opt/python@3.13/bin/python3.13
PPY=$L/../lane-c-emu/.venv/bin/python
PLAYER=$L/../lane-c-emu/player/show_player.py
ASSET=/Users/spectrasynq/Downloads/Loreen-My-Heart-Is-Refusing-Me.mp3
export K1_UNIT=rpl
mkdir -p "$OUT"; cd "$L" || exit 2
if pgrep -x afplay >/dev/null; then echo "REFUSED: other audio playing"; exit 2; fi
i=0
for c in "$@"; do i=$((i+1)); $PY k1_bench.py cmd "$OUT/set$i.txt" "$c" || { echo "command $c failed"; exit 3; }; done
$PY k1_bench.py arm "$OUT/arm.txt" 92 6 || exit 3
$PY listen.py "$OUT/ap.jsonl" "${LISTEN_S:-88}" > "$OUT/listen.out" 2>&1 &
LP=$!
( cd "$L/../lane-c-emu" && $PPY "$PLAYER" --stream stream/loreen_75_155_120hz_v2.prsm --asset "$ASSET" --allow-line "[AP]" \
  --start-delay-s 1 --audio-only --gain-db -10 --log "$OUT/player.jsonl" ) > "$OUT/player.out" 2>&1
echo "player rc=$?" >> "$OUT/player.out"
wait $LP
$PY k1_bench.py dump "$OUT/dump" ; echo "dump rc=$?" > "$OUT/dump.rc"
pgrep -lx afplay || echo "no afplay running" >> "$OUT/player.out"
echo "DONE $NAME"
