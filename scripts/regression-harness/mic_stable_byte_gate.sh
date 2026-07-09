#!/usr/bin/env bash
# ============================================================================
# mic_stable_byte_gate.sh — trustworthy byte-identity gate for the mic lane
# ----------------------------------------------------------------------------
# DETERMINISM FINDING (2026-07-06): the ESP-IDF/Arduino image is NOT bit-
# reproducible in .flash.text / .flash.rodata — two CLEAN builds of identical
# source produce different hashes for those two sections (link-order / embedded
# timestamp). So registry_byte_gate.sh (which hashes all five loadable sections)
# is inherently flaky and cannot be trusted to distinguish a real regression
# from benign build noise.
#
# The other three loadable sections REPRODUCE byte-for-byte across clean rebuilds
# of identical source:
#     .dram0.data   .iram0.text   .iram0.vectors
# This gate hashes ONLY those three, so a committed reference for them is a
# TRUSTWORTHY behaviour-preservation oracle for the IM73D productionization lane
# (the "SPH0645 stays byte-identical while we do IM73D work" contract).
#
# This is ADDITIVE — registry_byte_gate.sh is left untouched as the historical
# trust root; this is the reliable oracle to use going forward for mic work.
#
# Usage:
#   bash scripts/regression-harness/mic_stable_byte_gate.sh            # check all
#   bash scripts/regression-harness/mic_stable_byte_gate.sh --update   # re-record
#   bash scripts/regression-harness/mic_stable_byte_gate.sh <env>...   # subset
#
# Exit 0 == every checked env's stable-section fingerprint matches the reference.
# Non-zero on any mismatch, build failure, or missing toolchain (fail-closed).
# ============================================================================
set -uo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT" || exit 1

# The three REPRODUCIBLE loadable sections (see header).
SECTIONS=(.dram0.data .iram0.text .iram0.vectors)
REF_FILE="scripts/regression-harness/results/mic_stable_byte_gate.reference"
# SPH builds whose byte-identity is the behaviour-preservation invariant, plus
# the IM73D reference build. Override by passing env names on the command line.
DEFAULT_ENVS=(k1_hardware k1_bench_reference k1_bench_im73d)

say() { printf '%s\n' "$*" >&2; }

UPDATE=0
ENVS=()
for a in "$@"; do
  if [ "$a" = "--update" ]; then UPDATE=1; else ENVS+=("$a"); fi
done
[ "${#ENVS[@]}" -eq 0 ] && ENVS=("${DEFAULT_ENVS[@]}")

find_objcopy() {
  for c in \
    "$HOME/.platformio/packages/toolchain-xtensa-esp-elf/bin/xtensa-esp32s3-elf-objcopy" \
    "$HOME/.platformio/packages/toolchain-xtensa-esp-elf/bin/xtensa-esp-elf-objcopy"; do
    [ -x "$c" ] && { echo "$c"; return 0; }
  done
  command -v xtensa-esp32s3-elf-objcopy 2>/dev/null && return 0
  echo ""; return 1
}
find_pio() {
  if command -v pio >/dev/null 2>&1; then echo "pio";
  elif [ -x "$HOME/.local/bin/pio" ]; then echo "$HOME/.local/bin/pio";
  elif python3 -c 'import platformio' >/dev/null 2>&1; then echo "python3 -m platformio";
  else echo ""; fi
}
sha256_file() {
  if command -v shasum >/dev/null 2>&1; then shasum -a 256 "$1" | awk '{print $1}';
  else sha256sum "$1" | awk '{print $1}'; fi
}

OBJCOPY="$(find_objcopy)"; PIO="$(find_pio)"
[ -z "$OBJCOPY" ] && { say "✗ xtensa objcopy not found — fail-closed."; exit 3; }
[ -z "$PIO" ] && { say "✗ PlatformIO not found — fail-closed."; exit 3; }

fingerprint_env() {  # -> prints "<env> <hash>"
  local env_name="$1"
  local elf=".pio/build/${env_name}/firmware.elf"
  if ! out="$($PIO run -e "$env_name" 2>&1)"; then
    printf '%s\n' "$out" | tail -6 >&2
    say "✗ ${env_name} build FAILED"; return 2
  fi
  [ -f "$elf" ] || { say "✗ ${env_name} ELF missing: $elf"; return 2; }
  local tmp; tmp="$(mktemp -d)"; local i=0
  for s in "${SECTIONS[@]}"; do
    i=$((i+1))
    "$OBJCOPY" -O binary --only-section="$s" "$elf" "$tmp/sec${i}.bin" 2>/dev/null
  done
  cat "$tmp"/sec*.bin > "$tmp/all.bin"
  local h; h="$(sha256_file "$tmp/all.bin")"
  rm -rf "$tmp"
  printf '%s %s\n' "$env_name" "$h"
}

if [ "$UPDATE" -eq 1 ]; then
  mkdir -p "$(dirname "$REF_FILE")"
  say "→ recording stable-section reference for: ${ENVS[*]}"
  : > "$REF_FILE.tmp"
  rc=0
  for e in "${ENVS[@]}"; do fingerprint_env "$e" >> "$REF_FILE.tmp" || rc=1; done
  [ "$rc" -eq 0 ] && mv "$REF_FILE.tmp" "$REF_FILE" && say "✓ reference recorded → $REF_FILE"
  exit "$rc"
fi

[ -f "$REF_FILE" ] || { say "✗ no reference at $REF_FILE — run --update first."; exit 2; }

fail=0
for e in "${ENVS[@]}"; do
  line="$(fingerprint_env "$e")" || { fail=1; continue; }
  got="$(echo "$line" | awk '{print $2}')"
  want="$(awk -v env="$e" '$1==env{print $2}' "$REF_FILE")"
  if [ -z "$want" ]; then say "⚠ ${e}: no reference entry (add via --update)"; continue; fi
  if [ "$got" = "$want" ]; then say "✓ ${e}: stable sections byte-identical";
  else say "✗ ${e}: STABLE-SECTION DRIFT — want ${want:0:16}… got ${got:0:16}…"; fail=1; fi
done
exit "$fail"
