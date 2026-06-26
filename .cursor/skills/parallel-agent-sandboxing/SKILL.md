---
name: parallel-agent-sandboxing
description: "Use when running parallel sub-agents (SSAs): either 2+ agents modifying source concurrently (workspace isolation) OR a multi-agent research/orchestration swarm (stall-retry cost avoidance). Prevents the file-corruption AND the orchestration cost-blowup failure classes."
abstract: "SSA (parallel sub-agent) management, two failure classes. (1) Concurrent-edit file corruption: sandbox isolation, data-only return contracts, 30K-token/agent budget. (2) Orchestration cost-blowup: heavy agent types + per-lane web search trip the 180s no-progress watchdog into a retry storm — fix with lightweight-agent-for-fanout, web-search-in-research-phase-only, pre-flight budget, resume-don't-restart. From the BeatTracker.cpp corruption + the SuperPixie 7h/6.5M-token feasibility stall."
---

# Parallel Agent Sandboxing Protocol

This skill governs **parallel sub-agent (SSA) management** and covers two distinct failure classes:
**(1) concurrent-edit corruption** (the isolation protocol below) and **(2) the orchestration stall-retry cost-blowup** (read-only research/synthesis swarms, Failure Class 2). Apply the half that matches your fan-out — or both.

## Failure Class 1 — Concurrent-Edit Corruption (The BeatTracker Incident)

Six parameters in `BeatTracker.cpp` were corrupted when parallel agents edited the same file simultaneously. A codebase passing 17/17 tests regressed to 15/17. The corruption was subtle — parameter values silently changed, not syntax errors — so diagnosis consumed hours before the root cause (concurrent file writes) was identified. **Parallel agents MUST NEVER share a mutable working directory.**

---

## Isolation Protocol

### 1. Create Sandboxes Before Dispatch

Before dispatching parallel agents, create isolated copies:

```bash
TIMESTAMP=$(date +%s)
cp -r firmware-dir /tmp/agent_<name>_${TIMESTAMP}/
```

Each agent gets its own complete copy of the source tree. No exceptions.

### 2. Restrict Agent Working Directory

Every subagent prompt MUST include an explicit working directory restriction:

```
You are working ONLY in /tmp/agent_<name>_<timestamp>/
Do NOT read or modify files outside this directory.
```

### 3. Return Contract — Data Only

Agents return ONLY data. Never file modifications. The orchestrator applies winning changes exactly once to the canonical source.

**Required return format:**

```
Files inspected: [list]
Findings: [distilled, not raw]
Confidence: [high/medium/low]
Open questions: [list]
Recommended action: [specific]
```

The orchestrator reviews all agent outputs, resolves conflicts, and applies changes in a single controlled pass.

---

## Git Worktree Alternative

When agents need git history inside their sandbox:

```bash
git worktree add /tmp/agent_<name>_sandbox <branch-name>
```

**Build cache optimization:** Symlink shared build directory to avoid redundant compilation:
```bash
ln -s /path/to/original/.pio/build /tmp/agent_<name>_sandbox/.pio/build
```

**Cleanup is mandatory** — abandoned worktrees cause lock conflicts:
```bash
git worktree remove /tmp/agent_<name>_sandbox
```

---

## Token Budget Per Subagent

**Hard limit: 30K tokens per subagent.**

If scope exceeds budget, split further before dispatching. **Proven failure mode:** 240K tokens across 3 agents (80K each) produced context sprawl, lost focus, and unreliable outputs. The BeatTracker incident involved exactly this anti-pattern.

---

## When Sandboxing Is MANDATORY

- 2+ agents modifying any source file (even different files in the same directory)
- Parameter tuning across multiple agents
- Build or test tasks that share the build cache (`.pio/build/`, `build/`, `node_modules/`)
- Any task where agents might touch overlapping files

**If in doubt, sandbox.** The cost of copying a directory is trivial compared to diagnosing silent corruption.

## When Sandboxing Is NOT Needed

- Read-only research or analysis agents (no file writes)
- Agents working on completely separate subsystems (e.g., firmware + documentation)
- Single-agent execution (no concurrency risk)

---

## Failure Class 2 — The Orchestration Stall-Retry Blowup

Sandboxing (above) protects **writers**. This class protects **read-only research / synthesis swarms** — the multi-agent fan-outs that touch no source but can still burn hours and millions of tokens, or hard-fail, when mis-configured. (Per the "When Sandboxing Is NOT Needed" list, these skip isolation — but they are NOT exempt from orchestration discipline.)

### Origin: The SuperPixie Feasibility Run

