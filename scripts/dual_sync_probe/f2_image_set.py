"""Fail-closed validation for the frozen F2 reviewed-image set.

The image-set manifest is firmware authority. It deliberately contains no host
controller identity: host execution may advance while the reviewed firmware
source and exact application images remain fixed.
"""

from __future__ import annotations

import hashlib
import json
import re
import struct
import subprocess
from pathlib import Path


class F2ImageSetError(RuntimeError):
    """Frozen image-set input is missing, mutable, or internally incoherent."""


REQUIRED_ENVS = (
    "k1_sync_probe_main_sync_only",
    "k1_sync_probe_main",
    "k1_sync_probe_bench",
)
ESPTOOL_PACKAGE = "tool-esptoolpy@4.8.9"
PARTITION_TABLE_OFFSET = 0x8000
PARTITION_TABLE_SIZE = 0xC00
APPLICATION_LABEL = "app0"
APPLICATION_OFFSET = 0x10000
_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_GIT_SHA_RE = re.compile(r"[0-9a-f]{40}")
_IMAGE_KEYS = {
    "role",
    "required_chip",
    "available",
    "bin_path",
    "bin_sha256",
    "elf_path",
    "elf_sha256",
    "app_elf_sha256",
}
_PARTITION_KEYS = {
    "path",
    "sha256",
    "offset",
    "size",
    "application_label",
    "application_offset",
    "application_size",
}
_TOP_LEVEL_KEYS = {
    "schema_version",
    "status",
    "blockers",
    "firmware_source_sha",
    "raw_pack_relative_path",
    "esptool_package",
    "package_provenance",
    "partition_table",
    "images",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise F2ImageSetError(
                f"image-set manifest contains duplicate key {key!r}"
            )
        result[key] = value
    return result


def _read_json(path: Path) -> dict:
    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
        )
    except (OSError, json.JSONDecodeError) as error:
        raise F2ImageSetError(
            f"cannot read image-set manifest {path}: {error}"
        ) from error
    if not isinstance(payload, dict):
        raise F2ImageSetError("image-set manifest root must be an object")
    return payload


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _direct_file(
    value: object,
    *,
    manifest_root: Path,
    label: str,
) -> Path:
    if not isinstance(value, str) or not value:
        raise F2ImageSetError(f"{label} path is missing")
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise F2ImageSetError(
            f"{label} must be relative to the frozen image-set root"
        )
    path = manifest_root / relative
    cursor = manifest_root
    for part in relative.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise F2ImageSetError(f"{label} may not contain symlinks")
    if ".pio" in relative.parts:
        raise F2ImageSetError(f"{label} may not live under .pio")
    resolved = path.resolve()
    if not _inside(resolved, manifest_root) or not path.is_file():
        raise F2ImageSetError(
            f"{label} is not a direct file in the frozen image set"
        )
    return resolved


def _require_sha256(value: object, label: str) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise F2ImageSetError(f"{label} must be a lowercase SHA-256")
    return value


