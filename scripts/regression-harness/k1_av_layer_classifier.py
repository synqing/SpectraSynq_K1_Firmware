#!/usr/bin/env python3
"""Layer-first classification for the K1 audio-visual regression pack."""

from __future__ import annotations

import re
from typing import Any

# Runtime contract (k1_hardware AP0/VP1)
EXPECTED_SAMPLE_RATE = 12800
EXPECTED_SAMPLES_PER_CHUNK = 96
EXPECTED_TEMPO_DECIM = 3
EXPECTED_AP_CORE = 0
EXPECTED_VP_CORE = 1
EXPECTED_DMA_DESC = 3

NEAR_BPM_TOL = 3
LOCKED_CONF_MIN = 0.60
NEAR127_LO = 124
NEAR127_HI = 130

# Silence isolation lane labels (protocol v4 taped mic campaign, 2026-06-07)
SILENCE_TEMPO_PASS = "PASS_no_false_tempo_lock_under_verified_taped_mic"
SILENCE_EVENT_FAIL_KNOWN = "FAIL_event_layer_false_onsets_on_low_energy_input"
KNOWN_HOST_TEMPO_SEMANTIC_FAILURES = frozenset()


def is_known_host_semantic_failure(entry: dict[str, Any]) -> bool:
    fixture_id = str(entry.get("id", ""))
    if fixture_id in KNOWN_HOST_TEMPO_SEMANTIC_FAILURES:
        return True
    fixture = entry.get("fixture") or {}
    return fixture.get("matrix_tempo_gate") == "known_host_semantic_failure"
OPEN_FINDING_P1_SILENCE_ONSETS = "P1_event_layer_false_onsets_on_low_energy_input"
OPEN_FINDING_P2_LOREEN_WEAK_LOCK = "P2_loreen_127_confidence_weak_lock_scoped"

# Required fixtures whose production AP-stream weak-lock label is superseded by
# declared-rate device NOV replay lock proof (2026-06-07 weak-lock probe).
WEAK_LOCK_NOV_RECONCILED_FIXTURES = frozenset(
    {
        "slow_84_syncopated",
        "click_127",
        "fast_127_fourfloor",
    }
)

RUNTIME_GUARD_RE = re.compile(
    r"RUNTIME_TIMING_GUARD:\s*"
    r"timing_ok=(?P<timing_ok>\d+)\s+"
    r"sample_rate=(?P<sample_rate>\d+)\s+"
    r"samples_per_chunk=(?P<samples_per_chunk>\d+)\s+"
    r"tempo_decim=(?P<tempo_decim>\d+)\s+"
    r"declared_ap_hz=(?P<declared_ap_hz>[\d.]+)\s+"
    r"declared_nov_hz=(?P<declared_nov_hz>[\d.]+)\s+"
    r"(?:response_gain=(?P<response_gain>[\d.]+)\s+)?"
    r"dma_desc=(?P<dma_desc>\d+)\s+"
    r"ap_core=(?P<ap_core>\d+)\s+"
    r"vp_core=(?P<vp_core>\d+)\s+"
    r"core_ok=(?P<core_ok>\d+)\s+"
    r"vp_task_created=(?P<vp_task_created>\d+)"
)


def parse_runtime_timing_guard(line: str) -> dict[str, Any] | None:
    match = RUNTIME_GUARD_RE.search(line.strip())
    if not match:
        return None
    out: dict[str, Any] = {}
    for key, value in match.groupdict().items():
        if value is None:
            continue
        if key in {"declared_ap_hz", "declared_nov_hz", "response_gain"}:
            out[key] = float(value)
        else:
            out[key] = int(value)
    return out


