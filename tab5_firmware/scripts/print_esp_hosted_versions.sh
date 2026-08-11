#!/usr/bin/env bash
set -euo pipefail

# Print host-side ESP-Hosted / WiFi Remote versions detected in vendor libs

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VER_FILE="${ROOT_DIR}/vendor/pio_packages/framework-arduinoespressif32-libs/versions.txt"

if [[ ! -f "$VER_FILE" ]]; then
  echo "versions.txt not found at: $VER_FILE" >&2
  exit 1
fi

echo "Detected host stack (from versions.txt):"
awk '
  $1 ~ /^esp-idf:/ {print "-", $0}
  $1 ~ /^espressif__esp_hosted:/ {print "-", $0}
  $1 ~ /^espressif__esp_wifi_remote:/ {print "-", $0}
' "$VER_FILE"

