---
abstract: "MabuTrace attribution for the VPAB secondary WAVEFORM-FAST render_us gate failure. Shows WAVEFORM-FAST code time under the 2 ms effect ceiling and identifies the VPAB failure as a wall-clock secondary-envelope max polluted by a rare scheduling gap."
---

# VPAB Trace-Dev Secondary Render Attribution

## Scope

Reference state:
- Primary: `MODE=3` / `BLOOM`, primary `MOOD=0.250`
- Secondary: `SECONDARY_MODE=7` / `WAVEFORM-FAST`
- Secondary palette: `SECONDARY_PALETTE_INDEX=24` / `fire_gp`
- Calibration source: config/profile loaded, `CAL_VALID=1`

This investigation addresses the VPAB gate failure where secondary `render_us`
reported `2231-2254 us` and failed the 2 ms K1 runtime ceiling.

## Evidence

| Tier | Evidence | Path |
|---|---|---|
| [FACT] | Trace-dev build created as non-shippable `k1_hardware_trace_dev`; production and harness builds still exclude MabuTrace. | `platformio.ini`, `tests/test_trace_dev_static.py`, `tests/test_dev_instrumentation_boundary.py` |
| [FACT] | Production build passed after trace wrapper changes. | `pio run -e k1_hardware` |
| [FACT] | Harness build passed after trace wrapper changes. | `pio run -e k1_hardware_harness` |
| [FACT] | Trace-dev build passed and was uploaded to K1 on `/dev/cu.usbmodem1101`. | `pio run -e k1_hardware_trace_dev -t upload --upload-port /dev/cu.usbmodem1101` |
| [FACT] | Deep WAVEFORM-FAST trace captured. | `docs/forensics/runtime-evidence/2026-05-27-k1-trace-dev-waveform-fast-deep.json` |
| [FACT] | VPAB + VP perf exact-condition trace captured. | `docs/forensics/runtime-evidence/2026-05-27-k1-trace-dev-vpab-vpperf.json` |
| [FACT] | VPAB scalar gate still fails with secondary `render_us=2231/2254`. | `docs/forensics/runtime-evidence/2026-05-27-k1-vpab-after-trace-dev-runtime.log` |

## Trace Results

Exact-condition trace: `2026-05-27-k1-trace-dev-vpab-vpperf.json`

| Metric | n | p50 us | p95 us | p99 us | max us |
|---|---:|---:|---:|---:|---:|
| `vp_waveform_fast_body` | 607 | 758 | 1327 | 1353 | 1387 |
| `vp_waveform_fast_history_store` | 607 | 18 | 24 | 30 | 153 |
| `vp_channel_seed_history` | 607 | 20 | 24 | 24 | 25 |
| `vp_secondary_effect` | 607 | 874 | 1445 | 1466 | 1502 |
| `vp_secondary_store_clip` | 607 | 51 | 58 | 180 | 1045 |
| `vp_secondary_restore` | 607 | 23 | 27 | 142 | 150 |
| `vp_secondary_render_us` wall envelope | 607 | 1028 | 1593 | 1616 | 2245 |

Derived exact-condition frame split:

| Derived metric | n | p50 us | p95 us | p99 us | max us |
|---|---:|---:|---:|---:|---:|
| Sum of measured secondary subspans | 606 | 978 | 1545 | 1575 | 1614 |
| Gap from `store_clip` end to `restore` start | 606 | 6 | 19 | 22 | 1021 |
| Secondary wall envelope | 606 | 1019 | 1593 | 1616 | 2245 |

## Finding

[FACT] WAVEFORM-FAST code time is not the steady offender. In the exact
VPAB + `vp_perf` trace condition, `vp_waveform_fast_body` maxed at `1387 us`,
and the measured secondary subspan sum maxed at `1614 us`.

[FACT] The over-2 ms secondary wall-envelope event was caused by a `1021 us`
gap between the end of `vp_secondary_store_clip` and the start of
`vp_secondary_restore`. There is no source code work between those two trace
spans, only scope exit/entry and scheduler-visible wall time.

[FACT] VPAB currently reports `render_us` from `vp_perf.secondary_render.max_us`.
One wall-clock outlier becomes the max for the whole VPAB window, so later VPAB
rows repeat the same failure even when the sampled frame itself is not over
budget.

[INFERENCE] The current VPAB gate is mixing two different contracts:
- effect/render code cost, which the trace shows is under 2 ms for this reference
  state;
- wall-clock render envelope, which can include FreeRTOS scheduling gaps.

## Decision Impact

Do not optimise WAVEFORM-FAST based on the current VPAB `render_us` failure.
The trace does not support that conclusion.

The next viable change is to split the harness contract:
- keep a wall-envelope diagnostic for scheduling/latency risk;
- add or report a code-time render metric for the 2 ms effect ceiling;
- stop treating `vp_perf.secondary_render.max_us` as a per-record effect-code
  failure in VPAB.

## Changelog

| Date | Change |
|---|---|
| 2026-05-27 | Added trace-dev lane, captured exact-condition MabuTrace evidence, and attributed VPAB secondary `render_us` failure to wall-clock gap plus max-accumulator semantics. |
