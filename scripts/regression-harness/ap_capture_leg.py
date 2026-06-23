#!/usr/bin/env python3
# AP baseline capture leg for freeze-88428a2 (NON-silence legs: tone / track-A / track-B).
# Captain plays the stimulus and cues; this script captures :ap_capture (+ :dump_raw for tone).
# It NEVER fires calibration. It does NOT gate on silence (these legs are intentionally non-silent).
#
# Usage:  ap_capture_leg.py <leg> <run>
#   leg : tone | track-a | track-b
#   run : 1 | 2          (which baseline run, for run-to-run bands)
#
# Output: docs/refactor/harness-baselines/freeze-88428a2/ap_<leg>_run<run>_<ts>.log
import serial, time, re, sys, subprocess

PORT, BAUD = "/dev/tty.usbmodem1101", 115200
DIR = "/Users/spectrasynq/SensoryBridge-main 9/docs/refactor/harness-baselines/freeze-88428a2"

LEGS = {"tone": "tone-1k", "track-a": "track-A", "track-b": "track-B"}


def rd(ser, secs):
    end = time.time() + secs
    b = b""
    while time.time() < end:
        n = ser.in_waiting
        b += ser.read(n) if n else b""
        if not n:
            time.sleep(0.02)
    return b.decode(errors="replace")


def snd(ser, c):
    ser.reset_input_buffer()
    ser.write((c + "\n").encode())
    ser.flush()


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in LEGS or sys.argv[2] not in ("1", "2"):
        print(__doc__)
        raise SystemExit(2)
    leg, run = sys.argv[1], sys.argv[2]
    stimulus = LEGS[leg]
    ts = time.strftime("%Y-%m-%dT%H%M%S%z")

    ser = serial.Serial(PORT, BAUD, timeout=0.1)
    ser.dtr = True
    time.sleep(6.0)               # CDC settle after connect
    ser.reset_input_buffer()
    snd(ser, ":get_mode_name")    # warmup — first cmd after CDC connect often drops
    rd(ser, 1.2)
    snd(ser, ":version")          # firmware self-stamp (proves which build answered)
    fw = " | ".join(l.strip() for l in rd(ser, 1.5).splitlines() if l.strip())[:200] or "(no :version reply)"
    snd(ser, ":ap_stream=off")
    time.sleep(0.5)
    ser.reset_input_buffer()

    try:
        head_sha = subprocess.check_output(
            ["git", "-C", "/Users/spectrasynq/SensoryBridge-main 9", "rev-parse", "--short", "HEAD"],
            text=True).strip()
    except Exception:
        head_sha = "unknown"

    out = [
        "# freeze-88428a2 AP leg=%s stimulus=%s run=%s %s" % (leg, stimulus, run, ts),
        "# BUILD STAMP (standing rule): env=k1_hardware_harness source=feat/pio-core-bump@%s (operator-flashed by CC)" % head_sha,
        "# FIRMWARE :version reply: %s" % fw,
        "# NON-silence leg — captured while Captain played %s." % stimulus,
    ]

    # --- harness command-path sanity ---
    # Harness proof = device knows :ap_capture (prints "AP_CAPTURE: armed ..." then later [APCAP]).
    # Release build prints "Bad command". Accept either harness marker; the [APCAP] summary can
    # arrive after a short read, so do NOT require it here — only require proof the cmd exists.
    snd(ser, ":ap_capture=2000")
    sane = rd(ser, 5.0)
    if "Bad command" in sane:
        print("RELEASE_BUILD: :ap_capture rejected ('Bad command'). Reflash k1_hardware_harness. ABORT.")
        ser.close()
        raise SystemExit(3)
    if "AP_CAPTURE:" not in sane and "[APCAP]" not in sane:
        print("NO_RESPONSE from :ap_capture (got: %r). Device not answering on usbmodem1101. ABORT."
              % (sane.strip()[:200] or "(none)"))
        ser.close()
        raise SystemExit(3)

    # --- tone leg also captures a labelled raw dump ---
    if leg == "tone":
        snd(ser, ":dump_raw=tone")
        dr = rd(ser, 3.5)
        out += ["# === dump_raw=tone ==="] + [l for l in dr.splitlines() if l.strip()]

    # --- the AP capture window (5 s on-device) ---
    snd(ser, ":ap_capture=5000")
    ap = rd(ser, 7.0)
    out += ["# === ap_capture=5000 (%s) ===" % stimulus] + [l for l in ap.splitlines() if l.strip()]
    ser.close()

    path = "%s/ap_%s_run%s_%s.log" % (DIR, leg, run, ts)
    open(path, "w").write("\n".join(out))

    apcaps = [l.strip() for l in ap.splitlines() if "[APCAP]" in l]
    print("wrote %s" % path)
    print("APCAP lines: %d" % len(apcaps))
    for l in apcaps[:4]:
        print("  " + l)
    if "Bad command" in ap or "vp_out_test" in ap:
        print("WARNING: log contains 'Bad command' or 'vp_out_test' — capture likely INVALID.")


if __name__ == "__main__":
    main()
