# MAS-DESIGN-01 SSA Design Review

Date: 2026-07-10
Repo: `/Users/spectrasynq/SpectraSynq_K1_Firmware`
Live branch/HEAD observed read-only: `lane/dual-sync-phase0` / `cc97081`

## Verdict

VERIFIED for a minimal repo-consistent telemetry-only scaffold design.

NOT VERIFIED for any applied controller, product tuning benefit, production enablement, or persisted sensitivity change. Those are explicitly out of scope.

## Claim

The minimal safe design is a default-off, telemetry-only `audio/k1_mic_auto_sense.{h,cpp}` shadow observer that reports raw and conditioned health beside the existing AP/loud-guard telemetry while forcing applied mic auto scale to `1.0f`, leaving `CONFIG.SENSITIVITY`, calibration, DSR mode, loud guard, and GDFT AGC untouched.

## Governing Evidence

- The prior synthesis says the feature exists as docs-only design, not current firmware, and that the design requires telemetry first, default-off behaviour, no automatic `start_noise_cal`, no persistence writes, and Captain gates before production enablement: `artifacts/self_calibrating_sensitivity_forensics_2026-07-10/orchestrator_synthesis.md:8-13`.
- The same synthesis names the next authorised slice as telemetry only, applied scale `1.0f`, no calibration, no `CONFIG.SENSITIVITY`/NVS writes, and proof gates before any applied controller: `artifacts/self_calibrating_sensitivity_forensics_2026-07-10/orchestrator_synthesis.md:69-77`.
- The design doc non-negotiables ban automatic calibration, hidden adaptive scale during purity work, v1 persistence, hot-loop cost, and require default-off `K1_MIC_AUTO_SENSE_V1`: `docs/hardware/k1-auto-sensing-mic-sensitivity-scaling-design-2026-07-06.md:18-34`.
- The design doc requires raw/pre-conditioning telemetry plus `auto_scale`, `auto_state`, `auto_reason`, and window age before control: `docs/hardware/k1-auto-sensing-mic-sensitivity-scaling-design-2026-07-06.md:127-150`.
- The design doc's Phase 1 says telemetry only and "Do not implement scaling yet": `docs/hardware/k1-auto-sensing-mic-sensitivity-scaling-design-2026-07-06.md:318-331`.
- The design doc's future firmware shape already names `audio/k1_mic_auto_sense.h` and optional `.cpp`, with a tiny getter near effective sensitivity, default flag off, O(1) updates, no hot-path serial, and no config save: `docs/hardware/k1-auto-sensing-mic-sensitivity-scaling-design-2026-07-06.md:398-418`.
- The shadow proof phase says to compute state/reason/recommended scale while leaving applied scale at `1.0f`, and to accept only if raw telemetry is unchanged and no persistence writes occur: `docs/hardware/k1-auto-sensing-mic-sensitivity-scaling-design-2026-07-06.md:420-432`.
- The purity audit separates raw mic evidence from conditioned production signals and states `[AP]`, `[APCAP]`, `agc_debug`, and semantic state are not raw microphone measurements: `docs/hardware/im73d-audio-pipeline-purity-audit-2026-07-06.md:21-31`.
- Current raw continuous telemetry exists as `raw_i16_abs_peak`, `raw_i16_rms`, and `raw_i16_near_pct`: `docs/hardware/im73d-audio-pipeline-purity-audit-2026-07-06.md:33-39`.
- Future measurement comparability must record sensitivity, response gain, trim, calibration source/validity, SSL, and DC offset: `docs/hardware/im73d-audio-pipeline-purity-audit-2026-07-06.md:120-123`.
- Tier-0 raw acquisition purity requires MAC/chip identity, `:build`/`:dump`, raw evidence, and no I2S fault; continuous `raw_i16_*` closes the read-only field gap for DSR/headroom comparisons: `docs/hardware/im73d-audio-pipeline-purity-audit-2026-07-06.md:125-144`.
- Restored bench evidence shows raw telemetry is already the decision basis and volume 75 is a stress/fail condition, not acceptance evidence: `docs/hardware/im73d-restored-bench-validation-2026-07-07.md:55-79`.
- `:stream_agc` evidence at accepted levels stayed below the starvation ceiling, so the scaffold should observe AGC state without becoming another AGC loop: `docs/hardware/im73d-restored-bench-validation-2026-07-07.md:81-91`.

