---
title: Agent stack — autonomous operator tooling execution
status: verified
last_verified: 2026-07-13
sources:
  - docs/agent-stack/PHASED-ROLLOUT.md
  - docs/agent-stack/AUTHORITY-CONTRACT.md
  - AGENT_OS.md
  - phase1-p1-08-codex-adversarial-result.md
owner: knowledge-curator
---

# Decision: agents execute Phase 1–2 operator tooling installs (+ Phase 5 Headroom compression benchmark)

## Context

Phase 1 tasks previously implied Captain/manual install gates (`brew install`, plugin UI). That contradicts the agent-stack goal of **fully autonomous** rollout for approved operator tooling. P1-08-08 flagged the allowlist as too broad.

## Decision

1. **Agents MAY install and verify** only tools on the **enumerated allowlist** below for Phases 1–2 (and Phase 5 Headroom compression-only row), when the matching `ACTIONABLE-TASKS` ID is active.
2. **Captain blockers only** for: missing credentials, license acceptance requiring human click-through, sudo/password prompts, hardware flash/upload, or tools explicitly rejected in the authority contract.
3. **Agents MUST document evidence** under `knowledge/research/phase1-*-proof.md` (or phase-appropriate paths) and update `docs/agent-stack/ACTIONABLE-TASKS.md`.
4. **Agents MUST NOT** enable Codex auto stop-gate (`ReviewGate`), auto-sync Claude-mem → OpenKnowledge, Ruflo full init, OmniRoute primary, pxpipe, or firmware upload.

## Enumerated allowlist (exclusive)

| Tool | Version / pin | Phase | Method | Task ID | Evidence |
|------|---------------|-------|--------|---------|----------|
| **sqlite-utils** | brew latest or pip pin in proof | 1 | `brew install sqlite-utils` | P1-06 | [`phase1-sqlite-utils-proof.md`](../research/phase1-sqlite-utils-proof.md) |
| **Herdr** | brew latest | 1 | `brew install herdr` | P1-01 | [`phase1-herdr-proof.md`](../research/phase1-herdr-proof.md) |
| **Codex plugin** | `codex@openai-codex` (marketplace) | 1 | `claude plugin marketplace add` + `install codex@openai-codex` | P1-03 | [`phase1-codex-plugin-audit.md`](../research/phase1-codex-plugin-audit.md) |
| **OpenKnowledge MCP** | **v0.29.1** project-scoped | 2 | Per Phase 2 runbook (not Phase 1) | P2-02 | [`phase2-openknowledge-mcp-proof.md`](../research/phase2-openknowledge-mcp-proof.md) (install **PASS**; `.mcp.json` + `.cursor/mcp.json` OK-only) |
| **Headroom** | compression-only proxy/library | 5 | npm/brew per P5-01 protocol; **no** memory/learn/instruction-write paths | P5-01..03 | [`phase5-headroom-benchmark-plan.md`](../research/phase5-headroom-benchmark-plan.md); results [`headroom-ab.md`](../research/headroom-ab.md) |

**Not on list = forbidden** until a future phase task explicitly adds the tool.

### Allowlist footnotes

- **OpenKnowledge (`@inkeep/open-knowledge`):** after `ok init`, run the [scope audit checklist](../research/phase2-openknowledge-scope-audit.md) and `bash scripts/agent/ok-scope-check.sh` (user-global MCP). **Keep both** project files — `.mcp.json` (Claude) and `.cursor/mcp.json` (Cursor, OK-only); when Cursor is in use, verify `.cursor/mcp.json` exists before marking install DONE or closing P2-02 evidence.
- **Headroom (Phase 5):** **compression-only** A/B is pre-approved per `AUTHORITY-CONTRACT.md` § Benchmark later. No Captain spend gate. Forbidden: memory, learn, instruction writes, output shaping, effort reduction, provider routing. Quality review (P5-04) is reviewer-agent delegated, not Captain-gated for this scope.

## AGENT_OS alignment

Narrow exception to “Install new MCPs, plugins, packages, or global tools”: **allowed only** for rows in the table above + active task ID. See `AGENT_OS.md` §7 install allowlist.

## Rollback

Uninstall tools per runbooks; set proof docs `status: rolled_back` in frontmatter; disable Codex plugin — no firmware dependency. See `knowledge/runbooks/codex-plugin-manual-only.md`, `herdr-workspace-setup.md`.
