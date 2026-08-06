# MAS-CODE-01: Mic Auto-Sense Telemetry Seam Map

Date: 2026-07-10
Repo: `/Users/spectrasynq/SpectraSynq_K1_Firmware`
Scope: read-only source inspection plus this artifact

## Verdict

STATUS: VERIFIED

Telemetry-only mic auto-sense should integrate at the I2S acquisition/front-end telemetry boundary in `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h`, emit read-only fields through the existing `[AP]` key/value stream, and keep any future applied-scale hook adjacent to `k1_loud_guard_effective_sensitivity()` without changing that formula in the telemetry-only slice.

This verdict is current-checkout source evidence, not a design-doc symbol assumption. The proposed controller symbols are absent from live firmware/test/script/protocol surfaces:

```bash
rg -n "K1_MIC_AUTO_SENSE|k1_mic_auto|auto_scale|auto_state|auto_reason" SPECTRASYNQ_K1_FIRMWARE tests scripts platformio.ini docs/protocol 2>/dev/null
```

Observed result: zero matches.

## Required First Actions

- CWD guard passed:

```bash
git -C /Users/spectrasynq/SpectraSynq_K1_Firmware rev-parse --show-toplevel
```

Output matched `/Users/spectrasynq/SpectraSynq_K1_Firmware`.

- Required artifact/design docs were read before live source:
  - `artifacts/self_calibrating_sensitivity_forensics_2026-07-10/orchestrator_synthesis.md:6-34`
  - `docs/hardware/k1-auto-sensing-mic-sensitivity-scaling-design-2026-07-06.md:18-34`
  - `docs/hardware/k1-auto-sensing-mic-sensitivity-scaling-design-2026-07-06.md:127-150`
  - `docs/hardware/k1-auto-sensing-mic-sensitivity-scaling-design-2026-07-06.md:398-432`
  - `docs/hardware/im73d-audio-pipeline-purity-audit-2026-07-06.md:21-50`
  - `docs/hardware/im73d-audio-pipeline-purity-audit-2026-07-06.md:73-101`

## Safe Integration Seams

### 1. Raw/pre-conditioning telemetry seam

Use the acquisition block in `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h`.

Evidence:

- I2S/PDM read fills raw DMA buffers before any gain or sensitivity:
  - `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:320-348`
- Existing IM73D raw telemetry is already computed before fixed mic gain, `CONFIG.SENSITIVITY`, clamp, DC removal, response gain, GDFT, and AGC:
  - `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:359-377`
- The telemetry storage lives beside the raw buffers:
  - `SPECTRASYNQ_K1_FIRMWARE/system/globals.h:143-152`
- The IM73D raw near-rail threshold is explicitly a measurement-purity surface, not a gain control:
  - `SPECTRASYNQ_K1_FIRMWARE/system/constants.h:73-75`

Seam decision:

- For IM73D-only telemetry, extend the existing `#ifdef K1_MIC_IM73D_PDM_V1` raw telemetry block at `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:359-377`.
- For product-wide mic telemetry, add an equivalent SPH0645 pre-conditioning calculation after the `i2s_samples_raw` read and before SPH extraction at `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:423-427`.
- Keep the block O(n) over `CONFIG.SAMPLES_PER_CHUNK`, heap-free, serial-silent, and without sorting.

Rerun:

```bash
nl -ba SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h | sed -n '320,377p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/system/globals.h | sed -n '136,152p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/system/constants.h | sed -n '62,76p'
```

### 2. Effective sensitivity seam for future applied control

The future applied-scale hook belongs beside the loud-guard effective sensitivity getter, but telemetry-only must leave applied scale at `1.0f` and avoid changing the current formula.

Evidence:

- Current formula is only `CONFIG.SENSITIVITY` or `CONFIG.SENSITIVITY * k1_loud_input_trim`:
  - `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:115-117`
- The getter is sampled once before the per-sample loop:
  - `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:405-410`
- The per-sample hot path applies that scalar, then records loud-guard preclip evidence:
  - `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:417-433`
- Loud-guard state lives in inline static globals:
  - `SPECTRASYNQ_K1_FIRMWARE/system/globals.h:122-134`

Seam decision:

- Telemetry-only slice may publish `auto_scale=1.000`, `auto_state=disabled` or `shadow`, and `auto_reason=<reason>` as read-only state.
- Do not multiply `k1_effective_sensitivity` by auto-scale in this slice.
- When a future controller is authorised, the minimal applied hook is a tiny inline getter adjacent to `k1_loud_guard_effective_sensitivity()` at `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:115-117`.

Rerun:

