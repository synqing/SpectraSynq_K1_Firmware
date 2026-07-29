# WB-3 convergence — parallel tracks (no pre-test A/B lock-in)

**Status:** **Bench convergence authorised** for Track A and Track B in parallel. **Production** convergence remains conditional on `WB3_COMPARATIVE_DECISION_RECORD.md` after both evidence packets (Captain directive 2026-07-29).

## Shared gates (both tracks)

- Clean `origin/main` worktree for STM C++ (not dirty dual-sync lane).
- clangd Gate 0 (`GATE0_CLANGD_BLOCKER.md`) before producer/render edits.
- Bench K1 allocated; `read_mac`; rollback image recorded (`WB3_AUTHORITY_MAP.md`).
- Captain playback approval (exact source, device, volume, duration, stop) before VP matrix music fixtures.

**Mutual exclusion:** Never enable native `K1_STM` and Track B FFT bench flag in the same firmware image.

## Track A — Native 40-bin (bench)

**Entry:** Branch from `origin/main`; env `k1_bench_im73d_stm`.

**Work blocks:** H1 `pytest tests/test_k1_stm_replay.py`; single snapshot adapter; static 40-bin centre-correct LUT (LEDs 79/80 → bin 0); serial/mode bound fixes; VP matrix; Core-0 re-measure if producer changes; hardware eyes-on before behaviour commit.

**Evidence bundle:** `artifacts/stm-track-a/` (README checklist).

**Production:** Remains flag-off in `k1_hardware` until comparative decision + Phase 9.

## Track B — True 512-point FFT (bench spike)

**Entry:** Separate bench branch; flag mutually exclusive with `K1_STM`.

**Work blocks:** Close or waive reference attestation (`WB3_REFERENCE_ATTESTATION.md`); bench-only producer per `WB3_FFT512_FEASIBILITY.md` § Bench spike; microbenchmark + Core-0 + VP when reference arm valid.

**Evidence bundle:** `artifacts/stm-track-b/` (README checklist).

**Blocked on:** Independent 512-point reference (**INDETERMINATE**) — documentation and spike scaffolding may proceed; H2 reference-vs-candidate parity cannot close until attestation.

## Path C — Removal (deferred)

**Entry:** Captain selects Path C **only after** both tracks fail product gates (H2/H3/H5) or formal abandon of both.

**Work blocks:** Absence tests first; remove producer, modes 7–8, bench env; preserve unrelated `a9ff00c` collateral; document drop rationale.

## Current session deliverables

Documentation, host VP gate, per-track artefact scaffolds, evidence matrix columns — **no** production `k1_hardware` promotion without comparative sign-off.
