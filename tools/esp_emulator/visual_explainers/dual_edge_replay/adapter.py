#!/usr/bin/env python3
"""Immutable scene data for one accepted dual-edge emulator capture.

Reuses emu_capture.decode and player.case_audio. It does not parse UART itself,
recompute firmware, or drop a record to fit a frame rate.
"""

from __future__ import annotations

import base64
import hashlib
import json
import struct
import tempfile
import wave
from pathlib import Path

import emu_capture as ec
import player

RATE = player.RATE
HOP = player.HOP


class AdapterError(ValueError):
    pass


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _hop(side: ec.Sidecar) -> int:
    if side.processed % HOP != 0:
        raise AdapterError(f"processed samples {side.processed} are not a whole hop")
    hop = side.processed // HOP - 1
    if hop < 0:
        raise AdapterError(f"hop {hop} from processed {side.processed}")
    return hop


def load_accepted(run_dir: Path, case_id: str) -> tuple[dict, dict, ec.Capture, bytes]:
    run_dir = run_dir.resolve()
    result_path = run_dir / "result.json"
    if not result_path.is_file():
        raise AdapterError(f"missing {result_path}")
    result = json.loads(result_path.read_text())
    rec = (result.get("cases") or {}).get(case_id)
    if rec is None:
        raise AdapterError(f"case {case_id!r} is not in {result_path}")
    if rec.get("status") != "PASS":
        raise AdapterError(f"case {case_id!r} status is {rec.get('status')}; only an accepted capture is used")
    uart_path = run_dir / case_id / "uart.txt"
    if not uart_path.is_file():
        raise AdapterError(f"missing {uart_path}")
    try:
        cap = ec.decode(uart_path.read_text(errors="replace"))
    except ec.CaptureError as exc:
        raise AdapterError(f"decoder rejected the capture: {exc}") from exc
    with tempfile.TemporaryDirectory(prefix="dual-edge-audio-") as tmp:
        pcm, note = player.case_audio(run_dir, rec, Path(tmp), {})
    if pcm is None:
        raise AdapterError(f"matching audio is unavailable: {note}")
    want = (rec.get("pcm") or {}).get("sha256")
    got = _sha(pcm)
    if got != want:
        raise AdapterError(f"PCM sha256 {got} != recorded {want}")
    return result, rec, cap, pcm


def _records(cap: ec.Capture, rec: dict) -> list[dict]:
    header = cap.header
    try:
        px = int(header["px"])
        bpp = int(header["bpp"])
        edges = int(header["edges"])
    except (KeyError, ValueError) as exc:
        raise AdapterError(f"capture header is missing px/bpp/edges: {header}") from exc
    if bpp != 16 or edges != 2:
        raise AdapterError(f"header bpp/edges {bpp}/{edges} is not the dual 16-bit contract")
    wire_bytes = px * 6
    frames = sorted(cap.frames, key=lambda f: f.index)
    if not frames:
        raise AdapterError("capture has no frames")
    if len(frames) != len({f.index for f in frames}):
        raise AdapterError("duplicate frame index survived the decoder")
    rows = []
    for frame in frames:
        side = cap.sidecars.get(frame.index)
        if side is None:
            raise AdapterError(f"frame {frame.index} has no sidecar")
        if len(frame.A) != wire_bytes or len(frame.B) != wire_bytes:
            raise AdapterError(
                f"frame {frame.index} wire length {len(frame.A)}/{len(frame.B)} != {wire_bytes}"
            )
        meaning = cap.meanings.get(frame.index)
        rows.append({
            "index": frame.index,
            "ms": frame.ms,
            "mode": frame.mode,
            "hop": _hop(side),
            "generation": side.generation,
            "admitted": side.admitted,
            "processed": side.processed,
            "app_us": side.app_us,
            "limit_scale": side.limit_scale,
            "power_mw": side.power_mw,
            "A": frame.A,
            "B": frame.B,
            "meaning_index": None if meaning is None else meaning.index,
        })
    req = ((rec.get("requested") or {}).get("capture") or {})
    every = int(req.get("every") or 0)
    start = int(req.get("start_hop") if req.get("start_hop") is not None else rows[0]["hop"])
    end = req.get("end_hop")
    end = int(end) if end is not None else rows[-1]["hop"] + every
    if every < 1:
        raise AdapterError(f"capture every is {every}")
    expected = list(range(start, end, every))
    have = [row["hop"] for row in rows]
    missing = [h for h in expected if h not in set(have)]
    extra = [h for h in have if h not in set(expected)]
    if extra:
        raise AdapterError(f"hops outside the requested capture window: {extra[:8]}")
    if have != sorted(have):
        raise AdapterError("hop sequence is out of order")
    return rows, {
        "px": px,
        "bpp": bpp,
        "edges": edges,
        "header_every": header.get("every"),
        "header_fmt": header.get("fmt"),
        "header_crc32": header.get("crc32"),
        "capture_start_hop": start,
        "capture_end_hop": end,
        "capture_every": every,
        "missing_hops": missing,
        "frame_count": len(rows),
        "begin_count": cap.begin_count,
        "end_marker_count": cap.end_marker_count,
    }


def _pack(rows: list[dict], px: int) -> bytes:
    native = bytearray()
    for row in rows:
        for wire in (row["A"], row["B"]):
            for r, g, b in ec.wire_to_rgb16(wire):
                native += struct.pack("<HHH", r, g, b)
    expect = len(rows) * 2 * px * 6
    if len(native) != expect:
        raise AdapterError(f"native pack {len(native)} != {expect}")
    return bytes(native)


