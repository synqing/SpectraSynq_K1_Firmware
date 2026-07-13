# Agent Operating System — SpectraSynq K1 Firmware

**Canonical, tool-agnostic manual for all agents** (Devin, Claude Code, Codex,
Cursor). Read this before any task in this repo.

Tool-specific overlays (permissions, config files, blueprint) live in each
tool's own config — see [Tool-specific overlays](#tool-specific-overlays)
at the end of this file.

---

## 1. Session bootstrap ritual

At the start of every session, run:

```bash
bash scripts/agent/session-bootstrap.sh
```

The bootstrap runs `scripts/agent/repo-truth.sh` as a pre-session gate:

- **FAIL** (lane-integrity problem: missing IM73D env/guard/plan) → bootstrap exits nonzero; dual-track applies per [`knowledge/decisions/agent-stack-repo-truth-dual-track.md`](knowledge/decisions/agent-stack-repo-truth-dual-track.md).
  - **Firmware work:** do not proceed — no firmware source edits, `pio-build.sh`, or firmware commits until FAIL is resolved.
  - **Docs-only agent-stack work:** may proceed only when explicitly scoped (governance/knowledge/runbooks) and FAIL is acknowledged in the artifact.
- **WARN** (non-fatal hygiene, e.g. dirty `docs/hardware/device-build-registry.md`) → bootstrap exits **0**; firmware work is not blocked (dual-track does not apply).
- **PASS** → bootstrap exits 0 normally.

IM73D upload-guard false-FAIL fix (2026-07-13): [`knowledge/research/repo-truth-fix-evidence.md`](knowledge/research/repo-truth-fix-evidence.md).

Then read this file and the files it flags as current. Do not proceed until you know:

- current branch
- HEAD commit
- dirty / untracked state
- active lane
- whether handoff docs are stale

---

## 2. Source-of-truth hierarchy

Trust sources in this order:

1. **Git branch + HEAD + working tree** — canonical current state
2. **`platformio.ini` + `scripts/platformio/k1_upload_guard.py`** — envs and hardware targets
3. **Lane-specific docs** — e.g. `docs/hardware/im73d122-ap-vp-migration-plan.md`
4. **`docs/hardware/device-build-registry.md`** — physically-deployed state (including dirty entries)
5. **`.claude/CLAUDE.md` + `AGENTS.md`** — load-bearing process rules
6. **`knowledge/`** — Captain-ratified durable knowledge (OpenKnowledge pilot scaffold); `status: verified` frontmatter required for agent consumption
7. **`claude-mem`** — prior-session context and recurrence patterns only; never promoted without verification into `knowledge/`

`progress.md`, `.claude/handoff.md`, and `docs/spec-index.md` are authoritative only when confirmed fresh. If `scripts/agent/repo-truth.sh` flags them stale, treat them as historical, not current.

### Agent stack rollout (standard stack v1 — ratified 2026-07-13)

Cross-tool agent infrastructure rollout (Herdr, Codex plugin, OpenKnowledge,
Claude-mem coexistence) is documented under [`docs/agent-stack/`](docs/agent-stack/README.md).
**Phases 0–6 closed** (Captain ratification 2026-07-13). **Canonical manifest:**
[`docs/agent-stack/STANDARD-STACK.md`](docs/agent-stack/STANDARD-STACK.md).
Durable knowledge lives in [`knowledge/`](knowledge/index.md); routing skill:
`.cursor/skills/knowledge-memory-routing/` (mirror in `.claude/skills/`).

| Doc | Use for |
|-----|---------|
| [`docs/agent-stack/STANDARD-STACK.md`](docs/agent-stack/STANDARD-STACK.md) | **Adopted tools, version pins, forbidden paths** (start here after bootstrap) |
| [`docs/agent-stack/AUTHORITY-CONTRACT.md`](docs/agent-stack/AUTHORITY-CONTRACT.md) | Ratified ownership boundaries (code vs rules vs durable knowledge vs episodic memory) |
| [`docs/agent-stack/PHASED-ROLLOUT.md`](docs/agent-stack/PHASED-ROLLOUT.md) | Phased adoption history, gates, rollback |
| [`docs/agent-stack/ACTIONABLE-TASKS.md`](docs/agent-stack/ACTIONABLE-TASKS.md) | Numbered task backlog with acceptance criteria |
| [`docs/agent-stack/SWARM-ORCHESTRATION.md`](docs/agent-stack/SWARM-ORCHESTRATION.md) | Multi-agent roles, Herdr/Ruflo/Codex handoffs, promotion workflow |
| [`knowledge/runbooks/agent-onboarding.md`](knowledge/runbooks/agent-onboarding.md) | New-agent cold start (routing + promote + operator tools) |

