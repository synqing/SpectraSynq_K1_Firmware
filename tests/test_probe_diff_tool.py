"""The probe-differ must stay able to detect a no-op probe (HF-69).

A DSR-clock "probe" once re-declared a flag its base env already defined, built an
identical binary, and its null result was written up with a plausible mechanism. This
tool exists to make that one second of work. Its own fault battery must keep passing —
including the cases expected to be RED, because a battery of all-green expectations
cannot detect a harness that tests nothing (HF-80).
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "scripts" / "tools" / "probe_diff.py"


def test_tool_self_test_passes_including_red_cases():
    r = subprocess.run([sys.executable, str(TOOL), "--self-test"],
                       capture_output=True, text=True, cwd=str(ROOT))
    assert r.returncode == 0, f"probe_diff self-test failed:\n{r.stdout}{r.stderr}"
    # The battery must actually contain deliberately-red cases, not just green ones.
    assert r.stdout.count("want=1") >= 3, (
        "self-test lost its RED cases — a suite of all-green expectations cannot "
        "detect a harness that is testing nothing"
    )


def test_tool_detects_a_real_noop_on_the_live_ini():
    """K1_MIC_IM69D_DSR_16S_V1 is defined in the base im69d env, so asking for it as a
    probe delta must FAIL — this is the exact historical HF-69 shape."""
    r = subprocess.run(
        [sys.executable, str(TOOL), "k1_bench_im69d_hpf",
         "--expect", "K1_MIC_IM69D_DSR_16S_V1"],
        capture_output=True, text=True, cwd=str(ROOT))
    assert r.returncode == 1, (
        "probe_diff did not flag an already-defined flag as a no-op probe:\n" + r.stdout)


def test_tool_accepts_a_genuine_probe():
    r = subprocess.run(
        [sys.executable, str(TOOL), "k1_bench_im69d_hpf",
         "--expect", "K1_AP_SUBSONIC_HPF_V1"],
        capture_output=True, text=True, cwd=str(ROOT))
    assert r.returncode == 0, (
        "probe_diff rejected a genuine single-variable probe:\n" + r.stdout)
