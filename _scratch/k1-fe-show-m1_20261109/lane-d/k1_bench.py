"""Lane D bench helper (K1-FE-SHOW), any registered bench unit (lane-d/units.py).

Set K1_UNIT=b489|rpl. The port is found from the unit's USB serial number (never assumed).

Sub-commands (each opens the port, does one job, closes it):
  ident  OUTDIR            identity + settings read-back (:build, :chip_id, :dump)
  cmd    OUT LINE [WAIT_S] send ONE allow-listed command line, capture the reply
  arm    OUT SECONDS EVERY :rtrace_arm=SECONDS,EVERY (needs a build with K1_RENDER_TRACE_V1)
  dump   OUT               :ap_stream=0, :rtrace_dump=1 until [RTRACE-END] (one re-dump on CRC
                           failure), :ap_stream=1; then parse + CRC-verify into OUT.npz
  parse  RAW OUT           parse/verify an existing dump log (no device needed, no K1_UNIT needed)
  unlock OUT               after a prepared stream (firmware >= a6bad318): wait for >= 200 ms of
                           silence, send ':prsm_exit', require 'PRSM_SESSION: interactive', then
                           read ':authored_status'. Exit 1 if the session did not unlock.

a6bad318 receiver (10 Nov 2026): once binary traffic is seen, hotkeys and ':' commands stay off
until the exact line ':prsm_exit' arrives after 200 ms of silence. The prepared-frame records
([RTRACE-PREPARED-BEGIN]..[RTRACE-PREPARED-END], P-lines) follow [RTRACE-END]; dump keeps them.

Dump formats (visual/k1_render_trace.cpp): rgb8hex (6 hex/px) or rgb16hex (12 hex/px, R16 G16 B16
big-endian); one edge per line, or two when the BEGIN line says edges=2. CRC = zlib/esp crc32 over
each stored edge slot padded to 160 px x 6 bytes; rgb16 slots are the packed wire order G,R,B.

Safety: refuses any port whose USB serial is not the named unit's; refuses any line not on ALLOWED
(never a bare byte, never a hotkey); DTR asserted / RTS low (k1_device_identity_guard convention).
No flash, reset or erase. British English. Updated 10 Nov 2026 for the Main RPL (unit swap).
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from units import UNITS, port_for, unit_name  # noqa: E402

BAUD = 115200
# Exact lines this helper may send. set_mode persists (save_config_delayed,
# serial_cmd_handlers.cpp:1638): used only to set a test mode and to restore the resident one.
ALLOWED = re.compile(
    r"^:(build|chip_id|dump|smart_status|rtrace_status=1|rtrace_dump=1|"
    r"rtrace_arm=\d{1,3},\d{1,3}|ap_stream=(0|1)|set_mode=(18|22|32)|prsm_exit|authored_status|"
    r"k1_afe=(on|off|true|false|status)|k1_afe_gamma=[0-2](\.\d{1,2})?|k1_afe_floor=[01](\.\d{1,2})?|"
    r"k1_afe_silence=(on|off|true|false))$"  # AFE2 stage 2 switch (11 Nov 2026), RAM only
)
BEGIN_RE = re.compile(r"^\[RTRACE-BEGIN\b(?P<body>[^\]]*)\]\s*$")
F_RE = re.compile(r"^F,(?P<idx>\d+),(?P<ms>\d+),(?P<mode>\d+),(?P<hex>[0-9a-fA-F]+)(?:,(?P<hex2>[0-9a-fA-F]+))?$")
EDGE_BYTES = 160 * 6  # firmware K1_RTRACE_EDGE_BYTES (CRC stride per edge slot)


def open_port() -> tuple[serial.Serial, str]:
    unit = unit_name()
    port = port_for(unit)
    s = serial.Serial()
    s.port, s.baudrate, s.timeout = port, BAUD, 0.2
    s.dtr, s.rts = True, False
    s.open()
    return s, unit


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
            buf.extend(s.read(4096))
            break
    return bytes(buf)


def stamp(f, text: str) -> None:
    f.write(f"# {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} mono={time.monotonic():.6f} {text}\n")


def cmd_lines(out: Path, lines: list[tuple[str, float]]) -> str:
    s, unit = open_port()
    text_all = []
    try:
        time.sleep(0.4)
        s.read(65536)
        with out.open("a") as f:
            stamp(f, f"UNIT {unit} USB {UNITS[unit]['usb']} PORT {s.port}")
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


def _decode_edge(hexs: str, fmt: str, px: int):
    if fmt == "rgb16hex":
        if len(hexs) != px * 12:
            return None
        return np.frombuffer(bytes.fromhex(hexs), dtype=">u2").reshape(px, 3).astype(np.uint16)
    if len(hexs) != px * 6:
        return None
    return np.frombuffer(bytes.fromhex(hexs), dtype=np.uint8).reshape(px, 3)


def _slot_bytes(edge, fmt: str) -> bytes:
    if fmt == "rgb16hex":
        b = edge[:, (1, 0, 2)].astype(">u2").tobytes()  # stored wire order G,R,B
    else:
        b = edge.tobytes()
    return b + b"\0" * (EDGE_BYTES - len(b))


def parse_dump(raw_path: Path, out_npz: Path) -> dict:
    begin = None
    e1, e2, ms, mode, idxs = [], [], [], [], []
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
        if not (m and begin is not None and not saw_end):
            continue
        fmt = begin.get("fmt", "rgb8hex")
        px = int(begin.get("px", 160))
        edges = int(begin.get("edges", 1))
        idx = int(m.group("idx"))
        a = _decode_edge(m.group("hex"), fmt, px)
        b = _decode_edge(m.group("hex2"), fmt, px) if m.group("hex2") else None
        if a is None or idx in seen or (edges == 2 and b is None):
            rejected += 1
            continue
        seen.add(idx)
        e1.append(a)
        if b is not None:
            e2.append(b)
        ms.append(int(m.group("ms")))
        mode.append(int(m.group("mode")))
        idxs.append(idx)
    if begin is None:
        raise SystemExit("no [RTRACE-BEGIN] in dump")
    fmt = begin.get("fmt", "rgb8hex")
    edges = int(begin.get("edges", 1))
    n_decl = int(begin.get("frames", 0))
    crc_decl = int(begin.get("crc32", "0"), 16)
    rec = bytearray()
    for i in range(len(e1)):
        rec.extend(_slot_bytes(e1[i], fmt))
        if edges == 2:
            rec.extend(_slot_bytes(e2[i], fmt))
    crc_calc = zlib.crc32(rec) & 0xFFFFFFFF
    dt = np.uint16 if fmt == "rgb16hex" else np.uint8
    arr = np.stack(e1) if e1 else np.zeros((0, 160, 3), dt)
    extra = {"rgb_secondary": np.stack(e2)} if e2 else {}
    np.savez_compressed(out_npz, rgb=arr, ms=np.array(ms, np.uint32), mode=np.array(mode, np.uint8),
                        idx=np.array(idxs, np.uint32), **extra)
    missing = sorted(set(range(n_decl)) - seen)
    scale = 257.0 if fmt == "rgb16hex" else 1.0  # report luma on the 8-bit scale either way
    summary = {
        "raw": str(raw_path), "npz": str(out_npz), "begin": begin, "fmt": fmt, "edges": edges,
        "frames_declared": n_decl, "frames_decoded": len(e1), "lines_rejected": rejected,
        "missing_indices": len(missing), "missing_first": missing[:10],
        "end_marker": saw_end, "crc_declared": f"{crc_decl:08x}", "crc_calculated": f"{crc_calc:08x}",
        "crc_ok": (crc_calc == crc_decl and len(e1) == n_decl and saw_end),
        "ms_first": ms[0] if ms else None, "ms_last": ms[-1] if ms else None,
        "modes": sorted(set(mode)),
        "mean_luma_8bit_scale": float(arr.astype(np.float32).mean() / scale) if len(e1) else None,
    }
    Path(str(out_npz) + ".json").write_text(json.dumps(summary, indent=1))
    return summary


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    sub = sys.argv[1]
    if sub == "ident":
        out = Path(sys.argv[2])
        out.mkdir(parents=True, exist_ok=True)
        t = cmd_lines(out / "ident.txt", [(":build", 1.5), (":chip_id", 1.5), (":dump", 3.0)])
        chip = UNITS[unit_name()]["chip"]
        print("BUILD" in t, chip in t)
        return 0 if ("BUILD" in t and chip in t) else 1
    if sub == "cmd":
        out, line = Path(sys.argv[2]), sys.argv[3]
        wait = float(sys.argv[4]) if len(sys.argv) > 4 else 1.5
        print(cmd_lines(out, [(line, wait)])[-600:])
        return 0
    if sub == "unlock":
        out = Path(sys.argv[2])
        time.sleep(0.4)  # >= 200 ms of silence before the exit line (K1_PRSM_RX_EXIT_GUARD_MS)
        t = cmd_lines(out, [(":prsm_exit", 1.0), (":authored_status", 1.5)])
        ok = "PRSM_SESSION: interactive" in t
        print("UNLOCKED" if ok else "UNLOCK FAILED", t[-700:])
        return 0 if ok else 1
    if sub == "arm":
        out, sec, every = Path(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
        t = cmd_lines(out, [(f":rtrace_arm={sec},{every}", 1.0)])
        ok = "[RTRACE] ARMED" in t
        print("ARMED" if ok else "ARM FAILED (does this build have K1_RENDER_TRACE_V1?)", t[-300:])
        return 0 if ok else 1
    if sub == "dump":
        out = Path(sys.argv[2])
        s, _unit = open_port()
        try:
            time.sleep(0.3)
            s.read(65536)
            send(s, ":ap_stream=0")
            capture(s, 1.0)
            with out.open("wb") as f:
                send(s, ":rtrace_dump=1")
                f.write(capture(s, 120.0, until="[RTRACE-END]"))
                # a6bad318+: prepared-frame records follow [RTRACE-END] when the window held any
                f.write(capture(s, 3.0, until="[RTRACE-PREPARED-END]"))
            first = parse_dump(out, out.with_suffix(".npz"))
            if not first["crc_ok"]:
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
