"""Controlled two-device C1-to-C2 reboot and runtime continuity proof.

This controller is the only normal F2 path that emits ``:reset``.  It resolves
both devices by USB serial, verifies their chip identities, opens both reset
streams before sending either command, then rebinds and proves the application
images are unchanged while both boot nonces are new.
"""

from __future__ import annotations

import argparse
import functools
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from . import (
    capture,
    f2_capture,
    f2_image_set,
    f2_ports,
    f2_status,
)

SCHEMA_VERSION = 1
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_BOOT_NONCE_RE = re.compile(r"^[0-9a-f]{16}$")
_ADV_READY_RE = re.compile(
    r"\[k1_sync_diag\] adv scan_rsp_configured=1 uuid=1 "
    r"name=[01] start=1 active=1"
)
_SCAN_READY_RE = re.compile(
    r"\[k1_sync_diag\] scan_start ok=1 active=1"
)
_DISCOVERY_RE = re.compile(
    r"\[k1_sync_diag\] discovered uuid=1 name_match=[01] scan_stop=[01]"
)


class F2RebootError(RuntimeError):
    """Controlled reboot preflight, action, or continuity proof failure."""


def _created_at_utc() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def _normalise_c1_identity(
    identity: object,
) -> dict[str, dict[str, str | int]]:
    if isinstance(identity, dict) and "roles" in identity:
        identity = identity["roles"]
    if not isinstance(identity, dict) or set(identity) != {"leader", "follower"}:
        raise F2RebootError("C1 identity requires leader and follower roles only")

    result: dict[str, dict[str, str | int]] = {}
    for role in ("leader", "follower"):
        observed = identity.get(role)
        if not isinstance(observed, dict):
            raise F2RebootError(f"C1 {role} identity must be an object")
        expected = f2_ports.ROLE_CONTRACT[role]
        chip_id = observed.get("chip_id")
        image_id = observed.get("app_elf_sha256")
        boot_nonce = observed.get("boot_nonce")
        uptime_ms = observed.get("uptime_ms")
        reset_reason = observed.get("reset_reason")
        if not isinstance(chip_id, str) or chip_id.upper() != expected["chip_id"]:
            raise F2RebootError(
                f"C1 {role} chip mismatch: observed {chip_id!r}, "
                f"expected {expected['chip_id']}"
            )
        if not isinstance(image_id, str) or not _SHA256_RE.fullmatch(image_id):
            raise F2RebootError(f"C1 {role} application image ID is malformed")
        if not isinstance(boot_nonce, str) or not _BOOT_NONCE_RE.fullmatch(
            boot_nonce
        ):
            raise F2RebootError(f"C1 {role} boot nonce is malformed")
        if (
            not isinstance(uptime_ms, int)
            or isinstance(uptime_ms, bool)
            or uptime_ms < 0
        ):
            raise F2RebootError(f"C1 {role} uptime is malformed")
        if not isinstance(reset_reason, int) or isinstance(reset_reason, bool):
            raise F2RebootError(f"C1 {role} reset reason is malformed")
        result[role] = {
            "chip_id": chip_id.upper(),
            "app_elf_sha256": image_id,
            "boot_nonce": boot_nonce,
            "uptime_ms": uptime_ms,
            "reset_reason": reset_reason,
        }
    if result["leader"]["boot_nonce"] == result["follower"]["boot_nonce"]:
        raise F2RebootError("C1 leader and follower boot nonces are not distinct")
    return result


def _verify_binding_continuity(
    observed: dict[str, dict[str, str]],
    manifest: dict[str, object],
    *,
    label: str,
) -> None:
    for role in ("leader", "follower"):
        for key in ("usb_serial", "chip_id"):
            if observed[role][key] != manifest[role][key]:
                raise F2RebootError(
                    f"{label} {role} {key} differs from C1 ports manifest"
                )


