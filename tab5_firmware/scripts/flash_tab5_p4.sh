#!/usr/bin/env bash
set -euo pipefail

# Flashing helper for ESP32-P4 (Tab5) using PlatformIO build artifacts.
#
# Usage:
#   scripts/flash_tab5_p4.sh [--port /dev/tty.usbmodemXXXX] [--baud 1500000]
#
# Defaults:
#   PORT: auto-detected (tty.usbmodem*, tty.usbserial*, tty.SLAB*)
#   BAUD: 1500000

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJ_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
BUILD_DIR="${PROJ_DIR}/.pio/build/tab5_p4"
FLASHER_JSON="${BUILD_DIR}/flasher_args.json"

PORT=""
BAUD="1500000"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --port)
      PORT="$2"; shift 2;;
    --baud)
      BAUD="$2"; shift 2;;
    -h|--help)
      grep '^#' "$0" | sed -e 's/^# \{0,1\}//'; exit 0;;
    *)
      echo "Unknown arg: $1" >&2; exit 1;;
  esac
done

if [[ -z "$PORT" ]]; then
  # Try common macOS/Linux patterns
  for pat in /dev/tty.usbmodem* /dev/tty.usbserial* /dev/tty.SLAB* /dev/ttyACM* /dev/ttyUSB*; do
    match=( $pat )
    if [[ -e "${match[0]:-}" ]]; then
      PORT="${match[0]}"; break
    fi
  done
fi

if [[ -z "$PORT" ]]; then
  echo "Error: Could not auto-detect serial port. Use --port." >&2
  exit 1
fi

echo "Using port: $PORT"
echo "Using baud: $BAUD"

# Gather flash arguments and image list
FLASH_ARGS=()
WRITE_ARGS=()
FLASH_IMAGES=()
FLASH_OFFSETS=()

has_offset() {
  local target="$1"
  if (( ${#FLASH_OFFSETS[@]} == 0 )); then
    return 1
  fi
  for present in "${FLASH_OFFSETS[@]}"; do
    [[ "$present" == "$target" ]] && return 0
  done
  return 1
}

add_image_if_present() {
  local offset="$1" path="$2"
  if [[ -f "$path" ]]; then
    FLASH_IMAGES+=("$offset" "$path")
    FLASH_OFFSETS+=("$offset")
    echo "Auto-adding $path @ $offset" >&2
    return 0
  fi
  return 1
}

if [[ -f "$FLASHER_JSON" ]]; then
  FLASH_PLAN=()
  while IFS= read -r line; do
    FLASH_PLAN+=("$line")
  done < <(python3 - "$FLASHER_JSON" "$BUILD_DIR" <<'PY'
import json, os, sys

flasher_path = sys.argv[1]
build_dir = sys.argv[2]
with open(flasher_path, 'r', encoding='utf-8') as fh:
    data = json.load(fh)

for arg in data.get('write_flash_args', []):
    print('WARG', arg)

extra = data.get('extra_esptool_args', {})
for key, value in extra.items():
    if key == 'chip':
        continue
    if key == 'stub':
        if not value:
            print('ARG', '--no-stub')
        continue
    flag = f"--{key.replace('_', '-')}"
    if isinstance(value, bool):
        if value:
            print('ARG', flag)
    elif value is not None:
        print('ARGKV', flag, str(value))

flash_files = data.get('flash_files', {})
for addr in sorted(flash_files, key=lambda k: int(k, 16)):
    rel_path = flash_files[addr]
    abs_path = os.path.normpath(os.path.join(build_dir, rel_path))
    print('IMG', addr, abs_path)
PY
  )

  for entry in "${FLASH_PLAN[@]}"; do
    set -- $entry
    case "$1" in
      ARG)
        FLASH_ARGS+=("$2")
        ;;
      ARGKV)
        FLASH_ARGS+=("$2" "$3")
        ;;
      WARG)
        WRITE_ARGS+=("$2")
        ;;
      WARGKV)
        WRITE_ARGS+=("$2" "$3")
        ;;
      IMG)
        addr="$2"
        img="$3"
        if [[ -f "$img" ]]; then
          FLASH_IMAGES+=("$addr" "$img")
          FLASH_OFFSETS+=("$addr")
        else
          echo "Warning: skipping missing image $img" >&2
        fi
        ;;
    esac
  done
  set --
