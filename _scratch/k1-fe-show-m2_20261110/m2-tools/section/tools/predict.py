#!/usr/bin/env python3
"""Write the M2-section prediction BEFORE the sectioned stream exists.

Edit: impact transform.beat_amp_u16 48000 -> 12000 inside ONE chorus segment only
(segment 4, "chorus", 45.68 s .. 60.81 s of the Loreen consumer contract).

Two independent predictions of the sectioned 120 Hz stream:
  P1 (from M2's own streams, made by M2's pipeline, not by this branch):
       frame i == M2 post-edit frame i   if t_i in [seg.start, seg.end)
       frame i == M2 pre-edit  frame i   otherwise
  P2 (from first principles, contract beats only):
       frames that change vs pre-edit = ticks t_i in [seg.start, seg.end) that fall inside
       [tb, tb + 40 ms) of a NON-downbeat beat tb (any tb, including one just before the
       segment whose pulse runs into it); only the impact channel (bytes 20..21) changes.
Both are written to prediction.json; P1's changed-frame set must equal P2's.
"""
import json, sys, hashlib
from pathlib import Path

M2 = Path("/Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/k1-fe-show-m2_20261110/m2-compose/projects/loreen")
OUT = Path(sys.argv[1])
SEG = 4
HZ = 120
FRAME = 34
IMPACT_OFF = 18 + 2 * 1  # prim8 index 1


def tick_us(i, hz=HZ):
    return (i * 1_000_000 + hz // 2) // hz


def sec_to_us(s):  # trinity_contract_adapter_v1.js secondsToUs
    return round(s * 1_000_000)


contract = json.loads((M2 / "inputs/contract.json").read_text())
seg = contract["structure"]["segments"][SEG]
assert seg["label"] == "chorus", seg
t0, t1 = sec_to_us(seg["start"]), sec_to_us(seg["end"])
pre = (M2 / "stream/loreen_pre_edit_120hz.prsm").read_bytes()
post = (M2 / "stream/loreen_post_edit_120hz.prsm").read_bytes()
assert len(pre) == len(post) and len(pre) % FRAME == 0
n = len(pre) // FRAME

# P1
p1_changed = []
for i in range(n):
    t = tick_us(i)
    a, b = pre[i * FRAME:(i + 1) * FRAME], post[i * FRAME:(i + 1) * FRAME]
    if t0 <= t < t1 and a != b:
        p1_changed.append(i)

# P2
beats = [sec_to_us(b) for b in contract["rhythm"]["beats"]]
down = set(sec_to_us(b) for b in contract["rhythm"]["downbeats"])
weak = [b for b in beats if b not in down]
p2_changed = []
for i in range(n):
    t = tick_us(i)
    if not (t0 <= t < t1):
        continue
    if any(tb <= t < tb + 40_000 for tb in weak):
        p2_changed.append(i)

# Pulses straddling a boundary (a cut through a sloped interval; see section_splice.js).
straddle = [tb for tb in beats if (tb < t0 < tb + 60_000) or (tb < t1 < tb + 60_000)]

pred = {
    "segment_index": SEG,
    "segment": seg,
    "span_us": [t0, t1],
    "frames_total": n,
    "frames_in_span": sum(1 for i in range(n) if t0 <= tick_us(i) < t1),
    "weak_beats_in_span": [tb for tb in weak if t0 <= tb < t1],
    "pulses_straddling_a_boundary_us": straddle,
    "P1_changed_frames": p1_changed,
    "P2_changed_frames": p2_changed,
    "P1_equals_P2": p1_changed == p2_changed,
    "rule": "frame i == post[i] if t_i in span else pre[i]; changed = P2 set; only bytes 20..21 (impact) differ",
    "pre_sha256": hashlib.sha256(pre).hexdigest(),
    "post_sha256": hashlib.sha256(post).hexdigest(),
}
# The expected stream bytes, built from M2's files only.
exp = bytearray()
for i in range(n):
    src = post if t0 <= tick_us(i) < t1 else pre
    exp += src[i * FRAME:(i + 1) * FRAME]
pred["expected_stream_sha256"] = hashlib.sha256(bytes(exp)).hexdigest()
OUT.write_text(json.dumps(pred, indent=1) + "\n")
print(json.dumps({k: v for k, v in pred.items() if not k.endswith("_frames")}, indent=1))
print("P1 changed", len(p1_changed), "P2 changed", len(p2_changed))
