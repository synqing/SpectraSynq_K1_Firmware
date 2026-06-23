#!/usr/bin/env bash
# Row 1 — build + run the host-side dispatch-table classification test.
# No firmware / Arduino toolchain required: this compiles the pure logic on the
# host with the system C++ compiler and asserts the safety invariants + the
# D5/D6 signed deltas. See row1_dispatch_table_test.cpp for what it does and
# does not cover.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$HERE/row1_dispatch_table_test.cpp"
BIN="$(mktemp -t row1_test.XXXXXX)"
trap 'rm -f "$BIN"' EXIT

CXX="${CXX:-c++}"
echo "Compiling $SRC with $CXX -std=c++17 ..."
"$CXX" -std=c++17 -Wall -Wextra "$SRC" -o "$BIN"
echo "Running ..."
"$BIN"
