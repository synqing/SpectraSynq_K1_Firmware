#!/usr/bin/env bash
# Create an immutable F2 run only after the complete reviewed image set passes.

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

exec python3 -m scripts.dual_sync_probe.f2_run "$@"
