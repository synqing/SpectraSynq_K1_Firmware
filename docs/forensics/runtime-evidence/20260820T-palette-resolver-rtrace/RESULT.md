---
abstract: "Palette-safe EdgeMixer resolver — LED-buffer rtrace PASS. Real firmware apply() on Naberius Gold, scored with hue_coverage rtrace decoder. Complementary ON lands on authored blue (54,24,241); complementary OFF synthesizes azure (23,121,240). Harmony family stays on-curve. No Captain eyes-on."
---

# Palette-resolver rtrace (2026-08-20)

Ship `k1_main_rpl_im69d` @ `79d220fa` does **not** compile `K1_RENDER_TRACE_V1`
(that flag is `k1_bench_im69d_hueaud` only). Device `:rtrace_dump` is therefore
unavailable on 9087A500 without a diagnostic reflash.

This pack drives the **same** `k1_edgemixer.cpp` + `k1_palette_edge_bridge.cpp`
the RPL binary contains, dumps 160-px frames in the device rtrace hex layout
(`F,<idx>,<ms>,<mode>,<rgb8hex>`), and scores them with
`scripts/regression-harness/score_palette_resolver_rtrace.py` (decoder =
`hue_coverage.rtrace_frames`).

## Verdict: PASS

| Check | Result |
|---|---|
| Gold + complementary ON (full amount) | `[54, 24, 241]` indigo, hue error **0.10°** vs Naberius curve, bucket **16** (authored). Echo `complementary_palette`. Not identity. |
| Gold + complementary OFF (RGB control) | `[23, 121, 240]` azure, bucket **14** (not authored). Echo `complementary_rgb`. |
| Analogous / split / triadic / tetradic ON | all `_palette`, max hue error **0.15–9.5°**, no cyan/azure buckets |
| Veil ON | hue error **0.08°**, chroma 129 vs gold 255 |
| Silicon twin (SPLIT / 0.65 / mask / OKLab) | ON `[169, 65, 156]` ≠ OFF `[236, 137, 144]` ≠ gold. Echo `_palette` vs `_rgb`. Partial-strength RGB lerp of gold+violet is magenta; that is the amount blend, not teal. |

Host pytest: `tests/test_edgemixer_palette_resolver_native.py` — PASS.

Artefacts: `dump.log`, `score.json`.
