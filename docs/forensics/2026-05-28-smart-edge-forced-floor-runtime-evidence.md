---
abstract: "Runtime checkpoint for Smart Assist mode switching and EdgeMixer white-flood safety using forced confidence-floor harness evidence on K1 hardware."
---

# Smart Assist + EdgeMixer Forced-Floor Runtime Evidence

Date: 2026-05-28

## Scope

This checkpoint records a developer-harness proof that Smart Assist can drive a
real primary-mode switch under VPABB/VPABC final-byte capture, and that the
previous EdgeMixer secondary white-flood signature was not present in this run.

The initial checkpoint was not product tuning evidence: the Smart confidence
floor was forced to `0.050` to exercise the switching path under weak bench
audio.

Later runs moved the source default and runtime restore floor to `0.080`, then
completed the full build/upload/runtime matrix on both K1 devices. The main K1
was temporarily flashed with the harness image for VPABB/VPABC final-byte proof,
then restored to the production `k1_hardware` image.

## Evidence Tier

- `[FACT]` Harness K1 port: `/dev/tty.usbmodem101`.
- `[FACT]` Bench reference K1 port: `/dev/tty.usbmodem2101`.
- `[FACT]` Harness log:
  `docs/forensics/runtime-evidence/2026-05-28-k1-smart-edge-vpabb-context-forced-floor-v1.log`.
- `[FACT]` Production/reference AP log:
  `docs/forensics/runtime-evidence/2026-05-28-k1-bench-reference-production-context-forced-floor-v1.log`.
- `[FACT]` Parsed summary:
  `docs/forensics/runtime-evidence/2026-05-28-k1-smart-edge-context-forced-floor-v1-summary.json`.
- `[FACT]` Follow-up `0.080` floor harness log:
  `docs/forensics/runtime-evidence/2026-05-28-k1-smart-edge-vpabb-context-floor0080-v1.log`.
- `[FACT]` Follow-up `0.080` parsed summary:
  `docs/forensics/runtime-evidence/2026-05-28-k1-smart-edge-context-floor0080-v1-summary.json`.
- `[FACT]` Post-change product-floor v2 harness log:
  `docs/forensics/runtime-evidence/2026-05-28-k1-smart-edge-vpabb-context-product-floor-v2.log`.
- `[FACT]` Post-change product-floor v2 parsed summary:
  `docs/forensics/runtime-evidence/2026-05-28-k1-smart-edge-context-product-floor-v2-summary.json`.
- `[FACT]` Main K1 production reference-state log:
  `docs/forensics/runtime-evidence/2026-05-28-k1-main-production-smart-edge-reference-state-v2.log`.
- `[FACT]` Bench K1 production reference-state log:
  `docs/forensics/runtime-evidence/2026-05-28-k1-bench-reference-production-smart-edge-reference-state-v2.log`.
- `[FACT]` Full-test main production log:
  `docs/forensics/runtime-evidence/2026-05-28-k1-main-production-full-test-v1.log`.
- `[FACT]` Full-test bench production log:
  `docs/forensics/runtime-evidence/2026-05-28-k1-bench-production-full-test-v1.log`.
- `[FACT]` Full-test harness log:
  `docs/forensics/runtime-evidence/2026-05-28-k1-main-harness-full-test-v1.log`.
- `[FACT]` Full-test parsed summary:
  `docs/forensics/runtime-evidence/2026-05-28-k1-smart-edge-full-test-v1-summary.json`.
- `[FACT]` Final restored main production log:
  `docs/forensics/runtime-evidence/2026-05-28-k1-main-production-final-restore-v1.log`.
- `[FACT]` Final restored bench production log:
  `docs/forensics/runtime-evidence/2026-05-28-k1-bench-production-final-restore-v1.log`.
- `[FACT]` Final restored main parsed summary:
  `docs/forensics/runtime-evidence/2026-05-28-k1-smart-edge-full-test-final-main-restore-v1-summary.json`.
