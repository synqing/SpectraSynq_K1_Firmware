#!/usr/bin/env python3
"""Host-side palette COVERAGE gate (palette-resolution lane, item 6).

Lineage: salvaged from `palette_richness_gate.py` (recoverable at
`git show f23e438:scripts/regression-harness/palette_richness_gate.py`).
That tool was source-only — it parsed Palettes.cpp gradient stops and gated
on static stop statistics (mean saturation, luma span, pure-white stops).
It was removed because it asserted since-reverted palette DATA, not because
the approach was wrong. This successor measures what the firmware actually
RENDERS instead: it drives the real host-compiled render path (render_replay)
with palette_mode enabled and computes colour-distribution metrics from the
rendered LED frames.

WHAT IS (AND IS NOT) COMPUTABLE — be honest about the basis
  The replay harness dumps the final leds_16 working buffer per frame as raw
  RGB bytes (VPABBytesPayload layout). The HD palette sampler coordinate
  (PaletteStopsHD / palette_manual_colour's float hue input in
  visual/lightshow_modes.h) is NOT exposed by the replay output, and this
  tool deliberately does NOT modify firmware to expose it. Therefore:

    * palette-COORDINATE coverage (fraction of the [0,1) sampler space
      visited) is NOT computable here → reported as null.
    * OUTPUT colour coverage IS computable: hue-histogram entropy, hue-bin
      coverage, distinct-colour counts, white fraction, near-black fraction,
      saturation/value statistics — all from the rendered frames.

  These output metrics are a faithful proxy for "how much of the palette the
  effect actually shows", which is the perceptual question the lane cares
  about (a palette can have 16 stops; if the effect only ever samples two of
  them, output coverage is what the eye sees).

MVP CONTRACT (report-only)
  Exit 0 whenever metrics are computed — NO thresholds yet. Thresholds come
  after Captain eyes-on correlates these numbers with perception. Exit 2 only
  on infrastructure failure (no compiler, build error, missing fixture).
  Host metrics RANK and COMPARE; they never certify perceptual acceptance.

USAGE
  python3 scripts/regression-harness/palette_coverage_gate.py \
      --effect bloom --palette 3 [--fixture beat-pulse]

  JSON report → stdout (machine-parseable). Human summary → stderr.
"""

from __future__ import annotations

import argparse
import collections
import colorsys
import hashlib
import json
import math
import sys
import tempfile
from pathlib import Path

HARNESS = Path(__file__).resolve().parent
sys.path.insert(0, str(HARNESS))
import render_replay as rr  # noqa: E402

SCHEMA = "palette-coverage-gate/v1"
DEFAULT_FIXTURE = "beat-pulse"

# Colour-classification constants (output domain, HSV unless noted).
HUE_BINS = 36                 # 10-degree hue resolution
LIT_THRESHOLD = 8             # max(R,G,B) > this → pixel is "lit" (uint8)
WHITE_SAT_MAX = 0.15          # sat <= this AND val >= WHITE_VAL_MIN → white
WHITE_VAL_MIN = 0.80
NEAR_BLACK_MAX = 8            # max(R,G,B) <= this → near-black (uint8)
DESAT_SAT_MAX = 0.20          # sat < this among lit → desaturated
QUANT_BITS = 5                # distinct-colour robustness quantisation


def _decode_frames(hexes):
    """hex frame dumps -> list of frames, each a list of (r, g, b) uint8."""
    frames = []
    for hx in hexes:
        raw = bytes.fromhex(hx)
        frames.append([(raw[i], raw[i + 1], raw[i + 2])
                       for i in range(0, len(raw), 3)])
    return frames


