---
title: Phase 3 Test 3 — MCP retrieval addendum
status: verified
last_verified: 2026-07-13
sources:
  - knowledge/research/phase3-test3-arch-decision.md
  - knowledge/research/phase2-openknowledge-mcp-proof.md
  - .mcp.json (open-knowledge @0.29.1)
owner: knowledge-curator
test_scenario: phase3-test3-mcp-retrieval
---

# Phase 3 Test 3 — MCP retrieval addendum

**Follow-up to:** [`phase3-test3-arch-decision.md`](./phase3-test3-arch-decision.md) gap #3 (MCP retrieval untested).  
**Execution date:** 2026-07-13  
**OK pin:** `@inkeep/open-knowledge@0.29.1` (Captain note: MCP live `7351cae5`)

## Verdict

| Test | Result |
|------|--------|
| **MCP `search` vs markdown-only pilot** | **PASS** |
| **Scenario 3 overall (with MCP)** | **PASS** — retrieval friction on promotion-not-sync **closed** |

## Method

OpenKnowledge MCP `search` with `cwd` = workspace root, `path` = `knowledge/decisions/`, queries aligned to the original markdown-only test keywords. Transport: stdio `@inkeep/open-knowledge@0.29.1 mcp` (same pin as `.mcp.json`; mirrors Phase 2 proof when IDE MCP catalog is detached).

## Query results

| Query | Top hit (`knowledge/decisions/`) | Score | `status` / `last_verified` |
|-------|----------------------------------|-------|----------------------------|
| `promotion-not-sync` | `agent-stack-promotion-not-sync.md` | 1046.69 | verified / 2026-07-13 |
| `dual-track` | `agent-stack-repo-truth-dual-track.md` | 555.55 | verified / 2026-07-13 |
| `ratification` | `agent-stack-authority-ratified-2026-07-13.md` | 859.94 | verified / 2026-07-13 |

All three queries returned the expected ratified ADR as **#1** full-text hit inside `decisions/`.

## vs markdown-only test (2026-07-13)

| Dimension | Markdown-only | MCP `search` | Delta |
|-----------|---------------|--------------|-------|
| Ratification | HIGH (title match) | #1 hit | **Same** |
| Dual-track | HIGH (title match) | #1 hit | **Same** |
| Promotion-not-sync | **MEDIUM** (no dedicated ADR at pilot time) | #1 hit on dedicated ADR + `tags: promotion-not-sync` | **Improved** |
| Frontmatter cite | Manual grep | Hits include `status` / `last_verified` in snippet | **Same** |
| Discoverability | 3/4 direct grep | 3/3 keyword → correct ADR | **Improved** |

## Notes

- Promotion-not-sync grep gap from the original pilot is **closed** by [`agent-stack-promotion-not-sync.md`](../decisions/agent-stack-promotion-not-sync.md) (added after markdown-only run).
- MCP is an accelerator; markdown + `knowledge/index.md` remain authoritative fallback per Phase 2 pilot go ADR.
- Subagent session: `CallMcpTool` catalog did not list `user-open-knowledge`; stdio MCP exercised successfully. Reload Cursor if IDE-integrated tools are missing.
