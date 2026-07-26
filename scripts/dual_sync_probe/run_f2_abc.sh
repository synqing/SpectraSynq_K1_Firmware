#!/usr/bin/env bash
# F2 A/B/C Link Ready capture entry point. This is not a Gate-0 runner.
# The Python controller locks case semantics, probes identity/build provenance,
# enforces A -> B -> C and writes the evidence manifest. It never flashes.

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

exec python3 -m scripts.dual_sync_probe.f2_capture "$@"
