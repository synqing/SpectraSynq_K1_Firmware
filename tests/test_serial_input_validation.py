"""Serial setters validate before they commit (Modernes C++ lane, 2026-11-10).

Drives the production parse_command()/setter code through the existing golden
serial oracle (scripts/regression-harness/golden/oracle_serial_replay.py), which
compiles the real serial_*.cpp files on the host. Before the fix, on e2e83e53:
`secondary_photons=nan` and `saturation=nan` stored NaN, `led_count=500` stored
500 and rebooted into boot-sized buffers, `note_offset=24` was saved (notes[] read
out of bounds at boot), `silence_dwell=-5` became 4294967291 ms, non-numeric text
became 0, and a 40-byte line without '=' echoed uninitialised stack bytes.
Evidence: _scratch/modernes-cpp_20261110/oracle_probe_before.txt.
"""
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "regression-harness" / "golden"))
import oracle_serial_replay as oracle  # noqa: E402

FW = ROOT / "SPECTRASYNQ_K1_FIRMWARE"

REJECTED = [
    "secondary_photons=nan", "secondary_chroma=abc", "secondary_mood=inf",
    "secondary_saturation=", "secondary_prism_count=nan",
    "sweet_spot_min=abc", "sweet_spot_max=nan", "chromagram_range=nan",
    "max_current_ma=nan", "incandescent_filter=nan", "bulb_opacity=x",
    "saturation=nan",
    "led_count=500", "led_count=0", "led_count=abc",
    "silence_enter=abc", "silence_exit=nan", "silence_rms_enter=x",
    "silence_rms_exit=nan", "silence_dwell=-5", "silence_dwell=99999999999",
    # Independent review (2026-11-10): garbage became 0 (and was saved, some
    # with a reboot), or NaN reached the core-0 sample path.
    "response_gain=nan", "note_offset=abc", "note_offset", "square_iter=abc",
    "prism_count=abc", "sample_rate=abc", "samples_per_chunk=abc",
]

ACCEPTED = {
    "secondary_photons=0.25": {"SECONDARY_PHOTONS": 0.25},
    "secondary_prism_count=12": {"SECONDARY_PRISM_COUNT": 10.0},
    "saturation=2": {"SATURATION": 1.0},
    "sweet_spot_min=1e20": {"SWEET_SPOT_MIN_LEVEL": 4294967040.0},
    "chromagram_range=200": {"CHROMAGRAM_RANGE": 80.0},
    "note_offset=24": {"NOTE_OFFSET": 16.0},
    "note_offset=12": {"NOTE_OFFSET": 12.0},
    # Out-of-range numbers keep clamping as before; only non-numbers are rejected.
    # Order matters (replay is sequential): set 4 first so the clamp to 0 shows.
    "square_iter=4": {"SQUARE_ITER": 4.0},
    "square_iter=-5": {"SQUARE_ITER": 0.0},
}

LONG_NO_EQUALS = "A" * 40


@pytest.fixture(scope="module")
def replay(tmp_path_factory, monkeypatch_module=None):
    corpus = REJECTED + list(ACCEPTED) + ["led_count=160", "silence_dwell=4000", LONG_NO_EQUALS]
    saved = oracle.CORPUS
    oracle.CORPUS = corpus
    try:
        out = oracle.capture()  # raises on compile failure or non-zero exit
    finally:
        oracle.CORPUS = saved
    rows = [json.loads(line) for line in out.splitlines() if line.strip()]
    assert [r["cmd"] for r in rows] == corpus
    return {r["cmd"]: r for r in rows}


@pytest.mark.parametrize("cmd", REJECTED)
def test_invalid_value_is_rejected_without_state_change(replay, cmd):
    row = replay[cmd]
    assert row["bad_command"] is True, row
    assert row["config_delta"] == {}, row
    assert not row["save_config"] and not row["save_config_delayed"] and not row["reboot"], row


@pytest.mark.parametrize("cmd,delta", sorted(ACCEPTED.items()))
def test_valid_value_still_commits_with_existing_range(replay, cmd, delta):
    row = replay[cmd]
    assert row["bad_command"] is False, row
    assert row["config_delta"] == delta, row


def test_led_count_equal_to_compiled_count_keeps_save_and_reboot(replay):
    row = replay["led_count=160"]
    assert row["bad_command"] is False
    assert row["save_config"] and row["reboot"]


def test_silence_dwell_accepts_plain_milliseconds(replay):
    row = replay["silence_dwell=4000"]
    assert row["bad_command"] is False
    assert "SILENCE_DWELL_MS: 4000" in row["emitted"]


def test_long_line_without_equals_is_terminated(replay):
    # json.loads already proved the echo is valid UTF-8 (the old over-read
    # emitted raw stack bytes). The echoed type is exactly 31 bytes.
    row = replay[LONG_NO_EQUALS]
    assert row["bad_command"] is True
    assert "Bad command: " + "A" * 31 + "=" in row["emitted"]


def test_noise_cal_reset_runs_on_the_audio_loop_not_the_render_task():
    led = (FW / "visual" / "led_utilities.h").read_text(encoding="utf-8")
    fade = led[led.index("inline void run_transition_fade"):]
    fade = fade[:fade.index("\n}\n")]
    assert "start_noise_cal()" not in fade
    assert "request_noise_cal_start();" in fade
    ino = (FW / "SPECTRASYNQ_K1_FIRMWARE.ino").read_text(encoding="utf-8")
    loop = ino[ino.index("void loop() {"):]
    assert loop.index("service_noise_cal_start_request();") < loop.index("acquire_sample_chunk(t_now);")
    cal = (FW / "calibration" / "noise_cal.h").read_text(encoding="utf-8")
    start = cal[cal.index("void start_noise_cal() {"):cal.index("void request_noise_cal_start()")]
    assert "ui_mask" not in re.sub(r"//.*", "", start)  # render-owned; cleared on core 1


def test_finite_math_guard_present():
    const = (FW / "system" / "constants.h").read_text(encoding="utf-8")
    assert "#if defined(__FINITE_MATH_ONLY__) && __FINITE_MATH_ONLY__" in const
