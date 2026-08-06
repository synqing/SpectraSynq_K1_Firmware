#!/usr/bin/env bash
# Identity-first exact application writer for F2 A/B.
# C1/C2 never flash. This path never builds or invokes PlatformIO upload.

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

exec python3 -m scripts.dual_sync_probe.f2_flash "$@"