def validate_runtime_guard(guard: dict[str, Any] | None) -> tuple[bool, str, str | None]:
    if not guard:
        return False, "FAIL_runtime_timing_contract", "RUNTIME_TIMING_GUARD line not found"
    if guard.get("timing_ok") != 1:
        return False, "FAIL_runtime_timing_contract", "timing_ok != 1"
    if guard.get("core_ok") != 1:
        return False, "FAIL_core_invariant", "core_ok != 1"
    if guard.get("vp_task_created") != 1:
        return False, "FAIL_core_invariant", "vp_task_created != 1"
    for field, expected in (
        ("sample_rate", EXPECTED_SAMPLE_RATE),
        ("samples_per_chunk", EXPECTED_SAMPLES_PER_CHUNK),
        ("tempo_decim", EXPECTED_TEMPO_DECIM),
        ("ap_core", EXPECTED_AP_CORE),
        ("vp_core", EXPECTED_VP_CORE),
        ("dma_desc", EXPECTED_DMA_DESC),
    ):
        if guard.get(field) != expected:
            return False, "FAIL_runtime_timing_contract", f"{field}={guard.get(field)} expected {expected}"
    return True, "PASS_timing_and_tempo", None


def _near_bpm(bpm: float, expected: int | None) -> bool:
    if expected is None:
        return NEAR127_LO <= int(round(bpm)) <= NEAR127_HI
    return abs(int(round(bpm)) - int(expected)) <= NEAR_BPM_TOL


def summarise_production_ap_stream(
    ap_rows: list[dict[str, Any]],
    *,
    warm_ms: int,
    expected_bpm: int | None,
    locked_conf_min: float = LOCKED_CONF_MIN,
) -> dict[str, Any]:
    if not ap_rows:
        return {
            "ap_row_count": 0,
            "warm_row_count": 0,
            "warm_median_bpm": None,
            "warm_near_target_rows": 0,
            "warm_near_target_denominator": 0,
            "warm_locked_near_rows": 0,
            "warm_high_or_locked_near_rows": 0,
            "beat_tick_count": 0,
            "onset_count": 0,
            "bass_onset_count": 0,
        }

    t0 = ap_rows[0]["t_ms"]
    warm = [row for row in ap_rows if row["t_ms"] - t0 >= warm_ms]
    warm_bpms = [float(row["bpm"]) for row in warm if row.get("bpm") is not None]
    near_target = sum(1 for row in warm if _near_bpm(float(row["bpm"]), expected_bpm))
    locked_near = sum(
        1
        for row in warm
        if int(row.get("lock", 0)) and _near_bpm(float(row["bpm"]), expected_bpm)
    )
    high_or_locked_near = sum(
        1
        for row in warm
        if (int(row.get("lock", 0)) or float(row.get("conf", 0.0)) >= locked_conf_min)
        and _near_bpm(float(row["bpm"]), expected_bpm)
    )
    warm_median = None
    if warm_bpms:
        ordered = sorted(warm_bpms)
        mid = len(ordered) // 2
        warm_median = ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2.0

    return {
        "ap_row_count": len(ap_rows),
        "warm_row_count": len(warm),
        "warm_median_bpm": warm_median,
        "warm_near_target_rows": near_target,
        "warm_near_target_denominator": len(warm),
        "warm_locked_near_rows": locked_near,
        "warm_high_or_locked_near_rows": high_or_locked_near,
        "beat_tick_count": sum(int(row.get("beat", 0)) for row in warm),
        "onset_count": sum(int(row.get("onset", 0)) for row in warm),
        "bass_onset_count": sum(int(row.get("bass", 0)) for row in warm),
    }


