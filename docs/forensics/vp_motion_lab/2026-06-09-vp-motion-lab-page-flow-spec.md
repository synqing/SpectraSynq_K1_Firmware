---
abstract: "Source-backed page-flow implementation plan for the VP Motion Lab host-side tool: run console, built-in picker layer, evidence gate, protocol-readiness lock, and deferred promotion ledger."
---

# VP Motion Lab Page-Flow Implementation Plan - 2026-06-09

## Status

Planning artefact only. This document does not implement firmware, UI, host-service, protocol, or harness changes.

Implementation companion created from this plan:

- `scripts/regression-harness/vpml_evidence_page.py` builds the file-backed Evidence Gate / Motion Readability model from existing VPML runtime artefacts.
- `scripts/regression-harness/vpml_host_surface.py` builds the file-backed host page-flow surface for Run Console, Programme + Parameter Picker, Evidence Gate, Protocol Readiness Lock, and deferred Promotion Ledger.
- `scripts/regression-harness/vpml_live_runner.py` is the operational host runner: it opens USB CDC serial, verifies chip identity, sends fixed built-in VPML commands, drains VPAB K1DF frames, and writes raw/frame-gate/runtime-summary evidence.
- `docs/forensics/vp_motion_lab/2026-06-09-vpml-evidence-page.json` and `.html` are generated Evidence Gate artefacts.
- `docs/forensics/vp_motion_lab/2026-06-09-vpml-host-surface.json` and `.html` are generated host-surface artefacts.
- The live runner is limited to fixed built-ins (`intro_bounce`, `intro_bounce_loop`) and existing typed serial commands. It does not upload programmes, compile authoring syntax, use raw receive, use AP/REST/WebSocket control, or claim Captain visual acceptance.

Current live checkout verified during this pass:

- Branch: `wip/audio-saliency-recovery`
- HEAD: `e6a70f3`
- Worktree: dirty, with VPML files mixed beside unrelated Tab5, wireless, protocol, firmware, script, and test changes. Stage only VPML documentation for this task.

The research document records an older live HEAD, `a6415f8`, for its own pass (`docs/forensics/vp_motion_lab/2026-06-09-vp-motion-lab-research.md:21-30`). Treat that as historical context, not current checkout truth.

## Source Authority

This plan implements the "First Onwards Task" requested by the roadmap: create a VPML page-flow specification covering the run console, programme picker, evidence gate, protocol lock, deferred promotion ledger, exact field sources, command/API boundaries, state matrix, and no Tab5/AP/REST/wireless scope (`docs/forensics/vp_motion_lab/2026-06-09-vp-motion-lab-onwards-roadmap.md:242-270`).

Load-bearing source facts:

| Fact | Source |
|---|---|
| On-disk handover beats memory for current lane status. | `.claude/CLAUDE.md:19-30`, `docs/spec-index.md:9-18` |
| Developer, harness, trace, benchmark, probe, and diagnostic code never ships with production firmware. | `.claude/CLAUDE.md:31-37` |
| Device-write actions require verified port plus stable hardware identity. | `.claude/CLAUDE.md:45-57` |
| Parallel agent work needs a consumption contract and final delegation ledger. | `.claude/CLAUDE.md:72-116` |
| Current VPML boundary is non-shippable fixed built-ins only, not Tab5/AP/REST/WebSocket/wireless/Smart Director/audio/persistence/production work. | `docs/forensics/vp_motion_lab/2026-06-09-vp-motion-lab-mvp-decision.md:13-28`, `docs/forensics/vp_motion_lab/2026-06-09-vp-motion-lab-mvp-decision.md:29-42` |
| `intro_bounce_loop` has clean byte proof on `F887A500`, but no Captain eyes-on acceptance. | `docs/forensics/vp_motion_lab/2026-06-09-vp-motion-lab-stepback-knowns.md:14-24`, `docs/forensics/vp_motion_lab/2026-06-09-vp-motion-lab-stepback-knowns.md:25-33` |
| AP WebSocket is a bounded Tab5 control contract, not VPML programme transport. | `docs/protocol/k1-ws-contract.yaml:1-17`, `docs/protocol/k1-ws-contract.yaml:23-34` |
| REST has no paths and must not gain controls unless a future feature explicitly requires them. | `docs/protocol/k1-rest-contract.yaml:1-9` |
| VPML source currently exposes only fixed built-ins and no programme transport, raw receive, compiler, audio modulation, persistence, AP, REST, Tab5, wireless, or Smart Director integration. | `platformio.ini:148-160`, `SPECTRASYNQ_K1_FIRMWARE/diag/vp_motion_lab.h:3-14` |
| Current VPML command body supports `status`, `play_builtin,intro_bounce`, `play_builtin,intro_bounce_loop`, and `stop` only. | `SPECTRASYNQ_K1_FIRMWARE/diag/vp_motion_lab.h:172-190` |
| VPML owns the LED frame only while active, renders, sets VPAB context, calls canonical `show_leds()`, and skips the shipping visual roster for that frame. | `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:670-695` |
| Current frame renderers preserve centre-origin bands around 79/80 and render primary plus secondary buffers. | `SPECTRASYNQ_K1_FIRMWARE/visual/led_utilities.h:1155-1169`, `SPECTRASYNQ_K1_FIRMWARE/visual/led_utilities.h:1196-1246`, `SPECTRASYNQ_K1_FIRMWARE/visual/led_utilities.h:1248-1284` |
| VPML runtime summary proves byte transport and final-byte coverage only; it is not an eyes-on visual acceptance gate. | `scripts/regression-harness/vpml_runtime_summary.py:1-7` |
| Strict VPAB frame gate fails closed on survivor frames plus unexpected fragments. | `scripts/regression-harness/vpab_frame_gate.py:1-6`, `scripts/regression-harness/vpab_frame_gate.py:45-67` |

Source gaps:

- `firmware-v3/docs/reference/codebase-map.md` is missing in this checkout.
- `firmware-v3/docs/reference/fsm-reference.md` is missing in this checkout.
- The current `.claude/handoff.md` and `docs/spec-index.md` still point at VME/VMEWT June 7 lane state (`.claude/handoff.md:13-20`, `docs/spec-index.md:21-33`). The VPML documents under `docs/forensics/vp_motion_lab/` and Captain's current prompt are the immediate lane input for this plan, but the routing docs should be updated only in a separate approved housekeeping task.

## Requirements

### Functional Requirements

1. Provide a local host-side VPML tool surface that can verify a K1 device, play current fixed built-ins, stop preview, start evidence capture through existing scripts, and open the resulting evidence gate.
2. Keep the first tool surface independent from Tab5, AP, REST, K1 WebSocket, wireless, Smart Director, audio modulation, persistence, and production firmware.
3. Support only `intro_bounce` and `intro_bounce_loop` as playable built-ins until firmware support expands.
4. Make Page 2 usable from existing evidence files before new device interaction.
5. Separate transport proof, byte-clean proof, motion-readability views, and Captain eyes-on acceptance.
6. Keep authoring and upload locked behind explicit protocol readiness. Do not expose a host compiler before the evidence/page loop is proven.
7. Keep promotion and regression tracking deferred until there are real candidates to manage.

