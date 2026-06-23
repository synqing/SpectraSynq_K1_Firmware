#!/usr/bin/env python3
"""Fixture manifest loading for the K1 audio-visual regression pack."""

from __future__ import annotations

import json
import re
import subprocess
import wave
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "k1_av_regression_fixtures.template.json"

DEFAULT_PLAYBACK = {
    "normalize": True,
    "target_peak_db": -6.0,
    "target_mean_db": -14.0,
    "max_gain_db": 18.0,
    "min_gain_db": -24.0,
    "sparse_mean_boost_cap_db": 15.0,
    "limiter_when_gain_above_db": 3.0,
    "limiter_ceiling": 0.92,
}


def load_manifest(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    root_token = data.get("harmonix_corpus_root", "")
    for fixture in data.get("fixtures", []):
        raw_path = str(fixture.get("path", ""))
        raw_path = raw_path.replace("{harmonix_corpus_root}", root_token)
        if raw_path == "__generated_silence__" or raw_path.startswith("__generated_control_"):
            fixture["resolved_path"] = raw_path
        elif raw_path.startswith("/"):
            fixture["resolved_path"] = raw_path
        else:
            fixture["resolved_path"] = str((ROOT / raw_path).expanduser())
    return data


def wav_duration_ms(path: Path) -> int | None:
    try:
        with wave.open(str(path), "rb") as handle:
            rate = handle.getframerate()
            if rate <= 0:
                return None
            return int(1000 * handle.getnframes() / rate)
    except (wave.Error, OSError):
        return None


def apply_fixture_timing(entry: dict[str, Any]) -> dict[str, Any]:
    """Clamp capture/warm windows to the resolved audio file length."""
    path = str(entry.get("resolved_path", ""))
    if path in {"", "__generated_silence__"}:
        return entry
    wav_ms = wav_duration_ms(Path(path).expanduser())
    if wav_ms is None or wav_ms <= 0:
        return entry
    duration_ms = int(entry.get("duration_ms", wav_ms))
    warm_ms = int(entry.get("warm_ms", 5000))
    clamped_duration = min(duration_ms, wav_ms)
    # Keep >=5s lead-in and >=10s warm music where possible.
    max_warm = max(0, clamped_duration - 5000)
    min_warm = min(5000, max(0, clamped_duration - 10000))
    clamped_warm = min(warm_ms, max_warm)
    if clamped_warm < min_warm and max_warm >= min_warm:
        clamped_warm = min_warm
    entry = dict(entry)
    entry["duration_ms"] = clamped_duration
    entry["warm_ms"] = clamped_warm
    entry["source_wav_duration_ms"] = wav_ms
    if clamped_duration != duration_ms or clamped_warm != warm_ms:
        entry["timing_clamped"] = True
    return entry


def resolve_playback_window(fixture: dict[str, Any]) -> tuple[int, int]:
    """Return (start_ms, duration_ms) for host playback. Missing start_ms defaults to 0."""
    start_ms = int(fixture.get("start_ms", 0))
    duration_ms = int(fixture["duration_ms"])
    return start_ms, duration_ms


def playback_settings(manifest: dict[str, Any]) -> dict[str, float | bool]:
    merged = dict(DEFAULT_PLAYBACK)
    merged.update(manifest.get("playback") or {})
    return merged


def measure_playback_loudness(
    track_path: Path | str,
    *,
    start_ms: int = 0,
    duration_ms: int | None = None,
) -> dict[str, float | None]:
    """Measure mean/max dBFS for the exact playback window via ffmpeg volumedetect."""
    start_sec = start_ms / 1000.0
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-nostats",
        "-ss",
        str(start_sec),
    ]
    if duration_ms is not None:
        cmd.extend(["-t", str(duration_ms / 1000.0)])
    cmd.extend(["-i", str(track_path), "-af", "volumedetect", "-f", "null", "-"])
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    mean_db: float | None = None
    max_db: float | None = None
    for line in proc.stderr.splitlines():
        if "mean_volume:" in line:
            match = re.search(r"mean_volume:\s*([-\d.]+)", line)
            if match:
                mean_db = float(match.group(1))
        if "max_volume:" in line:
            match = re.search(r"max_volume:\s*([-\d.]+)", line)
            if match:
                max_db = float(match.group(1))
    return {"mean_volume_db": mean_db, "max_volume_db": max_db}


