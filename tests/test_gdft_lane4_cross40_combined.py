"""Host gate for the combined Cross40 × Lane-4 exact backend candidate.

Lane-4 must remain bit-identical to the scalar/reference path with Cross40
active. Cross40 itself is allowed to change low-bin window policy versus
Cross0; this file only proves Lane-4 adds no extra semantic change.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

from test_gdft_lane4_exact_probe import (
    PRODUCTION_INT64_DEFINES,
    _capture,
    _exact_driver,
)


ROOT = Path(__file__).resolve().parents[1]
PIO = ROOT / "platformio.ini"
IDENTITIES = ROOT / "scripts" / "platformio" / "k1_device_identities.json"
UPLOAD_GUARD = ROOT / "scripts" / "platformio" / "k1_upload_guard.py"
PIO_BUILD = ROOT / "scripts" / "agent" / "pio-build.sh"
ORACLE_PATH = ROOT / "scripts" / "regression-harness" / "golden" / "oracle_gdft.py"
MODEL_PATH = ROOT / "scripts" / "regression-harness" / "gdft_center_honesty_model.py"
COMBINED = "k1_bench_scheduling_gdft_cross40_lane4_full_probe"
CROSS40 = ["K1_GDFT_X2_CROSSOVER_BIN=40u"]
LANE4 = ["K1_GDFT_LANE4_V1=1"]


def _section(text: str, name: str) -> str:
    start = text.index(f"[env:{name}]")
    end = text.find("\n[env:", start + 1)
    return text[start : end if end >= 0 else len(text)]


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _captain_fixture_driver() -> str:
    oracle = _load(ORACLE_PATH, "oracle_gdft_cross40_lane4_driver")
    prefix = oracle.DRIVER[: oracle.DRIVER.index("int main()")]
    return prefix + r"""
static uint32_t float_bits(float value) {
  uint32_t bits = 0;
  std::memcpy(&bits, &value, sizeof(bits));
  return bits;
}

static void fill_tone(int bin, int frame_in_hold) {
  const double w = 2.0 * M_PI * (double)frequencies[bin].target_freq / 12800.0;
  const double amplitude = 12000.0;
  const long base = (long)frame_in_hold * 96;
  for (int s = SAMPLE_HISTORY_LENGTH - 1; s >= 0; s--) {
    const double t = (double)(base + (SAMPLE_HISTORY_LENGTH - 1 - s));
    sample_window[s] = (short)(amplitude * sin(w * t));
  }
}

static void fill_frame(int frame) {
  if (frame < 8) {
    std::memset(sample_window, 0, sizeof(sample_window));
    return;
  }
  if (frame < 15) {
    const int offsets[7] = {
        0, 1, 16, 64, 255, SAMPLE_HISTORY_LENGTH / 2, SAMPLE_HISTORY_LENGTH - 1};
    const int offset = offsets[frame - 8];
    std::memset(sample_window, 0, sizeof(sample_window));
    sample_window[offset] = (short)((frame & 1) ? 32767 : -32768);
    return;
  }
  if (frame == 15) {
    for (int s = 0; s < SAMPLE_HISTORY_LENGTH; s++) sample_window[s] = 32767;
    return;
  }
  if (frame == 16) {
    for (int s = 0; s < SAMPLE_HISTORY_LENGTH; s++) sample_window[s] = -32768;
    return;
  }
  if (frame < 25) {
    uint32_t state = 0xa5a5a5a5u ^ (uint32_t)(frame - 17) * 0x9e3779b9u;
    for (int s = 0; s < SAMPLE_HISTORY_LENGTH; s++) {
      state = state * 1664525u + 1013904223u;
      sample_window[s] = (short)(state >> 16);
    }
    return;
  }
  if (frame < 41) {
    fill_tone(0, frame - 25);
    return;
  }
  if (frame < 57) {
    fill_tone(20, frame - 41);
    return;
  }
  if (frame < 73) {
    fill_tone(39, frame - 57);
    return;
  }
  if (frame < 89) {
    fill_tone(40, frame - 73);
    return;
  }
  fill_tone(70, frame - 89);
}

