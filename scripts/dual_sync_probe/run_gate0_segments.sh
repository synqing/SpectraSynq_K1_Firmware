#!/usr/bin/env bash
# Until F3, this is NOT Gate-0. delay* firmware is timestamp-fake; these
# segments validate host plumbing only and must not be cited as Gate-0 silicon.

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

exec python3 -m scripts.dual_sync_probe.capture "$@"
