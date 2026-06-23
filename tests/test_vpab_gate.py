import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "regression-harness" / "vpab_gate.py"
FIXTURES = ROOT / "tests" / "fixtures"


def load_module():
    spec = importlib.util.spec_from_file_location("vpab_gate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class VPABGateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.vpab = load_module()

    def test_parse_vpab_line_converts_numbers(self):
        record = self.vpab.parse_vpab_line(
            "VPAB,ver=1,mode=7,channel=primary,scenario=self_shadow,frame=42,"
            "mae8=0.42,p95_abs8=1,max_abs8=6,changed_led_pct=1.8,changed_channel_pct=0.9,"
            "energy_a=812,energy_b=806,energy_delta_pct=-0.7,"
            "com_a=79.2,com_b=79.1,com_delta_leds=0.1,com_slope_delta_pct=2.3",
            line_no=9,
        )
        self.assertEqual(record["tag"], "VPAB")
        self.assertEqual(record["line"], 9)
        self.assertEqual(record["fields"]["mode"], 7)
        self.assertEqual(record["fields"]["channel"], "primary")
        self.assertAlmostEqual(record["fields"]["mae8"], 0.42)

    def test_pass_fixture_evaluates_cleanly(self):
        result = self.vpab.evaluate_text((FIXTURES / "vpab_pass.log").read_text())
        self.assertTrue(result["valid"], result)
        self.assertTrue(result["passed"], result)
        self.assertEqual(result["result"], "PASS")
        self.assertEqual(result["counts"]["vpab_records"], 2)
        self.assertEqual(result["counts"]["passed_records"], 2)
        self.assertFalse(result["failures"])

    def test_deferred_dump_fixture_evaluates_cleanly(self):
        result = self.vpab.evaluate_text((FIXTURES / "vpab_deferred_dump.log").read_text())
        self.assertFalse(result["valid"], result)
        self.assertFalse(result["passed"], result)
        issue_text = "\n".join(issue["message"] for issue in result["issues"])
        self.assertIn("self-shadow or absent memory metrics are instrumentation smoke", issue_text)

    def test_deferred_dump_fixture_can_be_allowed_as_instrumentation_smoke(self):
        result = self.vpab.evaluate_text(
            (FIXTURES / "vpab_deferred_dump.log").read_text(),
            allow_self_shadow_smoke=True,
        )
        self.assertTrue(result["valid"], result)
        self.assertTrue(result["passed"], result)
        self.assertEqual(result["counts"]["vpab_records"], 2)
        self.assertEqual(result["counts"]["passed_records"], 2)
        self.assertFalse(result["failures"])

    def test_fail_fixture_reports_level1_threshold_breaches(self):
        result = self.vpab.evaluate_text((FIXTURES / "vpab_fail.log").read_text())
        self.assertTrue(result["valid"], result)
        self.assertFalse(result["passed"], result)
        metrics = {failure["metric"] for failure in result["failures"]}
        for metric in {
            "mae8",
            "p95_abs8",
            "max_abs8",
            "changed_led_pct",
            "com_delta_leds",
            "trail_delta_frames",
            "tail_integral_delta_pct",
            "frame_us",
            "over",
            "dropped",
        }:
            self.assertIn(metric, metrics)
        render_metrics = {failure["metric"] for failure in result["render_budget"]["failures"]}
        self.assertIn("render_us", render_metrics)

    def test_missing_mandatory_fields_invalidates_record(self):
        result = self.vpab.evaluate_text(
            "VPAB,ver=1,mode=7,channel=primary,scenario=self_shadow,frame=1,"
            "mae8=0.1,p95_abs8=1,max_abs8=2,changed_led_pct=0.2,changed_channel_pct=0.1,"
            "energy_a=10,com_a=79,com_b=79,com_delta_leds=0,com_slope_delta_pct=0\n"
        )
        self.assertFalse(result["valid"], result)
        self.assertFalse(result["passed"], result)
        issue_text = "\n".join(issue["message"] for issue in result["issues"])
        self.assertIn("missing mandatory field energy_b", issue_text)
        self.assertIn("missing mandatory field energy_delta_pct", issue_text)

    def test_cli_returns_json_and_pass_exit_code(self):
        completed = subprocess.run(
            [sys.executable, str(SCRIPT), str(FIXTURES / "vpab_pass.log")],
            check=False,
            text=True,
            capture_output=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn('"result": "PASS"', completed.stdout)

    def test_strict_memory_rejects_self_shadow_placeholder(self):
        result = self.vpab.evaluate_text(
            "VPAB,ver=1,mode=7,channel=primary,scenario=self_shadow,shadow=self,"
            "memory_metrics=absent,frame=1,mae8=0,p95_abs8=0,max_abs8=0,"
            "changed_led_pct=0,changed_channel_pct=0,energy_a=10,energy_b=10,"
            "energy_delta_pct=0,com_a=79,com_b=79,com_delta_leds=0,"
            "com_slope_delta_pct=0\n",
            strict_memory=True,
        )
        self.assertFalse(result["valid"], result)
        issue_text = "\n".join(issue["message"] for issue in result["issues"])
        self.assertIn("strict memory gate rejects absent/placeholder memory metrics", issue_text)

    def test_diag_summary_drop_or_overflow_fails_gate(self):
        result = self.vpab.evaluate_text(
            "sbr{{\n"
            "VPAB_RECORDS: captured=2 dropped=1 high_water=2 overflowed=1\n"
            "}}\n"
            "VPAB,ver=1,mode=7,channel=primary,scenario=trail,frame=42,"
            "mae8=0,p95_abs8=0,max_abs8=0,changed_led_pct=0,changed_channel_pct=0,"
            "energy_a=10,energy_b=10,energy_delta_pct=0,"
            "com_a=79,com_b=79,com_delta_leds=0,com_slope_delta_pct=0,"
            "trail_half_life_delta_frames=0,tail_integral_delta_pct=0,"
            "render_us=900,frame_us=8100,over=0,dropped=0\n"
        )
        self.assertTrue(result["valid"], result)
        self.assertFalse(result["passed"], result)
        metrics = {failure["metric"] for failure in result["failures"]}
        self.assertIn("diag_dropped", metrics)
        self.assertIn("diag_overflowed", metrics)

    def test_strict_memory_preserves_runtime_failures(self):
        result = self.vpab.evaluate_text(
            "VPAB,ver=1,mode=7,channel=primary,scenario=self_shadow,shadow=self,"
            "memory_metrics=absent,frame=1,mae8=0,p95_abs8=0,max_abs8=0,"
            "changed_led_pct=0,changed_channel_pct=0,energy_a=10,energy_b=10,"
            "energy_delta_pct=0,com_a=79,com_b=79,com_delta_leds=0,"
            "com_slope_delta_pct=0,render_us=2100,frame_us=8400,over=1,dropped=1\n",
            strict_memory=True,
        )
        self.assertFalse(result["valid"], result)
        metrics = {failure["metric"] for failure in result["failures"]}
        self.assertIn("frame_us", metrics)
        self.assertIn("over", metrics)
        self.assertIn("dropped", metrics)
        render_metrics = {failure["metric"] for failure in result["render_budget"]["failures"]}
        self.assertIn("render_us", render_metrics)

    def test_render_us_is_reported_separately_from_final_byte_gate_by_default(self):
        result = self.vpab.evaluate_text(
            "VPAB,ver=1,mode=7,channel=primary,scenario=trail,frame=42,"
            "mae8=0,p95_abs8=0,max_abs8=0,changed_led_pct=0,changed_channel_pct=0,"
            "energy_a=10,energy_b=10,energy_delta_pct=0,"
            "com_a=79,com_b=79,com_delta_leds=0,com_slope_delta_pct=0,"
            "trail_half_life_delta_frames=0,tail_integral_delta_pct=0,"
            "render_us=2400,frame_us=8100,over=0,dropped=0\n"
        )
        self.assertTrue(result["valid"], result)
        self.assertTrue(result["passed"], result)
        self.assertTrue(result["visual_gate"]["passed"], result)
        self.assertFalse(result["render_budget"]["passed"], result)
        self.assertEqual(result["render_budget"]["status"], "WARN")
        metrics = {failure["metric"] for failure in result["render_budget"]["failures"]}
        self.assertIn("render_us", metrics)

    def test_strict_render_budget_makes_render_us_fail_the_overall_gate(self):
        result = self.vpab.evaluate_text(
            "VPAB,ver=1,mode=7,channel=primary,scenario=trail,frame=42,"
            "mae8=0,p95_abs8=0,max_abs8=0,changed_led_pct=0,changed_channel_pct=0,"
            "energy_a=10,energy_b=10,energy_delta_pct=0,"
            "com_a=79,com_b=79,com_delta_leds=0,com_slope_delta_pct=0,"
            "trail_half_life_delta_frames=0,tail_integral_delta_pct=0,"
            "render_us=2400,frame_us=8100,over=0,dropped=0\n",
            strict_render_budget=True,
        )
        self.assertTrue(result["valid"], result)
        self.assertFalse(result["passed"], result)
        self.assertFalse(result["render_budget"]["passed"], result)
        metrics = {failure["metric"] for failure in result["failures"]}
        self.assertIn("render_us", metrics)


if __name__ == "__main__":
    unittest.main()
