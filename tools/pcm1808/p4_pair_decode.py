#!/usr/bin/env python3
"""Decode a post-epoch [PCMPAIR] dump into PCM / MIC / hop arrays.

Stdlib only. Hex is parsed after the epoch has already been frozen on device;
this file never talks to serial.
"""

from __future__ import annotations

import argparse
import json
import re
import struct
import zlib
from pathlib import Path


BEGIN = re.compile(
    r"\[PCMPAIR-BEGIN\] epoch_valid=(\d+) fill_ok=(\d+) ovf_epoch=(\d+) "
    r"ring_drop_epoch=(\d+) mic_err_epoch=(\d+) dur_us=(\-?\d+) "
    r"pcm_frames=(\d+) mic_samples=(\d+) hop_n=(\d+) "
    r"hop_mean=(\d+) hop_p95=(\d+) hop_p99=(\d+) hop_max=(\d+) "
    r"cap_read_us=(\d+) slot0=RIGHT slot1=LEFT ap_source=im69d "
    r"mic_only=(\d+) fixture=(\S+)"
)
PCM_HDR = re.compile(r"\[PCMPAIR-PCM bytes=(\d+) crc32=([0-9a-f]{8})", re.I)
MIC_HDR = re.compile(r"\[PCMPAIR-MIC bytes=(\d+) crc32=([0-9a-f]{8})", re.I)
HOP_HDR = re.compile(r"\[PCMPAIR-HOP bytes=(\d+) n=(\d+)")


def _hex_section(text: str, start_tag: str, end_tag: str) -> bytes:
    a = text.find(start_tag)
    b = text.find(end_tag)
    if a < 0 or b < 0 or b <= a:
        raise SystemExit(f"missing section {start_tag} .. {end_tag}")
    body = text[a:b].split("\n", 1)[-1].replace("\r", "")
    hex_body = "".join(re.findall(r"^[0-9a-f]+$", body, re.M | re.I))
    return bytes.fromhex(hex_body) if hex_body else b""


def _s24_stereo(raw: bytes) -> tuple[list[int], list[int]]:
    if len(raw) % 6:
        raise SystemExit(f"PCM length {len(raw)} is not a multiple of 6")
    s0: list[int] = []
    s1: list[int] = []
    for i in range(0, len(raw), 6):
        u0 = raw[i] | (raw[i + 1] << 8) | (raw[i + 2] << 16)
        u1 = raw[i + 3] | (raw[i + 4] << 8) | (raw[i + 5] << 16)
        if u0 & 0x800000:
            u0 -= 0x1000000
        if u1 & 0x800000:
            u1 -= 0x1000000
        s0.append(u0)
        s1.append(u1)
    return s0, s1


def decode_text(text: str) -> dict:
    m = BEGIN.search(text)
    if not m:
        raise SystemExit("no [PCMPAIR-BEGIN] header")
    if "[PCMPAIR-END]" not in text:
        raise SystemExit("no [PCMPAIR-END]")
    if "DUMP REFUSED" in text:
        raise SystemExit("dump refused: epoch was still armed")
    pcm_raw = _hex_section(text, "[PCMPAIR-PCM ", "[PCMPAIR-PCM-END]")
    mic_raw = _hex_section(text, "[PCMPAIR-MIC ", "[PCMPAIR-MIC-END]")
    hop_raw = _hex_section(text, "[PCMPAIR-HOP ", "[PCMPAIR-HOP-END]")
    pcm_h = PCM_HDR.search(text)
    mic_h = MIC_HDR.search(text)
    hop_h = HOP_HDR.search(text)
    if not (pcm_h and mic_h and hop_h):
        raise SystemExit("missing PCMPAIR section headers")
    pcm_bytes, pcm_crc = int(pcm_h.group(1)), int(pcm_h.group(2), 16)
    mic_bytes, mic_crc = int(mic_h.group(1)), int(mic_h.group(2), 16)
    hop_bytes, hop_n = int(hop_h.group(1)), int(hop_h.group(2))
    if len(pcm_raw) != pcm_bytes:
        raise SystemExit(f"PCM length header={pcm_bytes} decoded={len(pcm_raw)}")
    if len(mic_raw) != mic_bytes:
        raise SystemExit(f"MIC length header={mic_bytes} decoded={len(mic_raw)}")
    if len(hop_raw) != hop_bytes:
        raise SystemExit(f"HOP length header={hop_bytes} decoded={len(hop_raw)}")
    slot0, slot1 = _s24_stereo(pcm_raw) if pcm_raw else ([], [])
    mic = list(struct.unpack("<" + "h" * (len(mic_raw) // 2), mic_raw)) if mic_raw else []
    hops = list(struct.unpack("<" + "H" * (len(hop_raw) // 2), hop_raw)) if hop_raw else []
    fill_ok = int(m.group(2)) == 1
    ovf_epoch = int(m.group(3))
    drop_epoch = int(m.group(4))
    mic_err_epoch = int(m.group(5))
    return {
        "epoch_valid": int(m.group(1)) == 1,
        "fill_ok": fill_ok,
        "ovf_epoch": ovf_epoch,
        "ring_drop_epoch": drop_epoch,
        "mic_err_epoch": mic_err_epoch,
        "dur_us": int(m.group(6)),
        "pcm_frames": int(m.group(7)),
        "mic_samples": int(m.group(8)),
        "hop_n": int(m.group(9)),
        "hop_mean": int(m.group(10)),
        "hop_p95": int(m.group(11)),
        "hop_p99": int(m.group(12)),
        "hop_max": int(m.group(13)),
        "cap_read_us": int(m.group(14)),
        "mic_only": int(m.group(15)) == 1,
        "fixture": m.group(16).strip(),
        "ap_source": "im69d",
        "slot0_physical": "RIGHT",
        "slot1_physical": "LEFT",
        "pcm_crc_ok": (zlib.crc32(pcm_raw) & 0xFFFFFFFF) == pcm_crc,
        "mic_crc_ok": (zlib.crc32(mic_raw) & 0xFFFFFFFF) == mic_crc,
        "hop_n_decoded": hop_n,
        "slot0": slot0,
        "slot1": slot1,
        "physical_right": slot0,
        "physical_left": slot1,
        "mic": mic,
        "hops_us": hops,
        "clean": fill_ok
        and ovf_epoch == 0
        and drop_epoch == 0
        and mic_err_epoch == 0
        and (zlib.crc32(pcm_raw) & 0xFFFFFFFF) == pcm_crc
        and (zlib.crc32(mic_raw) & 0xFFFFFFFF) == mic_crc,
    }


def rms(x: list[int]) -> float:
    if not x:
        return 0.0
    return (sum(float(v) * float(v) for v in x) / float(len(x))) ** 0.5


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("log")
    ap.add_argument("--json", default="")
    args = ap.parse_args()
    d = decode_text(Path(args.log).read_text(errors="replace"))
    summary = {k: d[k] for k in d if k not in ("slot0", "slot1", "physical_right", "physical_left", "mic", "hops_us")}
    summary["pcm_rms_slot0"] = rms(d["slot0"])
    summary["pcm_rms_slot1"] = rms(d["slot1"])
    summary["mic_rms"] = rms(d["mic"])
    print(json.dumps(summary, indent=2))
    if args.json:
        Path(args.json).write_text(json.dumps(summary, indent=2) + "\n")
    return 0 if d["clean"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
