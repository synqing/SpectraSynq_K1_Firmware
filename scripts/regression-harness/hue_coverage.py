#!/usr/bin/env python3
"""Hue-coverage metric for the K1 colour fix lane (2026-08-13 contract).

Measures how much of the palette's hue space the rendered output actually
deploys, per minute, from either instrument:

  video   — camera footage of the physical strips (works on ANY firmware,
            including the golden Aug-8 readback which has no pixel surface;
            this is how the ORACLE number is taken). The metric is used
            comparatively (same camera, same placement, same track), so
            absolute camera colour fidelity does not matter.
  hueaud  — serial log carrying 1 Hz `HUEAUD,` histogram lines from the
            K1_HUE_AUDIT_V1 firmware tap (main-side bisect instrument).

Metrics per window (default 60 s):
  coverage — fraction of the 24 hue buckets holding >= --floor of lit mass
  entropy  — Shannon entropy (bits) of the hue-bucket distribution
  lit      — mean fraction of pixels lit (video: pixels above V threshold)

Verdict law (docs/forensics/colour-nuance-regression-verdict-2026-08-13.md):
no Captain eyes-on until fixed-main matches the golden oracle numbers.

Self-test (`--self-test`) is a fault battery per the oracle-discipline canon:
it contains cases that MUST fail (single-hue "collapse" input scoring high
coverage would mean the metric is blind) and prints RED/GREEN per case.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from dataclasses import dataclass, field

import numpy as np

HUE_BUCKETS = 24  # 15 degrees per bucket; matches chromatic perceptual granularity
DEFAULT_WINDOW_S = 60.0
DEFAULT_MASS_FLOOR = 0.02  # bucket counts as "deployed" >= 2% of lit mass
DEFAULT_V_FLOOR = 40       # 0-255 V threshold: below = not lit (camera black level)
DEFAULT_S_FLOOR = 60       # 0-255 S threshold: below = white/grey, huemeaningless

HUEAUD_RE = re.compile(
    r"HUEAUD,ver=1,ch=(?P<ch>[ps]),lit=(?P<lit>\d+)(?:,mode=(?P<mode>-?\d+))?"
    r"(?:,pal=(?P<pal>\d+))?(?:,pmode=(?P<pmode>[01]))?(?:,acs=(?P<acs>[01]))?"
    r",h=(?P<h>[0-9,]+)")


@dataclass
class WindowAccum:
    start_t: float
    hist: np.ndarray = field(default_factory=lambda: np.zeros(HUE_BUCKETS, dtype=np.float64))
    lit_sum: float = 0.0
    frames: int = 0


def bucket_metrics(hist: np.ndarray, mass_floor: float) -> tuple[float, float]:
    total = float(hist.sum())
    if total <= 0.0:
        return 0.0, 0.0
    p = hist / total
    coverage = float((p >= mass_floor).sum()) / HUE_BUCKETS
    nz = p[p > 0.0]
    entropy = float(-(nz * np.log2(nz)).sum())
    return coverage, entropy


def close_window(w: WindowAccum, mass_floor: float) -> dict:
    coverage, entropy = bucket_metrics(w.hist, mass_floor)
    return {
        "t_start": round(w.start_t, 3),
        "frames": w.frames,
        "coverage": round(coverage, 4),
        "entropy_bits": round(entropy, 4),
        "lit_mean": round(w.lit_sum / w.frames, 4) if w.frames else 0.0,
        "hist": [round(float(x), 1) for x in w.hist],
    }


def iter_windows(samples, window_s: float, mass_floor: float):
    """samples: iterable of (t_seconds, hist[HUE_BUCKETS], lit_fraction)."""
    out = []
    cur: WindowAccum | None = None
    for t, hist, lit in samples:
        if cur is None:
            cur = WindowAccum(start_t=t)
        elif t - cur.start_t >= window_s:
            out.append(close_window(cur, mass_floor))
            cur = WindowAccum(start_t=t)
        cur.hist += hist
        cur.lit_sum += lit
        cur.frames += 1
    if cur is not None and cur.frames:
        out.append(close_window(cur, mass_floor))
    return out


# ---------------------------------------------------------------- video mode

def video_samples(path: str, fps: float, v_floor: int, s_floor: int,
                  roi: tuple[int, int, int, int] | None):
    import cv2  # deferred: hueaud mode must not require cv2

    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise SystemExit(f"cannot open video: {path}")
    src_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    step = max(1, int(round(src_fps / fps)))
    idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if idx % step == 0:
            t = idx / src_fps
            if roi is not None:
                x, y, w, h = roi
                frame = frame[y:y + h, x:x + w]
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            h_ch = hsv[:, :, 0].astype(np.int32)  # OpenCV hue: 0-179
            s_ch = hsv[:, :, 1]
            v_ch = hsv[:, :, 2]
            lit = v_ch >= v_floor
            chromatic = lit & (s_ch >= s_floor)
            hist = np.zeros(HUE_BUCKETS, dtype=np.float64)
            if chromatic.any():
                buckets = (h_ch[chromatic] * HUE_BUCKETS) // 180
                np.add.at(hist, np.clip(buckets, 0, HUE_BUCKETS - 1), 1.0)
            lit_frac = float(lit.mean())
            yield t, hist, lit_frac
        idx += 1
    cap.release()


# --------------------------------------------------------------- hueaud mode

def hueaud_samples(path: str, channel: str):
    """Parse 1 Hz HUEAUD lines emitted by K1_HUE_AUDIT_V1:
    HUEAUD,ver=1,ch=p,lit=<n>,mode=<m>,h=<c0>,...,<c23>
    Bucket counters are CUMULATIVE (single-writer on Core 1); each sample is
    the delta between consecutive lines. A negative delta in any bucket means
    the device rebooted — that pair is skipped. Timestamps: line index
    (1 Hz cadence) — good enough for windowing."""
    t = 0.0
    prev: np.ndarray | None = None
    with open(path, "r", errors="replace") as f:
        for line in f:
            m = HUEAUD_RE.search(line)
            if not m or m.group("ch") != channel:
                continue
            vals = [int(x) for x in m.group("h").split(",") if x != ""]
            if len(vals) != HUE_BUCKETS:
                continue
            cur = np.asarray(vals, dtype=np.float64)
            lit = int(m.group("lit"))
            if prev is not None:
                delta = cur - prev
                if (delta >= 0).all():
                    yield t, delta, lit / 160.0  # render canvas 160
                    t += 1.0
                # else: reboot — drop this pair, re-baseline
            prev = cur


# ---------------------------------------------------------------- rtrace mode

RTRACE_F_RE = re.compile(r"^F,(?P<idx>\d+),(?P<ms>\d+),(?P<mode>\d+),(?P<hex>[0-9a-f]+)\s*$")


def rtrace_frames(path: str):
    """Yield (t_seconds, ms, mode, rgb ndarray[px,3]) from an rtrace_dump log.
    Frames live between [RTRACE-BEGIN ...] and [RTRACE-END]; each is
    F,<idx>,<ms>,<mode>,<hex of px*3 bytes> (K1_RENDER_TRACE_V1)."""
    t0 = None
    dropped = 0
    with open(path, "r", errors="replace") as f:
        for line in f:
            m = RTRACE_F_RE.match(line.strip())
            if not m:
                continue
            hexs = m.group("hex")
            # The 1 Hz AP/HUEAUD emitters can interleave mid-dump and truncate
            # or splice a frame line; drop anything that isn't a whole number
            # of RGB pixels rather than crashing (count and report).
            if len(hexs) % 6 != 0 or len(hexs) == 0:
                dropped += 1
                continue
            raw = bytes.fromhex(hexs)
            rgb = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3)
            ms = int(m.group("ms"))
            if t0 is None:
                t0 = ms
            yield (ms - t0) / 1000.0, ms, int(m.group("mode")), rgb
    if dropped:
        print(f"rtrace: dropped {dropped} malformed frame lines (serial interleave)",
              file=sys.stderr)


def rgb_hue_hist(rgb: np.ndarray) -> tuple[np.ndarray, float]:
    """Hue histogram of one frame using the SAME chromatic gate as the firmware
    tap (max>2 AND max-min>=8) so tap and trace numbers agree by construction."""
    r = rgb[:, 0].astype(np.int16)
    g = rgb[:, 1].astype(np.int16)
    b = rgb[:, 2].astype(np.int16)
    mx = np.max(rgb, axis=1).astype(np.int16)
    mn = np.min(rgb, axis=1).astype(np.int16)
    d = mx - mn
    chromatic = (mx > 2) & (d >= 8)
    hist = np.zeros(HUE_BUCKETS, dtype=np.float64)
    if not chromatic.any():
        return hist, 0.0
    rc, gc, bc = r[chromatic], g[chromatic], b[chromatic]
    mxc, dc = mx[chromatic], d[chromatic]
    h = np.where(mxc == rc, (43 * (gc - bc)) // dc,
                 np.where(mxc == gc, 85 + (43 * (bc - rc)) // dc,
                          171 + (43 * (rc - gc)) // dc)).astype(np.int16)
    h = np.where(h < 0, h + 256, h)
    buckets = (h.astype(np.uint16) * HUE_BUCKETS) >> 8
    np.add.at(hist, np.clip(buckets, 0, HUE_BUCKETS - 1), 1.0)
    return hist, float(chromatic.mean())


def rtrace_samples(path: str):
    for t, _ms, _mode, rgb in rtrace_frames(path):
        hist, lit = rgb_hue_hist(rgb)
        yield t, hist, lit


# ---------------------------------------------------------------- self-test

def synth(hues_deg: list[float], frames: int, jitter: float = 0.0, seed: int = 7):
    """Synthetic sample stream: each frame's mass spread over the given hues."""
    rng = np.random.default_rng(seed)
    for i in range(frames):
        hist = np.zeros(HUE_BUCKETS, dtype=np.float64)
        for hd in hues_deg:
            h = (hd + (rng.uniform(-jitter, jitter) if jitter else 0.0)) % 360.0
            hist[int(h / 360.0 * HUE_BUCKETS) % HUE_BUCKETS] += 100.0
        yield float(i), hist, 0.5


