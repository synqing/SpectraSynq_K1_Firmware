"""Static checks for k1_lever2_emit.h and the flagged show_leds/init_leds cut."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EMIT = (
    ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "visual" / "k1_lever2_emit.h"
).read_text(encoding="utf-8")
LED = (
    ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "visual" / "led_utilities.h"
).read_text(encoding="utf-8")
GLOBALS = (
    ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "system" / "globals.h"
).read_text(encoding="utf-8")


def _fn_body(src: str, name: str) -> str:
    m = re.search(rf"static inline uint16_t {name}\s*\(", src)
    assert m, f"{name} not found"
    brace = src.index("{", m.start())
    depth = 0
    for i, c in enumerate(src[brace:], brace):
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return src[brace : i + 1]
    raise AssertionError(f"unbalanced braces for {name}")


def _ifdef_blocks(src: str, flag: str) -> list[str]:
    blocks = []
    token = f"#ifdef {flag}"
    start = 0
    while True:
        i = src.find(token, start)
        if i < 0:
            break
        depth = 0
        j = i
        while j < len(src):
            if src.startswith("#ifdef", j) or src.startswith("#ifndef", j) or src.startswith("#if ", j):
                # only count at line starts
                if j == 0 or src[j - 1] == "\n":
                    depth += 1
            if src.startswith("#endif", j) and (j == 0 or src[j - 1] == "\n"):
                depth -= 1
                if depth == 0:
                    blocks.append(src[i : j + 6])
                    start = j + 6
                    break
            j += 1
        else:
            raise AssertionError(f"unclosed ifdef {flag}")
    return blocks


def _uncommented(src: str) -> str:
    no_block = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    return "\n".join(
        line.split("//", 1)[0] for line in no_block.splitlines()
    )


def test_emit_header_exists_and_packs():
    body = _uncommented(EMIT)
    assert "ws2816_pack_pixel" in body
    assert "k1_lever2_pack_frame" in body
    assert "quantize_color" not in body
    assert "nscale8" not in body
    assert "setBrightness" not in body
    assert "setMaxPower" not in body


def test_limiter_functions_have_no_float():
    for name in ("k1_lever2_scale_q16", "k1_lever2_apply_q16"):
        body = _fn_body(EMIT, name)
        assert "float" not in body
        assert "double" not in body


def test_quantize_color_remains_on_flag_off_path():
    assert "quantize_color(CONFIG.TEMPORAL_DITHERING)" in LED
    blocks = _ifdef_blocks(LED, "K1_WS2816_LEVER2_V1")
    assert blocks, "no Lever-2 ifdef in led_utilities.h"
    show_block = next(b for b in blocks if "k1_lever2_pack_frame" in b)
    assert "quantize_color" not in show_block
    assert show_block.count("FastLED.show") >= 1


def test_show_leds_lever2_block_has_no_post_pack_colour_ops():
    blocks = _ifdef_blocks(LED, "K1_WS2816_LEVER2_V1")
    show_block = next(b for b in blocks if "k1_lever2_pack_frame" in b)
    pack_at = show_block.index("k1_lever2_pack_frame")
    after = show_block[pack_at:]
    for forbidden in ("nscale8", "setBrightness", "setCorrection", "setMaxPower"):
        assert forbidden not in after, f"{forbidden} after pack"


def test_init_leds_lever2_skips_max_power():
    blocks = _ifdef_blocks(LED, "K1_WS2816_LEVER2_V1")
    init_block = next(b for b in blocks if "addLeds<WS2812B, LED_DATA_PIN, RGB>(ws2816_wire" in b)
    assert "setMaxPower" not in init_block
    assert "DISABLE_DITHER" in init_block
    assert "REVERSE_ORDER" in init_block


def test_ws2816_wire_symbol_is_flag_gated():
    assert "#ifdef K1_WS2816_LEVER2_V1" in GLOBALS
    gated = _ifdef_blocks(GLOBALS, "K1_WS2816_LEVER2_V1")
    assert any("ws2816_wire" in b for b in gated)


def test_incandescent_inplace_skipped_when_lever2():
    assert (
        "!defined(K1_INCANDESCENT_OUTPUT_V1) && !defined(K1_WS2816_LEVER2_V1)"
        in LED
    )
