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

## Status log
| Date | Status | Evidence |
|---|---|---|
| 2026-10-21 | OPEN — dev measured | Hypothesis above tested on dev: no comb variant raises Acc2; min-tooth cuts wrong locks 14 -> 10 but Acc2 19 -> 16, rejected (p2.2-selection-ablation-dev). Trap suite reproduces the 2/3 attractor (p2.1-trap-baseline). No correctness term for the tracker reaches dev AUC 0.8 (p3.1-terms-dev; best 0.75 in p2.6-joint-auc-dev); one estimator-side value of 0.838 is the best of 648 grid comparisons and gives 12-14 right / 5-7 wrong locks (p2.6-joint-lowflux-auc-dev). |
| 2026-10-21 | OPEN — Phase 2.6 measured, rule 3.3 implemented | Host joint tempo+phase estimator: dev Acc2 20/36, 1 at 3:2 (lane tracker 19/36, 7) — selection error type changes, Acc2 does not rise (p2.6-joint-score-dev). Agreement-gated lock dev 8 right / 2 wrong vs lane 11 / 11 (p2.6-agreement-gate-vs-lane-dev); in-sample, not held-out. K1_TEMPO_LOCK_OFF_V1 withholds the LOCKED band (p3.3-*). Lock-ON vs lock-OFF awaits the Captain. |
| 2026-10-22 | OPEN (kept, Captain 2026-10-21) | Fallback ruled: lock-off qualified, so the 3:2 winner can no longer publish a confident wrong lock or beat cue in that build (c2-consumer-clean-repaired). The selection defect itself is unchanged; the proposed host-only experiment E1 (agreement-gated lock, dev -> separate validation, plan 2026-10-21 night) is the next measurement. |
| 2026-10-22 | OPEN — E1 falls short on development data | E1's development pick (hold D in {0, 2, 4} s, frozen scorer, 36 dev clips): D 0 = 8 right / 2 wrong (not eligible, more than 1 wrong); D 2 = 1 / 1; D 4 = 1 / 0 (e1-dev-score-hold*). The best eligible result covers 1 of 36 tracks against the pre-registered validation bar of 25 %. Recommendation: no validation material for E1 (plan, update 2026-10-22). No held-out or validation clip run. |
