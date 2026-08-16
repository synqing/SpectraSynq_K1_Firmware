"""Gate 1 structural checks for VP cadence and stack-watermark evidence."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / "SPECTRASYNQ_K1_FIRMWARE"
GLOBALS = FW / "system" / "globals.h"
INO = FW / "SPECTRASYNQ_K1_FIRMWARE.ino"
SERIAL = FW / "serial" / "serial_menu.cpp"


def test_vp_perf_records_start_to_start_separately_from_frame_service():
    source = GLOBALS.read_text(encoding="utf-8")
    assert "VPPerfStat frame_interval" in source
    assert "vp_perf_record(vp_perf.frame_interval, delta_us)" in source
    assert "vp_perf_record(vp_perf.frame, frame_us)" in source


def test_both_application_owners_publish_stack_high_watermarks():
    ino = INO.read_text(encoding="utf-8")
    serial = SERIAL.read_text(encoding="utf-8")
    assert "vp_perf_note_ap_stack((uint32_t)uxTaskGetStackHighWaterMark(NULL))" in ino
    assert "vp_perf_note_vp_stack((uint32_t)uxTaskGetStackHighWaterMark(NULL))" in ino
    assert "ap_stack_hwm_words=" in serial
    assert "vp_stack_hwm_words=" in serial


def test_stack_and_interval_evidence_remain_in_existing_probe_gate():
    ino = INO.read_text(encoding="utf-8")
    for call in ("vp_perf_note_ap_stack", "vp_perf_note_vp_stack"):
        position = ino.index(call)
        gate = ino.rfind("#if ENABLE_VP_PERF_AUDIT", 0, position)
        end = ino.find("#endif", position)
        assert gate >= 0 and end > position


def test_stack_scans_are_runtime_gated_and_sampled_at_one_hz():
    ino = INO.read_text(encoding="utf-8")
    ap = ino[ino.index("vp_perf_ap_stack_last_ms"):ino.index("stream_vp_perf_data")]
    vp_start = ino.index("vp_perf_vp_stack_last_us")
    vp = ino[vp_start:ino.index("#endif", vp_start)]
    assert "!vp_perf.running" in ap
    assert ">= 1000UL" in ap
    assert "uxTaskGetStackHighWaterMark" in ap
    assert "if (vp_perf.running)" in vp
    assert ">= 1000000LL" in vp
    assert "uxTaskGetStackHighWaterMark" in vp
