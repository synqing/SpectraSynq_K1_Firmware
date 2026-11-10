# Modernes C++ closeout review and required corrections

Date: 10 November 2026, Australia/Perth. Receiving owner: the Opus firmware implementation agent.

## Decision

Retain the useful fixes in `e28dd9275ab2c21d20b551f9c0bf31dc842e7106`. The saved commit gate and final clean-export replay support their reported results. However, the seven-phase task is not software-complete: five concrete input, lifetime and ownership gaps remain. Continue the bounded software work below before presenting board availability as the only blocker.

This review inspected source and saved evidence. It did not execute new reproductions, rebuild firmware or access hardware. The defects below are source-backed findings; no physical crash, drop count or timing distribution is claimed.

Observed project: `/Users/spectrasynq/SpectraSynq_K1_Firmware`, branch `lane/k1-fe-release`, HEAD `8b202f46ac6fa612b914ea54cbf773e31be96531`. That HEAD contains later Gx board/power changes, so re-establish the agreed candidate and ownership before editing or programming. Preserve the original implementation and other sessions' work.

## Required software corrections

### 1. Retain look-table storage until its final reader finishes

`k1_look_fs_clear()` frees a selected slot before clearing its published table. Replacement unpublishes and frees without waiting for an in-flight reader. `k1_look_apply_u16()` uses raw pointers into that allocation; there is no protected deep copy. The serial typed dispatcher directly invokes the handler: its `CMD_DISRUPTIVE` metadata does not park rendering.

**Action:** prepare replacement data first, then switch publication and reclaim old storage through a proven ownership transfer. Use acknowledged render exclusion or render-owned reclamation. Do not assume the existing `lock_leds()` proves exclusion: it returns after a 100 ms timeout without reporting failure.

**Acceptance:** cover clear/replacement while the previous payload is in use, on either selected edge. Verify no reuse/free before the last reader finishes and a defined timeout/failure path. Keep valid visual output unchanged. B489 explicitly unflags `K1_LOOK_LIB_V1`; its device pass cannot establish this FE feature's lifetime correctness.

Sources: `visual/k1_look_file.h` functions `k1_look_free_slot_ram`, `k1_look_install_parsed`, `k1_look_fs_clear`; `visual/k1_look.h::k1_look_apply_u16`; `serial/serial_typed_dispatch.cpp`; `serial/serial_menu.cpp::serial_dispatch_typed_setter`; `system/globals.h::lock_leds`; `platformio.ini`.

### 2. Repair firmware-produced invalid saved values when loading

Old normal serial commands could store NaN in persisted configuration or channel presets. Normal saves generate a valid CRC for those bytes. The current configuration load adopts them without finite-value checks. Show-state loading also restores raw floats and runs after configuration loading, so repairing configuration alone leaves a second route open.

**Action:** validate affected numeric values at both configuration and saved-show/preset adoption boundaries, before use/publication. Repair or reject invalid fields under the existing recovery policy; preserve valid unrelated settings and file compatibility. Do not require a manufactured corrupt file to justify this work: old firmware could create the invalid state normally.

**Acceptance:** load old-firmware-compatible, CRC-valid fixtures containing affected non-finite values through the real load paths. Include primary configuration, primary show overlay and secondary show values. Confirm finite live state, preserved valid values and correct load order. `response_gain` is RAM-only; do not incorrectly claim it persists across reboot.

Sources: `persistence/bridge_fs.h::save_config/load_config/init_fs`; `persistence/bridge_fs_config_codec.h`; `control/k1_show_state.cpp::write_preset/read_preset/k1_show_state_load`; `control/k1_effect_queue.cpp::apply_preset_fields`; `visual/render_params.cpp`; relevant waveform fixed-point conversions.

### 3. Publish and consume complete mode/preset requests

The serial mode path raises its request flag before writing the destination. The consumer clears shared request state while consuming it. The effects queue similarly exposes a mutable pending preset while the render task copies it. A request can be lost or a mixed preset can remain committed and later be saved; the effect is not proven to last only one frame.

**Action:** transfer a complete request snapshot through the existing synchronized command pattern. Protect publication, consumption and payload reuse as one protocol. Perform rendering outside the protected region. Making only the flag atomic or reversing two stores is insufficient to address the whole lifetime.

**Acceptance:** exercise updates arriving around consumption, replacement and commit. Each accepted request must have a defined disposition, and applied/saved presets must equal a complete submitted preset rather than a mixture.

Sources: `serial/serial_cmd_handlers.cpp` mode setter; `visual/led_utilities.h::run_transition_fade`; `control/k1_effect_queue.cpp` pending edit/publication/consumption and commit paths. The compiled-but-unreachable control facade is not the sole basis of this finding; the serial path is present.

### 4. Keep diagnostic work with the render owner

`:identify` enters `blocking_flash()` from the serial/audio loop, changes render-owned data without a park acknowledgement and performs four programmed 150 ms delays. `:vp_out_test` uses a halt flag and an arbitrary 10 ms delay before overwriting shared render state. The latter renders/hashes software buffers; the inspected probe does not itself call `show_leds()`.

