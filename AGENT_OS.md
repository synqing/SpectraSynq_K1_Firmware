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

- **FAIL** (lane-integrity problem: active authority missing, untracked,
  inactive, or branch-mismatched; required production invariant missing) →
  bootstrap exits nonzero. Do not proceed. Resolve the FAIL first.
- **WARN** (stale docs that do not misroute the lane) → bootstrap continues and prints the warnings.
- **PASS** → bootstrap continues normally.

Then read this file and the files it flags as current. Do not proceed until you know:

- current branch
- HEAD commit
- dirty / untracked state
- active lane
- whether handoff docs are stale

**Active lane (2026-08-28):** `COLOUR_LAB_PALETTE_BENCH_20260827` on
`lane/colourlab-bench`.
Authority: `tools/colourlab/EXECUTION.md`.
Production Preview R1.1 is frozen. The live task is the explicit no-flash verification programme
on `9087A500` and `B489A500`, including serial mutations and clean leave-state. No firmware
change, flash, further UI redesign or merge to `main` is authorised by this lane.

**If the task touches K1 vs donor lineage, migration, flash identity, or "latest build":** read `docs/agent/K1_LINEAGE_AGENT_ORACLE.md` and load `.claude/skills/k1-lineage-routing/SKILL.md` before any build/flash/port answer. Cross-repo canonical: `Lightwave-Ledstrip/instructions/k1-lineage-agent-oracle.md`.

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

The current live lane is declared in the machine-readable frontmatter of
`docs/spec-index.md`:

- `active_branch`
- `active_lane`
- `active_authority`

At this revision:

- **Branch:** `lane/colourlab-bench`
- **Project:** `SPECTRASYNQ_K1_FIRMWARE`
- **Focus:** Colour Lab production Workbench device verification and clean close.
- **Authority:** `tools/colourlab/EXECUTION.md`

Before any work, verify the checked-out branch matches `active_branch` and the
authority path exists. `scripts/agent/repo-truth.sh` enforces both. If either
check fails, stop and report the conflict rather than silently rewriting lane
authority.

---

## 4. Stale-doc handling rule

If `repo-truth.sh` reports `handoff.md`, `progress.md`, or `spec-index.md` as stale:

- Do not rely on them for current lane status.
- Do not silently update them to match git unless Captain has explicitly
  authorised an orchestration/lane takeover.
- Report the stale docs in your handoff.
- Ask for explicit approval before editing governance/docs files.

The dirty `docs/hardware/device-build-registry.md` entries are current evidence. Do not auto-commit them.

---

## 5. claude-mem usage rule (HIGHEST-LEVERAGE — do not skip)

`claude-mem` is the single highest-leverage agentic tool in this repo: it gives
the next session understanding of what was previously done. A session that
records nothing is a session the next agent cannot learn from. **Skipping
observation recording is a process failure, not a shortcut.**

### Memory skill router (scenario → skill)

When the task involves **resume / prior work / "did we already" / memory /
history narrative / unfamiliar codebase**, invoke **`/claude-mem-router`**
(or apply its table below) and pick **one** skill. Do not invoke the whole set.

| Scenario | Skill |
|----------|-------|
| Current lane / device / branch status; before flash/forensics | `/spec-recall` |
| Prior bug / "did we already fix X?" / recurrence | `/mem-search` |
| Code structure without full-file reads | `/smart-explore` |
| Cold-start / prime unfamiliar tree | `/learn-codebase` |
| Theme corpus Q&A | `/knowledge-agent` |
| One sweeping journey report | `/timeline-report` |
| Week-by-week serial chapters | `/weekly-digests` |
| How the memory tool works | `/how-it-works` |
| Memory empty/stale/offline/contradicts Tier 0 | `/memory-authority-gate` |

**Default K1 ladder:** bootstrap → `/spec-recall` → `/mem-search` (2–4 single-term
queries) → act from git + on-disk + filtered observations → record observations.

