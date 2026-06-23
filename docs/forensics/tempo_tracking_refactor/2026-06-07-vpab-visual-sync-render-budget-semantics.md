# VPAB Visual Sync and Render-Budget Semantics

## Scope

This note records the AP0/VP1 v2 visual-sync evidence added after the SAT palette rollout and the K1 AV regression v2 repaired matrix. It is intentionally limited to VPAB/final-byte visual evidence and render-budget semantics; it is not a timing-causality proof.

## Evidence

- Firmware env for capture: `k1_hardware_harness` (non-shippable)
- Production env restored after capture: `k1_hardware`
- Device: main K1 `/dev/cu.usbmodem1401`, serial `B4:3A:45:A5:87:F8`
- Fixture: `dense_clipped_edm`
- Visual mode: `21` (`DENSE FORGE`)
- Palette mode: `on`
- Capture artifact: `build/audio-semantic-metrics/k1-vpab-visual-sync/k1_vpab_dense_visual_sync_20260607_051025/k1_vpab_dense_visual_sync_20260607_051025__dense_clipped_edm__summary.json`
- Raw VPAB log: `build/audio-semantic-metrics/k1-vpab-visual-sync/k1_vpab_dense_visual_sync_20260607_051025/k1_vpab_dense_visual_sync_20260607_051025__dense_clipped_edm__vpab.log`

Capture summary:

- `vpab_rows`: 64
- `vpabb_rows`: 32
- `vpabc_rows`: 1
- channels: primary and secondary
- modes observed: primary `21`, secondary `18`
- `max_dropped`: 0
- `max_white_bias_score`: 0.0
- `max_render_us_wall_envelope`: 2436

## Semantics

VPAB rows are visual/effect evidence. They prove that the harness captured final LED byte/metric records tied to a fixture, mode, port identity, and git SHA.

VPAB scalar timing fields must not be used as source-code causality proof:

- `render_us`: wall-envelope/max-accumulator diagnostic from VP perf state.
- `quant_us`: final-byte quantization/LED byte conversion timing.
- `frame_us`: visual frame envelope diagnostic.
- `show_us`: FastLED/RMT output diagnostic.

The prior trace-dev investigation showed that a VPAB `render_us` outlier can include scheduling gaps and max-accumulator carry-forward. Therefore, any claim that an effect body violates the effect-code budget still requires trace-dev/MabuTrace evidence, not VPAB scalar rows alone.

## Instrumentation Boundary

VPAB capture requires `ENABLE_DIAG_CAPTURE=1` and `ENABLE_VPAB_PROBE=1` from `k1_hardware_harness`. The production `k1_hardware` build does not include these flags and was restored to the main K1 after capture.
