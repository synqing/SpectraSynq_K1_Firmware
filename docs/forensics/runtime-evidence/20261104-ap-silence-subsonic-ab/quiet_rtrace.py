#!/usr/bin/env python3
"""Quiet-room LED capture: open port (resets B489), wait SETTLE s, :rtrace_arm=SECS,EVERY,
wait, :rtrace_dump=1, read to [RTRACE-END]. usage: quiet_rtrace.py PORT SETTLE SECS EVERY OUT"""
import sys, time, serial
port, settle, secs, every, out = sys.argv[1], float(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
s = serial.Serial(); s.port = port; s.baudrate = 115200; s.timeout = 0.05
s.dtr = False; s.rts = False; s.open()
buf = bytearray(); t0 = time.time(); stage = 0
while True:
    t = time.time() - t0
    if stage == 0 and t >= settle:
        s.write(f":rtrace_arm={secs},{every}\n".encode()); stage = 1; t_arm = t
    elif stage == 1 and t >= t_arm + secs + 2:
        s.write(b":rtrace_dump=1\n"); stage = 2; t_dump = t
    elif stage == 2 and (b"[RTRACE-END]" in buf[-4000:] or t > t_dump + 120):
        s.write(b":build\n"); time.sleep(1.0); buf += s.read(65536); break
    buf += s.read(65536)
s.close(); open(out, "wb").write(bytes(buf)); print(f"captured {len(buf)} bytes -> {out}")
