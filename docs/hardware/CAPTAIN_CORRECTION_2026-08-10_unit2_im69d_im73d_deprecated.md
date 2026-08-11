---
abstract: "Captain correction 2026-08-10 — Bench Unit 2 is dual IM69D130 hardware; IM73D is deprecated; k1_custom→IM73D inheritance is false authority. Binding Tier-0 supersession for the dual-IM69D130 resolution runbook."
status: active
branch: fix/dual-im69d130-resolution-20260810
lane: K1_DUAL_IM69D130_RESOLUTION_20260810
---

# Captain Correction — Unit 2 = Dual IM69D130; IM73D Deprecated

**Date:** 2026-08-10 (session) / applied 2026-08-11  
**Status:** BINDING — supersedes conflicting registry, eval, and production-mic claims  
**Runbook:** `.cursor/plans/im69d_dual_resolution_d171d7f2.plan.md`  
**Evidence pack:** `_scratch/im69d_resolution_20260810/`

## Binding statements

1. **Bench Unit 2** (`chip 0C54FC00`, USB MAC `AC:A7:04:FC:54:0C`) physical microphone board is **dual IM69D130**.
2. **IM73D122 is deprecated** for new product, bench, and consumer work. Remaining `*im73d*` envs are archive / rollback-only until tombstoned.
3. Live **`[env:k1_custom]` extending `k1_bench_im73d_ble` → `K1_MIC_IM73D_PDM_V1`** is **false authority** relative to Unit 2 hardware. It must not be treated as Unit 2 truth.
4. Unit 2 **PDM CLK/DATA/SELECT pins are not authoritative until measured** (see `_scratch/im69d_resolution_20260810/UNIT2_PIN_RECEIPT.md`). Firmware pin branches must wait on `CAPTAIN_PIN_AUTH=GO`.

## What this invalidates as Unit 2 root-cause

- Treating Unit 2 Aug-9 silence / lock / M18 work as proven “IM73D quiet-floor vs SPH consumers” product truth.
- Copying Aug-9 IM73D-only thresholds into IM69D profiles without independent IM69D measurement.
- Any colour / tempo / presence PASS claimed under the IM73D `k1_custom` binary as IM69D-certified.

Those artefacts remain useful as **code-coupling inventory** and **legacy-scar inventory**, not as Unit 2 hardware root-cause.

## One-line diagnosis (Captain-ratified)

This was not twenty unrelated lightshow defects. It was **one uncontrolled identity failure** (device × physical mic × build env × deployed binary) that generated real, apparent, and misclassified downstream defects.

## Recovery posture (first slice only)

```text
PROVE PHYSICAL MIC + PINS
→ CORRECT ENV IDENTITY
→ CLEAN BUILD
→ PROVE DEPLOYED BINARY
→ MEASURE IM69D
→ RE-EVALUATE CONSUMERS
→ FIX ONLY WHAT SURVIVES
```

Everything before measurement is **containment and restoration of truth**, not another lightshow-fix wave.

## Supersedes

| Prior claim | Status |
|-------------|--------|
| “IM73D122 remains the production mic” (IM69D eval docs 2026-08-05) | **SUPERSEDED** — IM73D deprecated |
| Registry Unit 2 row: dual-206 + IM73D / DIN=38 CLK=39 as mic identity | **SUPERSEDED** for mic part — LEDs 4/5 dual-206 may stand; **pins TBD until P0.C** |
| Deployed-state Unit 2 `k1_custom` IM73D glass PASS as colour/mic truth | **MISFLASH / WRONG MIC IDENTITY** pending retarget — bin retained as rollback only |
| Deck16 as active lane blocking mic resolution | **Flash-frozen** on Unit 2 / B489 mic envs until named gates (see `FLASH_FREEZE.md`) |

## Flash discipline

No flash without in-session `CAPTAIN_FLASH_AUTH=GO`, chip/MAC identity, rollback bin, and clean-worktree provenance. Never flash `*im73d*` onto confirmed IM69D wiring.
