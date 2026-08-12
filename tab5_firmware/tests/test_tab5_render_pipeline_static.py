"""Regression contracts for the Tab5 atomic display presenter and value typography."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2] / "tab5_firmware"
BRIDGE = ROOT / "src/lvgl_bridge.cpp"
CONFIG = ROOT / "include/tab5_config.h"
UI = ROOT / "src/deck_ui.cpp"
OVERLAY = ROOT / "scripts/patch_m5gfx_dsi_double_buffer.py"


def test_full_scale_percent_value_cannot_clip_its_leading_digit():
    text = UI.read_text(encoding="utf-8")
    width = int(re.search(r"kValueLabelWidth = (\d+)", text).group(1))
    right_inset = int(re.search(r"kValueLabelRightInset = (\d+)", text).group(1))
    assert width >= 4 * 33  # Berkeley Mono 55: four cells in "100%".
    assert right_inset >= 8
    assert "w - kValueLabelWidth - kValueLabelRightInset" in text


def test_production_contract_forbids_partial_scanout():
    text = CONFIG.read_text(encoding="utf-8")
    assert "#define TAB5_LVGL_DUAL_PARTIAL_FB 0" in text
    assert "#define TAB5_LVGL_FULL_DIRECT_FB 1" in text
    assert "#define TAB5_USE_PPA 1" in text
    assert '#error "Production Tab5 requires full-frame PPA rendering with VSYNC presentation"' in text


def test_presenter_uses_complete_frames_ppa_and_vsync_swap_only():
    text = BRIDGE.read_text(encoding="utf-8")
    assert "LV_DISPLAY_RENDER_MODE_DIRECT" in text
    assert "lv_display_flush_is_last" in text
    assert "ppa_do_scale_rotate_mirror" in text
    assert "operation.byte_swap = false" in text
    assert "esp_lcd_panel_draw_bitmap" in text
    assert "on_refresh_done" in text
    assert "buffer2" in text
    assert "LV_DISPLAY_RENDER_MODE_PARTIAL" not in text
    assert "pushImage" not in text
    assert text.count("heap_caps_aligned_alloc") == 1


def test_pinned_m5gfx_overlay_is_double_buffered_and_checksum_gated():
    text = OVERLAY.read_text(encoding="utf-8")
    assert 'CPP_COUNT_PATCHED = "    dpi_config.num_fbs = 2;"' in text
    assert "void* buffer2 = nullptr" in text
    assert "esp_lcd_panel_handle_t panel_handle" in text
    for name in ("HPP_PATCHED_SHA256", "CPP_PATCHED_SHA256"):
        match = re.search(rf'{name} = "([0-9a-f]{{64}})"', text)
        assert match, name


def test_palette_preview_uses_one_shared_subpixel_spatial_field():
    text = UI.read_text(encoding="utf-8")
    assert "GRAD_STRIP_H      36" in text
    assert "kPaletteAnimationFrameUs = 16000" in text
    assert "kPaletteAnimationMaxDtUs = 50000" in text
    assert "palette_flow_build_field(&gPaletteFlow" in text
    assert "gPaletteSamplesQ16[pixel]" in text
    assert "gPaletteLightDeltaQ8[pixel]" in text
    assert "apply_palette_light" in text
    assert "Circular 11-tap integration is executable host-tested" in text
    assert "palette_flow_prefilter_rgb888(raw_lut, 256, z->palette_lut)" in text
    assert "sample_palette_lut" in text
    assert "if (z.grad_w != shared_width) return" in text
    assert "PaletteMotion gPaletteMotion[2]" not in text
    assert "lv_obj_set_style_translate_x" not in text
    assert "GRAD_STRIP_RING_W" not in text
    assert "z->grad_buf[y * w + x] = px" in text
    assert "lv_obj_set_size(z->grad, z->grad_w, GRAD_STRIP_H)" in text


def test_status_strip_does_not_rewrite_lvgl_labels_at_palette_tick_rate():
    text = UI.read_text(encoding="utf-8")
    body = text.split("static void refresh_status_strip(void)\n{", 1)[1]
    body = body.split("\n}\n\nstatic void wing_event_cb", 1)[0]
    assert "!gStatusUiInitialised" in body
    assert "if (phase_changed) {\n    if (gPhaseLabel)" in body
    assert body.count("lv_label_set_text(gPhaseLabel") == 1
