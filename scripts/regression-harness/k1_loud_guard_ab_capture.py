#!/usr/bin/env python3
"""K1 loud-guard release/floor-cut A/B capture v2 (AP-audit Item 1, 2026-07-10).

v2 changes for the definitive test (Captain-directed):
  - louder (drive spec_sat_duty > 0 so the spec-sat->AGC limit-cycle loop actually runs)
  - longer sustained-loud window (tempo locks; clean onset/tempo regression read)
  - requires the 10 Hz diagnostic build (-DK1_AP_STREAM_INTERVAL_MS=100) to resolve a
    ~1.5 s limit cycle without aliasing
  - steady-state slicing (exclude convergence transient) + oscillation detection

Drives k1_loud_guard=mode0|1|2 on the IM73D bench; same source (Avicii-Levels) per mode.
AUDIO SAFETY: plays ONLY the approved file, at a stated volume, bounded duration, and
ALWAYS kills playback + restores volume on exit.
"""
import serial, time, re, sys, subprocess, statistics

PORT, BAUD = "/dev/cu.usbmodem1401", 115200
TRACK = "/Users/spectrasynq/Downloads/Avicii-Levels.mp3"
VOLUME = 78                 # louder — drive spec_sat saturation
LOUD_SECS = 35             # long enough for tempo lock + sustained-loud limit-cycle window
STEADY_SKIP = 12           # exclude convergence transient (audio A/B gate 2)
RECOVERY_SECS = 8
SETTLE_SECS = 4
MODES = [0, 1, 2]

AP_RE = {
    "gdft_trim": re.compile(r"gdft_trim=([-\d.]+)"),
    "spec_duty": re.compile(r"spec_pin=([-\d.]+)"),   # k1_loud_spec_sat_duty
    "spec_frac": re.compile(r"spec_sat=([-\d.]+)"),   # k1_loud_spec_sat_fraction
    "peak_pin":  re.compile(r"peak_pin=([-\d.]+)"),
    "mode":      re.compile(r"mode=(\d)"),
    "bpm":       re.compile(r"bpm=([-\d.]+)"),
    "lock":      re.compile(r"lock=(\d)"),
    "onset":     re.compile(r"onset=(\d)"),
}


def snd(ser, c):
    ser.reset_input_buffer(); ser.write((c + "\n").encode()); ser.flush()


def read_lines(ser, secs, log, tag, t0):
    end = time.time() + secs
    buf = ""; parsed = []
    while time.time() < end:
        n = ser.in_waiting
        if n:
            buf += ser.read(n).decode(errors="replace")
            while "\n" in buf:
                line, buf = buf.split("\n", 1)
                line = line.strip()
                if not line:
                    continue
                now = time.time()
                log.append("%.3f %-8s %s" % (now, tag, line))
                if "[AP]" in line:
                    row = {}
                    for k, rx in AP_RE.items():
                        m = rx.search(line)
                        if m:
                            row[k] = float(m.group(1))
                    if "gdft_trim" in row:
                        row["t"] = now - t0
                        parsed.append(row)
        else:
            time.sleep(0.01)
    return parsed


def mean_crossings(xs):
    if len(xs) < 3:
        return 0
    mu = statistics.mean(xs)
    c = 0
    for a, b in zip(xs, xs[1:]):
        if (a - mu) * (b - mu) < 0:
            c += 1
    return c


def series_stats(rows, key):
    xs = [r[key] for r in rows if key in r]
    if not xs:
        return {}
    mu = statistics.mean(xs)
    n = len(xs)
    return {"n": n, "mean": mu, "min": min(xs), "max": max(xs), "pp": max(xs) - min(xs),
            "var": statistics.pvariance(xs) if n > 1 else 0.0, "crossings": mean_crossings(xs)}


def vol_get():
    try:
        return int(subprocess.check_output(["osascript", "-e", "output volume of (get volume settings)"], text=True).strip())
    except Exception:
        return None


def vol_set(v):
    subprocess.run(["osascript", "-e", "set volume output volume %d" % v], check=False)


