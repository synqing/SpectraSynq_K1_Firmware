#!/usr/bin/env python3
"""vp_bleed_check.py — run the secondary-channel bleed probe (:vp_probe=secondary).

Proves the RenderParams core (items 1-17): rendering a *different* secondary mode
and params after a primary render must (a) leave global CONFIG unchanged and (b)
produce a different frame hash. The firmware computes this and emits a single
`VPB,...,result=PASS|FAIL` row between `event=start` / `event=end` markers.

The firmware serial layer is single-char HOTKEY mode by default; ':' switches to
line-command mode, so the command MUST be ':' prefixed and newline terminated:
':vp_probe=secondary\\n'. The probe uses SEEDED SYNTHETIC INPUT and saves/restores
CONFIG, so it is deterministic and independent of the acoustic environment — no
silence window or calibration is involved. With --reboot the device is reset first
so the VP_* tuning globals (not saved/restored by the probe) return to defaults.

Usage: vp_bleed_check.py <port> [--reboot] [--settle SEC] [--read SEC]
Exit:  0 = result=PASS (cfg_unchanged=1 and hashes_differ=1)
       1 = result=FAIL (probe ran but the assertion failed) or error
       2 = no VPB event=end seen (probe did not complete)
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


def parse_kv(line):
    """Split a 'VPB,k=v,k=v' row into a dict (first token 'VPB' has no '=')."""
    kv = {}
    for tok in line.split(","):
        if "=" in tok:
            k, v = tok.split("=", 1)
            kv[k.strip()] = v.strip()
    return kv


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("port")
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
    s.write(b":vp_probe=secondary\n"); s.flush()

    saw_start, saw_end = False, False
    result_row = None
    deadline = time.time() + a.read
    while time.time() < deadline:
        raw = s.readline()
        if not raw:
            continue
        line = raw.decode("utf-8", "replace").rstrip("\r\n")
        if not line:
            continue
        if line.startswith("VPB,"):
            if "event=start" in line:
                saw_start = True
            elif "event=end" in line:
                saw_end = True
                break
            elif "result=" in line:
                result_row = line
    s.close()

    if not saw_end:
        print("vp_bleed_check: no VPB event=end seen (start=%s, result_row=%s)"
              % (saw_start, result_row is not None), file=sys.stderr)
        return 2

    if result_row is None:
        print("vp_bleed_check: VPB block completed but no result row found",
              file=sys.stderr)
        return 1

    kv = parse_kv(result_row)
    result = kv.get("result", "")
    cfg_unchanged = kv.get("cfg_unchanged", "")
    hashes_differ = kv.get("hashes_differ", "")
    print("vp_bleed_check: result=%s cfg_unchanged=%s hashes_differ=%s "
          "hash_prim=%s hash_sec=%s"
          % (result, cfg_unchanged, hashes_differ,
             kv.get("hash_prim", "?"), kv.get("hash_sec", "?")), file=sys.stderr)

    ok = (result == "PASS" and cfg_unchanged == "1" and hashes_differ == "1")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
