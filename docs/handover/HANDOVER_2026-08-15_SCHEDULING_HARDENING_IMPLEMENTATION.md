---
abstract: "ACTIVE. Captain 2026-08-16 evening restamp: AP service p99 ≤ 8000 µs (6 ms / 0.8 fraction STRUCK). Hop remains 12.8 kHz/96/d3/7.5 ms (stamp A: no 10 ms hop). Gate 2 close-out = Cross40+Lane4 on k1_hardware. Gate 3 UNBLOCKED after G2 close-out. Live plan: docs/superpowers/plans/2026-08-16-scheduling-hardening-g2-g8.md. G0R cadence plan SUPERSEDED for live execution. AP-input P4 remains open. AP0/VP1 locked. F887 flash NO until G8 separate GO."
status: active
branch: feat/k1-scheduling-generation-hardening
active_lane: K1_SCHEDULING_HARDENING_20260815
authority_plan: docs/forensics/2026-08-15-freertos-scheduling-audit/EXECUTION_PLAN.md
live_task_plan: docs/superpowers/plans/2026-08-16-scheduling-hardening-g2-g8.md
g0r_plan: docs/superpowers/plans/2026-08-16-g0r-cadence-authority.md
g0r_plan_status: SUPERSEDED_FOR_LIVE_EXECUTION
captain_authorisation: FULL_UNRESTRICTED_SCHEDULING_IMPLEMENTATION_GO_2026-08-15
g0r_captain_stamp: A
service_restamp: G2_SERVICE_8000_2026_08_16
ap_input_p4_status: OPEN_SEPARATE_PROGRAMME
g0_oracle_implementation: CLOSED
g0_contract_content: AMENDED_SERVICE_P99_8000
g2_product_selection: CROSS40_PLUS_LANE4_CLOSE_OUT
g2_service: CLOSE_OUT_P99_8000
g3: UNBLOCKED_AFTER_G2_CLOSE_OUT
b489_flash: NAMED_GATES_ONLY_SEPARATE_GO
f887_flash: NO_UNTIL_G8
harness_firmware_pin_sha: 14c53d239524aa891e71470880f6917d4adf2ea6
final_abba_toolchain_pin_sha: c1aba345603bc2cacc8cf30648768d346f572779
deployed_contract_sha256: 8b0f5b31000d5dec27aecbdb84505f24ad5e0711a7fc8460827b13dde26df2cc
---

# Handover — K1 scheduling hardening implementation

## Captain authority receipt

Captain's direct instruction on 2026-08-15 is the implementation authority:

> You have full unrestricted authority to fully implement all the phases of the
> scheduling system hardening design end to end.

This authorises production scheduling-source mutation through the Gate 0-8 programme on
the named feature branch. It supersedes the scheduling audit's pre-implementation hold.

**2026-08-16 evening restamp (binding):** AP service p99 target is **8000 µs**, never
6000. The 0.8 × 7500 haircut is struck. Stamp **A** still forbids a 10 ms hop.
Gate 2 close-out selects **Cross40 + Lane-4**. Gate 3 is unblocked after that unit.
Live executable plan:
[`docs/superpowers/plans/2026-08-16-scheduling-hardening-g2-g8.md`](../superpowers/plans/2026-08-16-scheduling-hardening-g2-g8.md).

It does **not** silently declare the separate AP-input-integrity P4 programme complete and
does not authorise unrelated microphone slot, microphone-health default, calibration or
colour-lane promotion changes. Those remain governed by
`HANDOVER_2026-08-14b_AP_INPUT_INTEGRITY.md`.

## Binding implementation authority

Read in order:

1. this handover;
2. `docs/superpowers/plans/2026-08-16-scheduling-hardening-g2-g8.md` (live tasks);
3. `docs/forensics/2026-08-15-freertos-scheduling-audit/EXECUTION_PLAN.md`;
4. the reconciled audit `README.md` beside it;
5. `docs/agent/AGENT_EXECUTION_STANDARD.md`, `AGENT_OS.md` and `.claude/CLAUDE.md`;
6. `gate0/amendments/G2_SERVICE_8000_2026-08-16.json` + `gate0/contract.json`.

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
AP service p99                   = 8000 µs (absolute)
GDFT production contract         = Cross40 + Lane-4 (close-out)
```

## Physical and safety boundaries still binding

- Identity, not port, before any serial/device action.
- No upload, flash, erase or device-write without the exact environment-to-device guard
  and a **named** GO for that gate (`B489_G2_CONFIRM_FLASH`, `B489_G3_FLASH`, …).
- No `start_noise_cal` without Captain's explicit silence confirmation.
- Real-music timing/perceptual evidence requires Captain-confirmed audible music.
- Host/build green is not device, photon or perceptual proof.
- No implementation unit may weaken the oracle, fixtures, thresholds or CI that accepts it
  except the authorised 8000 µs restamp already landed.

## Immediate execution state (map–territory, 2026-08-16 evening)

```text
EXECUTION_MODE               = SEQUENTIAL_SINGLE_LANE
G0_ORACLE_IMPLEMENTATION     = CLOSED
G0_CONTRACT_CONTENT          = AMENDED_SERVICE_P99_8000
G0R_CAPTAIN_STAMP            = A (hop freeze; 10 ms NO)
TEN_MS_AP_HOP_AUTHORISED     = NO
AP_SERVICE_P99_LIMIT_US      = 8000
G1_B489_SMOKE                = VALID_CURRENT_IMPLEMENTATION
G1_F887_PRODUCTION           = ABSENT
G2_GDFT_CONTRACT             = CROSS40_PLUS_LANE4_CLOSE_OUT
G2_SERVICE                   = CLOSED
G2_DEVICE                    = CLOSED
G3                           = HOST_CLOSED
G6                           = NOT_REQUIRED
B489_FLASH                   = NAMED_GATES_ONLY_SEPARATE_GO
F887_FLASH                   = NO_UNTIL_G8
DEPLOYED_CONTRACT_SHA256     = 8b0f5b31000d5dec27aecbdb84505f24ad5e0711a7fc8460827b13dde26df2cc
LIVE_TASK_PLAN               = docs/superpowers/plans/2026-08-16-scheduling-hardening-g2-g8.md
G0R_PLAN                     = SUPERSEDED_FOR_LIVE_EXECUTION
```

G2 is CLOSED on bench `k1_bench_im69d` @ `e911f86d`. Next firmware units on
this branch are already in source (G3 sidecar freeze, G4 scene apply, G5
ratchet, G7A request mailbox). Remaining device work: named `B489_G3_FLASH`
(lock-margin), named `B489_G7B_FLASH` (real persist/cache), then G8 + separate
`F887_PRODUCTION_FLASH` GO. Do **not** start rolling ACF.

Historical Cross0/40/80 matrix and
`docs/forensics/runtime-evidence/20260816T-g2-lane4-cross40/` remain admissible
evidence. Under the 8000 µs gate the admitted music compact p99 (7712 µs) and
tempo-emit p99 (7792 µs) pass; they failed only the struck 6000 µs haircut.
