# FPS / AGC probe — RESULT (`9087A500`, 2026-08-19)

**GO:** Captain flash `k1_main_rpl_fps_agc_probe` to Main RPL only.  
**Silicon:** `IDENTITY OK: git=b318a0ec env=k1_main_rpl_fps_agc_probe epoch=1787141154`  
**Chip:** `CHIP ID: 9087A500` (`02_dump.txt`) · USB `B4:3A:45:A5:87:90` · `/dev/cu.usbmodem1401`  
**Cal:** `CAL_SOURCE: persisted_profile` · `CAL_VALID: 1` · SSL 172 · DC −247. **Do not re-fire `start_noise_cal`.**  
**Env flags:** `ENABLE_VP_PERF_AUDIT=1`, `K1_SHOW_SKIP_DISCRIMINATOR_V1=1`, **`K1_AGC_DT_CLOCK_V1=0`** (baseline alphas). NON-SHIPPABLE. Never promote from this env.  
**Untouched:** bench `B489A500` · F887 OFFSITE · no WCH adapter.

Capture: `capture_probe.py` after the `:show_skip=` parser fix (`b318a0ec`). First flash `dec5fb53` pack/show numbers remain consistent; its skip series was invalid (`Bad command`) and is superseded by this run.

---

## Pack / show (VPF 1 Hz, mode 32, seq 1–10)

From `04_vpf_stream.txt` + `05_vp_perf_status.txt` (this capture):

| Surface | avg / max (µs) |
|---|---|
| **pack_us** | **123 / 146** |
| **show_us** | **2432–2468 / 3560** |
| VP interval | ~4940 / 5511 (~202 Hz) |
| VP frame | ~3920–3980 / 4960 |
| **gdft_us** | **~6060 / 7861** (stream avg of avgs) |
| acq_us | ~1480 / 2808 |
| heap | 122292 |
| over / dropped | 0 / 0 |

`:dump` (`02_dump.txt`): `SYSTEM_FPS: 74.39` · `LED_FPS: 203.05`.  
Script `led_fps` sample: **202.52**.

**Decision vs handover rules:**

- `show_us` **2.4 ms avg / 3.6 ms max** — not ≳ 9.6 ms. **Does not convict LED serialisation.** `LED_FPS` ~203 matches a ~4.9 ms VP interval.
- `pack_us` ~123 µs — identity skip is cheap; Lever-2 packer is not the AP hole.
- **GDFT ~5.6–6.2 ms** is most of the 7.5 ms AP chunk **on this dump**, but that is not the discriminator (see skip series).

---

## Show-skip `SYSTEM_FPS` series (armed)

Ack: `SHOW_SKIP: on ms=5000`  
Status: `remaining_ms=4392` (armed, not `Bad command`).

| Phase | `SYSTEM_FPS` |
|---|---|
| baseline (pre-stream) | 78.70 … 82.98 (n=6) |
| pre-skip | 76.17 … 78.24 (n=4) |
| **armed skip (first 8 of 12)** | **132.74 … 135.88** (mean **134.6**) |
| skip expired (last 4 of 12; 5 s window, script ran ~6 s) | 81.23, 78.63, 76.83, 79.06 |
| post `:show_skip=off` | 74.15 … 80.49 (n=6) |

Hop design rate is **133.33 Hz** (96 samples @ 12.8 kHz). Armed skip sits on that hop (± ~2 %). The 10-frame average then falls back to ~76–80 Hz as soon as `show_leds()` resumes.

**Decision (handover §2.3, C4 now closed for this unit):**

- Jump **~78 → ~133–136** while skip is armed **convicts LED-wire *servicing* (ISR / bus contention) on Core 0**.
- It does **not** convict RMT *serialisation* time (`show_us` stays ~2.4 ms).
- Standing hypothesis (setup()-time `show()` pinning RMT refill IRQs on Core 0 at ~202 Hz) is **now supported by the discriminator**. Pinning vs other `show()` Core-0 side-effects is the next measurement, not this stamp.
- **I2S / LCD_CAM LED remains struck.** Next lane is ISR-core / channel-allocation, not a wire-throughput swap.

`pri_render_us` max `41661221` is a polluted EMA (boot / first-frame); ignore the max. `show_us` during skip is stale last-sample (gate skips `show_leds()` so Lever-2 timers do not refresh).

---

## What this does not close

- Clock-fix (`K1_AGC_DT_CLOCK_V1=1`) is **in source default ON**; this probe binary **forces it OFF**. Not on this silicon.
- Honour / `k1_hardware` / F887 / dull-show **#119716** stay separate.
- Bench `LED_FPS` remains RPL-only unless a later `B489A500` GO.
- Probe env **must not** be promoted.

---

## Restore / ship stamps

| Intent | Stamp |
|---|---|
| This probe (current silicon) | `IDENTITY OK: git=b318a0ec env=k1_main_rpl_fps_agc_probe epoch=1787141154` |
| Restore Lever-2 ship look | reflash `k1_main_rpl_im69d` @ **`a6149b29`** (epoch `1787031584`) |
| Clock-fix on RPL (later named GO) | `k1_main_rpl_im69d` at the clock-fix commit (`dec5fb53` lineage; HEAD after parser fix still carries it) + music eyes-on |
