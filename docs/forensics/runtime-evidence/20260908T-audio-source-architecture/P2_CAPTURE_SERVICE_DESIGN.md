---
abstract: "P2 design (not yet on silicon): continuous I2S1 drain into a bounded raw ring, SRC consumer, canonical 96-queue. Sized from the 4×60-frame DMA (~5 ms) vs 7.5 ms hop plus AP p99 8000 µs gap. Implemented only after P1 overflow soak classifies loss."
---

# P2 — continuous PCM capture service (design)

Status: **SOURCE_PROVEN design, UNMEASURED on silicon until P1 soak closes.**

Current hop-drain (`k1_pcm1808_take_canonical_samples`) blocks the AP path on `i2s_channel_read` until 360 frames, then SRC, then K1 DSP. DMA is 4 descriptors × 60 stereo frames = 240 frames ≈ **5.0 ms** at 48 kHz. Hop is 7.5 ms; AP service p99 contract is 8000 µs. If DSP holds the core past ~5 ms without a reader, the IDF RX queue overflows.

P1 measures that. P2 is required even if overflow is zero, because an externally clocked 48 kHz producer must not be slaved to AP cadence.

## Ownership

Producer (capture task): I2S1 drain, stereo frame integrity, acq timestamps/counters, overflow/drop accounting, raw ring writes. No AP, GDFT, tempo, render, NVS, fast gain.

Consumer (AP hop or SRC task): stereo-to-mono, Line conditioner (none frozen before P3), 4/15 SRC, canonical 96-frame queue.

## Ring sizing (pre-measure, to be replaced by soak high-water)

| Quantity | Value |
|---|---|
| DMA depth | 240 frames / 5.0 ms |
| Worst expected consumer gap | 8 ms AP p99 + 7.5 ms hop ≈ 15.5 ms (~744 frames) |
| Margin | ×2 |
| Proposed capacity | 1536 stereo frames / 32 ms / 9216 bytes |
| Allocation | static BSS, no steady-state heap |

After P1/P2 soak, replace this with measured worst consumer gap + high-water.

## Placement

Do not assume a free core. Benchmark capture overflow, AP p95/p99/max, render timing, capture-task CPU. Smallest placement/priority that stays lossless wins.

## PASS

≥10 min load: acquired ≈ 48 kHz, RX overflow 0, ring drop 0, SRC invariant PASS, reset/WDT 0, high-water bounded with margin.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-09-08 | agent:grok | Pre-P1 design; ring size is a hypothesis until soak. |
