#!/usr/bin/env bash
# ============================================================================
# framework-safety-gate — Gate-0 regression guard for the effect framework
# ----------------------------------------------------------------------------
# Two CHEAP greps that hard-fail the commit if a known crash class is
# re-introduced into the effect framework. Documented, fast, no build.
#
#   CL-2 (fail-closed allocators):
#     No flash-write symbol may appear under effects/framework/. A flash write
#     (LittleFS / NVS / EEPROM.commit / File.write) on a framework path means
#     the PSRAM render and a flash-cache-disable window can collide.
#
#   CL-1 (real cross-core barrier):
#     The framework-gated lock_leds(){...} body in globals.h must NOT be empty.
#     An empty body = the no-op guard = crash the moment a preset save lands
#     mid-frame while the framework render touches PSRAM.
#
# Exit 0 = clean, exit 1 = a crash class regressed. Run directly any time:
#   scripts/hooks/framework-safety-gate.sh
# ============================================================================
set -uo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT" || exit 1

FW_DIR="SPECTRASYNQ_K1_FIRMWARE/effects/framework"
GLOBALS="SPECTRASYNQ_K1_FIRMWARE/system/globals.h"
fail=0

say() { printf '%s\n' "$*" >&2; }

# --- CL-2: no flash-write symbol anywhere under the framework ---------------
# Match flash-write APIs and method-call shapes that imply a flash write.
FLASH_RE='LittleFS|EEPROM\.commit|nvs_set|\.write\(|\bFile '
if [ -d "$FW_DIR" ]; then
  hits="$(grep -REn "$FLASH_RE" "$FW_DIR" --include='*.cpp' --include='*.h' --include='*.hpp' 2>/dev/null || true)"
  if [ -n "$hits" ]; then
    say "  ✗ CL-2 REGRESSION: flash-write symbol found under ${FW_DIR}/ —"
    say "    the framework render touches PSRAM and must NEVER write flash."
    printf '%s\n' "$hits" | sed 's/^/      /' >&2
    fail=1
  fi
fi

# --- CL-1: the park-gated lock_leds() body must not be empty -----------
# Extract the lock_leds(){ ... } body that sits under #ifdef K1_LED_PARK_V1
# (or the legacy #ifdef K1_EFFECT_FRAMEWORK_V1) and confirm it contains real
# statements. G7B compiles the same barrier via K1_PERSIST_PARK_V1.
if [ -f "$GLOBALS" ]; then
  body="$(awk '
    /#ifdef K1_LED_PARK_V1/ { inflag=1 }
    /#ifdef K1_EFFECT_FRAMEWORK_V1/ { inflag=1 }
    inflag && /inline void lock_leds\(\)/ { grab=1 }
    grab {
      print
      if ($0 ~ /\}/ && seenopen) { exit }
      if ($0 ~ /\{/) { seenopen=1 }
    }
  ' "$GLOBALS")"
  # Strip the signature/braces/comments/blank lines; what remains must be real code.
  real="$(printf '%s\n' "$body" \
    | grep -v 'inline void lock_leds' \
    | sed 's://.*::' \
    | tr -d '{} \t' \
    | grep -v '^$' || true)"
  if [ -z "$real" ]; then
    say "  ✗ CL-1 REGRESSION: framework-gated lock_leds() body is EMPTY in ${GLOBALS}."
    say "    The flag-on path needs a real ack-barrier, not a no-op."
    fail=1
  fi
fi

if [ "$fail" -ne 0 ]; then
  say "  framework-safety-gate: FAIL"
  exit 1
fi
exit 0
