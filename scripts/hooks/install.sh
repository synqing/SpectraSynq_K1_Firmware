#!/usr/bin/env bash
# Install the tracked git hooks for this clone (one-time, per clone).
# core.hooksPath is a LOCAL config value and is not committed, so every fresh
# clone runs this once. Idempotent.
set -euo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

chmod +x scripts/hooks/pre-commit scripts/hooks/wip-checkpoint.sh 2>/dev/null || true
git config core.hooksPath scripts/hooks

echo "commit-gate installed:"
echo "  core.hooksPath = $(git config --get core.hooksPath)"
echo "  hook           = scripts/hooks/pre-commit"
echo
echo "Test it:   touch _gate_probe.md && git add _gate_probe.md && git commit -m probe"
echo "Uninstall: git config --unset core.hooksPath"
