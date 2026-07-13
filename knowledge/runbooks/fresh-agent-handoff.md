---
title: Fresh-agent cold-start handoff (Phase 3 Test 1)
status: verified
last_verified: 2026-07-13
sources:
  - docs/agent-stack/SWARM-ORCHESTRATION.md § Scenario 1
  - docs/agent-stack/ACTIONABLE-TASKS.md P3-04
  - AGENT_OS.md § Session bootstrap ritual
owner: knowledge-curator
---

# Fresh-agent cold-start handoff

**Phase 3 task P3-04 (Test 1).** A new agent session with **zero chat history** completes a scoped task using promoted knowledge + code — no Captain oral re-brief.

## Preconditions

- Task scope is explicit (docs-only, firmware, or mixed) and recorded in the assignment or `ACTIONABLE-TASKS` row.
- Required runbooks/decisions already exist under `knowledge/` with `status: verified` frontmatter.

## Cold-start read order (mandatory)

Read in this sequence before substantive work:

| # | Source | Why |
|---|--------|-----|
| 1 | [`knowledge/index.md`](../index.md) | Navigation, maturity disclaimer, minimum-before-acting |
| 2 | [`docs/agent-stack/AUTHORITY-CONTRACT.md`](../../docs/agent-stack/AUTHORITY-CONTRACT.md) | Ownership boundaries: code vs rules vs durable knowledge vs episodic memory |
| 3 | [`knowledge/current-priorities.md`](../current-priorities.md) | Phase ledger + active firmware lane; verify against git |
| 4 | [`docs/agent-stack/ACTIONABLE-TASKS.md`](../../docs/agent-stack/ACTIONABLE-TASKS.md) — **active phase section** | Numbered tasks, acceptance criteria, dependencies for the assigned phase |
| 5 | **Bootstrap** — run and read output | See § Bootstrap ritual below |

Then load task-specific surfaces only as needed:

- Routing skill: `.cursor/skills/knowledge-memory-routing/SKILL.md` (mirror in `.claude/skills/`)
- Lane handoff: [`.claude/handoff.md`](../../.claude/handoff.md) — **historical** unless git confirms freshness
- Process/safety: [`AGENT_OS.md`](../../AGENT_OS.md), [`.claude/CLAUDE.md`](../../.claude/CLAUDE.md)

## Bootstrap ritual

```bash
bash scripts/agent/session-bootstrap.sh
git branch --show-current
git rev-parse --short HEAD
git status --short
```

| Bootstrap exit | `repo-truth` OVERALL | Firmware edits / `pio-build.sh` | Docs-only `knowledge/` / `docs/agent-stack/` |
|----------------|----------------------|----------------------------------|-----------------------------------------------|
| **0** | **PASS** | Allowed per lane scope | Allowed per scope |
| **0** | **WARN** | Allowed per lane scope; heed bootstrap `WARN:` lines (not a firmware block) | Allowed per scope |
| **nonzero** | **FAIL** | **Blocked** until FAIL resolved | Allowed when task is explicitly docs-only and FAIL is acknowledged in the artifact |

Record bootstrap exit code, branch, HEAD, and dirty/untracked state in the task evidence log.

## Dual-track note (repo-truth FAIL only)

**WARN** does not fail bootstrap (exit 0). Dual-track applies when OVERALL is **FAIL**.

Firmware lane integrity (`scripts/agent/repo-truth.sh`) and agent-stack governance are **orthogonal**:

- **Firmware track** — blocked on bootstrap FAIL: no firmware source, no `platformio.ini` behavior changes, no build/upload commits until PASS.
- **Agent-stack docs track** — may proceed under FAIL when scope is docs-only; FAIL must be **acknowledged**, not ignored.

Authority: [`decisions/agent-stack-repo-truth-dual-track.md`](../decisions/agent-stack-repo-truth-dual-track.md).

A branch name in `current-priorities.md` is a **reference default**, not a mandate. Git at session start wins.

## Test 1 pass / fail

| Pass | Fail |
|------|------|
| Task complete without Captain re-brief | Captain had to orally re-brief lane or authority |
| Cites `knowledge/` paths with frontmatter where applicable | Used stale handoff as lane truth |
| Bootstrap + git lane recorded in evidence | Wrong authority source (e.g. Claude-mem as current lane) |
| Scope respected (firmware blocked only under FAIL, not WARN) | Firmware work attempted under repo-truth FAIL |

Archive evidence under `knowledge/research/` (e.g. `agent-stack-phase3-test1-*.md`) per [`PHASED-ROLLOUT.md`](../../docs/agent-stack/PHASED-ROLLOUT.md) Phase 3 exit gate.

## Cross-links

- Phase 3 backlog: [`ACTIONABLE-TASKS.md`](../../docs/agent-stack/ACTIONABLE-TASKS.md) § Phase 3
- Phase ledger: [`current-priorities.md`](../current-priorities.md)
- Scenario definition: [`SWARM-ORCHESTRATION.md`](../../docs/agent-stack/SWARM-ORCHESTRATION.md) § Test scenarios — Scenario 1
