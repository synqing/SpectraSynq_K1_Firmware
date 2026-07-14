---
abstract: "Concise capability overview of the SensoryBridge K1 firmware (v40103, ESP32-S3 dual-core) across audio pipeline, visual pipeline, hardware I/O, and Smart-Director. Each capability carries a provenance tag (LIVE / CODE-COMPLETE / BUILT-NOT-WIRED / DISABLED / DEV-ONLY). Read when you need an accurate, externally-defensible summary of what the firmware can do and what is intentionally not live. Reflects feat/gdft-harness HEAD f67054d as of 2026-06-02; verify against source before quoting in external claims."
---

# SensoryBridge K1 Firmware — Capability Overview

**Firmware version 40103 · ESP32-S3, dual-core · captured 2026-06-02 (branch `feat/gdft-harness`, HEAD `f67054d`)**

A music-to-light engine: it listens to a room through a single MEMS mic, decomposes
the sound into musical pitch and energy in real time, and renders that onto a
160-pixel addressable LED canvas through a library of audio-reactive effects —
either under hands-on control or steering itself. The benchmark is perceptual:
musical relevance and visual impact, not just "LEDs that flash to volume."

## Provenance tags

Every capability below carries a status tag, because the codebase spans several
branches and includes intentionally-disabled and dev-only surfaces:

- **[LIVE]** — flashed / running on K1
- **[CODE-COMPLETE]** — present on-branch, on-device verification pending
- **[BUILT-NOT-WIRED]** — module exists and is correct, but renders no output yet
- **[PARTIAL]** — functional but not the canonical path, or incomplete
- **[DISABLED]** — compiled but locked out of selection
- **[DEV-ONLY]** — instrumentation / test tooling, never ships in production

---

## 1 · Audio pipeline — *what it hears*

| Capability | Status | Detail |
|---|---|---|
| Mic capture | [LIVE] | IM73D MEMS over PDM, 12.8 kHz, 16-bit **mono**; `k1_prod_im73d` is the production/reference environment |
| Pitch analysis ("GDFT") | [LIVE] | **80 parallel Goertzel bins, one per semitone**, from ~110 Hz (A2) up through the musical range; per-bin variable window (long for bass, short for treble). Not an FFT — pitch-resolved by design (`constants.h:23-24`, `GDFT.h`) |
| Effective update rate | [LIVE] | DMA frames at 133 Hz; low bins interlaced → ~66 Hz lower / ~133 Hz upper spectral refresh (`GDFT.h` `interlace_flip`) |
| Chromagram | [LIVE] | 80 bins folded into **12 pitch classes** — drives note-coloured effects |
| Auto-gain (AGC) | [LIVE] | **Multi-band differential** (bass / low-mid / high-mid / high gain independently) — a loud kick doesn't wash out the highs; preserves spectral contrast (`system.h:535-544`) |
| Onset detection | [LIVE] | Generic + dedicated **bass-onset**; solid, consumed by render (Comet) and the visual-hooks layer (`sb_onset_beat.*`) |
| Noise calibration | [LIVE] | `start_noise_cal` — 256-frame two-phase: DC-offset + per-bin floor + adaptive sweet-spot level; persisted, sanity-clamped on boot (`noise_cal.h`, `GDFT.h:137-154`) |
| BPM / beat-phase tempo | **[BUILT-NOT-WIRED]** | Full Goertzel-over-novelty tempo tracker (`sb_tempo`) computes BPM, phase, confidence — **but nothing consumes it yet**; renders zero output today (`sb_tempo.h:17`) |
| GDFT correctness harness | [DEV-ONLY] | Synthetic-tone sweep validator; `ENABLE_GDFT_HARNESS` PIO env only, never in release (`gdft_harness.h`) |
| `audio_transfer.h` | [DEV-ONLY/DEAD] | Legacy `driver/i2s.h` path; not on the live capture path |

> **Bin count note:** the active fork uses **`NUM_FREQS = 80`** (one bin per canvas
> pixel before mirror-fill; `NATIVE_RESOLUTION = 160`). The legacy stock Sensory
> Bridge figure of 64 does not apply here — verified at `constants.h:23-24` /
> `config_types.h:42`.

## 2 · Visual pipeline — *what it shows*

**18-mode roster; 10 product-enabled, 8 disabled.**

| Live effects (selectable) | Character |
|---|---|
| **Bloom / Bloom-Fast / Aurora** | Centre-origin chromagram bloom + palette-flow trails |
| **Waveform / Waveform-Fast / Waveform-Hybrid** | Centre-origin spectrum/waveform with history seeding |
| **Spectrum River / River V2** | 80-bin spectrum mapped to space, flowed outward; V2 adds bass-energy "breathing" tide |
| **Comet** (v4) | Bass-onset-triggered travelling comets, 6-comet pool/channel, salience-gated lock-on + palette trails |
| **Ember** | Centre-anchored energy-bloom glow with novelty-driven shimmer |

- **Colour engine** [LIVE]: 3-tier authority — **33 cpt-city palette gradients** (LUT)
  → chromatic note-sum HSV → auto-colour-shift HSV driven by spectral novelty
  (`effect_palette_or_chroma_colour()`, `lightshow_modes.h:199`, `Palettes.h`).
- **Dual independent channels** [LIVE/CODE-COMPLETE]: primary + secondary strips can
  run *different* modes/params via per-channel `RenderParams` + isolated
  `ChannelEffectState` (no cross-bleed, no heap) (`render_params.h`, `channel_effect_state.h`).
- **Edge mixer** [LIVE]: 6 harmonic colour-blend modes (analogous, complementary,
  split, veil, triadic, tetradic) on the secondary channel, bass-driven (`sb_edgemixer_lite.h`).
