#!/usr/bin/env bash
# Rebuild scoped AST graphify graph (Tab5 + K1 firmware only).
# Output: evidence/graphify-trial-20260609/stage2-scoped/scoped-ast-graph.json
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="${GRAPHIFY_SCOPED_TMP:-/tmp/sb-graphify-stage2}"
OUT_DIR="$REPO_ROOT/evidence/graphify-trial-20260609/stage2-scoped"
OUT_GRAPH="$OUT_DIR/scoped-ast-graph.json"

rm -rf "$TMP"
mkdir -p "$TMP" "$OUT_DIR"

rsync -a "$REPO_ROOT/sb-tab5-wireless-controller/" "$TMP/sb-tab5-wireless-controller/" \
  --exclude graphify-out \
  --exclude .pio \
  --exclude build \
  --exclude dist

rsync -a "$REPO_ROOT/SPECTRASYNQ_K1_FIRMWARE/" "$TMP/SPECTRASYNQ_K1_FIRMWARE/" \
  --exclude .pio \
  --exclude build \
  --exclude dist

(cd "$TMP" && graphify update . --no-cluster)

cp "$TMP/graphify-out/graph.json" "$OUT_GRAPH"
echo "scoped graph: $OUT_GRAPH ($(wc -c <"$OUT_GRAPH" | tr -d ' ') bytes)"