## Current Source Anchors

- Build shape: `platformio.ini` already includes `+<audio/k1_*.cpp>`, so a future `audio/k1_mic_auto_sense.cpp` follows the local build pattern without changing `build_src_filter`: `platformio.ini:40-44`.
- IM73D-specific envs define `K1_MIC_IM73D_PDM_V1`; `k1_hardware` remains SPH/default and flag-off: `platformio.ini:207-220`, `platformio.ini:232-244`.
- Fixed IM73D pre-sensitivity gain is hardware characterisation, not a runtime controller; raw near-rail threshold is explicitly a measurement-purity surface: `SPECTRASYNQ_K1_FIRMWARE/system/constants.h:62-75`.
- Loud guard effective sensitivity is currently `CONFIG.SENSITIVITY * k1_loud_input_trim`: `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:115-117`.
- Loud guard owns fast protection by tracking clip, near-rail, peak pin, and spectral saturation, then adjusting input/GDFT trim: `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:141-193`.
- Raw IM73D telemetry is computed before fixed mic gain, `CONFIG.SENSITIVITY`, clamp, DC removal, response gain, GDFT, and AGC: `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:359-377`.
- Shared front-end gain applies IM73D fixed gain, then `k1_effective_sensitivity`, then clamp/DC correction: `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:405-443`.
- AP stream already emits conditioned fields, IM73D raw fields, and loud-guard fields at 1 Hz: `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:797-825`.
- Raw IM73D globals already live as static/global firmware state, not heap: `SPECTRASYNQ_K1_FIRMWARE/system/globals.h:143-152`.
- Loud guard state is global runtime state with a reset path when disabled: `SPECTRASYNQ_K1_FIRMWARE/system/globals.h:122-134`, `SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h:360-390`.
- Persisted sensitivity setter writes `CONFIG.SENSITIVITY` and calls `save_config_delayed()`: `SPECTRASYNQ_K1_FIRMWARE/serial/serial_cmd_handlers.cpp:259-281`.
- Runtime-only `response_gain` writes RAM state and emits status without persistence; this is the safer local pattern for auto-sense telemetry state: `SPECTRASYNQ_K1_FIRMWARE/serial/serial_cmd_handlers.cpp:836-849`.
- Typed `start_noise_cal` is guidance-only and the command table marks it arm-required/typed-only: `SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h:2139-2145`, `SPECTRASYNQ_K1_FIRMWARE/serial/serial_cmd_table.def:45-50`.
- Serial safety gates forbid dangerous hotkeys for destructive/calibration rows: `SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h:2429-2466`.
- WebSocket controls expose persisted `global.sensitivity` but no mic auto-sense control; calibration is two-step and `start_noise_cal` is rejected: `docs/protocol/k1-ws-controls-registry.yaml:1-84`.
- Static tests already lock the raw-before-conditioning order and AP schema fields: `tests/test_im73d_audio_purity_static.py:20-54`, `tests/test_audio_telemetry_schema_static.py:15-63`.

## TRIZ Separation

Contradiction: K1 needs future adaptation to quiet and loud rooms, but the same mechanism must not corrupt raw mic measurement, fight loud guard, or mutate persisted sensitivity.

Resolution:

- Separation by layer: raw measurement remains before IM73D gain/sensitivity; auto-sense telemetry is a read-only observer; any future runtime scale is a separate RAM-only multiplier; loud guard remains the fast protection layer; GDFT AGC remains spectral normalisation.
- Separation in time: Phase 1 collects telemetry only; Phase 5 may compute shadow recommendations with applied scale fixed at `1.0f`; applied control is a later lane only after host/device/Captain gates.
- Separation by condition: purity, DSR, calibration, raw dump, BLE/demo, invalid calibration, stale I2S, clip/near/input-trim, and loud-guard activity force bypass/observe-only state.
- Separation by level: `CONFIG.SENSITIVITY` stays the persisted user/product baseline; auto-sense state is volatile runtime telemetry and must not call `save_config`, `save_config_delayed`, or calibration persistence.

