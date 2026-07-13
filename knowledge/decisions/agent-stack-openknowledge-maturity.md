---
title: OpenKnowledge v0.29.1 Pre-1.0 Maturity Risk
status: verified
last_verified: 2026-07-13
sources:
  - docs/agent-stack/AUTHORITY-CONTRACT.md
  - docs/agent-stack/PHASED-ROLLOUT.md Phase 2
owner: knowledge-curator
---

# OpenKnowledge v0.29.1 — Pre-1.0 Maturity Risk

## Context

OpenKnowledge is adopted as a **controlled pilot** for project-scoped durable
knowledge (`knowledge/`). The pinned pilot version is **v0.29.1**, which is
**pre-1.0** and may introduce breaking changes to MCP tools, frontmatter schema,
or sync behaviour without semver guarantees.

## Install coordinates (authoritative)

| Wrong coordinate | Correct coordinate |
|------------------|-------------------|
| `openknowledge@0.29.1` (npm 404) | **`@inkeep/open-knowledge@0.29.1`** |
| Bare `openknowledge` on npm registry | Scoped package `@inkeep/open-knowledge` |

MCP launcher (project `.mcp.json` / `.cursor/mcp.json`): `npx -y @inkeep/open-knowledge@0.29.1 mcp`.
Install proof: [`phase2-openknowledge-mcp-proof.md`](../research/phase2-openknowledge-mcp-proof.md).

## Risk assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Breaking MCP API before 1.0 | Medium | Pin version; pilot one repo; manual git commits only |
| Schema drift in frontmatter | Low | Repo-owned Markdown is source; OK is index/MCP layer |
| False authority (stale `verified` docs) | High | Require `last_verified`; routing skill checks git/code |
| Auto-sync from Claude-mem | High | **Forbidden** — promotion workflow only |
| Scope creep to firmware lane | High | `knowledge/` is docs; no firmware edits via OK pilot |

## Pilot constraints (binding)

1. **Project scope only** — this repo's `knowledge/` directory; no org-wide deploy until Phase 6.
2. **Manual git commits** — no auto GitHub sync or bot push in Phase 2 pilot.
3. **Pin version** — document exact OK version at install time in runbook (Phase 2).
4. **Code wins** — if `knowledge/` disagrees with code/tests, file a bug or update knowledge; never treat OK as implementation truth.

## Rollback triggers

Execute rollback to **Phase 1 only** (Claude-mem + git docs, no OpenKnowledge MCP) if any of:

| Trigger | Action |
|---------|--------|
| OK MCP corrupts or auto-writes `knowledge/` without promotion | Disable MCP; revert bad commits; document incident |
| Two agents cite conflicting `status: verified` decisions with same topic | Freeze promotions; Captain resolves; add precedence note |
| OK upgrade breaks retrieval and blocks agent sessions | Pin previous version or disable MCP; continue with repo Markdown + grep |
| Auto-sync pipeline discovered (Claude-mem → OK) | **Immediate stop** — remove pipeline; audit per P3-07 |
| Captain Phase 2 go/no-go = **no-go** | Archive pilot config; keep `knowledge/` as plain Markdown in git |

## Rollback procedure

1. Disable OpenKnowledge MCP in operator config.
2. Retain `knowledge/` Markdown in git (plain files remain useful).
3. Update [`PHASED-ROLLOUT.md`](../../docs/agent-stack/PHASED-ROLLOUT.md) status to rolled back.
4. Record incident in `knowledge/decisions/` if rollback was triggered by failure.

## Review cadence

Re-verify this decision at **Phase 2 exit gate** and before any OK version bump.
