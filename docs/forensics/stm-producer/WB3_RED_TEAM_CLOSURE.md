# WB-3 red-team closure checklist

**Session:** 2026-07-29 WB-3 investigation-to-convergence (agent execution)

| # | Attack / failure mode | Control | Status |
|---|----------------------|---------|--------|
| 1 | Stale BACKLOG "not started / 42 bins" | `BACKLOG.md` WB-3 corrected | **Done** |
| 2 | Cherry-pick `f6cf78f` as integration base | `WB3_AUTHORITY_MAP.md` | **Done** |
| 3 | Self-shadow A==A parity PASS | `stm_vp_compare.py` + tests | **Done** (host) |
| 4 | Blank/constant stream parity credit | `stm_vp_compare` stream gates | **Done** (host) |
| 5 | Post-hoc threshold edits | Frozen hash in hypotheses doc | **Documented** |
| 6 | Unattested 512 reference | `WB3_REFERENCE_ATTESTATION.md` INDETERMINATE | **Done** |
| 7 | Fake Core-0 measurement | `WB3_CORE0_BENCH_INDETERMINATE.md` | **Done** |
| 8 | Agent chooses Path A/B/C | `WB3_CAPTAIN_DECISION_PENDING.md` | **Done** |
| 9 | Convergence without decision | `WB3_CONVERGENCE_CONDITIONAL.md` | **Done** |
| 10 | clangd bypass for C++ claims | `GATE0_CLANGD_BLOCKER.md` | **Done** |
| 11 | Flash without MAC/registry | No flash this session | **N/A** |
| 12 | Unapproved audio playback | No playback | **N/A** |

## Open items (not closure)

- Run `pytest tests/test_stm_vp_compare.py` and `test_k1_stm_replay` on `origin/main` worktree
- Captain decision record
- Hardware evidence matrix rows E6–E7

## Audit chain links

- K1: `docs/forensics/stm-producer/WB3_*.md`, `docs/forensics/stm-vp/STM_VP_MEASUREMENT_SPEC.md`
- Ledger: `Lightwave-Ledstrip/BACKLOG.md` § WB-3
- Changelog: both repos `[Unreleased]` WB-3 entries
