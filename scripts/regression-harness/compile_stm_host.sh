#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="$ROOT/.pio/stm_host_shim.dylib"
mkdir -p "$(dirname "$OUT")"
TMP="$(mktemp -d)"
cat > "$TMP/stm_host.cpp" << 'CPP'
#define K1_STM
#include "k1_stm.h"
extern "C" {
void host_k1_stm_reset(void) { k1_stm_reset(); }
void host_k1_stm_process(const float* spectrum, uint8_t num_bins, int silence, K1StmResult* out) {
  k1_stm_process(spectrum, num_bins, silence != 0, out);
}
}
CPP
c++ -shared -fPIC -O2 -std=c++17 -DK1_STM \
  -I"$ROOT/SPECTRASYNQ_K1_FIRMWARE/audio" \
  "$TMP/stm_host.cpp" "$ROOT/SPECTRASYNQ_K1_FIRMWARE/audio/k1_stm.cpp" \
  -o "$OUT"
echo "$OUT"
