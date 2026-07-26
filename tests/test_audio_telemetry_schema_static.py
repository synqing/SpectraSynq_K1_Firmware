from pathlib import Path
from _fwpath import FwDir, read_serial_menu_surface


ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / "SPECTRASYNQ_K1_FIRMWARE"
FW_DIR = FwDir(FW)
I2S_AUDIO = FW / "audio" / "i2s_audio.h"
SERIAL_MENU = FW / "serial" / "serial_menu.h"
GDFT_CORE = FW / "audio" / "k1_gdft_core.cpp"
GLOBALS = FW / "system" / "globals.h"
PIN_H = FW / "diag" / "k1_pin_evidence.h"
PIN_CPP = FW / "diag" / "k1_pin_evidence.cpp"
PIN_SUMMARY = ROOT / "scripts" / "regression-harness" / "k1_pin_evidence_summary.py"


def test_ap_stream_schema_keeps_front_end_and_loud_guard_fields():
    text = I2S_AUDIO.read_text(encoding="utf-8")

    ap_fields = (
        "SSL=%u",
        "DC=%d",
        "max_raw=%.0f",
        "follower=%.0f",
        "peak_scaled=%.3f",
        "response_gain=%.3f",
        "silent_scale=%.3f",
        "silence=%d",
        "cal_source=%s",
        "cal_valid=%d",
        "cal_reason=%s",
        "bpm=%.1f",
        "conf=%.2f",
        "lock=%d",
        "phase=%.2f",
        "beat=%d",
        "bstr=%.2f",
        "onset=%d",
        "bass=%d",
        "ostr=%.2f",
    )
    for field in ap_fields:
        assert field in text

    im73d_fields = (
        "raw_i16_abs_peak=%u",
        "raw_i16_rms=%.1f",
        "raw_i16_near_pct=%.3f",
    )
    for field in im73d_fields:
        assert field in text

    loud_guard_fields = (
        "input_trim=%.3f",
        "gdft_trim=%.3f",
        "agc_gain=%.3f",
        "agc_env=%.3f",
        "clip_pct=%.3f",
        "near_pct=%.3f",
        "peak_pin=%.3f",
        "spec_pin=%.3f",
        "spec_sat=%.3f",
    )
    for field in loud_guard_fields:
        assert field in text


def test_ap_capture_schema_keeps_capture_summary_fields():
    text = I2S_AUDIO.read_text(encoding="utf-8")
    fmt = (
        "[APCAP] frames=%lu max_raw=%.0f/%.0f peak_scaled=%.3f/%.3f "
        "follower_mean=%.1f spec_argmax=%u chroma_mean=%.4f silence=%d "
        "SSL=%u DC=%d cal_source=%s cal_valid=%d cal_reason=%s\\n"
    )

    assert fmt in text
    assert "ap_capture_tick()" in text
    assert "spectrogram_smooth[i]" in text
    assert "chromagram_smooth[c]" in text


def test_agc_stream_schema_exposes_legacy_and_active_floor_fields():
    serial = read_serial_menu_surface(FW_DIR)
    gdft = GDFT_CORE.read_text(encoding="utf-8")
    globals_h = GLOBALS.read_text(encoding="utf-8")

    for field in ("energy:", ";gain:", ";threshold:", ";floor:", ";active_floor:"):
        assert field in serial

    assert "agc_active_floor_debug[NUM_AGC_BANDS]" in globals_h
    assert "agc_active_floor_debug[b] = pb_noise_floor[b];" in gdft
    assert "agc_active_floor_debug[b] = agc_noise_floor;" in gdft


def test_pin_evidence_schema_v2_uses_conditioned_not_raw_peak_label():
    header = PIN_H.read_text(encoding="utf-8")
    source = PIN_CPP.read_text(encoding="utf-8")
    summary = PIN_SUMMARY.read_text(encoding="utf-8")

    for text in (header, source, summary):
        assert "conditioned_peak_q" in text
        assert "raw_peak_q" not in text
        assert "raw_peak\"" not in text

    assert "post_sensitivity_peak_q" in header
    assert '"conditioned_peak": _q16(row["conditioned_peak_q"])' in summary
