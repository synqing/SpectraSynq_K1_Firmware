"""Fail-closed F2 C1/C2 evidence and status finalisation.

This module does not access devices.  It validates separately immutable
pre-run attestations and post-run physical feedback, derives the F2 software,
physical, collection and acceptance statuses, and writes a hash-inventoried
Captain STOP.  F3 authorisation is deliberately outside this module.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Mapping, Sequence

SCHEMA_VERSION = 1
CASES = ("A", "B", "C1", "C2")
C_CASES = ("C1", "C2")

PASS = "PASS"
FAIL = "FAIL"
BLOCKED = "BLOCKED"
UNMEASURED = "UNMEASURED"
COMPLETE = "COMPLETE"
INCOMPLETE = "INCOMPLETE"
REJECTED = "REJECTED"
PENDING = "PENDING"

SOFTWARE_STATUSES = frozenset((PASS, FAIL, BLOCKED))
PHYSICAL_STATUSES = frozenset((PASS, FAIL, UNMEASURED))
DECISIONS = frozenset((PASS, REJECTED))

REQUIRED_EVIDENCE = (
    "case_A_manifest",
    "case_B_manifest",
    "case_C1_manifest",
    "case_C2_manifest",
    "c1_pre_attestation",
    "c1_post_feedback",
    "c2_pre_attestation",
    "c2_post_feedback",
)

_C_CONTRACT = {
    "C1": {
        "scenario": "late_join",
        "k718_state": "off",
    },
    "C2": {
        "scenario": "controlled_cold_coexistence",
        "k718_state": "powered_and_advertising",
    },
}
_SHA256_RE = re.compile(r"[0-9a-f]{64}")


class F2StatusError(RuntimeError):
    """F2 status evidence is missing, mutable, malformed or contradictory."""


def _has_symlink_component(path: Path) -> bool:
    absolute = Path(os.path.abspath(path))
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current = current / part
        if current.is_symlink():
            return True
    return False


def _inside(path: Path, root: Path) -> bool:
    try:
        Path(os.path.abspath(path)).relative_to(
            Path(os.path.abspath(root))
        )
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _require_direct_file(path: Path, root: Path, label: str) -> Path:
    if _has_symlink_component(path) or _has_symlink_component(root):
        raise F2StatusError(f"{label} may not contain a symlink")
    if not _inside(path, root):
        raise F2StatusError(f"{label} escapes its evidence root")
    if not path.is_file():
        raise F2StatusError(f"{label} is missing")
    return path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def evidence_record(path: Path, root: Path, label: str) -> dict:
    """Return a hash record for one direct, regular evidence file."""
    path = _require_direct_file(path, root, label)
    return {
        "path": str(path.resolve().relative_to(root.resolve())),
        "sha256": _sha256(path),
        "size": path.stat().st_size,
    }


def write_immutable_json(path: Path, payload: Mapping, root: Path) -> dict:
    """Atomically create one JSON evidence file and refuse replacement."""
    if _has_symlink_component(path) or _has_symlink_component(root):
        raise F2StatusError("immutable evidence path may not contain a symlink")
    if not _inside(path, root):
        raise F2StatusError("immutable evidence path escapes its evidence root")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise F2StatusError(f"refusing to overwrite immutable evidence {path}")
    temporary = path.with_name(f".{path.name}.tmp")
    if temporary.exists():
        raise F2StatusError(f"stale immutable-evidence temporary {temporary}")
    try:
        with temporary.open("x", encoding="utf-8") as output:
            json.dump(dict(payload), output, indent=2, sort_keys=True)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    except OSError as error:
        raise F2StatusError(
            f"cannot write immutable evidence {path}: {error}"
        ) from error
    return evidence_record(path, root, "immutable evidence")


def _load_json(path: Path, root: Path, label: str) -> tuple[dict, dict]:
    path = _require_direct_file(path, root, label)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise F2StatusError(f"{label} is not valid JSON: {error}") from error
    if not isinstance(payload, dict):
        raise F2StatusError(f"{label} must be a JSON object")
    return payload, evidence_record(path, root, label)


def _require_exact_fields(
    payload: Mapping, expected: Mapping, fields: set[str], label: str
) -> None:
    if set(payload) != fields:
        missing = sorted(fields - set(payload))
        extra = sorted(set(payload) - fields)
        raise F2StatusError(
            f"{label} fields mismatch; missing={missing}, extra={extra}"
        )
    for key, value in expected.items():
        if payload.get(key) != value:
            raise F2StatusError(f"{label} requires {key}={value!r}")


def _require_captain_and_timestamp(payload: Mapping, label: str) -> None:
    captain = payload.get("captain")
    if not isinstance(captain, str) or not captain.strip():
        raise F2StatusError(f"{label} requires a Captain identity")
    created_at = payload.get("created_at_utc")
    if not isinstance(created_at, str) or not created_at.endswith("Z"):
        raise F2StatusError(
            f"{label} requires an RFC3339 UTC created_at_utc"
        )
    try:
        datetime.fromisoformat(created_at[:-1] + "+00:00")
    except ValueError as error:
        raise F2StatusError(
            f"{label} requires an RFC3339 UTC created_at_utc"
        ) from error


def validate_pre_attestation(
    path: Path, expected_case: str, root: Path
) -> dict:
    """Validate a closed, pre-run-only C1 or C2 physical attestation."""
    if expected_case not in C_CASES:
        raise F2StatusError("pre-run attestation case must be C1 or C2")
    payload, record = _load_json(path, root, "pre-run attestation")
    contract = _C_CONTRACT[expected_case]
    fields = {
        "schema_version",
        "kind",
        "case",
        "scenario",
        "captain",
        "created_at_utc",
        "gpio_wiring_confirmed",
        "common_ground_confirmed",
        "logic_voltage",
        "k718_state",
        "four_detent_commitment",
    }
    if expected_case == "C2":
        fields.add("controlled_reboot_authorised")
    _require_exact_fields(
        payload,
        {
            "schema_version": SCHEMA_VERSION,
            "kind": "f2_pre_attestation",
            "case": expected_case,
            "scenario": contract["scenario"],
            "gpio_wiring_confirmed": True,
            "common_ground_confirmed": True,
            "logic_voltage": "3V3",
            "k718_state": contract["k718_state"],
            "four_detent_commitment": True,
        },
        fields,
        "pre-run attestation",
    )
    _require_captain_and_timestamp(payload, "pre-run attestation")
    if (
        expected_case == "C2"
        and payload.get("controlled_reboot_authorised") is not True
    ):
        raise F2StatusError(
            "C2 pre-run attestation requires "
            "controlled_reboot_authorised=true"
        )
    return {"payload": payload, "evidence": record}


def validate_post_feedback(
    path: Path,
    expected_case: str,
    pre_attestation: Mapping,
    root: Path,
) -> dict:
    """Validate post-run feedback bound to a distinct pre-run file hash."""
    if expected_case not in C_CASES:
        raise F2StatusError("post-run feedback case must be C1 or C2")
    pre_record = pre_attestation.get("evidence")
    if not isinstance(pre_record, Mapping):
        raise F2StatusError("validated pre-run attestation is required")
    pre_hash = pre_record.get("sha256")
    pre_path = pre_record.get("path")
    if (
        not isinstance(pre_hash, str)
        or _SHA256_RE.fullmatch(pre_hash) is None
        or not isinstance(pre_path, str)
    ):
        raise F2StatusError("pre-run attestation evidence is malformed")

    payload, record = _load_json(path, root, "post-run feedback")
    if record["path"] == pre_path:
        raise F2StatusError(
            "pre-run attestation and post-run feedback must be separate files"
        )
    fields = {
        "schema_version",
        "kind",
        "case",
        "captain",
        "created_at_utc",
        "pre_attestation_sha256",
        "k1_mode_changed",
        "k718_confirmation_displayed",
        "status",
    }
    _require_exact_fields(
        payload,
        {
            "schema_version": SCHEMA_VERSION,
            "kind": "f2_post_run_feedback",
            "case": expected_case,
            "pre_attestation_sha256": pre_hash,
        },
        fields,
        "post-run feedback",
    )
    _require_captain_and_timestamp(payload, "post-run feedback")
    physical_status = payload["status"]
    if physical_status not in PHYSICAL_STATUSES:
        raise F2StatusError(
            "post-run feedback status must be "
            "PASS, FAIL or UNMEASURED"
        )
    mode_changed = payload["k1_mode_changed"]
    confirmation = payload["k718_confirmation_displayed"]
    if physical_status == PASS and (mode_changed is not True or confirmation is not True):
        raise F2StatusError(
            "PASS feedback requires both physical observations true"
        )
    if physical_status == FAIL and not (
        mode_changed is False or confirmation is False
    ):
        raise F2StatusError(
            "FAIL feedback requires at least one physical observation false"
        )
    if physical_status == UNMEASURED and not (
        mode_changed is None and confirmation is None
    ):
        raise F2StatusError(
            "UNMEASURED feedback requires both observations null"
        )
    return {
        "payload": payload,
        "evidence": record,
        "physical_status": physical_status,
    }


def validate_captain_decision(
    path: Path, expected_stop_sha256: str, root: Path
) -> dict:
    """Validate a separate Captain decision bound to the immutable STOP."""
    if _SHA256_RE.fullmatch(expected_stop_sha256) is None:
        raise F2StatusError("Captain STOP SHA-256 is malformed")
    payload, record = _load_json(path, root, "Captain decision")
    fields = {
        "schema_version",
        "kind",
        "decided_by",
        "captain_stop_sha256",
        "decision",
    }
    _require_exact_fields(
        payload,
        {
            "schema_version": SCHEMA_VERSION,
            "kind": "f2_captain_decision",
            "decided_by": "Captain",
            "captain_stop_sha256": expected_stop_sha256,
        },
        fields,
        "Captain decision",
    )
    if payload["decision"] not in DECISIONS:
        raise F2StatusError("Captain decision must be PASS or REJECTED")
    return {
        "payload": payload,
        "evidence": record,
        "decision": payload["decision"],
    }


def _valid_evidence(record: object) -> bool:
    return (
        isinstance(record, Mapping)
        and isinstance(record.get("path"), str)
        and bool(record["path"])
        and isinstance(record.get("size"), int)
        and not isinstance(record["size"], bool)
        and record["size"] > 0
        and isinstance(record.get("sha256"), str)
        and _SHA256_RE.fullmatch(record["sha256"]) is not None
    )


def _evidence_matches(record: object, root: Path, label: str) -> bool:
    if not _valid_evidence(record):
        return False
    assert isinstance(record, Mapping)
    try:
        path = _require_direct_file(
            root / str(record["path"]), root, f"{label} evidence"
        )
    except F2StatusError:
        return False
    return (
        path.stat().st_size == record["size"]
        and _sha256(path) == record["sha256"]
    )


def _software_summary(statuses: Mapping[str, str]) -> str:
    values = tuple(statuses[case] for case in CASES)
    if FAIL in values:
        return FAIL
    if BLOCKED in values:
        return BLOCKED
    return PASS


def _physical_summary(statuses: Mapping[str, str]) -> str:
    values = tuple(statuses[case] for case in C_CASES)
    if FAIL in values:
        return FAIL
    if UNMEASURED in values:
        return UNMEASURED
    return PASS


def finalise_f2_status(
    *,
    software_status: Mapping[str, str],
    physical_status: Mapping[str, str],
    evidence: Mapping[str, Mapping],
    evidence_root: Path,
    captain_decision: Mapping | None = None,
) -> dict:
    """Derive the approved fail-closed F2 collection/acceptance matrix."""
    if set(software_status) != set(CASES):
        raise F2StatusError("software status requires A, B, C1 and C2")
    if any(value not in SOFTWARE_STATUSES for value in software_status.values()):
        raise F2StatusError(
            "software status values must be PASS, FAIL or BLOCKED"
        )
    if set(physical_status) != set(C_CASES):
        raise F2StatusError("physical status requires C1 and C2")
    if any(value not in PHYSICAL_STATUSES for value in physical_status.values()):
        raise F2StatusError(
            "physical status values must be PASS, FAIL or UNMEASURED"
        )

    missing_evidence = [
        label
        for label in REQUIRED_EVIDENCE
        if not _evidence_matches(evidence.get(label), evidence_root, label)
    ]
    software_summary = _software_summary(software_status)
    physical_summary = _physical_summary(physical_status)
    collection = (
        COMPLETE
        if software_summary == PASS and not missing_evidence
        else INCOMPLETE
    )

    decision = None
    decision_evidence = None
    if captain_decision is not None:
        decision = captain_decision.get("decision")
        decision_evidence = captain_decision.get("evidence")
        decision_payload = captain_decision.get("payload")
        stop_evidence = evidence.get("captain_stop")
        if (
            decision not in DECISIONS
            or not isinstance(decision_payload, Mapping)
            or not _evidence_matches(
                decision_evidence, evidence_root, "Captain decision"
            )
            or not _evidence_matches(
                stop_evidence, evidence_root, "Captain STOP"
            )
        ):
            raise F2StatusError("validated Captain decision is required")
        assert isinstance(decision_evidence, Mapping)
        decision_path = evidence_root / str(decision_evidence["path"])
        try:
            stored_decision = json.loads(
                decision_path.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError) as error:
            raise F2StatusError(
                f"cannot revalidate Captain decision: {error}"
            ) from error
        assert isinstance(stop_evidence, Mapping)
        if (
            stored_decision != dict(decision_payload)
            or decision_payload.get("decision") != decision
            or decision_payload.get("captain_stop_sha256")
            != stop_evidence["sha256"]
        ):
            raise F2StatusError(
                "Captain decision does not bind the immutable Captain STOP"
            )

    if physical_summary == FAIL or decision == REJECTED:
        acceptance = REJECTED
    elif decision == PASS and collection == COMPLETE:
        acceptance = PASS
    else:
        acceptance = PENDING

    result = {
        "schema_version": SCHEMA_VERSION,
        "case_software_status": dict(software_status),
        "software_status": software_summary,
        "case_physical_status": dict(physical_status),
        "physical_status": physical_summary,
        "f2_evidence_collection": collection,
        "missing_evidence": missing_evidence,
        "f2_acceptance": acceptance,
        "captain_decision": decision,
        "captain_decision_evidence": decision_evidence,
        "f3_authorised": False,
    }
    result.update(
        {
            f"case_{case}_software_status": software_status[case]
            for case in CASES
        }
    )
    result.update(
        {
            f"case_{case}_physical_feedback": physical_status[case]
            for case in C_CASES
        }
    )
    return result


def render_captain_stop(
    status: Mapping, evidence: Mapping[str, Mapping]
) -> str:
    """Render a deterministic STOP with every evidence SHA-256."""
    if status.get("f3_authorised") is not False:
        raise F2StatusError("Captain STOP must keep f3_authorised=false")
    if status.get("f2_acceptance") == PASS:
        raise F2StatusError(
            "Captain STOP precedes and cannot embed Captain acceptance"
        )
    invalid = sorted(
        label for label, record in evidence.items() if not _valid_evidence(record)
    )
    if invalid:
        raise F2StatusError(f"Captain STOP evidence is malformed: {invalid}")

    lines = [
        "---",
        f"schema_version: {SCHEMA_VERSION}",
        (
            "f2_evidence_collection: "
            f"{status.get('f2_evidence_collection', INCOMPLETE)}"
        ),
        f"f2_acceptance: {status.get('f2_acceptance', PENDING)}",
        "f3_authorised: false",
        "---",
        "",
        "# Dual-sync F2 — Captain STOP",
        "",
        "| Case | Software | Physical |",
        "|---|---|---|",
    ]
    software = status.get("case_software_status", {})
    physical = status.get("case_physical_status", {})
    for case in CASES:
        lines.append(
            f"| {case} | {software.get(case, BLOCKED)} | "
            f"{physical.get(case, 'n/a')} |"
        )
    lines.extend(("", "## Evidence hashes", ""))
    for label in sorted(evidence):
        record = evidence[label]
        lines.append(
            f"- {label}: `{record['sha256']}` "
            f"({record['path']}, {record['size']} bytes)"
        )
    lines.extend(
        (
            "",
            "A separate, immutable Captain decision file is required.",
            "This STOP does not authorise F3.",
            "",
        )
    )
    return "\n".join(lines)


def write_captain_stop(
    path: Path,
    status: Mapping,
    evidence: Mapping[str, Mapping],
    root: Path,
) -> dict:
    """Create the non-overwriting Captain STOP and return its hash record."""
    if _has_symlink_component(path) or _has_symlink_component(root):
        raise F2StatusError("Captain STOP path may not contain a symlink")
    if not _inside(path, root):
        raise F2StatusError("Captain STOP path escapes its evidence root")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise F2StatusError(f"refusing to overwrite Captain STOP {path}")
    invalid = sorted(
        label
        for label, record in evidence.items()
        if not _evidence_matches(record, root, label)
    )
    if invalid:
        raise F2StatusError(
            f"Captain STOP evidence does not match files: {invalid}"
        )
    expected = finalise_f2_status(
        software_status=status.get("case_software_status", {}),
        physical_status=status.get("case_physical_status", {}),
        evidence=evidence,
        evidence_root=root,
    )
    status_keys = (
        "software_status",
        "physical_status",
        "f2_evidence_collection",
        "missing_evidence",
        "f2_acceptance",
        "f3_authorised",
    )
    if any(status.get(key) != expected[key] for key in status_keys):
        raise F2StatusError(
            "Captain STOP status does not match revalidated evidence"
        )
    text = render_captain_stop(status, evidence)
    temporary = path.with_name(f".{path.name}.tmp")
    if temporary.exists():
        raise F2StatusError(f"stale Captain STOP temporary {temporary}")
    try:
        with temporary.open("x", encoding="utf-8") as output:
            output.write(text)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    except OSError as error:
        raise F2StatusError(f"cannot write Captain STOP: {error}") from error
    return evidence_record(path, root, "Captain STOP")


def require_evidence_labels(
    records: Mapping[str, Mapping], labels: Sequence[str], root: Path
) -> None:
    """Reject missing/malformed caller-specific evidence beyond the minimum."""
    missing = [
        label
        for label in labels
        if not _evidence_matches(records.get(label), root, label)
    ]
    if missing:
        raise F2StatusError(f"required F2 evidence is missing: {missing}")


def _recursive_evidence(
    root: Path, *, label_prefix: str, evidence_root: Path
) -> dict[str, dict]:
    records = {}
    for path in sorted(root.rglob("*")):
        if (
            not path.is_file()
            or path.is_symlink()
            or path.name.startswith(".")
            or path.name in {
                "CAPTAIN_STOP.md",
                "CAPTAIN_STOP.sha256",
                "CAPTAIN_DECISION.json",
            }
        ):
            continue
        relative = path.relative_to(root)
        records[f"{label_prefix}:{relative}"] = evidence_record(
            path, evidence_root, f"{label_prefix} evidence"
        )
    return records


def _run_authority_evidence(
    run_manifest: Path,
    *,
    repo_root: Path,
    host_execution_sha: str,
    firmware_source_sha: str,
    image_set_manifest: Path,
) -> dict[str, dict]:
    """Rehash every authority file frozen when the immutable run opened."""
    payload, run_record = _load_json(
        run_manifest, repo_root, "F2 run manifest"
    )
    if (
        payload.get("status") != "OPEN"
        or payload.get("host_execution_sha") != host_execution_sha
        or payload.get("firmware_source_sha") != firmware_source_sha
        or payload.get("f3_authorised") is not False
    ):
        raise F2StatusError("F2 run manifest authority mismatch")
    authority = payload.get("authority")
    if not isinstance(authority, Mapping) or not authority:
        raise F2StatusError("F2 run manifest authority set is missing")
    records = {"run_manifest": run_record}
    for relative, expected in authority.items():
        if not isinstance(relative, str) or not isinstance(expected, Mapping):
            raise F2StatusError("F2 run authority record is malformed")
        path = repo_root / relative
        try:
            path = _require_direct_file(
                path, repo_root, f"run authority {relative}"
            )
        except F2StatusError:
            raise
        record = evidence_record(path, repo_root, f"run authority {relative}")
        if (
            record["sha256"] != expected.get("sha256")
            or record["size"] != expected.get("size")
        ):
            raise F2StatusError(
                f"run authority changed after creation: {relative}"
            )
        records[f"authority:{relative}"] = record

    image_record = payload.get("image_set_manifest")
    if (
        not isinstance(image_record, Mapping)
        or image_record.get("path")
        != str(image_set_manifest.resolve().relative_to(repo_root.resolve()))
        or not _evidence_matches(
            image_record, repo_root, "run image-set manifest"
        )
    ):
        raise F2StatusError("run image-set manifest evidence mismatch")
    ports_record = payload.get("ports_pre_A_manifest")
    if not _evidence_matches(
        ports_record, repo_root, "run ports_pre_A manifest"
    ):
        raise F2StatusError("run ports_pre_A manifest evidence mismatch")
    return records


def _image_artifact_evidence(
    image_set: Mapping, *, repo_root: Path
) -> dict[str, dict]:
    """Emit direct evidence for every frozen image and partition artefact."""
    records = {
        "image:partition_table": evidence_record(
            image_set["partition_table"]["path"],
            repo_root,
            "frozen partition table",
        )
    }
    for env, image in sorted(image_set["images"].items()):
        records[f"image:{env}:bin"] = evidence_record(
            image["bin_path"], repo_root, f"{env} application BIN"
        )
        records[f"image:{env}:elf"] = evidence_record(
            image["elf_path"], repo_root, f"{env} application ELF"
        )
    return records


def finalise_run(args) -> dict:
    """Revalidate a complete A/B/C1/C2 run and emit the immutable STOP."""
    from . import f2_capture, f2_image_set, f2_ports

    repo_root = Path(__file__).resolve().parents[2]
    observed_host_sha = f2_capture._git_head(repo_root)
    if observed_host_sha != args.host_execution_sha:
        try:
            f2_capture._close_run_for_host_drift(
                repo_root,
                args.run_root,
                expected_host_sha=args.host_execution_sha,
                observed_host_sha=observed_host_sha,
            )
        except f2_capture.F2ContractError as error:
            raise F2StatusError(str(error)) from error
        raise F2StatusError(
            "host execution SHA does not equal current committed HEAD"
        )
    try:
        f2_capture._require_run_open(repo_root, args.run_root)
        f2_capture._require_clean_host_inputs(repo_root)
    except f2_capture.F2ContractError as error:
        raise F2StatusError(str(error)) from error
    if args.host_execution_sha == args.firmware_source_sha:
        raise F2StatusError(
            "host execution SHA and firmware source SHA must remain distinct"
        )
    image_set = f2_image_set.load(
        args.image_set_manifest, repo_root=repo_root
    )
    if image_set["firmware_source_sha"] != args.firmware_source_sha:
        raise F2StatusError(
            "firmware source SHA does not match image-set manifest"
        )
    raw_root = args.run_root.resolve()
    if (
        not f2_capture._inside(raw_root, repo_root / "_scratch")
        or not raw_root.name.startswith("dual_sync_f2_abc_")
    ):
        raise F2StatusError(
            "run root must be _scratch/dual_sync_f2_abc_<run-id>"
        )
    run_id = raw_root.name.removeprefix("dual_sync_f2_abc_")
    f2_capture._validate_run_id(run_id)
    tracked_root = repo_root / f2_capture.TRACKED_F2_REL / run_id
    try:
        f2_ports.validate_ports_manifest(
            args.ports_manifest,
            expected_stage="C2",
            expected_host_execution_sha=args.host_execution_sha,
            expected_firmware_source_sha=args.firmware_source_sha,
        )
    except f2_ports.F2PortsError as error:
        raise F2StatusError(f"final ports chain rejected: {error}") from error

    software_status = {}
    evidence = _run_authority_evidence(
        tracked_root / "RUN_MANIFEST.json",
        repo_root=repo_root,
        host_execution_sha=args.host_execution_sha,
        firmware_source_sha=args.firmware_source_sha,
        image_set_manifest=args.image_set_manifest,
    )
    evidence.update(
        _image_artifact_evidence(image_set, repo_root=repo_root)
    )
    previous_digest = None
    prior_runtime = None
    for case in CASES:
        case_path = tracked_root / f"case_{case}.json"
        try:
            payload = f2_capture._validate_prior_case(
                case_path,
                case_name=case,
                firmware_sha=args.firmware_source_sha,
                host_sha=args.host_execution_sha,
                repo_root=repo_root,
                out_root=raw_root,
                tracked_root=tracked_root,
                previous_digest=previous_digest,
                prior_runtime=prior_runtime,
            )
        except f2_capture.F2ContractError as error:
            raise F2StatusError(
                f"Case {case} recursive re-evaluation failed: {error}"
            ) from error
        record = evidence_record(
            case_path, repo_root, f"Case {case} manifest"
        )
        software_status[case] = payload.get("case_status", BLOCKED)
        evidence[f"case_{case}_manifest"] = record
        previous_digest = f2_capture._sha256(case_path)
        prior_runtime = payload.get("runtime_identity")

    for path, label, allowed in (
        (
            args.c1_pre_attestation,
            "C1 pre-attestation",
            tracked_root / "attestations",
        ),
        (
            args.c1_feedback,
            "C1 feedback",
            tracked_root / "feedback",
        ),
        (
            args.c2_pre_attestation,
            "C2 pre-attestation",
            tracked_root / "attestations",
        ),
        (
            args.c2_feedback,
            "C2 feedback",
            tracked_root / "feedback",
        ),
    ):
        f2_capture._require_direct_file(path, allowed, label)
    c1_pre = validate_pre_attestation(
        args.c1_pre_attestation, "C1", repo_root
    )
    c1_feedback = validate_post_feedback(
        args.c1_feedback, "C1", c1_pre, repo_root
    )
    c2_pre = validate_pre_attestation(
        args.c2_pre_attestation, "C2", repo_root
    )
    c2_feedback = validate_post_feedback(
        args.c2_feedback, "C2", c2_pre, repo_root
    )
    evidence.update(
        {
            "c1_pre_attestation": c1_pre["evidence"],
            "c1_post_feedback": c1_feedback["evidence"],
            "c2_pre_attestation": c2_pre["evidence"],
            "c2_post_feedback": c2_feedback["evidence"],
            "image_set_manifest": evidence_record(
                args.image_set_manifest,
                repo_root,
                "image-set manifest",
            ),
            "ports_C2_manifest": evidence_record(
                args.ports_manifest, repo_root, "ports C2 manifest"
            ),
        }
    )
    evidence.update(
        _recursive_evidence(
            raw_root, label_prefix="raw", evidence_root=repo_root
        )
    )
    evidence.update(
        _recursive_evidence(
            tracked_root,
            label_prefix="tracked",
            evidence_root=repo_root,
        )
    )
    status = finalise_f2_status(
        software_status=software_status,
        physical_status={
            "C1": c1_feedback["physical_status"],
            "C2": c2_feedback["physical_status"],
        },
        evidence=evidence,
        evidence_root=repo_root,
    )
    status.update(
        {
            "host_execution_sha": args.host_execution_sha,
            "firmware_source_sha": args.firmware_source_sha,
            "run_id": run_id,
        }
    )
    status_path = tracked_root / "F2_STATUS.json"
    status_record = write_immutable_json(status_path, status, repo_root)
    evidence["f2_status"] = status_record
    stop_path = tracked_root / "CAPTAIN_STOP.md"
    stop_record = write_captain_stop(
        stop_path, status, evidence, repo_root
    )
    sidecar = tracked_root / "CAPTAIN_STOP.sha256"
    if sidecar.exists():
        raise F2StatusError(
            f"refusing to overwrite Captain STOP hash {sidecar}"
        )
    try:
        with sidecar.open("x", encoding="utf-8") as output:
            output.write(
                f"{stop_record['sha256']}  CAPTAIN_STOP.md\n"
            )
            output.flush()
            os.fsync(output.fileno())
    except OSError as error:
        raise F2StatusError(
            f"cannot write Captain STOP hash: {error}"
        ) from error
    return {
        "status": status,
        "captain_stop": stop_record,
        "captain_stop_sha256": evidence_record(
            sidecar, repo_root, "Captain STOP hash"
        ),
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Finalise immutable F2 A/B/C1/C2 evidence."
    )
    parser.add_argument("--host-execution-sha", required=True)
    parser.add_argument("--firmware-source-sha", required=True)
    parser.add_argument("--image-set-manifest", type=Path, required=True)
    parser.add_argument("--ports-manifest", type=Path, required=True)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--c1-pre-attestation", type=Path, required=True)
    parser.add_argument("--c1-feedback", type=Path, required=True)
    parser.add_argument("--c2-pre-attestation", type=Path, required=True)
    parser.add_argument("--c2-feedback", type=Path, required=True)
    return parser


def main(argv=None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        result = finalise_run(args)
    except (F2StatusError, OSError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
