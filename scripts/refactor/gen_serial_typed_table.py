#!/usr/bin/env python3
"""Generate serial_typed_cmd_table.def rows (M2.1 R2 design lock)."""
from __future__ import annotations

from pathlib import Path

# (name, handler, safety_class, flags, ifdef_guard or None)
# safety: SC_SAFE, SC_TYPED_ONLY, SC_ARM_REQUIRED, SC_FORBIDDEN_SINGLE_BYTE
# flags: 0 or CMD_HARNESS | CMD_PERSISTS etc.

def row(name: str, handler: str, sc: str = "SC_TYPED_ONLY", flags: str = "0", guard: str | None = None) -> tuple:
    return (name, handler, sc, flags, guard)

def emit_rows(rows: list[tuple]) -> list[str]:
    out: list[str] = []
    cur_guard: str | None = "__INIT__"
    for name, handler, sc, flags, guard in rows:
        if guard != cur_guard:
            if cur_guard not in (None, "__INIT__"):
                out.append("#endif")
            if guard:
                out.append(f"#if {guard}")
            cur_guard = guard
        out.append(f'SERIAL_TYPED_CMD("{name}", {handler}, {sc}, {flags})')
    if cur_guard not in (None, "__INIT__"):
        out.append("#endif")
    return out

PURE = [
    "photons", "chroma", "mood", "palette_mode", "palette_index", "square_iter",
    "led_interpolation", "base_coat", "temporal_dithering", "sensitivity",
    "mirror_enabled", "sweet_spot_min", "sweet_spot_max", "chromagram_range",
    "standby_dimming", "reverse_order", "max_current_ma", "auto_color_shift",
    "incandescent_filter", "incandescent_mode", "bulb_opacity", "saturation", "prism_count",
]
REBOOT = [
    "sample_rate", "note_offset", "led_type", "led_count", "led_color_order",
    "samples_per_chunk", "boot_animation",
]
VP_TUNING = [
    ("vp_agc_soft", "vp_fix1"), ("vp_chroma_gate", "vp_fix2"), ("vp_prism_off", "vp_fix3"),
    ("vp_bloom_decay", "vp_fix4"), ("vp_hsv_source_sat", "vp_fix5"), "vp_secondary_clean",
    "vp_bloom_alpha", "vp_bloom_shift", "vp_bloom_force_sat", "vp_wave_idle_fade",
    "vp_wave_raw_margin", "vp_wave_peak_floor", "vp_wave_active_fade", "vp_wave_blend_gain",
    "vp_wave_fallback", "vp_wave_vu_floor", "vp_wave_shift",
]
QUEUE = ["queue_mode", "transition_style", "transition_dip_ms", "transition_xfade_ms", "commit_quantise"]
SMART_DIR = ["smart_assist", "smart_switching", "smart_confidence_floor", "smart_scene"]
EDGE = [
    "edge_enabled", "edge_mode", "edge_stm", "edge_strength", "edge_spread", "edge_rotation",
    "edge_dual", "edge_uniform", "edge_bench", "edge_xform",
]
SECONDARY = [
    "secondary_auto_color_shift", "secondary_incandescent_mode", "secondary_enabled",
    "secondary_photons", "secondary_chroma", "secondary_mood", "secondary_saturation",
    "secondary_prism_count", "secondary_mirror_enabled", "secondary_reverse_order",
    "secondary_control", "secondary_palette_mode", "secondary_palette_index", "secondary_base_coat",
]
AP_DIAG = [
    "ap_frontend_debug", "apdbg", "nov_capture", "nov_dump", "nov_clear", "nov_status",
    "apcad_capture", "apcad_dump", "apcad_clear", "apcad_status", "apcad_soak",
    "apcad_soak_status", "apcad_abort",
]

rows: list[tuple] = []
rows.append(row("vp_profile", "serial_typed_vp_profile", flags="CMD_PERSISTS"))
rows.append(row("vp_all", "serial_typed_vp_all", flags="CMD_PERSISTS"))
for n in ["vivid", "vivid_level", "vivid_chroma", "vivid_black"]:
    rows.append(row(n, "serial_typed_wrap_vivid", guard="K1_VIVID_PRECOMP_V1"))
rows.append(row("ap_stream", "serial_typed_ap_stream", flags="CMD_HARNESS"))
for n in ["tempo_stream"]:
    rows.append(row(n, "serial_typed_tempo_stream", flags="CMD_HARNESS", guard="ENABLE_TEMPO_STREAM"))
for n in AP_DIAG:
    rows.append(row(n, "serial_typed_wrap_ap_diag", flags="CMD_HARNESS", guard="ENABLE_TEMPO_STREAM && ENABLE_AP_FRONTEND_DEBUG"))
for n in ["ap_capture"]:
    rows.append(row(n, "serial_typed_ap_capture", flags="CMD_HARNESS", guard="ENABLE_AP_STREAM"))
for n in ["frame_dump"]:
    rows.append(row(n, "serial_typed_frame_dump", flags="CMD_HARNESS", guard="ENABLE_FRAME_DUMP"))
for n in ["vp_probe"]:
    rows.append(row(n, "serial_typed_vp_probe", flags="CMD_HARNESS", guard="ENABLE_VP_PROBE_CMD"))
