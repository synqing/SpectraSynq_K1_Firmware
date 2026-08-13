#!/usr/bin/env python3
"""Palette-derived hue reference for the colour fix lane (2026-08-13).

Parses the AUTHORED palette definitions (visual/Palettes.cpp gradient tables,
ordered by the visual/Palettes.h registry) and emits, per palette index, the
authored hue-bucket set and authored entropy. This is the metric's EXTERNAL
denominator (completeness-claim rule): "full spectrum within each palette"
is measured against what the palette author actually put in the palette —
never against the render output being judged.

Usage:
  palette_reference.py generate [--json PATH]   # parse firmware source → reference
  palette_reference.py show <index>             # print one palette's reference
  palette_reference.py self-test                # fault battery

Consumed by hue_coverage.py (compare deployed hue buckets vs authored).
Buckets/thresholds are IDENTICAL to hue_coverage.py / the firmware taps so all
instruments agree by construction.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
PALETTES_CPP = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "visual" / "Palettes.cpp"
PALETTES_H = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "visual" / "Palettes.h"
DEFAULT_JSON = Path(__file__).parent / "results" / "palette_reference.json"

HUE_BUCKETS = 24
SAMPLES = 256           # gradient interpolation resolution
MASS_FLOOR = 0.02       # bucket "authored" if >= 2% of chromatic mass


def parse_gradients(cpp_text: str) -> dict[str, list[tuple[int, int, int, int]]]:
    """name -> [(pos, r, g, b), ...] from DEFINE_GRADIENT_PALETTE blocks."""
    out: dict[str, list[tuple[int, int, int, int]]] = {}
    for m in re.finditer(
            r"DEFINE_GRADIENT_PALETTE\((\w+)\)\s*\{([^}]*)\}", cpp_text, re.S):
        name, body = m.group(1), m.group(2)
        nums = [int(x) for x in re.findall(r"-?\d+", body)]
        if len(nums) % 4 != 0 or not nums:
            raise ValueError(f"{name}: entry count {len(nums)} not divisible by 4")
        entries = [tuple(nums[i:i + 4]) for i in range(0, len(nums), 4)]
        if entries[0][0] != 0 or entries[-1][0] != 255:
            raise ValueError(f"{name}: gradient must span 0..255")
        out[name] = entries  # type: ignore[assignment]
    return out


def parse_registry(h_text: str) -> list[str]:
    m = re.search(r"gGradientPalettes\[\]\s*=\s*\{([^}]*)\}", h_text, re.S)
    if not m:
        raise ValueError("gGradientPalettes registry not found in Palettes.h")
    return re.findall(r"(\w+_gp)", m.group(1))


def interpolate(entries, samples: int = SAMPLES) -> np.ndarray:
    """Linear interpolation of the authored gradient at `samples` points → [N,3] u8."""
    pos = np.array([e[0] for e in entries], dtype=np.float64)
    rgb = np.array([[e[1], e[2], e[3]] for e in entries], dtype=np.float64)
    xs = np.linspace(0.0, 255.0, samples)
    out = np.stack([np.interp(xs, pos, rgb[:, c]) for c in range(3)], axis=1)
    return np.clip(np.round(out), 0, 255).astype(np.uint8)


def hue_profile(rgb: np.ndarray) -> dict:
    """Authored hue histogram with the instrument-identical chromatic gate."""
    r = rgb[:, 0].astype(np.int16)
    g = rgb[:, 1].astype(np.int16)
    b = rgb[:, 2].astype(np.int16)
    mx = np.max(rgb, axis=1).astype(np.int16)
    mn = np.min(rgb, axis=1).astype(np.int16)
    d = mx - mn
    chromatic = (mx > 2) & (d >= 8)
    hist = np.zeros(HUE_BUCKETS, dtype=np.float64)
    if chromatic.any():
        rc, gc, bc = r[chromatic], g[chromatic], b[chromatic]
        mxc, dc = mx[chromatic], d[chromatic]
        h = np.where(mxc == rc, (43 * (gc - bc)) // dc,
                     np.where(mxc == gc, 85 + (43 * (bc - rc)) // dc,
                              171 + (43 * (rc - gc)) // dc)).astype(np.int16)
        h = np.where(h < 0, h + 256, h)
        buckets = (h.astype(np.uint16) * HUE_BUCKETS) >> 8
        np.add.at(hist, np.clip(buckets, 0, HUE_BUCKETS - 1), 1.0)
    total = hist.sum()
    if total > 0:
        p = hist / total
        authored = [int(i) for i in np.where(p >= MASS_FLOOR)[0]]
        nz = p[p > 0]
        entropy = float(-(nz * np.log2(nz)).sum())
    else:
        authored, entropy = [], 0.0
    return {
        "hist": [round(float(x), 1) for x in hist],
        "authored_buckets": authored,
        "authored_coverage": round(len(authored) / HUE_BUCKETS, 4),
        "authored_entropy_bits": round(entropy, 4),
        "chromatic_fraction": round(float(chromatic.mean()), 4),
    }


def generate() -> dict:
    grads = parse_gradients(PALETTES_CPP.read_text(encoding="utf-8"))
    order = parse_registry(PALETTES_H.read_text(encoding="utf-8"))
    missing = [n for n in order if n not in grads]
    if missing:
        raise SystemExit(f"registry names without definitions: {missing}")
    palettes = []
    for idx, name in enumerate(order):
        prof = hue_profile(interpolate(grads[name]))
        palettes.append({"index": idx, "name": name, **prof})
    return {
        "source": "SPECTRASYNQ_K1_FIRMWARE/visual/Palettes.cpp + Palettes.h registry",
        "hue_buckets": HUE_BUCKETS,
        "samples": SAMPLES,
        "mass_floor": MASS_FLOOR,
        "count": len(palettes),
        "palettes": palettes,
    }


def self_test() -> int:
    failures = 0

    def check(name, cond, detail):
        nonlocal failures
        print(f"[{'GREEN' if cond else 'RED'}] {name}: {detail}")
        if not cond:
            failures += 1

    # Case 1: pure single-hue synthetic gradient → exactly one authored bucket.
    prof = hue_profile(interpolate([(0, 255, 0, 0), (255, 128, 0, 0)]))
    check("single-hue", prof["authored_buckets"] == [0],
          f"buckets={prof['authored_buckets']}")

    # Case 2: full rainbow synthetic → high authored coverage.
    rainbow = []
    for i in range(13):
        h = i / 12.0
        r = int(255 * max(0, min(1, abs(h * 6 - 3) - 1)))
        g = int(255 * max(0, min(1, 2 - abs(h * 6 - 2))))
        b = int(255 * max(0, min(1, 2 - abs(h * 6 - 4))))
        rainbow.append((round(i * 255 / 12), r, g, b))
    prof = hue_profile(interpolate(rainbow))
    check("rainbow-coverage", prof["authored_coverage"] >= 0.75,
          f"coverage={prof['authored_coverage']}")

    # Case 3 (must go RED if the gate is blind): a black gradient authors nothing.
    prof = hue_profile(interpolate([(0, 0, 0, 0), (255, 2, 2, 2)]))
    check("black-authors-nothing", prof["authored_buckets"] == [],
          f"buckets={prof['authored_buckets']}")

    # Case 4: the REAL firmware source parses, count matches the registry, and a
    # known palette (ib_jul01: reds + a green mid) spans red and green regions.
    ref = generate()
    check("real-source-count", ref["count"] >= 40, f"count={ref['count']}")
    ib = next(p for p in ref["palettes"] if p["name"] == "ib_jul01_gp")
    has_red = any(b in (0, 1, 23) for b in ib["authored_buckets"])
    has_green = any(5 <= b <= 11 for b in ib["authored_buckets"])
    check("ib_jul01-red-and-green", has_red and has_green,
          f"buckets={ib['authored_buckets']}")

    # Case 5: malformed gradient rejected loudly.
    try:
        parse_gradients("DEFINE_GRADIENT_PALETTE(bad_gp){ 0, 1, 2 };")
        check("malformed-rejected", False, "no exception raised")
    except ValueError:
        check("malformed-rejected", True, "ValueError as expected")

    print(f"self-test: {'PASS' if failures == 0 else f'FAIL ({failures} red)'}")
    return 1 if failures else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate")
    g.add_argument("--json", default=str(DEFAULT_JSON))
    s = sub.add_parser("show")
    s.add_argument("index", type=int)
    sub.add_parser("self-test")
    args = ap.parse_args()

    if args.cmd == "self-test":
        return self_test()
    ref = generate()
    if args.cmd == "show":
        for p in ref["palettes"]:
            if p["index"] == args.index:
                print(json.dumps(p, indent=1))
                return 0
        print(f"no palette index {args.index}", file=sys.stderr)
        return 2
    out = Path(args.json)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(ref, indent=1) + "\n")
    print(f"wrote {out} ({ref['count']} palettes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
