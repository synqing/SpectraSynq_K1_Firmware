"""Static / pure-logic tests for scripts/regression-harness/wireless_ab_bench.py.

No device, no serial, no afplay, no g++. Validates:
- stimulus generator (duration, sample rate, silence windows, beat energy, peak)
- metric computation on fabricated host-timestamped serial logs
- pre-registered compare/verdict threshold logic
- command-plan safety (no calibration/erase/flash; no flashing in the tool)
"""

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "regression-harness" / "wireless_ab_bench.py"


def load_module():
    spec = importlib.util.spec_from_file_location("wireless_ab_bench", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BENCH = load_module()


def make_ap_line(
    ts: float,
    *,
    peak: float = 0.5,
    silence: int = 0,
    bpm: float = 120.0,
    conf: float = 0.62,
    lock: int = 1,
    onset: int = 0,
    bass: int = 0,
) -> str:
    return (
        "[%.3f] [AP] SSL=281 DC=-8767 max_raw=12000 follower=9000 peak_scaled=%.3f "
        "silent_scale=1.000 silence=%d cal_source=flash cal_valid=1 | "
        "bpm=%.1f conf=%.2f lock=%d phase=0.25 beat=0 bstr=0.40 | "
        "onset=%d bass=%d ostr=0.30" % (ts, peak, silence, bpm, conf, lock, onset, bass)
    )


def make_vpf_line(ts: float, seq: int, frame_avg: int = 5200, frame_max: int = 9100) -> str:
    return (
        "[%.3f] VPF,ver=1,seq=%d,mode=22,smode=3,sec=1,acq_us=120/300,vu_us=20/45,"
        "gdft_us=900/1400,smooth_us=300/600,pri_render_us=1500/2600,sec_render_us=800/1500,"
        "pri_prep_us=100/220,sec_prep_us=90/200,quant_pri_us=200/380,quant_sec_us=150/320,"
        "show_us=700/1300,frame_us=%d/%d" % (ts, seq, frame_avg, frame_max)
    )


class StimulusTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sr = BENCH.STIMULUS_SR
        cls.samples = BENCH.generate_stimulus()

    def test_duration_and_sample_rate(self):
        self.assertEqual(self.sr, 48000)
        self.assertEqual(len(self.samples), int(BENCH.STIMULUS_DURATION_S * self.sr))
        self.assertEqual(str(self.samples.dtype), "float32")

    def test_fixed_peak_amplitude(self):
        peak = float(abs(self.samples).max())
        self.assertAlmostEqual(peak, BENCH.STIMULUS_PEAK, places=3)

    def test_silence_cut_windows_are_fully_silent(self):
        for cut_start, cut_end in BENCH.SILENCE_CUTS:
            window = self.samples[int(cut_start * self.sr): int(cut_end * self.sr)]
            self.assertEqual(float(abs(window).max()), 0.0, "cut %s-%s not silent" % (cut_start, cut_end))
            self.assertAlmostEqual(cut_end - cut_start, 1.5)
        self.assertEqual(len(BENCH.SILENCE_CUTS), 2)

    def test_final_ten_seconds_are_silent(self):
        tail = self.samples[int(BENCH.FINAL_SILENCE_START_S * self.sr):]
        self.assertEqual(float(abs(tail).max()), 0.0)
        self.assertAlmostEqual(len(tail) / self.sr, 10.0, places=3)

    def test_beats_have_energy_at_120_bpm(self):
        # Energy in a 100 ms window at each of the first 8 beats (0.5 s grid).
        for beat in range(8):
            i0 = int(beat * 0.5 * self.sr)
            window = self.samples[i0: i0 + int(0.1 * self.sr)]
            self.assertGreater(float(abs(window).max()), 0.05, "no energy at beat %d" % beat)
        # And an off-beat gap (between kick decay and next beat) is quieter than the beat onset.
        gap = self.samples[int(0.42 * self.sr): int(0.46 * self.sr)]
        onset = self.samples[0: int(0.05 * self.sr)]
        self.assertLess(float(abs(gap).max()), float(abs(onset).max()))


class ApLineParsingTest(unittest.TestCase):
    def test_split_host_line(self):
        ts, payload = BENCH.split_host_line("[1718000000.123] [AP] SSL=281")
        self.assertAlmostEqual(ts, 1718000000.123)
        self.assertEqual(payload, "[AP] SSL=281")

    def test_parse_kv_payload_handles_pipes_and_types(self):
        _, payload = BENCH.split_host_line(make_ap_line(1.0, peak=0.512, onset=1))
        fields = BENCH.parse_kv_payload(payload.split("[AP]", 1)[1])
        self.assertEqual(fields["SSL"], 281)
        self.assertEqual(fields["DC"], -8767)
        self.assertAlmostEqual(fields["peak_scaled"], 0.512)
        self.assertEqual(fields["lock"], 1)
        self.assertEqual(fields["onset"], 1)
        self.assertEqual(fields["cal_source"], "flash")

    def test_parse_vpf_payload_avg_max_pairs(self):
        _, payload = BENCH.split_host_line(make_vpf_line(1.0, seq=7))
        fields = BENCH.parse_vpf_payload(payload)
        self.assertEqual(fields["seq"], 7)
        self.assertEqual(fields["frame_us"], {"avg": 5200, "max": 9100})


class RunMetricsTest(unittest.TestCase):
    def build_log(self):
        lines = []
        t0 = 1718000000.0
        # 10 [AP] lines at a clean 1 Hz cadence; sample 7 has a +0.4 s stall.
        offsets = [0, 1, 2, 3, 4, 5, 6, 7.4, 8.4, 9.4]
        for i, off in enumerate(offsets):
            silence = 1 if i in (4, 5) else 0
            lock = 0 if i in (0, 4, 5) else 1
            conf = 0.30 if i == 0 else 0.62
            onset = 1 if i in (1, 3) else 0
            bass = 1 if i == 1 else 0
            lines.append(
                make_ap_line(
                    t0 + off, peak=0.5, silence=silence, lock=lock, conf=conf,
                    onset=onset, bass=bass, bpm=120.0 if lock else 0.0,
                )
            )
        # VPF reports with one seq gap (3 -> 5).
        lines.append(make_vpf_line(t0 + 1.0, seq=1))
        lines.append(make_vpf_line(t0 + 2.0, seq=2))
        lines.append(make_vpf_line(t0 + 3.0, seq=3))
        lines.append(make_vpf_line(t0 + 5.0, seq=5))
        lines.append(make_vpf_line(t0 + 6.0, seq=6, frame_avg=6000, frame_max=12000))
        # One crash marker, one garbage line, one command echo (ignored).
        lines.append("[%.3f] Guru Meditation Error: Core 1 panic'ed" % (t0 + 6.5))
        lines.append("[%.3f] �� junk" % (t0 + 6.6))
        lines.append("[%.3f] >>> :ap_stream=on" % (t0 + 0.1))
        return lines

    def setUp(self):
        self.metrics = BENCH.compute_run_metrics(self.build_log())

    def test_crash_and_garbage_counts(self):
        self.assertEqual(self.metrics["crash_markers"], 1)
        self.assertEqual(self.metrics["garbage_lines"], 1)

    def test_beat_metrics_active_only(self):
        beat = self.metrics["beat"]
        self.assertEqual(beat["active_samples"], 8)       # 2 silence samples excluded
        self.assertEqual(beat["locked_samples"], 7)       # active minus the conf=0.30 unlocked one
        self.assertAlmostEqual(beat["lock_ratio_active"], 7.0 / 8.0)
        expected_conf = (0.30 + 0.62 * 7) / 8.0
        self.assertAlmostEqual(beat["conf_mean_active"], expected_conf, places=4)
        self.assertAlmostEqual(beat["bpm_mean_locked"], 120.0)
        self.assertEqual(beat["bpm_std_locked"], 0.0)
        self.assertAlmostEqual(beat["bpm_abs_err_vs_120"], 0.0)

    def test_onset_counts_are_sampled_proxies(self):
        self.assertEqual(self.metrics["onset"]["onset_sampled_count"], 2)
        self.assertEqual(self.metrics["onset"]["bass_sampled_count"], 1)

    def test_peak_scaled_distribution(self):
        peak = self.metrics["peak_scaled"]
        self.assertAlmostEqual(peak["mean"], 0.5)
        self.assertEqual(sum(peak["hist_counts"]), 10)
        self.assertEqual(peak["hist_counts"][5], 10)      # all samples in [0.5, 0.6)

    def test_ap_cadence_jitter_captures_stall(self):
        cadence = self.metrics["ap_cadence"]
        self.assertEqual(cadence["samples"], 10)
        self.assertAlmostEqual(cadence["median_gap_s"], 1.0, places=3)
        self.assertAlmostEqual(cadence["max_gap_s"], 1.4, places=3)
        self.assertGreater(cadence["p95_jitter_ms"], 200.0)  # the 0.4 s stall dominates p95

    def test_vpf_surface_and_seq_gap(self):
        self.assertEqual(self.metrics["vpf"]["reports"], 5)
        self.assertEqual(self.metrics["vpf"]["seq_gaps"], 1)
        render = self.metrics["render"]
        self.assertEqual(render["surface"], "vpf_frame_us")
        self.assertEqual(render["max_us"], 12000)
        self.assertGreater(render["p95_us"], 5200)

    def test_render_falls_back_to_vp_then_none(self):
        vp_lines = ["[%.3f] [VP] profile=p render_us=%d render_avg=5000 render_max=9000" % (1000.0 + i, 5000 + i) for i in range(6)]
        metrics = BENCH.compute_run_metrics(vp_lines)
        self.assertEqual(metrics["render"]["surface"], "vp_render_us")
        empty = BENCH.compute_run_metrics(["[1.000] hello"])
        self.assertIsNone(empty["render"]["surface"])


class CompareVerdictTest(unittest.TestCase):
    def make_run(
        self,
        *,
        lock=0.90,
        conf=0.62,
        onset=40,
        peak=0.50,
        jitter=20.0,
        render=5200.0,
        crashes=0,
    ):
        return {
            "crash_markers": crashes,
            "ap_cadence": {"p95_jitter_ms": jitter},
            "beat": {"lock_ratio_active": lock, "conf_mean_active": conf},
            "onset": {"onset_sampled_count": onset},
            "peak_scaled": {"mean": peak},
            "render": {"p95_us": render},
        }

    def check_status(self, result, metric):
        for check in result["checks"]:
            if check["metric"] == metric:
                return check["status"]
        raise AssertionError("metric %s missing from result" % metric)

    def test_identical_conditions_pass(self):
        off = [self.make_run() for _ in range(3)]
        on = [self.make_run() for _ in range(3)]
        result = BENCH.compare_runs(off, on)
        self.assertEqual(result["verdict"], "PASS")
        for check in result["checks"]:
            self.assertEqual(check["status"], "PASS")

    def test_lock_ratio_drop_threshold(self):
        off = [self.make_run(lock=0.90)]
        self.assertEqual(self.check_status(BENCH.compare_runs(off, [self.make_run(lock=0.84)]), "beat_lock_ratio_active"), "FAIL")
        self.assertEqual(self.check_status(BENCH.compare_runs(off, [self.make_run(lock=0.86)]), "beat_lock_ratio_active"), "PASS")
        # Improvement never fails.
        self.assertEqual(self.check_status(BENCH.compare_runs(off, [self.make_run(lock=0.99)]), "beat_lock_ratio_active"), "PASS")

    def test_confidence_drop_threshold(self):
        off = [self.make_run(conf=0.62)]
        self.assertEqual(self.check_status(BENCH.compare_runs(off, [self.make_run(conf=0.56)]), "beat_conf_mean_active"), "FAIL")
        self.assertEqual(self.check_status(BENCH.compare_runs(off, [self.make_run(conf=0.58)]), "beat_conf_mean_active"), "PASS")

    def test_onset_count_relative_threshold_is_symmetric(self):
        off = [self.make_run(onset=40)]
        self.assertEqual(self.check_status(BENCH.compare_runs(off, [self.make_run(onset=33)]), "onset_sampled_count"), "FAIL")
        self.assertEqual(self.check_status(BENCH.compare_runs(off, [self.make_run(onset=47)]), "onset_sampled_count"), "FAIL")
        self.assertEqual(self.check_status(BENCH.compare_runs(off, [self.make_run(onset=44)]), "onset_sampled_count"), "PASS")

    def test_peak_scaled_relative_threshold(self):
        off = [self.make_run(peak=0.50)]
        self.assertEqual(self.check_status(BENCH.compare_runs(off, [self.make_run(peak=0.44)]), "peak_scaled_mean"), "FAIL")
        self.assertEqual(self.check_status(BENCH.compare_runs(off, [self.make_run(peak=0.53)]), "peak_scaled_mean"), "PASS")

    def test_jitter_increase_threshold(self):
        off = [self.make_run(jitter=20.0)]
        self.assertEqual(self.check_status(BENCH.compare_runs(off, [self.make_run(jitter=130.0)]), "ap_cadence_p95_jitter_ms"), "FAIL")
        self.assertEqual(self.check_status(BENCH.compare_runs(off, [self.make_run(jitter=110.0)]), "ap_cadence_p95_jitter_ms"), "PASS")

    def test_render_p95_relative_threshold_and_skip(self):
        off = [self.make_run(render=5000.0)]
        self.assertEqual(self.check_status(BENCH.compare_runs(off, [self.make_run(render=5600.0)]), "render_p95_us"), "FAIL")
        self.assertEqual(self.check_status(BENCH.compare_runs(off, [self.make_run(render=5400.0)]), "render_p95_us"), "PASS")
        # Surface unavailable in one condition -> SKIPPED, overall still PASS.
        no_render = self.make_run()
        no_render["render"] = {"p95_us": None}
        result = BENCH.compare_runs([no_render], [no_render])
        self.assertEqual(self.check_status(result, "render_p95_us"), "SKIPPED")
        self.assertEqual(result["verdict"], "PASS")

    def test_any_crash_marker_fails_overall(self):
        off = [self.make_run(crashes=1)]
        on = [self.make_run()]
        result = BENCH.compare_runs(off, on)
        self.assertEqual(self.check_status(result, "crash_markers_total"), "FAIL")
        self.assertEqual(result["verdict"], "FAIL")

    def test_missing_load_bearing_metric_yields_incomplete(self):
        off = [self.make_run()]
        broken = self.make_run()
        broken["beat"] = {}
        result = BENCH.compare_runs(off, [broken])
        self.assertEqual(result["verdict"], "INCOMPLETE")

    def test_verdict_table_renders(self):
        text = BENCH.format_comparison_table(BENCH.compare_runs([self.make_run()], [self.make_run()]))
        self.assertIn("OVERALL VERDICT: PASS", text)
        self.assertIn("not causal proof", text.lower())


class SafetyTest(unittest.TestCase):
    def test_command_plans_contain_only_safe_runtime_commands(self):
        plans = [
            BENCH.setup_commands(22, "l1"),
            BENCH.setup_commands(None, None),
            BENCH.capture_start_commands(True),
            BENCH.capture_start_commands(False),
            BENCH.capture_stop_commands(True),
        ]
        for plan in plans:
            BENCH.assert_command_plan_is_safe(plan)
            for command in plan:
                self.assertTrue(command.startswith(":"))

    def test_forbidden_commands_rejected(self):
        for bad in (":start_noise_cal", ":erase", ":factory_reset", "version"):
            with self.assertRaises(ValueError):
                BENCH.validate_runtime_command(bad)

    def test_tool_never_flashes_or_calibrates(self):
        source = SCRIPT.read_text(encoding="utf-8")
        body = source.split('"""', 2)[2]  # strip module docstring (mentions flash commands as runbook text)
        runbook, _, code = body.partition("PROTOCOL_TEXT")
        # The runbook text (after PROTOCOL_TEXT) may cite flash commands for the
        # OPERATOR; the executable code before it must not invoke any flasher.
        for forbidden in ("pio run", "esptool", "--target upload"):
            self.assertNotIn(forbidden, runbook)
        # The calibration command appears only in the deny-list, never as a send.
        self.assertIn("start_noise_cal", BENCH.FORBIDDEN_COMMAND_TYPES)
        self.assertNotIn(':start_noise_cal', runbook)

    def test_doctrine_note_present_in_compare_output(self):
        result = BENCH.compare_runs([], [])
        self.assertIn("MabuTrace", result["doctrine_note"])


if __name__ == "__main__":
    unittest.main()