### Non-Functional Requirements

| Requirement | Plan consequence | Source |
|---|---|---|
| Non-shippable boundary | Host UI must show VPML as a harness surface; production build claims require separate evidence. | `.claude/CLAUDE.md:31-37`, `platformio.ini:148-160` |
| Hardware identity discipline | Device-write controls are disabled until port plus chip identity are verified. | `.claude/CLAUDE.md:45-57`, `docs/spec-index.md:51-66` |
| Centre-origin geometry | Motion-readability views use centre pair 79/80 and radius/offset language, not left-to-right sweep language. | `SPECTRASYNQ_K1_FIRMWARE/visual/led_utilities.h:1155-1169` |
| No rainbow/hue wheel | Future authoring lock must reject hue-wheel/rainbow primitives before unlock. | `docs/forensics/vp_motion_lab/2026-06-09-vp-motion-lab-research.md:332-345` |
| No heap/render blocking | Protocol readiness must require static buffers and render-safe tests before uploaded programmes can play. | `docs/forensics/vp_motion_lab/2026-06-09-vp-motion-lab-research.md:364-380`, `tests/test_vp_motion_lab_static.py:76-96` |
| Evidence before claims | UI badges must not turn byte proof into product or aesthetic acceptance. | `scripts/regression-harness/vpml_runtime_summary.py:1-7`, `docs/forensics/vp_motion_lab/2026-06-09-vp-motion-lab-stepback-knowns.md:25-33` |

### User Jobs

| Performer | Job | Page support | Source |
|---|---|---|---|
| Captain / Creative Director | Try controlled motion variants live and judge whether the motion feels like SpectraSynq on the physical plate. | Run Console, Picker, Evidence Gate, eyes-on annotation. | `docs/forensics/vp_motion_lab/2026-06-09-vp-motion-lab-onwards-roadmap.md:216-224` |
| Firmware agent | Prove primary/secondary bytes through strict evidence gates without production leakage. | Evidence Gate, Protocol Lock, tests/harness list. | `docs/forensics/vp_motion_lab/2026-06-09-vp-motion-lab-onwards-roadmap.md:226-232` |
| Future promotion owner | Preserve manifest, evidence, acceptance, and implementation notes for native promotion. | Deferred Promotion + Regression Ledger. | `docs/forensics/vp_motion_lab/2026-06-09-vp-motion-lab-onwards-roadmap.md:234-240` |

## Component And Data-Flow Design

```text
Browser UI or CLI shell
  -> VPML host service on localhost
       -> DevicePort adapter
            -> host OS serial port scan
            -> USB CDC typed commands only
       -> ProgrammeRegistry
            -> fixed built-in metadata for intro_bounce and intro_bounce_loop
       -> CaptureRunner
            -> existing VPAB/K1DF capture scripts
       -> GateRunner
            -> vpab_frame_gate.py
            -> vpml_runtime_summary.py
       -> EvidenceIndex
            -> docs/forensics/runtime-evidence/*
            -> local annotation sidecars

K1 running k1_vp_motion_lab
  -> typed serial metadata command vpml=...
  -> vpml frame-owner branch while active
  -> primary and secondary buffers
  -> explicit VPAB context mode 250
  -> canonical show_leds()
  -> VPAB/K1DF final-byte drain
```

The browser UI may use a localhost event stream or WebSocket only between UI and host service. It must not use the K1 AP WebSocket for VPML (`docs/forensics/vp_motion_lab/2026-06-09-vp-motion-lab-onwards-roadmap.md:600-617`).

### Host-Side Ports And Adapters

| Port | Adapter now | Future adapter | Boundary rule |
|---|---|---|---|
| `DevicePort` | USB CDC serial, typed commands. | Same, plus future bounded VPML transport only after Page 3 unlock. | Never AP/REST/K1 WebSocket for VPML MVP. |
| `ProgrammeRegistry` | Static registry for `intro_bounce` and `intro_bounce_loop`. | Generated registry from firmware command support or future manifest. | No programme appears playable without source-backed command support. |
| `CaptureRunner` | Existing VPAB capture flow and logs. | Same with session metadata. | No calibration, erase, factory reset, or restore-defaults commands. |
| `GateRunner` | `vpab_frame_gate.py` and `vpml_runtime_summary.py`. | Same plus protocol fixtures. | Strict gate result appears before derived views. |
| `AnnotationStore` | Local sidecar only. | Promotion ledger later. | Human judgement is explicit, dated, and separate from byte proof. |

## Local API And Event Boundary

These are host-service events, not K1 AP messages. Responses should be structured JSON so browser, CLI, tests, and future automation share one contract.

| Event | Current implementation boundary | Source | Notes |
|---|---|---|---|
| `device.scan` | Host OS serial scan only. | Host-local. | No K1 write. |
| `device.identify` | Send existing typed `chip_id` and optionally typed-only `identify`; parse chip ID. | `SPECTRASYNQ_K1_FIRMWARE/serial/serial_cmd_table.def:31-44`, `scripts/regression-harness/vpml_runtime_summary.py:111-153` | Record port, expected chip, observed chip, timestamp, and raw response. |
| `vpml.status` | Send `:vpml=status`; parse active, programme, frame, frames, loops, `vpab_mode`. | `SPECTRASYNQ_K1_FIRMWARE/diag/vp_motion_lab.h:157-169`, `SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h:3132-3138` | Failure means "VPML command surface absent or unavailable", not necessarily "wrong build" unless build evidence is present. |
| `programme.list` | Return registry for supported built-ins only. | `SPECTRASYNQ_K1_FIRMWARE/diag/vp_motion_lab.h:29-67`, `SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h:2219-2225` | No upload/compiler entries. |
| `programme.play_builtin` | Send `:vpml=play_builtin,<programme>`. | `SPECTRASYNQ_K1_FIRMWARE/diag/vp_motion_lab.h:172-184` | Allowed only after `device.identify` and `vpml.status` pass. |
| `programme.stop` | Send `:vpml=stop`. | `SPECTRASYNQ_K1_FIRMWARE/diag/vp_motion_lab.h:143-155`, `SPECTRASYNQ_K1_FIRMWARE/diag/vp_motion_lab.h:185-187` | Should be offered in Playing/Capturing states. |
| `capture.start` | Use existing capture scripts and VPAB command surface. | `SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h:2212-2218`, `scripts/regression-harness/vpml_runtime_summary.py:291-337` | No new firmware command in this page slice. |
| `capture.gate` | Run strict gate and runtime summary. | `scripts/regression-harness/vpab_frame_gate.py:1-6`, `scripts/regression-harness/vpml_runtime_summary.py:156-288` | Must fail closed on parser issues, overflow, drops, missing channel, mode mismatch, or identity mismatch. |
| `capture.annotate` | Write local annotation sidecar. | New host storage only. | Annotation starts now. Existing captures have no backfilled eyes-on status unless Captain supplies it. |
| `evidence.open` | Open local evidence file by path. | Local filesystem. | Never infer freshness from filename alone. |
| Future `programme.compile` | Locked behind Page 3. | `docs/forensics/vp_motion_lab/2026-06-09-vp-motion-lab-research.md:414-432` | Hidden until host compiler and validator exist. |
| Future `programme.upload` | Locked behind Page 3. | `docs/forensics/vp_motion_lab/2026-06-09-vp-motion-lab-research.md:356-413` | Hidden until chunked protocol proof exists. |

