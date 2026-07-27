"""Guarded exact-application writer for F2 A/B.

This controller never builds and never invokes PlatformIO's upload target. It
validates one frozen reviewed-image set, proves every target and partition
table before the first write, then writes only the selected application image
with the pinned esptool package. C1/C2 have no flash path and reuse Case B.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import subprocess
import time
from pathlib import Path

from serial import Serial
from serial.tools import list_ports

from . import capture, f2_capture, f2_image_set, f2_ports, gate_eval


class F2FlashError(RuntimeError):
    """Exact-image validation, target guard, flash, or evidence failure."""


def _run_logged(command: list[str], log_path: Path, *, append: bool) -> int:
    mode = "a" if append else "x"
    with log_path.open(mode, encoding="utf-8") as output:
        output.write(f"$ {json.dumps(command)}\n")
        output.flush()
        completed = subprocess.run(
            command,
            stdout=output,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        output.write(f"[exit={completed.returncode}]\n")
        output.flush()
    return completed.returncode


def _write_manifest_once(path: Path, payload: dict) -> None:
    """Durably publish evidence without an overwrite-capable rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as output:
        json.dump(payload, output, indent=2, sort_keys=True)
        output.write("\n")
        output.flush()
        os.fsync(output.fileno())


def _port_for_usb_serial(usb_serial: str, timeout_s: float) -> str:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        for port in list_ports.comports():
            if (port.serial_number or "") == usb_serial:
                return str(port.device)
        time.sleep(0.1)
    raise F2FlashError(
        f"USB serial {usb_serial} did not re-enumerate before timeout"
    )


def _query(stream: Serial, command: str, matcher, timeout_s: float):
    stream.reset_input_buffer()
    stream.write(f":{command}\n".encode("ascii"))
    stream.flush()
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        raw = stream.readline()
        if not raw:
            time.sleep(0.001)
            continue
        line = raw.decode("utf-8", errors="replace").strip()
        value = matcher(line)
        if value is not None:
            return value
    raise F2FlashError(f":{command} read-back missing before timeout")


def _postflash_identity(
    usb_serial: str, expected: dict[str, str], timeout_s: float
) -> dict[str, str | int]:
    port = _port_for_usb_serial(usb_serial, timeout_s)
    with Serial(
        port=port,
        baudrate=capture.DEFAULT_BAUD,
        timeout=0.05,
        write_timeout=1.0,
        exclusive=True,
    ) as stream:
        stream.dtr = False
        stream.rts = False
        chip = _query(
            stream,
            "chip_id",
            lambda line: line.upper()
            if re.fullmatch(r"[0-9A-F]{8}", line.upper())
            else None,
            timeout_s,
        )

        def match_build(line: str):
            match = capture._BUILD_RE.fullmatch(line)
            return match.groups() if match is not None else None

        version, git_hash, epoch, env = _query(
            stream, "build", match_build, timeout_s
        )

        def match_image(line: str):
            match = capture._IMAGE_ID_RE.fullmatch(line)
            return match.group(1) if match is not None else None

        image_id = _query(stream, "image_id", match_image, timeout_s)

        def match_runtime(line: str):
            match = capture._RUNTIME_ID_RE.fullmatch(line)
            return match.groups() if match is not None else None

        boot_nonce, uptime_ms, reset_reason = _query(
            stream, "runtime_id", match_runtime, timeout_s
        )

    if chip != expected["chip_id"]:
        raise F2FlashError(
            f"post-flash chip mismatch: {chip} != {expected['chip_id']}"
        )
    if env != expected["env"]:
        raise F2FlashError(
            f"post-flash env mismatch: {env} != {expected['env']}"
        )
    if (
        len(git_hash) < 7
        or not expected["firmware_source_sha"].startswith(git_hash)
    ):
        raise F2FlashError(
            "post-flash build does not match reviewed firmware source"
        )
    if image_id != expected["app_elf_sha256"]:
        raise F2FlashError(
            "post-flash app ELF identity does not match reviewed image"
        )
    return {
        "port": port,
        "chip_id": chip,
        "version": version,
        "git": git_hash,
        "epoch": int(epoch),
        "env": env,
        "app_elf_sha256": image_id,
        "boot_nonce": boot_nonce,
        "uptime_ms": int(uptime_ms),
        "reset_reason": int(reset_reason),
    }