def _open_reset_streams(
    bindings: dict[str, dict[str, str]],
    *,
    serial_factory: Callable[[str, int], object],
    baud: int,
) -> dict[str, object]:
    streams: dict[str, object] = {}
    try:
        for role in ("leader", "follower"):
            stream = serial_factory(bindings[role]["port"], baud)
            if hasattr(stream, "dtr"):
                stream.dtr = False
            if hasattr(stream, "rts"):
                stream.rts = False
            streams[role] = stream
    except Exception as error:
        for stream in streams.values():
            try:
                stream.close()
            except Exception:
                pass
        raise F2RebootError(
            f"could not open both reset streams before action: {error}"
        ) from error
    return streams


def _send_typed_resets(
    bindings: dict[str, dict[str, str]],
    *,
    serial_factory: Callable[[str, int], object],
    baud: int,
    timeout_s: float,
) -> dict[str, dict[str, str]]:
    streams = _open_reset_streams(
        bindings, serial_factory=serial_factory, baud=baud
    )
    try:
        acknowledgements: dict[str, dict[str, str]] = {}
        for role in ("leader", "follower"):
            sent_at = (
                datetime.now(timezone.utc)
                .isoformat(timespec="microseconds")
                .replace("+00:00", "Z")
            )
            streams[role].write(b":reset\n")
            streams[role].flush()
            deadline = time.monotonic() + timeout_s
            ack = None
            while time.monotonic() < deadline:
                raw = streams[role].readline()
                if not raw:
                    time.sleep(0.001)
                    continue
                line = (
                    raw.decode("utf-8", errors="replace").strip()
                    if isinstance(raw, bytes)
                    else str(raw).strip()
                )
                if line == "SBOK":
                    ack = line
                    break
            if ack is None:
                raise F2RebootError(f"{role} reset ACK missing")
            acknowledgements[role] = {
                "sent_at_utc": sent_at,
                "ack": str(ack),
            }
    except Exception as error:
        raise F2RebootError(f"typed :reset failed: {error}") from error
    finally:
        for stream in streams.values():
            try:
                stream.close()
            except Exception:
                pass
    return acknowledgements


def _cold_start_checks(
    leader_text: str, follower_text: str, sync_status: dict
) -> dict[str, bool]:
    return {
        "leader_advertising_ready": bool(_ADV_READY_RE.search(leader_text)),
        "follower_scan_started": bool(_SCAN_READY_RE.search(follower_text)),
        "follower_uuid_discovered": bool(_DISCOVERY_RE.search(follower_text)),
        "leader_link_ready_snapshot": bool(
            sync_status.get("leader", {}).get("linked")
        ),
        "follower_link_ready_snapshot": bool(
            sync_status.get("follower", {}).get("linked")
        ),
    }


def _capture_c2_startup(
    bindings: dict[str, dict[str, str]],
    *,
    output_dir: Path,
    repo_root: Path,
    serial_factory: Callable[[str, int], object],
    baud: int,
    duration_s: float,
    status_timeout_s: float,
    label: str = "c2",
) -> dict[str, object]:
    """Capture both C2 boot streams and prove adv/scan/discovery/link startup."""
    if duration_s <= 0:
        raise F2RebootError("C2 startup capture duration must be positive")
    logs = {
        role: output_dir / f"{label}_startup_{role}.log"
        for role in ("leader", "follower")
    }
    if any(path.exists() or path.is_symlink() for path in logs.values()):
        raise F2RebootError("refusing to overwrite C2 startup capture")
    streams: dict[str, object] = {}
    handles: dict[str, object] = {}
    try:
        for role in ("leader", "follower"):
            streams[role] = serial_factory(bindings[role]["port"], baud)
            if hasattr(streams[role], "dtr"):
                streams[role].dtr = False
            if hasattr(streams[role], "rts"):
                streams[role].rts = False
            handles[role] = logs[role].open("x", encoding="utf-8")
        dual = capture.DualCapture(
            streams["leader"],
            streams["follower"],
            capture._RoleWriter(handles["leader"]),
            capture._RoleWriter(handles["follower"]),
        )
        dual.pump(duration_s)
        sync_status = dual.capture_sync_status(status_timeout_s)
    except capture.CaptureContractError as error:
        raise F2RebootError(f"C2 startup capture failed: {error}") from error
    finally:
        for handle in handles.values():
            try:
                handle.close()
            except Exception:
                pass
        for stream in streams.values():
            try:
                stream.close()
            except Exception:
                pass

    leader_text = logs["leader"].read_text(
        encoding="utf-8", errors="replace"
    )
    follower_text = logs["follower"].read_text(
        encoding="utf-8", errors="replace"
    )
    checks = _cold_start_checks(leader_text, follower_text, sync_status)
    if not all(checks.values()):
        failed = sorted(key for key, value in checks.items() if not value)
        raise F2RebootError(
            "C2 cold-start establishment evidence failed: "
            + ", ".join(failed)
        )
    return {
        "status": "PASS",
        "duration_s": duration_s,
        "checks": checks,
        "sync_status": sync_status,
        "logs": {
            role: f2_capture._evidence_record(path, repo_root)
            for role, path in logs.items()
        },
    }


