# RMT alloc on VP core — RESULT (`9087A500`, 2026-08-19)

**Silicon:** `IDENTITY OK: git=b8cd4ca9 env=k1_main_rpl_fps_agc_probe epoch=1787142506`  
**Chip:** `CHIP ID: 9087A500` · `/dev/cu.usbmodem1401`  
**Flag:** `-DK1_RMT_ALLOC_ON_VP_CORE_V1=1` (probe only on this flash). Clock-fix still **forced off**. NON-SHIPPABLE.  
**Cal:** `persisted_profile` · SSL/DC unchanged (−247). **Do not re-fire `start_noise_cal`.**

Control: [`20260819T-fps-agc-probe-9087/RESULT.md`](../20260819T-fps-agc-probe-9087/RESULT.md) @ `b318a0ec` (same probe env, **no** VP-core alloc).

---

## Discriminator (show still running)

| Surface | Before (`b318a0ec`) | After (`b8cd4ca9`) |
|---|---|---|
| **SYSTEM_FPS** with show | ~76–80 | **134.1–137.7** (dump **138.32**) |
| **LED_FPS** | ~203 | **162–166** |
| pack_us | 123 / 146 | 132 / 206 |
| show_us | ~2.4 / 3.6 ms | **1.08 / 1.37 ms** |
| gdft_us | ~6.1 / 7.9 ms | **1.75 / 1.81 ms** |
| acq_us | ~1.5 / 2.8 ms | **~3.77 / 4.86 ms** (I2S wait) |
| VP interval | ~4.94 ms | ~6.16 ms |
| over / dropped | 0 / 0 | 0 / 0 |

Hop design is **133.33 Hz**. AP now sits on the hop **with `show_leds()` still firing**.

`acq_us` rising while `gdft_us` collapsing is the healthy signature: Core 0 waits on the 96-sample I2S chunk instead of overrunning it. GDFT was slow before because the chunk was late and the pipeline was spliced.

`LED_FPS` ~163 is Core 1 now servicing RMT refill IRQs plus render. Still well above the 100 FPS soft target (`1/163 ≈ 6.1 ms`).

---

## Decision

Standing hypothesis **confirmed**: FastLED IDF5 allocates RMT on the first `show()`; that call was `init_leds()` / setup on Core 0; refill IRQs at ~200 Hz stole 1.5–3.5 ms per AP frame.

Fix (probe): skip every `show_leds()` / bootstrap `FastLED.show()` that is not on `K1_LED_TASK_CORE`, so the first `loadPixelData` runs on Core 1.

I2S / LCD_CAM LED remains **struck**. This is an ISR-core fix, not a wire-driver swap.

---

## Stamps

| Intent | Stamp |
|---|---|
| This measurement | `IDENTITY OK: git=b8cd4ca9 env=k1_main_rpl_fps_agc_probe epoch=1787142506` |
| Restore Lever-2 look without this AP fix | `k1_main_rpl_im69d` @ `a6149b29` (will re-pin RMT on Core 0) |
| Product next | `k1_main_rpl_im69d` with `K1_RMT_ALLOC_ON_VP_CORE_V1=1` + clock-fix default ON + music eyes-on |