def _preflash_chip_identity(
    supplied_port: str,
    usb_serial: str,
    expected_chip: str,
    timeout_s: float,
) -> dict[str, str]:
    """Resolve USB identity and prove eFuse identity before any write."""
    observed_port = _port_for_usb_serial(usb_serial, timeout_s)
    if observed_port != supplied_port:
        raise F2FlashError(
            f"USB serial {usb_serial} resolved to {observed_port}, "
            f"not supplied port {supplied_port}"
        )
    with Serial(
        port=observed_port,
        baudrate=capture.DEFAULT_BAUD,
        timeout=0.05,
        write_timeout=1.0,
        exclusive=True,
    ) as stream:
        stream.dtr = False
        stream.rts = False
        chip = _query(
            stream,
            "chip_id",
            lambda line: line.upper()
            if re.fullmatch(r"[0-9A-F]{8}", line.upper())
            else None,
            timeout_s,
        )
    if chip != expected_chip:
        raise F2FlashError(
            f"pre-flash chip mismatch: {chip} != {expected_chip}"
        )
    return {
        "port": observed_port,
        "usb_serial": usb_serial,
        "chip_id": chip,
    }


def _target(case_name: str, role: str) -> dict[str, str]:
    expected = f2_capture._expected_device(case_name, role)
    usb_serial = (
        f2_capture.LEADER_USB_SERIAL
        if role == "leader"
        else f2_capture.FOLLOWER_USB_SERIAL
    )
    return {**expected, "usb_serial": usb_serial}


