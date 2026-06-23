# VPML Run Console Scope Audit - 2026-06-09

Task ID: `VPML-RUN-CONSOLE-SCOPE-AUDIT-2026-06-09`

Verdict: `NEEDS_WORK`. No active compile/upload/raw-receive/AP/REST/K1-WebSocket/Smart-Director/audio/persistence command path was found in the scoped runner, but the browser server still exposes a device-write `/run` endpoint behind a configurable bind host.

## Sources Read

- `.claude/CLAUDE.md`, `progress.md`, `.claude/handoff.md`, `docs/spec-index.md`
- `docs/protocol/k1-ws-contract.yaml`, `docs/protocol/k1-rest-contract.yaml`
- `docs/forensics/vp_motion_lab/2026-06-09-vp-motion-lab-mvp-decision.md`
- `docs/forensics/vp_motion_lab/2026-06-09-vp-motion-lab-page-flow-spec.md`
- `evidence/ssa/vpml-implementation-20260609/scope-guard.md`
- `docs/forensics/vp_motion_lab/ssa/2026-06-09-scope-red-team.md`
- `docs/forensics/vp_motion_lab/ssa/2026-06-09-runner-audit.md`
- `docs/forensics/vp_motion_lab/ssa/2026-06-09-runtime-boundary.md`
- `scripts/regression-harness/vpml_run_console_server.py`
- `scripts/regression-harness/vpml_run_console.py`
- `tests/test_vpml_run_console.py`

Missing reference docs observed in this checkout: `firmware-v3/docs/reference/codebase-map.md`, `firmware-v3/docs/reference/fsm-reference.md`.

## Risk List

1. Medium - non-local browser bind can turn a host-local dev console into a network-reachable device-write surface. `vpml_run_console_server.py:21` defaults to `127.0.0.1`, but `vpml_run_console_server.py:508` accepts arbitrary `--host`, and `vpml_run_console_server.py:471-493` serves `POST /run`, which calls `run_capture_from_form()` and ultimately opens USB CDC and sends VPML/VPAB typed commands. The VPML page-flow contract says the browser UI is a `localhost` host service, not K1 AP/REST/WebSocket (`2026-06-09-vp-motion-lab-page-flow-spec.md:90-116`). Fix control: remove `--host`, or reject anything except `127.0.0.1`, `localhost`, and `::1` unless a separately approved non-local threat model exists.
2. Low - two form labels can look like programme parameters rather than capture preflight settings. `vpml_run_console_server.py:365-369` labels fields as `Seconds` and `Every N Frames`; the page-flow spec says capture cadence belongs to Page 1 capture preflight and no runtime sliders/programme parameters exist in the MVP (`2026-06-09-vp-motion-lab-page-flow-spec.md:250`, `:352`). Fix strings: rename to `Capture Window Seconds` and `VPAB Capture Cadence` or equivalent explicit capture-only wording.
3. Low - server-specific scope checks are not covered by the current unit test. `tests/test_vpml_run_console.py` covers `vpml_run_console.py` command order, denylist, bounded noisy reads, and partial evidence, but not `vpml_run_console_server.py` host binding, `/run` parsing, or the rendered copy. Fix control: add a host-only test/static check for loopback-only bind and forbidden UI affordances.

## Forbidden Strings / Controls Found

Forbidden strings present only as negative boundary copy or denylist entries: `compile`, `upload`, `raw_receive`, `rawrecv`, `factory`, `erase`, `restore`, `cal`, `wifi`, `websocket`, `AP/REST/WebSocket`, `persistence`, `Smart Director`, `audio` (`vpml_run_console.py:1-8`, `:38-49`; `vpml_run_console_server.py:341-345`; `tests/test_vpml_run_console.py:167-170`).

Active device controls found: `:version`, `:chip_id`, `:vpml=status`, `:vpml=play_builtin,<fixed programme>`, `:vpml=stop`, `:vpab=stop`, `:vpab=reset`, `:vpab=start,<every>,bytes`, `:vpab=frames`, `:vp_perf=stop`, `:vp_perf=reset`, `:vp_perf=start` (`vpml_run_console.py:263-386`, `:396-398`). These are typed USB CDC run/capture controls, which are inside VPML scope when chip identity passes.

No positive active controls found for `compile`, `upload`, `raw_receive`, `factory`, `erase`, `restore`, `wifi`, `websocket`, Tab5, AP, REST, K1 WebSocket, Smart Director, audio modulation, persistence, NVS programme storage, host compiler, or arbitrary runtime authoring.

## Host-Only Check

Run:

```bash
python3 -B -m unittest tests.test_vpml_run_console
```

Result: `PASS` (`Ran 6 tests in 0.032s OK`). This is host-only proof for the runner test surface; it is not live device proof and does not cover the server risks above.

## Re-Run Command After Fix

Minimum host-only re-run: `python3 -B -m unittest tests.test_vpml_run_console`

Add a server-specific host-only test or static grep before closing the `--host`/`/run` risk.
