#!/usr/bin/env bash
# USB-serial-first F2 port resolver. It never flashes or resets a device.

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

exec python3 -m scripts.dual_sync_probe.f2_ports "$@"
