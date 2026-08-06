#!/usr/bin/env bash
# SpectraSynq global git doctrine installer — run ONCE per dev machine,
# in a real terminal (not an agent sandbox; sandboxes have their own $HOME).
# Doctrine: docs/process/SPECTRASYNQ-GIT-DOCTRINE.md. Do not extend.
set -euo pipefail

SRC_DIR="$(cd "$(dirname "$0")" && pwd)"
HOOK_SRC="$SRC_DIR/../.githooks/commit-msg"
HOOKS_DIR="$HOME/.config/git/hooks"

[ -f "$HOOK_SRC" ] || { echo "cannot find $HOOK_SRC — run from a repo carrying the doctrine files" >&2; exit 1; }

mkdir -p "$HOOKS_DIR"
cp "$HOOK_SRC" "$HOOKS_DIR/commit-msg"
chmod +x "$HOOKS_DIR/commit-msg"
git config --global core.hooksPath "$HOOKS_DIR"

echo "✔ Global commit-msg hook active for ALL repos on this machine (present and future)."
echo "  hooksPath = $HOOKS_DIR"
echo "  Note: a repo with its own LOCAL core.hooksPath (e.g. husky) overrides this — correct, leave it."
echo ""
echo "Remaining manual step (once): paste the session-protocol stanza from"
echo "docs/process/SPECTRASYNQ-GIT-DOCTRINE.md into ~/.claude/CLAUDE.md so every"
echo "agent session on this machine inherits it."
