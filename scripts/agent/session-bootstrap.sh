#!/usr/bin/env bash
# Session bootstrap for SpectraSynq K1 Firmware agents.
# Safe, read-only, deterministic, dependency-light.
# Prints a human-readable summary and writes .devin/last-bootstrap.json.

set -uo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "")"
if [ -z "$REPO_ROOT" ]; then
  echo "ERROR: not inside a git repository"
  exit 1
fi

cd "$REPO_ROOT" || exit 1

NOW_EPOCH="$(date +%s)"
BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")"
HEAD="$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")"
HEAD_DATE="$(git log -1 --format=%cd --date=iso 2>/dev/null || echo "unknown")"
DIRTY="$(git status --porcelain 2>/dev/null)"

HOOKS_PATH="$(git config core.hooksPath 2>/dev/null || echo "")"
HOOK_INSTALLED="false"
if [ -n "$HOOKS_PATH" ] && [ -x "$REPO_ROOT/$HOOKS_PATH/pre-commit" ]; then
  HOOK_INSTALLED="true"
fi

# Detect K1 / IM73D relevant PlatformIO envs cheaply.
K1_ENVS="unknown"
IM73D_ENV="unknown"
if [ -f "$REPO_ROOT/platformio.ini" ]; then
  K1_ENVS="$(grep -E '^\[env:k1_' platformio.ini | sed 's/\[env://;s/\]//' | tr '\n' ',' | sed 's/,$//')"
  if grep -q '^\[env:k1_bench_im73d\]' platformio.ini; then
    IM73D_ENV="present"
  else
    IM73D_ENV="missing"
  fi
fi

# Check claude-mem worker reachability (best-effort, non-fatal).
# Use bash /dev/tcp to avoid an external curl dependency.
MEM_STATUS="unreachable"
if exec 3<>/dev/tcp/127.0.0.1/37777 2>/dev/null; then
  MEM_STATUS="reachable"
  exec 3<&- 3>&- 2>/dev/null || true
fi

# Doc mtimes for stale detection (repo-truth.sh does the classification).
file_mtime() {
  local f="$1"
  if [ -z "$f" ] || [ ! -f "$f" ]; then
    echo "unknown"
    return
  fi
  if [ "$(uname -s)" = "Darwin" ]; then
    stat -f %Sm -t "%Y-%m-%d %H:%M:%S" "$f" 2>/dev/null || echo "unknown"
  else
    stat -c "%y" "$f" 2>/dev/null || echo "unknown"
  fi
}
HANDOFF_MTIME="$(file_mtime "$REPO_ROOT/.claude/handoff.md")"
PROGRESS_MTIME="$(file_mtime "$REPO_ROOT/progress.md")"
SPEC_MTIME="$(file_mtime "$REPO_ROOT/docs/spec-index.md")"

# Human-readable summary.
echo ""
echo "══════════════════════════════════════════════════════════════════"
echo "  K1 Firmware Agent Session Bootstrap"
echo "══════════════════════════════════════════════════════════════════"
echo "  repo root    : $REPO_ROOT"
echo "  branch       : $BRANCH"
echo "  HEAD         : $HEAD"
echo "  HEAD date    : $HEAD_DATE"
echo "  dirty        : $([ -n "$DIRTY" ] && echo "yes" || echo "no")"
echo "  untracked    : $([ -n "$(git ls-files --others --exclude-standard 2>/dev/null)" ] && echo "yes" || echo "no")"
echo "  git hooks    : $([ "$HOOK_INSTALLED" = "true" ] && echo "installed ($HOOKS_PATH)" || echo "NOT installed")"
echo "  K1 envs      : $K1_ENVS"
echo "  IM73D env    : $IM73D_ENV"
echo "  claude-mem   : $MEM_STATUS"
echo "  handoff.md   : $HANDOFF_MTIME"
echo "  progress.md  : $PROGRESS_MTIME"
echo "  spec-index   : $SPEC_MTIME"
echo "══════════════════════════════════════════════════════════════════"
echo ""

# Write JSON snapshot.
mkdir -p "$REPO_ROOT/.devin"
{
  echo "{"
  echo "  \"timestamp_epoch\": $NOW_EPOCH,"
  echo "  \"repo_root\": \"$REPO_ROOT\","
  echo "  \"branch\": \"$BRANCH\","
  echo "  \"head\": \"$HEAD\","
  echo "  \"head_date\": \"$HEAD_DATE\","
  echo "  \"dirty\": $([ -n "$DIRTY" ] && echo "true" || echo "false"),"
  echo "  \"untracked\": $([ -n "$(git ls-files --others --exclude-standard 2>/dev/null)" ] && echo "true" || echo "false"),"
  echo "  \"hooks_path\": \"${HOOKS_PATH}\","
  echo "  \"hooks_installed\": $HOOK_INSTALLED,"
  echo "  \"k1_envs\": \"$K1_ENVS\","
  echo "  \"im73d_env\": \"$IM73D_ENV\","
  echo "  \"claude_mem_status\": \"$MEM_STATUS\","
  echo "  \"handoff_mtime\": \"$HANDOFF_MTIME\","
  echo "  \"progress_mtime\": \"$PROGRESS_MTIME\","
  echo "  \"spec_index_mtime\": \"$SPEC_MTIME\""
  echo "}"
} > "$REPO_ROOT/.devin/last-bootstrap.json"

exit 0
