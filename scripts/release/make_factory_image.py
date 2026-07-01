#!/usr/bin/env python3
"""Lane N4 factory-image assembler (READ-ONLY of the build tree, NON-FLASHING).

Combines the four K1 boot artefacts produced by ``pio run -e k1_hardware`` —
bootloader, partition table, OTA-data (``boot_app0``) and the application image —
into a single flashable factory image via ``esptool merge_bin``. Optionally folds
in a provisioned NVS partition (see ``make_unit_nvs.py``) at the partition-table
NVS offset so a unit boots fully provisioned from one write.

DISCIPLINE (hard rules, mirrors ``make_release.py``):
  * READ-ONLY of the build tree — it only reads the ``*.bin`` artefacts; it never
    rebuilds and never edits firmware.
  * NON-FLASHING — it assembles a file on disk. It NEVER runs write-flash and
    NEVER touches a serial port or device. After assembling, it PRINTS the exact
    esptool write-flash command for a human to run by hand.
  * NEVER pushes anything.

Flash layout (arduino-esp32 / ESP32-S3, default_16MB.csv):
    0x0      bootloader.bin     (S3 bootloader offset is 0x0, not 0x1000)
    0x8000   partitions.bin     (partition table)
    0x9000   <nvs.bin>          (optional — only when --nvs is supplied)
    0xe000   boot_app0.bin      (OTA-data, from the arduino-esp32 framework pkg)
    0x10000  firmware.bin       (application)

Usage:
    python3 scripts/release/make_factory_image.py
    python3 scripts/release/make_factory_image.py --nvs build/unit-0001.nvs.bin
    python3 scripts/release/make_factory_image.py --build-dir .pio/build/k1_hardware

Exit: 0 on a clean assembled image; non-zero if a required artefact is missing or
      esptool fails. It never flashes regardless of exit code.
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLATFORMIO_INI = ROOT / "platformio.ini"
DEFAULT_ENV = "k1_hardware"

# Fixed flash offsets — these are the arduino-esp32 / default_16MB.csv layout for
# the ESP32-S3. NVS comes straight from the partition CSV (nvs @ 0x9000, 0x5000).
OFFSET_BOOTLOADER = 0x0
OFFSET_PARTITIONS = 0x8000
OFFSET_NVS = 0x9000
OFFSET_BOOT_APP0 = 0xE000
OFFSET_FIRMWARE = 0x10000

CHIP = "esp32s3"


def _ini_section(text: str, name: str) -> str:
    """Return the body of [<name>] up to the next section header."""
    m = re.search(r"^\[%s\]\s*$" % re.escape(name), text, re.MULTILINE)
    if not m:
        return ""
    rest = text[m.end():]
    nxt = re.search(r"^\[", rest, re.MULTILINE)
    return rest[: nxt.start()] if nxt else rest


def _ini_value(section: str, key: str, default: str) -> str:
    m = re.search(r"^\s*%s\s*=\s*(\S+)" % re.escape(key), section, re.MULTILINE)
    return m.group(1).strip() if m else default


def flash_params() -> tuple[str, str, str]:
    """Resolve (flash_mode, flash_freq, flash_size) from [env:k1_hardware].

    Faithful to the env's configured flash so the merged bootloader header is not
    silently rewritten. Sensible arduino-esp32 S3 defaults if a key is absent.
    """
    try:
        text = PLATFORMIO_INI.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ("dio", "80m", "16MB")
    section = _ini_section(text, "env:%s" % DEFAULT_ENV)
    mode = _ini_value(section, "board_build.flash_mode", "dio")
    size = _ini_value(section, "board_build.flash_size", "16MB")
    freq = _ini_value(section, "board_build.f_flash", "")
    # f_flash is given in Hz (e.g. 80000000L) when present; otherwise default 80m.
    if freq:
        digits = re.sub(r"\D", "", freq)
        freq = "%dm" % (int(digits) // 1_000_000) if digits else "80m"
    else:
        freq = "80m"
    return (mode, freq, size)


def default_build_dir() -> Path:
    """Mirror PlatformIO's build-dir resolution, honouring PLATFORMIO_BUILD_DIR."""
    base = os.environ.get("PLATFORMIO_BUILD_DIR")
    base_path = Path(base) if base else (ROOT / ".pio" / "build")
    return base_path / DEFAULT_ENV


def resolve_boot_app0(override: str | None) -> Path:
    """Locate boot_app0.bin (OTA-data) — override, then the framework package."""
    if override:
        p = Path(override)
        if not p.is_file():
            raise SystemExit("make_factory_image: --boot-app0 not found: %s" % p)
        return p
    pio_pkgs = Path(os.environ.get("PLATFORMIO_CORE_DIR", Path.home() / ".platformio")) / "packages"
    matches = sorted(
        glob.glob(str(pio_pkgs / "framework-arduinoespressif32*" / "tools" / "partitions" / "boot_app0.bin"))
    )
    if not matches:
        raise SystemExit(
            "make_factory_image: could not locate boot_app0.bin in the arduino-esp32 "
            "framework package. Pass --boot-app0 <path> explicitly."
        )
    return Path(matches[-1])


