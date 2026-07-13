# Agent Stack Authority Contract — SpectraSynq

**Status:** Ratified 2026-07-13  
**Scope:** SpectraSynq K1 Firmware repo and sibling SpectraSynq workspaces  
**Supersedes:** Ad-hoc tool adoption decisions; does **not** supersede `AGENT_OS.md` for firmware safety gates

---

## Purpose

This document is the **single source of truth** for which system owns which class of information and which operations. Agents must not invent parallel authority paths. When two sources disagree, resolve using the precedence order below.

**Deferral with `AGENT_OS.md`:** Firmware safety gates, bootstrap ritual, flash/upload prohibition, and firmware lane verification are owned by `AGENT_OS.md` and are not overridden by this contract. This contract owns agent-stack tool domains, promotion boundaries, and cross-tool orchestration.

---

## Authority table

| Domain | Owner | What it holds | Agents may… | Agents must NOT… |
|--------|-------|---------------|-------------|------------------|
| **Implemented truth** | Code + tests | Behavior, APIs, pin maps, build flags, regression oracles | Read, modify per lane scope, prove via pytest/PIO | Treat docs or memory as substitute for code |
| **Agent execution rules** | `AGENTS.md`, `.claude/CLAUDE.md`, `AGENT_OS.md` | Safety gates, build discipline, lane verification, claude-mem policy | Follow; propose edits via Captain approval | Auto-rewrite rules from session memory |
| **Durable curated knowledge** | OpenKnowledge (`knowledge/`) | Architecture decisions, runbooks, product context, verified research | Read; **promote** vetted learnings via workflow | Auto-sync from Claude-mem; treat as live lane state |
| **Session / episodic history** | Claude-mem | Debugging trails, prior attempts, recurrence patterns, session notes | Search at task start; record at checkpoints | Use as current branch/lane truth |
| **Commit provenance** | Entire (pilot) | Local checkpoint lineage tied to agent sessions | Enable in pilot repo only; audit handoffs | Push sessions to remote; replace git as truth |
| **Human supervision console** | Herdr | Operator visibility across repos, human-in-loop checkpoints | One workspace per repo; Captain reviews | Route core agent work through Herdr |
| **Claude ↔ Codex transfer** | `openai/codex-plugin-cc` | Manual review, adversarial pass, rescue, scoped handoff | Invoke **manually** per handoff contract | Enable auto stop-gate; silent Codex takeover |
| **Multi-agent orchestration** | Ruflo (pilot, isolated) | Parallel lane dispatch, eval-task orchestration | Minimal init in isolated worktree only | Full init, daemon, memory, routing, federation |
| **Context compression** | Headroom (benchmark only) | Token/headroom A/B measurements | Run compression-only experiments | Use for memory, learn, instruction writes, output shaping |
| **Provider routing** | First-party direct APIs | Model/provider selection | Use vendor defaults (Anthropic, OpenAI, Cursor) | OmniRoute as primary gateway; silent fallback |
| **Operator DB snapshots** | sqlite-utils | Read-only inspection of local SQLite stores | Query, export, diff snapshots | Write production state via sqlite-utils |
| **Lane / git state** | Git branch + HEAD + working tree | Current implementation state | Verify before every session (`session-bootstrap.sh`) | Trust stale handoff without verification |

---

## Precedence when sources conflict

1. **Git branch + HEAD + working tree** (current implementation)
2. **`platformio.ini` + upload guards** (hardware/env truth)
3. **Lane-specific docs** confirmed fresh by `repo-truth.sh`
4. **`AGENT_OS.md` + `.claude/CLAUDE.md` + `AGENTS.md`** (process)
5. **OpenKnowledge** (`status: verified` entries with recent `last_verified`)
6. **Claude-mem** (historical context only)
7. **Session chat** (lowest — never authoritative)

---

## OpenKnowledge vs Claude-mem (non-negotiable)

| | OpenKnowledge | Claude-mem |
|---|---------------|------------|
| **Nature** | Curated, durable, Markdown-in-Git | Episodic, searchable session history |
| **Write path** | **Promotion workflow** (human/agent review → PR/commit) | Hook pipeline observations (Claude Code, Codex, Cursor) |
| **Read path** | MCP + repo `knowledge/` + routing skill | MCP search/timeline at session start |
| **Forbidden** | Auto-sync from Claude-mem | Treating as implementation or lane truth |

**Promotion rule:** A learning enters OpenKnowledge only when an agent or Captain explicitly promotes it with frontmatter (`status`, `last_verified`, `sources`). Claude-mem entries are **citations**, not automatic imports.

---

## Tool decisions (binding)

### Adopt now

| Tool | Role |
|------|------|
| **Herdr** | Human ops console; one workspace per repo |
| **Codex plugin (`openai/codex-plugin-cc`)** | Manual Claude↔Codex handoff (review, adversarial, rescue) |
| **sqlite-utils** | Operator read-only snapshots |

