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
  composed through the LGP. Current acceptance requires 120 Hz; measured
  cadence still fails that gate in several modes.
- **Separate audio and rendering tasks** — audio runs on Core 0, rendering on
  Core 1. The current acceptance target is below 8 ms from audio to visual
  output. Audio service timing alone does not establish that latency.

<!-- BEGIN S3 REPAIR RESULTS -->
## 5 November S3 repair

Silicon-tested source: `36607a8f`; final source `e42eec55` adds only the
registry-compatible silence-dwell declaration repair. The diagnostic B489 capture shows modes 7, 11 and
32 dark in both quiet windows and lit throughout their music windows. The
seven targeted effects still exceed the 2 ms ceiling; mode 24 also fails the
diagnostic cadence gate. The sixty-second settings-save fallback was captured; quiet-edge save timing and
whole-session save cadence remain OPEN. Held-out beat qualification was not run.

The normal-image 28-mode capture completed and its primary-output checksums
were independently verified; mode 27 remained dark in its sampled window.
The single full suite returned **2,027 passed, two skipped, one failed**.
The registry-sync failure was repaired and four focused tests passed; the full
suite was not rerun. All 45 saved settings matched after restoration. Normal-image per-effect timing and frame-start cadence
remain **OPEN**: its primary-only render trace records output-store timestamps
in milliseconds, not effect calls or dispatch starts. Diagnostic timing is
reported separately in the [device registry](./docs/hardware/device-build-registry.md#s3-repair-2026-11-05).
<!-- END S3 REPAIR RESULTS -->

## Hardware

| | |
|---|---|
| MCU | ESP32-S3-DevKitC-1-N16R8 (dual-core Xtensa LX7 @ 240 MHz) |
| Flash / PSRAM | 16 MB flash (QIO), 8 MB OPI PSRAM, 512 KB SRAM |
| Audio in | I2S MEMS microphone (12.8 kHz build contract) |
| LED out | FE: native 16-bit WS2816 packing; current B489 bench: WS2812. Installed FastLED RMT5 AUTO disables DMA. |
| Control | USB-CDC serial (115200) + optional AP-only WebSocket bridge |

## Build & flash

This project builds with **PlatformIO** (pioarduino 54.03.20 ≡ arduino-esp32
3.2.0 / ESP-IDF 5.4.1). FastLED 3.10.3 is resolved via `lib_deps`.

```bash
# Build the shipping single-S3 Founders' Edition source
pio run -e k1_fe

# Connected B489 bench only; port observed 5 November 2026.
# The canonical flasher checks target identity and verifies the running image.
bash scripts/agent/k1-flash-verified.sh k1_fe_bench_b489 --port /dev/cu.usbmodem101
```

> **Device discipline.** Each physical unit is bound to exactly one build
> environment by GPIO map — never cross-flash. See
> [`docs/hardware/device-build-registry.md`](./docs/hardware/device-build-registry.md).
> Match USB serial and chip identity before using any port. B489 is the
> available WS2812 bench; Main RPL is a separate, unavailable WS2816 unit.
> `k1_hardware` remains a legacy build and a host-gate target, not the B489
> FE bench environment.

## Test

A host-side Python regression harness validates the DSP and render logic
offline (no device required):

```bash
python3 -m pytest tests/ -q
```

The [light-show acceptance standard](./tools/esp_emulator/k1_lightshow_acceptance.json)
also requires musical meaning, final colour, independent controls, motion,
silence/return behaviour and measured S3 deadlines. A passing host suite does
not qualify physical output. The 5 November assessment retains failed beat,
effect and cadence gates; see the device registry for exact image and receipts.

## Architecture (audio → light)

```
I2S mic (Core 0)
  → Goertzel GDFT (133 Hz)            SPECTRASYNQ_K1_FIRMWARE/audio/
  → onset / beat / chord / tempo
  → K1AudioFrame + acquired semantic/spectrum sidecars
  → Smart / beat-aware director       SPECTRASYNQ_K1_FIRMWARE/director/
  → effect render (Core 1)           SPECTRASYNQ_K1_FIRMWARE/effects/
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
