#!/usr/bin/env python3
"""Generate golden fixtures for the Colour Lab web instrument.

Authority: tests/colour_lab.py (host replica of
SPECTRASYNQ_K1_FIRMWARE/visual/k1_colour_lab.h). This script extends the
float paint fill with the exact fixed-point emit pipeline pinned in
tools/colourlab/README.md section 1.5:

    float pixel (0..1)
      -> Both-target scale (x0.30 ONLY when the profile enables it)
      -> SQ15x16 truncation toward zero at 1/65536 steps
      -> u16 = (raw * 65535) >> 16              (k1_lever2_sq_to_u16, inc=1)
      -> optional slot-15 RGB_1D LUT            (k1_look_lerp_1d)

Usage:
    python3 tests/generate_colourlab_fixtures.py
    python3 tests/generate_colourlab_fixtures.py --n 160
    python3 tests/generate_colourlab_fixtures.py --n 150

Default emits both n=160 (Main RPL, both-scale on) and n=150 (bench, no
both-scale).
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import colour_lab  # noqa: E402

BOTH_SCALE = 0.30


def sq_trunc_to_u16(f: float) -> int:
    """float -> SQ15x16 (trunc toward zero) -> k1_lever2_sq_to_u16 (inc=1)."""
    raw = int(f * 65536.0)
    if raw <= 0:
        return 0
    v = (raw * 65535) >> 16
    return 65535 if v > 65535 else v


def lut_lerp_1d(v: int, xs: list[int], ys: list[int]) -> int:
    """Replica of k1_look_lerp_1d (k1_look.h:165-192)."""
    if v == 0:
        return 0
    if v >= 65535:
        return 65535
    lo, hi = 0, 255
    while hi - lo > 1:
        mid = (lo + hi) >> 1
        if xs[mid] <= v:
            lo = mid
        else:
            hi = mid
    x0, x1, y0, y1 = xs[lo], xs[hi], ys[lo], ys[hi]
    if x1 <= x0:
        return y0
    num = (y1 - y0) * (v - x0)
    den = x1 - x0
    return y0 + (num + (den >> 1)) // den


def channel_vectors(
    paint: colour_lab.PaintState,
    tune: colour_lab.Tune,
    channel: str,
    n: int,
    both_scale_enabled: bool,
) -> tuple[list[int] | None, list[int] | None]:
    if paint.mode == "off":
        return None, None
    targeted = paint.target == "both" or paint.target == channel
    if not targeted:
        return None, None
    scale = BOTH_SCALE if (paint.target == "both" and both_scale_enabled) else 1.0
    nodes = colour_lab.build_rgb1d(tune)
    xs = nodes[0:256]
    yr = nodes[256:512]
    yg = nodes[512:768]
    yb = nodes[768:1024]
    pre: list[int] = []
    post: list[int] = []
    for i in range(n):
        r, g, b = colour_lab.pixel(paint, i, n)
        u = (
            sq_trunc_to_u16(r * scale),
            sq_trunc_to_u16(g * scale),
            sq_trunc_to_u16(b * scale),
        )
        pre.extend(u)
        post.extend(
            (
                lut_lerp_1d(u[0], xs, yr),
                lut_lerp_1d(u[1], xs, yg),
                lut_lerp_1d(u[2], xs, yb),
            )
        )
    return pre, post


def make_case(
    name: str,
    paint: colour_lab.PaintState,
    tune: colour_lab.Tune,
    n: int,
    both_scale_enabled: bool,
) -> dict:
    p_pre, p_post = channel_vectors(paint, tune, "primary", n, both_scale_enabled)
    s_pre, s_post = channel_vectors(paint, tune, "secondary", n, both_scale_enabled)
    return {
        "name": name,
        "n": n,
        "both_scale_enabled": both_scale_enabled,
        "paint": {
            "mode": paint.mode,
            "target": paint.target,
            "r": paint.r,
            "g": paint.g,
            "b": paint.b,
            "s": paint.s,
            "v": paint.v,
            "stops": [list(t) for t in paint.stops],
        },
        "tune": {
            "gain_r": tune.gain_r,
            "gain_g": tune.gain_g,
            "gain_b": tune.gain_b,
            "gamma": tune.gamma,
        },
        "expect": {
            "primary_pre": p_pre,
            "primary_post": p_post,
            "secondary_pre": s_pre,
            "secondary_post": s_post,
        },
    }


def make_curve(name: str, tune: colour_lab.Tune) -> dict:
    nodes = colour_lab.build_rgb1d(tune)
    return {
        "name": name,
        "tune": {
            "gain_r": tune.gain_r,
            "gain_g": tune.gain_g,
            "gain_b": tune.gain_b,
            "gamma": tune.gamma,
        },
        "x": nodes[0:256],
        "r": nodes[256:512],
        "g": nodes[512:768],
        "b": nodes[768:1024],
        "valid": colour_lab.rgb1d_valid(nodes),
    }


def case_list(n: int, both_scale_enabled: bool) -> list[dict]:
    P = colour_lab.PaintState
    T = colour_lab.Tune
    identity = T()

    cases = [
        make_case(
            "solid_representative",
            P(mode="solid", target="primary", r=200, g=64, b=10),
            identity,
            n,
            both_scale_enabled,
        ),
        make_case(
            "solid_default_both",
            P(mode="solid", target="both", r=140, g=140, b=140),
            identity,
            n,
            both_scale_enabled,
        ),
        make_case(
            "solid_secondary_only",
            P(mode="solid", target="secondary", r=0, g=255, b=1),
            identity,
            n,
            both_scale_enabled,
        ),
        make_case(
            "ramp_default",
            P(mode="ramp", target="primary", s=1.0, v=0.55),
            identity,
            n,
            both_scale_enabled,
        ),
        make_case(
            "ramp_desaturated_full_v",
            P(mode="ramp", target="primary", s=0.0, v=1.0),
            identity,
            n,
            both_scale_enabled,
        ),
        make_case(
            "stops_1",
            P(mode="stops", target="primary", stops=[(255, 140, 0)]),
            identity,
            n,
            both_scale_enabled,
        ),
        make_case(
            "stops_2_black_white",
            P(mode="stops", target="primary", stops=[(0, 0, 0), (255, 255, 255)]),
            identity,
            n,
            both_scale_enabled,
        ),
        make_case(
            "stops_8",
            P(
                mode="stops",
                target="primary",
                stops=[
                    (255, 0, 0),
                    (255, 140, 0),
                    (255, 255, 0),
                    (0, 255, 0),
                    (0, 255, 255),
                    (0, 0, 255),
                    (140, 0, 255),
                    (255, 255, 255),
                ],
            ),
            identity,
            n,
            both_scale_enabled,
        ),
        make_case(
            "stops_edge_codes",
            P(mode="stops", target="primary", stops=[(0, 1, 254), (255, 254, 1)]),
            identity,
            n,
            both_scale_enabled,
        ),
        make_case(
            "card_primary",
            P(mode="card", target="primary"),
            identity,
            n,
            both_scale_enabled,
        ),
        make_case(
            "solid_white_nonunity_gains",
            P(mode="solid", target="primary", r=255, g=255, b=255),
            T(gain_r=0.5, gain_g=1.0, gain_b=2.0),
            n,
            both_scale_enabled,
        ),
        make_case(
            "solid_grey_gamma_min",
            P(mode="solid", target="primary", r=128, g=128, b=128),
            T(gamma=0.20),
            n,
            both_scale_enabled,
        ),
        make_case(
            "solid_grey_gamma_max",
            P(mode="solid", target="primary", r=128, g=128, b=128),
            T(gamma=4.00),
            n,
            both_scale_enabled,
        ),
        make_case(
            "off_passthrough",
            P(mode="off", target="both"),
            identity,
            n,
            both_scale_enabled,
        ),
    ]
    if both_scale_enabled:
        cases.append(
            make_case(
                "card_both_scaled",
                P(mode="card", target="both"),
                identity,
                n,
                both_scale_enabled,
            )
        )
        cases.append(
            make_case(
                "ramp_both_gain_gamma",
                P(mode="ramp", target="both", s=1.0, v=0.55),
                T(gain_r=1.5, gain_g=0.8, gain_b=1.0, gamma=2.2),
                n,
                both_scale_enabled,
            )
        )
    else:
        cases.append(
            make_case(
                "card_both_unscaled",
                P(mode="card", target="both"),
                identity,
                n,
                both_scale_enabled,
            )
        )
        cases.append(
            make_case(
                "ramp_both_gain_gamma_unscaled",
                P(mode="ramp", target="both", s=1.0, v=0.55),
                T(gain_r=1.5, gain_g=0.8, gain_b=1.0, gamma=2.2),
                n,
                both_scale_enabled,
            )
        )
    return cases


def curve_list() -> list[dict]:
    T = colour_lab.Tune
    return [
        make_curve("identity", T()),
        make_curve("gain_edges", T(gain_r=0.0, gain_g=1.0, gain_b=2.0)),
        make_curve("gamma_min", T(gamma=0.20)),
        make_curve("gamma_max", T(gamma=4.00)),
        make_curve("mixed", T(gain_r=1.5, gain_g=0.8, gain_b=1.0, gamma=2.2)),
    ]


SUITES = {
    160: {
        "n": 160,
        "both_scale_enabled": True,
        "both_scale": BOTH_SCALE,
        "env": "k1_main_rpl_im69d",
        "chip_id": "9087A500",
    },
    150: {
        "n": 150,
        "both_scale_enabled": False,
        "both_scale": None,
        "env": "k1_bench_im69d_led150",
        "chip_id": "B489A500",
    },
}


def build_suite(n: int) -> dict:
    meta = SUITES[n]
    return {
        **meta,
        "cases": case_list(meta["n"], meta["both_scale_enabled"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--n",
        type=int,
        action="append",
        choices=sorted(SUITES),
        help="LED count suite to emit (repeatable). Default: 160 and 150.",
    )
    args = parser.parse_args()
    ns = args.n or [160, 150]
    suites = [build_suite(n) for n in ns]
    out = {
        "generator": "tests/generate_colourlab_fixtures.py",
        "authority": "tests/colour_lab.py",
        "curves": curve_list(),
        "suites": suites,
    }
    path = (
        pathlib.Path(__file__).resolve().parent / "fixtures" / "colourlab_render_vectors.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, separators=(",", ":")) + "\n")
    n_cases = sum(len(s["cases"]) for s in suites)
    print(
        f"wrote {path} ({path.stat().st_size} bytes, "
        f"{len(suites)} suites, {n_cases} cases, {len(out['curves'])} curves)"
    )


if __name__ == "__main__":
    main()
