---
title: Phase 2 — OpenKnowledge init scope audit
status: verified
last_verified: 2026-07-13
sources:
  - docs/agent-stack/AUTHORITY-CONTRACT.md
  - knowledge/research/phase2-openknowledge-install-resolution.md
  - knowledge/runbooks/openknowledge-manual-git-policy.md
owner: knowledge-curator
---

# OpenKnowledge `ok init` scope audit (2026-07-13)

## Policy anchor

**AUTHORITY-CONTRACT:** OpenKnowledge is a **project-scoped pilot** (manual git, no auto-sync). `ok init` registers MCP with **every detected editor** at user and project scope — that default **exceeds** pilot blast radius.

**Target footprint for this repo:** project MCP only (no user-global OK), plus OK project metadata (`.ok/`, `.okignore`) and in-repo `knowledge/`.

### Canonical MCP files by editor (reconciled 2026-07-13)

| Editor | Project file | `open-knowledge` | Other servers |
|--------|--------------|----------------|---------------|
| **Claude Code** | `.mcp.json` (repo root) | ✅ pinned `@0.29.1` | `codex-computer-use` (pre-existing) |
| **Cursor** | `.cursor/mcp.json` | ✅ same launcher as `.mcp.json` | **none** — do not duplicate `codex-computer-use` |

**Research (Cursor docs):** Cursor loads project MCP from **`.cursor/mcp.json`** and global from `~/.cursor/mcp.json`. It does **not** read repo-root `.mcp.json` (that path is Claude Code / shared `ok init` convention). Phase 2 closeout briefly removed `.cursor/mcp.json` assuming a shared file; that broke Cursor project scope — restored with **OK-only** entry to avoid unrelated server duplication.

---

## What `ok init` touched (inventory)

| Scope | Path | Action (2026-07-13 audit → reconciled) |
|-------|------|------------------------------------------|
| **project** | `.mcp.json` | **Kept** — `open-knowledge` MCP + existing `codex-computer-use` (Claude Code canonical) |
| **project** | `.cursor/mcp.json` | **Restored** — `open-knowledge` only (Cursor canonical; not a full duplicate of `.mcp.json`) |
| **project** | `.ok/config.yml`, `.ok/.gitignore` | **Kept** — required OK project config |
| **project** | `.okignore` | **Kept** |
| **project** | `.cursor/skills/open-knowledge/` | **Removed** — vendor skill tree duplicate |
| **project** | `.claude/skills/open-knowledge/` | **Removed** |
| **project** | `.codex/skills/open-knowledge/` | **Removed** |
| **project** | `.opencode/skills/open-knowledge/` | **Removed** |
| **project** | `.pi/skills/open-knowledge/` | **Removed** |
| **project** | `opencode.json` | **Not present** (never written or already absent) |
| **project** | `.codex/config.toml` | **Kept** — pre-existing project stub only (computer-use plugin); no OK block |
| **user** | `~/.cursor/mcp.json` | **Reverted** — removed `open-knowledge` entry |
| **user** | `~/.claude.json` (`mcpServers`) | **Reverted** — removed `open-knowledge` |
| **user** | `~/Library/Application Support/Claude/claude_desktop_config.json` | **Reverted** — removed `open-knowledge` |
| **user** | `~/.codex/config.toml` | **Reverted** — removed `[mcp_servers.open-knowledge]` block |
| **user** | `~/.config/opencode/opencode.json` | **Reverted** — removed `mcp.open-knowledge` |

**Not modified by this audit:** Cursor project cache under `~/.cursor/projects/.../mcps/user-open-knowledge/` (IDE metadata; harmless). Other repos (e.g. SpectraSynq-EDA) may still show OK MCP cache if opened in Cursor.

---

## Install coordinates (authoritative)

| Wrong | Correct |
|-------|---------|
| `openknowledge` (npm 404) | **`@inkeep/open-knowledge`** |
| `npm i openknowledge@0.29.1` | `npm install -g @inkeep/open-knowledge` then `ok init` |

Pinned MCP launcher in project configs uses `@inkeep/open-knowledge@0.29.1` (matches AUTHORITY-CONTRACT pilot version).

---

## Verification commands

```bash
# Claude Code project MCP (OK + codex-computer-use):
rg 'open-knowledge' .mcp.json

# Cursor project MCP (OK only):
test -f .cursor/mcp.json && rg -c '"open-knowledge"' .cursor/mcp.json
! rg -q 'codex-computer-use' .cursor/mcp.json && echo "PASS: Cursor MCP is OK-only"

# User-global must stay clean:
bash scripts/agent/ok-scope-check.sh
```

---

## Re-enable user-global OK (explicit opt-in only)

Do **not** re-run bare `ok init` from home or another repo without `--help` scope flags. If Captain wants OK on all Cursor workspaces, add `open-knowledge` back to `~/.cursor/mcp.json` manually and document the decision in `knowledge/decisions/`.

---

## Related

- **Canonical proof:** [`phase2-openknowledge-mcp-proof.md`](./phase2-openknowledge-mcp-proof.md)
- Install investigation (historical): [`phase2-openknowledge-install-resolution.md`](./phase2-openknowledge-install-resolution.md)
- Git policy: [`../runbooks/openknowledge-manual-git-policy.md`](../runbooks/openknowledge-manual-git-policy.md)
- Captain go (P2-08): [`../decisions/agent-stack-openknowledge-pilot-go-2026-07-13.md`](../decisions/agent-stack-openknowledge-pilot-go-2026-07-13.md)