## Storage And Evidence Model

### Files

| Record | Proposed path | Writer | Purpose |
|---|---|---|---|
| `VpmlRunSession` | `docs/forensics/runtime-evidence/<timestamp>-vpml-<programme>-<chip>.session.json` | Host service | Port/chip identity, repo state, commands sent, capture paths, gate paths. |
| Raw serial log | Existing pattern, `*.raw.log` | Capture runner | Unstructured serial transcript and identity proof. |
| K1DF frame log | Existing pattern, `*.frames.log` | Capture runner | Strict VPAB records for gate/summary. |
| Frame gate JSON | Existing pattern, `*.frame-gate.json` | Gate runner | Strict transport acceptance/failure. |
| VPML summary JSON | Existing pattern, `*.vpml-summary.json` | Gate runner | Decoded final-byte coverage and timing summary. |
| Annotation sidecar | `*.vpml-annotation.json` | User/agent via host service | Human status: rejected, byte-clean, eyes-on pending, Captain accepted, superseded. |
| Future programme manifest | `docs/forensics/vp_motion_lab/manifests/<id>.json` | Future compiler | Locked until Page 3 unlock. |

### Annotation Schema

```json
{
  "schema": "vpml_annotation.v1",
  "capture_id": "20260609T193511-vpml-intro-bounce-loop-1401",
  "programme": "intro_bounce_loop",
  "device": {
    "port": "/dev/cu.usbmodem1401",
    "expected_chip_id": "F887A500",
    "observed_chip_id": "F887A500"
  },
  "byte_status": "byte_clean",
  "visual_status": "eyes_on_pending",
  "verdict": "pending",
  "accepted_by": null,
  "accepted_at": null,
  "review_source": null,
  "supersedes": [],
  "superseded_by": null,
  "note": "Byte proof only; no Captain eyes-on yet.",
  "source_summary": "docs/forensics/runtime-evidence/20260609T193511-vpml-intro-bounce-loop-1401.vpml-summary.json"
}
```

Allowed `byte_status` values:

- `not_evaluated`
- `transport_failed`
- `coverage_failed`
- `byte_clean`
- `byte_clean_with_observations`

Allowed `visual_status` values:

- `not_reviewed`
- `eyes_on_pending`
- `captain_accepted`
- `captain_rejected`
- `superseded`

Rule: `visual_status=captain_accepted` requires a human note that cites Captain eyes-on, camera/video review, or another explicitly accepted equivalent. It is not set by gate JSON.

Required `HumanAcceptance` fields before promotion unlock:

| Field | Requirement |
|---|---|
| `verdict` | One of `pending`, `accepted`, `rejected`, `superseded`. |
| `accepted_by` | Must be `Captain` or the named accepted review authority for accepted state. |
| `accepted_at` | Timestamp of review, not capture timestamp. |
| `capture_id` | Must match the gate artefact being annotated. |
| `programme` | Must match the programme in the VPML status/capture evidence. |
| `device.expected_chip_id` and `device.observed_chip_id` | Must match for target proof. |
| `source_summary` | Must link to the summary JSON used for byte status. |
| `review_source` | Text note, video path, camera review path, or explicit Captain eyes-on statement. |
| `supersedes` / `superseded_by` | Required when a capture replaces earlier evidence. |

## Page 1 - VPML Run Console

### User Job

When a VPML build is live on K1, Captain or an agent needs one surface to verify the target, play a fixed built-in, stop it, capture evidence, and hand the capture to Page 2 without serial-console choreography (`docs/forensics/vp_motion_lab/2026-06-09-vp-motion-lab-onwards-roadmap.md:274-289`).

### Primary Workflow

1. Scan serial ports.
2. Select candidate port.
3. Identify K1 and verify expected chip ID.
4. Probe VPML status.
5. Open the Programme + Parameter Picker layer.
6. Select `intro_bounce_loop` by default.
7. Send `play_builtin`.
8. Show live status and command log.
9. Stop or capture.
10. Run existing capture flow and open Page 2.

### Controls

| Control | Host event | K1/device action | Enabled when | Failure behaviour |
|---|---|---|---|---|
| Scan Ports | `device.scan` | None | Always | Empty state with no device claim. |
| Identify K1 | `device.identify` | `:chip_id`, optional `:identify` | Port selected | Wrong or missing chip disables play/capture. |
| Probe VPML Status | `vpml.status` | `:vpml=status` | Chip verified | Unsupported command becomes Wrong Firmware/VPML Absent. |
| Programme Picker | `programme.list` | None | VPML status known or offline review | Shows fixed built-ins only. |
| Play Built-In | `programme.play_builtin` | `:vpml=play_builtin,intro_bounce_loop` or `:vpml=play_builtin,intro_bounce` | Chip verified, VPML status available, not capturing | Timeout returns command failure; no status upgrade. |
| Stop | `programme.stop` | `:vpml=stop` | Playing or uncertain after play | Failure keeps "stop unconfirmed" warning. |
| Capture VPAB Bytes | `capture.start` | Existing capture command/script path | Playing, chip verified, VPML status available | Capture result is not proof until Page 2 gates it. |
| Open Evidence | `evidence.open` | None | Capture path exists | Missing files open Page 2 in Missing Files state. |

Capture preflight is part of Page 1, not the Programme Picker. It must show capture cadence, expected record count, VPAB mode, pool/counter expectations, output paths, and "no proof until Page 2" before capture starts. Because one prior capture was rejected for dropped/overflowed records, the first implementation must treat cadence as an evidence safety setting, not a programme parameter (`docs/forensics/vp_motion_lab/2026-06-09-vp-motion-lab-onwards-roadmap.md:103-110`, `docs/forensics/runtime-evidence/20260609T193419-vpml-intro-bounce-loop-1401.frame-gate.json:1-31`).

### Readbacks And Data Sources

