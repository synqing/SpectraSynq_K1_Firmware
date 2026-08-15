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

The implementation branch began at `9259a9d5`. Gate 0 was independently accepted at
`68c9a51e`. Gate 1 now has a host/build-green trace surface and a guarded B489A500
bench smoke: two-channel RMT completion is observed without drops, while both short
scalar bench probes show AP service demand above the nominal 7.5 ms arrival period.
That RED service-capacity result admits Gate 2 without authorising priority or task
changes. Gate 1 remains open for the exact-production F887A500 quiet/music/crossfade
baseline and Captain-confirmed audible real-music fixture.

Gate 2 now has a source-parity, one-variable cross0/cross40/cross80 probe matrix. All
three B489A500 environments build and 105 focused geometry/semantic/static tests pass.
The actually executed resonator iteration totals are 34,254 / 18,550 / 17,109; the
older 34,484 figure included bins skipped before the inner loop. No production crossover
has been selected: the bench disconnected before paired device and Captain-confirmed
real-music acceptance, so Gate 3 remains dependency-blocked rather than being started on
an unproven GDFT service contract.

The bench subsequently reconnected. The first six 15-second acquisitions were only
partial serial-export prefixes and are retained solely as negative witnesses. The
capture path now fails incomplete dumps visibly, and a corrected complete six-run matrix
was recorded on B489A500: cross0/cross40/cross80 with no host playback and with
Captain-confirmed audible `Anchor Point`. Cross0 ran 92.86 Hz under music; cross40
recovered 127.85 Hz; cross80 recovered 132.68 Hz. All three miss the pre-registered 6 ms
active-work p99 ceiling (music p99 11.82 / 8.72 / 8.42 ms respectively). The sequential
20-second eyes-on A/B was explicitly rejected by Captain as inconclusive. Product
acceptance now requires at least two authorised K1 units running different builds
simultaneously for 30–60 minutes across multiple real tracks. Only B489A500 is present,
so Gate 2 is blocked/open and Gate 3 must not begin. The bench is restored to the cross0
baseline; the durable `:build` readback names git `35de4e53` and the exact baseline env.

Gate-2 decomposition then falsified further work spreading as a complete repair: even
perfect three-frame levelling of the measured workload misses 6 ms under real music. A
hop-incremental backend was implemented as a bounded probe and removed after it exceeded
the one-code spectral bound and changed the impulse winner on 15/24 frames. The direct
fixed-point recurrence is non-linear under per-step Q14 truncation and cannot be safely
decomposed by a conventional sliding transform.

An exact four-lane direct-recurrence probe remains non-shippable but reusable. Host
differential is bit-identical across all 71 safe bins and adversarial fixtures. On
B489A500 it reduced real-music GDFT median from 7.174 ms to 4.896 ms, but full AP p99 was
still 8.590 ms and cadence 126.30 Hz. It therefore fails Gate 2 and is not promoted. The
bench was restored again to `k1_bench_scheduling_baseline_probe`, running git `2c0db532`,
epoch `1786786833`. The active engineering node is now non-shippable detailed residual-
stage attribution; Gate 3 remains dependency-blocked.

The residual-stage attribution surface is now independently accepted at the
source/host/build boundary. Capture-only timing records cover pre-I2S service, I2S,
VU/sweet-spot work, GDFT, post-GDFT service, novelty, snapshot/configuration, onset,
saliency, the full tempo call and the post-publication loop tail. Thirteen ordered
offsets make each derived span mechanically checkable; the monolithic GDFT internal
split is explicitly unavailable rather than fabricated. The FULL endpoint is after
benchmark, optional encoder and debug service and immediately before `vTaskDelay(1)`.
The parser rejects missing, zero, misordered or inconsistent FULL attribution. The
canonical host gate passes (`1165 passed, 1 skipped`), and both `k1_hardware` and
`k1_bench_scheduling_baseline_probe` build. This is not yet device evidence: the next
node is an identity-gated complete B489A500 capture and attribution-led repair choice.
