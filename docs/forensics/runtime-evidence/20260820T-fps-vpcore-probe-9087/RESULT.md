# FPS probe under RMT-on-VP — RESULT (`9087A500`, 2026-08-20)

**GO:** Captain 2026-08-20 (~04:26): "GO" on one measurement session with `k1_main_rpl_fps_agc_probe`.
**Silicon:** `IDENTITY OK: git=f96390e3 env=k1_main_rpl_fps_agc_probe epoch=1787171579`
**Chip:** `9087A500` · `/dev/cu.usbmodem1401` · flashed via `k1-flash-verified.sh`
**Env flags:** `ENABLE_VP_PERF_AUDIT=1`, `K1_SHOW_SKIP_DISCRIMINATOR_V1=1`, `K1_RMT_ALLOC_ON_VP_CORE_V1=1` (current production allocation), `K1_AGC_DT_CLOCK_V1=0` (probe forces clock-fix OFF — known delta vs production, irrelevant to LED timing). NON-SHIPPABLE. Never promote.
**Untouched:** bench `B489A500` on 1101 · F887 OFFSITE · no `start_noise_cal`.

**Question:** where does the RPL's ~6.8–7.0 ms LED frame period go (LED_FPS ~143–152) vs the bench's ~4.95 ms (~202), given identical per-DIN wire bits (160 slots × 24 bit = 80 WS2816 × 48 bit = 3,840 bits ≈ 4.8 ms + latch)?

---

## Measured split (VPF stream, mode 32, seq 2–11, steady state)

| Surface | avg / max (µs) |
|---|---|
| **VP interval** (= 1/LED_FPS) | **6,973 / 8,513** (~143 Hz) |
| **VP frame (busy)** | **5,828 / 7,061** |
| pack_us (Lever-2 packer) | **130 / 193** |
| show_us (FastLED.show call) | **1,083 / 1,440** |
| sec_render_us | 1,331 / 2,733 |
| smooth_us | 336 / 825 |
| pri_prep_us | 199 / 286 |
| pri_render_us (derived¹) | ~2,700 |
| acq_us (AP side) | 3,885 / 4,659 |
| gdft_us (AP side) | 1,753 / 1,815 |
| over / dropped | 0 / 0 |
| heap | 120,212 |

¹ `pri_render_us` EMA is boot-polluted (max 36.8 s); derived as frame − (sec_render + prep + pack + show + smooth + vu).

`:fps` / `:led_fps` samples: SYSTEM_FPS 134–140 · LED_FPS 142–145.

## Show-skip series

SYSTEM_FPS ~135 before, **~135 during skip**, ~135 after. Core 0 no longer changes when the LED wire stops — `K1_RMT_ALLOC_ON_VP_CORE_V1` has fully lifted wire servicing off the AP core (2026-08-19 probe without it: 78 → 135 on skip).

---

## Comparison vs 2026-08-19 probe (`b318a0ec`, RMT IRQs on Core 0)

| Surface | 08-19 (IRQs on Core 0) | 08-20 (IRQs on Core 1) |
|---|---|---|
| VP interval | 4,940 µs (~202 Hz) | 6,973 µs (~143 Hz) |
| VP frame | ~3,950 µs | 5,828 µs |
| show_us | 2,432 µs | 1,083 µs |
| pack_us | 123 µs | 130 µs |
| SYSTEM_FPS | ~78 | ~135 |

**Reading:** pack and the show call are cheap on both. The ~1.9–2.9 ms that stretches the VP frame under the current allocation is **RMT refill interrupt servicing landing on Core 1 mid-render** (4 controllers × ~80 refills/frame). The cost did not disappear when it left Core 0 — it moved. RPL's four-lane topology carries ~2× the bench's IRQ load, which is why the bench holds ~202 while the RPL holds ~143–152 at the same wire bit-count.

## Decision surface

- Lever-2 packer: **exonerated again** (130 µs).
- RMT serialisation/wire throughput: **exonerated** (show 1.1 ms; wire runs in background).
- **Convicted: per-symbol RMT refill IRQ servicing** — a fixed CPU tax (~2–3 ms/frame) that must land on some core. Core 0 → audio starves (78 FPS). Core 1 → LED period stretches (143 Hz). There is no core it can sit on for free.
- The 2026-08-19 stamp "I2S/LCD_CAM remains struck; next lane is ISR-core/channel-allocation, not a wire-throughput swap" is **completed and superseded**: the ISR-core lane was done (`K1_RMT_ALLOC_ON_VP_CORE_V1` promoted) and this probe quantifies its residual cost. The Captain-authorised I2S/LCD_CAM eval (2026-08-20 ~04:26, option b) targets the IRQ tax itself — the one cost RMT cannot shed — not wire throughput. Bench WS2816 colour proof is mandatory before any RPL flash.

## Perceptual note

LED_FPS 143 > audio semantic rate (~133 Hz). The gap to 202 is Core-1 headroom, not a visible deficit.

## Restore / ship stamps

| Intent | Stamp |
|---|---|
| This probe (superseded same session) | `IDENTITY OK: git=f96390e3 env=k1_main_rpl_fps_agc_probe epoch=1787171579` |
| Production restore (same session) | reflash `k1_main_rpl_im69d` @ HEAD `f96390e3` — see registry row |