| Field | Data source | Source authority | Display rule |
|---|---|---|---|
| Port | Host OS serial scan/session manifest | Host-local | Do not imply identity. |
| Expected chip ID | User/session config, spec-index quick-ref, or capture args | `docs/spec-index.md:51-66`, `scripts/regression-harness/vpml_runtime_summary.py:128-138` | Must be visible before device-write controls. |
| Observed chip ID | `chip_id`/`identify` command or raw log parser | `SPECTRASYNQ_K1_FIRMWARE/serial/serial_cmd_table.def:31-44`, `scripts/regression-harness/vpml_runtime_summary.py:128-138` | Red if absent or mismatched. |
| Firmware status | `vpml.status` command response | `SPECTRASYNQ_K1_FIRMWARE/diag/vp_motion_lab.h:157-169` | Label as "VPML command surface present", not "env proven" unless build/upload evidence is attached. |
| VPML active | `vpml.status` response | `SPECTRASYNQ_K1_FIRMWARE/diag/vp_motion_lab.h:157-160` | Boolean badge. |
| Programme | `vpml.status`, play response, registry | `SPECTRASYNQ_K1_FIRMWARE/diag/vp_motion_lab.h:59-67`, `SPECTRASYNQ_K1_FIRMWARE/diag/vp_motion_lab.h:130-132` | Must be one of registry values. |
| Frame/frames/loops | `vpml.status` response | `SPECTRASYNQ_K1_FIRMWARE/diag/vp_motion_lab.h:162-168` | Diagnostic, not aesthetic. |
| VPAB mode | `vpml.status` response, summary JSON | `SPECTRASYNQ_K1_FIRMWARE/diag/vp_motion_lab.h:35-39`, `SPECTRASYNQ_K1_FIRMWARE/diag/vp_motion_lab.h:168-169` | Expected `250`. |
| Last command result | Raw serial response | `SPECTRASYNQ_K1_FIRMWARE/diag/vp_motion_lab.h:130-154` | Show raw line and parsed status. |
| Capture status | Capture runner process state and raw log lines | `scripts/regression-harness/vpml_runtime_summary.py:111-153` | Not proof until gated. |
| Gate summary link | Local evidence file | Existing runtime-evidence pattern | Open Page 2. |

### States

| State | Meaning | Allowed actions | Exit condition |
|---|---|---|---|
| No Device | No serial port selected. | Scan, select port. | Port selected. |
| Port Selected | Port exists but K1 identity not verified. | Identify, scan. | Observed chip ID parsed. |
| Wrong Device | Observed chip ID mismatches expected target. | Re-identify, select another port. | Matching chip ID. |
| Identity Verified | Chip ID matches, VPML status not yet probed. | Probe VPML status. | VPML status response. |
| Wrong Firmware / VPML Absent | K1 responds, but `vpml=status` fails or is unsupported. | Status retry, stop disabled unless active state is uncertain. | VPML status response or intentional reflash outside this page plan. |
| Ready | VPML status present and inactive. | Picker, play, capture setup, status. | Play command starts preview. |
| Playing | VPML active on a selected built-in. | Stop, status, capture. | Stop response or capture start. |
| Capturing | Capture command/script is running or draining. | Stop capture if supported, open partial logs read-only. | Gate artefacts produced or capture failed. |
| Capture Rejected | Page 2 gate failed. | Open Evidence, rerun with safer cadence. | New capture or annotation. |
| Byte Clean / Eyes-On Pending | Page 2 gate passed, no human acceptance. | Open Evidence, annotate, prepare eyes-on. | Human acceptance/rejection. |
| Captain Accepted | Human acceptance recorded separately. | Create future promotion candidate, still no production claim. | Promotion task opened. |
| Blocked / Identity Stale | Previous identity is too old, port changed, or chip ID was not observed in the current session. | Scan, identify. | Fresh matching identity. |
| Blocked / Product Trust Restore Needed | K1 may still be running a non-shippable probe build and next use is product eyes-on or trusted handback. | Do not play/capture for product claim; restore/verify under separate approved task. | Normal intended firmware state verified. |
| Blocked / Lane Isolation | Worktree staging/isolation is not known and the task is commit/promotion related. | Continue read-only operation only. | Explicit staging list or clean isolated worktree. |
| Blocked / Repeated Transport Failure | Multiple captures fail with dropped/corrupt/overflow counters. | Stop treating capture cadence as a tweak; open transport diagnosis. | Clean strict gate evidence. |

### Failure States

| Failure | Required handling |
|---|---|
| Serial port disappears | Stop polling, mark device disconnected, require re-identification. |
| Command timeout | Preserve last known state but mark stale; do not auto-retry play. |
| Unexpected `vpml` response | Keep raw line, no state upgrade. |
| Unsupported programme | Show registry/firmware drift; do not send play. |
| Capture overflow/dropped/corrupt | Page 1 labels "capture produced files"; Page 2 labels proof failed. |
| Stale gate artefact | Require explicit "open older evidence" state, not latest-run state. |
| Dirty worktree warning | Non-blocking for UI operation, blocking for commit/promotion staging. |

### Must Not Claim

- "Looks good" or "Captain accepted" from bytes.
- "Production ready".
- "Uploaded programme".
- "Compiled programme".
- "Saved on K1".
- "Tab5 live".
- "AP connected".
- "REST/WebSocket control".
- "Audio reactive".

### Acceptance Evidence

- Mock serial tests cover No Device, Wrong Device, Wrong Firmware, Ready, Playing, Capturing, Capture Rejected, Byte Clean, and Eyes-On Pending.
- Fixture replay can reproduce `20260609T193511` as byte-clean and eyes-on pending (`docs/forensics/vp_motion_lab/2026-06-09-vp-motion-lab-stepback-knowns.md:20-24`).
- Fixture replay can reproduce `20260609T193419` as rejected for dropped/overflowed records (`docs/forensics/runtime-evidence/20260609T193419-vpml-intro-bounce-loop-1401.frame-gate.json:1-31`).
- Live-device test, when approved, records port plus chip ID before play/capture (`.claude/CLAUDE.md:45-57`).

### Implementation Prerequisites

- Host-service skeleton with serial adapter abstraction.
- Built-in programme registry.
- Session manifest writer.
- Evidence file locator.
- Mock serial fixtures from current raw/status lines.
- Decision on local UI shell: CLI-first, local web app, or both. The safest first slice is data-only Page 2 with a CLI or static local page.

## Layer A - Programme + Parameter Picker

### User Job

When running a controlled preview, Captain or an agent needs to choose a supported built-in and see its proof/acceptance status without implying a mature programme library or compiler (`docs/forensics/vp_motion_lab/2026-06-09-vp-motion-lab-onwards-roadmap.md:349-392`).

### Primary Workflow

