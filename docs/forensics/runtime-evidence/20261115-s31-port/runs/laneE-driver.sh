#!/usr/bin/env bash
# laneE driver: serial G1 -> S3 emulator run -> S31 emulator run -> cross-chip compare.
# No tool, tolerance or scenario is changed. Every stage writes its own log and exit-code file in $E.
# GIT_CEILING_DIRECTORIES stops git inside an export from discovering the enclosing worktree
# (the exports live under the worktree's _scratch/); a normal clean export has no repository above it.
set -u
R=/Users/spectrasynq/SpectraSynq_K1_Firmware-s31
E=$R/_scratch/s31-port-20261115/laneE
BASE=fcdefec5
LANE=7a36f8c7
LANEFULL=7a36f8c78155c305d647d4832af59159f18a573a
export GIT_CEILING_DIRECTORIES=$E
export K1_ESP_EMU=/Users/spectrasynq/Workspace_Management/Software/SpectraSynq-ESP-Emulator/tools/esp-emu-pin/bin/esp-emu
GATE=scripts/regression-harness/mic_stable_byte_gate.sh
REF=scripts/regression-harness/results/mic_stable_byte_gate.reference
cd "$E" || exit 9
stamp() { echo "[$(date '+%F %T')] $*"; }

export_tree() {  # $1 = dir, $2 = commit
  mkdir "$1" && /usr/bin/git -C "$R" archive "$2" | tar -x -C "$1" \
    && mkdir -p "$1/.pio" && cp -cR "$R/.pio/libdeps" "$1/.pio/libdeps"
}

# ---------------- G1 ----------------
stamp "G1 step2: base ($BASE) --update in $E/g1 (already exported)"
( cd "$E/g1" && bash "$GATE" --update k1_fe k1_main_rpl_im69d ) > "$E/g1-base-update.log" 2>&1
echo $? > "$E/g1-base-update.rc"
stamp "G1 base update rc=$(cat "$E/g1-base-update.rc")"
G1_OK=0
if [ "$(cat "$E/g1-base-update.rc")" = "0" ] && [ "$(wc -l < "$E/g1/$REF" | tr -d ' ')" = "2" ] \
   && /usr/bin/grep -q '^k1_fe ' "$E/g1/$REF" && /usr/bin/grep -q '^k1_main_rpl_im69d ' "$E/g1/$REF"; then
  cp "$E/g1/$REF" "$E/g1-base.reference"
  G1_OK=1
else
  stamp "G1 base reference NOT valid (rc or content); G1 lane check will not run"
fi
if [ "$G1_OK" = 1 ]; then
  stamp "G1 step3: move base tree, export lane ($LANE) at the same path"
  mv "$E/g1" "$E/g1-base-tree" && export_tree "$E/g1" "$LANE" \
    && cp "$E/g1-base.reference" "$E/g1/$REF"
  echo $? > "$E/g1-setup.rc"
  stamp "G1 step4: lane check"
  ( cd "$E/g1" && bash "$GATE" k1_fe k1_main_rpl_im69d ) > "$E/g1-lane-check.log" 2>&1
  echo $? > "$E/g1-lane-check.rc"
  stamp "G1 lane check rc=$(cat "$E/g1-lane-check.rc")"
fi

# ---------------- exports for G2/G3 ----------------
stamp "step5: exports run-s3 and run-s31 at $LANE"
for d in run-s3 run-s31; do
  export_tree "$E/$d" "$LANE"
  printf '{"commit": "%s", "branch": "lane/k1-s31-port"}\n' "$LANEFULL" > "$E/$d/.k1-source-identity.json"
done
if [ -e "$E/run-s31/targets/esp32s31/managed_components" ]; then
  stamp "managed_components already present in export (tracked); not copying"
else
  cp -cR "$R/targets/esp32s31/managed_components" "$E/run-s31/targets/esp32s31/managed_components" \
    || stamp "managed_components copy FAILED (build will download)"
fi

# ---------------- G2/G3: one after the other ----------------
stamp "step6: S3 run start"
( cd "$E/run-s3" && python3 tools/esp_emulator/run.py --scenario tools/esp_emulator/s3_music_regression.json \
    --profile fe --output "$E/out-s3" ) > "$E/run-s3.log" 2>&1
echo $? > "$E/run-s3.rc"
stamp "S3 run rc=$(cat "$E/run-s3.rc")"

stamp "step6: S31 run start"
( cd "$E/run-s31" && python3 tools/esp_emulator/run.py --scenario tools/esp_emulator/s31_music_regression.json \
    --profile fe --output "$E/out-s31" ) > "$E/run-s31.log" 2>&1
echo $? > "$E/run-s31.rc"
stamp "S31 run rc=$(cat "$E/run-s31.rc")"

stamp "step8: cross-chip compare"
python3 "$E/run-s31/tools/esp_emulator/cross_chip_compare.py" --base "$E/out-s3" --other "$E/out-s31" \
  --output "$E/cross-chip.json" > "$E/cross-chip.log" 2>&1
echo $? > "$E/cross-chip.rc"
stamp "cross-chip rc=$(cat "$E/cross-chip.rc")"
stamp "DRIVER DONE"
echo done > "$E/driver.done"
