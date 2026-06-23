# Changelog

All notable changes to the SpectraSynq K1 Firmware are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/); this project
versions firmware via `FIRMWARE_VERSION` and tagged releases.

## [Unreleased]

### Added
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
