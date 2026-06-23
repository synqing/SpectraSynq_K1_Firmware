import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "regression-harness" / "smart_visuals_gate.py"


SAMPLE_LOG = """
#LEG baseline_features_off
SMART_ASSIST: off
SMART_SWITCHING: off
SMART_APPLIED_MODE: 3
EDGE_ENABLED: off
EDGE_MODE: off
EDGE_STRENGTH: 0.000
VPAB_RECORDS: captured=2 dropped=0 high_water=2 overflowed=0
VPABB,ver=1,mode=3,channel=primary,frame=1,hash=0x1,energy=100,com=79.5,r_sum=30,g_sum=20,b_sum=10,nonzero_led_pct=50.0,over=0,dropped=0
VPABB,ver=1,mode=7,channel=secondary,frame=1,hash=0x2,energy=80,com=79.5,r_sum=40,g_sum=30,b_sum=20,nonzero_led_pct=35.0,over=0,dropped=0
#LEG edge_complementary_strength_1
EDGE_ENABLED: on
EDGE_MODE: complementary
EDGE_STRENGTH: 1.000
VPAB_RECORDS: captured=2 dropped=0 high_water=2 overflowed=0
VPABB,ver=1,mode=3,channel=primary,frame=1,hash=0x3,energy=102,com=79.6,r_sum=31,g_sum=20,b_sum=10,nonzero_led_pct=50.0,over=0,dropped=0
VPABB,ver=1,mode=7,channel=secondary,frame=1,hash=0x4,energy=210,com=79.4,r_sum=200,g_sum=180,b_sum=170,nonzero_led_pct=70.0,over=0,dropped=0
""".strip()


class SmartVisualsGateTest(unittest.TestCase):
    def test_module_parses_status_and_groups(self):
        sys.path.insert(0, str(SCRIPT.parent))
        import smart_visuals_gate

        summary = smart_visuals_gate.summarise_text(SAMPLE_LOG)
        self.assertEqual(summary["records_total"], 4)
        self.assertIn("baseline_features_off/secondary", summary["vpabb_groups"])
        self.assertIn("edge_complementary_strength_1/secondary", summary["vpabb_groups"])
        self.assertEqual(summary["smart_status_tail"][-1]["SMART_APPLIED_MODE"], 3)
        self.assertEqual(summary["edge_status_tail"][-1]["EDGE_STRENGTH"], 1.0)

    def test_edge_materiality_report_uses_secondary_delta(self):
        sys.path.insert(0, str(SCRIPT.parent))
        import smart_visuals_gate

        summary = smart_visuals_gate.summarise_text(SAMPLE_LOG)
        materiality = summary["edge_materiality"]
        self.assertTrue(materiality["baseline_found"])
        self.assertTrue(materiality["edge_found"])
        self.assertGreater(materiality["secondary_energy_delta_pct"], 100.0)
        self.assertGreater(materiality["secondary_rgb_sum_delta_pct"], 100.0)
        self.assertLess(materiality["primary_rgb_sum_delta_pct"], 10.0)

    def test_strict_mode_reports_overflow_and_drops(self):
        sys.path.insert(0, str(SCRIPT.parent))
        import smart_visuals_gate

        bad_log = SAMPLE_LOG + "\nVPAB_RECORDS: captured=1 dropped=1 high_water=1 overflowed=1\n"
        summary = smart_visuals_gate.summarise_text(bad_log)
        issues = smart_visuals_gate.gate_summary(summary, strict=True)
        messages = " ".join(issue["message"] for issue in issues)
        self.assertIn("dropped", messages)
        self.assertIn("overflowed", messages)

    def test_cli_writes_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "capture.log"
            out_path = Path(tmpdir) / "summary.json"
            log_path.write_text(SAMPLE_LOG, encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(log_path), "--out", str(out_path)],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["records_total"], 4)


if __name__ == "__main__":
    unittest.main()