```bash
nl -ba SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h | sed -n '86,122p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h | sed -n '405,433p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/system/globals.h | sed -n '122,134p'
```

### 3. Read-only AP telemetry emission seam

Use the existing `[AP]` stream shape for telemetry fields.

Evidence:

- `[AP]` is already rate-limited to about 1 Hz:
  - `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:784-797`
- Base AP fields include conditioned front-end, calibration, tempo, and onset data:
  - `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:800-806`
- IM73D raw fields are appended only under `K1_MIC_IM73D_PDM_V1`:
  - `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:807-812`
- Loud-guard telemetry is appended under `K1_LOUD_GUARD_V1`:
  - `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:813-825`
- Schema-lock tests already assert the AP/front-end/loud-guard field strings:
  - `tests/test_audio_telemetry_schema_static.py:15-63`

Seam decision:

- Append telemetry-only fields to the `[AP]` line, using simple key/value tokens already parsed by the harness.
- Candidate fields that match the design intent: `auto_scale`, `auto_state`, `auto_reason`, `auto_window_sec`, plus any missing raw/pre-conditioning health fields.
- Do not print from inside the per-sample loop. Keep emission in the existing rate-limited AP block.

Rerun:

```bash
nl -ba SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h | sed -n '784,825p'
nl -ba tests/test_audio_telemetry_schema_static.py | sed -n '15,63p'
```

### 4. Optional module/file placement

If telemetry state needs a dedicated module, current build filtering already accepts `audio/k1_*.cpp`.

Evidence:

- Production build compiles `+<audio/k1_*.cpp>`:
  - `platformio.ini:44`
- Existing `audio/` pattern includes `k1_gdft_core.cpp` and `k1_gdft_core.h`:
  - `SPECTRASYNQ_K1_FIRMWARE/audio/k1_gdft_core.cpp`
  - `SPECTRASYNQ_K1_FIRMWARE/audio/k1_gdft_core.h`
- Current audio directory has no `k1_mic_auto_sense.*` file:
  - `SPECTRASYNQ_K1_FIRMWARE/audio/`

Seam decision:

- Future file targets are `SPECTRASYNQ_K1_FIRMWARE/audio/k1_mic_auto_sense.h` and, if needed, `SPECTRASYNQ_K1_FIRMWARE/audio/k1_mic_auto_sense.cpp`.
- Keep hot-path access through a tiny inline/status getter from `i2s_audio.h`; keep heavier window/state formatting outside the per-sample loop.

Rerun:

```bash
nl -ba platformio.ini | sed -n '32,45p'
find SPECTRASYNQ_K1_FIRMWARE/audio -maxdepth 1 -type f | sort | sed -n '1,120p'
```

## Surfaces The Slice Must Respect

### User/base sensitivity is persistent product intent

Evidence:

- Factory default `CONFIG.SENSITIVITY` is `2.4`:
  - `SPECTRASYNQ_K1_FIRMWARE/system/globals_config.cpp:48-65`
- Canonical sensitivity range is `0.10..20.0`:
  - `SPECTRASYNQ_K1_FIRMWARE/system/config_types.h:55-56`
- Typed serial `:sensitivity=<value>` writes `CONFIG.SENSITIVITY` and schedules persistence:
  - `SPECTRASYNQ_K1_FIRMWARE/serial/serial_cmd_handlers.cpp:259-280`
- Legacy hotkeys `w`/`W` also write `CONFIG.SENSITIVITY` and schedule persistence:
  - `SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h:1678-1688`
- Wireless `global.sensitivity` writes `CONFIG.SENSITIVITY` and schedules persistence:
  - `SPECTRASYNQ_K1_FIRMWARE/control/sb_k1_control_facade.cpp:747-751`
- The WebSocket controls registry includes `global.sensitivity`; REST is explicitly empty for this control slice:
  - `docs/protocol/k1-ws-controls-registry.yaml:45-50`
  - `docs/protocol/k1-rest-contract.yaml:1-8`

Rule:

- Telemetry-only auto-sense must not write `CONFIG.SENSITIVITY`.
- Telemetry-only auto-sense must not call `save_config()` or `save_config_delayed()`.
- Do not add a parallel REST control.

Rerun:

```bash
nl -ba SPECTRASYNQ_K1_FIRMWARE/system/globals_config.cpp | sed -n '48,66p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/system/config_types.h | sed -n '48,56p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/serial/serial_cmd_handlers.cpp | sed -n '259,280p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h | sed -n '1678,1688p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/control/sb_k1_control_facade.cpp | sed -n '747,751p'
nl -ba docs/protocol/k1-ws-controls-registry.yaml | sed -n '45,84p'
nl -ba docs/protocol/k1-rest-contract.yaml | sed -n '1,8p'
```