def resolve_playback_gain_db(
    fixture: dict[str, Any],
    manifest: dict[str, Any],
    *,
    loudness: dict[str, float | None] | None = None,
) -> tuple[float, dict[str, Any]]:
    """Return playback gain in dB plus provenance metadata for logging."""
    if fixture.get("playback_gain_db") is not None:
        gain = float(fixture["playback_gain_db"])
        return gain, {"source": "manifest_playback_gain_db", "gain_db": gain}

    settings = playback_settings(manifest)
    if not settings.get("normalize", True):
        return 0.0, {"source": "normalize_disabled", "gain_db": 0.0}

    if loudness is None:
        start_ms, duration_ms = resolve_playback_window(fixture)
        loudness = measure_playback_loudness(
            fixture["resolved_path"],
            start_ms=start_ms,
            duration_ms=duration_ms,
        )

    target_peak = float(settings["target_peak_db"])
    target_mean = float(settings["target_mean_db"])
    max_gain = float(settings["max_gain_db"])
    min_gain = float(settings["min_gain_db"])
    mean_db = loudness.get("mean_volume_db")
    peak_db = loudness.get("max_volume_db")

    if peak_db is None:
        return 0.0, {"source": "loudness_unavailable", "gain_db": 0.0, **loudness}

    peak_gain = target_peak - peak_db
    gain = peak_gain
    fixture_type = str(fixture.get("fixture_type", ""))
    if fixture_type == "synthetic_control" and mean_db is not None:
        sparse_cap = float(settings["sparse_mean_boost_cap_db"])
        mean_gain = min(target_mean - mean_db, sparse_cap)
        gain = max(peak_gain, mean_gain)

    gain = max(min_gain, min(max_gain, gain))
    return gain, {
        "source": "auto_normalize",
        "gain_db": gain,
        "peak_gain_db": peak_gain,
        "target_peak_db": target_peak,
        "target_mean_db": target_mean,
        **loudness,
    }


def build_ffplay_audio_filter(
    gain_db: float,
    *,
    settings: dict[str, float | bool] | None = None,
) -> str | None:
    if abs(gain_db) < 0.05:
        return None
    settings = settings or DEFAULT_PLAYBACK
    limiter_threshold = float(settings.get("limiter_when_gain_above_db", 3.0))
    ceiling = float(settings.get("limiter_ceiling", 0.92))
    if gain_db > limiter_threshold:
        return f"volume={gain_db:.3f}dB,alimiter=limit={ceiling:.3f}"
    return f"volume={gain_db:.3f}dB"


def build_ffplay_command(
    track_path: Path | str,
    *,
    start_ms: int = 0,
    duration_ms: int | None = None,
    gain_db: float = 0.0,
    playback_settings: dict[str, float | bool] | None = None,
) -> list[str]:
    """Build ffplay argv matching Smart Auto offset playback (-ss/-t, nodisp, autoexit)."""
    start_sec = start_ms / 1000.0
    cmd = [
        "ffplay",
        "-nodisp",
        "-autoexit",
        "-loglevel",
        "error",
        "-ss",
        str(start_sec),
    ]
    if duration_ms is not None:
        duration_sec = duration_ms / 1000.0
        cmd.extend(["-t", str(duration_sec)])
    audio_filter = build_ffplay_audio_filter(gain_db, settings=playback_settings)
    if audio_filter:
        cmd.extend(["-af", audio_filter])
    cmd.extend(["-i", str(track_path)])
    return cmd


def fixture_availability(fixture: dict[str, Any]) -> tuple[bool, str]:
    status = str(fixture.get("status", "active"))
    path = str(fixture.get("resolved_path", ""))
    if status == "blocked":
        return False, str(fixture.get("block_reason", "fixture blocked"))
    if status == "candidate":
        return False, str(
            fixture.get("block_reason", "candidate anchor requires Captain spot-check")
        )
    if status == "pending" or path == "PENDING_CAPTAIN_TRACK_PATH":
        return False, "pending captain track path"
    if path == "__generated_silence__" or path.startswith("__generated_control_"):
        return True, "generated"
    if not Path(path).expanduser().exists():
        return False, f"missing path: {path}"
    return True, "ok"


def resolve_fixtures(manifest: dict[str, Any], args: Any) -> list[dict[str, Any]]:
    wanted = {item.strip() for item in args.fixture_ids.split(",")} if args.fixture_ids else None
    fixtures: list[dict[str, Any]] = []
    for fixture in manifest.get("fixtures", []):
        if wanted and fixture["id"] not in wanted:
            continue
        mode = fixture.get("run_mode", "production_smoke")
        if args.production_smoke and not args.probe_replay and mode == "probe_nov_replay":
            continue
        if args.probe_replay and not args.production_smoke and mode in {"production_smoke", "silence_only"}:
            continue
        entry = dict(fixture)
        if args.duration_ms:
            entry["duration_ms"] = args.duration_ms
        if args.warm_ms:
            entry["warm_ms"] = args.warm_ms
        entry = apply_fixture_timing(entry)
        fixtures.append(entry)
    return fixtures


def order_fixtures(fixtures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Run silence before music so the quiet fixture is not polluted by prior lock state."""
    mode_rank = {"silence_only": 0, "production_smoke": 1, "probe_nov_replay": 2}

    def sort_key(fixture: dict[str, Any]) -> tuple[int, str]:
        return (mode_rank.get(str(fixture.get("run_mode", "production_smoke")), 9), str(fixture["id"]))

    return sorted(fixtures, key=sort_key)