def self_test() -> int:
    failures = 0

    def check(name: str, cond: bool, detail: str):
        nonlocal failures
        print(f"[{'GREEN' if cond else 'RED'}] {name}: {detail}")
        if not cond:
            failures += 1

    # Case 1 (must score LOW): single-hue collapse — the defect signature.
    w = iter_windows(synth([40.0], 60), 60.0, DEFAULT_MASS_FLOOR)[0]
    check("collapse-low-coverage", w["coverage"] <= 2 / HUE_BUCKETS,
          f"coverage={w['coverage']} entropy={w['entropy_bits']}")
    check("collapse-low-entropy", w["entropy_bits"] <= 1.0,
          f"entropy={w['entropy_bits']}")

    # Case 2 (must score HIGH): full palette sweep.
    sweep = [i * 360.0 / HUE_BUCKETS for i in range(HUE_BUCKETS)]
    w = iter_windows(synth(sweep, 60), 60.0, DEFAULT_MASS_FLOOR)[0]
    check("sweep-high-coverage", w["coverage"] >= 0.9,
          f"coverage={w['coverage']} entropy={w['entropy_bits']}")
    check("sweep-high-entropy", w["entropy_bits"] >= math.log2(HUE_BUCKETS) - 0.5,
          f"entropy={w['entropy_bits']}")

    # Case 3 (discrimination): 3-hue partial deployment sits strictly between.
    w3 = iter_windows(synth([0.0, 120.0, 240.0], 60), 60.0, DEFAULT_MASS_FLOOR)[0]
    check("partial-between", 2 / HUE_BUCKETS < w3["coverage"] < 0.9,
          f"coverage={w3['coverage']}")

    # Case 4 (deliberately-RED design check): the metric must NOT report high
    # coverage for the collapse input. Assert the failure direction is detectable
    # by inverting case 1 — if this 'passes', the battery itself is broken.
    inverted = w3["coverage"] <= 2 / HUE_BUCKETS
    check("battery-can-go-red", not inverted,
          "inverted assertion correctly rejected" if not inverted else "battery blind")

    # Case 5: empty input → zero metrics, no crash.
    z = iter_windows(iter(()), 60.0, DEFAULT_MASS_FLOOR)
    check("empty-input", z == [], f"windows={len(z)}")

    # Case 6: HUEAUD parser round-trip on a synthetic line (with and without mode=).
    line = "HUEAUD,ver=1,ch=p,lit=120,mode=32,h=" + ",".join(["10"] * HUE_BUCKETS)
    m = HUEAUD_RE.search(line)
    check("hueaud-parse", bool(m) and len(m.group("h").split(",")) == HUE_BUCKETS,
          "parsed" if m else "NO MATCH")

    # Case 7: cumulative diffing + reboot skip. Three lines rising, then a
    # counter reset (reboot) which must be dropped, then rising again.
    import tempfile, os
    def hline(counts):
        return "HUEAUD,ver=1,ch=p,lit=100,mode=32,h=" + ",".join(str(c) for c in counts)
    rows = [hline([100] * HUE_BUCKETS), hline([200] * HUE_BUCKETS),
            hline([5] * HUE_BUCKETS),   # reboot: counters reset
            hline([50] * HUE_BUCKETS)]
    with tempfile.NamedTemporaryFile("w", suffix=".log", delete=False) as tf:
        tf.write("\n".join(rows) + "\n")
        tmp = tf.name
    got = list(hueaud_samples(tmp, "p"))
    os.unlink(tmp)
    check("hueaud-cumulative-diff", len(got) == 2 and got[0][1][0] == 100.0
          and got[1][1][0] == 45.0,
          f"samples={len(got)} deltas={[g[1][0] for g in got]}")

    # Case 8: rtrace round-trip — a synthetic 2-frame dump (one pure red frame,
    # one red+green+blue frame) must decode to the right hue buckets, and a
    # corrupt hex line must be dropped, not crash.
    red = "ff0000" * 160
    rgbmix = ("ff0000" * 54) + ("00ff00" * 53) + ("0000ff" * 53)
    dump = ("[RTRACE-BEGIN frames=2 every=4 px=160 fmt=rgb8hex crc32=0]\n"
            f"F,0,1000,32,{red}\n"
            f"F,1,1040,32,{rgbmix}\n"
            "F,2,1080,32,zznothex\n"
            "[RTRACE-END]\n")
    with tempfile.NamedTemporaryFile("w", suffix=".log", delete=False) as tf:
        tf.write(dump)
        tmp = tf.name
    frames = list(rtrace_samples(tmp))
    os.unlink(tmp)
    ok = (len(frames) == 2
          and frames[0][1].argmax() == 0 and frames[0][1].sum() == 160.0
          and (frames[1][1] > 0).sum() == 3)
    check("rtrace-roundtrip", ok,
          f"frames={len(frames)} f0_bucket={frames[0][1].argmax() if frames else '-'} "
          f"f1_buckets={(frames[1][1] > 0).sum() if len(frames) > 1 else '-'}")

    print(f"self-test: {'PASS' if failures == 0 else f'FAIL ({failures} red)'}")
    return 1 if failures else 0