**Core rule (when rollout is active):** promote verified learnings to OpenKnowledge;
never auto-sync Claude-mem observations into curated knowledge.

**Hierarchy deferral:** Firmware safety and session rules in this file prevail.
For agent-stack **tool ownership** and promotion boundaries, defer to
[`AUTHORITY-CONTRACT.md`](docs/agent-stack/AUTHORITY-CONTRACT.md) when not in conflict
with firmware gates.

---

## 3. Current-lane verification rule

### Firmware lane (verify from git every session)

At session start, **git branch + HEAD + working tree** are authoritative for the
active firmware lane. Do not assume a branch named in docs without verifying:

```bash
git branch --show-current && git rev-parse --short HEAD
```

**IM73D productionization reference** (when on that lane):

- **Typical branch:** `lane/im73d-pdm-eval`
- **Project:** `SPECTRASYNQ_K1_FIRMWARE`
- **Focus:** IM73D122 productionisation. Phase-1 firmware is done;
  bench IM73D R1/no-speaker DSR proof is closed; current blocker is R2
  production-shape hardware proof (main K1 SPH0645 -> IM73D on GPIO13/12/14,
  or a dedicated production-shape IM73D unit).

If scoped **firmware** work and `git status` shows a different branch than lane
docs imply, stop and report the conflict before editing source.

### Agent-stack rollout (lane-orthogonal)

Agent-stack phases (`docs/agent-stack/`) are **lane-orthogonal**: docs, operator
tooling, and `knowledge/` curation may proceed on any branch when explicitly
scoped docs-only. Agent-stack docs **do not** override firmware lane verification
in this section. Parallel priorities: [`knowledge/current-priorities.md`](knowledge/current-priorities.md).

---

## 4. Stale-doc handling rule

If `repo-truth.sh` reports `handoff.md`, `progress.md`, or `spec-index.md` as stale:

- Do not rely on them for current lane status.
- Do not silently update them to match git.
- Report the stale docs in your handoff.
- Ask for explicit approval before editing governance/docs files.

The dirty `docs/hardware/device-build-registry.md` entries are current evidence. Do not auto-commit them.

---

## 5. claude-mem usage rule (HIGHEST-LEVERAGE — do not skip)

`claude-mem` is the single highest-leverage agentic tool in this repo: it gives
the next session understanding of what was previously done. A session that
records nothing is a session the next agent cannot learn from. **Skipping
observation recording is a process failure, not a shortcut.**

### Retrieval (all tools, when starting a task)

- Always `search` → `timeline` → `get_observations` for prior work on the lane
  or task type before acting. Run multiple single-term queries (compound
  AND/OR/NOT queries silently return zero in worker-mode FTS).
- Use `claude-mem` for historical context, prior bugs, failed attempts, and
  recurrence patterns.
- Never treat claude-mem as current lane truth — git + on-disk docs win for
  current state. Memory is for prior-session context and recurrence.

### Recording — tool-split policy (load-bearing)

`claude-mem` runs in **worker mode** (13.6.0). The write path is the
**hook pipeline** (`PostToolUse` / `Stop` hooks in `~/.claude/hooks/`), which
fires for **Claude Code, Codex, and Cursor** — NOT for Devin. This is an
architectural fact of worker mode, not a wiring bug.

**Claude Code / Codex / Cursor (write-capable):**

Record a `claude-mem` observation at each of these moments:

1. **Session start** — what lane, what branch/HEAD, what you're about to do
2. **Green checkpoint** — what was proven, the commit SHA, the gate result
3. **Blocker / failure** — what failed, the hypothesis, the next action
4. **Captain decision** — any decision that constrains future work
5. **Session end** — what's done, what's open, the next recommended action

If `claude_mem_observations` in the post-session report is `none`, you must
explain why. "Forgot" / "ran out of time" / "it was a small task" are not valid
explanations — small tasks still produce a start + end observation.

