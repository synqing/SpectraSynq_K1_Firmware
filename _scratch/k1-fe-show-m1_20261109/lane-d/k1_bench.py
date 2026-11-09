"""Lane D bench helper for K1-FE-SHOW-M1 Rev 2 (bench K1 B489A500 only).

Sub-commands (each opens the port, does one job, closes it):
  ident  OUTDIR            identity + settings read-back (:build, :chip_id, :dump)
  cmd    OUT LINE [WAIT_S] send ONE allow-listed command line, capture the reply
  arm    OUT SECONDS EVERY :rtrace_arm=SECONDS,EVERY (primary-edge LED capture)
  dump   OUT               :ap_stream=0, :rtrace_dump=1 until [RTRACE-END], :ap_stream=1;
                           then parse + CRC-verify the rgb8 dump into OUT.npz
  parse  RAW OUT           parse/verify an existing dump log

Safety: refuses any port whose USB serial number is not B489A500's
(B4:3A:45:A5:89:B4); refuses any line not on ALLOWED (never a bare byte, never a
hotkey); DTR asserted / RTS low as scripts/regression-harness/k1_device_identity_guard.py.
No flash, reset or erase. British English.
"""
from __future__ import annotations

import json
import re
import sys
import time
import zlib
from pathlib import Path

import numpy as np
import serial
from serial.tools import list_ports

EXPECT_USB = "B4:3A:45:A5:89:B4"
BAUD = 115200
# Exact lines this helper may send. set_mode persists (save_config_delayed,
# serial_cmd_handlers.cpp:1638) and is used only for the 32 setup / 22 restore.
ALLOWED = re.compile(
    r"^:(build|chip_id|dump|smart_status|rtrace_status=1|rtrace_dump=1|"
    r"rtrace_arm=\d{1,3},\d{1,3}|ap_stream=(0|1)|set_mode=(22|32))$"
)
BEGIN_RE = re.compile(r"^\[RTRACE-BEGIN\b(?P<body>[^\]]*)\]\s*$")
F_RE = re.compile(r"^F,(?P<idx>\d+),(?P<ms>\d+),(?P<mode>\d+),(?P<hex>[0-9a-fA-F]+)$")
EDGE_BYTES = 160 * 6  # firmware K1_RTRACE_EDGE_BYTES (CRC stride per frame)


def find_port(port: str) -> None:
    sn = {p.device: (p.serial_number or "") for p in list_ports.comports()}
    got = sn.get(port, "").upper()
    if got != EXPECT_USB:
        raise SystemExit(f"REFUSED: {port} USB serial {got!r} != {EXPECT_USB}")


def open_port(port: str) -> serial.Serial:
    find_port(port)
    s = serial.Serial()
    s.port, s.baudrate, s.timeout = port, BAUD, 0.2
    s.dtr, s.rts = True, False
    s.open()
    return s


def send(s: serial.Serial, line: str) -> float:
    if not ALLOWED.match(line):
        raise SystemExit(f"REFUSED line {line!r}: not on the allow-list")
    s.write((line + "\n").encode("ascii"))
    s.flush()
    return time.monotonic()


def capture(s: serial.Serial, seconds: float, until: str | None = None) -> bytes:
    buf = bytearray()
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        buf.extend(s.read(65536))
        if until and until.encode() in buf:
            # read a little more so the terminator line is complete
            buf.extend(s.read(4096))
            break
    return bytes(buf)


def stamp(f, text: str) -> None:
    f.write(f"# {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} mono={time.monotonic():.6f} {text}\n")


def cmd_lines(port: str, out: Path, lines: list[tuple[str, float]]) -> str:
    s = open_port(port)
    text_all = []
    try:
        time.sleep(0.4)
        s.read(65536)
        with out.open("a") as f:
            for line, wait in lines:
                stamp(f, f"SEND {line}")
                send(s, line)
                rep = capture(s, wait).decode("utf-8", "replace")
                f.write(rep)
                f.write("\n")
                text_all.append(rep)
    finally:
        s.close()
    return "\n".join(text_all)


