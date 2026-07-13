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

# Pre-session gate: run repo-truth.sh and apply its classification.
# repo-truth.sh OWNS classification (PASS/WARN/FAIL); bootstrap OWNS exit policy.
# FAIL = lane-integrity problem (missing env/guard/plan) -> exit nonzero.
# WARN = stale docs that do not misroute the lane -> continue, print warnings.
# PASS = clean -> continue.
TRUTH_OUTPUT=""
REPO_TRUTH_OVERALL="unknown"
REPO_TRUTH_WARNINGS=""
TRUTH_SCRIPT="$REPO_ROOT/scripts/agent/repo-truth.sh"
if [ -x "$TRUTH_SCRIPT" ]; then
  TRUTH_OUTPUT="$(bash "$TRUTH_SCRIPT" 2>/dev/null || true)"
  REPO_TRUTH_OVERALL="$(printf '%s\n' "$TRUTH_OUTPUT" | sed -n 's/^[[:space:]]*OVERALL[[:space:]]*:[[:space:]]*//p' | tail -1 | tr -d '[:space:]')"
  REPO_TRUTH_WARNINGS="$(printf '%s\n' "$TRUTH_OUTPUT" | sed -n 's/^WARN: //p')"
  [ -z "$REPO_TRUTH_OVERALL" ] && REPO_TRUTH_OVERALL="unknown"
else
  REPO_TRUTH_OVERALL="missing-script"
fi


# Advisory: OpenKnowledge user-global scope (only when .ok/ exists).
OK_SCOPE_STATUS="skipped"
OK_SCOPE_WARNINGS=""
OK_SCOPE_SCRIPT="$REPO_ROOT/scripts/agent/ok-scope-check.sh"
if [ -d "$REPO_ROOT/.ok" ] && [ -f "$OK_SCOPE_SCRIPT" ]; then
  OK_SCOPE_RC=0
  OK_SCOPE_OUTPUT="$(bash "$OK_SCOPE_SCRIPT" 2>&1)" || OK_SCOPE_RC=$?
  if [ "$OK_SCOPE_RC" -eq 0 ]; then
    OK_SCOPE_STATUS="PASS"
  elif [ "$OK_SCOPE_RC" -eq 1 ]; then
    OK_SCOPE_STATUS="WARN"
    OK_SCOPE_WARNINGS="$OK_SCOPE_OUTPUT"
  else
    OK_SCOPE_STATUS="ERROR"
    OK_SCOPE_WARNINGS="$OK_SCOPE_OUTPUT"
  fi
fi

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
echo "  agent-stack  : read docs/agent-stack/STANDARD-STACK.md (v1 manifest); AUTHORITY-CONTRACT.md for domains; install per knowledge/decisions/agent-stack-autonomous-execution.md"
echo "  repo-truth   : $REPO_TRUTH_OVERALL"
if [ "$REPO_TRUTH_OVERALL" = "WARN" ] && [ -n "$REPO_TRUTH_WARNINGS" ]; then
  printf '%s\n' "$REPO_TRUTH_WARNINGS" | while IFS= read -r line; do
    [ -n "$line" ] && echo "    WARN: $line"
  done
fi

echo "  ok-scope     : $OK_SCOPE_STATUS"
if [ "$OK_SCOPE_STATUS" = "WARN" ]; then
  echo "    WARN: user-global OpenKnowledge scope creep — see knowledge/runbooks/openknowledge-manual-git-policy.md (Post-init guardrails)"
  if [ -n "$OK_SCOPE_WARNINGS" ]; then
    printf '%s\n' "$OK_SCOPE_WARNINGS" | while IFS= read -r line; do
      [ -n "$line" ] && echo "    WARN: $line"
    done
  fi
elif [ "$OK_SCOPE_STATUS" = "ERROR" ] && [ -n "$OK_SCOPE_WARNINGS" ]; then
  printf '%s\n' "$OK_SCOPE_WARNINGS" | while IFS= read -r line; do
    [ -n "$line" ] && echo "    WARN: $line"
  done
fi
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
  echo "  \"spec_index_mtime\": \"$SPEC_MTIME\","
  echo "  \"ok_scope_status\": \"$OK_SCOPE_STATUS\","
  echo "  \"repo_truth_overall\": \"$REPO_TRUTH_OVERALL\""
  echo "}"
} > "$REPO_ROOT/.devin/last-bootstrap.json"

# Exit policy: FAIL is fatal. WARN and PASS continue. claude-mem unavailability
# is never fatal (it is supporting context only, never source of truth).
if [ "$REPO_TRUTH_OVERALL" = "FAIL" ]; then
  echo "FATAL: repo-truth.sh reports FAIL — lane-integrity problem detected." >&2
  echo "       Resolve before proceeding. Run: bash scripts/agent/repo-truth.sh" >&2
  exit 1
fi

exit 0
