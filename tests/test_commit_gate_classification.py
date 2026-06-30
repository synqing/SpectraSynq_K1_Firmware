"""Commit-gate change-class classification (scripts/hooks/pre-commit --classify).

Pins that build-critical PlatformIO **pre-scripts** are classified as the
`firmware` tier (-> pytest **and** `pio run -e k1_hardware`), closing the gap
that let the N4a upload-guard refactor (2026-06-27) ship a production-build
break with pytest-only local verification.

Tests the pure classifier seam (`pre-commit --classify <paths...>`) only — it
does NOT run pio or a build, and needs no git state.
"""
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "scripts" / "hooks" / "pre-commit"


def classify(*paths: str) -> str:
    r = subprocess.run(
        ["bash", str(HOOK), "--classify", *paths],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


def test_hook_present_and_executable_classifier():
    assert HOOK.is_file()
    assert classify("README.md") == "docs"  # seam works


@pytest.mark.parametrize("path", [
    "scripts/platformio/k1_upload_guard.py",            # the N4a culprit
    "scripts/platformio/k1_src_includes.py",            # the other build pre-script
    "scripts/platformio/k1_device_identities.json",     # consumed by the guard
    "platformio.ini",                                   # pre-existing
    "SPECTRASYNQ_K1_FIRMWARE/audio/sb_tempo.cpp",       # pre-existing firmware
    "SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino",
])
def test_build_critical_paths_require_firmware_tier(path):
    # firmware tier => the hook runs pytest AND `pio run -e k1_hardware`
    assert classify(path) == "firmware", path


@pytest.mark.parametrize("path", [
    "docs/anything.md",
    "README.md",
    "docs/hardware/device-build-registry.md",
    "docs/git/commit-gate.md",
])
def test_docs_do_not_require_a_build(path):
    assert classify(path) == "docs", path


def test_host_harness_stays_pytest_only():
    assert classify("tests/test_x.py") == "pyharness"
    assert classify("scripts/regression-harness/foo.py") == "pyharness"


def test_prescript_alongside_firmware_is_firmware():
    assert classify(
        "scripts/platformio/k1_upload_guard.py",
        "SPECTRASYNQ_K1_FIRMWARE/audio/sb_tempo.cpp",
    ) == "firmware"


def test_the_n4a_stage_set_would_now_be_build_gated():
    # the exact N4a stage set (guard + manifest + identity test) -> firmware tier,
    # so `pio run -e k1_hardware` would have been required at commit time.
    assert classify(
        "scripts/platformio/k1_upload_guard.py",
        "scripts/platformio/k1_device_identities.json",
        "tests/test_k1_upload_guard_identity_static.py",
    ) == "firmware"


def test_unrelated_scripts_are_not_build_gated():
    # only scripts/platformio pre-scripts are build-critical; other scripts/ are not
    assert classify("scripts/hooks/install.sh") == "docs"
