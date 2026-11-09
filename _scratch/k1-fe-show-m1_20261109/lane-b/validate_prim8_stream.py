#!/usr/bin/env python3
"""validate_prim8_stream — host-only gate for prepared Prim8 (PRSM) streams.

Rejects a malformed stream BEFORE any byte is sent to a K1. It never opens a port and never
writes the stream anywhere; it only reads the two files.

Usage:
  validate_prim8_stream.py STREAM.prsm [--sidecar STREAM.prsm.json] [--quiet]

Exit codes:
  0  VALID         (prints "VALID frames=N sha256=..." and any warnings)
  1  INVALID       (prints "INVALID frame=<index|-> rule=<RULE> <detail>"; first failure only)
  2  UNSUPPORTED   (well-formed, but asks for something the FE device cannot do, e.g. per-edge cues)
  3  usage / IO error

Rule identifiers (B-P1-contract.md, "Validator rules"):
  Sidecar:   SIDECAR_MISSING, SIDECAR_SCHEMA, SIDECAR_FIELD, ASSET_IDENTITY, EPOCHS
  Stream:    TRUNCATED, FRAME_COUNT, STREAM_SHA256
  Device-level (the firmware applies these too):  DEVICE_MAGIC, DEVICE_VERSION, DEVICE_HZ_RANGE
  Host-only (stricter than the device):           HZ_MISMATCH, SEQ_DISCONTINUITY, T_US_OFF_GRID,
             T_US_NOT_NEXT_TICK, T_US_BEFORE_PASSAGE, T_US_BEYOND_ASSET, PASSAGE_START_TICK,
             EPOCH_START_SEQ
  Capability: EDGE_ADDRESSING_UNSUPPORTED
"""

from __future__ import annotations

import argparse
import json
import re
import struct
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prim8_stream as ps  # noqa: E402

DEVICE_RULES = ("DEVICE_MAGIC", "DEVICE_VERSION", "DEVICE_HZ_RANGE")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


@dataclass
class Verdict:
    status: str                 # VALID | INVALID | UNSUPPORTED
    rule: str | None = None
    frame_index: int | None = None
    detail: str = ""
    frames: int = 0
    warnings: list = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.status == "VALID"

    def line(self) -> str:
        if self.ok:
            return f"VALID frames={self.frames}"
        fi = "-" if self.frame_index is None else str(self.frame_index)
        return f"{self.status} frame={fi} rule={self.rule} {self.detail}".rstrip()


def device_frame_verdict(chunk: bytes) -> tuple[bool, str | None]:
    """Device-level rules only, applied to one 34-byte chunk, in firmware order:
    k1_prsm_parse (magic, version) then k1_authored_map_prim8 (hz 30..240).
    Independent re-implementation; the differential oracle compares it with the real C."""
    if len(chunk) != ps.FRAME_LEN:
        return False, "TRUNCATED"
    if chunk[0:4] != ps.MAGIC:
        return False, "DEVICE_MAGIC"
    if chunk[4] != ps.VERSION:
        return False, "DEVICE_VERSION"
    if not ps.DEVICE_HZ_MIN <= chunk[5] <= ps.DEVICE_HZ_MAX:
        return False, "DEVICE_HZ_RANGE"
    return True, None


def _bad(rule, idx=None, detail=""):
    return Verdict("INVALID", rule, idx, detail)


def _check_sidecar(side) -> Verdict | None:
    if side is None:
        return _bad("SIDECAR_MISSING", None, "no sidecar; asset/epoch binding unknown")
    if side.get("schema") != ps.SIDECAR_SCHEMA_ID:
        return _bad("SIDECAR_SCHEMA", None, f"schema={side.get('schema')!r}")
    for key, typ in (("hz", int), ("passage_start_sample", int), ("frame_count", int),
                     ("stream_sha256", str), ("epochs", list), ("asset", dict)):
        if not isinstance(side.get(key), typ) or isinstance(side.get(key), bool):
            return _bad("SIDECAR_FIELD", None, f"{key} missing or not {typ.__name__}")
    a = side["asset"]
    if not (isinstance(a.get("sha256"), str) and _HEX64.match(a["sha256"])):
        return _bad("ASSET_IDENTITY", None, "asset.sha256 must be 64 lowercase hex")
    for key in ("sample_rate", "sample_count", "channels"):
        v = a.get(key)
        if not isinstance(v, int) or isinstance(v, bool) or v <= 0:
            return _bad("ASSET_IDENTITY", None, f"asset.{key} must be a positive integer")
    if not ps.DEVICE_HZ_MIN <= side["hz"] <= ps.DEVICE_HZ_MAX:
        return _bad("SIDECAR_FIELD", None, f"sidecar hz={side['hz']} outside device range 30..240")
    if not 0 <= side["passage_start_sample"] < a["sample_count"]:
        return _bad("SIDECAR_FIELD", None, "passage_start_sample outside asset")
    ep = side["epochs"]
    if not ep or ep[0].get("first_frame") != 0:
        return _bad("EPOCHS", None, "epochs must start with first_frame 0")
    seen, prev = set(), -1
    for e in ep:
        eid, ff = e.get("epoch_id"), e.get("first_frame")
        if not isinstance(eid, str) or not eid or eid in seen:
            return _bad("EPOCHS", None, f"epoch_id {eid!r} empty or duplicated")
        if not isinstance(ff, int) or isinstance(ff, bool) or ff <= prev:
            return _bad("EPOCHS", None, f"epoch {eid} first_frame not strictly increasing")
        seen.add(eid)
        prev = ff
    if side.get("epoch_id") not in (None, ep[0]["epoch_id"]):
        return _bad("EPOCHS", None, "epoch_id must equal epochs[0].epoch_id")
    edge = side.get("edge_cues")
    if edge:
        targets = {c.get("edge") for c in edge}
        if targets - {"both"}:
            first = min((c.get("frame", 0) for c in edge if c.get("edge") != "both"), default=None)
            return Verdict("UNSUPPORTED", "EDGE_ADDRESSING_UNSUPPORTED", first,
                           f"edges {sorted(t for t in targets if t)} requested; PRSM v1 has no "
                           "edge field and FE firmware drives both edges from one stream")
    return None


