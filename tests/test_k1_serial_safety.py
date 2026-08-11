"""Guard the K1 serial safety classification against drift and regression.

Origin: 2026-08-11, bench K1v2 (chip B489A500). ``:led_count`` sent as a read;
it is a setter, ``atol("") == 0`` clamped to 1, saved and rebooted. These tests
pin the classification that would have refused that send, and fail if either
dispatch .def is edited without regenerating
``scripts/regression-harness/k1_serial_safety.py``.
"""

import importlib.util
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / "SPECTRASYNQ_K1_FIRMWARE"
TYPED_DEF = FW / "serial" / "serial_typed_cmd_table.def"
BARE_DEF = FW / "serial" / "serial_cmd_table.def"
MODULE_PATH = ROOT / "scripts" / "regression-harness" / "k1_serial_safety.py"

_ROW = re.compile(r'^\s*SERIAL_(?:TYPED_)?CMD\(\s*"([^"]+)"\s*,(.*)$')


def _load_module():
    spec = importlib.util.spec_from_file_location("k1_serial_safety", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SAFETY = _load_module()


def _parse_def(path: Path, typed: bool) -> dict:
    """Fresh parse of a dispatch .def -> {command_name: set(CMD_* flags)}.

    Independent of the generator that produced the module literals: this is the
    oracle the drift test compares against. Rows inside ``#if`` blocks are
    included unconditionally, matching the module's documented stance.
    """
    rows: dict = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = _ROW.match(line)
        if not match:
            continue
        args = [a.strip() for a in match.group(2).rstrip().rstrip(")").split(",")]
        # typed: handler, safety_class, flags...
        # bare:  hotkey, handler, safety_class, flags, input_surface
        flag_args = args[2:] if typed else args[3:-1]
        flags = set()
        for arg in flag_args:
            flags.update(re.findall(r"CMD_[A-Z_]+", arg))
        rows.setdefault(match.group(1), set()).update(flags)
    return rows


def _fresh_flags() -> dict:
    merged: dict = {}
    for path, typed in ((TYPED_DEF, True), (BARE_DEF, False)):
        for name, flags in _parse_def(path, typed).items():
            merged.setdefault(name, set()).update(flags)
    return merged


def _blob_sha(path: Path) -> str:
    return subprocess.run(
        ["git", "hash-object", str(path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


# ---------------------------------------------------------------------------
# The incident: setters must never be classified safe.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "name", ["led_count", "sample_rate", "note_offset", "led_type"]
)
def test_reboot_setters_are_not_safe_readonly(name):
    assert name not in SAFETY.SAFE_READONLY_COMMANDS
    assert name in SAFETY.DISRUPTIVE_COMMANDS
    assert name in SAFETY.PERSISTING_COMMANDS


def test_assert_read_only_rejects_led_count_naming_the_flags():
    with pytest.raises(RuntimeError) as excinfo:
        SAFETY.assert_read_only("led_count")
    message = str(excinfo.value)
    assert "CMD_DISRUPTIVE" in message
    assert "CMD_PERSISTS" in message


def test_assert_read_only_accepts_the_dump_witness():
    SAFETY.assert_read_only("dump")  # must not raise
    SAFETY.assert_read_only("chip_id")


def test_assert_read_only_rejects_unknown_tokens():
    with pytest.raises(RuntimeError):
        SAFETY.assert_read_only("no_such_command")


# ---------------------------------------------------------------------------
# The mechanism: a valueless typed name is still a setter.
# ---------------------------------------------------------------------------

def test_valueless_typed_setter_is_refused():
    """':led_count' with no '=' is the exact line that poisoned the device."""
    with pytest.raises(RuntimeError) as excinfo:
        SAFETY.assert_safe_to_send(":led_count")
    assert "SETTER" in str(excinfo.value)


def test_bare_bytes_without_colon_are_refused():
    with pytest.raises(RuntimeError) as excinfo:
        SAFETY.assert_safe_to_send("dump")
    assert "hotkey" in str(excinfo.value)


def test_row1_bare_read_commands_are_allowed():
    SAFETY.assert_safe_to_send(":dump\n")
    SAFETY.assert_safe_to_send(":chip_id")


def test_explicit_write_still_refused_by_classification():
    with pytest.raises(RuntimeError):
        SAFETY.assert_safe_to_send(":led_count=160")


# ---------------------------------------------------------------------------
# Calibration and destructive rows must never leak into the safe set.
# ---------------------------------------------------------------------------

def test_calibration_and_destructive_rows_are_not_safe():
    """These carry neither CMD_DISRUPTIVE nor CMD_PERSISTS, so the naive
    two-flag predicate would call them safe. The module removes them."""
    for name in ("start_noise_cal", "clear_noise_cal", "factory_reset",
                 "restore_defaults"):
        assert name not in SAFETY.SAFE_READONLY_COMMANDS
        with pytest.raises(RuntimeError):
            SAFETY.assert_read_only(name)
    # Proof that the naive predicate really would have admitted the first two.
    assert "start_noise_cal" in SAFETY.FLAG_CLEAN_COMMANDS
    assert "clear_noise_cal" in SAFETY.FLAG_CLEAN_COMMANDS


# ---------------------------------------------------------------------------
# Drift guard: the literals must match a fresh parse of the current .def files.
# ---------------------------------------------------------------------------

def test_literal_sets_match_a_fresh_parse_of_both_defs():
    flags = _fresh_flags()
    assert set(flags) == set(SAFETY.ALL_COMMANDS)

    expected_disruptive = {n for n, f in flags.items() if "CMD_DISRUPTIVE" in f}
    expected_persists = {n for n, f in flags.items() if "CMD_PERSISTS" in f}
    expected_irrev = {n for n, f in flags.items() if "CMD_IRREVERSIBLE" in f}
    expected_silence = {n for n, f in flags.items() if "CMD_NEEDS_SILENCE" in f}
    expected_clean = {
        n for n, f in flags.items()
        if not ({"CMD_DISRUPTIVE", "CMD_PERSISTS"} & f)
    }

    assert expected_disruptive == set(SAFETY.DISRUPTIVE_COMMANDS)
    assert expected_persists == set(SAFETY.PERSISTING_COMMANDS)
    assert expected_irrev == set(SAFETY.IRREVERSIBLE_COMMANDS)
    assert expected_silence == set(SAFETY.SILENCE_GATED_COMMANDS)
    assert expected_clean == set(SAFETY.FLAG_CLEAN_COMMANDS)
    assert (
        expected_clean - expected_irrev - expected_silence
        == set(SAFETY.SAFE_READONLY_COMMANDS)
    )


def test_row1_bare_table_membership_matches_fresh_parse():
    assert set(_parse_def(BARE_DEF, typed=False)) == set(SAFETY.ROW1_BARE_COMMANDS)


def test_recorded_def_blob_shas_are_current():
    """Fails if a .def was edited without regenerating k1_serial_safety.py.

    Fix: re-derive the literals, then update TYPED_DEF_BLOB_SHA /
    BARE_DEF_BLOB_SHA with `git hash-object <path>`.
    """
    assert _blob_sha(TYPED_DEF) == SAFETY.TYPED_DEF_BLOB_SHA
    assert _blob_sha(BARE_DEF) == SAFETY.BARE_DEF_BLOB_SHA
