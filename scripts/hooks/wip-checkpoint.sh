#!/usr/bin/env bash
# wip-checkpoint — durably save in-progress (possibly broken) work WITHOUT
# polluting a clean branch. Crash-safety, not a milestone.
#
# Only operates on wip/* branches (the gate auto-skips build/test there). If you
# are on a feature branch with broken work, it offers to move you to wip/<branch>.
set -euo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel)"; cd "$REPO_ROOT"
B="$(git rev-parse --abbrev-ref HEAD)"

case "$B" in
  wip/*) ;;
  *)
    WIP="wip/$B"
    echo "You are on '$B' (a gated branch). Broken checkpoints belong on '$WIP'."
    read -r -p "Switch to '$WIP' and checkpoint there? [y/N] " ans
    [ "${ans:-N}" = "y" ] || { echo "aborted."; exit 1; }
    git switch -c "$WIP" 2>/dev/null || git switch "$WIP"
    B="$WIP" ;;
esac

git add -A
if git diff --cached --quiet; then echo "nothing to checkpoint."; exit 0; fi
git commit --no-verify -m "wip: checkpoint $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "checkpointed on '$B'. Back up off this machine:  git push -u origin $B"
