#!/usr/bin/env python3
"""Lane N4 per-unit NVS provisioning generator (NON-FLASHING, build-tree-free).

Produces a per-unit NVS partition binary from the placeholder CSV template
(``unit_nvs_template.csv``) using the ESP-IDF ``nvs_partition_gen.py`` tool. The
resulting ``.bin`` can be folded into a factory image by ``make_factory_image.py
--nvs <bin>`` or flashed by a human to the NVS offset (0x9000) on its own.

CAPTAIN DECISION D4 — UNDECIDED: the per-unit serial / SKU SCHEME is not yet
decided. This generator therefore uses a clearly-marked PLACEHOLDER template and
loud placeholder defaults. It must NOT be used to mint real production units until
D4 is resolved and the template is replaced with the agreed scheme. The template
namespace/key/value formats here are illustrative only.

DISCIPLINE (hard rules, mirrors the release tooling):
  * NON-FLASHING — generates a file on disk. NEVER runs write-flash and NEVER
    touches a serial port or device.
  * Does NOT read or modify the firmware build tree.
  * NEVER pushes anything and NEVER mints NVS keys (plaintext provisioning only).

Usage:
    python3 scripts/release/make_unit_nvs.py --serial K1-XXXX-0001 --sku PLACEHOLDER
    python3 scripts/release/make_unit_nvs.py --serial K1-XXXX-0001 --sku PH \\
        --calibration cal-rev-a --output build/unit-0001.nvs.bin

Exit: 0 on a generated binary; non-zero if the template or nvs_partition_gen.py
      cannot be resolved, or generation fails. It never flashes regardless.
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "scripts" / "release" / "unit_nvs_template.csv"

# NVS partition size from default_16MB.csv (nvs @ 0x9000, size 0x5000).
DEFAULT_NVS_SIZE = "0x5000"

# Loud placeholders so an un-argument'd run can never be mistaken for a real unit.
PLACEHOLDER_SERIAL = "PLACEHOLDER-SERIAL-D4-PENDING"
PLACEHOLDER_SKU = "PLACEHOLDER-SKU-D4-PENDING"

TOKENS = {
    "device_serial": "__DEVICE_SERIAL__",
    "sku": "__SKU__",
    "calibration": "__CALIBRATION__",
}


def resolve_python(override: str | None) -> str:
    """Resolve an interpreter that can run the ESP-IDF tool.

    nvs_partition_gen.py (this IDF vintage) imports ``distutils``, which Python
    3.12+ removed; it must run under the IDF/PlatformIO interpreter, not whatever
    ``python3`` happens to be on PATH. Order: --python override, the PlatformIO
    penv python, then the current interpreter (if it still ships distutils).
    """
    if override:
        return override
    import importlib.util

    penv = Path(os.environ.get("PLATFORMIO_CORE_DIR", Path.home() / ".platformio")) / "penv" / "bin" / "python"
    if penv.is_file():
        return str(penv)
    if importlib.util.find_spec("distutils") is not None:
        return sys.executable
    # Last resort: current interpreter; nvs_partition_gen will report the missing
    # distutils clearly rather than us guessing wrong.
    return sys.executable


def resolve_nvs_gen(override: str | None) -> Path:
    """Locate ESP-IDF nvs_partition_gen.py — override, IDF_PATH, then framework pkg."""
    if override:
        p = Path(override)
        if not p.is_file():
            raise SystemExit("make_unit_nvs: --nvs-gen not found: %s" % p)
        return p
    idf = os.environ.get("IDF_PATH")
    if idf:
        cand = Path(idf) / "components" / "nvs_flash" / "nvs_partition_generator" / "nvs_partition_gen.py"
        if cand.is_file():
            return cand
    pio_pkgs = Path(os.environ.get("PLATFORMIO_CORE_DIR", Path.home() / ".platformio")) / "packages"
    matches = sorted(glob.glob(str(
        pio_pkgs / "framework-espidf*" / "components" / "nvs_flash" / "nvs_partition_generator" / "nvs_partition_gen.py"
    )))
    if matches:
        return Path(matches[-1])
    raise SystemExit(
        "make_unit_nvs: could not locate nvs_partition_gen.py. Set IDF_PATH or pass "
        "--nvs-gen <path> (it ships in framework-espidf/components/nvs_flash/...)."
    )


def fill_template(values: dict[str, str | None]) -> str:
    """Substitute tokens in the template; drop comment lines and unset optional rows.

    Returns a clean CSV string (no ``#`` comments) suitable for nvs_partition_gen.py.
    A row whose token is left unset (value is None) is dropped — this is how the
    optional ``calibration`` field is omitted when not supplied.
    """
    if not TEMPLATE.is_file():
        raise SystemExit("make_unit_nvs: missing template: %s" % TEMPLATE)
    out_lines: list[str] = []
    for raw in TEMPLATE.read_text(encoding="utf-8").splitlines():
        if raw.strip().startswith("#") or not raw.strip():
            continue
        line = raw
        drop = False
        for field, token in TOKENS.items():
            if token in line:
                value = values.get(field)
                if value is None:
                    drop = True
                    break
                line = line.replace(token, value)
        if drop:
            continue
        out_lines.append(line)
    # Any residual unfilled token means the template carries a field we did not map.
    residual = re.search(r"__[A-Z_]+__", "\n".join(out_lines))
    if residual:
        raise SystemExit(
            "make_unit_nvs: template has an unmapped token %s — update TOKENS in this script."
            % residual.group(0)
        )
    return "\n".join(out_lines) + "\n"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Generate a per-unit K1 NVS partition (non-flashing).")
    parser.add_argument("--serial", default=PLACEHOLDER_SERIAL,
                        help="device serial (D4 scheme UNDECIDED — placeholder if omitted)")
    parser.add_argument("--sku", default=PLACEHOLDER_SKU,
                        help="device SKU (D4 scheme UNDECIDED — placeholder if omitted)")
    parser.add_argument("--calibration", default=None,
                        help="optional calibration tag (row omitted if not supplied)")
    parser.add_argument("--output", type=Path, default=None,
                        help="output .bin (default: ./k1_unit_<serial>.nvs.bin)")
    parser.add_argument("--size", default=DEFAULT_NVS_SIZE,
                        help="NVS partition size (default 0x5000 from default_16MB.csv)")
    parser.add_argument("--nvs-gen", default=None, help="override nvs_partition_gen.py path")
    parser.add_argument("--python", default=None,
                        help="interpreter to run nvs_partition_gen.py (default: PlatformIO penv python)")
    parser.add_argument("--keep-csv", action="store_true", help="keep the generated intermediate CSV")
    args = parser.parse_args(argv)

    is_placeholder = (args.serial == PLACEHOLDER_SERIAL) or (args.sku == PLACEHOLDER_SKU)

    safe_serial = re.sub(r"[^A-Za-z0-9._-]", "_", args.serial)
    output = args.output or (Path.cwd() / ("k1_unit_%s.nvs.bin" % safe_serial))

    csv_text = fill_template({
        "device_serial": args.serial,
        "sku": args.sku,
        "calibration": args.calibration,
    })

    nvs_gen = resolve_nvs_gen(args.nvs_gen)
    python = resolve_python(args.python)

    print("=" * 72)
    print("K1 PER-UNIT NVS GENERATOR (non-flashing — writes a partition file)")
    print("=" * 72)
    if is_placeholder:
        print("  !! PLACEHOLDER RUN — Captain decision D4 (serial/SKU scheme) UNDECIDED.")
        print("  !! Do NOT mint real production units from this output.")
    print("  serial       : %s" % args.serial)
    print("  sku          : %s" % args.sku)
    print("  calibration  : %s" % (args.calibration if args.calibration is not None else "(omitted)"))
    print("  nvs size     : %s" % args.size)
    print("  nvs_gen      : %s" % nvs_gen)
    print("  python       : %s" % python)
    print("  output       : %s" % output)
    print("-" * 72)

    # Write the filled CSV to a temp file; hand it to nvs_partition_gen.py. The only
    # subprocess this script runs is the NVS partition generator — never a write-flash.
    tmp = tempfile.NamedTemporaryFile(
        "w", suffix=".csv", prefix="k1_unit_nvs_", delete=False, encoding="utf-8",
        dir=str(output.parent if output.parent.exists() else Path.cwd()),
    )
    try:
        tmp.write(csv_text)
        tmp.close()
        gen_cmd = [python, str(nvs_gen), "generate", tmp.name, str(output), str(args.size)]
        print("nvs_partition_gen command:")
        print("  " + " ".join(gen_cmd))
        try:
            subprocess.run(gen_cmd, check=True, cwd=str(ROOT))
        except FileNotFoundError as exc:
            raise SystemExit("make_unit_nvs: could not run nvs_partition_gen.py (%s)." % exc)
        except subprocess.CalledProcessError as exc:
            raise SystemExit("make_unit_nvs: nvs_partition_gen.py failed (exit %d)." % exc.returncode)
    finally:
        if args.keep_csv:
            print("  intermediate CSV kept at: %s" % tmp.name)
        else:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass

    print("-" * 72)
    print("Generated NVS partition: %s" % output)
    print()
    print("Fold into a factory image:")
    print("  python3 scripts/release/make_factory_image.py --nvs %s" % output)
    print()
    print("Or a human may flash it alone to the NVS offset (verify chip-ID first):")
    print("  esptool --chip esp32s3 --port <PORT> write_flash 0x9000 %s" % output)
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
