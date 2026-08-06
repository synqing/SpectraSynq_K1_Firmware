#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-.}"
cd "$ROOT"

echo "GATE K718 HALO Phase 1"

fail=0
check_no_match() {
  local name="$1"; shift
  local pattern="$1"; shift
  local files=("$@")
  if grep -RInE "$pattern" "${files[@]}" >/tmp/k718_gate_hits.txt 2>/dev/null; then
    echo "FAIL $name"
    cat /tmp/k718_gate_hits.txt
    fail=1
  else
    echo "PASS $name"
  fi
}

# Runtime glass/UI source only. Generated map is intentionally excluded.
UI_FILES=(remoted_dashboard.cpp remoted_dashboard.h knob.cpp k718_feedback.cpp k718_feedback.h)

check_no_match "old UI object names" 's_center|s_hint|s_link|s_pri|s_sec|s_global|s_menu_rows' "${UI_FILES[@]}"
check_no_match "banned glass words as standalone tokens" '\b(PEND|CONF|CONFIRMED|ACK|LINKED|ADVERTISING)\b|BLE LINK|BLE ADV|BLE LOST|received|applied' "${UI_FILES[@]}"
check_no_match "hardcoded ten-preset display" '"0?6"|"0?7"|"0?8"|"0?9"|"10"' remoted_dashboard.cpp
check_no_match "fake tempo driver" '\bBPM\b|bpm=128|period_ms|60000' remoted_dashboard.cpp
check_no_match "linear menu rows" 'menu_rows|FUNCTIONS|TAP a function|ENCODER chooses|SWIPE DOWN closes' remoted_dashboard.cpp knob.cpp
check_no_match "boot self-test enabled" '#define[[:space:]]+K718_PHASE1_SELFTEST[[:space:]]+1' knob.cpp

# Allow allocations in build/init only. This is a blunt check for obvious regressions.
if grep -nE 'heap_caps_malloc|malloc|calloc|new ' remoted_dashboard.cpp | grep -Ei 'tick|render_fx\(|on_encoder|on_touch|compose|frame' >/tmp/k718_alloc_hits.txt; then
  echo "FAIL render-loop allocation suspect"
  cat /tmp/k718_alloc_hits.txt
  fail=1
else
  echo "PASS render-loop allocation suspect"
fi

if [[ $fail -ne 0 ]]; then
  echo "K718_PHASE1_GATE FAIL"
  exit 1
fi

echo "K718_PHASE1_GATE PASS"
