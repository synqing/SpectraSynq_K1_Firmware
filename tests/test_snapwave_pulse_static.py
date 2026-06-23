"""Static wiring checks for SAT-promoted additive light modes."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / "SPECTRASYNQ_K1_FIRMWARE"


def read(path: Path) -> str:
    return path.read_text()


ADD_HISTORY_EFFECTS = [
    "light_mode_snapwave.cpp",
    "light_mode_pulse_prism.cpp",
    "light_mode_tempo_river.cpp",
    "light_mode_spectrum_river.cpp",
    "light_mode_spectrum_river_v2.cpp",
    "light_mode_ember.cpp",
    "light_mode_ember_v2.cpp",
    "light_mode_dense_forge.cpp",
    "light_mode_bloom.cpp",
    "light_mode_aurora.cpp",
]

IN_PLACE_TRAIL_EFFECTS = [
    "light_mode_comet.cpp",
    "light_mode_tempo_comet.cpp",
]


def test_snapwave_pulse_modes_are_append_only_registered():
    config = read(FW / "system" / "config_types.h")
    enum_body = config.split("enum lightshow_modes {", 1)[1].split("};", 1)[0]
    dense_idx = enum_body.index("LIGHT_MODE_DENSE_FORGE")
    snap_idx = enum_body.index("LIGHT_MODE_SNAPWAVE")
    prism_idx = enum_body.index("LIGHT_MODE_PULSE_PRISM")
    num_idx = enum_body.index("NUM_MODES")

    assert dense_idx < snap_idx < prism_idx < num_idx
    assert "LIGHT_MODE_SNAPWAVE_SAT" not in enum_body
    assert "LIGHT_MODE_PULSE_PRISM_SAT" not in enum_body


def test_snapwave_pulse_modes_have_user_visible_names():
    system = read(FW / "system" / "system.h")

    assert 'set_mode_name(22, "SNAPWAVE");' in system
    assert 'set_mode_name(23, "PULSE PRISM");' in system
    assert "SNAPWAVE SAT" not in system
    assert "PULSE PRISM SAT" not in system


def test_snapwave_pulse_modes_are_declared():
    modes = read(FW / "visual" / "lightshow_modes.h")

    assert "void light_mode_snapwave(CRGB16* leds_prev_buffer, ChannelEffectState& fx);" in modes
    assert "void light_mode_pulse_prism(CRGB16* leds_prev_buffer, ChannelEffectState& fx);" in modes
    assert "light_mode_snapwave_sat" not in modes
    assert "light_mode_pulse_prism_sat" not in modes


def test_snapwave_pulse_modes_are_dispatched():
    sketch = read(FW / "SPECTRASYNQ_K1_FIRMWARE.ino")

    assert "mode == LIGHT_MODE_SNAPWAVE" in sketch
    assert "light_mode_snapwave(channel.history, *channel.effect);" in sketch
    assert "mode == LIGHT_MODE_PULSE_PRISM" in sketch
    assert "light_mode_pulse_prism(channel.history, *channel.effect);" in sketch
    assert "LIGHT_MODE_SNAPWAVE_SAT" not in sketch
    assert "LIGHT_MODE_PULSE_PRISM_SAT" not in sketch
    assert "light_mode_snapwave_sat" not in sketch
    assert "light_mode_pulse_prism_sat" not in sketch


def test_snapwave_pulse_modes_are_smart_auto_allowed():
    mode_selection = read(FW / "director" / "sb_mode_selection.cpp")

    assert "case LIGHT_MODE_SNAPWAVE:" in mode_selection
    assert "case LIGHT_MODE_PULSE_PRISM:" in mode_selection
    assert "LIGHT_MODE_SNAPWAVE_SAT" not in mode_selection
    assert "LIGHT_MODE_PULSE_PRISM_SAT" not in mode_selection


def test_snapwave_pulse_sat_sources_removed():
    effects = FW / "effects"

    assert not (effects / "light_mode_snapwave_sat.cpp").exists()
    assert not (effects / "light_mode_pulse_prism_sat.cpp").exists()


def test_additive_finalizer_helper_exists():
    modes = read(FW / "visual" / "lightshow_modes.h")

    assert "clamp_crgb16_preserve_sat" in modes
    assert "void finalize_additive_frame(CRGB16* leds, CRGB16* leds_prev_buffer, bool store_history)" in modes
    assert "leds[i] = clamp_crgb16_preserve_sat(leds[i]);" in modes
    assert "memcpy(leds_prev_buffer, leds, sizeof(CRGB16) * NATIVE_RESOLUTION);" in modes


def test_additive_history_effects_store_only_finalized_trails():
    for name in ADD_HISTORY_EFFECTS:
        source = read(FW / "effects" / name)
        assert "finalize_additive_frame(leds_16, leds_prev_buffer, true)" in source, name
        assert "memcpy(leds_prev_buffer, leds_16" not in source, name
        assert "clamp_crgb16(leds_16[i])" not in source, name


def test_in_place_trail_comets_use_preserve_sat_final_clamp():
    for name in IN_PLACE_TRAIL_EFFECTS:
        source = read(FW / "effects" / name)
        assert "clamp_crgb16_preserve_sat(leds_16[i])" in source, name
        assert "clamp_crgb16(leds_16[i])" not in source, name


def test_promoted_snapwave_and_prism_use_sat_tuning():
    snapwave = read(FW / "effects" / "light_mode_snapwave.cpp")
    prism = read(FW / "effects" / "light_mode_pulse_prism.cpp")

    assert "if (fade_f > 0.965f) fade_f = 0.965f;" in snapwave
    assert "static const float PRISM_RING_GAIN      = 0.70f;" in prism
    assert "static const float PRISM_BED_GAIN       = 0.36f;" in prism
    assert "if (fade_f > 0.965f) fade_f = 0.965f;" in prism


def test_persisted_mode_ids_keep_current_append_only_modes():
    config = read(FW / "system" / "config_types.h")
    bridge_fs = read(FW / "persistence" / "bridge_fs.h")

    assert "uint8_t light_mode_sanitize_persisted(uint8_t mode)" in config
    assert "if (mode == 24) return LIGHT_MODE_SNAPWAVE;" not in config
    assert "if (mode == 25) return LIGHT_MODE_PULSE_PRISM;" not in config
    assert "if (mode >= NUM_MODES) return LIGHT_MODE_BLOOM;" in config
    assert "return light_mode_is_enabled(mode) ? mode : light_mode_next_enabled(mode, 1);" in config
    assert "CONFIG.LIGHTSHOW_MODE = light_mode_sanitize_persisted(CONFIG.LIGHTSHOW_MODE);" in bridge_fs
    assert "SECONDARY_LIGHTSHOW_MODE = light_mode_sanitize_persisted(SECONDARY_LIGHTSHOW_MODE);" in bridge_fs


def test_host_replay_stub_has_no_sat_modes():
    replay = read(ROOT / "scripts" / "regression-harness" / "smart_director_replay.py")

    assert "LIGHT_MODE_SNAPWAVE," in replay
    assert "LIGHT_MODE_PULSE_PRISM," in replay
    assert "LIGHT_MODE_SNAPWAVE_SAT" not in replay
    assert "LIGHT_MODE_PULSE_PRISM_SAT" not in replay
