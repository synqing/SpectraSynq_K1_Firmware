#!/usr/bin/env bash
# k1-session-preflight.sh — run BEFORE touching a K1 device or deriving any constant.
#
# Enforces the two failures that prose doctrine did not prevent (canon 2026-08-12):
#   HF-32  the fix you are about to write already exists, unmerged, on another branch
#   HF-33  your branch is based on a stale main and silently omits crash fixes
# and orients you on HF-29 (who is actually on each port right now).
#
# On 2026-08-11/12 all five of the following existed unmerged and were re-derived by hand:
#   395116f (G=8 revert) · 248ec79 (peakiness gate) · FINDING-rms-cannot-separate.md
#   SESSION_CANON_2026-08-07 (joint composition) · 622997b3 (null-guard crash fix)
# The last one, missing from a stale branch base, boot-looped a bench device.
#
# Usage:  bash scripts/agent/k1-session-preflight.sh [symbol ...]
#   e.g.  bash scripts/agent/k1-session-preflight.sh K1_SILENCE_PEAKINESS_BREAK INPUT_GAIN
#
# Advisory by design: it prints WARN and exits 0 so it can open any session. The one thing
# it must never do is stay silent about a stale base.
set -uo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

RED=$'\033[31m'; YEL=$'\033[33m'; GRN=$'\033[32m'; BLD=$'\033[1m'; RST=$'\033[0m'
warn=0
hdr() { printf '\n%s== %s%s\n' "$BLD" "$*" "$RST"; }

# ── HF-33 · is this branch based on current origin/main? ──────────────────────
hdr "HF-33  branch base"
git fetch -q origin main 2>/dev/null || echo "  (fetch failed — offline? base check may be stale)"
BR=$(git rev-parse --abbrev-ref HEAD)
BEHIND=$(git rev-list --count HEAD..origin/main 2>/dev/null || echo "?")
if [[ "$BEHIND" == "0" ]]; then
  echo "  ${GRN}OK${RST}  $BR is up to date with origin/main"
elif [[ "$BEHIND" == "?" ]]; then
  echo "  ${YEL}WARN${RST}  could not compare to origin/main"; warn=1
else
  echo "  ${RED}STALE${RST}  $BR is ${BLD}$BEHIND commits behind origin/main${RST}"
  echo "         Commits you do not have — check for crash/safety fixes before flashing:"
  git log --oneline HEAD..origin/main 2>/dev/null | grep -iE 'fix|guard|null|crash|panic|boot|safe' | head -8 | sed 's/^/           /'
  echo "         A stale base boot-looped a bench device on 2026-08-11 (missing 622997b3)."
  warn=1
fi

# ── HF-32 · does the thing you are about to derive already exist? ─────────────
if [[ $# -gt 0 ]]; then
  hdr "HF-32  unmerged prior art for: $*"
  for sym in "$@"; do
    hits=$(git log --all --oneline -S "$sym" 2>/dev/null | head -6)
    if [[ -z "$hits" ]]; then
      echo "  ${GRN}none${RST}  $sym"
    else
      echo "  ${YEL}EXISTS${RST}  $sym — commits that touched this value:"
      while IFS= read -r line; do
        sha=${line%% *}
        merged=$(git merge-base --is-ancestor "$sha" origin/main 2>/dev/null && echo "on main" || echo "${RED}NOT on main${RST}")
        echo "           $line   [$merged]"
      done <<< "$hits"
      warn=1
    fi
  done
  echo "  Read the NOT-on-main ones before deriving anything. Five for five this session."
else
  hdr "HF-32  unmerged prior art"
  echo "  (pass the symbols you are about to touch, e.g. K1_SILENCE_PEAKINESS_BREAK)"
fi

# ── HF-29 · who is actually on each port right now? ───────────────────────────
hdr "HF-29  live device identity"
GUARD=scripts/regression-harness/k1_device_identity_guard.py
found=0
for p in /dev/cu.usbmodem*; do
  [[ -e "$p" ]] || continue
  found=1
  out=$(python3 "$GUARD" --port "$p" 2>&1 | tail -1)
  printf '  %-26s %s\n' "$(basename "$p")" "$out"
done
[[ $found -eq 1 ]] || echo "  (no /dev/cu.usbmodem* visible — sandboxed shell hides /dev; rerun unsandboxed)"
echo "  Anything you did not flash yourself is a CONCURRENT SESSION. Resolve ownership first."

# ── concurrent worktrees that can flash the same devices ─────────────────────
hdr "concurrent worktrees"
n=$(git worktree list | grep -c '.worktrees/' || true)
git worktree list | grep '.worktrees/' | sed 's/^/  /' || echo "  (none)"
[[ "$n" -gt 1 ]] && { echo "  ${YEL}$n worktrees can build and flash these devices.${RST}"; warn=1; }

hdr "verdict"
if [[ $warn -eq 0 ]]; then
  echo "  ${GRN}CLEAR${RST} — base current, no unmerged prior art, devices accounted for."
else
  echo "  ${YEL}WARNINGS ABOVE${RST} — none block, all have cost a session before. Read them."
fi
exit 0
