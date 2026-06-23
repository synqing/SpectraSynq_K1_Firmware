"""Minimal UI state mirror for Tab5 harness dispatch replay (SC-4)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class MockUiState:
    selected: str = "primary"
    page: str = "COMPOSER"
    overlay: str = "NONE"
    pending: list[dict[str, object]] = field(default_factory=list)
    last_request_id: int = 0
    last_result_id: int = 0
    ack_pending: int = 0

    def select_surface(self, surface: str) -> bool:
        surface = surface.upper()
        if surface not in {"PRIMARY", "SECONDARY"}:
            return False
        self.selected = surface.lower()
        return True

    def set_slider(self, name: str, value: int) -> tuple[bool, str | None]:
        if value < 0 or value > 100:
            return False, None
        name = name.upper()
        mapping = {
            "BRIGHTNESS": "photons",
            "COLOUR": "chroma",
            "COLOR": "chroma",
            "SPEED": "mood",
        }
        param = mapping.get(name)
        if not param:
            return False, None
        control = f"{self.selected}.{param}"
        self.last_request_id += 1
        self.pending.append({"id": self.last_request_id, "control": control})
        self.ack_pending = len(self.pending)
        return True, control

    def apply_result(self, control_id: int, control: str, ok: bool = True) -> bool:
        for index, item in enumerate(self.pending):
            if item["id"] == control_id and item["control"] == control:
                self.pending.pop(index)
                if ok:
                    self.last_result_id = control_id
                self.ack_pending = len(self.pending)
                return True
        return False
