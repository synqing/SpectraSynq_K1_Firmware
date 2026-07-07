# K1 Auto-Sensing Mic Sensitivity Scaling - Research And Execution Plan

Date: 2026-07-06 14:58 AWST
Branch verified before drafting: `lane/im73d-pdm-eval`
HEAD verified before drafting: `cb5e71f test(im73d): lock audio pipeline purity`

## Purpose

Captain's feature idea: add an auto-sensing, self-adjusting mic sensitivity
supervisor that periodically observes the room/audio condition and adjusts the
effective mic/front-end scale so the visual pipeline receives a usable,
unclipped Audio Pipeline (AP) signal across quiet rooms, normal playback, and
loud-room conditions.

This document is a research/design/handoff artefact for another Codex agent. It
does not implement firmware, flash devices, play audio, or run calibration.

## Non-Negotiable Boundaries

1. Do not auto-fire `start_noise_cal`, `N`, or `Y`. Existing noise calibration
   remains Captain-authorised silence work only.
2. Do not treat `[AP]`, `[APCAP]`, `agc_debug`, or semantic state as raw
   microphone evidence. The purity audit established they are conditioned
   production-behaviour surfaces, not raw mic proof.
3. Keep raw/purity measurement modes able to disable or bypass auto-sensing.
   IM73D DSR, SNR, and mic-ratio work must not be coloured by a hidden
   adaptive scale.
4. Do not persist auto-scale changes to NVS in the first implementation. A slow
   runtime multiplier is safe; repeated writes to `CONFIG.SENSITIVITY` are not.
5. Keep Core 0 real-time safe: no heap, no `String`, no blocking I/O, no serial
   prints, and no expensive sorting in the audio hot loop.
6. Gate all firmware behaviour behind a default-off flag, proposed
   `K1_MIC_AUTO_SENSE_V1`, until host tests, bench proof, and Captain eyes-on
   acceptance are complete.

## Current Source Truth

The relevant gain and conditioning surfaces are already layered:

