#!/usr/bin/env python3
"""Direct-observe diagnostic for the go-dark raw-RMS fix (audio-free, read-mostly).

Logs FULL [AP] lines (not filtered) so the telemetry FORMAT is visible (confirms which
firmware is running), captures command ACKs, and reports the rms_raw distribution + whether
the `silence` flag latches. Dimming stays OFF — this tests DETECTION only, no plate blanking.
The quiet room is the stimulus; nothing is played.
"""
import serial, time, re, statistics, sys

PORT, BAUD = "/dev/cu.usbmodem1401", 115200
BOOT_WAIT_S = 12
OBSERVE_S = 22

rx = {k: re.compile(k + r"=([-\d.]+)") for k in ("rms_raw", "silence", "dim", "sil_pk", "max_raw")}


def main():
    ser = serial.Serial(PORT, BAUD, timeout=0.1); ser.dtr = True
    print("Booting (%ds)..." % BOOT_WAIT_S); time.sleep(BOOT_WAIT_S)
    ser.reset_input_buffer()
    for c in (":ap_stream=on", ":silence_rms_enter=0.04", ":silence_rms_exit=0.08", ":silence_dwell=4000"):
        ser.write((c + "\n").encode()); ser.flush(); time.sleep(0.25)
    print("Observing %ds — STAY QUIET..." % OBSERVE_S)
    end = time.time() + OBSERVE_S; buf = ""; lines = []; rows = []
    while time.time() < end:
        n = ser.in_waiting
        if n:
            buf += ser.read(n).decode(errors="replace")
            while "\n" in buf:
                ln, buf = buf.split("\n", 1); ln = ln.strip()
                if not ln:
                    continue
                lines.append(ln)
                if "[AP]" in ln:
                    row = {}
                    for k, r in rx.items():
                        m = r.search(ln)
                        if m:
                            row[k] = float(m.group(1))
                    rows.append(row)
    ser.write(b":ap_stream=off\n"); ser.flush(); ser.close()

    ts = time.strftime("%Y-%m-%dT%H%M%S")
    open("/private/tmp/k1_godark_observe_%s.log" % ts, "w").write("\n".join(lines))
    has_rmsraw = any("rms_raw" in r for r in rows)
    acks = [l for l in lines if any(t in l for t in ("SILENCE_RMS", "AP stream", "K1_SILENCE"))]
    rr = sorted(r["rms_raw"] for r in rows if "rms_raw" in r)
    mr = [r.get("max_raw", 0) for r in rows]
    sil = [r.get("silence", 0) for r in rows]
    print("=== observe %s (AP rows=%d) ===" % (ts, len(rows)))
    print("log: /private/tmp/k1_godark_observe_%s.log" % ts)
    print("telemetry has rms_raw field: %s   (proves MY firmware if True)" % has_rmsraw)
    print("command ACKs seen: %s" % (acks[:4] if acks else "NONE"))
    if rr:
        print("rms_raw: min=%.4f p50=%.4f p90=%.4f max=%.4f" %
              (rr[0], rr[len(rr)//2], rr[min(len(rr)-1, int(0.9*len(rr)))], rr[-1]))
    if mr:
        print("max_raw(peak): min=%.0f p50=%.0f max=%.0f" %
              (min(mr), statistics.median(mr), max(mr)))
    print("silence latched (any==1): %s   [dimming was OFF — flag-only test]" %
          any(s >= 1 for s in sil))
    return 0


if __name__ == "__main__":
    sys.exit(main())