### `audio_response_gain` is a separate downstream runtime knob

Evidence:

- Runtime-only global and clamp:
  - `SPECTRASYNQ_K1_FIRMWARE/system/globals.h:54-60`
- Serial `response_gain` handler updates `audio_response_gain`, clamps to `0.25..4.0`, and does not save config:
  - `SPECTRASYNQ_K1_FIRMWARE/serial/serial_cmd_handlers.cpp:836-849`
- AP reports `response_gain` in the conditioned telemetry line:
  - `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:800-803`

Rule:

- Do not overload `audio_response_gain` as mic auto-scale.
- Treat it as downstream visual/DSP response evidence and a possible comparison field only.

Rerun:

```bash
nl -ba SPECTRASYNQ_K1_FIRMWARE/system/globals.h | sed -n '54,60p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/serial/serial_cmd_handlers.cpp | sed -n '836,849p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h | sed -n '800,803p'
```

### Noise calibration remains Captain-authorised and persistent

Evidence:

- `start_noise_cal()` resets calibration state and starts the calibration path:
  - `SPECTRASYNQ_K1_FIRMWARE/calibration/noise_cal.h:53-78`
- `clear_noise_cal()` persists config/calibration/profile changes:
  - `SPECTRASYNQ_K1_FIRMWARE/calibration/noise_cal.h:80-94`
- Accepted noise calibration persists ambient noise, config, and calibration profile:
  - `SPECTRASYNQ_K1_FIRMWARE/audio/k1_gdft_core.cpp:217-266`
- Wireless facade explicitly rejects direct `calibration.noise.start` / `start_noise_cal` and points to arm/confirm:
  - `SPECTRASYNQ_K1_FIRMWARE/control/sb_k1_control_facade.cpp:471-475`
- Allowed calibration controls are the two-step/status/clear names:
  - `SPECTRASYNQ_K1_FIRMWARE/control/sb_k1_control_facade.cpp:447-450`
- The arm helper queues calibration only after the confirm window:
  - `SPECTRASYNQ_K1_FIRMWARE/control/sb_noise_cal_arm.cpp:21-42`

Rule:

- Telemetry-only auto-sense must not call `start_noise_cal()`.
- It must not set `noise_complete=false`, queue `noise_transition_queued`, or write calibration/profile files.
- It may report calibration status fields already exposed in `[AP]`: `cal_source`, `cal_valid`, and `cal_reason`.

Rerun:

```bash
nl -ba SPECTRASYNQ_K1_FIRMWARE/calibration/noise_cal.h | sed -n '53,94p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/audio/k1_gdft_core.cpp | sed -n '217,266p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/control/sb_k1_control_facade.cpp | sed -n '447,475p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/control/sb_noise_cal_arm.cpp | sed -n '21,42p'
```

### GDFT/AGC is downstream conditioning, not raw front-end telemetry

Evidence:

- Noise calibration completion and persistence happen in `process_GDFT()`:
  - `SPECTRASYNQ_K1_FIRMWARE/audio/k1_gdft_core.cpp:195-266`
- GDFT/AGC computes conditioned spectrogram output and telemetry mirrors:
  - `SPECTRASYNQ_K1_FIRMWARE/audio/k1_gdft_core.cpp:304-523`
- Loud guard trims the AGC target/floor downstream when enabled:
  - `SPECTRASYNQ_K1_FIRMWARE/audio/k1_gdft_core.cpp:335-342`

Rule:

- Do not implement telemetry-only mic auto-sense in `k1_gdft_core.cpp`.
- Use GDFT/AGC fields only as downstream context, never as raw mic proof.

Rerun:

```bash
nl -ba SPECTRASYNQ_K1_FIRMWARE/audio/k1_gdft_core.cpp | sed -n '195,266p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/audio/k1_gdft_core.cpp | sed -n '304,523p'
```

### Manual raw dump and harness read-only contract

Evidence:

- Manual one-shot `dump_raw` request flag is declared in `i2s_audio.h`:
  - `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:71-74`
- The raw dump prints a single future raw frame and clears the request:
  - `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:379-396`
- Serial `dump_raw=silence|tone` arms it manually and warns agents not to auto-trigger:
  - `SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h:2795-2858`
- The IM73D real-audio harness parses `[AP]` key/value fields, allows only read-only `:build`/`:dump`, and refuses `start_noise_cal`, `N`, and `Y`:
  - `scripts/regression-harness/im73d_audio_eval.py:58-69`
  - `scripts/regression-harness/im73d_audio_eval.py:219-227`
  - `scripts/regression-harness/im73d_audio_eval.py:273-279`