| Layer | Source | Current behaviour | Design implication |
| --- | --- | --- | --- |
| Factory base sensitivity | `SPECTRASYNQ_K1_FIRMWARE/system/globals_config.cpp:48-66` | `CONFIG.SENSITIVITY` defaults to `2.4`. | Treat this as the user's/base product intent, not the auto controller's working variable. |
| IM73D pre-sensitivity gain | `SPECTRASYNQ_K1_FIRMWARE/system/constants.h:62-71`; `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:395-399` | IM73D int16 PCM is multiplied by `K1_MIC_IM73D_INPUT_GAIN` before shared sensitivity. Current default is `16.0f`. | Do not dynamically tune this constant at runtime. It is a mic-characterisation constant. |
| Loud guard effective sensitivity | `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:115-117` | Effective sensitivity is `CONFIG.SENSITIVITY * k1_loud_input_trim` while loud guard is enabled. | Auto-scale must sit above or beside this, never fight it. Loud guard remains the fast protection layer. |
| Loud guard protection | `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:130-193`; `SPECTRASYNQ_K1_FIRMWARE/system/constants.h:74-93` | Tracks clip, near-rail, peak-pin, spectral saturation, then trims input/GDFT response. | Auto-scale can use these as "too hot" signals and should back off slowly after guard activity. |
| Post-gain clamp and DC correction | `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:405-440` | Sensitivity is applied, samples are clipped, `CONFIG.DC_OFFSET` is subtracted, and `max_waveform_val_raw` is updated. | `max_waveform_val_raw` is historical naming; it is post-gain/post-DC, not raw DMA. |
| Noise calibration | `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:459-550`; `SPECTRASYNQ_K1_FIRMWARE/audio/k1_gdft_core.cpp:195-267` | Learns DC/SSL floors, validates, then persists accepted calibration/config/profile. | Auto-sensing must observe calibration validity but must not start or overwrite calibration. |
| Response gain | `SPECTRASYNQ_K1_FIRMWARE/system/globals.h:54-60`; `SPECTRASYNQ_K1_FIRMWARE/serial/serial_cmd_handlers.cpp:826-839` | Runtime-only `audio_response_gain` clamps to `0.25..4.0`, default `1.0`. | Do not overload this for mic auto-scale; it is a downstream response knob. |
| GDFT AGC | `SPECTRASYNQ_K1_FIRMWARE/audio/k1_gdft_core.cpp:304-519` | Broadband/per-band AGC normalises spectral output, gates silence, clamps spectrogram bins to `[0,1]`. | Auto-sensing should feed AGC a healthier input range; it should not be another spectral AGC. |
| Serial sensitivity | `SPECTRASYNQ_K1_FIRMWARE/serial/serial_cmd_handlers.cpp:259-280` | `:sensitivity=<float>` writes `CONFIG.SENSITIVITY`, clamps to `0.10..20.0`, rejects malformed input, and schedules save. | Existing serial surface is broad and persistent; auto-sense must not spam it. |
| Wireless sensitivity | `SPECTRASYNQ_K1_FIRMWARE/control/sb_k1_control_facade.cpp:414-450`; sensitivity apply branch | `global.sensitivity` now uses the same `0.10..20.0` range as serial/hotkeys, then saves config. | The user-facing scale mismatch is closed; auto-sense still needs a persistence-churn guard. |
| Protocol contract | `docs/protocol/k1-ws-controls-registry.yaml:35-50`; `docs/protocol/k1-rest-contract.yaml:1-8` | WebSocket controls include `global.sensitivity`; the REST contract is explicitly empty/not implemented for this control slice. | Do not add a parallel REST control for auto-sense. If exposed, use the existing WebSocket control pattern. |
| Persistence | `SPECTRASYNQ_K1_FIRMWARE/persistence/bridge_fs.h:17-27`; `:31-64`; `:146-159` | PDM config/calibration files are namespaced away from SPH files; `save_config()` writes the whole `CONFIG` blob and is guarded against low internal RAM before LittleFS open. | Runtime auto-scale must avoid persistence churn and avoid LittleFS work from the controller path. |
| Raw sample surface | `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:356-372`; `SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h:2784-2847` | `:dump_raw` prints the first 32 DMA samples before IM73D gain, sensitivity, clamp, and DC offset. | Existing raw proof is manual/one-shot. Auto-sense should add read-only raw health telemetry before relying on conditioned AP data. |
| Real-audio harness | `scripts/regression-harness/im73d_audio_eval.py:1-15`; `:193-200`; `:232-271`; `:482-560` | Identifies devices by USB serial, DTR/RTS low, sends only `:build`/`:dump`, refuses calibration tokens, records front-end state, gates clip/near/input trim, warns on downstream peak pin. | Reuse this safety model for live proof. Extend it only with explicit read-only commands/fields. |
| Byte gate | `scripts/regression-harness/mic_stable_byte_gate.sh:1-40`; `tests/test_mic_stable_byte_gate_static.py:1-52` | Stable-section byte gate is the trustworthy mic-lane behaviour-preservation oracle. | With the feature flag off, SPH/IM73D reference envs must remain stable-section byte-identical. |

Reference audit to read first:
`docs/hardware/im73d-audio-pipeline-purity-audit-2026-07-06.md`.

## Design Position

Auto-sensing should be a slow supervisory controller, not a replacement for:

- raw mic proof,
- manual/Captain-authorised silence calibration,
- loud guard,
- `audio_response_gain`,
- GDFT AGC, or
- user-facing `CONFIG.SENSITIVITY`.

Recommended layering:

```text
raw DMA sample
  -> fixed mic extraction gain (IM73D/SPH characterisation)
  -> base user/product sensitivity
  -> auto-sense runtime scale
  -> loud-guard fast input trim
  -> clamp/DC correction/drive follower
  -> response gain
  -> GDFT/per-band AGC/spectral tilt
  -> semantic/visual consumers
```

Proposed effective input scale:

```cpp
effective_sensitivity =
    CONFIG.SENSITIVITY
  * k1_mic_auto_scale
  * k1_loud_input_trim;
```

`k1_mic_auto_scale` should be RAM-only in v1, bounded, slow-moving, observable,
and resettable to `1.0f`.

The safest integration seam is beside `k1_loud_guard_effective_sensitivity()`.
Update the auto-scale outside the per-sample loop, using rolling metrics already
published for the previous frame, then apply the scalar to the next frame. This
keeps the hot path to a single multiply and avoids sorting, serial output,
LittleFS/NVS access, or control decisions inside sample acquisition.

