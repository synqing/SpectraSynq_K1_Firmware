# SpectraSynq K1 Firmware

Real-time, music-to-light firmware for the **SpectraSynq K1** — a dual-channel,
edge-lit Light-Guide-Plate (LGP) lighting instrument. The K1 listens to music
through an on-board MEMS microphone, analyses it with a Goertzel-based spectral
engine, and renders synchronized visual shows across two independently-driven
LED channels diffused through a sealed light-guide plate.

> **Heritage & licence.** This firmware is a derivative work of
> [Sensory Bridge](https://github.com/connornishijima/SensoryBridge) by Connor
> Nishijima (Lixie Labs), licensed under the **GNU GPL v3.0**. SpectraSynq K1
> remains GPL-3.0 (see [`LICENSE`](./LICENSE)) and preserves the upstream
> author's attribution (see [`NOTICE`](./NOTICE)). Inherited heritage modules
> keep the `sb_` source prefix to mark their provenance.

---

## What it does

- **Spectral analysis** — Goertzel GDFT at **133 Hz** frame rate (96-sample
  chunks @ 12.8 kHz), producing an 80-bin spectrum mapped to 24 perceptual
  octave bands.
- **Musical features** — per-band onset detection, periodicity/PLL beat
  tracking, and chord/harmonic saliency, published as a read-only
  `AudioSemanticState` snapshot across cores.
- **Dual-channel rendering** — independent primary/secondary edge effects
  composed and diffused through the LGP; ~100 FPS render loop.
- **Low-latency by design** — audio runs hard-real-time on Core 0, rendering on
  Core 1; the design target is <50 ms audio-to-LED (not yet measured
  end-to-end on device — see the audit backlog).

## Hardware

| | |
|---|---|
| MCU | ESP32-S3-DevKitC-1-N16R8 (dual-core Xtensa LX7 @ 240 MHz) |
| Flash / PSRAM | 16 MB flash (QIO), 8 MB OPI PSRAM, 512 KB SRAM |
| Audio in | I2S MEMS microphone (12.8 kHz build contract) |
| LED out | WS2812B / APA102 via RMT5 DMA, dual channel |
| Control | USB-CDC serial (115200) + optional AP-only WebSocket bridge |

## Build & flash

This project builds with **PlatformIO** (pioarduino 54.03.20 ≡ arduino-esp32
3.2.0 / ESP-IDF 5.4.1). FastLED 3.10.3 is resolved via `lib_deps`.

```bash
# Build the production firmware
pio run -e k1_hardware

# Flash to the device (a pre-upload guard verifies USB serial + chip ID
# before writing — it refuses a mismatched target)
pio run -e k1_hardware -t upload

# Serial monitor (live status + hotkeys)
pio device monitor -b 115200
```

> **Device discipline.** Each physical unit is bound to exactly one build
> environment by GPIO map — never cross-flash. See
> [`docs/hardware/device-build-registry.md`](./docs/hardware/device-build-registry.md):
> the main K1 (`/dev/tty.usbmodem1401`, chip `F887A500`) takes `k1_hardware`;
> the bench unit (`12201`, chip `B489A500`) takes `k1_bench_reference`.

## Test

A host-side Python regression harness validates the DSP and render logic
offline (no device required):

```bash
pytest tests/          # full host regression (≈560 tests)
```

Host green is a compile + numeric-correctness gate. **Device eyes-on remains
the final perceptual gate** before a production release.

## Architecture (audio → light)

```
I2S mic (Core 0)
  → Goertzel GDFT (133 Hz)            SPECTRASYNQ_K1_FIRMWARE/audio/
  → onset / beat / chord / tempo
  → AudioSemanticState (cross-core publish)
  → Smart / beat-aware director       SPECTRASYNQ_K1_FIRMWARE/director/
  → effect render (Core 1, ~100 FPS)  SPECTRASYNQ_K1_FIRMWARE/effects/
  → dual-channel LGP composition → FastLED RMT5 → LEDs
```

See [`CLAUDE.md`](./CLAUDE.md) for the full module map and build-environment
reference, and [`docs/spec-index.md`](./docs/spec-index.md) for lane authority.

## Safety

⚠️ **Photosensitive Epilepsy (PSE):** people with
[photosensitive epilepsy](https://en.wikipedia.org/wiki/Photosensitive_epilepsy)
should not operate or view the K1. Visual effects are constrained to spatial /
transport motion (no global full-field strobing) by design, but this warning
applies regardless.

## Licence

GNU General Public License v3.0 — see [`LICENSE`](./LICENSE) and
[`NOTICE`](./NOTICE). Derivative of Sensory Bridge © Connor Nishijima / Lixie
Labs, GPL-3.0.