- `[FACT]` Final restored bench parsed summary:
  `docs/forensics/runtime-evidence/2026-05-28-k1-smart-edge-full-test-final-bench-restore-v1-summary.json`.

## Commands

```sh
python3 -B -m unittest discover -s tests
python3 scripts/regression-harness/smart_edge_runtime_capture.py --harness-port /dev/tty.usbmodem101 --harness-out docs/forensics/runtime-evidence/2026-05-28-k1-smart-edge-vpabb-context-forced-floor-v1.log --baud 230400 --settle 4.0 --smart-confidence-floor 0.050
python3 scripts/regression-harness/smart_edge_runtime_capture.py --production-port /dev/tty.usbmodem2101 --production-out docs/forensics/runtime-evidence/2026-05-28-k1-bench-reference-production-context-forced-floor-v1.log --baud 230400 --settle 4.0 --smart-confidence-floor 0.050
python3 scripts/regression-harness/analyse_smart_edge_runtime_capture.py docs/forensics/runtime-evidence/2026-05-28-k1-smart-edge-vpabb-context-forced-floor-v1.log docs/forensics/runtime-evidence/2026-05-28-k1-bench-reference-production-context-forced-floor-v1.log docs/forensics/runtime-evidence/2026-05-28-k1-smart-edge-context-forced-floor-v1-summary.json
python3 scripts/regression-harness/smart_edge_runtime_capture.py --harness-port /dev/tty.usbmodem101 --harness-out docs/forensics/runtime-evidence/2026-05-28-k1-smart-edge-vpabb-context-floor0080-v1.log --baud 230400 --settle 4.0 --smart-confidence-floor 0.080
python3 scripts/regression-harness/smart_edge_runtime_capture.py --production-port /dev/tty.usbmodem2101 --production-out docs/forensics/runtime-evidence/2026-05-28-k1-bench-reference-production-context-floor0080-v1.log --baud 230400 --settle 4.0 --smart-confidence-floor 0.080
python3 scripts/regression-harness/analyse_smart_edge_runtime_capture.py docs/forensics/runtime-evidence/2026-05-28-k1-smart-edge-vpabb-context-floor0080-v1.log docs/forensics/runtime-evidence/2026-05-28-k1-bench-reference-production-context-floor0080-v1.log docs/forensics/runtime-evidence/2026-05-28-k1-smart-edge-context-floor0080-v1-summary.json
python3 -B -m unittest discover -s tests
pio run -e k1_hardware_harness
pio run -e k1_hardware
pio run -e k1_bench_reference
pio run -e k1_hardware_harness -t upload --upload-port /dev/tty.usbmodem101
pio run -e k1_bench_reference -t upload --upload-port /dev/tty.usbmodem2101
python3 scripts/regression-harness/smart_edge_runtime_capture.py --harness-port /dev/tty.usbmodem101 --harness-out docs/forensics/runtime-evidence/2026-05-28-k1-smart-edge-vpabb-context-product-floor-v2.log --baud 230400 --settle 4.0
python3 scripts/regression-harness/smart_edge_runtime_capture.py --production-port /dev/tty.usbmodem2101 --production-out docs/forensics/runtime-evidence/2026-05-28-k1-bench-reference-production-context-product-floor-v2.log --baud 230400 --settle 4.0
python3 scripts/regression-harness/analyse_smart_edge_runtime_capture.py docs/forensics/runtime-evidence/2026-05-28-k1-smart-edge-vpabb-context-product-floor-v2.log docs/forensics/runtime-evidence/2026-05-28-k1-bench-reference-production-context-product-floor-v2.log docs/forensics/runtime-evidence/2026-05-28-k1-smart-edge-context-product-floor-v2-summary.json
python3 -B -m unittest discover -s tests
pio run -e k1_hardware
pio run -e k1_hardware_harness
pio run -e k1_bench_reference
pio run -e k1_hardware -t upload --upload-port /dev/tty.usbmodem101
pio run -e k1_bench_reference -t upload --upload-port /dev/tty.usbmodem2101
python3 scripts/regression-harness/smart_edge_runtime_capture.py --production-port /dev/tty.usbmodem101 --production-out docs/forensics/runtime-evidence/2026-05-28-k1-main-production-smart-edge-reference-state-v2.log --baud 230400 --settle 4.0
python3 scripts/regression-harness/smart_edge_runtime_capture.py --production-port /dev/tty.usbmodem2101 --production-out docs/forensics/runtime-evidence/2026-05-28-k1-bench-reference-production-smart-edge-reference-state-v2.log --baud 230400 --settle 4.0
python3 -B -m unittest discover -s tests
pio run -e k1_hardware
pio run -e k1_bench_reference
pio run -e k1_hardware_harness
pio run -e k1_hardware_trace_dev
pio run -e k1_hardware -t upload --upload-port /dev/tty.usbmodem101
pio run -e k1_bench_reference -t upload --upload-port /dev/tty.usbmodem2101
python3 scripts/regression-harness/smart_edge_runtime_capture.py --production-port /dev/tty.usbmodem101 --production-out docs/forensics/runtime-evidence/2026-05-28-k1-main-production-full-test-v1.log --baud 230400 --settle 4.0
python3 scripts/regression-harness/smart_edge_runtime_capture.py --production-port /dev/tty.usbmodem2101 --production-out docs/forensics/runtime-evidence/2026-05-28-k1-bench-production-full-test-v1.log --baud 230400 --settle 4.0
pio run -e k1_hardware_harness -t upload --upload-port /dev/tty.usbmodem101
python3 scripts/regression-harness/smart_edge_runtime_capture.py --harness-port /dev/tty.usbmodem101 --harness-out docs/forensics/runtime-evidence/2026-05-28-k1-main-harness-full-test-v1.log --baud 230400 --settle 4.0
python3 scripts/regression-harness/smart_edge_runtime_capture.py --production-port /dev/tty.usbmodem2101 --production-out docs/forensics/runtime-evidence/2026-05-28-k1-bench-production-full-test-reference-v1.log --baud 230400 --settle 4.0
python3 scripts/regression-harness/analyse_smart_edge_runtime_capture.py docs/forensics/runtime-evidence/2026-05-28-k1-main-harness-full-test-v1.log docs/forensics/runtime-evidence/2026-05-28-k1-bench-production-full-test-reference-v1.log docs/forensics/runtime-evidence/2026-05-28-k1-smart-edge-full-test-v1-summary.json
pio run -e k1_hardware -t upload --upload-port /dev/tty.usbmodem101
pio run -e k1_bench_reference -t upload --upload-port /dev/tty.usbmodem2101
python3 scripts/regression-harness/smart_edge_runtime_capture.py --production-port /dev/tty.usbmodem101 --production-out docs/forensics/runtime-evidence/2026-05-28-k1-main-production-final-restore-v1.log --baud 230400 --settle 4.0
python3 scripts/regression-harness/smart_edge_runtime_capture.py --production-port /dev/tty.usbmodem2101 --production-out docs/forensics/runtime-evidence/2026-05-28-k1-bench-production-final-restore-v1.log --baud 230400 --settle 4.0
python3 scripts/regression-harness/analyse_smart_edge_runtime_capture.py docs/forensics/runtime-evidence/2026-05-28-k1-main-harness-full-test-v1.log docs/forensics/runtime-evidence/2026-05-28-k1-main-production-final-restore-v1.log docs/forensics/runtime-evidence/2026-05-28-k1-smart-edge-full-test-final-main-restore-v1-summary.json
python3 scripts/regression-harness/analyse_smart_edge_runtime_capture.py docs/forensics/runtime-evidence/2026-05-28-k1-main-harness-full-test-v1.log docs/forensics/runtime-evidence/2026-05-28-k1-bench-production-final-restore-v1.log docs/forensics/runtime-evidence/2026-05-28-k1-smart-edge-full-test-final-bench-restore-v1-summary.json
```

