"""Locked eight-plus-two inventory and flash-on-arm-change policy for the B489 E2E A/B."""

from __future__ import annotations

import importlib.util
from pathlib import Path

RUNNER = (
    Path(__file__).resolve().parents[1]
    / "docs/forensics/runtime-evidence/20260817T-g2g3-e2e-ab-b489/run_e2e_ab.py"
)


def _load():
    spec = importlib.util.spec_from_file_location("run_e2e_ab", RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_should_flash_only_on_arm_change():
    m = _load()
    assert m.should_flash(None, "A") is True
    assert m.should_flash("A", "B") is True
    assert m.should_flash("B", "B") is False
    assert m.should_flash("B", "A") is True
    assert m.should_flash("A", "A") is False


def test_primary_inventory_is_exactly_eight_abba():
    m = _load()
    assert [leg[0] for leg in m.PRIMARY_LEGS] == [
        "Q_A1",
        "Q_B1",
        "Q_B2",
        "Q_A2",
        "M_A1",
        "M_B1",
        "M_B2",
        "M_A2",
    ]
    assert [leg[1] for leg in m.PRIMARY_LEGS] == ["A", "B", "B", "A", "A", "B", "B", "A"]
    assert [leg[2] for leg in m.PRIMARY_LEGS] == [
        "no_playback",
        "no_playback",
        "no_playback",
        "no_playback",
        "music",
        "music",
        "music",
        "music",
    ]


def test_contingent_inventory_is_c_only_not_twelve():
    m = _load()
    assert [leg[0] for leg in m.CONTINGENT_LEGS] == ["C_Q", "C_M"]
    assert len(m.PRIMARY_LEGS) + len(m.CONTINGENT_LEGS) == 10
    assert "C_B1" not in {leg[0] for leg in m.PRIMARY_LEGS + m.CONTINGENT_LEGS}


def test_primary_flash_sequence_skips_b2():
    m = _load()
    previous = None
    flashed = []
    for leg_id, arm, _fixture in m.PRIMARY_LEGS:
        will = m.should_flash(previous, arm)
        flashed.append((leg_id, arm, will))
        previous = arm
    assert flashed == [
        ("Q_A1", "A", True),
        ("Q_B1", "B", True),
        ("Q_B2", "B", False),
        ("Q_A2", "A", True),
        ("M_A1", "A", False),
        ("M_B1", "B", True),
        ("M_B2", "B", False),
        ("M_A2", "A", True),
    ]


def test_q_a2_to_m_a1_does_not_reflash():
    m = _load()
    assert m.should_flash("A", "A") is False
