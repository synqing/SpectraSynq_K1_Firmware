# HANDOVER B4 — stop polishing the Emotiscope oracle; do the differential

**Project folder:** `/Users/spectrasynq/Workspace_Management/Software/SpectraSynq-K1-DualMCU-Firmware`
**Branch:** `lane/k1-dm-110-vectors-24k` (HEAD `3fed3e4`).
**Agent:** Claude Code or Codex, one session.

---

The B3 correction landed properly: the three invalid vectors are gone, verification is the default with `--regenerate` explicit and unused by `init.sh`, the source-pin and index-expression guards are good discipline, and the GDFT fixture hash is real. Two things remain wrong with the Emotiscope oracle, and the right response to both is to stop treating it as an oracle.

## 1. Retire the Emotiscope tempo-field oracle

`test/fixtures/emotiscope_novelty_input.txt` contains one line and no data:

```
# periodic novelty train: 120 BPM at 50 Hz, 1024 ticks
```

The 1024 values are synthesised inside `generate_emotiscope_tempo_field.py` when it string-matches that comment. So the manifest's `fixture_sha256` hashes a 62-byte comment while its `fixture_description` claims "1024-tick periodic novelty train". That is the same false-provenance shape B3 just removed, in a new place: the fixture cannot be inspected, diffed, or reproduced from the file that names it.

The `peak != 59` assertion is also pinned to the wrong reason. Its comment says the coefficient quantisation "places the 120 BPM train in the adjacent 119 BPM bin". The bin centres are exact — `tempo = 96·(i/96) + 60 = i + 60`, so bin 60 *is* 120 BPM. The real cause: `block_size` clamps to 1024 for every bin, so `k = int(0.5 + 1024·hz/50)` produces only **34 distinct values across the 96 bins**. Bins 59, 60 and 61 all take `k = 41`; 119/120/121 BPM are not separable. Which of the triplet wins is decided by round-robin order and the 0.995 smoothing. The oracle's own output confirms it: bins 60 and 61 bit-identical, 62 and 63 bit-identical, 66 distinct magnitudes across 96 bins.

And `silence_level` is **1.0 on all 1024 records** — full silence reported while 95 of 96 magnitudes are non-zero and confidence is 0.33.

An oracle is a trusted reference. This one has an out-of-bounds read we had to patch, a bank that is ~3× oversampled, a confidence that reads 10.0 on silence, and a silence field pinned at 1. K1 does not need it: **a synthetic periodic novelty train at a known BPM is ground truth by construction**, so K1's own tempo bank can be asserted directly against the BPM that generated the train.

Do this:

- Delete `test/fixtures/emotiscope_*` (golden, manifest, sentinel) and `scripts/generate_emotiscope_tempo_field.py`; remove its line from `init.sh`. Keep `harness/oracles/emotiscope/README.md` and the `NOTICE` attribution as the record of what was learned.
- Remove the Emotiscope acceptance item from K1-DM-110 and note why in the ledger attempt.
- The findings are already written up as §11 of `docs/research/2026-09-02-emotiscope-architecture-review.md` in the legacy repo. Do not re-derive them.

If Captain later wants a tempo-field golden, it is a synthetic train plus an assertion on K1's own bank — no third-party oracle involved.

## 2. Do the differential

This is the only remaining blocker and your stated next step is right. Feed the same 440 Hz/silence trace through the RT1062 GDFT path configured at 24 000 / 180, compare all 16 × 80 bins against `test/fixtures/gdft_24k180.golden.jsonl`, and record a per-feature tolerance with a one-line numeric justification for each. Keep the existing configuration assertions.

Leave the onset and chord vectors blocked. "The rate enters upstream of those oracle files" is the correct finding and it is worth one line in the evidence doc, not more work.

## Constraints

No hardware. Production stays 12 800 Hz / 96. Do not change existing frozen goldens or contracts. Do not touch the legacy repo. British English. Stop report in the repo's format.

## One process note

Three status reports in a row have contained a line the artefact did not support — most recently "first record has confidence 10, silence 1" when the committed first record reads `tempo_confidence = 0.499999881`. The work itself has been sound and the corrections were accepted cleanly. Read the artefact you are about to describe before describing it.
