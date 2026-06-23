#!/usr/bin/env python3
"""gdft_check.py — verify Goertzel bin response via the GDFT synthetic-signal harness.

Drives the firmware GDFT harness (item 22, harness build only) over serial. The
harness injects a pure synthetic sine into the GDFT integration buffer and runs
the UNMODIFIED process_GDFT(), so the response is deterministic and independent
of the acoustic environment — no mic, no audio playback, no calibration.

The argmax is taken from the firmware's RAW per-bin response (magnitudes_normalized[],
GDFT.h:118-119) — no EMA, no AGC gain, no spectral tilt — so a standalone probe at
frequency F reports the SAME bin as the sweep step nearest F, every run.

Like vp_capture.py, the firmware serial layer is a single-char HOTKEY mode by
default; ':' switches to line-command mode (serial_menu.h command_mode). So line
commands MUST be prefixed with ':' and terminated with newline, e.g.
':gdft_probe=1000\\n'.

Three assertions, all FIRMWARE-SELF-REFERENTIAL (no mic-path CANONICAL anchor;
that real-vs-synthetic comparison was wrong and is dropped):

  1. MONOTONIC SWEEP — :gdft_sweep=300,3000,12 argmax bins are monotonically
     non-decreasing. A rising sine sweep must move the peak bin upward.

  2. ABSOLUTE MAPPING — for every probed freq F, the peak bin's OWN Goertzel
     target frequency (bin_freq, reported by the firmware) is the closest of all
     bins to F. The firmware bins are semitone-spaced (88-key piano note table),
     so "closest bin" means F lies within half a semitone of bin_freq, i.e.
     |log2(F / bin_freq)| <= 0.5/12 (+ small margin). This validates absolute
     frequency mapping against the device's OWN table — not a mic measurement.

  3. SELF-CONSISTENCY (determinism) — a standalone :gdft_probe=<F> at the EXACT
     frequency of a sweep step must report the SAME bin as that sweep step. (We
     probe the sweep step nearest 1000 Hz so the two commands inject an identical
     tone; comparing against a different sweep grid frequency would be apples to
     oranges.) This is the test that previously failed (standalone bin 9 vs sweep
     bin 32) before the raw-magnitudes argmax fix.

Usage: gdft_check.py <port> [--baud N] [--reboot] [--settle SEC] [--read SEC] [--out LOG]
Exit:  0 = all three assertions pass
       1 = a captured assertion failed
       2 = no GDFTP lines captured (harness not built / not responding)
"""
import sys, time, os, argparse, re, math

try:
    import serial
except ImportError:
    print("error: pyserial not installed", file=sys.stderr); sys.exit(1)

SWEEP_F0, SWEEP_F1, SWEEP_STEPS = 300.0, 3000.0, 12
DETERMINISM_NEAR_HZ = 1000.0  # we probe the sweep step nearest this for the
                              # apples-to-apples determinism check (not a golden bin)


def sweep_step_freq(i, f0=SWEEP_F0, f1=SWEEP_F1, steps=SWEEP_STEPS):
    """Reproduce the firmware's sweep step frequency (gdft_harness.h gdft_run_sweep):
    f = f0 + (f1-f0) * i/(steps-1)."""
    if steps <= 1:
        return f0
    return f0 + (f1 - f0) * (float(i) / float(steps - 1))

# Firmware bins are one semitone apart (notes[] table). Half a semitone in log2
# space is 0.5/12; allow a small margin for the k-rounding in
# precompute_goertzel_constants (system.h:283) that quantises each bin's actual
# detected frequency to an integer Goertzel k.
SEMITONE_LOG2 = 1.0 / 12.0
ABS_TOL_LOG2 = 0.5 * SEMITONE_LOG2 + 0.10 * SEMITONE_LOG2   # half-step + 10% margin

# GDFTP,probe=<freq>,bin=<argmax>,bin_freq=<target>,chroma_bin=<0-11>,mag=<peak>
GDFTP_RE = re.compile(
    r"GDFTP,probe=(?P<freq>[-+0-9.eE]+),"
    r"bin=(?P<bin>\d+),"
    r"bin_freq=(?P<bin_freq>[-+0-9.eE]+),"
    r"chroma_bin=(?P<chroma>\d+),"
    r"mag=(?P<mag>[-+0-9.eE]+)"
)


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