def _app_elf_sha256(bin_path: Path) -> str:
    command = [
        "pio",
        "pkg",
        "exec",
        "--package",
        ESPTOOL_PACKAGE,
        "--",
        "esptool.py",
        "image_info",
        str(bin_path),
    ]
    try:
        output = subprocess.check_output(
            command,
            text=True,
            stderr=subprocess.STDOUT,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise F2ImageSetError(
            f"cannot inspect reviewed application image: {error}"
        ) from error
    match = re.search(r"ELF file SHA256:\s*([0-9a-f]{64})", output)
    if match is None:
        raise F2ImageSetError(
            "reviewed application image has no ELF SHA-256 identity"
        )
    return match.group(1)


def _partition_entries(data: bytes) -> dict[str, tuple[int, int]]:
    entries: dict[str, tuple[int, int]] = {}
    for index in range(0, len(data), 32):
        raw = data[index : index + 32]
        if len(raw) != 32:
            break
        magic = int.from_bytes(raw[:2], "little")
        if magic in {0xFFFF, 0xEBEB}:
            break
        if magic != 0x50AA:
            raise F2ImageSetError(
                f"partition table entry {index // 32} has invalid magic"
            )
        (
            _magic,
            entry_type,
            _subtype,
            offset,
            size,
            raw_label,
            _flags,
        ) = struct.unpack("<HBBII16sI", raw)
        label = raw_label.split(b"\0", 1)[0].decode(
            "ascii", errors="strict"
        )
        if label in entries:
            raise F2ImageSetError(
                f"partition table contains duplicate label {label!r}"
            )
        if entry_type == 0:
            entries[label] = (offset, size)
    return entries


def load(path: Path, *, repo_root: Path) -> dict:
    """Validate and normalise one complete immutable reviewed-image set."""
    repo_root = repo_root.resolve()
    manifest_path = path.resolve()
    if (
        not _inside(manifest_path, repo_root)
        or manifest_path.is_symlink()
        or not manifest_path.is_file()
    ):
        raise F2ImageSetError(
            "image-set manifest must be a direct file inside the repository"
        )
    manifest_root = manifest_path.parent
    if ".pio" in manifest_path.relative_to(repo_root).parts:
        raise F2ImageSetError("image-set manifest may not live under .pio")

    payload = _read_json(manifest_path)
    unexpected = set(payload) - _TOP_LEVEL_KEYS
    if unexpected & {"host_execution_sha", "upload_controller_sha"}:
        raise F2ImageSetError(
            "image-set manifest must not embed host execution authority"
        )
    if set(payload) != _TOP_LEVEL_KEYS:
        raise F2ImageSetError(
            "image-set manifest top-level fields are not exact"
        )
    if payload["schema_version"] != 2:
        raise F2ImageSetError("image-set schema_version must be 2")
    status = payload["status"]
    blockers = payload["blockers"]
    if status not in {"READY", "BLOCKED"} or not isinstance(blockers, list):
        raise F2ImageSetError("image-set status/blockers are malformed")
    if status != "READY":
        detail = "; ".join(str(item) for item in blockers) or "unspecified"
        raise F2ImageSetError(
            f"reviewed image set is BLOCKED: {detail}"
        )
    if blockers:
        raise F2ImageSetError("READY image set may not contain blockers")
    firmware_sha = payload["firmware_source_sha"]
    if (
        not isinstance(firmware_sha, str)
        or _GIT_SHA_RE.fullmatch(firmware_sha) is None
    ):
        raise F2ImageSetError(
            "firmware_source_sha must be a full lowercase commit SHA"
        )
    if payload["esptool_package"] != ESPTOOL_PACKAGE:
        raise F2ImageSetError(
            f"image-set esptool_package must be {ESPTOOL_PACKAGE}"
        )
    package_provenance = payload["package_provenance"]
    required_packages = {
        "platformio",
        "python",
        "platform",
        "framework_arduino",
        "framework_espidf_libraries",
        "toolchain_xtensa",
        "toolchain_riscv",
        "nimble_arduino",
        "fastled",
        "fixedpoints",
        "m5rotate8",
    }
    if (
        not isinstance(package_provenance, dict)
        or set(package_provenance) != required_packages
        or package_provenance.get("nimble_arduino") != "2.5.0"
        or any(
            not isinstance(value, str) or not value
            for value in package_provenance.values()
        )
    ):
        raise F2ImageSetError(
            "image-set package provenance is incomplete or unpinned"
        )
    raw_pack_relative = payload["raw_pack_relative_path"]
    if (
        not isinstance(raw_pack_relative, str)
        or Path(raw_pack_relative).is_absolute()
        or ".." in Path(raw_pack_relative).parts
    ):
        raise F2ImageSetError("raw image pack path is malformed")
    raw_pack_root = (repo_root / raw_pack_relative).resolve()
    if (
        not _inside(raw_pack_root, repo_root)
        or not raw_pack_root.is_dir()
        or raw_pack_root.is_symlink()
    ):
        raise F2ImageSetError("raw image pack is missing or indirect")

    partition = payload["partition_table"]
    if not isinstance(partition, dict) or set(partition) != _PARTITION_KEYS:
        raise F2ImageSetError(
            "image-set partition_table fields are not exact"
        )
    expected_partition = {
        "offset": PARTITION_TABLE_OFFSET,
        "size": PARTITION_TABLE_SIZE,
        "application_label": APPLICATION_LABEL,
        "application_offset": APPLICATION_OFFSET,
    }
    for key, expected in expected_partition.items():
        if partition.get(key) != expected:
            raise F2ImageSetError(
                f"image-set partition_table requires {key}={expected!r}"
            )
    application_size = partition.get("application_size")
    if not isinstance(application_size, int) or application_size <= 0:
        raise F2ImageSetError(
            "image-set application_size must be a positive integer"
        )
    partition_path = _direct_file(
        partition.get("path"),
        manifest_root=raw_pack_root,
        label="partition table",
    )
    if partition_path.stat().st_size != PARTITION_TABLE_SIZE:
        raise F2ImageSetError("partition table size does not match manifest")
    partition_sha = _require_sha256(
        partition.get("sha256"), "partition table hash"
    )
    if _sha256(partition_path) != partition_sha:
        raise F2ImageSetError("partition table hash mismatch")
    entries = _partition_entries(partition_path.read_bytes())
    if entries.get(APPLICATION_LABEL) != (
        APPLICATION_OFFSET,
        application_size,
    ):
        raise F2ImageSetError(
            "partition table app0 geometry does not match manifest"
        )

    images = payload["images"]
    if not isinstance(images, dict) or set(images) != set(REQUIRED_ENVS):
        raise F2ImageSetError(
            "image-set images must contain exactly the three F2 environments"
        )
    normalised_images = {}
    for env in REQUIRED_ENVS:
        image = images[env]
        if not isinstance(image, dict) or set(image) != _IMAGE_KEYS:
            raise F2ImageSetError(
                f"image-set {env} fields are not exact"
            )
        role = image.get("role")
        required_chip = image.get("required_chip")
        expected_identity = {
            "k1_sync_probe_main_sync_only": ("leader", "F887A500"),
            "k1_sync_probe_main": ("leader", "F887A500"),
            "k1_sync_probe_bench": ("follower", "B489A500"),
        }[env]
        if (role, required_chip) != expected_identity:
            raise F2ImageSetError(f"image-set {env} role/chip mismatch")
        if image.get("available") is not True:
            raise F2ImageSetError(f"image-set {env} is unavailable")
        bin_path = _direct_file(
            image.get("bin_path"),
            manifest_root=raw_pack_root,
            label=f"{env} BIN",
        )
        elf_path = _direct_file(
            image.get("elf_path"),
            manifest_root=raw_pack_root,
            label=f"{env} ELF",
        )
        bin_sha = _require_sha256(
            image.get("bin_sha256"), f"{env} BIN hash"
        )
        elf_sha = _require_sha256(
            image.get("elf_sha256"), f"{env} ELF hash"
        )
        app_elf_sha = _require_sha256(
            image.get("app_elf_sha256"), f"{env} app ELF identity"
        )
        if _sha256(bin_path) != bin_sha:
            raise F2ImageSetError(f"{env} BIN hash mismatch")
        if _sha256(elf_path) != elf_sha:
            raise F2ImageSetError(f"{env} ELF hash mismatch")
        if elf_sha != app_elf_sha or _app_elf_sha256(bin_path) != elf_sha:
            raise F2ImageSetError(
                f"{env} BIN/ELF application identity mismatch"
            )
        if firmware_sha[:7].encode("ascii") not in bin_path.read_bytes():
            raise F2ImageSetError(
                f"{env} BIN lacks firmware source provenance"
            )
        if bin_path.stat().st_size > application_size:
            raise F2ImageSetError(
                f"{env} BIN exceeds the declared app0 partition"
            )
        normalised_images[env] = {
            "env": env,
            "bin_path": bin_path,
            "bin_sha256": bin_sha,
            "elf_path": elf_path,
            "elf_sha256": elf_sha,
            "app_elf_sha256": app_elf_sha,
        }

    return {
        "schema_version": 2,
        "status": "READY",
        "manifest_path": manifest_path,
        "manifest_sha256": _sha256(manifest_path),
        "firmware_source_sha": firmware_sha,
        "raw_pack_root": raw_pack_root,
        "esptool_package": ESPTOOL_PACKAGE,
        "package_provenance": package_provenance,
        "partition_table": {
            "path": partition_path,
            "sha256": partition_sha,
            "offset": PARTITION_TABLE_OFFSET,
            "size": PARTITION_TABLE_SIZE,
            "application_label": APPLICATION_LABEL,
            "application_offset": APPLICATION_OFFSET,
            "application_size": application_size,
        },
        "images": normalised_images,
    }