## Results

- `[FACT]` Python tests passed: `67 tests OK`.
- `[FACT]` Harness capture completed: `1201` lines, `VPABB=146`,
  `VPAB=146`.
- `[FACT]` Bench reference capture completed: `612` lines, `AP=11`.
- `[FACT]` `visual_safety_failures` was empty.
- `[FACT]` Smart primary VPABB mode counts were `3:12` and `8:12`.
- `[FACT]` VPABC tail reported `primary_mode=8`, `primary_config_mode=3`,
  `secondary_mode=7`, `smart_enabled=1`, `hooks_enabled=1`,
  `manual_owner_active=0`, `edge_enabled=1`, `edge_mode=2`,
  `edge_strength_milli=350`, `edge_effective_strength_milli=386`.
- `[FACT]` Bench AP capture remained weak: `ap_max_raw.mean=509.09`,
  `ap_peak_scaled.max=0.186`.
- `[FACT]` Follow-up `0.080` floor run also switched: Smart primary VPABB
  mode counts were `3:12` and `8:12`.
- `[FACT]` Follow-up `0.080` floor run also had no visual safety failures.
- `[FACT]` Follow-up VPABC tail reported `primary_mode=8`,
  `primary_config_mode=3`, `secondary_mode=7`, `smart_enabled=1`,
  `hooks_enabled=1`, `manual_owner_active=0`, `edge_enabled=1`,
  `edge_mode=2`, `edge_strength_milli=350`,
  `edge_effective_strength_milli=352`.
