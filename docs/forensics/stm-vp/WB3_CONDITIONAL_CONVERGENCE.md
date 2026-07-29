# WB-3 conditional convergence branches (pre-decision)

**RBDO:** GROUNDED as conditional work breakdown; **no branch executes** until `WB3_CAPTAIN_DECISION_PENDING.md` records A, B, or C.

## Common prerequisites (all paths)

1. Clean integration tip; Gate 0 clangd verification.
2. Restore `STM_REDERIVATION_DESIGN.md` on current history with K1 naming and sign-off state.
3. Single `K1AudioSnapshot` per frame; adapter maps `snap.stm.*` once for both strips.
4. Offline 160-entry centre-correct LUT (no render-path `powf()`).
5. Full test matrix + bench builds; VP + Core-0 evidence; Captain hardware sign-off before behaviour commit.

## Path A — Native 40-bin (after Captain selects A)

- Fix adapter, readiness semantics, LUT centres 79/80 → bin 0, mode/serial guard alignment.
- Modes 7/8 behaviour per design; keep `K1_STM` out of `k1_hardware` until Phase 9 promotion decision.

## Path B — True 512-point FFT (after Captain selects B)

- Separate flag/env; mutual exclusion with native STM.
- New design record, producer spike, 42-bin LUT, full VP/Core-0 matrix — not a patch to Path A.

## Path C — Drop modes 7–8 (after Captain selects C)

- Surgical removal on reconciled main: producer, snapshot fields, modes 7/8, serial tokens, bench env, STM tests.
- Do not broad-revert `a9ff00c`; preserve unrelated changes unless independently rejected.
- Record rejection rationale; retain commit hashes as archaeology.

## Explicit non-action

Until Captain decision: **no** promotion to production, **no** cherry-pick of `f6cf78f`, **no** agent path selection.