def _plate_hexes(hexes, width=160, height=60):
    """--plate hook: re-render each LED frame through the K1Optics_v1
    PHYSICAL plate model (k1_optics.render_plate) and re-encode the diffused
    plate pixels as hex, so the existing colour metrics measure PLATE
    emission instead of raw strip pixels. Replay frames are single-channel
    today, so the whole frame drives the primary (bottom) edge."""
    import numpy as np
    from k1_optics import render_plate
    out = []
    for frame in _decode_frames(hexes):
        leds = np.asarray(frame, dtype=np.float64) / 255.0
        img = render_plate(leds, None, width=width, height=height)
        out.append(np.clip(img * 255.0 + 0.5, 0, 255)
                   .astype(np.uint8).tobytes().hex())
    return out


def _entropy_bits(counts):
    total = sum(counts)
    if total <= 0:
        return 0.0
    ent = 0.0
    for c in counts:
        if c > 0:
            p = c / total
            ent -= p * math.log2(p)
    return ent


def compute_colour_metrics(hexes):
    """Output-side colour metrics from replay hex frame dumps.

    Pure function: no compilation, no I/O. Returns a dict (see SCHEMA docs in
    the module docstring for the honesty contract on what these measure).
    """
    frames = _decode_frames(hexes)
    led_count = len(frames[0]) if frames else 0
    total_px = sum(len(f) for f in frames)

    hue_hist = [0] * HUE_BINS
    distinct = set()
    distinct_q = set()
    lit = white = near_black = desat = 0
    sat_sum = val_sum = 0.0

    for frame in frames:
        for (r, g, b) in frame:
            mx = max(r, g, b)
            if mx <= NEAR_BLACK_MAX:
                near_black += 1
            if mx <= LIT_THRESHOLD:
                continue
            lit += 1
            distinct.add((r, g, b))
            shift = 8 - QUANT_BITS
            distinct_q.add((r >> shift, g >> shift, b >> shift))
            h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
            sat_sum += s
            val_sum += v
            if s <= WHITE_SAT_MAX and v >= WHITE_VAL_MIN:
                white += 1
            if s < DESAT_SAT_MAX:
                desat += 1
            if s > DESAT_SAT_MAX:           # hue is meaningless when desaturated
                hue_hist[min(int(h * HUE_BINS), HUE_BINS - 1)] += 1

    occupied = sum(1 for c in hue_hist if c > 0)
    return {
        "frames": len(frames),
        "led_count": led_count,
        "total_pixels": total_px,
        "lit_fraction": lit / total_px if total_px else 0.0,
        "near_black_fraction": near_black / total_px if total_px else 0.0,
        "white_fraction": white / lit if lit else 0.0,
        "desaturated_lit_fraction": desat / lit if lit else 0.0,
        "mean_saturation": sat_sum / lit if lit else 0.0,
        "mean_value": val_sum / lit if lit else 0.0,
        "distinct_colour_count": len(distinct),
        "distinct_colour_count_q5": len(distinct_q),
        "hue_bins": HUE_BINS,
        "hue_histogram": hue_hist,
        "hue_bin_coverage": occupied / HUE_BINS,
        "hue_entropy_bits": _entropy_bits(hue_hist),
        "hue_entropy_norm": (_entropy_bits(hue_hist) / math.log2(HUE_BINS))
                            if occupied else 0.0,
        "frames_hash": hashlib.sha256("".join(hexes).encode("ascii")).hexdigest(),
    }


