"""Parser tests: execute shipped colourlab-core.js on reply fixtures."""
from __future__ import annotations

import json
from pathlib import Path

from colourlab_node import call_core, require_core

require_core()

FIXTURES = (
    Path(__file__).resolve().parent / "fixtures" / "colourlab_replies.json"
)


def _cases() -> list[dict]:
    data = json.loads(FIXTURES.read_text(encoding="utf-8"))
    return data["cases"]


def test_fixtures_include_framed_and_inner_payload_cases():
    names = {c["name"] for c in _cases()}
    assert "simple_paint_lf" in names
    assert "framed_paint_success" in names
    assert "framed_save_fail_error_then_success" in names
    assert "framed_chip_id" in names
    assert "envelope_markers_are_not_events" in names


def test_parser_matches_each_fixture_via_shipped_js():
    for case in _cases():
        out = call_core({"op": "parse", "chunks": case["chunks"]})
        assert out["events"] == case["events"], case["name"]


def test_envelope_markers_are_framing_not_events():
    out = call_core(
        {
            "op": "parse",
            "chunks": [
                "sbr{{\nPAINT: mode=off target=both rgb=140,140,140 s=1.000 v=0.550 stops=0\n}}\n"
            ],
        }
    )
    kinds = [e["kind"] for e in out["events"]]
    assert kinds == ["paint"]
    assert all(e.get("line") not in ("sbr{{", "}}") for e in out["events"])


def test_partial_tail_stays_buffered():
    out = call_core(
        {
            "op": "parse",
            "chunks": [
                "sbr{{\nPAINT: mode=solid target=both rgb=1,2,3 s=1.000 v=0.550 stops=0"
            ],
        }
    )
    assert out["events"] == []
    assert "PAINT:" in out["pending"]
