---
title: Smart Scene Runtime Preset Control Evidence
date: 2026-05-28
status: compile-static-verified-runtime-pending
abstract: >
  Adds typed runtime control-surface presets for the passed 1101/1401 Smart
  Visual Engine A/B recipes and the Smart Autonomy candidate, without changing
  production defaults or persistent visual configuration.
---

# Smart Scene Runtime Preset Control Evidence

## Evidence Tier

`compile-static-verified-runtime-pending`

## Mechanism

`smart_scene=[off/assist/l1/auto]` is a typed serial command that applies
repeatable runtime Smart Visual Engine recipe states:

- `off`: Smart Assist off, Smart switching off, visual hooks off, EdgeMixer off.
- `assist` / `control`: 1101-style control recipe: Smart Assist on, switching
  on, confidence floor `0.080`, visual hooks off, EdgeMixer off.
- `l1` / `accent`: 1401-style candidate recipe: Smart Assist on, switching on,
  confidence floor `0.080`, visual hooks on, EdgeMixer complementary at `0.350`.
- `auto` / `autonomy` / `demo`: Smart Assist on, switching on, director
  autonomy on, confidence floor `0.055`, shorter dwell/cooldown for bench
  demo movement, visual hooks on, EdgeMixer complementary at `0.350`.

## Boundaries

- `[FACT]` No production default is enabled by this change.
- `[FACT]` No calibration, AP/GDFT, pixel buffer, palette persistence, or upload
  path is touched.
- `[FACT]` The `auto` preset enables palette and auto-colour overlays only
  through frame-local `RenderParams`; it does not persist
  `CONFIG.PALETTE_INDEX`, `CONFIG.PALETTE_MODE_ENABLED`, or
  `CONFIG.AUTO_COLOR_SHIFT`.
- `[FACT]` The command starts with `smart_`, so the existing manual-owner stamp
  applies before the command body runs.
- `[FACT]` The helper resets Smart mode-selection state to the current manual
  fallback mode with `sb_mode_selection_init(CONFIG.LIGHTSHOW_MODE, millis())`.
- `[INFERENCE]` This is an iteration-throughput feature: it makes the passed L1
  A/B state reproducible quickly, but it is not itself a new visual-quality claim.

## Verification

| Command | Result |
|---|---|
| `python3 -B -m unittest tests.test_smart_visual_engine_static.SmartVisualEngineStaticTest.test_smart_scene_preset_reproduces_l1_ab_runtime_recipe` | PASS |
| `python3 -B -m unittest tests.test_smart_director_replay` | PASS |
| `python3 -B -m unittest discover -s tests` | PASS, 81 tests OK |
| `pio run -e k1_hardware` | PASS, existing `system.h:48` warning only |
| `pio run -e k1_hardware_harness` | PASS, existing harness warnings only |
| `pio run -e k1_bench_reference` | PASS, existing `system.h:48` warning only |
| `pio run -e k1_hardware_trace_dev` | PASS, trace-dev non-shippable, existing harness warnings only |

## Runtime Proof Boundary

Runtime scalar proof for the `auto` preset now exists in:

- `docs/forensics/runtime-evidence/2026-05-28-k1-smart-autonomy-ab-config-v1.log`
- `docs/forensics/runtime-evidence/2026-05-28-k1-smart-autonomy-ab-config-v1-status-summary.json`

`[FACT]` The `1401` candidate reported `SMART_DIRECTOR_AUTONOMY: on`,
`SMART_PALETTE_OVERLAY: 1`, palette indices `29` and `11`, non-neutral ambient
scalars (`PHOTONS=0.860`, `CHROMA=0.920`, `SATURATION=0.900`), and an
`SMART_APPLIED_MODE` transition from `3` to `8`.

`[FACT]` The `1101` reference reported `SMART_DIRECTOR_AUTONOMY: off` and
`SMART_PALETTE_OVERLAY: 0`.

This is scalar/status runtime evidence. It does not replace Captain visual A/B
judgement or VPABB final-byte proof.

## Changelog

| Date | Change |
|---|---|
| 2026-05-28 | Added `smart_scene` typed preset command and static/build evidence |
| 2026-05-28 | Added `auto` / `autonomy` / `demo` preset and scalar runtime evidence on 1101/1401 |
