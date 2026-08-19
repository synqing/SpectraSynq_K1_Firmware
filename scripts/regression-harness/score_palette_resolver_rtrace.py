#!/usr/bin/env python3
"""Score palette-safe EdgeMixer rtrace dumps against Naberius Gold.

Decoder: hue_coverage.rtrace_frames (same F,<idx>,<ms>,<mode>,<hex> lines as
device :rtrace_dump). PASS law is the frozen contract, not 24-bucket mass
stray (wrap interpolation on Naberius legitimately touches neighbour buckets).

  1. Full-amount complementary ON is not the honour bypass (not identity).
  2. Full-amount complementary ON stays on the Naberius curve (no teal).
  3. Full-amount complementary OFF leaves that curve (RGB split still exists).
  4. Every chroma mode under palette-ON at full amount stays on the curve.
  5. Silicon twin (SPLIT / 0.65 / mask / OKLab): ON != OFF, echo is _palette.
  6. Veil ON stays on the curve and drops chroma.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "regression-harness"))
from hue_coverage import rtrace_frames, rgb_hue_hist  # noqa: E402
from palette_reference import interpolate, parse_gradients  # noqa: E402

NABERIUS = "K1_Naberius_Gold_gp"
GOLD = np.array([255, 140, 0], dtype=np.uint8)
TEAL_BUCKETS = set(range(8, 16))  # cyan→azure: RGB complement of Naberius gold
MAX_ON_HUE_DEG = 15.0
MIN_OFF_HUE_DEG = 25.0
CHROMA_GATE = 8


def hue_deg(rgb: np.ndarray):
    r = rgb[:, 0].astype(np.float64)
    g = rgb[:, 1].astype(np.float64)
    b = rgb[:, 2].astype(np.float64)
    mx = np.maximum(np.maximum(r, g), b)
    mn = np.minimum(np.minimum(r, g), b)
    d = mx - mn
    h = np.zeros(len(rgb))
    ok = (d >= CHROMA_GATE) & (mx > 2)
    if ok.any():
        rc, gc, bc, mxc, dc = r[ok], g[ok], b[ok], mx[ok], d[ok]
        hh = np.where(
            mxc == rc,
            (gc - bc) / dc,
            np.where(mxc == gc, 2.0 + (bc - rc) / dc, 4.0 + (rc - gc) / dc),
        )
        h[ok] = np.mod(hh, 6.0) * 60.0
    return h, ok


def circ_dist_deg(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    d = np.abs(a[:, None] - b[None, :])
    return np.minimum(d, 360.0 - d)


def vocab_hues() -> np.ndarray:
    cpp = (ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "visual" / "Palettes.cpp").read_text()
    rgb = interpolate(parse_gradients(cpp)[NABERIUS], 256)
    h, ok = hue_deg(rgb)
    return h[ok]


def frame_map(path: Path) -> dict:
    names = []
    with path.open() as f:
        for line in f:
            m = re.match(r"^FRAME name=(\S+) effective=(\S+)", line.strip())
            if m:
                names.append((m.group(1), m.group(2)))
    frames = list(rtrace_frames(str(path)))
    out = {}
    for (name, effective), (_t, _ms, _mode, rgb) in zip(names, frames):
        out[name] = {"rgb": rgb, "effective": effective}
    return out


def score_frame(rgb: np.ndarray, vocab: np.ndarray) -> dict:
    h, ok = hue_deg(rgb)
    hist, lit = rgb_hue_hist(rgb)
    deployed = set(int(i) for i in np.where(hist / max(hist.sum(), 1) >= 0.02)[0])
    teal = sorted(deployed & TEAL_BUCKETS)
    if ok.any():
        dist = circ_dist_deg(h[ok], vocab).min(axis=1)
        max_deg = float(dist.max())
        p95_deg = float(np.percentile(dist, 95))
    else:
        max_deg = p95_deg = 0.0
    mx = rgb.max(axis=1).astype(np.int16)
    mn = rgb.min(axis=1).astype(np.int16)
    live = mx > 2
    chroma_mean = float((mx - mn)[live].mean()) if live.any() else 0.0
    return {
        "lit": round(lit, 4),
        "deployed": sorted(deployed),
        "teal_buckets": teal,
        "max_hue_deg": round(max_deg, 3),
        "p95_hue_deg": round(p95_deg, 3),
        "chroma_mean": round(chroma_mean, 2),
        "gold_identity": bool(np.array_equal(rgb, np.broadcast_to(GOLD, rgb.shape))),
        "px0": [int(x) for x in rgb[0]],
        "px79": [int(x) for x in rgb[79]],
        "chromatic_px": int(ok.sum()),
    }


def main() -> int:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/k1_palette_rtrace/dump.log")
    frames = frame_map(path)
    vocab = vocab_hues()
    rows = {name: {**score_frame(v["rgb"], vocab), "effective": v["effective"]}
            for name, v in frames.items()}
    checks = []

    def check(name: str, cond: bool, detail: str):
        checks.append({"name": name, "pass": bool(cond), "detail": detail})
        print(f"[{'PASS' if cond else 'FAIL'}] {name}: {detail}")

    on = rows["gold_on_comp_full"]
    off = rows["gold_off_comp_full"]
    check("full_on_not_bypass",
          on["effective"] == "complementary_palette" and not on["gold_identity"],
          f"effective={on['effective']} px0={on['px0']} identity={on['gold_identity']}")
    check("full_on_on_curve",
          on["max_hue_deg"] <= MAX_ON_HUE_DEG,
          f"max={on['max_hue_deg']}deg px0={on['px0']}")
    check("full_on_no_teal",
          on["teal_buckets"] == [],
          f"teal={on['teal_buckets']} deployed={on['deployed']}")
    check("full_off_leaves_curve",
          off["max_hue_deg"] >= MIN_OFF_HUE_DEG and off["effective"] == "complementary_rgb",
          f"max={off['max_hue_deg']}deg px0={off['px0']} deployed={off['deployed']}")
    check("full_off_is_teal_control",
          bool(off["teal_buckets"]) and 16 not in off["deployed"],
          f"off {off['max_hue_deg']} vs on {on['max_hue_deg']} teal={off['teal_buckets']} on_px={on['px0']} off_px={off['px0']}")

    son = rows["gold_on_comp_silicon"]
    soff = rows["gold_off_comp_silicon"]
    check("silicon_echo_palette",
          son["effective"] == "complementary_palette" and soff["effective"] == "complementary_rgb",
          f"on={son['effective']} off={soff['effective']}")
    check("silicon_not_bypass",
          not son["gold_identity"] and son["px0"] != [255, 140, 0],
          f"px0={son['px0']}")
    check("silicon_on_ne_off",
          son["px0"] != soff["px0"],
          f"on {son['px0']} off {soff['px0']}")

    for mode, expect in (
        ("analogous", "analogous_palette"),
        ("split", "split_palette"),
        ("triadic", "triadic_palette"),
        ("tetradic", "tetradic_palette"),
        ("comp", "complementary_palette"),
    ):
        row = rows[f"sweep_on_{mode}_full" if mode != "comp" else "sweep_on_comp_full"]
        check(f"family_{mode}_live",
              row["effective"] == expect and row["max_hue_deg"] <= MAX_ON_HUE_DEG,
              f"effective={row['effective']} max={row['max_hue_deg']}deg px0={row['px0']}")
        check(f"family_{mode}_no_teal",
              row["teal_buckets"] == [],
              f"teal={row['teal_buckets']}")

    veil = rows["gold_on_veil_full"]
    gold_chroma = float(GOLD.max() - GOLD.min())
    check("veil_on_curve",
          veil["effective"] == "saturation_veil" and veil["max_hue_deg"] <= MAX_ON_HUE_DEG,
          f"effective={veil['effective']} max={veil['max_hue_deg']}deg")
    check("veil_desaturates",
          veil["chroma_mean"] < gold_chroma * 0.95,
          f"chroma {veil['chroma_mean']} vs gold {gold_chroma}")

    failed = [c for c in checks if not c["pass"]]
    summary = {
        "verdict": "FAIL" if failed else "PASS",
        "failed": [c["name"] for c in failed],
        "frames": rows,
        "thresholds": {"max_on_hue_deg": MAX_ON_HUE_DEG, "min_off_hue_deg": MIN_OFF_HUE_DEG,
                       "teal_buckets": sorted(TEAL_BUCKETS)},
    }
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else path.with_suffix(".score.json")
    out.write_text(json.dumps(summary, indent=2) + "\n")
    print("SUMMARY", json.dumps({"verdict": summary["verdict"], "failed": summary["failed"]}))
    print(f"wrote {out}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
