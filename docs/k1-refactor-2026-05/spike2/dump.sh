#!/usr/bin/env bash
# Spike #2 byte-identity dump harness.
# Usage: ./dump.sh <baseline|after>
# Dumps:
#   1. full .dram0.data + .flash.rodata sections (objdump -s -j)
#   2. nm -S symbol table filtered to the relocated objects
#   3. per-symbol initializer bytes extracted by VMA+size (the load-bearing proof)
set -euo pipefail

TAG="${1:?usage: dump.sh <baseline|after>}"
ROOT="/Users/spectrasynq/SensoryBridge-main 9/.claude/worktrees/agent-a0b332d904b690d68"
ELF="$ROOT/.pio/build/k1_hardware/firmware.elf"
OUT="$ROOT/docs/k1-refactor-2026-05/spike2"
OBJDUMP="$HOME/.platformio/packages/toolchain-xtensa-esp-elf/bin/xtensa-esp32s3-elf-objdump"
NM="$HOME/.platformio/packages/toolchain-xtensa-esp-elf/bin/xtensa-esp32s3-elf-nm"

# Full sections (whole-section addresses may legitimately shift; kept for audit).
"$OBJDUMP" -s -j .dram0.data "$ELF"   > "$OUT/$TAG.dram0.data.txt"
"$OBJDUMP" -s -j .flash.rodata "$ELF" > "$OUT/$TAG.flash.rodata.txt"

# Symbol table (address + size) for the relocated objects.
"$NM" -S "$ELF" | grep -iE " CONFIG$| CONFIG_DEFAULTS$| a_weight_table$" \
  | sort -k3 > "$OUT/$TAG.symbols.txt"

# Per-symbol initializer-byte extraction: for each relocated symbol, dump
# exactly [VMA, VMA+size) from the ELF via objdump --start/--stop on the
# section that contains it. This is the byte-identity proof — independent of
# whole-section address shift, because we compare the BYTES AT THE SYMBOL.
extract() {
  local sym="$1"
  local line vma size sec
  line=$("$NM" -S "$ELF" | grep -iE " ${sym}\$" | head -1)
  [ -z "$line" ] && { echo "$sym: NOT FOUND (likely BSS/zero-init)"; return; }
  vma=$(echo "$line" | awk '{print $1}')
  size=$(echo "$line" | awk '{print $2}')
  local class
  class=$(echo "$line" | awk '{print $3}')
  # B/b = BSS (zero-init): no initializer bytes to compare; record class only.
  if [ "$class" = "B" ] || [ "$class" = "b" ]; then
    echo "$sym  VMA=0x$vma  SIZE=0x$size  CLASS=$class (BSS / zero-init — no initializer bytes)"
    return
  fi
  # Determine containing section by VMA range.
  local vma_dec start_dec end_dec
  vma_dec=$((16#$vma))
  end_dec=$((vma_dec + 16#$size))
  # .dram0.data range 0x3fc95300 + 0x4870 ; .flash.rodata 0x3c050120 + 0x231a0
  if [ "$vma_dec" -ge $((16#3fc95300)) ] && [ "$vma_dec" -lt $((16#3fc99b70)) ]; then
    sec=".dram0.data"
  elif [ "$vma_dec" -ge $((16#3c050120)) ] && [ "$vma_dec" -lt $((16#3c0732c0)) ]; then
    sec=".flash.rodata"
  else
    sec="UNKNOWN"
  fi
  echo "### $sym  VMA=0x$vma  SIZE=0x$size  CLASS=$class  SEC=$sec"
  "$OBJDUMP" -s -j "$sec" \
    --start-address=0x$vma \
    --stop-address=$(printf '0x%x' "$end_dec") \
    "$ELF" | grep -E '^ ' || echo "(no bytes in range)"
}

{
  echo "# Spike #2 per-symbol initializer-byte dump — TAG=$TAG"
  echo "# ELF: $ELF"
  echo
  extract CONFIG
  echo
  extract a_weight_table
  echo
  extract CONFIG_DEFAULTS
} > "$OUT/$TAG.symbol-bytes.txt"

echo "wrote $OUT/$TAG.{dram0.data,flash.rodata,symbols,symbol-bytes}.txt"
