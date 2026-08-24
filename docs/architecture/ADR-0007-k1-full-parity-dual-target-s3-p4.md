# ADR-0007: K1 full-parity dual-target (S3 + P4-WIFI6)

**Status:** Accepted for architecture and scope (Captain 2026-08-21 fold-in). Not a flash GO. Not complete until both targets run the same K1 implementation.
**Date:** 2026-08-21
**Deciders:** Captain
**Tree (locked):** [`SpectraSynq_K1_Firmware`](/Users/spectrasynq/SpectraSynq_K1_Firmware) — add `env:k1_p4_wifi6`. Keep `[env:k1_hardware]` intact.
**Destination silicon:** Waveshare ESP32-P4-WIFI6 (this lab board). Pins: IM69D130 PDM CLK22/DATA21; LED DINs currently GPIO4/5 on the bench. C6 SDIO 14–19. USB 24/25.

P4 is **another hardware target for K1 Firmware**, not a separate interpretation of K1.

Do not confuse names: K1 programme “P4” (AP-input-integrity promotion) is not this SoC.

---

## Decision (locked)

**Canonical ownership:** `SPECTRASYNQ_K1_FIRMWARE` is behavioural and product authority. One shared K1 implementation. S3 adapters and P4 adapters underneath. Not old-K1 plus a new K1-ish P4 app.

**P4-Nano is donor/reference only.** Consume proven ESP32-P4 knowledge (PDM/I2S, SPI/DMA, USB, cache/DMA allocation, core/peripheral scars, C6/SDIO when radio matters). Do not recreate K1 inside P4-Nano. Do not finish P4-Nano as alternative K1.

**No third tree. No `git worktree add`.** Work in the existing K1 repo. Tab5 (`tab5_firmware/`) stays the controller; do not flash it as this port.

**Refactor only where required** so the same K1 implementation runs on both SoCs. Test for every abstraction: *is this required to preserve one K1 across S3 and P4?* If not, leave it alone. Not a general cleanup. Not a clean-room rewrite. Not “turn on dormant `IEffect` and throw away `light_mode_*.cpp`.”

**Do not retarget `k1_hardware`.** Changing `board =` is not the migration.

---

## Context (unchanged SoC facts)

Shipping K1 (`k1_hardware`) is Arduino on **ESP32-S3 N16R8** via pioarduino **54.03.20** / arduino-esp32 3.2.0 / IDF **5.4.1** / FastLED 3.10.3. AP loop core 0, VP `led_thread` core 1. Hop **12.8 kHz / 96 / d3 / 7.5 ms**. AP service p99 **8000 µs**. G8 closed on bench. Prod LED GPIO **6/7** (bench 4/5 is a different chip with the same numbers).

P4-WIFI6 is **RISC-V**, in-package PSRAM, **one GDMA-capable RMT TX**, **no native Wi-Fi/BLE** (C6 on SDIO). IM69 path frozen in K1 source to IDF **5.4.1** (`i2s_audio.h` `#error`). P4 donor builds on IDF **5.5.2**.

K1 product tree: **~65k LOC**, **~17k LOC header-only** HAL (`led_utilities.h`, `i2s_audio.h`, `lightshow_modes.h`, `globals.h`). **Zero** `#if CONFIG_IDF_TARGET_ESP32S3`. 38 modes. Shipping RF off.

P4-Nano: ESP-IDF rewrite, **7 FX**, **512-sample / 40 ms** hop, funnel gap. Evidence that continuing that rewrite does not produce K1.

Tab5 already boots Arduino-on-P4 in-repo (54.03.21 / 3.3.1, different pins). Proof that the framework exists; not a template for FastLED dual-strip + 12.8 kHz AP.

---

## Required architecture

Shared K1 emits a **logical frame** and product state. Physical LED protocol (WS2812 vs WS2816), FastLED RMT, SPI, PARLIO sit **only** in adapters. The WS2812-versus-WS2816 product decision is **separate** and must not contaminate common domain.

Logical AP vs VP stays. Physical core numbers are an adapter. Do not copy P4-Nano core inversion or S3 AP0/VP1 until measured; do not change product scheduling semantics to match a bring-up graph.

First seams (this landing):

| Seam | Shared domain | S3 adapter | P4 adapter |
|------|---------------|------------|------------|
| Colour scratch | `CRGB` via `k1_rgb.h`; working canvas `CRGB16` | FastLED RMT / Lever-2 packer | Dual-SPI queue-all/wait-all |
| Capture | hop 12.8 kHz / 96 / d3 | SPH or IM69 per pinmap; IDF 5.4.1 frozen | IM69 PDM GPIO22/21; slot asserts restamped; no 5.4.1 `#error` |
| GPIO | `K1_P4_WIFI6_PINMAP_V1` vs production 6/7 vs bench 4/5 | unchanged | GPIO4 primary **data**, GPIO5 secondary **data**, PDM 22/21. GPIO6 is C6_IO2. No LED clock pin. |
| USB / FS | existing Arduino USB CDC + LittleFS | S3 native USB | P4 USB 24/25; WCH UART for upload |
| Identity | `k1_upload_guard.py` | F887 / B489 / 9087 usbmodem | `k1_p4_wifi6` on `wchusbserial` only; refuse Tab5 usbmodem |

