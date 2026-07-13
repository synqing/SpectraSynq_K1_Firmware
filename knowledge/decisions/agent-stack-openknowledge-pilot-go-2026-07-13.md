---
title: Agent stack — OpenKnowledge pilot go (Phase 2 exit)
status: verified
last_verified: 2026-07-13
sources:
  - docs/agent-stack/ACTIONABLE-TASKS.md P2-08
  - docs/agent-stack/PHASED-ROLLOUT.md § Phase 2 exit gate
  - knowledge/research/phase2-openknowledge-mcp-proof.md
  - Captain ratification 2026-07-13 (P2-08 autonomous go)
owner: knowledge-curator
---

# Decision: OpenKnowledge pilot go (P2-08)

## Context

Phase 2 scoped a **project-only** OpenKnowledge pilot for `SpectraSynq_K1_Firmware`:
`knowledge/` scaffold, manual-git policy, Claude-mem budget runbook, and MCP v0.29.1 at project scope.
P2-02 MCP install and verification completed 2026-07-13 (`@inkeep/open-knowledge@0.29.1`).
P2-08 required Captain go/no-go before Phase 3 exit criteria treat Phase 2 as closed.

## Decision

1. **Pilot go** — Captain ratified **continue** on 2026-07-13. Phase 2 exit gate = **PASS**.
2. **Binding config**
   - MCP registration (editor split): **`.mcp.json`** (Claude Code) **and `.cursor/mcp.json`** (Cursor, `open-knowledge` only). Cursor does not read repo-root `.mcp.json`; keeping both project files is intentional, not duplicate unrelated servers. **No user-global** editor MCP configs for this pilot.
   - Content root: `.ok/config.yml` → `content.dir: knowledge`.
   - Version pin: `@inkeep/open-knowledge@0.29.1`.
   - No GitHub auto-sync; promotion-not-sync policy unchanged.
3. **Markdown remains authoritative** when MCP is unavailable; MCP is an accelerator, not a truth override.
4. **Rollback trigger** — disable `open-knowledge` in project `.mcp.json` and `.cursor/mcp.json`; retain `knowledge/` as plain git Markdown.

## Evidence

| Criterion | Proof |
|-----------|-------|
| `knowledge/` navigable | P2-03 — [`knowledge/index.md`](../index.md) |
| MCP project-scoped | P2-02 — [`phase2-openknowledge-mcp-proof.md`](../research/phase2-openknowledge-mcp-proof.md) |
| 3+ decision docs | P2-04 — 4 files `status: verified` under `knowledge/decisions/` |
| Captain go/no-go | This decision (2026-07-13) |

## Related

- Canonical Phase 2 summary: [`phase2-openknowledge-mcp-proof.md`](../research/phase2-openknowledge-mcp-proof.md)
- Scope cleanup: [`phase2-openknowledge-scope-audit.md`](../research/phase2-openknowledge-scope-audit.md)
- Install investigation (historical): [`phase2-openknowledge-install-resolution.md`](../research/phase2-openknowledge-install-resolution.md)
