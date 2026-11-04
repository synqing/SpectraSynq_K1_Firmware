#!/usr/bin/env python3
"""Quiet-room AP capture: open the K1 port (this resets B489), record SECONDS of serial,
then send :build. usage: quiet_capture.py PORT SECONDS OUT"""
import sys, time, serial
port, secs, out = sys.argv[1], float(sys.argv[2]), sys.argv[3]
s = serial.Serial(); s.port = port; s.baudrate = 115200; s.timeout = 0.05
s.dtr = False; s.rts = False; s.open()
buf = bytearray(); t0 = time.time(); sent = False
while time.time() - t0 < secs:
    if not sent and time.time() - t0 > secs - 3:
        s.write(b":build\n"); sent = True
    buf += s.read(4096)
s.close(); open(out, "wb").write(bytes(buf)); print(f"captured {len(buf)} bytes -> {out}")