A 20-agent feasibility swarm ran **~7 hours** and burned **~6.5M tokens**, then HARD-FAILED at its red-team phase with `agent stalled on all 6 attempts (no progress for 180000ms each)`. Root cause: every lane used a **heavy forensic agent type** (`deep-technical-analyst`) **and live web search**, so each agent ran far past the harness's **180 s no-progress watchdog**, which then **retried each agent 6×** — the tail was hours of timeouts, not analysis. A comparable 44-agent swarm on the *default* workflow agent (no per-lane web) did the same shape of work in **~17 min / ~2.8M tokens**: ~25× faster, ~2–3× fewer tokens. Pure misconfiguration.

### Recognition Signature (catch it early)

- Projected or observed wall-clock / token spend **wildly exceeds a sane estimate** for the fan-out — hours not minutes; many-M tokens for read-only research.
- Notifications: `agent stalled (no progress for 180000ms)`, `stalled on all N attempts`, or a phase that hard-fails.
- **Pre-emptive tells:** about to fan out >5 agents on a heavy agent type, or run web search on *every* lane / in a non-research phase.

### Avoidance Protocol

1. **Agent-type discipline.** Default to the **lightweight workflow agent** for any fan-out. Reserve heavy/forensic types (`deep-technical-analyst`, etc.) for a **single deep target** — never an N-wide parallel phase.
2. **Web-search containment.** Web search lives **only in the research/gather phase** (ideally a bounded subset of lanes). Critique / synthesis / red-team phases **reason over the cached findings** — pass them the data, forbid re-searching.
3. **Watchdog-aware tasking.** Keep each agent's task bounded and instruct it to **"conclude promptly."** An agent emitting structured output steadily never trips the 180 s no-progress watchdog.
4. **Pre-flight budget.** Estimate wall-clock + tokens **before launch**. Sane bound for a research fan-out: **~10–20 min, low-single-digit M tokens.** If the design implies hours, it is mis-configured — redesign before launching, do not launch and hope.
5. **Resume, don't restart.** On stall/failure, **patch the offending stage and RESUME from the run id** — completed phases replay from cache for free. Never re-run a whole swarm to fix one bad stage. (The recovery run above: cached research + 5 live agents = **~6.6 min / 0.55M tokens.**)

### Calibration Numbers

| Run | Config | Wall-clock | Tokens | Outcome |
|---|---|---|---|---|
| Healthy | 44 agents · default agent · no per-lane web | ~17 min | ~2.8M | ✅ |
| Pathological | 20 agents · `deep-technical-analyst` + per-lane web | ~7 h | ~6.5M | ❌ stall-fail |
| Recovery (resume) | cached phases + 5 live agents | ~6.6 min | ~0.55M | ✅ |

---

## Anti-Patterns — Do Not Do These

| Anti-Pattern | Why It Fails |
|---|---|
| Concurrent edits to same file | Silent parameter corruption, merge conflicts |
| Shared build cache across writers | Build artifacts from one agent poison another's test results |
| Uncontrolled file modifications | No audit trail, no way to diff agent contributions |
| Subagent context sprawl (>30K tokens) | Agents lose focus, hallucinate parameters, miss constraints |
| Trusting agent file changes without review | Agents make plausible-looking but wrong modifications |
| Skipping sandbox "because agents work on different functions" | Functions share files; concurrent writes corrupt regardless of target |
| Heavy agent type (e.g. `deep-technical-analyst`) fanned out N-wide | Each agent runs exhaustively long → trips the 180 s watchdog → 6×-retry storm; ~25× slower (Failure Class 2) |
| Live web search on every lane / in critique or synthesis phases | Network latency + long runs → stalls; re-searches data already gathered |
| Relaunching a whole swarm to fix one failed stage | Re-burns every prior phase; resume-from-run-id replays them for free |
| Launching a fan-out with no wall-clock / token pre-flight estimate | Mis-configured swarms (hours / many-M tokens) ship undetected |

---

## Orchestrator Checklist

**Before dispatch:** Create sandbox per agent. Include working directory restriction and return format in each prompt. Set 30K token budget. Plan single-pass merge strategy.

**After return:** Review all outputs for conflicts. Apply changes to canonical source exactly once. Run full test suite on merged result. Clean up all sandbox directories and worktrees.

**For research / orchestration fan-outs (Failure Class 2):** default agent type for the fan-out (heavy/forensic types are single-target only); confine web search to the research phase; bound each agent task and tell it to "conclude promptly"; pre-flight a wall-clock/token estimate and refuse to launch anything implying hours. On stall or hard-fail, **patch the offending stage and resume from the run id** — never restart the whole swarm.

---

**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-03-18 | agent:claude | Created — codified parallel agent isolation protocol from BeatTracker.cpp corruption incident |
| 2026-06-05 | agent:claude | Added Failure Class 2 (orchestration stall-retry blowup): agent-type discipline, web-search containment, watchdog-aware tasking, pre-flight budget, resume-don't-restart — from the SuperPixie 7h/6.5M-token feasibility-run stall. Broadened skill scope to general SSA management (both failure classes) |
