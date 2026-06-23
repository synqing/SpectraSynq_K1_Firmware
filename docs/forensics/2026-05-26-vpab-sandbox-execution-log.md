---
abstract: "Execution log for the sandboxed SSA pass implementing and evaluating the Level 1 Visual-Memory Engine VPAB/Bloom proof path. Canonical firmware is not modified by this log; all implementation lanes run in isolated /tmp sandboxes."
---

# VPAB Sandbox Execution Log

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Canonical repo | `/Users/spectrasynq/SensoryBridge-main 9` |
| Canonical branch | `feat/gdft-harness` |
| Canonical HEAD | `8c1c0e0` |
| Build target | `k1_hardware`; harness target `k1_hardware_harness` |
| Mode | Sandboxed execution only. No serial, upload, commit, branch, tag, or canonical firmware edit. |
| Sandbox root | `/tmp/k1_vme_exec_20260526210423` |

## Doctrine Gate

Current truth:
: `feat/gdft-harness` at `8c1c0e0`; dirty tree contains existing docs/skill/workbench artefacts. Active PlatformIO default env is `k1_hardware`.

Change class:
: VP/LED-output probe scaffolding and visual-memory sandbox prototype. No canonical adoption in this pass.

Files/seams touched:
: Sandbox copies of `led_utilities.h`, `lightshow_modes.h`, `serial_menu.h`, `light_mode_bloom.cpp`, regression harness tooling, and optional docs/scripts.

Known breakage avoided:
: Current `vp_probe` and `frame_dump` are pre-output `CRGB16` instruments; they cannot prove final WS2812-byte equivalence. This pass avoids making CRGB16/LUT decisions from upstream hashes.

State ownership:
: Canonical source remains untouched. Each SSA lane owns one isolated sandbox and returns data/diffs only.

Runtime proof required:
: None claimed in this pass. Future canonical adoption will require build plus Captain-supplied serial/timing/video or physical A/B evidence.

Minimal edit plan:
: Implement Packet A VPAB final-byte probe scaffolding in a sandbox, implement Bloom compact-memory comparison in a sandbox, implement VPAB parser/gate tooling in a sandbox, then adversarially review false-pass risks.

Explicit non-goals:
: No global CRGB16 removal, no Pharap FixedPoints removal, no serial access, no calibration command, no upload, no default visual behaviour change, no canonical patch.

Stop conditions:
: Stop if a lane requires serial, cannot measure final bytes, mutates displayed output by default, introduces heap in render path, or crosses unrelated AP/audio/serial seams.

## SSA Lanes

| Lane | Agent | Sandbox | Scope |
|---|---|---|---|
| VPAB firmware scaffold | Einstein `019e6463-f9d7-7631-acf3-aa035ceacba1` | `/tmp/k1_vme_exec_20260526210423/vpab_impl` | Packet A final-byte probe scaffold, guarded, no output mutation. |
| Bloom shadow prototype | Banach `019e6464-327d-7362-ab14-7360bedca1d8` | `/tmp/k1_vme_exec_20260526210423/bloom_shadow` | Packet B current Bloom vs compact/RGB8 final-byte metrics. |
| VPAB parser/gate tooling | Meitner `019e6464-58a7-7692-8aef-6a7a8fb798b1` | `/tmp/k1_vme_exec_20260526210423/probe_tools` | Packet parser and threshold gate. |
| Adversarial proof review | Laplace `019e6464-7f1c-7ba0-b885-a73d7d1ab622` | `/tmp/k1_vme_exec_20260526210423/adversarial_review` | False-pass risks, missing metrics, stop conditions. |

## SSA Return Synthesis

### VPAB firmware scaffold

[FACT] Einstein produced a guarded Packet A probe in `/tmp/k1_vme_exec_20260526210423/vpab_impl`.

[FACT] Changed sandbox files: `SPECTRASYNQ_K1_FIRMWARE/constants.h`, `SPECTRASYNQ_K1_FIRMWARE/globals.h`, `SPECTRASYNQ_K1_FIRMWARE/led_utilities.h`, `SPECTRASYNQ_K1_FIRMWARE/serial_menu.h`, `platformio.ini`.

