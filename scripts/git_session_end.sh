#!/usr/bin/env bash
# SpectraSynq session-end: record everything, label honestly, push the lane.
# Usage: scripts/git_session_end.sh "<message>" [none|host|device:<chip>@<receipt>]
# Doctrine: docs/process/SPECTRASYNQ-GIT-DOCTRINE.md. Do not extend.
set -euo pipefail

msg="${1:?usage: git_session_end.sh \"<message>\" [none|host|device:<chip>@<receipt>]}"
verify="${2:-none}"

branch="$(git rev-parse --abbrev-ref HEAD)"
if [ "$branch" = "main" ] || [ "$branch" = "master" ]; then
  echo "refuse: session work belongs on a lane branch, not '$branch'." >&2
  exit 1
fi

git add -A
if git diff --cached --quiet; then
  echo "tree already clean — nothing to record."
else
  git commit -m "$msg" -m "Verify: $verify"
fi

if git remote get-url origin >/dev/null 2>&1; then
  git push -u origin "$branch" \
    || echo "warn: push failed — commit is recorded locally; push when remote/network is available." >&2
else
  echo "warn: no 'origin' remote — commit recorded locally only (doctrine rule 6 owed)." >&2
fi