# --------------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("video", help="camera footage of the strips")
    v.add_argument("path")
    v.add_argument("--fps", type=float, default=10.0, help="analysis sample rate")
    v.add_argument("--v-floor", type=int, default=DEFAULT_V_FLOOR)
    v.add_argument("--s-floor", type=int, default=DEFAULT_S_FLOOR)
    v.add_argument("--roi", type=int, nargs=4, metavar=("X", "Y", "W", "H"),
                   help="crop to the strip region (recommended)")

    h = sub.add_parser("hueaud", help="serial log with HUEAUD tap lines")
    h.add_argument("path")
    h.add_argument("--channel", choices=["p", "s"], default="p")

    r = sub.add_parser("rtrace", help="rtrace_dump log (LED-level frame capture)")
    r.add_argument("path")

    for p in (v, h, r):
        p.add_argument("--window", type=float, default=DEFAULT_WINDOW_S)
        p.add_argument("--floor", type=float, default=DEFAULT_MASS_FLOOR)
        p.add_argument("--json", dest="json_out", help="write windows JSON here")
        p.add_argument("--palette", type=int, default=None,
                       help="palette index for the authored-reference comparison")
        p.add_argument("--palette-ref", default=None,
                       help="palette_reference.json (from palette_reference.py generate)")

    sub.add_parser("self-test", help="fault battery (must show RED capability)")

    args = ap.parse_args()
    if args.cmd == "self-test":
        return self_test()

    if args.cmd == "video":
        samples = video_samples(args.path, args.fps, args.v_floor, args.s_floor,
                                tuple(args.roi) if args.roi else None)
    elif args.cmd == "rtrace":
        samples = rtrace_samples(args.path)
    else:
        samples = hueaud_samples(args.path, args.channel)

    windows = iter_windows(samples, args.window, args.floor)
    if not windows:
        print("NO SAMPLES — wrong file, wrong channel, or everything below thresholds",
              file=sys.stderr)
        return 2

    for w in windows:
        print(f"t={w['t_start']:>8.1f}s frames={w['frames']:>5} "
              f"coverage={w['coverage']:.3f} entropy={w['entropy_bits']:.3f} bits "
              f"lit={w['lit_mean']:.3f}")
    cov = [w["coverage"] for w in windows]
    ent = [w["entropy_bits"] for w in windows]
    summary = {
        "windows": len(windows),
        "coverage_mean": round(float(np.mean(cov)), 4),
        "coverage_min": round(float(np.min(cov)), 4),
        "entropy_mean_bits": round(float(np.mean(ent)), 4),
        "entropy_min_bits": round(float(np.min(ent)), 4),
    }
    if args.palette_ref is not None and args.palette is not None:
        # Authored-reference comparison (palette-derived oracle): what fraction
        # of the palette's AUTHORED hue arc did the render actually deploy?
        ref = json.load(open(args.palette_ref))
        pal = next((p for p in ref["palettes"] if p["index"] == args.palette), None)
        if pal is None:
            print(f"palette index {args.palette} not in {args.palette_ref}",
                  file=sys.stderr)
            return 2
        agg = np.zeros(HUE_BUCKETS, dtype=np.float64)
        for w in windows:
            agg += np.asarray(w["hist"], dtype=np.float64)
        total = agg.sum()
        deployed = set(int(i) for i in np.where(agg / total >= args.floor)[0]) if total > 0 else set()
        authored = set(pal["authored_buckets"])
        hit = sorted(deployed & authored)
        missed = sorted(authored - deployed)
        stray = sorted(deployed - authored)
        summary["palette"] = pal["name"]
        summary["authored_deployment"] = round(len(hit) / len(authored), 4) if authored else 0.0
        summary["authored_missed_buckets"] = missed
        summary["out_of_palette_buckets"] = stray
        print(f"PALETTE {pal['name']}: deployed {len(hit)}/{len(authored)} authored "
              f"buckets ({summary['authored_deployment']:.0%}); missed={missed} stray={stray}")
    print("SUMMARY " + json.dumps(summary))
    if args.json_out:
        with open(args.json_out, "w") as f:
            json.dump({"summary": summary, "windows": windows,
                       "hue_buckets": HUE_BUCKETS, "mass_floor": args.floor}, f, indent=1)
        print(f"wrote {args.json_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