- `[FACT]` Follow-up bench AP was weaker than the first forced-floor run:
  `ap_max_raw.mean=280.00`, `ap_peak_scaled.max=-0.141`.
- `[FACT]` Smart Director source default was changed from `0.62f` to `0.08f`.
- `[FACT]` Regression harness default and cleanup floor were changed to `0.080`.
- `[FACT]` Post-change tests passed: `68 tests OK`.
- `[FACT]` Post-change builds passed for `k1_hardware_harness`,
  `k1_hardware`, and `k1_bench_reference`.
- `[FACT]` Main K1 and bench K1 uploads exited successfully.
- `[FACT]` Post-change product-floor v2 run switched: Smart primary VPABB
  mode counts were `3:12` and `8:12`.
- `[FACT]` Post-change product-floor v2 run had no visual safety failures.
- `[FACT]` Post-change VPABC tail reported `primary_mode=8`,
  `primary_config_mode=3`, `secondary_mode=7`, `smart_enabled=1`,
  `hooks_enabled=1`, `manual_owner_active=0`, `edge_enabled=1`,
  `edge_mode=2`, `edge_strength_milli=350`,
  `edge_effective_strength_milli=361`.
- `[FACT]` Post-change restore tails reported `SMART_CONFIDENCE_FLOOR: 0.080`
  on both K1 devices.
- `[FACT]` Typed primary visual controls were added for `photons`, `chroma`,
  `mood`, `palette_mode`, and `palette_index` to avoid imprecise hotkey-only
  reference-state setup.
- `[FACT]` Final reference-state captures accepted `:mood=0.250`,
  `:palette_mode=on`, `:palette_index=29`, `:secondary_palette_mode=true`,
  and `:secondary_palette_index=24` on both devices.
- `[FACT]` Main K1 final production run reached `SMART_APPLIED_MODE: 8`,
  `SMART_SWITCHES_IN_WINDOW: 1`, `SMART_MANUAL_OWNER_ACTIVE: 0` during the
  active Smart window, then restored to `SMART_APPLIED_MODE: 3`, Smart off,
  Edge off, `SMART_CONFIDENCE_FLOOR: 0.080`.
- `[FACT]` Bench K1 final production run reached `SMART_APPLIED_MODE: 8`,
  `SMART_SWITCHES_IN_WINDOW: 1`, `SMART_MANUAL_OWNER_ACTIVE: 0` during the
  active Smart window, then restored to `SMART_APPLIED_MODE: 3`, Smart off,
  Edge off, `SMART_CONFIDENCE_FLOOR: 0.080`.