1. Open from Run Console.
2. Show fixed built-ins and metadata.
3. Default to `intro_bounce_loop`.
4. Show `intro_bounce` as boot-shaped reference with fade trough warning.
5. Confirm selection.
6. Return programme ID to Run Console.

### Controls

| Control | Host event | K1/device action | Enabled when |
|---|---|---|---|
| Select Programme | `programme.select` | None | Registry loaded. |
| Confirm | `programme.select.commit` | None | Selected programme has command support. |
| View Evidence | `evidence.open` | None | Evidence link exists. |
| Close | UI local | None | Always. |

No runtime sliders in the MVP. Programme parameters such as duration, palette token, travel curve, phase offset, or brightness floor stay deferred until firmware supports parameterised built-ins or host-side manifests (`docs/forensics/vp_motion_lab/2026-06-09-vp-motion-lab-onwards-roadmap.md:370-379`). Capture cadence is not a programme parameter; it belongs to the Page 1 capture preflight and Page 2 evidence gate.

### Readbacks And Data Sources

| Field | Data source | Source authority | Display rule |
|---|---|---|---|
| Programme ID | `VPMotionLabProgram` enum and command body | `SPECTRASYNQ_K1_FIRMWARE/diag/vp_motion_lab.h:29-67`, `SPECTRASYNQ_K1_FIRMWARE/diag/vp_motion_lab.h:172-190` | Only `intro_bounce`, `intro_bounce_loop`. |
| Recommended default | Plan registry | `docs/forensics/vp_motion_lab/2026-06-09-vp-motion-lab-stepback-knowns.md:20-24` | `intro_bounce_loop`. |
| Frame count | VPML constants/status | `SPECTRASYNQ_K1_FIRMWARE/diag/vp_motion_lab.h:35-37`, `SPECTRASYNQ_K1_FIRMWARE/diag/vp_motion_lab.h:164-165` | 112 for boot reference, 96 for loop preview. |
| Primary/secondary support | Renderer and VPML branch | `SPECTRASYNQ_K1_FIRMWARE/visual/led_utilities.h:1220-1232`, `SPECTRASYNQ_K1_FIRMWARE/visual/led_utilities.h:1270-1283`, `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:670-695` | Show as source-backed capability. |
| Byte proof link | Evidence index | `docs/forensics/vp_motion_lab/2026-06-09-vp-motion-lab-stepback-knowns.md:20-24` | Link to accepted/rejected artefacts. |
| Eyes-on status | Annotation sidecar | New local annotation | Starts as `eyes_on_pending`. |

### States

| State | Meaning |
|---|---|
| Registry Loading | Host metadata not loaded. |
| Supported Built-In | Programme has a current firmware command. |
| Reference Only | Programme exists but should not be the default live loop, e.g. `intro_bounce` with fade trough. |
| Unsupported / Future | Metadata exists but no command support. Hide from play list unless developer mode is explicitly enabled. |
| Evidence Missing | Programme is playable but has no linked evidence. |
| Byte Clean / Eyes-On Pending | Linked evidence passed byte gates but no human acceptance. |

### Failure States

| Failure | Required handling |
|---|---|
| Registry includes unsupported programme | Static test failure; do not show as playable. |
| Firmware status returns programme outside registry | Show firmware/UI drift. |
| Evidence link missing | No proof badge; do not infer status. |
| Parameter requested before support | Hide control, do not show disabled fake affordance. |

### Must Not Claim

- Custom code.
- Compiler.
- Saved to K1.
- Uploaded programme.
- Audio reactive.
- Palette acceptance.
- Parameter support.

### Acceptance Evidence

- Shared programme registry drives Page 1 and Page 2 labels.
- Static test asserts playable programmes have matching current `vpml_command` support.
- Fixture test proves `intro_bounce_loop` is default and `intro_bounce` carries boot fade/dark-sample warning.

### Implementation Prerequisites

- `programme_registry.v1` JSON or equivalent typed module.
- Parser for current `vpml.status` lines.
- Evidence index keyed by programme ID.

## Page 2 - Evidence Gate / Motion Readability

### User Job

When a VPML run has been captured, Captain or an agent needs to know whether evidence is valid, what each channel produced, and what the final bytes did over time without pretending that byte plots prove aesthetic quality (`docs/forensics/vp_motion_lab/2026-06-09-vp-motion-lab-onwards-roadmap.md:393-408`).

### Primary Workflow

1. Open latest capture from Page 1 or select an existing capture path.
2. Verify required files exist.
3. Run strict K1DF gate.
4. Run VPML runtime summary.
5. Show gate result before any derived plots.
6. Render motion-readability views from decoded final bytes.
7. Label each derived view as `evidence`, `hypothesis`, or `presentation`.
8. Compare against a previous capture or baseline when selected.
9. Add annotation: rejected, byte-clean, eyes-on pending, Captain accepted, or superseded.
10. Export closeout snippet for handover.

### Controls

| Control | Host event | Data action | Enabled when |
|---|---|---|---|
| Open Capture | `evidence.open` | Select raw/frame/summary paths. | Always. |
| Run Strict Gate | `capture.gate.strict` | Execute `vpab_frame_gate.py`. | Frame log present. |
| Run VPML Summary | `capture.gate.summary` | Execute `vpml_runtime_summary.py`. | Frame log present; raw log optional but required for identity. |
| Toggle View | UI local | Switch heatmap/terrain/delta/energy/nonzero views. | Summary has decoded records. |
| Compare Capture | `evidence.compare` | Load two evidence summaries side by side. | Two summaries available. |
| Mark Superseded | `capture.annotate` | Update annotation sidecars. | Replacement capture selected. |
| Rerun Recommendation | UI local | Suggest rerun reason from failure class. | Gate result loaded. |
| Annotate | `capture.annotate` | Write annotation sidecar. | Evidence loaded. |
| Export Snippet | `evidence.export` | Generate Markdown summary. | Gate result loaded. |

### Readbacks And Data Sources

