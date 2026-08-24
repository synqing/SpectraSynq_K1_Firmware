#!/usr/bin/env bash
# Isolated PlatformIO build for k1_usb_audio_mac_probe only.
#
# Arduino 3.3.11 / pioarduino 55.03.311 must not share ~/.platformio/packages
# with production 54.03.20 / Arduino 3.2.0. Captain 2026-08-24: use
# PLATFORMIO_{PLATFORMS,PACKAGES,CACHE}_DIR plus a private workspace.
# No hashed-framework symlink. Never upload from this wrapper.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

ENV_NAME="k1_usb_audio_mac_probe"
USB_PIO_ROOT="${PLATFORMIO_K1_USB_AUDIO_ROOT:-$HOME/.platformio-k1-usb-audio}"
PIO_BIN="${PLATFORMIO_K1_USB_AUDIO_PIO:-$HOME/.platformio/penv/bin/pio}"

if [[ ! -x "$PIO_BIN" ]]; then
  echo "ERROR: pio not executable at $PIO_BIN" >&2
  exit 1
fi

if [[ "$#" -gt 1 ]]; then
  echo "ERROR: this wrapper accepts no extra args (build only)" >&2
  exit 1
fi
if [[ "$#" -eq 1 && "$1" != "$ENV_NAME" ]]; then
  echo "ERROR: only $ENV_NAME is allowed (got '$1')" >&2
  exit 1
fi

export PLATFORMIO_PLATFORMS_DIR="$USB_PIO_ROOT/platforms"
export PLATFORMIO_PACKAGES_DIR="$USB_PIO_ROOT/packages"
export PLATFORMIO_CACHE_DIR="$USB_PIO_ROOT/cache"
export PLATFORMIO_WORKSPACE_DIR="$REPO_ROOT/.pio-usb-audio"

mkdir -p "$PLATFORMIO_PLATFORMS_DIR" "$PLATFORMIO_PACKAGES_DIR" "$PLATFORMIO_CACHE_DIR" \
  "$PLATFORMIO_WORKSPACE_DIR"

echo "USB isolated PIO root: $USB_PIO_ROOT"
echo "USB workspace: $PLATFORMIO_WORKSPACE_DIR"
exec "$PIO_BIN" run -e "$ENV_NAME"
