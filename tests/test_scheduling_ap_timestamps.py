"""Gate 1 structural and arithmetic checks for truthful AP timestamp boundaries."""

from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / "SPECTRASYNQ_K1_FIRMWARE"
TYPES = FW / "audio" / "k1_i2s_capture_types.h"
I2S = FW / "audio" / "i2s_audio.h"
INO = FW / "SPECTRASYNQ_K1_FIRMWARE.ino"
CAPTURE_H = FW / "serial" / "k1_ap_capture_telemetry.h"
CAPTURE_CPP = FW / "serial" / "k1_ap_capture_telemetry.cpp"


def test_sample_span_estimator_compiles_and_matches_12k8_96(tmp_path):
    driver = tmp_path / "driver.cpp"
    driver.write_text(
        """
#include <stdint.h>
#include "audio/k1_i2s_capture_types.h"
int main() {
  const uint64_t newest = 1000000ULL;
  const uint64_t oldest = k1_i2s_estimate_oldest_sample_us(newest, 96U, 12800U);
  if (oldest != 992579ULL) return 1;
  if (k1_i2s_estimate_oldest_sample_us(newest, 0U, 12800U) != newest) return 2;
  if (k1_i2s_estimate_oldest_sample_us(newest, 96U, 0U) != newest) return 3;
  return 0;
}
""",
        encoding="utf-8",
    )
    binary = tmp_path / "driver"
    build = subprocess.run(
        ["c++", "-std=c++17", "-I", str(FW), str(driver), "-o", str(binary)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert build.returncode == 0, build.stderr
    run = subprocess.run([str(binary)], check=False)
    assert run.returncode == 0


def test_i2s_probe_records_read_return_and_declared_sample_estimates():
    types = TYPES.read_text(encoding="utf-8")
    i2s = I2S.read_text(encoding="utf-8")
    for field in (
        "read_start_us",
        "read_return_us",
        "newest_sample_estimate_us",
        "oldest_sample_estimate_us",
        "ap_publish_us",
        "capture_sequence",
        "samples_read",
        "sample_time_assumption_id",
    ):
        assert field in types
        assert field in i2s
    assert "newest_sample_estimate_us = i2s_read_return_us" in i2s
    assert "k1_i2s_estimate_oldest_sample_us" in i2s


def test_publish_boundary_is_after_all_current_semantic_publishers():
    ino = INO.read_text(encoding="utf-8")
    snapshot = ino.index("k1_audio_snapshot_update(t_now)")
    onset = ino.index("k1_onset_beat_update(k1_audio_snapshot)")
    saliency = ino.index("k1_musical_saliency_update(k1_audio_snapshot")
    tempo = ino.index("k1_tempo_update(k1_audio_snapshot)")
    publish = ino.index("k1_audio_i2s_debug_note_ap_publish")
    assert snapshot < onset < saliency < tempo < publish


def test_apcad_carries_distinct_timestamps_and_prints_assumption():
    header = CAPTURE_H.read_text(encoding="utf-8")
    source = CAPTURE_CPP.read_text(encoding="utf-8")
    for field in (
        "capture_sequence",
        "i2s_read_return_us",
        "newest_sample_estimate_us",
        "oldest_sample_estimate_us",
        "ap_publish_us",
        "sample_time_assumption_id",
        "newest_to_publish_us",
        "oldest_to_publish_us",
    ):
        assert field in header or field in source
    assert "sample.capture_sequence = frame.i2s.capture_sequence" in source
    assert "USBSerial.print(sample.capture_sequence)" in source


def test_timestamp_instrumentation_stays_probe_gated():
    i2s = I2S.read_text(encoding="utf-8")
    ino = INO.read_text(encoding="utf-8")
    assert "#if ENABLE_TEMPO_STREAM && ENABLE_AP_FRONTEND_DEBUG" in i2s
    call = ino.index("k1_audio_i2s_debug_note_ap_publish")
    gate = ino.rfind("#if ENABLE_TEMPO_STREAM && ENABLE_AP_FRONTEND_DEBUG", 0, call)
    end = ino.find("#endif", call)
    assert gate >= 0 and end > call