[FACT] Release default remains off through `ENABLE_VPAB_PROBE=0`; only the sandbox `k1_hardware_harness` env defines `-DENABLE_VPAB_PROBE=1`.

[FACT] Probe hook is after `quantize_color(CONFIG.TEMPORAL_DITHERING)` and reverse-order handling, before `FastLED.show()`, so it samples final `CRGB` bytes rather than upstream `CRGB16`.

[FACT] Packet A is `shadow=self`: candidate bytes are copied from the final output bytes and compared against themselves. It proves instrumentation placement and schema shape only; it does not prove a visual-memory replacement.

### Bloom shadow prototype

[FACT] Banach produced `scripts/regression-harness/bloom_visual_memory_probe.py` and `tools/bloom_visual_memory_probe_results.json` in `/tmp/k1_vme_exec_20260526210423/bloom_shadow`.

[FACT] The model snapshots Bloom history before display-only edge fade/mirror, then compares final 8-bit bytes with firmware-style temporal dither and gamma disabled.

[FACT] `compact_q0_16` and `compact_q8_8` stayed within the starting thresholds across the tested scenarios. The `rgb8_early_quantised` candidate failed materially, including severe tail/energy loss and centre-of-mass displacement.

[INFERENCE] Compact fractional visual-memory state remains a viable Level 1 exploration vector. Early RGB8 history replacement is not viable for Bloom-like trails.

### VPAB parser/gate tooling

[FACT] Meitner produced `scripts/regression-harness/vpab_gate.py`, `tests/test_vpab_gate.py`, and VPAB pass/fail fixtures in `/tmp/k1_vme_exec_20260526210423/probe_tools`.

[FACT] The parser expects final-byte packet fields including `scenario`, `mae8`, `p95_abs8`, `max_abs8`, `changed_pct`, energy, centre-of-mass, motion, and optional strict memory fields.

[FACT] The gate thresholds are intentionally Level 1 starting thresholds, not final perceptual acceptance criteria.

### Adversarial proof review

[FACT] Laplace identified the existing `VPO`/`FDUMP` probes as upstream instruments that cannot certify final WS2812-byte equivalence.

[FACT] The actual primary visible boundary includes brightness, clipping, incandescent/base-coat/UI/ambient transformations, scaling, temporal quantisation, reverse ordering, and FastLED output.

[FACT] High-risk false passes include pre-output comparisons, omitted dither phase, single-frame probes, aggregate-only metrics, misplaced Bloom history snapshots, and treating self-shadow packets as candidate evidence.

## Verification Performed

[FACT] Canonical contamination check: `ENABLE_VPAB_PROBE`, `VPAB,ver=1`, `vpab_gate`, and `bloom_visual_memory` do not appear in canonical firmware/tooling paths. The only canonical match is this execution log.

[FACT] Canonical untracked `scripts/regression-harness/__pycache__/` contains `gdft_check`, `parse_serial`, and `vp_bleed_check` bytecode only; no VPAB/Bloom files were found there.

[FACT] Parser unit tests passed in the sandbox:
`python3 -B -m unittest discover -s tests -p test_vpab_gate.py` -> 5 tests OK.

[FACT] Parser CLI behaved as expected:
`vpab_pass.log --strict-memory` exited 0, and `vpab_fail.log --strict-memory` exited 2 with threshold failures.

[FACT] Bloom harness was reproducible:
`python3 -B scripts/regression-harness/bloom_visual_memory_probe.py --json-out tools/bloom_visual_memory_probe_results.verify.json` produced JSON identical to the agent result by `diff -q`.

[FACT] VPAB firmware scaffold builds in the sandbox:
`pio run -e k1_hardware_harness` exited 0.

[FACT] Release env with the guarded scaffold also builds in the sandbox:
`pio run -e k1_hardware` exited 0.

