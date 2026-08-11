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
    "SPECTRASYNQ_K1_FIRMWARE/audio/k1_tempo.cpp",       # pre-existing firmware
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
        "SPECTRASYNQ_K1_FIRMWARE/audio/k1_tempo.cpp",
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


# ── in-repo Tab5 Deck16 controller (ported 2026-08-06, gated 2026-08-11) ──────
# Before the classifier gained a `tab5_firmware/*` case, every path under it fell
# through to the default `docs` tier — no test, no build — while
# tests/test_deck_state_v1.py makes 12 assertions by READING those sources. 203
# files were about to land unverified. These pin the repair.
@pytest.mark.parametrize("path", [
    "tab5_firmware/src/deck_ui.cpp",
    "tab5_firmware/src/ble_midi_transport.cpp",   # read by test_deck_state_v1
    "tab5_firmware/src/deck_state.cpp",           # read by test_deck_state_v1
    "tab5_firmware/include/deck_theme.h",
    "tab5_firmware/platformio.ini",               # NOT the root one -> not firmware
    "tab5_firmware/README.md",
])
def test_tab5_firmware_is_pytest_gated_not_docs(path):
    assert classify(path) == "pyharness", (
        f"{path} must not fall through to the docs tier — the host suite reads "
        "these sources, so a Tab5 edit can break pytest with no gate."
    )


def test_tab5_firmware_does_not_outrank_k1_firmware():
    # K1 firmware staged alongside Tab5 must still demand the k1_hardware build.
    assert classify(
        "tab5_firmware/src/deck_ui.cpp",
        "SPECTRASYNQ_K1_FIRMWARE/audio/k1_tempo.cpp",
    ) == "firmware"


def test_tab5_firmware_does_not_shadow_the_legacy_tab5_tier():
    # sb-tab5-wireless-controller is a different project with its own build leg;
    # the in-repo controller must not swallow it.
    assert classify(
        "tab5_firmware/src/deck_ui.cpp",
        "platformio.ini",
        "sb-tab5-wireless-controller/src/main.cpp",
    ) == "firmware+tab5"


def test_classifier_default_is_a_whitelist_miss_not_a_safe_default():
    """DOCUMENTS A KNOWN FRAGILITY — this test asserts the current behaviour so a
    future change is deliberate, and names the trap for whoever reads it.

    classify_tier() starts at `docs` and only upgrades on an explicit match, so
    ANY new top-level tree is ungated until someone adds a case. That is exactly
    how tab5_firmware/ went unverified. If a new subsystem lands, add its case
    here and in scripts/hooks/pre-commit BEFORE the first commit of its sources.
    """
    assert classify("some_new_subsystem/src/main.cpp") == "docs"
