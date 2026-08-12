"""The identity guard must FAIL on the exact line that fooled us on 2026-08-11."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_MOD = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "regression-harness"
    / "k1_device_identity_guard.py"
)
_spec = importlib.util.spec_from_file_location("k1_device_identity_guard", _MOD)
guard = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(guard)


# The literal line the device emitted while a foreign session owned it.
FOREIGN = "BUILD: version=40103 git=622997b epoch=1786444207 env=k1_custom_silicon_closure"
# The build we believed we were measuring.
MINE = "BUILD: version=40103 git=1249286 epoch=1786444727 env=k1_unit2_im69d_right"


def test_parses_the_real_build_line():
    ident = guard.parse_build_line(FOREIGN)
    assert ident == {
        "version": "40103",
        "git": "622997b",
        "epoch": "1786444207",
        "env": "k1_custom_silicon_closure",
    }


def test_parses_when_embedded_in_streaming_telemetry():
    noisy = "[AP] SSL=53 DC=220 max_raw=86 silence=1\nsbr{{\n" + FOREIGN + "\n}}\n[k1_sc_rssi] rssi_dbm=-54"
    assert guard.parse_build_line(noisy)["git"] == "622997b"


def test_returns_none_when_absent():
    assert guard.parse_build_line("[AP] SSL=53 DC=220 silence=1") is None


def _fake(monkeypatch, line: str):
    monkeypatch.setattr(guard, "read_identity", lambda *a, **k: guard.parse_build_line(line))


def test_foreign_build_is_rejected_on_git(monkeypatch):
    """The regression this file exists for: a foreign build must not pass."""
    _fake(monkeypatch, FOREIGN)
    with pytest.raises(guard.IdentityMismatch) as exc:
        guard.assert_identity("/dev/null", expect_git="1249286")
    assert "622997b" in str(exc.value)


def test_foreign_build_is_rejected_on_env(monkeypatch):
    _fake(monkeypatch, FOREIGN)
    with pytest.raises(guard.IdentityMismatch):
        guard.assert_identity("/dev/null", expect_env="k1_unit2_im69d_right")


def test_matching_build_passes(monkeypatch):
    _fake(monkeypatch, MINE)
    ident = guard.assert_identity(
        "/dev/null", expect_git="1249286", expect_env="k1_unit2_im69d_right"
    )
    assert ident["env"] == "k1_unit2_im69d_right"


def test_epoch_mismatch_is_caught(monkeypatch):
    """Same git can be rebuilt; epoch pins the actual binary."""
    _fake(monkeypatch, MINE)
    with pytest.raises(guard.IdentityMismatch):
        guard.assert_identity("/dev/null", expect_epoch="1786444207")


def test_guard_is_not_a_tautology(monkeypatch):
    """A guard that passes everything is documentation, not a guard."""
    _fake(monkeypatch, FOREIGN)
    with pytest.raises(guard.IdentityMismatch):
        guard.assert_identity("/dev/null", expect_git="deadbee", expect_env="anything")