If a future product goal is only "stronger-looking visuals", `audio_response_gain`
is the lower-risk downstream knob. It cannot, however, prevent pre-clamp overload
or recover weak raw capture before DC/floor logic, so it is not sufficient for
true mic front-end conditioning.

## Control Objective

The controller should keep the AP front end in a target operating window:

- quiet passages remain quiet; the controller must not "turn up silence";
- normal music produces enough `max_waveform_val_raw`, `waveform_peak_scaled`,
  spectrum energy, and onset/chord material for visuals;
- loud music does not clip, hit near-rail, reduce `input_trim`, or pin a large
  fraction of the spectrogram;
- downstream AGC does not sit at extremes for long periods;
- behaviour changes slowly enough that the audience does not see pumping.

Exact thresholds must not be guessed in implementation. Use the existing
documented IM73D/SPH target intent as a starting hypothesis only:
`constants.h:62-70` notes that `K1_MIC_IM73D_INPUT_GAIN=16.0f` was chosen to
land around the SPH `~7000` `max_raw` band while staying below the near-rail
region. That is not yet an auto-sense acceptance window.

## Required Telemetry Before Control

Add a telemetry-only phase before any automatic scaling.

Minimum new read-only metrics:

| Metric | Purpose | Source domain |
| --- | --- | --- |
| `raw_abs_peak` | detect dead mic, raw silence, and raw rail before firmware gain | DMA/pre-conditioning |
| `raw_rms` | distinguish single transients from real room level | DMA/pre-conditioning |
| `raw_clip_pct` or `raw_near_rail_pct` | prove the microphone/driver itself is not railing | DMA/pre-conditioning |
| `post_gain_peak` | separate raw mic level from configured gain effect | after fixed mic gain and base/auto sensitivity |
| `auto_scale` | active multiplier, always reported | controller state |
| `auto_state` | state machine state, numeric plus readable dump | controller state |
| `auto_reason` | last transition/rejection reason | controller state |
| `auto_window_sec` | rolling window age used for the decision | controller state |

Existing useful conditioned fields:

- `[AP] max_raw`, `peak_scaled`, `response_gain`, `input_trim`, `gdft_trim`,
  `clip_pct`, `near_pct`, `peak_pin`, `spec_sat`, `cal_source`, `cal_valid`.
- `stream_agc` gain/energy fields, with the purity-audit caveat that reported
  floor/threshold fields are not authoritative active per-band AGC floors in the
  current per-band path.

## State Machine

Proposed states:

| State | Meaning | Exit condition |
| --- | --- | --- |
| `DISABLED` | Feature compiled or runtime disabled; scale forced to `1.0f`. | Runtime enable command/control. |
| `OBSERVE_BOOT` | Collect enough rolling data after boot/reset, no adjustment. | Required window age and calibration status known. |
| `HOLD` | Signal is inside the target window; no adjustment. | Too hot, too cold, fault, or stale data. |
| `ADJUST_UP` | Sustained usable music is under-driving the AP path with no rail/trim signals. | Scale step applied, then return to observe/hold. |
| `ADJUST_DOWN` | Sustained signal is too hot but not emergency-clipping. | Scale step applied, then return to observe/hold. |
| `PROTECT` | Clip/near-rail/input-trim/saturation event means fast protection has engaged or is imminent. | Immediate downward cap, then cooldown. |
| `FAULT` | Invalid/stale telemetry, I2S faults, bad calibration state, non-finite scale, or raw mic impossible state. | Manual reset or enough healthy telemetry. |

State rules:

1. `PROTECT` can reduce `auto_scale` quickly, but only within bounds.
2. `ADJUST_UP` must be slow and require sustained evidence of under-drive during
   non-silence music.
3. `HOLD` is a first-class outcome. Constant motion is a bug.
4. Quiet/silence windows should update environmental estimates, not gain-up the
   mic.
5. If loud guard reduces `input_trim`, auto-sense should interpret that as a
   failed headroom condition and back off after cooldown.

## Algorithm Sketch

The first executable controller should be deterministic and host-testable.

Inputs per AP frame:

```text
raw_abs_peak
raw_rms
raw_near_rail_pct
max_waveform_val_raw
waveform_peak_scaled
clip_pct
near_pct
input_trim
gdft_trim
spec_sat
agc_gain[4]
agc_energy[4]
cal_valid
cal_source
noise_complete
```

Rolling windows:

- 10-30 seconds for room/music level percentiles;
- 2-5 seconds for emergency headroom detection;
- cooldown window after any downscale/protect event;
- separate quiet-window tracking so silence does not masquerade as a weak room.

Decision logic:

1. Reject/update-freeze if telemetry is stale, calibration invalid, sample read
   faulted, or any metric is non-finite.
2. Enter `PROTECT` if any hard headroom signal appears:
   `clip_pct > 0`, `near_pct > 0`, raw near-rail, `input_trim < 0.999`, or
   sustained high spectral saturation.
3. Enter `ADJUST_DOWN` if rolling p90/p99 conditioned drive or spectral
   saturation is too high while hard rails are not yet active.
4. Enter `ADJUST_UP` only if:
   - the window is classified as active music, not silence;
   - raw telemetry is healthy;
   - no clip/near/input-trim/saturation signals are present;
   - rolling p90/p99 conditioned drive is below the measured target lower band;
   - AGC gains are consistently near the high end, implying downstream
     normalisation is compensating for weak input.
5. Apply bounded multiplicative steps:
   - up: small, e.g. `+3..5%` per accepted window;
   - down: larger than up, e.g. `-8..15%` per accepted window;
   - protect: clamp immediately toward a safe cap.
6. Use hysteresis and minimum dwell time. Do not reverse direction on a single
   transient.

Candidate bounds for v1 should be conservative and measured, not guessed. A
reasonable shape is:

```text
auto_scale_min <= k1_mic_auto_scale <= auto_scale_max
auto_scale starts at 1.0
auto_scale does not persist across boot in v1
auto_scale never bypasses loud-guard min trims
```

## Why This Is Worth Doing

The system-archetype case for the feature is strong:

- "Limits to growth": one fixed mic sensitivity cannot fit quiet bedrooms,
  desk speakers, loud-room playback, and device placement variance.
- "Shifting the burden": downstream AGC can make visuals look alive while hiding
  a weak or over-hot input. Auto-sense should reduce that burden by feeding the
  AP path a healthier range.
- "Fixes that fail": turning up sensitivity blindly can create clipping,
  calibration contamination, and washed-out spectral/chroma behaviour. This
  design avoids that by separating raw telemetry, slow control, and fast guard.

The TRIZ contradiction is: K1 needs high sensitivity in quiet rooms and low
sensitivity in loud rooms, without asking Captain/users to retune manually and
without corrupting measurements. The resolution is separation by layer and time:
fixed mic gain for hardware characterisation, user/base sensitivity for intent,
slow auto-scale for environment adaptation, fast loud guard for protection, and
downstream AGC for spectral normalisation.

## Steelman Against The Feature

The strongest objection is that adaptive sensitivity can make the product less
deterministic:

- it may hide bad mic wiring or a failed calibration;
- it may cause visual pumping during quiet passages;
- it may fight existing AGC/loud guard loops;
- it may make IM73D/SPH/DSR comparisons unreproducible;
- it may wear flash if implemented by writing `CONFIG.SENSITIVITY`;
- it may add hot-loop cost on Core 0.

Answer:

- ship telemetry first, controller second;
- make v1 runtime-only, default-off, and feature-flagged;
- require raw/pre-conditioning metrics before scaling;
- never auto-run calibration;
- pin/disable auto-sense for all canonical mic-purity measurements;
- host-test the controller from deterministic traces before bench proof;
- keep heavy rolling-stat work out of the audio hot loop.

## Cynefin Classification

This is not a simple one-shot firmware edit.

- Complicated: controller implementation, state machine, bounds, tests, and
  source integration can be engineered and reviewed.
- Complex: real room acoustics, speaker placement, track dynamics, and visual
  perception require safe-to-fail experiments and Captain eyes-on acceptance.

Therefore the execution lane must be phased, with measurement gates between
phases.

## Execution Plan For The Next Agent

### Phase 0 - Read And Verify

Read, in order:

1. `AGENT_OS.md`
2. `docs/hardware/im73d-codex-resume-handover-2026-07-06.md`
3. `docs/hardware/im73d-audio-pipeline-purity-audit-2026-07-06.md`
4. this document
5. source files listed in Current Source Truth

Then verify:

```bash
git rev-parse --abbrev-ref HEAD
git log --oneline -8
git status --short
```

Expected active branch at the time this handoff was written:
`lane/im73d-pdm-eval`.

### Phase 1 - Telemetry Only

Goal: expose enough read-only health data to decide whether automatic scaling is
safe. Do not implement scaling yet.

Tasks:

1. Add pre-conditioning raw peak/RMS/near-rail counters in static storage.
2. Update `[AP]` or a new colon-prefixed read-only status command with those
   metrics.
3. Add schema/parser tests so telemetry drift is caught.
4. Extend `im73d_audio_eval.py` only if the command remains read-only and never
   sends calibration tokens.
5. Build/test/byte-gate with auto-sense behaviour still absent.

Acceptance:

- existing IM73D purity static tests pass;
- harness self-test passes;
- no serial write path can trigger calibration;
- default production behaviour remains unchanged where required;
- raw telemetry can distinguish silence, music, and rail-ish failure.

### Phase 2 - Measurement Characterisation

Goal: derive target windows from live data, not intuition.

Run on radio-free `k1_bench_im73d`, not BLE. Use MAC identity, not port name.
Use fixed track, fixed start offset, fixed Mac volume ladder, and repeated runs.
Capture quiet windows separately. Do not auto-calibrate.

Recommended evidence matrix:

| Condition | Purpose |
| --- | --- |
| quiet room, no stimulus | floor and false-boost protection |
| low volume music | under-drive detection |
| normal volume music | desired target band |
| loud music below rail | high-drive but acceptable band |
| intentionally over-hot only if Captain authorises volume | protect-state validation |

Outputs:

- proposed lower/upper target bands for raw and conditioned metrics;
- false-positive analysis for silence and quiet passages;
- expected AGC gain ranges in weak/healthy/too-hot conditions;
- reject reasons for any contaminated captures.

### Phase 3 - Host Controller Oracle

Goal: prove the controller with deterministic traces before firmware integration.

Create a pure host-testable controller model, either in C++ host harness or a
Python oracle mirroring the intended firmware state machine.

Required fixtures:

- stable healthy music;
- quiet room/no music;
- weak but active music;
- sudden loud transient;
- sustained loud music;
- raw near-rail;
- conditioned peak pin without raw clipping;
- loud guard input trim reduced;
- invalid calibration;
- stale telemetry;
- AGC max-gain compensation;
- repeated alternating quiet/loud passages.

Required assertions:

- no scale-up during silence;
- no scale-up during invalid calibration;
- fast downscale/protect on hard headroom signals;
- slow bounded upscale under sustained weak active music;
- no oscillation under alternating passages;
- `auto_scale` remains finite and in bounds;
- v1 does not call persistence or calibration functions.

### Phase 4 - Firmware Integration Behind Flag

Recommended file shape:

- `SPECTRASYNQ_K1_FIRMWARE/audio/k1_mic_auto_sense.h`
- `SPECTRASYNQ_K1_FIRMWARE/audio/k1_mic_auto_sense.cpp` if the build structure
  can support it cleanly; otherwise follow the repo's current header/TU pattern
  and keep the state small.
- Source touchpoint in `audio/i2s_audio.h` near effective sensitivity
  computation, using a tiny inline getter only.
- Optional read-only command/status surface in serial code, colon-prefixed.

Rules:

1. Default flag off.
2. With flag off, existing behaviour must be stable-section byte-identical where
   the mic lane requires it.
3. With flag on, controller state updates must be O(1) per AP frame or slower.
4. No serial output from the hot path.
5. No config save from controller updates.
6. Runtime reset command is allowed only if colon-prefixed and explicit.

### Phase 5 - Shadow Device Proof

Goal: prove recommendations before applying them.

Run the flagged build in shadow mode: compute `auto_state`, `auto_reason`, and
recommended `auto_scale`, but leave the applied scale at `1.0f`. Repeat quiet and
music captures. Accept only if:

