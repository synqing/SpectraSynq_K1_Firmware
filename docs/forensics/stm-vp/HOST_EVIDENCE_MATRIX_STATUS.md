# Host evidence matrix — status

**RBDO:** GROUNDED for tool tests; hardware matrix **INDETERMINATE**.

## Completed (host)

| Control | Tool | Expected |
|---------|------|----------|
| Empty manifest | `stm_vp_compare.py` | INDETERMINATE |
| Identical provenance hashes | `stm_vp_compare.py` | INDETERMINATE |
| Blank active streams | `stm_vp_compare.py` | INDETERMINATE |
| Self-shadow parity claim | `stm_vp_compare.py` | INDETERMINATE |
| Deliberate divergence injection | `stm_vp_compare.py` | FAIL |

Run: `pytest tests/test_stm_vp_compare.py` from `SpectraSynq_K1_Firmware` root.

## Not run (blocked)

| Matrix | Blocker |
|--------|---------|
| Hardware paired capture | Device allocation + playback approval |
| Optical lane | Locked camera protocol + Captain sign-off |
| Reference vs candidate end-to-end | Independent 512 reference unattested |

## Next action

Execute Phase 4–6 hardware only after Captain clears blockers in `WB3_CAPTAIN_DECISION_PENDING.md`.
