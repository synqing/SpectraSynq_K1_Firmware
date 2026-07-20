# Source of Truth — SpectraSynq K1 Firmware

**This repository (`synqing/SpectraSynq_K1_Firmware`) is the single canonical source of truth for K1 firmware.**

Ratified 2026-07-21. All new firmware development happens here. Other historical
firmware repositories are frozen references or archived experiments (see below).

## Repository roles

| Repository | Role | Status |
|---|---|---|
| **SpectraSynq_K1_Firmware** (this repo) | **Canon** — go-forward firmware source of truth | Active |
| Lightwave-Ledstrip (`firmware-v3/`) | Reference-of-record — deep history + effect/DSP breadth being migrated | Frozen at tag `reference-of-record/v3-final` (`60009324`, 2026-07-12). No new features. |
| SpectraSynq-K1-Firmware-SB9- | Heritage analysis workspace (Sensory Bridge) | Harvest lessons → archive |
| rewrite | Greenfield simulation-first spike | Harvest lessons → archive |
| FL.ledstrip, K1.esp32s3, K1.Ambience, K1-09/10, K1.node1/2, K1.Sliders, K1.tab5, Tab5.DSP | Variant archaeology (2025 probe era) | Archive as heritage |

## Rules

1. **No new firmware features on Lightwave-Ledstrip.** It is frozen. Bug-only fixes
   require an explicit exception.
2. **Nothing is deleted — ever — without the owner's explicit, per-item approval.**
   Retirement is backup-first and archive-by-default (reversible); deletion is a
   separate, later, explicitly-approved step. Lightwave stays as reference-of-record
   until the effect/DSP migration passes the parity harness (see
   `docs/consolidation/FIRMWARE-CONSOLIDATION-PLAN.md` and
   `docs/consolidation/WORKING-COPY-INVENTORY.md`).
3. **Effects/DSP are re-derived, not copy-pasted**, using the effect-decomposition
   method already established in `SPECTRASYNQ_K1_FIRMWARE/effects/`, gated by the
   parity harness.

## Heritage & licence

Derivative of [Sensory Bridge](https://github.com/connornishijima/SensoryBridge)
(Connor Nishijima / Lixie Labs), GPL-3.0. This repository preserves upstream
attribution (`NOTICE`) and the `sb_` provenance prefix on inherited modules.

See `docs/consolidation/` for the full consolidation plan, effect migration backlog,
and working-copy inventory.
