#!/usr/bin/env bash
# ============================================================================
# registry_byte_gate.sh — automate the k1_hardware byte-identity invariant
# ----------------------------------------------------------------------------
# The effect-registry work (feat/effect-registry-rewire) is flag-gated behind
# K1_EFFECT_REGISTRY_V1 / K1_EFFECT_FRAMEWORK_V1. The shipping `k1_hardware`
# env defines NEITHER, so the production firmware MUST stay byte-identical.
#
# This gate builds `k1_hardware` and compares the LOADABLE-SECTION SHA-256 of
# the resulting ELF against a committed reference fingerprint. The whole .bin
# embeds a build timestamp (esp_app_desc), so a whole-file hash drifts on every
# build for benign reasons — the proven method is the per-section content hash
# of the loadable PROGBITS sections (the functional firmware image), which is
# stable across rebuilds of identical source.
#
# Sections hashed (content-bearing, loaded to the device):
#   .flash.text  .flash.rodata  .dram0.data  .iram0.text  .iram0.vectors
#
# Usage:
#   bash scripts/regression-harness/registry_byte_gate.sh            # check
#   bash scripts/regression-harness/registry_byte_gate.sh --update   # re-record reference
#
# Exit 0 == fingerprint matches the reference (byte-identical). Non-zero on any
# mismatch, build failure, or missing toolchain — fail-closed.
# Cheap: one k1_hardware build (incremental) + five section dumps + one sha.
# ============================================================================
set -uo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT" || exit 1

ENV_NAME="k1_hardware"
ELF=".pio/build/${ENV_NAME}/firmware.elf"
BIN=".pio/build/${ENV_NAME}/firmware.bin"
REF_FILE="scripts/regression-harness/results/registry_byte_gate.reference"

# Loadable, content-bearing PROGBITS sections (the functional firmware image).
#   .flash.text / .iram0.text / .dram0.data / .iram0.vectors are PATH-INVARIANT
#   (verified bit-identical between this branch HEAD and its pre-registry parent
#   feat/effect-framework-v3-graft, built in a separate worktree path).
#   .flash.rodata carries __FILE__ / assert path strings, so it is stable only
#   when the checkout PATH is constant (true for CI / pre-commit on a fixed
#   tree). The gate hashes all five for the same-tree pre-commit use; a
#   CROSS-PATH audit must compare the four path-invariant sections only.
SECTIONS=(.flash.text .flash.rodata .dram0.data .iram0.text .iram0.vectors)

UPDATE=0
[ "${1:-}" = "--update" ] && UPDATE=1

say() { printf '%s\n' "$*" >&2; }

# --- locate toolchain objcopy + pio ----------------------------------------
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
sha256_stdin() {
  if command -v shasum >/dev/null 2>&1; then shasum -a 256 | awk '{print $1}';
  else sha256sum | awk '{print $1}'; fi
}

OBJCOPY="$(find_objcopy)"
PIO="$(find_pio)"
if [ -z "$OBJCOPY" ]; then say "✗ xtensa objcopy not found — cannot fingerprint (fail-closed)."; exit 3; fi
if [ -z "$PIO" ]; then say "✗ PlatformIO not found — cannot build (fail-closed)."; exit 3; fi

# --- build k1_hardware ------------------------------------------------------
say "→ ${PIO} run -e ${ENV_NAME}"
if ! out="$($PIO run -e "$ENV_NAME" 2>&1)"; then
  printf '%s\n' "$out" | tail -6 >&2
  say "✗ k1_hardware build FAILED — cannot verify byte-identity."; exit 2
fi
[ -f "$ELF" ] || { say "✗ ELF missing after build: $ELF"; exit 2; }

# --- whole-.bin size sanity (the human-readable invariant) ------------------
# NB: the absolute size is toolchain-dependent (this env: 649888 B). The brief's
# 649486 figure was recorded under a different toolchain. The byte-IDENTITY
# invariant is the per-section fingerprint below, not a hard-coded magic number;
# the recorded reference is the source of truth for "did the registry leak?".
BIN_BYTES="$(wc -c < "$BIN" 2>/dev/null | tr -d ' ')"
say "  firmware.bin size: ${BIN_BYTES} B"

# --- per-section content fingerprint ----------------------------------------
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT
{
  for s in "${SECTIONS[@]}"; do
    dump="$TMPDIR/sec"
    if "$OBJCOPY" -O binary --only-section "$s" "$ELF" "$dump" 2>/dev/null && [ -s "$dump" ]; then
      printf '%s:' "$s"
      sha256_stdin < "$dump"
    else
      printf '%s:MISSING\n' "$s"
    fi
  done
} > "$TMPDIR/manifest"

FINGERPRINT="$(sha256_stdin < "$TMPDIR/manifest")"
say "  loadable-section fingerprint: ${FINGERPRINT}"

# --- update mode: record the reference --------------------------------------
if [ "$UPDATE" -eq 1 ]; then
  mkdir -p "$(dirname "$REF_FILE")"
  {
    echo "# registry_byte_gate.sh reference — loadable-section SHA-256 of k1_hardware ELF"
    echo "# Regenerate ONLY when the production binary is INTENTIONALLY changed."
    echo "bin_bytes=${BIN_BYTES}"
    echo "fingerprint=${FINGERPRINT}"
    echo "# per-section manifest the fingerprint hashes:"
    sed 's/^/#   /' "$TMPDIR/manifest"
  } > "$REF_FILE"
  say "✓ reference recorded → ${REF_FILE}"
  exit 0
fi

# --- compare against committed reference ------------------------------------
if [ ! -f "$REF_FILE" ]; then
  say "✗ no reference fingerprint at ${REF_FILE} — run with --update to record one."
  exit 4
fi
REF_FP="$(grep '^fingerprint=' "$REF_FILE" | head -1 | cut -d= -f2)"
REF_BYTES="$(grep '^bin_bytes=' "$REF_FILE" | head -1 | cut -d= -f2)"

fail=0
if [ "$FINGERPRINT" != "$REF_FP" ]; then
  say "✗ LOADABLE-SECTION FINGERPRINT MISMATCH"
  say "    reference: ${REF_FP}"
  say "    built:     ${FINGERPRINT}"
  say "  The flag-gated registry work has LEAKED into the production k1_hardware"
  say "  build. Find the leak (a non-flag-gated edit to a shared TU) and restore"
  say "  byte-identity, OR — if the change is intentional — re-record with --update."
  fail=1
fi
if [ "$BIN_BYTES" != "$REF_BYTES" ]; then
  say "✗ firmware.bin size drift: ${BIN_BYTES} B vs reference ${REF_BYTES} B"
  fail=1
fi

if [ "$fail" -ne 0 ]; then
  say "GATE BLOCKED — k1_hardware is no longer byte-identical."; exit 1
fi
say "GATE PASSED — k1_hardware loadable-section fingerprint matches reference (byte-identical)."
exit 0
