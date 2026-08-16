"""Exact host contract for the non-shippable four-lane GDFT service probe."""

from __future__ import annotations

import importlib.util
import json
import re
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ORACLE_PATH = ROOT / "scripts" / "regression-harness" / "golden" / "oracle_gdft.py"
MODEL_PATH = ROOT / "scripts" / "regression-harness" / "gdft_center_honesty_model.py"
CORE = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "audio" / "k1_gdft_core.cpp"
KERNEL = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "audio" / "k1_gdft_lane4_exact.h"
PIO = ROOT / "platformio.ini"
IDENTITIES = ROOT / "scripts" / "platformio" / "k1_device_identities.json"

PRODUCTION_INT64_DEFINES = [
    "DEFAULT_SAMPLE_RATE=12800",
    "DEFAULT_SAMPLES_PER_CHUNK=96",
    "K1_TEMPO_NOVELTY_DECIMATION=3U",
    "K1_LOUD_GUARD_V1",
    "K1_RENDER_HOST_TEST",
    "K1_GDFT_INT64_MAGNITUDE_V1=1",
    "K1_GDFT_INT64_RECURRENCE_V1=1",
]


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _capture(defines: list[str], driver: str) -> str:
    oracle = _load(ORACLE_PATH, f"oracle_gdft_lane4_{len(defines)}")
    oracle.DEFINES = defines
    oracle.DRIVER = driver
    with tempfile.TemporaryDirectory(prefix="gdft_lane4_exact_") as td:
        binary = oracle._compile(Path(td))
        return oracle._run(binary)


