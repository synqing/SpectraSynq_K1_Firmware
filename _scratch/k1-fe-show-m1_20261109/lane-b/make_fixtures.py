#!/usr/bin/env python3
"""Generate Lane B host-only fixtures (deterministic) and their hand-declared expectations.

Expectations in EXPECTED below were written from the contract rules and the firmware source
(k1_prsm.cpp / k1_authored_source.cpp at 407fdf6f) BEFORE the validator was run; they are not
derived from validator output.

Fixture asset identity is a declared TEST identity (sha256 of a fixed label string), not audio.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import prim8_stream as ps  # noqa: E402

OUT = HERE / "fixtures"
HZ = 120
RATE = 48000
PASSAGE = 1_440_017                      # 30.000354 s; deliberately off-grid
ASSET = {
    "sha256": ps.sha256_bytes(b"lane-b fixture asset identity - not audio"),
    "sample_rate": RATE,
    "sample_count": RATE * 600,          # 10 minutes
    "channels": 2,
    "path_hint": "FIXTURE ONLY - no audio file",
}
N = 24
T0 = ps.first_tick_at_or_after_us(ps.sample_to_us(PASSAGE, RATE), HZ)   # 3601
BASE = [30000, 0, 20000, 15000, 0, 0, 10000, 0]

# host: VALID | INVALID | UNSUPPORTED ; rule ; frame (None = stream-level)
# device_rejects: chunk indices the firmware's parse+map rejects; device_accepts: count of
# frames the byte scanner + authored layer accept.
EXPECTED = {
    "constant":                    ("VALID", None, None, [], 24),
    "ramp":                        ("VALID", None, None, [], 24),
    "single_impact":               ("VALID", None, None, [], 24),
    "simultaneous_top_bottom":     ("UNSUPPORTED", "EDGE_ADDRESSING_UNSUPPORTED", 10, [], 24),
    "silence_section":             ("VALID", None, None, [], 24),
    "invalid_hz_0":                ("INVALID", "DEVICE_HZ_RANGE", 5, [5], 23),
    "invalid_hz_241":              ("INVALID", "DEVICE_HZ_RANGE", 5, [5], 23),
    "bad_magic":                   ("INVALID", "DEVICE_MAGIC", 5, [5], 23),
    "bad_version":                 ("INVALID", "DEVICE_VERSION", 5, [5], 23),
    "truncated":                   ("INVALID", "TRUNCATED", 23, [], 23),
    "truncated_mid_stream":        ("INVALID", "DEVICE_MAGIC", 11, list(range(11, 23)), 11),
    "non_monotonic_t_us":          ("INVALID", "T_US_NOT_NEXT_TICK", 10, [], 24),
    "seq_discontinuity_undeclared": ("INVALID", "SEQ_DISCONTINUITY", 12, [], 24),
    "seq_gap_2_undeclared":        ("INVALID", "SEQ_DISCONTINUITY", 12, [], 24),
    "seq_discontinuity_declared":  ("VALID", None, None, [], 24),
    "backward_seek":               ("VALID", None, None, [], 24),
    "backward_seek_undeclared":    ("INVALID", "T_US_NOT_NEXT_TICK", 12, [], 24),
    "forward_seek":                ("VALID", None, None, [], 24),
    "epoch_change":                ("VALID", None, None, [], 24),
    "epoch_start_seq_wrong":       ("INVALID", "EPOCH_START_SEQ", 12, [], 24),
    "hz_mismatch":                 ("INVALID", "HZ_MISMATCH", 5, [], 24),
    "off_grid_t_us":               ("INVALID", "T_US_OFF_GRID", 7, [], 24),
    "beyond_asset":                ("INVALID", "T_US_BEYOND_ASSET", 12, [], 24),
    "before_passage":              ("INVALID", "T_US_BEFORE_PASSAGE", 0, [], 24),
    "stream_sha_mismatch":         ("INVALID", "STREAM_SHA256", None, [], 24),
    "missing_sidecar":             ("INVALID", "SIDECAR_MISSING", None, [], 24),
    "bad_asset_identity":          ("INVALID", "ASSET_IDENTITY", None, [], 24),
    "unconsumed_dims":             ("VALID", None, None, [], 24),
}


def frame(k, prim8=None, *, tick=None, seq=None, hz=HZ, version=1, magic=b"PRSM"):
    t = ps.tick_time_us(T0 + k if tick is None else tick, HZ)
    return ps.encode_frame(k if seq is None else seq, t, prim8 or BASE, hz,
                           version=version, magic=magic)


def plain(n=N, rows=None):
    return [frame(k, rows[k] if rows else None) for k in range(n)]


def write(name, frames, *, epochs=None, asset=None, sidecar_edit=None, raw=None, no_sidecar=False,
          note=""):
    data = raw if raw is not None else b"".join(frames)
    path = OUT / f"{name}.prsm"
    path.write_bytes(data)
    side = ps.make_sidecar(data if raw is None else b"".join(frames), asset=asset or ASSET,
                           passage_start_sample=PASSAGE, hz=HZ, epochs=epochs,
                           source={"generator": "lane-b/make_fixtures.py"}, notes=note or None)
    if raw is not None:
        # sidecar describes the intended (untruncated) stream; file on disk is damaged
        side["frame_count"] = len(frames)
    if sidecar_edit:
        sidecar_edit(side)
    sp = Path(str(path) + ".json")
    if no_sidecar:
        if sp.exists():
            sp.unlink()
    else:
        sp.write_text(json.dumps(side, indent=2) + "\n", encoding="utf-8")


def main():
    OUT.mkdir(exist_ok=True)
    write("constant", plain(), note="constant Prim8")
    write("ramp", plain(rows=[[min(65535, k * 2849), 0, 20000, 15000, 0, 0, 10000, 0]
                              for k in range(N)]), note="pressure ramp 0..65527")
    rows = [list(BASE) for _ in range(N)]
    rows[10][1] = rows[11][1] = 65535
    write("single_impact", plain(rows=rows), note="impact full-scale for 2 frames (10,11)")

    def edges(s):
        s["edge_cues"] = [{"frame": 10, "edge": "top", "prim8": "impact"},
                          {"frame": 10, "edge": "bottom", "prim8": "impact"}]
        s["edge_addressing"] = "REQUESTED per-edge (unsupported)"
    write("simultaneous_top_bottom", plain(rows=rows), sidecar_edit=edges,
          note="top and bottom impact at the same frame")

    rows = [list(BASE) for _ in range(N)]
    for k in range(8, 16):
        rows[k][0:3] = [0, 0, 0]
    write("silence_section", plain(rows=rows), note="frames 8..15 silence (Prim8[0..2]=0)")

    for name, hz in (("invalid_hz_0", 0), ("invalid_hz_241", 241)):
        fr = plain()
        fr[5] = frame(5, hz=hz)
        write(name, fr, note=f"frame 5 hz={hz}")
    fr = plain()
    fr[5] = frame(5, magic=b"PRSX")
    write("bad_magic", fr, note="frame 5 magic PRSX")
    fr = plain()
    fr[5] = frame(5, version=2)
    write("bad_version", fr, note="frame 5 version 2")
    fr = plain()
    write("truncated", fr, raw=b"".join(fr)[:23 * 34 + 20], note="last frame cut to 20 bytes")
    fr = plain()
    write("truncated_mid_stream", fr, raw=b"".join(fr[:10]) + fr[10][:20] + b"".join(fr[11:]),
          note="frame 10 cut to 20 bytes, stream continues with frames 11..23")

    fr = plain()
    fr[10] = frame(10, tick=T0 + 8)
    write("non_monotonic_t_us", fr, note="frame 10 t_us steps back two ticks; seq continuous")

    fr = [frame(k, seq=k if k < 12 else k + 9) for k in range(N)]
    write("seq_discontinuity_undeclared", fr, note="seq 11 -> 21 at frame 12, no epoch")
    fr = [frame(k, seq=k if k < 12 else k + 1) for k in range(N)]
    write("seq_gap_2_undeclared", fr, note="seq 11 -> 13 at frame 12 (device tolerates <=3)")
    fr = [frame(k, seq=k if k < 12 else k + 9) for k in range(N)]
    write("seq_discontinuity_declared", fr,
          epochs=[{"epoch_id": "e0", "first_frame": 0, "kind": "start"},
                  {"epoch_id": "e1", "first_frame": 12, "kind": "reconnect"}],
          note="seq jump declared as epoch e1")

    back = [frame(k, tick=(T0 + k) if k < 12 else (T0 + k - 10)) for k in range(N)]
    write("backward_seek", back,
          epochs=[{"epoch_id": "e0", "first_frame": 0, "kind": "start"},
                  {"epoch_id": "e1", "first_frame": 12, "kind": "seek_backward"}],
          note="10-tick (83 ms) backward seek at frame 12; seq continuous (PRISM playback.js seek style)")
    write("backward_seek_undeclared", back, note="same bytes as backward_seek, no epoch")
    fwd = [frame(k, tick=(T0 + k) if k < 12 else (T0 + k + 1200),
                 seq=k if k < 12 else k + 100) for k in range(N)]
    write("forward_seek", fwd,
          epochs=[{"epoch_id": "e0", "first_frame": 0, "kind": "start"},
                  {"epoch_id": "e1", "first_frame": 12, "kind": "seek_forward"}],
          note="10 s forward seek at frame 12; seq +100")
    rst = [frame(k, tick=(T0 + k) if k < 12 else (T0 + k - 12),
                 seq=k if k < 12 else k - 12) for k in range(N)]
    write("epoch_change", rst,
          epochs=[{"epoch_id": "e0", "first_frame": 0, "kind": "start"},
                  {"epoch_id": "e1", "first_frame": 12, "kind": "restart", "seq_start": 0}],
          note="restart from passage start, seq reset to 0")
    bad = [frame(k, tick=(T0 + k) if k < 12 else (T0 + k - 12),
                 seq=k if k < 12 else k - 7) for k in range(N)]
    write("epoch_start_seq_wrong", bad,
          epochs=[{"epoch_id": "e0", "first_frame": 0, "kind": "start"},
                  {"epoch_id": "e1", "first_frame": 12, "kind": "restart", "seq_start": 0}],
          note="declared seq_start 0 but frame 12 has seq 5")

    fr = plain()
    fr[5] = frame(5, hz=60)
    write("hz_mismatch", fr, note="frame 5 hz=60 (device-valid) vs sidecar 120")
    fr = plain()
    fr[7] = ps.encode_frame(7, ps.tick_time_us(T0 + 7, HZ) + 1, BASE, HZ)
    write("off_grid_t_us", fr, note="frame 7 t_us +1 us off the tick grid")
    short = dict(ASSET, sample_count=PASSAGE + 4800)
    write("beyond_asset", plain(), asset=short, note="asset ends 100 ms after passage start")
    write("before_passage", [frame(k, tick=T0 - 1 + k) for k in range(N)],
          note="stream starts one tick before the passage start")

    def wrong_sha(s):
        s["stream_sha256"] = "0" * 64
    write("stream_sha_mismatch", plain(), sidecar_edit=wrong_sha, note="sidecar sha wrong")
    write("missing_sidecar", plain(), no_sidecar=True)

    def bad_asset(s):
        s["asset"]["sha256"] = "abc"
    write("bad_asset_identity", plain(), sidecar_edit=bad_asset, note="asset sha256 malformed")
    write("unconsumed_dims", plain(rows=[[30000, 0, 20000, 15000, 9000, 9000, 10000, 9000]] * N),
          note="heat/space/gravity non-zero: no FE consumer (warning, still valid)")

    exp = {name: {"host": h, "rule": r, "frame": f, "device_rejects": dr, "device_accepts": da}
           for name, (h, r, f, dr, da) in EXPECTED.items()}
    (OUT / "expected.json").write_text(json.dumps(exp, indent=2) + "\n", encoding="utf-8")
    made = sorted(p.stem for p in OUT.glob("*.prsm"))
    assert made == sorted(EXPECTED), (set(made) ^ set(EXPECTED))
    print(f"wrote {len(made)} fixtures to {OUT}")


if __name__ == "__main__":
    main()