def classify_production_tempo(
    summary: dict[str, Any],
    *,
    expected_bpm: int | None,
    fixture_type: str,
    tempo_gate: str | None = None,
) -> tuple[str, str]:
    warm = summary.get("warm_row_count", 0) or 0
    if warm == 0:
        return "INCONCLUSIVE_missing_probe_surface", "no warm AP stream rows"

    if tempo_gate == "product_feel_only":
        lock_frac = float(summary.get("lock_frac", 0.0))
        max_conf = float(summary.get("max_conf", 0.0))
        median = summary.get("warm_median_bpm")
        median_text = f" median={median}" if median is not None else ""
        if lock_frac >= 0.35 or max_conf >= 0.55:
            return (
                "PASS_timing_and_tempo",
                f"exploratory anchor responsive (lock_frac={lock_frac:.2f} max_conf={max_conf:.2f}{median_text})",
            )
        return (
            "INCONCLUSIVE_exploratory_anchor",
            f"exploratory anchor weak lock/conf (lock_frac={lock_frac:.2f} max_conf={max_conf:.2f}{median_text})",
        )

    if fixture_type == "silence_noise":
        max_conf = summary.get("max_conf", 0.0)
        lock_frac = summary.get("lock_frac", 0.0)
        if max_conf >= LOCKED_CONF_MIN or lock_frac >= 0.10:
            return "FAIL_false_positive_silence_noise", "confidence or lock on silence fixture"
        return "PASS_timing_and_tempo", "silence fixture did not false-lock"

    near = summary.get("warm_near_target_rows", 0) or 0
    denom = summary.get("warm_near_target_denominator", 0) or warm
    locked_near = summary.get("warm_locked_near_rows", 0) or 0

    if denom and (near / denom) >= 0.80:
        if locked_near >= 1 or expected_bpm is None:
            return "PASS_timing_and_tempo", "warm near-target ratio >= 0.80"
        return "PASS_timing_but_weak_lock", "near-target but no locked-near rows"

    median = summary.get("warm_median_bpm")
    if median is not None and expected_bpm is not None and _near_bpm(float(median), expected_bpm):
        return "PASS_timing_but_weak_lock", "median near target but row ratio weak"

    return "FAIL_tempo_lane", "warm near-target ratio below threshold"


def classify_probe_cadence(summary: dict[str, Any]) -> tuple[str, str]:
    classification = str(summary.get("classification", ""))
    if classification.startswith("A_"):
        return "PASS_timing_and_tempo", classification
    if classification.startswith("B_"):
        return "FAIL_i2s_or_byte_health", classification
    if classification.startswith("C_"):
        return "FAIL_runtime_timing_contract", classification
    if classification.startswith("D_"):
        return "FAIL_runtime_timing_contract", classification
    if classification.startswith("E_"):
        return "INCONCLUSIVE_missing_probe_surface", classification
    if classification.startswith("F_"):
        return "INCONCLUSIVE_missing_probe_surface", classification
    health_ok = summary.get("health_ok")
    if health_ok == 1:
        return "PASS_timing_and_tempo", "APCAD health_ok"
    return "INCONCLUSIVE_missing_probe_surface", classification or "unknown APCAD classification"


def classify_probe_nov_replay(replay_summary: dict[str, Any]) -> tuple[str, str]:
    classification = str(replay_summary.get("classification", ""))
    if classification == "declared_rate_device_nov_replay_locks_near_target":
        return "PASS_timing_and_tempo", classification
    if classification in {"invalid_no_nov", "invalid_no_warm_replay", "partial_capture_parser_gaps"}:
        return "FAIL_i2s_or_byte_health", classification
    if classification == "host_replay_of_device_nov_reproduces_wrong_lane_frontend_novelty_suspect":
        return "FAIL_tempo_lane", classification
    return "FAIL_tempo_lane", classification or "unclassified nov replay"


def classify_event_layer(
    event_summary: dict[str, Any],
    *,
    fixture_type: str,
) -> tuple[str | None, str]:
    verdict = event_summary.get("product_feel_verdict")
    reason = str(event_summary.get("product_feel_reason", ""))
    if verdict == "FAIL":
        if fixture_type == "silence_noise":
            return SILENCE_EVENT_FAIL_KNOWN, reason
        return "FAIL_beat_phase_or_event_layer", reason
    return None, reason


def classify_silence_fixture_lanes(
    primary_class: str,
    event_class: str | None,
) -> tuple[str, str | None]:
    """Map silence fixture tempo/event lanes to isolation campaign labels."""
    if primary_class == "PASS_timing_and_tempo":
        tempo_lane = SILENCE_TEMPO_PASS
    elif primary_class == "FAIL_false_positive_silence_noise":
        tempo_lane = primary_class
    else:
        tempo_lane = primary_class
    event_lane = SILENCE_EVENT_FAIL_KNOWN if event_class and event_class.startswith("FAIL_") else None
    return tempo_lane, event_lane


