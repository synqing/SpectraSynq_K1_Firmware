#!/usr/bin/env python3
"""C4 on the resident source ed0aa984 (PROTOTYPE ADAPTER) with Lane B's bench wire format.

Bench-equivalent bytes: every frame is one 64-byte guarded packet (lane-b prim8_stream.wire_packets:
30 NUL + 34-byte frame), and RESYNC_PREAMBLE (64 B) precedes the first frame of the session and
of every seek epoch. The adapter delivers these bytes through the production check_serial() byte
loop, ahead of USBSerial, not through the USB peripheral itself.
Arrival model (unchanged): the bytes for a frame at original time T are consumed before hop
ceil((T - 75 s) / 7.5 ms) - 1. Record = {u32 hop, u32 len, u8 bytes[128]} (136 B), one per hop.
Rejected-input set (lead, 9 Nov): hz=0, hz=241, version=2. Bad magic is a finding, not a case.
"""
from __future__ import annotations

import copy
import hashlib
import json
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LANE = HERE.parent
sys.path.insert(0, str(LANE.parent / "lane-b"))
import prim8_stream as ps  # noqa: E402

EXPORT = LANE / "src-ed0aa984"
STREAM = LANE / "stream" / "loreen_75_155_120hz_v2.prsm"
HOP_US = 7500
P0_US = 75_000_000
REC_DATA = 128
SEEK_FWD_AT, SEEK_FWD_TO = 100_000_000, 110_000_000
SEEK_BACK_AT, SEEK_BACK_TO = 120_000_000, 105_000_000
STOP_AT = 125_000_000
BENCH_FLAGS = ["K1_AP_SUBSONIC_HPF_V1", "K1_TEMPO_CONSUMER_BANDS_V1", "K1_FX_BATTERY"]


