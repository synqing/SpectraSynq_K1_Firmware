import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GATE_PATH = ROOT / "scripts" / "regression-harness" / "sb_trace_l1_gate.py"


def load_gate():
    spec = importlib.util.spec_from_file_location("sb_trace_l1_gate", GATE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_trace(path, hook_durations, bus_durations=(10, 12, 14), primary=(700,), secondary=(800,)):
    events = []
    for value in bus_durations:
        events.append({"name": "vp_bus_read", "ph": "X", "dur": value})
    for value in hook_durations:
        events.append({"name": "vp_visual_hooks_tick", "ph": "X", "dur": value})
    for value in primary:
        events.append({"name": "vp_primary_render_us", "ph": "C", "args": {"value": value}})
    for value in secondary:
        events.append({"name": "vp_secondary_render_us", "ph": "C", "args": {"value": value}})
    path.write_text(json.dumps({"traceEvents": events}), encoding="utf-8")


class SBTraceL1GateTest(unittest.TestCase):
    def test_baseline_comparison_allows_non_regressing_hook_tail(self):
        gate = load_gate()
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            baseline_path = tmp / "baseline.json"
            candidate_path = tmp / "candidate.json"
            write_trace(baseline_path, [30, 40, 200])
            write_trace(candidate_path, [31, 41, 190])

            candidate = gate.analyse(candidate_path)
            baseline = gate.analyse(baseline_path)
            candidate["issues"] = [
                issue for issue in candidate["issues"]
                if issue != "vp_visual_hooks_tick p99 exceeds 50us"
            ]
            candidate["pass"] = not candidate["issues"]

            summary = gate.compare_against_baseline(candidate, baseline, 10.0)

        self.assertTrue(summary["pass"])
        self.assertLessEqual(summary["comparisons"]["vp_visual_hooks_tick_p99_widening_pct"], 10.0)

    def test_baseline_comparison_fails_regressing_hook_tail(self):
        gate = load_gate()
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            baseline_path = tmp / "baseline.json"
            candidate_path = tmp / "candidate.json"
            write_trace(baseline_path, [30, 40, 100])
            write_trace(candidate_path, [31, 41, 130])

            candidate = gate.analyse(candidate_path)
            baseline = gate.analyse(baseline_path)
            candidate["issues"] = [
                issue for issue in candidate["issues"]
                if issue != "vp_visual_hooks_tick p99 exceeds 50us"
            ]
            candidate["pass"] = not candidate["issues"]

            summary = gate.compare_against_baseline(candidate, baseline, 10.0)

        self.assertFalse(summary["pass"])
        self.assertIn("vp_visual_hooks_tick p99 widened", summary["issues"][-1])


if __name__ == "__main__":
    unittest.main()
