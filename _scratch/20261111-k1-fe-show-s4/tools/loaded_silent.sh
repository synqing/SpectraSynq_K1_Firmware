#!/usr/bin/env bash
# Loaded silent run on the Main RPL (R3-1 acceptance; K1-FE-SHOW lead session 4, 11 Nov 2026).
# No audio. The Mac is deliberately loaded (8 CPU burners, killed by PID afterwards) while the prepared
# Loreen stream is sent; late frames are skipped by the sender. Pass = the show epoch rises by exactly 1
# (one session, no mid-show reset). Epochs from :authored_status before and after (after = unlock step).
# Usage: loaded_silent.sh <run name>
set -u
NAME=$1
L=/Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/k1-fe-show-m1_20261109/lane-d
OUT=/Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/20261111-k1-fe-show-s4/bench/$NAME
PY=/opt/homebrew/opt/python@3.13/bin/python3.13
export K1_UNIT=rpl
mkdir -p "$OUT"; cd "$L" || exit 2
$PY k1_bench.py cmd "$OUT/status-before.txt" ":authored_status" || exit 3
PIDS=()
for i in $(seq 1 "${BURN:-8}"); do yes > /dev/null & PIDS+=($!); done
echo "burners ${PIDS[*]}" > "$OUT/load.txt"; sysctl -n vm.loadavg >> "$OUT/load.txt"
$PY silent_stream.py ../lane-c-emu/stream/loreen_75_155_120hz_v2.prsm "$OUT/stream.jsonl" > "$OUT/sender.out" 2>&1
echo "sender rc=$?" >> "$OUT/sender.out"
sysctl -n vm.loadavg >> "$OUT/load.txt"
kill "${PIDS[@]}" 2>/dev/null; wait "${PIDS[@]}" 2>/dev/null
$PY k1_bench.py unlock "$OUT/unlock.txt"; echo "unlock rc=$?" >> "$OUT/sender.out"
b=$(/usr/bin/grep -o 'AUTHORED_STATUS state=[0-9]* epoch=[0-9]*' "$OUT/status-before.txt" | tail -1 | /usr/bin/grep -o 'epoch=[0-9]*' | cut -d= -f2)
a=$(/usr/bin/grep -o 'AUTHORED_STATUS state=[0-9]* epoch=[0-9]*' "$OUT/unlock.txt" | tail -1 | /usr/bin/grep -o 'epoch=[0-9]*' | cut -d= -f2)
echo "epoch before=$b after=$a rise=$((a-b))" | tee "$OUT/verdict.txt"
tail -1 "$OUT/stream.jsonl" | cut -c1-300 >> "$OUT/verdict.txt"
