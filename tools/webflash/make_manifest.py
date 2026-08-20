#!/usr/bin/env python3
"""K1 web-flasher manifest generator.

Reads built PlatformIO images for the curated env list, copies them into
tools/webflash/firmware/<env>/, and writes tools/webflash/manifest.json with
offsets taken from the ACTUAL partition table binary (never hardcoded).

Usage (from anywhere):
    python3 tools/webflash/make_manifest.py            # curated envs
    python3 tools/webflash/make_manifest.py --envs k1_main_rpl_im69d,k1_hardware

The resulting folder (index.html + manifest.json + firmware/ + assets/) is
self-contained: serve it locally (python3 -m http.server) or push it verbatim
to a public GitHub Pages repo — the manifest uses relative paths only.
"""

import argparse
import glob
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import sys
from datetime import datetime, timezone

# ── Curated env list (Captain-ruled 2026-08-18). Add envs here or via --envs.
CURATED_ENVS = [
    "k1_main_rpl_im69d",
]

LABELS = {
    "k1_hardware": "K1 Main (k1_hardware)",
    "k1_main_rpl_im69d": "K1 Main RPL — IM69D (k1_main_rpl_im69d)",
}

# ESP32-S3 ROM constants (chip-fixed, not project-tunable).
BOOTLOADER_OFFSET = 0x0
PARTITION_TABLE_OFFSET = 0x8000

WEBFLASH_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(WEBFLASH_DIR, "..", ".."))


