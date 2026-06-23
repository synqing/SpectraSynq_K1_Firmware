# VPML Host Workbench Audit - 2026-06-10

Task ID: `VPML-HOST-WORKBENCH-AUDIT`

## Verdict

`NOT_VERIFIED` for any claim that VPML has a host-side compiler or live parameter editor today.

The smallest credible implementation is a local Python workbench that centralises the existing fixed built-in registry, validates a host-local run plan, and routes all device writes through the current USB CDC live runner/session functions. A dashboard that only renders evidence, or a parameter editor whose values are not consumed by `vpml_run_console.run_vpml_session()` / `vpml_live_runner.run_capture_transport()`, is cosmetic and should not be promoted as a real VPML workbench.

## Sources Read

- `.claude/CLAUDE.md`, `docs/spec-index.md`, `.claude/handoff.md`
- `docs/protocol/k1-ws-contract.yaml`, `docs/protocol/k1-rest-contract.yaml`
- Missing at this checkout root: `firmware-v3/docs/reference/codebase-map.md`, `firmware-v3/docs/reference/fsm-reference.md`
- `scripts/regression-harness/vpml_live_runner.py`
- `scripts/regression-harness/vpml_run_console.py`
- `scripts/regression-harness/vpml_run_console_server.py` (untracked)
- `scripts/regression-harness/vpml_host_surface.py`
- `scripts/regression-harness/vpml_evidence_page.py`
- `scripts/regression-harness/vpml_runtime_summary.py`
- Read-only source confirmation only: `SPECTRASYNQ_K1_FIRMWARE/diag/vp_motion_lab.h`, `SPECTRASYNQ_K1_FIRMWARE/visual/led_utilities.h`, `SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h`

## Source Facts

