#!/usr/bin/env bash
# Docs-lane helper: fail if open-knowledge appears in user-global editor MCP configs.
# After ok init, also verify project .cursor/mcp.json exists when Cursor is in use (see openknowledge-manual-git-policy.md Post-init guardrails).
# Not part of pre-commit or session-bootstrap. See knowledge/research/phase2-openknowledge-scope-audit.md

set -euo pipefail

HOME="${HOME:-}"
if [ -z "$HOME" ]; then
  echo "ERROR: HOME is unset"
  exit 2
fi

CLAUDE_DESKTOP="${HOME}/Library/Application Support/Claude/claude_desktop_config.json"

PATHS=(
  "${HOME}/.cursor/mcp.json"
  "${HOME}/.claude.json"
  "${HOME}/.codex/config.toml"
  "${HOME}/.config/opencode/opencode.json"
  "${CLAUDE_DESKTOP}"
)

FOUND=0
for f in "${PATHS[@]}"; do
  if [ -f "$f" ] && grep -q 'open-knowledge' "$f" 2>/dev/null; then
    echo "FAIL: open-knowledge in user-global config: $f"
    FOUND=1
  fi
done

if [ "$FOUND" -ne 0 ]; then
  echo "Remove entries per knowledge/runbooks/openknowledge-manual-git-policy.md (Post-init guardrails)."
  exit 1
fi

echo "PASS: no open-knowledge in user-global MCP configs"
exit 0
