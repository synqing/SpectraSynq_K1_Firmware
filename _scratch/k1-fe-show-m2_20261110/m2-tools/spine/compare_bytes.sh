#!/bin/bash
# Byte comparisons for the Spine CLI run on projects/loreen. Read-only on m2-compose.
EV=/Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/k1-fe-show-m2_20261110/m2-tools/spine
M2=/Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/k1-fe-show-m2_20261110/m2-compose/projects/loreen
fail=0
chk() { if cmp -s "$1" "$2"; then echo "IDENTICAL  $3"; else echo "DIFFERENT  $3   ($1 vs $2)"; fail=1; fi; }
echo "== CLI run 1 vs CLI run 2 (verify output, run-a and run-b, and build-demo output)"
for f in showbundle.json trace.jsonl mapping_coverage.json compile_manifest.json build_manifest.json; do
  chk $EV/out/run1/verify/run-a/$f $EV/out/run2/verify/run-a/$f "run1 vs run2 verify/run-a/$f"
  chk $EV/out/run1/verify/run-a/$f $EV/out/run1/verify/run-b/$f "run1 verify run-a vs run-b $f (A04)"
done
for f in showbundle.json mapping_coverage.json compile_manifest.json build_manifest.json; do
  chk $EV/out/run1/build/$f $EV/out/run2/build/$f "run1 vs run2 build-demo/$f"
  chk $EV/out/run1/build/$f $EV/out/run1/verify/run-a/$f "build-demo vs verify run-a $f"
done
echo "== CLI (run 1) vs M2 post-edit artefacts ($M2/out/post_edit/run-a)"
chk $EV/out/run1/verify/run-a/showbundle.json $M2/out/post_edit/run-a/showbundle.json "ShowBundle CLI vs M2"
chk $EV/out/run1/verify/run-a/trace.jsonl $M2/out/post_edit/run-a/trace_120hz.jsonl "Intent Trace CLI vs M2"
chk $EV/out/run1/verify/run-a/mapping_coverage.json $M2/out/post_edit/run-a/mapping_coverage.json "coverage CLI vs M2"
chk $EV/out/run1/verify/run-a/compile_manifest.json $M2/out/post_edit/run-a/compile_manifest.json "compile manifest CLI vs M2"
echo "== build manifest (expected to differ in shape: CLI adds a trinity block and remotes)"
chk $EV/out/run1/verify/run-a/build_manifest.json $M2/out/post_edit/run-a/build_manifest.json "build manifest CLI vs M2"
shasum -a 256 $EV/out/run1/verify/run-a/{showbundle.json,trace.jsonl,mapping_coverage.json,compile_manifest.json,build_manifest.json}
exit $fail