| Field | Data source | Source authority |
|---|---|---|
| Capture path | Host EvidenceIndex/session manifest | Local filesystem. |
| Raw log path | Session manifest or selected file | `scripts/regression-harness/vpml_runtime_summary.py:291-308` |
| Frame log path | Session manifest or selected file | `scripts/regression-harness/vpml_runtime_summary.py:291-308` |
| Summary path | GateRunner output | `scripts/regression-harness/vpml_runtime_summary.py:291-337` |
| Schema | Summary JSON `schema` | `scripts/regression-harness/vpml_runtime_summary.py:260-288` |
| Gate result | Summary JSON `result`/`passed` | `scripts/regression-harness/vpml_runtime_summary.py:260-288` |
| Acceptance flags | Summary JSON `acceptance` | `scripts/regression-harness/vpml_runtime_summary.py:244-258` |
| Strict gate counts | Summary JSON `strict_gate.counts` or frame-gate JSON `counts` | `scripts/regression-harness/vpml_runtime_summary.py:266-271`, `docs/forensics/runtime-evidence/20260609T193419-vpml-intro-bounce-loop-1401.frame-gate.json:1-8` |
| Transport counters | `strict_gate.stream.begin/end` | `scripts/regression-harness/vpml_runtime_summary.py:266-271`, `docs/forensics/runtime-evidence/20260609T193419-vpml-intro-bounce-loop-1401.frame-gate.json:32-51` |
| Issues/failures | Frame gate JSON and summary JSON | `scripts/regression-harness/vpab_frame_gate.py:31-67`, `scripts/regression-harness/vpml_runtime_summary.py:179-225` |
| Device identity | Runtime facts from raw log | `scripts/regression-harness/vpml_runtime_summary.py:111-153` |
| Programme | Runtime VPML status line | `scripts/regression-harness/vpml_runtime_summary.py:139-144` |
| VPAB mode | Decoded records, expected mode | `scripts/regression-harness/vpml_runtime_summary.py:194-215`, `SPECTRASYNQ_K1_FIRMWARE/diag/vp_motion_lab.h:35-39` |
| Primary/secondary record counts | Summary JSON `channel_counts` | `scripts/regression-harness/vpml_runtime_summary.py:207-223` |
| Nonzero totals | Summary JSON `channel_nonzero_led_bytes_total` | `scripts/regression-harness/vpml_runtime_summary.py:207-223`, `scripts/regression-harness/vpml_runtime_summary.py:273-285` |
| Energy totals | Summary JSON `channel_energy_sum_total` | `scripts/regression-harness/vpml_runtime_summary.py:207-223`, `scripts/regression-harness/vpml_runtime_summary.py:273-285` |
| Dark sample records | Summary JSON `dark_sample_records` and observations | `scripts/regression-harness/vpml_runtime_summary.py:200-225`, `scripts/regression-harness/vpml_runtime_summary.py:236-242` |
| Render/frame/show timing | Summary JSON stats | `scripts/regression-harness/vpml_runtime_summary.py:101-107`, `scripts/regression-harness/vpml_runtime_summary.py:281-283` |
| Eyes-on status | Annotation sidecar | New local annotation only. |

### Motion-Readability Views

| View | Proof label | Purpose | Restrictions |
|---|---|---|---|
| Channel heatmap | `evidence` | Show byte intensity over frame/time for primary and secondary. | Uses decoded final bytes only. |
| Centre-origin terrain/waterfall | `evidence` | Re-map LED index to centre radius so outward/inward motion is readable. | Centre pair 79/80 must be marked. |
| Primary/secondary delta | `evidence` | Show channel independence and lag/offset shape. | Do not call it perceptual separation. |
| Energy/nonzero traces | `evidence` | Show intensity and dark-sample risk over time. | Do not call it brightness feel. |
| Loop phase sketch | `hypothesis` | Help reason about motion loop period. | Must state it is inferred from samples. |
| Handover thumbnail | `presentation` | Human-readable summary. | Cannot increase proof strength. |

### States

| State | Meaning | Required UI treatment |
|---|---|---|
| No Capture | No file selected. | Prompt to open capture or run Page 1. |
| Missing Files | Required raw/frame/summary paths missing. | Cannot evaluate. |
| Malformed Evidence | JSON or frame stream cannot parse. | Red; show parser issue. |
| Transport Failed | Strict gate failed. | Red; no proof badge, no promotion. |
| Coverage Failed | Primary or secondary missing. | Red; identify missing channel. |
| Mode Failed | Records are not VPML sentinel `250`. | Red; not VPML proof. |
| Identity Failed | Expected chip ID does not match observed chip ID. | Red; do not use as target proof. |
| Dark Sample Warning | Dark sample exists but capture did not require loop-safe no-dark rule. | Amber observation. |
| Dark Sample Failed | Loop-safe capture uses `--fail-on-dark-sample` and dark record exists. | Red. |
| Byte Clean | Required byte gates passed. | Green byte badge only. |
| Eyes-On Pending | Byte clean but no human acceptance. | Amber product badge. |
| Captain Accepted | Human acceptance recorded. | Unlock future promotion candidate; still no production claim. |
| Superseded | Later capture replaces this one. | Grey; keep evidence available. |
| Blocked / Evidence Stale | Summary, raw log, frame log, annotation, or expected chip ID do not describe the same capture. | Red; require regeneration or explicit stale-note annotation. |
| Blocked / No Acceptance Source | User attempts to mark accepted without Captain eyes-on, camera/video review, or equivalent source. | Block accepted state; allow note only. |
| Blocked / Transport Diagnosis Needed | Repeated strict gate transport failures. | Stop derived analysis by default and route to transport diagnosis. |

### Failure States

| Failure | Existing evidence example | Required handling |
|---|---|---|
| Dropped/overflowed transport | `dropped=28`, `overflowed=1` in rejected capture. | Mark invalid proof before derived views. |
| Unexpected strict-stream line | Rejected capture has `#CMD :vpml=stop` and `#CMD :vpml=status` issues. | Preserve issue list; do not ignore fragments. |
| Dark sample in boot-shaped capture | `intro_bounce` summary passes but records dark observations. | Label as observation, not loop-safe acceptance. |
| Missing secondary | Covered by runtime summary test. | Red coverage failure. |
| Malformed/missing JSON | To be added in Page 2 tests. | Red missing/malformed state. |
| Stale human annotation | Annotation capture ID does not match evidence hash/path. | Mark annotation stale and require reconfirmation. |

### Must Not Claim

- Visual quality.
- Product fitness.
- Native effect parity.
- Audio responsiveness.
- Beat/tempo/onset causality.
- That host preview equals K1 output.
- That byte-clean equals Captain acceptance.

### Acceptance Evidence

- Existing accepted loop capture renders as `Byte Clean / Eyes-On Pending`, with strict transport clean, primary/secondary present, mode 250, no dark samples, perf no over/dropped frames, and chip `F887A500` (`docs/forensics/runtime-evidence/20260609T193511-vpml-intro-bounce-loop-1401.vpml-summary.json:1-45`).
- Existing rejected high-cadence capture renders as `Transport Failed`, with four failures for dropped/overflowed counters and issue rows for unexpected lines (`docs/forensics/runtime-evidence/20260609T193419-vpml-intro-bounce-loop-1401.frame-gate.json:1-31`, `docs/forensics/runtime-evidence/20260609T193419-vpml-intro-bounce-loop-1401.frame-gate.json:32-51`).
- Original `intro_bounce` renders as byte transport clean with dark-sample observation, not loop-safe acceptance (`docs/forensics/runtime-evidence/20260609T190853-vpml-intro-bounce-1401.vpml-summary-v2.json:1-40`).
- Unit tests already cover dual-channel pass, dark-sample observation, dark-sample fail option, missing secondary, and CLI summary output (`tests/test_vpml_runtime_summary.py:72-139`).
- Compare/rerun tests show accepted versus rejected capture side by side, preserve superseded annotations, and never upgrade a rejected capture through derived plots.

