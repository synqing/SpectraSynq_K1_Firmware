---
title: Phase 3 Test 1 — Fresh-Agent Handoff
status: verified
last_verified: 2026-07-13
sources:
  - knowledge/index.md
  - docs/agent-stack/AUTHORITY-CONTRACT.md
  - knowledge/current-priorities.md
  - docs/agent-stack/ACTIONABLE-TASKS.md (out-of-scope for simulation; cited for gap analysis)
owner: tester
---

# Phase 3 Test 1 — Fresh-Agent Handoff

**Scenario:** Cold-start agent reads only promoted knowledge entrypoints (no Claude-mem).  
**Acceptance target (P3-04):** Agent completes scoped task without Captain re-brief.

## Inputs read (simulation)

| File | Read |
|------|------|
| `knowledge/index.md` | Yes |
| `docs/agent-stack/AUTHORITY-CONTRACT.md` | Yes |
| `knowledge/current-priorities.md` | Yes |
| Claude-mem | **No** (by design) |
| `docs/agent-stack/ACTIONABLE-TASKS.md` | **No** (gap test) |
| Git / `session-bootstrap.sh` | **No** (gap test) |

## Results

### 1. Authority — PASS

From `AUTHORITY-CONTRACT.md` + `knowledge/index.md`, a cold agent can determine:

- **Implemented truth** → code + tests + git
- **Process / safety** → `AGENT_OS.md`, `AGENTS.md`, `.claude/CLAUDE.md` (referenced, not loaded)
- **Durable knowledge** → `knowledge/` with `status` + `last_verified`
- **Episodic history** → Claude-mem only; not lane truth
- **Precedence chain** when sources conflict (git → platformio → lane docs → process → knowledge → mem → chat)
- **Promotion rule:** no auto-sync Claude-mem → OpenKnowledge

Inline routing summary at AUTHORITY-CONTRACT § "Routing skill (minimal content)" covers the 8 query types without loading the skill file.

**Caveat:** Firmware safety gates (flash prohibition, build wrapper, calibration policy) live in `AGENT_OS.md` — agent knows *where* to look but cannot enforce without reading it.

### 2. Lane — PARTIAL PASS

From `current-priorities.md`:

| Track | Stated lane | Verifiable from 3 files? |
|-------|-------------|--------------------------|
| **Firmware** | IM73D122 productionization; ref branch `lane/im73d-pdm-eval`; blocker = R2 production-shape hardware proof | Structure yes; **current branch no** |
| **Agent stack** | Phase 2 IN PROGRESS (markdown pilot); P2-08 Captain go/no-go pending; MCP blocked | Yes |
| **Bootstrap** | Git beats docs; `repo-truth` dual-track (firmware blocked on FAIL; docs-only agent-stack allowed when scoped) | Policy yes; **live FAIL/PASS unknown** |

Agent correctly learns: **do not trust handoff/progress without git verify**. Cannot confirm whether firmware work is allowed this session.

### 3. Next action — FAIL

From the 3-file corpus alone, agent **cannot** determine:

- That Phase 3 coexistence testing is active
- Task IDs P3-01..P3-08 or P3-04 acceptance criteria
- Which track this session is scoped to (firmware vs agent-stack vs test harness)
- Concrete next step beyond generic pointers:
  - Firmware: "R2 hardware proof" (needs lane handover docs)
  - Agent stack: "P2-08 Captain go/no-go" (blocking item, not agent-executable)

`current-priorities.md` phase ledger stops at **Phase 2** — Phase 3 absent.

`knowledge/index.md` references routing skill `knowledge-memory-routing` but does not inline skill path (`.cursor/skills/...`); contract §183–196 is sufficient for routing logic only.

### 4. Without Claude-mem

| Need | Satisfied? |
|------|------------|
| Authority / routing rules | Yes |
| Current lane *labels* | Yes |
| Prior session debugging context | No (by design) |
| Scoped task assignment | No |
| Stale-doc detection | Requires bootstrap, not in 3 files |

## Gaps (remediation backlog)

| ID | Gap | Severity | Remediation |
|----|-----|----------|-------------|
| G1 | Phase 3 not in `current-priorities.md` ledger | **H** | Add Phase 3 row + pointer to `ACTIONABLE-TASKS.md` § Phase 3 |
| G2 | Scoped task not in promoted knowledge | **H** | Add `knowledge/runbooks/fresh-agent-handoff.md` or frontmatter `active_task:` in index |
| G3 | Bootstrap ritual not in 3-file set | **M** | Index "Minimum before acting" bullet: `session-bootstrap.sh` + git verify |
| G4 | `AGENT_OS.md` not reachable from index alone | **M** | Already linked; consider 1-line safety summary in index |
| G5 | Lane handover docs referenced but not summarized | **M** | One-line "firmware next step" in `current-priorities.md` when git-verified |
| G6 | P3-04 test procedure not self-describing | **L** | This file satisfies once committed |

## P3-01 cross-check (out of simulation scope)

Routing skill exists at:

- `.cursor/skills/knowledge-memory-routing/SKILL.md`
- `.claude/skills/knowledge-memory-routing/SKILL.md`

Content aligns with AUTHORITY-CONTRACT §183–196 (routing table, precedence, anti-patterns). **Recommend P3-01 → DONE** in `ACTIONABLE-TASKS.md`.

## Test verdict

| Metric | Result |
|--------|--------|
| Authority determination | **PASS** |
| Lane structure determination | **PARTIAL PASS** |
| Scoped next action without re-brief | **FAIL** |
| **P3-04 gate** | **FAIL** (this run) |

**Conclusion:** Promoted knowledge supports authority routing and dual-track awareness. It does **not** yet support autonomous scoped-task execution — agent needs `ACTIONABLE-TASKS.md`, bootstrap/git verify, or explicit task frontmatter. Phase 3 ledger gap in `current-priorities.md` is the highest-leverage fix.

## Evidence

- Simulation date: 2026-07-13
- Agent: cursor (read-only subagent `8731edfe`)
- No firmware edits; no Captain prompts; no Claude-mem queries
