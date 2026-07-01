# Agent Operating System — SpectraSynq K1 Firmware

Concise manual for Devin / Claude / Codex-style agents working on this repo.

---

## 1. Session bootstrap ritual

At the start of every session, run:

```bash
bash scripts/agent/session-bootstrap.sh
```

The bootstrap runs `scripts/agent/repo-truth.sh` as a pre-session gate:

- **FAIL** (lane-integrity problem: missing IM73D env/guard/plan) → bootstrap exits nonzero. Do not proceed. Resolve the FAIL first.
- **WARN** (stale docs that do not misroute the lane) → bootstrap continues and prints the warnings.
- **PASS** → bootstrap continues normally.

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
6. **`claude-mem`** — prior-session context and recurrence patterns only

`progress.md`, `.claude/handoff.md`, and `docs/spec-index.md` are authoritative only when confirmed fresh. If `scripts/agent/repo-truth.sh` flags them stale, treat them as historical, not current.

---

## 3. Current-lane verification rule

The current live lane is:

- **Branch:** `lane/im73d-pdm-eval`
- **Project:** `SpectraSynq_K1_Firmware`
- **Focus:** IM73D122 PDM microphone evaluation on bench K1 `B489A500`

Before any work, verify the lane has not shifted. If `git status` shows a different branch, or if the lane doc says something different, stop and report the conflict.

---

## 4. Stale-doc handling rule

If `repo-truth.sh` reports `handoff.md`, `progress.md`, or `spec-index.md` as stale:

- Do not rely on them for current lane status.
- Do not silently update them to match git.
- Report the stale docs in your handoff.
- Ask for explicit approval before editing governance/docs files.

The dirty `docs/hardware/device-build-registry.md` entries are current evidence. Do not auto-commit them.

---

## 5. claude-mem usage rule

- Use `claude-mem` only for historical context, prior bugs, failed attempts, and recurrence patterns.
- Use `search` → `timeline` → `get_observations` workflow.
- Never treat claude-mem as current lane truth.
- Record milestones at session start, green checkpoints, and blockers.

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

## 7. Forbidden actions

- Edit firmware source unless explicitly scoped
- Change `platformio.ini` default envs or build behavior unless explicitly scoped
- Flash, upload, erase flash, or open a serial monitor without explicit approval
- Run `start_noise_cal` without the user confirming a silence window
- Auto-commit dirty `device-build-registry.md` or other governance docs
- Edit files outside the approved scope
- Install new MCPs, plugins, packages, or global tools
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
ignored, safety constraints respected, next recommended action.

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

---

## 13. Devin environment setup

The future Devin git-backed blueprint lives at `.devin/blueprint.yaml`. It is a
knowledge-only draft: it documents the repo's safe-command surface and does not
install speculative packages, call sync/build APIs, or configure hardware
access. Sync + build are triggered separately via Devin API/UI after the file
is committed to the default branch. Do not create `.devin/config.json` (shared
project policy) without explicit approval.

---

## 14. Thinking gate

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

- **Shifting the burden:** invoking a thinking skill is not certification of the
  answer. The post-session report still needs proof.
- **Fixes that fail:** keep the gate narrow (decision/ambiguity/architecture
  only). If you wire thinking into every task, agents will skip it to hit
  deadlines and the wiring gets removed.
- **Accidental adversaries:** if two skills conflict, resolve explicitly; do
  not average.
- **Tragedy of the commons:** do not invoke the router "to be safe." It exists
  for decision-class tasks, not as a ritual.

The post-session report includes a `thinking_skill_used` field so skipped-thinking
on a decision task is a visible process bug, not a silent one.

---

## 15. Skill, tool & specialist awareness

There is a large inventory of skills, tools, MCP servers, and specialist agents
available. The problem is not "agents don't know they exist" — the inventories
are already visible in the session. The problem is scanning them at the right
moment without over-invoking. This is a narrow gate, not a ritual.

### Task-intake ritual

Before acting on any task, run this scan in order:

1. **Keyword scan `available_skills`** (cheap, always do this). Match task
   keywords against skill titles. If a skill title clearly fits the task
   domain, invoke it.
2. **If the task is complex or multi-domain** → invoke `/discover-specialists`
   and check `.claude/agents/*.md` for a specialist whose scope matches. A
   specialist subagent often beats a general agent on its domain.
3. **If no installed skill covers the task** → invoke `/find-skills`
   (`npx skills find <query>`) to search the open skills ecosystem. Do NOT
   invoke this for tasks covered by installed skills — it is for gaps.
4. **If the task needs an external service** (GitHub, Linear, Slack, browser,
   database, etc.) → scan the MCP server list in the system prompt and call
   `mcp_list_tools` on the matching server before using its tools.

Mechanical execution against a clear spec: do step 1 only, then proceed. Do
not invoke specialists, find-skills, or MCP tools "to be safe."

### Inventory cost table

| Inventory | Already visible? | Cost to check | When to check |
|-----------|------------------|---------------|---------------|
| Installed skills (`available_skills`) | Yes (system prompt) | ~0 (scan titles) | Every task — keyword scan |
| Installed specialists (`.claude/agents/*.md`) | No | One `/discover-specialists` call | Complex / multi-domain tasks |
| Discoverable skills (skills.sh) | No | One `npx skills find` call | Only when installed skills don't cover the task |
| MCP servers | Yes (system prompt) | ~0 (scan list) + `mcp_list_tools` | When the task needs an external service |

### Failure modes to avoid

- **Tragedy of the commons:** do not invoke every inventory "to be safe."
  Over-invocation burns tokens and produces ritual noise. The gate is narrow.
- **Shifting the burden:** invoking a skill does not certify the answer. The
  post-session report still needs proof.
- **Map-territory:** skill descriptions are the map; the agent's judgment is
  the territory. A skill that sounds like a fit may not be — read its actual
  scope before leaning on it.
- **Skipping the scan on complex tasks:** if a complex task reports
  `skills_used: none` and an obvious skill fit existed, that is a visible
  process bug caught by the post-session report.

The post-session report includes `skills_used` and `specialists_used` fields so
skipped-scans on tasks that needed them are visible, not silent.

---

Last updated: 2026-07-02
