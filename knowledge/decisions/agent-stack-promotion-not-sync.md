---
title: Agent stack — promotion-not-sync policy
status: verified
last_verified: 2026-07-13
tags:
  - promotion-not-sync
  - openknowledge
  - claude-mem
sources:
  - docs/agent-stack/SWARM-ORCHESTRATION.md § Promotion
  - docs/agent-stack/AUTHORITY-CONTRACT.md
  - knowledge/decisions/agent-stack-openknowledge-maturity.md
owner: knowledge-curator
---

# Decision: promotion-not-sync (Claude-mem → OpenKnowledge)

## Context

Claude-mem holds **episodic session history** (searchable, high volume, unreviewed).
OpenKnowledge / `knowledge/` holds **curated durable knowledge** (reviewed, versioned in git).
Phase 3 Test 3 found promotion-not-sync policy binding but **grep-friction** when no
standalone ADR existed — agents grepping `knowledge/decisions/` alone could miss the
full approval table.

## Decision

1. **No auto-sync** from Claude-mem to OpenKnowledge or `knowledge/` — ever. No hooks,
   MCP pipelines, cron jobs, or background agents may copy observations into curated
   knowledge without the promotion workflow.
2. **Promotion only** — durable learnings enter `knowledge/` through the reviewed
   promotion workflow defined in
   [`docs/agent-stack/SWARM-ORCHESTRATION.md` § OpenKnowledge promotion workflow](../../docs/agent-stack/SWARM-ORCHESTRATION.md#openknowledge-promotion-workflow).
3. **Review gate required** — before `status: verified`:
   - Draft with `status: draft` and cited sources (including `claude-mem:<id>` when applicable).
   - Reviewer agent or Captain checks against code/tests.
   - **Captain OR delegated agent** sets `status: verified` + `last_verified` only after
     review gate PASS and linked evidence artifact.
4. **Manual git commit** — promoted knowledge is committed manually; no auto GitHub sync
   or bot push in the Phase 2 pilot.
5. **Authority split** — Claude-mem = history; `knowledge/` = curated intent. Code + tests
   win for implementation behavior; if knowledge disagrees with code, file a bug or update
   knowledge — never treat memory or OK as implementation truth.

## Forbidden (binding)

| Path | Status |
|------|--------|
| Claude-mem → OpenKnowledge MCP auto-write | **Forbidden** |
| Claude-mem → `knowledge/` hook or script | **Forbidden** |
| Agent self-set `status: verified` without review gate | **Forbidden** |
| Auto GitHub sync of `knowledge/` | **Forbidden** (Phase 2 pilot) |

## When to promote

- Architectural decision ratified by Captain
- Runbook proven across 2+ sessions
- Research conclusion with verified sources
- Recurring bug pattern with fix SHA

## When NOT to promote

- Session-specific debugging noise
- Unverified hypotheses
- Lane status (use git + `progress.md` with freshness rules)
- Duplicate of existing decision without new evidence

## Promotion steps (summary)

See full workflow: [`SWARM-ORCHESTRATION.md` § Promotion](../../docs/agent-stack/SWARM-ORCHESTRATION.md#openknowledge-promotion-workflow).

```
IDENTIFY → DRAFT → FRONTMATTER → REVIEW → VERIFY → COMMIT → RETRIEVE
```

## Related decisions

- [`agent-stack-openknowledge-maturity.md`](./agent-stack-openknowledge-maturity.md) — rollback if auto-sync discovered
- [`agent-stack-autonomous-execution.md`](./agent-stack-autonomous-execution.md) — agents MUST NOT enable auto-sync
- [`agent-stack-authority-ratified-2026-07-13.md`](./agent-stack-authority-ratified-2026-07-13.md) — Phase 0 promotion workflow ratified

## Evidence

- Phase 3 Test 3 retrieval: [`knowledge/research/phase3-test3-arch-decision.md`](../research/phase3-test3-arch-decision.md)
- Auditor task P3-07: grep/config audit **PASS** — [`phase3-p3-07-auto-sync-audit.md`](../research/phase3-p3-07-auto-sync-audit.md); prior inline log [`repo-truth-im73d-manifest-check-2026-07-13.md`](./repo-truth-im73d-manifest-check-2026-07-13.md) § P3-07
