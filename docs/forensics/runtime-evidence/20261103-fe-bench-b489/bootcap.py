#!/usr/bin/env python3
"""Reset the ESP32-S3 via the USB-Serial/JTAG RTS line (app boot, IO0 high) and capture.
usage: bootcap.py PORT SECONDS OUTFILE [cmd ...]  (cmds sent 1 s apart starting 6 s after reset)"""
import sys, time, serial
port, secs, out = sys.argv[1], float(sys.argv[2]), sys.argv[3]; cmds = sys.argv[4:]
s = serial.Serial(port, 115200, timeout=0.05)
s.dtr = False; s.rts = True; time.sleep(0.1); s.rts = False
buf = bytearray(); t0 = time.time(); nxt = t0 + 6.0
while time.time() - t0 < secs:
    try:
        buf += s.read(4096)
        if cmds and time.time() >= nxt:
            s.write((cmds.pop(0) + "\n").encode()); nxt = time.time() + 1.0
    except serial.SerialException:
        time.sleep(0.2)
        try: s.close(); s = serial.Serial(port, 115200, timeout=0.05)
        except Exception: pass
s.close(); open(out, "wb").write(bytes(buf)); print(f"captured {len(buf)} bytes -> {out}")
