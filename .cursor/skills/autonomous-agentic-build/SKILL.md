---
name: autonomous-agentic-build
description: "Use when scoping, planning, or handing off a large body of work to be executed as a long-running, autonomous, multi-agent build/migration/refactor/modernization — any 'fan out agents and let them build the whole thing' effort, in any language or domain. Load-bearing principle: the verification HARNESS IS THE PRODUCT — stand up a PLUGGABLE oracle (golden-master / differential / property / spec) that is fault-EVIDENT (proven against an injected fault battery at Gate 0) BEFORE any production lane; pace by gates not dates; one unit = one agent = one atomic commit; gate runs in infra (agents cannot self-certify); rollback-on-red. Trigger words: autonomous build, agentic build, long-running build, harness-first, golden master, behavior-preserving refactor, strangler-fig migration, mass refactor, 'set agents loose'."
abstract: "Project-agnostic doctrine + paste-ready handoff template for running work as a long-horizon autonomous multi-agent build. Thesis: a weak oracle doesn't slow autonomy — it lets agents confidently MASS-PRODUCE broken work that passes, reinforcing failures at scale. So the first flawless deliverable is scope-decomposition + a verification harness, NOT the change. Hardened v2 (after adversarial teardown): the oracle is PLUGGABLE (golden-master / differential-vs-live / property+metamorphic / executable-spec — picked by baseline-exists × deterministic, so it covers greenfield too); a determinism contract (Gate −1) precedes freezing; mutation testing is a blind-spot finder, not a 'fail-proof' stamp; the gate runs in INFRASTRUCTURE (agents cannot self-certify, and cannot modify the harness/CI/branch-protection trust root); the fleet is GOVERNED (retry budget → decomposition-failure escalation, human-queue circuit breaker, stuck-rate + behaviour-change-ticket-rate monitors, post-merge-HEAD integration gate, liveness/cost alarms, explicit completion predicate). Right-size it — don't build the apparatus for a small change. Origin: SpectraSynq K1 firmware-modernization program, ratified 2026-06-23."
---

# Autonomous Agentic Build — Harness-First Doctrine

When agent-hours collapse to near-zero, the bottleneck is no longer *writing* the change — it is *trusting* it. A fleet working autonomously over hours or days produces an enormous volume of plausible work. Without a verification harness strong enough to reject what's subtly wrong, autonomy doesn't give you a finished system — it gives you a confidently-broken one at scale. This skill is the method for not letting that happen.

**When to use:** decompose a large effort and let agents execute it autonomously and in parallel — major refactor, framework/platform migration, modernization, mass mechanical change, or greenfield under a strong spec. Domain- and language-agnostic.

**When NOT to use (right-size it):** a single small change, or anything where building the harness costs more than the work it guards. The apparatus is justified by *volume × risk × autonomy-duration*. For a one-off edit, just write the test. Don't build a cathedral to lay a brick.

## The Law (non-negotiable)

1. **The harness IS the product; the work is only what flows through it.** A weak oracle doesn't slow autonomy — it lets agents mass-produce plausible-but-broken work that *passes*. The first flawless deliverable is scope-decomposition + the verification harness, **never the change itself**.
2. **Pace by GATES, NOT DATES.** Agent-hours are cheap. The only true constraints are the oracle and the human/real-world checkpoints autonomy **cannot self-certify**. Quote gates, not calendars.
3. **Behavior-preserving by default.** Restructure units must not change observable behavior. Anything that *intends* to change behavior is isolated onto a separate ticketed track (§7).
4. **Autonomy structurally cannot merge red.** Rollback-on-red is the property that makes long-running autonomy safe — *and it only holds if the gate is trustworthy.* A flaky gate, a self-reported gate, or a gate the fleet can edit silently voids this law.

**Honest limits (the method is fault-EVIDENT, not fail-proof).** The oracle only catches regressions *at the boundaries you tapped, under the inputs you sampled, in the fault classes you imagined*. It cannot prove the absence of bugs. Treat "all gates green" as "no regression detected in the measured envelope," never as "behavior preserved." The whole craft is making the measured envelope wide enough that the gap is small — and naming the residual gap, not hiding it.

## Step 0 — Inventory before you invent (highest leverage)
The oracle usually **half-exists**: existing tests, replay harnesses, golden files, staging environments, the still-running old system. Find them and **formalize**, don't rebuild. The cheapest fault-evident harness is the one already latent in the repo. (Origin case: 10 host-compile replay harnesses already existed — the oracle keystone was formalized, not invented.)

## Choose your oracle (pluggable — pick per boundary)
The equivalence engine is not always a frozen golden master. Select by *(is there a known-good baseline?) × (is the boundary deterministic?)*:

| Situation | Oracle |
|---|---|
| Brownfield, deterministic boundary | **Golden-master**: freeze baseline outputs; reproduce exactly. |
| Brownfield, baseline still runnable | **Differential**: run old vs new on the same input, diff live. No staleness; best for long runs. |
| Nondeterministic, or no frozen reference | **Property + metamorphic**: assert invariants and input→output relations, not exact bytes. |
| Greenfield / behavior-changing | **Executable spec / acceptance**: the spec (or a reference impl) IS the oracle; property tests for the rest. |

Most real programs use a **portfolio** — golden-master on the fixed-point core, property tests on the timing-dependent edges, differential on what the old system still computes. Combine deliberately.

## Step −1 — Determinism contract (BEFORE you freeze anything)
A flaky oracle is worse than none: it teaches everyone to rubber-stamp re-runs, which destroys rollback-on-red. Before capturing any baseline: **seed RNG, inject the clock, pin concurrency/thread order, freeze IDs/timestamps, sort unordered collections, isolate the network.** Then run the baseline **N times** and derive each boundary's tolerance *empirically* from observed variance — never guess "epsilon." Exact-match wherever you can make it exact; tolerance only where nondeterminism is irreducible *and characterized*.

## How to apply it

### 1 — Decompose scope into a gated DAG
Units **small, single-responsibility, independently revertible**, ordered by leverage/risk; hard dependencies as a DAG so independents run concurrently. No unit bundles unrelated changes. Sloppy decomposition is how autonomy reinforces failure — this is half the deliverable.

### 2 — Build the harness (oracle + anti-gaming)
- **Oracle** (per the menu above): deterministic, committed, checksummed input/scenario battery over the real operating envelope (normal, edge, stress, failure, real-world samples). Capture outputs at **every observable boundary**. For a frozen master: **immutable, checksummed, owned OUTSIDE the fleet's write scope.** *If the master changes, behavior changed → human-approved behavior-change ticket, never an autonomous edit.*
- **Battery coverage is itself a gate:** measure the code coverage of the oracle battery. An equivalence check over code the battery never exercises is vacuous. Unexercised critical paths are a finding.
- **Anti-gaming:** oracle + harness checksummed-immutable (any diff by a production lane = automatic FAIL); test-deletion/skip detector + coverage floor; **rollback-on-red**.

### 3 — Gate 0: prove the harness is fault-EVIDENT (mutation as blind-spot finder)
Before any production lane: inject deliberate regressions into **live code paths** (flip a sign, perturb a constant, drop a guard, corrupt an output) and require the harness to catch **every one**. An *uncaught* mutation is not a pass — it is a located **oracle blind spot** (unmeasured boundary or un-exercised path); widen the battery/taps until it's caught. Re-run on a schedule. A **human signs off Gate 0**. This proves the harness rejects the faults you imagined — name the fault classes you did *not* test as residual risk.

### 4 — Run the lanes (execution model)
- **Each unit = one agent** working to the per-unit gate, looping **build → test → iterate until green OR stuck.**
- **Each unit = one small, independently revertible atomic commit** on a lane branch.
- **The gate runs in INFRASTRUCTURE, not in the agent.** An agent's "it's green" is a claim, not proof (ssa-management: orchestrator/infra re-verifies decision-critical claims). The merge queue runs the gate on the **post-merge HEAD** — file-level DAG independence does *not* guarantee semantic independence, so every integrated state is re-gated, not just the lane branch.

### 5 — Govern the fleet (the part that makes "hours of autonomy" safe)
Long autonomy fails operationally, not just technically. Mandatory controls:
- **Retry budget per unit:** after K reverts, stop retrying the *code* and escalate the *decomposition* — a unit that won't go green is usually mis-scoped, not just buggy. Reverting it forever is "fixes that fail."
- **Human-queue circuit breaker:** "stuck → human queue" is an unbounded buffer. Cap it: if queue depth > N, **halt the fleet** and surface it. An invisible backlog that explodes at the end is the default failure of "minimal-maintenance" autonomy.
- **Meta-monitors:** track **stuck-rate** and **behavior-change-ticket-rate**. A ticket spike means "behavior-preserving" is quietly eroding (goal erosion) — alarm on it.
- **Trust root:** the harness, CI definition, branch protections, and golden masters are the **most privileged surface**. The fleet must have **no write access** to them (a fleet that can edit `.github/workflows` can disable its own gate). Out-of-band, human-anchored.
- **Liveness + cost:** heartbeat the run; alarm on stall, cost-burn, or no-progress (see [[parallel-agent-sandboxing]] for the stall-retry cost-blowup half). A wedged fleet at hour 2 of a 20-hour run must page at hour 2.
- **Completion predicate:** "done" = *all DAG units merged + all gates green on HEAD + all human checkpoints signed*. Keep a burndown ledger so a long run is observable, not a black box.