---

## Full parity scope (completion surface)

P4 inherits the **complete** shipping K1 behavioural surface, using the **existing implementations**, not approximations:

- Audio acquisition semantics; frozen hop 12.8 kHz / 96 / d3 / 7.5 ms
- GDFT / Lane-4; tempo; onset/chord/features; all product DSP
- All K1 light modes (not a representative subset; not P4-Nano’s seven)
- Effect state and timing; palettes; honour/ownership
- Output funnel: gamma / dither / incandescent / soft-clip / power / brightness as in K1
- Geometry and mirroring semantics
- Serial/control; configuration/state; persistence
- USB-facing behaviour; diagnostics; product identity
- Every other shipping facility that is not intrinsically S3-specific

A faster P4 implementation of the **same algorithm** is welcome. A different algorithm that is merely “similar” is not parity unless hardware makes the original impossible — then **report** what differs, why, and the closest behaviour-preserving implementation. Do not silently substitute.

**Visual parity:** same input + same state + same mode + same palette/settings → same logical K1 frame within unavoidable numerical/hardware tolerances. “P4 can light LEDs” is not the requirement. The K1 must look like the K1.

**S3 must remain K1.** After refactor, `k1_hardware` is behaviourally equivalent to the current authority. Host oracles stay the contract.

---

## Build matrix (locked intent)

- **S3:** keep pioarduino **54.03.20** / IDF **5.4.1** / FastLED 3.10.3. Do not drag `k1_hardware` to Tab5’s 54.03.21 / 3.3.1 to make P4 easier.
- **P4:** new PlatformIO `env:k1_p4_wifi6`, Arduino-on-P4 (same family as Tab5, not a second IDF product tree). Adapters may use IDF APIs. Restamp IM69 slot assertions against the P4 IDF; do not copy the 5.4.1 `#error` onto P4 and do not relax it on S3.
- P4-Nano C is **pattern donor** (SPI DMA `spi_bus_dma_memory_alloc`, WS2812 2.5 MHz encoder, PDM pins). Copy into K1 P4 adapters; do not grow P4-Nano as K1.

---

## Options

### Option A: Lift the `.ino` with `board =` P4

Rejected. Dual FastLED RMT vs one GDMA RMT TX; no `CONFIG_IDF_TARGET` seam; IM69 frozen to 5.4.1; GPIO 4/5 coincidence with bench S3.

### Option B: Shared K1 + S3/P4 adapters in the K1 repo (accepted)

Minimum seams, existing product code, `env:k1_p4_wifi6`, S3 intact. This is the migration.

### Option C: Finish P4-Nano until it looks like K1

Rejected. Wrong hop, seven FX, funnel gap. Donor only.

### Option D: Vertical slice / first-light modes / stop after LED+AP

Rejected as **completion**. Implementation may still be ordered (seams → P4 env compile → capture → logical frame on wire → remaining surfaces). None of those waypoints is “done.”

### Option E: Lab-first execution inside P4-Nano

Rejected. Captain locked product-first. P4-Nano does not become destination firmware.

---

## Hardware differences (allowed only behind the boundary)

Expected to differ: LED peripheral/transport; PDM/I2S driver; DMA allocation; task/core assignment; USB; filesystem if required; chip identity/upload protection; radio/C6 if later required.

Those do **not** authorise changing product semantics above them.

P4 LED adapter must not be two RMT-DMA devices, sequential blocking refreshes, or a 320-px software mirror. Dual-SPI queue-all/wait-all (donor) or a later-selected protocol — chosen **below** the logical frame.

### Named deltas on this lab board (restamped 2026-08-22)

Captain 2026-08-22: the two strips on IO4 and IO5 are **physically separate WS2812** lengths, 160 pixels each, **one data line per strip**. GPIO6 is C6 radio control (`C6_IO2`) and is not a LED pad. This is not a WS2816C-1313 bar split over DIN-A and DIN-B. Neither WS2812 nor WS2816 has a clock pin; `LED_CLOCK_PIN` on this pinmap is `-1`.

Captain 2026-08-24: child env `k1_p4_wifi6_led150` keeps that default loom intact and adds a proto map — 150 px/channel on GPIO39 (primary) / GPIO40 (secondary). Those pads are Waveshare SD DAT0/DAT1; leave the TF slot empty. Canvas stays 160.

