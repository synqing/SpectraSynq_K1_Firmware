# Phase 2 P2-02: OpenKnowledge MCP Install Resolution

> **Supplementary / historical.** Canonical Phase 2 closeout: [`phase2-openknowledge-mcp-proof.md`](./phase2-openknowledge-mcp-proof.md). Captain go (P2-08): [`agent-stack-openknowledge-pilot-go-2026-07-13.md`](../decisions/agent-stack-openknowledge-pilot-go-2026-07-13.md). Scope cleanup: [`phase2-openknowledge-scope-audit.md`](./phase2-openknowledge-scope-audit.md).

**Status:** ✅ RESOLVED (superseded by mcp-proof for exit-gate authority)  
**Date:** 2026-07-13  
**Agent:** search-specialist (P2-02 unblock phase)

---

## Problem Statement

Prior agent attempt to install `openknowledge@0.29.1` via npm → **404 (package not found)**. Need authoritative install path and verify MCP registration.

---

## Investigation: Official Install Coordinates

### Correct Package Name

**Official:** `@inkeep/open-knowledge` (not `openknowledge`)

- npm registry: https://www.npmjs.com/package/@inkeep/open-knowledge
- Latest stable: **v0.29.1** (released 2026-07-10)
- Latest prerelease: v0.29.0-beta.1

### Install Method (All Platforms)

```bash
# Install CLI globally
npm install -g @inkeep/open-knowledge

# Initialize project (scaffolds .ok/, registers MCP with detected editors)
cd your-project
ok init

# Start editor (optional, for UI)
ok start --open
```

### MCP Registration

`ok init` automatically registers the OpenKnowledge MCP server (`open-knowledge`) with detected editors:

- **Claude Code** (user + project scope)
- **Claude Desktop** (user scope)
- **Cursor** (user + project scope)
- **Codex** (user + project scope)
- **OpenCode** (user + project scope)
- **LM Studio, Pi, Antigravity** (user scope)

### Key Implementation Detail: Resilient Launcher

The MCP registration uses a fallback launcher chain (shell script) that:

1. Checks for desktop app bundle (macOS: `~/Applications/OpenKnowledge.app`)
2. Falls back to `npx -y @inkeep/open-knowledge@latest mcp`
3. Searches common Node.js install paths (NVM, fnm, asdf, Homebrew)
4. Fails gracefully if Node.js 24+ not found

This ensures MCP survival across platform-specific deployment modes.

---

## Project Installation Summary

### Executed Commands

```bash
# Global CLI install
npm install -g @inkeep/open-knowledge
# ✅ Exit 0: added 166 packages in 9s

# Project initialization at /Users/spectrasynq/SpectraSynq_K1_Firmware
cd /Users/spectrasynq/SpectraSynq_K1_Firmware
ok init --json
# ✅ Exit 0: Project initialized
# ✅ MCP registration: 12 editors detected and configured
```

### Outputs

**Installed Version:** v0.29.1

**MCP Configuration Files Created/Modified:**

| Scope   | Editor        | Config Path                                                     | Status    |
|---------|---------------|-----------------------------------------------------------------|-----------|
| user    | Claude        | `~/.claude.json`                                                | ✅ written |
| project | Claude        | `.mcp.json`                                                     | ✅ written |
| user    | Claude Desktop| `~/Library/Application Support/Claude/claude_desktop_config.json` | ✅ written |
| user    | Cursor        | `~/.cursor/mcp.json`                                            | ✅ written |
| project | Cursor        | `.cursor/mcp.json`                                              | ✅ written |
| user    | Codex         | `~/.codex/config.toml`                                          | ✅ written |
| project | Codex         | `.codex/config.toml`                                            | ✅ written |
| user    | OpenCode      | `~/.config/opencode/opencode.json`                              | ✅ written |
| project | OpenCode      | `opencode.json`                                                 | ✅ written |

**Project Structure Created:**

```
.ok/
├── config.yml       # Project defaults (schema-aware)
└── .gitignore       # Content exclusions
```

### Verification: Project-Level MCP Registration (Cursor)

**File:** `/Users/spectrasynq/SpectraSynq_K1_Firmware/.cursor/mcp.json`

