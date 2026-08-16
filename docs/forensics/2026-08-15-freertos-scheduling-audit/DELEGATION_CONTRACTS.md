# FreeRTOS scheduling audit — delegation contracts

All tasks are read-only except for their single assigned evidence file. Every agent must
abort unless `git -C /Users/spectrasynq/SpectraSynq_K1_Firmware rev-parse --show-toplevel`
returns the exact repository path. No agent may edit firmware, flash, upload, monitor a
device, commit, install dependencies, or change any other file. Checkpoint: 15 minutes;
one 5-minute request-for-partial retry; fallback owner: orchestrator-local.

## FRTOS-01 — task topology

- Classification: load-bearing.
- Evidence question: What tasks, loops, callbacks, ISRs and pollers exist, and what are
  their core affinities, priorities, stack sizes, cadences and blocking/yield semantics?
- Source scope: firmware source, `platformio.ini`, relevant tests and current docs.
- Required artefact: `evidence/task-topology.md` with file:line citations and exact rerun
  searches.
- Failure mode: trusting stale architecture prose or historical line numbers.
- Consumption: only source-cited claims survive orchestrator rerun.

## FRTOS-02 — Core-0 audio path

- Classification: load-bearing.
- Evidence question: What is the exact I2S-to-audio-semantic execution path on Core 0,
  including DMA wait, DSP stages, publication, WDT, delay, compute budget and priority
  inversion/starvation risks?
- Source scope: audio, system, main sketch, timing diagnostics/tests/current evidence.
- Required artefact: `evidence/core0-audio.md` with causal timing chain and rerun commands.
- Failure mode: conflating chunk duration, AP throughput, active CPU time and latency.
- Consumption: decision-critical claims require orchestrator source reread.

## FRTOS-03 — Core-1 render path

- Classification: load-bearing.
- Evidence question: What is the exact snapshot-to-final-LED execution path on Core 1,
  including transitions, effects, dual-edge composition, FastLED/RMT, WDT/delay and spare
  capacity evidence?
- Source scope: main sketch, visual/effects/director/LED modules and timing diagnostics.
- Required artefact: `evidence/core1-render.md` with file:line citations and rerun commands.
- Failure mode: inferring idle capacity from nominal FPS or assuming FastLED behaviour.
- Consumption: source facts accepted after rerun; capacity claims remain bounded by data.

## FRTOS-04 — control, radio, persistence and queues

- Classification: load-bearing.
- Evidence question: Which non-audio concerns execute on Core 0 or create their own tasks,
  how are requests bounded, and where can serial, AP WebSocket, BLE, sync, flash/persistence
  or queue drains interfere with hard-real-time audio?
- Source scope: network, serial, control, persistence, platform flags and contracts.
- Required artefact: `evidence/control-radio-persistence.md` with production-vs-probe
  boundaries and exact rerun commands.
- Failure mode: promoting bench-only radio risks into production claims.
- Consumption: claims split by production env and feature flag.

## FRTOS-05 — concurrency primitives and data ownership

- Classification: load-bearing.
- Evidence question: What queues, task notifications, semaphores, mutexes, critical
  sections, atomics, volatile/shared globals and halt barriers exist, and which cross-core
  ownership contracts are actually enforced?
- Source scope: all firmware source plus concurrency tests/audits.
- Required artefact: `evidence/concurrency-primitives.md` with inventory and hazard ranking.
- Failure mode: judging safety from names or from generic actor-model doctrine.
- Consumption: every high-severity finding must cite the exact live declaration and use.

## FRTOS-06 — adversarial scheduling alternatives

- Classification: load-bearing.
- Evidence question: Try to refute each option: keep two-loop architecture; add task
  priorities/cadence control only; split audio actors; offload DSP to Core 1. Which option
  survives the hard product constraints and current evidence?
- Source scope: current source, timing/forensic evidence, prior rejected designs.
- Required artefact: `evidence/red-team-options.md` with assumptions, attack scenarios,
  evidence gaps and a provisional verdict.
- Failure mode: architecture aesthetics, framework preference or false precision.
- Consumption: provisional until orchestrator applies KT scoring and rereads decisive facts.

## FRTOS-07 — publication lifetime and event semantics

- Classification: load-bearing.
- Evidence question: Does Captain's VP-local copy proposal close the two-slot lifetime
  hole, and what exact ownership semantics are required for continuous state, onset/beat
  edges, complete desired-state commands, non-idempotent commands and telemetry?
