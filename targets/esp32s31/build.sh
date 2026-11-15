#!/usr/bin/env bash
# Build one K1 profile for the ESP32-S31 (plain ESP-IDF v6.1). BUILD ONLY: never flashes.
#
#   targets/esp32s31/build.sh k1_fe        # product image
#   targets/esp32s31/build.sh k1_fe_emu    # emulator replay image
#
# The profile name is a PlatformIO env: its sources and flags come from platformio.ini.
# Outputs: targets/esp32s31/build/<env>/ (ESP-IDF layout) and build/<env>/stage/ with the
# file names tools/esp_emulator expects (firmware.elf/.bin, bootloader.bin, partitions.bin).
# K1_S31_IDF_PATH overrides the ESP-IDF checkout (default ~/esp/esp-idf-v6.1).
set -euo pipefail

ENV_NAME="${1:?usage: build.sh <pio env>}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IDF="${K1_S31_IDF_PATH:-$HOME/esp/esp-idf-v6.1}"
[ -f "$IDF/export.sh" ] || { echo "build.sh: no ESP-IDF at $IDF" >&2; exit 3; }

# ESP-IDF made its Python environment with the interpreter that ran install.sh. Point
# export.sh at that environment so a different python3 on PATH cannot break it.
if [ -z "${IDF_PYTHON_ENV_PATH:-}" ]; then
  IDF_PYTHON_ENV_PATH="$(ls -d "$HOME"/.espressif/python_env/idf6.1_py*_env 2>/dev/null | head -1 || true)"
  export IDF_PYTHON_ENV_PATH
fi
# shellcheck disable=SC1091
. "$IDF/export.sh" >/dev/null

BUILD="$HERE/build/$ENV_NAME"
cd "$HERE"
idf.py --preview -B "$BUILD" -DK1_PROFILE="$ENV_NAME" -DSDKCONFIG="$BUILD/sdkconfig" build

STAGE="$BUILD/stage"
mkdir -p "$STAGE"
stage() {  # copy-on-write clone where the file system supports it
  rm -f "$STAGE/$2"
  cp -c "$BUILD/$1" "$STAGE/$2" 2>/dev/null || cp "$BUILD/$1" "$STAGE/$2"
}
stage k1_s31.elf firmware.elf
stage k1_s31.bin firmware.bin
stage bootloader/bootloader.bin bootloader.bin
stage partition_table/partition-table.bin partitions.bin
echo "build.sh: $ENV_NAME -> $STAGE"