for n in ["gdft_probe", "gdft_sweep", "gdft_agc_probe"]:
    rows.append(row(n, "serial_typed_wrap_gdft_harness", flags="CMD_HARNESS", guard="ENABLE_GDFT_HARNESS"))
for n in ["mp_step", "mp_flash", "mp_off", "mp_status"]:
    rows.append(row(n, f"serial_typed_{n}", flags="CMD_HARNESS", guard="ENABLE_MOTION_PROBE"))
rows.append(row("dump_raw", "serial_typed_dump_raw", flags="CMD_HARNESS"))
rows.append(row("vp_stream", "serial_typed_vp_stream", flags="CMD_HARNESS"))
rows.append(row("ble_stream", "serial_typed_ble_stream", flags="CMD_HARNESS"))
rows.append(row("vp_perf", "serial_typed_vp_perf", flags="CMD_HARNESS"))
for n in SMART_DIR:
    rows.append(row(n, "serial_typed_wrap_smart_director"))
rows.append(row("smart_hooks", "serial_typed_wrap_smart_visual"))
for n in EDGE:
    rows.append(row(n, "serial_typed_wrap_edge_mixer"))
rows.append(row("diag", "serial_typed_diag", flags="CMD_HARNESS", guard="ENABLE_DIAG_CAPTURE"))
rows.append(row("vpab", "serial_typed_vpab", flags="CMD_HARNESS", guard="ENABLE_VPAB_PROBE"))
rows.append(row("k1_pin_evidence", "serial_typed_k1_pin_evidence", flags="CMD_HARNESS", guard="K1_PIN_EVIDENCE_V1"))
rows.append(row("vpml", "serial_typed_vpml", flags="CMD_HARNESS", guard="ENABLE_VP_MOTION_LAB"))
for item in VP_TUNING:
    if isinstance(item, tuple):
        for n in item:
            rows.append(row(n, "serial_typed_wrap_vp_tuning"))
    else:
        rows.append(row(item, "serial_typed_wrap_vp_tuning"))
rows.append(row("debug", "serial_typed_debug"))
for n in ["set_mode", "secondary_mode"]:
    rows.append(row(n, "serial_typed_wrap_mode"))
rows.append(row("get_mode_name", "serial_typed_get_mode_name"))
for n in PURE:
    rows.append(row(n, "serial_typed_wrap_pure_setter", flags="CMD_PERSISTS"))
for n in REBOOT:
    rows.append(row(n, "serial_typed_wrap_reboot_setter", flags="CMD_DISRUPTIVE | CMD_PERSISTS"))
rows.append(row("response_gain", "serial_typed_wrap_response_gain", flags="CMD_PERSISTS"))
rows.append(row("k1_loud_guard", "serial_typed_k1_loud_guard", flags="CMD_PERSISTS", guard="K1_LOUD_GUARD_V1"))
for n in ["silence_enter", "silence_exit", "silence_dwell", "silence_rms_enter", "silence_rms_exit"]:
    rows.append(row(n, f"serial_typed_{n}", flags="CMD_PERSISTS"))
rows.append(row("beat_director", "serial_typed_wrap_beat_director", guard="K1_EFFECT_FRAMEWORK_V1"))
rows.append(row("set_chroma_profile", "serial_typed_set_chroma_profile", flags="CMD_DISRUPTIVE | CMD_PERSISTS"))
rows.append(row("bass_mode", "serial_typed_bass_mode", flags="CMD_DISRUPTIVE | CMD_PERSISTS"))
rows.append(row("stream", "serial_typed_stream", flags="CMD_HARNESS"))
rows.append(row("preset", "serial_typed_wrap_preset", flags="CMD_PERSISTS"))
for n in QUEUE:
    rows.append(row(n, "serial_typed_wrap_queue", flags="CMD_PERSISTS"))
for n in ["slot_save", "slot_load", "slot_arm"]:
    handler = "serial_typed_slot_load" if n in ("slot_load", "slot_arm") else f"serial_typed_{n}"
    rows.append(row(n, handler, flags="CMD_PERSISTS"))
rows.append(row("chromatic", "serial_typed_chromatic"))
for n in SECONDARY:
    rows.append(row(n, "serial_typed_wrap_secondary", flags="CMD_PERSISTS"))
rows.append(row("secondary_status", "serial_typed_secondary_status"))
rows.append(row("start_benchmark", "serial_typed_start_benchmark", flags="CMD_HARNESS"))
for n in ["stream_spectrogram", "stream_agc", "stream_chromagram"]:
    rows.append(row(n, f"serial_typed_{n}", flags="CMD_HARNESS"))

HEADER = """// ============================================================================
//  serial_typed_cmd_table.def — Stage B typed `type=value` dispatch rows (X-macro).
//  Included by serial_menu.h (firmware) and serial_typed_dispatch_table_test.cpp (host).
//  SERIAL_TYPED_CMD(name, handler, safety_class, flags)
// ============================================================================

"""

def main() -> None:
    lines = HEADER.splitlines() + emit_rows(rows) + [""]
    path = Path(__file__).resolve().parents[2] / "SPECTRASYNQ_K1_FIRMWARE/serial/serial_typed_cmd_table.def"
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {len(rows)} rows to {path}")

if __name__ == "__main__":
    main()