def capture_block(s, command, read_sec):
    """Send one ':<command>\\n' and collect GDFTP rows between event=start/end.

    Returns (rows, saw_end, all_lines). Each row:
    {freq, bin, bin_freq, chroma, mag}."""
    s.reset_input_buffer()
    s.write((":" + command + "\n").encode()); s.flush()
    rows, saw_start, saw_end, all_lines = [], False, False, []
    deadline = time.time() + read_sec
    while time.time() < deadline:
        raw = s.readline()
        if not raw:
            continue
        line = raw.decode("utf-8", "replace").rstrip("\r\n")
        if not line:
            continue
        all_lines.append(line)
        if line.startswith("GDFTP,") and "event=start" in line:
            saw_start = True
            continue
        if line.startswith("GDFTP,") and "event=end" in line:
            saw_end = True
            break
        m = GDFTP_RE.search(line)
        if m:
            rows.append({
                "freq": float(m.group("freq")),
                "bin": int(m.group("bin")),
                "bin_freq": float(m.group("bin_freq")),
                "chroma": int(m.group("chroma")),
                "mag": float(m.group("mag")),
            })
    return rows, saw_end, all_lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("port")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--reboot", action="store_true")
    ap.add_argument("--settle", type=float, default=7.0)
    ap.add_argument("--read", type=float, default=20.0)
    ap.add_argument("--out", default=None, help="optional raw capture log path")
    a = ap.parse_args()

    s = open_retry(a.port, a.baud)
    if a.reboot:
        s.reset_input_buffer()
        s.write(b":reboot\n"); s.flush()
        time.sleep(1.0)
        s.close()
        time.sleep(4.0)                  # USB re-enumeration window
        s = open_retry(a.port, a.baud)   # device comes back same path
    time.sleep(a.settle)                 # boot + boot_animation
    s.reset_input_buffer()               # drop boot spam + 1 Hz [AP] backlog

    log_lines = []

    # ---- 300..3000 sweep (run first; determines the determinism probe freq) ----
    sweep_rows, sweep_end, sweep_log = capture_block(
        s, "gdft_sweep=%g,%g,%d" % (SWEEP_F0, SWEEP_F1, SWEEP_STEPS), a.read)
    log_lines += sweep_log

    # ---- standalone probe at the EXACT sweep-step frequency nearest 1000 Hz ----
    # Reproduce the firmware's grid host-side so the probe injects a tone identical
    # to one sweep step -> a true determinism check (same input, same output bin?).
    near_i = min(range(SWEEP_STEPS),
                 key=lambda i: abs(sweep_step_freq(i) - DETERMINISM_NEAR_HZ))
    probe_freq = sweep_step_freq(near_i)
    probe_rows, probe_end, probe_log = capture_block(
        s, "gdft_probe=%g" % probe_freq, a.read)
    log_lines += probe_log

    s.close()

    if a.out:
        try:
            with open(a.out, "w") as f:
                f.write("\n".join(log_lines) + "\n")
        except Exception as e:
            print("warn: could not write log %s: %s" % (a.out, e), file=sys.stderr)

    if not probe_rows and not sweep_rows:
        print("FAIL: no GDFTP lines captured — harness not built (ENABLE_GDFT_HARNESS) "
              "or device not responding", file=sys.stderr)
        return 2

    ok = True

    # ---- Assertion 1: rising sweep -> monotonically non-decreasing argmax bins ----
    if not sweep_rows:
        print("FAIL: sweep produced no GDFTP lines", file=sys.stderr)
        ok = False
    else:
        bins = [r["bin"] for r in sweep_rows]
        seq = " ".join("%.0f->%d" % (r["freq"], r["bin"]) for r in sweep_rows)
        monotonic = all(bins[i] <= bins[i + 1] for i in range(len(bins) - 1))
        if monotonic:
            print("PASS [monotonic]: sweep argmax bins non-decreasing: %s" % seq,
                  file=sys.stderr)
        else:
            print("FAIL [monotonic]: sweep argmax bins NOT non-decreasing: %s" % seq,
                  file=sys.stderr)
            ok = False

    # ---- Assertion 2: absolute mapping — bin_freq is the closest bin to F ----
    # Firmware-self-referential: F must be within half a semitone of the reported
    # peak-bin target frequency. Checked over the union of all probe + sweep rows.
    abs_rows = list(probe_rows) + list(sweep_rows)
    abs_fail = []
    for r in abs_rows:
        f, bf = r["freq"], r["bin_freq"]
        if bf <= 0.0 or f <= 0.0:
            abs_fail.append((f, r["bin"], bf, float("inf")))
            continue
        dist_log2 = abs(math.log2(f / bf))
        if dist_log2 > ABS_TOL_LOG2:
            abs_fail.append((f, r["bin"], bf, dist_log2))
    if not abs_rows:
        print("FAIL [absolute]: no rows to check", file=sys.stderr)
        ok = False
    elif abs_fail:
        for f, b, bf, d in abs_fail:
            cents = d * 1200.0 if math.isfinite(d) else float("inf")
            print("FAIL [absolute]: F=%.1f bin=%d bin_freq=%.2f off by %.0f cents "
                  "(> %.0f cents)" % (f, b, bf, cents, ABS_TOL_LOG2 * 1200.0),
                  file=sys.stderr)
        ok = False
    else:
        worst = max(abs(math.log2(r["freq"] / r["bin_freq"])) for r in abs_rows) * 1200.0
        print("PASS [absolute]: all %d probes within half a semitone of their peak "
              "bin's target (worst %.0f cents, tol %.0f cents)"
              % (len(abs_rows), worst, ABS_TOL_LOG2 * 1200.0), file=sys.stderr)

    # ---- Assertion 3: self-consistency — standalone probe == matching sweep step ----
    # The standalone probe was issued at probe_freq, the EXACT frequency of one
    # sweep step. Match against that sweep step (same injected tone) by frequency.
    if not probe_rows:
        print("FAIL [self-consistency]: standalone probe produced no GDFTP line",
              file=sys.stderr)
        ok = False
    elif not sweep_rows:
        print("FAIL [self-consistency]: no sweep rows to compare against",
              file=sys.stderr)
        ok = False
    else:
        probe_bin = probe_rows[-1]["bin"]
        match = min(sweep_rows, key=lambda r: abs(r["freq"] - probe_freq))
        if probe_bin == match["bin"]:
            print("PASS [self-consistency]: standalone probe(%.1f Hz)=bin %d == "
                  "matching sweep step(%.1f Hz)=bin %d"
                  % (probe_freq, probe_bin, match["freq"], match["bin"]),
                  file=sys.stderr)
        else:
            print("FAIL [self-consistency]: standalone probe(%.1f Hz)=bin %d != "
                  "matching sweep step(%.1f Hz)=bin %d (nondeterministic probe)"
                  % (probe_freq, probe_bin, match["freq"], match["bin"]),
                  file=sys.stderr)
            ok = False

    print("probe_rows=%d sweep_rows=%d probe_end=%s sweep_end=%s"
          % (len(probe_rows), len(sweep_rows), probe_end, sweep_end), file=sys.stderr)

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
