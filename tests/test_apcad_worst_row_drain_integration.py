"""The live APCAD capture runner must drain all declared worst rows before the next command."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = (ROOT / "scripts" / "regression-harness" / "device_ap_cadence_capture.py").read_text(encoding="utf-8")


def test_compact_runner_uses_declared_worst_row_drain():
    assert "from apcad_worst_row_drain import WorstRowDrainError, drain_declared_worst_rows" in RUNNER
    assert RUNNER.count("drain_declared_worst_rows(") >= 2
    assert 'read_until_done(ser, "APCAD_SOAK_DONE", 15.0)' not in RUNNER


def test_vp_perf_cannot_start_before_compact_drain_call():
    regular = RUNNER.index('send_action("apcad_soak_status=1")')
    drain = RUNNER.index("drain_declared_worst_rows(", regular)
    vp = RUNNER.index('send_action("vp_perf=start")', drain)
    assert regular < drain < vp
