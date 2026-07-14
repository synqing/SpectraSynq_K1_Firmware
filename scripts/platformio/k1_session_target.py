#!/usr/bin/env python3
"""Pin and verify the one physical K1 target authorised for this session."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STATE = ROOT / ".devin" / "k1-session-target.json"
MANIFEST = Path(__file__).resolve().with_name("k1_device_identities.json")
SOURCE_ROOTS = (
    Path("platformio.ini"),
    Path("SPECTRASYNQ_K1_FIRMWARE"),
    Path("libraries"),
    Path("scripts/platformio"),
)
SOURCE_IGNORES = {".DS_Store", "__pycache__"}
GENERATED_SOURCE_SUFFIXES = (".ino.cpp",)


def normalise_port(value: str) -> str:
    value = str(value or "").strip()
    return "/dev/tty." + value[8:] if value.startswith("/dev/cu.") else value


def normalise_id(value: object) -> str:
    return "".join(ch for ch in str(value or "").upper() if ch.isalnum())


def current_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def current_source_fingerprint(root: Path = ROOT) -> str:
    """Hash the bytes that can affect a PlatformIO K1 build.

    This deliberately fingerprints the working tree, not only tracked git
    state. A dirty edit or untracked source file therefore invalidates a pin
    rather than silently sharing the same embedded HEAD provenance.
    """
    digest = hashlib.sha256()
    files: list[Path] = []
    for relative in SOURCE_ROOTS:
        candidate = root / relative
        if candidate.is_file():
            files.append(candidate)
        elif candidate.is_dir():
            files.extend(
                path
                for path in candidate.rglob("*")
                if path.is_file()
                and not any(part in SOURCE_IGNORES for part in path.relative_to(root).parts)
                and path.suffix != ".pyc"
                and not path.name.endswith(GENERATED_SOURCE_SUFFIXES)
            )
    for path in sorted(files, key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
    return digest.hexdigest()


def load_manifest(path: Path = MANIFEST) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def target_for_env(env: str, manifest: dict | None = None) -> dict | None:
    for target in (manifest or load_manifest()).get("authorized", []):
        if env in target.get("envs", []):
            return target
    return None


def list_serial_ports() -> list[dict[str, object]]:
    from serial.tools import list_ports

    return [
        {"device": port.device, "serial_number": port.serial_number}
        for port in list_ports.comports()
        if "usbmodem" in str(port.device or "")
    ]


def find_live_port(port: str, ports: list[dict[str, object]]) -> dict | None:
    wanted = normalise_port(port)
    return next(
        (item for item in ports if normalise_port(str(item.get("device") or "")) == wanted),
        None,
    )


def create_pin(
    *,
    chip_id: str,
    upload_port: str,
    capture_port: str,
    envs: list[str],
    purpose: str,
    state_path: Path = DEFAULT_STATE,
    ports: list[dict[str, object]] | None = None,
    now: int | None = None,
    ttl_seconds: int = 14400,
    head: str | None = None,
    source_fingerprint: str | None = None,
) -> dict:
    if not envs:
        raise RuntimeError("at least one --env is required")
    manifest = load_manifest()
    targets = [target_for_env(env, manifest) for env in envs]
    if any(target is None for target in targets):
        unknown = [env for env, target in zip(envs, targets) if target is None]
        raise RuntimeError(f"unmapped K1 environment(s): {', '.join(unknown)}")
    expected = targets[0]
    assert expected is not None
    if any(normalise_id(target["chip_id"]) != normalise_id(expected["chip_id"]) for target in targets if target):
        raise RuntimeError("all pinned environments must resolve to the same physical K1")
    if normalise_id(chip_id) != normalise_id(expected["chip_id"]):
        raise RuntimeError(f"chip {chip_id} is not authorised for {envs[0]} (expected {expected['chip_id']})")

    live_ports = list_serial_ports() if ports is None else ports
    upload = find_live_port(upload_port, live_ports)
    capture = find_live_port(capture_port, live_ports)
    if upload is None or capture is None:
        raise RuntimeError("both explicit upload and capture ports must be currently enumerated")
    expected_serial = normalise_id(expected["usb_serial"])
    for label, item in (("upload", upload), ("capture", capture)):
        actual = normalise_id(item.get("serial_number"))
        if actual != expected_serial:
            raise RuntimeError(f"{label} port USB identity mismatch: expected {expected_serial}, observed {actual or 'NONE'}")

    created = int(time.time() if now is None else now)
    pin = {
        "schema_version": 1,
        "chip_id": expected["chip_id"],
        "usb_serial": expected["usb_serial"],
        "role": expected["role"],
        "upload_port": upload_port,
        "capture_port": capture_port,
        "allowed_envs": sorted(set(envs)),
        "purpose": purpose,
        "git_head": head or current_head(),
        "source_fingerprint": source_fingerprint or current_source_fingerprint(),
        "created_epoch": created,
        "expires_epoch": created + ttl_seconds,
    }
    state_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = state_path.with_suffix(".tmp")
    temporary.write_text(json.dumps(pin, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(state_path)
    return pin


def validate_session_pin(
    env: str,
    port: str,
    *,
    state_path: Path = DEFAULT_STATE,
    ports: list[dict[str, object]] | None = None,
    now: int | None = None,
    head: str | None = None,
    source_fingerprint: str | None = None,
) -> tuple[bool, str]:
    if not state_path.is_file():
        return False, f"session target pin missing: {state_path}"
    try:
        pin = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return False, f"session target pin unreadable: {exc}"
    current_time = int(time.time() if now is None else now)
    if current_time >= int(pin.get("expires_epoch", 0)):
        return False, "session target pin expired; re-pin against live hardware"
    live_head = head or current_head()
    if pin.get("git_head") != live_head:
        return False, f"session target pin HEAD drift: pinned {pin.get('git_head')}, live {live_head}"
    live_source = source_fingerprint or current_source_fingerprint()
    if pin.get("source_fingerprint") != live_source:
        return False, "session target pin source drift: build-relevant working-tree bytes changed"
    if env not in pin.get("allowed_envs", []):
        return False, f"environment {env} is not in the session target pin"
    if normalise_port(port) not in {
        normalise_port(pin.get("upload_port", "")),
        normalise_port(pin.get("capture_port", "")),
    }:
        return False, f"port {port} is not in the session target pin"
    target = target_for_env(env)
    if target is None or normalise_id(target["chip_id"]) != normalise_id(pin.get("chip_id")):
        return False, "session pin no longer agrees with the identity manifest"
    live = find_live_port(port, list_serial_ports() if ports is None else ports)
    if live is None:
        return False, f"pinned port {port} is not currently enumerated"
    actual = normalise_id(live.get("serial_number"))
    if actual != normalise_id(pin.get("usb_serial")):
        return False, f"pinned port USB identity mismatch: expected {pin.get('usb_serial')}, observed {actual or 'NONE'}"
    return True, (
        f"session target verified: {pin['role']} chip {pin['chip_id']} env {env} "
        f"HEAD {live_head[:8]} source {live_source[:12]}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    pin = sub.add_parser("pin")
    pin.add_argument("--chip-id", required=True)
    pin.add_argument("--upload-port", required=True)
    pin.add_argument("--capture-port", required=True)
    pin.add_argument("--env", action="append", required=True)
    pin.add_argument("--purpose", required=True)
    pin.add_argument("--ttl-seconds", type=int, default=14400)
    verify = sub.add_parser("verify")
    verify.add_argument("--env", required=True)
    verify.add_argument("--port", required=True)
    sub.add_parser("show")
    args = parser.parse_args()
    if args.command == "pin":
        if not 300 <= args.ttl_seconds <= 14400:
            parser.error("--ttl-seconds must be between 300 and 14400")
        try:
            result = create_pin(chip_id=args.chip_id, upload_port=args.upload_port, capture_port=args.capture_port,
                                envs=args.env, purpose=args.purpose, ttl_seconds=args.ttl_seconds)
        except RuntimeError as exc:
            print(f"session target pin FAIL: {exc}")
            return 2
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    if args.command == "show":
        if not DEFAULT_STATE.is_file():
            print(f"session target pin missing: {DEFAULT_STATE}")
            return 2
        print(DEFAULT_STATE.read_text(encoding="utf-8"), end="")
        return 0
    ok, message = validate_session_pin(args.env, args.port)
    print(message)
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
