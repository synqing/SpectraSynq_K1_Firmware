---
title: Phase 2 — OpenKnowledge MCP install and verification proof
status: verified
last_verified: 2026-07-13
sources:
  - docs/agent-stack/ACTIONABLE-TASKS.md P2-02
  - knowledge/decisions/agent-stack-autonomous-execution.md
  - npm @inkeep/open-knowledge@0.29.1
owner: implementer
---

# Phase 2 — OpenKnowledge MCP proof (2026-07-13)

## Executive status

| Item | Status |
|------|--------|
| **Install** | **PASS** — `@inkeep/open-knowledge@0.29.1` via `npx` (no Desktop bundle on host) |
| **Project scope** | **PASS** — `.ok/config.yml` → `content.dir: knowledge` |
| **`.mcp.json` registration** | **PASS** — `open-knowledge` stdio server; pin `@0.29.1` (Claude Code project MCP) |
| **`.cursor/mcp.json` registration** | **PASS** — `open-knowledge` only (Cursor project MCP; reconciled post–Phase 2 close) |
| **GitHub auto-sync** | **Not enabled** — manual git policy; no OK sync jobs configured |
| **MCP vs `knowledge/`** | **PASS** — live `search` hit on `agent-stack-promotion-not-sync`; `config` confirms `content.dir: knowledge` |

**Executor:** autonomous Phase 2 subagent (`agent:cursor`), workspace `/Users/spectrasynq/SpectraSynq_K1_Firmware`.

## Install coordinates (resolved)

Authority pin **v0.29.1** maps to npm package **`@inkeep/open-knowledge@0.29.1`** (not bare `openknowledge@0.29.1`, which 404s).

| Step | Command | Result |
|------|---------|--------|
| Version pin | `npm view @inkeep/open-knowledge@0.29.1 version` | `0.29.1` |
| CLI help | `npx -y @inkeep/open-knowledge@0.29.1 --help` | OK |
| Project scaffold | `.ok/` present; `content.dir: knowledge` set in `.ok/config.yml` | OK |
| Desktop bundle | `~/Applications` / `/Applications` `ok.sh` | **absent** (npx fallback used) |

### MCP config inspection (2026-07-13 autonomous follow-up)

| File | `open-knowledge` entry | Pin | Notes |
|------|------------------------|-----|-------|
| `.mcp.json` | **PASS** | `@inkeep/open-knowledge@0.29.1` | Claude Code; also `codex-computer-use` |
| `.cursor/mcp.json` | **PASS** | same launcher | Cursor-only path; **OK entry only** |
| `~/.cursor/mcp.json` | **PASS** (absent) | — | User-global OK reverted per scope audit |

### Policy compliance

- **Project MCP only** (no user-global OK) — **`.mcp.json`** for Claude Code; **`.cursor/mcp.json`** for Cursor (`open-knowledge` only). Collateral `init` writes to `opencode.json`, `.pi/` **removed**; `.codex/config.toml` OK block **reverted**; user-global configs **reverted**.
- **Editor split:** Cursor does not read repo-root `.mcp.json` ([Cursor MCP docs](https://cursor.com/docs/mcp) → `.cursor/mcp.json`). Keeping both files is intentional, not duplication of unrelated servers.
- **No** GitHub auto-sync enabled (`autoSync.enabled: null` in merged config).
- **No** global operator MCP edits required for this proof.

## MCP verification

| Check | Status | Evidence |
|-------|--------|----------|
| Server registered in Cursor | **PASS** | `user-open-knowledge` MCP catalog `serverStatus: ready` |
| `tools/list` | **PASS** | `search`, `exec`, `config`, `workflow`, `write`, `edit`, … |
| Project-scoped `search` | **PASS** | Query `agent-stack-promotion-not-sync` → 1 hit (`decisions/agent-stack-promotion-not-sync`) |
| Project-scoped `config` | **PASS** | `content.dir: knowledge`; `autoSync.enabled: null` |
| Read decision via `exec` | **PARTIAL** | `&&` rejected by OK exec (use single command or pipe); `head` path works when server attached |
| Server session stability | **NOTE** | MCP may drop mid-session; **IDE reload** if tools missing — Cursor reads `.cursor/mcp.json` |

### Live MCP query log (2026-07-13 autonomous follow-up)

```text
# 1) Config inspection
rg 'open-knowledge' .mcp.json
→ open-knowledge launcher, pin @inkeep/open-knowledge@0.29.1
test -f .cursor/mcp.json && rg open-knowledge .cursor/mcp.json → PASS (Cursor project MCP)

# 2) npm pin
npm view @inkeep/open-knowledge@0.29.1 version
→ 0.29.1

# 3) MCP tools/call → search
server: user-open-knowledge
query: agent-stack-promotion-not-sync
cwd: /Users/spectrasynq/SpectraSynq_K1_Firmware
→ PASS — 1 hit: "Agent stack — promotion-not-sync policy" (decisions/agent-stack-promotion-not-sync)

# 4) MCP tools/call → config
→ PASS — content.dir: knowledge; semantic search disabled; autoSync not enabled

# 5) MCP tools/call → exec (read target ADR)
command: head -25 knowledge/decisions/agent-stack-promotion-not-sync.md
→ INTERMITTENT — first attempt: OK exec rejects `&&` chains; retry may fail if MCP stdio detached
→ Markdown on disk confirms status: verified, last_verified: 2026-07-13 (repo truth)
```

Transport: Cursor loads `open-knowledge` from `.cursor/mcp.json`; Claude Code from `.mcp.json` — both via npx `@inkeep/open-knowledge@0.29.1 mcp`.

### Markdown fallback (still valid)

```text
$ rg -l "status: verified" knowledge/decisions/*.md
→ 5 verified decision files (incl. promotion-not-sync ADR)
```

## `.mcp.json` snapshot

- Preserves existing `codex-computer-use` server.
- Adds/updates `open-knowledge` launcher with **`@inkeep/open-knowledge@0.29.1`** (both npx code paths).

## Decision migration (P2-04)

| Path | `status: verified` |
|------|-------------------|
| `knowledge/decisions/agent-stack-authority-ratified-2026-07-13.md` | yes |
| `knowledge/decisions/agent-stack-openknowledge-maturity.md` | yes |
| `knowledge/decisions/agent-stack-autonomous-execution.md` | yes |
| `knowledge/decisions/agent-stack-repo-truth-dual-track.md` | yes |
| `knowledge/decisions/agent-stack-promotion-not-sync.md` | yes |

## Related runbooks

- [`knowledge/runbooks/openknowledge-manual-git-policy.md`](../runbooks/openknowledge-manual-git-policy.md) (P2-05)
- [`knowledge/runbooks/claude-mem-compact-injection.md`](../runbooks/claude-mem-compact-injection.md) (P2-06)

## Notes

- `ok init --content-dir knowledge` reported `contentDirApplied: false` (existing layout); **`content.dir: knowledge` applied manually** in `.ok/config.yml`.
- **P2-08 DONE** — Captain ratified go 2026-07-13 — [`agent-stack-openknowledge-pilot-go-2026-07-13.md`](../decisions/agent-stack-openknowledge-pilot-go-2026-07-13.md).
- **IDE reload:** If `open-knowledge` tools are not in the MCP catalog after install, reload Cursor window once to load `.cursor/mcp.json`.
- Phase 2 exit gate **PASS** — all criteria met including MCP search + Captain go/no-go.
- Supplementary: [`phase2-openknowledge-scope-audit.md`](./phase2-openknowledge-scope-audit.md), [`phase2-openknowledge-install-resolution.md`](./phase2-openknowledge-install-resolution.md).