**Devin (retrieval-only — cannot write in worker mode):**

Devin does not participate in the claude-mem hook pipeline, so it cannot
directly record observations. `observation_add` / `memory_add` MCP tools error
in worker mode (server-beta only). Do NOT attempt workarounds, do NOT write
directly to the SQLite DB, do NOT call undocumented worker routes to force a
write. Devin must instead write durable continuity to **on-disk repo artifacts**:

- `scripts/agent/post-session-report.md` — every session end
- `.claude/handoff.md` — when lane state changes
- `progress.md` — when project state changes
- `docs/spec-index.md` — when the source-of-truth index changes
- `docs/hardware/device-build-registry.md` — when deployed state changes (with explicit approval; never auto-commit)
- commit messages — for accepted changes

These on-disk artifacts ARE the cross-tool continuity layer. They are read by
every tool's bootstrap and survive session resets. `claude-mem` is supporting
context, not the canonical record — git + on-disk docs are source of truth.

### No false claims (load-bearing)

No agent may claim it recorded a `claude-mem` observation unless it can
**retrieve or otherwise prove** the observation exists. A queued write that
did not produce an observation row is not a recorded observation. If you
cannot retrieve it, write `write_status: unavailable_in_worker_mode_for_devin`
(or the equivalent for your tool) in the report and fall back to on-disk docs.

### Health check

If `claude-mem` is unreachable, that is a fatal session condition for retrieval
but NOT for recording (Claude Code/Codex/Cursor queue writes for later; Devin
falls back to on-disk docs). Note the outage in the report and proceed with
on-disk evidence only. Do not silently drop the memory layer.

### Backlog (do not implement now)

Evaluate a Devin → claude-mem observation bridge **only if** all three are true:
Devin becomes a primary daily executor, AND memory loss causes repeated
duplicated work or bad decisions, AND on-disk handoff/report docs are proven
insufficient. Non-goals: no server-beta migration by default, no direct SQLite
writes without a stable supported route, no memory bridge that bypasses
repo-truth or commit evidence.

---

## 6. Allowed actions

- Read source, docs, and git history
- Edit files inside the scope approved by the user
- Run `pytest tests/` for validation
- Run `pio run -e <env>` **only via `scripts/agent/pio-build.sh <env>`** (the wrapper rejects upload/flash/monitor tokens and limits envs to `k1_hardware`, `k1_bench_reference`, `k1_bench_im73d`)
- Commit green checkpoints on feature/wip branches (pre-commit gate enforced)
- Use `scripts/hooks/wip-checkpoint.sh` for broken-work checkpoints
- Delegate to subagents with a written consumption contract
- Add `claude-mem` observations
- Install/verify **enumerated** agent-stack operator tools only (see §7 install allowlist) — document evidence in `knowledge/research/`

## 7. Forbidden actions

- Edit firmware source unless explicitly scoped
- Change `platformio.ini` default envs or build behavior unless explicitly scoped
- Flash, upload, erase flash, or open a serial monitor without explicit approval
- Run `start_noise_cal` without the user confirming a silence window
- Auto-commit dirty `device-build-registry.md` or other governance docs
- Edit files outside the approved scope
- Install new MCPs, plugins, packages, or global tools **except** the enumerated Phase 1–2 allowlist below (no blanket “operator tooling”; no tools not on the list)

### Install allowlist (standard stack v1)

Agents may install/verify **only** these tools per [`STANDARD-STACK.md`](docs/agent-stack/STANDARD-STACK.md):

| Tool | Install path | Forbidden |
|------|--------------|-----------|
| **Herdr** | `brew install herdr` | Routing agent execution through Herdr |
| **sqlite-utils** | `brew install sqlite-utils` or pip equivalent | Writes to production SQLite stores |
| **Codex plugin** | `claude plugin marketplace add` + `install codex@openai-codex` | `reviewGateEnabled: true` (auto stop-gate) |
| **OpenKnowledge MCP** | Project-scoped `@inkeep/open-knowledge@0.29.1` per runbook | Auto-sync Claude-mem → OK; global install |