## Proposed File And Module Shape

Telemetry-only Phase 1:

- `SPECTRASYNQ_K1_FIRMWARE/audio/k1_mic_auto_sense.h`
  - Declares a small POD telemetry struct, enum state/reason values, `k1_mic_auto_sense_reset()`, `k1_mic_auto_sense_update_frame(...)`, `k1_mic_auto_sense_read()`, and `k1_mic_auto_sense_applied_scale()`.
  - Provides flag-off inline stubs returning disabled state and `1.0f`.
- `SPECTRASYNQ_K1_FIRMWARE/audio/k1_mic_auto_sense.cpp`
  - Compiled only when `K1_MIC_AUTO_SENSE_V1` is defined.
  - Uses file-static state only. No heap, no `String`, no serial output, no LittleFS/NVS, no blocking API.
  - O(1) per AP frame. It consumes existing raw globals and closed-frame conditioned/loud-guard values.
- Touchpoint, future implementation only:
  - Include `k1_mic_auto_sense.h` near `i2s_audio.h` effective sensitivity.
  - In telemetry-only Phase 1, do not multiply the acquisition path by auto scale. `k1_mic_auto_sense_applied_scale()` must return `1.0f`.
  - If the AP stream is extended, append fields under `#ifdef K1_MIC_AUTO_SENSE_V1` after existing raw/loud fields, preserving existing field names and parser compatibility.
- Optional later status command:
  - `:mic_auto_sense_status` can be added as `SC_SAFE` / read-only / colon-prefixed if AP line length or parser drift argues for a separate command.
  - No setter/reset command in Phase 1. A reset command belongs to a later shadow/controller lane and must be explicit, typed, and non-persistent.

Do not add REST or WebSocket control in Phase 1. The REST contract is empty/not implemented for this control slice, and the WS registry currently exposes persisted `global.sensitivity`, not mic auto-sense telemetry.

## Proposed State Struct

This is shape, not implementation:

```cpp
enum K1MicAutoSenseState : uint8_t {
  K1_MIC_AUTO_DISABLED = 0,
  K1_MIC_AUTO_TELEMETRY = 1,
  K1_MIC_AUTO_BYPASSED = 2,
  K1_MIC_AUTO_FAULT = 3,
};

enum K1MicAutoSenseReason : uint8_t {
  K1_MIC_AUTO_REASON_FLAG_OFF = 0,
  K1_MIC_AUTO_REASON_OK = 1,
  K1_MIC_AUTO_REASON_RAW_UNAVAILABLE = 2,
  K1_MIC_AUTO_REASON_CAL_INVALID = 3,
  K1_MIC_AUTO_REASON_MEASUREMENT_BYPASS = 4,
  K1_MIC_AUTO_REASON_HEADROOM_GUARD = 5,
  K1_MIC_AUTO_REASON_STALE_I2S = 6,
  K1_MIC_AUTO_REASON_NONFINITE = 7,
};

struct K1MicAutoSenseTelemetry {
  uint32_t frame_count;
  uint32_t updated_ms;
  float window_age_sec;

  uint16_t raw_i16_abs_peak;
  float raw_i16_rms;
  float raw_i16_near_pct;

  float conditioned_peak;
  float peak_scaled;
  float input_trim;
  float gdft_trim;
  float clip_pct;
  float near_pct;
  float peak_pin;
  float spec_sat;

  float agc_gain[NUM_AGC_BANDS];
  float agc_active_floor[NUM_AGC_BANDS];

  bool cal_valid;
  uint8_t cal_source;
  K1MicAutoSenseState state;
  K1MicAutoSenseReason reason;

  float applied_scale;       // Always 1.0f in telemetry-only Phase 1.
  float shadow_scale;        // Always 1.0f until a separate shadow-recommendation lane.
};
```

Rationale:

