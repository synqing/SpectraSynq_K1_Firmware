"""PlatformIO upload guard for K1 GPIO pin-map targets.

The bench K1 units expose the same ESP32-S3 USB product name, so the build
environment must be matched to the physical USB serial before any upload.

Identity is single-sourced in `k1_device_identities.json` (this directory).
**Identity-by-USB-serial GOVERNS** every decision; the `advisory_port` is operator
convenience only and never grants a pass. The guard fails CLOSED for protected
(mapped) K1 envs: a wrong serial, a KNOWN_QUARANTINED unit, or an unknown
ESP32-S3 at the requested port are all rejected.

N4a (dev identity hygiene): the manifest is the source of truth; this module
consumes it. No SKU/manufacturing/NVS/efuse logic lives here.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

def _default_manifest_path() -> Path:
    """Locate k1_device_identities.json next to this script.

    PlatformIO/SCons exec this file as a build PRE-SCRIPT *without* setting
    `__file__` (a NameError otherwise crashes every `pio run`). In that context
    the build cwd is the project root, so fall back to the known in-repo path.
    Normal import (tests / CLI) has `__file__` and uses the script's own dir.
    """
    try:
        base = Path(__file__).resolve().parent
    except NameError:
        base = Path.cwd() / "scripts" / "platformio"
    return base / "k1_device_identities.json"


_MANIFEST_PATH = _default_manifest_path()


@dataclass(frozen=True)
class K1Target:
    envs: tuple[str, ...]
    role: str
    upload_port: str  # advisory only — identity-by-serial governs
    usb_serial: str
    chip_id: str
    pinmap: str


def _norm_serial(value: object) -> str:
    return str(value or "").strip().upper()


def load_identities(
    manifest_path: str | Path | None = None,
) -> tuple[tuple[K1Target, ...], dict[str, dict], dict[str, str]]:
    """Load (authorized targets, quarantined-by-serial, blocked envs) from the manifest."""
    path = Path(manifest_path) if manifest_path is not None else _MANIFEST_PATH
    if not path.is_file():
        raise RuntimeError(
            f"k1_upload_guard: identity manifest not found at {path}. "
            "It is the single source of device identity and must be present."
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    targets = tuple(
        K1Target(
            envs=tuple(entry["envs"]),
            role=entry["role"],
            upload_port=entry["advisory_port"],
            usb_serial=entry["usb_serial"],
            chip_id=entry["chip_id"],
            pinmap=entry["pinmap"],
        )
        for entry in data.get("authorized", [])
    )
    quarantined = {_norm_serial(q["usb_serial"]): q for q in data.get("quarantined", [])}
    blocked = dict(data.get("blocked_envs", {}))
    return targets, quarantined, blocked


# Module-level identity, loaded once from the manifest (the single source).
K1_TARGETS, QUARANTINED, BLOCKED_UPLOAD_ENVS = load_identities()


def _normalise_port(port: str) -> str:
    value = str(port or "").strip()
    if value.startswith("/dev/cu."):
        return "/dev/tty." + value[len("/dev/cu.") :]
    return value


def _expected_target_for_env(pioenv: str, targets: Iterable[K1Target]) -> K1Target | None:
    for target in targets:
        if pioenv in target.envs:
            return target
    return None


def expected_target_for_env(pioenv: str) -> K1Target | None:
    return _expected_target_for_env(pioenv, K1_TARGETS)


def list_serial_ports() -> list[dict[str, str | None]]:
    try:
        from serial.tools import list_ports
    except Exception as exc:  # pragma: no cover - depends on PlatformIO runtime
        raise RuntimeError(f"pyserial list_ports unavailable: {exc}") from exc

    ports: list[dict[str, str | None]] = []
    for port in list_ports.comports():
        device = port.device or ""
        if "usbmodem" not in device:
            continue
        ports.append(
            {
                "device": device,
                "normalised_device": _normalise_port(device),
                "serial_number": port.serial_number,
                "location": port.location,
                "hwid": port.hwid,
            }
        )
    return ports


def find_port(upload_port: str, ports: Iterable[dict[str, str | None]]) -> dict[str, str | None] | None:
    expected = _normalise_port(upload_port)
    for port in ports:
        if _normalise_port(str(port.get("device") or "")) == expected:
            return port
    return None


def validate_upload_target(
    pioenv: str,
    upload_port: str,
    ports: Iterable[dict[str, str | None]] | None = None,
    *,
    targets: Iterable[K1Target] | None = None,
    quarantined: dict[str, dict] | None = None,
    blocked: dict[str, str] | None = None,
) -> tuple[bool, str]:
    """Validate that the device at `upload_port` is authorized for `pioenv`.

    Fails CLOSED for protected (mapped) K1 envs. `upload_port` only LOCATES the
    device to inspect; the USB serial is the authority. Optional `targets`/
    `quarantined`/`blocked` injection exists for tests (Gate-Falpha); production
    uses the module-level manifest data.
    """
    targets = K1_TARGETS if targets is None else tuple(targets)
    quarantined = QUARANTINED if quarantined is None else quarantined
    blocked = BLOCKED_UPLOAD_ENVS if blocked is None else blocked

    if pioenv in blocked:
        return False, f"{pioenv}: upload blocked: {blocked[pioenv]}"

    target = _expected_target_for_env(pioenv, targets)
    if target is None:
        return True, f"{pioenv}: no K1 upload mapping enforced"

    port_list = list(ports) if ports is not None else list_serial_ports()
    port = find_port(upload_port, port_list)
    if port is None:
        return False, f"{pioenv}: {upload_port} is not currently enumerated"

    actual = _norm_serial(port.get("serial_number"))
    expected = _norm_serial(target.usb_serial)

    if actual == expected:
        return (
            True,
            (
                f"{pioenv}: {upload_port} verified as {target.role} "
                f"({target.usb_serial}, chip {target.chip_id}, {target.pinmap})"
            ),
        )

    q = quarantined.get(actual)
    if q is not None:
        return (
            False,
            (
                f"{pioenv}: {upload_port} is {q.get('usb_serial', actual)} = "
                f"{q.get('state', 'KNOWN_QUARANTINED')} ({q.get('reason', 'quarantined')}); "
                f"not authorized for {target.role} ({pioenv})"
            ),
        )

    return (
        False,
        (
            f"{pioenv}: {upload_port} has USB serial {actual or '<missing>'}; "
            f"expected {target.usb_serial} for {target.role} ({target.pinmap}); "
            f"configured default is {target.upload_port}"
        ),
    )


def format_identities(
    targets: Iterable[K1Target] | None = None,
    quarantined: dict[str, dict] | None = None,
    blocked: dict[str, str] | None = None,
) -> str:
    """Human-readable dump of the known identity manifest. NO device I/O."""
    targets = K1_TARGETS if targets is None else tuple(targets)
    quarantined = QUARANTINED if quarantined is None else quarantined
    blocked = BLOCKED_UPLOAD_ENVS if blocked is None else blocked

    lines = ["K1 device identities (source: k1_device_identities.json)", "", "AUTHORIZED:"]
    for t in targets:
        lines.append(
            f"  {t.role}: serial {t.usb_serial} (chip {t.chip_id}), "
            f"advisory_port {t.upload_port}, {t.pinmap}, {len(t.envs)} env(s)"
        )
    lines.append("")
    lines.append("QUARANTINED (refused on every K1 env):")
    for q in quarantined.values():
        lines.append(
            f"  {q.get('usb_serial')} [{q.get('state', 'KNOWN_QUARANTINED')}] "
            f"role={q.get('role', 'unassigned')} — {q.get('reason', '')}"
        )
    lines.append("")
    lines.append("BLOCKED ENVS (build-only):")
    for env, reason in blocked.items():
        lines.append(f"  {env}: {reason}")
    return "\n".join(lines)


def _guard_upload_action(source, target, env) -> None:  # pragma: no cover - exercised by PlatformIO
    pioenv = env.subst("$PIOENV")
    upload_port = env.subst("$UPLOAD_PORT")
    ok, message = validate_upload_target(pioenv, upload_port)
    prefix = "[k1-upload-guard] "
    if not ok:
        raise SystemExit(prefix + message)
    print(prefix + message)


def _install_platformio_hook() -> None:
    try:
        Import("env")  # type: ignore[name-defined]  # noqa: F821
    except NameError:
        return
    env.AddPreAction("upload", _guard_upload_action)  # type: ignore[name-defined]  # noqa: F821


def _main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Validate K1 PlatformIO upload target mapping.")
    parser.add_argument("--env", dest="pioenv")
    parser.add_argument("--upload-port")
    parser.add_argument("--ports-json", type=Path)
    parser.add_argument(
        "--list-identities",
        action="store_true",
        help="Print the known identity manifest and exit (no device I/O).",
    )
    args = parser.parse_args(argv)

    if args.list_identities:
        print(format_identities())
        return 0

    if not args.pioenv or not args.upload_port:
        parser.error("--env and --upload-port are required unless --list-identities is given")

    ports = None
    if args.ports_json is not None:
        ports = json.loads(args.ports_json.read_text())

    ok, message = validate_upload_target(args.pioenv, args.upload_port, ports)
    print(message)
    return 0 if ok else 2


_install_platformio_hook()


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
