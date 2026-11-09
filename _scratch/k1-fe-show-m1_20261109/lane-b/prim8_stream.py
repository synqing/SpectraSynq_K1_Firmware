"""prim8_stream — prepared Prim8 stream library (K1-FE-SHOW-M1 Rev 2, Lane B).

A "prepared stream" is two files:
  <name>.prsm       concatenated 34-byte PRSM frames (the exact bytes sent to the K1)
  <name>.prsm.json  sidecar, schema "k1-prim8-stream/0" (see SIDECAR_SCHEMA_ID below)

Wire format (firmware audio/k1_prsm.h:10-27, k1_prsm.cpp:22-43, host PRISM.studio src/cdc.js:24-39):
  off  0  4 B  magic 'P','R','S','M'
  off  4  u8   version = 1
  off  5  u8   hz (device accepts 30..240, k1_authored_source.cpp:28)
  off  6  u32  seq, little-endian
  off 10  u64  t_us, little-endian (ShowBundle timeline microseconds; device ignores it for scheduling)
  off 18  8 x u16 LE Prim8: pressure, impact, mass, momentum, heat, space, texture, gravity

Timebase (one rule each; full derivation in B-P1-contract.md section B5):
  master axis   = asset sample index n at asset rate R (sample 0 = first decoded sample of the asset)
  tick time     = tick_time_us(i, hz) = (i*1_000_000 + hz//2) // hz        (== vm.js tickTimeUs, vm.js:140-145)
  sample -> us  = sample_to_us(n, R)  = (2*n*1_000_000 + R) // (2*R)       (round half up)
  us -> sample  = us_to_sample(t, R)  = (2*t*R + 1_000_000) // 2_000_000   (round half up)
  passage start = first tick i0 with tick_time_us(i0, hz) >= sample_to_us(start_sample, R)

PUBLIC API (stable for lane-c-emu):
  PRIM8_NAMES                      tuple of 8 names in wire order
  DEVICE_CONSUMED_INDICES          frozenset({0,1,2,3,6})
  FRAME_LEN                        34
  SIDECAR_SCHEMA_ID                "k1-prim8-stream/0"
  RESYNC_PREAMBLE                  b"\n" + 63 x b"\x00" (64 B, one write); send before the first frame of every
                                   session/epoch (bench gate: audit_prsm_bytes.py)
  FRAME_GUARD_BYTES = 30; wire_packets(stream, guard=30) -> list of 64-byte writes (30 NUL + frame);
                                   the player must issue exactly one write per packet
  encode_frame(seq, t_us, prim8, hz=120, *, version=1, magic=b"PRSM") -> bytes
      Strict for normal use: raises ValueError on out-of-range fields unless the
      override kwargs are used (fixtures use version/magic/hz overrides to build bad frames).
  decode_frame(buf) -> dict {magic, version, hz, seq, t_us, prim8}   (no semantic checks)
  tick_time_us(i, hz) -> int
  sample_to_us(n, rate) -> int ; us_to_sample(t_us, rate) -> int
  first_tick_at_or_after_us(t_us, hz) -> int
  build_frames(prim8_rows, hz, start_tick, seq0=0) -> list[bytes]
      one frame per row, tick i = start_tick + k, seq = seq0 + k
  default_prim8_semantics() -> list[dict]   (sidecar "prim8" block)
  make_sidecar(frames_bytes, *, asset, passage_start_sample, hz, epochs, source=None, notes=None) -> dict
  write_stream(bin_path, frames, *, asset, passage_start_sample, hz, epochs=None, source=None, notes=None) -> dict
      writes <bin_path> and <bin_path>.json; returns the sidecar dict
  read_stream(bin_path, sidecar_path=None) -> (list[dict], dict|None, bytes)
      decoded frames, sidecar (None if absent), raw bytes. Trailing partial frame is
      returned as a dict with key "truncated_len".
  sha256_bytes(b) -> hex ; sha256_file(path) -> hex

Epochs: sidecar "epochs" is a list of {"epoch_id": str, "first_frame": int, "kind": str}, sorted by
first_frame, first entry first_frame == 0. A seq or t_us discontinuity is legal ONLY at a declared
epoch boundary (validated by validate_prim8_stream.py, not here).
"""

from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path
from typing import Iterable, Sequence