def validate(data: bytes, side: dict | None) -> Verdict:
    v = _check_sidecar(side)
    if v is not None:
        return v
    hz = side["hz"]
    rate = side["asset"]["sample_rate"]
    count = side["asset"]["sample_count"]
    n_full, rem = divmod(len(data), ps.FRAME_LEN)
    epoch_starts = {e["first_frame"]: e for e in side["epochs"]}
    passage_us = ps.sample_to_us(side["passage_start_sample"], rate)
    asset_end_us = ps.sample_to_us(count, rate)  # first instant after the last sample
    warnings = []
    unconsumed_seen = set()
    prev_seq = prev_tick = None

    for k in range(n_full):
        chunk = data[k * ps.FRAME_LEN:(k + 1) * ps.FRAME_LEN]
        ok, rule = device_frame_verdict(chunk)
        if not ok:
            return _bad(rule, k, f"bytes[0:6]={chunk[:6].hex()}")
        f = ps.decode_frame(chunk)
        if f["hz"] != hz:
            return _bad("HZ_MISMATCH", k, f"frame hz={f['hz']} sidecar hz={hz}")
        t = f["t_us"]
        tick = ps.first_tick_at_or_after_us(t, hz)
        if ps.tick_time_us(tick, hz) != t:
            return _bad("T_US_OFF_GRID", k, f"t_us={t} is not a {hz} Hz tick time")
        if t < passage_us:
            return _bad("T_US_BEFORE_PASSAGE", k, f"t_us={t} < passage start {passage_us}")
        if t >= asset_end_us:
            return _bad("T_US_BEYOND_ASSET", k, f"t_us={t} >= asset end {asset_end_us}")
        if k == 0:
            want = ps.first_tick_at_or_after_us(passage_us, hz)
            if tick != want:
                return _bad("PASSAGE_START_TICK", k, f"first tick {tick} != first tick at/after "
                            f"passage start ({want})")
        boundary = k in epoch_starts
        if k > 0 and not boundary:
            if f["seq"] != (prev_seq + 1) & 0xFFFFFFFF:
                return _bad("SEQ_DISCONTINUITY", k, f"seq {prev_seq} -> {f['seq']} with no epoch "
                            "declared at this frame")
            if tick != prev_tick + 1:
                return _bad("T_US_NOT_NEXT_TICK", k, f"tick {prev_tick} -> {tick} with no epoch "
                            "declared at this frame")
        if boundary:
            want_seq = epoch_starts[k].get("seq_start")
            if want_seq is not None and f["seq"] != want_seq:
                return _bad("EPOCH_START_SEQ", k, f"seq {f['seq']} != declared seq_start {want_seq}")
        for i in (4, 5, 7):
            if f["prim8"][i]:
                unconsumed_seen.add(ps.PRIM8_NAMES[i])
        prev_seq, prev_tick = f["seq"], tick

    if rem:
        return _bad("TRUNCATED", n_full, f"{rem} trailing bytes (< {ps.FRAME_LEN})")
    if side["frame_count"] != n_full:
        return _bad("FRAME_COUNT", None, f"sidecar frame_count={side['frame_count']} file has {n_full}")
    if side["stream_sha256"] != ps.sha256_bytes(data):
        return _bad("STREAM_SHA256", None, "stream bytes do not match sidecar stream_sha256")
    for ep in side["epochs"]:
        if ep["first_frame"] >= n_full:
            return _bad("EPOCHS", None, f"epoch {ep['epoch_id']} starts past the last frame")
    if unconsumed_seen:
        warnings.append("non-zero Prim8 with no FE device consumer: " + ", ".join(sorted(unconsumed_seen)))
    return Verdict("VALID", frames=n_full, warnings=warnings)


def validate_files(bin_path, sidecar_path=None) -> Verdict:
    bin_path = Path(bin_path)
    data = bin_path.read_bytes()
    sp = Path(sidecar_path) if sidecar_path else Path(str(bin_path) + ".json")
    side = json.loads(sp.read_text(encoding="utf-8")) if sp.exists() else None
    return validate(data, side)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("stream")
    ap.add_argument("--sidecar")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args(argv)
    try:
        v = validate_files(a.stream, a.sidecar)
    except (OSError, json.JSONDecodeError, struct.error) as e:
        print(f"ERROR {type(e).__name__}: {e}", file=sys.stderr)
        return 3
    if v.ok:
        if not a.quiet:
            print(v.line() + f" sha256={ps.sha256_file(a.stream)}")
            for w in v.warnings:
                print("WARNING " + w)
        return 0
    print(v.line(), file=sys.stderr)
    return 2 if v.status == "UNSUPPORTED" else 1


if __name__ == "__main__":
    sys.exit(main())
