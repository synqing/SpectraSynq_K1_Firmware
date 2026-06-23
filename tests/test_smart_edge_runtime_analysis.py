import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ANALYSER_PATH = ROOT / "scripts" / "regression-harness" / "analyse_smart_edge_runtime_capture.py"


def load_analyser():
    spec = importlib.util.spec_from_file_location("analyse_smart_edge_runtime_capture", ANALYSER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SmartEdgeRuntimeAnalysisTest(unittest.TestCase):
    def test_vpabb_white_flood_signature_fails_visual_safety_gate(self):
        analyse = load_analyser()
        groups = {
            "edge_complementary_strength_1/secondary": {
                "energy": {"mean": 60000.0},
                "nonzero_led_pct": {"mean": 100.0},
                "sat_avg": {"mean": 2.0},
                "white_bias_avg": {"mean": 252.0},
            }
        }

        failures = analyse.evaluate_visual_safety(groups)

        self.assertIn("white_flood", {failure["metric"] for failure in failures})
        self.assertEqual(failures[0]["group"], "edge_complementary_strength_1/secondary")

    def test_normal_saturated_output_does_not_fail_visual_safety_gate(self):
        analyse = load_analyser()
        groups = {
            "baseline_features_off/primary": {
                "energy": {"mean": 5100.0},
                "nonzero_led_pct": {"mean": 87.0},
                "sat_avg": {"mean": 182.0},
                "white_bias_avg": {"mean": 39.0},
            }
        }

        failures = analyse.evaluate_visual_safety(groups)

        self.assertEqual(failures, [])

    def test_vpabc_context_rows_are_summarised(self):
        analyse = load_analyser()
        text = "\n".join(
            (
                "#LEG smart_context",
                "VPABC,ver=1,primary_mode=8,primary_config_mode=3,secondary_mode=7,smart_enabled=1,hooks_enabled=1,manual_owner_active=0,edge_enabled=1,edge_mode=2,edge_strength_milli=350,edge_effective_strength_milli=420",
                "VPABB,ver=1,seq=1,mode=8,channel=primary,frame=1,t_ms=1,dt_ms=0.00,leds=1,bytes=3,hash=0x1,energy=255,r_sum=255,g_sum=0,b_sum=0,nonzero_led_pct=100.00,com=0.00,sat_avg=255.00,white_bias_avg=0.00,max_luma=85,render_us=1,quant_us=1,show_us=1,frame_us=1,over=0,dropped=0",
                "",
            )
        )
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
            handle.write(text)
            log = Path(handle.name)

        summary = analyse.summarise_vpabb(log)

        self.assertEqual(summary["vpab_context_tail"][0]["primary_mode"], "8")
        self.assertEqual(summary["vpab_context_tail"][0]["primary_config_mode"], "3")
        self.assertEqual(summary["vpabb_groups"]["smart_context/primary"]["modes"], ["8"])

    def test_smart_switch_path_is_reported_from_mode_counts(self):
        analyse = load_analyser()
        groups = {
            "smart_assist_low_floor_edge_on/primary": {
                "modes": ["3", "8"],
                "mode_counts": {"3": 12, "8": 12},
            }
        }

        result = analyse.evaluate_smart_switch_path(groups)

        self.assertTrue(result["checked"])
        self.assertTrue(result["switched"])
        self.assertEqual(result["switched_modes"], ["8"])
        self.assertEqual(result["mode_counts"], {"3": 12, "8": 12})


if __name__ == "__main__":
    unittest.main()
