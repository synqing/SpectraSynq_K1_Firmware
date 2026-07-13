---
name: promote-learning
description: "Promote durable learnings from Claude-mem into knowledge/ via reviewed workflow — promotion not sync; frontmatter, review gate, manual commit"
---

# Promote Learning

Use at **session end** when a learning may belong in curated `knowledge/`.
Full checklist: [`knowledge/runbooks/promote-learning.md`](../../knowledge/runbooks/promote-learning.md)

Authority: [`docs/agent-stack/AUTHORITY-CONTRACT.md`](../../docs/agent-stack/AUTHORITY-CONTRACT.md)  
Workflow spec: [`docs/agent-stack/SWARM-ORCHESTRATION.md`](../../docs/agent-stack/SWARM-ORCHESTRATION.md) § Promotion  
Policy ADR: [`knowledge/decisions/agent-stack-promotion-not-sync.md`](../../knowledge/decisions/agent-stack-promotion-not-sync.md)

## Golden rule

**Promotion, not synchronization.** Claude-mem is read-only evidence. Write to `knowledge/`
only through the steps below. Never auto-dump session history.

---

## When to promote (all six required)

| # | Criterion | Verify |
|---|-----------|--------|
| 1 | **Category match** — fits durable type (decision, runbook, research) | One of rows 2–5 |
| 2 | **Architectural decision ratified by Captain** | Authority / lane / forbidden path |
| 3 | **Runbook proven across 2+ sessions** | Same steps succeeded twice |
| 4 | **Research conclusion with verified sources** | Phase test PASS or primary sources |
| 5 | **Recurring bug pattern with fix SHA** | `commit:<sha>` in `sources` |
| 6 | **Evidence artifact linkable** | Research doc, test log, PR, or Captain sign-off |

Rows 2–5 are **alternatives** (≥1 required). Rows 1 and 6 apply to every promotion.

**Default:** `openknowledge_promoted: none` in post-session report when any criterion fails.

---

## Workflow (do not skip VERIFY)

```
IDENTIFY → DRAFT → FRONTMATTER → REVIEW → VERIFY → COMMIT → RETRIEVE
```

| Step | Action | Gate |
|------|--------|------|
| **IDENTIFY** | Confirm all six criteria | Checklist PASS |
| **DRAFT** | Create under `knowledge/decisions/`, `runbooks/`, or `research/` | `status: draft` |
| **FRONTMATTER** | Apply template; cite `claude-mem:<id>`, `commit:<sha>`, `pr:<url>` | Required keys present |
| **REVIEW** | Cross-check code, tests, existing decisions | PASS/FAIL artifact |
| **VERIFY** | Captain or delegated agent sets `status: verified` + `last_verified` | Review gate PASS only |
| **COMMIT** | Manual `git add` / `git commit` | No auto-push |
| **RETRIEVE** | Routing skill finds doc | Smoke via `knowledge-memory-routing` |

---

## Frontmatter template

```yaml
---
title: <Decision or runbook title>
status: draft
last_verified: YYYY-MM-DD
tags:
  - <optional-topic>
sources:
  - claude-mem:<observation-id>
  - commit:<sha>
  - pr:<url>
owner: knowledge-curator
---
```

- Start as `status: draft`. Set `verified` only after VERIFY.
- `last_verified` = date evidence was last cross-checked.
- `sources` must include at least one verifiable pointer.

---

## Captain vs delegated VERIFY

| Step | Captain | Delegated agent |
|------|---------|-----------------|
| Draft | Allowed | Scoped task only |
| Review | Allowed | Reviewer agent or Captain |
| Verify (`status: verified`) | Always | **Only** with explicit delegation record + evidence link |
| Commit | Allowed | Knowledge curator; manual git |

Delegated verify requires: (1) written scope in `ACTIONABLE-TASKS.md`, handoff, or Captain message;
(2) completed review gate with linked artifact; (3) **no** self-verify without that record.

---

## Claude-mem (read-only evidence)

| Tool | Purpose |
|------|---------|
| `search` | Find prior observations by keyword |
| `timeline` | Session-ordered context |
| `get_observations` | Full text for cited ids |

1. Search mem → note observation ids.  
2. Cross-check mem against **code, tests, git** (mem loses on conflict).  
3. Cite ids in `sources:` as `claude-mem:<id>`.  
4. Write curated content only via DRAFT → REVIEW → VERIFY.

---

## Anti-patterns (forbidden)

| Anti-pattern | Use instead |
|--------------|-------------|
| Session debugging noise | Post-session report + mem observation |
| Unverified hypotheses | `status: draft` research or defer |
| Lane status (branch, blockers) | `git status`, `.claude/handoff.md`, `progress.md` |
| Duplicate decision without new evidence | Update existing doc + `last_verified` |
| Auto-sync mem → `knowledge/` via hooks or MCP | This workflow only |
| Agent self-set `verified` without review | Leave `draft`; escalate |

---

## Post-session fields

In [`scripts/agent/post-session-report.md`](../../scripts/agent/post-session-report.md):

```text
openknowledge_promoted: <knowledge/path.md|none>
claude_mem_observations: <ids or one-line summary>
```

---

## Related skills

- `knowledge-memory-routing` — which source wins for a query type
- `/spec-recall` — lane recall via spec-index + claude-mem