def resolve_esptool(override: str | None) -> list[str]:
    """Return the argv prefix that invokes esptool (override / module / package)."""
    if override:
        return [override]
    # Prefer the importable module so we follow PlatformIO's pinned esptool.
    try:
        import esptool  # noqa: F401

        return [sys.executable, "-m", "esptool"]
    except Exception:
        pass
    pio_pkgs = Path(os.environ.get("PLATFORMIO_CORE_DIR", Path.home() / ".platformio")) / "packages"
    matches = sorted(glob.glob(str(pio_pkgs / "tool-esptoolpy*" / "esptool.py")))
    if matches:
        return [sys.executable, matches[-1]]
    return ["esptool.py"]


def require(path: Path, label: str) -> Path:
    if not path.is_file():
        raise SystemExit(
            "make_factory_image: missing %s: %s\n"
            "  Build the production target first:  pio run -e %s"
            % (label, path, DEFAULT_ENV)
        )
    return path


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Assemble a K1 flashable factory image (non-flashing).")
    parser.add_argument("--build-dir", type=Path, default=None,
                        help="env build dir (default: $PLATFORMIO_BUILD_DIR/k1_hardware or .pio/build/k1_hardware)")
    parser.add_argument("--output", type=Path, default=None,
                        help="output image path (default: <build-dir>/k1_factory.bin)")
    parser.add_argument("--nvs", type=Path, default=None,
                        help="optional provisioned NVS partition .bin to fold in at 0x9000")
    parser.add_argument("--boot-app0", default=None, help="override boot_app0.bin path")
    parser.add_argument("--esptool", default=None, help="override esptool invocation")
    parser.add_argument("--dry-run", action="store_true",
                        help="print the merge_bin command without running it")
    args = parser.parse_args(argv)

    build_dir = args.build_dir or default_build_dir()
    bootloader = require(build_dir / "bootloader.bin", "bootloader")
    partitions = require(build_dir / "partitions.bin", "partition table")
    firmware = require(build_dir / "firmware.bin", "application image")
    boot_app0 = resolve_boot_app0(args.boot_app0)

    nvs = None
    if args.nvs is not None:
        nvs = require(args.nvs, "provisioned NVS partition")

    output = args.output or (build_dir / "k1_factory.bin")
    mode, freq, size = flash_params()
    esptool = resolve_esptool(args.esptool)

    # merge_bin assembles a file; it does NOT touch any device. This is the only
    # subprocess this script runs, and it is never a write-flash.
    merge_cmd = esptool + [
        "--chip", CHIP, "merge_bin", "-o", str(output),
        "--flash_mode", mode, "--flash_freq", freq, "--flash_size", size,
        "0x%x" % OFFSET_BOOTLOADER, str(bootloader),
        "0x%x" % OFFSET_PARTITIONS, str(partitions),
    ]
    if nvs is not None:
        merge_cmd += ["0x%x" % OFFSET_NVS, str(nvs)]
    merge_cmd += [
        "0x%x" % OFFSET_BOOT_APP0, str(boot_app0),
        "0x%x" % OFFSET_FIRMWARE, str(firmware),
    ]

    print("=" * 72)
    print("K1 FACTORY IMAGE ASSEMBLER (read-only build tree — never flashes)")
    print("=" * 72)
    print("  env          : %s" % DEFAULT_ENV)
    print("  build dir    : %s" % build_dir)
    print("  bootloader   : 0x%05x  %s" % (OFFSET_BOOTLOADER, bootloader))
    print("  partitions   : 0x%05x  %s" % (OFFSET_PARTITIONS, partitions))
    if nvs is not None:
        print("  nvs          : 0x%05x  %s" % (OFFSET_NVS, nvs))
    else:
        print("  nvs          : (none — unprovisioned image; provision at first boot)")
    print("  boot_app0    : 0x%05x  %s" % (OFFSET_BOOT_APP0, boot_app0))
    print("  firmware     : 0x%05x  %s" % (OFFSET_FIRMWARE, firmware))
    print("  flash        : mode=%s freq=%s size=%s" % (mode, freq, size))
    print("  output       : %s" % output)
    print("-" * 72)
    print("merge_bin command:")
    print("  " + " ".join(merge_cmd))

    if args.dry_run:
        print("-" * 72)
        print("--dry-run: image NOT assembled.")
        return 0

    try:
        subprocess.run(merge_cmd, check=True, cwd=str(ROOT))
    except FileNotFoundError as exc:
        raise SystemExit("make_factory_image: esptool not runnable (%s). Pass --esptool." % exc)
    except subprocess.CalledProcessError as exc:
        raise SystemExit("make_factory_image: esptool merge_bin failed (exit %d)." % exc.returncode)

    print("-" * 72)
    print("Assembled factory image: %s" % output)
    print()
    print("HUMAN ACTION — verify chip-ID is the intended unit, THEN flash by hand")
    print("(this script will NOT flash). Identity is chip-ID, never the port:")
    print()
    print("  %s --chip %s --port <PORT> write_flash 0x0 %s"
          % (" ".join(esptool), CHIP, output))
    print()
    print("  Confirm 'Hash of data verified' + 'Hard resetting' before unplugging.")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
