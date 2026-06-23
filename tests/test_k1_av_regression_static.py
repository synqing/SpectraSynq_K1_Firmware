"""Static tests for the K1 audio-visual regression pack (host-only)."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "scripts" / "regression-harness"
SERIAL_MENU = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "serial" / "serial_menu.h"
sys.path.insert(0, str(HARNESS))

import k1_av_event_quality as event_quality  # noqa: E402
import k1_av_layer_classifier as lc  # noqa: E402
import k1_av_manifest as manifest_mod  # noqa: E402
import device_novelty_replay as novelty_replay  # noqa: E402


GUARD_LINE = (
    "RUNTIME_TIMING_GUARD: timing_ok=1 sample_rate=12800 samples_per_chunk=96 tempo_decim=3 "
    "declared_ap_hz=133.333 declared_nov_hz=44.444 response_gain=3.000 dma_desc=3 ap_core=0 vp_core=1 core_ok=1 vp_task_created=1"
)

LEGACY_GUARD_LINE = GUARD_LINE.replace("response_gain=3.000 ", "")


class K1AvRegressionStaticTest(unittest.TestCase):
    def test_parse_runtime_timing_guard(self):
        parsed = lc.parse_runtime_timing_guard(GUARD_LINE)
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed["timing_ok"], 1)
        self.assertEqual(parsed["ap_core"], 0)
        self.assertEqual(parsed["vp_core"], 1)
        self.assertEqual(parsed["response_gain"], 3.0)

    def test_parse_runtime_timing_guard_keeps_legacy_logs_readable(self):
        parsed = lc.parse_runtime_timing_guard(LEGACY_GUARD_LINE)
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed["timing_ok"], 1)
        self.assertNotIn("response_gain", parsed)

    def test_validate_runtime_guard_pass(self):
        parsed = lc.parse_runtime_timing_guard(GUARD_LINE)
        ok, classification, _ = lc.validate_runtime_guard(parsed)
        self.assertTrue(ok)
        self.assertEqual(classification, "PASS_timing_and_tempo")

    def test_validate_runtime_guard_fail_core(self):
        parsed = lc.parse_runtime_timing_guard(GUARD_LINE.replace("core_ok=1", "core_ok=0"))
        ok, classification, _ = lc.validate_runtime_guard(parsed)
        self.assertFalse(ok)
        self.assertEqual(classification, "FAIL_core_invariant")

    def test_production_click_near_127_passes(self):
        rows = []
        for idx in range(45):
            rows.append(
                {
                    "t_ms": idx * 1000,
                    "bpm": 127.0,
                    "conf": 0.55 if idx < 40 else 0.75,
                    "lock": 1 if idx >= 42 else 0,
                    "beat": 1 if idx % 4 == 0 else 0,
                    "onset": 0,
                    "bass": 0,
                }
            )
        summary = lc.summarise_production_ap_stream(rows, warm_ms=15000, expected_bpm=127)
        classification, _ = lc.classify_production_tempo(
            summary,
            expected_bpm=127,
            fixture_type="synthetic_control",
        )
        self.assertEqual(classification, "PASS_timing_and_tempo")

    def test_production_wrong_lane_fails(self):
        rows = [
            {"t_ms": 20000 + idx * 1000, "bpm": 88.0, "conf": 0.8, "lock": 1, "beat": 0, "onset": 0, "bass": 0}
            for idx in range(20)
        ]
        summary = lc.summarise_production_ap_stream(rows, warm_ms=15000, expected_bpm=127)
        classification, _ = lc.classify_production_tempo(
            summary,
            expected_bpm=127,
            fixture_type="synthetic_control",
        )
        self.assertEqual(classification, "FAIL_tempo_lane")

    def test_device_novelty_replay_supports_non_127_expected_bpm(self):
        frames = [
            {"t_ms": idx * 1000, "bpm": 84.0, "conf": 0.75, "lock": 1, "phase": 0.0, "beat": 0}
            for idx in range(10)
        ]
        summary = novelty_replay.summarise_frames(
            frames,
            warm_ms=2000,
            high_conf=0.60,
            expected_bpm=84,
            near_bpm_tolerance=3,
        )
        self.assertEqual(summary["warm_high_or_locked_near_target_rows"], 8)
        self.assertEqual(summary["warm_high_or_locked_near_127_rows"], 0)
        self.assertEqual(
            novelty_replay.classify({"row_count": 10}, summary, expected_bpm=84, near_bpm_tolerance=3),
            "declared_rate_device_nov_replay_locks_near_target",
        )

    def test_device_novelty_replay_names_timing_but_weak_lock(self):
        summary = {
            "warm_frame_count": 20,
            "warm_high_or_locked_near_target_rows": 0,
            "warm_high_or_locked_count": 0,
            "warm_bpm_counts": {"129": 20},
        }
        self.assertEqual(
            novelty_replay.classify({"row_count": 10}, summary, expected_bpm=127, near_bpm_tolerance=3),
            "declared_rate_device_nov_replay_timing_but_weak_lock",
        )

    def test_apcad_capture_supports_ffplay_gain_path(self):
        source = (HARNESS / "device_ap_cadence_capture.py").read_text(encoding="utf-8")
        self.assertIn('parser.add_argument("--player"', source)
        self.assertIn('choices=("afplay", "ffplay")', source)
        self.assertIn('parser.add_argument("--playback-gain-db"', source)
        self.assertIn("def build_playback_command", source)
        self.assertIn("ffplay", source)
        self.assertIn("volume={float(args.playback_gain_db):.3f}dB", source)

    def test_apcad_dump_yields_during_large_serial_prints(self):
        source = SERIAL_MENU.read_text(encoding="utf-8")
        self.assertIn("void ap_cad_capture_dump()", source)
        self.assertIn("USBSerial.println(\",src=buf\");", source)
        self.assertIn("if ((i & 0x0F) == 0x0F)", source)
        self.assertIn("vTaskDelay(1);", source)

    def test_apcad_capture_records_stage_probe_field(self):
        source = SERIAL_MENU.read_text(encoding="utf-8")
        ino = (ROOT / "SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino").read_text(encoding="utf-8")
        capture = (HARNESS / "device_ap_cadence_capture.py").read_text(encoding="utf-8")
        self.assertIn("uint8_t stage;", source)
        self.assertIn("sample.stage = frame.stage;", source)
        self.assertIn('USBSerial.print(",stage=");', source)
        self.assertIn('"unique_stage": unique_sorted(rows, "stage")', capture)
        self.assertIn('"tempo_acf_elapsed_us": describe_ms([numeric(row, "tempo_acf_us") for row in rows])', capture)
        self.assertIn("SB_AP_STAGE_GDFT", ino)
        self.assertIn("SB_AP_STAGE_NOVELTY", ino)
        self.assertIn("SB_AP_STAGE_SNAPSHOT", ino)
        self.assertIn("SB_AP_STAGE_ONSET", ino)
        self.assertIn("SB_AP_STAGE_SALIENCY", ino)
        self.assertIn("SB_AP_STAGE_TEMPO", ino)
        self.assertIn("sb_ap_cadence_capture_frame", ino)

    def test_tempo_profiler_timer_is_diagnostic_only(self):
        tempo = (ROOT / "SPECTRASYNQ_K1_FIRMWARE/audio/sb_tempo.cpp").read_text(encoding="utf-8")

        self.assertIn("#if ENABLE_TEMPO_STREAM\n#if __has_include(<esp_timer.h>)", tempo)
        self.assertIn("static inline int64_t sb_tempo_diag_time_us()", tempo)
        self.assertEqual(tempo.count("esp_timer_get_time()"), 1)

        self.assertIn(
            "#define SB_TEMPO_AP_FRAME_HZ ((float)DEFAULT_SAMPLE_RATE / (float)DEFAULT_SAMPLES_PER_CHUNK)",
            tempo,
        )
        self.assertIn("#define SB_TEMPO_ACF_REFRESH_DECIMATION 1U", tempo)
        self.assertIn("SB_NOVELTY_RATE_HZ    = SB_AP_FRAME_HZ / (float)SB_NOVELTY_DECIMATION", tempo)
        self.assertIn("if (++sb_frame_ctr < SB_NOVELTY_DECIMATION)", tempo)

    def test_16k_acf_amortisation_probe_is_non_shippable_env_only(self):
        tempo = (ROOT / "SPECTRASYNQ_K1_FIRMWARE/audio/sb_tempo.cpp").read_text(encoding="utf-8")
        platformio = (ROOT / "platformio.ini").read_text(encoding="utf-8")
        guard = (ROOT / "scripts/platformio/k1_upload_guard.py").read_text(encoding="utf-8")

        env_name = "k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_stage_tempo_acf_d8"
        self.assertIn(env_name, platformio)
        self.assertIn(env_name, guard)
        self.assertIn("-DSB_TEMPO_ACF_REFRESH_DECIMATION=8U", platformio)
        self.assertIn("if (sb_acf_refresh_now)", tempo)
        self.assertIn("production leaves the", tempo)

    def test_16k_acf_spread_probe_is_non_shippable_env_only(self):
        tempo = (ROOT / "SPECTRASYNQ_K1_FIRMWARE/audio/sb_tempo.cpp").read_text(encoding="utf-8")
        tempo_h = (ROOT / "SPECTRASYNQ_K1_FIRMWARE/audio/sb_tempo.h").read_text(encoding="utf-8")
        serial = (ROOT / "SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h").read_text(encoding="utf-8")
        capture = (HARNESS / "device_ap_cadence_capture.py").read_text(encoding="utf-8")
        platformio = (ROOT / "platformio.ini").read_text(encoding="utf-8")
        guard = (ROOT / "scripts/platformio/k1_upload_guard.py").read_text(encoding="utf-8")

        env_name = "k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_stage_tempo_acf_spread16"
        spread12_env = "k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_stage_tempo_acf_spread12"
        spread8_env = "k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_stage_tempo_acf_spread8"
        spread4_env = "k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_stage_tempo_acf_spread4"
        full_ap_spread8_env = "k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_acf_spread8"
        full_ap_spread4_env = "k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1_acf_spread4"
        self.assertIn(env_name, platformio)
        self.assertIn(spread12_env, platformio)
        self.assertIn(spread8_env, platformio)
        self.assertIn(spread4_env, platformio)
        self.assertIn(full_ap_spread8_env, platformio)
        self.assertIn(full_ap_spread4_env, platformio)
        self.assertIn(env_name, guard)
        self.assertIn(spread12_env, guard)
        self.assertIn(spread8_env, guard)
        self.assertIn(spread4_env, guard)
        self.assertIn(full_ap_spread8_env, guard)
        self.assertIn(full_ap_spread4_env, guard)
        self.assertIn("-DSB_TEMPO_ACF_SPREAD_PROBE=1", platformio)
        self.assertIn("-DSB_TEMPO_ACF_SPREAD_LAGS_PER_EMIT=16U", platformio)
        self.assertIn("-DSB_TEMPO_ACF_SPREAD_LAGS_PER_EMIT=12U", platformio)
        self.assertIn("-DSB_TEMPO_ACF_SPREAD_LAGS_PER_EMIT=8U", platformio)
        self.assertIn("-DSB_TEMPO_ACF_SPREAD_LAGS_PER_EMIT=4U", platformio)
        self.assertIn("-DSB_TEMPO_ACF_SKIP_UPDATE_ON_PUBLISH=1", platformio)
        self.assertIn("#define SB_TEMPO_ACF_SKIP_UPDATE_ON_PUBLISH 0", tempo)
        self.assertIn("#define SB_TEMPO_ACF_SPREAD_PROBE 0", tempo)
        self.assertIn("sb_compute_acf_salience_spread", tempo)
        self.assertIn("sb_acf_spread_publish_pending", tempo)
        self.assertIn("if (!sb_acf_published_now)", tempo)
        self.assertIn("if (!sb_acf_spread_active) return false;", tempo)
        self.assertIn("d.acf_spread_active", tempo)
        self.assertIn("uint16_t acf_lag_cursor;", tempo_h)
        self.assertIn('USBSerial.print(",acf_spread=");', serial)
        self.assertIn('"acf_spread_active_rows": acf_spread_rows', capture)
        self.assertIn('"active_ap_work_over_7500_count":', capture)

    def test_apcad_compact_soak_command_is_bounded_and_abortable(self):
        serial = (ROOT / "SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h").read_text(encoding="utf-8")
        ino = (ROOT / "SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino").read_text(encoding="utf-8")

        self.assertIn("#define AP_CAD_SOAK_MAX_MS 600000UL", serial)
        self.assertIn("#define AP_CAD_SOAK_WORST_COUNT 16", serial)
        self.assertIn("static uint32_t AP_CAD_SOAK_ACTIVE_HIST", serial)
        self.assertIn("void ap_cad_soak_tick", serial)
        self.assertIn("APCAD_SOAK_DONE,ver=1", serial)
        self.assertIn("APCAD_SOAK_WORST,ver=1", serial)
        self.assertIn('strcmp(command_type, "apcad_soak")', serial)
        self.assertIn('strcmp(command_type, "apcad_soak_status")', serial)
        self.assertIn('strcmp(command_type, "apcad_abort")', serial)
        self.assertIn("AP_CAD_SOAK_ACTIVE = false;", serial)
        self.assertIn("ap_cad_soak_tick(ap_cadence_frame);", ino)
        capture = (HARNESS / "device_ap_cadence_capture.py").read_text(encoding="utf-8")
        self.assertIn('parser.add_argument("--compact-soak"', capture)
        self.assertIn('arm_cmd = f"apcad_soak={args.duration_ms}" if args.compact_soak', capture)
        self.assertIn('"core_bad_count": int(numeric(soak, "core_bad"))', capture)
        self.assertIn('"compact_soak_mode": bool(args.compact_soak)', capture)

    def test_apcad_capture_buffers_tempo_v2_lock_fields(self):
        source = (ROOT / "SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h").read_text(encoding="utf-8")
        for token in (
            "winner_bpm_q8_8",
            "top1_bpm_q8_8",
            "v2_conf_ema_q16",
            "v2_quality_q16",
            "v2_hist_share_q16",
            "v2_prominence_q16",
            "v2_periodicity_q16",
            "v2_peak_share_q16",
            "tempo_acf_elapsed_us",
            "acf_lag_cursor",
            "acf_publish_count",
            ",tempo_acf_us=",
            ",tempo_emit_us=",
            ",acf_spread=",
            ",acf_lag_cursor=",
            ",acf_pub=",
            ",v2_ema=",
            ",v2_q=",
            ",v2_lock=",
        ):
            with self.subTest(token=token):
                self.assertIn(token, source)

    def test_silence_fixture_false_lock(self):
        rows = [
            {"t_ms": 6000 + idx * 1000, "bpm": 120.0, "conf": 0.85, "lock": 1, "beat": 0, "onset": 0, "bass": 0}
            for idx in range(8)
        ]
        summary = lc.summarise_production_ap_stream(rows, warm_ms=5000, expected_bpm=None)
        summary["max_conf"] = 0.85
        summary["lock_frac"] = 1.0
        classification, _ = lc.classify_production_tempo(
            summary,
            expected_bpm=None,
            fixture_type="silence_noise",
        )
        self.assertEqual(classification, "FAIL_false_positive_silence_noise")

    def test_silence_event_lane_known_label(self):
        summary = {
            "product_feel_verdict": "FAIL",
            "product_feel_reason": "silence fixture had onsets_per_min=67.5",
        }
        event_class, _ = lc.classify_event_layer(summary, fixture_type="silence_noise")
        self.assertEqual(event_class, lc.SILENCE_EVENT_FAIL_KNOWN)

    def test_silence_event_fail_does_not_block_matrix(self):
        entry = {
            "id": "silence_noise",
            "skipped": False,
            "primary_classification": "PASS_timing_and_tempo",
            "event_classification": lc.SILENCE_EVENT_FAIL_KNOWN,
        }
        self.assertFalse(lc.is_matrix_blocking_failure(entry))

    def test_onset_v2_open_quiet_gate_is_output_permission_only(self):
        source = (ROOT / "SPECTRASYNQ_K1_FIRMWARE/audio/sb_onset_beat.cpp").read_text(encoding="utf-8")
        self.assertIn("SBV2_QUIET_SPECTRAL_FLOOR = 0.08f", source)
        self.assertIn("SBV2_QUIET_NOVELTY_FLOOR  = 0.08f", source)
        self.assertIn("bool open_quiet = audio.spectral_energy < SBV2_QUIET_SPECTRAL_FLOOR", source)
        self.assertIn("bool inactive = audio.spectral_energy < SBV2_ACT_FLOOR || open_quiet", source)
        self.assertIn("stats updates below run regardless", source)

    def test_tempo_lane_fail_blocks_matrix(self):
        entry = {
            "id": "click_127",
            "skipped": False,
            "primary_classification": "FAIL_tempo_lane",
        }
        self.assertTrue(lc.is_matrix_blocking_failure(entry))

    def test_compute_matrix_verdict_pass_with_open_finding(self):
        fixture_results = [
            {
                "id": "silence_noise",
                "skipped": False,
                "primary_classification": "PASS_timing_and_tempo",
                "event_classification": lc.SILENCE_EVENT_FAIL_KNOWN,
            },
            {
                "id": "click_127",
                "skipped": False,
                "primary_classification": "PASS_timing_and_tempo",
            },
        ]
        verdict, _, open_findings = lc.compute_matrix_verdict(
            runtime_ok=True,
            runtime_class="PASS_timing_and_tempo",
            fixture_results=fixture_results,
            fixtures_total=2,
        )
        self.assertEqual(verdict, "PASS_WITH_OPEN_FINDINGS")
        self.assertIn(lc.OPEN_FINDING_P1_SILENCE_ONSETS, open_findings)

    def test_compute_matrix_verdict_reconciled_weak_lock_does_not_partial(self):
        fixture_results = [
            {
                "id": "click_127",
                "skipped": False,
                "classification": "PASS_timing_but_weak_lock",
                "primary_classification": "PASS_timing_but_weak_lock",
            },
            {
                "id": "slow_84_syncopated",
                "skipped": False,
                "classification": "PASS_timing_and_tempo",
                "primary_classification": "PASS_timing_and_tempo",
            },
        ]
        verdict, next_action, open_findings = lc.compute_matrix_verdict(
            runtime_ok=True,
            runtime_class="PASS_timing_and_tempo",
            fixture_results=fixture_results,
            fixtures_total=2,
        )
        self.assertEqual(verdict, "PASS")
        self.assertIn("Scene Policy v2", next_action)
        self.assertEqual(open_findings, [])

    def test_compute_matrix_verdict_loreen_weak_lock_stays_partial(self):
        fixture_results = [
            {
                "id": "loreen_127",
                "skipped": False,
                "classification": "PASS_timing_but_weak_lock",
                "primary_classification": "PASS_timing_but_weak_lock",
            },
            {
                "id": "click_127",
                "skipped": False,
                "classification": "PASS_timing_but_weak_lock",
                "primary_classification": "PASS_timing_but_weak_lock",
            },
        ]
        verdict, next_action, open_findings = lc.compute_matrix_verdict(
            runtime_ok=True,
            runtime_class="PASS_timing_and_tempo",
            fixture_results=fixture_results,
            fixtures_total=2,
        )
        self.assertEqual(verdict, "PARTIAL")
        self.assertIn("loreen_127", next_action)
        self.assertIn(lc.OPEN_FINDING_P2_LOREEN_WEAK_LOCK, open_findings)

    def test_compute_matrix_verdict_clears_closed_silence_lane(self):
        fixture_results = [
            {
                "id": "silence_noise",
                "skipped": False,
                "primary_classification": "PASS_timing_and_tempo",
                "event_classification": None,
            },
            {
                "id": "click_127",
                "skipped": False,
                "primary_classification": "PASS_timing_and_tempo",
            },
        ]
        verdict, next_action, open_findings = lc.compute_matrix_verdict(
            runtime_ok=True,
            runtime_class="PASS_timing_and_tempo",
            fixture_results=fixture_results,
            fixtures_total=2,
        )
        self.assertEqual(verdict, "PASS")
        self.assertEqual(open_findings, [])
        self.assertIn("Scene Policy v2", next_action)

    def test_silence_primary_fail_does_not_block_matrix(self):
        entry = {
            "id": "silence_noise",
            "skipped": False,
            "primary_classification": "FAIL_false_positive_silence_noise",
            "event_classification": lc.SILENCE_EVENT_FAIL_KNOWN,
        }
        self.assertFalse(lc.is_matrix_blocking_failure(entry))

    def test_generated_fast_replacement_active_required(self):
        manifest_path = HARNESS / "fixtures/k1_av_regression_fixtures.template.json"
        manifest = manifest_mod.load_manifest(manifest_path)
        fast = next(item for item in manifest["fixtures"] if item["id"] == "fast_127_fourfloor")
        self.assertEqual(fast["resolved_path"], "__generated_control_127_fourfloor__")
        self.assertTrue(fast["required"])
        self.assertEqual(fast["status"], "active")
        available, reason = manifest_mod.fixture_availability(fast)
        self.assertTrue(available, reason)

    def test_fast_130_historical_fixture_blocked(self):
        manifest_path = HARNESS / "fixtures/k1_av_regression_fixtures.template.json"
        manifest = manifest_mod.load_manifest(manifest_path)
        fast = next(item for item in manifest["fixtures"] if item["id"] == "fast_130_fourfloor")
        self.assertFalse(fast["required"])
        self.assertEqual(fast["status"], "blocked")
        available, reason = manifest_mod.fixture_availability(fast)
        self.assertFalse(available)
        self.assertIn("fast_127_fourfloor", reason)

    def test_metadata_marked_semantic_failure_does_not_block_matrix(self):
        entry = {
            "id": "historical_unsuitable_fixture",
            "fixture": {"matrix_tempo_gate": "known_host_semantic_failure"},
            "skipped": False,
            "required": True,
            "primary_classification": "FAIL_tempo_lane",
        }
        self.assertFalse(lc.is_matrix_blocking_failure(entry))

    def test_generated_fast_replacement_failure_blocks_matrix(self):
        entry = {
            "id": "fast_127_fourfloor",
            "skipped": False,
            "required": True,
            "primary_classification": "FAIL_tempo_lane",
        }
        self.assertTrue(lc.is_matrix_blocking_failure(entry))

    def test_dense_clipped_active(self):
        manifest_path = HARNESS / "fixtures/k1_av_regression_fixtures.template.json"
        manifest = manifest_mod.load_manifest(manifest_path)
        dense = next(item for item in manifest["fixtures"] if item["id"] == "dense_clipped_edm")
        self.assertEqual(dense["start_ms"], 80000)
        self.assertEqual(dense["status"], "active")
        available, _ = manifest_mod.fixture_availability(dense)
        if not available:
            self.skipTest("dense_clipped_edm audio fixture is not committed (dev-machine only)")
        self.assertTrue(available)

    def test_pending_fixture_skipped_not_failed(self):
        pending_fixture = {
            "id": "synthetic_pending",
            "path": "PENDING_CAPTAIN_TRACK_PATH",
            "status": "pending",
            "required": False,
        }
        available, reason = manifest_mod.fixture_availability(pending_fixture)
        self.assertFalse(available)
        self.assertIn("pending", reason)
        classification = lc.combine_fixture_classification(
            runtime_ok=True,
            runtime_class="PASS_timing_and_tempo",
            primary_class="PASS_timing_and_tempo",
            event_class=None,
            skipped=True,
        )
        self.assertEqual(classification, "SKIPPED_pending_fixture")

    def test_fixture_order_silence_first(self):
        manifest_path = HARNESS / "fixtures/k1_av_regression_fixtures.template.json"
        manifest = manifest_mod.load_manifest(manifest_path)
        ordered = manifest_mod.order_fixtures(list(manifest["fixtures"]))
        self.assertEqual(ordered[0]["id"], "silence_noise")

        manifest_path = HARNESS / "fixtures/k1_av_regression_fixtures.template.json"
        manifest = manifest_mod.load_manifest(manifest_path)
        silence = next(item for item in manifest["fixtures"] if item["id"] == "silence_noise")
        self.assertEqual(silence["resolved_path"], "__generated_silence__")
        available, _ = manifest_mod.fixture_availability(silence)
        self.assertTrue(available)

        manifest_path = HARNESS / "fixtures/k1_av_regression_fixtures.template.json"
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        ids = {item["id"] for item in data["fixtures"]}
        for required_id in (
            "click_127",
            "loreen_127",
            "slow_84_syncopated",
            "fast_127_fourfloor",
            "dense_clipped_edm",
            "silence_noise",
        ):
            self.assertIn(required_id, ids)

    def test_halftime_suspect_blocked_with_slow_80_replacement(self):
        manifest_path = HARNESS / "fixtures/k1_av_regression_fixtures.template.json"
        manifest = manifest_mod.load_manifest(manifest_path)
        halftime = next(item for item in manifest["fixtures"] if item["id"] == "halftime_suspect_80")
        replacement = next(item for item in manifest["fixtures"] if item["id"] == "slow_80_fourfloor")
        self.assertFalse(halftime["required"])
        self.assertEqual(halftime["status"], "blocked")
        available, reason = manifest_mod.fixture_availability(halftime)
        self.assertFalse(available)
        self.assertIn("slow_84_syncopated", reason)
        self.assertFalse(replacement["required"])
        self.assertEqual(replacement["status"], "blocked")
        self.assertEqual(replacement["control_pattern"], "fourfloor")
        available, reason = manifest_mod.fixture_availability(replacement)
        self.assertFalse(available)
        self.assertIn("slow_84_syncopated", reason)

    def test_event_quality_silence_pass(self):
        rows = [
            {"t_ms": 6000 + idx * 1000, "bpm": 0.0, "conf": 0.05, "lock": 0, "beat": 0, "onset": 0, "bass": 0}
            for idx in range(8)
        ]
        summary = event_quality.summarise_event_quality(
            rows,
            warm_ms=5000,
            fixture_type="silence_noise",
            duration_ms=15000,
        )
        self.assertEqual(summary["product_feel_verdict"], "PASS")

    def test_ffplay_command_click_defaults_start_zero(self):
        manifest_path = HARNESS / "fixtures/k1_av_regression_fixtures.template.json"
        manifest = manifest_mod.load_manifest(manifest_path)
        click = next(item for item in manifest["fixtures"] if item["id"] == "click_127")
        start_ms, duration_ms = manifest_mod.resolve_playback_window(click)
        gain_db, _ = manifest_mod.resolve_playback_gain_db(click, manifest)
        self.assertEqual(start_ms, 0)
        self.assertGreater(gain_db, 3.0)
        cmd = manifest_mod.build_ffplay_command(
            click["resolved_path"],
            start_ms=start_ms,
            duration_ms=duration_ms,
            gain_db=gain_db,
            playback_settings=manifest_mod.playback_settings(manifest),
        )
        self.assertIn("-af", cmd)
        self.assertEqual(cmd[0], "ffplay")
        self.assertIn("-ss", cmd)
        self.assertIn("-t", cmd)
        self.assertIn("-i", cmd)

    def test_ffplay_command_acestep_offset_window(self):
        manifest_path = HARNESS / "fixtures/k1_av_regression_fixtures.template.json"
        manifest = manifest_mod.load_manifest(manifest_path)
        anchor = next(
            item for item in manifest["fixtures"] if item["id"] == "acestep_steady_groove"
        )
        start_ms, duration_ms = manifest_mod.resolve_playback_window(anchor)
        self.assertEqual(start_ms, 125000)
        self.assertEqual(duration_ms, 25000)
        available, _ = manifest_mod.fixture_availability(anchor)
        if not available:
            self.skipTest("acestep_steady_groove audio fixture is not committed (dev-machine only)")
        gain_db, _ = manifest_mod.resolve_playback_gain_db(anchor, manifest)
        self.assertLess(gain_db, 0.0)
        cmd = manifest_mod.build_ffplay_command(
            anchor["resolved_path"],
            start_ms=start_ms,
            duration_ms=duration_ms,
            gain_db=gain_db,
            playback_settings=manifest_mod.playback_settings(manifest),
        )
        self.assertIn("-af", cmd)
        af = cmd[cmd.index("-af") + 1]
        self.assertIn("volume=", af)

    def test_optional_tempo_fail_does_not_block_matrix(self):
        entry = {
            "id": "acestep_kick_drop_heavy",
            "skipped": False,
            "required": False,
            "primary_classification": "FAIL_tempo_lane",
        }
        self.assertFalse(lc.is_matrix_blocking_failure(entry))

    def test_exploratory_tempo_gate_never_fails_lane(self):
        summary = {
            "warm_row_count": 10,
            "lock_frac": 0.1,
            "max_conf": 0.2,
            "warm_median_bpm": 118.0,
        }
        classification, _ = lc.classify_production_tempo(
            summary,
            expected_bpm=None,
            fixture_type="known_real_music",
            tempo_gate="product_feel_only",
        )
        self.assertEqual(classification, "INCONCLUSIVE_exploratory_anchor")
        summary["lock_frac"] = 0.5
        classification, _ = lc.classify_production_tempo(
            summary,
            expected_bpm=None,
            fixture_type="known_real_music",
            tempo_gate="product_feel_only",
        )
        self.assertEqual(classification, "PASS_timing_and_tempo")

    def test_acestep_active_when_paths_exist(self):
        manifest_path = HARNESS / "fixtures/k1_av_regression_fixtures.template.json"
        manifest = manifest_mod.load_manifest(manifest_path)
        anchor = next(
            item for item in manifest["fixtures"] if item["id"] == "acestep_kick_drop_heavy"
        )
        self.assertEqual(anchor["status"], "active")
        available, _ = manifest_mod.fixture_availability(anchor)
        self.assertEqual(available, Path(anchor["resolved_path"]).expanduser().exists())


if __name__ == "__main__":
    unittest.main()
