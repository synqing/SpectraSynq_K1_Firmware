---
name: k1-firmware-change-gate
description: Use when modifying or planning K1 SensoryBridge firmware feature/function work, light modes, AP/VP/audio/render/palette/encoder/serial/LED-output changes, uploads, or runtime evidence checks in SensoryBridge-main 9.
---

# K1 Firmware Change Gate

## Purpose

Prevent repeat damage from known K1 firmware failure modes. This skill is mandatory before proposing, editing, uploading, or validating non-trivial firmware work.

It complements `/sensorybridge-doctrine`: doctrine protects the product north star; this gate protects the current codebase seams and proof discipline.

## Current Truth

- Verify live state first: `git status --short --branch`, `git rev-parse --short HEAD`, and the active build target. Do not trust handover text without checking.
- **Spec routing authority:** [`docs/spec-index.md`](../../../docs/spec-index.md) Active Lanes table — handover prose is stale until re-verified against live git and device state.
- `refactor/main @ ed22d33` was a prior known base; always verify current branch/HEAD live before citing.
- Rows 5/6/7 were deliberately deferred: `system.h`, AP/GDFT/audio headers, persistence/knob/button leftovers, and `.ino -> main.cpp`.
- `LightwaveOS_Official` is doctrine/reference only. Active firmware truth is this repo.
- Compile/upload is not runtime proof. Runtime proof requires matching source,
  binary, serial/timing/video evidence, and the right board.
- Serial monitoring, upload/flash, erase, and device-write commands are allowed
  when the active validation lane requires them, but only after verifying the
  target by port plus stable hardware identity such as USB MAC, adapter serial,
  chip ID, or board role. Never assume a port name proves device identity.

## Mandatory Preflight

Before touching firmware, output this compact gate:

```markdown
Current truth:
Change class:
Files/seams touched:
Known breakage avoided:
State ownership:
Runtime proof required:
Minimal edit plan:
Explicit non-goals:
Stop conditions:
```

Reasoning Protocol (see `.specify/memory/constitution.md`): before proof/promotion decisions apply `thinking-pre-mortem` + `thinking-red-team` + `thinking-margin-of-safety`; for "is it visibly better?" apply `thinking-scientific-method` + `thinking-bayesian` + `thinking-map-territory` + `thinking-debiasing`; for AP/GDFT/render-budget work apply `thinking-theory-of-constraints` + `thinking-feedback-loops`. Entry point: `thinking-model-router`.

Then read only the relevant local sources:

- Always: `.claude/CLAUDE.md`, this skill, `.claude/skills/sensorybridge-doctrine/SKILL.md`, [`docs/spec-index.md`](../../../docs/spec-index.md), and [`.claude/handoff.md`](../../handoff.md).
- Refactor scope: `docs/k1-refactor-2026-05/02-SPLIT-JUSTIFICATION-MATRIX.md`.
- Baseline/gates: `docs/refactor/harness-baselines/freeze-88428a2/CANONICAL.md`.
- Secondary renderer: `docs/superpowers/plans/2026-05-22-secondary-channel-renderer.md`.
- Feature recovery: `docs/superpowers/plans/2026-05-22-release-feature-recovery-roadmap.md`.
- Preserved live look: `docs/config-snapshots/2026-05-22-perfect-dual-channel-v40102.md`.

## Change Classes

### New Light Mode

Allowed path: add one `light_mode_*.cpp` and register it deliberately.

Required touches:
- append-only enum in `config_types.h`; never reorder existing mode IDs
- prototype in `lightshow_modes.h`
- `render_lightshow_for_channel(...)` dispatch in `SENSORY_BRIDGE_FIRMWARE.ino`
- mode name in `system.h`
- `vp_probe` coverage or explicit nondeterministic exclusion
- build filter already includes `+<light_mode_*.cpp>`

Rules:
- centre-origin unless Captain explicitly approves an exception
- no default rainbow/full hue-wheel sweep
- no heap allocation in render path
- no shared static state unless it is proven channel-safe or intentionally global
- stateful modes must have a primary/secondary bleed test and secondary-enabled perf check

### Secondary Channel / Render Context

Do not claim full independent visual processors until proven.

Known remaining hazards:
- secondary render still snapshots/restores global `CONFIG`
- multiple modes still consume shared globals or static locals
- Dot, Kaleidoscope, Quantum, palette, auto-colour, Prism, and history paths can bleed unless isolated

Required proof:
- primary/secondary different stateful modes for 120 seconds
- no visible state bleed or resets
- VP/perf telemetry with secondary enabled
- output-probe or frame-dump evidence for config restore and cross-channel state

### Colour / Palette / Auto-Colour

At any render frame, exactly one colour authority owns the active source.

Rules:
- palette mode owns colour while active
- manual HSV/RGB changes must either exit palette mode or mutate only the manual source
- auto-colour must not silently override palette-owned colour
- no uncontrolled hue-wheel travel as default behaviour
- palette/manual/auto-colour changes need hardware-visible evidence, not just serial acknowledgement

### Bloom / Waveform / Kaleidoscope

Protect visual character, not just function calls.

Rules:
- display-only fades/mirroring must not feed back into transport history
- Bloom keeps centre-origin history transport and bounded colour identity
- Waveform Fast, Waveform, and Waveform Hybrid keep their distinct visual roles
- Kaleidoscope state must be per-channel before it is trusted in dual-channel compositions
- motion memory regressions are product regressions even if the code is cleaner

### AP / GDFT / Audio

Default: do not touch unless the task names a measured AP bug or a required feature surface.

Rules:
- never auto-run `start_noise_cal`; Captain must confirm silence
- AP claims need AP capture evidence; magnitude-only acoustic captures are gross-regression evidence unless level-controlled
- GDFT/window/interlace/sample-rate changes need synthetic or captured backtests plus latency/perf read
- do not use S2/S3 migration as a substitute for proving the current signal path

### Encoder / Serial / Destructive Commands

Rules:
- keep Row 1 dispatch-table safety intact
- no destructive single-byte hotkeys
- `start_noise_cal` stays N-arm -> Y-confirm under silence
- factory/reset/clear destructive commands keep typed `CONFIRM`
- command changes require host dispatch tests and serial smoke evidence

### LED Output / Performance

Rules:
- separate render cost from FastLED/show cost
- no heap in render or functions called from render
- brightness, gamma, temporal dither, quantisation, clipping, and incandescent filters must not double-apply
- secondary-enabled frame budget must be measured before adding heavier visual logic

## Stop Conditions

Stop and ask Captain when:

- calibration or a silence window is needed
- target board/build identity is unclear
- hardware identity is unclear before serial, flash/upload, erase, or
  device-write actions
- runtime proof is missing for a behavioural claim
- the same failure happens twice
- a visual regression may be intentional but is not Captain-approved
- scope expands beyond the named change
- a change crosses AP/audio, render, colour, and serial seams at once

## Completion Standard

Do not say "done" unless the final response states:

- files changed
- build/test commands and result
- runtime proof captured, or exactly why it is still unproven
- whether Captain hardware/video validation is still required
- any deferred hazards left intact
