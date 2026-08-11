#!/usr/bin/env bash
set -euo pipefail

# Build and flash ESP-Hosted "slave" firmware for ESP32-C6 over SDIO (Tab5 co-processor).
#
# This helper will:
#  - Clone esp-hosted at a specified tag/branch (default: v2.0.13)
#  - Locate an ESP-IDF project for ESP32-C6 + SDIO transport
#  - Build it with ESP-IDF (expects idf.py available or IDF_PATH set)
#  - Flash it to the target port
#
# Usage:
#   scripts/build_flash_c6_esp_hosted.sh \
#     [--port /dev/ttyACM0] [--baud 1500000] [--branch v2.0.13] \
#     [--repo-dir <dir>] [--project-dir <dir>] [--idf-path <dir>] [--dry-run]
#
# Notes:
#  - You must have ESP-IDF v5.4 installed and usable (via idf.py in PATH or export.sh from --idf-path).
#  - If detection fails, pass --project-dir to the specific ESP-Hosted slave project directory.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DECK_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
WORK_DIR="${DECK_DIR}/.thirdparty"
REPO_DIR=""
PROJECT_DIR=""
IDF_PATH_IN=""
PORT=""
BAUD="1500000"
BRANCH="v2.0.13"
DRY_RUN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --port) PORT="$2"; shift 2;;
    --baud) BAUD="$2"; shift 2;;
    --branch) BRANCH="$2"; shift 2;;
    --repo-dir) REPO_DIR="$2"; shift 2;;
    --project-dir) PROJECT_DIR="$2"; shift 2;;
    --idf-path) IDF_PATH_IN="$2"; shift 2;;
    --dry-run) DRY_RUN=1; shift 1;;
    -h|--help)
      grep '^#' "$0" | sed -e 's/^# \{0,1\}//'; exit 0;;
    *) echo "Unknown arg: $1" >&2; exit 1;;
  esac
done

mkdir -p "$WORK_DIR"

die() { echo "Error: $*" >&2; exit 1; }
say() { echo "[c6] $*"; }
run() { echo "+" "$@"; (( DRY_RUN )) || "$@"; }

# Ensure IDF environment is available
ensure_idf() {
  if command -v idf.py >/dev/null 2>&1; then
    say "Found idf.py in PATH"
    return 0
  fi
  if [[ -n "$IDF_PATH_IN" ]]; then
    local exp="$IDF_PATH_IN/export.sh"
    [[ -f "$exp" ]] || die "export.sh not found at $exp"
    say "Sourcing $exp"
    # shellcheck disable=SC1090
    source "$exp"
    command -v idf.py >/dev/null 2>&1 || die "idf.py not available after sourcing $exp"
    return 0
  fi
  if [[ -n "${IDF_PATH:-}" && -f "${IDF_PATH}/export.sh" ]]; then
    say "Sourcing ${IDF_PATH}/export.sh"
    # shellcheck disable=SC1090
    source "${IDF_PATH}/export.sh"
    command -v idf.py >/dev/null 2>&1 || die "idf.py not available after sourcing IDF_PATH"
    return 0
  fi
  die "ESP-IDF is not available. Install v5.4 and re-run, or pass --idf-path <dir>."
}

# Clone esp-hosted if needed
prepare_repo() {
  if [[ -n "$REPO_DIR" ]]; then
    [[ -d "$REPO_DIR/.git" ]] || die "--repo-dir provided but .git not found: $REPO_DIR"
    say "Using provided repo-dir: $REPO_DIR"
    return 0
  fi
  REPO_DIR="${WORK_DIR}/esp-hosted-${BRANCH}"
  if [[ -d "$REPO_DIR/.git" ]]; then
    say "Using existing repo: $REPO_DIR"
    return 0
  fi
  say "Cloning esp-hosted@$BRANCH into $REPO_DIR"
  run git clone --branch "$BRANCH" --depth 1 https://github.com/espressif/esp-hosted.git "$REPO_DIR"
}

# Try to detect the ESP32-C6 SDIO slave project
detect_project_dir() {
  if [[ -n "$PROJECT_DIR" ]]; then
    [[ -f "$PROJECT_DIR/CMakeLists.txt" ]] || die "--project-dir has no CMakeLists.txt: $PROJECT_DIR"
    say "Using provided project-dir: $PROJECT_DIR"
    return 0
  fi

  say "Searching for ESP32-C6 SDIO slave project under $REPO_DIR"
  # Prefer directories containing both CMakeLists.txt and Kconfig (IDF style)
  local candidates
  IFS=$'\n' read -r -d '' -a candidates < <(
    find "$REPO_DIR" -maxdepth 5 -type f -name CMakeLists.txt -print0 | xargs -0 -n1 dirname | sort -u && printf '\0'
  ) || true

  # Filter for likely slave/SDIO/C6 hints
  local best=""
  for d in "${candidates[@]:-}"; do
    [[ -d "$d" ]] || continue
    if grep -R "ESP32C6\|esp32c6" -n "$d" >/dev/null 2>&1; then
      if grep -R "TRANSPORT_SDIO\|esp_hosted.*sdio" -n "$d" >/dev/null 2>&1; then
        best="$d"; break
      fi
    fi
  done
  if [[ -z "$best" ]]; then
    # Fallback: any project mentioning sdio + slave
    for d in "${candidates[@]:-}"; do
      [[ -d "$d" ]] || continue
      if grep -R "slave\|sdio" -n "$d" >/dev/null 2>&1; then
        best="$d"; break
      fi
    done
  fi
  [[ -n "$best" ]] || die "Could not auto-detect project dir. Pass --project-dir explicitly."
  PROJECT_DIR="$best"
  say "Auto-detected project-dir: $PROJECT_DIR"
}

# Determine serial port if not provided
detect_port() {
  if [[ -n "$PORT" ]]; then return 0; fi
  for pat in /dev/tty.usbmodem* /dev/tty.usbserial* /dev/tty.SLAB* /dev/ttyACM* /dev/ttyUSB*; do
    set +e
    match=( $pat )
    set -e
    if [[ -e "${match[0]:-}" ]]; then
      PORT="${match[0]}"; break
    fi
  done
  [[ -n "$PORT" ]] || die "Could not auto-detect serial port. Use --port."
}

main() {
  ensure_idf
  prepare_repo
  detect_project_dir
  detect_port

  say "Setting target: esp32c6"
  ( cd "$PROJECT_DIR" && run idf.py set-target esp32c6 )

  say "Configuring (menuconfig can be used manually if needed)"
  # Build directly; users can run idf.py menuconfig separately if needed
  ( cd "$PROJECT_DIR" && run idf.py build )

  say "Flashing @ $PORT (baud $BAUD)"
  ( cd "$PROJECT_DIR" && run idf.py -p "$PORT" -b "$BAUD" flash )

  say "Done. Power-cycle Tab5 and monitor the host logs for successful STA connect."
}

main "$@"