else
  # Fallback for legacy builds without flasher_args.json
  FLASH_ARGS+=(--before default_reset --after hard_reset)
  WRITE_ARGS+=(--flash_mode qio --flash_size 16MB --flash_freq 80m)
  default_images=(
    "0x2000 ${BUILD_DIR}/bootloader/bootloader.bin"
    "0x2000 ${BUILD_DIR}/bootloader.bin"
    "0x8000 ${BUILD_DIR}/partition_table/partition-table.bin"
    "0x8000 ${BUILD_DIR}/partitions.bin"
    "0x10000 ${BUILD_DIR}/firmware.bin"
    "0x10000 ${BUILD_DIR}/deck.bin"
  )
  seen_offsets=()
  for spec in "${default_images[@]}"; do
    offset="${spec%% *}"
    path="${spec#* }"
    if [[ ! -f "$path" ]]; then
      continue
    fi
    skip=false
    for existing in "${seen_offsets[@]}"; do
      if [[ "$existing" == "$offset" ]]; then
        skip=true
        break
      fi
    done
    $skip && continue
    seen_offsets+=("$offset")
    FLASH_IMAGES+=("$offset" "$path")
    FLASH_OFFSETS+=("$offset")
  done
fi

has_offset "0x8000" || add_image_if_present "0x8000" "${BUILD_DIR}/partition_table/partition-table.bin" || add_image_if_present "0x8000" "${BUILD_DIR}/partitions.bin"
has_offset "0x10000" || add_image_if_present "0x10000" "${BUILD_DIR}/firmware.bin" || add_image_if_present "0x10000" "${BUILD_DIR}/deck.bin"
has_offset "0x2000" || add_image_if_present "0x2000" "${BUILD_DIR}/bootloader/bootloader.bin" || add_image_if_present "0x2000" "${BUILD_DIR}/bootloader.bin" || true

if (( ${#FLASH_IMAGES[@]} == 0 )); then
  echo "No flash images found. Build first: (cd ${PROJ_DIR} && pio run -e tab5_p4)" >&2
  exit 1
fi

# Prefer esptool.py from PATH, then the repo-vendored Python shim used by
# PlatformIO, then Python module fallback.
if command -v esptool.py >/dev/null 2>&1; then
  ESPTOOL=( esptool.py )
elif command -v esptool >/dev/null 2>&1; then
  ESPTOOL=( esptool )
elif [[ -x "${PROJ_DIR}/vendor/python/python" && -f "${PROJ_DIR}/vendor/pio_packages/tool-esptoolpy/esptool.py" ]]; then
  ESPTOOL=( "${PROJ_DIR}/vendor/python/python" "${PROJ_DIR}/vendor/pio_packages/tool-esptoolpy/esptool.py" )
elif [[ -x "${HOME}/.platformio/penv/bin/python" && -f "${PROJ_DIR}/vendor/pio_packages/tool-esptoolpy/esptool.py" ]]; then
  ESPTOOL=( "${HOME}/.platformio/penv/bin/python" "${PROJ_DIR}/vendor/pio_packages/tool-esptoolpy/esptool.py" )
else
  ESPTOOL=( python -m esptool )
fi

set -x
"${ESPTOOL[@]}" \
  --chip esp32p4 \
  --port "$PORT" \
  --baud "$BAUD" \
  "${FLASH_ARGS[@]}" \
  write_flash -z \
  "${WRITE_ARGS[@]}" \
  "${FLASH_IMAGES[@]}"
set +x

echo "Flash complete. Open a serial monitor to verify boot logs."