- `[FACT]` Final reference-state AP streams were live on both devices; main K1
  reached `max_raw=8491`, `peak_scaled=0.744`; bench K1 reached
  `max_raw=1365`, `peak_scaled=0.730`.

## Interpretation

- `[FACT]` Smart Assist mode switching is now hardware-proven at the final-byte
  evidence layer under a forced low confidence floor.
- `[FACT]` EdgeMixer did not reproduce the white-flood signature in this run.
- `[INFERENCE]` The earlier default-floor run did not switch because the bench
  audio confidence was below the product threshold, not because the mode switch
  path was dead.
- `[INFERENCE]` A Smart floor around `0.080` is enough to exercise mode
  switching under current bench conditions; the current `0.620` floor is too
  high for this evidence set.
- `[FACT]` Product-floor Smart switching is hardware-proven for the current
  bench stimulus at the final-byte evidence layer.
- `[HYPOTHESIS]` Captain video/visual judgement is still needed to decide
  whether the resulting mode switch timing is perceptually satisfying, too
  eager, or too conservative.
- `[FACT]` The main K1 is no longer left on the harness image; it was flashed
  with `k1_hardware` after VPABB evidence was collected.
- `[FACT]` Full-test host regression passed: `69 tests OK`.
- `[FACT]` Full-test build matrix passed for `k1_hardware`,
  `k1_bench_reference`, `k1_hardware_harness`, and compile-only
  `k1_hardware_trace_dev`. Trace-dev remains non-shippable.
- `[FACT]` Full-test production captures completed on both devices before the
  harness flash: main `662` lines / `AP=36`; bench `646` lines / `AP=20`.
- `[FACT]` Full-test harness capture completed on the main K1:
  `1225` lines, `VPABB=146`, `VPAB=146`.
- `[FACT]` Full-test VPABB/VPABC summary had no visual safety failures.
- `[FACT]` Full-test Smart switch path was checked and switched; primary
  Smart leg mode counts were `3:13` and `8:11`.
- `[FACT]` Full-test VPABC tail reported `primary_mode=8`,
  `primary_config_mode=3`, `secondary_mode=7`, `smart_enabled=1`,
  `hooks_enabled=1`, `manual_owner_active=0`, `edge_enabled=1`,
  `edge_mode=2`, `edge_strength_milli=350`,
  `edge_effective_strength_milli=350`.
- `[FACT]` Full-test VPAB record status reported captured frames with
  `dropped=0` and `overflowed=0`.
- `[FACT]` Final restored main production summary recorded `ap_rows=36`,
  `ap_peak_scaled.max=0.641`, and `ap_silence_rows=0`.
- `[FACT]` Final restored bench production summary recorded `ap_rows=20`,
  `ap_peak_scaled.max=1.001`, and `ap_silence_rows=0`.
- `[FACT]` Final restored production logs on both devices contain
  `#RESTORE safe_runtime_state`,
  `PALETTE: 29 (BlacK_Blue_Magenta_White_gp)`,
  `SECONDARY_PALETTE_INDEX: 24 (fire_gp)`, final
  `SMART_APPLIED_MODE: 3`, and final `EDGE_ENABLED: off`.

## Changelog

| Date | Change |
|---|---|
| 2026-05-28 | Added forced-floor runtime checkpoint after VPABB/VPABC capture on both K1 devices. |
| 2026-05-28 | Added `0.080` floor follow-up proving the switch path still triggers above the initial `0.050` forced floor. |
| 2026-05-28 | Recorded decision to move the Smart Director product default towards the evidence-backed `0.080` floor and require a post-change hardware capture. |
| 2026-05-28 | Added post-change build, upload, and product-floor v2 runtime evidence; restore now leaves the floor at `0.080`. |
| 2026-05-28 | Added typed primary visual serial controls, reflashed both K1s, and recorded final production reference-state evidence. |
| 2026-05-28 | Added full build/test/upload/harness/final-restore matrix and confirmed both devices finish on production-class firmware. |
