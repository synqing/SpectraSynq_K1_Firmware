#!/usr/bin/env bash
# F2 A/B/C1/C2 Link Ready capture entry point. This is not Gate-0.
# The Python controller locks case semantics, probes identity/build provenance,
# enforces A -> B -> C1 -> C2 and writes the evidence manifest. It never flashes.

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

exec python3 -m scripts.dual_sync_probe.f2_capture "$@"
