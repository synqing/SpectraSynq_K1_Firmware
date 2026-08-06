#!/usr/bin/env python3
"""Validate the silence go-dark fix on the K1 bench (plate-only; no indicator LEDs).

Raw-RMS pre-gate port (firmware-v3 Stage 7 analogue): the `silence` latch is driven off
`k1_silence_rms_raw` (raw per-frame RMS, normalised [0,1]) vs an ABSOLUTE threshold with
hysteresis + dwell. Calibrated 2026-07-10 from k1_godark_measure.py (quiet-room floor
p99≈0.02) → enter 0.04 / exit 0.08.

AUDIO-FREE. Nothing is played. The quiet room itself IS the silence stimulus, so the full
latch→plate-dark path is validated autonomously; only the wake (clap/speak) needs a human.
Never run afplay concurrently — CoreAudio stutter leaks into the mic and poisons readings.

Phases (dimming ENABLED — quiet room, so darkening is the CORRECT behaviour, no music to
false-blank):
  A  latch+dark: stay quiet → silence must latch (after dwell) AND silent_scale → ~0 (plate
     goes dark). This is the core fix.
  B  wake: human claps/speaks → silence=0 instantly, silent_scale snaps back toward 1.
Restores STANDBY_DIMMING=off (dormant) on exit — the feature ships OFF until Captain flips it.
"""
import serial, time, re, sys

PORT, BAUD = "/dev/cu.usbmodem1401", 115200   # bench, MAC ...89:B4 (verified via pio device list)
BOOT_WAIT_S = 12
RMS_ENTER, RMS_EXIT, DWELL_MS = 0.04, 0.08, 5000
LATCH_WATCH_S = DWELL_MS / 1000 + 8   # allow dwell + fade
WAKE_WATCH_S = 10

F = {k: re.compile(k + r"=([-\d.]+)") for k in
     ("rms_raw", "silence", "silent_scale", "sil_pk", "SSL", "dim")}


def snd(ser, c):
    ser.write((c + "\n").encode()); ser.flush(); time.sleep(0.2)


def read(ser, secs, tag, log):
    end = time.time() + secs; buf = ""; rows = []
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
                    if "silent_scale" in row:
                        row["t"] = time.time(); rows.append(row)
                        log.append("%.2f %-6s %s" % (time.time(), tag, line))
        else:
            time.sleep(0.01)
    return rows


def main():
    log = []
    ser = serial.Serial(PORT, BAUD, timeout=0.1); ser.dtr = True
    print("Booting (%ds)..." % BOOT_WAIT_S); time.sleep(BOOT_WAIT_S)
    ser.reset_input_buffer()
    snd(ser, ":ap_stream=on")
    # Re-assert AFTER boot so the PDM boot force-off (system.h:439) cannot wipe it.
    snd(ser, ":silence_rms_enter=%.3f" % RMS_ENTER)
    snd(ser, ":silence_rms_exit=%.3f" % RMS_EXIT)
    snd(ser, ":silence_dwell=%d" % DWELL_MS)
    snd(ser, ":standby_dimming=on")
    print("Phase A latch+dark (%.0fs) — STAY QUIET, watch the plate..." % LATCH_WATCH_S)
    A = read(ser, LATCH_WATCH_S, "latch", log)
    print(">>> Phase B: CLAP or speak NOW to test wake (%ds) <<<" % WAKE_WATCH_S)
    B = read(ser, WAKE_WATCH_S, "wake", log)
    snd(ser, ":standby_dimming=off")   # restore dormant ship state
    snd(ser, ":ap_stream=off")
    ser.close()

    ts = time.strftime("%Y-%m-%dT%H%M%S")
    open("/private/tmp/k1_godark_validate_%s.log" % ts, "w").write("\n".join(log))
    a_sil = [r.get("silence", 0) for r in A]
    a_ss = [r.get("silent_scale", 1) for r in A]
    latched = any(s >= 1 for s in a_sil)
    dark = (min(a_ss) < 0.1) if a_ss else False
    dim_on = any(r.get("dim", 0) >= 1 for r in A)
    woke = next((r for r in B if r.get("silence", 1) == 0 and r.get("silent_scale", 0) > 0.5), None)
    print("=== K1 SILENCE GO-DARK validation (%s) ===" % ts)
    print("log: /private/tmp/k1_godark_validate_%s.log" % ts)
    print("enter=%.3f exit=%.3f dwell=%dms" % (RMS_ENTER, RMS_EXIT, DWELL_MS))
    print("A latch+dark: dim_on=%s | silence latched=%s | silent_scale min=%.3f → PLATE DARK=%s"
          % (dim_on, latched, min(a_ss) if a_ss else 1, dark))
    print("B wake: recovered=%s" % (woke is not None))
    ok = latched and dim_on and dark
    print("VERDICT (detection+dark, autonomous):",
          "PASS" if ok else "REVIEW — inspect log")
    if woke is None:
        print("  (wake unconfirmed — needs a clap/speak during Phase B)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
