# Stream B — beat report

1. Changed artefacts
- `_scratch/s3-repair-20261105/beat-heldout.json`: authority audit; beat run not executed.
- `sw-b/authority-search.log` and `sw-b/gates.json`: command evidence. No firmware changes.

2. Gates run
- Authority search: `rg -n -i 'held.?out|approved|Captain supplement' docs/architecture/tempo-lock-hardening-plan.md docs/defects/DEF-002-tempo-3to2-winner-and-sharpness-confidence.md`; exit 0; `sw-b/authority-search.log`.
- `ls docs/decisions`: exit 1; directory absent. Existing architecture/defect/fixture/scratch sources inspected instead.
- Beat qualification: NOT_RUN; no gate exit code.

3. Measured numbers
- No timing or beat-performance measurements. Source inspected at `b779e561`; host file inspection only; processor frequency/build flags not applicable.
- Existing scorer's match window: inclusive ±70 milliseconds (ms), with five-second warm-up.
- Manifest names 1,359 held-out clips; approval is conditional and execution remains reserved.

4. Not verified
- OPEN: no currently authorised executable held-out beat set found. No clips decoded or scored; no new published-tick, match, precision, recall, wrong-lock or beats-per-minute (BPM) range result.
- This is the section 9.1 no-run branch, not three failed approaches: no experimental approaches were attempted.
- Development HarmonixSet, the 483-clip screen and previous ten V1 validation clips were not substituted.

5. Open decisions for Captain
- Preserve the reserved acceptance set until its recorded development entry gates clear; no method decision needed for this repair lane.
- Continue the lane with beat qualification OPEN.
