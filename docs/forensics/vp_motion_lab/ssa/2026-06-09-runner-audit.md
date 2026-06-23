# VPML Runner Audit - 2026-06-09

Task ID: `VPML-RUNNER-AUDIT-2026-06-09`

## Verdict

`RUNNER_BUG_SUPPORTED_BY_SOURCE`; exact live failure invocation remains `NOT_REPRODUCED` because this audit did not open serial hardware.

Direct probe evidence and prior VPML logs show the command surface can exist on `/dev/cu.usbmodem1401`; they do not prove this runner is healthy. The failure shape "exit -1/no output/no new evidence" is consistent with the Python runner being externally timed out while waiting for serial idle, then losing its in-memory partial capture.

## Evidence

- `scripts/regression-harness/vpml_run_console.py:98-109` implements `read_idle()` with no wall-clock deadline. It exits only after `idle_reads` consecutive empty `readline()` calls.
- `scripts/regression-harness/vpml_run_console.py:131-136` calls `read_idle()` after every typed command, so unsolicited serial traffic can keep a command read alive indefinitely.
- `scripts/regression-harness/vpml_run_console.py:190-218` sends all runner commands through that idle-based path.
- `scripts/regression-harness/vpml_run_console.py:306-320` writes evidence only after the entire session returns successfully. `scripts/regression-harness/vpml_run_console.py:323-325` catches normal exceptions and returns `1`, but an external timeout/kill would bypass both the error print and evidence writes.
- `scripts/regression-harness/vpml_run_console.py:327-330` prints output paths only after evidence has already been written; a hang/timeout before that point naturally appears as no output from the tool.
- Prior successful VPML evidence contains unsolicited AP/K1WS traffic before and around typed responses: `docs/forensics/runtime-evidence/20260609T193511-vpml-intro-bounce-loop-1401.raw.log:2-24`.
- That same successful log proves VPML typed commands can work on `/dev/cu.usbmodem1401`: `docs/forensics/runtime-evidence/20260609T193511-vpml-intro-bounce-loop-1401.raw.log:39-42`, and stop/status worked at `docs/forensics/runtime-evidence/20260609T193511-vpml-intro-bounce-loop-1401.raw.log:319-322`.
- A later `/dev/tty.usbmodem1401` run proves identity/serial response but wrong firmware or missing VPML command surface, not hardware silence: `docs/forensics/runtime-evidence/20260609T212727-vpml-intro-bounce-loop-1401.raw.log:21-37` then `Bad command` at `docs/forensics/runtime-evidence/20260609T212727-vpml-intro-bounce-loop-1401.raw.log:38-60`.
- Adjacent helper `scripts/regression-harness/vpml_live_runner.py:93-125` uses fixed-duration reads instead of idle-only reads, and `scripts/regression-harness/vpml_live_runner.py:277-289` writes outputs even on chip identity failure.

## Suspected Failure Point

Primary suspect: `vpml_run_console.py` waits for serial silence, not bounded command windows. On a chatty K1, AP/K1WS/telemetry lines can prevent `read_idle()` from reaching its empty-read threshold. If an outer UI or orchestration layer kills the subprocess, the script has not reached `write_capture_outputs()`, so no raw log, frame log, summary, dashboard paths, or stderr error are emitted.

Secondary suspects:

- The console runner and live runner have diverged. `vpml_run_console.py:32` defaults to `230400`, while `scripts/regression-harness/vpml_live_runner.py:26` defaults to `115200`. The brief's direct probe was at `115200`; this should be made explicit in the patched runner or CLI.
- `tests/test_vpml_run_console.py:48-129` covers the happy path with a quiet fake serial and no background stream. It does not test timeout, no-response, continuous-noise, partial-evidence, or CLI failure semantics.

## Minimal Patch

1. Replace `read_idle()` with a bounded read primitive: `max_seconds` plus optional early idle exit. Every `send_command()` call must have a deadline.
2. Keep partial capture lines in an object available to `main()`, and write at least `<prefix>.raw.log` plus `<prefix>.error.json` on chip-id failure, missing command response, bad VPML command, or bounded timeout.
3. Align baud handling with the live path: either make `115200` the console default or require `--baud` explicitly and print the selected baud before opening serial.
4. Prefer reusing `vpml_live_runner.py` transport semantics rather than maintaining two subtly different VPML runners.

## Minimal Tests

- Add a fake serial that returns endless AP/K1WS lines and assert `run_vpml_session()` exits via bounded timeout, not an unbounded loop.
- Add a fake serial with no chip-id response and assert `main()` writes raw/error evidence and returns nonzero without sending play/capture commands.
- Add a CLI/default-baud assertion once the expected baud is chosen.
- Keep the existing happy-path test, but add noisy background lines around command responses.

## Re-run

Command: `python3 -B -m pytest tests/test_vpml_run_console.py -q`

Result: `3 passed in 0.03s`

## Boundary

No hardware, upload, firmware, serial monitor, or production source edits were touched. This audit does not claim hardware failure.