### Implementation Prerequisites

- Evidence indexer over existing runtime-evidence files.
- GateRunner wrapper that can run existing scripts and ingest existing JSON without rerun.
- Byte decoder/visualiser that consumes `decoded_vpab_bytes.records`.
- Annotation sidecar writer.
- Tests for malformed JSON, missing raw log, missing frame log, stale annotation, rejected transport, missing channel, dark samples, and mode mismatch.

## Page 3 - Protocol Readiness / Authoring Lock

### User Job

When fixed built-ins are not enough, Captain or an agent needs to know whether VPML is ready to move toward uploaded programmes without the tool implying upload, compiler, or authoring support before transport and validator proof exist (`docs/forensics/vp_motion_lab/2026-06-09-vp-motion-lab-onwards-roadmap.md:469-486`).

### Primary Workflow

1. Show authoring as locked.
2. Display readiness checklist with current status.
3. Link missing ADR/spec/test artefacts.
4. Run or display protocol tests when they exist.
5. Run or display production-exclusion tests.
6. Keep upload/compiler panels hidden until all gates are green and Captain approves the next implementation phase.

This page is checklist-only in the current plan. It must not show disabled upload/compiler panels as fake affordances. The roadmap's later phrase "Upload panel disabled until transport gate exists" is superseded here by the same roadmap's higher-level acceptance rule that unsupported controls are deferred, not shown disabled (`docs/forensics/vp_motion_lab/2026-06-09-vp-motion-lab-onwards-roadmap.md:261-270`, `docs/forensics/vp_motion_lab/2026-06-09-vp-motion-lab-onwards-roadmap.md:537-544`).

### Controls

| Control | Host event | Current state |
|---|---|---|
| View Readiness Checklist | `protocol.readiness.view` | Available now. |
| Open Transport ADR | `protocol.adr.open` | Locked/missing until ADR exists. |
| Run Protocol Fixtures | `protocol.tests.run` | Locked until fixtures exist. |
| Run Production Exclusion Check | `protocol.production_exclusion.run` | Existing VPML static tests can inform current non-shippable state. |
| Unlock Authoring | `authoring.unlock.intent` | Hidden as a control; displayed only as final checklist outcome until approved. |

### Readbacks And Data Sources

| Field | Data source | Current value |
|---|---|---|
| Dedicated VPML transport ADR | Future doc path | Missing. |
| Command protocol specified | Future ADR/spec | Research sketch only, not implementation authority (`docs/forensics/vp_motion_lab/2026-06-09-vp-motion-lab-research.md:393-413`). |
| Session/sequence/offset/CRC/timeout specified | Future ADR/spec | Research requirements exist, but not a gate artefact (`docs/forensics/vp_motion_lab/2026-06-09-vp-motion-lab-research.md:364-390`). |
| Existing parser preserved | Static/source check | Current parser remains typed metadata path with 32-byte command type and 94-byte data (`SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h:2500-2565`). |
| Static receive buffers | Future firmware source | Missing until implementation. |
| Commit/play separation | Future protocol tests | Required by API notes (`docs/forensics/vp_motion_lab/2026-06-09-vp-motion-lab-research.md:434-445`). |
| Production exclusion | Existing static tests | `tests/test_vp_motion_lab_static.py:99-123`, `tests/test_vp_motion_lab_static.py:158-235`. |
| Corrupt stream fixtures | Future tests | Missing. |

### States

| State | Meaning |
|---|---|
| Locked / No ADR | No accepted transport ADR exists. |
| Locked / Design Draft | ADR exists but tests are absent or red. |
| Locked / Host Tests Green | Host protocol model exists, but firmware validator missing. |
| Locked / Firmware Validator Green | Firmware validates but no live upload proof. |
| Locked / Live Transport Failed | Live proof has dropped/corrupt/overflow or parser issues. |
| Transport Ready | ADR, host tests, firmware tests, production exclusion, and live transport proof are green. |
| Authoring Unlocked | Captain has approved moving into host compiler/authoring implementation. |
| Blocked / Raw Mode Requested | A proposed path requires raw receive mode. Current constraints forbid it. |
| Blocked / Parser Loosening | A proposed path weakens the existing serial parser. |
| Blocked / Compiler Too Early | Host compiler is requested before Page 2/Page 1 evidence loop acceptance. |

### Failure States

| Failure | Required handling |
|---|---|
| Parser loosening proposed | Block. Existing serial gate must not be weakened (`docs/forensics/vp_motion_lab/2026-06-09-vp-motion-lab-research.md:153-169`). |
| Raw receive mode proposed | Block for MVP. It is explicitly out of current constraints and must not be used unless separately accepted. |
| Host compiler appears before Page 2/Page 1 loop | Block. First evidence/page loop must be proven. |
| Upload implies persistence | Block. Upload cannot imply persistence (`docs/forensics/vp_motion_lab/2026-06-09-vp-motion-lab-research.md:434-445`). |
| Commit implies play | Block. Commit/play separation is required. |
| Partial programme can render | Block. Commit cannot render partial programmes (`docs/forensics/vp_motion_lab/2026-06-09-vp-motion-lab-onwards-roadmap.md:488-501`). |

### Must Not Claim

- Runtime code execution.
- Safe because host preview passed.
- Saved on K1.
- Upload works.
- Compiler exists.
- Authoring exists.
- Production candidate before Page 2 byte gate and Captain eyes-on.

### Acceptance Evidence

- Transport ADR accepted.
- Host protocol fixtures cover missing chunk, duplicate sequence, reorder, CRC mismatch, oversize, unsupported version, timeout, partial commit, and stale session.
- Firmware validator tests cover bad CRC, oversize, unsupported version, absolute sweep, rainbow/hue wheel, too many ops, and duration too long.
- Production env excludes VPML upload code.
- Live upload proof has zero dropped/corrupt/overflow and both primary/secondary VPAB proof.

### Implementation Prerequisites

- No Page 3 implementation beyond read-only lock until Page 2 evidence reader and Page 1 run console are accepted.
- Transport ADR.
- Host protocol model tests.
- Firmware parser/validator tests before firmware implementation.
- Explicit Captain approval to move beyond fixed built-ins.

## Deferred Page 4 - Promotion + Regression Ledger

### User Job

When a lab motion is useful, Captain or an agent needs a ledger that preserves evidence, acceptance, implementation path, and regression gates so native promotion does not lose proof or pollute production (`docs/forensics/vp_motion_lab/2026-06-09-vp-motion-lab-onwards-roadmap.md:559-598`).

