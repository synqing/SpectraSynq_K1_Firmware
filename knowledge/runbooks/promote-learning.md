---
title: Post-session promote-learning checklist
status: verified
last_verified: 2026-07-13
sources:
  - docs/agent-stack/SWARM-ORCHESTRATION.md § OpenKnowledge promotion workflow
  - knowledge/decisions/agent-stack-promotion-not-sync.md
  - docs/agent-stack/AUTHORITY-CONTRACT.md
owner: knowledge-curator
---

# Post-session promote-learning checklist

Use at **session end** (with [`scripts/agent/post-session-report.md`](../../scripts/agent/post-session-report.md))
when a durable learning may belong in `knowledge/`. **Promotion, not sync** — Claude-mem is
read-only evidence; curated knowledge is written only through this workflow.

Binding policy: [`agent-stack-promotion-not-sync.md`](../decisions/agent-stack-promotion-not-sync.md)

---

## When to promote

Promote only when **all six** criteria pass:

| # | Criterion | Verify |
|---|-----------|--------|
| 1 | **Category match** — learning fits at least one durable type below | One of rows 2–5 |
| 2 | **Architectural decision ratified by Captain** | Authority change, lane ownership, forbidden path |
| 3 | **Runbook proven across 2+ sessions** | Same steps succeeded twice without Captain re-brief |
| 4 | **Research conclusion with verified sources** | Phase test PASS or cited primary sources |
| 5 | **Recurring bug pattern with fix SHA** | Same root cause; `commit:<sha>` in `sources` |
| 6 | **Evidence artifact linkable** | Research doc, test log, PR review, or Captain sign-off path exists for REVIEW/VERIFY |

Rows 2–5 are **alternatives** (at least one required); rows 1 and 6 apply to every promotion.

If any criterion fails, default answer is **do not promote** — record in post-session
report as `openknowledge_promoted: none` and optionally cite Claude-mem ids under
`claude_mem_observations` for episodic history only.

---

## When NOT to promote

| Anti-pattern | Use instead |
|--------------|-------------|
| Session-specific debugging noise | Post-session report + Claude-mem observation |
| Unverified hypotheses | `status: draft` research doc or defer |
| Lane status (active branch, blockers, WIP) | `git status`, `.claude/handoff.md`, `progress.md` (verify freshness) |
| Duplicate of existing decision without new evidence | Update existing doc or add `sources` + `last_verified` after review |

**Forbidden:** auto-sync from Claude-mem, hooks, or MCP into `knowledge/`; agent self-set
`status: verified` without review gate; bot auto-push of knowledge commits.

---

## Review gate steps

Complete in order. Do not skip VERIFY before setting `status: verified`.

```
IDENTIFY → DRAFT → FRONTMATTER → REVIEW → VERIFY → COMMIT → RETRIEVE
```

| Step | Actor | Action | Gate |
|------|-------|--------|------|
| **1. IDENTIFY** | Agent or Captain | Flag durable learning; confirm all six § When to promote criteria | Checklist PASS |
| **2. DRAFT** | Knowledge curator | Create Markdown under `knowledge/decisions/`, `knowledge/runbooks/`, or `knowledge/research/` | `status: draft` |
| **3. FRONTMATTER** | Knowledge curator | Apply template below; cite `claude-mem:<id>`, `commit:<sha>`, `pr:<url>` as applicable | All required keys present |
| **4. REVIEW** | Reviewer agent **or** Captain | Cross-check against code, tests, and existing `knowledge/decisions/`; adversarial review optional for high-risk | Findings doc or inline PASS/FAIL |
| **5. VERIFY** | **Captain** **or** delegated agent (see § Approval paths) | Set `status: verified` + `last_verified: YYYY-MM-DD`; link evidence artifact path | Review gate PASS only |
| **6. COMMIT** | Knowledge curator | Manual `git add` / `git commit`; no auto GitHub sync | Pre-commit / docs policy |
| **7. RETRIEVE** | Any agent | Confirm routing skill finds doc (`knowledge-memory-routing`) | Smoke retrieval |

---

## Frontmatter template (new decision / runbook docs)

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

- Start every new doc as `status: draft`.
- Set `status: verified` only after step 5 (VERIFY) completes.
- Set `last_verified` to the date evidence was last cross-checked (not draft date).
- `sources` must include at least one verifiable pointer (commit, research artifact, or claude-mem id used as citation — not as authority).

---

## Captain vs delegated agent approval paths

| Step | Captain | Delegated agent |
|------|---------|-----------------|
| **Draft** | May draft directly | May draft when scoped to assigned task |
| **Review** | May review | Reviewer agent or Captain per assignment |
| **Verify** (`status: verified`) | Always allowed | **Only** when Captain has explicitly delegated promotion authority for a **scoped task** |
| **Commit** | May commit | Knowledge curator role; manual git only |

**Delegated verification requirements (all mandatory):**

1. Written delegating record names the agent, scope, and evidence path (task row in
   `ACTIONABLE-TASKS.md`, handoff, or Captain message).
2. Review gate completed with linked artifact (`knowledge/research/…`, PR review, or test PASS log).
3. Agent **must not** self-verify without that record and evidence link.

When in doubt, leave `status: draft` and escalate to Captain.

---

## Evidence gathering — Claude-mem (read-only)

Use Claude-mem MCP to **search history**, not to **write** knowledge.

| Tool | Purpose |
|------|---------|
| `search` | Find prior observations by keyword (bug, decision, lane) |
| `timeline` | Session-ordered context around a date or topic |
| `get_observations` | Fetch full text for ids cited in `sources` |

**Workflow:**

1. Search mem for related prior work → note observation ids.
2. Cross-check mem claims against **code, tests, git** (mem loses on conflict).
3. Cite ids in frontmatter `sources:` as `claude-mem:<id>` when promoting.
4. Write curated content to `knowledge/` only via DRAFT → REVIEW → VERIFY.

Routing skill: [`.cursor/skills/knowledge-memory-routing/SKILL.md`](../../.cursor/skills/knowledge-memory-routing/SKILL.md)

---

## Post-session fields

In [`scripts/agent/post-session-report.md`](../../scripts/agent/post-session-report.md):

```text
openknowledge_promoted: <knowledge/path.md|none>
claude_mem_observations: <ids or one-line summary used as evidence only>
```

- `openknowledge_promoted: none` — default when no promotion criteria met.
- Path — relative from repo root, e.g. `knowledge/decisions/agent-stack-promotion-not-sync.md`.

---

## Related

- Full workflow spec: [`SWARM-ORCHESTRATION.md` § Promotion](../../docs/agent-stack/SWARM-ORCHESTRATION.md#openknowledge-promotion-workflow)
- Policy ADR: [`agent-stack-promotion-not-sync.md`](../decisions/agent-stack-promotion-not-sync.md)
- Manual git policy: [`openknowledge-manual-git-policy.md`](./openknowledge-manual-git-policy.md)
- Phase 3 task P3-03 evidence: this runbook
