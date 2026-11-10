#!/bin/zsh
# run_real.sh — the full M2 lane C loop on the real recording. Each step runs once via rec.sh.
# Args: CONTRACT STEM_FEATURES NAME ASSET_JSON
set -e
M=/Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/k1-fe-show-m2_20261110/m2-compose
cd $M
C=$1; S=$2; NAME=$3; ASSET=$4
P=projects/$NAME; N=/opt/homebrew/bin/node; PY=/opt/homebrew/opt/python@3.13/bin/python3.13
LB=/Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/k1-fe-show-m1_20261109/lane-b
mkdir -p $P/inputs $P/mapping $P/stream $P/stream_reopen $P/diff
cp $C $P/inputs/contract.json; cp $S $P/inputs/stem_features.json
cp $ASSET $P/inputs/asset.json
print 3d521f5d0f9c06ab3e46222f74b92600c802d217324d2ac45a14d9772a8b43fd > $P/inputs/contract_schema.sha256
cp /Users/spectrasynq/Workspace_Management/Software/SpectraSynq-Instrument-Spine/mapping/prim8_natural_v1.json $P/mapping/
shasum -a 256 $C $P/inputs/contract.json $S $P/inputs/stem_features.json > raw/r0_${NAME}_input_copies.sha256
tools/rec.sh r1_${NAME}_init $N tools/compose.mjs init --project $P/composition.json --contract $P/inputs/contract.json --stems $P/inputs/stem_features.json --schema-sha-file $P/inputs/contract_schema.sha256 --profile $P/mapping/prim8_natural_v1.json
cp $P/composition.json $P/composition.pre_edit.snapshot.json
tools/rec.sh r2_${NAME}_compile_pre_edit $N tools/compose.mjs compile --project $P/composition.json --out $P/out/pre_edit --record
tools/rec.sh r3_${NAME}_stream_pre_edit $PY tools/make_stream.py --run $P/out/pre_edit/run-a --project $P/composition.json --asset-json $P/inputs/asset.json --out $P/stream/${NAME}_pre_edit_120hz.prsm
tools/rec.sh r4_${NAME}_edit $N tools/compose.mjs edit --project $P/composition.json --set 'prim8.impact.transform.beat_amp_u16=12000' --id prim8_natural_v1_bar_accent --version 1.0.0-m2c.1 --note "Bar accent: off-downbeat beat pulses 48000->12000 so impact marks the bar; downbeats unchanged." --out-profile mapping/prim8_natural_v1_bar_accent.json
/usr/bin/diff -u $P/composition.pre_edit.snapshot.json $P/composition.json > raw/r4_${NAME}_composition_diff.patch || true
tools/rec.sh r5_${NAME}_compile_post_edit $N tools/compose.mjs compile --project $P/composition.json --out $P/out/post_edit --record
tools/rec.sh r6_${NAME}_stream_post_edit $PY tools/make_stream.py --run $P/out/post_edit/run-a --project $P/composition.json --asset-json $P/inputs/asset.json --out $P/stream/${NAME}_post_edit_120hz.prsm
tools/rec.sh r7_${NAME}_reopen_verify $N tools/compose.mjs verify --project $P/composition.json --out $P/out/reopen
tools/rec.sh r8_${NAME}_stream_reopen $PY tools/make_stream.py --run $P/out/reopen/run-a --project $P/composition.json --asset-json $P/inputs/asset.json --out $P/stream_reopen/${NAME}_post_edit_120hz.prsm
{ shasum -a 256 $P/stream/${NAME}_post_edit_120hz.prsm* $P/stream_reopen/${NAME}_post_edit_120hz.prsm*
  cmp $P/stream/${NAME}_post_edit_120hz.prsm $P/stream_reopen/${NAME}_post_edit_120hz.prsm && cmp $P/stream/${NAME}_post_edit_120hz.prsm.json $P/stream_reopen/${NAME}_post_edit_120hz.prsm.json && print REOPEN_STREAM_IDENTICAL; } > raw/r8_${NAME}_reopen_stream_sha.txt 2>&1
/bin/cat raw/r8_${NAME}_reopen_stream_sha.txt
tools/rec.sh r9_${NAME}_cdc_crosscheck $N tools/crosscheck_cdc.mjs $P/out/post_edit/run-a/trace_120hz.jsonl $P/stream/${NAME}_post_edit_120hz.prsm 120
