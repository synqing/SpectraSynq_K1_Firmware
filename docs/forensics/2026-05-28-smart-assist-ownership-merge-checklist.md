---
abstract: "Static merge checklist for Smart Visual Engine manual/show ownership before runtime proof."
---

# Smart Assist Ownership Merge Checklist

**Date:** 2026-05-28
**Evidence tier:** static source review only
**Scope:** Smart Visual Engine manual/show ownership, merge gates, and runtime-proof inputs.

This checklist is a sidecar artefact for the in-flight Smart Visual Engine work. It does not approve visual quality, runtime correctness, or any default-on behaviour.

## Source Truth Snapshot

- `[FACT]` Manual ownership has an explicit reason enum and stamp/read API in `SPECTRASYNQ_K1_FIRMWARE/sb_smart_director.h:27-42`.
- `[FACT]` `sb_smart_director_mark_manual_control()` records the latest manual-control time and reason under `sb_director_manual_mux` in `SPECTRASYNQ_K1_FIRMWARE/sb_smart_director.cpp:198-205`.
- `[FACT]` `sb_smart_director_manual_owner_active()` treats queued transitions, active mode destinations, recent manual stamps, and recent encoder activity as manual ownership in `SPECTRASYNQ_K1_FIRMWARE/sb_smart_director.cpp:208-228`.
- `[FACT]` `sb_mode_selection_resolve()` returns the fallback mode and marks `SB_MODE_REASON_MANUAL_OWNERSHIP` when manual ownership is active or the fallback mode changed in `SPECTRASYNQ_K1_FIRMWARE/sb_mode_selection.cpp:56-83`.
- `[FACT]` The primary render path resolves a temporary `smart_primary_mode` from `CONFIG.LIGHTSHOW_MODE` and renders that mode without writing it back to `CONFIG` in `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:580-607`.
- `[FACT]` Serial mode hotkeys mutate `CONFIG.LIGHTSHOW_MODE` or `SECONDARY_LIGHTSHOW_MODE` in `SPECTRASYNQ_K1_FIRMWARE/serial_menu.h:782-790`; serial palette controls mutate primary/secondary palette state in `SPECTRASYNQ_K1_FIRMWARE/serial_menu.h:814-842`.
- `[FACT]` Serial hotkeys and typed commands can stamp Smart Assist manual ownership before dispatch in `SPECTRASYNQ_K1_FIRMWARE/serial_menu.h:1105-1108` and `SPECTRASYNQ_K1_FIRMWARE/serial_menu.h:1819-1821`.
- `[FACT]` Encoder paths can mutate auto-colour and lightshow mode in `SPECTRASYNQ_K1_FIRMWARE/encoders.h:439-459` and `SPECTRASYNQ_K1_FIRMWARE/encoders.h:501-519`; any detected encoder activity updates `g_last_encoder_activity_time` in `SPECTRASYNQ_K1_FIRMWARE/encoders.h:769-771`.

## Merge Gates

- Every manual visual mutation surface must be classified as one of: mode ownership, palette/colour ownership, scalar ownership, effect-local state ownership, or non-visual command.
- Every mode-changing surface must either stamp `sb_smart_director_mark_manual_control()` or flow through a mechanism already visible to `sb_smart_director_manual_owner_active()`.
- Encoder coverage must be reviewed as a single source-truth rule: any encoder mutation that sets `activity_detected = true` is currently covered by `g_last_encoder_activity_time`; a direct encoder mutation that bypasses `activity_detected` is not covered.
- Serial command coverage must be checked against the actual allowlist in `serial_command_marks_manual_visual_control()` before merge. Missing manual visual setters are defects; non-visual commands must stay out of the allowlist.
- Smart Assist must remain an overlay unless Captain approves a policy change. It may resolve a render-time mode, but it must not persist `CONFIG.LIGHTSHOW_MODE`, `SECONDARY_LIGHTSHOW_MODE`, palette index, palette mode, or auto-colour state as a side effect.
- Palette, auto-colour, and preset ownership need explicit product policy before Smart Assist owns or overrides them. Until then, manual colour/show controls win.
- Any switch policy that changes dwell, cooldown, switch-window, fallback drift, or manual quiet-window semantics needs Captain approval before implementation.

## Runtime Proof Inputs

The future Captain capture should include at minimum:

- `SMART_*` status lines showing assist state, applied mode, requested mode, switch reason, switch window, confidence, and manual ownership outcome.
- `EDGE_*` status lines showing enabled state, mode, and strength.
- `VPAB_RECORDS` lines with zero dropped rows and zero overflow for strict parser proof.
- `VPABB` rows grouped by named legs such as `baseline_features_off`, `assist_enabled`, and `edge_complementary_strength_1`.
- Video or operator observation for visual quality. The parser can summarise bytes and materiality; it cannot prove that the result looks good.

## No-Touch Boundaries For Sidecar Work

- Do not edit `SPECTRASYNQ_K1_FIRMWARE/sb_mode_selection.*`, `SPECTRASYNQ_K1_FIRMWARE/sb_smart_director.*`, `SPECTRASYNQ_K1_FIRMWARE/sb_onset_beat.*`, `SPECTRASYNQ_K1_FIRMWARE/sb_visual_hooks.*`, or `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino` while the current Smart Visual Engine agent owns those files.
- Serial capture and firmware upload are permitted when the active validation lane requires them, but verify the exact hardware target by port plus stable device identity before opening serial, flashing, erasing, or issuing device-write commands. Calibration commands that assume silence still require Captain's explicit silence-window confirmation.
- Do not claim runtime proof from compile/static evidence.
- Do not promote trace-dev instrumentation into production.

## Changelog

| Date | Change |
|---|---|
| 2026-05-28 | Initial static ownership checklist for Smart Visual Engine merge review. |
