#!/usr/bin/env python3
"""Beat/onset product-feel metrics from production [AP] stream rows."""

from __future__ import annotations

import statistics
from typing import Any

EVENT_STORM_THRESHOLD_EVENTS_PER_MIN = 240.0
SILENCE_MAX_CONF = 0.60
SILENCE_MAX_LOCK_FRAC = 0.10


def _beat_spacings_ms(ap_rows: list[dict[str, Any]]) -> list[float]:
    beat_times = [float(row["t_ms"]) for row in ap_rows if int(row.get("beat", 0))]
    if len(beat_times) < 2:
        return []
    return [beat_times[i] - beat_times[i - 1] for i in range(1, len(beat_times))]


def summarise_event_quality(
    ap_rows: list[dict[str, Any]],
    *,
    warm_ms: int,
    fixture_type: str,
    duration_ms: int | None = None,
) -> dict[str, Any]:
    if not ap_rows:
        return {
            "beat_tick_count": 0,
            "beat_tick_spacing_ms_p50": None,
            "beat_tick_spacing_ms_p95": None,
            "onset_count": 0,
            "bass_onset_count": 0,
            "onsets_per_minute": 0.0,
            "silence_false_onset_count": 0,
            "dense_track_onset_saturation": None,
            "max_conf": 0.0,
            "lock_frac": 0.0,
            "product_feel_verdict": "WARN",
            "product_feel_reason": "no AP rows",
        }

    t0 = ap_rows[0]["t_ms"]
    warm = [row for row in ap_rows if row["t_ms"] - t0 >= warm_ms]
    spacings = _beat_spacings_ms(warm)
    onset_count = sum(int(row.get("onset", 0)) for row in warm)
    bass_count = sum(int(row.get("bass", 0)) for row in warm)
    beat_count = sum(int(row.get("beat", 0)) for row in warm)
    conf_values = [float(row.get("conf", 0.0)) for row in warm]
    lock_values = [int(row.get("lock", 0)) for row in warm]

    span_ms = (warm[-1]["t_ms"] - warm[0]["t_ms"]) if len(warm) > 1 else (duration_ms or 0)
    minutes = max(span_ms / 60000.0, 1.0 / 60.0)
    onsets_per_min = (onset_count + bass_count) / minutes
    onset_saturation = (onset_count / len(warm)) if warm else None
    max_conf = max(conf_values) if conf_values else 0.0
    lock_frac = (sum(lock_values) / len(lock_values)) if lock_values else 0.0

    spacing_p50 = statistics.median(spacings) if spacings else None
    spacing_p95 = sorted(spacings)[int(max(0, round(0.95 * (len(spacings) - 1))))] if spacings else None

    verdict, reason = _evaluate_product_feel(
        fixture_type=fixture_type,
        beat_count=beat_count,
        onsets_per_min=onsets_per_min,
        onset_saturation=onset_saturation,
        max_conf=max_conf,
        lock_frac=lock_frac,
        warm_rows=len(warm),
    )

    return {
        "beat_tick_count": beat_count,
        "beat_tick_spacing_ms_p50": spacing_p50,
        "beat_tick_spacing_ms_p95": spacing_p95,
        "onset_count": onset_count,
        "bass_onset_count": bass_count,
        "onsets_per_minute": onsets_per_min,
        "silence_false_onset_count": (onset_count + bass_count) if fixture_type == "silence_noise" else 0,
        "dense_track_onset_saturation": onset_saturation,
        "max_conf": max_conf,
        "lock_frac": lock_frac,
        "product_feel_verdict": verdict,
        "product_feel_reason": reason,
    }


def _evaluate_product_feel(
    *,
    fixture_type: str,
    beat_count: int,
    onsets_per_min: float,
    onset_saturation: float | None,
    max_conf: float,
    lock_frac: float,
    warm_rows: int,
) -> tuple[str, str]:
    if fixture_type == "silence_noise":
        if max_conf >= SILENCE_MAX_CONF or lock_frac >= SILENCE_MAX_LOCK_FRAC:
            return "FAIL", f"silence fixture max_conf={max_conf:.2f} lock_frac={lock_frac:.2f}"
        if onsets_per_min > 1.0:
            return "FAIL", f"silence fixture had onsets_per_min={onsets_per_min:.1f}"
        return "PASS", "silence fixture stayed quiet"

    if fixture_type == "synthetic_control" and beat_count == 0:
        return "WARN", "127 click control had zero beat ticks in warm window"

    if onsets_per_min >= EVENT_STORM_THRESHOLD_EVENTS_PER_MIN:
        return "WARN", f"onset storm onsets_per_min={onsets_per_min:.1f}"

    if warm_rows >= 5 and beat_count == 0 and onsets_per_min < 0.5:
        return "WARN", "sparse event stream for music fixture"

    if onset_saturation is not None and onset_saturation > 0.85:
        return "WARN", f"onset saturation={onset_saturation:.2f} may be too dense for visual control"

    return "PASS", "event stream plausible for visual control"