int main() {
  CONFIG.SAMPLE_RATE = 12800;
  CONFIG.NOTE_OFFSET = 12;
  CONFIG.MOOD = 0.5f;
  CONFIG.LIGHTSHOW_MODE = 0;
  host_precompute_goertzel_constants();
  host_init_spectral_tilt_lut();
  noise_complete = true;

  const int TOTAL_FRAMES = 105;
  std::printf(
      "cross_blk0=%u blk39=%u blk40=%u blk70=%u frames=%d\n",
      (unsigned)frequencies[0].block_size,
      (unsigned)frequencies[39].block_size,
      (unsigned)frequencies[40].block_size,
      (unsigned)frequencies[70].block_size,
      TOTAL_FRAMES);
  for (int frame = 0; frame < TOTAL_FRAMES; frame++) {
    fill_frame(frame);
    process_GDFT();
    calculate_novelty((uint32_t)frame);

    std::printf("f=%d", frame);
    for (int i = 0; i < NUM_FREQS; i++) {
      std::printf(",%d:%08x:%08x:%08x:%08x:%lld",
                  (int)magnitudes[i],
                  (unsigned)float_bits(magnitudes_normalized[i]),
                  (unsigned)float_bits(magnitudes_normalized_avg[i]),
                  (unsigned)float_bits(magnitudes_final[i]),
                  (unsigned)float_bits(magnitudes_last[i]),
                  (long long)spectrogram[i].getInternal());
    }
    const int novelty_index = spectral_history_index == 0
        ? SPECTRAL_HISTORY_LENGTH - 1
        : spectral_history_index - 1;
    std::printf(",nov=%lld,env=%lld,floor=%lld,gated=%d\n",
                (long long)novelty_curve[novelty_index].getInternal(),
                (long long)agc_envelope.getInternal(),
                (long long)agc_noise_floor.getInternal(),
                agc_gated ? 1 : 0);
  }
  return 0;
}
"""


def test_combined_probe_env_is_full_attribution_cross40_lane4_only():
    pio = PIO.read_text(encoding="utf-8")
    section = _section(pio, COMBINED)
    assert "NON-SHIPPABLE" in section
    assert "extends = env:k1_bench_scheduling_stage_full_probe" in section
    # Clear Cross0 baseline unflags so both production selectors remain active.
    assert "build_unflags =" in section
    assert "-DK1_GDFT_X2_CROSSOVER_BIN=40u" in section
    assert "-DK1_GDFT_LANE4_V1=1" in section
    assert "K1_GDFT_X2_CROSSOVER_BIN=80u" not in section
    assert "K1_SPECTRAL_WINDOW_V1" not in section
    assert "K1_AUDIO_TASK" not in section
    full = _section(pio, "k1_bench_scheduling_stage_full_probe")
    assert "-DK1_AP_STAGE_ATTRIBUTION_DETAIL=1" in full


def test_combined_probe_is_allowlisted_only_for_b489a500():
    manifest = json.loads(IDENTITIES.read_text(encoding="utf-8"))
    owners = [
        row["chip_id"]
        for row in manifest["authorized"]
        if COMBINED in row["envs"]
    ]
    assert owners == ["B489A500"]
    main = next(row for row in manifest["authorized"] if row["chip_id"] == "F887A500")
    assert COMBINED not in main["envs"]


def test_combined_probe_is_in_pio_build_wrapper():
    wrapper = PIO_BUILD.read_text(encoding="utf-8")
    assert COMBINED in wrapper
    # Case arm may continue with another env; require a bounded alternative.
    assert f"|{COMBINED}|" in wrapper or f"|{COMBINED})" in wrapper
    rejected = subprocess.run(
        ["bash", str(PIO_BUILD), f"{COMBINED} --target upload"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert rejected.returncode != 0
    assert "not in allowed list" in rejected.stderr


def test_upload_guard_accepts_b489_and_rejects_f887_for_combined_env():
    guard_spec = importlib.util.spec_from_file_location(
        "gdft_cross40_lane4_upload_guard", UPLOAD_GUARD
    )
    guard = importlib.util.module_from_spec(guard_spec)
    assert guard_spec.loader is not None
    sys.modules[guard_spec.name] = guard
    guard_spec.loader.exec_module(guard)
    accepted, accepted_message = guard.validate_upload_target(
        COMBINED,
        "/dev/tty.usbmodem12201",
        [{"device": "/dev/tty.usbmodem12201", "serial_number": "B4:3A:45:A5:89:B4"}],
    )
    rejected, rejected_message = guard.validate_upload_target(
        COMBINED,
        "/dev/tty.usbmodem1401",
        [{"device": "/dev/tty.usbmodem1401", "serial_number": "B4:3A:45:A5:87:F8"}],
    )
    assert accepted and "B489A500" in accepted_message
    assert not rejected and "expected one of [B4:3A:45:A5:89:B4]" in rejected_message


def test_cross40_changes_low_bin_windows_versus_cross0():
    model = _load(MODEL_PATH, "gdft_cross40_lane4_model")
    cross0 = model.compute_bins(x2_crossover=0)
    cross40 = model.compute_bins(x2_crossover=40)
    assert cross0[0]["block_size"] == 1956
    assert cross40[0]["block_size"] == 978
    assert cross40[39]["block_size"] == 102
    assert cross40[40]["block_size"] == 194
    assert cross40[70]["block_size"] == cross0[70]["block_size"]


def test_exact_driver_cross40_scalar_versus_lane4_is_bit_identical():
    driver = _exact_driver()
    defines = PRODUCTION_INT64_DEFINES + CROSS40
    scalar = _capture(defines, driver)
    lane4 = _capture(defines + LANE4, driver)
    assert scalar.startswith("safe=71 frames=120\n")
    assert lane4 == scalar


def test_captain_fixture_set_cross40_scalar_versus_lane4_is_bit_identical():
    driver = _captain_fixture_driver()
    defines = PRODUCTION_INT64_DEFINES + CROSS40
    scalar = _capture(defines, driver)
    lane4 = _capture(defines + LANE4, driver)
    cross0 = _capture(PRODUCTION_INT64_DEFINES, driver)
    assert scalar.startswith("cross_blk0=978 blk39=102 blk40=194 blk70=")
    assert " frames=105\n" in scalar.split("\n", 1)[0] + "\n"
    assert lane4 == scalar
    assert cross0 != scalar
    assert cross0.startswith("cross_blk0=1956 ")
