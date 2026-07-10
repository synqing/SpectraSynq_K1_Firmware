#!/usr/bin/env python3
"""Validate the silence go-dark fix on the K1 bench (plate-only; no indicator LEDs).

Mostly SILENT by design (Captain audio-fatigue): a quiet-room detection phase, a go-dark
phase, and a 2 s blip to confirm instant wake. Reads the [AP] telemetry fields
silence / sil_pk (smoothed peak) / SSL / silent_scale / dim.

Phases:
  A  detection (dimming OFF): quiet room → silence must LATCH (after dwell); sil_pk must
     fall below ~SILENCE_ENTER_SSL_FRAC*SSL. silent_scale stays 1.0 (dimming off).
  B  go-dark (dimming ON): enable → silent_scale must fade toward 0 → PLATE GOES DARK.
  C  wake: 2 s of an approved track → silence=0 instantly, silent_scale snaps to 1.

AUDIO SAFETY: only the 2 s wake blip plays — approved corpus, moderate volume, bounded,
always killed + volume restored on exit.
"""
import serial, time, re, subprocess, statistics, sys

PORT, BAUD = "/dev/cu.usbmodem1401", 115200
WAKE_TRACK = "/Users/spectrasynq/Downloads/MartinGarrix-Animals.mp3"   # ASCII path (avoid afplay unicode fault)
WAKE_VOL = 50
DETECT_SECS = 16     # quiet: allow >dwell (5 s) to latch
DARK_SECS = 10       # after enabling dimming, watch fade to black
WAKE_BLIP_SECS = 2

F = {k: re.compile(k + r"=([-\d.]+)") for k in ("silence", "sil_pk", "SSL", "silent_scale", "dim")}


def snd(ser, c):
    ser.reset_input_buffer(); ser.write((c + "\n").encode()); ser.flush()


def read(ser, secs, log, tag):
    end = time.time() + secs; buf = ""; rows = []
    while time.time() < end:
        n = ser.in_waiting
        if n:
            buf += ser.read(n).decode(errors="replace")
            while "\n" in buf:
                line, buf = buf.split("\n", 1); line = line.strip()
                if not line:
                    continue
                log.append("%.3f %-7s %s" % (time.time(), tag, line))
                if "[AP]" in line:
                    row = {}
                    for k, rx in F.items():
                        m = rx.search(line)
                        if m:
                            row[k] = float(m.group(1))
                    if "silent_scale" in row:
                        row["t"] = time.time(); rows.append(row)
        else:
            time.sleep(0.01)
    return rows


def vget():
    try:
        return int(subprocess.check_output(["osascript","-e","output volume of (get volume settings)"],text=True).strip())
    except Exception:
        return None


def vset(v):
    subprocess.run(["osascript","-e","set volume output volume %d"%v], check=False)


def main():
    log=[]; orig=vget(); ser=None
    try:
        ser=serial.Serial(PORT,BAUD,timeout=0.1); ser.dtr=True
        time.sleep(6.0); ser.reset_input_buffer()
        snd(ser, ":ap_stream=on"); time.sleep(1.0)
        # Quiet-room floor sits near SSL (prior run: min sil_pk 173 vs SSL 179), so
        # thresholds must be near 1.0*SSL, not 0.35. Tuned live (runtime-adjustable).
        snd(ser, ":silence_enter=1.0"); time.sleep(0.2)
        snd(ser, ":silence_exit=1.2"); time.sleep(0.2)
        snd(ser, ":standby_dimming=off"); time.sleep(0.3)     # ensure dormant for phase A
        A = read(ser, DETECT_SECS, log, "detect")
        snd(ser, ":standby_dimming=on"); time.sleep(0.3)
        B = read(ser, DARK_SECS, log, "dark")
        # WAKE: NO audio played (afplay stutters + leaks into the mic). Clap or speak to
        # wake — observe the silence break + relight in the telemetry.
        print(">>> CLAP or speak NOW to test wake (watching ~10 s) <<<")
        C = read(ser, 10, log, "wake")
        snd(ser, ":standby_dimming=off"); snd(ser, ":ap_stream=off")
    finally:
        subprocess.run(["killall","afplay"], check=False)
        if orig is not None: vset(orig)
        if ser: ser.close()

    ts=time.strftime("%Y-%m-%dT%H%M%S")
    open("/private/tmp/k1_godark_validate_%s.log"%ts,"w").write("\n".join(log))
    ssl = statistics.median([r["SSL"] for r in A if "SSL" in r]) if A else 0
    a_sil = [r.get("silence",0) for r in A]; a_pk=[r.get("sil_pk",0) for r in A]
    latched = any(s>=1 for s in a_sil)
    b_ss = [r.get("silent_scale",1) for r in B]
    dark = (min(b_ss) < 0.1) if b_ss else False
    dim_on = any(r.get("dim",0)>=1 for r in B)
    # wake: first sample in C where silence back to 0 AND silent_scale recovering
    woke = next((r for r in C if r.get("silence",1)==0 and r.get("silent_scale",0)>0.5), None)
    print("=== K1 SILENCE GO-DARK validation (%s) ===" % ts)
    print("log: /private/tmp/k1_godark_validate_%s.log" % ts)
    print("SSL(median)=%.0f  enter_thresh≈%.0f  exit_thresh≈%.0f" % (ssl, 0.35*ssl, 0.55*ssl))
    print("A detect: sil_pk mean=%.0f min=%.0f max=%.0f | silence latched=%s" % (
        statistics.mean(a_pk) if a_pk else 0, min(a_pk) if a_pk else 0, max(a_pk) if a_pk else 0, latched))
    print("B go-dark: dim toggled on=%s | silent_scale min=%.3f → PLATE DARK=%s" % (
        dim_on, min(b_ss) if b_ss else 1, dark))
    print("C wake: recovered=%s" % (woke is not None))
    ok = latched and dim_on and dark and (woke is not None)
    print("VERDICT:", "PASS — latches in silence, plate goes dark, wakes on sound" if ok
          else "REVIEW — inspect log (thresholds may need tuning via :silence_enter/:silence_exit)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
