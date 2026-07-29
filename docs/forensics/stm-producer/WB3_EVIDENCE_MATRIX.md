# WB-3 evidence matrix (execution log)

**Last updated:** 2026-07-29

| Row | Experiment | Environment | Result | Artefact |
|-----|------------|-------------|--------|----------|
| E0 | K1 lineage preflight | Lightwave-Ledstrip | **PASS** | Shell log 2026-07-29 |
| E1 | Commit topology f6cf78f / d40114f / a9ff00c | `origin/main` | **PASS** | `WB3_AUTHORITY_MAP.md` |
| E2 | clangd semantic smoke | K1_Firmware | **INDETERMINATE** | `GATE0_CLANGD_BLOCKER.md` |
| E3 | `test_stm_vp_compare.py` host controls | Host Python | **PASS** (7/7, 2026-07-29) | `tests/test_stm_vp_compare.py` |
| E4 | `test_k1_stm_replay.py` (H1) | Requires `origin/main` tree | **INDETERMINATE** on dual-sync branch | — |
| E5 | Reference 512 attestation | — | **INDETERMINATE** | `WB3_REFERENCE_ATTESTATION.md` |
| E6 | Core-0 hardware timing | Bench K1 | **INDETERMINATE** | `WB3_CORE0_BENCH_INDETERMINATE.md` |
| E7 | Device VPAB STM modes 7/8 | Both K1s | **BLOCKED** | Registry dual-sync + donor main |
| E8 | Captain Path A/B/C | — | **PENDING** | `WB3_CAPTAIN_DECISION_PENDING.md` |

## Host control run (E3)

Execute on clean checkout:

```bash
cd /Users/spectrasynq/SpectraSynq_K1_Firmware
python3 -m pytest tests/test_stm_vp_compare.py -q
```

## Hardware matrix blockers (summary)

1. **No allocatable K1** without violating dual-sync Phase-0 or donor experiment on main unit.
2. **No approved playback** for music fixtures.
3. **No flash** of `k1_bench_im73d_stm` without MAC check + registry update + Captain order.

## Negative controls (host)

Covered by `test_stm_vp_compare.py`: blank both, candidate blank, self-shadow, identical executable, negative control sensitivity.