**Not on allowlist (always forbidden):** pxpipe, OmniRoute as primary, Ruflo full init, Entire on main firmware lane (pilot closed), Headroom in agent path (promotion deferred), Claude-mem → OK auto-sync, any other MCP/plugin/package. Authority: [`knowledge/decisions/agent-stack-autonomous-execution.md`](knowledge/decisions/agent-stack-autonomous-execution.md), [`docs/agent-stack/STANDARD-STACK.md`](docs/agent-stack/STANDARD-STACK.md).
- Create large frameworks or task bureaucracy
- Treat stale handoff docs as current truth
- Run `pio run --target upload` without verifying the target via `k1_upload_guard.py`

---

## 8. Firmware safety / upload prohibition

Hardware writes are gated. `scripts/platformio/k1_upload_guard.py` matches the build env to the USB serial / chip ID before any upload. Even if the guard passes, you must get explicit user approval before:

- `pio run --target upload`
- `pio device monitor`
- `erase_flash`
- any serial command that writes to a device

Bench K1 (`B489A500`) is the only valid target for `k1_bench_im73d`.
Main K1 (`F887A500`) is the only valid target for `k1_hardware`.

---

## 9. Validation gate expectations

Before any non-`wip/*` commit:

1. `pytest tests/` must pass
2. `bash scripts/agent/pio-build.sh k1_hardware` must be clean for firmware source changes
3. The pre-commit hook runs automatically
4. For IM73D changes, `bash scripts/agent/pio-build.sh k1_bench_im73d` must also be clean

For visual-only changes, host-green is sufficient; device eyes-on is a tracked non-blocking follow-up.

---

## 10. Handoff / report template

End every session with `scripts/agent/post-session-report.md`. Fill the fields:
session objective, branch/HEAD at start and end, files changed, commands run,
validation results, evidence captured, blockers, generated files intentionally
ignored, safety constraints respected, thinking skill used, skills used,
specialists used, next recommended action.

---

## 11. Failure-report template

If a gate or build fails, capture:

```text
## Failure Report

### Symptom
- one-line summary

### Repro
- command that failed

### Error output
- relevant excerpt

### Git state
- branch / HEAD / dirty files

### Hypothesis
- most likely cause

### Next action
- narrow investigation or fix
```

---

## 12. Subagent dispatch

Before dispatching any subagent, fill `scripts/agent/subagent-dispatch-template.md`.
Every delegated task is classified `load-bearing` or `optional` before launch.
Load-bearing tasks cannot be downgraded after launch. Stuck-agent recovery is
mandatory: one bounded retry, then fallback. No indefinite polling. Any final
answer that used delegated evidence must include a synthesis ledger.

Run `scripts/agent/delegation_guard.py register` before each launch and `ack`
immediately after the collaboration tool returns an agent ID. Launch sequentially,
keep at most two active, and use checkpoints of at most 300 seconds. If a launch
does not acknowledge within 30 seconds, do not spawn again: close it as `aborted`
and execute the declared fallback locally. Canonical runbook:
`knowledge/runbooks/k1-device-session-and-delegation-gates.md`.

---

## 13. Thinking gate

Before acting on any task that involves a **decision between approaches**,
**ambiguity**, **architecture**, **root-cause debugging under uncertainty**, or
**estimation under unknowns**, invoke `/thinking-model-router` first and
consume its output before proceeding.

Do NOT invoke a thinking skill for mechanical execution against a clear spec.
Forcing a thinking-model step on "write a pytest function" is process sludge.

The router is the single entry point. It maps the task to one of five buckets
and returns 1-2 named skills. Do not invoke all thinking skills; do not build a
parallel router. If the router returns two skills that conflict, resolve the
conflict explicitly — do not average their recommendations.

### Compact taxonomy (the router's reference)

| Bucket | Trigger shape | Representative skills |
|--------|---------------|----------------------|
| Decision under options | "should we X or Y", "which approach" | `thinking-reversibility`, `thinking-opportunity-cost`, `thinking-steel-manning` |
| Root cause / debugging | "why did this break", "symptom vs cause" | `systematic-debugging`, `thinking-five-whys-plus`, `thinking-scientific-method` |
| Estimation under unknowns | "how long", "how much", "is it feasible" | `thinking-fermi-estimation`, `thinking-probabilistic`, `thinking-margin-of-safety` |
| Systems / second-order | "what happens downstream", "feedback loops", "unintended consequences" | `thinking-systems`, `thinking-second-order`, `thinking-archetypes`, `thinking-feedback-loops` |
| First-principles / reframing | "conventional approach fails", "challenge assumptions" | `thinking-first-principles`, `thinking-inversion`, `thinking-triz` |

