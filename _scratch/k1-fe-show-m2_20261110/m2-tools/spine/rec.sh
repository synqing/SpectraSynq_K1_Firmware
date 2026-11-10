#!/bin/bash
# rec.sh LABEL CMD... : run once, record command line, exit code and combined output to raw/LABEL.log
EV=/Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/k1-fe-show-m2_20261110/m2-tools/spine
label="$1"; shift
{ echo "# cwd: $(pwd)"; echo "# cmd: $*"; echo "# start: $(date -u +%FT%TZ)"; } > "$EV/raw/$label.log"
"$@" >> "$EV/raw/$label.log" 2>&1
rc=$?
{ echo "# exit: $rc"; echo "# end: $(date -u +%FT%TZ)"; } >> "$EV/raw/$label.log"
echo "$label exit=$rc"
exit $rc
