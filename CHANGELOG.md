# Changelog

All notable changes to the SpectraSynq K1 Firmware are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/); this project
versions firmware via `FIRMWARE_VERSION` and tagged releases.

## [Unreleased]

### Added

- **PRISM authored ingress (option A):** 34-byte PRSM parser and magic-first byte scanner (`audio/k1_prsm.*`), source arbitration STANDALONE/AUTHORED/RECOVERY (`audio/k1_authored_source.*`, freshness **50 ms**), and `k1_audio_snapshot_publish()` as the single store write. `check_serial()` demuxes PRSM before immediate hotkeys (`P`/`R`/`S` collide with magic `PRSM`). Live microphone update is suppressed while authored is fresh; stale frames hand back to the live snapshot, not USB-bridge GPIO fallback. AUTHORED freezes Core-1 chromagram and forces drop-cut scale to 1. Host gate: `tests/test_authored_ingress_native.py`. No second renderer. No eFuse / erase_flash.

### Removed
- **BREAKING — `global.standby_dimming` struck from every operator surface**
  (2026-08-11, Captain order 2026-08-09). Removed from the BLE-MIDI/WebSocket
  control registry, `k1_control_apply()`, the serial pure-setter dispatcher, the
  typed command table, the immediate-hotkey list and `cmd_help()`. Core-0 now
  pins `silent_scale = 1.0f` unconditionally, `init_system()` force-clears a
  stale NVS `true`, and the factory default flips to `false`. The
  `CONFIG.STANDBY_DIMMING` field is retained as inert storage so persisted
  config layout is unchanged. `:standby_dimming=` now returns `bad_command`.
- **BREAKING — `primary.mirror` / `secondary.mirror` purged from BLE/Deck**
  (2026-08-11, Captain HARD order 2026-08-09). Mirroring is centre-origin
  geometry, not an operator preference. Serial `:mirror_enabled=` and
  `:secondary_mirror_enabled=` are retained as **USB bringup only**.
- **BREAKING — control registry 71 → 68.** CC assignments 65–70 reflow on
  channels 0 and 1. Registry md5 becomes
  `9b5db3fbb17438367adeaceb541db03b`. K1 and Tab5 compare identity digests at
  link time and reject on mismatch, so any controller built against the
  71-control map must be rebuilt and reflashed.

### Added
- **Tab5 Deck16 controller firmware in-repo** (`tab5_firmware/`, ESP32-P4). The
  repository now hosts two PlatformIO projects; they build independently but are
  protocol-coupled through `docs/protocol/`. Previously only 11 of ~190 Tab5
  files were tracked, so `tests/test_deck_state_v1.py` could not run from a
  clean clone (2 failed / 6 passed on `git archive HEAD`; now 16 passed).
- **Deck16 protocol specs** — `k1-deck-state-v1.md`, `k1-deck-identity-v1.md`,
  `deck16-layout-v1.json` (carrying `param_set = NOT_CAPTAIN_APPROVED`),
  `protocol-map-hashes.json`.
- **`[env:k1_bench_im69d_ble]`** — Deck16 radio baseline on the active IM69D
  bench base. NON-SHIPPABLE, bench `B489A500` only.
- **Session canon + discipline skills** (2026-08-07 / 2026-08-09) and the UI
  pre-code optical gate wired into `AGENT_OS.md` §7a (fail-closed).
- **Housekeeping doctrine** + git doctrine SCOPE/BIRTH/SWEEP rules.

### Fixed
- **Boot-loop on units with a persisted secondary-strip show.**
  `k1_show_state_load()` sets `ENABLE_SECONDARY_LEDS` during `init_fs()`, before
  `init_secondary_leds()` allocates the buffers, so `show_leds()` dereferenced
  null. The existing `try/catch` was decorative — C++ exceptions do not catch a
  null dereference on ESP32; the panic handler reboots. Replaced with explicit
  pointer guards in `show_leds()` and `scale_to_secondary_strip()`. Observed as
  `StoreProhibited` in `init_leds`/`scale_to_secondary_strip` on `B489A500`,
  2026-08-11 (`PHASE1_GATE=FAIL`). **Host-verified only — device proof pending
  the standing flash freeze.**
- **Upload guard failed OPEN on unmapped `k1_*` environments** — a typo or a new
  env bypassed the chip-ID check entirely. Now fails closed. Also accepts
  `wchusbserial*` bridges and matches against all authorised targets for an env.
  Bench Unit 2 (`0C54FC00`) registered; `k1_custom` removed from `B489A500`.
- **Commit gate did not gate `tab5_firmware/`** — it classified as the `docs`
  tier (no test, no build). Now pytest tier. Verified adversarially: the gate
  blocks a broken build and a failing test, not just passes a good tree.
- **14-bit CC decoder latched an MSB indefinitely** — a lost LSB left a stale
  high byte that combined with the next unrelated LSB into a plausible-but-wrong
  value. Bounded by a 50 ms pairing window with a malformed counter.
- **AP telemetry `mode=` was ambiguous** — the loud-guard matrix index was read
  as the lightshow mode and produced a false "silence fixed" PASS while mode 32
  rendered a dead plate. Now `lg_mode=` plus an explicit `lightshow=`.
- **Quiet-mic units rendered a dead plate on modes 18 and 32** — an SPH-calibrated
  `vu_level >= 0.05` presence floor and chromagram-only colour returning
  near-black. Presence now keys on `max(peak, vu)`; a peak-seeded colour fallback
  engages when the sanctioned colour authority returns black. Visual class:
  host-green, **on-device eyes-on outstanding**.

### Changed
- **`[env:k1_custom]` retargeted** from 224-LED single-channel to dual-206
  (both channels), `MAX_CURRENT_MA` boot-forced to 2500, PDM CLK/DIN 39/38.
  NON-SHIPPABLE, Bench Unit 2 only. `NATIVE_RESOLUTION` stays 160 — physical
  counts change, the render canvas does not. **PDM pin map is provisional**
  pending `CAPTAIN_PIN_AUTH=GO`.
- **`[env:k1_ble_remoted_probe]`** now extends `k1_hardware` rather than the
  harness (harness flags broke the compile).
- **IM73D quiet-mic tempo/silence retune** — lock 0.60→0.28, hysteresis
  0.42→0.18, novelty ×4.0, silence RMS 0.04/0.08→0.001/0.003. All behind
  `K1_MIC_IM73D_PDM_V1`, which production does not define.
  **PROVISIONAL:** measured on Bench Unit 2 under a mic identity the Captain
  correction of 2026-08-10 has since voided. Not evidence about the IM73D122.
- **`.gitignore`** now excludes `tab5_firmware/vendor/` (5.6 GB pinned
  toolchain), `.worktrees/`, and trial-licensed type specimens — staging went
  from 58,130 untracked files / 9.5 GB to 243 / 2.6 MB.
- **Captain correction 2026-08-10:** Bench Unit 2 carries **dual IM69D130**;
  IM73D122 is **deprecated** and the 2026-07-03 production-mic ratification is
  superseded. Prior Unit 2 receipts are void as evidence. Superseded claims are
  marked in place, not deleted.

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