def run_gate(effect, palette_index, fixture=DEFAULT_FIXTURE, binary=None,
             workdir=None, compiler=None, param_overrides=None, plate=False):
    """Build (unless `binary` given), replay the fixture with palette_mode on,
    and return the full report dict. Raises RuntimeError on infra failure."""
    if effect not in rr.MODES:
        raise RuntimeError("unknown effect %r (host modes: %s)"
                           % (effect, ", ".join(sorted(rr.MODES))))
    fx_path = rr.FIXTURE_DIR / (fixture + ".ndjson")
    if not fx_path.exists():
        avail = sorted(p.stem for p in rr.FIXTURE_DIR.glob("*.ndjson"))
        raise RuntimeError("fixture not found: %s (available: %s)"
                           % (fx_path, ", ".join(avail)))

    if binary is None:
        wd = workdir or tempfile.mkdtemp(prefix="palgate_")
        ok, binary, comp = rr.build_binary(str(wd), mode=effect,
                                           compiler=compiler)
        if not ok:
            raise RuntimeError("host build failed: %s"
                               % (comp.get("stderr") or "")[:800])

    params = dict(rr.DEFAULT_PARAMS)
    params.update(param_overrides or {})
    params["palette_mode"] = True
    params["palette_index"] = int(palette_index)

    frames = rr.load_fixture(fx_path)
    ok, hexes, meta = rr.replay_frames(binary, frames, params)
    if not ok or len(hexes) != len(frames):
        raise RuntimeError("replay failed: rc=%s %s"
                           % (meta.get("returncode"),
                              (meta.get("stderr") or "")[:400]))

    return {
        "schema": SCHEMA,
        "effect": effect,
        "fixture": fixture,
        "palette_index": int(palette_index),
        "palette_mode": True,
        "params": params,
        "basis": "k1_optics_plate" if plate else "rendered_rgb_output",
        "palette_coordinate_coverage": None,
        "palette_coordinate_coverage_note": (
            "sampler coordinate (PaletteStopsHD hue input) is not exposed by "
            "the replay output; not computable without firmware edits"),
        "thresholds": None,   # MVP: report-only, no pass/fail
        "metrics": compute_colour_metrics(_plate_hexes(hexes) if plate
                                          else hexes),
    }


def _summary(report, stream=sys.stderr):
    m = report["metrics"]
    print("palette_coverage_gate: effect=%s palette=%d fixture=%s"
          % (report["effect"], report["palette_index"], report["fixture"]),
          file=stream)
    print("  frames=%d leds=%d lit=%.1f%% near_black=%.1f%%"
          % (m["frames"], m["led_count"], 100 * m["lit_fraction"],
             100 * m["near_black_fraction"]), file=stream)
    print("  distinct_colours=%d (q5=%d) hue_bins=%d/%d hue_entropy=%.2f bits"
          % (m["distinct_colour_count"], m["distinct_colour_count_q5"],
             round(m["hue_bin_coverage"] * m["hue_bins"]), m["hue_bins"],
             m["hue_entropy_bits"]), file=stream)
    print("  mean_sat=%.3f mean_val=%.3f white=%.1f%% desat=%.1f%%"
          % (m["mean_saturation"], m["mean_value"],
             100 * m["white_fraction"], 100 * m["desaturated_lit_fraction"]),
          file=stream)
    print("  basis: rendered RGB output (sampler-coordinate coverage not "
          "available from replay output)", file=stream)
    print("  MVP report-only: no thresholds, exit 0", file=stream)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Host-side palette coverage metrics (report-only MVP)")
    ap.add_argument("--effect", default="bloom",
                    help="host replay mode (default: bloom)")
    ap.add_argument("--palette", type=int, required=True,
                    help="palette index (CONFIG.PALETTE_INDEX)")
    ap.add_argument("--fixture", default=DEFAULT_FIXTURE,
                    help="fixture name under fixtures/ (default: %s)"
                         % DEFAULT_FIXTURE)
    ap.add_argument("--compiler", default=None,
                    help="explicit host g++ (default: autodetect)")
    ap.add_argument("--plate", action="store_true",
                    help="compute metrics on K1Optics_v1 PHYSICAL diffused "
                         "plate emission instead of raw LED pixels")
    args = ap.parse_args(argv)

    try:
        report = run_gate(args.effect, args.palette, fixture=args.fixture,
                          compiler=args.compiler, plate=args.plate)
    except RuntimeError as exc:
        json.dump({"schema": SCHEMA, "error": str(exc)}, sys.stdout, indent=2)
        print(file=sys.stdout)
        print("palette_coverage_gate: INFRA ERROR — %s" % exc, file=sys.stderr)
        return 2

    json.dump(report, sys.stdout, indent=2, sort_keys=True)
    print(file=sys.stdout)
    _summary(report)
    return 0   # MVP: report-only, never threshold-fails


if __name__ == "__main__":
    sys.exit(main())
