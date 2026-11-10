#!/usr/bin/env python3
"""compare_wire_laneb — check captured PRISM playback.js wire bytes against lane-b prim8_stream.

full:  capture == RESYNC_PREAMBLE + b"".join(wire_packets(M2_STREAM)), every write 64 B; writes the
       de-guarded frames to <out>.prsm (must equal M2_STREAM) for audit_prsm_bytes.py --guard 30.
seek:  capture splits into epochs at RESYNC_PREAMBLE writes; each epoch == RESYNC_PREAMBLE +
       wire_packets(epoch frames); epoch 1 frames == M2_STREAM frames 0..k-1; epoch 2 frames carry
       M2's magic/version/hz/t_us/prim8 for ticks from the seek tick on, with seq continuing from k
       (playback.js keeps counting seq through a seek). Each epoch's frames go to <out>.eN.prsm.

Usage: compare_wire_laneb.py full|seek CAPTURE_PREFIX M2_STREAM OUT_PREFIX [SEEK_TICK]
"""
import hashlib
import json
import struct
import sys
from pathlib import Path

LANE_B = Path("/Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/k1-fe-show-m1_20261109/lane-b")
sys.path.insert(0, str(LANE_B))
import prim8_stream as ps  # noqa: E402


def sha(b):
    return hashlib.sha256(b).hexdigest()


def split_writes(prefix):
    wire = Path(prefix + ".bin").read_bytes()
    lens = json.loads(Path(prefix + ".json").read_text())["lens"]
    out, o = [], 0
    for n in lens:
        out.append(wire[o:o + n])
        o += n
    assert o == len(wire), "lengths do not cover capture"
    return wire, out


def main():
    mode, prefix, m2_path, out = sys.argv[1:5]
    m2 = Path(m2_path).read_bytes()
    wire, writes = split_writes(prefix)
    ok = True
    print(f"capture writes={len(writes)} bytes={len(wire)} sha256={sha(wire)}")
    print(f"write lengths: {sorted(set(map(len, writes)))}")
    print(f"M2 stream frames={len(m2) // 34} sha256={sha(m2)}")
    if any(len(w) != 64 for w in writes):
        print("FAIL a write is not 64 bytes"); ok = False
    if mode == "full":
        expect = ps.RESYNC_PREAMBLE + b"".join(ps.wire_packets(m2))
        print(f"lane-b expected wire bytes={len(expect)} sha256={sha(expect)}")
        same = wire == expect
        print(f"capture == RESYNC_PREAMBLE + wire_packets(M2): {same}")
        ok &= same
        same_writes = writes == [ps.RESYNC_PREAMBLE] + ps.wire_packets(m2)
        print(f"write boundaries == lane-b packet list: {same_writes}")
        ok &= same_writes
        frames = b"".join(w[ps.FRAME_GUARD_BYTES:] for w in writes[1:])
        Path(out + ".prsm").write_bytes(frames)
        print(f"de-guarded frames -> {out}.prsm sha256={sha(frames)} equals M2: {frames == m2}")
        ok &= frames == m2
    else:
        seek_tick = int(sys.argv[5])
        idx = [i for i, w in enumerate(writes) if w == ps.RESYNC_PREAMBLE]
        print(f"preamble write indices: {idx}")
        if idx[:1] != [0] or len(idx) != 2:
            print("FAIL expected exactly two preambles, the first at write 0"); ok = False
        epochs = [writes[a + 1:b] for a, b in zip(idx, idx[1:] + [len(writes)])]
        k = len(epochs[0])
        for n, ep in enumerate(epochs, 1):
            frames = b"".join(w[ps.FRAME_GUARD_BYTES:] for w in ep)
            rebuilt = ps.RESYNC_PREAMBLE + b"".join(ps.wire_packets(frames))
            seg = b"".join([ps.RESYNC_PREAMBLE] + ep)
            print(f"epoch {n}: frames={len(ep)} wire == RESYNC_PREAMBLE + wire_packets(frames): {seg == rebuilt}")
            ok &= seg == rebuilt
            Path(f"{out}.e{n}.prsm").write_bytes(frames)
        e1 = b"".join(w[ps.FRAME_GUARD_BYTES:] for w in epochs[0])
        print(f"epoch 1 frames == M2 frames 0..{k - 1}: {e1 == m2[:k * 34]}")
        ok &= e1 == m2[:k * 34]
        bad = 0
        for j, w in enumerate(epochs[1]):
            f = w[ps.FRAME_GUARD_BYTES:]
            ref = m2[(seek_tick + j) * 34:(seek_tick + j + 1) * 34]
            seq = struct.unpack_from("<I", f, 6)[0]
            if f[:6] != ref[:6] or f[10:] != ref[10:] or seq != k + j:
                bad += 1
        print(f"epoch 2 frames == M2 ticks {seek_tick}.. (seq continuing from {k}): {bad == 0} ({bad} mismatches)")
        ok &= bad == 0
    print("RESULT", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
