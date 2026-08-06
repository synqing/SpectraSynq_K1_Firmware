#!/usr/bin/env bash
# Controlled C1-to-C2 typed dual reset. No flash, erase or build is permitted.

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

exec python3 -m scripts.dual_sync_probe.f2_reboot "$@"