[FACT] Both firmware builds retained the existing `system.h:48` volatile `++` warning. No upload, serial capture, runtime packet capture, or hardware proof was attempted.

## Promotion Review

Verdict:
: Do not promote the VPAB firmware scaffold as-is. Promote the idea and the measured seams, not this exact patch.

Blocking issues:

1. [FACT] Parser/schema mismatch: `vpab_gate.py` requires `scenario`, but the firmware packet scaffold does not emit `scenario=...`.
2. [FACT] `changed_pct` is firmware-side LED percentage, while the parser contract does not make that semantic explicit. Either rename to `changed_led_pct` or add a true changed-channel metric.
3. [FACT] `vpab_command()` calls `strcmp(command_data, ...)` before guarding null. If the command parser can pass null command data, this can crash.
4. [FACT] `trail_half_life_delta_frames=0` and `tail_integral_delta_pct=energy_delta_pct` are placeholders in `shadow=self`; they must not be accepted as candidate memory proof.
5. [FACT] Packet emission uses `USBSerial` and `ESP.getFreeHeap()` from the render-adjacent probe path. This is acceptable only while compile-gated to the harness and manually armed, not as default firmware behaviour.

Promotable pieces:

1. [FACT] Final-byte VPAB instrumentation belongs after primary/secondary quantisation and reverse-order handling, before `FastLED.show()`.
2. [FACT] Offline parser/gate tooling is useful once the firmware packet schema is aligned.
3. [FACT] Bloom compact-memory harness is useful as a sandbox regression tool, excluding `__pycache__`.
4. [INFERENCE] Compact fractional memory deserves the next experiment; early RGB8 history should be rejected for Bloom-like trails unless a new perception argument appears.

## Next Canonical Step

Patch Packet A in a small canonical candidate branch/sandbox only after addressing the blocking issues above:

1. Emit `scenario=self_shadow` and `shadow=self`.
2. Define `changed_pct` semantics, preferably `changed_led_pct` plus optional `changed_channel_pct`.
3. Null-guard `vpab_command()` before any string comparison.
4. Mark placeholder memory fields as absent for `shadow=self`, or emit explicit `memory_metrics=placeholder` and make the parser reject placeholders under `--strict-memory`.
5. Keep `ENABLE_VPAB_PROBE` default-off and harness-only.
6. Re-run `pio run -e k1_hardware_harness`, `pio run -e k1_hardware`, parser tests, and then wait for Captain-supplied runtime capture before claiming evidence.

## Phase 2 Canonical Candidate Adoption

[FACT] The Packet A candidate has now been adopted into canonical source as guarded instrumentation, not as visual behaviour.

Files changed:

- `SPECTRASYNQ_K1_FIRMWARE/constants.h`
- `SPECTRASYNQ_K1_FIRMWARE/globals.h`
- `SPECTRASYNQ_K1_FIRMWARE/led_utilities.h`
- `SPECTRASYNQ_K1_FIRMWARE/serial_menu.h`
- `platformio.ini`
- `scripts/regression-harness/vpab_gate.py`
- `tests/test_vpab_gate.py`
- `tests/fixtures/vpab_pass.log`
- `tests/fixtures/vpab_fail.log`

Schema fixes applied:

1. [FACT] Firmware emits `scenario=self_shadow`, `shadow=self`, and `memory_metrics=absent`.
2. [FACT] Firmware emits explicit `changed_led_pct` and `changed_channel_pct`; the ambiguous `changed_pct` field is not used.
3. [FACT] `vpab_command()` guards null/empty `command_data` before string comparison.
4. [FACT] Self-shadow packets omit trail/tail proof fields; the parser rejects `memory_metrics=absent` under `--strict-memory`.
5. [FACT] `ENABLE_VPAB_PROBE` defaults to `0` and is enabled only in `k1_hardware_harness`.

Verification:

- [FACT] `python3 -B -m unittest discover -s tests -p test_vpab_gate.py` -> 6 tests OK.
- [FACT] `python3 -B scripts/regression-harness/vpab_gate.py tests/fixtures/vpab_pass.log --strict-memory` -> exit 0.
- [FACT] `python3 -B scripts/regression-harness/vpab_gate.py tests/fixtures/vpab_fail.log --strict-memory` -> exit 2 with expected threshold failures.
- [FACT] `pio run -e k1_hardware_harness` -> exit 0.
- [FACT] `pio run -e k1_hardware` -> exit 0.

Warnings/limits:

- [FACT] Builds retained existing warnings in `system.h:48`; harness build also showed a current `gdft_harness.h` IRAM section warning from the dirty GDFT harness lane.
- [FACT] No upload, serial capture, runtime packet capture, hardware video, or physical A/B proof was attempted.
- [INFERENCE] Packet A is now ready for Captain-run runtime capture, but it still cannot prove compact visual-memory equivalence until a real candidate shadow renderer is added.

## Phase 3 K1 Runtime Capture

[FACT] Captain explicitly made K1 available on `/dev/cu.usbmodem1101`; the device probed as ESP32-S3 USB JTAG/serial unit `B4:3A:45:A5:87:F8`.

[FACT] Harness upload was performed:
`pio run -e k1_hardware_harness -t upload --upload-port /dev/cu.usbmodem1101` -> exit 0.

[FACT] First serial attempt used raw command text without the required `:` command-mode prefix. The firmware correctly treated those bytes as immediate hotkeys, causing runtime-only knob/stream changes. Evidence: `docs/forensics/runtime-evidence/2026-05-26-vpab-usbmodem1101.log`. Further raw input was stopped.

[FACT] Source inspection showed legacy command mode is entered by `:` in `check_serial()`. Second capture used colon-framed commands only.

Runtime evidence files:

- `docs/forensics/runtime-evidence/2026-05-26-vpab-usbmodem1101-colon.log`
- `docs/forensics/runtime-evidence/2026-05-26-vpab-usbmodem1101-colon.vpab.json`
- `docs/forensics/runtime-evidence/2026-05-26-vpab-usbmodem1101-colon.strict.json`
- `docs/forensics/runtime-evidence/2026-05-26-vpab-usbmodem1101-cleanup.log`

Capture commands:

- `:stop`
- `:ap_stream=off`
- `:vp_stream=off`
- `:vpab=stop`
- `:vp_perf=reset`
- `:vp_perf=start`
- `:vpab=status`
- `:vpab=once`
- `:vpab=start,30`
- `:vpab=stop`
- `:vp_perf=stop`
- `:stop`

Results:

- [FACT] Runtime capture produced 50 `VPAB` rows and 8 `VPF` rows.
- [FACT] Self-shadow byte-equivalence metrics were clean across all 50 VPAB rows: `mae8=0`, `p95_abs8=0`, `max_abs8=0`, `changed_led_pct=0`, `changed_channel_pct=0`, and `com_delta_leds=0`.
- [FACT] Non-strict VPAB gate failed: `2/50 records passed; 66 failures; 100 warnings`.
- [FACT] Failure metrics were runtime-only: 48 `over` failures and 18 `render_us` failures.
- [FACT] `render_us` range in VPAB rows was 887-2120 us; `frame_us` range was 3905-4029 us; `dropped=0` throughout.
- [FACT] Strict-memory gate failed by design: self-shadow packets emit `memory_metrics=absent`, so no trail/tail candidate proof is accepted.
- [FACT] Cleanup sent colon-framed `:stop` and `:reset`; device rebooted with `RTC_SW_CPU_RST`.

Runtime verdict:

- [FACT] Packet A final-byte capture path works on hardware and emits parseable primary/secondary final-byte packets.
- [FACT] Packet A self-shadow proves instrumentation placement and byte identity only; it does not prove compact visual-memory equivalence.
- [FACT] The full Level 1 gate is not green under live capture because runtime budget counters tripped while the probe/perf harness was active.
- [INFERENCE] The runtime failures are compatible with serial-heavy diagnostic overhead and/or the current dirty GDFT harness lane, but they must be treated as real evidence until isolated.