```json
{
  "mcpServers": {
    "open-knowledge": {
      "command": "/bin/sh",
      "args": [
        "-l",
        "-c",
        "# ok-mcp-v1\nUSER_BUNDLE=\"$HOME/Applications/OpenKnowledge.app/Contents/Resources/cli/bin/ok.sh\"\n[ -f \"$USER_BUNDLE\" ] && [ -x \"$USER_BUNDLE\" ] && exec \"$USER_BUNDLE\" mcp\nBUNDLE=\"/Applications/OpenKnowledge.app/Contents/Resources/cli/bin/ok.sh\"\n[ -f \"$BUNDLE\" ] && [ -x \"$BUNDLE\" ] && exec \"$BUNDLE\" mcp\ncommand -v npx >/dev/null 2>&1 && exec npx -y @inkeep/open-knowledge@latest mcp\n... [fallback chain for NVM, fnm, asdf, Homebrew paths] ..."
      ]
    },
    "codex-computer-use": { ... }
  }
}
```

**Status:** ✅ Registered with resilient fallback launcher

---

## Tool Access Verification

### MCP Server Status

Test command: `ok mcp` (spawns MCP protocol listener)

```bash
cd /Users/spectrasynq/SpectraSynq_K1_Firmware && ok mcp
# ✅ Server starts (PID: 38168)
# ✅ Listens for MCP protocol input (stdio)
# ✅ No errors in startup
```

### Expected MCP Tools (per OpenKnowledge docs/reference/mcp)

The MCP server exposes these tools to agents:

- `exec` — Execute shell commands directly from knowledge base
- `read` — Read file contents
- `write` — Write or create documents
- `edit` — Edit a document in-place
- `config` — Query project configuration
- `palette` — Access colour/theming registry
- `workflow` — Trigger editor workflows
- `preview_url` — Resolve preview URLs (auto-starts server if needed)

---

## Installation Maturity

| Criterion                          | Status | Notes                                                                         |
|:-----------------------------------|:------:|:-------|
| Package name correct               | ✅     | `@inkeep/open-knowledge` (official npm scope)                                 |
| CLI installs globally              | ✅     | `npm install -g @inkeep/open-knowledge` → v0.29.1                             |
| Project initialization works       | ✅     | `ok init` scaffolds `.ok/` and registers with 12 editors                      |
| MCP registered (project scope)     | ✅     | `.cursor/mcp.json` and `.mcp.json` created with resilient launcher            |
| MCP server starts                  | ✅     | `ok mcp` spawns listener (PID 38168, no errors)                               |
| Tools accessible in agent          | ⏳     | Requires Cursor restart to load new .cursor/mcp.json                          |
| Desktop app alternative            | ℹ️     | macOS DMG available; CLI used for Linux/Windows/Intel Mac                     |

---

## Next Steps (Manual Operator)

1. **Restart Cursor** to load the new `open-knowledge` MCP entry from `.cursor/mcp.json`
2. **Approve MCP server** when prompted (Cursor approval dialog)
3. **Test a tool call** from an agent: Ask agent to `exec` a simple command in the knowledge base
4. **Activate Phase 2 P2-02** tasks (research routing, content ingestion, consolidation workflows)

---

## Fallback Notes

- **If Node.js < 24:** Install Node 24+ from nodejs.org (required)
- **If MCP entry doesn't appear after restart:** Check console for `left unchanged` warning; fix `.cursor/mcp.json` parse errors and re-run `ok init`
- **If editor still can't see tools:** Try `ok diagnose` for support bundle; check `~/.ok/` for permission issues

---

## References

- Official docs: https://openknowledge.ai/docs
- Quick start: https://openknowledge.ai/docs/get-started/quickstart
- MCP reference: https://openknowledge.ai/docs/reference/mcp
- Cursor integration: https://openknowledge.ai/docs/integrations/cursor
- GitHub repo: https://github.com/inkeep/open-knowledge
- Latest release: v0.29.1 (2026-07-10)

---

## Summary

**OpenKnowledge MCP is now installed and registered at project scope.**

The correct package is `@inkeep/open-knowledge` (v0.29.1), not `openknowledge`. Project initialization succeeds, MCP server registers with Cursor and all other detected editors, and the resilient launcher ensures fallback to `npx -y @inkeep/open-knowledge@latest mcp` if the global CLI is unavailable.

**Action required:** Restart Cursor to load the new `.cursor/mcp.json` entry, approve the `open-knowledge` MCP server when prompted, and test a tool call to confirm agent access.

P2-02 is unblocked. Ready for Phase 2 content ingestion and research workflows.
