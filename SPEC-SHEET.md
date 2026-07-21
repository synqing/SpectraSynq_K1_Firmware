# SpectraSynq K1 — Authoritative Product Spec Sheet

**This document is the single source of truth for K1 marketing and product
specifications.** Every number below was extracted from the K1 firmware source
code. Marketing copy, landing pages, and datasheets MUST cite this sheet (and
the firmware files it references) rather than restating numbers from memory.

- **Repository:** `synqing/SpectraSynq_K1_Firmware` (canon)
- **Last verified:** 2026-07-22 @ `origin/main` `accc5f09d320a8e207b39495f62889c8748099b3`
- **Verification method:** direct read of source/config at the ref above, with file:line evidence.

Paths are relative to the repository root. Firmware sources live under
`SPECTRASYNQ_K1_FIRMWARE/`.

---

## Audio / spectral engine

| Spec | Value | Source |
| --- | --- | --- |
| Algorithm | Goertzel-based Discrete Fourier Transform (**GDFT**, not FFT) | `SPECTRASYNQ_K1_FIRMWARE/audio/GDFT.h:11`; `SPECTRASYNQ_K1_FIRMWARE/audio/k1_gdft_core.h:26` |
| Frequency bins | **80** parallel Goertzel bins (`NUM_FREQS`) | `SPECTRASYNQ_K1_FIRMWARE/system/constants.h:121`; `SPECTRASYNQ_K1_FIRMWARE/system/config_types.h:121` |
| Sample rate | **12,800 Hz** (`DEFAULT_SAMPLE_RATE`; production build flag) | `SPECTRASYNQ_K1_FIRMWARE/system/config_types.h:37`; `platformio.ini:75` |
| Analysis hop | **96 samples/frame** (`DEFAULT_SAMPLES_PER_CHUNK`) | `platformio.ini:76` |
| Analysis frame rate | **≈133 Hz** (12,800 Hz ÷ 96-sample hop) | derived from the two rows above |
| Output canvas | **160-px** render canvas (`NATIVE_RESOLUTION`); 80 bins → canvas, mirror-filled at the midpoint | `SPECTRASYNQ_K1_FIRMWARE/system/constants.h:118-121` |
| Chromagram | **12** pitch classes (chromagram / chord modes) | `SPECTRASYNQ_K1_FIRMWARE/system/config_types.h:157-158` |
| AGC perceptual bands | **4** (bass, low-mid, high-mid, treble; `NUM_AGC_BANDS`) | `SPECTRASYNQ_K1_FIRMWARE/system/constants.h:177-178` |
| Onset / beat detection | **Yes** — per-band onset + beat tick (`K1_ONSET_V2` shipped) | `SPECTRASYNQ_K1_FIRMWARE/audio/k1_onset_beat.cpp`; `platformio.ini:95` |
| Tempo / BPM tracking | **Yes** — PLL beat-phase flywheel + ACF (`K1_TEMPO_*` shipped) | `SPECTRASYNQ_K1_FIRMWARE/audio/k1_tempo.cpp`; `platformio.ini:93-94,136` |
| Chord / harmonic detection | **Yes** — `ChordState` + harmonic saliency (`K1_CHORD_V2` shipped) | `SPECTRASYNQ_K1_FIRMWARE/audio/k1_chord_detect.cpp`; `platformio.ini:96` |

> Note: `audio/GDFT.h` retains a legacy header comment describing "64 bins" and
> "256 new samples per frame" from the upstream SensoryBridge lineage. The
> **authoritative production values are 80 bins and a 96-sample hop** as set by
> `NUM_FREQS` and the `DEFAULT_SAMPLES_PER_CHUNK` build flag; the legacy prose is
> not the shipped configuration.

## Effects / programmes

| Spec | Value | Source |
| --- | --- | --- |
| Light modes defined | **30** (`NUM_MODES`; append-only, IDs 0–29) | `SPECTRASYNQ_K1_FIRMWARE/system/config_types.h:155-188` |
| Playable (enabled) modes | **22** (8 disabled via `light_mode_is_enabled`) | `SPECTRASYNQ_K1_FIRMWARE/system/config_types.h:195-209` |
| Native (v3 IEffect) registry rows | **5** (`beat_pulse_resonant`, `lgp_harmonic_tide`, `lgp_beat_prism`, `lgp_flux_rift`, `lgp_transient_lattice`) | `SPECTRASYNQ_K1_FIRMWARE/effects/framework/EffectRegistry.cpp:308-316` |
| Effect families | **4** — Legacy `0x00`, V3 Beat `0x10`, V3 Chord `0x11`, V3 LGP `0x12` | `SPECTRASYNQ_K1_FIRMWARE/effects/framework/EffectRegistry.h:52-55` |

## Palettes

| Spec | Value | Source |
| --- | --- | --- |
| Gradient palettes | **44** (`gGradientPaletteCount`) | `SPECTRASYNQ_K1_FIRMWARE/visual/Palettes.h:76-125` |

## Zones

| Spec | Value | Source |
| --- | --- | --- |
| Zones | **2** (`NUM_ZONES`) | `SPECTRASYNQ_K1_FIRMWARE/system/constants.h:122` |

## LEDs