- Source scope: current publication/control source, original audit and post-review list.
- Required artefact: `evidence/publication-event-plan-review.md` with explicit invariants,
  failure interleavings and gate criteria.
- Failure mode: approving an attractive primitive without proving buffer lifetime or
  event-loss semantics.
- Consumption: orchestrator must independently reconcile every recommended invariant.

## FRTOS-08 — gate, oracle and contract architecture

- Classification: load-bearing.
- Evidence question: Does the updated Gate 0-8 programme pace by proof, keep behaviour-
  changing lanes separate, and provide a fault-evident oracle for each implementation
  unit without turning the plan into governance theatre?
- Source scope: current audit, post-review list, active P4 authority and existing tests.
- Required artefact: `evidence/gate-oracle-plan-review.md` with a minimal gate DAG,
  acceptance owners, negative tests and stop/rollback rules.
- Failure mode: letting implementation agents self-certify or building a harness larger
  than the contained firmware changes.
- Consumption: orchestrator retains only gates tied to a concrete failure or decision.

## Implementation read-through and Gate 0 delegations

### Shared contract — FRTOS-09 through FRTOS-17

```text
classification:          load-bearing
classification_rationale: full-source priming and independent Gate 0 evidence are prerequisites to production implementation
forbidden_actions:       no firmware/test/harness/CI edits; no build, upload, flash, erase, serial/device action, commit, push or edit outside the named evidence file
checkpoint_timeout:      5 minutes
bounded_retry:           one 3-minute request for a useful partial after the first miss
fallback_owner:          orchestrator-local
final_answer_dependency: no
escalation_condition:    second missed checkpoint or failure to produce the named artefact
consumption_rule:        reconcile against live source; missing evidence blocks the affected gate until orchestrator-local replacement
collaboration_rule:      other agents share this checkout; never revert, reformat or overwrite their work
```

| ID | Role / task | Expected output | Source scope | Write scope |
|---|---|---|---|---|
| FRTOS-09 | exhaustive source reader 1; read every file in manifest chunk 1 in full and identify scheduling/publication/timing implications | complete file ledger plus findings in `evidence/codebase-read-1.md` | `/tmp/k1-source-manifest.WdLSdO/chunk_1.txt` | named evidence file only |
| FRTOS-10 | exhaustive source reader 2; same contract for chunk 2 | `evidence/codebase-read-2.md` | `/tmp/k1-source-manifest.WdLSdO/chunk_2.txt` | named evidence file only |
| FRTOS-11 | exhaustive source reader 3; same contract for chunk 3 | `evidence/codebase-read-3.md` | `/tmp/k1-source-manifest.WdLSdO/chunk_3.txt` | named evidence file only |
| FRTOS-12 | exhaustive source reader 4; same contract for chunk 4 | `evidence/codebase-read-4.md` | `/tmp/k1-source-manifest.WdLSdO/chunk_4.txt` | named evidence file only |
| FRTOS-13 | exhaustive source reader 5; same contract for chunk 5 | `evidence/codebase-read-5.md` | `/tmp/k1-source-manifest.WdLSdO/chunk_5.txt` | named evidence file only |
| FRTOS-14 | exhaustive source reader 6; same contract for chunk 6 | `evidence/codebase-read-6.md` | `/tmp/k1-source-manifest.WdLSdO/chunk_6.txt` | named evidence file only |
| FRTOS-15 | exhaustive source reader 7; same contract for chunk 7 | `evidence/codebase-read-7.md` | `/tmp/k1-source-manifest.WdLSdO/chunk_7.txt` | named evidence file only |
| FRTOS-16 | verification-harness auditor; inventory existing deterministic, replay, property, mutation, timing and device gates reusable for Gate 0 | `evidence/gate0-harness-inventory.md`; minimum partial is a boundary-to-oracle table with blind spots | `tests/`, `scripts/regression-harness/`, `scripts/agent/`, `platformio.ini` | named evidence file only |
| FRTOS-17 | adversarial Gate 0 architect; attack authority, determinism, fault battery, anti-gaming and acceptance ownership | `evidence/gate0-fault-battery-review.md`; minimum partial is the smallest fault battery that can kill each required failure class | execution plan, existing audit evidence, current tests and harness scripts | named evidence file only |

All seven source readers must include the manifest SHA, every assigned path, an explicit
`READ_IN_FULL` or failure status per file, and a final count matching the chunk. A grep-only
summary does not satisfy `learn-codebase`.
