"""T' ffplay 8 must not use the removed -stream_loop flag."""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_probe():
    path = (
        Path(__file__).resolve().parents[1]
        / "docs"
        / "forensics"
        / "runtime-evidence"
        / "20260816T-g0r-abba-b489"
        / "device_ap_cadence_capture_probe.py"
    )
    spec = importlib.util.spec_from_file_location("tprime_apcad_probe", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_tprime_ffplay_uses_loop0_not_stream_loop():
    probe = _load_probe()

    class Args:
        player = "ffplay"
        start_ms = 0
        duration_ms = 15000
        playback_gain_db = 0.0

    command = probe.build_playback_command(Args(), Path("fixture.wav"), duration_ms=0)
    assert "-stream_loop" not in command
    assert command[command.index("-loop") + 1] == "0"
    assert "-t" not in command
