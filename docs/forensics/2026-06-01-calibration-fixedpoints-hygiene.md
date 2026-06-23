---
abstract: "Calibration invalid-profile product posture and FixedPoints licence/NOTICE hygiene review. No calibration, hardware, numeric, AP, or GDFT mutation was performed."
status: "static-docs-verified"
evidence-tier: "static-source-and-package-metadata"
created: "2026-06-01"
---

# Calibration And FixedPoints Hygiene

## Scope

- [FACT] Hardware, serial, upload, erase, and calibration execution were out of
  scope and were not run.
- [FACT] This pass inspected calibration profile/status source, calibration
  static tests, and vendored FixedPoints package metadata.
- [FACT] This pass changes documentation/NOTICE surfaces only. No calibration
  source, numeric code, AP code, GDFT code, build config, tests, or vendored
  FixedPoints source files were changed.

## Calibration Source Truth

- [FACT] Calibration profile persistence is version-independent through
  `CAL_PROFILE_FILE "/cal_profile.bin"` in `SPECTRASYNQ_K1_FIRMWARE/bridge_fs.h`.
- [FACT] A valid config-derived calibration seeds or refreshes the profile; an
  invalid config falls back to `/cal_profile.bin`.
- [FACT] Valid persisted profiles restore `CONFIG.DC_OFFSET`,
  `CONFIG.SWEET_SPOT_MIN_LEVEL`, optional `CONFIG.SWEET_SPOT_MAX_LEVEL`, and
  `noise_samples[]`, then mark calibration loaded.
- [FACT] Calibration validity currently requires `noise_complete`, non-zero and
  bounded DC offset, and `CONFIG.SWEET_SPOT_MIN_LEVEL` in `(0, 3000]`.
- [FACT] Serial config dump, diagnostic status, AP stream/capture, and VPAB
  capture expose calibration source/validity fields.
- [FACT] VPAB capture refuses to arm when `calibration_profile_valid()` is false.
- [FACT] `python3 -m pytest tests/test_calibration_profile_static.py` passed in
  the sandbox worker lane.

## Invalid-Profile Product Posture

- [INFERENCE] Product posture should be fail-visible, not self-healing by silent
  calibration. If profile validity is false after config/profile load, the
  device should report `CAL_SOURCE=default_invalid` and `CAL_VALID=0` rather
  than hiding the state.
- [INFERENCE] The current source already makes invalid calibration visible on
  the relevant debug/harness surfaces and blocks VPAB capture before collecting
  misleading evidence.
- [INFERENCE] The product must not auto-run `start_noise_cal`, including on
  missing or invalid profile, because calibration requires a confirmed silence
  window.
- [INFERENCE] Any user-facing invalid-calibration UX beyond the current evidence
  surfaces is a separate firmware-gated task.

## FixedPoints Package Hygiene

- [FACT] `platformio.ini` vendors FixedPoints through
  `file://libraries/FixedPoints`.
- [FACT] `libraries/FixedPoints/library.json` identifies FixedPoints version
  `1.1.2`, author `Pharap`, repository
  `https://github.com/Pharap/FixedPointsArduino.git`, and licence `Apache-2.0`.
- [FACT] `libraries/FixedPoints/LICENCE` contains Apache License 2.0.
- [FACT] `libraries/FixedPoints/README.md` says to package copies of `LICENCE`
  and `NOTICE`.
- [FACT] No vendored FixedPoints `NOTICE` file exists.
- [INFERENCE] Because the vendored package has no upstream NOTICE file to copy,
  the lowest-risk package-only hygiene patch is to add FixedPoints attribution
  to this repo's product NOTICE using local package metadata as provenance.

## Changelog

| Date | Change |
|---|---|
| 2026-06-01 | Added static calibration posture and FixedPoints licence/NOTICE hygiene findings. |