def scene_document(run_dir: Path, case_id: str) -> tuple[dict, bytes, dict]:
    """Return scene JSON (without the bulky base64 yet), the PCM, and a check record."""
    result, rec, cap, pcm = load_accepted(run_dir, case_id)
    rows, shape = _records(cap, rec)
    if len(pcm) % 2:
        raise AdapterError("PCM byte length is odd")
    samples = len(pcm) // 2
    if samples % RATE:
        raise AdapterError(f"{samples} samples is not a whole number of seconds at {RATE} Hz")
    native = _pack(rows, shape["px"])
    epochs = cap.epochs
    doc = {
        "schema": "k1-dual-edge-replay-scene/1",
        "case_id": case_id,
        "run_dir": str(run_dir.resolve()),
        "invocation_id": result.get("invocation_id"),
        "overall": result.get("overall"),
        "capture_source": result.get("source"),
        "px": shape["px"],
        "bpp": shape["bpp"],
        "edges": ["A", "B"],
        "edge_names": "logical channels; A is primary and B is secondary. Not physical top or bottom.",
        "rate_hz": RATE,
        "hop_samples": HOP,
        "clock": "hop_end",
        "audio_delta_s": 0,
        "audio_rule": "movie time t seconds is replay PCM sample round-trip t * rate_hz, with t = 0 at sample 0 of this case PCM. The recorded epoch is not an audio delay.",
        "sample_start": 0,
        "sample_end": samples,
        "duration_s": samples // RATE,
        "fps": 60,
        "projection": "round(c16 * 255 / 65535), same display projection as player.py. Not an optical model.",
        "header": {
            "every": shape["header_every"],
            "fmt": shape["header_fmt"],
            "crc32": shape["header_crc32"],
            "px": str(shape["px"]),
            "bpp": str(shape["bpp"]),
            "edges": str(shape["edges"]),
        },
        "capture": {
            "start_hop": shape["capture_start_hop"],
            "end_hop": shape["capture_end_hop"],
            "every": shape["capture_every"],
            "missing_hops": shape["missing_hops"],
            "frame_count": shape["frame_count"],
        },
        "epochs": epochs,
        "pcm": rec.get("pcm"),
        "hops": [row["hop"] for row in rows],
        "index": [row["index"] for row in rows],
        "generation": [row["generation"] for row in rows],
        "processed": [row["processed"] for row in rows],
        "app_us": [row["app_us"] for row in rows],
        "mode": [row["mode"] for row in rows],
        "limit_scale": [row["limit_scale"] for row in rows],
        "native_b64": base64.b64encode(native).decode("ascii"),
        "pcm_b64": base64.b64encode(pcm).decode("ascii"),
    }
    checks = {
        "native_sha256": _sha(native),
        "pcm_sha256": _sha(pcm),
        "pcm_samples": samples,
        "missing_hops": shape["missing_hops"],
        "frame_count": shape["frame_count"],
        "begin_count": shape["begin_count"],
        "end_marker_count": shape["end_marker_count"],
    }
    return doc, pcm, checks


def write_wav(pcm: bytes, path: Path, rate: int = RATE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(pcm)


def lookup_native(doc: dict, t: float) -> dict | None:
    """Latest captured row whose hop-end is at or before t, or None if none or a gap."""
    rate = int(doc["rate_hz"])
    hop_n = int(doc["hop_samples"])
    hops = doc["hops"]
    missing = set(doc["capture"]["missing_hops"])
    # Float64 is exact for these integers. 1e-9 samples keeps an exact boundary.
    limit = t * rate + 1e-9
    chosen = None
    for i, hop in enumerate(hops):
        if (hop + 1) * hop_n <= limit:
            chosen = i
        else:
            break
    if chosen is None:
        return None
    hop = hops[chosen]
    for lost in missing:
        if hop < lost and (lost + 1) * hop_n <= limit:
            return None
    native = base64.b64decode(doc["native_b64"])
    px = int(doc["px"])
    stride = 2 * px * 6
    blob = native[chosen * stride:(chosen + 1) * stride]
    if len(blob) != stride:
        raise AdapterError("native row is short")

    def pix(edge: int, i: int) -> tuple[int, int, int]:
        off = (edge * px + i) * 6
        return struct.unpack_from("<HHH", blob, off)

    return {
        "row": chosen,
        "hop": hop,
        "hop_end_sample": (hop + 1) * hop_n,
        "generation": doc["generation"][chosen],
        "mode": doc["mode"][chosen],
        "app_us": doc["app_us"][chosen],
        "A79": pix(0, 79),
        "A0": pix(0, 0),
        "A159": pix(0, px - 1),
        "B79": pix(1, 79),
        "B0": pix(1, 0),
        "B159": pix(1, px - 1),
    }


def boundary_agreement(run_dir: Path, case_id: str, doc: dict) -> list[dict]:
    """Re-decode the UART and compare native pixels at the zero and return boundaries."""
    _result, rec, cap, _pcm = load_accepted(run_dir, case_id)
    by_hop = {}
    for frame in cap.frames:
        side = cap.sidecars[frame.index]
        by_hop[_hop(side)] = frame
    times = [6.99, 7.0, 7.02, 9.99, 10.0, 10.02]
    rows = []
    for t in times:
        got = lookup_native(doc, t)
        if got is None:
            rows.append({"t": t, "agree": False, "reason": "scene has no row"})
            continue
        frame = by_hop[got["hop"]]
        a = ec.wire_to_rgb16(frame.A)
        b = ec.wire_to_rgb16(frame.B)
        expect = {
            "A79": a[79], "A0": a[0], "A159": a[159],
            "B79": b[79], "B0": b[0], "B159": b[159],
        }
        same = all(got[k] == expect[k] for k in expect)
        rows.append({"t": t, "hop": got["hop"], "agree": same, "scene": {k: got[k] for k in expect}})
    return rows