PRIM8_NAMES = ("pressure", "impact", "mass", "momentum", "heat", "space", "texture", "gravity")
DEVICE_CONSUMED_INDICES = frozenset({0, 1, 2, 3, 6})
FRAME_LEN = 34
MAGIC = b"PRSM"
VERSION = 1
DEVICE_HZ_MIN = 30
DEVICE_HZ_MAX = 240
SIDECAR_SCHEMA_ID = "k1-prim8-stream/0"
US_PER_S = 1_000_000

# Safe resync preamble: send before the first frame of every session and every epoch.
# LF exits ':' command mode (executing a line only if one was already pending; firmware has no
# abort byte) and is skipped outside command mode; the 63 NUL bytes complete any partial PRSM
# buffer (fill 1..33 needs at most 30 bytes) and are no-ops at the hotkey dispatcher.
# 64 bytes = one full USB packet, so it keeps the 64-byte guarded frame writes packet-aligned.
# Proof against the real scanner for every start state: B-P1-contract.md "Resync preamble".
RESYNC_PREAMBLE = b"\n" + b"\x00" * 63

# Per-frame guard: write every frame as ONE 64-byte write = 30 x NUL + 34-byte frame (one full-speed
# USB packet). If the device's USB RX queue overflows and drops the tail of a packet, the next
# packet's 30 NULs complete the stale partial frame before any frame byte arrives, so no byte can
# reach the hotkey dispatcher. Proof: B-P1-contract.md "USB packet loss exposure".
FRAME_GUARD_BYTES = 30


def wire_packets(stream: bytes, guard: int = FRAME_GUARD_BYTES) -> list:
    """Split a .prsm byte string into per-write packets: guard NULs + one 34-byte frame each."""
    if len(stream) % 34:
        raise ValueError("stream length is not a multiple of 34")
    return [b"\x00" * guard + stream[k:k + 34] for k in range(0, len(stream), 34)]

_FMT = "<4sBBIQ8H"  # 4+1+1+4+8+16 = 34
assert struct.calcsize(_FMT) == FRAME_LEN

# Device consumer per Prim8 index (firmware k1_authored_source.cpp:31-47 at 407fdf6f).
_DEVICE_CONSUMER = {
    0: "vu_level, peak_scaled, spectral_energy (also silence term)",
    1: "novelty (also silence term)",
    2: "low_energy (also silence term)",
    3: "mid_energy",
    4: None,
    5: None,
    6: "high_energy",
    7: None,
}


def encode_frame(seq: int, t_us: int, prim8: Sequence[int], hz: int = 120, *,
                 version: int = VERSION, magic: bytes = MAGIC) -> bytes:
    """Encode one 34-byte PRSM frame. Field widths are always enforced; hz/version/magic
    may be set to device-invalid values deliberately (fixtures)."""
    if len(prim8) != 8:
        raise ValueError(f"prim8 must have 8 values, got {len(prim8)}")
    for i, v in enumerate(prim8):
        if not isinstance(v, int) or not 0 <= v <= 0xFFFF:
            raise ValueError(f"prim8[{i}]={v!r} not a u16 integer")
    if not 0 <= hz <= 0xFF:
        raise ValueError(f"hz={hz} does not fit u8 (host cdc.js masks hz & 0xff; refuse instead)")
    if not 0 <= version <= 0xFF:
        raise ValueError("version must fit u8")
    if not 0 <= seq <= 0xFFFFFFFF:
        raise ValueError("seq must fit u32")
    if not 0 <= t_us <= 0xFFFFFFFFFFFFFFFF:
        raise ValueError("t_us must fit u64")
    if len(magic) != 4:
        raise ValueError("magic must be 4 bytes")
    return struct.pack(_FMT, magic, version, hz, seq, t_us, *prim8)


def decode_frame(buf: bytes) -> dict:
    if len(buf) != FRAME_LEN:
        raise ValueError(f"frame must be {FRAME_LEN} bytes, got {len(buf)}")
    magic, version, hz, seq, t_us, *prim8 = struct.unpack(_FMT, buf)
    return {"magic": magic, "version": version, "hz": hz, "seq": seq, "t_us": t_us,
            "prim8": list(prim8)}