def _read_post_reboot_identity(
    bindings: dict[str, dict[str, str]],
    *,
    serial_factory: Callable[[str, int], object],
    baud: int,
    timeout_s: float,
) -> dict[str, dict[str, str | int]]:
    identities: dict[str, dict[str, str | int]] = {}
    for role in ("leader", "follower"):
        path = bindings[role]["port"]
        try:
            stream = serial_factory(path, baud)
        except Exception as error:
            raise F2RebootError(
                f"cannot open post-reboot {role} port {path}: {error}"
            ) from error
        try:
            if hasattr(stream, "dtr"):
                stream.dtr = False
            if hasattr(stream, "rts"):
                stream.rts = False

            def match_image(line: str):
                match = capture._IMAGE_ID_RE.fullmatch(line)
                return match.group(1) if match is not None else None

            image_id = f2_ports.query_identity(
                stream,
                "image_id",
                match_image,
                timeout_s=timeout_s,
            )

            def match_build(line: str):
                match = capture._BUILD_RE.fullmatch(line)
                return match.groups() if match is not None else None

            version, git_hash, epoch, env = f2_ports.query_identity(
                stream,
                "build",
                match_build,
                timeout_s=timeout_s,
            )

            def match_runtime(line: str):
                match = capture._RUNTIME_ID_RE.fullmatch(line)
                return match.groups() if match is not None else None

            boot_nonce, uptime_ms, reset_reason = f2_ports.query_identity(
                stream,
                "runtime_id",
                match_runtime,
                timeout_s=timeout_s,
            )
        except f2_ports.F2PortsError as error:
            raise F2RebootError(
                f"post-reboot {role} identity read-back failed: {error}"
            ) from error
        finally:
            try:
                stream.close()
            except Exception:
                pass
        identities[role] = {
            "usb_serial": bindings[role]["usb_serial"],
            "port": path,
            "chip_id": bindings[role]["chip_id"],
            "app_elf_sha256": str(image_id),
            "version": str(version),
            "git": str(git_hash),
            "epoch": int(epoch),
            "env": str(env),
            "boot_nonce": str(boot_nonce),
            "uptime_ms": int(uptime_ms),
            "reset_reason": int(reset_reason),
        }
    return identities


