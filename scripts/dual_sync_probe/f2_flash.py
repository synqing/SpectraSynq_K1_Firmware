"""Guarded, evidence-producing F2 upload controller.

This is the only F2 writer. It builds and uploads one ordered A/B device pair
through the existing PlatformIO guard, preserves the exact BIN/ELF artefacts,
and requires post-flash chip/build/image read-back before publishing a PASS
upload event. Case C deliberately has no upload path and must reuse Case B.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import shutil
import subprocess
import time
from pathlib import Path

from serial import Serial
from serial.tools import list_ports

from . import capture, f2_capture, gate_eval


class F2FlashError(RuntimeError):
    """Guarded build, upload, identity, or evidence failure."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def _app_elf_sha256(bin_path: Path) -> str:
    try:
        return f2_capture._app_elf_sha256(bin_path)
    except f2_capture.F2ContractError as error:
        raise F2FlashError(str(error)) from error


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
            "post-flash build does not match firmware source commit"
        )
    if image_id != expected["app_elf_sha256"]:
        raise F2FlashError(
            "post-flash app ELF identity does not match built image"
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
    if role == "leader":
        usb_serial = f2_capture.LEADER_USB_SERIAL
    else:
        usb_serial = f2_capture.FOLLOWER_USB_SERIAL
    return {**expected, "usb_serial": usb_serial}


def _require_clean_inputs(repo_root: Path) -> None:
    paths = [
        "platformio.ini",
        "SPECTRASYNQ_K1_FIRMWARE",
        "libraries",
        "scripts/agent/pio-build.sh",
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
            "tracked firmware/build/upload inputs are dirty; commit or stop"
        )


def run(
    args,
    *,
    command_runner=_run_logged,
    identity_reader=_postflash_identity,
    preflash_reader=_preflash_chip_identity,
    repo_root_override: Path | None = None,
) -> dict:
    repo_root = (
        repo_root_override.resolve()
        if repo_root_override is not None
        else Path(__file__).resolve().parents[2]
    )
    host_sha = f2_capture._git_head(repo_root)
    firmware_sha = f2_capture._resolve_commit(repo_root, args.firmware_sha)
    if firmware_sha != host_sha:
        raise F2FlashError(
            "guarded upload requires firmware SHA to equal current clean HEAD"
        )
    _require_clean_inputs(repo_root)
    if args.case not in ("A", "B"):
        raise F2FlashError("Case C must reuse the exact Case-B upload event")
    try:
        f2_capture._validate_run_id(args.run_id)
    except f2_capture.F2ContractError as error:
        raise F2FlashError(str(error)) from error
    if args.leader_port == args.follower_port:
        raise F2FlashError("leader and follower ports must be distinct")

    raw_root = repo_root / "_scratch" / f"dual_sync_f2_abc_{args.run_id}"
    tracked_root = repo_root / f2_capture.TRACKED_F2_REL / args.run_id
    if (
        f2_capture._has_symlink_component(raw_root)
        or f2_capture._has_symlink_component(tracked_root)
    ):
        raise F2FlashError("F2 evidence roots may not contain symlinks")
    if not f2_capture._inside(
        tracked_root, repo_root / f2_capture.TRACKED_F2_REL
    ):
        raise F2FlashError("F2 tracked root escapes fixed evidence root")
    upload_raw = raw_root / "uploads" / f"case_{args.case}"
    upload_manifest = tracked_root / "uploads" / f"flash_{args.case}.json"
    if upload_raw.exists() or upload_manifest.exists():
        raise F2FlashError("refusing to overwrite F2 upload evidence")

    ports = {"leader": args.leader_port, "follower": args.follower_port}
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
    preflash: dict[str, dict[str, str]] = {}
    for role in ("leader", "follower"):
        target = _target(args.case, role)
        preflash[role] = preflash_reader(
            ports[role],
            target["usb_serial"],
            target["chip_id"],
            args.readback_timeout_s,
        )

    upload_raw.mkdir(parents=True, exist_ok=False)
    upload_manifest.parent.mkdir(parents=True, exist_ok=True)

    roles_to_upload = (
        ("leader", "follower") if args.case == "A" else ("leader",)
    )
    prepared: dict[str, dict] = {}
    uploads: dict[str, dict] = {}
    write_actions: list[dict] = []
    try:
        # Complete every required build and explicit guard before the first
        # device write. Case B only changes the leader environment.
        for role in roles_to_upload:
            target = _target(args.case, role)
            env = target["env"]
            role_dir = upload_raw / role
            role_dir.mkdir()
            log_path = role_dir / "upload.log"
            build_command = ["bash", "scripts/agent/pio-build.sh", env]
            if command_runner(build_command, log_path, append=False) != 0:
                raise F2FlashError(f"{role} canonical build failed")
            build_log = log_path.read_text(
                encoding="utf-8", errors="replace"
            )
            provenance = re.search(
                rf"\[k1-build-provenance\]\s+env={re.escape(env)}\s+"
                r"git=([0-9a-f]+)\s+epoch=(\d+)",
                build_log,
            )
            if (
                provenance is None
                or not f2_capture._valid_git_prefix(
                    firmware_sha, provenance.group(1)
                )
            ):
                raise F2FlashError(
                    f"{role} build log lacks matching source provenance"
                )

            build_dir = repo_root / ".pio" / "build" / env
            built_bin = build_dir / "firmware.bin"
            built_elf = build_dir / "firmware.elf"
            if not built_bin.is_file() or not built_elf.is_file():
                raise F2FlashError(f"{role} build artefacts are missing")
            preserved_bin = role_dir / "firmware.bin"
            preserved_elf = role_dir / "firmware.elf"
            shutil.copy2(built_bin, preserved_bin)
            shutil.copy2(built_elf, preserved_elf)
            bin_sha = _sha256(preserved_bin)
            elf_sha = _sha256(preserved_elf)
            app_elf_sha = _app_elf_sha256(preserved_bin)
            if app_elf_sha != elf_sha:
                raise F2FlashError(
                    f"{role} BIN app identity does not match ELF hash"
                )

            guard_command = [
                "python3",
                "scripts/platformio/k1_upload_guard.py",
                "--env",
                env,
                "--upload-port",
                ports[role],
            ]
            if command_runner(guard_command, log_path, append=True) != 0:
                raise F2FlashError(f"{role} upload guard rejected target")
            prepared[role] = {
                "target": target,
                "env": env,
                "log_path": log_path,
                "build_command": build_command,
                "guard_command": guard_command,
                "built_bin": built_bin,
                "built_elf": built_elf,
                "preserved_bin": preserved_bin,
                "preserved_elf": preserved_elf,
                "bin_sha256": bin_sha,
                "elf_sha256": elf_sha,
                "app_elf_sha256": app_elf_sha,
            }

        for role in roles_to_upload:
            item = prepared[role]
            target = item["target"]
            env = item["env"]
            log_path = item["log_path"]
            upload_command = [
                "pio",
                "run",
                "-e",
                env,
                "-t",
                "upload",
                "--upload-port",
                ports[role],
            ]
            action = {
                "role": role,
                "command": upload_command,
                "attempted": True,
                "outcome": "running",
                "exit_code": None,
            }
            write_actions.append(action)
            try:
                upload_exit = command_runner(
                    upload_command, log_path, append=True
                )
            except Exception:
                action["outcome"] = "error"
                raise
            action["exit_code"] = upload_exit
            action["outcome"] = (
                "success" if upload_exit == 0 else "failed"
            )
            if upload_exit != 0:
                raise F2FlashError(f"{role} upload failed")
            if (
                _sha256(item["built_bin"]) != item["bin_sha256"]
                or _sha256(item["built_elf"]) != item["elf_sha256"]
            ):
                raise F2FlashError(
                    f"{role} build artefacts changed during guarded upload"
                )
            log_text = log_path.read_text(
                encoding="utf-8", errors="replace"
            )
            if "verified as" not in log_text:
                raise F2FlashError(
                    f"{role} upload log lacks guard verification"
                )
            readback = identity_reader(
                target["usb_serial"],
                {
                    **target,
                    "firmware_source_sha": firmware_sha,
                    "app_elf_sha256": item["app_elf_sha256"],
                },
                args.readback_timeout_s,
            )
            uploads[role] = {
                "action": "upload",
                "source_case": args.case,
                "env": env,
                "chip_id": target["chip_id"],
                "usb_serial": target["usb_serial"],
                "port": ports[role],
                "preflash_identity": preflash[role],
                "guard_verified": True,
                "upload_exit_code": upload_exit,
                "command": upload_command,
                "build_command": item["build_command"],
                "guard_command": item["guard_command"],
                "bin_path": f2_capture._repo_relative(
                    item["preserved_bin"], repo_root
                ),
                "bin_sha256": item["bin_sha256"],
                "elf_path": f2_capture._repo_relative(
                    item["preserved_elf"], repo_root
                ),
                "elf_sha256": item["elf_sha256"],
                "app_elf_sha256": item["app_elf_sha256"],
                "postflash_readback": readback,
                "log": f2_capture._evidence_record(log_path, repo_root),
            }

        if args.case == "B":
            case_a_flash_record = prior[0]["flash_manifest"]
            case_a_flash_path = (
                repo_root / str(case_a_flash_record["path"])
            )
            case_a_flash = f2_capture._read_manifest(case_a_flash_path)
            follower = copy.deepcopy(case_a_flash["uploads"]["follower"])
            follower["action"] = "reuse"
            follower["source_case"] = "A"
            follower["reused_flash_manifest"] = case_a_flash_record
            follower["reuse_preflight_identity"] = preflash["follower"]
            uploads["follower"] = follower

        manifest = {
            "schema_version": 1,
            "status": gate_eval.PASS,
            "run_id": args.run_id,
            "case": args.case,
            "upload_controller_sha": host_sha,
            "firmware_source_sha": firmware_sha,
            "uploads": uploads,
        }
        f2_capture._atomic_manifest(upload_manifest, manifest)
        return manifest
    except (F2FlashError, OSError) as error:
        blocked = {
            "schema_version": 1,
            "status": gate_eval.BLOCKED,
            "run_id": args.run_id,
            "case": args.case,
            "upload_controller_sha": host_sha,
            "firmware_source_sha": firmware_sha,
            "prepared_roles": sorted(prepared),
            "write_actions": write_actions,
            "completed_uploads": uploads,
            "error": str(error),
        }
        f2_capture._atomic_manifest(upload_manifest, blocked)
        raise


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Guard-build, upload and read back one F2 A/B device pair."
    )
    parser.add_argument("--case", choices=("A", "B"), required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--firmware-sha", required=True)
    parser.add_argument("--attestation", type=Path, required=True)
    parser.add_argument("--leader-port", required=True)
    parser.add_argument("--follower-port", required=True)
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
        OSError,
        ValueError,
    ) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