### Failure modes to avoid

- **Shifting the burden:** invoking a thinking skill is not certification of the answer. The post-session report still needs proof.
- **Fixes that fail:** keep the gate narrow (decision/ambiguity/architecture only). If you wire thinking into every task, agents will skip it to hit deadlines and the wiring gets removed.
- **Accidental adversaries:** if two skills conflict, resolve explicitly; do not average.
- **Tragedy of the commons:** do not invoke the router "to be safe." It exists for decision-class tasks, not as a ritual.

The post-session report includes a `thinking_skill_used` field so skipped-thinking on a decision task is a visible process bug, not a silent one.

---

## 14. Skill, tool & specialist awareness

There is a large inventory of skills, tools, MCP servers, and specialist agents
available. The problem is not "agents don't know they exist" — the inventories
are already visible in the session. The problem is scanning them at the right
moment without over-invoking. This is a narrow gate, not a ritual.

### Task-intake ritual

Before acting on any task, run this scan in order:

1. **Keyword scan `available_skills`** (cheap, always do this). Match task keywords against skill titles. If a skill title clearly fits the task domain, invoke it.
2. **If the task is complex or multi-domain** → invoke `/discover-specialists` and check `.claude/agents/*.md` for a specialist whose scope matches. A specialist subagent often beats a general agent on its domain.
3. **If no installed skill covers the task** → invoke `/find-skills` (`npx skills find <query>`) to search the open skills ecosystem. Do NOT invoke this for tasks covered by installed skills — it is for gaps.
4. **If the task needs an external service** (GitHub, Linear, Slack, browser, database, etc.) → scan the MCP server list in the system prompt and call `mcp_list_tools` on the matching server before using its tools.

Mechanical execution against a clear spec: do step 1 only, then proceed. Do not invoke specialists, find-skills, or MCP tools "to be safe."

### Inventory cost table

| Inventory | Already visible? | Cost to check | When to check |
|-----------|------------------|---------------|---------------|
| Installed skills (`available_skills`) | Yes (system prompt) | ~0 (scan titles) | Every task — keyword scan |
| Installed specialists (`.claude/agents/*.md`) | No | One `/discover-specialists` call | Complex / multi-domain tasks |
| Discoverable skills (skills.sh) | No | One `npx skills find` call | Only when installed skills don't cover the task |
| MCP servers | Yes (system prompt) | ~0 (scan list) + `mcp_list_tools` | When the task needs an external service |

### Failure modes to avoid

- **Tragedy of the commons:** do not invoke every inventory "to be safe." Over-invocation burns tokens and produces ritual noise. The gate is narrow.
- **Shifting the burden:** invoking a skill does not certify the answer. The post-session report still needs proof.
- **Map-territory:** skill descriptions are the map; the agent's judgment is the territory. A skill that sounds like a fit may not be — read its actual scope before leaning on it.
- **Skipping the scan on complex tasks:** if a complex task reports `skills_used: none` and an obvious skill fit existed, that is a visible process bug caught by the post-session report.

The post-session report includes `skills_used` and `specialists_used` fields so skipped-scans on tasks that needed them are visible, not silent.

---

## Tool-specific overlays

The sections above are tool-agnostic. Each tool's native config adds a thin
pointer to this file plus tool-specific settings:

| Tool | Reads | Tool-specific overlay |
|------|-------|----------------------|
| **Devin** | `.devin/agent-os.md` | `.devin/config.local.json` (permissions), `.devin/blueprint.yaml` (knowledge), `scripts/agent/pio-build.sh` (guarded build wrapper) |
| **Claude Code** | `CLAUDE.md` (root) + `.claude/CLAUDE.md` | `.claude/agents/*.md` (specialists), `.claude/skills/` (skills), `claude-mem` MCP |
| **Codex** | `AGENTS.md` (root) | same specialist/skill inventory as Claude Code |
| **Cursor** | `.cursor/rules/agent-os.mdc` | `.cursor/skills/` (skills) |

If your tool's overlay conflicts with this file, this file wins for
tool-agnostic rules (safety, gates, source-of-truth). The overlay wins only for
tool-specific mechanics (how to invoke a build, where permissions live).

---

Last updated: 2026-07-13
