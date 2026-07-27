"""F2 USB-serial-first port rebinding and continuity manifests.

Device paths are observations, never identities.  Each manifest is written
only after both configured USB serials have been resolved and their chips have
answered ``:chip_id`` with the expected eFuse identity.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from . import capture

SCHEMA_VERSION = 1
STAGE_PREDECESSOR = {
    "pre_A": None,
    "A": "pre_A",
    "B": "A",
    "C1": "B",
    "C2": "C1",
}
ROLE_CONTRACT = {
    "leader": {
        "usb_serial": "B4:3A:45:A5:87:F8",
        "chip_id": "F887A500",
    },
    "follower": {
        "usb_serial": "B4:3A:45:A5:89:B4",
        "chip_id": "B489A500",
    },
}
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_CHIP_ID_RE = re.compile(r"^[0-9A-Fa-f]{8}$")


class F2PortsError(RuntimeError):
    """Port identity, continuity, or non-overwrite contract failure."""


def sha256_file(path: Path | str) -> str:
    """Return a file SHA-256 without following an untrusted manifest link."""
    source = Path(path)
    if source.is_symlink():
        raise F2PortsError(f"refusing symlink manifest: {source}")
    digest = hashlib.sha256()
    try:
        with source.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as error:
        raise F2PortsError(f"cannot hash {source}: {error}") from error
    return digest.hexdigest()


def _default_port_provider():
    try:
        from serial.tools import list_ports
    except Exception as error:  # pragma: no cover - host dependency
        raise F2PortsError(f"pyserial port enumeration unavailable: {error}") from error
    return list_ports.comports()


def _query(
    stream,
    command: str,
    matcher: Callable[[str], object | None],
    timeout_s: float,
) -> object:
    try:
        stream.reset_input_buffer()
        stream.write(f":{command}\n".encode("ascii"))
        stream.flush()
    except Exception as error:
        raise F2PortsError(f":{command} write failed: {error}") from error

    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            raw = stream.readline()
        except Exception as error:
            raise F2PortsError(f":{command} read failed: {error}") from error
        if not raw:
            time.sleep(0.001)
            continue
        if isinstance(raw, bytes):
            line = raw.decode("utf-8", errors="replace").strip()
        else:
            line = str(raw).strip()
        value = matcher(line)
        if value is not None:
            return value
    raise F2PortsError(f":{command} read-back missing before timeout")


def query_identity(
    stream,
    command: str,
    matcher: Callable[[str], object | None],
    *,
    timeout_s: float,
) -> object:
    """Issue one typed identity query on an already-open serial stream."""
    return _query(stream, command, matcher, timeout_s)


def _resolve_usb_paths(
    port_provider: Callable[[], object],
    timeout_s: float,
) -> dict[str, str]:
    deadline = time.monotonic() + timeout_s
    missing: list[str] = []
    while True:
        try:
            observed = list(port_provider())
        except Exception as error:
            raise F2PortsError(f"USB serial enumeration failed: {error}") from error

        resolved: dict[str, str] = {}
        missing = []
        for role, expected in ROLE_CONTRACT.items():
            matches = [
                str(port.device)
                for port in observed
                if str(getattr(port, "serial_number", "") or "")
                == expected["usb_serial"]
            ]
            if len(matches) > 1:
                raise F2PortsError(
                    f"{role} USB serial {expected['usb_serial']} matched "
                    f"multiple ports: {matches}"
                )
            if not matches:
                missing.append(role)
            else:
                resolved[role] = matches[0]
        if not missing:
            if resolved["leader"] == resolved["follower"]:
                raise F2PortsError("leader and follower resolved to one device path")
            return resolved
        if time.monotonic() >= deadline:
            break
        time.sleep(0.05)
    raise F2PortsError(
        f"USB serials did not enumerate before timeout: {','.join(missing)}"
    )


def resolve_bindings(
    *,
    port_provider: Callable[[], object] | None = None,
    serial_factory: Callable[[str, int], object] | None = None,
    timeout_s: float = 5.0,
    baud: int = capture.DEFAULT_BAUD,
) -> dict[str, dict[str, str]]:
    """Resolve USB serials, then verify chip identities over those paths."""
    if timeout_s <= 0:
        raise F2PortsError("timeout_s must be positive")
    provider = port_provider or _default_port_provider
    opener = serial_factory or capture._open_serial
    paths = _resolve_usb_paths(provider, timeout_s)
    bindings: dict[str, dict[str, str]] = {}

    for role in ("leader", "follower"):
        path = paths[role]
        try:
            stream = opener(path, baud)
        except Exception as error:
            raise F2PortsError(f"cannot open {role} port {path}: {error}") from error
        try:
            if hasattr(stream, "dtr"):
                stream.dtr = False
            if hasattr(stream, "rts"):
                stream.rts = False
            chip = _query(
                stream,
                "chip_id",
                lambda line: (
                    line.upper() if _CHIP_ID_RE.fullmatch(line) else None
                ),
                timeout_s,
            )
        finally:
            try:
                stream.close()
            except Exception:
                pass

        expected = ROLE_CONTRACT[role]
        if chip != expected["chip_id"]:
            raise F2PortsError(
                f"{role} chip mismatch: observed {chip}, "
                f"expected {expected['chip_id']}"
            )
        bindings[role] = {
            "usb_serial": expected["usb_serial"],
            "port": path,
            "chip_id": str(chip),
        }
    return bindings


def resolve_usb_paths_by_serial(
    *,
    port_provider: Callable[[], object] | None = None,
    timeout_s: float = 5.0,
) -> dict[str, dict[str, str]]:
    """Resolve both USB identities without consuming their boot serial logs."""
    if timeout_s <= 0:
        raise F2PortsError("timeout_s must be positive")
    provider = port_provider or _default_port_provider
    paths = _resolve_usb_paths(provider, timeout_s)
    return {
        role: {
            "usb_serial": expected["usb_serial"],
            "port": paths[role],
            "chip_id": expected["chip_id"],
        }
        for role, expected in ROLE_CONTRACT.items()
    }


def _normalise_bindings(
    bindings: object,
) -> dict[str, dict[str, str]]:
    if not isinstance(bindings, dict) or set(bindings) != set(ROLE_CONTRACT):
        raise F2PortsError("ports manifest requires leader and follower roles only")
    normalised: dict[str, dict[str, str]] = {}
    for role, expected in ROLE_CONTRACT.items():
        value = bindings.get(role)
        if not isinstance(value, dict):
            raise F2PortsError(f"{role} binding must be an object")
        usb_serial = value.get("usb_serial")
        port = value.get("port")
        chip = value.get("chip_id")
        if usb_serial != expected["usb_serial"]:
            raise F2PortsError(
                f"{role} USB serial mismatch: observed {usb_serial!r}, "
                f"expected {expected['usb_serial']}"
            )
        if not isinstance(port, str) or not port:
            raise F2PortsError(f"{role} device path is missing")
        if not isinstance(chip, str) or chip.upper() != expected["chip_id"]:
            raise F2PortsError(
                f"{role} chip mismatch: observed {chip!r}, "
                f"expected {expected['chip_id']}"
            )
        normalised[role] = {
            "usb_serial": usb_serial,
            "port": port,
            "chip_id": chip.upper(),
        }
    if normalised["leader"]["port"] == normalised["follower"]["port"]:
        raise F2PortsError("leader and follower share one device path")
    return normalised


def _load_json(path: Path) -> dict[str, object]:
    if path.is_symlink():
        raise F2PortsError(f"refusing symlink manifest: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise F2PortsError(f"cannot read ports manifest {path}: {error}") from error
    if not isinstance(payload, dict):
        raise F2PortsError(f"ports manifest is not an object: {path}")
    return payload


def _created_at_utc() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def validate_ports_manifest(
    path: Path | str,
    *,
    expected_stage: str | None = None,
    expected_host_execution_sha: str | None = None,
    expected_firmware_source_sha: str | None = None,
) -> dict[str, object]:
    """Validate one manifest and its complete predecessor hash chain."""
    manifest_path = Path(path)
    payload = _load_json(manifest_path)
    stage = payload.get("stage")
    if stage not in STAGE_PREDECESSOR:
        raise F2PortsError(f"invalid ports manifest stage: {stage!r}")
    if expected_stage is not None and stage != expected_stage:
        raise F2PortsError(
            f"ports manifest stage mismatch: observed {stage}, "
            f"expected {expected_stage}"
        )
    if manifest_path.name != f"ports_{stage}.json":
        raise F2PortsError(
            f"ports manifest filename mismatch for stage {stage}: "
            f"{manifest_path.name}"
        )
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise F2PortsError("ports manifest schema version mismatch")
    expected_fields = {
        "schema_version",
        "stage",
        "host_execution_sha",
        "firmware_source_sha",
        "leader",
        "follower",
        "created_at_utc",
        "previous_manifest_sha256",
    }
    if set(payload) != expected_fields:
        raise F2PortsError("ports manifest fields are not exact")
    host_sha = payload.get("host_execution_sha")
    firmware_sha = payload.get("firmware_source_sha")
    if not isinstance(host_sha, str) or _GIT_SHA_RE.fullmatch(host_sha) is None:
        raise F2PortsError("ports manifest host_execution_sha is malformed")
    if (
        not isinstance(firmware_sha, str)
        or _GIT_SHA_RE.fullmatch(firmware_sha) is None
    ):
        raise F2PortsError("ports manifest firmware_source_sha is malformed")
    if expected_host_execution_sha is not None and host_sha != expected_host_execution_sha:
        raise F2PortsError("ports manifest host execution identity mismatch")
    if (
        expected_firmware_source_sha is not None
        and firmware_sha != expected_firmware_source_sha
    ):
        raise F2PortsError("ports manifest firmware source identity mismatch")
    created_at = payload.get("created_at_utc")
    if not isinstance(created_at, str) or not created_at.endswith("Z"):
        raise F2PortsError("ports manifest created_at_utc is malformed")
    try:
        datetime.fromisoformat(created_at[:-1] + "+00:00")
    except ValueError as error:
        raise F2PortsError(
            "ports manifest created_at_utc is malformed"
        ) from error
    roles = _normalise_bindings(
        {"leader": payload.get("leader"), "follower": payload.get("follower")}
    )
    if payload.get("leader") != roles["leader"] or payload.get("follower") != roles["follower"]:
        raise F2PortsError("ports manifest role values are not canonical")

    predecessor_stage = STAGE_PREDECESSOR[str(stage)]
    previous = payload.get("previous_manifest_sha256")
    if predecessor_stage is None:
        if previous is not None:
            raise F2PortsError(
                "ports_pre_A.json must not name a predecessor"
            )
        return payload

    required_name = f"ports_{predecessor_stage}.json"
    if not isinstance(previous, str) or not _SHA256_RE.fullmatch(previous):
        raise F2PortsError(f"ports_{stage}.json is missing predecessor hash")
    expected_hash = previous
    predecessor_path = manifest_path.with_name(required_name)
    observed_hash = sha256_file(predecessor_path)
    if observed_hash != expected_hash:
        raise F2PortsError(
            f"ports_{stage}.json predecessor hash mismatch: "
            f"observed {observed_hash}, expected {expected_hash}"
        )
    predecessor = validate_ports_manifest(
        predecessor_path,
        expected_stage=predecessor_stage,
        expected_host_execution_sha=host_sha,
        expected_firmware_source_sha=firmware_sha,
    )
    prior_roles = {
        "leader": predecessor["leader"],
        "follower": predecessor["follower"],
    }
    for role in ("leader", "follower"):
        for identity_key in ("usb_serial", "chip_id"):
            if roles[role][identity_key] != prior_roles[role][identity_key]:
                raise F2PortsError(
                    f"{role} {identity_key} continuity failed from "
                    f"{predecessor_stage} to {stage}"
                )
    return payload


def _write_json_exclusive(path: Path, payload: dict[str, object]) -> None:
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    try:
        with path.open("x", encoding="utf-8") as output:
            output.write(text)
            output.flush()
            os.fsync(output.fileno())
    except FileExistsError as error:
        raise F2PortsError(f"refusing overwrite; {path} already exists") from error
    except OSError as error:
        raise F2PortsError(f"cannot write ports manifest {path}: {error}") from error


def write_ports_manifest(
    stage: str,
    output_dir: Path | str,
    bindings: object,
    *,
    host_execution_sha: str,
    firmware_source_sha: str,
    prior_manifest: Path | str | None = None,
    created_at_utc: str | None = None,
) -> dict[str, object]:
    """Write a canonical, non-overwriting stage manifest."""
    if stage not in STAGE_PREDECESSOR:
        raise F2PortsError(f"unsupported ports stage: {stage!r}")
    root = Path(output_dir)
    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise F2PortsError(f"cannot create output directory {root}: {error}") from error
    target = root / f"ports_{stage}.json"
    if target.exists() or target.is_symlink():
        raise F2PortsError(f"refusing overwrite; {target} already exists")

    canonical_bindings = _normalise_bindings(bindings)
    if _GIT_SHA_RE.fullmatch(host_execution_sha) is None:
        raise F2PortsError("host_execution_sha must be a full commit SHA")
    if _GIT_SHA_RE.fullmatch(firmware_source_sha) is None:
        raise F2PortsError("firmware_source_sha must be a full commit SHA")
    predecessor_stage = STAGE_PREDECESSOR[stage]
    previous: str | None = None
    if predecessor_stage is None:
        if prior_manifest is not None:
            raise F2PortsError("stage A must not have a prior manifest")
    else:
        required_name = f"ports_{predecessor_stage}.json"
        if prior_manifest is None:
            raise F2PortsError(f"stage {stage} requires {required_name}")
        prior_path = Path(prior_manifest)
        if prior_path.is_symlink():
            raise F2PortsError(f"refusing symlink manifest: {prior_path}")
        try:
            expected_path = (root / required_name).resolve(strict=True)
            observed_path = prior_path.resolve(strict=True)
        except OSError as error:
            raise F2PortsError(
                f"stage {stage} requires {required_name}; "
                f"it is not readable: {error}"
            ) from error
        if observed_path != expected_path:
            raise F2PortsError(f"stage {stage} requires {required_name}")
        predecessor = validate_ports_manifest(
            prior_path,
            expected_stage=predecessor_stage,
            expected_host_execution_sha=host_execution_sha,
            expected_firmware_source_sha=firmware_source_sha,
        )
        prior_roles = {
            "leader": predecessor["leader"],
            "follower": predecessor["follower"],
        }
        for role in ("leader", "follower"):
            for key in ("usb_serial", "chip_id"):
                if canonical_bindings[role][key] != prior_roles[role][key]:
                    raise F2PortsError(
                        f"{role} {key} continuity failed from "
                        f"{predecessor_stage} to {stage}"
                    )
        previous = sha256_file(prior_path)

    payload: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "stage": stage,
        "host_execution_sha": host_execution_sha,
        "firmware_source_sha": firmware_source_sha,
        "leader": canonical_bindings["leader"],
        "follower": canonical_bindings["follower"],
        "created_at_utc": created_at_utc or _created_at_utc(),
        "previous_manifest_sha256": previous,
    }
    _write_json_exclusive(target, payload)
    return validate_ports_manifest(
        target,
        expected_stage=stage,
        expected_host_execution_sha=host_execution_sha,
        expected_firmware_source_sha=firmware_source_sha,
    )


def resolve_and_write_ports_manifest(
    stage: str,
    output_dir: Path | str,
    *,
    host_execution_sha: str,
    firmware_source_sha: str,
    prior_manifest: Path | str | None = None,
    port_provider: Callable[[], object] | None = None,
    serial_factory: Callable[[str, int], object] | None = None,
    timeout_s: float = 5.0,
    baud: int = capture.DEFAULT_BAUD,
) -> dict[str, object]:
    """Resolve live identities and persist the resulting stage manifest."""
    target = Path(output_dir) / f"ports_{stage}.json"
    if target.exists() or target.is_symlink():
        raise F2PortsError(f"refusing overwrite; {target} already exists")
    observed = resolve_bindings(
        port_provider=port_provider,
        serial_factory=serial_factory,
        timeout_s=timeout_s,
        baud=baud,
    )
    return write_ports_manifest(
        stage,
        output_dir,
        observed,
        host_execution_sha=host_execution_sha,
        firmware_source_sha=firmware_source_sha,
        prior_manifest=prior_manifest,
    )


def main(argv: list[str] | None = None) -> int:
    from . import f2_capture
    parser = argparse.ArgumentParser(
        description="Resolve F2 devices by USB serial and write a chained port manifest"
    )
    parser.add_argument(
        "--stage", choices=("pre_A", "A", "B", "C1"), required=True
    )
    parser.add_argument("--host-execution-sha", required=True)
    parser.add_argument("--firmware-source-sha", required=True)
    parser.add_argument("--image-set-manifest", type=Path, required=True)
    parser.add_argument("--ports-manifest", type=Path)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--timeout-s", type=float, default=5.0)
    args = parser.parse_args(argv)
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
            parser.error(str(error))
        parser.error("host execution SHA does not equal current HEAD")
    if args.host_execution_sha == args.firmware_source_sha:
        parser.error(
            "host execution SHA and firmware source SHA must remain distinct"
        )
    try:
        f2_capture._require_run_open(repo_root, args.run_root)
        f2_capture._require_clean_host_inputs(repo_root)
        out_dir = (
            f2_capture._run_tracked_root(repo_root, args.run_root)
            / "runtime"
        )
    except f2_capture.F2ContractError as error:
        parser.error(str(error))
    from . import f2_image_set
    try:
        image_set = f2_image_set.load(
            args.image_set_manifest, repo_root=repo_root
        )
    except f2_image_set.F2ImageSetError as error:
        parser.error(str(error))
    if image_set["firmware_source_sha"] != args.firmware_source_sha:
        parser.error("firmware source SHA does not match image-set manifest")
    try:
        payload = resolve_and_write_ports_manifest(
            args.stage,
            out_dir,
            host_execution_sha=args.host_execution_sha,
            firmware_source_sha=args.firmware_source_sha,
            prior_manifest=args.ports_manifest,
            timeout_s=args.timeout_s,
        )
    except F2PortsError as error:
        parser.error(str(error))
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI boundary
    raise SystemExit(main())
