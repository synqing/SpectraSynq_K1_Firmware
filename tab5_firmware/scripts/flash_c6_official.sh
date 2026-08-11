#!/usr/bin/env bash
set -euo pipefail

# Flash the official M5 Tab5 ESP32-C6 Wi-Fi (ESP-Hosted SDIO) firmware
# pulled from the M5Tab5-UserDemo repository.
#
# This script will:
#   - Locate the official C6 Wi-Fi firmware binary in ../M5Tab5-UserDemo
#   - Auto-detect a serial port with an ESP32-C6 connected
#   - Flash the image with esptool
#
# Usage:
#   scripts/flash_c6_official.sh [--port /dev/ttyUSB0] [--baud 1500000]
#
# Requirements:
#   - python3 -m esptool available
#   - C6 connected to your computer via the Tab5 C6 download header and a USB-TTL adapter

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Try to locate the official binary near the workspace root
search_base="$(cd "${ROOT_DIR}/../../.." && pwd)"
BIN_ABS="${search_base}/M5Tab5-UserDemo/platforms/tab5/wifi_c6_fw/ESP32C6-WiFi-SDIO-Interface-V1.4.1-96bea3a_0x0.bin"
if [[ ! -f "$BIN_ABS" ]]; then
  # Fallback: search anywhere under workspace root
  BIN_ABS="$(find "$search_base" -maxdepth 4 -type f -name 'ESP32C6-WiFi-SDIO-Interface-*_0x0.bin' 2>/dev/null | head -n1 || true)"
fi

PORT=""
BAUD="1500000"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --port) PORT="$2"; shift 2;;
    --baud) BAUD="$2"; shift 2;;
    -h|--help)
      grep '^#' "$0" | sed -e 's/^# \{0,1\}//'; exit 0;;
    *) echo "Unknown arg: $1" >&2; exit 1;;
  esac
done

[[ -n "${BIN_ABS:-}" && -f "$BIN_ABS" ]] || {
  echo "Firmware binary not found: $BIN_ABS" >&2
  echo "Clone the official repo alongside this project:" >&2
  echo "  git clone https://github.com/m5stack/M5Tab5-UserDemo.git" >&2
  exit 1
}

if ! python3 -m esptool --help >/dev/null 2>&1; then
  echo "esptool not found. Try: python3 -m pip install esptool" >&2
  exit 1
fi

detect_c6_port() {
  local p dev chip
  if [[ -n "$PORT" ]]; then
    echo "$PORT"
    return 0
  fi
  for p in /dev/tty.usbserial* /dev/tty.SLAB* /dev/ttyUSB* /dev/ttyACM* /dev/tty.usbmodem* /dev/cu.usbserial* /dev/cu.SLAB* /dev/cu.usbmodem* /dev/cu.usbserial*; do
    for dev in $p; do
      [[ -e "$dev" ]] || continue
      echo "Probing $dev..." >&2
      if python3 -m esptool --chip auto -p "$dev" -b 921600 --after no_reset flash_id 2>&1 | grep -q "Chip is ESP32-C6"; then
        echo "$dev"
        return 0
      fi
    done
  done
  return 1
}

PORT_FOUND="$(detect_c6_port || true)"
if [[ -z "$PORT_FOUND" ]]; then
  echo "Could not find an ESP32-C6 serial port. Connect the C6 to USB (Tab5 C6 download header + USB-TTL) and re-run." >&2
  exit 2
fi

echo "Using C6 port: $PORT_FOUND"
set -x
python3 -m esptool --chip esp32c6 -p "$PORT_FOUND" -b "$BAUD" write_flash 0x0 "$BIN_ABS"
set +x
echo "C6 flash complete. Power cycle the Tab5 and monitor the host logs."
