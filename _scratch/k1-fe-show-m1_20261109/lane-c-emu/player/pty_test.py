#!/usr/bin/env python3
"""C5 pty test: run show_player against a pty pair and parse what arrives by the firmware's rules.

The reader is a Python port of audio/k1_prsm.cpp k1_prsm_scanner_push + k1_authored_map_prim8's hz
check (407fdf6f): hunt 'P','R','S','M'; on broken magic re-hunt with the same byte; fill 34 bytes;
reject version != 1; then reject hz outside 30..240. Bytes outside a frame are counted as
"would reach the hotkey path". Never opens a /dev/cu.* device.
Writes <out>/reader.json and <out>/stats.json (send error vs schedule from the player log).
"""
from __future__ import annotations

import json
import os
import select
import subprocess
import sys
import threading
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent


class Scanner:
    def __init__(self):
        self.buf = bytearray()
        self.ok, self.bad, self.hz_reject, self.stray = [], 0, 0, 0
        self.ignorable = 0          # NUL guard / preamble newline: no hotkey case exists for them

    def push(self, byte: int, now_ns: int):
        if not self.buf:
            if byte != ord("P"):
                if byte in (0, 10, 13):
                    self.ignorable += 1
                else:
                    self.stray += 1
                return
            self.buf.append(byte)
            return
        if len(self.buf) < 4:
            if byte != b"PRSM"[len(self.buf)]:
                self.buf.clear()
                return self.push(byte, now_ns)
            self.buf.append(byte)
            return
        self.buf.append(byte)
        if len(self.buf) < 34:
            return
        frame = bytes(self.buf)
        self.buf.clear()
        if frame[4] != 1:
            self.bad += 1
            return
        if not 30 <= frame[5] <= 240:
            self.hz_reject += 1
            return
        self.ok.append((now_ns, frame))


def main() -> int:
    out = Path(sys.argv[1])
    extra, injects, term_at = [], [], None
    it = iter(sys.argv[2:])
    for a in it:
        if a == "--inject":                       # --inject T_S=LINE : device-side line at T seconds
            t_s, line = next(it).split("=", 1)
            injects.append((float(t_s), line))
        elif a == "--inject-raw":                 # --inject-raw T_S=TEXT : device bytes with no newline
            t_s, line = next(it).split("=", 1)
            injects.append((float(t_s), "\x00RAW" + line))
        elif a == "--term-at":                    # harness sends SIGTERM to the player at S seconds
            term_at = float(next(it))
        else:
            extra.append(a)
    out.mkdir(parents=True, exist_ok=True)
    master, slave = os.openpty()
    name = os.ttyname(slave)
    sc = Scanner()
    stop = threading.Event()

    raw_rx = bytearray()

    def injector(t_start):
        for t_s, line in sorted(injects):
            while time.monotonic() < t_start + t_s and not stop.is_set():
                time.sleep(0.005)
            if line.startswith("\x00RAW"):
                os.write(master, line[4:].encode())
            else:
                os.write(master, (line + "\r\n").encode())

    def reader():
        while not stop.is_set():
            r, _, _ = select.select([master], [], [], 0.05)
            if r:
                try:
                    data = os.read(master, 4096)
                except OSError:
                    break
                now = time.monotonic_ns()
                raw_rx.extend(data)
                for b in data:
                    sc.push(b, now)

    th = threading.Thread(target=reader, daemon=True)
    th.start()
    log = out / "player.jsonl"
    cmd = [sys.executable, str(HERE / "show_player.py"), "--port", name, "--no-audio", "--log", str(log), *extra]
    proc = subprocess.Popen(cmd)
    if injects:
        threading.Thread(target=injector, args=(time.monotonic(),), daemon=True).start()
    if term_at is not None:
        def term():
            time.sleep(term_at)
            proc.send_signal(__import__("signal").SIGTERM)
        threading.Thread(target=term, daemon=True).start()
    rc = proc.wait()
    time.sleep(0.3)
    stop.set()
    th.join()
    recs = [json.loads(l) for l in log.read_text().splitlines()]
    fr = [r for r in recs if "idx" in r]
    stream = Path(extra[extra.index("--stream") + 1]).read_bytes()
    file_frames = {stream[k:k + 34] for k in range(0, len(stream), 34)}
    got = [f for _, f in sc.ok]
    seqs = [int.from_bytes(f[6:10], "little") for f in got]
    sent_seqs = [r["seq"] for r in fr]
    reader_rec = {"port": name, "frames_ok": len(got), "frames_bad_version": sc.bad, "frames_hz_reject": sc.hz_reject,
                  "stray_bytes_to_hotkey_path": sc.stray, "ignorable_nul_newline_bytes": sc.ignorable,
                  "partial_frame_bytes_at_end": len(sc.buf), "term_at_s": term_at,
                  "preambles_seen": bytes(raw_rx).count(b"\n" + b"\x00" * 63), "injected": injects, "all_frames_byte_identical_to_file": all(f in file_frames for f in got),
                  "seq_sequence_equals_sent": seqs == sent_seqs, "player_exit": rc}
    err = np.array([r["err_us"] for r in fr], dtype=float)
    write_us = np.array([r["done_us"] - r["send_us"] for r in fr], dtype=float)
    sched = np.array([r["sched_us"] for r in fr], dtype=float)
    send = np.array([r["send_us"] for r in fr], dtype=float)
    # arrival at the reader vs schedule (pty transport, coarse: reader wakes on select)
    t0_guess = None
    stats = {"frames": len(fr), "send_err_us": {"p50": float(np.percentile(err, 50)), "p95": float(np.percentile(err, 95)),
                                                 "p99": float(np.percentile(err, 99)), "max": float(err.max()), "min": float(err.min())},
             "write_call_us": {"p50": float(np.percentile(write_us, 50)), "p95": float(np.percentile(write_us, 95)), "max": float(write_us.max())},
             "cumulative_drift_us_end": float(np.mean(err[-120:]) - np.mean(err[:120])),
             "duration_s": float((send[-1] - send[0]) / 1e6) if len(send) else 0,
             "linear_fit_slope_ppm": float((np.polyfit(sched, send, 1)[0] - 1) * 1e6) if len(send) > 2 else None,
             "frames_skipped_late": next((r.get("frames_skipped_late") for r in recs if r.get("kind") == "footer"), None),
             "late_counts": {"over_4ms": int((err > 4000).sum()), "over_10ms": int((err > 10000).sum()),
                             "over_25ms": int((err > 25000).sum())},
             "reader": reader_rec}
    (out / "stats.json").write_text(json.dumps(stats, indent=2) + "\n")
    print(json.dumps(stats, indent=1))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
