#!/usr/bin/env bash
# Fail-closed F2 evidence finaliser and immutable Captain STOP writer.

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

exec python3 -m scripts.dual_sync_probe.f2_status "$@"
