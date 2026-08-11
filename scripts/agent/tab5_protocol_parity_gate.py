#!/usr/bin/env python3
"""Fail-fast K1/Tab5 protocol parity and live-receipt gate.

The current product contract is the live-proven 68-control registry.  This gate
exists because a coherent-looking 71-control source set was once flashed to the
Tab5 while Unit2 was still emitting the correct 68-control wire map.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path


EXPECTED_COUNT = 68
EXPECTED_MD5 = "9b5db3fbb17438367adeaceb541db03b"


class GateFailure(RuntimeError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code


def fail(code: str, detail: str) -> None:
    raise GateFailure(code, detail)


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        fail("SOURCE_MISSING", f"{path}: {exc}")


def require_text(text: str, needle: str, code: str, source: Path) -> None:
    if needle not in text:
        fail(code, f"{source} does not contain {needle!r}")


def render_header(repo: Path, contract: dict) -> str:
    generator = repo / "scripts/ble_midi/gen_k1_ble_midi_header.py"
    spec = importlib.util.spec_from_file_location("k1_ble_midi_header_generator", generator)
    if spec is None or spec.loader is None:
        fail("GENERATOR_IMPORT", f"cannot import {generator}")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
        return module.render(contract)
    except Exception as exc:  # generator errors must fail closed with one stable code
        fail("GENERATOR_RENDER", f"{generator}: {exc}")


def check_source_parity(repo: Path) -> None:
    contract_path = repo / "docs/protocol/k1-ble-midi-map.json"
    try:
        contract = json.loads(read(contract_path))
    except json.JSONDecodeError as exc:
        fail("CONTRACT_JSON", f"{contract_path}: {exc}")

    entries = contract.get("entries")
    if not isinstance(entries, list):
        fail("CONTRACT_ENTRIES", "entries must be a list")
    declared_count = contract.get("control_count")
    if declared_count != len(entries):
        fail("CONTRACT_COUNT_INTERNAL", f"declared={declared_count} entries={len(entries)}")
    if declared_count != EXPECTED_COUNT:
        fail("CONTRACT_COUNT", f"expected={EXPECTED_COUNT} observed={declared_count}")
    observed_md5 = contract.get("registry_md5")
    if observed_md5 != EXPECTED_MD5:
        fail("CONTRACT_MD5", f"expected={EXPECTED_MD5} observed={observed_md5}")

    generated = render_header(repo, contract)
    header_paths = (
        ("K1_HEADER_GENERATION_DRIFT", repo / "SPECTRASYNQ_K1_FIRMWARE/network/k1_ble_midi_map.h"),
        ("TAB5_HEADER_GENERATION_DRIFT", repo / "tab5_firmware/src/k1_ble_midi_map.h"),
    )
    for code, path in header_paths:
        if read(path) != generated:
            fail(code, f"regenerate {path} from {contract_path}")

    k1_identity = repo / "SPECTRASYNQ_K1_FIRMWARE/network/k1_deck_identity_v1.h"
    tab5_identity = repo / "tab5_firmware/include/k1_deck_identity_v1.h"
    identity_needle = f'#define K1_DECK_IDENTITY_REGISTRY_MD5_HEX "{EXPECTED_MD5}"'
    require_text(read(k1_identity), identity_needle, "K1_IDENTITY_DIGEST", k1_identity)
    require_text(read(tab5_identity), identity_needle, "TAB5_IDENTITY_DIGEST", tab5_identity)

    k1_claim = repo / "SPECTRASYNQ_K1_FIRMWARE/network/k1_claim_adv_v1.h"
    tab5_claim = repo / "tab5_firmware/include/k1_claim_adv_v1.h"
    if read(k1_claim) != read(tab5_claim):
        fail("CLAIM_HEADER_DRIFT", f"{k1_claim} and {tab5_claim} differ")

    receiver = repo / "tab5_firmware/src/deck_state_rx.cpp"
    receiver_text = read(receiver)
    require_text(
        receiver_text,
        f"static_assert(K1_BLE_MIDI_CONTROL_COUNT == {EXPECTED_COUNT}",
        "RECEIVER_COUNT",
        receiver,
    )
    require_text(
        receiver_text,
        f'constexpr char kCanonicalRegistryMd5[] = "{EXPECTED_MD5}"',
        "RECEIVER_DIGEST",
        receiver,
    )


def parse_status(line: str) -> dict[str, str]:
    return dict(re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)=([^\s]+)", line))


def check_live_receipt(path: Path) -> tuple[str, str, int]:
    log = read(path)
    require_text(log, f"map_md5={EXPECTED_MD5}", "LIVE_MAP_MD5", path)
    unit_matches = re.findall(r"HELLO unit_proof=([0-9A-Fa-f]{8})", log)
    if not unit_matches:
        fail("LIVE_UNIT_PROOF", f"{path} contains no HELLO unit_proof")
    status_lines = [line for line in log.splitlines() if "DECK_RX:" in line]
    if not status_lines:
        fail("LIVE_STATUS_MISSING", f"{path} contains no DECK_RX status")
    status = parse_status(status_lines[-1])
    phase = status.get("phase", "")
    if phase not in {"ARMED", "LIVE"}:
        fail("LIVE_PHASE", f"expected ARMED or LIVE, observed {phase or 'missing'}")
    if status.get("armed") != "1":
        fail("LIVE_ARMED", f"expected armed=1, observed {status.get('armed', 'missing')}")
    try:
        snapshot_commits = int(status.get("snap_commit", "-1"))
    except ValueError:
        snapshot_commits = -1
    if snapshot_commits < 1:
        fail("LIVE_SNAPSHOT", f"expected snap_commit>=1, observed {status.get('snap_commit', 'missing')}")
    for counter in ("map_mismatch", "snap_reject", "invalid", "desync", "recovery"):
        value = status.get(counter)
        if value != "0":
            fail(f"LIVE_COUNTER_{counter.upper()}", f"expected {counter}=0, observed {value or 'missing'}")
    return unit_matches[-1].upper(), phase, snapshot_commits


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--serial-log", type=Path)
    args = parser.parse_args()
    repo = args.repo_root.resolve()
    try:
        check_source_parity(repo)
        print(f"TAB5_PROTOCOL_PARITY=PASS controls={EXPECTED_COUNT} md5={EXPECTED_MD5}")
        if args.serial_log is not None:
            unit, phase, snapshots = check_live_receipt(args.serial_log)
            print(
                "TAB5_LIVE_PROTOCOL=PASS "
                f"unit={unit} phase={phase} snap_commit={snapshots}"
            )
        return 0
    except GateFailure as exc:
        print(f"TAB5_PROTOCOL_PARITY=FAIL {exc.code}: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
