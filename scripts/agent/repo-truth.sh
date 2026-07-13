#!/usr/bin/env bash
# Repo truth / source-of-truth harness for SpectraSynq K1 Firmware.
# Safe and read-only. Prints a report and writes .devin/repo-truth-report.json.

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
DIRTY_FILES="$(git diff --name-only 2>/dev/null)"
UNTRACKED_FILES="$(git ls-files --others --exclude-standard 2>/dev/null)"

OVERALL="PASS"
REASONS=""

warn() {
  # WARN must never downgrade an existing FAIL (FAIL is the higher severity).
  if [ "$OVERALL" = "PASS" ]; then OVERALL="WARN"; fi
  REASONS="${REASONS}WARN: $1\n"
}

fail() {
  OVERALL="FAIL"
  REASONS="${REASONS}FAIL: $1\n"
}

# --- IM73D lane checks ---
IM73D_ENV="FAIL"
if [ -f "$REPO_ROOT/platformio.ini" ] && grep -q '^\[env:k1_bench_im73d\]' "$REPO_ROOT/platformio.ini"; then
  IM73D_ENV="PASS"
else
  fail "platformio.ini is missing [env:k1_bench_im73d]"
fi

IM73D_GUARD="FAIL"
MANIFEST="$REPO_ROOT/scripts/platformio/k1_device_identities.json"
GUARD_PY="$REPO_ROOT/scripts/platformio/k1_upload_guard.py"
if [ -f "$GUARD_PY" ] && [ -f "$MANIFEST" ] && grep -q 'k1_device_identities\.json' "$GUARD_PY"; then
  if python3 - "$MANIFEST" <<'PYEOF' >/dev/null 2>&1
import json
import sys
from pathlib import Path

manifest = Path(sys.argv[1])
data = json.loads(manifest.read_text(encoding="utf-8"))
envs = {env for row in data.get("authorized", []) for env in row.get("envs", [])}
sys.exit(0 if "k1_bench_im73d" in envs else 1)
PYEOF
  then
    IM73D_GUARD="PASS"
  else
    fail "k1_device_identities.json does not authorize k1_bench_im73d"
  fi
else
  fail "upload guard must load k1_device_identities.json (manifest missing or guard not wired)"
fi

IM73D_PLAN="FAIL"
if [ -f "$REPO_ROOT/docs/hardware/im73d122-ap-vp-migration-plan.md" ]; then
  IM73D_PLAN="PASS"
else
  fail "docs/hardware/im73d122-ap-vp-migration-plan.md is missing"
fi

# --- Stale doc checks ---
HANDOFF_STATUS="PASS"
if [ -f "$REPO_ROOT/.claude/handoff.md" ]; then
  if ! grep -qi 'im73d\|IM73D\|PDM' "$REPO_ROOT/.claude/handoff.md"; then
    HANDOFF_STATUS="WARN"
    warn ".claude/handoff.md does not mention IM73D/PDM lane"
  fi
fi

PROGRESS_STATUS="PASS"
if [ -f "$REPO_ROOT/progress.md" ]; then
  if ! grep -qi 'im73d\|IM73D\|PDM' "$REPO_ROOT/progress.md"; then
    PROGRESS_STATUS="WARN"
    warn "progress.md does not mention IM73D/PDM lane"
  fi
fi

SPEC_STATUS="PASS"
if [ -f "$REPO_ROOT/docs/spec-index.md" ]; then
  if ! grep -qi 'im73d\|IM73D\|PDM' "$REPO_ROOT/docs/spec-index.md"; then
    SPEC_STATUS="WARN"
    warn "docs/spec-index.md does not mention IM73D/PDM lane"
  fi
fi

# --- Dirty registry ---
REGISTRY_DIRTY="false"
if echo "$DIRTY_FILES" | grep -q '^docs/hardware/device-build-registry.md$'; then
  REGISTRY_DIRTY="true"
  warn "docs/hardware/device-build-registry.md has uncommitted changes (do not auto-commit)"
fi

# --- Dirty / untracked summary ---
DIRTY_FLAG="false"
if [ -n "$DIRTY_FILES" ]; then
  DIRTY_FLAG="true"
fi
UNTRACKED_FLAG="false"
if [ -n "$UNTRACKED_FILES" ]; then
  UNTRACKED_FLAG="true"
fi

# --- Human-readable report ---
echo ""
echo "══════════════════════════════════════════════════════════════════"
echo "  K1 Repo Truth Report"
echo "══════════════════════════════════════════════════════════════════"
echo "  branch           : $BRANCH"
echo "  HEAD             : $HEAD"
echo "  HEAD date        : $HEAD_DATE"
echo "  dirty files      : $([ "$DIRTY_FLAG" = "true" ] && echo "yes" || echo "no")"
echo "  untracked files  : $([ "$UNTRACKED_FLAG" = "true" ] && echo "yes" || echo "no")"
echo ""
echo "  IM73D env        : $IM73D_ENV"
echo "  IM73D guard      : $IM73D_GUARD"
echo "  IM73D plan       : $IM73D_PLAN"
echo ""
echo "  handoff.md       : $HANDOFF_STATUS"
echo "  progress.md      : $PROGRESS_STATUS"
echo "  spec-index.md    : $SPEC_STATUS"
echo "  registry dirty   : $REGISTRY_DIRTY"
echo ""
echo "  OVERALL          : $OVERALL"
if [ -n "$REASONS" ]; then
  echo ""
  printf "%b" "$REASONS"
fi
echo "══════════════════════════════════════════════════════════════════"
echo ""

# --- JSON report ---
mkdir -p "$REPO_ROOT/.devin"

# Build JSON arrays for dirty/untracked files.
json_array() {
  local items="$1"
  local first="true"
  echo -n "["
  if [ -n "$items" ]; then
    while IFS= read -r line; do
      [ -n "$line" ] || continue
      if [ "$first" = "true" ]; then
        first="false"
      else
        echo -n ","
      fi
      echo -n " \"$line\""
    done <<< "$items"
  fi
  echo -n "]"
}

{
  echo "{"
  echo "  \"timestamp_epoch\": $NOW_EPOCH,"
  echo "  \"branch\": \"$BRANCH\","
  echo "  \"head\": \"$HEAD\","
  echo "  \"head_date\": \"$HEAD_DATE\","
  echo "  \"dirty\": $DIRTY_FLAG,"
  echo "  \"dirty_files\": $(json_array "$DIRTY_FILES"),"
  echo "  \"untracked\": $UNTRACKED_FLAG,"
  echo "  \"untracked_files\": $(json_array "$UNTRACKED_FILES"),"
  echo "  \"im73d_env\": \"$IM73D_ENV\","
  echo "  \"im73d_upload_guard\": \"$IM73D_GUARD\","
  echo "  \"im73d_plan\": \"$IM73D_PLAN\","
  echo "  \"handoff_status\": \"$HANDOFF_STATUS\","
  echo "  \"progress_status\": \"$PROGRESS_STATUS\","
  echo "  \"spec_index_status\": \"$SPEC_STATUS\","
  echo "  \"device_registry_dirty\": $REGISTRY_DIRTY,"
  echo "  \"overall\": \"$OVERALL\","
  echo "  \"reasons\": $(json_array "$REASONS")"
  echo "}"
} > "$REPO_ROOT/.devin/repo-truth-report.json"

exit 0
