---
title: Compact Claude-mem retrieval budget (coexistence with knowledge/)
status: verified
last_verified: 2026-07-13
sources:
  - AGENT_OS.md §5
  - docs/agent-stack/AUTHORITY-CONTRACT.md
owner: knowledge-curator
---

# Compact Claude-mem injection policy

Aligns with `AGENT_OS.md` §5 and Phase 2 coexistence prep (P2-06).

## When to search

| Trigger | Action |
|---------|--------|
| Session start on non-trivial task | Up to **3** `search` calls before acting |
| Lane / bug / "what did we try?" | +1–2 `search` if first pass empty |
| Durable decision needed | **Stop** — read `knowledge/decisions/` first; mem is supplemental |

## Query rules (worker-mode FTS)

- **One term per query** — compound AND/OR/NOT returns zero rows.
- Prefer lane tokens: `IM73D`, `repo-truth`, `agent-stack`, effect names, chip IDs.
- After search: **one** `timeline` narrow + **≤5** `get_observations` IDs total per task.

## Budget caps (per session task)

| Tool | Max calls |
|------|-----------|
| `search` | 5 |
| `timeline` | 2 |
| `get_observations` | 5 observation fetches |

## Authority order

1. Git + code/tests  
2. `knowledge/` (`status: verified`)  
3. Claude-mem (episodic)  
4. Chat memory (never authoritative)

## Promotion gate

Do not paste large mem dumps into `knowledge/`. Promote only via explicit workflow with frontmatter.
