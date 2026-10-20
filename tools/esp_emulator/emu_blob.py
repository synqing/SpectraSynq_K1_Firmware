"""Build the run-owned scenario blob and the merged emulator flash image.

The blob layout matches ``BlobHeader`` in SPECTRASYNQ_K1_FIRMWARE/audio/
k1_emu_fixture.cpp. It is written into the unused ota_1 (app1) partition of the
run's own flash copy, so the application image is executed exactly as built.
"""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass

MAGIC = b"K1EMUSC2"
VERSION = 2
HEADER_BYTES = 256
COMMAND_BYTES = 96
COMMAND_TEXT = 88
MAX_COMMANDS = 64
FLAG_RECOVERY = 1 << 0
FLAG_BOOT_EPOCH = 1 << 1
FLAG_DECLARED_EPOCH = 1 << 2
FLAG_NOVELTY_TRACE = 1 << 3
EPOCH_POLICIES = ("zero", "boot_monotonic", "declared")

FLASH_SIZE = 16 * 1024 * 1024
BOOTLOADER_AT = 0x0
PARTITIONS_AT = 0x8000
APP_AT = 0x10000
APP_SIZE = 0x640000
SCENARIO_AT = 0x650000      # app1 / ota_1 in default_16MB.csv
SCENARIO_SIZE = 0x640000
LITTLEFS_AT = 0xC90000      # "spiffs" label, LittleFS
LITTLEFS_SIZE = 0x360000


@dataclass
class BlobSpec:
    run_id: str
    sample_rate: int
    hop_samples: int
    pcm: bytes                 # real samples, s16le mono
    pad_samples: int
    capture_start_hop: int
    capture_end_hop: int
    capture_every: int
    recovery: bool
    commands: list[tuple[int, str]]
    stall_ms: int
    epoch_policy: str = "boot_monotonic"
    declared_epoch_us: int = 0
    novelty_trace: bool = False


def _epoch_flag(spec: BlobSpec) -> int:
    if spec.epoch_policy not in EPOCH_POLICIES:
        raise ValueError(f"unknown epoch policy {spec.epoch_policy!r}")
    if spec.epoch_policy != "declared" and spec.declared_epoch_us:
        raise ValueError("declared_epoch_us is only meaningful for the declared policy")
    return {"zero": 0, "boot_monotonic": FLAG_BOOT_EPOCH, "declared": FLAG_DECLARED_EPOCH}[spec.epoch_policy]


def build_blob(spec: BlobSpec) -> tuple[bytes, int]:
    """Return (blob, payload_crc32)."""
    if len(spec.pcm) % 2:
        raise ValueError("PCM byte length is odd")
    if len(spec.run_id.encode()) >= 48:
        raise ValueError("run id is too long")
    if len(spec.commands) > MAX_COMMANDS:
        raise ValueError("too many commands")
    real_samples = len(spec.pcm) // 2
    hops_real = -(-real_samples // spec.hop_samples)
    pcm_padded = spec.pcm + b"\0" * (hops_real * spec.hop_samples * 2 - len(spec.pcm))
    cmd_blob = bytearray()
    for hop, text in spec.commands:
        raw = text.encode("ascii")
        if len(raw) >= COMMAND_TEXT:
            raise ValueError(f"command text too long: {text!r}")
        cmd_blob += struct.pack("<II", hop, 0) + raw + b"\0" * (COMMAND_TEXT - len(raw))
    command_offset = HEADER_BYTES
    pcm_offset = command_offset + len(cmd_blob)
    pcm_offset += (-pcm_offset) % 4
    payload = bytes(cmd_blob) + b"\0" * (pcm_offset - command_offset - len(cmd_blob)) + pcm_padded
    blob_bytes = HEADER_BYTES + len(payload)
    if blob_bytes > SCENARIO_SIZE:
        raise ValueError(f"scenario blob {blob_bytes} bytes exceeds the ota_1 partition")
    payload_crc = zlib.crc32(payload) & 0xFFFFFFFF
    head = struct.pack(
        "<8sII48s14IQ124s",
        MAGIC, VERSION, HEADER_BYTES, spec.run_id.encode().ljust(48, b"\0"),
        spec.sample_rate, spec.hop_samples, real_samples, spec.pad_samples,
        spec.capture_start_hop, spec.capture_end_hop, spec.capture_every,
        (FLAG_RECOVERY if spec.recovery else 0) | _epoch_flag(spec)
        | (FLAG_NOVELTY_TRACE if spec.novelty_trace else 0),
        len(spec.commands), command_offset,
        pcm_offset, spec.stall_ms, blob_bytes, payload_crc, spec.declared_epoch_us, b"\0" * 124,
    )
    assert len(head) == HEADER_BYTES - 4
    head += struct.pack("<I", zlib.crc32(head) & 0xFFFFFFFF)
    return head + payload, payload_crc


def merge_flash(bootloader: bytes, partitions: bytes, app: bytes) -> bytearray:
    """Erased 16 MB flash with bootloader, partition table and app0 placed as built.

    otadata stays erased, so the bootloader selects ota_0 (app0). No header
    patching: the bootloader and app bytes are exactly the build outputs.
    """
    if len(app) > APP_SIZE:
        raise ValueError("app image larger than app0")
    flash = bytearray(b"\xff" * FLASH_SIZE)
    flash[BOOTLOADER_AT:BOOTLOADER_AT + len(bootloader)] = bootloader
    flash[PARTITIONS_AT:PARTITIONS_AT + len(partitions)] = partitions
    flash[APP_AT:APP_AT + len(app)] = app
    return flash


def place_blob(flash: bytearray, blob: bytes) -> None:
    """Erase the whole scenario partition and write this run's blob."""
    flash[SCENARIO_AT:SCENARIO_AT + SCENARIO_SIZE] = b"\xff" * SCENARIO_SIZE
    flash[SCENARIO_AT:SCENARIO_AT + len(blob)] = blob


def littlefs_region(flash: bytes) -> bytes:
    return bytes(flash[LITTLEFS_AT:LITTLEFS_AT + LITTLEFS_SIZE])


def app_region(flash: bytes, length: int) -> bytes:
    return bytes(flash[APP_AT:APP_AT + length])
