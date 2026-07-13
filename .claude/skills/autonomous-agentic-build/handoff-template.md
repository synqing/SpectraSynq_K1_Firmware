---
abstract: "Paste-ready, project-agnostic execution order for a long-running autonomous multi-agent build/migration/refactor. Copy it, fill the <…> slots, hand to an executor. v2 — pluggable oracle, determinism contract (Gate −1), infra-run gate (agents can't self-certify), fleet governance, completion predicate. Doctrine: the autonomous-agentic-build skill."
---

# Autonomous Agentic Build — Handoff Template (v2)

> Copy the block below, fill every `<…>` slot, delete this heading, hand it to your executor
> (orchestrator agent or engineer). Doctrine + rationale: the `autonomous-agentic-build` skill.

```
AUTONOMOUS LONG-RUNNING AGENTIC BUILD — EXECUTION ORDER
System / repo: <SYSTEM/REPO>   ·   Orchestration: <Workflow / agent fleet / tool>
Decision authority: <who ratifies + signs gates>

WHEN TO USE / RIGHT-SIZE
A large, long-horizon body of work executed by many agents autonomously and in parallel.
Behavior-preserving work is the default; behavior-changing work is isolated. Do NOT stand up this
apparatus for a change too small to need it — justify by volume × risk × autonomy-duration.

THE LAW (non-negotiable)
- The VERIFICATION HARNESS IS THE PRODUCT; the work is only what flows through it. A weak oracle does
  not slow autonomy — it lets agents confidently mass-produce broken work that PASSES.
- Pace by GATES, NOT DATES. The only true constraints are the oracle + the human/real-world checkpoints
  autonomy cannot self-certify.
- The method is FAULT-EVIDENT, not fail-proof: "all gates green" = "no regression detected in the
  measured envelope," NEVER "behavior preserved." Name the residual gap; don't hide it.

STEP 0 — INVENTORY BEFORE YOU INVENT (highest leverage)
Find existing verification assets (tests, replay harnesses, golden files, staging, the still-running old
system) and FORMALIZE them. Existing assets: <what already exists>.

CHOOSE THE ORACLE (pluggable — pick per boundary)
  Brownfield + deterministic      → GOLDEN-MASTER (freeze baseline outputs; reproduce exactly)
  Brownfield + baseline runnable   → DIFFERENTIAL (old vs new, diff live; no staleness — best for long runs)
  Nondeterministic / no reference  → PROPERTY + METAMORPHIC (invariants + input→output relations)
  Greenfield / behavior-changing   → EXECUTABLE SPEC / ACCEPTANCE (spec or reference impl IS the oracle)
  Oracle type per boundary: <boundary → oracle type>

GATE −1 — DETERMINISM CONTRACT (before freezing anything)
Seed RNG; inject the clock; pin concurrency/thread order; freeze IDs/timestamps; sort unordered
collections; isolate the network. Run the baseline N times; derive each boundary's tolerance EMPIRICALLY
from observed variance — never guess epsilon. Determinism controls: <controls applied>.
Per-boundary tolerances (empirical): <tolerances + how derived>.

PHASE 0 — BUILD AND PROVE THE HARNESS
1. Oracle: deterministic, committed, checksummed input/scenario battery over the real envelope
   (normal/edge/stress/failure/real-world). Battery: <input/scenario battery>.
   Capture outputs at EVERY observable boundary: <observable boundaries to tap>.
   Frozen master (if used): IMMUTABLE, checksummed, owned OUTSIDE the fleet's write scope.
   If the master changes, BEHAVIOR CHANGED → human-approved ticket, NEVER an autonomous edit.
   BATTERY COVERAGE GATE: measure code coverage of the battery; equivalence over un-exercised code is
   vacuous. Unexercised critical paths: <list / none>.
2. Per-unit gate (binary — ALL required; RUN BY INFRA, not the agent):
   a. Builds / compiles / lints clean:  <build cmd>
   b. Oracle satisfied within characterized tolerance at EVERY boundary, on the POST-MERGE HEAD.
   c. Full suite green (<test cmd>); ZERO tests deleted/skipped vs baseline; coverage floor (code +
      battery) not reduced.
   d. NO harness / oracle / golden / CI / branch-protection file modified by the unit.
   e. Units touching human-judgment-only surfaces flagged into the human review queue.
3. Anti-gaming: oracle + harness checksummed-immutable (any diff by a lane = auto-FAIL);
   test-deletion/skip detector + coverage floor; ROLLBACK-ON-RED (can't go green → reverted, never merged).
4. GATE 0 — fault-evidence (mutation as BLIND-SPOT FINDER):
   Inject deliberate regressions into LIVE code paths (flip a sign, perturb a constant, drop a guard,
   corrupt an output). Harness must catch EVERY one. An UNCAUGHT mutation = a located oracle blind spot →
   widen battery/taps until caught. Re-run on a schedule. Human sign-off: <who signs Gate 0>.
   Residual fault classes NOT tested: <name them>.

EXECUTION MODEL
- Each unit = one agent → per-unit gate, looping build→test→iterate until green OR stuck.
- Each unit = one small, independently revertible ATOMIC commit on a lane branch.
- THE GATE RUNS IN INFRASTRUCTURE (merge queue/CI), on the POST-MERGE HEAD. An agent's "it's green" is a
  claim, not proof. File-DAG independence ≠ semantic independence — re-gate every integrated state.

GOVERN THE FLEET (makes hours of autonomy safe)
- Retry budget per unit: after <K> reverts, stop retrying the code → escalate as a DECOMPOSITION failure.
- Human-queue circuit breaker: if queue depth > <N>, HALT the fleet and surface it.
- Meta-monitors: stuck-rate and behavior-change-ticket-rate (ticket spike = "behavior-preserving" eroding).
- Trust root: harness + CI def + branch protections + golden masters = most privileged surface; fleet has
  NO write access to them. Out-of-band, human-anchored.
- Liveness + cost: heartbeat the run; alarm on stall / cost-burn / no-progress. Thresholds: <stall, $cap>.
- COMPLETION PREDICATE: done = all DAG units merged + all gates green on HEAD + all human checkpoints
  signed. Burndown ledger: <where progress is tracked>.

LANES (dependency DAG — instantiate)
Phase F — Foundation: inventory → determinism contract → CI + hermetic build + oracle + anti-gaming +
          mutation self-test → GATE 0 (human).
Phase R — Restructure (behavior-preserving): decompose <monoliths/modules, ordered by leverage/risk> into
          modular units w/ clean seams; each = extract → clean interface → unit test → oracle UNCHANGED →
          green → GATE <human review>.
Phase C — Capability/Platform (behavior-CHANGING; after R): <new features / migration>, each separately
          specced + validated. Platform swaps: strangler-fig + dual-run parity before cutover →
          FINAL GATE <human + real-world>.
Parallelism: Phase R is highly parallel (one agent per module/unit); the DAG enforces order.

SEPARATE TRACK (never fold in)
Behavior-CHANGING work rides its OWN ticketed track with its own golden-master update + human/real-world
A/B validation. A behavior-preserving unit must never change observable behavior.

HUMAN-IN-LOOP CHECKPOINTS (autonomy cannot self-certify — mandatory, scheduled)
Judgment-bound correctness — UX/perceptual quality, real-world fit, security posture, anything needing a
human or the physical world. Checkpoints + owners: <human checkpoints + owners>.

PRE-MORTEM (failure → guard)
- Mass-produces plausible-but-broken work → fault-evident oracle + mutation self-test, proven first.
- "Passes" by weakening/deleting tests → oracle immutability + deletion detector + coverage floor.
- Agent self-reports green / edits the gate → gate in infra; harness/CI/branch-protection outside fleet write.
- Flaky oracle trains red→green rubber-stamping → determinism contract + characterized tolerance.
- Green-in-isolation, broken-when-merged → gate on post-merge HEAD (merge queue).
- Oracle blind spot → mutate live code; uncaught = locate & widen; battery code-coverage gate.
- Frozen master rots → prefer differential-vs-live; else documented re-baseline policy.
- Human queue explodes at the end → queue-depth circuit breaker + stuck-rate monitor + retry budget.
- "Behavior-preserving" erodes → behavior-change-ticket-rate monitor; behavior-changing on a separate track.
- Big-bang swap breaks everything → strangler-fig + dual-run parity before cutover.

INSTANTIATION CHECKLIST (fill every slot before handoff)
[ ] <system/repo>  [ ] <orchestration tool>  [ ] <who ratifies + signs gates>
[ ] <existing verification assets>            [ ] <oracle type per boundary>
[ ] <determinism controls>                    [ ] <empirical per-boundary tolerances>
[ ] <input/scenario battery>                  [ ] <observable boundaries to tap>
[ ] <build cmd>  [ ] <test cmd>               [ ] <unit decomposition, ordered by leverage/risk>
[ ] <retry budget K>  [ ] <queue cap N>  [ ] <stall + $cost alarms>
[ ] <human checkpoints + owners>              [ ] <completion predicate + burndown ledger location>
[ ] <residual fault classes / boundaries NOT covered — stated honestly>
```

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-06-24 | agent:claude-code | v2: pluggable oracle menu, Gate −1 determinism contract, infra-run/post-merge-HEAD gate, fleet governance (retry budget, queue breaker, monitors, trust root, liveness/cost), completion predicate, battery-coverage gate, honest-limits framing. |
| 2026-06-24 | agent:claude-code | Created: generic fill-in handoff template, bundled with the autonomous-agentic-build skill. |
