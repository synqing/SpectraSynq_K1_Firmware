#!/usr/bin/env bash
# k1-flash-verified.sh — the ONLY sanctioned way to put firmware on a K1 bench device.
#
# Build → flash → prove the device is running exactly what we just built → emit a
# registry-ready deployed-state line.
#
# Why this exists (2026-08-11): a lane flashed a device twelve times without ever
# recording deployed state, and a later session collected forty minutes of device
# evidence — a noise calibration, quiet/music distributions, a derived threshold —
# against a build a CONCURRENT session had flashed underneath it. Every number
# looked plausible. Nothing in the process forced the question "what is actually
# running right now?", so nobody asked it.
#
# This script asks it, twice, and refuses to report success unless the answer is
# the binary it just built.
#
# Usage:
#   bash scripts/agent/k1-flash-verified.sh <env> [--port /dev/cu.usbmodemXXXX]
#
# Exit codes: 0 flashed+verified · 1 usage/build/flash failure · 3 identity mismatch
set -euo pipefail

ENV_NAME="${1:-}"
shift || true
PORT=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --port) PORT="$2"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 1 ;;
  esac
done

if [[ -z "$ENV_NAME" ]]; then
  echo "usage: $0 <pio-env> [--port /dev/cu.usbmodemXXXX]" >&2
  exit 1
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"
GUARD="scripts/regression-harness/k1_device_identity_guard.py"

say() { printf '\n\033[1m== %s\033[0m\n' "$*"; }

# ── 0. refuse to flash a dirty tree ────────────────────────────────────────────
# A flash from uncommitted source cannot be reproduced or rolled back to, and the
# git SHA stamped into the binary would name a commit that does not contain it.
if [[ -n "$(git status --porcelain -- SPECTRASYNQ_K1_FIRMWARE platformio.ini)" ]]; then
  echo "REFUSING: firmware source or platformio.ini is dirty. Commit first — a flash" >&2
  echo "from an uncommitted tree stamps a git SHA that does not contain the code." >&2
  git status --short -- SPECTRASYNQ_K1_FIRMWARE platformio.ini >&2
  exit 1
fi
EXPECT_GIT="$(git rev-parse --short=7 HEAD)"

say "Building $ENV_NAME @ $EXPECT_GIT"
pio run -e "$ENV_NAME" >/dev/null

# ── 1. who is on the port BEFORE we write? ─────────────────────────────────────
# Not fatal — it is legitimately a different (older) build. But it is recorded, so
# a surprise here is visible rather than silent.
if [[ -n "$PORT" ]]; then
  say "Device BEFORE flash"
  # HF-57 (canon 2026-08-14): prefix so a grep for the verdict can NEVER match
  # this pre-flash line. The ONLY success signals are this script's exit code 0
  # and the FLASHED-AND-VERIFIED block below (post-flash identity, NEW epoch).
  python3 "$GUARD" --port "$PORT" 2>&1 | sed 's/^/BEFORE-FLASH: /' || echo "  (no identity — device may be unflashed or busy)"
fi

# ── 2. flash. The pio upload guard verifies chip-id ↔ env on its own. ──────────
say "Flashing $ENV_NAME"
pio run -e "$ENV_NAME" --target upload

# ── 3. prove the device is running what we just built ─────────────────────────
sleep 6
if [[ -z "$PORT" ]]; then
  PORT="$(sed -n "/^\[env:${ENV_NAME}\]/,/^\[env:/p" platformio.ini \
          | sed -n 's/^upload_port *= *//p' | head -1 | sed 's#/dev/tty#/dev/cu#')"
fi
say "Device AFTER flash — must be $EXPECT_GIT"
if ! python3 "$GUARD" --port "$PORT" --expect-git "$EXPECT_GIT" --expect-env "$ENV_NAME"; then
  echo >&2
  echo "FLASH NOT VERIFIED. The device is not running the build we just made." >&2
  echo "Do NOT collect evidence from it. Resolve device ownership first." >&2
  exit 3
fi

# ── 4. registry-ready line — deployed state is part of the flash, not a chore ──
CHIP="$(python3 - "$PORT" <<'PY' 2>/dev/null || true
import sys, time, serial
s = serial.Serial(); s.port = sys.argv[1]; s.baudrate = 115200; s.timeout = 0.3
s.dtr = True; s.rts = False; s.open(); time.sleep(0.6); s.reset_input_buffer()
s.write(b":dump\n"); s.flush()
buf = bytearray(); t = time.time() + 3
while time.time() < t:
    c = s.read(4096)
    if c: buf.extend(c)
s.close()
for line in buf.decode("utf-8", "replace").splitlines():
    if "CHIP ID" in line:
        print(line.split(":")[-1].strip()); break
PY
)"

say "FLASHED AND VERIFIED"
cat <<EOF
Paste into docs/hardware/device-build-registry.md deployed-state:

| chip \`${CHIP:-unknown}\` on \`$PORT\` | \`$(git rev-parse --abbrev-ref HEAD)\` @ \`$EXPECT_GIT\` | **\`$ENV_NAME\`** | flashed $(date +%Y-%m-%d) |
EOF
