#!/usr/bin/env bash
# Identity-first F2 A/B guarded upload entry point. Case C never flashes.

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

exec python3 -m scripts.dual_sync_probe.f2_flash "$@"
