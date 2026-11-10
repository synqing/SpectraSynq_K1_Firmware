"""Read-only identity read-back for any K1 on USB-Serial-JTAG (lead tool, 10 Nov 2026).

Usage: python3.13 read_ident_any.py PORT EXPECTED_USB_SERIAL OUT_DIR

1. Refuses unless the port's USB serial number equals EXPECTED_USB_SERIAL.
2. Listens 3 s WITHOUT writing (what does the firmware print on its own?).
3. Only if that output looks like K1 product firmware ('[AP]' telemetry or a BUILD line),
   sends the read-only lines ':build', ':chip_id', ':dump' (SC_SAFE / read-only per
   scripts/regression-harness/k1_serial_safety.py) and captures each reply.
DTR asserted, RTS low (repo identity-guard convention). No flash, reset or erase.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import serial
from serial.tools import list_ports

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts" / "regression-harness"))
from k1_device_identity_guard import parse_build_line  # noqa: E402
from k1_serial_safety import assert_safe_to_send  # noqa: E402


def main() -> int:
    port, expect, out = sys.argv[1], sys.argv[2].upper(), Path(sys.argv[3])
    sn = {p.device: (p.serial_number or "") for p in list_ports.comports()}
    if sn.get(port, "").upper() != expect:
        print(f"REFUSED: {port} USB serial {sn.get(port)!r} != {expect}")
        return 2
    out.mkdir(parents=True, exist_ok=True)
    s = serial.Serial()
    s.port, s.baudrate, s.timeout = port, 115200, 0.2
    s.dtr, s.rts = True, False
    s.open()
    log = []
    try:
        end = time.time() + 3.0
        passive = bytearray()
        while time.time() < end:
            passive.extend(s.read(4096))
        ptxt = passive.decode("utf-8", "replace")
        (out / "passive_3s.txt").write_text(ptxt)
        looks_k1 = ("[AP]" in ptxt) or ("BUILD:" in ptxt)
        print(f"passive bytes={len(passive)} looks_like_k1_product={looks_k1}")
        if not looks_k1:
            print("STOP: output does not look like K1 product firmware; nothing sent")
            return 3
        for line, wait in ((":build", 1.5), (":chip_id", 1.5), (":dump", 3.0)):
            assert_safe_to_send(line)
            s.reset_input_buffer()
            s.write((line + "\n").encode("ascii"))
            s.flush()
            buf = bytearray()
            e2 = time.time() + wait
            while time.time() < e2:
                buf.extend(s.read(65536))
            txt = buf.decode("utf-8", "replace")
            log.append(f"# SEND {line} at {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}\n{txt}\n")
    finally:
        s.close()
    full = "".join(log)
    (out / "ident.txt").write_text(full)
    print("BUILD", parse_build_line(full))
    for ln in full.splitlines():
        if ln.startswith("CHIP ID") or ln.startswith("CONFIG.LIGHTSHOW_MODE") or ln.startswith("CONFIG.LED_COUNT"):
            print(ln)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
