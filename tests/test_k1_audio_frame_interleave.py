"""Host interleave battery for K1AudioFrame Candidate A."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIO = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "audio"
DRIVER = ROOT / "scripts" / "regression-harness" / "k1_audio_frame_host_driver.cpp"
SHIM_C = AUDIO / "k1_audio_frame_host_shim.c"
FRAME_CPP = AUDIO / "k1_audio_frame.cpp"

CASES = (
    "case1_consumer_during_private_build",
    "case2_segment_pause_complete_only",
    "case3_vp_local_survives_40ms_stall",
    "case4_generation_before_payload",
    "case5_two_events_yield_delta_two",
    "case6_epoch_reset_no_phantom",
    "case7_field_stamp_matches_generation",
)

MUTANTS = {
    "MUTANT_EARLY_GENERATION": "case4_generation_before_payload",
    "MUTANT_DIRECT_GLOBAL": "case7_field_stamp_matches_generation",
    "MUTANT_TWO_SLOT_REUSE": "case3_vp_local_survives_40ms_stall",
    "MUTANT_LOST_EVENT": "case5_two_events_yield_delta_two",
}


def _compile(extra_defines: list[str], work: Path) -> Path:
    binary = work / "k1_audio_frame_host"
    cmd = [
        "c++",
        "-std=c++17",
        "-O0",
        "-g",
        "-DK1_AUDIO_FRAME_HOST_TEST=1",
        f"-I{AUDIO}",
        *extra_defines,
        str(DRIVER),
        str(FRAME_CPP),
        str(SHIM_C),
        "-o",
        str(binary),
    ]
    subprocess.run(cmd, check=True, cwd=ROOT, capture_output=True, text=True)
    return binary


def _run(binary: Path, case: str = "all") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(binary), case],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_eight_interleave_cases_pass_on_clean_build():
    with tempfile.TemporaryDirectory(prefix="k1_af_") as td:
        binary = _compile([], Path(td))
        result = _run(binary, "all")
        assert result.returncode == 0, result.stdout + result.stderr
        assert "ALL_PASS" in result.stdout
        for case in CASES:
            assert f"PASS {case}" in result.stdout


def test_fault_battery_rejects_every_unsafe_variant():
    for mutant, expected_case in MUTANTS.items():
        with tempfile.TemporaryDirectory(prefix=f"k1_af_{mutant}_") as td:
            binary = _compile([f"-D{mutant}=1"], Path(td))
            result = _run(binary, "all")
            assert result.returncode != 0, f"{mutant} was not caught\n{result.stdout}"
            blob = result.stdout + result.stderr
            assert expected_case in blob, (
                f"{mutant} was caught, but not by {expected_case}\n{blob}"
            )
