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

# --- Active lane authority ---
SPEC_INDEX="$REPO_ROOT/docs/spec-index.md"
ACTIVE_BRANCH=""
ACTIVE_LANE=""
ACTIVE_AUTHORITY=""
AUTHORITY_BRANCH=""
AUTHORITY_STATUS=""
if [ -f "$SPEC_INDEX" ]; then
  ACTIVE_BRANCH="$(sed -n 's/^active_branch:[[:space:]]*//p' "$SPEC_INDEX" | head -1)"
  ACTIVE_LANE="$(sed -n 's/^active_lane:[[:space:]]*//p' "$SPEC_INDEX" | head -1)"
  ACTIVE_AUTHORITY="$(sed -n 's/^active_authority:[[:space:]]*//p' "$SPEC_INDEX" | head -1)"
fi

if [ -z "$ACTIVE_BRANCH" ]; then
  fail "docs/spec-index.md has no active_branch frontmatter"
elif [ "$BRANCH" != "$ACTIVE_BRANCH" ]; then
  fail "checked-out branch '$BRANCH' does not match active_branch '$ACTIVE_BRANCH'"
fi

if [ -z "$ACTIVE_AUTHORITY" ]; then
  fail "docs/spec-index.md has no active_authority frontmatter"
elif [[ "$ACTIVE_AUTHORITY" = /* || "$ACTIVE_AUTHORITY" = *".."* ]]; then
  fail "active_authority must be a repository-relative path without '..': $ACTIVE_AUTHORITY"
elif [ ! -f "$REPO_ROOT/$ACTIVE_AUTHORITY" ]; then
  fail "active authority does not exist: $ACTIVE_AUTHORITY"
else
  AUTHORITY_BRANCH="$(sed -n 's/^branch:[[:space:]]*//p' "$REPO_ROOT/$ACTIVE_AUTHORITY" | head -1)"
  AUTHORITY_STATUS="$(sed -n 's/^status:[[:space:]]*//p' "$REPO_ROOT/$ACTIVE_AUTHORITY" | head -1)"
  if ! git ls-files --error-unmatch -- "$ACTIVE_AUTHORITY" >/dev/null 2>&1; then
    fail "active authority is not tracked or staged: $ACTIVE_AUTHORITY"
  fi
  if [ "$AUTHORITY_STATUS" != "active" ]; then
    fail "active authority status is '${AUTHORITY_STATUS:-missing}', expected 'active'"
  fi
  if [ -z "$AUTHORITY_BRANCH" ]; then
    fail "active authority has no branch frontmatter"
  elif [ "$AUTHORITY_BRANCH" != "$ACTIVE_BRANCH" ]; then
    fail "active authority branch '$AUTHORITY_BRANCH' does not match spec-index '$ACTIVE_BRANCH'"
  fi
fi

# --- Repository capability checks retained across lanes ---
IM73D_ENV="FAIL"
if [ -f "$REPO_ROOT/platformio.ini" ] && grep -q '^\[env:k1_bench_im73d\]' "$REPO_ROOT/platformio.ini"; then
  IM73D_ENV="PASS"
else
  fail "platformio.ini is missing [env:k1_bench_im73d]"
fi

# N4a: env→device mapping lives in k1_device_identities.json (consumed by
# k1_upload_guard.py). Accept either the JSON manifest or a legacy hard-coded
# reference in the Python file.
IM73D_GUARD="FAIL"
if [ -f "$REPO_ROOT/scripts/platformio/k1_device_identities.json" ] && grep -q 'k1_bench_im73d' "$REPO_ROOT/scripts/platformio/k1_device_identities.json"; then
  IM73D_GUARD="PASS"
elif [ -f "$REPO_ROOT/scripts/platformio/k1_upload_guard.py" ] && grep -q 'k1_bench_im73d' "$REPO_ROOT/scripts/platformio/k1_upload_guard.py"; then
  IM73D_GUARD="PASS"
else
  fail "k1_bench_im73d missing from k1_device_identities.json (and k1_upload_guard.py)"
fi

IM73D_PLAN="FAIL"
if [ -f "$REPO_ROOT/docs/hardware/im73d122-ap-vp-migration-plan.md" ]; then
  IM73D_PLAN="PASS"
else
  fail "docs/hardware/im73d122-ap-vp-migration-plan.md is missing"
fi

# --- Current-lane doc checks ---
HANDOFF_STATUS="PASS"
if [ -f "$REPO_ROOT/.claude/handoff.md" ]; then
  if [ -n "$ACTIVE_AUTHORITY" ] && ! grep -Fq "$ACTIVE_AUTHORITY" "$REPO_ROOT/.claude/handoff.md"; then
    HANDOFF_STATUS="FAIL"
    fail ".claude/handoff.md does not reference active authority $ACTIVE_AUTHORITY"
  fi
fi

PROGRESS_STATUS="PASS"
if [ -f "$REPO_ROOT/progress.md" ]; then
  if [ -n "$ACTIVE_AUTHORITY" ] && ! grep -Fq "$ACTIVE_AUTHORITY" "$REPO_ROOT/progress.md"; then
    PROGRESS_STATUS="FAIL"
    fail "progress.md does not reference active authority $ACTIVE_AUTHORITY"
  fi
fi

SPEC_STATUS="PASS"
if [ -f "$REPO_ROOT/docs/spec-index.md" ]; then
  if [ -n "$ACTIVE_AUTHORITY" ] && ! grep -Fq "$ACTIVE_AUTHORITY" "$REPO_ROOT/docs/spec-index.md"; then
    SPEC_STATUS="FAIL"
    fail "docs/spec-index.md does not reference active authority $ACTIVE_AUTHORITY"
  fi
fi

AGENT_OS_STATUS="PASS"
if [ -f "$REPO_ROOT/AGENT_OS.md" ]; then
  if [ -n "$ACTIVE_AUTHORITY" ] && ! grep -Fq "$ACTIVE_AUTHORITY" "$REPO_ROOT/AGENT_OS.md"; then
    AGENT_OS_STATUS="FAIL"
    fail "AGENT_OS.md does not reference active authority $ACTIVE_AUTHORITY"
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
echo "  active branch    : ${ACTIVE_BRANCH:-missing}"
echo "  active lane      : ${ACTIVE_LANE:-missing}"
echo "  active authority : ${ACTIVE_AUTHORITY:-missing}"
echo "  authority branch : ${AUTHORITY_BRANCH:-missing}"
echo "  authority status : ${AUTHORITY_STATUS:-missing}"
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
echo "  AGENT_OS.md      : $AGENT_OS_STATUS"
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
  echo "  \"active_branch\": \"$ACTIVE_BRANCH\","
  echo "  \"active_lane\": \"$ACTIVE_LANE\","
  echo "  \"active_authority\": \"$ACTIVE_AUTHORITY\","
  echo "  \"authority_branch\": \"$AUTHORITY_BRANCH\","
  echo "  \"authority_status\": \"$AUTHORITY_STATUS\","
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
  echo "  \"agent_os_status\": \"$AGENT_OS_STATUS\","
  echo "  \"device_registry_dirty\": $REGISTRY_DIRTY,"
  echo "  \"overall\": \"$OVERALL\","
  echo "  \"reasons\": $(json_array "$REASONS")"
  echo "}"
} > "$REPO_ROOT/.devin/repo-truth-report.json"

if [ "$OVERALL" = "FAIL" ]; then
  exit 1
fi
exit 0
