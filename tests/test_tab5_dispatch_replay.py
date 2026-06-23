"""Host dispatch replay without LVGL/desktop (SC-4)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "tests" / "tab5_harness_spec"
if str(SPEC) not in sys.path:
    sys.path.insert(0, str(SPEC))

from mock_ui_state import MockUiState  # noqa: E402
from replay_dispatch import replay_line, replay_transcript  # noqa: E402


def test_surface_updates_before_slider_mapping() -> None:
    state = MockUiState()
    ok, _ = replay_line(state, "UI_SURFACE SECONDARY")
    assert ok
    assert state.selected == "secondary"
    ok, response = replay_line(state, "UI_SLIDER COLOUR 61")
    assert ok
    assert state.pending[-1]["control"] == "secondary.chroma"
    assert "COLOUR" in response


def test_ack_pending_decrements_on_matching_result() -> None:
    state = MockUiState()
    replay_line(state, "UI_SLIDER BRIGHTNESS 70")
    assert state.ack_pending == 1
    assert state.apply_result(state.last_request_id, "primary.photons")
    assert state.ack_pending == 0


def test_transcript_replay_sequence() -> None:
    lines = [
        "UI_SURFACE PRIMARY",
        "UI_SLIDER BRIGHTNESS 70",
        "UI_STATUS",
    ]
    events = replay_transcript(lines)
    assert all(ok for _, ok, _ in events)
    status_line = events[-1][2]
    assert "ack_pending=1" in status_line