Rule:

- Do not auto-trigger `dump_raw`.
- Prefer continuous read-only `[AP]` telemetry for this slice.
- If harness parsing is extended, preserve the read-only serial command set.

Rerun:

```bash
nl -ba SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h | sed -n '71,74p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h | sed -n '379,396p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h | sed -n '2795,2858p'
nl -ba scripts/regression-harness/im73d_audio_eval.py | sed -n '58,69p'
nl -ba scripts/regression-harness/im73d_audio_eval.py | sed -n '219,227p'
nl -ba scripts/regression-harness/im73d_audio_eval.py | sed -n '273,279p'
```

### Build/env byte gates

Evidence:

- Default env is `k1_hardware`, source dir is `SPECTRASYNQ_K1_FIRMWARE`, and `build_src_filter` includes `audio/k1_*.cpp`:
  - `platformio.ini:14-16`
  - `platformio.ini:44`
- Production build has loud guard enabled:
  - `platformio.ini:116-119`
- `k1_hardware` does not define `K1_MIC_IM73D_PDM_V1`; IM73D bench/prod envs add that flag:
  - `platformio.ini:216-244`
- Stable-section byte gate covers `k1_hardware`, `k1_bench_reference`, and `k1_bench_im73d`:
  - `scripts/regression-harness/mic_stable_byte_gate.sh:35-40`
  - `tests/test_mic_stable_byte_gate_static.py:40-52`

Rule:

- Any future telemetry implementation must keep flag-off production behaviour byte-stable where required.
- IM73D-specific telemetry is currently compiled only in IM73D envs. If the slice requires main SPH telemetry too, add the SPH pre-conditioning path explicitly rather than assuming IM73D fields exist in `k1_hardware`.

Rerun:

```bash
nl -ba platformio.ini | sed -n '14,16p'
nl -ba platformio.ini | sed -n '44,44p'
nl -ba platformio.ini | sed -n '116,119p'
nl -ba platformio.ini | sed -n '216,244p'
nl -ba scripts/regression-harness/mic_stable_byte_gate.sh | sed -n '35,40p'
nl -ba tests/test_mic_stable_byte_gate_static.py | sed -n '40,52p'
```

## Unsafe Seams Refuted

1. Do not integrate auto-sense as `CONFIG.SENSITIVITY` writes.
   - Refuted by persistent serial/hotkey/WebSocket paths at `serial_cmd_handlers.cpp:259-280`, `serial_menu.h:1678-1688`, and `sb_k1_control_facade.cpp:747-751`.

2. Do not integrate in `audio_response_gain`.
   - Refuted by runtime downstream response-gain semantics at `globals.h:54-60` and `serial_cmd_handlers.cpp:836-849`.

3. Do not integrate in `k1_gdft_core.cpp` AGC.
   - Refuted by downstream conditioned AGC path at `k1_gdft_core.cpp:304-523` and purity audit warning that GDFT/AGC outputs are not raw mic proof.

4. Do not integrate by firing calibration.
   - Refuted by `start_noise_cal()` side effects at `noise_cal.h:53-78`, calibration persistence at `k1_gdft_core.cpp:263-265`, and WebSocket rejection of direct start controls at `sb_k1_control_facade.cpp:471-475`.

5. Do not integrate by auto-triggering `dump_raw`.
   - Refuted by the serial handler's manual interpretation/safety warning at `serial_menu.h:2795-2858`.

6. Do not trust design-doc proposed symbols as implemented source.
   - Refuted by zero live matches for `K1_MIC_AUTO_SENSE|k1_mic_auto|auto_scale|auto_state|auto_reason` in firmware/tests/scripts/platformio/protocol surfaces.

## Minimal Telemetry-Only Slice Shape

No implementation was performed. If authorised later, the lowest-risk current-source shape is:

1. Define a tiny telemetry state surface, likely `SPECTRASYNQ_K1_FIRMWARE/audio/k1_mic_auto_sense.h` plus optional `SPECTRASYNQ_K1_FIRMWARE/audio/k1_mic_auto_sense.cpp`.
2. Populate raw/pre-conditioning fields from `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:359-377` or its SPH equivalent at the same pre-conditioning boundary.
3. Publish read-only state through the existing `[AP]` block at `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:784-825`.
4. Keep applied `auto_scale` at `1.0f`; do not change `k1_loud_guard_effective_sensitivity()` in the telemetry-only phase.
5. Extend schema/parser tests around `tests/test_audio_telemetry_schema_static.py:15-63` and harness parsing in `scripts/regression-harness/im73d_audio_eval.py:58-86`.
6. Do not touch persistence, calibration, REST, or user-facing sensitivity controls.

