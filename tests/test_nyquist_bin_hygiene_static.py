import re
import unittest
from pathlib import Path
from _fwpath import FwDir


ROOT = Path(__file__).resolve().parents[1]
FW = FwDir(ROOT / "SPECTRASYNQ_K1_FIRMWARE")
PLATFORMIO = (ROOT / "platformio.ini").read_text()
CONSTANTS = (FW / "constants.h").read_text()
CONFIG_TYPES = (FW / "config_types.h").read_text()
GLOBALS_CONFIG = (FW / "globals_config.cpp").read_text()
ONSET = (FW / "k1_onset_beat.cpp").read_text()
SNAPSHOT_CPP = (FW / "k1_audio_snapshot.cpp").read_text()
SNAPSHOT_H = (FW / "k1_audio_snapshot.h").read_text()
AP_CADENCE_MATRIX = (ROOT / "scripts/regression-harness/device_ap_cadence_matrix.py").read_text()


def _parse_notes():
    match = re.search(r"const\s+float\s+notes\[\]\s*=\s*\{(?P<body>.*?)\};", CONSTANTS, re.S)
    assert match is not None, "constants.h must define notes[]"
    return [float(token) for token in re.findall(r"\b\d+\.\d+\b", match.group("body"))]


def _define_int(text, name):
    match = re.search(rf"#define\s+{re.escape(name)}\s+(\d+)U?\b", text)
    assert match is not None, f"{name} must be defined"
    return int(match.group(1))


def _default_note_offset():
    match = re.search(r"^\s*(\d+),\s*//\s*NOTE_OFFSET\b", GLOBALS_CONFIG, re.M)
    assert match is not None, "globals_config.cpp must initialise CONFIG.NOTE_OFFSET"
    return int(match.group(1))


def _safe_hi(sample_rate, note_offset):
    notes = _parse_notes()
    num_freqs = _define_int(CONSTANTS, "NUM_FREQS")
    nyquist = sample_rate / 2.0
    for index in range(num_freqs):
        note_index = index + note_offset
        if note_index >= len(notes) or notes[note_index] > nyquist:
            return index
    return num_freqs


def _platformio_sections():
    matches = list(re.finditer(r"^\[(?P<name>[^\]]+)\]\s*$", PLATFORMIO, re.M))
    sections = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(PLATFORMIO)
        sections[match.group("name")] = PLATFORMIO[match.end():end]
    return sections


