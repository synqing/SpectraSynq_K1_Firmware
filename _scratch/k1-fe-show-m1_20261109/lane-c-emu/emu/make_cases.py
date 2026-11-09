#!/usr/bin/env python3
"""C4 — build hop-tagged RX schedules and the C4 scenario (Lane C-emu, PROTOTYPE ADAPTER).

Arrival model (stated, not measured): a frame whose stream time is original-recording time T
is delivered with zero transport latency at T. Replay hop h covers original time
P0 + [h, h+1) * 7.5 ms (P0 = passage start in the original). The production loop runs
check_serial() for hop h at hop-end time P0 + (h+1)*7.5 ms, so the frame is consumed
before hop h = ceil((T - P0) / 7500 us) - 1, clamped to >= 0. Emulator timing is lockstep;
this is a coordinate model, never physical latency evidence.

Record = {u32 hop, u32 len, u8 bytes[40]} (emu_blob.RX_RECORD_BYTES = 48).
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

EXPORT = LANE / "src-407fdf6f"
import os
STREAM = LANE / "stream" / os.environ.get("C4_STREAM", "loreen_75_155_120hz.prsm")
SUFFIX = os.environ.get("C4_SUFFIX", "")
HOP_US = 7500
P0_US = 75_000_000          # passage start, original time
PASSAGE_MS_IN_EXCERPT = (19000, 99000)   # loreen_src excerpt starts at original 56.0 s
TOTAL_HOPS = -(-(80 * 12800) // 96)      # 10667 (final partial hop zero-padded)


def hop_for(t_us: int) -> int:
    return max(0, -(-(t_us - P0_US) // HOP_US) - 1)


def frames():
    data = STREAM.read_bytes()
    return [data[k:k + 34] for k in range(0, len(data), 34)]


def pack(entries) -> bytes:
    out = bytearray()
    last = 0
    for hop, b in entries:
        assert hop >= last and len(b) <= 40
        last = hop
        out += struct.pack("<II", hop, len(b)) + b + b"\0" * (40 - len(b))
    return bytes(out)


def schedule(variant: str):
    fr = frames()
    ent = []
    for f in fr:
        d = ps.decode_frame(f)
        t = d["t_us"]
        b = bytearray(f)
        if variant == "hz0":
            b[5] = 0
        elif variant == "ver2":
            b[4] = 2
        elif variant == "magic":
            b[3] = ord("X")                  # 'PRSX' — same corruption as lane-b fixtures/bad_magic.prsm
        ent.append((hop_for(t), bytes(b), d))
    return ent


SEEK_FWD_AT = 100_000_000   # original 100 s: jump the stream forward to 110 s
SEEK_FWD_TO = 110_000_000
SEEK_BACK_AT = 120_000_000  # original 120 s: jump the stream back to 105 s
SEEK_BACK_TO = 105_000_000
STOP_AT = 125_000_000       # original 125 s: last frame sent before this time, then nothing


def seek_entries():
    """Stream timeline jumps while the audio continues linearly (device-level seek: seq jump)."""
    by_t = {ps.decode_frame(f)["t_us"]: f for f in frames()}
    ts = sorted(by_t)
    ent = []
    for t in ts:                       # t = arrival (wall) time on the original axis
        if t < SEEK_FWD_AT:
            src = t
        elif t < SEEK_BACK_AT:
            src = t + (SEEK_FWD_TO - SEEK_FWD_AT)
        else:
            src = t - (SEEK_BACK_AT - SEEK_BACK_TO)
        # nearest stream tick at or after the content time
        i = ps.first_tick_at_or_after_us(src, 120)
        content = by_t.get(ps.tick_time_us(i, 120))
        if content is None:
            break
        ent.append((hop_for(t), content, None))
    return ent


def stop_entries():
    return [(h, b, d) for h, b, d in schedule("authored") if d["t_us"] < STOP_AT]


def write_sched(name: str, ent) -> dict:
    d = LANE / "emu" / "schedules"
    d.mkdir(parents=True, exist_ok=True)
    raw = pack([(h, b) for h, b, _ in ent])
    p = d / f"{name}{SUFFIX}.rx"
    if not p.exists() or p.read_bytes() != raw:
        p.write_bytes(raw)
    per_hop = {}
    for h, _, _ in ent:
        per_hop[h] = per_hop.get(h, 0) + 1
    return {"schedule": str(p), "sha256": hashlib.sha256(raw).hexdigest(), "records": len(ent),
            "max_frames_per_hop": max(per_hop.values()), "first_hop": ent[0][0], "last_hop": ent[-1][0]}


def main() -> int:
    base = json.loads((EXPORT / "tools/esp_emulator/s3_music_regression.json").read_text())
    sc = copy.deepcopy(base)
    sc["name"] = "k1-fe-show-m1-c4-prototype-adapter"
    sc["description"] = ("PROTOTYPE ADAPTER — not product tooling. Lane C-emu C4: prepared Prim8 (PRSM) bytes "
                         "delivered into the production check_serial() at declared replay hops.")
    sc["assets"]["show_passage"] = {
        "kind": "concat", "qualification": "real_music",
        "segments": [{"asset": "loreen_src", "from_ms": PASSAGE_MS_IN_EXCERPT[0], "to_ms": PASSAGE_MS_IN_EXCERPT[1],
                      "label": "original 75.0-155.0 s (lane-a ASSET.json passage; transition 137.0 s = hop 8266)"}],
        "origin": "lane-a ASSET.json passage inside the maintained loreen_src excerpt (ffmpeg mono mean, 12800 Hz, peak 4096)."}
    rec = {}
    for name, ent in (("authored", schedule("authored")), ("hz0", schedule("hz0")), ("ver2", schedule("ver2")),
                      ("magic", schedule("magic")), ("seek", seek_entries()), ("stop", stop_entries()),
                      ("probe", [e for e in schedule("authored") if e[0] < 1300])):
        rec[name] = write_sched(name, ent)
    every6 = {"start_hop": 0, "end_hop": None, "every": 6}
    stop_hop = hop_for(STOP_AT)
    dense = {"start_hop": stop_hop - 200, "end_hop": stop_hop + 1700, "every": 1}
    cases = {}
    for mode, tag in ((32, "wfh"), (22, "snap")):
        comp = f"show_{tag}"
        sc["compositions"][comp] = {"commands": [f"set_mode={mode}", f"secondary_mode={mode}", "secondary_enabled=true"],
                                    "note": f"both edges mode {mode}"}

        def case(cid, purpose, rx=None, capture=every6):
            c = {"purpose": purpose, "pcm": "show_passage", "epoch": {"policy": "declared", "us": 1000000},
                 "partial_hop": "zero_pad", "composition": comp, "capture": capture}
            if rx:
                c["rx_stream"] = {"schedule": rec[rx]["schedule"], "sha256": rec[rx]["sha256"],
                                  "note": "PROTOTYPE ADAPTER"}
            sc["cases"][f"{tag}-{cid}"] = c
            cases.setdefault(tag, []).append(f"{tag}-{cid}")
        case("base", "Live baseline: passage PCM, no RX bytes.")
        for k in (1, 2, 3):
            case(f"auth-{k}", f"Authored stream repeat {k}.", "authored")
        case("rej-hz0", "Every frame hz=0 (device rejects in k1_authored_map_prim8).", "hz0")
        case("rej-ver2", "Every frame version=2 (scanner consumes 34 bytes, parse rejects).", "ver2")
        case("rej-magic", "Every frame magic 'PRSX' (scanner rejects magic; remaining bytes reach the hotkey/command path).", "magic")
        sc["assets"].setdefault("zero_passage", {"kind": "concat", "qualification": "diagnostic_composite",
            "segments": [{"zeros_ms": 80000, "label": "declared all-zero PCM, same length as the passage"}],
            "origin": "live-leak control: authored stream over silent input"})
        c_leak = {"purpose": "Live-leak control: the same authored stream over all-zero PCM. Equal to auth-1 = no live "
                             "audio reaches the authored output; different = live input leaks.",
                  "pcm": "zero_passage", "epoch": {"policy": "declared", "us": 1000000}, "partial_hop": "zero_pad",
                  "composition": comp, "capture": every6,
                  "rx_stream": {"schedule": rec["authored"]["schedule"], "sha256": rec["authored"]["sha256"]}}
        sc["cases"][f"{tag}-auth-zeropcm"] = c_leak
        if tag == "wfh":
            case("seek", "Stream seq jumps forward at 100 s (to 110 s) and back at 120 s (to 105 s); audio linear.", "seek")
            case("stop", "Stream stops at 125 s; dense capture across the stop.", "stop", dense)
            case("base-dense", "Live baseline with the stop case's dense window.", capture=dense)
        comps = [("auth-1", "differs", "authored output differs from live baseline"),
                 ("auth-2", "equal", "repeat 1 == repeat 2"), ("auth-3", "equal", "repeat 1 == repeat 3")]
        for cid, kind, label in comps:
            a = f"{tag}-base" if cid == "auth-1" else f"{tag}-auth-1"
            sc["comparisons"].append({"id": f"{tag}-{cid}-{kind}", "kind": kind, "a": a, "b": f"{tag}-{cid}",
                                      "criterion": "SW02", "label": label})
        for r in ("rej-hz0", "rej-ver2", "rej-magic"):
            sc["comparisons"].append({"id": f"{tag}-{r}-equal", "kind": "equal", "a": f"{tag}-base", "b": f"{tag}-{r}",
                                      "criterion": "SW03", "label": f"{r} output equals live baseline"})
    sc["assets"]["probe_passage"] = {"kind": "concat", "qualification": "real_music",
        "segments": [{"asset": "loreen_src", "from_ms": 19000, "to_ms": 29000, "label": "original 75.0-85.0 s"}],
        "origin": "adapter probe: first 10 s of the passage"}
    for tag, rx in (("probe-base", None), ("probe-auth", "probe")):
        c = {"purpose": "adapter probe", "pcm": "probe_passage", "epoch": {"policy": "declared", "us": 1000000},
             "partial_hop": "zero_pad", "composition": "show_wfh", "capture": {"start_hop": 0, "end_hop": None, "every": 4}}
        if rx:
            c["rx_stream"] = {"schedule": rec[rx]["schedule"], "sha256": rec[rx]["sha256"]}
        sc["cases"][tag] = c
    sc["suites"] = {"default": ["smoke-a"], "probe": ["probe-base", "probe-auth"], "wfh": ["smoke-a", "smoke-b"] + cases["wfh"], "snap": ["wfh-auth-zeropcm", "snap-auth-zeropcm"] + cases["snap"]}
    sc["host_checks"] = {"pytest": ["tests/test_esp_emulator_seams_static.py"], "builds": [],
                         "requires_git": base.get("host_checks", {}).get("requires_git", [])}
    sc["suites"]["v2"] = ["smoke-a", "wfh-base", "wfh-auth-1", "wfh-auth-2", "wfh-auth-3", "wfh-rej-hz0", "wfh-rej-ver2",
                          "wfh-seek", "wfh-stop", "wfh-base-dense", "wfh-auth-zeropcm", "snap-base", "snap-auth-1"]
    out = LANE / "emu" / f"c4_scenario{SUFFIX}.json"
    out.write_text(json.dumps(sc, indent=2) + "\n")
    (LANE / "emu" / "schedules" / f"index{SUFFIX}.json").write_text(json.dumps(
        {"arrival_model": __doc__.strip(), "stop_hop": stop_hop, "schedules": rec}, indent=2) + "\n")
    print(json.dumps({"stop_hop": stop_hop, "schedules": rec}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
