#!/usr/bin/env python3
"""Tiny serial helper: open port without reset, optionally send commands, capture for N seconds.
usage: ser.py PORT SECONDS OUTFILE [cmd ...]   (cmds sent ~1 s apart after a 1 s settle)"""
import sys, time, serial
port, secs, out = sys.argv[1], float(sys.argv[2]), sys.argv[3]
cmds = sys.argv[4:]
s = serial.Serial()
s.port = port; s.baudrate = 115200; s.timeout = 0.05
s.dtr = False; s.rts = False
s.open()
buf = bytearray(); t0 = time.time(); nxt = t0 + 1.0
while time.time() - t0 < secs:
    if cmds and time.time() >= nxt:
        c = cmds.pop(0); s.write((c + "\n").encode()); nxt = time.time() + 1.0
    buf += s.read(4096)
s.close()
open(out, "wb").write(bytes(buf))
print(f"captured {len(buf)} bytes -> {out}")
