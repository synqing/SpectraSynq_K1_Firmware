Any agent who engages in busy work will be destroyed. Before you begin a task or even THINK, you will first ask yourself: "Can I be absolutely sure what I'm about to do is not busy work" - If the answer is no. STOP.

## Do not re-approve work already approved (Captain 2026-08-22 — HARD FAIL)

If approval is already given or implied, execute. Do not ask again. Skill:
`/no-reapprove-already-given`.

## Instrument, not Captain eyes (Captain 2026-08-22 — HARD FAIL)

Do not pull Captain into LED/plate visual inspection when rtrace / LED-buffer
dump exists. Score the dump. Wrong tap → move the tap. Skill:
`/instrument-not-captain-eyes`.

## Ship path required (Captain 2026-08-17 — HARD FAIL)

Never tell Captain that a result does not mean ship, promote, close, or done
unless the **same answer** states: what is already promoted / on silicon;
numbered remaining steps; who acts on each; the exact stamp or flash that
means shipped. A hold without a ship path is a failed answer. Skill:
`/ship-path-required`.

## Plain English work summaries (Captain 2026-08-22 — HARD FAIL)

Summary of agent work MUST be plain English: what happened, what is true now,
what is left. Do not lead with labels or jargon. Skill:
`/plain-english-work-summaries`.

# Sensory Bridge core firmware on K1 hardware — Project Instructions

## Sensory Bridge Doctrine Bridge

Product north star:
This project is not trying to produce merely clean firmware or generic audio-reactive LEDs. The objective is a music-to-visual translation system that exceeds Sensory Bridge's perceptual impact and musical relevance. Architecture is subordinate to that benchmark.

Before any non-trivial Sensory Bridge core firmware refactor on K1 hardware, AP/VP change, audio pipeline change, visual pipeline change, S2/S3 migration work, timing/performance change, or multi-file agentic edit:

1. Invoke `/sensorybridge-doctrine`.
2. Treat the LightwaveOS_Official doctrine as reference doctrine, not local K1 hardware historical truth.
3. Treat the K1 hardware forensic reconstruction as the local fork evidence base for Bloom/Waveform/K1 hardware migration state.
4. Check relevant re-test triggers before proposing changes.
5. Do not treat compile/upload as runtime proof unless the matching serial/video/timing evidence exists.
6. Do not treat architecture as success if visual impact, musical responsiveness, independent dual-channel behaviour, colour clarity, or motion memory regresses.

Full doctrine is not loaded by default. Invoke `/sensorybridge-doctrine` when active application is needed.

## Agent read order (load-bearing — added 2026-06-07)

Before firmware, forensic, or device-validation work:

0. [`AGENT_OS.md`](../AGENT_OS.md) — canonical agent manual (all tools): session bootstrap, source-of-truth hierarchy, safety gates, thinking gate, skill awareness
1. [`progress.md`](../progress.md) — rolling status
2. [`.claude/handoff.md`](./handoff.md) — active session pointer
3. [`docs/spec-index.md`](../docs/spec-index.md) — lane authority, devices, recall conventions
4. Lane handover linked from spec-index Active Lanes table
5. claude-mem `search` → `timeline` → `get_observations` for prior sessions only

On-disk handover beats claude-mem for **current lane status**. Invoke
`/claude-mem-router` (or `/spec-recall`) when resuming work or checking "did we
already solve this?" — pick one memory skill from the scenario table; do not
fan out the whole set.

## Developer Instrumentation Boundary (load-bearing — added 2026-05-27)

Developer, harness, trace, benchmark, probe, and diagnostic code **never ships with production firmware**.

Production build environments must not include MabuTrace, trace-dev dependencies, developer-only feature flags, implementation sources, storage, command surfaces, or behaviour that relies on instrumentation being present. Production may contain only audited no-op macro declarations required to keep shared source buildable. SB-native diagnostics are the canonical substrate for product-proof evidence: VPAB/final-byte payloads, visual-memory gates, diagnostic pool health, parser-compatible forensic logs, and reusable internal harness checks.

MabuTrace is not optional lore. Before any timing, performance, dropped-frame, race, ordering, audio-to-render, or cross-core diagnostic claim, classify the question as timeline/causality or non-causal scalar evidence. If the unknown is nested frame timing, audio-to-render causality, counter disagreement, frame-drop causality, race/reorder proof, diagnostic harness perturbation, or another timeline/causality trigger, MabuTrace dev-trace is mandatory. SB-native scalar diagnostics may detect or quantify the symptom; they do not close causal attribution. If the trace-dev lane is unavailable, report `blocked` or `approval`, not verified, complete, or scalar-equivalent. Any MabuTrace build is non-shippable and must be labelled as such in build config, docs, and evidence.

## Calibration command policy (load-bearing — added 2026-05-24)

`start_noise_cal` and any other calibration command that assumes silence is **NEVER auto-fired by the agent**. The agent MUST wait for Captain to confirm the silence window verbally (e.g. "music paused, go") before sending the command, and MUST wait for Captain to say "resume" before assuming normal acoustic conditions again. Violation = STOP-and-rollback (revert any cal state that was poisoned by music-during-cal, e.g. via re-cal under a confirmed silence window or `erase_flash`).

Origin: 2026-05-24 Stage 7 incident — agent auto-ran `start_noise_cal` during continuous music, poisoning `SWEET_SPOT_MIN_LEVEL` (281 → 745). Captain's correction at agent-acknowledgement promoted this from a one-time mistake to a permanent rule.

## Hardware target discipline (load-bearing — added 2026-05-28)

