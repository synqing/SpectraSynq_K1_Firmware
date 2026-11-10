#!/bin/bash
# Re-export each cold run's contract with Trinity HEAD (export_contract only; no re-analysis).
# The contract is a pure function of analysis.json + the WAV's duration. analysis.json names its
# WAV by the run's work path, so work/<view> is pointed at the run directory while exporting.
# Output: runs/<run>/contract.json is kept; the new one is runs/<run>/contract_<head>.json.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
PY="$HERE/env-trinity-repro-20261110/bin/python"
A=/Users/spectrasynq/Workspace_Management/Software/Trinity/analysis
HEAD=$(/usr/bin/git -C "$A" rev-parse --short HEAD)
test -z "$(/usr/bin/git -C "$A" status --porcelain)" || { echo "Trinity tree not clean" >&2; exit 2; }
for run in excerpt_A excerpt_B full_A full_B; do
  view=${run%_*}
  rm -f "$HERE/work/$view"; mkdir -p "$HERE/work"
  ln -s "$HERE/runs/$run" "$HERE/work/$view"
  PYTHONPATH="$A/vendor/allin1/src:$A" "$PY" -c "from export_contract import export_contract; export_contract('$HERE/work/$view/analysis.json', '$HERE/runs/$run/contract_$HEAD.json', tier='k1-lite', audio_path='$HERE/work/$view/audio/track.wav')"
  rm "$HERE/work/$view"
  shasum -a 256 "$HERE/runs/$run/contract_$HEAD.json"
done
