---
title: OpenKnowledge pilot — manual git policy
status: verified
last_verified: 2026-07-13
sources:
  - docs/agent-stack/AUTHORITY-CONTRACT.md
  - knowledge/decisions/agent-stack-openknowledge-maturity.md
  - knowledge/research/phase2-openknowledge-scope-audit.md
owner: knowledge-curator
---

# OpenKnowledge pilot — manual git commits (no auto GitHub sync)

## Package and CLI (install)

| Item | Value |
|------|--------|
| **npm package** | `@inkeep/open-knowledge` (not `openknowledge`) |
| **Pilot pin** | v0.29.1 (see AUTHORITY-CONTRACT) |
| **Global CLI** | `npm install -g @inkeep/open-knowledge` |
| **Project init** | `cd <repo> && ok init` — **registers all detected editors**; constrain scope per [`phase2-openknowledge-scope-audit.md`](../research/phase2-openknowledge-scope-audit.md) |

MCP launcher fallback: `npx -y @inkeep/open-knowledge@0.29.1 mcp`. Project files: **`.mcp.json`** (Claude Code) and **`.cursor/mcp.json`** (Cursor, OK-only).

## Binding policy (Phase 2)

1. **All `knowledge/` changes** enter git via normal `git add` / `git commit` after human or agent review with frontmatter checks.
2. **No bot auto-push** — no GitHub Actions, hooks, or OpenKnowledge sync jobs that push to remote without explicit Captain approval.
3. **No auto-pull** of knowledge from remote into working tree during agent sessions.
4. **No Claude-mem → OpenKnowledge auto-sync** — promotion workflow only ([`SWARM-ORCHESTRATION.md`](../../docs/agent-stack/SWARM-ORCHESTRATION.md) § Promotion).
5. **MCP optional** — if OpenKnowledge MCP is unavailable, agents read `knowledge/` as plain Markdown in-repo.
6. **Project-scoped MCP only** for this pilot — keep **`.mcp.json`** (Claude Code) and **`.cursor/mcp.json`** (Cursor, `open-knowledge` only) in-repo; no user-global editor configs unless explicitly ratified.

## Commit checklist

- Frontmatter includes `status`, `last_verified`, `sources`
- `status: verified` only after cross-check with code/tests or ratified decision
- Link evidence in `knowledge/research/` when install or gate proof is involved

## Rollback

1. Remove `open-knowledge` from project `.mcp.json` and `.cursor/mcp.json`.
2. Revert any user-global MCP entries (see scope audit).
3. Retain Markdown history in git; optional: remove `.ok/` if decommissioning OK tooling.

## Post-init guardrails

Run **after every** `ok init` or OpenKnowledge upgrade in this repo — `ok init` re-registers MCP and skills across detected editors; bare re-init is the main scope-creep vector.

1. **Verify user-global configs are clean** — no `open-knowledge` in `~/.cursor/mcp.json`, `~/.claude.json` (`mcpServers`), `~/.codex/config.toml`, `~/.config/opencode/opencode.json`, or Claude Desktop config. Use the verification block in [`phase2-openknowledge-scope-audit.md`](../research/phase2-openknowledge-scope-audit.md) or `bash scripts/agent/ok-scope-check.sh`.
   `bash scripts/agent/session-bootstrap.sh` also runs this check when `.ok/` exists (advisory WARN only; does not change bootstrap exit code).
2. **KEEP both project MCP files; forbid user-global only** — `.mcp.json` (Claude Code) and `.cursor/mcp.json` (Cursor, `open-knowledge` only) must remain in-repo. Cursor does not read repo-root `.mcp.json`; removing `.cursor/mcp.json` breaks Cursor project scope. When Cursor is in use, verify `test -f .cursor/mcp.json` after every `ok init`. Also keep `.ok/` (plus `.okignore` and in-repo `knowledge/`). Do not commit user-global MCP changes.
3. **Remove duplicate vendor skill trees** — delete project copies under `.cursor/skills/open-knowledge/`, `.claude/skills/open-knowledge/`, `.codex/skills/open-knowledge/`, `.opencode/skills/open-knowledge/`, `.pi/skills/open-knowledge/` if `ok init` recreated them; rely on repo-local agent skills policy instead.
4. **Complete the scope audit checklist** in [`phase2-openknowledge-scope-audit.md`](../research/phase2-openknowledge-scope-audit.md) before marking install DONE or updating `ACTIONABLE-TASKS.md`.

