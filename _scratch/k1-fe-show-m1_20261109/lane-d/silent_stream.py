"""Lane D: no-audio PRSM sender for the SILENT-ROOM T2 runs on bench K1 B489A500.

No audio is played (silent-room condition), so pacing is an absolute wall-clock
schedule (time.perf_counter; no cumulative drift by construction). Music runs use
Lane C-emu's audio-clocked player instead.

Safety (Lane B, lane-b/B-P1-contract.md): 64-byte RESYNC_PREAMBLE before the first
frame and every seek epoch; every frame is ONE 64-byte write (30 NUL guard + frame,
prim8_stream.wire_packets); a reader thread logs every device line and a watchdog
stops all writes on any line that is not an [AP] telemetry line (stop for >=5.5 s,
never sends Y/N/':'); the exact bytes are audited with audit_prsm_bytes.py --guard 30
before the port is opened. Port identity: USB serial B4:3A:45:A5:89:B4 only.

Usage:
  python3.13 silent_stream.py STREAM.prsm LOG.jsonl [--rejected hz0|ver2]
         [--seek AT_S:TO_S ...] [--stop-after-s S] [--start-delay-s S]
Exit codes: 0 ok · 2 refused before sending · 3 watchdog stop · 4 CRITICAL (NOISE_CAL: queued)
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import threading
import time
from pathlib import Path

import serial
from serial.tools import list_ports

HERE = Path(__file__).resolve().parent
LANE_B = HERE.parent / "lane-b"
sys.path.insert(0, str(LANE_B))
import prim8_stream as ps  # noqa: E402

sys.path.insert(0, str(HERE))
from units import UNITS, port_for, unit_name  # noqa: E402  (10 Nov: any registered unit; K1_UNIT=b489|rpl)

PY = "/opt/homebrew/opt/python@3.13/bin/python3.13"
ALLOWED_PREFIXES = ("[AP]",)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("stream")
    ap.add_argument("log")
    ap.add_argument("--rejected", choices=["hz0", "ver2"])
    ap.add_argument("--seek", action="append", default=[])
    ap.add_argument("--stop-after-s", type=float)
    ap.add_argument("--start-delay-s", type=float, default=0.0)
    a = ap.parse_args()

    raw = Path(a.stream).read_bytes()
    n = len(raw) // 34
    frames = [bytearray(raw[i * 34:(i + 1) * 34]) for i in range(n)]
    hz = frames[0][5]
    if a.rejected == "hz0":
        for f in frames:
            f[5] = 0
    elif a.rejected == "ver2":
        for f in frames:
            f[4] = 2
    sent_bytes = b"".join(bytes(f) for f in frames)
    log_path = Path(a.log)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = log_path.with_suffix(".sent.prsm")
    tmp.write_bytes(sent_bytes)
    audit = [PY, str(LANE_B / "audit_prsm_bytes.py"), "--guard", str(ps.FRAME_GUARD_BYTES), str(tmp)]
    if a.rejected:
        audit.insert(-1, "--allow-rejected-frames")
    au = subprocess.run(audit, capture_output=True, text=True)
    header = {
        "kind": "header", "stream": a.stream, "stream_sha256": ps.sha256_bytes(raw),
        "sent_sha256": ps.sha256_bytes(sent_bytes), "rejected": a.rejected, "hz": hz,
        "frames": n, "seek": a.seek, "stop_after_s": a.stop_after_s,
        "audit_rc": au.returncode, "audit_tail": au.stdout.strip().splitlines()[-1:] if au.stdout else [],
        "pacing": "absolute wall-clock perf_counter schedule (no audio)",
    }
    if au.returncode != 0:
        log_path.write_text(json.dumps(header) + "\n")
        print("REFUSED: byte audit failed", au.stdout[-400:], au.stderr[-400:])
        return 2

    unit = unit_name()
    PORT = port_for(unit)  # refuses unless exactly one port carries the unit's USB serial
    header["unit"] = {"name": unit, **UNITS[unit], "port": PORT}

    seeks = []
    for s in a.seek:
        at, to = (float(x) for x in s.split(":"))
        seeks.append((at, to))
    seeks.sort()

    stop_evt = threading.Event()
    incident = {"line": None, "critical": False, "mono": None}
    lines_out = []

    s = serial.Serial()
    s.port, s.baudrate, s.timeout, s.write_timeout = PORT, 115200, 0.05, 0.5
    s.dtr, s.rts = True, False
    s.open()

    armed = threading.Event()

    def reader():
        buf = b""
        clean = False  # becomes True at the first line boundary seen after arming
        while not stop_evt.is_set() or s.in_waiting:
            try:
                chunk = s.read(4096)
            except Exception as e:  # noqa: BLE001
                lines_out.append({"mono": time.monotonic(), "reader_error": str(e)})
                return
            if not chunk:
                if stop_evt.is_set():
                    return
                continue
            buf += chunk
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                t = line.decode("utf-8", "replace").strip()
                m = time.monotonic()
                lines_out.append({"mono": m, "line": t[:400], "armed": clean})
                if not armed.is_set():
                    continue
                if not clean:
                    clean = True  # this line may have started before arming: skip it ...
                    if "NOISE_CAL" in t and incident["line"] is None:  # ... unless it shows calibration activity
                        incident.update(line=t[:400], mono=m, critical="queued" in t)
                    continue
                if t and not t.startswith(ALLOWED_PREFIXES) and incident["line"] is None:
                    incident.update(line=t[:400], mono=m, critical=t.startswith("NOISE_CAL: queued"))

    th = threading.Thread(target=reader, daemon=True)
    th.start()
    recs = []
    t_start = None
    rc = 0
    try:
        time.sleep(0.3 + a.start_delay_s)
        armed.set()
        # wait for the first clean line boundary (the [AP] line prints at 1 Hz)
        t_arm = time.monotonic()
        while time.monotonic() - t_arm < 2.5:
            if any(x.get("armed") for x in lines_out):
                break
            time.sleep(0.01)
        mono_start = t_end_mono = time.monotonic()
        if incident["line"] is not None:  # calibration activity before we sent anything: never start
            rc = 4 if incident["critical"] else 3
            time.sleep(5.5)
            raise SystemExit(rc)
        s.write(ps.RESYNC_PREAMBLE)
        s.flush()
        t_start = time.perf_counter()
        mono_start = time.monotonic()
        idx = 0
        seek_i = 0
        epoch = 0
        tick = 0  # send-slot counter (absolute schedule)
        while idx < n:
            elapsed_sched = tick / hz
            if a.stop_after_s is not None and elapsed_sched >= a.stop_after_s:
                break
            if seek_i < len(seeks) and elapsed_sched >= seeks[seek_i][0]:
                idx = max(0, min(n - 1, int(round(seeks[seek_i][1] * hz))))
                seek_i += 1
                epoch += 1
                s.write(ps.RESYNC_PREAMBLE)
                recs.append({"kind": "epoch", "epoch": epoch, "slot": tick, "to_index": idx,
                             "mono": time.monotonic()})
            target = t_start + tick / hz
            while True:
                d = target - time.perf_counter()
                if d <= 0:
                    break
                time.sleep(min(d, 0.002) if d > 0.003 else 0)
            if incident["line"] is not None:
                rc = 4 if incident["critical"] else 3
                break
            pkt = b"\x00" * ps.FRAME_GUARD_BYTES + bytes(frames[idx])
            t_send = time.perf_counter()
            s.write(pkt)
            seq = int.from_bytes(frames[idx][6:10], "little")
            recs.append({"slot": tick, "idx": idx, "seq": seq, "sched_s": tick / hz,
                         "send_err_ms": round((t_send - target) * 1000, 3)})
            idx += 1
            tick += 1
        s.flush()
        t_end_mono = time.monotonic()
        if rc in (3, 4):
            time.sleep(5.5)  # let any armed noise calibration expire; never send Y
        else:
            time.sleep(0.6)  # observe recovery-window lines
    finally:
        stop_evt.set()
        th.join(timeout=2)
        s.close()
    errs = [r["send_err_ms"] for r in recs if "send_err_ms" in r]
    errs_sorted = sorted(errs)
    summary = {
        "kind": "summary", "rc": rc, "frames_sent": len(errs), "epochs": sum(1 for r in recs if r.get("kind") == "epoch"),
        "mono_start": mono_start if t_start else None, "mono_end": t_end_mono if t_start else None,
        "send_err_ms_p50": errs_sorted[len(errs) // 2] if errs else None,
        "send_err_ms_p95": errs_sorted[int(len(errs) * 0.95)] if errs else None,
        "send_err_ms_max": max(errs) if errs else None,
        "incident": incident, "device_lines": len(lines_out),
    }
    with log_path.open("w") as f:
        f.write(json.dumps(header) + "\n")
        for r in recs:
            f.write(json.dumps(r) + "\n")
        f.write(json.dumps(summary) + "\n")
    Path(str(log_path) + ".device.jsonl").write_text("\n".join(json.dumps(x) for x in lines_out) + "\n")
    print(json.dumps(summary))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