def tick_time_us(i: int, hz: int) -> int:
    """vm.js tickTimeUs (vm.js:140-145): (i*1e6 + floor(hz/2)) / hz, integer."""
    return (i * US_PER_S + hz // 2) // hz


def first_tick_at_or_after_us(t_us: int, hz: int) -> int:
    i = (t_us * hz) // US_PER_S
    while tick_time_us(i, hz) < t_us:
        i += 1
    while i > 0 and tick_time_us(i - 1, hz) >= t_us:
        i -= 1
    return i


def sample_to_us(n: int, rate: int) -> int:
    """Asset sample index -> microseconds, round half up."""
    return (2 * n * US_PER_S + rate) // (2 * rate)


def us_to_sample(t_us: int, rate: int) -> int:
    """Microseconds -> nearest asset sample index, round half up."""
    return (2 * t_us * rate + US_PER_S) // (2 * US_PER_S)


def build_frames(prim8_rows: Iterable[Sequence[int]], hz: int, start_tick: int,
                 seq0: int = 0) -> list[bytes]:
    out = []
    for k, row in enumerate(prim8_rows):
        out.append(encode_frame(seq0 + k, tick_time_us(start_tick + k, hz), list(row), hz))
    return out


def default_prim8_semantics() -> list[dict]:
    sem = []
    for i, name in enumerate(PRIM8_NAMES):
        consumer = _DEVICE_CONSUMER[i]
        sem.append({
            "index": i,
            "name": name,
            "unit": "u16 linear; 0 = none, 65535 = full scale (device maps v/65535 to float 0..1)",
            "consumed_on_device": consumer is not None,
            "device_consumer": consumer if consumer else "UNCONSUMED on FE firmware 407fdf6f",
        })
    return sem


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def make_sidecar(frames_bytes: bytes, *, asset: dict, passage_start_sample: int, hz: int,
                 epochs: list | None = None, source: dict | None = None,
                 notes: str | None = None) -> dict:
    if epochs is None:
        epochs = [{"epoch_id": "e0", "first_frame": 0, "kind": "start"}]
    n_frames, rem = divmod(len(frames_bytes), FRAME_LEN)
    side = {
        "schema": SIDECAR_SCHEMA_ID,
        "asset": dict(asset),  # sha256, sample_rate, sample_count, channels[, path_hint]
        "timebase": {
            "origin": "asset sample 0 == ShowBundle t_us 0 == Trinity contract t=0.0 s",
            "tick_time_us": "(i*1000000 + hz//2) // hz  (PRISM.studio src/vm.js:140-145)",
            "sample_to_us": "(2*n*1000000 + R) // (2*R)  (round half up)",
            "us_to_sample": "(2*t_us*R + 1000000) // 2000000  (round half up)",
            "device_note": "device ignores t_us for scheduling; uses arrival time (k1_authored_source.cpp:48-50)",
        },
        "passage_start_sample": passage_start_sample,
        "hz": hz,
        "frame_len": FRAME_LEN,
        "frame_count": n_frames,
        "trailing_bytes": rem,
        "epoch_id": epochs[0]["epoch_id"],
        "epochs": epochs,
        "stream_sha256": sha256_bytes(frames_bytes),
        "prim8": default_prim8_semantics(),
        "edge_addressing": "none: one stream drives both edges (no per-edge field in PRSM v1)",
    }
    if source:
        side["source"] = source
    if notes:
        side["notes"] = notes
    return side


def write_stream(bin_path, frames: Sequence[bytes], *, asset: dict, passage_start_sample: int,
                 hz: int, epochs: list | None = None, source: dict | None = None,
                 notes: str | None = None) -> dict:
    bin_path = Path(bin_path)
    data = b"".join(frames)
    bin_path.write_bytes(data)
    side = make_sidecar(data, asset=asset, passage_start_sample=passage_start_sample, hz=hz,
                        epochs=epochs, source=source, notes=notes)
    Path(str(bin_path) + ".json").write_text(json.dumps(side, indent=2, sort_keys=False) + "\n",
                                             encoding="utf-8")
    return side


def read_stream(bin_path, sidecar_path=None):
    bin_path = Path(bin_path)
    data = bin_path.read_bytes()
    sp = Path(sidecar_path) if sidecar_path else Path(str(bin_path) + ".json")
    side = json.loads(sp.read_text(encoding="utf-8")) if sp.exists() else None
    frames = []
    n, rem = divmod(len(data), FRAME_LEN)
    for k in range(n):
        frames.append(decode_frame(data[k * FRAME_LEN:(k + 1) * FRAME_LEN]))
    if rem:
        frames.append({"truncated_len": rem})
    return frames, side, data
