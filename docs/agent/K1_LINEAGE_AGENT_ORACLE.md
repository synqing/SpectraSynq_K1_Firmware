---
abstract: "K1 firmware mirror of the lineage agent oracle. Canonical master copy lives in Lightwave-Ledstrip monorepo governance."
status: active
canonical_source: "/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/instructions/k1-lineage-agent-oracle.md"
skill_lightwave: "/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/.claude/skills/k1-lineage-routing/SKILL.md"
skill_k1: ".claude/skills/k1-lineage-routing/SKILL.md"
preflight_k1: "bash scripts/agent/session-bootstrap.sh"
preflight_lightwave: "Lightwave-Ledstrip/tools/k1-lineage-preflight.sh"
session_origin: "2026-07-29"
---

# K1 Lineage Agent Oracle (K1 repo mirror)

**If this file and the Lightwave canonical disagree on governance/process, the Lightwave copy wins.**  
**For K1 product facts (envs, lanes, registry), `K1_CANONICAL_CONTEXT.md` + `AGENT_OS.md` win.**

**Full text (authoritative):**  
`/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/instructions/k1-lineage-agent-oracle.md`

---

## Executive summary (read every K1 session)

### Three answers to "latest firmware build"

| # | Question | Answer location |
|---|----------|-----------------|
| A | What ships? | **This repo**, env `k1_hardware` |
| B | Newest source? | `git log origin/main -1` here |
| C | On device? | `esptool read_mac` + `docs/hardware/device-build-registry.md` + serial `:build` |

### Two repos — one product

| Repo | Role |
|------|------|
| **`SpectraSynq_K1_Firmware` (here)** | ONLY shipping firmware |
| **`Lightwave-Ledstrip/firmware-v3`** | DEAD donor — read-only WB-4 mining; do not edit or flash for product |

### Session failures we must not repeat (F1–F8)

| ID | Failure | Guardrail |
|----|---------|-----------|
| F1 | Cited deprecated `esp32dev_audio_esv11_k1v2_32khz` as "the" K1 build | Use three-answer table; run preflight |
| F2 | Trusted USB port name over device identity | `read_mac` before every flash |
| F3 | Flashed donor ESV11 to main K1 without lineage consequence stated | Warn + update registry |
| F4 | Framework transplant (`IEffect`/`ControlBus` paste) | `light_mode_*` + `K1AudioContext` only |
| F5 | Re-litigated rejected families/gems | See gem surfaced + captivation docs |
| F6 | Ported unwired `MotionSemanticEngine` | C-10: abandon or wire donor first |
| F7 | Single-agent read of 200+ effects | Parallel SSAs ≤30K tokens each |
| F8 | Captain menu without upstream facts | C-8/C-9/C-10 in `BACKLOG.md` |

### Migration doctrine (WB-4)

- **Harvest, not merge** — algorithms + primitives into `light_mode_*`, not actor model.
- **Receiving seam:** 8-file registration gate or flag-gated `K1_EFFECT_FRAMEWORK_V1`.
- **Phase A next:** adapter gaps in `K1AudioContext` (see `effects/framework/K1AudioContext.h`).
- **Tracking:** Lightwave `BACKLOG.md` § WB-4; plan `.cursor/plans/wb-4_migration_execution_*.plan.md`.

### Impedance (donor → fork)

| Donor | Fork | Rule |
|-------|------|------|
| `CRGB` + `ControlBus` @ 125 Hz | `CRGB16` + `SBAudioSnapshot` @ ~133 Hz | Field adapters, no struct paste |
| `RenderContext` | `mirror_image_downwards` + centre 79/80 | Re-implement |
| `TransitionEngine` | Already in `effects/framework/` | WB-4.C promote gate |

### Agent preflight

```bash
# This repo
bash scripts/agent/session-bootstrap.sh

# Lightwave monorepo (when working cross-repo)
./tools/k1-lineage-preflight.sh
```

Load skill: `.claude/skills/k1-lineage-routing/SKILL.md`

---

## Maintenance

Update the **Lightwave canonical** first, then sync this mirror's executive summary if F-table or doctrine changes.