def md5_of(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_partition_table(path):
    """Parse an ESP-IDF partition table binary into a list of entries."""
    sub_app = {0x00: "factory", 0x10: "ota_0", 0x11: "ota_1", 0x20: "test"}
    sub_data = {0x00: "otadata", 0x01: "phy", 0x02: "nvs", 0x03: "coredump",
                0x81: "fat", 0x82: "spiffs", 0x83: "littlefs"}
    entries = []
    data = open(path, "rb").read()
    for i in range(0, len(data), 32):
        e = data[i:i + 32]
        if e[:2] != b"\xaaP":
            continue
        ptype, subtype = e[2], e[3]
        off, size = struct.unpack("<I", e[4:8])[0], struct.unpack("<I", e[8:12])[0]
        name = e[12:28].rstrip(b"\x00").decode()
        sub = (sub_app if ptype == 0 else sub_data).get(subtype, hex(subtype))
        entries.append({"name": name, "type": "app" if ptype == 0 else "data",
                        "subtype": sub, "offset": off, "size": size})
    return entries


def find_boot_app0():
    """Prefer the framework's boot_app0.bin; fall back to the vendored copy."""
    candidates = glob.glob(os.path.expanduser(
        "~/.platformio/packages/framework-arduinoespressif32*/tools/partitions/boot_app0.bin"))
    vendored = os.path.join(WEBFLASH_DIR, "assets", "boot_app0.bin")
    for c in candidates + [vendored]:
        if os.path.isfile(c) and os.path.getsize(c) == 8192:
            return c
    sys.exit("ERROR: boot_app0.bin not found (framework package or assets/boot_app0.bin).")


def firmware_version():
    """Parse FIRMWARE_VERSION from the source of truth (system/constants.h)."""
    path = os.path.join(PROJECT_ROOT, "SPECTRASYNQ_K1_FIRMWARE", "system", "constants.h")
    try:
        with open(path) as f:
            for line in f:
                m = re.match(r"\s*#define\s+FIRMWARE_VERSION\s+(\d+)", line)
                if m:
                    return int(m.group(1))
    except OSError:
        pass
    return None


def git_stamp():
    def run(*args):
        return subprocess.run(["git", "-C", PROJECT_ROOT] + list(args),
                              capture_output=True, text=True)
    sha = run("rev-parse", "--short", "HEAD")
    if sha.returncode != 0:
        return {"sha": "unknown", "dirty": None}
    dirty = run("status", "--porcelain", "--untracked-files=no")
    return {"sha": sha.stdout.strip(), "dirty": bool(dirty.stdout.strip())}


def build_variant(env, boot_app0_src):
    build_dir = os.path.join(PROJECT_ROOT, ".pio", "build", env)
    images = {n: os.path.join(build_dir, n + ".bin")
              for n in ("bootloader", "partitions", "firmware")}
    missing = [p for p in images.values() if not os.path.isfile(p)]
    if missing:
        print(f"  SKIP {env}: missing {', '.join(os.path.basename(m) for m in missing)}")
        return None

    table = parse_partition_table(images["partitions"])
    by_sub = {e["subtype"]: e for e in table}
    for req in ("otadata", "ota_0"):
        if req not in by_sub:
            sys.exit(f"ERROR: {env}: partition table has no '{req}' entry — refusing to guess offsets.")

    app_size = os.path.getsize(images["firmware"])
    slot = by_sub["ota_0"]["size"]
    if app_size > slot:
        sys.exit(f"ERROR: {env}: firmware.bin ({app_size}B) exceeds ota_0 slot (0x{slot:x}).")

    out_dir = os.path.join(WEBFLASH_DIR, "firmware", env)
    os.makedirs(out_dir, exist_ok=True)
    parts = []
    plan = [
        ("bootloader.bin", images["bootloader"], BOOTLOADER_OFFSET),
        ("partitions.bin", images["partitions"], PARTITION_TABLE_OFFSET),
        ("boot_app0.bin", boot_app0_src, by_sub["otadata"]["offset"]),
        ("firmware.bin", images["firmware"], by_sub["ota_0"]["offset"]),
    ]
    for name, src, offset in plan:
        dst = os.path.join(out_dir, name)
        shutil.copyfile(src, dst)
        parts.append({
            "path": f"firmware/{env}/{name}",
            "offset": offset,
            "size": os.path.getsize(dst),
            "md5": md5_of(dst),
        })

    built = datetime.fromtimestamp(os.path.getmtime(images["firmware"]),
                                   tz=timezone.utc).isoformat(timespec="seconds")
    variant = {
        "env": env,
        "label": LABELS.get(env, env),
        "builtAt": built,
        "parts": parts,
        "partitionMap": [
            {"name": e["name"], "subtype": e["subtype"],
             "offset": e["offset"], "size": e["size"]} for e in table
        ],
    }
    if "ota_1" in by_sub:
        variant["otaSeedOffset"] = by_sub["ota_1"]["offset"]
    print(f"  OK   {env}: app {app_size}B @ 0x{by_sub['ota_0']['offset']:x} "
          f"(ota_1 @ 0x{by_sub.get('ota_1', {}).get('offset', 0):x})")
    return variant


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--envs", help="comma-separated env list (overrides curated list)")
    args = ap.parse_args()
    envs = [e.strip() for e in args.envs.split(",")] if args.envs else CURATED_ENVS

    boot_app0_src = find_boot_app0()
    print(f"boot_app0: {boot_app0_src} (md5 {md5_of(boot_app0_src)})")

    variants = [v for v in (build_variant(e, boot_app0_src) for e in envs) if v]
    if not variants:
        sys.exit("ERROR: no variants produced — build the curated envs first (pio run -e <env>).")

    fw_version = firmware_version()
    for v in variants:
        v["firmwareVersion"] = fw_version

    manifest = {
        "schema": 1,
        "name": "SpectraSynq K1",
        "chipFamily": "ESP32-S3",
        "flash": {"size": "keep", "mode": "keep", "freq": "keep"},
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git": git_stamp(),
        "variants": variants,
    }
    out = os.path.join(WEBFLASH_DIR, "manifest.json")
    with open(out, "w") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")
    print(f"wrote {out} ({len(variants)} variant(s), git {manifest['git']['sha']}"
          f"{' DIRTY' if manifest['git']['dirty'] else ''})")


if __name__ == "__main__":
    main()
