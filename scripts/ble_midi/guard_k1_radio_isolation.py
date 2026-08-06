#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2025-2026 SpectraSynq
"""Fail if the production K1 build contains the gated BLE Remoted surface."""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path


ROOT = next(p for p in Path(__file__).resolve().parents if (p / "platformio.ini").is_file())
DEFAULT_ENV = "k1_hardware"

FORBIDDEN_CONFIG_TOKENS = (
    "-DK1_BLE_REMOTED",
    "K1_BLE_REMOTED",
    "ble_remoted_central.cpp",
    "k1_ble_midi_decoder.cpp",
    "NimBLE-Arduino",
    # Dual-K1 sync probe surface (Phase 0, 2026-07-08) — extended BEFORE probe
    # firmware lands so a sync TU can never silently reach a production env.
    "-DSB_K1_SYNC_PROBE",
    "SB_K1_SYNC_PROBE",
    "k1_sync_link.cpp",
)

FORBIDDEN_ARTIFACT_TOKENS = (
    b"K1_BLE_REMOTED",
    b"ble_remoted",
    b"k1_ble_midi_decoder",
    b"k1_ble_midi_decode_packet",
    b"K1BleMidi",
    b"NimBLE",
    b"nimble",
    b"K1-Remoted-RX",
    b"SpectraSynq Remoted",
    b"03B80E5A-EDE8-4B33-A751-6CE34EC4C700",
    b"7772E5DB-3868-4112-A1A9-F2669D106BF3",
    # Dual-K1 sync probe surface (Phase 0, 2026-07-08)
    b"SB_K1_SYNC_PROBE",
    b"k1_sync_link",
    b"K1-SyncLink",
    b"53594E43-4B31-4544-9B1A-2026070800A1",
    # ESP-NOW is a rejected-but-contingency transport (F2): if it is ever
    # compiled in by accident, production must fail loudly.
    b"esp_now_init",
)


def section_text(platformio_ini: Path, env: str) -> str:
    text = platformio_ini.read_text(encoding="utf-8")
    marker = re.search(rf"^\[env:{re.escape(env)}\]\s*$", text, re.M)
    if not marker:
        raise SystemExit(f"[FAIL] env:{env} not found in {platformio_ini}")
    next_section = re.search(r"^\[", text[marker.end():], re.M)
    end = marker.end() + next_section.start() if next_section else len(text)
    return text[marker.start():end]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def inspect_config(platformio_ini: Path, env: str) -> list[str]:
    section = section_text(platformio_ini, env)
    failures = []
    for token in FORBIDDEN_CONFIG_TOKENS:
        if token in section:
            failures.append(f"config token {token!r} present in env:{env}")
    return failures


def inspect_artifacts(build_dir: Path) -> tuple[list[str], list[Path]]:
    artifacts = [
        build_dir / "firmware.map",
        build_dir / "firmware.elf",
        build_dir / "firmware.bin",
    ]
    existing = [p for p in artifacts if p.is_file()]
    missing = [p.name for p in artifacts if not p.is_file()]
    failures = []
    if missing:
        failures.append(f"missing build artifacts after PlatformIO build: {', '.join(missing)}")
        return failures, existing

    for artifact in existing:
        data = artifact.read_bytes()
        for token in FORBIDDEN_ARTIFACT_TOKENS:
            if token in data:
                failures.append(f"{artifact.relative_to(ROOT)} contains forbidden token {token.decode(errors='replace')!r}")
    return failures, existing


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--env", default=DEFAULT_ENV)
    ap.add_argument("--platformio-ini", type=Path, default=ROOT / "platformio.ini")
    ap.add_argument("--build-dir", type=Path, default=None)
    args = ap.parse_args()

    build_dir = args.build_dir or (ROOT / ".pio" / "build" / args.env)
    failures = []
    failures.extend(inspect_config(args.platformio_ini, args.env))
    artifact_failures, artifacts = inspect_artifacts(build_dir)
    failures.extend(artifact_failures)

    for artifact in artifacts:
        rel = artifact.relative_to(ROOT)
        print(f"[INFO] {rel} size={artifact.stat().st_size} sha256={sha256(artifact)[:16]}...")

    if failures:
        for failure in failures:
            print(f"[FAIL] {failure}")
        print("K1_RADIO_ISOLATION: FAILED")
        return 1

    print(f"[PASS] env:{args.env} does not enable K1_BLE_REMOTED or compile BLE Remoted sources")
    print("[PASS] production map/ELF/bin contain no BLE Remoted, NimBLE, or generated decoder symbols")
    print("K1_RADIO_ISOLATION: PROVEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