Full playbook: `.claude/skills/claude-mem-router/SKILL.md` (mirrored in
`.cursor/skills/` and `.codex/skills/`).

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

## 7. Forbidden actions

- Tell Captain a result does not mean ship / promote / close / done without
  immediately giving the remaining numbered ship path in the **same** answer
  (what is already on silicon or in source; remaining steps; who acts; the
  stamp or flash that means shipped). A hold without a ship path is a failed
  answer. Captain standing order 2026-08-17. Skill: `/ship-path-required`.
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
- Edit SpectraSynq UI look (LVGL/firmware UI, fonts, type/geometry/layout flags,
  soft-key chrome, product HTML sizes, FE control surfaces) without entering via
  `/spectrasynq-ui-router` and obtaining a PASS from
  `/spectrasynq-ui-precode-optical-gate` — see §7a

### 7a. UI pre-code optical gate (load-bearing)

BEFORE any SpectraSynq UI code — including LVGL/firmware UI, font asset
regen+rebind, type token / geometry / layout-flag edits, soft-key/sheet chrome,
product HTML that asserts sizes, or FE control surfaces — the agent MUST enter
via `/spectrasynq-ui-router` (UI skill dispatch) and PASS
`/spectrasynq-ui-precode-optical-gate` as the router’s mandatory first hop for
design→code.

FAIL-CLOSED:
- No PASS receipt with SHA-pinned evidence pack ⇒ UI edits are forbidden.
- “Small nudge”, “colour only”, “bugfix clip”, “sim only”, “HTML is enough”,
  “we already audited”, “G0 passed”, and “C++ inspection” are NOT exemptions.
- Source inspection, CSS hierarchy studies, and functional freezes (G0/bindings)
  are maps. Territory is measured optical ink on an opened native/sim still.
- Invented measurements, TBD tables, or skill-name drop-ins without artefacts
  ⇒ BLOCKED.
- Captain waiver is the ONLY override; it must use the waiver string in the
  skill. Verbal paraphrase is insufficient.

Declare gate tier (T0/T1/T2/T3) in writing before touching gated paths.
Undeclared tier defaults to T0.

**Authority:** router `.claude/skills/spectrasynq-ui-router/` (dispatch);
gate `.claude/skills/spectrasynq-ui-precode-optical-gate/` (PASS/BLOCKED law)
— both mirrored under `.cursor/skills/` and `.codex/skills/`;
canon `docs/canon/SESSION_CANON_2026-08-09_ui_precode_optical_gate.md`;
process `docs/process/SPECTRASYNQ-UI-PRECODE-OPTICAL-GATE.md`;
design `_scratch/precision_bay_r1/UI_ROUTER_DESIGN.md`.
PASS keys: `OPTICAL_GATE_RECEIPT.md` + SHA-pinned `MEASURED.json` + crops —
prose alone cannot PASS. `G0_PASS ≠ OPTICAL_PASS`.

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

For visual-only changes, host-green is sufficient. LED-output / occupancy / packing claims close with a scored rtrace or LED-buffer dump (`/instrument-not-captain-eyes`), not Captain looking at the plate. Product PNG craft boards still follow pixel-inspect. Do not re-request approval after it is given or implied (`/no-reapprove-already-given`).

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
   - Silence / peakiness / IM69D soak / Tab5 BLE / Deck16 / boot palette / boot show / K718 framing / safe-mode crash → **`k1-vj-session-discipline`** (canon: `docs/canon/SESSION_CANON_2026-08-07_im69d_peakiness_deck16_boot.md`).
   - Deck16 BLE backend / identity digests / deck_state haunt / full71 / C6 soak / dark-fade / MAIN glass authority / Mirror·STANDBY → **`k1-deck16-session-discipline`** (canon: `docs/canon/SESSION_CANON_2026-08-09_deck16_ble_backend_haunt_latency.md`; gate: `bash scripts/agent/deck16-first-contact-gate.sh`).
   - Any SpectraSynq **UI** work (LVGL/`deck_ui`, fonts, type/geometry, soft-key chrome, product HTML sizes, FE control surfaces, Tab5 dashboard, HTML proof boards) → **`/spectrasynq-ui-router` FIRST** (scenario → one skill; unsure which UI skill → stay on the router). For design→code the router mandates **`spectrasynq-ui-precode-optical-gate`** as the first hop (canon: `docs/canon/SESSION_CANON_2026-08-09_ui_precode_optical_gate.md`; process: `docs/process/SPECTRASYNQ-UI-PRECODE-OPTICAL-GATE.md`; design: `_scratch/precision_bay_r1/UI_ROUTER_DESIGN.md`). UI look edits without optical PASS receipt = forbidden (§7a). After PASS → `k1-tab5-lvgl-dashboard` (or the companion the router names).