def hop_for(t_us: int) -> int:
    return max(0, -(-(t_us - P0_US) // HOP_US) - 1)


def frames():
    data = STREAM.read_bytes()
    return [data[k:k + 34] for k in range(0, len(data), 34)]


def mutate(f: bytes, variant: str) -> bytes:
    b = bytearray(f)
    if variant == "hz0":
        b[5] = 0
    elif variant == "hz241":
        b[5] = 241
    elif variant == "ver2":
        b[4] = 2
    return bytes(b)


def by_hop(events):
    """events: (arrival_t_us, frame_bytes, new_epoch) -> {hop: bytes} with guard and preamble."""
    out: dict[int, bytearray] = {}
    for t, f, new_epoch in events:
        h = hop_for(t)
        buf = out.setdefault(h, bytearray())
        if new_epoch:
            buf += ps.RESYNC_PREAMBLE
        buf += ps.wire_packets(f)[0]
    return out


def pack(per_hop: dict) -> bytes:
    raw = bytearray()
    for h in sorted(per_hop):
        b = bytes(per_hop[h])
        if len(b) > REC_DATA:
            raise SystemExit(f"hop {h} carries {len(b)} bytes > {REC_DATA}")
        raw += struct.pack("<II", h, len(b)) + b + b"\0" * (REC_DATA - len(b))
    return bytes(raw)


def events(variant: str = "authored"):
    ev = []
    for k, f in enumerate(frames()):
        t = ps.decode_frame(f)["t_us"]
        ev.append((t, mutate(f, variant), k == 0))
    return ev


def seek_events():
    by_t = {ps.decode_frame(f)["t_us"]: f for f in frames()}
    ev, prev_epoch = [], None
    for t in sorted(by_t):
        if t < SEEK_FWD_AT:
            src, ep = t, 0
        elif t < SEEK_BACK_AT:
            src, ep = t + (SEEK_FWD_TO - SEEK_FWD_AT), 1
        else:
            src, ep = t - (SEEK_BACK_AT - SEEK_BACK_TO), 2
        f = by_t.get(ps.tick_time_us(ps.first_tick_at_or_after_us(src, 120), 120))
        if f is None:
            break
        ev.append((t, f, ep != prev_epoch))
        prev_epoch = ep
    return ev


def write(name, ev) -> dict:
    d = LANE / "emu" / "schedules_ed0"
    d.mkdir(parents=True, exist_ok=True)
    per_hop = by_hop(ev)
    raw = pack(per_hop)
    p = d / f"{name}.rx"
    p.write_bytes(raw)
    return {"schedule": str(p), "sha256": hashlib.sha256(raw).hexdigest(), "hops": len(per_hop),
            "frames": len(ev), "bytes": sum(len(v) for v in per_hop.values()),
            "max_bytes_per_hop": max(len(v) for v in per_hop.values())}


def main() -> int:
    sc = json.loads((EXPORT / "tools/esp_emulator/s3_music_regression.json").read_text())
    sc["name"] = "k1-fe-show-m1-c4-ed0aa984-prototype-adapter"
    sc["description"] = ("PROTOTYPE ADAPTER — not product tooling. Lane C-emu C4 on ed0aa984 with bench "
                         "audio/render flags; Lane B guarded packets + resync preamble.")
    sc["profile"]["adapter_flags"] += BENCH_FLAGS
    sc["assets"]["show_passage"] = {"kind": "concat", "qualification": "real_music",
        "segments": [{"asset": "loreen_src", "from_ms": 19000, "to_ms": 99000,
                      "label": "original 75.0-155.0 s (lane-a ASSET.json); transition 137.0 s = hop 8266"}],
        "origin": "lane-a passage inside loreen_src"}
    sc["assets"]["zero_passage"] = {"kind": "concat", "qualification": "diagnostic_composite",
        "segments": [{"zeros_ms": 80000, "label": "declared all-zero PCM, passage length"}],
        "origin": "live-leak control"}
    rec = {n: write(n, ev) for n, ev in (
        ("authored", events()), ("hz0", events("hz0")), ("hz241", events("hz241")), ("ver2", events("ver2")),
        ("seek", seek_events()), ("stop", [e for e in events() if e[0] < STOP_AT]))}
    stop_hop = hop_for(STOP_AT)
    every6 = {"start_hop": 0, "end_hop": None, "every": 6}
    dense = {"start_hop": stop_hop - 200, "end_hop": stop_hop + 1700, "every": 1}
    suite = ["smoke-a"]
    for mode, tag in ((32, "wfh"), (22, "snap")):
        comp = f"show_{tag}"
        sc["compositions"][comp] = {"commands": [f"set_mode={mode}", f"secondary_mode={mode}", "secondary_enabled=true"],
                                    "note": f"both edges mode {mode}"}

        def case(cid, purpose, rx=None, capture=every6, pcm="show_passage"):
            c = {"purpose": purpose, "pcm": pcm, "epoch": {"policy": "declared", "us": 1000000},
                 "partial_hop": "zero_pad", "composition": comp, "capture": capture}
            if rx:
                c["rx_stream"] = {"schedule": rec[rx]["schedule"], "sha256": rec[rx]["sha256"], "note": "PROTOTYPE ADAPTER"}
            sc["cases"][f"{tag}-{cid}"] = c
            suite.append(f"{tag}-{cid}")
        case("base", "Live baseline.")
        for k in (1, 2, 3):
            case(f"auth-{k}", f"Authored (guarded packets) repeat {k}.", "authored")
        for r in ("hz0", "hz241", "ver2"):
            case(f"rej-{r}", f"Every frame {r}; guarded packets; must equal live baseline.", r)
        case("auth-zeropcm", "Same authored stream over all-zero PCM (live-leak control).", "authored", pcm="zero_passage")
        if tag == "wfh":
            case("seek", "Seek fwd 100->110 s, back 120->105 s; preamble at each epoch; audio linear.", "seek")
            case("stop", "Stream stops at 125 s; dense capture.", "stop", dense)
            case("base-dense", "Live baseline, dense window.", capture=dense)
        sc["comparisons"] += [
            {"id": f"{tag}-auth-1-differs", "kind": "differs", "a": f"{tag}-base", "b": f"{tag}-auth-1", "criterion": "SW02", "label": "authored differs from live"},
            {"id": f"{tag}-auth-2-equal", "kind": "equal", "a": f"{tag}-auth-1", "b": f"{tag}-auth-2", "criterion": "SW02", "label": "repeat 1 == 2"},
            {"id": f"{tag}-auth-3-equal", "kind": "equal", "a": f"{tag}-auth-1", "b": f"{tag}-auth-3", "criterion": "SW02", "label": "repeat 1 == 3"}]
        for r in ("hz0", "hz241", "ver2"):
            sc["comparisons"].append({"id": f"{tag}-rej-{r}-equal", "kind": "equal", "a": f"{tag}-base", "b": f"{tag}-rej-{r}",
                                      "criterion": "SW03", "label": f"{r} equals live"})
    sc["suites"]["ed0"] = suite
    sc["host_checks"] = {"pytest": ["tests/test_esp_emulator_seams_static.py"], "builds": [],
                         "requires_git": sc.get("host_checks", {}).get("requires_git", [])}
    out = EXPORT / "tools/esp_emulator/c4_scenario_ed0.json"
    out.write_text(json.dumps(sc, indent=2) + "\n")
    (LANE / "emu" / "c4_scenario_ed0.json").write_text(out.read_text())
    (LANE / "emu" / "schedules_ed0" / "index.json").write_text(json.dumps(
        {"arrival_model": __doc__.strip(), "stop_hop": stop_hop, "schedules": rec}, indent=2) + "\n")
    print(json.dumps({"stop_hop": stop_hop, "suite": suite, "schedules": rec}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