## Commands Run

Read-only commands only, plus writing this artifact:

```bash
git -C /Users/spectrasynq/SpectraSynq_K1_Firmware rev-parse --show-toplevel
wc -l artifacts/self_calibrating_sensitivity_forensics_2026-07-10/orchestrator_synthesis.md
wc -l docs/hardware/k1-auto-sensing-mic-sensitivity-scaling-design-2026-07-06.md
wc -l docs/hardware/im73d-audio-pipeline-purity-audit-2026-07-06.md
nl -ba artifacts/self_calibrating_sensitivity_forensics_2026-07-10/orchestrator_synthesis.md
nl -ba docs/hardware/k1-auto-sensing-mic-sensitivity-scaling-design-2026-07-06.md
nl -ba docs/hardware/im73d-audio-pipeline-purity-audit-2026-07-06.md
rg -n "K1_MIC_AUTO_SENSE|k1_mic_auto|auto_scale|auto_state|auto_reason|raw_i16|dump_raw|loud_guard|effective_sensitivity|input_trim|clip_pct|near_pct|AUDIO_RESPONSE_GAIN|response_gain|global\\.sensitivity|K1_SENSITIVITY|save_config|start_noise_cal|noise_cal|K1_MIC_IM73D_INPUT_GAIN|src_filter|build_src_filter|lib_extra_dirs|build_flags" SPECTRASYNQ_K1_FIRMWARE platformio.ini scripts tests docs/protocol 2>/dev/null
git status --short
nl -ba SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h | sed -n '1,230p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h | sed -n '320,460p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h | sed -n '459,825p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/audio/k1_gdft_core.cpp | sed -n '180,540p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h | sed -n '2480,2870p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/serial/serial_cmd_handlers.cpp | sed -n '230,295p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/control/sb_k1_control_facade.cpp | sed -n '340,665p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/control/sb_k1_control_facade.cpp | sed -n '720,785p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/control/sb_k1_control_facade.cpp | sed -n '780,930p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/control/sb_noise_cal_arm.cpp | sed -n '1,80p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/calibration/noise_cal.h | sed -n '45,100p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/system/globals.h | sed -n '1,230p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/system/globals_config.cpp | sed -n '45,75p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/system/constants.h | sed -n '1,125p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/system/config_types.h | sed -n '44,62p'
nl -ba platformio.ini | sed -n '1,310p'
nl -ba docs/protocol/k1-ws-controls-registry.yaml | sed -n '1,90p'
nl -ba docs/protocol/k1-rest-contract.yaml | sed -n '1,80p'
nl -ba scripts/regression-harness/im73d_audio_eval.py | sed -n '1,285p'
nl -ba scripts/regression-harness/mic_stable_byte_gate.sh | sed -n '1,80p'
nl -ba tests/test_mic_stable_byte_gate_static.py | sed -n '1,90p'
nl -ba tests/test_audio_telemetry_schema_static.py | sed -n '1,180p'
find SPECTRASYNQ_K1_FIRMWARE/audio -maxdepth 1 -type f | sort | sed -n '1,120p'
rg -n "K1_SENSITIVITY_MIN|K1_SENSITIVITY_MAX|AUDIO_RESPONSE_GAIN_MIN|DEFAULT_AUDIO_RESPONSE_GAIN|AUDIO_RESPONSE_GAIN_MAX" SPECTRASYNQ_K1_FIRMWARE/system SPECTRASYNQ_K1_FIRMWARE 2>/dev/null
rg -n "K1_MIC_AUTO_SENSE|k1_mic_auto|auto_scale|auto_state|auto_reason" SPECTRASYNQ_K1_FIRMWARE tests scripts platformio.ini docs/protocol 2>/dev/null
```

## Method Risk

The main way this could be wrong is if an uninspected generated/control surface outside `SPECTRASYNQ_K1_FIRMWARE`, `tests`, `scripts`, `platformio.ini`, and `docs/protocol` already consumes future auto-sense telemetry names. That would not change the safe firmware seam, but it could change parser/schema update targets. I found no live firmware implementation of the proposed symbols in the inspected surfaces.

## Next Orchestrator Action

Use this seam map as the implementation handoff for a future telemetry-only phase. The implementation phase should require no calibration, no build flash, no serial monitor, no audio playback, and no persistence path in the auto-sense code. It should add static/schema tests and run the mic stable-byte gate before any device work is considered.