- raw/pre-conditioning telemetry is unchanged by shadow mode;
- recommendations are stable and explainable;
- silence windows do not recommend gain-up;
- loud/protect windows recommend downscale or hold;
- no persistence writes occur from the auto-sense path.

### Phase 6 - Bench Runtime A/B

Goal: prove the feature helps without corrupting measurements.

Use bench IM73D, radio-free build. Disable feature for baseline, enable for
candidate. Keep all other factors pinned.

Acceptance:

- feature disabled reproduces baseline telemetry;
- feature enabled brings weak active music toward the measured target band;
- no `clip_pct`, `near_pct`, raw near-rail, or `input_trim` reduction;
- `auto_scale` changes slowly and then holds;
- downstream visuals improve under Captain eyes-on judgement;
- disabling auto-sense restores canonical measurement behaviour.

### Phase 7 - Production/Main-K1 Consideration

Do not move this feature to the main production K1 until:

- IM73D production swap status is resolved separately;
- raw/purity gates are not using auto-sense;
- Captain accepts the bench A/B outcome;
- documentation names the enabled/disabled measurement contract.

## Required Tests And Gates

Docs-only design work:

```bash
git diff --check
```

Telemetry implementation:

```bash
python3 -m pytest tests/test_im73d_audio_purity_static.py tests/test_im73d_audio_eval_harness.py -q
python3 -m pytest tests/test_serial_hotkeys_static.py tests/test_calibration_profile_static.py -q
bash scripts/regression-harness/mic_stable_byte_gate.sh
```

Controller implementation:

```bash
python3 -m pytest tests/test_mic_auto_sense_controller.py -q
python3 -m pytest tests/test_im73d_audio_purity_static.py tests/test_im73d_audio_eval_harness.py -q
python3 -m pytest tests/test_k1_loud_guard_static.py tests/test_agc_perband_independence.py -q
python3 -m pytest tests/test_serial_hotkeys_static.py tests/test_calibration_profile_static.py -q
bash scripts/regression-harness/mic_stable_byte_gate.sh
```

Serial/control-surface changes must also check the golden serial replay fixture,
because it already separates persisted `sensitivity` from runtime-only
`response_gain`:

```bash
python3 -m pytest tests/test_golden_master.py -q
```

Firmware touchpoint:

```bash
pio run -e k1_hardware
pio run -e k1_bench_im73d
```

If any firmware file or `platformio.ini` changes, follow the repo's pre-commit
gate and do not claim completion from compile-only proof if device proof was
part of the phase.

## Stop Conditions

Stop and escalate to Captain only for:

- any action that would require real silence calibration;
- any main-K1 physical mic swap or soldering;
- any perceptual judgement about whether auto-sense "feels" better;
- any proposal to persist auto-scale or change the product default;
- any measurement requiring louder playback than Captain has already authorised.

Do not escalate for:

- reading source/docs;
- writing host tests;
- adding default-off telemetry;
- extending read-only parser tests;
- running host gates.

## Decision Points For Captain

These are not blockers for telemetry/host planning, but they are blockers before
production enablement:

1. Should auto-sense be presented as a user-visible "Auto Mic" mode, or remain
   an internal production supervisor?
2. Should the controller ever persist a learned profile, or should it remain
   runtime-only forever?
3. What is the perceptual priority when the controller sees a trade-off:
   stronger visuals in quiet rooms, or absolute resistance to false gain-up?
4. What explicit UI language should distinguish manual sensitivity from any
   future runtime-only auto-sense offset?

## One-Paragraph Handoff Prompt

You are resuming the K1 auto-sensing mic sensitivity design lane in
`/Users/spectrasynq/SpectraSynq_K1_Firmware`. Read `AGENT_OS.md`,
`docs/hardware/im73d-audio-pipeline-purity-audit-2026-07-06.md`, and
`docs/hardware/k1-auto-sensing-mic-sensitivity-scaling-design-2026-07-06.md`
before editing. Implement only the next phase: telemetry first, no auto-scale
control, no calibration firing, no device identity by port name, no BLE build
for measurements, no persistence writes from auto-sense. Preserve raw/purity
measurement semantics and keep all behaviour behind a default-off flag until
host, byte, bench, and Captain eyes-on gates are green.