### 6 — Human checkpoints + the behavior-changing track
- **What autonomy cannot self-certify** — UX/perceptual quality, real-world fit, security posture, anything needing a human or the physical world — is an **explicit, scheduled gate** at phase boundaries.
- **Behavior-CHANGING work** rides its **own ticketed track** with its own golden-master update + human/real-world A/B validation. Never folded into a behavior-preserving unit.

## The per-unit gate (binary — ALL required to merge; run by infra, not the agent)
1. Builds / compiles / lints clean.
2. Oracle satisfied within *characterized* tolerance at **every** boundary, on the **post-merge HEAD**.
3. Full suite green; **zero** tests deleted or newly skipped vs baseline; coverage floor (code + oracle-battery) not reduced.
4. **No** harness / oracle / golden / CI / branch-protection file modified by the unit.
5. Units touching human-judgment-only surfaces flagged into the human review queue.

## Generic lane DAG (instantiate per project)
- **Phase F — Foundation:** inventory existing assets → determinism contract → CI + hermetic build + oracle + anti-gaming + mutation self-test → **Gate 0 (human)**.
- **Phase R — Restructure (behavior-preserving):** decompose monoliths into modular units with clean seams; each = extract → clean interface → unit test → oracle unchanged → green → **human-review gate**.
- **Phase C — Capability/Platform (behavior-changing, after R):** new features / migrations, each separately specced + validated. Platform swaps: **incremental strangler-fig + dual-run parity before cutover**, never big-bang → **final gate (human + real-world)**.

## Pre-mortem (failure → guard)
| Failure | Guard |
|---|---|
| Autonomy mass-produces plausible-but-broken work | Fault-evident oracle + mutation self-test, proven before any lane |
| Agents "pass" by weakening/deleting tests | Oracle immutability + test-deletion detector + coverage floor |
| Agent self-reports green / edits the gate | Gate runs in infra; harness/CI/branch-protection outside fleet write scope |
| Flaky oracle trains red→green rubber-stamping | Determinism contract (Gate −1) + empirically-characterized tolerance |
| Green-in-isolation, broken-when-merged | Gate on post-merge HEAD (merge queue), not just the lane branch |
| Oracle blind spot (unmeasured boundary/path) | Mutate live code; uncaught mutation = locate & widen; battery code-coverage gate |
| Frozen master rots over a long run | Prefer differential-vs-live; else a documented re-baseline policy |
| Human queue silently explodes at the end | Queue-depth circuit breaker + stuck-rate monitor + per-unit retry budget |
| "Behavior-preserving" erodes one exception at a time | Behavior-change-ticket-rate monitor; behavior-changing work on a separate track |
| Big-bang swap breaks everything | Incremental strangler-fig + dual-run parity before cutover |
| Apparatus built for a change too small to need it | Right-size guard (§ When NOT to use) |

## Handoff template
A fill-in-the-blanks, paste-ready execution order lives next to this file: **`handoff-template.md`**. Copy it, fill the `<…>` slots (oracle type per boundary, determinism contract, build/test commands, boundaries, decomposition, tolerances, circuit-breaker thresholds, human checkpoints, completion predicate, orchestration tool), and ship. This `SKILL.md` is the doctrine; the template is the deliverable.

## Origin
Distilled from the SpectraSynq **K1 firmware-modernization program** (ratified 2026-06-23). Captain's framing — *"the harness IS the product; scope and harness must be flawless up front, or we reinforce failures at scale"* — is the spine. Hardened v2 after an adversarial teardown (TRIZ / systems / archetypes / Cynefin / map-territory / ssa-management). Related: [[parallel-agent-sandboxing]] for sub-agent isolation + orchestration-cost control.

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-06-24 | agent:claude-code | v2 hardening after adversarial teardown: pluggable oracle menu (covers greenfield); determinism contract (Gate −1); "fault-evident" reframing + honest-limits + mutation-as-blind-spot-finder; fleet governance (retry budget, queue circuit breaker, stuck/ticket-rate monitors, post-merge-HEAD gate, trust root, liveness/cost, completion predicate); inventory-before-invent step; right-size guard. |
| 2026-06-24 | agent:claude-code | Created: generalised the K1 firmware-modernization program into a project-agnostic harness-first autonomous-build doctrine + bundled handoff template. |
