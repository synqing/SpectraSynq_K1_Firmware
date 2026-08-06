# WB-3 evidence matrix (execution log)

**Last updated:** 2026-07-29 (dual-track columns)

| Row | Experiment | Track A | Track B | Environment | Result | Artefact |
|-----|------------|---------|---------|-------------|--------|----------|
| E0 | K1 lineage preflight | — | — | Lightwave-Ledstrip | **PASS** | Shell log 2026-07-29 |
| E1 | Commit topology f6cf78f / d40114f / a9ff00c | — | — | `origin/main` | **PASS** | `WB3_AUTHORITY_MAP.md` |
| E2 | clangd semantic smoke | shared | shared | K1_Firmware | **INDETERMINATE** | `GATE0_CLANGD_BLOCKER.md` |
| E3 | `test_stm_vp_compare.py` host controls | shared | shared | Host Python | **PASS** (7/7) | `tests/test_stm_vp_compare.py` |
| E4 | `test_k1_stm_replay.py` (H1) | **required** | — | `origin/main` worktree | **PASS** (1/1, 2026-07-29) | `artifacts/stm-track-a/h1_pytest_2026-07-29.log` |
| E5 | Reference 512 attestation | — | **required** | Host/offline | **INDETERMINATE** | `WB3_REFERENCE_ATTESTATION.md` |
| E6 | Core-0 hardware timing | measure | measure | Bench K1 | **INDETERMINATE** | `stm-track-{a,b}/` |
| E7 | Device VPAB STM modes 7/8 | matrix | matrix | Both K1s | **BLOCKED** | Registry dual-sync + donor main |
| E8 | Comparative Captain sign-off | packet | packet | — | **PENDING** | `WB3_COMPARATIVE_DECISION_RECORD.md` |

## Host control run (E3)

```bash
cd /Users/spectrasynq/SpectraSynq_K1_Firmware
python3 -m pytest tests/test_stm_vp_compare.py -q
```

## Hardware matrix blockers (summary)

1. **No allocatable K1** without violating dual-sync Phase-0 or donor experiment on main unit.
2. **No approved playback** for music fixtures.
3. **No flash** of bench STM/FFT envs without MAC check + registry update + Captain order.

## Negative controls (host)

Covered by `test_stm_vp_compare.py`: blank both, candidate blank, self-shadow, identical executable, negative control sensitivity.
