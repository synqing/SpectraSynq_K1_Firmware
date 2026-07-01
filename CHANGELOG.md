# Changelog

All notable changes to the SpectraSynq K1 Firmware are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/); this project
versions firmware via `FIRMWARE_VERSION` and tagged releases.

## [Unreleased]

### Added
- **Lane N7: OTA image signature verification (`SB_ENABLE_OTA`, DEFAULT OFF)** —
  the flag-gated OTA receiver (`system/k1_ota.cpp`) now REJECTS any image whose
  detached RSA-3072 / PKCS#1 v1.5 SHA-256 signature does not verify against the
  embedded operator PUBLIC key (`system/k1_ota_signing_public_key.h`, provenance
  `certs/k1_ota_signing_PUBLIC.pem`). Verification is application-level via mbedTLS
  (`mbedtls_pk_verify`) because the precompiled arduino-esp32 (ESP-IDF 5.4.1) ships
  `libbootloader_support.a` built with `CONFIG_SECURE_SIGNED_ON_UPDATE` compiled
  out, so the IDF-native `CONFIG_SECURE_SIGNED_APPS_NO_SECURE_BOOT` path is inert
  without an off-limits full-IDF rebuild. Verify-ONLY: needs only the PUBLIC key at
  build time (no build-time signing, no private key), and NO Secure Boot eFuse. The
  boot partition is switched only after the signature verifies; `k1_ota_end()` fails
  closed on missing/mis-signed/tampered images. Adds base64 serial ingress
  (`ota_datab64` / `ota_sigb64`) for the device-proof. Production byte-identical with
  the flag off (flag-OFF `k1_hardware` proven byte-for-byte unchanged).
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