- **Visual hooks** [LIVE]: onset/beat → live scalars on brightness (PHOTONS), colour
  (CHROMA), and edge strength across any mode (`sb_visual_hooks.h`).
- **Motion memory** [LIVE]: previous-frame buffer + per-channel decay state give trails/persistence.
- **Disabled** [DISABLED]: GDFT family (0–2), VU / VU-Dot, **Kaleidoscope**, Quantum
  Collapse, Ember V2 — compiled, locked out of selection. This is the known
  **effect-library bottleneck**: the engine is strong, the *roster* is the active growth lane.

## 3 · Hardware I/O — *how it's driven*

| Surface | Status | Detail |
|---|---|---|
| LED output | [LIVE] | FastLED WS2812 GRB, **2 × 160 px** strips + 1 status LED, dedicated Core-1 render task, hardware-bound FPS |
| **M5ROTATE8 encoders** | [LIVE] | 8 rotary encoders (single unit), **dual-channel via slide switch**, per-knob RGB feedback, I2C error-recovery. Map brightness/colour/mood/contrast/saturation/prism/palette/bulb-opacity + button toggles (`encoders.h`) |
| Serial control | [LIVE] | USB-CDC 115200, **~120+ commands** (single-key hotkeys + typed `:set`), `constexpr` safety dispatch table with arm-required guards (`serial_menu.h`) |
| Legacy buttons / analog knobs | [DISABLED] | Stubbed on K1v9 (pins `-1`); superseded by encoders + serial (`buttons.h`, `knobs.h`) |
| WiFi + WebSocket + web UI | **[PARTIAL]** | STA with AP-fallback (`LightCrystals`), AsyncWebSocket state push, basic HTTP UI — functional but a secondary path, not the canonical control surface |
| Persistence | [LIVE] | LittleFS, **chip-ID-keyed** CONFIG + noise-cal + cal-profile; 3 s deferred save (wear protection); 5 named presets (`bridge_fs.h`, `presets.h`) |
| VPAB / VP-perf / diag capture | [DEV-ONLY] | Flag-gated instrumentation; excluded from production per the Developer Instrumentation Boundary |

## 4 · Smart-Director (Smart-Auto) — *when it steers itself*

**[CODE-COMPLETE — wiring on `feat/gdft-harness` HEAD; default OFF]**

- **7-state audio classifier** per frame: Silence / Ambient / Steady / Build / Drop /
  Breakdown / Dense (from novelty, peak, band energies, smoothed energy-delta) (`sb_smart_director.cpp:173`).
- **Two autonomy levels**: *assist* (picks modes, respects manual override) and
  *autonomy* (full mode + palette + colour control on a rotating phase).
- **Per-state render shaping**: scales speed/brightness/colour/saturation on top of user settings.
- **Switch governance**: 8 s min-dwell, 20 s cooldown, max 2 switches/60 s, 8 s
  manual-override quiet period, and a **beat-boundary gate** so auto-switches land on
  the music (`sb_mode_selection.cpp`).
- **"Keepers" whitelist**: 7 of 18 modes are Smart-Auto-eligible — Bloom, Bloom-Fast,
  Waveform, Waveform-Fast, Waveform-Hybrid, and (newly wired `f67054d`) **Spectrum
  River + Comet**. Aurora, River V2, Ember are product-live but not yet whitelisted;
  Kaleidoscope/VU/GDFT/Quantum are excluded entirely.

## Runtime architecture

- **ESP32-S3, dual-core FreeRTOS.** Core 0 = audio (I2S capture, GDFT, snapshot,
  input polling); Core 1 = render (`led_thread`, smoothing, Smart-Director, visual
  hooks, mode selection, `FastLED.show()`).
- **Cross-core transfer** via a single `portMUX` spinlock-guarded `SBAudioSnapshot`
  (+ `SBOnsetBeatEvent`, `SBSmartDirectorOutput`) — no queues, no semaphores, no heap.
- **Frame rate** is runtime-measured, not capped; `led_thread` yields one tick
  (`vTaskDelay(1)`) between frames, so render is effectively hardware-bound.

---

## Provenance & branch map

- **Stable base:** `origin/refactor/main` (ed22d33) — refactor complete, all gates green.
- **This branch (`feat/gdft-harness`, HEAD `f67054d`):** new effects (Comet v4,
  Spectrum River V1/V2, Ember) **built and flashed to K1 (2026-06-02)**; Smart-Auto
  keeper-wiring is code-complete, **on-device verification of the keepers path still
  pending** (commit-fresh).
- **Branch-gated / not in this build:** runtime AGC-mode toggle (`feat/agc-bypass`),
  secondary RenderParams polish (`feat/secondary-renderparams`), VP product baseline
  (`feat/vp-product-baseline`). `CHROMA_PROFILE` config field has landed at v40103.

## Honesty caveats for external claims

The three claims most likely to be challenged — kept honest rather than aspirational:

1. **Audio analysis is mono**, not stereo. Independent dual-*channel* refers to the two
   LED output channels, not two audio channels.
2. **Tempo/BPM is computed but renders nothing yet.** Beat-reactive effects are
   *onset*-driven, not phase-locked to a tracked tempo.
3. **The effect library, not the engine, is the current limiter.** Roughly half the
   modes are intentionally locked out pending quality.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-06-02 | agent:claude-opus | Created — concise full-capability overview across audio/visual/IO/Smart-Director, grounded in 4-agent source survey of feat/gdft-harness HEAD f67054d; NUM_FREQS=80 contradiction resolved against constants.h:24. |