- `vpml_live_runner.py` is explicitly the live USB serial primitive: it scans ports, verifies chip identity, sends typed VPML built-in commands, drains VPAB K1DF frames, and writes evidence; it explicitly does not compile programmes, upload runtime code, use raw receive, AP, REST, or K1 WebSocket control (`scripts/regression-harness/vpml_live_runner.py:2-9`).
- `vpml_live_runner.py` only knows two programmes, both mapped to typed `:vpml=play_builtin,...` commands (`scripts/regression-harness/vpml_live_runner.py:49-58`).
- `vpml_live_runner.SerialTransport.command()` resets the input buffer, writes a colon-framed command plus newline, flushes, and reads serial lines (`scripts/regression-harness/vpml_live_runner.py:97-117`).
- `vpml_live_runner.validate_command()` rejects non-colon commands and blocks compile/upload/raw receive/factory/erase/restore/cal/wifi/websocket fragments (`scripts/regression-harness/vpml_live_runner.py:206-212`).
- `vpml_live_runner.run_capture_transport()` is the cleanest direct device-command sequence: chip identity, status, stop/reset VPAB and VP perf, play built-in, start VP perf, start VPAB bytes, wait, stop, drain `:vpab=frames`, stop VPML, then write raw/frame/gate/summary artefacts (`scripts/regression-harness/vpml_live_runner.py:324-409`).
- `vpml_run_console.py` has the same fixed built-in boundary and no compile/upload/raw/AP/REST/WebSocket path (`scripts/regression-harness/vpml_run_console.py:1-7`, `scripts/regression-harness/vpml_run_console.py:34-49`).
- `vpml_run_console.run_vpml_session()` is a real command path, not a report generator: it opens serial, sends `:version`, `:chip_id`, `:vpml=status`, resets capture/perf surfaces, sends `:vpml=play_builtin,<programme>`, starts `:vp_perf` and `:vpab`, drains `:vpab=frames`, and stops VPML (`scripts/regression-harness/vpml_run_console.py:227-403`).
- `vpml_run_console.write_capture_outputs()` writes raw logs, frames logs, frame-gate JSON, and VPML runtime summary JSON using `vpab_frame_gate.evaluate_text()` and `vpml_runtime_summary.evaluate_text()` (`scripts/regression-harness/vpml_run_console.py:406-449`).
- `vpml_run_console.refresh_dashboard()` only refreshes evidence JSON/HTML from local files; by itself it is not a live control path (`scripts/regression-harness/vpml_run_console.py:452-459`).
- `vpml_run_console_server.py` already implements the smallest local dashboard spine: `POST /run` parses the form, calls `vpml_run_console.run_vpml_session()`, writes capture outputs, refreshes the dashboard, and renders the result (`scripts/regression-harness/vpml_run_console_server.py:117-176`, `scripts/regression-harness/vpml_run_console_server.py:587-609`).
- The server is loopback-only by default and rejects non-loopback binds unless explicitly overridden (`scripts/regression-harness/vpml_run_console_server.py:21-25`, `scripts/regression-harness/vpml_run_console_server.py:110-114`, `scripts/regression-harness/vpml_run_console_server.py:622-643`).
- `vpml_host_surface.py` is not a live workbench. It is a file-backed surface model that explicitly does not scan devices, open K1 ports, upload programmes, compile authoring syntax, or use AP/REST/WebSocket control (`scripts/regression-harness/vpml_host_surface.py:1-7`).
- `vpml_host_surface.py` already models the correct future controls as requiring `vpml_live_runner` commands, and its global constraints say fixed built-ins only, no host compiler, no raw receive, no AP/REST/WebSocket control, and no visual acceptance without Captain review (`scripts/regression-harness/vpml_host_surface.py:79-120`, `scripts/regression-harness/vpml_host_surface.py:250-273`).
- `vpml_evidence_page.py` is evidence-only: it reads local artefacts, derives byte/motion summaries, and explicitly does not open serial, upload, compile authoring syntax, or claim visual acceptance (`scripts/regression-harness/vpml_evidence_page.py:1-8`).
- `vpml_evidence_page.PROGRAMME_METADATA` duplicates the same two fixed built-ins and play commands (`scripts/regression-harness/vpml_evidence_page.py:49-66`), then locks compile/upload/raw receive behind missing protocol readiness evidence (`scripts/regression-harness/vpml_evidence_page.py:674-701`).
- `vpml_runtime_summary.py` proves byte transport/final-byte coverage only and explicitly is not an eyes-on visual acceptance gate (`scripts/regression-harness/vpml_runtime_summary.py:1-7`).
- Firmware read-only confirmation matches the host boundary: VPML firmware declares fixed built-ins only, no arbitrary runtime code, no programme transport, no persistence, no AP/REST/Tab5/wireless surface (`SPECTRASYNQ_K1_FIRMWARE/diag/vp_motion_lab.h:1-14`).
- Firmware `vpml_command()` accepts only `status`, `play_builtin,intro_bounce`, `play_builtin,intro_bounce_loop`, and `stop`; unsupported command data returns false (`SPECTRASYNQ_K1_FIRMWARE/diag/vp_motion_lab.h:172-190`), and serial dispatch only routes the `vpml` command behind `ENABLE_VP_MOTION_LAB` (`SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h:3112-3118`).
- Firmware has `VPMLRenderParams` and mutable/default accessors (`SPECTRASYNQ_K1_FIRMWARE/visual/led_utilities.h:1126-1187`), but the audited command surface exposes no serial setter for those params. A host parameter editor cannot affect live K1 output without a new firmware command surface, which is out of scope for this audit.
- K1 REST is not implemented for this control slice; the contract says Tab5 control uses the AP-only WebSocket contract and not to add REST controls unless a future feature requires them (`docs/protocol/k1-rest-contract.yaml:1-8`). This audit is about a host-local HTTP dashboard, not K1 REST.

## Smallest Implementation Shape

1. `scripts/regression-harness/vpml_programmes.py`
   - Single source of truth for programme metadata currently duplicated in `vpml_live_runner.PROGRAMMES`, `vpml_run_console.PROGRAMMES`, and `vpml_evidence_page.PROGRAMME_METADATA`.
   - Proposed records: `id`, `label`, `frames`, `default_every`, `play_command`, `fail_on_dark_sample`, `enabled`, `notes`.
   - This is the first file to add; without it the dashboard/compiler/editor can drift from the only commands the runner can actually send.

