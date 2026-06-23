"""Tests for the palette coverage gate (scripts/regression-harness/palette_coverage_gate.py).

Two layers, mirroring tests/test_loop.py:
  * pure-logic unit tests (always run) — metric maths on synthetic hex frames,
    no compilation.
  * a g++-gated integration smoke (skipped if no host compiler) that compiles
    light_mode_bloom once via render_replay, replays the same fixture under two
    DIFFERENT palettes, and asserts the metrics distinguish them. One compile +
    two replays keeps runtime well under a minute.
"""
import pathlib
import shutil
import sys

import pytest

HARNESS = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "regression-harness"
sys.path.insert(0, str(HARNESS))
import palette_coverage_gate as pcg  # noqa: E402
import render_replay as rr  # noqa: E402

_HAVE_GPP = any(shutil.which(c) for c in rr.GPP_CANDIDATES)

_SCHEMA_METRIC_KEYS = {
    "frames", "led_count", "total_pixels", "lit_fraction",
    "near_black_fraction", "white_fraction", "desaturated_lit_fraction",
    "mean_saturation", "mean_value", "distinct_colour_count",
    "distinct_colour_count_q5", "hue_bins", "hue_histogram",
    "hue_bin_coverage", "hue_entropy_bits", "hue_entropy_norm", "frames_hash",
}


# ---- pure-logic unit tests (no compiler needed) -----------------------------

def _frame_hex(pixels):
    return "".join("%02x%02x%02x" % p for p in pixels)


def test_metrics_on_black_frames():
    hexes = [_frame_hex([(0, 0, 0)] * 8)] * 4
    m = pcg.compute_colour_metrics(hexes)
    assert m["frames"] == 4 and m["led_count"] == 8
    assert m["near_black_fraction"] == 1.0
    assert m["lit_fraction"] == 0.0
    assert m["distinct_colour_count"] == 0
    assert m["hue_entropy_bits"] == 0.0


def test_metrics_distinguish_single_vs_multi_hue():
    red = [_frame_hex([(200, 10, 10)] * 8)]
    rainbow = [_frame_hex([(200, 10, 10), (10, 200, 10), (10, 10, 200),
                           (200, 200, 10), (10, 200, 200), (200, 10, 200),
                           (200, 100, 10), (100, 10, 200)])]
    m1 = pcg.compute_colour_metrics(red)
    m2 = pcg.compute_colour_metrics(rainbow)
    assert m2["hue_entropy_bits"] > m1["hue_entropy_bits"]
    assert m2["distinct_colour_count"] > m1["distinct_colour_count"]
    assert m2["hue_bin_coverage"] > m1["hue_bin_coverage"]


def test_white_and_desaturated_classification():
    hexes = [_frame_hex([(250, 250, 250), (200, 10, 10)])]
    m = pcg.compute_colour_metrics(hexes)
    assert m["white_fraction"] == pytest.approx(0.5)
    assert m["desaturated_lit_fraction"] == pytest.approx(0.5)


# ---- integration smoke (real compile + render) -----------------------------

@pytest.mark.skipif(not _HAVE_GPP, reason="no host g++ available")
def test_gate_distinguishes_two_palettes(tmp_path):
    ok, binary, comp = rr.build_binary(str(tmp_path), mode="bloom")
    assert ok, (comp.get("stderr") or "")[:800]

    # Palette 0 vs 7 render visibly different hue families on beat-pulse
    # (verified red-family vs teal-family at authoring time); any two palettes
    # with distinct gradients must yield distinct output histograms.
    r0 = pcg.run_gate("bloom", 0, fixture="beat-pulse", binary=binary)
    r7 = pcg.run_gate("bloom", 7, fixture="beat-pulse", binary=binary)

    for rep, idx in ((r0, 0), (r7, 7)):
        assert rep["schema"] == pcg.SCHEMA
        assert rep["effect"] == "bloom"
        assert rep["palette_index"] == idx
        assert rep["palette_mode"] is True
        # honesty contract: coordinate coverage is NOT claimed
        assert rep["palette_coordinate_coverage"] is None
        assert rep["basis"] == "rendered_rgb_output"
        m = rep["metrics"]
        assert _SCHEMA_METRIC_KEYS <= set(m)
        assert m["frames"] > 0 and m["led_count"] > 0
        assert len(m["hue_histogram"]) == m["hue_bins"]
        assert 0.0 <= m["hue_bin_coverage"] <= 1.0
        assert m["distinct_colour_count"] >= m["distinct_colour_count_q5"] > 0

    m0, m7 = r0["metrics"], r7["metrics"]
    # the metric must DISTINGUISH the two palettes
    assert m0["frames_hash"] != m7["frames_hash"]
    assert m0["hue_histogram"] != m7["hue_histogram"]
    assert (m0["distinct_colour_count"], m0["hue_entropy_bits"]) != \
           (m7["distinct_colour_count"], m7["hue_entropy_bits"])