- Includes raw fields already present in source and tests.
- Includes conditioned/loud-guard fields needed to detect when the future controller would fight existing protection.
- Includes AGC gain/floor context without owning AGC.
- Includes `applied_scale` and `shadow_scale` only to make the no-apply contract visible. Both stay `1.0f` in this scaffold.
- Does not include thresholds, target bands, persisted learned profiles, or controller step sizes. Those belong after measurement characterisation.

## Telemetry Fields

Minimum AP/status fields for Phase 1:

- `mas_state`
- `mas_reason`
- `mas_window_age_sec`
- `mas_applied_scale` - always `1.000`
- `mas_shadow_scale` - always `1.000`
- `raw_i16_abs_peak` - existing source field
- `raw_i16_rms` - existing source field
- `raw_i16_near_pct` - existing source field
- `conditioned_peak` - use current `max_waveform_val_raw` semantics but label it conditioned if newly reported
- `peak_scaled`
- `input_trim`
- `gdft_trim`
- `clip_pct`
- `near_pct`
- `peak_pin`
- `spec_sat`
- `agc_gain[0..3]`
- `agc_active_floor[0..3]`
- `cal_valid`
- `cal_source`

If AP line length becomes a parser risk, keep `[AP]` unchanged and add one read-only `MAS` line emitted at the same 1 Hz cadence. Do not emit from the hot path directly.

## Update Cadence

- Raw acquisition counters already update once per audio chunk in `acquire_sample_chunk()` before conditioning. Do not add more per-sample work beyond the existing O(n) raw pass.
- Telemetry observer update should run once per AP frame after `process_GDFT()` and `k1_loud_guard_update(t_now)` so it sees closed-frame loud-guard/AGC state. The current order is `process_GDFT()` then `k1_loud_guard_update(t_now)` then streaming/debug hooks: `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:876-909`.
- Emission should be 1 Hz through existing AP/status surfaces, matching the current `AP_STREAM_ENABLED` cadence: `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:797-828`.
- No serial print, sorting, percentile calculation, allocation, file I/O, or controller decision inside sample acquisition.
- A later measurement phase may add fixed-size rolling windows, but the telemetry-only scaffold should initialise `window_age_sec` and simple counters only.

## Default-Off Flag Strategy

- Do not add `-DK1_MIC_AUTO_SENSE_V1` to `k1_hardware`, `k1_bench_reference`, `k1_bench_im73d`, or `k1_prod_im73d` in this design task.
- With `K1_MIC_AUTO_SENSE_V1` absent:
  - no new `.cpp` is linked;
  - inline stubs return disabled state and `1.0f`;
  - AP schema and production behaviour stay unchanged.
- If a later implementation needs proof, add a separate non-shippable probe/shadow env after design approval, for example `k1_bench_im73d_mic_auto_shadow`, extending radio-free `k1_bench_im73d`, with `-DK1_MIC_AUTO_SENSE_V1=1` and no apply flag.
- Do not define an apply flag in Phase 1. If a future lane needs one, use a separate `K1_MIC_AUTO_SENSE_APPLY_V1` that defaults absent and is impossible to enable accidentally through the telemetry flag.

## Bypass Conditions

The telemetry state may still report measurements, but any future shadow recommendation or applied scale must be bypassed with an explicit reason when:

- `K1_MIC_AUTO_SENSE_V1` is absent.
- `K1_MIC_IM73D_PDM_V1` is absent and no equivalent SPH raw telemetry has been added.
- `noise_complete == false`, `noise_transition_queued == true`, `calibration_valid == false`, or calibration source/state is unknown.
- `raw_dump_request != 0`, `:dump_raw` is being interpreted, or a purity/DSR measurement harness is active.
- Running BLE/demo/radio builds where mic SNR/tuning measurements are explicitly forbidden.
- I2S read status/bytes-read telemetry is stale or faulted.
- Any raw sample is non-finite/impossible, or raw field age exceeds the expected AP frame cadence.
- `clip_pct > 0`, `near_pct > 0`, `input_trim < 0.999f`, `gdft_trim < 0.999f`, high `peak_pin`, or high `spec_sat` indicates loud guard/protection pressure.
- `stream_agc` or AP evidence shows AGC gains/floors in a starvation/fault state.