def _prove_transition(
    before: dict[str, dict[str, str | int]],
    after: dict[str, dict[str, str | int]],
    *,
    firmware_source_sha: str,
) -> dict[str, dict[str, bool]]:
    checks: dict[str, dict[str, bool]] = {}
    failures: list[str] = []
    for role in ("leader", "follower"):
        role_checks = {
            "same_application_image": (
                after[role]["app_elf_sha256"]
                == before[role]["app_elf_sha256"]
            ),
            "new_boot_nonce": (
                after[role]["boot_nonce"] != before[role]["boot_nonce"]
            ),
            "chip_identity_preserved": (
                after[role]["chip_id"] == before[role]["chip_id"]
            ),
            "firmware_source_preserved": (
                isinstance(after[role].get("git"), str)
                and len(str(after[role]["git"])) >= 7
                and firmware_source_sha.startswith(str(after[role]["git"]))
            ),
            "environment_preserved": (
                after[role].get("env")
                == (
                    "k1_sync_probe_main"
                    if role == "leader"
                    else "k1_sync_probe_bench"
                )
            ),
            "expected_software_reset_reason": (
                after[role].get("reset_reason") == 3
            ),
        }
        checks[role] = role_checks
        failures.extend(
            f"{role}.{name}" for name, passed in role_checks.items() if not passed
        )
    if after["leader"]["boot_nonce"] == after["follower"]["boot_nonce"]:
        failures.append("post_reboot_boot_nonces_not_distinct")
    if failures:
        raise F2RebootError(
            "C1-to-C2 continuity proof failed: " + ", ".join(failures)
        )
    return checks


def _prove_live_c1(
    captured: dict[str, dict[str, str | int]],
    live: dict[str, dict[str, str | int]],
) -> dict[str, dict[str, bool]]:
    checks: dict[str, dict[str, bool]] = {}
    failures: list[str] = []
    for role in ("leader", "follower"):
        role_checks = {
            "same_application_image": (
                live[role]["app_elf_sha256"]
                == captured[role]["app_elf_sha256"]
            ),
            "same_boot_nonce": (
                live[role]["boot_nonce"] == captured[role]["boot_nonce"]
            ),
            "uptime_not_rewound": (
                int(live[role]["uptime_ms"])
                >= int(captured[role]["uptime_ms"])
            ),
            "chip_identity_preserved": (
                live[role]["chip_id"] == captured[role]["chip_id"]
            ),
        }
        checks[role] = role_checks
        failures.extend(
            f"{role}.{name}" for name, passed in role_checks.items() if not passed
        )
    if failures:
        raise F2RebootError(
            "live pre-reset identity is not the captured C1 boot: "
            + ", ".join(failures)
        )
    return checks


def _write_json_exclusive(path: Path, payload: dict[str, object]) -> None:
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    try:
        with path.open("x", encoding="utf-8") as output:
            output.write(text)
            output.flush()
            os.fsync(output.fileno())
    except FileExistsError as error:
        raise F2RebootError(f"refusing overwrite; {path} already exists") from error
    except OSError as error:
        raise F2RebootError(f"cannot write reboot evidence {path}: {error}") from error


