#!/usr/bin/env python3
"""Fault-evident Gate-1 oracle for the Tab5 hardening programme.

The production firmware is hardened in G2.  G1 first proves that the oracle can
distinguish a conforming reference behaviour from every M1-M9 failure class.
All deliberate mutations are applied to disposable specimen copies.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional


SCHEMA = "spectrasynq-tab5-gate1-mutations-v1"
ALL_FINDINGS = tuple(f"M{i}" for i in range(1, 10))

REQUIRED_MANIFEST_PATHS = (
    "docs/protocol/k1-ble-midi-map.json",
    "docs/protocol/k1-deck-state-v1.md",
    "scripts/ble_midi/gen_k1_ble_midi_header.py",
    "SPECTRASYNQ_K1_FIRMWARE/network/k1_ble_midi_map.h",
    "SPECTRASYNQ_K1_FIRMWARE/network/k1_deck_identity_v1.h",
    "tab5_firmware/platformio.ini",
    "tab5_firmware/toolchain-lock.json",
    "tab5_firmware/include/deck_state_rx.h",
    "tab5_firmware/include/k1_deck_identity_v1.h",
    "tab5_firmware/src/ble_midi_transport.cpp",
    "tab5_firmware/src/deck_state_rx.cpp",
    "tab5_firmware/src/hosted_vhci_drv.c",
    "tab5_firmware/src/k1_ble_midi_map.h",
    "tab5_firmware/src/main.cpp",
    "tab5_firmware/scripts/filter_p4_wifi_remote_archive.py",
    "tab5_firmware/simulator/sim_deck_state_rx.cpp",
)

SAFE_CALLBACK_SPECIMEN = r"""
/* G1_CALLBACKS_BEGIN */
class MidiServerCallbacks final {
 public:
  void onConnect(Server*, Desc* desc) {
    /* M1_LINK_SAFE */ enqueue_link_record(LinkEvent::Connected, desc->handle);
  }
  void onDisconnect(Server*, Desc* desc) {
    /* M1_UNLINK_SAFE */ enqueue_link_record(LinkEvent::Disconnected, desc->handle);
  }
};
class StateCallbacks final {
 public:
  void onWrite(Characteristic* characteristic) {
    /* M1_RAW_SAFE */ enqueue_bounded_raw(characteristic->getData(),
                                           characteristic->getLength());
  }
};
/* G1_CALLBACKS_END */
""".strip() + "\n"

SAFE_POLICY: dict[str, Any] = {
    "connection": {"coalesce_duplicate_connect": True},
    "queue": {
        "desynchronise_on_drop": True,
        "desynchronise_on_oversize": True,
    },
    "snapshot": {
        "transactional_commit": True,
        "validate_count": True,
        "validate_length": True,
        "validate_crc": True,
        "validate_generation": True,
        "validate_required": True,
        "validate_duplicate": True,
        "validate_unknown": True,
        "validate_range": True,
    },
    "delta": {
        "validate_partial": True,
        "validate_stale": True,
        "validate_out_of_order": True,
        "validate_gap": True,
        "validate_cross_generation": True,
    },
    "rssi": {
        "classify_unknown_handle": True,
        "transient_backoff": True,
        "fatal_suspend": True,
        "discard_stale_completion": True,
        "single_inflight": True,
    },
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def replace_exact(path: Path, old: str, new: str, *, expected_count: int = 1) -> None:
    """Replace an exact target and reject inert or ambiguous mutants."""

    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != expected_count:
        raise ValueError(
            f"mutation target count for {path.name}: expected {expected_count}, got {count}"
        )
    updated = text.replace(old, new)
    if updated == text:
        raise ValueError(f"inert mutation for {path.name}")
    path.write_text(updated, encoding="utf-8")


def set_policy(path: Path, dotted_key: str, value: Any) -> None:
    policy = json.loads(path.read_text(encoding="utf-8"))
    keys = dotted_key.split(".")
    node = policy
    for key in keys[:-1]:
        node = node[key]
    leaf = keys[-1]
    old = node[leaf]
    if old == value:
        raise ValueError(f"inert policy mutation: {dotted_key}")
    node[leaf] = value
    path.write_text(json.dumps(policy, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def tracked_manifest(repo_root: Path) -> str:
    output = subprocess.check_output(
        [
            "git",
            "ls-files",
            "--",
            "tab5_firmware",
            "docs/protocol/k1-ble-midi-map.json",
            "docs/protocol/k1-deck-state-v1.md",
            "scripts/ble_midi/gen_k1_ble_midi_header.py",
            "SPECTRASYNQ_K1_FIRMWARE/network/k1_ble_midi_map.h",
            "SPECTRASYNQ_K1_FIRMWARE/network/k1_deck_identity_v1.h",
        ],
        cwd=repo_root,
        text=True,
    )
    paths = sorted(line for line in output.splitlines() if line)
    return "\n".join(paths) + "\n"


def create_specimen(repo_root: Path, destination: Path) -> None:
    write_bytes(destination / "callback_specimen.cpp", SAFE_CALLBACK_SPECIMEN.encode())
    write_bytes(
        destination / "contract_policy.json",
        (json.dumps(SAFE_POLICY, indent=2, sort_keys=True) + "\n").encode(),
    )
    shutil.copy2(repo_root / "tab5_firmware/platformio.ini", destination / "platformio.ini")
    write_bytes(destination / "source_manifest.txt", tracked_manifest(repo_root).encode())
    parity = destination / "source_parity"
    parity.mkdir()
    for source, name in (
        ("docs/protocol/k1-ble-midi-map.json", "map.json"),
        ("SPECTRASYNQ_K1_FIRMWARE/network/k1_ble_midi_map.h", "k1_map.h"),
        ("tab5_firmware/src/k1_ble_midi_map.h", "tab5_map.h"),
        ("SPECTRASYNQ_K1_FIRMWARE/network/k1_deck_identity_v1.h", "k1_identity.h"),
        ("tab5_firmware/include/k1_deck_identity_v1.h", "tab5_identity.h"),
    ):
        shutil.copy2(repo_root / source, parity / name)


def callback_block(text: str) -> str:
    begin = "/* G1_CALLBACKS_BEGIN */"
    end = "/* G1_CALLBACKS_END */"
    if text.count(begin) != 1 or text.count(end) != 1:
        return ""
    return text.split(begin, 1)[1].split(end, 1)[0]


def check_m1(specimen: Path, _: dict[str, Any]) -> list[str]:
    block = callback_block((specimen / "callback_specimen.cpp").read_text(encoding="utf-8"))
    if not block:
        return ["callback specimen boundary missing"]
    forbidden = {
        "Deck mutation": r"\bdeck_state_",
        "LVGL mutation": r"\b(?:deck_ui_|lv_[a-zA-Z0-9_]*\s*\()",
        "heap String": r"\bString\b",
        "callback logging": r"\b(?:Serial|ESP_LOG)[A-Za-z_]*",
        "HCI work": r"\b(?:ble_gap_|connectionRssi|hci_)[A-Za-z0-9_]*\s*\(",
        "lifecycle work": r"\b(?:startAdvertising|apply_connected|apply_disconnected)\s*\(",
        "heap allocation": r"\b(?:malloc|calloc|realloc|new)\b",
    }
    problems = [label for label, pattern in forbidden.items() if re.search(pattern, block)]
    if "enqueue_bounded_raw" not in block or "enqueue_link_record" not in block:
        problems.append("bounded enqueue surface missing")
    return problems


@dataclass
class ConnectionOwner:
    coalesce: bool
    handle: Optional[int] = None
    generation: int = 0
    logical_connects: int = 0

    def connect(self, handle: int) -> None:
        if self.coalesce and self.handle == handle:
            return
        self.handle = handle
        self.generation += 1
        self.logical_connects += 1


def check_m2(_: Path, policy: dict[str, Any]) -> list[str]:
    owner = ConnectionOwner(policy["connection"]["coalesce_duplicate_connect"])
    owner.connect(0)
    owner.connect(0)  # framework dispatches both callback overloads
    if (owner.logical_connects, owner.generation, owner.handle) != (1, 1, 0):
        return ["duplicate framework callbacks created multiple logical connects"]
    return []


@dataclass
class QueueRecovery:
    armed: bool = True
    desynchronised: bool = False
    recovery_requests: int = 0

    def lose(self, kind: str, policy: dict[str, Any]) -> None:
        key = "desynchronise_on_drop" if kind == "drop" else "desynchronise_on_oversize"
        if policy["queue"][key]:
            self.armed = False
            self.desynchronised = True
            self.recovery_requests = 1


def check_m3(_: Path, policy: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    for kind in ("drop", "oversize"):
        recovery = QueueRecovery()
        recovery.lose(kind, policy)
        if (recovery.armed, recovery.desynchronised, recovery.recovery_requests) != (
            False,
            True,
            1,
        ):
            problems.append(f"{kind} continued without one fail-closed recovery")
    return problems


@dataclass(frozen=True)
class SnapshotItem:
    key: str
    value: int
    payload_length_ok: bool = True


class SnapshotReceiver:
    def __init__(self, policy: dict[str, Any]) -> None:
        self.policy = policy["snapshot"]
        self.generation = 7
        self.confirmed: dict[str, int] = {"stable": 42}
        self.before = dict(self.confirmed)
        self.stage: list[SnapshotItem] = []
        self.armed = False
        self.rejected = False

    def item(self, item: SnapshotItem) -> None:
        self.stage.append(item)
        if not self.policy["transactional_commit"]:
            self.confirmed[item.key] = item.value

    def end(
        self,
        *,
        declared_count: int,
        crc_ok: bool,
        generation: int,
        required: set[str],
        allowed: set[str],
    ) -> bool:
        keys = [item.key for item in self.stage]
        valid = True
        if self.policy["validate_count"] and declared_count != len(self.stage):
            valid = False
        if self.policy["validate_length"] and any(not item.payload_length_ok for item in self.stage):
            valid = False
        if self.policy["validate_crc"] and not crc_ok:
            valid = False
        if self.policy["validate_generation"] and generation != self.generation:
            valid = False
        if self.policy["validate_required"] and not required.issubset(keys):
            valid = False
        if self.policy["validate_duplicate"] and len(keys) != len(set(keys)):
            valid = False
        if self.policy["validate_unknown"] and any(key not in allowed for key in keys):
            valid = False
        if self.policy["validate_range"] and any(not 0 <= item.value <= 100 for item in self.stage):
            valid = False
        if not valid:
            self.rejected = True
            self.armed = False
            return False
        self.confirmed = {item.key: item.value for item in self.stage}
        self.armed = True
        return True


def check_m4(_: Path, policy: dict[str, Any]) -> list[str]:
    receiver = SnapshotReceiver(policy)
    receiver.item(SnapshotItem("a", 10))
    if receiver.confirmed != receiver.before:
        return ["snapshot member mutated confirmed state before validated END"]
    return []


def invalid_snapshot_cases() -> dict[str, dict[str, Any]]:
    base = {
        "items": [SnapshotItem("a", 10), SnapshotItem("b", 20)],
        "declared_count": 2,
        "crc_ok": True,
        "generation": 7,
        "required": {"a", "b"},
        "allowed": {"a", "b"},
    }
    cases: dict[str, dict[str, Any]] = {}
    cases["count"] = {**base, "declared_count": 3}
    cases["length"] = {
        **base,
        "items": [SnapshotItem("a", 10, False), SnapshotItem("b", 20)],
    }
    cases["crc"] = {**base, "crc_ok": False}
    cases["generation"] = {**base, "generation": 8}
    cases["required"] = {
        **base,
        "items": [SnapshotItem("a", 10)],
        "declared_count": 1,
    }
    cases["duplicate"] = {
        **base,
        "items": [SnapshotItem("a", 10), SnapshotItem("a", 20)],
        "required": {"a"},
    }
    cases["unknown"] = {
        **base,
        "items": [SnapshotItem("a", 10), SnapshotItem("z", 20)],
        "required": {"a"},
    }
    cases["range"] = {
        **base,
        "items": [SnapshotItem("a", 101), SnapshotItem("b", 20)],
    }
    return cases


def check_m5(_: Path, policy: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    for name, case in invalid_snapshot_cases().items():
        receiver = SnapshotReceiver(policy)
        for item in case["items"]:
            receiver.item(item)
        accepted = receiver.end(
            declared_count=case["declared_count"],
            crc_ok=case["crc_ok"],
            generation=case["generation"],
            required=case["required"],
            allowed=case["allowed"],
        )
        if accepted or receiver.confirmed != receiver.before or receiver.armed:
            problems.append(f"invalid {name} snapshot was not wholly rejected")
    return problems


class DeltaReceiver:
    def __init__(self, policy: dict[str, Any]) -> None:
        self.policy = policy["delta"]
        self.generation = 7
        self.revision = 10
        self.confirmed = {"a": 1, "b": 2}
        self.before = dict(self.confirmed)
        self.desynchronised = False

    def batch(
        self,
        *,
        complete: bool,
        generation: int,
        revisions: list[int],
        values: list[tuple[str, int]],
    ) -> bool:
        valid = True
        resnapshot = False
        first = revisions[0] if revisions else self.revision
        if self.policy["validate_partial"] and not complete:
            valid = False
            resnapshot = True
        if self.policy["validate_cross_generation"] and generation != self.generation:
            valid = False
            resnapshot = True
        if self.policy["validate_stale"] and revisions and revisions[-1] <= self.revision:
            valid = False
        ordered = all(b == a + 1 for a, b in zip(revisions, revisions[1:]))
        if self.policy["validate_out_of_order"] and not ordered:
            valid = False
            resnapshot = True
        if self.policy["validate_gap"] and revisions and first != self.revision + 1:
            if first > self.revision + 1:
                valid = False
                resnapshot = True
        if not valid:
            self.desynchronised = resnapshot
            return False
        staged = dict(self.confirmed)
        staged.update(values)
        self.confirmed = staged
        if revisions:
            self.revision = revisions[-1]
        return True


def delta_cases() -> dict[str, dict[str, Any]]:
    return {
        "partial": {
            "complete": False,
            "generation": 7,
            "revisions": [11],
            "values": [("a", 11)],
            "resnapshot": True,
        },
        "stale": {
            "complete": True,
            "generation": 7,
            "revisions": [10],
            "values": [("a", 10)],
            "resnapshot": False,
        },
        "out_of_order": {
            "complete": True,
            "generation": 7,
            "revisions": [11, 13, 12],
            "values": [("a", 11), ("b", 13), ("a", 12)],
            "resnapshot": True,
        },
        "gap": {
            "complete": True,
            "generation": 7,
            "revisions": [12],
            "values": [("a", 12)],
            "resnapshot": True,
        },
        "cross_generation": {
            "complete": True,
            "generation": 8,
            "revisions": [11],
            "values": [("a", 11)],
            "resnapshot": True,
        },
    }


def check_m6(_: Path, policy: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    for name, case in delta_cases().items():
        receiver = DeltaReceiver(policy)
        accepted = receiver.batch(
            complete=case["complete"],
            generation=case["generation"],
            revisions=case["revisions"],
            values=case["values"],
        )
        if (
            accepted
            or receiver.confirmed != receiver.before
            or receiver.desynchronised != case["resnapshot"]
        ):
            problems.append(f"invalid {name} delta batch was not atomically rejected")
    return problems


class RssiMachine:
    def __init__(self, policy: dict[str, Any]) -> None:
        self.policy = policy["rssi"]
        self.generation = 7
        self.connected = True
        self.desynchronised = False
        self.suspended = False
        self.inflight = False
        self.next_due = 0.0
        self.transient_failures = 0
        self.calls = 0
        self.cached: Optional[int] = None

    def start(self, now: float, generation: int = 7) -> bool:
        if not self.connected or self.suspended or now < self.next_due:
            return False
        if self.inflight and self.policy["single_inflight"]:
            return False
        self.inflight = True
        self.calls += 1
        return True

    def complete(self, outcome: str, now: float, generation: int = 7) -> None:
        if generation != self.generation and self.policy["discard_stale_completion"]:
            return
        self.inflight = False
        if outcome == "success":
            self.cached = -42
            self.transient_failures = 0
            self.next_due = now + 2.0
        elif outcome == "unknown":
            if self.policy["classify_unknown_handle"]:
                self.connected = False
                self.desynchronised = True
            else:
                self.next_due = now
        elif outcome == "transient":
            self.transient_failures += 1
            if self.policy["transient_backoff"]:
                delay = min(2 ** self.transient_failures, 30)
                self.next_due = now + float(delay)
            else:
                self.next_due = now
        elif outcome == "fatal":
            if self.policy["fatal_suspend"]:
                self.suspended = True
                self.desynchronised = True
            else:
                self.next_due = now


def check_m7(_: Path, policy: dict[str, Any]) -> list[str]:
    problems: list[str] = []

    unknown = RssiMachine(policy)
    unknown.start(0.0)
    unknown.complete("unknown", 0.1)
    if unknown.connected or not unknown.desynchronised or unknown.start(0.6):
        problems.append("unknown handle did not enter controlled disconnect")

    transient = RssiMachine(policy)
    transient.start(0.0)
    transient.complete("transient", 0.1)
    if transient.start(1.0) or not transient.start(2.1):
        problems.append("transient failure did not use bounded 2-second backoff")

    fatal = RssiMachine(policy)
    fatal.start(0.0)
    fatal.complete("fatal", 0.1)
    if not fatal.suspended or not fatal.desynchronised or fatal.start(60.0):
        problems.append("fatal transport failure did not suspend RSSI maintenance")

    stale = RssiMachine(policy)
    stale.start(0.0)
    stale.complete("success", 0.1, generation=6)
    if stale.cached is not None or stale.next_due != 0.0:
        problems.append("stale RSSI completion changed current generation state")

    inflight = RssiMachine(policy)
    first = inflight.start(0.0)
    second = inflight.start(0.0)
    if not first or second or inflight.calls != 1:
        problems.append("more than one RSSI operation was in flight")

    return problems


def ini_section(text: str, name: str) -> str:
    match = re.search(
        rf"(?ms)^\[{re.escape(name)}\]\s*$\n(.*?)(?=^\[|\Z)", text
    )
    return match.group(1) if match else ""


def resolved_defines(section: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in section.splitlines():
        stripped = line.strip()
        if stripped.startswith("-U"):
            values.pop(stripped[2:].strip(), None)
        elif stripped.startswith("-D"):
            token = stripped[2:].strip()
            key, _, value = token.partition("=")
            values[key] = value or "1"
    return values


def check_m8(specimen: Path, _: dict[str, Any]) -> list[str]:
    text = (specimen / "platformio.ini").read_text(encoding="utf-8")
    production = resolved_defines(ini_section(text, "env:tab5_p4"))
    diagnostic = resolved_defines(ini_section(text, "env:tab5_p4_hci_diag"))
    common = ini_section(text, "platformio")
    problems: list[str] = []
    for key in ("TAB5_HCI_PATH_DIAG", "TAB5_BLE_VERBOSE_DIAG"):
        if production.get(key) != "0":
            problems.append(f"production {key} resolved enabled or absent")
        if diagnostic.get(key) != "1":
            problems.append(f"diagnostic {key} did not resolve enabled")
    if diagnostic.get("TAB5_NON_SHIPPABLE_DIAGNOSTIC") != "1":
        problems.append("diagnostic environment lacks non-shippable marker")
    if not re.search(r"(?m)^default_envs\s*=\s*tab5_p4\s*$", common):
        problems.append("production is not the sole default environment")
    return problems


def check_m9(specimen: Path, _: dict[str, Any]) -> list[str]:
    listed = set((specimen / "source_manifest.txt").read_text(encoding="utf-8").splitlines())
    missing = [path for path in REQUIRED_MANIFEST_PATHS if path not in listed]
    problems = [f"required path missing from tracked source closure: {path}" for path in missing]
    parity = specimen / "source_parity"
    contract = json.loads((parity / "map.json").read_text(encoding="utf-8"))
    k1_map = (parity / "k1_map.h").read_text(encoding="utf-8")
    tab5_map = (parity / "tab5_map.h").read_text(encoding="utf-8")
    k1_identity = (parity / "k1_identity.h").read_text(encoding="utf-8")
    tab5_identity = (parity / "tab5_identity.h").read_text(encoding="utf-8")
    expected_count = f"#define K1_BLE_MIDI_CONTROL_COUNT {contract['control_count']}"
    expected_md5 = f'#define K1_BLE_MIDI_REGISTRY_MD5 "{contract["registry_md5"]}"'
    if k1_map != tab5_map:
        problems.append("K1 and Tab5 generated BLE-MIDI maps differ")
    if expected_count not in k1_map or expected_md5 not in k1_map:
        problems.append("generated BLE-MIDI map does not match JSON authority")
    identity_pattern = re.compile(
        r'#define\s+K1_DECK_IDENTITY_REGISTRY_MD5_HEX\s+"([0-9a-f]{32})"'
    )
    k1_match = identity_pattern.search(k1_identity)
    tab5_match = identity_pattern.search(tab5_identity)
    if not k1_match or not tab5_match or k1_match.group(1) != tab5_match.group(1):
        problems.append("K1 and Tab5 compatibility identity digests differ")
    return problems


CHECKS: dict[str, Callable[[Path, dict[str, Any]], list[str]]] = {
    "M1": check_m1,
    "M2": check_m2,
    "M3": check_m3,
    "M4": check_m4,
    "M5": check_m5,
    "M6": check_m6,
    "M7": check_m7,
    "M8": check_m8,
    "M9": check_m9,
}


def evaluate(specimen: Path) -> dict[str, list[str]]:
    policy = json.loads((specimen / "contract_policy.json").read_text(encoding="utf-8"))
    return {finding: check(specimen, policy) for finding, check in CHECKS.items()}


@dataclass(frozen=True)
class Mutation:
    finding: str
    variant: str
    target: str
    apply: Callable[[Path], None]


def policy_mutation(finding: str, variant: str, dotted_key: str) -> Mutation:
    return Mutation(
        finding,
        variant,
        "contract_policy.json",
        lambda specimen: set_policy(specimen / "contract_policy.json", dotted_key, False),
    )


def callback_mutation(variant: str, old: str, new: str) -> Mutation:
    return Mutation(
        "M1",
        variant,
        "callback_specimen.cpp",
        lambda specimen: replace_exact(specimen / "callback_specimen.cpp", old, new),
    )


def mutations() -> list[Mutation]:
    result = [
        callback_mutation(
            "deck_mutation",
            "/* M1_LINK_SAFE */ enqueue_link_record(LinkEvent::Connected, desc->handle);",
            "/* M1_LINK_SAFE */ deck_state_rx_on_identity_hint();",
        ),
        callback_mutation(
            "lvgl_mutation",
            "/* M1_UNLINK_SAFE */ enqueue_link_record(LinkEvent::Disconnected, desc->handle);",
            "/* M1_UNLINK_SAFE */ deck_ui_set_key_lamp(DECK_SHEET_EDGE, false);",
        ),
        callback_mutation(
            "string_allocation",
            "/* M1_RAW_SAFE */ enqueue_bounded_raw(characteristic->getData(),\n                                           characteristic->getLength());",
            "/* M1_RAW_SAFE */ String value = characteristic->getValue();",
        ),
        callback_mutation(
            "byte_logging",
            "/* M1_RAW_SAFE */ enqueue_bounded_raw(characteristic->getData(),\n                                           characteristic->getLength());",
            "/* M1_RAW_SAFE */ Serial.printf(\"rx byte %u\", characteristic->getLength());",
        ),
        callback_mutation(
            "hci_work",
            "/* M1_RAW_SAFE */ enqueue_bounded_raw(characteristic->getData(),\n                                           characteristic->getLength());",
            "/* M1_RAW_SAFE */ ble_gap_conn_rssi(0, nullptr);",
        ),
        callback_mutation(
            "lifecycle_work",
            "/* M1_UNLINK_SAFE */ enqueue_link_record(LinkEvent::Disconnected, desc->handle);",
            "/* M1_UNLINK_SAFE */ startAdvertising();",
        ),
        policy_mutation("M2", "double_connect_owner", "connection.coalesce_duplicate_connect"),
        policy_mutation("M3", "silent_queue_drop", "queue.desynchronise_on_drop"),
        policy_mutation("M3", "silent_oversize", "queue.desynchronise_on_oversize"),
        policy_mutation("M4", "early_snapshot_apply", "snapshot.transactional_commit"),
    ]
    for variant in (
        "count",
        "length",
        "crc",
        "generation",
        "required",
        "duplicate",
        "unknown",
        "range",
    ):
        result.append(policy_mutation("M5", variant, f"snapshot.validate_{variant}"))
    for variant in ("partial", "stale", "out_of_order", "gap", "cross_generation"):
        result.append(policy_mutation("M6", variant, f"delta.validate_{variant}"))
    rssi_keys = {
        "unknown_handle": "classify_unknown_handle",
        "transient_backoff": "transient_backoff",
        "fatal_suspend": "fatal_suspend",
        "stale_completion": "discard_stale_completion",
        "multiple_inflight": "single_inflight",
    }
    for variant, key in rssi_keys.items():
        result.append(policy_mutation("M7", variant, f"rssi.{key}"))
    result.extend(
        [
            Mutation(
                "M8",
                "production_hci_enabled",
                "platformio.ini",
                lambda specimen: replace_exact(
                    specimen / "platformio.ini",
                    "-DTAB5_HCI_PATH_DIAG=0",
                    "-DTAB5_HCI_PATH_DIAG=1",
                ),
            ),
            Mutation(
                "M8",
                "production_value_diag_enabled",
                "platformio.ini",
                lambda specimen: replace_exact(
                    specimen / "platformio.ini",
                    "-DTAB5_BLE_VERBOSE_DIAG=0",
                    "-DTAB5_BLE_VERBOSE_DIAG=1",
                ),
            ),
        ]
    )
    for variant, path in (
        ("protocol_missing", "docs/protocol/k1-deck-state-v1.md"),
        ("configuration_missing", "tab5_firmware/platformio.ini"),
    ):
        result.append(
            Mutation(
                "M9",
                variant,
                "source_manifest.txt",
                lambda specimen, path=path: replace_exact(
                    specimen / "source_manifest.txt", f"{path}\n", ""
                ),
            )
        )
    result.extend(
        [
            Mutation(
                "M9",
                "tab5_map_drift",
                "source_parity/tab5_map.h",
                lambda specimen: replace_exact(
                    specimen / "source_parity/tab5_map.h",
                    '#define K1_BLE_MIDI_CONTROL_COUNT 71',
                    '#define K1_BLE_MIDI_CONTROL_COUNT 68',
                ),
            ),
            Mutation(
                "M9",
                "json_map_drift",
                "source_parity/map.json",
                lambda specimen: replace_exact(
                    specimen / "source_parity/map.json",
                    '"control_count": 71',
                    '"control_count": 68',
                ),
            ),
            Mutation(
                "M9",
                "identity_drift",
                "source_parity/tab5_identity.h",
                lambda specimen: replace_exact(
                    specimen / "source_parity/tab5_identity.h",
                    '"9b5db3fbb17438367adeaceb541db03b"',
                    '"00000000000000000000000000000000"',
                ),
            ),
        ]
    )
    return result


def failed_findings(results: dict[str, list[str]]) -> list[str]:
    return sorted(finding for finding, problems in results.items() if problems)


def run_gate(repo_root: Path) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    with tempfile.TemporaryDirectory(prefix="tab5_gate1_") as tmp_name:
        tmp = Path(tmp_name)
        baseline = tmp / "positive"
        baseline.mkdir()
        create_specimen(repo_root, baseline)
        positive = evaluate(baseline)

        mutation_rows: list[dict[str, Any]] = []
        for index, mutation in enumerate(mutations()):
            specimen = tmp / f"mutant_{index:02d}"
            shutil.copytree(baseline, specimen)
            target = specimen / mutation.target
            before = target.read_bytes()
            mutation_error: Optional[str] = None
            try:
                mutation.apply(specimen)
            except Exception as exc:  # Gate evidence must survive an inert mutant.
                mutation_error = f"{type(exc).__name__}: {exc}"
            after = target.read_bytes()
            changed = before != after
            results = evaluate(specimen)
            observed = failed_findings(results)
            mutation_rows.append(
                {
                    "changed": changed,
                    "finding": mutation.finding,
                    "variant": mutation.variant,
                    "target": mutation.target,
                    "before_sha256": sha256_bytes(before),
                    "after_sha256": sha256_bytes(after),
                    "mutation_error": mutation_error,
                    "observed_findings": observed,
                    "killed": changed and mutation.finding in observed,
                }
            )

    coverage = sorted({row["finding"] for row in mutation_rows})
    positive_failures = failed_findings(positive)
    no_fail_everything = all(len(row["observed_findings"]) < len(ALL_FINDINGS) for row in mutation_rows)
    passed = (
        not positive_failures
        and coverage == list(ALL_FINDINGS)
        and all(row["changed"] and row["killed"] for row in mutation_rows)
        and no_fail_everything
    )
    return {
        "schema": SCHEMA,
        "passed": passed,
        "positive_control": {
            "passed": not positive_failures,
            "failed_findings": positive_failures,
            "finding_details": {key: positive[key] for key in ALL_FINDINGS},
        },
        "coverage": coverage,
        "mutation_count": len(mutation_rows),
        "no_fail_everything_oracle": no_fail_everything,
        "mutations": mutation_rows,
    }


def write_report(report: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def default_repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=default_repo_root())
    parser.add_argument("--json", type=Path, required=True, help="caller-owned JSON output path")
    args = parser.parse_args()
    report = run_gate(args.repo_root)
    write_report(report, args.json)
    print(
        f"TAB5_G1_MUTATION_GATE={'PASS' if report['passed'] else 'FAIL'} "
        f"mutants={report['mutation_count']} coverage={','.join(report['coverage'])}"
    )
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
