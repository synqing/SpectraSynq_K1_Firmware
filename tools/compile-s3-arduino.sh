#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKETCH_DIR="${ROOT_DIR}/SPECTRASYNQ_K1_FIRMWARE"
BUILD_PATH="${BUILD_PATH:-/tmp/sb-s3-build}"

FQBN="${FQBN:-esp32:esp32:esp32s3:USBMode=hwcdc,CDCOnBoot=cdc,MSCOnBoot=default,DFUOnBoot=default,UploadMode=default,CPUFreq=240,FlashMode=qio,FlashSize=8M,PartitionScheme=min_spiffs,DebugLevel=none,PSRAM=enabled,LoopCore=1,EventsCore=1,EraseFlash=none}"

rm -rf "${BUILD_PATH}"

arduino-cli compile \
  --clean \
  --fqbn "${FQBN}" \
  --libraries "${ROOT_DIR}/libraries" \
  --libraries "${HOME}/Documents/Arduino/libraries" \
  --build-path "${BUILD_PATH}" \
  "${SKETCH_DIR}"
