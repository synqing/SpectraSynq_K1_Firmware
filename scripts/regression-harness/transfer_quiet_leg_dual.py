#!/usr/bin/env python3
"""Transfer-test QUIET leg, both IM69D units, simultaneously.

PASSIVE ONLY — writes ZERO bytes to either device. The devices emit [AP] telemetry
continuously, so no command is needed, and 64 of 152 typed serial commands are
destructive persisted setters (handover trap table). Sending nothing is the only
safe read.

dtr is forced True: on USB-Serial-JTAG, dtr=False is a hardware reset, and without
dtr asserted the port returns zero bytes and a live device looks dead (HF trap).

Compares max_raw as a multiple of EACH DEVICE'S OWN SSL — that is the transfer
test's actual comparison, not raw counts.
"""
import re, sys, time, threading, statistics as st
import serial

DUR = float(sys.argv[1]) if len(sys.argv) > 1 else 45.0

UNITS = [
    ("Unit 2  (0C54FC00)", "/dev/cu.usbmodem1101"),
    ("bench   (B489A500)", "/dev/cu.usbmodem12201"),
]

AP = re.compile(r"\[AP\][^\n]*")
FIELD = re.compile(r"\b(\w+)=(-?[\d.]+)")

out = {}


def cap(name, port):
    try:
        ser = serial.Serial(port, 115200, timeout=0.1)
        ser.dtr = True                      # NEVER False — hardware reset
        time.sleep(0.6)
        # `:ap_stream` is SC_TYPED_ONLY + CMD_HARNESS but NOT CMD_PERSISTS — it sets
        # the RAM flag AP_STREAM_ENABLED and writes no config. Typed commands need
        # the ':' prefix; a bare byte would be read as a HOTKEY.
        ser.reset_input_buffer()
        ser.write(b":ap_stream=1\n"); ser.flush()   # type=value form; ' 1' is Bad command
        time.sleep(0.8)
        ack = ser.read(ser.in_waiting or 1).decode(errors="replace")
        if "AP_STREAM" not in ack and "[AP]" not in ack:
            out[name] = RuntimeError(f"no AP_STREAM ack; got {ack[:120]!r}")
            ser.close(); return
        ser.reset_input_buffer()
        buf, end = b"", time.time() + DUR
        while time.time() < end:
            n = ser.in_waiting
            buf += ser.read(n) if n else b""
            if not n:
                time.sleep(0.02)
        ser.write(b":ap_stream=0\n"); ser.flush()   # leave the device as found
        time.sleep(0.2)
        ser.close()
        text = buf.decode(errors="replace")
        frames = []
        for line in AP.findall(text):
            d = {k: float(v) for k, v in FIELD.findall(line)}
            if "max_raw" in d and "SSL" in d:
                frames.append(d)
        out[name] = frames
    except Exception as e:                                   # noqa: BLE001
        out[name] = e


ts = [threading.Thread(target=cap, args=u) for u in UNITS]
print(f"capturing {DUR:.0f}s, passive, both units concurrently...")
[t.start() for t in ts]
[t.join() for t in ts]


def pct(v, p):
    v = sorted(v)
    if not v:
        return float("nan")
    k = (len(v) - 1) * p / 100.0
    f = int(k); c = min(f + 1, len(v) - 1)
    return v[f] + (v[c] - v[f]) * (k - f)


print(f"\n{'':<20}{'frames':>8}{'SSL':>7}{'silence%':>10}{'rms med':>10}"
      f"{'ratio med':>11}{'ratio p95':>11}{'ratio max':>11}")
print("-" * 88)
ratios = {}
for name, _ in UNITS:
    f = out.get(name)
    if isinstance(f, Exception):
        print(f"{name:<20} ERROR: {f}")
        continue
    if not f:
        print(f"{name:<20} NO [AP] FRAMES — device silent on serial")
        continue
    ssl = st.median([d["SSL"] for d in f])
    r = [d["max_raw"] / d["SSL"] for d in f if d["SSL"] > 0]
    ratios[name] = r
    sil = [d.get("silence", float("nan")) for d in f if "silence" in d]
    rms = [d["rms_raw"] for d in f if "rms_raw" in d]
    print(f"{name:<20}{len(f):>8}{int(ssl):>7}"
          f"{(100*sum(sil)/len(sil) if sil else float('nan')):>9.1f}%"
          f"{(st.median(rms) if rms else float('nan')):>10.4f}"
          f"{st.median(r):>10.2f}x{pct(r,95):>10.2f}x{max(r):>10.2f}x")

if len(ratios) == 2:
    a, b = list(ratios.values())
    ma, mb = st.median(a), st.median(b)
    print(f"\nQUIET-LEG VERDICT (SSL-normalised, the transfer test's own comparison)")
    print(f"  median ratio  Unit2 {ma:.2f}x   bench {mb:.2f}x   "
          f"delta {abs(ma-mb):.2f}x  ({100*abs(ma-mb)/max(ma,mb):.0f}% apart)")
    print(f"  p95    ratio  Unit2 {pct(a,95):.2f}x   bench {pct(b,95):.2f}x")
    print("\n  Music legs still required before this can decide per-unit vs per-room.")
