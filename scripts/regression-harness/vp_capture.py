#!/usr/bin/env python3
"""vp_capture.py — capture the VP Tier-A probe (:vp_probe=all) over serial.

The firmware serial layer is a single-char HOTKEY mode by default; ':' switches
to line-command mode (serial_menu.h command_mode). So line commands MUST be
prefixed with ':' and terminated with newline, e.g. ':vp_probe=all\\n'.

VP Tier A uses SEEDED SYNTHETIC INPUT and the probe saves/forces/restores CONFIG,
so it is deterministic and independent of the acoustic environment — no silence
window or calibration is involved. With --reboot the device is reset first so the
VP_* tuning globals (not saved/restored by the probe) return to their defaults.

Usage: vp_capture.py <port> <out.log> [--reboot] [--settle SEC] [--read SEC]
Exit:  0 = captured full VPO block | 2 = no event=end seen | 1 = error
"""
import sys, time, os, argparse
try:
    import serial
except ImportError:
    print("error: pyserial not installed", file=sys.stderr); sys.exit(1)


def open_retry(port, baud, tries=30, delay=0.5):
    last = None
    for _ in range(tries):
        if os.path.exists(port):
            try:
                return serial.Serial(port, baud, timeout=0.2)
            except Exception as e:
                last = e
        time.sleep(delay)
    raise RuntimeError("cannot open %s: %s" % (port, last))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("port")
    ap.add_argument("out")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--reboot", action="store_true")
    ap.add_argument("--settle", type=float, default=7.0)
    ap.add_argument("--read", type=float, default=15.0)
    a = ap.parse_args()

    s = open_retry(a.port, a.baud)
    if a.reboot:
        s.reset_input_buffer()
        s.write(b":reboot\n"); s.flush()
        time.sleep(1.0)
        s.close()
        time.sleep(4.0)                      # USB re-enumeration window
        s = open_retry(a.port, a.baud)       # device comes back same path
    time.sleep(a.settle)                     # boot + boot_animation
    s.reset_input_buffer()                   # drop boot spam + 1 Hz [AP] backlog
    s.write(b":vp_probe=all\n"); s.flush()
    lines, saw_start, saw_end = [], False, False
    deadline = time.time() + a.read
    while time.time() < deadline:
        raw = s.readline()
        if not raw:
            continue
        line = raw.decode("utf-8", "replace").rstrip("\r\n")
        if not line:
            continue
        lines.append(line)
        if line.startswith("VPO,") and "event=start" in line:
            saw_start = True
        if line.startswith("VPO,") and "event=end" in line:
            saw_end = True
            break
    s.close()
    with open(a.out, "w") as f:
        f.write("\n".join(lines) + "\n")
    vpo = [l for l in lines if l.startswith("VPO,") and "mode=" in l]
    print("captured %d lines, %d VPO mode-rows, start=%s end=%s -> %s"
          % (len(lines), len(vpo), saw_start, saw_end, a.out), file=sys.stderr)
    return 0 if saw_end else 2


if __name__ == "__main__":
    sys.exit(main())