2. `scripts/regression-harness/vpml_plan.py`
   - A validator/plan compiler, not a runtime-code compiler.
   - Proposed functions:
     - `compile_run_plan(payload: Mapping[str, Any]) -> VPMLRunPlan`
     - `validate_capture_params(seconds, every, baud, expected_chip, port) -> CaptureParams`
     - `unsupported_parameter_errors(payload) -> list[str]`
   - Output should be limited to the current real control fields: programme id, port, baud, expected chip, capture seconds, capture cadence, read windows, and evidence/dashboard dirs.
   - It must reject colour/width/phase/render-param edits as `unsupported_parameter` until firmware exposes and proves a setter command.

3. `scripts/regression-harness/vpml_live_runner.py`
   - Keep this as the lowest-level command transport for scan/identify/status/play/stop/capture.
   - Any implementation endpoint that claims to send device commands should call `identify_transport()`, `run_status_transport()`, `run_simple_command_transport()`, or `run_capture_transport()` rather than rebuilding command strings in the server.

4. `scripts/regression-harness/vpml_run_console.py`
   - Keep this as the full-session run/capture/evidence writer, or refactor it to consume `VPMLRunPlan`.
   - `run_vpml_session()` plus `write_capture_outputs()` is the current smallest verified command-to-evidence path.

5. `scripts/regression-harness/vpml_run_console_server.py`
   - Promote or rename as the local dashboard only after it consumes the shared registry and run-plan validator.
   - Host-local endpoints:
     - `GET /` renders dashboard/form from registry + latest evidence.
     - `GET /data.json` returns `vpml_evidence_page.build_page(evidence_dir)`.
     - `GET /api/programmes` returns the shared registry.
     - `POST /api/compile` validates the form into a `VPMLRunPlan`; no serial side effects.
     - `POST /api/identify` calls `vpml_live_runner.identify_transport()` with chip guard.
     - `POST /api/status` calls `vpml_live_runner.run_status_transport()` with chip guard.
     - `POST /api/run` calls `vpml_run_console.run_vpml_session()` or `vpml_live_runner.run_capture_transport()` and writes evidence.
     - `POST /api/stop` calls `vpml_live_runner.run_simple_command_transport(":vpml=stop", ...)`.
     - `GET /evidence/<name>` serves only basename-constrained files from `evidence_dir`.
   - Keep binding loopback by default and treat `--allow-non-loopback` as an explicit risk switch.

6. `scripts/regression-harness/vpml_evidence_page.py` / `vpml_runtime_summary.py`
   - Keep as readback/gate modules only.
   - They can power dashboard state, but must not be used to imply live control or visual acceptance.

## Pitfalls

- Calling the current picker/editor a compiler is misleading unless the output is a checked `VPMLRunPlan` that flows into the live runner. There is no arbitrary runtime programme transport in the audited firmware or host scripts.
- A parameter editor for `VPMLRenderParams` would be fake today. The firmware has params in memory, but the serial command surface does not expose setters.
- Evidence-page-only UI is not a workbench. `vpml_evidence_page.py` and `vpml_host_surface.py` are explicitly file-backed/read-only surfaces.
- Programme metadata drift is already present across three scripts. Centralise before adding UI affordances.
- Dashboard HTTP endpoints are host-local convenience endpoints only. Do not describe them as K1 REST, AP, WebSocket, Tab5, or production controls.
- Keep compile/upload/raw receive/factory/erase/restore/cal/wifi/websocket fragments denied at the command boundary.
- Keep chip identity as a hard pre-send guard for play/run/stop/status; wrong-chip success would create false evidence.
- Byte-clean evidence is not Captain visual acceptance. The dashboard may show byte proof and motion readback, but acceptance still requires a review source/annotation path.

## Re-run

None. Read-only source audit; no tests, serial, upload, AP, REST, WebSocket, Tab5, firmware edits, or live device commands were run.
