---
abstract: "Active authority for the Main RPL PCM1808 + ST25R3916B bench bring-up. PCM clock gate PASS 47.986 kHz on e54f4728; ST25 SPI identity PASS 0x31 3916B on 605b855e / 9087A500. Product restore remains k1_main_rpl_im69d @ acaecaa8. RFAL/tag/combined not run. Colour Lab remains ready_for_merge."
branch: lane/pcm1808-st25r3916b-bringup
status: active
---

# Main RPL — PCM1808 + ST25R3916B bench bring-up

**Lane:** `PCM1808_ST25R3916B_BRINGUP_20260907`  
**Branch:** `lane/pcm1808-st25r3916b-bringup`  
**Evidence:** [`docs/forensics/runtime-evidence/20260907T-pcm1808-st25-bringup/PREFLIGHT.md`](../forensics/runtime-evidence/20260907T-pcm1808-st25-bringup/PREFLIGHT.md)

## Objective

Bring up PCM1808 wired stereo line-input on Main RPL, resample 48 kHz → 12.8 kHz without changing the K1 audio contract, then bring up ELECHOUSE ST25R3916B independently, then prove coexistence.

## Locked order

1. Live Main RPL authority (this preflight).
2. Untouched PCM1808 default 96 kHz clock measurement. **STOP — human.**
3. Short OP2 only → 48 kHz master re-measure. **STOP — human.**
4. Isolated I2S1 slave RX raw capture probe.
5. Rational 4/15 FIR resampler into canonical 96-sample hops.
6. K1 DSP from wired input.
7. Independent ST25 SPI+IRQ probe.
8. Combined soak.

Native PCM1808 12.8 kHz external-clocking is **not** this lane.

## Non-negotiables

- DSP remains 12,800 samples/s, 96-sample hop, 7.5 ms.
- No drop-sample "resampling".
- No microphone cal/NVS reuse or overwrite.
- No ESP32 MCLK to the PCM module on first bring-up.
- New hardware behind explicit probe envs; `k1_main_rpl_im69d` stays PCM/NFC-free until promotion.
- Do not upgrade pioarduino 54.03.20 to satisfy NFC.

## Colour Lab

Previous lane `COLOUR_LAB_PALETTE_BENCH_20260827` is **ready_for_merge** on `lane/colourlab-bench`. Do not merge it from this branch. Unrelated dirty Colour Lab / BLE-iPhone files travel with the working tree and must not be committed into this bring-up.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-09-07 | agent:grok | ST25 identity PASS on silicon `605b855e`: `[ST25ID] hex=0x31 family=ST25R3916B`. RFAL/tag/combined still open. |
| 2026-09-07 | agent:grok | PCM probe on silicon `e54f4728`: `[PCMCLK] gate=PASS` 47.986 kHz / ratio 63.957, DMA 47.998 kHz, hop 12800/96. Analog L/R map not proven. ST25 next. |
| 2026-09-07 | agent:grok | Created as active authority for PCM1808 + ST25R3916B Main RPL bring-up. |
