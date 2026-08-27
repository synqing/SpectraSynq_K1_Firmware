"""Render parity: Python authority fixtures vs executed colourlab-core.js."""
from __future__ import annotations

import json
from pathlib import Path

from colourlab_node import call_core, require_core

require_core()

VECTORS = (
    Path(__file__).resolve().parent / "fixtures" / "colourlab_render_vectors.json"
)


def _doc() -> dict:
    return json.loads(VECTORS.read_text(encoding="utf-8"))


def test_vectors_cover_160_and_150_without_universal_160():
    doc = _doc()
    ns = {suite["n"] for suite in doc["suites"]}
    assert ns == {160, 150}
    by_n = {s["n"]: s for s in doc["suites"]}
    assert by_n[160]["both_scale_enabled"] is True
    assert by_n[150]["both_scale_enabled"] is False
    scaled = [c["name"] for c in by_n[150]["cases"] if c["name"].endswith("_scaled")]
    assert scaled == [], scaled
    assert any(c["name"] == "card_both_scaled" for c in by_n[160]["cases"])
    assert any(c["name"] == "card_both_unscaled" for c in by_n[150]["cases"])


def test_shipped_js_matches_python_authority_vectors():
    doc = _doc()
    for suite in doc["suites"]:
        for case in suite["cases"]:
            got = call_core(
                {
                    "op": "render",
                    "paint": case["paint"],
                    "tune": case["tune"],
                    "n": suite["n"],
                    "both_scale_enabled": suite["both_scale_enabled"],
                    "both_scale": suite["both_scale"],
                }
            )
            assert got == case["expect"], f"{suite['n']}:{case['name']}"


def test_shipped_js_curves_match_python_authority():
    doc = _doc()
    for curve in doc["curves"]:
        got = call_core({"op": "curve", "tune": curve["tune"]})
        assert got["x"] == curve["x"], curve["name"]
        assert got["r"] == curve["r"], curve["name"]
        assert got["g"] == curve["g"], curve["name"]
        assert got["b"] == curve["b"], curve["name"]
        assert got["valid"] is curve["valid"]


def test_bench_both_target_is_not_scaled():
    doc = _doc()
    bench = next(s for s in doc["suites"] if s["n"] == 150)
    both = next(c for c in bench["cases"] if c["name"] == "solid_default_both")
    primary = both["expect"]["primary_pre"]
    # 140/255 unscaled, not ×0.30
    assert primary is not None
    assert primary[0] > 20000
    main = next(s for s in doc["suites"] if s["n"] == 160)
    main_both = next(c for c in main["cases"] if c["name"] == "solid_default_both")
    assert main_both["expect"]["primary_pre"][0] < primary[0]
