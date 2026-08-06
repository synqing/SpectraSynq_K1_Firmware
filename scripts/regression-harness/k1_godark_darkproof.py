#!/usr/bin/env python3
"""Prove the go-dark ACTION on a VALIDATION-FORCE-ON build (audio-free).

The serial standby_dimming toggle is broken (dev-tool defect); this build forces the fade
condition true in firmware, so silent_scale must fade 1.0 -> ~0 once silence latches in a
quiet room. Nothing is played. Reports the silent_scale trajectory + min.
"""
import serial, time, re, sys

PORT, BAUD = "/dev/cu.usbmodem1401", 115200
BOOT_WAIT_S, WATCH_S, DWELL_MS = 13, 20, 4000
rx = {k: re.compile(k + r"=([-\d.]+)") for k in ("rms_raw", "silence", "silent_scale", "dim")}


def main():
    s = serial.Serial(PORT, BAUD, timeout=0.1); s.dtr = True
    print("Booting (%ds)..." % BOOT_WAIT_S); time.sleep(BOOT_WAIT_S); s.reset_input_buffer()
    for c in (":ap_stream=on", ":silence_rms_enter=0.04", ":silence_rms_exit=0.08", ":silence_dwell=%d" % DWELL_MS):
        s.write((c + "\n").encode()); s.flush(); time.sleep(0.25)
    print("Watching %ds — STAY QUIET, silent_scale should fall to ~0..." % WATCH_S)
    end = time.time() + WATCH_S; buf = ""; rows = []
    while time.time() < end:
        n = s.in_waiting
        if n:
            buf += s.read(n).decode(errors="replace")
            while "\n" in buf:
                ln, buf = buf.split("\n", 1)
                if "[AP]" in ln:
                    r = {}
                    for k, rr in rx.items():
                        m = rr.search(ln)
                        if m: r[k] = float(m.group(1))
                    if "silent_scale" in r: rows.append(r)
    s.close()
    ss = [r.get("silent_scale", 1) for r in rows]
    sil = [r.get("silence", 0) for r in rows]
    dim = [int(r.get("dim", 0)) for r in rows]
    traj = " ".join("%.2f" % v for v in ss[::max(1, len(ss)//14)])
    print("=== go-dark ACTION dark-proof (n=%d) ===" % len(rows))
    print("silence latched: %s | dim field: %s" % (any(x >= 1 for x in sil), set(dim)))
    print("silent_scale trajectory: %s" % traj)
    print("silent_scale MIN: %.3f  -> PLATE DARK: %s" % (min(ss) if ss else 1, (min(ss) < 0.1) if ss else False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
