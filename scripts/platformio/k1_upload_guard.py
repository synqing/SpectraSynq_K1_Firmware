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
        # Native ESP32-S3 CDC enumerates as usbmodem*; CH9102/CH340 UART bridges
        # (custom dual-206 board) enumerate as wchusbserial*.
        if "usbmodem" not in device and "wchusbserial" not in device:
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
        if pioenv.startswith("k1_sync_probe_"):
            return False, f"{pioenv}: unmapped sync probe environment; upload blocked"
        if pioenv.startswith("k1_"):
            return False, f"{pioenv}: unmapped K1 environment; upload blocked"
        return True, f"{pioenv}: no K1 upload mapping enforced"

    candidates = [t for t in targets if pioenv in t.envs]

    port_list = list(ports) if ports is not None else list_serial_ports()
    port = find_port(upload_port, port_list)
    if port is None:
        return False, f"{pioenv}: {upload_port} is not currently enumerated"

    device = str(port.get("device") or upload_port)
    if pioenv.startswith("k1_p4_wifi6"):
        if "usbmodem" in device:
            return (
                False,
                (
                    f"{pioenv}: {upload_port} is native USB CDC (usbmodem) — "
                    "refuses Tab5 and S3. P4-WIFI6 lab upload is wchusbserial only "
                    "(ADR-0007)."
                ),
            )
        if "wchusbserial" not in device:
            return (
                False,
                (
                    f"{pioenv}: {upload_port} is not a WCH UART bridge; "
                    "P4-WIFI6 upload is wchusbserial only (ADR-0007)."
                ),
            )
    elif "wchusbserial" in device:
        return (
            False,
            (
                f"{pioenv}: {upload_port} is a P4 WCH UART bridge; "
                "S3 K1 envs refuse wchusbserial (ADR-0007)."
            ),
        )

    actual = _norm_serial(port.get("serial_number"))
    matched = next(
        (t for t in candidates if actual == _norm_serial(t.usb_serial)),
        None,
    )

    if matched is not None:
        return (
            True,
            (
                f"{pioenv}: {upload_port} verified as {matched.role} "
                f"({matched.usb_serial}, chip {matched.chip_id}, {matched.pinmap})"
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

    expected_serials = ", ".join(sorted({_norm_serial(t.usb_serial) for t in candidates}))
    return (
        False,
        (
            f"{pioenv}: {upload_port} has USB serial {actual or '<missing>'}; "
            f"expected one of [{expected_serials}] for {pioenv}; "
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


# ── Pinned saved-app restore (2026-10-14) ─────────────────────────────────────
# One pinned profile puts a retained app image back into the slot the installed
# bootloader already selects. It is NOT a general "flash this file" path: every
# declared value must equal the pin, the only write is one app region, and the
# admission is the USB serial plus a live ROM MAC read, so it still works when
# the application on the chip is broken and never answers `:build`.
# Contract: _scratch/b489-ws2816-reference-20261013/resume-20261014/recovery-contract.md

SAVED_APP_PROFILES: dict[str, dict] = {
    "b489-original-app0-20261013": {
        "image": "_scratch/b489-ws2816-reference-20261013/original-app-app0.bin",
        "sha256": "3d3b929e71b0d1ddc471f64f263a30c85aa38fc5a6c261dcef6087f376f9c226",
        "size": 6553600,
        "elf_sha256": "7edb88488c521da72d1d6bbeef3b1bfa24b6cacb134323560ebbfe6d87aaf104",
        "slot": 0,
        "offset": 0x10000,
        "expect_git": "eff9bf47",
        "expect_env": "k1_bench_im69d_led150",
        "expect_chip": "B489A500",
        "expect_usb_serial": "B4:3A:45:A5:89:B4",
        # Port allow-list only: proves the USB serial may receive this env. It is
        # not the identity of the bytes being restored.
        "guard_env": "k1_b489_ws2816_reference_capture",
        "otadata_offset": 0xE000,
        "otadata_size": 8192,
        "otadata_sha256": "f94c5d786a7a8fab06ac5d10e33bf37711a6697636dc037559ea19cc410a17f0",
        "partition_offset": 0x8000,
        "partition_size": 3072,
        "partition_sha256": "bd0f7954aca2ef7d925ee21aaa1f3dc8822d1d6ce5cbbd26a135e5886bfff6ce",
        "bootloader_size": 20208,
        "bootloader_sha256": "12c9a10fef2d95a3f6d74dc6089fa8fedc51a77a487be834c9207b8c687b8761",
        # A forward PlatformIO upload of these envs rewrites bootloader, partition
        # table and otadata (boot_app0.bin). It may proceed only while those
        # segments equal the pins, or this restore would refuse afterwards.
        "forward_envs": ("k1_b489_ws2816_reference_capture",),
    },
}

_RESTORE_PREFIX = "[k1-restore] "
_APP_DESC_OFFSET = 32
_APP_DESC_MAGIC = 0xABCD5432
_APP_DESC_ELF_SHA_OFFSET = 144
_OTA_ENTRY_SIZE = 32
_OTA_STATE_INVALID = 3
_OTA_STATE_ABORTED = 4
_FORBIDDEN_ESPTOOL_ARGS = ("--erase-all", "-e", "erase_flash", "erase_region", "--encrypt")

# Exit codes for the restore path. Every refusal before the writer is 2, so a
# caller can tell "chip untouched" apart from "write attempted".
RESTORE_OK = 0
RESTORE_WRITE_FAILED = 1  # writer exited non-zero: app0 may be partial; rerun the same pin
RESTORE_REFUSED = 2  # refused before any write; the chip was not written
RESTORE_READBACK_MISMATCH = 3  # bytes or app identity contradict the pin after the write
RESTORE_APP_SILENT = 4  # bytes verified, but the application never answered `:build`


class RestoreRefused(RuntimeError):
    """A check failed before the writer. The chip has not been written."""


def _sha256(data: bytes) -> str:
    import hashlib

    return hashlib.sha256(data).hexdigest()


def _repo_root() -> Path:
    return _MANIFEST_PATH.resolve().parent.parent.parent


def esp_rom_crc32_le(crc: int, data: bytes) -> int:
    """ESP ROM `esp_rom_crc32_le`: inverts on entry and exit, poly 0xEDB88320."""
    crc = ~crc & 0xFFFFFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ (0xEDB88320 if crc & 1 else 0)
    return ~crc & 0xFFFFFFFF


def select_ota_slot(otadata: bytes, app_count: int = 2) -> int:
    """Reproduce the bootloader's otadata choice. Refuse anything ambiguous.

    IDF `bootloader_common_ota_select_crc(s) = esp_rom_crc32_le(UINT32_MAX,
    &s->ota_seq, 4)`; an entry is valid when `ota_seq != UINT32_MAX` and the CRC
    matches; with two valid entries the higher sequence wins.
    """
    import struct

    if len(otadata) != 8192:
        raise RestoreRefused(f"otadata is {len(otadata)} bytes, expected 8192")
    entries = []
    for index, base in enumerate((0, 4096)):
        seq, state, crc = struct.unpack_from("<I20xII", otadata, base)
        valid = seq != 0xFFFFFFFF and crc == esp_rom_crc32_le(0xFFFFFFFF, struct.pack("<I", seq))
        entries.append({"index": index, "seq": seq, "state": state, "valid": valid})
    valid = [e for e in entries if e["valid"]]
    if not valid:
        raise RestoreRefused("otadata: no valid entry (erased or corrupt)")
    if len(valid) == 2 and valid[0]["seq"] == valid[1]["seq"]:
        raise RestoreRefused("otadata: both entries valid with equal sequence (ambiguous)")
    winner = max(valid, key=lambda e: e["seq"])
    if winner["state"] in (_OTA_STATE_INVALID, _OTA_STATE_ABORTED):
        raise RestoreRefused(f"otadata: winning entry state {winner['state']:#x} is not bootable")
    return (winner["seq"] - 1) % app_count


def find_app_partition(table: bytes, slot: int) -> tuple[int, int]:
    """Return (offset, size) of app ota_<slot> from a raw partition table."""
    import struct

    for base in range(0, len(table) - _OTA_ENTRY_SIZE + 1, _OTA_ENTRY_SIZE):
        magic, ptype, subtype, offset, size = struct.unpack_from("<HBBII", table, base)
        if magic != 0x50AA:
            break
        if ptype == 0 and subtype == 0x10 + slot:
            return offset, size
    raise RestoreRefused(f"partition table has no app ota_{slot} entry")


def inspect_app_image(data: bytes) -> dict[str, object]:
    """Read the ESP image magic and `esp_app_desc_t.app_elf_sha256` from an app image."""
    import struct

    info: dict[str, object] = {"size": len(data), "sha256": _sha256(data)}
    info["magic"] = data[0] if data else None
    if len(data) < _APP_DESC_OFFSET + _APP_DESC_ELF_SHA_OFFSET + 32:
        info["desc_magic"] = None
        info["elf_sha256"] = None
        return info
    (desc_magic,) = struct.unpack_from("<I", data, _APP_DESC_OFFSET)
    info["desc_magic"] = desc_magic
    start = _APP_DESC_OFFSET + _APP_DESC_ELF_SHA_OFFSET
    info["elf_sha256"] = data[start : start + 32].hex() if desc_magic == _APP_DESC_MAGIC else None
    return info


def check_image_against_profile(data: bytes, profile: dict) -> dict[str, object]:
    info = inspect_app_image(data)
    if info["size"] != profile["size"]:
        raise RestoreRefused(f"image size {info['size']} != pinned {profile['size']}")
    if info["sha256"] != profile["sha256"]:
        raise RestoreRefused(f"image sha256 {info['sha256']} != pinned {profile['sha256']}")
    if info["magic"] != 0xE9:
        raise RestoreRefused(f"image magic {info['magic']!r} is not 0xE9")
    if info["elf_sha256"] != profile["elf_sha256"]:
        raise RestoreRefused(f"image app ELF sha256 {info['elf_sha256']} != pinned {profile['elf_sha256']}")
    return info


def check_declared_against_profile(declared: dict, profile: dict, root: Path) -> None:
    """Every declared value must equal the pin. Nothing here is a default."""
    image = Path(str(declared.get("image") or ""))
    image = image if image.is_absolute() else root / image
    if image.resolve() != (root / profile["image"]).resolve():
        raise RestoreRefused(f"image {declared.get('image')} is not the pinned file {profile['image']}")
    checks = (
        ("sha256", str(declared.get("sha256") or "").lower(), profile["sha256"]),
        ("size", declared.get("size"), profile["size"]),
        ("slot", declared.get("slot"), profile["slot"]),
        ("offset", declared.get("offset"), profile["offset"]),
        ("expect-git", declared.get("expect_git"), profile["expect_git"]),
        ("expect-env", declared.get("expect_env"), profile["expect_env"]),
        ("expect-chip", _norm_serial(declared.get("expect_chip")), profile["expect_chip"]),
        ("expect-usb-serial", _norm_serial(declared.get("expect_usb_serial")), profile["expect_usb_serial"]),
    )
    for name, got, want in checks:
        if got != want:
            raise RestoreRefused(f"--{name} {got!r} does not equal the pin {want!r}")


def plan_saved_app_restore(
    profile: dict,
    *,
    image_bytes: bytes,
    otadata: bytes,
    partition: bytes,
) -> dict[str, object]:
    """Pure planner. Raises RestoreRefused; returns the one-write plan otherwise."""
    image = check_image_against_profile(image_bytes, profile)
    slot = select_ota_slot(otadata)
    if slot != profile["slot"]:
        raise RestoreRefused(f"bootloader selects slot {slot}, pin is slot {profile['slot']}")
    if len(partition) != profile["partition_size"]:
        raise RestoreRefused(f"partition prefix is {len(partition)} bytes, expected {profile['partition_size']}")
    offset, size = find_app_partition(partition, slot)
    if offset != profile["offset"] or size != profile["size"]:
        raise RestoreRefused(f"app ota_{slot} is {offset:#x}+{size}, pin is {profile['offset']:#x}+{profile['size']}")
    if _sha256(otadata) != profile["otadata_sha256"]:
        raise RestoreRefused(f"otadata sha256 {_sha256(otadata)} != pinned {profile['otadata_sha256']}")
    if _sha256(partition) != profile["partition_sha256"]:
        raise RestoreRefused(f"partition sha256 {_sha256(partition)} != pinned {profile['partition_sha256']}")
    return {
        "writes": [{"offset": profile["offset"], "length": profile["size"], "sha256": image["sha256"]}],
        "erase_all": False,
        "slot": slot,
        "elf_sha256": image["elf_sha256"],
    }


def check_forward_segments(profile: dict, extra_images: dict[int, str]) -> list[str]:
    """Bind the extra segments a forward upload actually sends to the pins.

    `extra_images` is {offset: file} exactly as the upload command consumes it
    (PlatformIO appends every FLASH_EXTRA_IMAGES pair to esptool write-flash).
    Refuses a missing, unexpected or changed segment; returns one line per file.
    """
    pins = {
        0x0: ("bootloader", profile["bootloader_sha256"]),
        profile["partition_offset"]: ("partition table", profile["partition_sha256"]),
        profile["otadata_offset"]: ("otadata (boot_app0)", profile["otadata_sha256"]),
    }
    extra = sorted(set(extra_images) - set(pins))
    if extra:
        raise RestoreRefused(f"upload sends unpinned extra segment(s) at {[hex(o) for o in extra]}")
    lines = []
    for offset, (name, want) in sorted(pins.items()):
        path = extra_images.get(offset)
        if path is None:
            raise RestoreRefused(f"upload sends no {name} at {offset:#x}; cannot bind it to the pin")
        try:
            got = _sha256(Path(path).read_bytes())
        except OSError as exc:
            raise RestoreRefused(f"{name} {path} unreadable: {exc}") from exc
        if got != want:
            raise RestoreRefused(f"{name} {path} sha256 {got} != pinned {want}")
        lines.append(f"{offset:#x} {name}: {path} sha256 {got} = pin")
    return lines


def forward_segments_from_env(env) -> dict[int, str]:
    """The (offset, file) pairs PlatformIO will append to this upload command."""
    return {int(str(env.subst(off)), 0): str(env.subst(path)) for off, path in env.get("FLASH_EXTRA_IMAGES", [])}


# ── device-facing steps (runner injected so tests never touch a port) ─────────
# runner(argv, timeout) -> (returncode, stdout, stderr). It may raise
# FileNotFoundError (tool missing) or subprocess.TimeoutExpired.


def _real_runner(argv: list[str], timeout: float) -> tuple[int, str, str]:  # pragma: no cover - device I/O
    import subprocess

    proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    return proc.returncode, proc.stdout, proc.stderr


def _run(runner, argv: list[str], timeout: float, what: str) -> tuple[int, str, str]:
    import subprocess

    try:
        return runner(argv, timeout)
    except FileNotFoundError as exc:
        raise RestoreRefused(f"{what}: tool not found ({exc})") from exc
    except subprocess.TimeoutExpired as exc:
        raise RestoreRefused(f"{what}: timed out after {timeout}s") from exc


def check_port_free(device: str, runner) -> None:
    """Refuse an owned port. lsof exits 1 with no output when nothing has the file
    open; that is "free", not an error. A hit, any stderr, or a missing lsof refuses."""
    nodes = {device, _normalise_port(device)}
    if device.startswith("/dev/tty."):
        nodes.add("/dev/cu." + device[len("/dev/tty.") :])
    for node in sorted(nodes):
        rc, out, err = _run(runner, ["lsof", node], 10, f"lsof {node}")
        if rc == 0 and out.strip():
            raise RestoreRefused(f"port {node} is open by another process:\n{out.strip()}")
        if rc == 1 and not out.strip() and not err.strip():
            continue
        raise RestoreRefused(f"lsof {node} could not establish ownership (rc={rc}): {err.strip() or out.strip()}")


def locate_port_by_serial(usb_serial: str, ports: list[dict], requested: str | None) -> str:
    want = _norm_serial(usb_serial)
    hits = [p for p in ports if _norm_serial(p.get("serial_number")) == want]
    if requested:
        port = find_port(requested, ports)
        if port is not None and _norm_serial(port.get("serial_number")) != want:
            raise RestoreRefused(
                f"{requested} has USB serial {port.get('serial_number')!r}, not {usb_serial}"
            )
    if len(hits) != 1:
        raise RestoreRefused(f"USB serial {usb_serial} is enumerated on {len(hits)} ports, need exactly 1")
    return str(hits[0]["device"])


def await_device(profile: dict, ports_provider, runner, sleep, *, previous: str | None = None,
                 attempts: int = 20, interval: float = 0.5, log=None) -> str:
    """Find the pinned USB serial again before an esptool session (hard resets
    re-enumerate USB-Serial-JTAG; the node may vanish briefly or change name).

    Bounded: `attempts` polls, then refuse. Never waits on, or returns, a port
    that carries another serial; a duplicate serial or an owned port refuses at once.
    """
    want = _norm_serial(profile["expect_usb_serial"])
    for _ in range(attempts):
        ports = list(ports_provider())
        if previous:
            old = find_port(previous, ports)
            if old is not None and _norm_serial(old.get("serial_number")) != want:
                raise RestoreRefused(f"{previous} now carries USB serial {old.get('serial_number')!r}, not {want}")
        hits = [p for p in ports if _norm_serial(p.get("serial_number")) == want]
        if len(hits) > 1:
            raise RestoreRefused(f"USB serial {want} is enumerated on {len(hits)} ports, need exactly 1")
        if len(hits) == 1:
            device = str(hits[0]["device"])
            ok, message = validate_upload_target(profile["guard_env"], device, ports)
            if not ok:
                raise RestoreRefused(f"upload guard: {message}")
            check_port_free(device, runner)
            if previous and log and _normalise_port(device) != _normalise_port(previous):
                log(f"port drift: {previous} -> {device} (same USB serial {want})")
            return device
        sleep(interval)
    raise RestoreRefused(f"USB serial {want} did not re-enumerate within {attempts} polls of {interval}s")


def chip_id_from_mac(mac: str) -> str:
    parts = mac.strip().upper().split(":")
    if len(parts) != 6:
        raise RestoreRefused(f"cannot derive chip id from MAC {mac!r}")
    return parts[5] + parts[4] + parts[3] + "00"


def _esptool_prefix() -> list[str]:
    import importlib.util

    penv = Path.home() / ".platformio" / "penv" / "bin" / "python"
    if penv.is_file():
        return [str(penv), "-m", "esptool"]
    if importlib.util.find_spec("esptool") is not None:
        return [sys.executable, "-m", "esptool"]
    raise RestoreRefused("esptool not found (PlatformIO penv or importable module required)")


def _esptool(prefix: list[str], device: str, after: str, *command: str) -> list[str]:
    # Every session ends in hard_reset so a refusal or a stop between steps leaves
    # the chip running its app, not parked in ROM download mode (incident
    # 2026-10-14: a killed run with no_reset left B489 silent until a reset).
    if after != "hard_reset":
        raise RestoreRefused(f"restore esptool sessions must end in hard_reset, not {after!r}")
    argv = [*prefix, "--chip", "esp32s3", "--port", device, "--baud", "921600",
            "--before", "default_reset", "--after", after, *command]
    if any(a in _FORBIDDEN_ESPTOOL_ARGS for a in argv):
        raise RestoreRefused(f"refusing forbidden esptool argument in {argv}")
    return argv


def read_rom_identity(prefix, device, runner, profile) -> str:
    """ROM bootloader identity: works whether or not the application runs."""
    import re

    rc, out, err = _run(runner, _esptool(prefix, device, "hard_reset", "read_mac"), 60, "esptool read_mac")
    if rc != 0:
        raise RestoreRefused(f"esptool read_mac failed (rc={rc}): {err.strip()[-400:]}")
    if "ESP32-S3" not in out:
        raise RestoreRefused("ROM did not report an ESP32-S3")
    match = re.search(r"^MAC:\s*([0-9A-Fa-f:]{17})", out, re.M)
    if match is None:
        raise RestoreRefused("ROM read_mac printed no MAC")
    mac = match.group(1).upper()
    if mac != _norm_serial(profile["expect_usb_serial"]):
        raise RestoreRefused(f"ROM MAC {mac} != pinned USB serial {profile['expect_usb_serial']}")
    chip = chip_id_from_mac(mac)
    if chip != profile["expect_chip"]:
        raise RestoreRefused(f"ROM chip {chip} != pinned {profile['expect_chip']}")
    return mac


def read_flash_region(prefix, device, runner, offset: int, size: int, out_path: Path, after: str = "hard_reset") -> bytes:
    rc, _out, err = _run(
        runner,
        _esptool(prefix, device, after, "read_flash", hex(offset), str(size), str(out_path)),
        600,
        f"esptool read_flash {offset:#x}",
    )
    if rc != 0 or not out_path.is_file():
        raise RestoreRefused(f"esptool read_flash {offset:#x}+{size} failed (rc={rc}): {err.strip()[-400:]}")
    data = out_path.read_bytes()
    if len(data) != size:
        raise RestoreRefused(f"read_flash {offset:#x} returned {len(data)} bytes, expected {size}")
    return data


def read_app_identity(device: str, runner) -> dict[str, str] | None:
    """Optional application identity via the existing `:build` guard. None = silent."""
    import re

    guard = _repo_root() / "scripts" / "regression-harness" / "k1_device_identity_guard.py"
    argv = [sys.executable, str(guard), "--port", device, "--baud", "115200"]
    try:
        rc, out, _err = _run(runner, argv, 25, "identity guard")
    except RestoreRefused:
        return None
    match = re.search(r"IDENTITY OK: git=(\S+) env=(\S+) epoch=(\S+)", out)
    if rc == 0 and match:
        return {"git": match.group(1), "env": match.group(2), "epoch": match.group(3)}
    return None


def run_saved_app_restore(
    declared: dict,
    *,
    profile_name: str = "b489-original-app0-20261013",
    profiles: dict[str, dict] | None = None,
    root: Path | None = None,
    runner=None,
    ports_provider=None,
    sleep=None,
    esptool_prefix: list[str] | None = None,
    log=print,
) -> int:
    """Guarded restore of the pinned app image. Returns a RESTORE_* exit code."""
    import tempfile
    import time

    profiles = SAVED_APP_PROFILES if profiles is None else profiles
    root = _repo_root() if root is None else root
    runner = _real_runner if runner is None else runner
    ports_provider = list_serial_ports if ports_provider is None else ports_provider
    sleep = time.sleep if sleep is None else sleep

    def say(msg: str) -> None:
        log(_RESTORE_PREFIX + msg)

    profile = profiles.get(profile_name)
    if profile is None:
        say(f"REFUSED: unknown profile {profile_name!r}")
        return RESTORE_REFUSED
    source = root / profile["image"]
    # Set immediately BEFORE the writer is invoked. From then on nothing may be
    # reported as "chip not written": a timeout, a failed or short readback, or
    # an unexpected error all mean app0 may be partial or unverified.
    write_attempted = False

    def failed(exc: BaseException, kind: str) -> int:
        if write_attempted:
            say(f"WRITE ATTEMPTED, NOT VERIFIED ({kind}): {exc}")
            say("app0 may be partial. The only allowed repair is rerunning this same pinned restore.")
            return RESTORE_WRITE_FAILED
        say(f"REFUSED (chip not written; writer never invoked) ({kind}): {exc}")
        return RESTORE_REFUSED

    try:
        # 1. static: declared flags and file bytes against the pin.
        check_declared_against_profile(declared, profile, root)
        image_bytes = source.read_bytes()
        check_image_against_profile(image_bytes, profile)
        say(f"image pinned: {profile['sha256']} elf {profile['elf_sha256']}")

        # 2. USB identity through the existing guard; port names may drift.
        ports = list(ports_provider())
        device = locate_port_by_serial(profile["expect_usb_serial"], ports, declared.get("port"))
        requested = declared.get("port")
        if requested and _normalise_port(requested) != _normalise_port(device):
            state = "not enumerated" if find_port(requested, ports) is None else "enumerated"
            say(f"requested port {requested} {state}; using {device}, found by USB serial {profile['expect_usb_serial']}")
        ok, message = validate_upload_target(profile["guard_env"], device, ports)
        if not ok:
            raise RestoreRefused(f"upload guard: {message}")
        say(f"usb guard: {message}")
        check_port_free(device, runner)
        prefix = esptool_prefix if esptool_prefix is not None else _esptool_prefix()

        # 3. application identity is preflight evidence only, never admission.
        before = read_app_identity(device, runner)
        say(f"app before: {before if before else 'no answer (recovery does not need one)'}")

        def session_device() -> str:
            # Re-find the pinned serial (bounded) before EVERY esptool session.
            nonlocal device
            device = await_device(profile, ports_provider, runner, sleep, previous=device, log=say)
            return device

        with tempfile.TemporaryDirectory(prefix="k1-restore-") as tmp:
            tmpdir = Path(tmp)
            # 4. ROM identity, then the live partition table and otadata.
            mac = read_rom_identity(prefix, session_device(), runner, profile)
            say(f"rom identity: MAC {mac}; chip id {chip_id_from_mac(mac)} is derived from that MAC, "
                "not an independent silicon register read")
            otadata = read_flash_region(prefix, session_device(), runner, profile["otadata_offset"],
                                        profile["otadata_size"], tmpdir / "otadata.bin")
            partition = read_flash_region(prefix, session_device(), runner, profile["partition_offset"],
                                          profile["partition_size"], tmpdir / "partition.bin")
            plan = plan_saved_app_restore(profile, image_bytes=image_bytes, otadata=otadata, partition=partition)
            say(f"plan: {plan}")

            # 5. stage the verified bytes privately; re-check source and target.
            staged = tmpdir / "app0.bin"
            staged.write_bytes(image_bytes)
            staged.chmod(0o600)
            if _sha256(staged.read_bytes()) != profile["sha256"]:
                raise RestoreRefused("staged image hash changed")
            if _sha256(source.read_bytes()) != profile["sha256"]:
                raise RestoreRefused("pinned source file changed after it was checked")
            read_rom_identity(prefix, session_device(), runner, profile)

            # 6. the one write: this file, this address, flash params kept.
            write = plan["writes"][0]
            argv = _esptool(prefix, session_device(), "hard_reset", "write_flash", "--flash_mode", "keep",
                            "--flash_freq", "keep", "--flash_size", "keep", hex(write["offset"]), str(staged))
            say(f"WRITING {profile['size']} bytes at {write['offset']:#x} on {device} (app slot {plan['slot']} only)")
            write_attempted = True
            rc, _out, err = _run(runner, argv, 900, "esptool write_flash")
            if rc != 0:
                say(f"WRITE FAILED rc={rc}: {err.strip()[-400:]}")
                say("app0 may be partial. The only allowed repair is rerunning this same pinned restore.")
                return RESTORE_WRITE_FAILED

            # 7. readback of the written bytes, otadata unchanged (each session hard-resets).
            back = read_flash_region(prefix, session_device(), runner, write["offset"], profile["size"],
                                     tmpdir / "readback.bin")
            info = inspect_app_image(back)
            ota_after = read_flash_region(prefix, session_device(), runner, profile["otadata_offset"],
                                          profile["otadata_size"], tmpdir / "otadata-after.bin")
            if info["sha256"] != profile["sha256"] or info["elf_sha256"] != profile["elf_sha256"]:
                say(f"READBACK MISMATCH: sha256 {info['sha256']} elf {info['elf_sha256']}")
                return RESTORE_READBACK_MISMATCH
            if _sha256(ota_after) != profile["otadata_sha256"]:
                say(f"READBACK MISMATCH: otadata now {_sha256(ota_after)}")
                return RESTORE_READBACK_MISMATCH
            say(f"readback verified: sha256 {info['sha256']} elf {info['elf_sha256']}; otadata unchanged")
    except RestoreRefused as exc:
        return failed(exc, "check")
    except Exception as exc:
        # Host errors (file, serial enumeration, decode, a blocked spawn) and
        # anything unexpected. The traceback goes to stderr so the evidence is
        # kept, and the exit code still says whether the writer was invoked.
        import traceback

        traceback.print_exc()
        return failed(exc, type(exc).__name__)

    # 8. application identity, reported separately from the byte proof.
    sleep(6)
    try:
        device = await_device(profile, ports_provider, runner, sleep, previous=device, log=say)
        after = read_app_identity(device, runner)
    except (RestoreRefused, OSError, RuntimeError) as exc:
        say(f"BYTES VERIFIED; application identity not read after reset: {exc}")
        return RESTORE_APP_SILENT
    if after is None:
        say("BYTES VERIFIED; application did not answer :build")
        return RESTORE_APP_SILENT
    if after["git"] != profile["expect_git"] or after["env"] != profile["expect_env"]:
        say(f"APP IDENTITY MISMATCH after verified bytes: {after}")
        return RESTORE_READBACK_MISMATCH
    say(f"RESTORED AND VERIFIED: git={after['git']} env={after['env']} chip {profile['expect_chip']}")
    return RESTORE_OK


def run_saved_app_plan_only(
    declared: dict,
    *,
    otadata_file: Path,
    partition_file: Path,
    ports: list[dict],
    profile_name: str = "b489-original-app0-20261013",
    profiles: dict[str, dict] | None = None,
    root: Path | None = None,
    log=print,
) -> int:
    """Host plan from local copies. Opens no port and runs no device tool."""
    profiles = SAVED_APP_PROFILES if profiles is None else profiles
    root = _repo_root() if root is None else root
    profile = profiles.get(profile_name)
    try:
        if profile is None:
            raise RestoreRefused(f"unknown profile {profile_name!r}")
        check_declared_against_profile(declared, profile, root)
        image_bytes = (root / profile["image"]).read_bytes()
        device = locate_port_by_serial(profile["expect_usb_serial"], ports, declared.get("port"))
        ok, message = validate_upload_target(profile["guard_env"], device, ports)
        if not ok:
            raise RestoreRefused(f"upload guard: {message}")
        plan = plan_saved_app_restore(
            profile,
            image_bytes=image_bytes,
            otadata=Path(otadata_file).read_bytes(),
            partition=Path(partition_file).read_bytes(),
        )
    except (RestoreRefused, OSError) as exc:
        log(_RESTORE_PREFIX + f"PLAN REFUSED: {exc}")
        return RESTORE_REFUSED
    log(_RESTORE_PREFIX + f"PLAN ONLY (no device opened, nothing written): {json.dumps(plan)}")
    return RESTORE_OK


def _restore_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Pinned saved-app restore (one profile only).")
    parser.add_argument("--profile", default="b489-original-app0-20261013")
    parser.add_argument("--port")
    parser.add_argument("--image", required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--size", type=int, required=True)
    parser.add_argument("--slot", type=int, required=True)
    parser.add_argument("--offset", type=lambda v: int(v, 0), required=True)
    parser.add_argument("--expect-git", required=True)
    parser.add_argument("--expect-env", required=True)
    parser.add_argument("--expect-chip", required=True)
    parser.add_argument("--expect-usb-serial", required=True)
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--otadata-file", type=Path)
    parser.add_argument("--partition-file", type=Path)
    parser.add_argument("--ports-json", type=Path)
    args = parser.parse_args(argv)
    declared = {
        "port": args.port, "image": args.image, "sha256": args.sha256, "size": args.size,
        "slot": args.slot, "offset": args.offset, "expect_git": args.expect_git,
        "expect_env": args.expect_env, "expect_chip": args.expect_chip,
        "expect_usb_serial": args.expect_usb_serial,
    }
    fixtures = [f for f in (args.otadata_file, args.partition_file, args.ports_json) if f is not None]
    if args.plan_only:
        if len(fixtures) != 3:
            print(_RESTORE_PREFIX + "PLAN REFUSED: --plan-only needs --otadata-file, --partition-file and --ports-json")
            return RESTORE_REFUSED
        try:
            ports = json.loads(args.ports_json.read_text())
        except (OSError, ValueError) as exc:
            print(_RESTORE_PREFIX + f"PLAN REFUSED: --ports-json unreadable: {exc}")
            return RESTORE_REFUSED
        return run_saved_app_plan_only(
            declared,
            otadata_file=args.otadata_file,
            partition_file=args.partition_file,
            ports=ports,
            profile_name=args.profile,
        )
    if fixtures:
        print(_RESTORE_PREFIX + "REFUSED (chip not written): fixture files cannot authorise a device write")
        return RESTORE_REFUSED
    return run_saved_app_restore(declared, profile_name=args.profile)


def _guard_upload_action(source, target, env) -> None:
    pioenv = env.subst("$PIOENV")
    upload_port = env.subst("$UPLOAD_PORT")
    ok, message = validate_upload_target(pioenv, upload_port)
    prefix = "[k1-upload-guard] "
    if not ok:
        raise SystemExit(prefix + message)
    print(prefix + message)
    # Pinned saved-app envs only: this pre-action runs at the real upload
    # boundary, after any rebuild, so it hashes the files actually sent.
    for profile in SAVED_APP_PROFILES.values():
        if pioenv not in profile["forward_envs"]:
            continue
        try:
            lines = check_forward_segments(profile, forward_segments_from_env(env))
        except RestoreRefused as exc:
            raise SystemExit(prefix + f"{pioenv}: saved-app restore would be impossible after this upload: {exc}")
        for line in lines:
            print(prefix + line)


def _install_platformio_hook() -> None:
    try:
        Import("env")  # type: ignore[name-defined]  # noqa: F821
    except NameError:
        return
    env.AddPreAction("upload", _guard_upload_action)  # type: ignore[name-defined]  # noqa: F821


def _main(argv: list[str]) -> int:
    if argv[:1] == ["--restore-saved-app"]:
        return _restore_main(argv[1:])
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
