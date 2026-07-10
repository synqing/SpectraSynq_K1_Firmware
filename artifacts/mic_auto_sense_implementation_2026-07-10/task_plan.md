# Mic Auto-Sense Implementation Plan

Date: 2026-07-10
Repo: `/Users/spectrasynq/SpectraSynq_K1_Firmware`
Live checkout: `lane/dual-sync-phase0 @ cc97081`

## Goal

Deliver the K1 mic auto-sense feature only after research proves a bounded, testable, repo-consistent implementation path. Default gate: research first; implementation begins only after design, safety, tests, branch authority, and Captain decision points are resolved.

## Current Phase

Phase 0 - research and gate definition.

## Phases

| Phase | Status | Exit criteria |
| --- | --- | --- |
| 0. Authority and memory | complete | Bootstrap, docs, memory, and prior synthesis recorded. |
| 1. SSA research fan-out | complete | Independent code/design/test/risk SSAs returned artifacts within timed waits. |
| 2. Orchestrator verification | complete | Decision-critical SSA claims were checked against live source and governing docs. |
| 3. Implementation decision gate | complete | Captain selected live `lane/dual-sync-phase0 @ cc97081` and telemetry-only Phase 1. |
| 4. Implementation | complete | Default-off telemetry-only module, AP fields, telemetry env, wrapper, tests, and upload guard landed. |
| 5. Verification | complete-with-known-blocker | Host/static/full pytest and guarded builds pass; stable-byte gate fails on clean HEAD with same hashes, so it is a pre-existing stale-reference blocker. |

## Non-Negotiables

- No automatic `start_noise_cal`, `N`, or `Y`.
- No hidden adaptive scale during raw/purity measurement modes.
- No v1 persistence writes from the auto-sense path.
- No heap, `String`, blocking I/O, serial printing, or expensive work in the audio hot path.
- Default-off flag for any new behaviour.
- Applied scale remains `1.0f` for telemetry-only slice unless Captain explicitly authorises controller behaviour.

## Open Decisions

1. Confirm intended implementation branch: live `lane/dual-sync-phase0` versus handoff-named `lane/im73d-pdm-eval`.
2. Confirm feature slice: telemetry-only Phase 1, shadow recommendation Phase 5, or applied runtime controller.
3. Confirm whether any device proof is in scope for this session; if yes, identify target by MAC/chip/env before action.

## SSA Ledger

| ID | Task | Classification | Status | Evidence path | Consumed as |
| --- | --- | --- | --- | --- | --- |
| MAS-CODE-01 | Source seam and existing telemetry map | load-bearing | complete (`019f4b62-4786-7380-9653-300bb71a1873`) | `findings/ssa_code_seam.md` | accepted: telemetry/AP seam |
| MAS-TEST-01 | Test/build/gate plan | load-bearing | complete (`019f4b62-4cc3-7791-bad2-47b460dbf1a1`) | `findings/ssa_test_plan.md` | accepted: focused host/static/build matrix |
| MAS-RISK-01 | Real-time safety and failure modes | load-bearing | complete (`019f4b62-52a9-7652-b847-3f7fc000a25f`) | `findings/ssa_risk_review.md` | accepted: blocker list and stop conditions |
| MAS-DESIGN-01 | Controller architecture and TRIZ contradiction resolution | load-bearing | complete (`019f4b62-5e49-7c93-b068-949c2d0ab15c`) | `findings/ssa_design_review.md` | accepted: telemetry-only shadow scaffold |

## Errors / Blockers

- `docs/agent/AGENT_EXECUTION_STANDARD.md` referenced by AGENTS is absent in the checkout.
- `firmware-v3/docs/reference/codebase-map.md` and `firmware-v3/docs/reference/fsm-reference.md` are absent in this repo layout.
- Live branch does not match `AGENT_OS.md` current-lane text (`lane/dual-sync-phase0` vs `lane/im73d-pdm-eval`). `AGENT_OS.md:51-62` says to stop and report this conflict before work if git shows a different branch.
- Captain resolved branch/scope for this task via input: use current branch and execute telemetry-only first slice.
- `mic_stable_byte_gate.sh` fails for `k1_hardware`, `k1_bench_reference`, and `k1_bench_im73d`; detached clean `HEAD` reproduces the same drift hashes, so this is not introduced by the mic auto-sense patch.

## Current Recommendation

Implemented Phase-1 telemetry-only scaffold:

- Default-off `K1_MIC_AUTO_SENSE_V1`.
- Added `audio/k1_mic_auto_sense.{h,cpp}` and compile it only in `k1_bench_im73d_mic_auto_telemetry`.
- Report read-only `mas_*` state/health through the existing 1 Hz AP telemetry surface when the flag is enabled.
- Keep applied scale `1.0f`.
- Do not write `CONFIG.SENSITIVITY`, persistence, calibration, REST, WebSocket controls, loud-guard thresholds, GDFT AGC, or DSR defaults.
- Verified with focused static/parser tests, full pytest, guarded `k1_hardware` / `k1_bench_im73d` / `k1_bench_im73d_mic_auto_telemetry` builds, and upload-guard registration.