## Phase 4 K1 Runtime Capture Rerun

[FACT] Captain requested the process be run again after the `:` command-parser requirement was identified.

[FACT] The rerun reconfirmed `/dev/cu.usbmodem1101` as the intended ESP32-S3 USB JTAG/serial unit `B4:3A:45:A5:87:F8`. A second ESP32-S3 device was present at `/dev/cu.usbmodem12201` and was not used.

[FACT] `lsof /dev/cu.usbmodem1101 /dev/tty.usbmodem1101` showed no process holding the intended port before the rerun.

[FACT] The rerun used colon-framed command-parser input only. No raw hotkey bytes were intentionally sent.

Runtime evidence files:

- `docs/forensics/runtime-evidence/2026-05-26-vpab-usbmodem1101-rerun-colon.log`
- `docs/forensics/runtime-evidence/2026-05-26-vpab-usbmodem1101-rerun-colon.vpab.json`
- `docs/forensics/runtime-evidence/2026-05-26-vpab-usbmodem1101-rerun-colon.strict.json`

Capture commands:

- `:stop`
- `:ap_stream=off`
- `:vp_stream=off`
- `:vpab=stop`
- `:vp_perf=reset`
- `:vp_perf=start`
- `:vpab=status`
- `:vpab=once`
- `:vpab=start,60`
- `:vpab=stop`
- `:vp_perf=stop`
- `:stop`

Results:

- [FACT] Runtime capture produced 38 `VPAB` rows and 10 `VPF` rows.
- [FACT] Self-shadow byte-equivalence metrics were clean across all 38 VPAB rows: `mae8=0`, `p95_abs8=0`, `max_abs8=0`, `changed_led_pct=0`, `changed_channel_pct=0`, and `com_delta_leds=0`.
- [FACT] Non-strict VPAB gate failed: `0/38 records passed; 56 failures; 76 warnings`.
- [FACT] Failure metrics were runtime-only: 20 `render_us` failures and 36 `over` failures.
- [FACT] `render_us` range in VPAB rows was 948-2123 us; `frame_us` range was 3934-3996 us; `dropped=0` throughout.
- [FACT] Strict-memory gate failed by design: self-shadow packets emit `memory_metrics=absent`, producing 114 strict-memory issues and no accepted trail/tail candidate proof.

Rerun verdict:

- [FACT] The corrected rerun was not a serial parser failure. The command transcript shows the `:` command-mode path was used end to end.
- [FACT] Packet A final-byte capture remains valid for self-shadow byte identity and instrumentation placement.
- [FACT] The Level 1 runtime gate still is not green because the live harness exceeded the render-budget and `over` thresholds while active.
- [INFERENCE] The next isolation step is not another parser rerun. It is a runtime-budget isolation pass that separates VPAB serial emission cost, VP perf collection cost, and the current dirty GDFT harness lane before any Level 1 acceptance claim.

## Phase 5 Diagnostic Substrate Hardening

[FACT] A primary-channel blackout during the diagnostic lane was isolated to persisted config, not the diagnostic substrate. Pre-erase stage probing showed nonzero primary render/brightness energy followed by zero final output; the runtime dump had `CONFIG.BASE_COAT: 1`. Full flash erase reset `CONFIG.BASE_COAT: 0`, and primary final-byte energy returned. The base-coat render path is now fail-closed when `CONFIG.BASE_COAT_INTENSITY <= 0.0f`, and `cmd_dump()` prints `CONFIG.BASE_COAT_INTENSITY` so this state is visible in future evidence.

[FACT] Read-only SSA review found three harness blockers:

1. Self-shadow rows could pass the default VPAB gate as if they were visual-memory proof.
2. `VPAB_RECORDS` / `VPAB_DUMP` diagnostic drop and overflow summaries were ignored by the parser.
3. Diagnostic pool state was shared between the serial command path and render task without a critical section.

[FACT] Fixes applied:

- `scripts/regression-harness/vpab_gate.py` now treats self-shadow / `memory_metrics=absent` rows as instrumentation smoke unless `--allow-self-shadow-smoke` is explicitly supplied.
- `vpab_gate.py` now parses `VPAB_RECORDS:` and `VPAB_DUMP:` summaries and fails on diagnostic `dropped`, `corrupt`, or `overflowed` values.
- `vpab_gate.py` now preserves runtime failures even when strict-memory validation issues exist on the same row.
- `diagnostic_capture.cpp` now protects pool state with a `portMUX_TYPE` critical section and exposes `diag_capture_can_push()` so VPAB can skip expensive payload construction after the pool is full.
- `vpab_capture.cpp` now uses file-scope static scratch payloads instead of large render-path stack payloads.
- Temporary primary stage-energy probes (`pre_energy`, `brightness_energy`, `source_energy`, `scaled_energy`, `final_energy`) were removed from VPAB hot-path capture.

[FACT] Host and build verification after hardening:

- `python3 -B -m unittest discover -s tests -p test_vpab_gate.py` -> 10 tests OK.
- `python3 -B -m unittest discover -s tests -p test_diag_capture_static.py` -> 3 tests OK.
- `pio run -e k1_hardware` -> exit 0; existing `system.h:48` volatile `++` warning remains.
- `pio run -e k1_hardware_harness` -> exit 0; existing `system.h:48` warning and GDFT harness IRAM section warning remain.

[FACT] Saved runtime log re-parsed with the hardened gate:

- Default proof gate: `docs/forensics/runtime-evidence/2026-05-26-vpab-deferred-diag-usbmodem1101-clean.hardened.vpab.json` -> `0/60 records passed; 60 issue(s); 24 failure(s); 120 warning(s)`.
- Smoke-only gate: `docs/forensics/runtime-evidence/2026-05-26-vpab-deferred-diag-usbmodem1101-clean.smoke.vpab.json` -> `36/60 records passed; 0 issue(s); 24 failure(s); 120 warning(s)`.
- Strict-memory gate: `docs/forensics/runtime-evidence/2026-05-26-vpab-deferred-diag-usbmodem1101-clean.hardened.strict.json` -> `0/60 records passed; 240 issue(s); 24 failure(s); 0 warning(s)`.
- The remaining smoke-mode failures are `render_us` only. Self-shadow byte identity remains instrumentation evidence only, not visual-memory proof.

Phase 5 verdict:

- [FACT] Release/harness builds and host gates are green after the hardening patch.
- [FACT] The lane remains NO-GO for Phase C/general telemetry expansion until a fresh K1 runtime matrix proves metrics/bytes capture with the hardened build and resolves the remaining `render_us` failures.
- [INFERENCE] The next useful hardware run is a narrow runtime-budget isolation pass: baseline VP perf, metrics capture without dump, bytes capture without dump, deferred dump after stop, all colon-framed on `/dev/cu.usbmodem1101`.

## Phase 6 Hardened K1 Runtime Matrix

[FACT] The hardened harness was uploaded to K1 on `/dev/cu.usbmodem1101`:

`pio run -e k1_hardware_harness -t upload --upload-port /dev/cu.usbmodem1101` -> exit 0.

[FACT] A repeatable runtime matrix script was added at `scripts/regression-harness/vpab_runtime_matrix.py`. It sends only colon-framed commands and does not call calibration or silence-window commands.

Runtime evidence files:

- `docs/forensics/runtime-evidence/2026-05-26-vpab-hardened-runtime-matrix.log`
- `docs/forensics/runtime-evidence/2026-05-26-vpab-hardened-runtime-matrix.proof.vpab.json`
- `docs/forensics/runtime-evidence/2026-05-26-vpab-hardened-runtime-matrix.smoke.vpab.json`
- `docs/forensics/runtime-evidence/2026-05-26-vpab-hardened-runtime-matrix.strict.vpab.json`

Runtime command:

`python3 -B scripts/regression-harness/vpab_runtime_matrix.py /dev/cu.usbmodem1101 docs/forensics/runtime-evidence/2026-05-26-vpab-hardened-runtime-matrix.log --settle 5 --baseline-seconds 4 --metrics-seconds 6 --bytes-seconds 6` -> exit 0.

Capture summary:

- [FACT] Transcript captured 229 lines, 56 `VPAB` rows, and 21 `VPF` rows.
- [FACT] Baseline, metrics, and bytes windows used only colon-framed commands.
- [FACT] `VPAB,` rows appeared during deferred `:vpab=dump` sections, not during the active capture waits.
- [FACT] Metrics capture summary: `captured=38 dropped=0 high_water=38 overflowed=0`.
- [FACT] Bytes capture summary: `captured=18 dropped=0 high_water=18 overflowed=0`.
- [FACT] Final `:diag=status`: `count=18 capacity=64 high_water=18`, `captured=18 dropped=0 corrupt=0 overflowed=0`, `payload_max=512 storage=34048`.
- [FACT] `VPF` summaries reported `over=0 dropped=0` throughout the runtime matrix.

Gate results:

- [FACT] Proof gate: `0/56 records passed; 56 issue(s); 38 failure(s); 112 warning(s)`.
- [FACT] Smoke gate: `18/56 records passed; 0 issue(s); 38 failure(s); 112 warning(s)`.
- [FACT] Strict-memory gate: `0/56 records passed; 224 issue(s); 38 failure(s); 0 warning(s)`.
- [FACT] All 38 gate failures are `render_us`.
- [FACT] By deferred section, metrics rows had `render_us` range `1172..3310` with 26 render failures; bytes rows had `render_us` range `1277..3302` with 12 render failures.
- [FACT] Bytes-mode quant telemetry is now sane in the fresh run: bytes rows had `quant_us` range `53..109`. This clears the earlier suspect secondary `quant_us` values from the pre-hardened log.

Phase 6 verdict:

- [FACT] Deferred drain is working: active capture windows do not serial-spam `VPAB,` rows, and diagnostic pool drop/overflow counters stayed zero.
- [FACT] Packet A remains smoke/instrumentation proof only; self-shadow rows are intentionally rejected by the default proof gate.
- [FACT] Runtime still remains NO-GO for Level 1 acceptance and Phase C expansion because the current gate still reports `render_us` failures.
- [INFERENCE] The next debugging target is the meaning/source of `vp_render_us_last` versus VPF `frame_us/over`. Current evidence shows `render_us` trips while total VPF frame over-budget stays zero, so either the gate threshold is measuring the wrong aggregate or the firmware is reporting a render subtotal that needs stage-level isolation.

## Phase 7 VP Perf Start-Race Fix And Re-Run

[FACT] Source inspection found a VP perf measurement race: `vp_perf=start` is handled on the serial/control loop while the LED task may already be mid-stage. Several stage timers set their start timestamp to `0` when `vp_perf.running` was false, then recorded `esp_timer_get_time() - 0` if `vp_perf.running` became true before the stage ended. This produced the previous multi-second VPF maxima.

[FACT] Fix applied: stage records now require both `vp_perf.running` and a nonzero stage start timestamp before recording elapsed time. Affected stages:

- audio acquisition, VU, and GDFT in `SPECTRASYNQ_K1_FIRMWARE.ino`.
- LED smooth/primary/secondary render in `SPECTRASYNQ_K1_FIRMWARE.ino`.
- primary prep, show, and secondary prep in `led_utilities.h`.

[FACT] Verification after the perf-race patch:

- `python3 -B -m unittest discover -s tests -p test_vpab_gate.py` -> 10 tests OK.
- `python3 -B -m unittest discover -s tests -p test_diag_capture_static.py` -> 3 tests OK.
- `pio run -e k1_hardware` -> exit 0; existing `system.h:48` volatile `++` warning remains.
- `pio run -e k1_hardware_harness` -> exit 0; existing `system.h:48` and GDFT harness IRAM warnings remain.
- `pio run -e k1_hardware_harness -t upload --upload-port /dev/cu.usbmodem1101` -> exit 0.