| Delta | Why | Closest behaviour-preserving implementation |
|-------|-----|-----------------------------------------------|
| LED transport is dual-SPI, not dual RMT | P4 has one GDMA RMT TX | Donor queue-all/wait-all SPI: SPI2 MOSI=GPIO4, SPI3 MOSI=GPIO5 |
| Wire protocol is WS2812 24-bit GRB | Two independent WS2812 strips | Adapter encodes 8-bit funnel `CRGB` with 2.5 MHz 3-symbol/bit SPI (`0→100`, `1→110`). Shared types stay `CRGB16` / funnel `CRGB`. Not Lever-2. Not WS2816 48-bit. |
| PDM CLK=22 DATA=21 | IM69 breakout on this board | Same `K1_MIC_IM69D_PDM_V1` path as bench/RPL; different pins |
| Two full 160-px canvases | Separate physical strips | `ENABLE_SECONDARY_LEDS` true. GPIO4 gets `leds_out[0..159]`. GPIO5 gets `leds_out_secondary[0..159]`. Centre-origin 79/80 is **on each strip**. |
| Upload UART is WCH `wchusbserial*`, 115200 | CH343 bridge; S3/Tab5 enumerate `usbmodem*` | New identity row; refuse usbmodem (Tab5 + S3) |
| Arduino-on-P4 IDF 5.4.0 libs via 54.03.21 | pioarduino 54.03.21 family | Slot `static_assert` kept; 5.4.1 `#error` S3-only |
| RF off | Shipping K1 RF is off; C6 not in this programme yet | Do not enable `K1_WIRELESS_ENABLED`; do not copy Tab5 SDIO 8–13 onto C6 14–19 |

---

## Radio

Shipping K1 RF is off. RF-off **is** present-product parity. C6-hosted SoftAP stays after core migration. Do not copy Tab5 SDIO pins (8–13) onto this C6 (14–19). Do not enable `K1_WIRELESS_ENABLED` on P4 until that programme exists.

---

## Red team (binding)

- Dual RMT; sequential SPI wait; `LED_LANES=1` 320-px lie
- Flash Tab5 / B489 / RPL / F887 as the P4 target
- Treat bench-S3 GPIO4/5 as this board
- 8-bit colour into a 16-bit WS2816 setter if that protocol is used (session canon §D) **without naming it**
- Generic `heap_caps_calloc(MALLOC_CAP_DMA)` for SPI on P4 — use the host’s DMA allocator
- 48 kHz / 512-hop constants at 12.8 kHz / 96
- Shared renderer types tied to WS2816
- Porting a mode subset or P4-Nano FX list and calling it K1
- `start_noise_cal` without Captain
- Sibling worktree / third repo
- Declaring completion on compile, first light, DSP-only, or representative modes

---

## Implementation order (waypoints, not done-stamps)

1. Write this ADR + spec-index. P4-Nano: one donor-pointer, no second product story.
2. Minimum seams in K1 so domain compiles without FastLED/I2S/GPIO/USB handles as *the only* path; `k1_hardware` still the S3 product (oracles green).
3. Add `env:k1_p4_wifi6`; RISC-V compile of shared K1 + stub/real adapters.
4. P4 capture adapter: IM69 22/21, hop 96/d3, existing DSP vs oracles, p99 ≤ 8000 µs.
5. P4 LED adapter under the **existing** funnel/modes — logical frame first, physical protocol as selected for this board (separate decision).
6. Remaining surface: serial, persist, USB, identity, diagnostics — the actual K1 code, adapted not rewritten.
7. S3 regression proof + P4 eyes-on of **product** behaviour (not a demo mode). Radio still later.

---

## Completion criterion

The P4 build is **K1 Firmware running on ESP32-P4**, not a P4 application inspired by K1.

- Common product implementation covers the **full** K1 behavioural surface
- Both targets build and run from that architecture
- S3 behaviour preserved
- P4 behaviour identical or as close as unavoidable hardware differences permit, with those differences **named**

**Shipped stamp (migration):** registry `IDENTITY OK` on the P4-WIFI6 (chip, MAC, `env=k1_p4_wifi6`, git, epoch) **and** S3 `k1_hardware` still the authority **and** Captain product-look on the P4 target across the K1 surface, not a subset. Not `pio run -e k1_hardware` on P4. Not a P4-Nano demo. Not Tab5.

### Remaining ship path (this landing is not the stamp)

1. **Agent:** keep `k1_hardware` on 54.03.20; host oracles / static gates green after every seam.
2. **Agent:** `pio run -e k1_p4_wifi6` RISC-V compile of the full `light_mode_*.cpp` surface + adapters.
3. **Captain:** named flash GO for the WCH serial P4-WIFI6 only (`k1-flash-verified.sh k1_p4_wifi6`).
4. **Agent:** capture hop 12.8 kHz / 96 / d3 on device; AP p99 ≤ 8000 µs.
5. **Captain:** product-look across modes/funnel/honour — not first light.
6. **Captain:** live `:chip_id` restamp of the P4 identity row (done 2026-08-22: USB serial `5AAF278179`, chip `0743E200`).
7. **Stamp:** `IDENTITY OK: git=… env=k1_p4_wifi6` on P4 **and** `k1_hardware` still authority on S3.

---

## Do not

- Build another P4 effect framework
- Finish P4-Nano as alternative K1
- Port only selected modes
- Simplify algorithms for P4
- Substitute the 40 ms P4-Nano pipeline
- Introduce different colour semantics
- Tie shared K1 to the WS2816 experiment
- Create a third firmware tree
- Unrelated architectural cleanup
- Treat “close enough” as acceptable where exact reuse is possible