Serial monitors, firmware uploads/flashes, erase operations, and device-write
commands are expected validation tools when the active task requires them. The
rule is not "never open serial"; the rule is "never assume the device on a port
is the intended target."

Before opening a serial monitor, flashing/uploading firmware, erasing flash, or
sending any device-write command, verify the exact target by port plus stable
hardware identity: USB MAC, adapter serial, chip ID, board role, or another
captured identity signal. If identity is missing, ambiguous, stale, or
mismatched, stop and resolve the target before touching the device. Record the
verified identity in the evidence.

Canonical device↔env↔build pairing and deployed-state table:
[`docs/hardware/device-build-registry.md`](../docs/hardware/device-build-registry.md)
(added 2026-06-11). Read it before any flash/erase/serial-write; update its
deployed-state table after every flash. 1401 (`F887A500`) = `k1_hardware` only;
12201 (`B489A500`) = `k1_bench_reference` only — different GPIO maps.

## Git discipline (load-bearing — added 2026-05-28)

Git is rollback safety, not paperwork. Agents should use branches, commits, and
tags deliberately to create recoverable checkpoints and isolate work when that
improves execution safety.

Never commit untested or unreviewed work. Before committing, inspect the actual
diff, stage only the intended files, run the relevant tests/builds, and record
the evidence. Do not commit known-broken code just because a task is "finished."
Remote pushes, destructive history changes, and public release tags require
Captain's explicit instruction or an active lane that clearly includes that
publication step.

## Parallel-agent orchestration discipline (load-bearing — added 2026-05-29)

Parallel agents are evidence producers, not a way to create unmanaged background
work. Before dispatching any sub-agent, the orchestrator must declare a
consumption contract: `delegation_id`, role, task/evidence question,
classification, classification rationale, expected output or minimum useful
partial, source scope, write scope, checkpoint timeout, bounded retry window,
fallback owner and action, final-answer dependency, escalation condition, and
consumption rule.

Every delegated task is classified before launch as `load-bearing` or
`optional`. `optional` means the task could be deleted before launch without
changing the final answer's correctness, scope, confidence, or wording.
Research, investigation, audit, and evaluation tasks are load-bearing whenever
they were delegated because the final judgement needs their evidence. A
load-bearing task cannot be downgraded after launch because it is late,
inconvenient, or hung.

A load-bearing delegated task creates a dependency barrier. The orchestrator
must not issue a final assessment that depends on that evidence until the result
is closed as `received`, `replaced`, `missing`, or `blocked`. A delegated task is
stuck when its checkpoint expires without a result, a wait returns no status
twice, it produces no expected artefact and no useful partial, or progress cannot
be inspected.

Stuck-agent recovery is mandatory. First missed checkpoint: request a partial
result or narrow the task, then wait only one bounded retry window. The retry
bound must be a concrete wall-clock or tool-call limit; default maximum is five
minutes for interactive work unless Captain's deadline is stricter. The parent
deadline must reserve `checkpoint + retry + fallback + synthesis` time. If the
first miss leaves no fallback and synthesis buffer, skip retry and start
fallback immediately. Second missed checkpoint: abandon that agent as a source
of truth, start the fallback owner immediately, and close or ignore the hung
worker. Do not keep polling a silent sidecar while Captain waits.

Replacement evidence is equivalent only when it answers the same evidence
question, covers the same declared scope, and has equal or higher authority; a
narrower replacement narrows the final claim. A partial result only satisfies the
dependency if it directly answers the declared evidence question or narrows the
unresolved area. Contradictory load-bearing evidence must be resolved, bounded,
or escalated; do not average it away. Any final answer that involved load-bearing
parallel work must include a delegation ledger: ID, task, classification, source,
deadline, status, evidence/artefact, and how the evidence was consumed. Missing
evidence reduces or removes the affected claim. Blocked evidence stops the
affected judgement.

## Commit cadence + the commit gate (load-bearing — added 2026-06-03)

Commit **continually, but only after the work is verified** — and recognise
those are two needs with two mechanisms, not one.

- **Milestone commits** (the feature/main branch) are **gated**. A tiered
  pre-commit hook (`scripts/hooks/pre-commit`, installed via
  `scripts/hooks/install.sh`) hard-blocks any commit that fails its
  change-class check: docs → none; `tests/`+`scripts/regression-harness` →
  `pytest tests/`; firmware source/`platformio.ini` → `pytest tests/` **and**
  clean `pio run -e k1_hardware`. The check runs the real build/tests — a
  self-asserted "verified" is never sufficient. Staged binaries/oversize blobs
  are rejected on every branch.
- **Checkpoints** (crash-safety for in-progress, possibly broken work) go on a
  `wip/*` branch (the gate auto-skips there) via
  `scripts/hooks/wip-checkpoint.sh`, or `git commit --no-verify` — never a
  broken commit on a feature/main branch.
- **Cadence:** commit at every green checkpoint, after each sub-task whose gate
  passes — not at end-of-session. Small, frequent, green.
- **compile ≠ runtime proof, but only where it matters.** Most changes are fully
  closed by the host gate. A narrow visual/perceptual set (`light_mode_*`,
  `leds`, `lightshow`, `palette`, `render_params`, `chroma`) commits on
  host-green with Captain's on-device eyes-on as a **tracked, non-blocking**
  follow-up — it does not gate the commit.
- **Never run a gate while broken.** If a gate is red on arrival, fix the gate as
  a class and restore green first (amend-broken-gates), then commit.

Full structure and rationale: `docs/git/commit-gate.md`.