### Build Conditions

Do not build this page until:

1. At least two byte-clean VPML programmes exist.
2. At least one has Captain eyes-on acceptance.
3. A native-promotion path has been attempted or scheduled.

### Controls

| Control | Current state |
|---|---|
| View Candidate | Deferred. |
| Link Evidence Chain | Deferred. |
| Create Promotion Decision Record | Deferred. |
| Attach Regression Gate | Deferred. |
| Mark Superseded | Annotation sidecar can support this earlier, but the ledger page waits. |

### Readbacks And Data Sources

| Field | Data source |
|---|---|
| Programme manifest | Future manifest or fixed built-in registry. |
| Capture list | EvidenceIndex/session manifests. |
| Byte gate status | VPML summary/frame gate JSON. |
| Eyes-on status | Annotation sidecar. |
| Native effect target | Future promotion decision record. |
| Open tasks | Future planning docs. |
| Production exclusion/inclusion decision | Future tests/build evidence. |
| Regression gate list | Future test plan. |

### States

| State | Meaning |
|---|---|
| Deferred | Build conditions unmet. |
| Candidate Available | Byte-clean plus eyes-on accepted candidate exists. |
| Promotion Planned | Native implementation plan exists. |
| Promotion In Progress | Native work has started under separate approval. |
| Promoted | Native implementation has its own tests/build/device evidence. |
| Rejected / Superseded | Candidate is archived. |

### Failure States

| Failure | Required handling |
|---|---|
| Lab proof treated as production proof | Block; native path requires separate implementation and gates. |
| Smart Director inclusion assumed | Block; Smart Director decision is separate. |
| Missing eyes-on acceptance | Cannot enter candidate state. |
| Missing evidence chain | Cannot promote. |
| Unrelated dirty files staged | Block promotion commit until staging list is isolated. |

### Must Not Claim

- Production readiness from lab proof alone.
- Smart Director inclusion.
- Audio modulation.
- Persistence.
- Native effect parity without native implementation evidence.

### Acceptance Evidence

One candidate has a complete chain:

1. Manifest or built-in registry entry.
2. K1 byte proof.
3. Captain eyes-on acceptance.
4. Native implementation plan.
5. Production exclusion or inclusion decision.
6. Relevant tests/build/upload evidence.

## Reliability And Failure Handling

| Risk | Fail-closed behaviour |
|---|---|
| Wrong device | Disable play/capture until chip ID matches expected target. |
| Probe firmware mistaken for product firmware | UI says "non-shippable harness"; product handback requires separate restore/verify. |
| Command timeout | Preserve raw log, mark state stale, require explicit retry. |
| Strict gate failure | Show failures before plots, block byte-clean and promotion. |
| Capture overflow | Treat as invalid proof, even if decoded records exist. |
| Missing source docs | Document source gap; do not invent reference authority. |
| Evidence/stale annotation mismatch | Mark annotation stale and require reconfirmation. |
| AP/WebSocket temptation | Keep local host UI transport separate from K1 AP contract. |
| UI overclaim | Separate badges: `transport`, `byte`, `motion readability`, `eyes-on`, `promotion`. |
| Worktree bundling | Stage only the new plan and any explicitly approved VPML files. |

## Trade-Offs

| Decision | Benefit | Cost | Verdict |
|---|---|---|---|
| Build Page 2 first | Proves existing evidence loop without touching devices. | Run console comes second. | Recommended first implementation slice. |
| Local host service over direct browser serial | Testable ports/adapters and reusable CLI/UI boundary. | More host plumbing. | Recommended. |
| Built-ins only in picker | Matches current firmware truth. | Slower creative breadth. | Required until protocol lock opens. |
| Page 3 lock before authoring | Prevents fake upload/compiler affordances. | Adds a page that mostly says "not ready". | Required to prevent scope creep. |
| Defer Page 4 | Avoids ledger UI with no candidates. | Promotion path remains manual. | Required for now. |
| Frame-owner VPML | Fast, isolated, avoids persisted mode IDs. | Does not exercise normal channel dispatcher semantics. | Accept for current built-ins; revisit later. |

## First Implementation Slice

Build **Page 2: Evidence Gate / Motion Readability** first as a data-only host tool using existing evidence files.

Scope:

1. Evidence index over the three current VPML captures.
2. Strict gate/summary ingestion.
3. Status classification:
   - `20260609T193511` -> byte-clean, eyes-on pending.
   - `20260609T193419` -> transport failed.
   - `20260609T190853` -> byte transport clean with dark-sample observation.
4. Centre-origin final-byte views.
5. Annotation sidecar schema.
6. Tests for accepted, rejected, dark-sample, missing files, malformed JSON, stale annotation, missing secondary, and mode mismatch.

No serial or device access is required for this slice.

## What To Revisit Later

1. UI shell decision: CLI-first, local web app, or both.
2. Whether local UI-to-host WebSocket/event stream is worth adding immediately.
3. Programme metadata registry generation from firmware source versus a checked-in host registry.
4. Channel-owned dev mode after frame-owner built-ins stop being enough.
5. Transport ADR and chunked upload protocol.
6. Host compiler syntax: JSON, YAML, or purpose-built `.vpml`.
7. Audio modulation, only after pure motion and protocol proof.
8. Promotion ledger, only after byte-clean and eyes-on accepted candidates exist.

## Delegation Ledger

| Delegation ID | Agent | Task | Classification | Source scope | Deadline | Status | Evidence consumed |
|---|---|---|---|---|---|---|---|
| `VPML-PAGE-JTBD-20260609` | Hooke | Review page jobs, workflow boundaries, state wording, and overclaim risks. | Load-bearing review sidecar | VPML docs plus governing docs | 5 minutes | Received | Consumed: Page 3 must be checklist-only; add explicit Blocked states; structure human acceptance; move capture cadence out of picker; add compare/rerun and supersession flow. |
| `VPML-ARCH-PROTOCOL-20260609` | Carver | Review current command/API boundary and future protocol lock requirements. | Load-bearing review sidecar | VPML source, serial menu, protocol docs, VPML research/roadmap | 5 minutes | Received | Consumed: current command boundary is fixed built-ins only; AP/REST/K1 WebSocket are out; Page 3 must preserve parser constraints and raw-receive prohibition. |
| `VPML-EVIDENCE-REDTEAM-20260609` | Chandrasekhar | Review evidence page states, failure states, tests, and overclaim blocks. | Load-bearing review sidecar | VPML runtime summaries, gate scripts, tests, VPML docs | 5 minutes | Received | Consumed: accepted/rejected/dark-sample evidence classification; safe wording; missing Page 2 tests for malformed/stale/rejected evidence; strict separation of byte proof from eyes-on acceptance. |

Subagent prose was not treated as proof by itself. Consumed claims were reconciled against the cited local sources already referenced in this document.
