#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKETCH_DIR="${ROOT_DIR}/SPECTRASYNQ_K1_FIRMWARE"
BUILD_PATH="${BUILD_PATH:-/tmp/sb-k1-build}"

FQBN="${FQBN:-esp32:esp32:esp32s3:USBMode=hwcdc,CDCOnBoot=cdc,MSCOnBoot=default,DFUOnBoot=default,UploadMode=default,CPUFreq=240,FlashMode=qio,FlashSize=8M,PartitionScheme=min_spiffs,DebugLevel=none,PSRAM=enabled,LoopCore=1,EventsCore=1,EraseFlash=none}"
K1_FLAGS="${K1_FLAGS:--DSB_K1_HARDWARE -DENABLE_VP_PERF_AUDIT=1 -DFASTLED_RMT_BUILTIN_DRIVER=0 -DFASTLED_RMT_MAX_CHANNELS=4 -DFASTLED_RMT_MAX_TICKS_FOR_GTX_SEM=100 -DFASTLED_ESP32_FLASH_LOCK=0 -DFASTLED_INTERRUPT_RETRY_COUNT=0 -DBOARD_HAS_PSRAM -O3 -ffast-math}"

rm -rf "${BUILD_PATH}"

arduino-cli compile \
  --clean \
  --fqbn "${FQBN}" \
  --build-property "compiler.c.extra_flags=${K1_FLAGS}" \
  --build-property "compiler.cpp.extra_flags=${K1_FLAGS}" \
  --libraries "${ROOT_DIR}/libraries" \
  --libraries "${HOME}/Documents/Arduino/libraries" \
  --build-path "${BUILD_PATH}" \
  "${SKETCH_DIR}"