def _require_clean_inputs(repo_root: Path) -> None:
    paths = [
        "platformio.ini",
        "SPECTRASYNQ_K1_FIRMWARE",
        "libraries",
        "scripts/platformio",
        "scripts/dual_sync_probe",
    ]
    completed = subprocess.run(
        [
            "git",
            "status",
            "--porcelain",
            "--untracked-files=all",
            "--",
            *paths,
        ],
        cwd=repo_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0 or completed.stdout.strip():
        raise F2FlashError(
            "tracked firmware/image/flash-controller inputs are dirty; "
            "commit or stop"
        )


def _esptool_command(port: str, operation: list[str]) -> list[str]:
    return [
        "pio",
        "pkg",
        "exec",
        "--package",
        f2_image_set.ESPTOOL_PACKAGE,
        "--",
        "esptool.py",
        "--chip",
        "esp32s3",
        "--port",
        port,
        "--baud",
        "921600",
        *operation,
    ]


def _guard_command(env: str, port: str) -> list[str]:
    return [
        "python3",
        "scripts/platformio/k1_upload_guard.py",
        "--env",
        env,
        "--upload-port",
        port,
    ]


def _cross_target_env(role: str) -> str:
    """Return an environment that must reject the resolved physical target."""
    if role == "leader":
        return "k1_sync_probe_bench"
    if role == "follower":
        return "k1_sync_probe_main_sync_only"
    raise F2FlashError(f"unknown flash role {role!r}")


def _postwrite_startup(
    case_name: str,
    *,
    output_dir: Path,
    repo_root: Path,
    timeout_s: float,
) -> tuple[dict[str, dict[str, str]], dict]:
    """Capture A/B establishment before identity queries consume boot logs."""
    from . import f2_reboot

    try:
        bindings = f2_ports.resolve_usb_paths_by_serial(timeout_s=timeout_s)
    except f2_ports.F2PortsError as error:
        raise F2FlashError(f"post-write USB rebinding failed: {error}") from error
    startup = f2_reboot._capture_c2_startup(
        bindings,
        output_dir=output_dir,
        repo_root=repo_root,
        serial_factory=capture._open_serial,
        baud=capture.DEFAULT_BAUD,
        duration_s=max(20.0, timeout_s),
        status_timeout_s=timeout_s,
        label=f"case_{case_name}",
    )
    return bindings, startup


def _image_evidence(image: dict, repo_root: Path) -> dict:
    return {
        "bin_path": f2_capture._repo_relative(
            image["bin_path"], repo_root
        ),
        "bin_sha256": image["bin_sha256"],
        "elf_path": f2_capture._repo_relative(
            image["elf_path"], repo_root
        ),
        "elf_sha256": image["elf_sha256"],
        "app_elf_sha256": image["app_elf_sha256"],
    }


def run(
    args,
    *,
    command_runner=_run_logged,
    identity_reader=_postflash_identity,
    preflash_reader=_preflash_chip_identity,
    startup_reader=None,
    repo_root_override: Path | None = None,
) -> dict:
    repo_root = (
        repo_root_override.resolve()
        if repo_root_override is not None
        else Path(__file__).resolve().parents[2]
    )
    host_sha = f2_capture._git_head(repo_root)
    if host_sha != args.host_execution_sha:
        f2_capture._close_run_for_host_drift(
            repo_root,
            args.run_root,
            expected_host_sha=args.host_execution_sha,
            observed_host_sha=host_sha,
        )
        raise F2FlashError(
            "host execution SHA does not equal current committed HEAD"
        )
    if args.case not in ("A", "B"):
        raise F2FlashError("C1/C2 must reuse the exact Case-B flash event")
    raw_root = args.run_root.resolve()
    if (
        not f2_capture._inside(raw_root, repo_root / "_scratch")
        or not raw_root.name.startswith("dual_sync_f2_abc_")
    ):
        raise F2FlashError(
            "run root must be _scratch/dual_sync_f2_abc_<run-id>"
        )
    run_id = raw_root.name.removeprefix("dual_sync_f2_abc_")
    try:
        f2_capture._validate_run_id(run_id)
    except f2_capture.F2ContractError as error:
        raise F2FlashError(str(error)) from error

    tracked_root = repo_root / f2_capture.TRACKED_F2_REL / run_id
    if (
        f2_capture._has_symlink_component(raw_root)
        or f2_capture._has_symlink_component(tracked_root)
    ):
        raise F2FlashError("F2 evidence roots may not contain symlinks")
    if not f2_capture._inside(
        tracked_root, repo_root / f2_capture.TRACKED_F2_REL
    ):
        raise F2FlashError("F2 tracked root escapes fixed evidence root")
    try:
        f2_capture._require_run_open(repo_root, args.run_root)
    except f2_capture.F2ContractError as error:
        raise F2FlashError(str(error)) from error
    flash_raw = raw_root / "uploads" / f"case_{args.case}"
    flash_manifest = tracked_root / "uploads" / f"flash_{args.case}.json"
    if flash_raw.exists() or flash_manifest.exists():
        raise F2FlashError("refusing to overwrite F2 flash evidence")

    image_set = f2_image_set.load(
        args.image_set_manifest, repo_root=repo_root
    )
    firmware_sha = f2_capture._resolve_commit(
        repo_root, args.firmware_source_sha
    )
    if (
        firmware_sha != args.firmware_source_sha
        or firmware_sha != image_set["firmware_source_sha"]
    ):
        raise F2FlashError(
            "image-set firmware source must be one exact full commit"
        )
    f2_capture._require_ancestor(repo_root, firmware_sha, host_sha)
    _require_clean_inputs(repo_root)

    expected_ports_stage = "pre_A" if args.case == "A" else "A"
    try:
        ports_payload = f2_ports.validate_ports_manifest(
            args.ports_manifest,
            expected_stage=expected_ports_stage,
            expected_host_execution_sha=host_sha,
            expected_firmware_source_sha=firmware_sha,
        )
    except f2_ports.F2PortsError as error:
        raise F2FlashError(f"ports manifest rejected: {error}") from error
    ports = {
        role: str(ports_payload[role]["port"])
        for role in ("leader", "follower")
    }
    prior = f2_capture.validate_case_order(
        args.case,
        raw_root,
        tracked_root,
        firmware_sha,
        host_sha,
        repo_root,
    )
    attestation = f2_capture._require_direct_file(
        args.attestation,
        tracked_root / "attestations",
        "physical attestation",
    )
    f2_capture._validate_attestation(attestation, args.case)

    flash_raw.mkdir(parents=True, exist_ok=False)
    flash_manifest.parent.mkdir(parents=True, exist_ok=True)
    image_set_record = f2_capture._evidence_record(
        image_set["manifest_path"], repo_root
    )
    roles_to_flash = (
        ("follower", "leader") if args.case == "A" else ("leader",)
    )
    preflash: dict[str, dict[str, str]] = {}
    prepared: dict[str, dict] = {}
    flashes: dict[str, dict] = {}
    operation_logs: dict[str, Path] = {}
    write_actions: list[dict] = []
    startup_reader = startup_reader or _postwrite_startup

    try:
        for role in ("leader", "follower"):
            target = _target(args.case, role)
            preflash[role] = preflash_reader(
                ports[role],
                target["usb_serial"],
                target["chip_id"],
                args.readback_timeout_s,
            )

        # Every target guard and partition-table read-back completes before the
        # first application write. A partial preflight cannot mutate hardware.
        for role in roles_to_flash:
            target = _target(args.case, role)
            env = target["env"]
            image = image_set["images"][env]
            role_dir = flash_raw / role
            role_dir.mkdir()
            log_path = role_dir / "flash.log"
            operation_logs[role] = log_path

            guard_command = _guard_command(env, ports[role])
            if command_runner(
                guard_command, log_path, append=False
            ) != 0:
                raise F2FlashError(f"{role} upload guard rejected target")
            if "verified as" not in log_path.read_text(
                encoding="utf-8", errors="replace"
            ):
                raise F2FlashError(
                    f"{role} guard log lacks target verification"
                )

            cross_guard_log = role_dir / "cross-target-guard.log"
            cross_guard_command = _guard_command(
                _cross_target_env(role), ports[role]
            )
            cross_guard_exit = command_runner(
                cross_guard_command, cross_guard_log, append=False
            )
            if cross_guard_exit != 2:
                raise F2FlashError(
                    f"{role} cross-target guard did not fail closed "
                    f"with exit 2 (observed {cross_guard_exit})"
                )
            cross_guard_text = cross_guard_log.read_text(
                encoding="utf-8", errors="replace"
            )
            if "verified as" in cross_guard_text or "expected" not in (
                cross_guard_text
            ):
                raise F2FlashError(
                    f"{role} cross-target guard lacks rejection evidence"
                )
            operation_logs[f"{role}_cross_target"] = cross_guard_log

            partition_readback = role_dir / "partition-table-readback.bin"
            partition = image_set["partition_table"]
            read_command = _esptool_command(
                ports[role],
                [
                    "read_flash",
                    hex(partition["offset"]),
                    hex(partition["size"]),
                    str(partition_readback),
                ],
            )
            if command_runner(read_command, log_path, append=True) != 0:
                raise F2FlashError(
                    f"{role} partition-table read-back failed"
                )
            if (
                partition_readback.is_symlink()
                or not partition_readback.is_file()
                or partition_readback.stat().st_size != partition["size"]
                or f2_capture._sha256(partition_readback)
                != partition["sha256"]
            ):
                raise F2FlashError(
                    f"{role} partition-table read-back mismatch"
                )

            write_command = _esptool_command(
                ports[role],
                [
                    "write_flash",
                    hex(partition["application_offset"]),
                    f2_capture._repo_relative(
                        image["bin_path"], repo_root
                    ),
                ],
            )
            prepared[role] = {
                "target": target,
                "env": env,
                "image": image,
                "log_path": log_path,
                "guard_command": guard_command,
                "cross_guard_command": cross_guard_command,
                "cross_guard_exit_code": cross_guard_exit,
                "cross_guard_log": cross_guard_log,
                "partition_read_command": read_command,
                "partition_readback": partition_readback,
                "write_command": write_command,
            }

        for role in roles_to_flash:
            item = prepared[role]
            target = item["target"]
            action = {
                "role": role,
                "command": item["write_command"],
                "attempted": True,
                "outcome": "running",
                "exit_code": None,
            }
            write_actions.append(action)
            try:
                write_exit = command_runner(
                    item["write_command"],
                    item["log_path"],
                    append=True,
                )
            except Exception:
                action["outcome"] = "error"
                raise
            action["exit_code"] = write_exit
            action["outcome"] = (
                "success" if write_exit == 0 else "failed"
            )
            if write_exit != 0:
                raise F2FlashError(
                    f"{role} application-image write failed"
                )
            image = item["image"]
            if (
                f2_capture._sha256(image["bin_path"])
                != image["bin_sha256"]
                or f2_capture._sha256(image["elf_path"])
                != image["elf_sha256"]
            ):
                raise F2FlashError(
                    f"{role} reviewed image changed during flash"
                )
            item["write_exit_code"] = write_exit

        startup_bindings, startup_capture = startup_reader(
            args.case,
            output_dir=flash_raw,
            repo_root=repo_root,
            timeout_s=args.readback_timeout_s,
        )
        for role in ("leader", "follower"):
            expected_target = _target(args.case, role)
            binding = startup_bindings.get(role)
            if (
                not isinstance(binding, dict)
                or binding.get("usb_serial")
                != expected_target["usb_serial"]
                or binding.get("chip_id") != expected_target["chip_id"]
                or not isinstance(binding.get("port"), str)
                or not binding["port"]
            ):
                raise F2FlashError(
                    f"{role} post-write USB binding is invalid"
                )
        if (
            not isinstance(startup_capture, dict)
            or startup_capture.get("status") != gate_eval.PASS
        ):
            raise F2FlashError("post-write link establishment did not PASS")

        for role in roles_to_flash:
            item = prepared[role]
            target = item["target"]
            image = item["image"]
            readback = identity_reader(
                target["usb_serial"],
                {
                    **target,
                    "firmware_source_sha": firmware_sha,
                    "app_elf_sha256": image["app_elf_sha256"],
                },
                args.readback_timeout_s,
            )
            write_exit = item["write_exit_code"]
            flashes[role] = {
                "action": "flash",
                "source_case": args.case,
                "env": item["env"],
                "chip_id": target["chip_id"],
                "usb_serial": target["usb_serial"],
                "port": ports[role],
                "preflash_identity": preflash[role],
                "guard_verified": True,
                "guard_command": item["guard_command"],
                "cross_target_guard_verified": True,
                "cross_target_guard_command": item["cross_guard_command"],
                "cross_target_guard_exit_code": item[
                    "cross_guard_exit_code"
                ],
                "cross_target_guard_log": f2_capture._evidence_record(
                    item["cross_guard_log"], repo_root
                ),
                "partition_read_command": item["partition_read_command"],
                "partition_table": {
                    "expected_path": f2_capture._repo_relative(
                        image_set["partition_table"]["path"], repo_root
                    ),
                    "expected_sha256": image_set[
                        "partition_table"
                    ]["sha256"],
                    "readback": f2_capture._evidence_record(
                        item["partition_readback"], repo_root
                    ),
                },
                "write_command": item["write_command"],
                "write_exit_code": write_exit,
                **_image_evidence(image, repo_root),
                "postflash_readback": readback,
                "log": f2_capture._evidence_record(
                    item["log_path"], repo_root
                ),
            }

        if args.case == "B":
            case_a_flash_record = prior[0]["flash_manifest"]
            case_a_flash_path = repo_root / str(
                case_a_flash_record["path"]
            )
            case_a_flash = f2_capture._read_manifest(case_a_flash_path)
            follower = copy.deepcopy(case_a_flash["uploads"]["follower"])
            follower["action"] = "reuse"
            follower["source_case"] = "A"
            follower["reused_flash_manifest"] = case_a_flash_record
            follower["reuse_preflight_identity"] = preflash["follower"]
            flashes["follower"] = follower

        next_bindings = {}
        for role in ("leader", "follower"):
            if flashes[role]["action"] == "flash":
                next_port = flashes[role]["postflash_readback"]["port"]
            else:
                next_port = startup_bindings[role]["port"]
            next_bindings[role] = {
                "port": next_port,
                "usb_serial": flashes[role]["usb_serial"],
                "chip_id": flashes[role]["chip_id"],
            }
        try:
            next_ports = f2_ports.write_ports_manifest(
                args.case,
                tracked_root / "runtime",
                next_bindings,
                host_execution_sha=host_sha,
                firmware_source_sha=firmware_sha,
                prior_manifest=args.ports_manifest,
            )
        except f2_ports.F2PortsError as error:
            raise F2FlashError(
                f"cannot persist post-flash ports manifest: {error}"
            ) from error
        next_ports_path = (
            tracked_root / "runtime" / f"ports_{args.case}.json"
        )

        manifest = {
            "schema_version": 2,
            "status": gate_eval.PASS,
            "run_id": run_id,
            "case": args.case,
            "host_execution_sha": host_sha,
            "firmware_source_sha": firmware_sha,
            "image_set": image_set_record,
            "input_ports_manifest": f2_capture._evidence_record(
                args.ports_manifest, repo_root
            ),
            "output_ports_manifest": f2_capture._evidence_record(
                next_ports_path, repo_root
            ),
            "port_bindings": next_ports,
            "startup_capture": startup_capture,
            "uploads": flashes,
        }
        _write_manifest_once(flash_manifest, manifest)
        return manifest
    except Exception as error:
        logs = {
            role: f2_capture._evidence_record(path, repo_root)
            for role, path in operation_logs.items()
            if path.is_file()
        }
        blocked = {
            "schema_version": 2,
            "status": gate_eval.BLOCKED,
            "run_id": run_id,
            "case": args.case,
            "host_execution_sha": host_sha,
            "firmware_source_sha": firmware_sha,
            "image_set": image_set_record,
            "preflash_identity": preflash,
            "prepared_roles": sorted(prepared),
            "write_actions": write_actions,
            "completed_flashes": flashes,
            "operation_logs": logs,
            "error": str(error),
        }
        _write_manifest_once(flash_manifest, blocked)
        if isinstance(error, F2FlashError):
            raise
        raise F2FlashError(str(error)) from error


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate and flash exact frozen F2 application images; "
            "never build and never invoke PlatformIO upload."
        )
    )
    parser.add_argument("--case", choices=("A", "B"), required=True)
    parser.add_argument("--host-execution-sha", required=True)
    parser.add_argument("--firmware-source-sha", required=True)
    parser.add_argument("--image-set-manifest", type=Path, required=True)
    parser.add_argument("--ports-manifest", type=Path, required=True)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--attestation", type=Path, required=True)
    parser.add_argument("--readback-timeout-s", type=float, default=20.0)
    return parser


def main(argv=None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        run(args)
    except (
        F2FlashError,
        f2_capture.F2ContractError,
        f2_image_set.F2ImageSetError,
        f2_ports.F2PortsError,
        OSError,
        ValueError,
    ) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
