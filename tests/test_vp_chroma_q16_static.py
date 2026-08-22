"""C1/C2: live colour paint must not round-trip FastLED uint8."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / "SPECTRASYNQ_K1_FIRMWARE"
EFFECTS = FW / "effects"
HSV = FW / "visual" / "led_utilities.h"
C1_FILES = (
    EFFECTS / "light_mode_gdft.cpp",
    EFFECTS / "light_mode_chromagram_dots.cpp",
    EFFECTS / "light_mode_chromagram_gradient.cpp",
    EFFECTS / "light_mode_vu.cpp",
    EFFECTS / "light_mode_vu_dot.cpp",
    EFFECTS / "light_mode_kaleidoscope.cpp",
    EFFECTS / "light_mode_quantum_collapse.cpp",
)


def test_hsv_does_not_use_chsv_uint8_bridge():
    text = HSV.read_text(encoding="utf-8")
    start = text.index("inline CRGB16 hsv(SQ15x16 h, SQ15x16 s, SQ15x16 v)")
    end = text.index("inline void clip_led_values_count", start)
    body = text[start:end]
    assert "CHSV(" not in body
    assert "uint8_t(h" not in body
    assert "h * 255" not in body
    assert "sector" in body


def test_c1_live_modes_use_palette_manual_colour():
    for path in C1_FILES:
        text = path.read_text(encoding="utf-8")
        assert "ColorFromPalette" not in text, path.name
        assert "palette_manual_colour" in text, path.name
