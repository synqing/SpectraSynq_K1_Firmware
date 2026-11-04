---
abstract: "P2 PASS on 9361a027: 10 min soak ovf=0 ring_drop=0 WDT=0, acq_hz=cons_hz mean 47993, canon_hz 133.31, ring high-water 1320/2048 (27.5 ms). Capture task core 0 pri idle+2. Probe-only."
---

# P2 — continuous capture soak

**MEASURED_ON_SILICON** 2026-09-08  
Image: `k1_main_rpl_pcm1808_probe` @ `9361a027` epoch `1788807504`  
Chip `9087A500` port `/dev/cu.usbmodem1101`

## Architecture on silicon

I2S1 slave RX → `pcm_cap` task (core 0, `tskIDLE_PRIORITY+2`) → 2048-frame / 42.7 ms SPSC ring → AP pops 360 → 4/15 SRC → 96 @ 12.8 kHz.

## 60 s

`P2_CAPTURE_SOAK_60s.json`: ovf=0, ring_drop=0, WDT=0, acq_hz=cons_hz mean 47993, canon_hz 133.31.

## 10 min

`P2_CAPTURE_SOAK.json` (600 s, 309 rate windows):

| Quantity | Value |
|---|---|
| ovf | 0 |
| ring_drop | 0 |
| dropped_exact | UNKNOWN (API policy; events were zero) |
| WDT/reset | 0 |
| acq_hz mean | 47,993 |
| cons_hz mean | 47,993 (identical to acq in every window) |
| canon_hz mean | 133.31 (want 133.33) |
| lrck_hz | 47,996.4 |
| high-water | 1320 / 2048 frames = 27.5 ms (64% of ring) |

## Sizing rationale (now measured)

Worst consumer gap ≈ 27.5 ms. Ring 42.7 ms leaves ~15 ms margin. No overflow.

## PASS

acquired ≈ physical 48 kHz, RX overflow 0, ring drop 0, SRC invariant still emitted as PASS on `[PCMRS]`, reset/WDT 0, high-water bounded.

Not promotion. Product restore remains `k1_main_rpl_im69d` @ `acaecaa8`.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-09-08 | agent:grok | 10 min lossless soak on capture ring. |
