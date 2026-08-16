#!/usr/bin/env python3
"""Fail-closed provenance and causal-trace oracle for K1 scheduling gates.

Gate 0 qualifies this host oracle against deliberate faults before production
firmware changes. Later gates provide a frozen expected manifest and an observed
manifest from the independently admitted build/device run. The validator never
updates expected values and has no device-write surface.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONTRACT = (
    ROOT
    / "docs"
    / "forensics"
    / "2026-08-15-freertos-scheduling-audit"
    / "gate0"
    / "contract.json"
)
SOURCE_ROOTS = ("SPECTRASYNQ_K1_FIRMWARE", "scripts", "tests")
SOURCE_SUFFIXES = {".cpp", ".def", ".h", ".ini", ".ino", ".py", ".sh"}
TIMESTAMP_FIELDS = (
    "oldest_sample_estimate_us",
    "newest_sample_estimate_us",
    "i2s_read_return_us",
    "ap_publish_us",
    "vp_acquire_us",
    "render_start_us",
    "rmt_submit_us",
    "rmt_complete_us",
)
FAULT_EXPECTED_REASON = {
    "wrong_git_sha": "mismatch:git_sha",
    "wrong_source_manifest": "mismatch:source_manifest_sha256",
    "wrong_platformio_ini": "mismatch:platformio_ini_sha256",
    "wrong_build_flags": "mismatch:effective_build_flags_sha256",
    "wrong_firmware_binary": "mismatch:firmware_bin_sha256",
    "wrong_device_identity_manifest": "mismatch:device_identity_manifest_sha256",
    "wrong_device_identity": "wrong_device_identity",
    "wrong_sample_tuple": "production_tuple:samples_per_chunk",
    "wrong_mode_stress_contract": "wrong_mode_stress_contract",
    "missing_trace_field": "trace[0].missing:rmt_complete_us",
    "regressed_timestamp": "trace[0].timestamp_order",
    "corrupt_generation": "trace[1].non_monotonic:ap_generation",
    "missing_final_bytes_crc": "trace[0].primary_bytes",
    "unconfirmed_rmt_completion": "trace[0].rmt_unconfirmed",
    "changed_frozen_fixture": "mismatch:fixture_manifest_sha256",
    "changed_test_inventory_hash": "mismatch:test_inventory_sha256",
    "deleted_required_test": "deleted_required_test",
    "skipped_required_test": "skipped_required_test",
    "xfailed_required_test": "xfailed_required_test",
    "deselected_required_test": "deselected_required_test",
    "perturbing_stream_enabled": "perturbing_stream_enabled",
}


class Gate0Error(RuntimeError):
    """One or more fail-closed admission checks rejected the evidence."""


@dataclass(frozen=True)
class ValidationResult:
    checks: int
    records: int


@dataclass(frozen=True)
class ContractSelection:
    selected_contract_path: Path
    selected_contract_id: str
    selected_contract_sha256: str
    selected_period_us: int
    selected_p99_limit_us: int
    selection_reason: str
    scope: str  # DEPLOYED | CANDIDATE_ONLY


_TUPLE_COMPARE_KEYS = (
    "sample_rate_hz",
    "samples_per_chunk",
    "tempo_novelty_decimation",
    "ap_arrival_period_us",
)


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def _git(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=ROOT, stderr=subprocess.DEVNULL, text=True
    ).strip()


def source_paths(root: Path = ROOT) -> list[Path]:
    paths: list[Path] = []
    for directory in SOURCE_ROOTS:
        base = root / directory
        paths.extend(
            path
            for path in base.rglob("*")
            if path.is_file() and path.suffix in SOURCE_SUFFIXES
        )
    paths.append(root / "platformio.ini")
    return sorted(paths, key=lambda path: path.relative_to(root).as_posix())


def source_manifest(root: Path = ROOT) -> dict[str, Any]:
    paths = source_paths(root)
    rows = [
        {
            "path": path.relative_to(root).as_posix(),
            "sha256": sha256_file(path),
            "bytes": path.stat().st_size,
        }
        for path in paths
    ]
    path_list = "".join(f"{row['path']}\n" for row in rows).encode("utf-8")
    return {
        "count": len(rows),
        "path_list_sha256": sha256_bytes(path_list),
        "content_manifest_sha256": sha256_bytes(_canonical_json(rows)),
        "rows": rows,
    }


def _command_version(argv: list[str]) -> str:
    try:
        result = subprocess.run(
            argv,
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return "unavailable"
    value = (result.stdout or result.stderr).strip().splitlines()
    return value[0] if value else f"exit={result.returncode}"


def create_provenance(contract_path: Path = DEFAULT_CONTRACT) -> dict[str, Any]:
    manifest = source_manifest()
    status = subprocess.check_output(
        ["git", "status", "--porcelain=v1"],
        cwd=ROOT,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    dirty_paths = [line[3:] for line in status.splitlines() if line]
    return {
        "schema_version": 1,
        "captured_utc": datetime.now(timezone.utc).isoformat(),
        "git": {
            "head": _git("rev-parse", "HEAD"),
            "tree": _git("rev-parse", "HEAD^{tree}"),
            "branch": _git("branch", "--show-current"),
            "dirty": bool(dirty_paths),
            "dirty_paths": dirty_paths,
        },
        "source_manifest": manifest,
        "contract_sha256": sha256_file(contract_path),
        "platformio_ini_sha256": sha256_file(ROOT / "platformio.ini"),
        "device_identity_manifest_sha256": sha256_file(
            ROOT / "scripts" / "platformio" / "k1_device_identities.json"
        ),
        "toolchain": {
            "python": sys.version.split()[0],
            "platformio": _command_version(["pio", "--version"]),
            "git": _command_version(["git", "--version"]),
        },
    }


def _require(condition: bool, code: str, errors: list[str]) -> None:
    if not condition:
        errors.append(code)


def _same(expected: dict[str, Any], observed: dict[str, Any], key: str, errors: list[str]) -> None:
    _require(key in expected, f"expected_missing:{key}", errors)
    _require(key in observed, f"observed_missing:{key}", errors)
    if key in expected and key in observed:
        _require(expected[key] == observed[key], f"mismatch:{key}", errors)


def _validate_trace(
    records: Iterable[dict[str, Any]], required_fields: set[str], errors: list[str]
) -> int:
    previous: dict[str, Any] | None = None
    count = 0
    for index, record in enumerate(records):
        count += 1
        missing = sorted(required_fields - set(record))
        for field in missing:
            errors.append(f"trace[{index}].missing:{field}")
        if missing:
            continue
        values = [record[field] for field in TIMESTAMP_FIELDS]
        _require(values == sorted(values), f"trace[{index}].timestamp_order", errors)
        _require(record["ap_generation"] > 0, f"trace[{index}].generation_zero", errors)
        _require(
            record["mixed_generation_count"] == 0,
            f"trace[{index}].mixed_generation",
            errors,
        )
        _require(record["trace_drop_count"] == 0, f"trace[{index}].drops", errors)
        _require(bool(record["trace_crc"]), f"trace[{index}].crc_missing", errors)
        if previous is not None:
            _require(
                record["boot_epoch"] == previous["boot_epoch"],
                f"trace[{index}].boot_epoch_changed",
                errors,
            )
            for field in ("capture_sequence", "ap_generation", "vp_frame_sequence"):
                _require(
                    record[field] > previous[field],
                    f"trace[{index}].non_monotonic:{field}",
                    errors,
                )
            for epoch, sequence in (("onset_epoch", "onset_sequence"), ("beat_epoch", "beat_sequence")):
                _require(
                    record[epoch] > previous[epoch]
                    or (record[epoch] == previous[epoch] and record[sequence] >= previous[sequence]),
                    f"trace[{index}].event_regression:{epoch}:{sequence}",
                    errors,
                )
        previous = record
    _require(count > 0, "trace_empty", errors)
    return count


def validate_run(contract: dict[str, Any], evidence: dict[str, Any]) -> ValidationResult:
    errors: list[str] = []
    checks = 0
    _require(evidence.get("schema_version") == 1, "schema_version", errors)
    _require(evidence.get("contract_id") == contract["contract_id"], "contract_id", errors)

    expected = evidence.get("expected", {})
    observed = evidence.get("observed", {})
    for key in (
        "git_sha",
        "source_manifest_sha256",
        "platformio_ini_sha256",
        "effective_build_flags_sha256",
        "firmware_bin_sha256",
        "device_identity_manifest_sha256",
        "fixture_manifest_sha256",
        "test_inventory_sha256",
        "mode_stress_contract_sha256",
    ):
        _same(expected, observed, key, errors)
        checks += 1

    tuple_expected = contract["production_tuple"]
    tuple_observed = observed.get("production_tuple", {})
    for key in (
        "platformio_environment",
        "sample_rate_hz",
        "samples_per_chunk",
        "tempo_novelty_decimation",
    ):
        _require(
            tuple_observed.get(key) == tuple_expected[key],
            f"production_tuple:{key}",
            errors,
        )
        checks += 1

    device = observed.get("device", {})
    _require(device.get("identity_verified") is True, "device_identity_unverified", errors)
    _require(device.get("chip_id") == "F887A500", "wrong_device_identity", errors)
    _require(device.get("environment") == "k1_hardware", "wrong_device_environment", errors)
    checks += 3

    instrumentation = observed.get("instrumentation", {})
    _require(
        instrumentation.get("ordinary_streaming_enabled") is False,
        "perturbing_stream_enabled",
        errors,
    )
    _require(
        instrumentation.get("bounded_probe") in {"minimal", "scheduling_trace_v1"},
        "instrumentation_lane",
        errors,
    )
    checks += 2

    inventory = observed.get("test_inventory", {})
    _require(inventory.get("required_count", 0) > 0, "required_test_inventory_empty", errors)
    _require(inventory.get("deleted_count") == 0, "deleted_required_test", errors)
    _require(inventory.get("skipped_count") == 0, "skipped_required_test", errors)
    _require(inventory.get("xfailed_count") == 0, "xfailed_required_test", errors)
    _require(inventory.get("deselected_count") == 0, "deselected_required_test", errors)
    checks += 5

    mode = observed.get("mode_stress", {})
    _require(
        mode.get("discovery") == contract["mode_stress_contract"]["discovery"],
        "wrong_mode_stress_contract",
        errors,
    )
    _require(
        mode.get("stress_transition") == "simultaneous_two_channel_crossfade",
        "wrong_stress_transition",
        errors,
    )
    _require(mode.get("selection_frozen") is True, "mode_selection_not_frozen", errors)
    checks += 3

    records = _validate_trace(
        observed.get("trace_records", []), set(contract["required_trace_fields"]), errors
    )
    for index, record in enumerate(observed.get("trace_records", [])):
        _require(bool(record.get("primary_final_bytes_crc")), f"trace[{index}].primary_bytes", errors)
        _require(bool(record.get("secondary_final_bytes_crc")), f"trace[{index}].secondary_bytes", errors)
        _require(record.get("rmt_completion_confirmed") is True, f"trace[{index}].rmt_unconfirmed", errors)
        _require(
            record.get("rmt_completion_source") in {"driver_completion_callback", "driver_wait_tx_done"},
            f"trace[{index}].rmt_completion_source",
            errors,
        )
    checks += records * (len(contract["required_trace_fields"]) + 8)

    if errors:
        raise Gate0Error(";".join(errors))
    return ValidationResult(checks=checks, records=records)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_deployed_contract_path(
    root: Path, deployed_contract_path: Path | None
) -> Path:
    if deployed_contract_path is not None:
        return deployed_contract_path
    candidate = root / "contract.json"
    if candidate.is_file():
        return candidate
    return DEFAULT_CONTRACT if root == ROOT else root / "contract.json"


def _p99_limit_us(contract: dict[str, Any]) -> int:
    period = int(contract["production_tuple"]["ap_arrival_period_us"])
    fraction = float(contract["margin_rules"]["ap_service_p99_max_fraction_of_arrival"])
    return int(period * fraction)


def _selection_from_contract(
    path: Path,
    contract: dict[str, Any],
    *,
    reason: str,
    scope: str,
) -> ContractSelection:
    return ContractSelection(
        selected_contract_path=path.resolve(),
        selected_contract_id=str(contract["contract_id"]),
        selected_contract_sha256=sha256_file(path),
        selected_period_us=int(contract["production_tuple"]["ap_arrival_period_us"]),
        selected_p99_limit_us=_p99_limit_us(contract),
        selection_reason=reason,
        scope=scope,
    )


def _tuple_matches(expected: dict[str, Any], measured: dict[str, Any] | None) -> bool:
    if measured is None:
        return False
    for key in _TUPLE_COMPARE_KEYS:
        if key not in expected:
            continue
        if measured.get(key) != expected[key]:
            return False
    return True


def select_contract(
    root: Path,
    *,
    pointer_path: Path | None = None,
    build_env: str | None = None,
    measured_tuple: dict[str, Any] | None = None,
    deployed_contract_path: Path | None = None,
) -> ContractSelection:
    """Select the controlling Gate-0 contract without promoting drafts.

    Live DEFAULT_CONTRACT remains the deployed 7.5 ms file. A pointer is required
    before any stamped candidate may be selected, and production promotion is
    rejected until Gate 8.
    """
    deployed_path = _resolve_deployed_contract_path(root, deployed_contract_path)
    if not deployed_path.is_file():
        raise Gate0Error(f"deployed_contract_missing:{deployed_path}")

    if pointer_path is None or not pointer_path.is_file():
        return _selection_from_contract(
            deployed_path,
            load_json(deployed_path),
            reason="no_pointer_deployed_contract",
            scope="DEPLOYED",
        )

    pointer = load_json(pointer_path)
    target_rel = pointer.get("target_path") or pointer.get("contract_path")
    if not target_rel:
        raise Gate0Error("pointer_missing_target_path")
    target_path = Path(target_rel)
    if not target_path.is_absolute():
        target_path = (root / target_path).resolve()
    if not target_path.is_file():
        raise Gate0Error(f"pointer_target_missing:{target_path}")

    target = load_json(target_path)
    status = str(target.get("status", ""))
    if status == "DRAFT_AWAITING_CAPTAIN":
        raise Gate0Error("DRAFT_AWAITING_CAPTAIN")

    candidate_scope = target.get("candidate_scope") or target.get("scope_block") or {}
    if isinstance(target.get("scope"), str) and not candidate_scope:
        candidate_scope = {
            "scope": target.get("scope"),
            "applicable_envs": target.get("applicable_envs", []),
            "promotion_status": target.get("promotion_status", "NOT_PRODUCTION"),
            "status": status,
        }

    promotion = str(
        candidate_scope.get("promotion_status")
        or target.get("promotion_status")
        or "NOT_PRODUCTION"
    )
    if promotion == "PRODUCTION":
        raise Gate0Error("production_promotion_not_authorised_before_gate8")

    if status != "CAPTAIN_STAMPED":
        raise Gate0Error(f"pointer_target_status_not_admissible:{status or 'missing'}")

    scope = str(candidate_scope.get("scope") or target.get("scope") or "")
    if scope != "CANDIDATE_ONLY":
        raise Gate0Error(f"pointer_target_scope_not_candidate:{scope or 'missing'}")

    applicable = list(candidate_scope.get("applicable_envs") or target.get("applicable_envs") or [])
    if build_env not in applicable:
        raise Gate0Error("applicable_envs")

    # Candidate files may embed a nested contract object or carry contract fields
    # at the top level (status/scope alongside production_tuple).
    contract_body = target
    if "contract" in target and isinstance(target["contract"], dict):
        contract_body = {**target["contract"]}
        if "contract_id" not in contract_body and "contract_id" in target:
            contract_body["contract_id"] = target["contract_id"]
        if "production_tuple" not in contract_body and "production_tuple" in target:
            contract_body["production_tuple"] = target["production_tuple"]
        if "margin_rules" not in contract_body and "margin_rules" in target:
            contract_body["margin_rules"] = target["margin_rules"]

    production_tuple = contract_body.get("production_tuple")
    if not isinstance(production_tuple, dict):
        raise Gate0Error("candidate_missing_production_tuple")
    if not _tuple_matches(production_tuple, measured_tuple):
        raise Gate0Error("measured_tuple_mismatch")
    if "contract_id" not in contract_body:
        raise Gate0Error("candidate_missing_contract_id")
    if "margin_rules" not in contract_body:
        raise Gate0Error("candidate_missing_margin_rules")

    return _selection_from_contract(
        target_path,
        contract_body,
        reason="candidate_env_and_tuple_match",
        scope="CANDIDATE_ONLY",
    )


def fault_mutations(valid: dict[str, Any]) -> dict[str, dict[str, Any]]:
    mutations: dict[str, dict[str, Any]] = {}

    def mutate(name: str, editor: Any) -> None:
        value = copy.deepcopy(valid)
        editor(value)
        mutations[name] = value

    mutate("wrong_git_sha", lambda value: value["observed"].__setitem__("git_sha", "0" * 40))
    mutate(
        "wrong_source_manifest",
        lambda value: value["observed"].__setitem__("source_manifest_sha256", "0" * 64),
    )
    mutate(
        "wrong_platformio_ini",
        lambda value: value["observed"].__setitem__("platformio_ini_sha256", "0" * 64),
    )
    mutate(
        "wrong_build_flags",
        lambda value: value["observed"].__setitem__("effective_build_flags_sha256", "0" * 64),
    )
    mutate(
        "wrong_firmware_binary",
        lambda value: value["observed"].__setitem__("firmware_bin_sha256", "0" * 64),
    )
    mutate(
        "wrong_device_identity_manifest",
        lambda value: value["observed"].__setitem__("device_identity_manifest_sha256", "0" * 64),
    )
    mutate("wrong_device_identity", lambda value: value["observed"]["device"].__setitem__("chip_id", "B489A500"))
    mutate("wrong_sample_tuple", lambda value: value["observed"]["production_tuple"].__setitem__("samples_per_chunk", 128))
    mutate(
        "wrong_mode_stress_contract",
        lambda value: value["observed"]["mode_stress"].__setitem__("discovery", "hand_picked_pair"),
    )
    mutate("missing_trace_field", lambda value: value["observed"]["trace_records"][0].pop("rmt_complete_us"))
    mutate(
        "regressed_timestamp",
        lambda value: value["observed"]["trace_records"][0].__setitem__("vp_acquire_us", 900),
    )
    mutate(
        "corrupt_generation",
        lambda value: value["observed"]["trace_records"][1].__setitem__(
            "ap_generation", value["observed"]["trace_records"][0]["ap_generation"]
        ),
    )
    mutate(
        "missing_final_bytes_crc",
        lambda value: value["observed"]["trace_records"][0].__setitem__("primary_final_bytes_crc", ""),
    )
    mutate(
        "unconfirmed_rmt_completion",
        lambda value: value["observed"]["trace_records"][0].__setitem__("rmt_completion_confirmed", False),
    )
    mutate(
        "changed_frozen_fixture",
        lambda value: value["observed"].__setitem__("fixture_manifest_sha256", "f" * 64),
    )
    mutate(
        "changed_test_inventory_hash",
        lambda value: value["observed"].__setitem__("test_inventory_sha256", "0" * 64),
    )
    for fault_name, counter in (
        ("deleted_required_test", "deleted_count"),
        ("skipped_required_test", "skipped_count"),
        ("xfailed_required_test", "xfailed_count"),
        ("deselected_required_test", "deselected_count"),
    ):
        mutate(
            fault_name,
            lambda value, counter=counter: value["observed"]["test_inventory"].__setitem__(counter, 1),
        )
    mutate(
        "perturbing_stream_enabled",
        lambda value: value["observed"]["instrumentation"].__setitem__(
            "ordinary_streaming_enabled", True
        ),
    )
    return mutations


def run_fault_battery(contract: dict[str, Any], valid: dict[str, Any]) -> list[str]:
    validate_run(contract, valid)
    caught: list[str] = []
    for name, mutation in fault_mutations(valid).items():
        try:
            validate_run(contract, mutation)
        except Gate0Error as exc:
            expected_reason = FAULT_EXPECTED_REASON[name]
            if expected_reason not in str(exc):
                raise Gate0Error(
                    f"fault_wrong_reason:{name}:expected={expected_reason}:actual={exc}"
                ) from exc
            caught.append(name)
        else:
            raise Gate0Error(f"fault_not_caught:{name}")
    required = set(contract["required_faults"])
    if set(caught) != required:
        missing = sorted(required - set(caught))
        extra = sorted(set(caught) - required)
        raise Gate0Error(f"fault_battery_membership:missing={missing}:extra={extra}")
    return caught


def verify_trust_root(path: Path) -> int:
    trust = load_json(path)
    errors: list[str] = []
    files = trust.get("files", [])
    _require(bool(files), "trust_root_empty", errors)
    for entry in files:
        candidate = ROOT / entry["path"]
        _require(candidate.is_file(), f"trust_root_missing:{entry['path']}", errors)
        if candidate.is_file():
            _require(
                sha256_file(candidate) == entry["sha256"],
                f"trust_root_hash:{entry['path']}",
                errors,
            )
    if errors:
        raise Gate0Error(";".join(errors))
    return len(files)


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    sub = parser.add_subparsers(dest="command", required=True)
    snapshot = sub.add_parser("snapshot", help="Write a read-only repository provenance snapshot")
    snapshot.add_argument("--output", type=Path, required=True)
    validate = sub.add_parser("validate", help="Validate an expected/observed run manifest")
    validate.add_argument("manifest", type=Path)
    battery = sub.add_parser("fault-battery", help="Prove all registered mutations are rejected")
    battery.add_argument("fixture", type=Path)
    trust = sub.add_parser("verify-trust-root", help="Verify the externally committed Gate 0 trust root")
    trust.add_argument("trust_root", type=Path)
    args = parser.parse_args(argv)

    contract = load_json(args.contract)
    try:
        if args.command == "snapshot":
            value = create_provenance(args.contract)
            _write_json(args.output, value)
            print(
                "GATE0_SNAPSHOT PASS "
                f"files={value['source_manifest']['count']} "
                f"content_sha256={value['source_manifest']['content_manifest_sha256']}"
            )
        elif args.command == "validate":
            result = validate_run(contract, load_json(args.manifest))
            print(f"GATE0_VALIDATE PASS checks={result.checks} records={result.records}")
        elif args.command == "fault-battery":
            caught = run_fault_battery(contract, load_json(args.fixture))
            print(f"GATE0_FAULT_BATTERY PASS caught={len(caught)} names={','.join(caught)}")
        else:
            count = verify_trust_root(args.trust_root)
            print(f"GATE0_TRUST_ROOT PASS files={count}")
    except (Gate0Error, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"GATE0_REJECT {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