### Controlled pilots

| Tool | Role | Constraints |
|------|------|-------------|
| **OpenKnowledge v0.29.1** | Project-scoped durable knowledge | Pre-1.0 maturity risk; manual git commits; no auto GitHub sync initially; MCP registration in **`.mcp.json`** (Claude Code) **and `.cursor/mcp.json`** (Cursor, `open-knowledge` only) — editor split intentional; **no user-global** OK MCP configs |
| **Entire CLI** | Commit provenance | One private repo; `--local --skip-push-sessions --telemetry=false` |
| **Ruflo** | Orchestration-only eval | Minimal init; no daemon/memory/RAG/SONA/routing |

### Benchmark later

| Tool | Role | Constraints |
|------|------|-------------|
| **Headroom** | Compression A/B | Exclude memory, learn, instruction writes, output shaping |

### Explicit rejections

| Tool | Reason |
|------|--------|
| **pxpipe** | Silent exact-value corruption — **REJECT** |
| **OmniRoute (primary gateway)** | Lab only; no silent fallback for core work — **REJECT as primary** |

---

## Ruflo pilot boundaries (hard limits)

```bash
export RUFLO_DAEMON_AUTOSTART=0
npx ruflo@latest init --minimal --no-global
```

**Forbidden during pilot:**

- CLI **and** marketplace simultaneously
- `--dual`, `--all-agents`
- Daemon autostart
- Ruflo memory / RAG / SONA
- Instruction rewriting
- Federation
- Provider routing
- Background workers

**Allowed:** Orchestration dispatch for three defined eval tasks in an **isolated git worktree**.

---

## Entire pilot boundaries

```bash
entire enable --agent claude-code --local --skip-push-sessions --telemetry=false
```

- One private pilot repository
- Local checkpoints only
- No session push to remote
- Telemetry off
- Does not replace git log or OpenKnowledge

---

## Codex plugin boundaries

**Allowed use cases (manual invocation only):**

- Second-opinion / adversarial review
- Scoped implementation transfer (rescue lane)
- Cross-tool handoff with explicit contract

**Forbidden:**

- Automatic stop-gate (Codex intercepts Claude without Captain intent)
- Silent replacement of Claude Code as primary executor
- Bypassing `AGENT_OS.md` firmware safety rules

---

## Herdr workspace contract

- **One Herdr workspace per git repository** (e.g. `SpectraSynq_K1_Firmware`, future Tab5 repo)
- Herdr is **supervision**, not execution authority
- AGPL license note: review compliance before org-wide deploy
- Captain uses Herdr for fleet visibility and human checkpoint sign-off

---

## OpenKnowledge layout (recommended)

```
knowledge/
├── index.md
├── product/
├── architecture/
├── current-priorities.md
├── decisions/          # ADR-style; status + last_verified + sources
├── runbooks/
└── research/
```

**Frontmatter (required on promoted docs):**

```yaml
---
status: draft | verified | stale
last_verified: YYYY-MM-DD
sources:
  - claude-mem:<id>   # optional citation
  - commit:<sha>      # optional
  - pr:<url>          # optional
---
```

---

## Routing skill (minimal content — authority summary)

Agents load a routing skill that answers:

1. **Need current implementation?** → Code/tests + git state
2. **Need process/safety rules?** → `AGENT_OS.md`, `AGENTS.md`, `.claude/CLAUDE.md`
3. **Need durable decision or runbook?** → OpenKnowledge `knowledge/` (check `status` + `last_verified`)
4. **Need what happened last session / prior bug?** → Claude-mem search → timeline → observations
5. **Need commit/session lineage?** → Entire (pilot repo only)
6. **Need human checkpoint?** → Herdr + Captain
7. **Need second implementer?** → Codex plugin (manual handoff contract)
8. **Need parallel lanes?** → Ruflo pilot worktree only

**Never:** Sync Claude-mem → OpenKnowledge without promotion workflow.

---

## Firmware repo invariant (unchanged)

This authority contract governs **agent tooling and knowledge**. It does **not** relax:

- No firmware edits unless explicitly scoped
- No flash/upload/erase without Captain approval
- Build via `bash scripts/agent/pio-build.sh <env>` only
- Pre-commit gate (pytest + PIO) before firmware commits

---

## Changelog

| Date | Author | Change |
|------|--------|--------|
| 2026-07-13 | agent:cursor | Phases 0–6 DONE; standard stack v1 promoted — [`STANDARD-STACK.md`](./STANDARD-STACK.md) |
| 2026-07-13 | agent:cursor | Phase 0 ratified; Phase 1 IN PROGRESS; knowledge/ scaffold + routing skill |
| 2026-07-13 | agent:orchestrator | Initial authority contract from architecture review |
