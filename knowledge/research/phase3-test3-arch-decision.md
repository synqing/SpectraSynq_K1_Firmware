---
title: Phase 3 Test 3 — Architectural Decision Retrieval
status: verified
last_verified: 2026-07-13
sources:
  - knowledge/decisions/agent-stack-authority-ratified-2026-07-13.md
  - knowledge/decisions/agent-stack-autonomous-execution.md
  - knowledge/decisions/agent-stack-repo-truth-dual-track.md
  - knowledge/decisions/agent-stack-openknowledge-maturity.md
  - docs/agent-stack/SWARM-ORCHESTRATION.md § Promotion
  - docs/agent-stack/SWARM-ORCHESTRATION.md § Scenario 3
owner: knowledge-curator
test_scenario: phase3-test3-arch-decision
---

# Phase 3 Test 3 — Architectural Decision Retrieval

**Scenario:** SWARM-ORCHESTRATION.md § Scenario 3 — agent loads `knowledge/decisions/` with `status: verified`, cites `last_verified`, applies to implementation choice.

**Execution date:** 2026-07-13  
**Method:** Keyword grep + frontmatter audit + cross-link trace (Markdown-only pilot; OpenKnowledge MCP blocked per `knowledge/research/phase2-openknowledge-mcp-proof.md`). **MCP follow-up:** [`phase3-test3-mcp-retrieval-addendum.md`](./phase3-test3-mcp-retrieval-addendum.md) — **PASS** (2026-07-13).

## Query results

### 1. Ratification

| Field | Value |
|-------|-------|
| **File** | `knowledge/decisions/agent-stack-authority-ratified-2026-07-13.md` |
| **Frontmatter** | `status: verified`, `last_verified: 2026-07-13`, `owner: Captain` |
| **Decision** | Captain ratified agent-stack rollout + `docs/agent-stack/AUTHORITY-CONTRACT.md`; does not supersede `AGENT_OS.md` firmware gates |
| **Phase 0 exit** | Authority ratified, OK maturity documented, promotion workflow defined, docs-only Phase 0 |

**Retrieval quality:** **HIGH** — filename and title match query; single authoritative ADR.

### 2. Autonomous execution

| Field | Value |
|-------|-------|
| **File** | `knowledge/decisions/agent-stack-autonomous-execution.md` |
| **Frontmatter** | `status: verified`, `last_verified: 2026-07-13`, `owner: knowledge-curator` |
| **Decision** | Agents MAY install enumerated Phase 1–2 operator tools when matching `ACTIONABLE-TASKS` ID is active; Captain blockers only for credentials, license click-through, sudo, flash/upload, rejected tools |
| **Allowlist** | sqlite-utils, Herdr, Codex plugin (`codex@openai-codex`); OpenKnowledge v0.29.1 Phase 2 only (install blocked) |
| **Forbidden** | ReviewGate auto stop-gate, Claude-mem → OK auto-sync, Ruflo full init, OmniRoute primary, pxpipe, firmware upload |

**Retrieval quality:** **HIGH** — dedicated ADR with enumerated allowlist table and AGENT_OS alignment note.

### 3. Dual-track (repo-truth FAIL)

| Field | Value |
|-------|-------|
| **File** | `knowledge/decisions/agent-stack-repo-truth-dual-track.md` |
| **Frontmatter** | `status: verified`, `last_verified: 2026-07-13`, `owner: knowledge-curator` |
| **Decision** | When `repo-truth` FAIL: firmware track blocked (no firmware/`platformio.ini` edits, no pio-build, no flash); agent-stack docs track may proceed if explicitly docs-only, FAIL acknowledged, not treated as firmware PASS |
| **Orthogonality** | Firmware lane = branch + HEAD; agent-stack rollout does not override lane verification |

**Retrieval quality:** **HIGH** — title contains "dual-track"; explicit allow/deny tables; cross-links to autonomous-execution ADR.

### 4. Promotion-not-sync

