#!/usr/bin/env python3
"""mirex_rescore.py — adversarial MIREX de-inflation re-scorer (BT-SCALE).

Reads the committed per-track CSV (docs/measurements/tempo-octave-baseline.tracks.csv)
and re-scores with:
  (A) repo-wide forgiveness set {1/3, 1/2, 1, 2, 3}  — reproduces the headline figures
  (B) MIREX-standard forgiveness set {1/2, 1, 2}       — de-inflated
at both ±4% and ±8% relative Acc1 tolerance.

Prints a comparison table and exits 0.  No firmware edit, no flash, no commit.

Run:
    python3 scripts/regression-harness/mirex_rescore.py
    python3 scripts/regression-harness/mirex_rescore.py --csv <path/to/tracks.csv>
"""
import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CSV = ROOT / "docs/measurements/tempo-octave-baseline.tracks.csv"


def score_row(det: float, gt: float, tol: float, octaves: list[float]) -> tuple[bool, bool]:
    acc1 = abs(det - gt) / gt <= tol
    errs = [abs(det - k * gt) / (k * gt) for k in octaves]
    acc2 = min(errs) <= tol
    return acc1, acc2


def calc_stats(
    subset: list[dict], tol: float, octaves: list[float]
) -> tuple[float, float]:
    a1 = sum(1 for r in subset if score_row(r["det"], r["gt"], tol, octaves)[0])
    a2 = sum(1 for r in subset if score_row(r["det"], r["gt"], tol, octaves)[1])
    n = len(subset)
    return (a1 / n * 100, a2 / n * 100) if n else (0.0, 0.0)


def main() -> None:
    parser = argparse.ArgumentParser(description="MIREX de-inflation re-scorer")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    args = parser.parse_args()

    if not args.csv.exists():
        sys.exit(f"ERROR: CSV not found: {args.csv}")

    rows_raw = list(csv.DictReader(args.csv.open()))
    all_rows = [
        {
            "gt": float(r["gt_bpm"]),
            "det": float(r["det_bpm"]),
            "in_range": r["in_range"].strip().lower() == "true",
        }
        for r in rows_raw
    ]
    inrange = [r for r in all_rows if r["in_range"]]
    n_all = len(all_rows)
    n_inr = len(inrange)

    WIDE = [1.0 / 3.0, 0.5, 1.0, 2.0, 3.0]   # repo set
    MIREX = [0.5, 1.0, 2.0]                    # MIREX standard

    configs = [
        ("Wide {1/3,1/2,1,2,3} ±4% (repo)", 0.04, WIDE),
        ("MIREX {1/2,1,2}       ±4%       ", 0.04, MIREX),
        ("MIREX {1/2,1,2}       ±8%       ", 0.08, MIREX),
    ]

    header = f"{'Scorer':<38} | {'Acc1-all':>8} {'Acc2-all':>8} | {'Acc1-inr':>8} {'Acc2-inr':>8}"
    print(f"\n{'='*len(header)}")
    print(f"Corpus: {args.csv.name}  |  n={n_all} total, {n_inr} in-range [60-155 BPM]")
    print("=" * len(header))
    print(header)
    print("-" * len(header))

    for label, tol, octaves in configs:
        a1_all, a2_all = calc_stats(all_rows, tol, octaves)
        a1_inr, a2_inr = calc_stats(inrange, tol, octaves)
        print(
            f"{label:<38} | {a1_all:>7.1f}% {a2_all:>7.1f}% | {a1_inr:>7.1f}% {a2_inr:>7.1f}%"
        )

    print("=" * len(header))

    # Inflation check: tracks that only pass Acc2 via x1/3 or x3
    inflate_only = [
        r for r in all_rows
        if score_row(r["det"], r["gt"], 0.04, WIDE)[1]
        and not score_row(r["det"], r["gt"], 0.04, MIREX)[1]
    ]
    print(f"\nInflation-only tracks (Acc2 passes wide but not MIREX): {len(inflate_only)}/{n_all}")
    for r in inflate_only:
        ratio = r["det"] / r["gt"]
        print(f"  det={r['det']:.0f}  gt={r['gt']:.0f}  ratio={ratio:.3f}  in_range={r['in_range']}")
    if not inflate_only:
        print("  (none — x1/3 and x3 contribute ZERO inflation on this corpus)")


if __name__ == "__main__":
    main()
