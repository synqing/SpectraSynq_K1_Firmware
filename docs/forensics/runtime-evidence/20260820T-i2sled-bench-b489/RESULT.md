# I2S/LCD_CAM LED emit eval — bench leg (`B489A500`, 2026-08-20)

**Lane GO:** Captain 2026-08-20 ~04:26 (option b: I2S/LCD_CAM driver eval behind a flag, bench proof before RPL).
**Silicon:** `IDENTITY OK: git=e5fb5710 env=k1_bench_im69d_i2sled_probe epoch=1787173445`
**Chip:** `B489A500` · `/dev/cu.usbmodem1101` · flashed via `k1-flash-verified.sh`
**Driver:** `-DFASTLED_USES_ESP32S3_I2S=1` reroutes `WS2812Controller800Khz` → FastLED's vendored Yves LCD_CAM parallel driver (double-buffered, one CPU transpose + one async DMA + ONE completion IRQ per frame). Zero firmware source changes.
**Untouched:** RPL `9087A500` on production `k1_main_rpl_im69d @ f96390e3` · F887 OFFSITE · no `start_noise_cal` (cal inherited, `cal_source=persisted_profile cal_valid=1`).

---

## Measured (mode 32, VPF seq 2–11 steady state)

| Surface | I2S/LCD_CAM (this run) | RMT baseline (69e21140, same unit) |
|---|---|---|
| LED_FPS | **176–177** | 202.34 |
| SYSTEM_FPS | 133–141 (healthy) | 136.63 |
| VP interval | 5,681 / 6,542 µs | ~4,940 µs |
| VP frame | 4,680 / 5,753 µs | — |
| show_us | 2,392 / 3,625 µs | — |
| pack_us | 0 (no Lever-2 on bench) | 0 |
| heap | 232,612 | — |
| over / dropped | 0 / 0 | — |
| stack HWM (words) | ap=4,884 vp=5,084 | — |

## Reading

- **Device is fully alive under the I2S driver**: boots, renders, AP telemetry flowing, no crashes, no drops, heap and stacks healthy.
- `show_us` 2.4 ms = the driver's one-shot 16-lane bit-transpose + 300 µs vendored extra-wait + DMA queue. It is a **deterministic CPU block on the VP task** — the scattered per-symbol RMT refill IRQs are gone entirely.
- Bench LED_FPS drops 202 → 177: expected. This 2-lane unit never paid a meaningful RMT IRQ tax on its VP core (no `K1_RMT_ALLOC_ON_VP_CORE_V1` here; Core 0 absorbed it with slack), so the transpose is a net add for the bench. **The bench is the driver-correctness leg, not the win leg.** The win leg is the RPL, whose 4-lane RMT IRQ tax (~2–3 ms/frame on Core 1, convicted in `20260820T-fps-vpcore-probe-9087`) the transpose replaces at ~¼ the cost.
- RPL prediction under I2S: VP frame ≈ true render ~1.5 ms + pack 0.13 ms + show ~2.4 ms ≈ 4.1 ms → LED_FPS ~175–195 (from 143) with SYSTEM_FPS unchanged (~135).

## Gate status

| Gate | Status |
|---|---|
| Bench boot/stability/telemetry under I2S | **PASS** (this capture) |
| Bench colour truth (Captain eyes-on the plates) | **OPEN — Captain verdict required** |
| RPL WS2816 two-slot latch + colour truth | BLOCKED on bench eyes-on PASS + named Captain GO to flash `k1_main_rpl_i2sled_probe` |

## Restore stamps

| Intent | Stamp |
|---|---|
| This eval (current bench silicon) | `IDENTITY OK: git=e5fb5710 env=k1_bench_im69d_i2sled_probe epoch=1787173445` |
| Restore bench RMT production look | reflash `k1_bench_im69d` (HEAD; prior state was `@ 69e21140` epoch `1787164605`) |