def _exact_driver() -> str:
    oracle = _load(ORACLE_PATH, "oracle_gdft_lane4_driver")
    prefix = oracle.DRIVER[: oracle.DRIVER.index("int main()")]
    main = r"""
static uint32_t float_bits(float value) {
  uint32_t bits = 0;
  std::memcpy(&bits, &value, sizeof(bits));
  return bits;
}

static void fill_frame(int frame) {
  if (frame < 4) {
    std::memset(sample_window, 0, sizeof(sample_window));
    return;
  }
  if (frame < 16) {
    const double w = 2.0 * M_PI * 440.0 / 12800.0;
    const long base = (long)(frame - 4) * 96;
    for (int s = SAMPLE_HISTORY_LENGTH - 1; s >= 0; s--) {
      const double t = (double)(base + (SAMPLE_HISTORY_LENGTH - 1 - s));
      sample_window[s] = (short)(16000.0 * sin(w * t));
    }
    return;
  }

  const int adversarial = frame - 16;
  if (adversarial < 9) {
    for (int s = 0; s < SAMPLE_HISTORY_LENGTH; s++) {
      switch (adversarial) {
        case 0: sample_window[s] = 32767; break;
        case 1: sample_window[s] = -32768; break;
        case 2: sample_window[s] = (s & 1) ? 32767 : -32768; break;
        case 3: sample_window[s] = (short)(s - 2048); break;
        case 4: sample_window[s] = (s == SAMPLE_HISTORY_LENGTH - 1) ? 32767 : 0; break;
        case 5: sample_window[s] = (s == 0) ? -32768 : 0; break;
        case 6: sample_window[s] = (s == SAMPLE_HISTORY_LENGTH / 2) ? 32767 : 0; break;
        case 7: sample_window[s] = (short)(((s * 257) & 0xffff) - 32768); break;
        default: sample_window[s] = 0; break;
      }
    }
    return;
  }

  const int random_frame = adversarial - 9;
  if (random_frame < 24) {
    uint32_t state = 0x9e3779b9u ^ (uint32_t)random_frame * 0x85ebca6bu;
    for (int s = 0; s < SAMPLE_HISTORY_LENGTH; s++) {
      state = state * 1664525u + 1013904223u;
      sample_window[s] = (short)(state >> 16);
    }
    return;
  }

  const int bin = random_frame - 24;
  const double w = 2.0 * M_PI * (double)frequencies[bin].target_freq / 12800.0;
  const double amplitude = 4000.0 + (double)((bin * 173) % 12000);
  for (int s = SAMPLE_HISTORY_LENGTH - 1; s >= 0; s--) {
    const double t = (double)(SAMPLE_HISTORY_LENGTH - 1 - s + bin * 31);
    sample_window[s] = (short)(amplitude * sin(w * t));
  }
}

int main() {
  CONFIG.SAMPLE_RATE = 12800;
  CONFIG.NOTE_OFFSET = 12;
  CONFIG.MOOD = 0.5f;
  CONFIG.LIGHTSHOW_MODE = 0;
  host_precompute_goertzel_constants();
  host_init_spectral_tilt_lut();
  noise_complete = true;

  const int SAFE_BINS = (int)k1_gdft_nyquist_safe_bin_hi(
      CONFIG.SAMPLE_RATE, CONFIG.NOTE_OFFSET);
  const int TOTAL_FRAMES = 4 + 12 + 9 + 24 + SAFE_BINS;
  std::printf("safe=%d frames=%d\n", SAFE_BINS, TOTAL_FRAMES);
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
    return prefix + main


def test_probe_is_one_flag_non_shippable_and_bench_only():
    pio = PIO.read_text(encoding="utf-8")
    start = pio.index("[env:k1_bench_scheduling_gdft_lane4_probe]")
    end = pio.find("\n[env:", start + 1)
    section = pio[start : end if end >= 0 else len(pio)]
    assert "NON-SHIPPABLE" in section
    assert "extends = env:k1_bench_scheduling_baseline_probe" in section
    added = [line.strip() for line in section.splitlines() if line.strip().startswith("-")]
    assert added == ["-DK1_GDFT_LANE4_PROBE=1"]

    manifest = json.loads(IDENTITIES.read_text(encoding="utf-8"))
    owners = [row["chip_id"] for row in manifest["authorized"]
              if "k1_bench_scheduling_gdft_lane4_probe" in row["envs"]]
    assert owners == ["B489A500"]


def test_scalar_path_remains_present_and_probe_is_strictly_gated():
    core = CORE.read_text(encoding="utf-8")
    kernel = KERNEL.read_text(encoding="utf-8")
    assert "#if K1_GDFT_LANE4_PROBE" in core
    assert "#else\n  for (uint16_t i = 0; i < NUM_FREQS; i++)" in core
    assert "#endif  // K1_GDFT_LANE4_PROBE" in core
    assert "requires the current int64 recurrence and magnitude contract" in core
    assert "spectral windowing is outside its contract" in core
    assert "(int64_t)state.coeff_q14 * (int64_t)state.q1" in kernel
    assert "((int64_t)sample >> 6) + (mult >> 14) - (int64_t)state.q2" in kernel
    assert "K1_GDFT_LANE4_Q0_OBSERVE(q0_64);" in kernel
    assert "k1_gdft_q0_overflow_count++" in core
    # Gate F-alpha mutates the first match only. The non-shippable branch must
    # not introduce a dead-code decoy before the live scalar mutation anchor.
    assert len(re.findall(r"\? MAGNITUDES_AVG_ATTACK", core)) == 1


def test_operation_counts_preserve_every_recurrence_and_lock_shared_load_count():
    model = _load(MODEL_PATH, "gdft_lane4_service_model")
    blocks = [row["block_size"] for row in model.compute_bins(x2_crossover=0)[:71]]
    recurrence_steps = sum(blocks)
    shared_sample_loads = 0
    for base in range(0, len(blocks), 4):
      lane = blocks[base : base + 4]
      common = min(lane)
      shared_sample_loads += common + sum(block - common for block in lane)
    assert recurrence_steps == 34254
    assert shared_sample_loads == 10753
    assert recurrence_steps - shared_sample_loads == 23501


def test_prior_gdft_oracle_fixture_is_byte_exact_under_current_int64_contract():
    oracle = _load(ORACLE_PATH, "oracle_gdft_lane4_prior_fixture")
    scalar = _capture(PRODUCTION_INT64_DEFINES, oracle.DRIVER)
    lane4 = _capture(PRODUCTION_INT64_DEFINES + ["K1_GDFT_LANE4_PROBE=1"], oracle.DRIVER)
    assert lane4 == scalar


def test_random_adversarial_and_all_safe_bin_histories_are_code_exact():
    driver = _exact_driver()
    scalar = _capture(PRODUCTION_INT64_DEFINES, driver)
    lane4 = _capture(PRODUCTION_INT64_DEFINES + ["K1_GDFT_LANE4_PROBE=1"], driver)
    assert scalar.startswith("safe=71 frames=120\n")
    assert lane4 == scalar


def test_non_monotonic_crossover_inside_lane_is_code_exact():
    # Crossover 41 creates a block-size jump between bins 40 and 41 inside one
    # four-bin group. This kills any accidental reliance on monotonic lane sizes.
    driver = _exact_driver()
    defines = PRODUCTION_INT64_DEFINES + ["K1_GDFT_X2_CROSSOVER_BIN=41u"]
    scalar = _capture(defines, driver)
    lane4 = _capture(defines + ["K1_GDFT_LANE4_PROBE=1"], driver)
    assert scalar.startswith("safe=71 frames=120\n")
    assert lane4 == scalar