def main():
    log = []; orig_vol = vol_get(); ser = None; results = {}
    try:
        ser = serial.Serial(PORT, BAUD, timeout=0.1); ser.dtr = True
        time.sleep(6.0); ser.reset_input_buffer()
        snd(ser, ":version"); ver = ser.read(500).decode(errors="replace")
        log.append("# probe -> %s" % " ".join(ver.split())[:200])
        snd(ser, ":ap_stream=on"); time.sleep(1.0)
        vol_set(VOLUME)
        log.append("# volume=%d (was %s) track=%s LOUD=%ds STEADY_SKIP=%ds" % (VOLUME, orig_vol, TRACK, LOUD_SECS, STEADY_SKIP))

        for mode in MODES:
            snd(ser, ":k1_loud_guard=mode%d" % mode); time.sleep(0.5)
            log.append("### MODE %d ###" % mode)
            t0 = time.time()
            read_lines(ser, SETTLE_SECS, log, "settle%d" % mode, t0)
            audio_t0 = time.time()
            subprocess.Popen(["afplay", TRACK])
            loud = read_lines(ser, LOUD_SECS, log, "loud%d" % mode, audio_t0)
            subprocess.run(["killall", "afplay"], check=False)
            t_stop = time.time()
            rec = read_lines(ser, RECOVERY_SECS, log, "recov%d" % mode, t_stop)
            time.sleep(1.5)

            steady = [r for r in loud if r["t"] >= STEADY_SKIP]
            steady_secs = max(1e-3, LOUD_SECS - STEADY_SKIP)
            rec_time = next((r["t"] for r in rec if r.get("gdft_trim", 0) >= 0.98), None)
            results[mode] = {
                "trim": series_stats(steady, "gdft_trim"),
                "duty": series_stats(steady, "spec_duty"),
                "frac": series_stats(steady, "spec_frac"),
                "peak_pin_max": max((r.get("peak_pin", 0) for r in steady), default=0.0),
                "recovery_s": rec_time,
                "bpm_median": statistics.median([r["bpm"] for r in steady if "bpm" in r]) if any("bpm" in r for r in steady) else None,
                "lock_frac": (sum(int(r.get("lock", 0)) for r in steady) / len(steady)) if steady else None,
                "onset_rate": sum(int(r.get("onset", 0)) for r in steady) / steady_secs,
                "steady_secs": steady_secs,
            }
        snd(ser, ":ap_stream=off")
    finally:
        subprocess.run(["killall", "afplay"], check=False)
        if orig_vol is not None:
            vol_set(orig_vol)
        if ser:
            ser.close()

    ts = time.strftime("%Y-%m-%dT%H%M%S")
    logpath = "/private/tmp/k1_loud_guard_ab_v2_%s.log" % ts
    open(logpath, "w").write("\n".join(log))

    print("=== K1 LOUD-GUARD A/B v2 (10 Hz [AP], vol %d, %s) ===" % (VOLUME, ts))
    print("log: %s" % logpath)
    for m in MODES:
        r = results.get(m, {}); t = r.get("trim", {}); d = r.get("duty", {})
        osc_hz = (t.get("crossings", 0) / 2.0) / r.get("steady_secs", 1)
        print("\n-- MODE %d --  steady=%.0fs  spec_sat engaged=%s (duty max %.3f, frac max %.3f, peak_pin max %.3f)" % (
            m, r.get("steady_secs", 0), (d.get("max", 0) > 0.001), d.get("max", 0), r.get("frac", {}).get("max", 0), r.get("peak_pin_max", 0)))
        print("   gdft_trim: mean %.3f  min %.3f  pp %.3f  var %.4f  crossings %d (~%.2f Hz osc)" % (
            t.get("mean", 0), t.get("min", 0), t.get("pp", 0), t.get("var", 0), t.get("crossings", 0), osc_hz))
        print("   spec_duty: mean %.3f  pp %.3f  var %.4f  crossings %d" % (
            d.get("mean", 0), d.get("pp", 0), d.get("var", 0), d.get("crossings", 0)))
        print("   recovery: %s s | bpm_median %s lock_frac %.2f | onset_rate %.2f/s" % (
            ("%.2f" % r["recovery_s"]) if r.get("recovery_s") is not None else "n/a",
            ("%.1f" % r["bpm_median"]) if r.get("bpm_median") is not None else "n/a",
            r.get("lock_frac") or 0.0, r.get("onset_rate", 0)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