class NyquistBinHygieneStaticTest(unittest.TestCase):
    def test_default_12800_profile_has_nine_bins_above_nyquist(self):
        sample_rate = _define_int(CONFIG_TYPES, "DEFAULT_SAMPLE_RATE")
        note_offset = _default_note_offset()
        notes = _parse_notes()
        safe_hi = _safe_hi(sample_rate, note_offset)

        self.assertEqual(sample_rate, 12800)
        self.assertEqual(note_offset, 12)
        self.assertEqual(safe_hi, 71)
        self.assertLessEqual(notes[note_offset + safe_hi - 1], sample_rate / 2.0)
        self.assertGreater(notes[note_offset + safe_hi], sample_rate / 2.0)
        self.assertEqual(_define_int(CONSTANTS, "NUM_FREQS") - safe_hi, 9)

    def test_candidate_sample_rates_and_note_offsets_compute_expected_safe_bins(self):
        self.assertEqual(_safe_hi(12800, 12), 71)
        self.assertEqual(_safe_hi(16000, 12), 75)
        self.assertEqual(_safe_hi(32000, 12), 80)
        self.assertEqual(_safe_hi(12800, 0), 80)

    def test_probe_matrix_contains_bclk_safe_cadence_preserving_16k_tuple(self):
        sections = _platformio_sections()
        expected = {
            "env:k1_ap_frontend_probe_matrix_12800_96_d3": ("12800", "96", "133.333333333f", "3U"),
            "env:k1_ap_frontend_probe_matrix_12800_128_d2": ("12800", "128", "100.0f", "2U"),
            "env:k1_ap_frontend_probe_matrix_16000_120_d3": ("16000", "120", "133.333333333f", "3U"),
            "env:k1_ap_frontend_probe_matrix_16000_160_d2": ("16000", "160", "100.0f", "2U"),
        }
        for env, (sample_rate, chunk, ap_hz, decim) in expected.items():
            with self.subTest(env=env):
                body = sections.get(env)
                self.assertIsNotNone(body, f"{env} must exist")
                self.assertIn("NON-SHIPPABLE", body)
                self.assertIn("build_unflags =", body)
                self.assertIn("-DDEFAULT_SAMPLE_RATE=12800", body)
                self.assertIn("-DDEFAULT_SAMPLES_PER_CHUNK=96", body)
                self.assertIn("-DK1_TEMPO_NOVELTY_DECIMATION=3U", body)
                self.assertIn(f"-DDEFAULT_SAMPLE_RATE={sample_rate}", body)
                self.assertIn(f"-DDEFAULT_SAMPLES_PER_CHUNK={chunk}", body)
                self.assertIn(f"-DK1_TEMPO_AP_FRAME_HZ={ap_hz}", body)
                self.assertIn(f"-DK1_TEMPO_NOVELTY_DECIMATION={decim}", body)

        self.assertIn("env:k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1", sections)
        self.assertIn(
            "extends = env:k1_ap_frontend_probe_matrix_16000_120_d3",
            sections["env:k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1"],
        )
        self.assertIn("env:k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_acq_probe", sections)
        self.assertIn(
            "extends = env:k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1",
            sections["env:k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_acq_probe"],
        )
        self.assertIn(
            "-DK1_ACQUISITION_ONLY_PROBE=1",
            sections["env:k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_acq_probe"],
        )
        for env, stage in (
            ("env:k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_stage_gdft", "K1_AP_STAGE_GDFT"),
            ("env:k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_stage_novelty", "K1_AP_STAGE_NOVELTY"),
            ("env:k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_stage_snapshot", "K1_AP_STAGE_SNAPSHOT"),
            ("env:k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_stage_onset", "K1_AP_STAGE_ONSET"),
            ("env:k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_stage_saliency", "K1_AP_STAGE_SALIENCY"),
            ("env:k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_stage_tempo", "K1_AP_STAGE_TEMPO"),
        ):
            with self.subTest(env=env):
                self.assertIn(env, sections)
                self.assertIn(
                    "extends = env:k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1",
                    sections[env],
                )
                self.assertIn(
                    f"-DK1_AP_STAGE_PROBE_STOP_STAGE={stage}",
                    sections[env],
                )
        spread_env = sections.get("env:k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_stage_tempo_acf_spread16")
        self.assertIsNotNone(spread_env)
        self.assertIn("NON-SHIPPABLE", spread_env)
        self.assertIn(
            "extends = env:k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_stage_tempo",
            spread_env,
        )
        self.assertIn("-DK1_TEMPO_ACF_SPREAD_PROBE=1", spread_env)
        self.assertIn("-DK1_TEMPO_ACF_SPREAD_LAGS_PER_EMIT=16U", spread_env)
        spread12_env = sections.get("env:k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_stage_tempo_acf_spread12")
        self.assertIsNotNone(spread12_env)
        self.assertIn("NON-SHIPPABLE", spread12_env)
        self.assertIn(
            "extends = env:k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_stage_tempo",
            spread12_env,
        )
        self.assertIn("-DK1_TEMPO_ACF_SPREAD_PROBE=1", spread12_env)
        self.assertIn("-DK1_TEMPO_ACF_SPREAD_LAGS_PER_EMIT=12U", spread12_env)
        spread8_env = sections.get("env:k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_stage_tempo_acf_spread8")
        self.assertIsNotNone(spread8_env)
        self.assertIn("NON-SHIPPABLE", spread8_env)
        self.assertIn(
            "extends = env:k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_stage_tempo",
            spread8_env,
        )
        self.assertIn("-DK1_TEMPO_ACF_SPREAD_PROBE=1", spread8_env)
        self.assertIn("-DK1_TEMPO_ACF_SPREAD_LAGS_PER_EMIT=8U", spread8_env)
        spread4_env = sections.get("env:k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_stage_tempo_acf_spread4")
        self.assertIsNotNone(spread4_env)
        self.assertIn("NON-SHIPPABLE", spread4_env)
        self.assertIn(
            "extends = env:k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_stage_tempo",
            spread4_env,
        )
        self.assertIn("-DK1_TEMPO_ACF_SPREAD_PROBE=1", spread4_env)
        self.assertIn("-DK1_TEMPO_ACF_SPREAD_LAGS_PER_EMIT=4U", spread4_env)
        self.assertIn("-DK1_TEMPO_ACF_SKIP_UPDATE_ON_PUBLISH=1", spread4_env)
        full_ap_spread8_env = sections.get("env:k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_acf_spread8")
        self.assertIsNotNone(full_ap_spread8_env)
        self.assertIn("NON-SHIPPABLE", full_ap_spread8_env)
        self.assertIn(
            "extends = env:k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1",
            full_ap_spread8_env,
        )
        self.assertIn("-DK1_TEMPO_ACF_SPREAD_PROBE=1", full_ap_spread8_env)
        self.assertIn("-DK1_TEMPO_ACF_SPREAD_LAGS_PER_EMIT=8U", full_ap_spread8_env)
        full_ap_spread4_env = sections.get("env:k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_acf_spread4")
        self.assertIsNotNone(full_ap_spread4_env)
        self.assertIn("NON-SHIPPABLE", full_ap_spread4_env)
        self.assertIn(
            "extends = env:k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1",
            full_ap_spread4_env,
        )
        self.assertIn("-DK1_TEMPO_ACF_SPREAD_PROBE=1", full_ap_spread4_env)
        self.assertIn("-DK1_TEMPO_ACF_SPREAD_LAGS_PER_EMIT=4U", full_ap_spread4_env)
        self.assertIn("-DK1_TEMPO_ACF_SKIP_UPDATE_ON_PUBLISH=1", full_ap_spread4_env)
        for env in (
            "env:k1_ap_frontend_probe_matrix_12800_96_d3_ap0_vp1",
            "env:k1_ap_frontend_probe_matrix_12800_128_d2_ap0_vp1",
            "env:k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1",
            "env:k1_ap_frontend_probe_matrix_16000_160_d2_ap0_vp1",
        ):
            with self.subTest(env=env):
                body = sections.get(env)
                self.assertIsNotNone(body, f"{env} must exist")
                self.assertIn("build_unflags =", body)
                self.assertIn("-DDEFAULT_SAMPLE_RATE=12800", body)
                self.assertIn("-DDEFAULT_SAMPLES_PER_CHUNK=96", body)
                self.assertIn("-DK1_TEMPO_NOVELTY_DECIMATION=3U", body)

    def test_ap_cadence_runner_includes_bclk_safe_cadence_preserving_16k_tuple(self):
        self.assertIn('"label": "c_16000_120_d3_ap0_vp1"', AP_CADENCE_MATRIX)
        self.assertIn('"env": "k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1"', AP_CADENCE_MATRIX)
        self.assertIn('"sample_rate": 16000', AP_CADENCE_MATRIX)
        self.assertIn('"samples_per_chunk": 120', AP_CADENCE_MATRIX)
        self.assertIn('"decimation": 3', AP_CADENCE_MATRIX)
        self.assertIn('"expected_ap_core": 0', AP_CADENCE_MATRIX)
        self.assertIn('"expected_vp_core": 1', AP_CADENCE_MATRIX)

    def test_runtime_helper_is_source_of_truth_for_nyquist_safe_bin_hi(self):
        self.assertIn("k1_gdft_nyquist_safe_bin_hi(uint16_t sample_rate, uint8_t note_offset)", CONSTANTS)
        self.assertIn("notes[note_index] > nyquist_hz", CONSTANTS)
        self.assertIn("k1_gdft_clamp_bin_hi_to_nyquist", CONSTANTS)
        self.assertNotIn('#include "globals.h"', ONSET)
        self.assertIn("audio.nyquist_safe_bin_hi", ONSET)
        self.assertIn("CONFIG.SAMPLE_RATE", SNAPSHOT_CPP)
        self.assertIn("CONFIG.NOTE_OFFSET", SNAPSHOT_CPP)
        self.assertIn("uint8_t nyquist_safe_bin_hi;", SNAPSHOT_H)

    def test_onset_v2_clamps_high_band_flux_to_runtime_nyquist(self):
        self.assertIn(
            "trans_hi = sbv2_clamp_hi_to_snapshot_nyquist(K1V2_TRANS_LO, K1V2_TRANS_HI",
            ONSET,
        )
        self.assertIn(
            "hihat_hi = sbv2_clamp_hi_to_snapshot_nyquist(K1V2_HIHAT_LO, K1V2_HIHAT_HI",
            ONSET,
        )
        self.assertIn("sbv2_band_flux(spec, g_v2.prev_spec, K1V2_TRANS_LO, trans_hi)", ONSET)
        self.assertIn("sbv2_band_flux(spec, g_v2.prev_spec, K1V2_HIHAT_LO, hihat_hi)", ONSET)
        self.assertIn("sbv2_band_normalise(hihat_flux, K1V2_HIHAT_LO, hihat_hi)", ONSET)
        self.assertNotIn("hihat_flux / float(K1V2_HIHAT_HI - K1V2_HIHAT_LO)", ONSET)

    def test_chroma_fold_excludes_above_nyquist_bins(self):
        self.assertIn("const uint8_t nyquist_safe_bin_hi =", SNAPSHOT_CPP)
        self.assertIn("k1_gdft_nyquist_safe_bin_hi(CONFIG.SAMPLE_RATE, CONFIG.NOTE_OFFSET)", SNAPSHOT_CPP)
        self.assertIn("for (uint8_t i = 0; i < nyquist_safe_bin_hi; i++)", SNAPSHOT_CPP)
        self.assertNotIn("for (uint8_t i = 0; i < NUM_FREQS; i++) {\n    chroma_bucket", SNAPSHOT_CPP)
        self.assertIn("Nyquist-clamped by the runtime sample rate and NOTE_OFFSET", SNAPSHOT_H)

    def test_gdft_skips_above_nyquist_goertzel_eval(self):
        gdft = (FW / "k1_gdft_core.cpp").read_text()
        self.assertIn("nyquist_safe_bin_hi", gdft)
        self.assertIn("if (i >= nyquist_safe_bin_hi)", gdft)
        self.assertIn("magnitudes_normalized_avg[i] = 0.0f", gdft)
        self.assertIn("continue;", gdft)
        # Phase 1 must not touch the ×2 block_size formula.
        # (Phase 2 later replaces ×2 with crossover Rayleigh; this Phase-1 lock
        # was superseded — see test_phase2_block_size_formula_global_one_semitone.)
        system_h = (FW / "system.h").read_text()
        self.assertIn("resolution_div", system_h)
        self.assertIn("K1_GDFT_X2_CROSSOVER_BIN", system_h)

    def test_phase2_block_size_formula_global_one_semitone(self):
        constants = CONSTANTS
        system_h = (FW / "system.h").read_text()
        self.assertIn("#define K1_GDFT_X2_CROSSOVER_BIN 0u", constants)
        self.assertIn(
            "const float resolution_div = (i < x2_cross) ? 2.0f : 1.0f;",
            system_h,
        )
        self.assertIn(
            "frequencies[i].block_size = CONFIG.SAMPLE_RATE / (max_distance_hz * resolution_div);",
            system_h,
        )

    def test_vp_spectrum_paint_uses_analysis_authority_not_ghosts(self):
        river = (FW / "light_mode_spectrum_river.cpp").read_text()
        gdft_fx = (FW / "light_mode_gdft.cpp").read_text()
        self.assertIn("sb_gdft_nyquist_safe_bin_hi(CONFIG.SAMPLE_RATE, CONFIG.NOTE_OFFSET)", river)
        self.assertIn("k < analysis_bins && k < HALF", river)
        self.assertNotIn("k < NUM_FREQS && k < HALF", river)
        self.assertIn("analysis_bins", gdft_fx)
        self.assertIn("freq_prog * (SQ15x16)analysis_hi", gdft_fx)
        self.assertNotIn("freq_prog * (NUM_FREQS - 1)", gdft_fx)


if __name__ == "__main__":
    unittest.main()