def is_matrix_blocking_failure(entry: dict[str, Any]) -> bool:
    """Matrix FAIL only on runtime/tempo-lock regressions on required music fixtures.

    silence_noise live row is open-quiet regression telemetry; canonical false-tempo-lock
    verdict comes from the taped-mic v4 isolation campaign (embedded in matrix metadata).
    Optional fixtures (required=false) are telemetry — never halt the matrix.
    """
    required = bool(entry.get("required", entry.get("fixture", {}).get("required", True)))
    if entry.get("skipped"):
        return entry.get("classification") == "FAIL_fixture_unavailable" and required
    if not required:
        return False
    if entry.get("id") == "silence_noise":
        return False
    if is_known_host_semantic_failure(entry):
        return False
    primary = str(entry.get("primary_classification", entry.get("classification", "")))
    return primary.startswith("FAIL_")


def combine_fixture_classification(
    *,
    runtime_ok: bool,
    runtime_class: str,
    primary_class: str,
    event_class: str | None,
    skipped: bool = False,
    fixture_type: str | None = None,
) -> str:
    if skipped:
        return "SKIPPED_pending_fixture"
    if not runtime_ok and runtime_class.startswith("FAIL_"):
        return runtime_class
    if primary_class.startswith("FAIL_"):
        return primary_class
    if fixture_type == "silence_noise":
        tempo_lane, _ = classify_silence_fixture_lanes(primary_class, event_class)
        return tempo_lane
    if event_class and event_class.startswith("FAIL_"):
        return event_class
    if primary_class == "PASS_timing_but_weak_lock":
        return primary_class
    if primary_class.startswith("INCONCLUSIVE"):
        return primary_class
    return primary_class


def compute_matrix_verdict(
    *,
    runtime_ok: bool,
    runtime_class: str,
    fixture_results: list[dict[str, Any]],
    fixtures_total: int,
) -> tuple[str, str, list[str]]:
    """Return (verdict, next_action, open_findings)."""
    open_findings: list[str] = []
    if not runtime_ok:
        return "FAIL", f"Fix runtime layer first: {runtime_class}", open_findings

    active = [item for item in fixture_results if not item.get("skipped")]
    for item in fixture_results:
        if item.get("id") == "silence_noise" and not item.get("skipped"):
            live_primary = str(item.get("primary_classification", ""))
            event_class = str(item.get("event_classification") or "")
            if event_class.startswith("FAIL_"):
                open_findings.append(OPEN_FINDING_P1_SILENCE_ONSETS)
            if live_primary.startswith("FAIL_"):
                open_findings.append("P1_open_quiet_silence_live_tempo_anomaly")

    blocking = [item for item in fixture_results if is_matrix_blocking_failure(item)]
    if blocking:
        failed = blocking[0]
        return (
            "FAIL",
            f"Investigate {failed['id']}: {failed.get('primary_classification') or failed.get('classification')} — "
            f"{failed.get('primary_reason') or failed.get('skip_reason', '')}",
            open_findings,
        )

    unreconciled_weak_lock = [
        item
        for item in active
        if item.get("classification") == "PASS_timing_but_weak_lock"
        and item.get("id") not in WEAK_LOCK_NOV_RECONCILED_FIXTURES
    ]
    if unreconciled_weak_lock:
        verdict = "PARTIAL"
        ids = ", ".join(str(item.get("id", "?")) for item in unreconciled_weak_lock)
        next_action = (
            f"Review unreconciled weak-lock fixtures ({ids}); "
            "slow_84_syncopated/click_127/fast_127_fourfloor closed by NOV replay proof"
        )
        if any(item.get("id") == "loreen_127" for item in unreconciled_weak_lock):
            open_findings.append(OPEN_FINDING_P2_LOREEN_WEAK_LOCK)
    elif any(item.get("classification") == "SKIPPED_pending_fixture" for item in fixture_results):
        verdict = "PARTIAL"
        next_action = "Production tempo/cadence green; add Captain dense/clipped track when available"
    elif len(active) < fixtures_total:
        verdict = "PARTIAL"
        next_action = "Rerun skipped fixtures when paths become available"
    else:
        verdict = "PASS"
        next_action = "Proceed to Scene Policy v2 A/B product validation"

    if open_findings and verdict == "PASS":
        verdict = "PASS_WITH_OPEN_FINDINGS"

    return verdict, next_action, open_findings
