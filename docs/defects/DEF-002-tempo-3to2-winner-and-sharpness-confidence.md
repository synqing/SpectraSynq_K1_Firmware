# DEF-002 — Tempo winner selects 3:2 metrical level; confidence measures sharpness, not correctness

Status: OPEN · Opened: 2026-10-21 · Builds affected: all builds using k1_tempo.cpp comb-ACF
selection + CONF_V2 · Owner lane: lane/k1-tempo-lock-r1

## Measured (FACT — _scratch/esp-emulator/next-phase-tempo-candidate-001/corpus-real-firmware/)
36 HarmonixSet clips through the real emulated firmware (host-vs-emulator fidelity 36/36):
- Shipped (A): Acc2 19/36, locked 2 (1 right, 1 wrong).  Pre-sqrt (B): Acc2 19/36, locked 27 (13 right, 14 wrong).
- The 14 wrong locks: 8 within ±6 % of ⅔ or 4⁄3 of gold (3:2); 4 within 20 % of 1.0; 1 out of range
  (200 BPM); 1 at ≈5⁄4. Octave errors: none.
- Confidence (CONF_V2) mean 0.73 on right tracks, 0.72 on wrong; AUC ≈ 0.5.
- 88 BPM selection prior: favoured the wrong bin on 3 of the 8 3:2 cases, the right bin on 2,
  neutral on 3 → contributor, not cause. The prior was tuned on these same 36 tracks (in-sample).

## Hypothesised mechanism (INFERENCE — not yet run)
Harmonic-SUM comb (teeth T,2T,3T,4T; weights 1/.8/.7/.6) gives a 3T⁄2 candidate the true 3T tooth for
free (~40 % of score). A harmonic PRODUCT or min-tooth comb zeroes a ladder with an empty tooth.
Falsified if: held-out 3:2 rate is not below shipped, or clean-train (90/120/144) lock is lost, or Acc2 falls.

## Rules this defect establishes
- Confidence may gate `locked` only with a committed held-out AUC ≥ 0.8 receipt.
- Dev corpus (the 36) tunes; acceptance only on a Captain-approved held-out corpus.
- Any change to selection or confidence runs the metrical trap suite (½, 2, ⅔, 4⁄3, ¾, 3⁄2, 3).

## Fix direction (lane R1, Phases 2–3) — see the handover of 2026-10-21 and
docs/architecture/tempo-lock-hardening-plan.md.
