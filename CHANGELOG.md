# Changelog

All notable changes to the SpectraSynq K1 Firmware are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/); this project
versions firmware via `FIRMWARE_VERSION` and tagged releases.

## [Unreleased]

### Changed
- **`k1_custom` overwritten: dual-214 wall-bounce (was single-channel 224 test bed).**
  Two independent WS2812B 5V channels of **214 LEDs each** (GPIO4/5), bare bulbs
  (no LGP), white-wall bounce viewing. Still extends `k1_bench_im73d_ble` (IM73D +
  K718). `NATIVE_RESOLUTION` stays 160 → upsample 160→214 both channels.
  `CONFIG.MAX_CURRENT_MA` locked to **2500** (2.5 A total) at default + boot force.
  Flag remains `K1_CUSTOM_LED_V1`. Retired the secondary-drop path. Detail:
  `docs/hardware/k1-custom-dual-214-wall-bounce-2026-07-12.md`.

### Added
- **`k1_custom_rgbic` build env (custom rig, NOT the K1 product) — EYES-ON PASS 2026-07-12.**
  Dual-channel variant of the bench build: swaps the two WS2812B channels (2× 160) for
  **two 138-LED addressable 12V 5050 strips**, driven as **WS2812B 800 kbps 250ns/750ns,
  RGB order** — an exact match to the Captain's proven Pixelblaze config. DATA pins
  unchanged from the bench K1 (primary GPIO4, secondary GPIO5); the strip's second
  ("CLK") wire is driven with **mirrored data** on GPIO7 / GPIO8 (GPIO8 reclaimed from
  the dead `RNG_SEED_PIN`) so the real DIN always gets a valid signal. Extends
  `k1_bench_im73d_ble` → IM73D PDM mic + NimBLE BLE-MIDI central (K718 Remoted dial),
  same base as `k1_custom`. `NATIVE_RESOLUTION` stays 160 → `scale_to_strip()`
  downsamples 160→138 on both independent channels. All gated behind
  `K1_CUSTOM_RGBIC_V1`; flag-off → `k1_hardware` / `k1_bench_reference` /
  `k1_bench_im73d` / `k1_custom` byte-identical. NON-SHIPPABLE, bench K1 only.
  **Bring-up root cause (documented so it's not repeated): the corruption was a MISSING
  COMMON GROUND** between the external 12V PSU and the ESP32-S3 — not protocol/order.
  Dead-ends tried before the Pixelblaze screenshot arrived: APA102/clocked-SPI and
  FastLED's `WS2815` chipset (wrong timing); both reverted.

### Removed
- **Beat Pulse (30), Moiré Cathedral (33), Cannonade (34): DELETED on 2026-07-12
  A/B fail** (Captain: "must be deleted / delete that filth"). Removed from every
  selection path via `light_mode_is_enabled()` (the Ember-V2 "unselectable" pattern);
  enumerators kept as ID-stable tombstones so Shockwave (35) and Iris (36) keep their
  `:set_mode` numbers. Effect code retained but unreachable (no shipping impact). A
  hard file-rip (with renumber) can follow if Captain wants the tree physically scrubbed.

### Changed
- **Bloom BassTreble (31): second motion rework after the first fix still read as
  "twitchy/confused"** on the A/B. Root cause of the residual twitch: integer-step
  scroll at low speed lurches, and the sqrt radial warp AMPLIFIES each near-centre
  step into a visible jump. Fixes: (1) SUB-PIXEL scroll — the display samples the
  transport at a fractional offset (`scroll_accum`) so motion is smooth between
  integer steps; (2) calmer speed range (35–85 px/s, was 22–100) so flow never
  near-stalls and is less erratic; (3) calmer radial colour walk (0.34, was 0.784 —
  a near-full palette traverse that read as "confused"). Awaiting Captain re-A/B.

### Added
- **Captivation families (Cannonade / Shockwave / Iris): three new purpose-built
  captivating effect modes for a 4-way on-device A/B vs Waveform (mode 32)** —
  built per `docs/architecture/effect-decomposition/00b-captivation-transposition.md`
  §6 (transpose Waveform's captivation DNA without collapsing into looking like
  Waveform). `LIGHT_MODE_CANNONADE` (34): ballistic lob from centre, arc-and-return
  under inward gravity, centre CRACK on impact. `LIGHT_MODE_SHOCKWAVE` (35): pure-age
  expanding concentric shells (radius = vel·age, radius ⟂ amplitude — the deliberate
  contrast to amplitude-coupled `pulse_prism`, which is left untouched), timbre-tilt
  colour. `LIGHT_MODE_IRIS` (36): in-place spring dilate-and-recoil membrane driven by
  the live beat-phase axis (`k1_tempo_read`). Each ships a pure, host-tested math core
  (`effects/{cannonade,shockwave,iris}_math.h` + `tests/native/test_*_math.cpp`),
  inherits the shared easing/silence-floor/centre-origin contract via `visual/easing.h`,
  and is enabled for manual `:set_mode` but kept out of the director allow-list.
  Build spec: `docs/effect-craft/captivation-families-build-spec.md`. Modes-only,
  no director/A-side behaviour change; awaiting Captain on-device A/B before commit.
- **Lane N4 (factory provisioning tooling): factory image + per-unit NVS** —
  new read-only, non-flashing `scripts/release/make_factory_image.py` assembles
  a single flashable factory image (`esptool merge_bin`: bootloader @ `0x0`,
  partitions @ `0x8000`, optional NVS @ `0x9000`, `boot_app0` @ `0xe000`,
  firmware @ `0x10000`) and prints the exact `esptool write_flash 0x0 <image>`
  command for a human to run — it never flashes. New
  `scripts/release/make_unit_nvs.py` generates a per-unit NVS partition
  (`0x5000`) from the placeholder template `scripts/release/unit_nvs_template.csv`
  via ESP-IDF `nvs_partition_gen.py` (run under the PlatformIO penv interpreter);
  it never flashes, never pushes, and never mints NVS keys. The per-unit
  serial/SKU scheme is Captain decision **D4 — UNDECIDED**, so the template and
  defaults are clearly-marked placeholders. New runbook
  `docs/hardware/factory-flash-runbook.md` (build → assemble → provision →
  verify-by-chip-ID → flash → confirm `Hash of data verified` + `Hard resetting`).
  Host gate `tests/test_factory_tooling_static.py` (read-only/non-flashing/
  no-push/no-keygen invariants + D4 placeholder discipline).
- **Lane N5 (release engineering): build provenance + release manifest** —
  new PlatformIO pre-script `scripts/platformio/k1_build_provenance.py` stamps
  `K1_BUILD_GIT_HASH` / `K1_BUILD_EPOCH` / `K1_BUILD_ENV` into every translation
  unit (fail-soft: degrades to `unknown` when git is unavailable, never fails a
  build), registered under `[env:k1_hardware]` `extra_scripts` so all derived
  envs inherit it. A new serial `build` command prints the provenance (version +
  git hash + epoch + env) — a running unit can now name its own source, closing
  the device-build-registry gap where `FIRMWARE_VERSION` 40103 does not
  discriminate commits. Read-only `scripts/release/make_release.py` prints a
  release manifest and the exact `git tag -a` command for the Captain to run
  (it never tags or pushes — tag-cut is Captain-gated). Host gate
  `tests/test_build_provenance_static.py`. `cmd_version` output left
  byte-identical (host goldens unchanged).
- **Lane N6 (prepare-only): per-band AGC candidate `SB_AGC_PERBAND_V1`** —
  flag-gated, **DEFAULT OFF** fix for the "louder -> dimmer" broadband single-scalar
  AGC defect (`audio/k1_gdft_core.cpp`). Reuses the existing `agc_bands[]` /
  `freq_to_band_map[]` scaffold to run the proven AGC pipeline per perceptual band.
  Host harness `oracle_agc_perband.py` + RED->GREEN property gate
  `test_agc_perband_independence.py`; production byte-identical with the flag off
  (gdft golden reproduces). Decision package + device A/B protocol:
  [`docs/architecture/n6-agc-perband-prepare-package.md`](./docs/architecture/n6-agc-perband-prepare-package.md).
  Class C — prepares only; the perceptual default is unchanged (Captain decides).
- **Initial SpectraSynq K1 fork** — clean-slate firmware repository forked from
  the `SensoryBridge-main 9` working tree (2026-06-23). See
  [`docs/spectrasynq-fork-2026-06-23.md`](./docs/spectrasynq-fork-2026-06-23.md).
- Accurate SpectraSynq K1 `README.md` (replaces the inherited upstream
  ESP32-S2 Sensory Bridge README).
- GPL-3.0 upstream attribution to Connor Nishijima / Lixie Labs in `NOTICE`.
- Clean-slate `.gitignore` excluding scratch, agent state, and build artefacts
  by construction.

### Changed
- Firmware source directory and sketch renamed
  `SENSORY_BRIDGE_FIRMWARE/` → `SPECTRASYNQ_K1_FIRMWARE/` (and `.ino` to match);
  all build/test/script path references updated. **Behaviour-preserving**: host
  regression 559 passed / 1 skipped; `pio run -e k1_hardware` green.

### Removed
- The two Tab5-controller test files (`test_tab5_harness_negatives.py`,
  `test_sb_tab5_wireless_controller_static.py`) — they belong with the Tab5
  controller, which is a separate project (see fork record).
- Two companion sub-projects (`sb-tab5-wireless-controller/`,
  `Lightwave-Ledstrip/`) and all build/agent/scratch cruft are **not** carried
  into this firmware-scoped repo; they remain in the archive repo.

### Licence
- Remains **GPL-3.0** (derivative of Sensory Bridge). The `LICENSE` file is the
  source of truth; the prior `CLAUDE.md` "MIT" wording is superseded.

### Notes — carried-forward audit backlog (not yet addressed)
- GDFT int32-overflow fix promotion to production (device A/B required).
- I2S `portMAX_DELAY` Core-0 timeout/recovery.
- CI pipeline + commit-gate enforcement.
- Wireless identity (SSID `LightwaveOS-AP` → SpectraSynq, per-device token) —
  deferred to the wireless-enablement task (requires Tab5 coordination).
- Full backlog: [`docs/audit/2026-06-23-repo-audit.md`](./docs/audit/2026-06-23-repo-audit.md).
