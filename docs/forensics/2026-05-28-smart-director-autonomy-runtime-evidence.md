---
title: Smart Director Autonomy Runtime Evidence
date: 2026-05-28
status: scalar-runtime-ready-visual-judgement-pending
abstract: >
  Implements and exercises a Smart Director autonomy preset that adds bounded
  mode movement, frame-local palette ownership, and stronger parameter
  modulation without persistent CONFIG mutation or production instrumentation.
---

# Smart Director Autonomy Runtime Evidence

## Evidence Tier

`scalar-runtime-ready-visual-judgement-pending`

This pass proves compile/static/host-replay correctness and scalar runtime
presence on both K1 devices. It does not claim final visual approval.

## Perception Gate

Mechanism:
: Smart Director autonomy preset (`smart_scene=auto`), state-to-mode policy,
  state-to-parameter scalars, and frame-local palette overlay.

Perceived output:
: K1 should look more like it is listening: restrained baseline sections,
  musically plausible mode changes, and palette/brightness/saturation shifts
  that track song energy instead of staying static.

Collapse points:
: Status fields can change without visible improvement; palette overlays matter
  only in modes that consume `RenderParams`; transient mode choice can be blocked
  by manual-owner and beat-boundary gates.

Survival paths:
: Bloom, Waveform, Waveform Fast, Waveform Hybrid, and VU now consume primary
  palette ownership/index/auto-colour through `RenderParams`; Smart scalars
  mutate `PHOTONS`, `CHROMA`, `MOOD`, and `SATURATION`; mode selection can
  apply a render-local mode without persisting `CONFIG.LIGHTSHOW_MODE`.

Simpler alternative:
: Keep L1 only: Smart switching/hooks/EdgeMixer on, autonomy off, palette fixed
  at `29`.

Materiality thresholds:
: Candidate must show `SMART_DIRECTOR_AUTONOMY=on`, `SMART_PALETTE_OVERLAY=1`,
  non-neutral scalars in at least one state, and an applied-mode transition under
  music before Captain visual judgement.

Evidence:
: Static tests, host replay, build matrix, upload logs, and scalar status capture.

Decision:
: Keep the autonomy primitive for live A/B. Do not promote as visually verified
  until Captain judges `1401` against `1101`.

Next experiment:
: Captain visual A/B with `1101` as L1/reference and `1401` as auto/autonomy
  candidate under the same music programme.

## Implementation

- `[FACT]` `SBSmartDirectorOutput` now carries `palette_overlay_enabled`,
  `palette_index`, and `auto_colour_shift`.
- `[FACT]` `sb_smart_director_apply_render_params()` applies palette ownership
  only to frame-local `RenderParams` when `director_autonomy_enabled` is true.
- `[FACT]` `smart_scene=auto` / `autonomy` / `demo` enables director autonomy,
  hooks, EdgeMixer complementary `0.350`, confidence floor `0.055`,
  `min_dwell_ms=6000`, `cooldown_ms=9000`, and max `4` switches per minute.
- `[FACT]` No AP/onset producer code, calibration path, pixel buffer code, or
  production instrumentation was added.

## Verification

| Check | Result |
|---|---|
| `python3 -B -m unittest tests.test_smart_visual_engine_static` | PASS, 21 tests OK |
| `python3 -B -m unittest tests.test_smart_director_replay` | PASS |
| `python3 -B -m unittest discover -s tests` | PASS, 81 tests OK |
| `pio run -e k1_hardware` | PASS |
| `pio run -e k1_hardware_harness` | PASS |
| `pio run -e k1_bench_reference` | PASS |
| `pio run -e k1_hardware_trace_dev` | PASS |
| `nm .pio/build/k1_hardware/firmware.elf \| grep -i mabutrace` | no matches |
| `nm .pio/build/k1_hardware_harness/firmware.elf \| grep -i mabutrace` | no matches |
| `pio run -e k1_hardware -t upload --upload-port /dev/tty.usbmodem1101` | PASS |
| `pio run -e k1_bench_reference -t upload --upload-port /dev/tty.usbmodem1401` | PASS |

Existing warnings remained: `system.h:48` volatile increment warning, plus the
known harness/trace-dev `process_GDFT` IRAM section attribute conflict warning.

## Runtime A/B Setup

Evidence files:

- `docs/forensics/runtime-evidence/2026-05-28-k1-smart-autonomy-ab-config-v1.log`
- `docs/forensics/runtime-evidence/2026-05-28-k1-smart-autonomy-ab-config-v1-status-summary.json`
- `docs/forensics/runtime-evidence/2026-05-28-smart-director-autonomy-replay-v1.json`
- `docs/forensics/runtime-evidence/2026-05-28-k1-smart-autonomy-final-status-v1.log`

Device roles:

- `1101`: `smart_scene=l1` reference, autonomy off.
- `1401`: `smart_scene=auto` candidate, autonomy on.

Observed scalar/status results:

- `[FACT]` `1101` reported `SMART_DIRECTOR_AUTONOMY: off` and
  `SMART_PALETTE_OVERLAY: 0`.
- `[FACT]` `1401` reported `SMART_DIRECTOR_AUTONOMY: on`,
  `SMART_PALETTE_OVERLAY: 1`, palette indices `29` and `11`, and applied modes
  `3` and `8`.
- `[FACT]` `1401` reported non-neutral ambient scalars:
  `SMART_SCALAR_PHOTONS: 0.860`, `SMART_SCALAR_CHROMA: 0.920`,
  `SMART_SCALAR_SATURATION: 0.900`.
- `[FACT]` `1401` reported `SMART_SWITCHES_IN_WINDOW: 1` and tail
  `SMART_APPLIED_MODE: 8` with `SMART_MANUAL_OWNER_ACTIVE: 0`.
- `[FACT]` A later final status snapshot found `1101` on applied mode `8`
  with autonomy still off, and `1401` on applied mode `9` with autonomy still
  on and palette overlay still active.
- `[FACT]` No calibration command was sent.

## Proof Boundary

`[FACT]` The generic VPABB parser reported no VPABB rows for this scalar-only
capture, so it is not final-byte evidence.

`[INFERENCE]` The feature is ready for live visual judgement, not promotion as
`verified`.

## Changelog

| Date | Change |
|---|---|
| 2026-05-28 | Added Smart Director autonomy overlay, host replay, build/upload proof, and 1101/1401 scalar A/B evidence. |