| Field | Value |
|-------|-------|
| **Primary ADR (partial)** | `knowledge/decisions/agent-stack-openknowledge-maturity.md` — L27: "Auto-sync from Claude-mem \| High \| **Forbidden** — promotion workflow only" |
| **Index pointer** | `knowledge/index.md` L46: "**Promotion, not sync.**" |
| **Ratification cross-ref** | `agent-stack-authority-ratified-2026-07-13.md` Phase 0 table cites `SWARM-ORCHESTRATION.md` § Promotion |
| **Canonical workflow** | `docs/agent-stack/SWARM-ORCHESTRATION.md` L250–291 — NOT auto-sync; review gate before `status: verified`; manual git commit |

**Retrieval quality:** **MEDIUM** — policy is binding and verified in maturity ADR, but **no dedicated `knowledge/decisions/*promotion*.md`**. Agent relying only on `decisions/` grep for "promotion-not-sync" may miss the full approval table unless routing skill or index is consulted.

## Frontmatter verification (all `knowledge/decisions/`)

| File | `status` | `last_verified` | `owner` |
|------|----------|-----------------|---------|
| `agent-stack-authority-ratified-2026-07-13.md` | verified | 2026-07-13 | Captain |
| `agent-stack-autonomous-execution.md` | verified | 2026-07-13 | knowledge-curator |
| `agent-stack-repo-truth-dual-track.md` | verified | 2026-07-13 | knowledge-curator |
| `agent-stack-openknowledge-maturity.md` | verified | 2026-07-13 | knowledge-curator |

**Result:** 4/4 decision files pass `status: verified` check.

## Retrieval quality assessment

| Dimension | Score | Notes |
|-----------|-------|-------|
| **Discoverability (grep)** | 3/4 direct | "promotion-not-sync" not in decision filenames or H1s |
| **Frontmatter completeness** | 5/5 | All decisions have title, status, last_verified, sources, owner |
| **Cross-linking** | 5/5 | Dual-track ↔ autonomous-execution; ratification ↔ maturity ↔ SWARM |
| **Policy ↔ implementation** | 4/5 | Decisions align with `AGENT_OS.md` deferral; promotion detail lives outside `decisions/` |
| **Stale-handoff resistance** | Pass | `last_verified: 2026-07-13` on all ADRs; index warns code wins |

### Gaps

1. **Promotion-not-sync** lacks a standalone ratified ADR in `knowledge/decisions/` — distributed across maturity risk doc + `SWARM-ORCHESTRATION.md` + `knowledge/index.md`.
2. **Keyword variance:** "ratification" appears in title/frontmatter; "dual-track" in title; "autonomous" in title; "promotion" only in body tables of maturity ADR.
3. ~~**MCP retrieval untested**~~ — **CLOSED** — see [`phase3-test3-mcp-retrieval-addendum.md`](./phase3-test3-mcp-retrieval-addendum.md) (PASS 2026-07-13).

## Scenario 3 verdict

| Criterion (SWARM-ORCHESTRATION.md) | Result |
|------------------------------------|--------|
| Load decision from `knowledge/decisions/` | **PASS** — 4 verified ADRs located |
| Cite with `last_verified` | **PASS** — all `2026-07-13` |
| Apply to implementation choice | **PASS** — dual-track + autonomous allowlist constrain agent behavior under repo-truth FAIL |
| Ignore stale handoff | **PASS** — decisions supersede narrative handoff when frontmatter present |
| Matches code policy | **PASS** — consistent with `AGENT_OS.md` bootstrap FAIL semantics and install allowlist exception |

**Overall:** **PASS** with **MEDIUM** retrieval friction on promotion-not-sync (requires index or SWARM cross-read, not single ADR).

## Recommended follow-ups (non-blocking)

- Promote promotion-not-sync to dedicated `knowledge/decisions/agent-stack-promotion-not-sync.md` (draft → verify) to close grep gap.
- Add `tags:` frontmatter (`ratification`, `dual-track`, `autonomous-execution`, `promotion-not-sync`) for MCP retrieval when OK unblocks.
