---
abstract: "ACTIVE. Captain authorised end-to-end implementation of the K1 scheduling hardening Gate 0-8 programme on feat/k1-scheduling-generation-hardening. This supersedes the scheduling lane's pre-implementation hold, while leaving the separate AP-input-integrity P4 promotion decision open. AP0/VP1 remains locked; harness and fault evidence precede production units."
status: active
branch: feat/k1-scheduling-generation-hardening
active_lane: K1_SCHEDULING_HARDENING_20260815
authority_plan: docs/forensics/2026-08-15-freertos-scheduling-audit/EXECUTION_PLAN.md
captain_authorisation: FULL_UNRESTRICTED_SCHEDULING_IMPLEMENTATION_GO_2026-08-15
ap_input_p4_status: OPEN_SEPARATE_PROGRAMME
---

# Handover — K1 scheduling hardening implementation

## Captain authority receipt

Captain's direct instruction on 2026-08-15 is the implementation authority:

> You have full unrestricted authority to fully implement all the phases of the
> scheduling system hardening design end to end.

This authorises production scheduling-source mutation through the Gate 0-8 programme on
the named feature branch. It supersedes the scheduling audit's pre-implementation hold.

It does **not** silently declare the separate AP-input-integrity P4 programme complete and
does not authorise unrelated microphone slot, microphone-health default, calibration or
colour-lane promotion changes. Those remain governed by
`HANDOVER_2026-08-14b_AP_INPUT_INTEGRITY.md`.

## Binding implementation authority

Read in order:

1. this handover;
2. `docs/forensics/2026-08-15-freertos-scheduling-audit/EXECUTION_PLAN.md`;
3. the reconciled audit `README.md` beside it;
4. `docs/agent/AGENT_EXECUTION_STANDARD.md`, `AGENT_OS.md` and `.claude/CLAUDE.md`;
5. the current Gate receipt in the audit pack.

## Locked destination

```text
AP owner                         = Core 0
VP owner                         = Core 1
broad RTOS rewrite               = rejected
multi-actor AP chain             = rejected
coherent AP generation           = required
state/event/command distinction  = required
explicit audio task              = conditional experiment only
real flash servicing             = separate safety gate
radio and 24 kHz/180-bin work    = separate programmes
```

## Physical and safety boundaries still binding

- Identity, not port, before any serial/device action.
- No upload, flash, erase or device-write without the exact environment-to-device guard.
- No `start_noise_cal` without Captain's explicit silence confirmation.
- Real-music timing/perceptual evidence requires Captain-confirmed audible music.
- Host/build green is not device, photon or perceptual proof.
- No implementation unit may weaken the oracle, fixtures, thresholds or CI that accepts it.

## Immediate execution state

The implementation branch begins at `9259a9d5`. Gate 0 is active. Production source does
not change until the current harness inventory, determinism contract and named fault battery
have demonstrated RED capability. Decision-critical units then advance serially through the
Gate 0-8 DAG with an independently re-run post-integration gate.