2. **If the task involves resume / prior work / memory / "did we already" / history narrative** → apply §5 scenario table or invoke `/claude-mem-router` (pick one skill; do not fan out the whole set).
3. **If the task is complex or multi-domain** → invoke `/discover-specialists` and check `.claude/agents/*.md` for a specialist whose scope matches. A specialist subagent often beats a general agent on its domain.
4. **If no installed skill covers the task** → invoke `/find-skills` (`npx skills find <query>`) to search the open skills ecosystem. Do NOT invoke this for tasks covered by installed skills — it is for gaps.
5. **If the task needs an external service** (GitHub, Linear, Slack, browser, database, etc.) → scan the MCP server list in the system prompt and call `mcp_list_tools` on the matching server before using its tools.

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
| **Codex** | `AGENTS.md` (root) | `.codex/skills/` (skills; same inventory as Claude Code / Cursor), `claude-mem` MCP |
| **Cursor** | `.cursor/rules/agent-os.mdc` | `.cursor/skills/` (skills), `claude-mem` MCP |

### UI skills (all three tools)

**Router (start here when unsure):** `/spectrasynq-ui-router` — scenario → one
skill. Design→code always hops to `/spectrasynq-ui-precode-optical-gate` first
(§7a). Playbook: `.claude/skills/spectrasynq-ui-router/SKILL.md` (`.cursor` / `.codex`
twins are **symlinks** to `.claude`). Globals under `~/.{claude,cursor,codex,agents}/skills/`
are re-asserted by `scripts/install-claude-mem-skills.sh` (`link_ui_skills_global`)
and by `setup-project-skills.sh` (`ensure_ui_router_skills`). Optical gate is the
mandatory first hop for design→code (§7a).

### claude-mem skills (all three tools)

**Router (start here when unsure):** `/claude-mem-router` — scenario → one skill.
Canonical table also lives in §5.

Project-local copies live in `.claude/skills/`, `.cursor/skills/`, and
`.codex/skills/`. Reinstall / refresh with:

```bash
bash scripts/install-claude-mem-skills.sh
```

| Skill | Invoke when |
|-------|-------------|
| `/claude-mem-router` | Unsure which memory/recall skill fits — scenario table |
| `/mem-search` | Prior-session recall (`search` → `timeline` → `get_observations`) |
| `/knowledge-agent` | Build/query observation corpora |
| `/timeline-report` | Full-project journey narrative from memory timeline |
| `/how-it-works` | Explain claude-mem capture / injection / storage |
| `/spec-recall` | On-disk-first lane resume (handoff beats memory for current status) |
| `/smart-explore` | Token-cheap AST structural code search (`smart_search` / outline / unfold) |
| `/learn-codebase` | Prime an unfamiliar codebase by reading sources |
| `/weekly-digests` | Week-by-week serial timeline chapters |
| `/memory-authority-gate` | Memory empty/stale/offline — DAF + Tier 0 docs |

If your tool's overlay conflicts with this file, this file wins for
tool-agnostic rules (safety, gates, source-of-truth). The overlay wins only for
tool-specific mechanics (how to invoke a build, where permissions live).

---

Last updated: 2026-08-09
