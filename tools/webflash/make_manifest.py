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

# ── Curated env list (Captain-ruled 2026-08-18; shortlist 2026-08-26).
# Default three homes. Add rows only when Captain names them. Never dump
# platformio.ini. ESP32-P4 (k1_p4_*) is a different chip family — not this page.
CURATED_ENVS = [
    "k1_main_rpl_im69d",
    "k1_bench_im69d_led150",
    "k1_unit2_im69d_right",
]

SIMPLE_ENV = "k1_main_rpl_im69d"

# Human labels name device + pin fact, not just the env string.
LABELS = {
    "k1_hardware": "F887 · legacy LED 6/7 (k1_hardware)",
    "k1_main_rpl_im69d": "Main RPL · 9087 · WS2816 160 GPIO15/16+17/18",
    "k1_bench_im69d_led150": "Bench K1v2 · B489 · WS2812 150 GPIO39/40",
    "k1_unit2_im69d_right": "Bench Unit 2 · 0C54 · WS2812 206 GPIO4/5 PDM CLK39/DATA38",
}

# ESP32-S3 ROM constants (chip-fixed, not project-tunable).
BOOTLOADER_OFFSET = 0x0
PARTITION_TABLE_OFFSET = 0x8000

WEBFLASH_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(WEBFLASH_DIR, "..", ".."))
IDENTITIES_PATH = os.path.join(
    PROJECT_ROOT, "scripts", "platformio", "k1_device_identities.json",
)


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


def load_identities():
    try:
        with open(IDENTITIES_PATH) as f:
            return json.load(f)
    except OSError as exc:
        sys.exit(f"ERROR: cannot read device identities at {IDENTITIES_PATH}: {exc}")


def records_for_env(identities, env):
    return [r for r in identities.get("authorized", []) if env in r.get("envs", [])]


def stamp_variant_identity(variant, identities):
    """Fail closed: every webflash row must name the chips/MACs allowed to take it."""
    env = variant["env"]
    if env.startswith("k1_p4_"):
        sys.exit(f"ERROR: {env} is ESP32-P4 — this flasher is chipFamily ESP32-S3 only.")
    recs = records_for_env(identities, env)
    if not recs:
        sys.exit(
            f"ERROR: {env} has no authorized device in k1_device_identities.json "
            "— refusing to ship an ungated webflash row."
        )
    chips, serials, roles = [], [], []
    for rec in recs:
        cid = rec.get("chip_id")
        serial = rec.get("usb_serial")
        if cid:
            cid_u = str(cid).upper()
            if cid_u.startswith("0743"):
                sys.exit(
                    f"ERROR: {env} is bound to ESP32-P4 chip {cid}; "
                    "this flasher is ESP32-S3 only."
                )
            chips.append(cid_u)
        if serial:
            serials.append(str(serial).upper())
        if rec.get("role"):
            roles.append(rec["role"])
    if not chips or not serials:
        sys.exit(f"ERROR: {env} identity record is missing chip_id or usb_serial.")
    variant["permittedChipIds"] = chips
    variant["usbSerial"] = serials
    if roles:
        variant["role"] = roles[0]
    return variant


def known_devices_for_page(identities, curated):
    """Registry units, with only curated envs listed as allowed on this page."""
    curated_set = set(curated)
    devices = []
    for rec in identities.get("authorized", []):
        serial = rec.get("usb_serial")
        if not serial:
            continue
        allowed = [e for e in rec.get("envs", []) if e in curated_set]
        devices.append({
            "chipId": rec.get("chip_id"),
            "usbSerial": str(serial).upper(),
            "role": rec.get("role") or "",
            "allowedCuratedEnvs": allowed,
        })
    return devices


def quarantined_serials(identities):
    return [
        str(rec["usb_serial"]).upper()
        for rec in identities.get("quarantined", [])
        if rec.get("usb_serial")
    ]


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

    identities = load_identities()
    fw_version = firmware_version()
    for v in variants:
        v["firmwareVersion"] = fw_version
        stamp_variant_identity(v, identities)

    manifest = {
        "schema": 1,
        "name": "SpectraSynq K1",
        "chipFamily": "ESP32-S3",
        "flash": {"size": "keep", "mode": "keep", "freq": "keep"},
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git": git_stamp(),
        "identityPolicy": {
            "unknownMac": "refuse",
            "simpleEnv": SIMPLE_ENV,
        },
        "knownDevices": known_devices_for_page(identities, envs),
        "quarantinedUsbSerials": quarantined_serials(identities),
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
