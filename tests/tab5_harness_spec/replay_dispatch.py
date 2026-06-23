"""Replay harness semantic commands against mock UI state."""

from __future__ import annotations

from mock_ui_state import MockUiState


def replay_line(state: MockUiState, line: str) -> tuple[bool, str]:
    parts = line.strip().split()
    if not parts:
        return False, "ERR empty"
    cmd = parts[0]
    if cmd == "UI_SURFACE" and len(parts) == 2:
        if state.select_surface(parts[1]):
            return True, f"OK UI_SURFACE surface={parts[1].upper()}"
        return False, "ERR UI_SURFACE bad_surface"
    if cmd == "UI_SLIDER" and len(parts) == 3 and parts[2].isdigit():
        ok, control = state.set_slider(parts[1], int(parts[2]))
        if not ok:
            return False, "ERR UI_SLIDER rejected"
        return True, f"OK UI_SLIDER name={parts[1].upper()} value={parts[2]}"
    if cmd == "UI_STATUS":
        return True, (
            f"OK UI_STATUS selected={state.selected.upper()} ack_pending={state.ack_pending} "
            f"pending_count={state.ack_pending} ui_page={state.page} overlay={state.overlay}"
        )
    return False, f"ERR UNKNOWN command={line}"


def replay_transcript(lines: list[str]) -> list[tuple[str, bool, str]]:
    state = MockUiState()
    out: list[tuple[str, bool, str]] = []
    for line in lines:
        ok, response = replay_line(state, line)
        out.append((line, ok, response))
    return out
