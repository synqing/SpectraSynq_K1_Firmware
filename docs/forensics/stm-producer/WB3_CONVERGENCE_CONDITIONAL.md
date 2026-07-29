# WB-3 convergence — conditional branches (pre-decision)

**Status:** **NO CODE CONVERGENCE** until `WB3_CAPTAIN_DECISION_PENDING.md` records Path A, B, or C.

## Path A — Native 40-bin (conditional)

**Entry:** Captain selects Path A on reconciled `origin/main` worktree (not dirty dual-sync lane).

**Work blocks (from plan §13):** single snapshot adapter, static 40-bin centre-correct LUT (LEDs 79/80 → bin 0), serial/mode bound fixes, test-first contract corrections, VP matrix, Core-0 re-measure if producer changes, hardware eyes-on before behaviour commit.

**Production:** Remains flag-off in `k1_hardware` until separate Phase 9 promotion decision.

## Path B — True 512-point FFT (conditional)

**Entry:** Captain selects Path B after H4 measurement and H2 reference attestation.

**Work blocks:** Separate design record, mutually exclusive bench flag, static FFT buffers, 42-bin LUT, full test/build/VP/hardware matrix.

## Path C — Removal (conditional)

**Entry:** Captain selects Path C.

**Work blocks:** Absence tests first; remove producer, modes 7–8, bench env; preserve unrelated `a9ff00c` collateral; document drop rationale.

## Current session deliverables

Documentation, host VP gate, evidence **INDETERMINATE** records only — **no** producer/render C++ edits.