| Spec | Value | Source |
| --- | --- | --- |
| LED chip | **WS2812B** | `SPECTRASYNQ_K1_FIRMWARE/visual/led_utilities.h:1095`; `SPECTRASYNQ_K1_FIRMWARE/system/constants.h:315` |
| LEDs per channel (default) | **160** (`LED_STRIP_MODE 3` / `LED_COUNT_VALUE`; SB v9 K1 hardware) | `SPECTRASYNQ_K1_FIRMWARE/system/config_types.h:123-140` |
| Channels | **2** — primary + secondary (`make_primary_channel` / `make_secondary_channel`; dual `addLeds`) | `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:192-220`; `SPECTRASYNQ_K1_FIRMWARE/visual/led_utilities.h:1105-1112` |
| Geometry | **Centre-origin**, mirror-filled across the second half (mirror anchor at `NATIVE_RESOLUTION/2`) | `SPECTRASYNQ_K1_FIRMWARE/system/constants.h:118-119` |

## Render rate

| Spec | Value | Source |
| --- | --- | --- |
| Target FPS | **100** (`K1_TARGET_FPS`; frame budget 8,333 µs) | `SPECTRASYNQ_K1_FIRMWARE/effects/framework/EffectContext.h:66` |
| Reference FPS | **120** (`K1_REFERENCE_FPS`, v3 persistence baseline) | `SPECTRASYNQ_K1_FIRMWARE/effects/framework/EffectContext.h:64` |
| Measured range | ~100–185 FPS (uncapped render loop, hardware-dependent) | `SPECTRASYNQ_K1_FIRMWARE/effects/framework/EffectContext.h:36` |

## Control surfaces

| Spec | Value | Source |
| --- | --- | --- |
| Serial commands | **33** safety-classified commands in the Row-1 dispatch table (single source of truth); additional typed `:key=value` settings handled in `serial_cmd_handlers.cpp` | `SPECTRASYNQ_K1_FIRMWARE/serial/serial_cmd_table.def` |
| Physical encoders | **Yes** — M5Stack Rotate8 (8-channel I2C encoder), shipped in the default build | `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:25,85,104` |
| REST/HTTP endpoints | **0** — no HTTP route handlers; control is serial + (gated) WebSocket | verified: no `server.on`/HTTP routes under `SPECTRASYNQ_K1_FIRMWARE/network/` |
| WebSocket endpoints | **1** endpoint (`/ws`, port 80) with **2** request kinds (`k1.state.get`, `k1.capabilities.get`) — **gated**, not in the production build | `SPECTRASYNQ_K1_FIRMWARE/network/k1_wireless.cpp:24,74,679-693`; gated by `platformio.ini:371-379` (`env:k1_wireless_ab_probe`, `-DK1_WIRELESS_ENABLED`) |
| BLE | **Present but gated / non-shipping** — BLE-MIDI central for the "SpectraSynq Remoted" dial; only under `-DK1_BLE_REMOTED` | `SPECTRASYNQ_K1_FIRMWARE/network/ble_remoted_central.h:4-6`; `platformio.ini:396-405` (`env:k1_ble_remoted_probe`) |
| iOS app | **Unverified** — no iOS/CoreBluetooth client code present in this firmware repo | not found under `SPECTRASYNQ_K1_FIRMWARE/` |

> Note: the default/production build (`build_src_filter`, `platformio.ini:44`)
> does **not** compile `network/`. WiFi AP, WebSocket, and BLE-MIDI are
> bench/probe-only environments. Serial and the M5Rotate8 encoders are the
> shipping control surfaces.

## MCU / board

| Spec | Value | Source |
| --- | --- | --- |
| Board / SoC | **ESP32-S3** (`esp32-s3-devkitc1-n16r8`) | `platformio.ini:21` |
| Flash | **16 MB** | `platformio.ini:28-30` |
| PSRAM | **8 MB OPI** (N16R8; `psram_type = opi`, `memory_type = qio_opi`) | `platformio.ini:24-26,66` |
| Toolchain | pioarduino 54.03.20 ≡ arduino-esp32 3.2.0 / ESP-IDF 5.4.1 | `platformio.ini:4` |

---

## In-flight work that may change these specs before launch

The authoritative numbers above are from `origin/main`. The canon primary
working copy is currently on branch `bench/ws2816-split` with uncommitted
changes; the following bench work would change the **LED / channel** specs if it
lands, and is all currently **flag-gated and non-shippable**:

- **WS2816C-1313 split-geometry bench build** (`env:k1_bench_ws2816_1313`,
  `-DK1_WS2816_1313_V1`; `platformio.ini:280-313`): drives **WS2816** (48-bit /
  pixel) as two offset controllers over one buffer (`LED_NEOPIXEL_X2` shape). If
  productised this changes **LED chip (WS2812B → WS2816)** and the channel/geometry
  model.
- **Custom 12V-5050 dual-channel build** (2026-07-12; `SPECTRASYNQ_K1_FIRMWARE/system/config_types.h:126`):
  **138** addressable LEDs **per channel**, driven as WS2812B at 800 kbps. Changes
  the **per-channel LED count**.
- **Earlier single-channel wall-bounce build** (`K1_CUSTOM_LED_V1`;
  `SPECTRASYNQ_K1_FIRMWARE/system/config_types.h:125-132`): **224** LEDs on the
  primary channel only, secondary dropped.

None of the above is on `origin/main`; treat them as "may change" and re-verify
against `origin/main` at launch.
