# VPML Scope Red-Team - 2026-06-09

Task ID: `VPML-SCOPE-REDTEAM-2026-06-09`

Verdict: `NOT_VERIFIED` for completion, production readiness, protocol readiness, visual acceptance, or firmware/UI promotion. Source audit found no current scope violation in the inspected host-runner/evidence-page direction, provided it remains labelled as a non-shippable host/dev evidence surface.

## Sources Read

- `.claude/CLAUDE.md:8-16`, `.claude/CLAUDE.md:31-37`, `.claude/CLAUDE.md:45-57`, `.claude/CLAUDE.md:72-116`
- `progress.md:1-15`
- `docs/spec-index.md:7-18`, `docs/spec-index.md:51-66`
- `.claude/handoff.md:13-20`, `.claude/handoff.md:49-65`
- `docs/protocol/k1-ws-contract.yaml:1-17`, `docs/protocol/k1-ws-contract.yaml:35-87`
- `docs/protocol/k1-rest-contract.yaml:1-9`
- `docs/forensics/vp_motion_lab/2026-06-09-vp-motion-lab-page-flow-spec.md:7-18`, `:57-79`, `:116-146`, `:268-318`, `:464-523`, `:533-623`, `:625-744`
- `scripts/regression-harness/vpml_run_console.py:1-8`, `:34-49`, `:122-136`, `:163-230`, `:233-286`, `:289-330`
- `tests/test_vpml_run_console.py:47-147`

Source gaps observed:

- `firmware-v3/docs/reference/codebase-map.md` is missing.
- `firmware-v3/docs/reference/fsm-reference.md` is missing.

Host-only check run:

```bash
python3 -m unittest tests/test_vpml_run_console.py
```

Result: `PASS` (`Ran 3 tests in 0.030s OK`). This is not live-device proof.

## Constraint Audit

1. Non-shippable harness boundary: currently respected.
   - `.claude/CLAUDE.md:31-37` forbids developer/harness/diagnostic code from shipping in production firmware.
   - `vpml_run_console.py:1-8` explicitly labels the runner as host-side development for the non-shippable VPML surface and excludes compile, upload, raw receive, AP/REST/WebSocket, persistence, Smart Director, and audio modulation.
   - Risk: the orchestrator must keep this as `host-dev evidence`, not a production firmware feature or product surface.

2. Device identity discipline: implemented in the runner, but every live run still needs fresh observed identity.
   - `.claude/CLAUDE.md:45-57` requires port plus stable hardware identity before device-write actions.
   - `vpml_run_console.py:190-198` sends `:version`, `:chip_id`, extracts the chip ID, logs identity, and fails on missing/mismatched chip.
   - `tests/test_vpml_run_console.py:84-102` asserts the identity/status/play/capture/stop command order.
   - Risk: default `F887A500` is an expectation, not proof. Proof requires the live raw log from the next run.

3. Tab5/AP/REST/WebSocket contamination: currently excluded.
   - Page-flow requirements keep the host tool independent from Tab5, AP, REST, K1 WebSocket, wireless, Smart Director, audio modulation, persistence, and production firmware (`page-flow-spec.md:61-67`).
   - The plan permits a browser-to-localhost event stream but forbids K1 AP WebSocket for VPML (`page-flow-spec.md:116-123`).
   - K1 WebSocket is an AP-only Tab5 control contract (`k1-ws-contract.yaml:1-17`, `:35-87`), and REST has no paths and must not gain controls for this slice (`k1-rest-contract.yaml:1-9`).
   - Risk: no `Tab5 live`, `AP connected`, `REST control`, or `WebSocket control` claim can be derived from VPML runner success.

4. Built-ins-only boundary: currently respected.
   - Current requirements allow only `intro_bounce` and `intro_bounce_loop` (`page-flow-spec.md:61-67`, `:354-363`).
   - Runner registry exposes only those two programmes (`vpml_run_console.py:34-37`) and rejects unsupported programme IDs before serial open (`tests/test_vpml_run_console.py:131-141`).
   - Forbidden command fragments cover compile/upload/raw receive/calibration/wifi/websocket-style escalation (`vpml_run_console.py:38-49`, `:122-136`; tested at `tests/test_vpml_run_console.py:143-147`).
   - Risk: "programme" here means fixed built-in command selection only. It is not authoring, compiler, upload, parameter support, persistence, or saved-on-K1 state.

5. Byte proof versus visual acceptance: separation is declared and tested.
   - Page 2 states separate `Byte Clean` from `Eyes-On Pending` and `Captain Accepted` (`page-flow-spec.md:475-493`).
   - Page 2 explicitly forbids visual/product/audio/causality claims from byte plots (`page-flow-spec.md:507-516`).
   - Tests assert a passing capture renders as `byte_clean` with `visual_status == eyes_on_pending` (`tests/test_vpml_run_console.py:125-130`).
   - Risk: a clean next run can prove strict VPAB/frame/summary bytes only. It cannot prove "looks good", motion feel, product fitness, colour clarity, or Captain acceptance.

6. Protocol/authoring/promotion readiness: still locked.
   - Page 3 is checklist-only; upload/compiler panels stay hidden until missing ADR/spec/tests/live transport proof and Captain approval exist (`page-flow-spec.md:533-623`).
   - Page 4 promotion ledger is deferred until at least two byte-clean programmes exist, at least one has Captain eyes-on acceptance, and a native-promotion path exists (`page-flow-spec.md:625-637`).
   - Failure states block lab proof being treated as production proof, Smart Director inclusion, and promotion with missing eyes-on or evidence chain (`page-flow-spec.md:673-689`).
   - Risk: even a successful live run does not unlock Page 3, authoring, upload, native promotion, Smart Director inclusion, or production readiness.

## Allowed Next Slice

Allowed without hardware: continue the Page 2 data-only Evidence Gate / Motion Readability slice from existing evidence files:

- evidence index over current captures,
- strict gate and runtime-summary ingestion,
- centre-origin final-byte views,
- annotation sidecar schema,
- tests for accepted, rejected, dark sample, missing/malformed/stale evidence, missing secondary, and mode mismatch.

Source: `page-flow-spec.md:728-744`. This slice does not require serial or device access.

Allowed with separate orchestrator live-run approval: run the host runner against a verified K1 port/chip only to produce raw/frame-gate/summary/dashboard evidence. The orchestrator must rerun and consume that evidence before any live-run claim.

## Forbidden Claims Even If The Next Live Run Succeeds

- `production ready`
- `Captain accepted`
- `looks good`
- `visual quality proven`
- `product fitness proven`
- `audio reactive`
- `beat/tempo/onset causality proven`
- `Tab5 live`
- `AP connected`
- `REST control`
- `K1 WebSocket control`
- `compiled programme`
- `uploaded programme`
- `saved on K1`
- `parameter support`
- `authoring exists`
- `protocol ready`
- `Smart Director included`
- `native effect parity`
- `promotion candidate`, unless a separate byte-clean plus eyes-on plus native-promotion evidence chain exists

## Re-Run Command

Host-only check identified and run:

```bash
python3 -m unittest tests/test_vpml_run_console.py
```

Live runner command: not run by this SSA. Any live-run decision claim requires orchestrator execution, fresh port/chip identity in the raw log, strict gate output, runtime summary output, and separate visual acceptance evidence.