def _close_run_on_c2_failure(function):
    """Make any production C2-controller failure terminal and immutable."""

    @functools.wraps(function)
    def wrapped(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except Exception as error:
            if kwargs.get("run_root") is not None:
                marker = Path(kwargs["output_dir"]).parent / "RUN_BLOCKED.json"
                if not marker.exists() and not marker.is_symlink():
                    try:
                        _write_json_exclusive(
                            marker,
                            {
                                "schema_version": 1,
                                "status": "BLOCKED",
                                "reason": "c2_controller_failed",
                                "error": str(error),
                                "host_execution_sha": kwargs.get(
                                    "host_execution_sha"
                                ),
                                "firmware_source_sha": kwargs.get(
                                    "firmware_source_sha"
                                ),
                                "f3_authorised": False,
                                "created_at_utc": _created_at_utc(),
                            },
                        )
                    except F2RebootError:
                        # Preserve the original controller failure. If the
                        # marker raced or storage failed, existing immutable
                        # evidence and missing C2 PASS still forbid progress.
                        pass
            raise

    return wrapped


@_close_run_on_c2_failure
def controlled_c2_reboot(
    *,
    output_dir: Path | str,
    run_root: Path | str | None = None,
    host_execution_sha: str,
    firmware_source_sha: str,
    image_set_manifest: Path | str,
    c1_ports_manifest: Path | str,
    c1_identity: object,
    c1_case_manifest: Path | str,
    case_b_flash_manifest: Path | str,
    c2_pre_attestation: Path | str,
    port_provider: Callable[[], object] | None = None,
    serial_factory: Callable[[str, int], object] | None = None,
    timeout_s: float = 5.0,
    reboot_settle_s: float = 0.0,
    startup_capture_s: float = 20.0,
    baud: int = capture.DEFAULT_BAUD,
    repo_root_override: Path | None = None,
    host_head_reader=f2_capture._git_head,
    image_set_loader=f2_image_set.load,
    startup_capture=_capture_c2_startup,
) -> dict[str, object]:
    """Reset both C1 devices and write C2 proof only after continuity passes."""
    if timeout_s <= 0:
        raise F2RebootError("timeout_s must be positive")
    if reboot_settle_s < 0:
        raise F2RebootError("reboot_settle_s must not be negative")
    if startup_capture_s <= 0:
        raise F2RebootError("startup_capture_s must be positive")
    root = Path(output_dir)
    ports_c2_path = root / "ports_C2.json"
    report_path = root / "reboot_C2.json"
    for target in (ports_c2_path, report_path):
        if target.exists() or target.is_symlink():
            raise F2RebootError(f"refusing overwrite; {target} already exists")

    repo_root = (
        repo_root_override.resolve()
        if repo_root_override is not None
        else Path(__file__).resolve().parents[2]
    )
    authority_run_root = (
        Path(run_root).resolve()
        if run_root is not None
        else root.parent.resolve()
    )
    observed_host_sha = host_head_reader(repo_root)
    if observed_host_sha != host_execution_sha:
        try:
            f2_capture._close_run_for_host_drift(
                repo_root,
                authority_run_root,
                expected_host_sha=host_execution_sha,
                observed_host_sha=observed_host_sha,
            )
        except f2_capture.F2ContractError as error:
            raise F2RebootError(str(error)) from error
        raise F2RebootError(
            "host execution SHA does not equal current committed HEAD"
        )
    if repo_root_override is None:
        try:
            expected_runtime = (
                f2_capture._run_tracked_root(
                    repo_root, authority_run_root
                )
                / "runtime"
            )
            if root.resolve() != expected_runtime.resolve():
                raise f2_capture.F2ContractError(
                    "C2 reboot output must be the tracked run runtime"
                )
            f2_capture._require_run_open(repo_root, authority_run_root)
            f2_capture._require_clean_host_inputs(repo_root)
        except f2_capture.F2ContractError as error:
            raise F2RebootError(str(error)) from error
    if host_execution_sha == firmware_source_sha:
        raise F2RebootError(
            "host execution SHA and firmware source SHA must remain distinct"
        )
    try:
        image_set = image_set_loader(
            Path(image_set_manifest), repo_root=repo_root
        )
    except f2_image_set.F2ImageSetError as error:
        raise F2RebootError(f"image set is not ready: {error}") from error
    if image_set["firmware_source_sha"] != firmware_source_sha:
        raise F2RebootError(
            "firmware source SHA does not match image-set manifest"
        )

    c1_path = Path(c1_ports_manifest)
    try:
        c1_ports = f2_ports.validate_ports_manifest(
            c1_path,
            expected_stage="C1",
            expected_host_execution_sha=host_execution_sha,
            expected_firmware_source_sha=firmware_source_sha,
        )
    except f2_ports.F2PortsError as error:
        raise F2RebootError(f"C1 ports manifest invalid: {error}") from error
    try:
        if c1_path.resolve(strict=True).parent != root.resolve(strict=True):
            raise F2RebootError(
                "C1 ports manifest must be in the C2 output directory"
            )
    except OSError as error:
        raise F2RebootError(f"cannot resolve C1/output paths: {error}") from error

    c1_case_path = Path(c1_case_manifest)
    case_b_flash_path = Path(case_b_flash_manifest)
    for evidence_path, label in (
        (c1_case_path, "C1 case manifest"),
        (case_b_flash_path, "Case-B flash manifest"),
    ):
        if evidence_path.is_symlink() or not evidence_path.is_file():
            raise F2RebootError(f"{label} is missing or indirect")
    c1_case = _read_json(c1_case_path)
    case_b_flash = _read_json(case_b_flash_path)
    if not isinstance(c1_case, dict) or (
        c1_case.get("case") != "C1"
        or c1_case.get("case_status") != "PASS"
        or c1_case.get("host_execution_sha") != host_execution_sha
        or c1_case.get("firmware_source_sha") != firmware_source_sha
    ):
        raise F2RebootError("C1 software evidence is not a bound PASS")
    if not isinstance(case_b_flash, dict) or (
        case_b_flash.get("case") != "B"
        or case_b_flash.get("status") != "PASS"
        or case_b_flash.get("host_execution_sha") != host_execution_sha
        or case_b_flash.get("firmware_source_sha") != firmware_source_sha
    ):
        raise F2RebootError("Case-B flash evidence is not a bound PASS")
    try:
        pre = f2_status.validate_pre_attestation(
            Path(c2_pre_attestation), "C2", root.parent
        )
    except f2_status.F2StatusError as error:
        raise F2RebootError(f"C2 pre-attestation is invalid: {error}") from error

    before = _normalise_c1_identity(c1_identity)
    for role in ("leader", "follower"):
        if before[role]["chip_id"] != c1_ports[role]["chip_id"]:
            raise F2RebootError(
                f"C1 {role} identity differs from ports manifest"
            )
        upload = case_b_flash.get("uploads", {}).get(role)
        if (
            not isinstance(upload, dict)
            or upload.get("app_elf_sha256")
            != before[role]["app_elf_sha256"]
        ):
            raise F2RebootError(
                f"C1 {role} application differs from Case-B flash evidence"
            )

    provider = port_provider or f2_ports._default_port_provider
    opener = serial_factory or capture._open_serial
    try:
        live_c1 = f2_ports.resolve_bindings(
            port_provider=provider,
            serial_factory=opener,
            timeout_s=timeout_s,
            baud=baud,
        )
    except f2_ports.F2PortsError as error:
        raise F2RebootError(f"C1 live identity preflight failed: {error}") from error
    _verify_binding_continuity(live_c1, c1_ports, label="live C1")
    live_before = _read_post_reboot_identity(
        live_c1,
        serial_factory=opener,
        baud=baud,
        timeout_s=timeout_s,
    )
    c1_checks = _prove_live_c1(before, live_before)

    acknowledgements = _send_typed_resets(
        live_c1,
        serial_factory=opener,
        baud=baud,
        timeout_s=timeout_s,
    )
    if reboot_settle_s:
        time.sleep(reboot_settle_s)

    try:
        c2_usb_paths = f2_ports.resolve_usb_paths_by_serial(
            port_provider=provider,
            timeout_s=timeout_s,
        )
    except f2_ports.F2PortsError as error:
        raise F2RebootError(f"C2 USB rebinding failed: {error}") from error
    _verify_binding_continuity(c2_usb_paths, c1_ports, label="C2 USB")
    cold_start_capture = startup_capture(
        c2_usb_paths,
        output_dir=root,
        repo_root=repo_root,
        serial_factory=opener,
        baud=baud,
        duration_s=startup_capture_s,
        status_timeout_s=timeout_s,
    )
    if (
        not isinstance(cold_start_capture, dict)
        or cold_start_capture.get("status") != "PASS"
    ):
        raise F2RebootError("C2 startup capture did not return PASS")
    try:
        live_c2 = f2_ports.resolve_bindings(
            port_provider=provider,
            serial_factory=opener,
            timeout_s=timeout_s,
            baud=baud,
        )
    except f2_ports.F2PortsError as error:
        raise F2RebootError(f"C2 live identity preflight failed: {error}") from error
    _verify_binding_continuity(live_c2, c1_ports, label="live C2")
    after = _read_post_reboot_identity(
        live_c2,
        serial_factory=opener,
        baud=baud,
        timeout_s=timeout_s,
    )
    checks = _prove_transition(
        before, after, firmware_source_sha=firmware_source_sha
    )

    try:
        ports_c2 = f2_ports.write_ports_manifest(
            "C2",
            root,
            live_c2,
            host_execution_sha=host_execution_sha,
            firmware_source_sha=firmware_source_sha,
            prior_manifest=c1_path,
        )
    except f2_ports.F2PortsError as error:
        raise F2RebootError(f"cannot persist C2 ports manifest: {error}") from error

    report: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "transition": "C1->C2",
        "status": "PASS",
        "host_execution_sha": host_execution_sha,
        "firmware_source_sha": firmware_source_sha,
        "reset_command": ":reset",
        "reset_acknowledgements": acknowledgements,
        "cold_start_capture": cold_start_capture,
        "c2_pre_attestation": pre["evidence"],
        "c1_case_manifest": {
            "name": c1_case_path.name,
            "sha256": f2_ports.sha256_file(c1_case_path),
        },
        "case_b_flash_manifest": {
            "name": case_b_flash_path.name,
            "sha256": f2_ports.sha256_file(case_b_flash_path),
        },
        "c1_ports_manifest": {
            "name": c1_path.name,
            "sha256": f2_ports.sha256_file(c1_path),
        },
        "c2_ports_manifest": {
            "name": ports_c2_path.name,
            "sha256": f2_ports.sha256_file(ports_c2_path),
        },
        "roles": {
            role: {
                "before": before[role],
                "live_before_reset": live_before[role],
                "c1_checks": c1_checks[role],
                "after": after[role],
                "checks": checks[role],
            }
            for role in ("leader", "follower")
        },
    }
    _write_json_exclusive(report_path, report)
    return report


