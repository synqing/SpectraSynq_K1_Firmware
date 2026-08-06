# Changelog

All notable changes to the SpectraSynq K1 Firmware are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/); this project
versions firmware via `FIRMWARE_VERSION` and tagged releases.

## [Unreleased]

### Added
- **docs (forensics):** WB-3 STM investigation pack — authority map, hypotheses/thresholds, reference attestation (INDETERMINATE), Core-0 bench spec + INDETERMINATE bundle, FFT512 feasibility sheet, evidence matrix, Captain decision pending, conditional convergence, red-team closure, STM re-derivation design; VP measurement spec under `docs/forensics/stm-vp/`. Refs: BACKLOG.md § WB-3 (Lightwave-Ledstrip), plan `correct-wb3-state`.
- **tools (forensics):** Fail-closed STM VP manifest gate `scripts/regression-harness/stm_vp_compare.py` with `tests/test_stm_vp_compare.py` (7 host controls). Refs: BACKLOG.md § WB-3.
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
