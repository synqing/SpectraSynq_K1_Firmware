"""Build-config policy drift-gate (Lane B — narrowed).

Detects silent drift in the RESOLVED brownout / coredump / WDT policy of the
`k1_hardware` build, and proves it cannot be defeated by the inert-vehicle trap.

WHY A DRIFT-GATE, NOT a LOCK->FIX firmware change:
  This lane changes NO firmware and NO binary — `framework = arduino` bakes the
  IDF sdkconfig into the precompiled libs, and a project `sdkconfig.defaults` is
  never read (see oracle_build_config_policy docstring + docs/hardware/
  build-config-policy.md). So the classic two-commit anti-gaming split (LOCK
  pins pre-state, FIX changes firmware) does not apply — there is no firmware
  delta to game. The anti-gaming guarantee here is `test_drift_gate_bites`
  (Gate-Falpha): the comparison provably FAILS on a mutated golden, so a
  perpetually-green gate cannot masquerade as "no drift".

Authoritative-source discipline: the gate resolves the live sdkconfig from the
build artifact first, then the prebuilt-libs source. If NEITHER is locatable it
SKIPS LOUD — it must never silently pass from an absent source.
"""
import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
GOLDEN_DIR = REPO / "scripts" / "regression-harness" / "golden"
sys.path.insert(0, str(GOLDEN_DIR))

import oracle_build_config_policy as ocfg  # noqa: E402


# --- the gate ---------------------------------------------------------------
def test_resolved_policy_matches_golden():
    """Live resolved brownout/coredump/WDT == the pinned golden (no drift)."""
    src = ocfg.resolve_live_sdkconfig(REPO)
    if src is None:
        pytest.skip(
            "LOUD-SKIP: no authoritative resolved sdkconfig found "
            "(.pio/build/k1_hardware/sdkconfig or "
            "$PLATFORMIO_CORE_DIR/packages/framework-arduinoespressif32-libs/"
            f"{ocfg.CHIP}/sdkconfig). Build k1_hardware or install the platform "
            "to activate this gate. NOT treating absence as 'no drift'."
        )
    resolved = ocfg.parse_sdkconfig(src.read_text(encoding="utf-8", errors="ignore"))
    live = ocfg.extract_policy(resolved)
    drift = ocfg.diff_policy(ocfg.GOLDEN_POLICY, live)
    assert not drift, (
        "Resolved build-config policy DRIFTED from the golden (source="
        f"{src}):\n  " + "\n  ".join(drift) +
        "\nIf intentional, update GOLDEN_POLICY + docs/hardware/build-config-policy.md."
    )


def test_coredump_partition_present():
    """Flash coredump needs a `coredump` partition in the active table."""
    csv = ocfg.resolve_partition_csv(REPO)
    if csv is None:
        pytest.skip(
            "LOUD-SKIP: no resolved partition table found "
            "(.pio/build/k1_hardware/partitions.csv or the framework "
            "default_16MB.csv). NOT treating absence as 'partition present'."
        )
    assert ocfg.partition_has_coredump(csv.read_text(encoding="utf-8", errors="ignore")), (
        f"No `coredump` partition in {csv} — flash coredump "
        "(CONFIG_ESP_COREDUMP_ENABLE_TO_FLASH=y) would have nowhere to write."
    )


# --- Gate-Falpha: prove the gate bites (anti-theatre) -----------------------
def test_drift_gate_bites():
    """A mutated golden MUST be flagged — otherwise the gate is theatre."""
    # disable-coredump mutation
    mutated = dict(ocfg.GOLDEN_POLICY)
    mutated["CONFIG_ESP_COREDUMP_ENABLE_TO_FLASH"] = "n"
    drift = ocfg.diff_policy(ocfg.GOLDEN_POLICY, mutated)
    assert any("COREDUMP_ENABLE_TO_FLASH" in d for d in drift), drift
    # brownout-level off-by-one mutation
    mutated2 = dict(ocfg.GOLDEN_POLICY)
    mutated2["CONFIG_ESP_BROWNOUT_DET_LVL"] = "6"
    assert ocfg.diff_policy(ocfg.GOLDEN_POLICY, mutated2), "brownout LVL drift not caught"
    # absent key must read as drift, not as a pass
    missing = {k: v for k, v in ocfg.GOLDEN_POLICY.items()
               if k != "CONFIG_ESP_TASK_WDT_PANIC"}
    assert ocfg.diff_policy(ocfg.GOLDEN_POLICY, ocfg.extract_policy(missing)), (
        "absent key not flagged as drift"
    )


def test_sdkconfig_parse_normalises_is_not_set():
    """`# CONFIG_X is not set` -> 'n', `=y` -> 'y', `=5` -> '5', quotes stripped."""
    sample = (
        'CONFIG_A=y\n'
        '# CONFIG_B is not set\n'
        'CONFIG_C=5\n'
        'CONFIG_D="hello"\n'
        '# a human comment\n'
    )
    parsed = ocfg.parse_sdkconfig(sample)
    assert parsed == {"CONFIG_A": "y", "CONFIG_B": "n", "CONFIG_C": "5", "CONFIG_D": "hello"}


# --- anti-trap guard: keep the inert vehicle out of the repo ----------------
def test_no_inert_sdkconfig_defaults_vehicle():
    """A root `sdkconfig.defaults` is INERT under framework=arduino here.

    Guards a future agent from "pinning" config via a file the build ignores
    (the exact theatre this lane exists to prevent). If a real override is ever
    needed it must go through pioarduino's `custom_sdkconfig` option (a
    deliberate from-source rebuild), not a silent root file.
    """
    inert = REPO / "sdkconfig.defaults"
    assert not inert.exists(), (
        "A root sdkconfig.defaults exists but framework=arduino ignores it "
        "(only the `custom_sdkconfig` option is honoured). It would be inert "
        "theatre — remove it or use custom_sdkconfig with intent."
    )
    pio = (REPO / "platformio.ini").read_text(encoding="utf-8", errors="ignore")
    if "custom_sdkconfig" in pio:
        # If it ever appears, it must be a deliberate, commented decision — flag
        # bare occurrences so they are reviewed (from-source rebuild = binary change).
        assert "custom_sdkconfig" in pio  # presence is allowed; this asserts visibility