def _read_json(path: Path) -> object:
    if path.is_symlink():
        raise F2RebootError(f"refusing symlink identity file: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise F2RebootError(f"cannot read C1 identity {path}: {error}") from error


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Perform the controlled F2 C1-to-C2 two-device reboot"
    )
    parser.add_argument("--host-execution-sha", required=True)
    parser.add_argument("--firmware-source-sha", required=True)
    parser.add_argument("--image-set-manifest", type=Path, required=True)
    parser.add_argument("--ports-manifest", type=Path, required=True)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--c1-identity", type=Path, required=True)
    parser.add_argument("--c1-case-manifest", type=Path, required=True)
    parser.add_argument("--case-b-flash-manifest", type=Path, required=True)
    parser.add_argument("--c2-pre-attestation", type=Path, required=True)
    parser.add_argument("--timeout-s", type=float, default=5.0)
    parser.add_argument("--reboot-settle-s", type=float, default=0.0)
    parser.add_argument("--startup-capture-s", type=float, default=20.0)
    args = parser.parse_args(argv)
    repo_root = Path(__file__).resolve().parents[2]
    try:
        runtime_root = (
            f2_capture._run_tracked_root(repo_root, args.run_root)
            / "runtime"
        )
    except f2_capture.F2ContractError as error:
        parser.error(str(error))
    try:
        result = controlled_c2_reboot(
            output_dir=runtime_root,
            run_root=args.run_root,
            host_execution_sha=args.host_execution_sha,
            firmware_source_sha=args.firmware_source_sha,
            image_set_manifest=args.image_set_manifest,
            c1_ports_manifest=args.ports_manifest,
            c1_identity=_read_json(args.c1_identity),
            c1_case_manifest=args.c1_case_manifest,
            case_b_flash_manifest=args.case_b_flash_manifest,
            c2_pre_attestation=args.c2_pre_attestation,
            timeout_s=args.timeout_s,
            reboot_settle_s=args.reboot_settle_s,
            startup_capture_s=args.startup_capture_s,
        )
    except (F2RebootError, OSError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI boundary
    raise SystemExit(main())