Runtime evidence files:

- `docs/forensics/runtime-evidence/2026-05-26-vpab-hardened-runtime-matrix-perf-race-fix.log`
- `docs/forensics/runtime-evidence/2026-05-26-vpab-hardened-runtime-matrix-perf-race-fix.proof.vpab.json`
- `docs/forensics/runtime-evidence/2026-05-26-vpab-hardened-runtime-matrix-perf-race-fix.smoke.vpab.json`
- `docs/forensics/runtime-evidence/2026-05-26-vpab-hardened-runtime-matrix-perf-race-fix.strict.vpab.json`

Runtime result:

- [FACT] Transcript captured 229 lines, 56 `VPAB` rows, and 21 `VPF` rows.
- [FACT] Diagnostic pool stayed clean: metrics `captured=38 dropped=0 high_water=38 overflowed=0`; bytes `captured=18 dropped=0 high_water=18 overflowed=0`; final diag `captured=18 dropped=0 corrupt=0 overflowed=0`.
- [FACT] `VPF` no longer contains the earlier multi-second bogus stage timings. Example baseline post-fix `pri_render_us=807/1757`, `sec_render_us=990/2370`, `frame_us=3831/6065`, `over=0`, `dropped=0`.
- [FACT] `VPF` still reports `over=0 dropped=0` throughout the matrix.
- [FACT] Proof gate: `0/56 records passed; 56 issue(s); 40 failure(s); 112 warning(s)`.
- [FACT] Smoke gate: `16/56 records passed; 0 issue(s); 40 failure(s); 112 warning(s)`.
- [FACT] Strict-memory gate: `0/56 records passed; 224 issue(s); 40 failure(s); 0 warning(s)`.
- [FACT] All 40 gate failures are `render_us`.
- [FACT] Metrics rows had `render_us` range `1429..2322`, `frame_us` range `3855..3933`, and 32/38 `render_us` failures.
- [FACT] Bytes rows had `render_us` range `1238..3204`, `frame_us` range `3815..3876`, and 8/18 `render_us` failures.

Phase 7 interpretation:

- [FACT] The original VPF maxima were measurement artefacts from starting perf mid-frame; that specific defect is fixed.
- [FACT] The remaining `render_us` failures are not caused by serial drain and are not measuring `vpab_capture_tick()` directly: `vp_render_us_last` is set in `led_thread()` before `show_leds()`, while `vpab_capture_tick()` runs inside `show_leds()` after quantisation/reverse.
- [FACT] The current `render_us` field measures the pre-show visual-pipeline aggregate: smoothing, primary render, secondary render, render-state snapshot/restore, and surrounding overhead before display transform.
- [INFERENCE] The VPAB diagnostic substrate is no longer the primary runtime suspect. The remaining decision is whether the Level 1 gate should hold the whole dual-channel pre-show aggregate to `<= 2.0ms`, or whether it should gate diagnostic overhead with `frame_us/over/dropped` and separately track visual-pipeline render budget as a baseline issue.

## Changelog

| Date | Change |
|---|---|
| 2026-05-26 | Initial execution log and lane dispatch record. |
| 2026-05-26 | Added SSA synthesis, verification results, promotion review, and next canonical action. |
| 2026-05-26 | Added Phase 2 canonical Packet A candidate adoption and verification record. |
| 2026-05-26 | Added Phase 3 K1 runtime capture evidence, parser results, and cleanup reboot record. |
| 2026-05-26 | Added Phase 4 colon-framed K1 runtime rerun evidence and parser results. |
| 2026-05-26 | Added Phase 5 diagnostic hardening, hardened gate re-parse results, and current NO-GO verdict for Phase C expansion. |
| 2026-05-26 | Added Phase 6 hardened K1 runtime matrix evidence and remaining render_us blocker. |
| 2026-05-26 | Added Phase 7 VP perf start-race fix, post-fix runtime matrix, and interpretation of remaining render_us failures. |