def parse_dump(raw_path: Path, out_npz: Path) -> dict:
    begin = None
    frames, ms, mode, idxs = [], [], [], []
    seen: set[int] = set()
    rejected = 0
    saw_end = False
    for line in raw_path.read_text(errors="replace").splitlines():
        t = line.strip()
        bm = BEGIN_RE.match(t)
        if bm:
            begin = dict(kv.split("=", 1) for kv in bm.group("body").split() if "=" in kv)
            continue
        if t == "[RTRACE-END]":
            saw_end = True
            continue
        m = F_RE.match(t)
        if m and begin is not None and not saw_end:
            hexs = m.group("hex")
            px = int(begin.get("px", 160))
            idx = int(m.group("idx"))
            if len(hexs) != px * 6 or idx in seen:
                rejected += 1
                continue
            seen.add(idx)
            frames.append(np.frombuffer(bytes.fromhex(hexs), dtype=np.uint8).reshape(px, 3))
            ms.append(int(m.group("ms")))
            mode.append(int(m.group("mode")))
            idxs.append(idx)
    if begin is None:
        raise SystemExit("no [RTRACE-BEGIN] in dump")
    n_decl = int(begin.get("frames", 0))
    crc_decl = int(begin.get("crc32", "0"), 16)
    rec = bytearray()
    for fr in frames:
        b = fr.tobytes()
        rec.extend(b)
        rec.extend(b"\0" * (EDGE_BYTES - len(b)))
    crc_calc = zlib.crc32(rec) & 0xFFFFFFFF
    arr = np.stack(frames) if frames else np.zeros((0, 160, 3), np.uint8)
    np.savez_compressed(out_npz, rgb=arr, ms=np.array(ms, np.uint32), mode=np.array(mode, np.uint8),
                        idx=np.array(idxs, np.uint32))
    missing = sorted(set(range(n_decl)) - seen)
    summary = {
        "raw": str(raw_path), "npz": str(out_npz), "begin": begin,
        "frames_declared": n_decl, "frames_decoded": len(frames), "lines_rejected": rejected,
        "missing_indices": len(missing), "missing_first": missing[:10],
        "end_marker": saw_end, "crc_declared": f"{crc_decl:08x}", "crc_calculated": f"{crc_calc:08x}",
        "crc_ok": (crc_calc == crc_decl and len(frames) == n_decl and saw_end),
        "ms_first": ms[0] if ms else None, "ms_last": ms[-1] if ms else None,
        "modes": sorted(set(mode)),
        "mean_luma": float(arr.astype(np.float32).mean()) if len(frames) else None,
    }
    Path(str(out_npz) + ".json").write_text(json.dumps(summary, indent=1))
    return summary


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    sub = sys.argv[1]
    port = "/dev/cu.usbmodem11301"
    if sub == "ident":
        out = Path(sys.argv[2])
        out.mkdir(parents=True, exist_ok=True)
        t = cmd_lines(port, out / "ident.txt", [(":build", 1.5), (":chip_id", 1.5), (":dump", 3.0)])
        print("BUILD" in t, "B489A500" in t)
        return 0
    if sub == "cmd":
        out, line = Path(sys.argv[2]), sys.argv[3]
        wait = float(sys.argv[4]) if len(sys.argv) > 4 else 1.5
        print(cmd_lines(port, out, [(line, wait)])[-600:])
        return 0
    if sub == "arm":
        out, sec, every = Path(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
        t = cmd_lines(port, out, [(f":rtrace_arm={sec},{every}", 1.0)])
        ok = "[RTRACE] ARMED" in t
        print("ARMED" if ok else "ARM FAILED", t[-300:])
        return 0 if ok else 1
    if sub == "dump":
        out = Path(sys.argv[2])
        s = open_port(port)
        try:
            time.sleep(0.3)
            s.read(65536)
            send(s, ":ap_stream=0")
            capture(s, 1.0)
            with out.open("wb") as f:
                send(s, ":rtrace_dump=1")
                f.write(capture(s, 120.0, until="[RTRACE-END]"))
            first = parse_dump(out, out.with_suffix(".npz"))
            if not first["crc_ok"]:
                # capture is retained until the next arm: one re-dump
                out.rename(out.with_suffix(".attempt1.txt"))
                capture(s, 1.0)
                with out.open("wb") as f:
                    send(s, ":rtrace_dump=1")
                    f.write(capture(s, 120.0, until="[RTRACE-END]"))
            send(s, ":ap_stream=1")
            tail = capture(s, 1.0).decode("utf-8", "replace")
        finally:
            s.close()
        summ = parse_dump(out, out.with_suffix(".npz"))
        summ["ap_stream_restore_reply"] = "AP_STREAM: on" in tail or "AP_STREAM: true" in tail or tail[-200:]
        print(json.dumps(summ, indent=1))
        return 0 if summ["crc_ok"] else 3
    if sub == "parse":
        print(json.dumps(parse_dump(Path(sys.argv[2]), Path(sys.argv[3])), indent=1))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
