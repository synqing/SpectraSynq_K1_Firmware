#!/usr/bin/env python3
"""Measure the raw-RMS silence floor on the K1 bench (audio-free, read-only).

The go-dark fix drives the `silence` latch off `k1_silence_rms_raw` (raw per-frame RMS,
firmware-v3 pre-gate port) vs an ABSOLUTE threshold. This script measures that raw floor
in a genuinely quiet room so the enter/exit thresholds can be set with margin.

NOTHING is played. The only serial write is `:ap_stream=on`. Reads the [AP] telemetry
field `rms_raw` (plus silence / silent_scale / sil_pk / SSL / dim for context).

Usage: run in a quiet room, stay quiet for the sample window, read the printed floor.
"""
import serial, time, re, statistics, sys

PORT, BAUD = "/dev/cu.usbmodem1401", 115200   # bench, MAC ...89:B4 (verified via pio device list)
BOOT_WAIT_S = 12          # allow full boot (PDM cal) before trusting telemetry
SAMPLE_S = 20             # quiet-room observation window

F = {k: re.compile(k + r"=([-\d.]+)") for k in
     ("rms_raw", "silence", "silent_scale", "sil_pk", "SSL", "dim")}


def main():
    log = []
    ser = serial.Serial(PORT, BAUD, timeout=0.1)
    ser.dtr = True                        # DTR toggle resets the board → clean boot
    print("Booting (%ds)..." % BOOT_WAIT_S)
    time.sleep(BOOT_WAIT_S)
    ser.reset_input_buffer()
    ser.write(b":ap_stream=on\n"); ser.flush()
    print("Sampling %ds — STAY QUIET..." % SAMPLE_S)
    end = time.time() + SAMPLE_S
    buf = ""; rows = []
    while time.time() < end:
        n = ser.in_waiting
        if n:
            buf += ser.read(n).decode(errors="replace")
            while "\n" in buf:
                line, buf = buf.split("\n", 1); line = line.strip()
                if "[AP]" in line:
                    row = {}
                    for k, rx in F.items():
                        m = rx.search(line)
                        if m:
                            row[k] = float(m.group(1))
                    if "rms_raw" in row:
                        rows.append(row); log.append(line)
        else:
            time.sleep(0.01)
    ser.write(b":ap_stream=off\n"); ser.flush(); ser.close()

    ts = time.strftime("%Y-%m-%dT%H%M%S")
    open("/private/tmp/k1_godark_measure_%s.log" % ts, "w").write("\n".join(log))
    if not rows:
        print("NO [AP] rows captured — check port / ap_stream / boot marker."); return 1
    rr = sorted(r["rms_raw"] for r in rows)
    ssl = statistics.median(r.get("SSL", 0) for r in rows)
    p = lambda q: rr[min(len(rr) - 1, int(q * len(rr)))]
    print("=== K1 raw-RMS silence floor (%s, n=%d) ===" % (ts, len(rr)))
    print("log: /private/tmp/k1_godark_measure_%s.log" % ts)
    print("rms_raw  min=%.3f  p50=%.3f  p90=%.3f  p99=%.3f  max=%.3f" %
          (rr[0], p(0.50), p(0.90), p(0.99), rr[-1]))
    print("SSL(median)=%.0f   silence latched=%s   dim=%s" %
          (ssl, any(r.get("silence", 0) >= 1 for r in rows),
           set(int(r.get("dim", 0)) for r in rows)))
    print("--- suggested (margin x2 / x4 above p99 floor): "
          "enter=%.2f  exit=%.2f ---" % (p(0.99) * 2.0, p(0.99) * 4.0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