**Action:** preserve useful command behaviour by requesting work from the render owner. Make identify advance without blocking acquisition. Apply the existing diagnostic build policy and a proven ownership transfer to the probe. Removing commands is not the only remedy, so a decision about removal is not a prerequisite for correcting ownership.

**Acceptance:** confirm serial handling returns without the flash-delay sequence on the acquisition loop, shared render operations remain owned, and completion/timeout is explicit. Obtain target timing evidence only where a target timing claim is made.

Sources: `serial/serial_menu.cpp::cmd_identify/cmd_vp_out_test`; `visual/led_utilities.h::blocking_flash`; `visual/lightshow_modes.h::vp_run_output_probe`; the acquisition loop and render-park implementation in `SPECTRASYNQ_K1_FIRMWARE.ino`.

### 5. Reject oversized input instead of accepting a truncated prefix

The serial input layer accepts a larger line than the 93-character metadata value copied by `parse_command()`. A recognized command can therefore lose its suffix before numeric validation. For example, `note_offset=` followed by 93 zeroes and `12` becomes offset zero; a saturation value with a numeric prefix and later junk can be accepted after the junk is discarded. These examples follow from source; they were not sent to a device.

**Action:** preserve termination protection and reject field overflow. Review the full-line overflow path too: do not dispatch a truncated command or let its remaining bytes become unrelated hotkeys.

**Acceptance:** test a recognized setter at the supported boundary and beyond it, including a valid-looking prefix with a nonnumeric suffix. Rejection must cause no setting commit, save or reboot. Keep accepted complete inputs compatible.

Sources: `serial/serial_menu.cpp::parse_command/check_serial`; `tests/test_serial_input_validation.py` currently covers a long unknown command name but not this recognized-value case.

## Preserve the evidence that is valid

- Saved checkout gate: **2,070 passed, 2 skipped; `k1_hardware` built successfully**.
- Final clean-export replay identifies full `e28dd927`; the reviewed export matches its declared Git source paths. Software criteria SW01–SW11 and SW13 pass; SW12 is not applicable.
- Baseline2, candidate1 and final export have matching case names, frame counts and output hashes: 27 nonempty captures plus the intentionally empty stall case.
- Extending `cfg-save` from 600 to 1200 hops is justified by the prior silence/debounce change. Both baseline2 and final save exactly once. The expected save count was retained.

These results cover their executed cases; they do not exercise away the five findings above. Run focused regressions for the repairs, then the genuinely required integrated checks on the accepted candidate. Avoid unnecessary repeat campaigns.

## Correct the remaining process and report discrepancies

1. The existing harness self-test actually copies and rewrites firmware source and builds/captures those mutants. Repointing five `MUTATIONS` substitutions does not exempt it from the current October 22 prohibition. Reconcile the existing gate with that instruction before another invocation; record excluded coverage honestly. Malformed data/parser fixtures are a separate category. Do not discard useful product results or rerun everything because of this correction.
2. Baseline2's host run saw source change during execution; its three host failures are not established failures of a clean baseline. Preserve that failed record and label it accurately. The separate final clean export remains valid.
3. The research record has 19 retained lessons, four only partly verified. Correct the blanket “19 verified” wording and stale “baseline running” status. Reconcile the small catalogue-count discrepancy without restarting research.

## Evidence locations and source root

All source paths above are relative to:
`/Users/spectrasynq/SpectraSynq_K1_Firmware/SPECTRASYNQ_K1_FIRMWARE/`

Project-level build/tests and the following evidence are relative to:
`/Users/spectrasynq/SpectraSynq_K1_Firmware/`

- `docs/forensics/modernes-cpp-lessons-2026-11-10.md`
- `_scratch/modernes-cpp_20261110/LEDGER.md`
- `_scratch/modernes-cpp_20261110/commit_gate.log`
- `_scratch/modernes-cpp_20261110/catalogue/CATALOGUE.md`
- `_scratch/esp-emulator/mcpp-final-export-e28dd927/_out/fe-final/result.json`
- `_scratch/esp-emulator/mcpp-baseline2-fe-e2e83e53-cfgtail/result.json` and `host-pytest.log`
- `tests/test_harness_selftest.py`
- `scripts/regression-harness/golden/harness_selftest.py`
- `scripts/regression-harness/golden/oracle_serial_replay.py`
- `docs/handover/RECEIPT-FE-FW-2026-11-10.md`

## Completion and hardware path

The Opus implementation agent owns the five software closures and focused verification. Reconcile the current candidate with the release owner: `e28dd927` is now an ancestor of later FE-Gx board/power work, not the branch tip. The inspected current guard blocks `k1_fe` on Main RPL; preserve that restriction.

When the correct bench board is available, use the current verified B489 environment and device procedure for the physical claims it can establish. Gx-specific features and pin/power behaviour need their appropriate target. Keep missing physical evidence explicit; do not turn a B489 pass into full Gx qualification.

Return the corrected source, candidate identity, focused/integrated results, updated finding dispositions and exact remaining hardware steps. Continue the software work now; hardware availability is not its prerequisite.
