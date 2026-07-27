"""Identity-checked, ordered F2 A/B/C1/C2 Link Ready capture controller.

This controller never flashes. It proves the already-flashed binaries and
devices before capture, enforces A -> B -> C1 -> C2, and writes a manifest.
It is deliberately separate from Gate-0.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from . import (
    capture,
    f2_image_set,
    f2_ports,
    f2_status,
    gate_eval,
    logfmt,
)

CASE_CONTRACT = {
    "A": {
        "physical_state": "sync-only",
        "leader_env": "k1_sync_probe_main_sync_only",
    },
    "B": {
        "physical_state": "dial-off",
        "leader_env": "k1_sync_probe_main",
    },
    "C1": {
        "physical_state": "dial-late-join",
        "leader_env": "k1_sync_probe_main",
    },
    "C2": {
        "physical_state": "dial-cold-coexistence",
        "leader_env": "k1_sync_probe_main",
    },
}
FOLLOWER_ENV = "k1_sync_probe_bench"
LEADER_CHIP = "F887A500"
FOLLOWER_CHIP = "B489A500"
LEADER_USB_SERIAL = "B4:3A:45:A5:87:F8"
FOLLOWER_USB_SERIAL = "B4:3A:45:A5:89:B4"
SCHEMA_VERSION = 3
MIN_CAPTURE_SECONDS = 60.0
MIN_DIAL_SAMPLES = 10
TRACKED_F2_REL = Path(
    "artifacts/k1_dual_sync_eval_2026-07-08/recovery/f2"
)

_REMOTED_COUNTER_RE = re.compile(
    r"(?:^|\s)\[ble_remoted\]\s+counters\s+linked=(0|1)"
    r"\s+scan_active=(0|1)\s+scan_start_ok=(\d+)"
    r"\s+scan_start_fail=(\d+)"
    r"\s+notify=(\d+)\s+decoded=(\d+)\s+enqueued=(\d+)"
    r"\s+queue_drops=(\d+)\s+decode_errors=(\d+)"
    r"\s+stale_generation_drops=(\d+)"
    r"\s+apply_ok=(\d+)\s+apply_fail=(\d+)"
    r"\s+link_up=(\d+)\s+link_down=(\d+)\s+connect_fail=(\d+)"
    r"\s+confirm_ok=(\d+)\s+confirm_fail=(\d+)"
    r"\s+confirm_pm=(\d+)\s+confirm_sm=(\d+)$"
)
_REMOTED_LINK_RE = re.compile(
    r"(?:^|\s)\[ble_remoted\]\s+link\s+(up|down)\s+generation=(\d+)"
    r"(?:\s+reason=(-?\d+))?$"
)
_MODE_APPLY_RE = re.compile(
    r"(?:^|\s)\[ble_remoted\]\s+mode_apply\s+record_id=(\d+)"
    r"\s+control=(primary\.mode|secondary\.mode)"
    r"\s+accepted=(\d+)\s+apply_ok=(\d+)$"
)
_CONFIRM_WRITE_RE = re.compile(
    r"(?:^|\s)\[ble_remoted\]\s+confirm_write\s+ok=(0|1)"
    r"\s+cause=(initial|dial_mode|other)\s+record_id=(\d+)"
    r"\s+generation=(\d+)\s+pm=(\d+)\s+sm=(\d+)$"
)


class F2ContractError(RuntimeError):
    """F2 ordering, identity, binary, or manifest contract failure."""


def _git_head(repo_root: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError) as error:
        raise F2ContractError(f"cannot resolve source HEAD: {error}") from error


def _require_clean_host_inputs(repo_root: Path) -> None:
    completed = subprocess.run(
        [
            "git",
            "status",
            "--porcelain",
            "--untracked-files=no",
        ],
        cwd=repo_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    allowed = {"docs/hardware/device-build-registry.md"}
    dirty = set()
    for line in completed.stdout.splitlines():
        if not line.strip():
            continue
        dirty.add(line[3:])
    unexpected = sorted(dirty - allowed)
    if completed.returncode != 0 or unexpected:
        raise F2ContractError(
            "F2 tracked inputs are dirty outside the explicit registry "
            f"exclusion: {unexpected}"
        )


def _resolve_commit(repo_root: Path, value: str) -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--verify", f"{value}^{{commit}}"],
            cwd=repo_root,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError) as error:
        raise F2ContractError(
            f"cannot resolve firmware source commit {value}: {error}"
        ) from error


def _validate_run_id(value: str) -> str:
    if (
        re.fullmatch(
            r"[A-Za-z0-9](?:[A-Za-z0-9_.-]{0,125}[A-Za-z0-9])?",
            value,
        )
        is None
    ):
        raise F2ContractError("F2 run ID contains unsafe characters")
    return value


def _valid_git_prefix(source_sha: str, value: object) -> bool:
    return (
        isinstance(value, str)
        and re.fullmatch(r"[0-9a-f]{7,40}", value) is not None
        and source_sha.startswith(value)
    )


def _app_elf_sha256(bin_path: Path) -> str:
    command = [
        "pio",
        "pkg",
        "exec",
        "--package",
        "tool-esptoolpy",
        "--",
        "esptool.py",
        "image_info",
        str(bin_path),
    ]
    try:
        output = subprocess.check_output(
            command, text=True, stderr=subprocess.STDOUT
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise F2ContractError(
            f"cannot inspect app ELF identity: {error}"
        ) from error
    match = re.search(r"ELF file SHA256:\s*([0-9a-f]{64})", output)
    if match is None:
        raise F2ContractError(
            "preserved image has no app ELF SHA-256 identity"
        )
    return match.group(1)


def _require_ancestor(
    repo_root: Path, firmware_sha: str, host_sha: str
) -> None:
    if firmware_sha == host_sha:
        raise F2ContractError(
            "host execution SHA and firmware source SHA must remain distinct"
        )
    try:
        subprocess.check_call(
            ["git", "merge-base", "--is-ancestor", firmware_sha, host_sha],
            cwd=repo_root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise F2ContractError(
            "firmware source commit must be a strict ancestor of the host "
            "controller commit"
        ) from error


def _sha256(path: Path) -> str:
    if not path.is_file():
        raise F2ContractError(f"binary evidence does not exist: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_manifest(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise F2ContractError(f"invalid prior manifest {path}: {error}") from error


def _inside(path: Path, parent: Path) -> bool:
    try:
        Path(os.path.abspath(path)).relative_to(
            Path(os.path.abspath(parent))
        )
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _has_symlink_component(path: Path) -> bool:
    absolute = Path(os.path.abspath(path))
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current = current / part
        if current.is_symlink():
            return True
    return False


def _repo_relative(path: Path, repo_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root.resolve()))
    except ValueError as error:
        raise F2ContractError(
            f"evidence path is outside repository: {path}"
        ) from error


def _evidence_record(path: Path, repo_root: Path) -> dict[str, str | int]:
    if _has_symlink_component(path):
        raise F2ContractError(f"evidence path may not be a symlink: {path}")
    return {
        "path": _repo_relative(path, repo_root),
        "sha256": _sha256(path),
        "size": path.stat().st_size,
    }


def _validate_evidence_record(
    record: object, repo_root: Path, allowed_root: Path, label: str
) -> Path:
    if not isinstance(record, dict):
        raise F2ContractError(f"{label} evidence record is missing")
    path_text = record.get("path")
    digest = record.get("sha256")
    size = record.get("size")
    if (
        not isinstance(path_text, str)
        or not isinstance(digest, str)
        or not isinstance(size, int)
    ):
        raise F2ContractError(f"{label} evidence record is malformed")
    path = _require_direct_file(
        repo_root / path_text, allowed_root, f"{label} evidence"
    )
    if path.stat().st_size != size:
        raise F2ContractError(f"{label} evidence size mismatch")
    if _sha256(path) != digest:
        raise F2ContractError(f"{label} evidence hash mismatch")
    return path


def _require_direct_file(
    path: Path, allowed_root: Path, label: str
) -> Path:
    """Reject indirection and path escape before evidence is trusted."""
    if _has_symlink_component(path) or _has_symlink_component(allowed_root):
        raise F2ContractError(f"{label} may not be a symlink")
    resolved = path.resolve()
    if not _inside(resolved, allowed_root):
        raise F2ContractError(f"{label} escapes its allowed root")
    if not resolved.is_file():
        raise F2ContractError(f"{label} does not exist")
    return resolved


def _validate_attestation(path: Path, case_name: str) -> dict:
    if case_name in ("C1", "C2"):
        try:
            return f2_status.validate_pre_attestation(
                path, case_name, path.parents[1]
            )["payload"]
        except f2_status.F2StatusError as error:
            raise F2ContractError(str(error)) from error
    payload = _read_manifest(path)
    expected_k718 = {"A": "irrelevant", "B": "off"}[case_name]
    required = {
        "schema_version": 1,
        "case": case_name,
        "confirmed_by": "Captain",
        "gpio_wiring_confirmed": True,
        "common_ground_confirmed": True,
        "logic_voltage": "3V3",
        "k718_state": expected_k718,
    }
    for key, expected in required.items():
        if payload.get(key) != expected:
            raise F2ContractError(
                f"Case {case_name} attestation requires {key}={expected!r}"
            )
    return payload


def _analyse_dial(
    case_name: str, leader_text: str, status_pair: dict | None
) -> dict:
    if case_name == "A":
        return {"status": gate_eval.PASS, "requirement": "not_applicable"}

    health = [
        record
        for record in logfmt.parse_log(leader_text).records
        if isinstance(record, logfmt.Health) and record.role == "leader"
    ]
    counters: list[dict[str, int]] = []
    lifecycle: list[dict[str, int | str | None]] = []
    mode_applies: list[dict[str, int | str]] = []
    confirm_writes: list[dict[str, int | str]] = []
    counter_keys = (
        "linked",
        "scan_active",
        "scan_start_ok",
        "scan_start_fail",
        "notify",
        "decoded",
        "enqueued",
        "queue_drops",
        "decode_errors",
        "stale_generation_drops",
        "apply_ok",
        "apply_fail",
        "link_up",
        "link_down",
        "connect_fail",
        "confirm_ok",
        "confirm_fail",
        "confirm_pm",
        "confirm_sm",
    )
    for line_index, line in enumerate(leader_text.splitlines()):
        match = _REMOTED_COUNTER_RE.search(line)
        if match is not None:
            counters.append(
                {
                    key: int(value)
                    for key, value in zip(counter_keys, match.groups())
                }
            )
        match = _REMOTED_LINK_RE.search(line)
        if match is not None:
            state, generation, reason = match.groups()
            lifecycle.append(
                {
                    "state": state,
                    "generation": int(generation),
                    "reason": int(reason) if reason is not None else None,
                }
            )
        match = _MODE_APPLY_RE.search(line)
        if match is not None:
            record_id, control, accepted, apply_ok = match.groups()
            mode_applies.append(
                {
                    "record_id": int(record_id),
                    "control": control,
                    "accepted": int(accepted),
                    "apply_ok": int(apply_ok),
                    "line_index": line_index,
                }
            )
        match = _CONFIRM_WRITE_RE.search(line)
        if match is not None:
            ok, cause, record_id, generation, pm, sm = match.groups()
            confirm_writes.append(
                {
                    "ok": int(ok),
                    "cause": cause,
                    "record_id": int(record_id),
                    "generation": int(generation),
                    "pm": int(pm),
                    "sm": int(sm),
                    "line_index": line_index,
                }
            )

    expected_linked = 0 if case_name == "B" else 1
    status_keys = {
        "linked",
        "generation",
        "scan_active",
        "scan_start_ok",
        "scan_start_fail",
        "notify",
        "decoded",
        "enqueued",
        "apply_ok",
        "apply_fail",
        "queue_drops",
        "decode_errors",
        "stale_generation_drops",
        "dial_mode_apply_ok",
        "confirm_write_ok",
        "confirm_write_fail",
        "dial_confirm_write_ok",
        "last_confirm_pm",
        "last_confirm_sm",
    }
    baseline = status_pair.get("baseline") if isinstance(status_pair, dict) else None
    end = status_pair.get("end") if isinstance(status_pair, dict) else None
    status_pair_valid = all(
        isinstance(item, dict)
        and status_keys <= set(item)
        and all(
            isinstance(item[key], int) and item[key] >= 0
            for key in status_keys
        )
        for item in (baseline, end)
    )
    if not status_pair_valid:
        baseline = end = None
    checks: dict[str, object] = {
        "health_samples": len(health),
        "counter_samples": len(counters),
        "status_pair_valid": status_pair_valid,
        "health_exact": (
            len(health) >= MIN_DIAL_SAMPLES
            and all(record.dial_linked == expected_linked for record in health)
        ),
        "counter_link_exact": (
            len(counters) >= MIN_DIAL_SAMPLES
            and all(sample["linked"] == expected_linked for sample in counters)
        ),
        "lifecycle_events": lifecycle,
        "no_lifecycle_events": not lifecycle,
        "baseline": baseline,
        "end": end,
    }
    endpoint_keys = (
        "scan_start_ok",
        "scan_start_fail",
        "notify",
        "decoded",
        "enqueued",
        "apply_ok",
        "apply_fail",
        "queue_drops",
        "decode_errors",
        "stale_generation_drops",
        "dial_mode_apply_ok",
        "confirm_write_ok",
        "confirm_write_fail",
        "dial_confirm_write_ok",
    )
    endpoint_deltas = (
        {key: end[key] - baseline[key] for key in endpoint_keys}
        if baseline is not None and end is not None
        else {}
    )
    checks["endpoint_deltas"] = endpoint_deltas
    checks["endpoint_monotonic"] = bool(endpoint_deltas) and all(
        value >= 0 for value in endpoint_deltas.values()
    )
    checks["endpoint_link_exact"] = (
        baseline is not None
        and end is not None
        and baseline["linked"] == expected_linked
        and end["linked"] == expected_linked
    )
    checks["generation_stable"] = (
        baseline is not None
        and end is not None
        and baseline["generation"] == end["generation"]
    )
    monotonic_counter_keys = (
        "scan_start_ok",
        "scan_start_fail",
        "notify",
        "decoded",
        "enqueued",
        "queue_drops",
        "decode_errors",
        "stale_generation_drops",
        "apply_ok",
        "apply_fail",
        "link_up",
        "link_down",
        "connect_fail",
        "confirm_ok",
        "confirm_fail",
    )
    checks["counter_monotonic"] = all(
        all(later[key] >= earlier[key] for key in monotonic_counter_keys)
        for earlier, later in zip(counters, counters[1:])
    )
    counter_deltas = (
        {
            key: counters[-1][key] - counters[0][key]
            for key in monotonic_counter_keys
        }
        if len(counters) >= MIN_DIAL_SAMPLES
        else {}
    )
    checks["counter_deltas"] = counter_deltas
    shared_counter_endpoint = {
        "scan_start_ok": "scan_start_ok",
        "scan_start_fail": "scan_start_fail",
        "notify": "notify",
        "decoded": "decoded",
        "enqueued": "enqueued",
        "queue_drops": "queue_drops",
        "decode_errors": "decode_errors",
        "stale_generation_drops": "stale_generation_drops",
        "apply_ok": "apply_ok",
        "apply_fail": "apply_fail",
        "confirm_ok": "confirm_write_ok",
        "confirm_fail": "confirm_write_fail",
    }
    # The status endpoints bracket the segment, while the first/last 1 Hz
    # samples necessarily fall inside it. Their deltas therefore cannot be
    # required to match exactly: that would discard traffic before the first
    # periodic sample and after the last. Absolute cumulative values must
    # instead remain bounded by the coherent endpoint snapshots.
    checks["counter_endpoint_bounded"] = (
        len(counters) >= MIN_DIAL_SAMPLES
        and baseline is not None
        and end is not None
        and all(
            baseline[endpoint_key]
            <= counters[0][counter_key]
            <= counters[-1][counter_key]
            <= end[endpoint_key]
            for counter_key, endpoint_key in shared_counter_endpoint.items()
        )
    )
    lifecycle_counter_keys = ("link_up", "link_down", "connect_fail")
    checks["counter_lifecycle_stable"] = (
        len(counters) >= MIN_DIAL_SAMPLES
        and all(
            counters[-1][key] == counters[0][key]
            for key in lifecycle_counter_keys
        )
    )
    if case_name == "B":
        checks["scanner_active_exact"] = (
            len(counters) >= MIN_DIAL_SAMPLES
            and all(sample["scan_active"] == 1 for sample in counters)
            and baseline is not None
            and end is not None
            and baseline["scan_active"] == 1
            and end["scan_active"] == 1
        )
        checks["scanner_start_observed"] = (
            len(counters) >= MIN_DIAL_SAMPLES
            and all(sample["scan_start_ok"] >= 1 for sample in counters)
            and baseline is not None
            and end is not None
            and baseline["scan_start_ok"] >= 1
            and end["scan_start_ok"] >= 1
        )
        zero_delta = bool(endpoint_deltas) and all(
            endpoint_deltas[key] == 0
            for key in (
                "scan_start_ok",
                "scan_start_fail",
                "notify",
                "decoded",
                "enqueued",
                "apply_ok",
                "apply_fail",
                "queue_drops",
                "decode_errors",
                "stale_generation_drops",
                "dial_mode_apply_ok",
                "confirm_write_ok",
                "confirm_write_fail",
                "dial_confirm_write_ok",
            )
        )
        checks["zero_endpoint_delta"] = zero_delta
        checks["counter_lifecycle_zero"] = (
            len(counters) >= MIN_DIAL_SAMPLES
            and all(
                sample[key] == 0
                for sample in counters
                for key in lifecycle_counter_keys
            )
        )
        complete = (
            checks["health_exact"]
            and checks["counter_link_exact"]
            and checks["no_lifecycle_events"]
            and checks["endpoint_link_exact"]
            and checks["generation_stable"]
            and checks["counter_monotonic"]
            and checks["counter_lifecycle_stable"]
            and checks["counter_lifecycle_zero"]
            and checks["scanner_active_exact"]
            and checks["scanner_start_observed"]
            and checks["endpoint_monotonic"]
            and checks["counter_endpoint_bounded"]
            and zero_delta
        )
        observed_contradiction = (
            (
                len(health) >= MIN_DIAL_SAMPLES
                and not checks["health_exact"]
            )
            or (
                len(counters) >= MIN_DIAL_SAMPLES
                and (
                    not checks["counter_link_exact"]
                    or not checks["counter_lifecycle_zero"]
                    or not checks["scanner_active_exact"]
                    or not checks["scanner_start_observed"]
                )
            )
            or not checks["no_lifecycle_events"]
            or (
                len(counters) >= MIN_DIAL_SAMPLES
                and status_pair_valid
                and checks["endpoint_monotonic"]
                and not checks["counter_endpoint_bounded"]
            )
            or (
                status_pair_valid
                and (
                    not checks["endpoint_link_exact"]
                    or not checks["generation_stable"]
                    or not checks["scanner_active_exact"]
                    or not checks["scanner_start_observed"]
                    or (
                        checks["endpoint_monotonic"]
                        and not zero_delta
                    )
                )
            )
        )
        status = (
            gate_eval.PASS
            if complete
            else gate_eval.FAIL
            if observed_contradiction
            else gate_eval.BLOCKED
        )
        return {
            "status": status,
            "requirement": "dial_off",
            "checks": checks,
        }

    checks["traffic_increased"] = bool(endpoint_deltas) and (
        endpoint_deltas["notify"] >= 1
        and all(
                endpoint_deltas[key] >= 4
            for key in (
                "decoded",
                "enqueued",
                "apply_ok",
                "dial_mode_apply_ok",
            )
        )
    )
    checks["traffic_drained"] = bool(endpoint_deltas) and (
        endpoint_deltas["decoded"]
        == endpoint_deltas["enqueued"]
        == endpoint_deltas["apply_ok"]
    )
    checks["counter_traffic_observed"] = bool(counter_deltas) and all(
        counter_deltas[key] >= 1
        for key in ("notify", "decoded", "enqueued", "apply_ok")
    )
    checks["error_deltas_zero"] = bool(endpoint_deltas) and all(
        endpoint_deltas[key] == 0
        for key in (
            "queue_drops",
            "decode_errors",
            "stale_generation_drops",
            "apply_fail",
            "scan_start_fail",
            "confirm_write_fail",
        )
    )
    checks["dial_confirmation_increased"] = bool(endpoint_deltas) and (
        endpoint_deltas["dial_confirm_write_ok"] >= 1
    )
    meaningful_modes: list[dict[str, int | str]] = []
    if baseline is not None:
        confirmed_mode = {
            "primary.mode": baseline["last_confirm_pm"],
            "secondary.mode": baseline["last_confirm_sm"],
        }
        for event in mode_applies:
            control = str(event["control"])
            accepted = int(event["accepted"])
            if (
                int(event["apply_ok"]) > 0
                and accepted != confirmed_mode[control]
            ):
                meaningful_modes.append(event)
                confirmed_mode[control] = accepted
    successful_modes = {
        int(event["record_id"]): event
        for event in meaningful_modes
    }
    causal_confirmations = [
        event
        for event in confirm_writes
        if event["ok"] == 1
        and event["cause"] == "dial_mode"
        and int(event["record_id"]) in successful_modes
        and int(event["line_index"])
        > int(successful_modes[int(event["record_id"])]["line_index"])
        and baseline is not None
        and int(event["generation"]) == baseline["generation"]
        and (
            (
                successful_modes[int(event["record_id"])]["control"]
                == "primary.mode"
                and event["pm"]
                == successful_modes[int(event["record_id"])]["accepted"]
            )
            or (
                successful_modes[int(event["record_id"])]["control"]
                == "secondary.mode"
                and event["sm"]
                == successful_modes[int(event["record_id"])]["accepted"]
            )
        )
    ]
    checks["mode_apply_events"] = mode_applies
    checks["meaningful_mode_changes"] = meaningful_modes
    checks["meaningful_mode_change_count"] = len(meaningful_modes)
    checks["mode_apply_counter_matches_events"] = (
        bool(endpoint_deltas)
        and endpoint_deltas["dial_mode_apply_ok"] == len(meaningful_modes)
    )
    checks["confirm_write_events"] = confirm_writes
    checks["causal_confirmations"] = causal_confirmations
    checks["causal_confirmation_present"] = bool(causal_confirmations)
    complete = (
        checks["health_exact"]
        and checks["counter_link_exact"]
        and checks["no_lifecycle_events"]
        and checks["endpoint_link_exact"]
        and checks["generation_stable"]
        and checks["counter_monotonic"]
        and checks["counter_lifecycle_stable"]
        and checks["endpoint_monotonic"]
        and checks["counter_endpoint_bounded"]
        and checks["traffic_increased"]
        and checks["counter_traffic_observed"]
        and checks["traffic_drained"]
        and checks["meaningful_mode_change_count"] >= 4
        and checks["mode_apply_counter_matches_events"]
        and checks["error_deltas_zero"]
        and checks["dial_confirmation_increased"]
        and checks["causal_confirmation_present"]
    )
    observed_contradiction = (
        (
            len(health) >= MIN_DIAL_SAMPLES
            and not checks["health_exact"]
        )
        or (
            len(counters) >= MIN_DIAL_SAMPLES
            and not checks["counter_link_exact"]
        )
        or not checks["no_lifecycle_events"]
        or (
            len(counters) >= MIN_DIAL_SAMPLES
            and status_pair_valid
            and checks["endpoint_monotonic"]
            and not checks["counter_endpoint_bounded"]
        )
        or (
            status_pair_valid
            and (
                not checks["endpoint_link_exact"]
                or not checks["generation_stable"]
                or (
                    checks["endpoint_monotonic"]
                    and (
                        not checks["traffic_drained"]
                        or not checks["error_deltas_zero"]
                    )
                )
            )
        )
    )
    status = (
        gate_eval.PASS
        if complete
        else gate_eval.FAIL
        if observed_contradiction
        else gate_eval.BLOCKED
    )
    return {
        "status": status,
        "requirement": "dial_on_turned_and_confirmed",
        "checks": checks,
    }


def _expected_device(case_name: str, role: str) -> dict[str, str]:
    if role == "leader":
        return {
            "chip_id": LEADER_CHIP,
            "env": CASE_CONTRACT[case_name]["leader_env"],
        }
    return {"chip_id": FOLLOWER_CHIP, "env": FOLLOWER_ENV}


def _validate_flash_manifest(
    path: Path,
    *,
    case_name: str,
    firmware_sha: str,
    host_sha: str,
    out_root: Path,
    tracked_root: Path,
    repo_root: Path,
    ports: dict[str, str],
) -> tuple[dict, dict[str, dict[str, str]]]:
    path = _require_direct_file(
        path, tracked_root / "uploads", "flash manifest"
    )
    payload = _read_manifest(path)
    expected_flash_case = (
        "B" if case_name in ("C1", "C2") else case_name
    )
    required = {
        "schema_version": 2,
        "status": gate_eval.PASS,
        "run_id": tracked_root.name,
        "case": expected_flash_case,
        "host_execution_sha": host_sha,
        "firmware_source_sha": firmware_sha,
    }
    for key, expected in required.items():
        if payload.get(key) != expected:
            raise F2ContractError(
                f"flash manifest requires {key}={expected!r}"
            )
    _validate_evidence_record(
        payload.get("image_set"),
        repo_root,
        repo_root,
        "flash image-set manifest",
    )
    _validate_evidence_record(
        payload.get("input_ports_manifest"),
        repo_root,
        tracked_root / "runtime",
        "flash input ports manifest",
    )
    _validate_evidence_record(
        payload.get("output_ports_manifest"),
        repo_root,
        tracked_root / "runtime",
        "flash output ports manifest",
    )
    _validate_startup_capture_payload(
        payload.get("startup_capture"),
        repo_root,
        out_root / "uploads" / f"case_{expected_flash_case}",
        f"Case {expected_flash_case} post-write startup",
    )
    uploads = payload.get("uploads")
    if not isinstance(uploads, dict):
        raise F2ContractError("flash manifest uploads are missing")
    binaries: dict[str, dict[str, str]] = {}
    for role in ("leader", "follower"):
        upload = uploads.get(role)
        if not isinstance(upload, dict):
            raise F2ContractError(f"flash manifest missing {role} upload")
        expected = _expected_device(expected_flash_case, role)
        source_case = (
            "A"
            if expected_flash_case == "B" and role == "follower"
            else expected_flash_case
        )
        expected_action = (
            "reuse" if source_case != expected_flash_case else "flash"
        )
        upload_port = upload.get("port")
        if not isinstance(upload_port, str) or not upload_port:
            raise F2ContractError(
                f"flash manifest {role} upload port is missing"
            )
        expected_guard = [
            "python3",
            "scripts/platformio/k1_upload_guard.py",
            "--env",
            expected["env"],
            "--upload-port",
            upload_port,
        ]
        expected_usb_serial = (
            LEADER_USB_SERIAL if role == "leader" else FOLLOWER_USB_SERIAL
        )
        required_upload = {
            "action": expected_action,
            "source_case": source_case,
            "env": expected["env"],
            "chip_id": expected["chip_id"],
            "usb_serial": expected_usb_serial,
            "guard_verified": True,
            "guard_command": expected_guard,
            "cross_target_guard_verified": True,
            "cross_target_guard_exit_code": 2,
        }
        for key, expected_value in required_upload.items():
            if upload.get(key) != expected_value:
                raise F2ContractError(
                    f"flash manifest {role} requires "
                    f"{key}={expected_value!r}"
                )
        if expected_action == "flash":
            cross_guard = upload.get("cross_target_guard_command")
            expected_cross_guard = [
                "python3",
                "scripts/platformio/k1_upload_guard.py",
                "--env",
                (
                    "k1_sync_probe_bench"
                    if role == "leader"
                    else "k1_sync_probe_main_sync_only"
                ),
                "--upload-port",
                upload_port,
            ]
            if cross_guard != expected_cross_guard:
                raise F2ContractError(
                    f"flash manifest {role} cross-target guard mismatch"
                )
            _validate_evidence_record(
                upload.get("cross_target_guard_log"),
                repo_root,
                out_root / "uploads",
                f"flash {role} cross-target guard log",
            )
            write_command = upload.get("write_command")
            if (
                not isinstance(write_command, list)
                or "write_flash" not in write_command
                or "pio" not in write_command
                or "pkg" not in write_command
                or "run" in write_command
                or upload.get("write_exit_code") != 0
            ):
                raise F2ContractError(
                    f"flash manifest {role} lacks exact app-only write"
                )
            partition = upload.get("partition_table")
            if not isinstance(partition, dict):
                raise F2ContractError(
                    f"flash manifest {role} partition proof is missing"
                )
            _validate_evidence_record(
                partition.get("readback"),
                repo_root,
                out_root / "uploads",
                f"flash {role} partition read-back",
            )
        binaries[role] = {}
        for kind in ("bin", "elf"):
            path_key = f"{kind}_path"
            hash_key = f"{kind}_sha256"
            if (
                not isinstance(upload.get(path_key), str)
                or not isinstance(upload.get(hash_key), str)
                or re.fullmatch(r"[0-9a-f]{64}", upload[hash_key]) is None
            ):
                raise F2ContractError(
                    f"flash manifest {role} {kind} identity is malformed"
                )
            artefact_path = _require_direct_file(
                repo_root / upload[path_key],
                repo_root / "_scratch",
                f"flash {role} {kind}",
            )
            if _sha256(artefact_path) != upload[hash_key]:
                raise F2ContractError(
                    f"flash manifest {role} {kind} hash mismatch"
                )
            binaries[role][path_key] = _repo_relative(
                artefact_path, repo_root
            )
            binaries[role][hash_key] = upload[hash_key]
        preflash = upload.get("preflash_identity")
        if preflash != {
            "port": upload_port,
            "usb_serial": expected_usb_serial,
            "chip_id": expected["chip_id"],
        }:
            raise F2ContractError(
                f"flash manifest {role} pre-flash identity mismatch"
            )
        if expected_action == "reuse":
            reuse_preflight = upload.get("reuse_preflight_identity")
            if reuse_preflight != {
                "port": ports[role],
                "usb_serial": expected_usb_serial,
                "chip_id": expected["chip_id"],
            }:
                raise F2ContractError(
                    f"flash manifest {role} reuse preflight mismatch"
                )
            reused_path = _validate_evidence_record(
                upload.get("reused_flash_manifest"),
                repo_root,
                tracked_root / "uploads",
                f"flash {role} reused upload",
            )
            reused_payload = _read_manifest(reused_path)
            original = reused_payload.get("uploads", {}).get(role)
            if not isinstance(original, dict):
                raise F2ContractError(
                    f"flash manifest {role} reused event is missing"
                )
            copied = {
                key: value
                for key, value in upload.items()
                if key
                not in {
                    "action",
                    "source_case",
                    "reused_flash_manifest",
                    "reuse_preflight_identity",
                }
            }
            original_base = {
                key: value
                for key, value in original.items()
                if key not in {"action", "source_case"}
            }
            if copied != original_base:
                raise F2ContractError(
                    f"flash manifest {role} reused event drift"
                )
        image_id = upload.get("app_elf_sha256")
        if not isinstance(image_id, str) or re.fullmatch(
            r"[0-9a-f]{64}", image_id
        ) is None:
            raise F2ContractError(
                f"flash manifest {role} app ELF identity is malformed"
            )
        if (
            image_id != binaries[role]["elf_sha256"]
            or image_id != _app_elf_sha256(
                repo_root / binaries[role]["bin_path"]
            )
        ):
            raise F2ContractError(
                f"flash manifest {role} app ELF identity mismatch"
            )
        readback = upload.get("postflash_readback")
        if not isinstance(readback, dict) or (
            readback.get("chip_id") != expected["chip_id"]
            or readback.get("env") != expected["env"]
            or (
                expected_action == "flash"
                and readback.get("port") != ports[role]
            )
            or readback.get("app_elf_sha256") != image_id
            or not _valid_git_prefix(
                firmware_sha, readback.get("git")
            )
        ):
            raise F2ContractError(
                f"flash manifest {role} post-flash read-back mismatch"
            )
        if (
            re.fullmatch(
                r"[0-9a-f]{16}", str(readback.get("boot_nonce", ""))
            )
            is None
            or not isinstance(readback.get("uptime_ms"), int)
            or readback["uptime_ms"] < 0
            or not isinstance(readback.get("reset_reason"), int)
        ):
            raise F2ContractError(
                f"flash manifest {role} runtime identity is malformed"
            )
        log_record = upload.get("log")
        _validate_evidence_record(
            log_record, repo_root, repo_root / "_scratch",
            f"flash {role} log"
        )
    return payload, binaries


def _runtime_continuity(
    identity: dict,
    flash_payload: dict,
    prior_runtime: dict | None = None,
    *,
    case_name: str = "C1",
    firmware_sha: str | None = None,
    reboot_payload: dict | None = None,
) -> tuple[dict, dict]:
    runtime: dict[str, dict[str, int | str]] = {}
    checks: dict[str, dict[str, bool]] = {}
    for role in ("leader", "follower"):
        observed = identity.get(role)
        readback = flash_payload["uploads"][role]["postflash_readback"]
        if not isinstance(observed, dict):
            runtime[role] = {}
            checks[role] = {"identity_present": False}
            continue
        runtime[role] = {
            "app_elf_sha256": observed.get("app_elf_sha256"),
            "git": observed.get("git"),
            "env": observed.get("env"),
            "boot_nonce": observed.get("boot_nonce"),
            "uptime_ms": observed.get("uptime_ms"),
            "reset_reason": observed.get("reset_reason"),
        }
        prior = prior_runtime.get(role) if prior_runtime else None
        expected_env = flash_payload["uploads"][role]["env"]
        expected_image = flash_payload["uploads"][role]["app_elf_sha256"]
        source_ok = (
            firmware_sha is None
            or _valid_git_prefix(firmware_sha, observed.get("git"))
        )
        if case_name == "A" or (case_name == "B" and role == "leader"):
            transition_ok = (
                observed.get("boot_nonce") == readback.get("boot_nonce")
                and isinstance(observed.get("uptime_ms"), int)
                and observed["uptime_ms"] >= readback.get("uptime_ms", -1)
            )
        elif case_name in ("B", "C1"):
            transition_ok = (
                isinstance(prior, dict)
                and observed.get("boot_nonce") == prior.get("boot_nonce")
                and isinstance(prior.get("uptime_ms"), int)
                and isinstance(observed.get("uptime_ms"), int)
                and observed["uptime_ms"] > prior["uptime_ms"]
            )
        elif case_name == "C2":
            reboot_role = (
                reboot_payload.get("roles", {}).get(role, {})
                if isinstance(reboot_payload, dict)
                else {}
            )
            expected_after = reboot_role.get("after", {})
            transition_ok = (
                isinstance(prior, dict)
                and isinstance(expected_after, dict)
                and observed.get("boot_nonce")
                == expected_after.get("boot_nonce")
                and observed.get("boot_nonce") != prior.get("boot_nonce")
                and observed.get("app_elf_sha256")
                == expected_after.get("app_elf_sha256")
                and isinstance(observed.get("uptime_ms"), int)
                and observed["uptime_ms"]
                >= expected_after.get("uptime_ms", -1)
            )
        else:
            transition_ok = False
        checks[role] = {
            "application_identity": (
                observed.get("app_elf_sha256") == expected_image
            ),
            "firmware_source": source_ok,
            "environment": observed.get("env") == expected_env,
            "transition_continuity": transition_ok,
        }
    result = {
        "status": (
            gate_eval.PASS
            if all(all(role_checks.values()) for role_checks in checks.values())
            else gate_eval.BLOCKED
        ),
        "checks": checks,
    }
    return runtime, result


def _case_status(
    link_ready: str, dial_status: str, runtime_status: str
) -> str:
    if link_ready == gate_eval.FAIL or dial_status == gate_eval.FAIL:
        return gate_eval.FAIL
    if (
        link_ready == gate_eval.PASS
        and dial_status == gate_eval.PASS
        and runtime_status == gate_eval.PASS
    ):
        return gate_eval.PASS
    return gate_eval.BLOCKED


def _validate_c2_startup_capture(
    reboot_payload: dict, repo_root: Path, tracked_root: Path
) -> dict:
    return _validate_startup_capture_payload(
        reboot_payload.get("cold_start_capture"),
        repo_root,
        tracked_root / "runtime",
        "controlled C2 reboot",
    )


def _validate_startup_capture_payload(
    startup: object,
    repo_root: Path,
    allowed_root: Path,
    label: str,
) -> dict:
    required_checks = {
        "leader_advertising_ready",
        "follower_scan_started",
        "follower_uuid_discovered",
        "leader_link_ready_snapshot",
        "follower_link_ready_snapshot",
    }
    if (
        not isinstance(startup, dict)
        or startup.get("status") != gate_eval.PASS
        or not isinstance(startup.get("checks"), dict)
        or not all(
            startup["checks"].get(check) is True
            for check in required_checks
        )
    ):
        raise F2ContractError(
            f"{label} lacks cold-start establishment PASS"
        )
    logs = startup.get("logs")
    if not isinstance(logs, dict) or set(logs) != {"leader", "follower"}:
        raise F2ContractError(f"{label} startup logs are missing")
    for role, record in logs.items():
        _validate_evidence_record(
            record,
            repo_root,
            allowed_root,
            f"{label} {role} startup log",
        )
    return startup


def _validate_prior_case(
    path: Path,
    *,
    case_name: str,
    firmware_sha: str,
    host_sha: str,
    repo_root: Path,
    out_root: Path,
    tracked_root: Path,
    previous_digest: str | None,
    prior_runtime: dict | None,
) -> dict:
    path = _require_direct_file(
        path, tracked_root, f"prior Case {case_name} manifest"
    )
    manifest = _read_manifest(path)
    required = {
        "schema_version": SCHEMA_VERSION,
        "run_id": tracked_root.name,
        "case": case_name,
        "case_status": gate_eval.PASS,
        "host_execution_sha": host_sha,
        "firmware_source_sha": firmware_sha,
        "prior_manifest_sha256": previous_digest,
    }
    for key, expected in required.items():
        if manifest.get(key) != expected:
            raise F2ContractError(
                f"prior Case {case_name} requires {key}={expected!r}"
            )
    link_ready = manifest.get("link_ready")
    if not isinstance(link_ready, dict) or link_ready.get("status") != gate_eval.PASS:
        raise F2ContractError(f"prior Case {case_name} lacks Link Ready PASS")
    dial = manifest.get("dial_evidence")
    if not isinstance(dial, dict) or dial.get("status") != gate_eval.PASS:
        raise F2ContractError(f"prior Case {case_name} lacks dial proof")
    records = manifest.get("raw_evidence")
    if not isinstance(records, dict) or not records:
        raise F2ContractError(
            f"prior Case {case_name} raw evidence is missing"
        )
    case_root = out_root / f"case_{case_name}"
    evidence_paths: dict[str, Path] = {}
    for label, record in records.items():
        evidence_paths[label] = _validate_evidence_record(
            record, repo_root, case_root, f"Case {case_name} {label}"
        )
    flash = manifest.get("flash_manifest")
    flash_path = _validate_evidence_record(
        flash, repo_root, tracked_root / "uploads",
        f"Case {case_name} flash manifest"
    )
    attestation = manifest.get("attestation")
    attestation_path = _validate_evidence_record(
        attestation, repo_root, tracked_root / "attestations",
        f"Case {case_name} attestation"
    )
    _validate_attestation(attestation_path, case_name)
    ports_record = manifest.get(
        "output_ports_manifest"
        if case_name == "C1"
        else "ports_manifest"
    )
    ports_path = _validate_evidence_record(
        ports_record,
        repo_root,
        tracked_root / "runtime",
        f"Case {case_name} ports manifest",
    )
    try:
        f2_ports.validate_ports_manifest(
            ports_path,
            expected_stage=case_name,
            expected_host_execution_sha=host_sha,
            expected_firmware_source_sha=firmware_sha,
        )
    except f2_ports.F2PortsError as error:
        raise F2ContractError(
            f"prior Case {case_name} ports chain mismatch: {error}"
        ) from error

    required_evidence = {
        "leader_session",
        "follower_session",
        "leader_segment",
        "follower_segment",
        "leader_proof",
        "follower_proof",
        "verdict",
        "identity",
        "sync_status",
        "index",
    }
    if case_name in ("B", "C1", "C2"):
        required_evidence.add("dial_status")
    missing = sorted(required_evidence - set(evidence_paths))
    if missing:
        raise F2ContractError(
            f"prior Case {case_name} evidence fields missing: {missing}"
        )
    try:
        recomputed = gate_eval.evaluate(
            evidence_paths["leader_proof"].read_text(
                encoding="utf-8", errors="replace"
            ),
            evidence_paths["follower_proof"].read_text(
                encoding="utf-8", errors="replace"
            ),
            strict_proof=True,
        )
    except (logfmt.LogContractError, ValueError) as error:
        raise F2ContractError(
            f"prior Case {case_name} proof cannot be re-evaluated: {error}"
        ) from error
    if recomputed.get("link_ready") != manifest.get("link_ready"):
        raise F2ContractError(
            f"prior Case {case_name} Link Ready derivation mismatch"
        )
    stored_verdict = _read_manifest(evidence_paths["verdict"])
    if stored_verdict != recomputed:
        raise F2ContractError(
            f"prior Case {case_name} verdict derivation mismatch"
        )
    negotiated = _read_manifest(evidence_paths["sync_status"])
    if negotiated != manifest.get("negotiated"):
        raise F2ContractError(
            f"prior Case {case_name} negotiated derivation mismatch"
        )
    if (
        recomputed["link_ready"]["checks"]["single_link_epoch"]
        != manifest.get("connection_counts")
    ):
        raise F2ContractError(
            f"prior Case {case_name} connection counts mismatch"
        )

    identity = _read_manifest(evidence_paths["identity"])
    ports: dict[str, str] = {}
    for role in ("leader", "follower"):
        expected = _expected_device(case_name, role)
        device = manifest.get(role)
        observed = identity.get(role)
        if not isinstance(device, dict) or not isinstance(observed, dict):
            raise F2ContractError(
                f"prior Case {case_name} {role} identity is missing"
            )
        ports[role] = str(device.get("port"))
        if (
            device.get("chip_id") != expected["chip_id"]
            or device.get("env") != expected["env"]
            or observed.get("chip_id") != expected["chip_id"]
            or observed.get("env") != expected["env"]
            or not _valid_git_prefix(
                firmware_sha, observed.get("git")
            )
        ):
            raise F2ContractError(
                f"prior Case {case_name} {role} identity mismatch"
            )
    stored_binaries = manifest.get("binaries")
    if not isinstance(stored_binaries, dict):
        raise F2ContractError(
            f"prior Case {case_name} binaries are missing"
        )
    flash_payload, binaries = _validate_flash_manifest(
        flash_path,
        case_name=case_name,
        firmware_sha=firmware_sha,
        host_sha=host_sha,
        out_root=out_root,
        tracked_root=tracked_root,
        repo_root=repo_root,
        ports=ports,
    )
    if binaries != stored_binaries:
        raise F2ContractError(
            f"prior Case {case_name} binary derivation mismatch"
        )
    for role in ("leader", "follower"):
        if identity[role].get("app_elf_sha256") != (
            flash_payload["uploads"][role]["app_elf_sha256"]
        ):
            raise F2ContractError(
                f"prior Case {case_name} {role} image identity mismatch"
            )
    reboot_payload = None
    if case_name == "C2":
        reboot_record = manifest.get("reboot_manifest")
        reboot_path = _validate_evidence_record(
            reboot_record,
            repo_root,
            tracked_root / "runtime",
            "Case C2 reboot manifest",
        )
        reboot_payload = _read_manifest(reboot_path)
        startup = _validate_c2_startup_capture(
            reboot_payload, repo_root, tracked_root
        )
        if manifest.get("cold_start_establishment") != startup["checks"]:
            raise F2ContractError(
                "prior Case C2 cold-start establishment mismatch"
            )
    runtime_identity, runtime_continuity = _runtime_continuity(
        identity,
        flash_payload,
        prior_runtime,
        case_name=case_name,
        firmware_sha=firmware_sha,
        reboot_payload=reboot_payload,
    )
    if (
        runtime_identity != manifest.get("runtime_identity")
        or runtime_continuity != manifest.get("runtime_continuity")
        or runtime_continuity["status"] != gate_eval.PASS
    ):
        raise F2ContractError(
            f"prior Case {case_name} runtime continuity mismatch"
        )
    status_pair = None
    if case_name in ("B", "C1", "C2"):
        status_payload = _read_manifest(evidence_paths["dial_status"])
        status_pair = status_payload.get("off")
    dial = _analyse_dial(
        case_name,
        evidence_paths["leader_segment"].read_text(
            encoding="utf-8", errors="replace"
        ),
        status_pair,
    )
    if dial != manifest.get("dial_evidence"):
        raise F2ContractError(
            f"prior Case {case_name} dial derivation mismatch"
        )
    return manifest


def validate_case_order(
    case_name: str,
    out_root: Path,
    tracked_root: Path,
    firmware_sha: str,
    host_sha: str,
    repo_root: Path,
) -> list[dict]:
    prior_names = {
        "A": (),
        "B": ("A",),
        "C1": ("A", "B"),
        "C2": ("A", "B", "C1"),
    }[case_name]
    prior: list[dict] = []
    previous_digest: str | None = None
    for prior_name in prior_names:
        path = tracked_root / f"case_{prior_name}.json"
        manifest = _validate_prior_case(
            path,
            case_name=prior_name,
            firmware_sha=firmware_sha,
            host_sha=host_sha,
            repo_root=repo_root,
            out_root=out_root,
            tracked_root=tracked_root,
            previous_digest=previous_digest,
            prior_runtime=(
                prior[-1].get("runtime_identity") if prior else None
            ),
        )
        previous_digest = _sha256(path)
        prior.append(manifest)
    return prior


def _atomic_manifest(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise F2ContractError(f"refusing to overwrite manifest {path}")
    temporary = path.with_name(f".{path.name}.tmp")
    with temporary.open("x", encoding="utf-8") as output:
        json.dump(payload, output, indent=2, sort_keys=True)
        output.write("\n")
        output.flush()
        os.fsync(output.fileno())
    os.replace(temporary, path)


def _run_tracked_root(repo_root: Path, run_root: Path) -> Path:
    raw_root = run_root.resolve()
    scratch_root = repo_root / "_scratch"
    if not _inside(raw_root, scratch_root) or not raw_root.name.startswith(
        "dual_sync_f2_abc_"
    ):
        raise F2ContractError(
            "F2 raw root must be _scratch/dual_sync_f2_abc_<stamp>"
        )
    run_id = raw_root.name.removeprefix("dual_sync_f2_abc_")
    _validate_run_id(run_id)
    tracked_root = repo_root / TRACKED_F2_REL / run_id
    if _has_symlink_component(tracked_root) or not _inside(
        tracked_root, repo_root / TRACKED_F2_REL
    ):
        raise F2ContractError("F2 tracked root is not a direct evidence path")
    return tracked_root


def _close_run_for_host_drift(
    repo_root: Path,
    run_root: Path,
    *,
    expected_host_sha: str,
    observed_host_sha: str,
) -> Path | None:
    """Write one immutable global BLOCKED marker for a started run."""
    tracked_root = _run_tracked_root(repo_root, run_root)
    if not tracked_root.is_dir():
        return None
    marker = tracked_root / "RUN_BLOCKED.json"
    _atomic_manifest(
        marker,
        {
            "schema_version": 1,
            "status": gate_eval.BLOCKED,
            "reason": "host_execution_sha_changed_after_run_creation",
            "expected_host_execution_sha": expected_host_sha,
            "observed_host_execution_sha": observed_host_sha,
            "created_at_utc": datetime.now(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "f3_authorised": False,
        },
    )
    return marker


def _require_run_open(repo_root: Path, run_root: Path) -> None:
    marker = _run_tracked_root(repo_root, run_root) / "RUN_BLOCKED.json"
    if marker.exists() or marker.is_symlink():
        raise F2ContractError(
            f"F2 run is already closed as BLOCKED: {marker}"
        )


def _capture_command(args, firmware_sha: str) -> list[str]:
    command = [
        "bash",
        "scripts/dual_sync_probe/run_f2_abc.sh",
        "--case",
        args.case,
        "--physical-state",
        args.physical_state,
        "--host-execution-sha",
        args.host_execution_sha,
        "--firmware-source-sha",
        firmware_sha,
        "--image-set-manifest",
        str(args.image_set_manifest),
        "--ports-manifest",
        str(args.ports_manifest),
        "--run-root",
        str(args.run_root),
        "--flash-manifest",
        str(args.flash_manifest),
        "--attestation",
        str(args.attestation),
        "--duration-s",
        str(args.duration_s),
        "--settle-s",
        str(args.settle_s),
        "--ack-timeout-s",
        str(args.ack_timeout_s),
        "--baud",
        str(args.baud),
    ]
    if args.reboot_manifest is not None:
        command.extend(
            ["--reboot-manifest", str(args.reboot_manifest)]
        )
    return command


def run(args) -> dict:
    repo_root = Path(__file__).resolve().parents[2]
    _require_clean_host_inputs(repo_root)
    host_sha = _git_head(repo_root)
    if host_sha != args.host_execution_sha:
        _close_run_for_host_drift(
            repo_root,
            args.run_root,
            expected_host_sha=args.host_execution_sha,
            observed_host_sha=host_sha,
        )
        raise F2ContractError(
            "host execution SHA does not equal current committed HEAD"
        )
    image_set = f2_image_set.load(
        args.image_set_manifest, repo_root=repo_root
    )
    firmware_sha = _resolve_commit(
        repo_root, args.firmware_source_sha
    )
    if (
        firmware_sha != args.firmware_source_sha
        or firmware_sha != image_set["firmware_source_sha"]
    ):
        raise F2ContractError(
            "firmware source SHA does not match the reviewed image set"
        )
    _require_ancestor(repo_root, firmware_sha, host_sha)
    contract = CASE_CONTRACT[args.case]
    if args.physical_state != contract["physical_state"]:
        raise F2ContractError(
            f"Case {args.case} requires physical state "
            f"{contract['physical_state']}"
        )
    if args.duration_s < MIN_CAPTURE_SECONDS:
        raise F2ContractError(
            f"F2 capture duration must be at least {MIN_CAPTURE_SECONDS:g}s"
        )
    if args.case == "C2" and args.reboot_manifest is None:
        raise F2ContractError("Case C2 requires --reboot-manifest")
    if args.case != "C2" and args.reboot_manifest is not None:
        raise F2ContractError(
            "--reboot-manifest is valid only for Case C2"
        )
    if _has_symlink_component(args.run_root):
        raise F2ContractError("F2 raw root may not contain symlinks")
    out_root = args.run_root.resolve()
    scratch_root = repo_root / "_scratch"
    if not _inside(out_root, scratch_root) or not out_root.name.startswith(
        "dual_sync_f2_abc_"
    ):
        raise F2ContractError(
            "F2 raw root must be _scratch/dual_sync_f2_abc_<stamp>"
        )
    run_id = out_root.name.removeprefix("dual_sync_f2_abc_")
    _validate_run_id(run_id)
    tracked_root = repo_root / TRACKED_F2_REL / run_id
    if _has_symlink_component(tracked_root):
        raise F2ContractError("F2 tracked root may not contain symlinks")
    if not _inside(tracked_root, repo_root / TRACKED_F2_REL):
        raise F2ContractError("F2 tracked root escapes fixed evidence root")
    _require_run_open(repo_root, args.run_root)
    tracked_case = tracked_root / f"case_{args.case}.json"
    if tracked_case.exists():
        raise F2ContractError(
            f"refusing to overwrite tracked Case {args.case} evidence"
        )
    attestation_path = _require_direct_file(
        args.attestation,
        tracked_root / "attestations",
        "physical attestation",
    )
    attestation_payload = _validate_attestation(
        attestation_path, args.case
    )
    prior = validate_case_order(
        args.case,
        out_root,
        tracked_root,
        firmware_sha,
        host_sha,
        repo_root,
    )

    expected_ports_stage = {
        "A": "A",
        "B": "B",
        "C1": "B",
        "C2": "C2",
    }[args.case]
    try:
        ports_payload = f2_ports.validate_ports_manifest(
            args.ports_manifest,
            expected_stage=expected_ports_stage,
            expected_host_execution_sha=host_sha,
            expected_firmware_source_sha=firmware_sha,
        )
    except f2_ports.F2PortsError as error:
        raise F2ContractError(f"ports manifest rejected: {error}") from error
    ports = {
        role: str(ports_payload[role]["port"])
        for role in ("leader", "follower")
    }
    flash_manifest_path = _require_direct_file(
        args.flash_manifest,
        tracked_root / "uploads",
        "flash manifest",
    )
    flash_payload, binaries = _validate_flash_manifest(
        flash_manifest_path,
        case_name=args.case,
        firmware_sha=firmware_sha,
        host_sha=host_sha,
        out_root=out_root,
        tracked_root=tracked_root,
        repo_root=repo_root,
        ports=ports,
    )

    if args.case in ("C1", "C2"):
        case_b = prior[-1]
        if case_b.get("binaries") != binaries:
            raise F2ContractError(
                f"Case {args.case} must use the exact Case-B binaries"
            )
        if case_b.get("flash_manifest", {}).get("sha256") != _sha256(
            flash_manifest_path
        ):
            raise F2ContractError(
                f"Case {args.case} must reuse the Case-B flash manifest"
            )

    expectations = {
        "leader": {
            "chip_id": LEADER_CHIP,
            "env": contract["leader_env"],
            "source_sha": firmware_sha,
            "app_elf_sha256": flash_payload["uploads"]["leader"][
                "app_elf_sha256"
            ],
        },
        "follower": {
            "chip_id": FOLLOWER_CHIP,
            "env": FOLLOWER_ENV,
            "source_sha": firmware_sha,
            "app_elf_sha256": flash_payload["uploads"]["follower"][
                "app_elf_sha256"
            ],
        },
    }
    case_dir = out_root / f"case_{args.case}"
    results = capture.run_segments(
        leader_port=ports["leader"],
        follower_port=ports["follower"],
        out_dir=case_dir,
        segments=("off",),
        duration_s=args.duration_s,
        ack_timeout_s=args.ack_timeout_s,
        settle_s=args.settle_s,
        baud=args.baud,
        identity_expectations=expectations,
        leader_ble_stream=args.case in ("B", "C1", "C2"),
        leader_dial_status=args.case in ("B", "C1", "C2"),
    )
    link_ready = results[0]["link_ready"]
    verdict_path = case_dir / "off" / "verdict_off.json"
    verdict = _read_manifest(verdict_path)
    identity_payload = _read_manifest(case_dir / "IDENTITY.json")
    prior_runtime = (
        prior[-1].get("runtime_identity")
        if args.case in ("B", "C1", "C2") and prior
        else None
    )
    reboot_payload = None
    reboot_manifest_path = None
    if args.case == "C2":
        reboot_manifest_path = _require_direct_file(
            args.reboot_manifest,
            tracked_root / "runtime",
            "controlled C2 reboot manifest",
        )
        reboot_payload = _read_manifest(reboot_manifest_path)
        if (
            reboot_payload.get("status") != gate_eval.PASS
            or reboot_payload.get("host_execution_sha") != host_sha
            or reboot_payload.get("firmware_source_sha") != firmware_sha
        ):
            raise F2ContractError(
                "controlled C2 reboot manifest is not a bound PASS"
            )
        startup = _validate_c2_startup_capture(
            reboot_payload, repo_root, tracked_root
        )
    runtime_identity, runtime_continuity = _runtime_continuity(
        identity_payload,
        flash_payload,
        prior_runtime,
        case_name=args.case,
        firmware_sha=firmware_sha,
        reboot_payload=reboot_payload,
    )
    leader_segment_path = case_dir / "off" / "leader_segment.log"
    dial_status_path = case_dir / "DIAL_STATUS.json"
    dial_status = (
        _read_manifest(dial_status_path).get("off")
        if args.case in ("B", "C1", "C2")
        else None
    )
    dial_evidence = _analyse_dial(
        args.case,
        leader_segment_path.read_text(encoding="utf-8", errors="replace"),
        dial_status,
    )
    evidence_paths = {
        "leader_session": case_dir / "leader_session.log",
        "follower_session": case_dir / "follower_session.log",
        "leader_segment": leader_segment_path,
        "follower_segment": case_dir / "off" / "follower_segment.log",
        "leader_proof": case_dir / "off" / "leader.log",
        "follower_proof": case_dir / "off" / "follower.log",
        "verdict": verdict_path,
        "identity": case_dir / "IDENTITY.json",
        "sync_status": case_dir / "SYNC_STATUS.json",
        "index": case_dir / "INDEX.md",
    }
    if args.case in ("B", "C1", "C2"):
        evidence_paths["dial_status"] = dial_status_path
    prior_digest = (
        _sha256(tracked_root / f"case_{prior[-1]['case']}.json")
        if prior
        else None
    )
    status = _case_status(
        link_ready,
        dial_evidence["status"],
        runtime_continuity["status"],
    )
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "case": args.case,
        "case_status": status,
        "link_ready": verdict["link_ready"],
        "connection_counts": verdict["link_ready"]["checks"][
            "single_link_epoch"
        ],
        "negotiated": _read_manifest(case_dir / "SYNC_STATUS.json"),
        "dial_evidence": dial_evidence,
        "runtime_identity": runtime_identity,
        "runtime_continuity": runtime_continuity,
        "physical_state": args.physical_state,
        "host_execution_sha": host_sha,
        "firmware_source_sha": firmware_sha,
        "prior_manifest_sha256": prior_digest,
        "leader": {
            "port": ports["leader"],
            "chip_id": LEADER_CHIP,
            "env": contract["leader_env"],
        },
        "follower": {
            "port": ports["follower"],
            "chip_id": FOLLOWER_CHIP,
            "env": FOLLOWER_ENV,
        },
        "binaries": binaries,
        "flash_manifest": _evidence_record(
            flash_manifest_path, repo_root
        ),
        "image_set_manifest": _evidence_record(
            image_set["manifest_path"], repo_root
        ),
        "ports_manifest": _evidence_record(
            args.ports_manifest, repo_root
        ),
        "attestation": _evidence_record(attestation_path, repo_root),
        "attestation_summary": attestation_payload,
        "commands": {
            "capture": _capture_command(args, firmware_sha),
            "firmware_writes": {
                role: flash_payload["uploads"][role].get("write_command")
                for role in ("leader", "follower")
            },
            "serial": (
                [":chip_id", ":build", ":image_id", ":runtime_id",
                 ":sync_status",
                 ":sync_fault=off"]
                if args.case == "A"
                else [
                    ":chip_id",
                    ":build",
                    ":image_id",
                    ":runtime_id",
                    ":sync_status",
                    ":ble_stream=on",
                    ":dial_status",
                    ":sync_fault=off",
                    ":dial_status",
                    ":ble_stream=off",
                ]
            ),
        },
        "capture_parameters": {
            "duration_s": args.duration_s,
            "settle_s": args.settle_s,
            "ack_timeout_s": args.ack_timeout_s,
            "baud": args.baud,
            "segments": ["off"],
        },
        "raw_evidence": {
            name: _evidence_record(path, repo_root)
            for name, path in evidence_paths.items()
        },
    }
    if reboot_manifest_path is not None:
        manifest["reboot_manifest"] = _evidence_record(
            reboot_manifest_path, repo_root
        )
        manifest["cold_start_establishment"] = startup["checks"]
    if args.case == "C1":
        try:
            f2_ports.write_ports_manifest(
                "C1",
                tracked_root / "runtime",
                {
                    "leader": ports_payload["leader"],
                    "follower": ports_payload["follower"],
                },
                host_execution_sha=host_sha,
                firmware_source_sha=firmware_sha,
                prior_manifest=args.ports_manifest,
            )
        except f2_ports.F2PortsError as error:
            raise F2ContractError(
                f"cannot persist ports_C1.json: {error}"
            ) from error
        manifest["output_ports_manifest"] = _evidence_record(
            tracked_root / "runtime" / "ports_C1.json", repo_root
        )
    _atomic_manifest(case_dir / "MANIFEST.json", manifest)
    _atomic_manifest(tracked_case, manifest)
    return manifest


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Capture one ordered, identity-checked F2 A/B/C1/C2 case."
        )
    )
    parser.add_argument("--case", choices=tuple(CASE_CONTRACT), required=True)
    parser.add_argument("--physical-state", required=True)
    parser.add_argument("--host-execution-sha", required=True)
    parser.add_argument("--firmware-source-sha", required=True)
    parser.add_argument("--image-set-manifest", type=Path, required=True)
    parser.add_argument("--ports-manifest", type=Path, required=True)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--flash-manifest", type=Path, required=True)
    parser.add_argument("--attestation", type=Path, required=True)
    parser.add_argument("--reboot-manifest", type=Path)
    parser.add_argument("--duration-s", type=float, default=60.0)
    parser.add_argument("--settle-s", type=float, default=10.0)
    parser.add_argument("--ack-timeout-s", type=float, default=3.0)
    parser.add_argument("--baud", type=int, default=capture.DEFAULT_BAUD)
    return parser


def main(argv=None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        manifest = run(args)
    except (F2ContractError, capture.CaptureContractError, OSError) as error:
        parser.error(str(error))
    return 0 if manifest["case_status"] == gate_eval.PASS else 2


if __name__ == "__main__":
    raise SystemExit(main())