For telemetry-only Phase 1, bypass changes `state`/`reason` only. It must not change gain.

## Explicit Non-Goals

- No applied controller.
- No hidden multiplier in the audio acquisition path.
- No writes to `CONFIG.SENSITIVITY`.
- No `save_config`, `save_config_delayed`, LittleFS, NVS, profile, or calibration persistence.
- No automatic `start_noise_cal`, `N`, `Y`, `clear_noise_cal`, or calibration confirm.
- No runtime tuning of `K1_MIC_IM73D_INPUT_GAIN`.
- No DSR8/DSR16 default change.
- No new AGC loop, no change to loud guard thresholds, no change to GDFT/per-band AGC.
- No WebSocket/REST control surface.
- No BLE/demo measurement lane.
- No new device run, build, calibration, playback, flash, or serial monitor in this SSA task.
- No target thresholds or acceptance bands guessed from intuition.

## Main Method Risk

The main way this design could be wrong is branch/lane drift: the current checkout is `lane/dual-sync-phase0`, while several IM73D docs cite `lane/im73d-pdm-eval`. I used current source anchors for module and line claims, and older docs only as design/history authority. No build or device proof was run because the SSA brief was read-only design.

Secondary risk: AP emission currently happens inside `acquire_sample_chunk()` before the later `.ino` `k1_loud_guard_update(t_now)` for the same frame. A future implementation must either report the previous closed frame or move only the auto-sense status emission to a post-update read-only surface. It must not move raw sampling or GDFT/loud-guard ordering casually.

## Required Re-Run Commands

Run these from repo root to verify the source and architecture claims:

```bash
git rev-parse --abbrev-ref HEAD
git rev-parse --short HEAD
git status --short
git log --oneline -8

nl -ba artifacts/self_calibrating_sensitivity_forensics_2026-07-10/orchestrator_synthesis.md | sed -n '6,34p;69,89p'
nl -ba docs/hardware/k1-auto-sensing-mic-sensitivity-scaling-design-2026-07-06.md | sed -n '18,34p;127,150p;318,331p;398,432p;536,546p'
nl -ba docs/hardware/im73d-audio-pipeline-purity-audit-2026-07-06.md | sed -n '21,50p;103,144p;192,240p'
nl -ba docs/hardware/im73d-restored-bench-validation-2026-07-07.md | sed -n '55,91p'

nl -ba platformio.ini | sed -n '40,44p;207,244p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/system/constants.h | sed -n '62,97p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/system/globals.h | sed -n '122,152p;452,468p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h | sed -n '115,193p;359,443p;797,825p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino | sed -n '876,909p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/audio/k1_gdft_core.cpp | sed -n '195,267p;304,520p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/serial/serial_cmd_handlers.cpp | sed -n '259,281p;836,849p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h | sed -n '2139,2145p;2429,2466p;2609,2662p;2795,2858p;3480,3615p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/serial/serial_cmd_table.def | sed -n '45,50p'
nl -ba docs/protocol/k1-ws-controls-registry.yaml | sed -n '1,84p'
nl -ba tests/test_im73d_audio_purity_static.py | sed -n '20,80p'
nl -ba tests/test_audio_telemetry_schema_static.py | sed -n '15,104p'

command rg -n "K1_MIC_AUTO_SENSE|k1_mic_auto|auto_scale|auto_state|auto_reason|mic_auto_sense" SPECTRASYNQ_K1_FIRMWARE tests scripts platformio.ini || true
command rg -n "raw_i16_abs_peak|raw_i16_rms|raw_i16_near_pct|k1_loud_guard_effective_sensitivity|stream_agc_data|global.sensitivity|start_noise_cal" SPECTRASYNQ_K1_FIRMWARE tests docs/protocol platformio.ini
```

## Stop Point

This creates decision value for the orchestrator: implement telemetry first or do not proceed. Any implementation that adds a gain multiplier, persists sensitivity, changes calibration behaviour, changes DSR mode, or exposes user controls before telemetry/shadow proof is outside this verified design.
