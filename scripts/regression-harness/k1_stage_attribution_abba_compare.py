#!/usr/bin/env python3
"""Fail-closed Gate-2 stage-attribution A-B-B-A comparator.

The comparator consumes a declarative series specification.  Each of its eight
legs references one 120-second compact-soak summary and the immediately
following five-second buffered summary.  It validates provenance and the frozen
run contract before applying the pre-registered conservative interval rules.

This is deliberately a file-only tool: it never opens a serial port, flashes a
device, starts playback, or mutates firmware.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import re
import subprocess
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = 1
CAPTURE_SCHEMA_VERSION = 2
PAIR_SCHEMA_VERSION = "k1-stage-attribution-pair/v1"
MIN_ENV = "k1_bench_scheduling_stage_min_probe"
FULL_ENV = "k1_bench_scheduling_stage_full_probe"
DETAIL_DEFINE = "K1_AP_STAGE_ATTRIBUTION_DETAIL"
EXPECTED_DEVICE = {
    "chip_id": "B489A500",
    "usb_serial": "B4:3A:45:A5:89:B4",
}
EXPECTED_MUSIC_PATH = (
    "/Users/spectrasynq/Music/Music/Media.localized/Music/"
    "Ahmed Spins_Stevo Atambire/Anchor Point EP/Anchor Point.mp3"
)
EXPECTED_MUSIC_SHA256 = (
    "02925982cf3900d1925fa0338db8e26432c265f7ca18ee93a06818dd4079a938"
)
EXPECTED_ORDER = (
    ("A1_no_playback", "MIN", 1, "no_playback"),
    ("A1_music", "MIN", 1, "music"),
    ("B1_music", "FULL", 1, "music"),
    ("B1_no_playback", "FULL", 1, "no_playback"),
    ("B2_no_playback", "FULL", 2, "no_playback"),
    ("B2_music", "FULL", 2, "music"),
    ("A2_music", "MIN", 2, "music"),
    ("A2_no_playback", "MIN", 2, "no_playback"),
)
METRICS = (
    "active_ap_work",
    "newest_sample_to_ap_publish",
    "ap_read_return_interval",
)
ZERO_COMPACT_COUNTS = (
    "frame_gap_count",
    "timestamp_regression_count",
    "i2s_not_ok_count",
    "bytes_mismatch_count",
    "core_bad_count",
    "compact_worst_mode_mismatch_count",
)
ZERO_BUFFERED_COUNTS = (
    "frame_gap_count",
    "capture_sequence_gap_count",
    "timestamp_regression_count",
    "timestamp_order_failure_count",
    "i2s_not_ok_count",
    "bytes_mismatch_count",
    "stage_timing_missing_count",
    "stage_duration_missing_count",
    "stage_timestamp_order_failure_count",
    "stage_tail_total_mismatch_count",
    "stage_duration_consistency_failure_count",
    "stage_nonempty_failure_count",
    "stage_coverage_failure_count",
    "invalid_stage_attribution_mode_count",
    "stage_header_mode_mismatch_count",
    "control_stage_missing_count",
    "control_stage_consistency_failure_count",
)
FORBIDDEN_ACTIVITY_FIELDS = (
    "calibration",
    "persistence_write",
    "radio",
    "benchmark",
    "debug_mode",
    "command_burst",
    "mode_change",
    "scene_change",
    "crossfade",
    "vp_perf_running_during_capture",
)
DETAIL_FLAGS = {
    "MIN": f"-D{DETAIL_DEFINE}=0",
    "FULL": f"-D{DETAIL_DEFINE}=1",
}
ROOT = Path(__file__).resolve().parents[2]
DEPLOYED_CONTRACT_PATH = (
    ROOT
    / "docs"
    / "forensics"
    / "2026-08-15-freertos-scheduling-audit"
    / "gate0"
    / "contract.json"
)
EXCLUSIVE_FRAME_CLASSES = ("neither", "tempo_only", "onset_only", "tempo_and_onset")
FRAME_CLASS_MINIMUM_N_FOR_P95 = 20
FRAME_CLASS_MINIMUM_N_FOR_P99 = 100
FRAME_CLASS_PERCENTILE_METHOD = "linear"
# Frozen AP rate tolerance around contract-derived expected Hz (preserves 132.0–134.5 at 133.⅓).
SERVICE_RATE_TOLERANCE_LOW_HZ = 133.33333333333334 - 132.0
SERVICE_RATE_TOLERANCE_HIGH_HZ = 134.5 - 133.33333333333334
# Frozen throughput / gap limits for perturbation verdict (pre-registered; do not retune after R8).
PERTURBATION_THROUGHPUT_DELTA_MAX_HZ = 2.0
PERTURBATION_FRAME_GAP_DELTA_MAX = 0
PERTURBATION_I2S_DELTA_MAX = 0
AUDIT_RECEIPT_PATH = (
    "docs/forensics/2026-08-15-freertos-scheduling-audit/evidence/"
    "gate2-stage-attribution-abba-comparator-implementation.md"
)
CAPTURE_PARSER_PATH = ROOT / "scripts" / "regression-harness" / "device_ap_cadence_capture.py"
BASE_ENV = "k1_bench_scheduling_baseline_probe"
EXACT_BASE_FLAGS = (
    "-DARDUINO_USB_MODE=1", "-DARDUINO_USB_CDC_ON_BOOT=1", "-DARDUINO_RUNNING_CORE=0",
    "-DBOARD_HAS_PSRAM", "-DK1_HARDWARE", "-DK1_LED_TASK_CORE=1",
    "-DK1_I2S_DMA_DESC_NUM_VALUE=3", "-DDEFAULT_SAMPLE_RATE=12800",
    "-DDEFAULT_SAMPLES_PER_CHUNK=96", "-DK1_TEMPO_NOVELTY_DECIMATION=3U",
    "-DK1_GDFT_INT64_MAGNITUDE_V1", "-DK1_GDFT_INT64_RECURRENCE_V1",
    "-DDEFAULT_AUDIO_RESPONSE_GAIN=1.0f", "-DESP32_ARDUINO_NO_RGB_BUILTIN", "-O3",
    "-ffast-math", "-fno-finite-math-only", "-Wno-deprecated-declarations", "-Wno-narrowing",
    "-DK1_TEMPO_CONF_V2", "-DK1_TEMPO_FLYWHEEL_V2", "-DK1_ONSET_V2", "-DK1_CHORD_V2",
    "-DK1_SEMANTIC_STATE", "-DK1_CHORD_HUE_V1", "-DK1_DROP_CUT_V1", "-DK1_PEAK_ASYM_ENV",
    "-DK1_VIVID_PRECOMP_V1", "-DK1_LOUD_GUARD_V1", "-DK1_AUDIO_FREEZE_GUARD_V1",
    "-DK1_TEMPO_ACF_SPREAD_V1=1", "-DK1_AGC_PERBAND_V1=1", "-DK1_BOOTLOOP_GUARD_V1",
    "-DK1_PALETTE_VIBRANCY_V1", "-DK1_BENCH_REFERENCE_PINMAP=1", "-DK1_MIC_IM69D_PDM_V1",
    "-DK1_MIC_IM69D_DSR_16S_V1", "-DK1_MIC_IM69D_SLOT_RIGHT", "-DENABLE_VP_PERF_AUDIT=1",
    "-DENABLE_AP_STREAM=1", "-DENABLE_TEMPO_STREAM=1", "-DENABLE_AP_FRONTEND_DEBUG=1",
    "-DTEMPO_STREAM_DEFAULT_ON=0", "-DAP_STREAM_DEFAULT_ON=0",
)
COMPACT_REPARSE_FIELDS = (
    "schema_ver", "stage_detail", "row_count", "duration_ms", "requested_duration_ms_device",
    "first_frame_ms", "last_frame_ms", "unique_sample_rate", "unique_samples_per_chunk",
    "active_tempo_decimation_mode", "measured_ap_frame_rate_hz",
    "measured_emitted_novelty_count", "measured_emitted_novelty_rate_hz", "frame_gap_count",
    "timestamp_regression_count", "i2s_not_ok_count", "bytes_mismatch_count", "core_bad_count",
    "active_ap_work_over_7500_count", "emitted_active_ap_work_over_7500_count",
    "active_ap_work_sum_us", "active_ap_work_mean_us", "max_consecutive_active_frames_over_7500",
    "p99_bounds_us", "percentile_bounds_us", "observed_max_us", "histogram_saturation", "histogram_geometry",
    "compact_worst_mode_mismatch_count", "compact_worst_count_mismatch", "compact_begin_mode_mismatch",
    "capture_complete", "stack_hwm_admissible", "timing_envelope_admissible",
    "stage_attribution_applicable", "capture_admissible", "vp_perf_stack_hwm_words",
)
BUFFERED_REPARSE_FIELDS = (
    "schema_ver", "stage_detail", "row_count", "capture_complete", "capture_admissible",
    "timing_envelope_admissible", "stage_attribution_applicable", "stage_attribution_admissible",
    "perturbation_control_admissible", "full_stage_row_count", "stage_detail_full_row_count",
    "stage_detail_minimal_row_count", "control_stage_valid_row_count", *ZERO_BUFFERED_COUNTS,
    "unique_sample_rate", "unique_samples_per_chunk", "unique_dma_desc_num", "unique_dma_frame_num",
    "unique_slot_bit_width", "unique_slot_mode", "unique_ap_core_id", "unique_vp_core_id",
    "sample_time_assumption_ids", "capture_metadata", "early_stage_row_count", "stage_timing_row_count",
)
_ACTION_RE = re.compile(
    r"^# action_ts_monotonic_ms=(\d+) action=(\S+) "
    r"phase=(paired_setup|paired_compact|paired_stack_hwm|paired_buffered|paired_postflight) "
    r"pair_id=(\S+) serial_session_id=(\S+)$"
)
_BUILD_RE = re.compile(r"^BUILD: version=(\S+) git=([0-9a-f]{8}) epoch=(\d+) env=(\S+)$")
_VERSION_RE = re.compile(r"^VERSION: (\S+)$")
_IMAGE_RE = re.compile(r"^IMAGE_ID: app_elf_sha256=([0-9a-f]{64})$")
_RUNTIME_RE = re.compile(r"^RUNTIME_ID: boot_nonce=([0-9a-f]{16}) uptime_ms=(\d+) reset_reason=(-?\d+)$")
_PHASE_RE = re.compile(
    r"^# phase_ts_monotonic_ms=(\d+) phase=(paired_compact|paired_stack_hwm|paired_buffered) "
    r"event=(begin|end) pair_id=(\S+) serial_session_id=(\S+)$"
)
_HOST_WINDOW_RE = re.compile(r"^# host_capture_window_(start|end)_monotonic_ms=(\d+)$")


class EvidenceError(ValueError):
    """Raised when the evidence pack cannot support a comparison."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise EvidenceError(message)


def _require_mapping(value: Any, label: str) -> dict[str, Any]:
    _require(isinstance(value, dict), f"{label} must be an object")
    return value


def _require_list(value: Any, label: str) -> list[Any]:
    _require(isinstance(value, list), f"{label} must be an array")
    return value


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"cannot read JSON {path}: {exc}") from exc
    return _require_mapping(value, str(path))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise EvidenceError(f"cannot hash {path}: {exc}") from exc
    return digest.hexdigest()


def _resolve_evidence(
    record: dict[str, Any], key: str, base_dir: Path, label: str
) -> tuple[Path, str]:
    raw_path = record.get(f"{key}_path")
    expected_hash = record.get(f"{key}_sha256")
    _require(isinstance(raw_path, str) and raw_path, f"{label}.{key}_path missing")
    _require(
        isinstance(expected_hash, str) and len(expected_hash) == 64,
        f"{label}.{key}_sha256 must be a SHA-256",
    )
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = base_dir / path
    path = path.resolve()
    actual_hash = _sha256(path)
    _require(actual_hash == expected_hash, f"{label}.{key} SHA-256 mismatch")
    return path, actual_hash


def _number(value: Any, label: str) -> float:
    _require(
        type(value) in (int, float),
        f"{label} must be numeric",
    )
    number = float(value)
    _require(math.isfinite(number), f"{label} must be finite")
    return number


def _raw_number(value: str, label: str) -> float:
    _require(isinstance(value, str) and value, f"{label} must be numeric")
    try:
        number = float(value)
    except ValueError as exc:
        raise EvidenceError(f"{label} must be numeric") from exc
    _require(math.isfinite(number), f"{label} must be finite")
    return number


def _raw_integer(value: str, label: str) -> int:
    number = _raw_number(value, label)
    _require(number.is_integer(), f"{label} must be an integer")
    return int(number)


def _integer(value: Any, label: str) -> int:
    _require(type(value) is int, f"{label} must be an integer")
    return value


def _exact_integer_list(value: Any, expected: list[int], label: str) -> list[int]:
    values = _require_list(value, label)
    _require(len(values) == len(expected), f"{label} mismatch")
    parsed = [_integer(item, f"{label}[{index}]") for index, item in enumerate(values)]
    _require(parsed == expected, f"{label} mismatch")
    return parsed


def _status_rank(status: str) -> int:
    return {"PASS": 0, "INCOMPLETE": 1, "INCONCLUSIVE": 2, "FAIL": 3}[status]


def _worst_status(statuses: Iterable[str]) -> str:
    values = list(statuses)
    _require(bool(values), "cannot classify an empty status set")
    return max(values, key=_status_rank)


def load_deployed_contract(path: Path | None = None) -> dict[str, Any]:
    contract_path = path or DEPLOYED_CONTRACT_PATH
    return _load_json(contract_path)


def perturbation_limits(contract: dict[str, Any] | None = None) -> dict[str, Any]:
    """Freeze min/full perturbation verdict limits from the deployed contract."""

    contract = contract or load_deployed_contract()
    period = int(contract["production_tuple"]["ap_arrival_period_us"])
    fraction = float(contract["margin_rules"]["instrumented_vs_minimal_p99_regression_max_fraction"])
    drop_max = int(contract["margin_rules"]["instrumented_capture_drop_max"])
    return {
        "ap_arrival_period_us": period,
        "ap_p99_delta_max_us": int(round(fraction * period)),
        "ap_p99_delta_max_fraction": fraction,
        "throughput_delta_max_hz": PERTURBATION_THROUGHPUT_DELTA_MAX_HZ,
        "frame_gap_delta_max": PERTURBATION_FRAME_GAP_DELTA_MAX,
        "i2s_delta_max": PERTURBATION_I2S_DELTA_MAX,
        "instrumented_capture_drop_max": drop_max,
        "stage_attribution_overhead_fraction": fraction,
        "repeatability_admission_limit_pp": 2.0,
        "source": "deployed_contract_margin_rules",
    }


def service_limits_from_contract(contract: dict[str, Any] | None = None) -> dict[str, Any]:
    contract = contract or load_deployed_contract()
    period = int(contract["production_tuple"]["ap_arrival_period_us"])
    fraction = float(contract["margin_rules"]["ap_service_p99_max_fraction_of_arrival"])
    sample_rate = float(contract["production_tuple"]["sample_rate_hz"])
    chunk = float(contract["production_tuple"]["samples_per_chunk"])
    expected_hz = sample_rate / chunk
    return {
        "ap_arrival_period_us": period,
        "ap_service_p99_max_us": int(period * fraction),
        "expected_ap_rate_hz": expected_hz,
        "measured_ap_rate_min_hz": expected_hz - SERVICE_RATE_TOLERANCE_LOW_HZ,
        "measured_ap_rate_max_hz": expected_hz + SERVICE_RATE_TOLERANCE_HIGH_HZ,
        "ap_max_consecutive_over_period": int(contract["margin_rules"]["ap_max_consecutive_over_period"]),
        "ap_recovery_hops_max": int(contract["margin_rules"]["ap_recovery_hops_max"]),
    }


def _row_flag(row: dict[str, Any], *keys: str) -> bool | None:
    for key in keys:
        if key in row and row[key] is not None:
            value = row[key]
            if isinstance(value, bool):
                return value
            try:
                return int(value) == 1
            except (TypeError, ValueError):
                return bool(value)
    return None


def classify_frame_row(row: dict[str, Any]) -> str:
    """Mutually exclusive frame class from tempo emit + onset event markers."""

    tempo_active = bool(_row_flag(row, "tempo_event", "emitted"))
    onset_active = bool(_row_flag(row, "onset_event", "onset_accepted"))
    if tempo_active and onset_active:
        return "tempo_and_onset"
    if tempo_active:
        return "tempo_only"
    if onset_active:
        return "onset_only"
    return "neither"


def _percentile_linear(sorted_values: list[float], percentile: float) -> float:
    """Numpy default linear percentile on a pre-sorted non-empty sequence."""

    if not sorted_values:
        raise ValueError("percentile requires at least one value")
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    rank = (len(sorted_values) - 1) * (percentile / 100.0)
    low = int(math.floor(rank))
    high = int(math.ceil(rank))
    if low == high:
        return float(sorted_values[low])
    weight = rank - low
    return float(sorted_values[low] * (1.0 - weight) + sorted_values[high] * weight)


def _metric_values(rows: list[dict[str, Any]], key: str) -> list[float]:
    values: list[float] = []
    for row in rows:
        if key not in row or row[key] is None:
            continue
        try:
            values.append(float(row[key]))
        except (TypeError, ValueError):
            continue
    return values


def _class_metric_block(
    values: list[float], *, onset_marker_present: bool, class_name: str
) -> dict[str, Any]:
    needs_onset = class_name in {"onset_only", "tempo_and_onset"}
    if needs_onset and not onset_marker_present:
        return {
            "n": len(values),
            "status": "MISSING_MARKER",
            "percentile_method": FRAME_CLASS_PERCENTILE_METHOD,
            "minimum_n_for_p95": FRAME_CLASS_MINIMUM_N_FOR_P95,
            "minimum_n_for_p99": FRAME_CLASS_MINIMUM_N_FOR_P99,
        }
    n = len(values)
    block: dict[str, Any] = {
        "n": n,
        "percentile_method": FRAME_CLASS_PERCENTILE_METHOD,
        "minimum_n_for_p95": FRAME_CLASS_MINIMUM_N_FOR_P95,
        "minimum_n_for_p99": FRAME_CLASS_MINIMUM_N_FOR_P99,
    }
    if n == 0:
        block["status"] = "INSUFFICIENT_N"
        return block
    ordered = sorted(values)
    block["max"] = ordered[-1]
    if n < FRAME_CLASS_MINIMUM_N_FOR_P99:
        block["status"] = "INSUFFICIENT_N"
        if n >= FRAME_CLASS_MINIMUM_N_FOR_P95:
            block["p95"] = _percentile_linear(ordered, 95.0)
        return block
    block["status"] = "COMPLETE"
    block["p95"] = _percentile_linear(ordered, 95.0)
    block["p99"] = _percentile_linear(ordered, 99.0)
    return block


def frame_class_distributions(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Partition rows into exclusive tempo/onset classes plus optional marginal views."""

    onset_marker_present = any(
        key in row for row in rows for key in ("onset_event", "onset_accepted")
    )
    buckets: dict[str, list[dict[str, Any]]] = {name: [] for name in EXCLUSIVE_FRAME_CLASSES}
    for row in rows:
        buckets[classify_frame_row(row)].append(row)

    exclusive: dict[str, Any] = {}
    for name, members in buckets.items():
        active = _class_metric_block(
            _metric_values(members, "active_ap_work_us")
            or _metric_values(members, "active_ap_work"),
            onset_marker_present=onset_marker_present,
            class_name=name,
        )
        gdft = _class_metric_block(
            _metric_values(members, "gdft_us") or _metric_values(members, "gdft_elapsed_us"),
            onset_marker_present=onset_marker_present,
            class_name=name,
        )
        exclusive[name] = {
            "n": len(members),
            "status": active["status"],
            "percentile_method": FRAME_CLASS_PERCENTILE_METHOD,
            "minimum_n_for_p95": FRAME_CLASS_MINIMUM_N_FOR_P95,
            "minimum_n_for_p99": FRAME_CLASS_MINIMUM_N_FOR_P99,
            "active_ap_work": active,
            "gdft": gdft,
        }

    tempo_any = buckets["tempo_only"] + buckets["tempo_and_onset"]
    onset_any = buckets["onset_only"] + buckets["tempo_and_onset"]
    return {
        "exclusive": exclusive,
        "marginal": {
            "tempo_any": {"n": len(tempo_any)},
            "onset_any": {"n": len(onset_any)},
        },
        "onset_marker_present": onset_marker_present,
        "row_count": len(rows),
    }


def compare_frame_classes(
    min_rows: list[dict[str, Any]], full_rows: list[dict[str, Any]]
) -> dict[str, Any]:
    """Per-class min versus full deltas required for ABBA stage attribution."""

    min_dist = frame_class_distributions(min_rows)
    full_dist = frame_class_distributions(full_rows)
    comparison: dict[str, Any] = {}
    for name in EXCLUSIVE_FRAME_CLASSES:
        min_n = min_dist["exclusive"][name]["n"]
        full_n = full_dist["exclusive"][name]["n"]
        min_active = min_dist["exclusive"][name]["active_ap_work"]
        full_active = full_dist["exclusive"][name]["active_ap_work"]
        min_gdft = min_dist["exclusive"][name]["gdft"]
        full_gdft = full_dist["exclusive"][name]["gdft"]

        def _delta(left: dict[str, Any], right: dict[str, Any], key: str) -> float | None:
            if key not in left or key not in right:
                return None
            return float(right[key]) - float(left[key])

        rate_min = min_n / max(len(min_rows), 1)
        rate_full = full_n / max(len(full_rows), 1)
        comparison[name] = {
            "min_n": min_n,
            "full_n": full_n,
            "active_ap_p99_delta_us": _delta(min_active, full_active, "p99"),
            "active_ap_max_delta_us": _delta(min_active, full_active, "max"),
            "gdft_p99_delta_us": _delta(min_gdft, full_gdft, "p99"),
            "rate_delta_hz": rate_full - rate_min,
            "classification_changed": min_n != full_n,
            "min_status": min_active.get("status"),
            "full_status": full_active.get("status"),
        }
    return comparison


def _normalise_flags(flags: Any, label: str) -> list[str]:
    values = _require_list(flags, label)
    _require(all(isinstance(item, str) and item for item in values), f"{label} has a non-string flag")
    _require(len(values) == len(set(values)), f"{label} contains duplicate flags")
    return list(values)


def _without_detail(flags: list[str]) -> Counter[str]:
    return Counter(flag for flag in flags if not flag.startswith(f"-D{DETAIL_DEFINE}="))


def _capture_parser() -> Any:
    module_spec = importlib.util.spec_from_file_location("k1_abba_capture_parser", CAPTURE_PARSER_PATH)
    _require(module_spec is not None and module_spec.loader is not None, "cannot load canonical capture parser")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def _parse_pio_config(value: Any, label: str) -> dict[str, dict[str, Any]]:
    rows = _require_list(value, label)
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        _require(isinstance(row, list) and len(row) == 2, f"{label} has an invalid environment row")
        name, options = row
        _require(isinstance(name, str) and name.startswith("env:"), f"{label} has an invalid environment name")
        option_rows = _require_list(options, f"{label}.{name}")
        option_map: dict[str, Any] = {}
        for option in option_rows:
            _require(isinstance(option, list) and len(option) == 2, f"{label}.{name} has an invalid option")
            key, option_value = option
            _require(isinstance(key, str) and key not in option_map, f"{label}.{name} has a duplicate option")
            option_map[key] = option_value
        result[name.removeprefix("env:")] = option_map
    return result


def _current_pio_config() -> Any:
    try:
        result = subprocess.run(
            ["pio", "project", "config", "--json-output"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        return json.loads(result.stdout)
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"cannot resolve current PlatformIO configuration: {exc}") from exc


def _current_git_state() -> dict[str, str]:
    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
            capture_output=True, text=True,
        ).stdout.strip()
        raw_status = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=all"], cwd=ROOT,
            check=True, capture_output=True, text=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        raise EvidenceError(f"cannot resolve current git state: {exc}") from exc
    return {"head": head, "tracked_status": raw_status}


def _validate_evidence_output_root(spec: dict[str, Any]) -> str:
    value = spec.get("evidence_output_root")
    _require(isinstance(value, str) and value, "evidence_output_root missing")
    path = Path(value)
    _require(not path.is_absolute() and ".." not in path.parts, "evidence_output_root must be repo-relative")
    normalised = path.as_posix().rstrip("/") + "/"
    _require(
        normalised.startswith("docs/forensics/runtime-evidence/")
        and len(path.parts) == 4
        and path.name == spec.get("series_id"),
        "evidence_output_root must name one runtime-evidence series directory",
    )
    return normalised


def _filter_worktree_status(status: str, evidence_root: str) -> str:
    retained: list[str] = []
    for line in status.splitlines():
        path = line[3:].split(" -> ")[-1] if len(line) >= 4 else ""
        allowed = line.startswith("?? ") and (
            path.startswith(evidence_root) or path == AUDIT_RECEIPT_PATH
        )
        if not allowed:
            retained.append(line)
    return "\n".join(retained) + ("\n" if retained else "")


def _validate_pio_config(
    spec: dict[str, Any], base_dir: Path, current_pio_config: Any | None
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    record = _require_mapping(spec.get("platformio_config"), "platformio_config")
    snapshot_path, snapshot_hash = _resolve_evidence(record, "snapshot", base_dir, "platformio_config")
    snapshot_raw = json.loads(snapshot_path.read_text(encoding="utf-8"))
    live_raw = _current_pio_config() if current_pio_config is None else current_pio_config
    snapshot = _parse_pio_config(snapshot_raw, "PlatformIO snapshot")
    live = _parse_pio_config(live_raw, "current PlatformIO config")
    names = (BASE_ENV, MIN_ENV, FULL_ENV)
    _require(all(name in snapshot and name in live for name in names), "PlatformIO config lacks a required probe environment")
    for name in names:
        _require(snapshot[name] == live[name], f"current resolved PlatformIO config differs from snapshot for {name}")
    baseline = snapshot[BASE_ENV]
    minimum = snapshot[MIN_ENV]
    full = snapshot[FULL_ENV]
    base_flags = _normalise_flags(baseline.get("build_flags"), f"{BASE_ENV}.build_flags")
    _require(tuple(base_flags) == EXACT_BASE_FLAGS, "resolved baseline build-flag list/order differs from the frozen contract")
    _require(minimum.get("build_flags") == base_flags + [DETAIL_FLAGS["MIN"]], "MIN flags are not exact baseline plus detail=0")
    _require(full.get("build_flags") == base_flags + [DETAIL_FLAGS["FULL"]], "FULL flags are not exact baseline plus detail=1")
    for role, options in (("MIN", minimum), ("FULL", full)):
        expected = {key: value for key, value in baseline.items() if key not in {"extends", "build_flags"}}
        actual = {key: value for key, value in options.items() if key not in {"extends", "build_flags"}}
        _require(actual == expected, f"{role} resolved libraries/linker/upload/options differ from baseline")
        expected_parent = [f"env:{BASE_ENV}"]
        _require(options.get("extends") == expected_parent, f"{role} does not extend only the baseline")
    return snapshot, {
        "path": str(snapshot_path),
        "sha256": snapshot_hash,
        "resolved_environments": {name: snapshot[name] for name in names},
    }


def _validate_builds(
    spec: dict[str, Any], base_dir: Path, pio_config: dict[str, dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    builds = _require_mapping(spec.get("builds"), "builds")
    _require(set(builds) == {"MIN", "FULL"}, "builds must contain exactly MIN and FULL")
    expected_env = {"MIN": MIN_ENV, "FULL": FULL_ENV}
    validated: dict[str, dict[str, Any]] = {}
    source_shas: set[str] = set()
    for role in ("MIN", "FULL"):
        build = _require_mapping(builds[role], f"builds.{role}")
        _require(build.get("environment") == expected_env[role], f"{role} environment mismatch")
        _require(
            _integer(build.get("stage_detail"), f"{role}.stage_detail") == (0 if role == "MIN" else 1),
            f"{role} stage_detail mismatch",
        )
        _require(
            _integer(build.get("schema_ver"), f"{role}.schema_ver") == CAPTURE_SCHEMA_VERSION,
            f"{role} schema_ver mismatch",
        )
        _require(build.get("working_tree_state") == "clean", f"{role} build was not made from a clean tree")
        git_sha = build.get("git_sha")
        _require(isinstance(git_sha, str) and len(git_sha) == 40, f"{role} git_sha must be full length")
        source_shas.add(git_sha)
        flags = _normalise_flags(build.get("resolved_build_flags"), f"builds.{role}.resolved_build_flags")
        _require(flags == pio_config[expected_env[role]]["build_flags"], f"{role} manifest flags differ from resolved PlatformIO config")
        _require(flags.count(DETAIL_FLAGS[role]) == 1, f"{role} detail flag is missing")
        _require(
            sum(flag.startswith(f"-D{DETAIL_DEFINE}=") for flag in flags) == 1,
            f"{role} has multiple detail definitions",
        )
        elf_path, elf_hash = _resolve_evidence(build, "elf", base_dir, f"builds.{role}")
        firmware_version = build.get("firmware_version")
        _require(isinstance(firmware_version, str) and firmware_version, f"{role} firmware_version missing")
        emitted_git_sha = build.get("emitted_git_sha")
        _require(
            emitted_git_sha == git_sha[:8] and re.fullmatch(r"[0-9a-f]{8}", emitted_git_sha) is not None,
            f"{role} emitted_git_sha must be the exact eight-character source prefix",
        )
        version_line = build.get("firmware_version_line")
        _require(version_line == f"VERSION: {firmware_version}", f"{role} firmware version line mismatch")
        _require(_integer(build.get("build_epoch"), f"builds.{role}.build_epoch") > 0, f"{role} build epoch missing")
        validated[role] = {
            **build,
            "resolved_build_flags": flags,
            "elf_path": str(elf_path),
            "elf_sha256": elf_hash,
        }
    _require(len(source_shas) == 1, "MIN and FULL do not use the same source SHA")
    _require(
        _without_detail(validated["MIN"]["resolved_build_flags"])
        == _without_detail(validated["FULL"]["resolved_build_flags"]),
        "resolved flags differ beyond K1_AP_STAGE_ATTRIBUTION_DETAIL",
    )
    _require(
        validated["MIN"]["elf_sha256"] != validated["FULL"]["elf_sha256"],
        "MIN and FULL ELF hashes are unexpectedly identical",
    )
    return validated


def _validate_fixture_contract(spec: dict[str, Any]) -> dict[str, dict[str, Any]]:
    fixtures = _require_mapping(spec.get("fixtures"), "fixtures")
    _require(set(fixtures) == {"music", "no_playback"}, "fixtures must contain exactly music and no_playback")
    music = _require_mapping(fixtures["music"], "fixtures.music")
    quiet = _require_mapping(fixtures["no_playback"], "fixtures.no_playback")
    _require(music.get("track_path") == EXPECTED_MUSIC_PATH, "music track path mismatch")
    _require(music.get("track_sha256") == EXPECTED_MUSIC_SHA256, "music track SHA-256 mismatch")
    _require(music.get("player") == "ffplay", "music player must be ffplay")
    _require(_integer(music.get("start_ms"), "fixtures.music.start_ms") == 0, "music start_ms must be zero")
    _require(_number(music.get("playback_gain_db"), "fixtures.music.playback_gain_db") == 0.0, "music gain must be 0.0 dB")
    _require(_integer(music.get("pre_roll_seconds"), "fixtures.music.pre_roll_seconds") == 10, "music pre-roll must be 10 seconds")
    _require(isinstance(music.get("output_device"), str) and music["output_device"], "music output device missing")
    _require("captain_audible_confirmation_timestamp" not in music, "exact audible-confirmation timestamp is not authoritative")
    confirmation = music.get("captain_audible_confirmation_not_after")
    _require(isinstance(confirmation, str) and confirmation, "Captain audible-confirmation upper bound missing")
    try:
        confirmation_time = datetime.fromisoformat(confirmation)
    except ValueError as exc:
        raise EvidenceError("Captain audible-confirmation upper bound is not valid ISO-8601") from exc
    _require(confirmation_time.tzinfo is not None, "Captain audible-confirmation upper bound lacks timezone")
    _require(quiet.get("host_playback") is False, "no_playback must disable host playback")
    _require(quiet.get("output_quiet_confirmed") is True, "quiet output confirmation missing")
    _require(quiet.get("output_device") == music.get("output_device"), "fixtures must use the same fixed output device")
    return {"music": dict(music), "no_playback": dict(quiet)}


def _validate_runtime_contract(spec: dict[str, Any]) -> dict[str, Any]:
    contract = _require_mapping(spec.get("runtime_contract"), "runtime_contract")
    exact = {
        "sample_rate": 12800,
        "samples_per_chunk": 96,
        "novelty_decimation": 3,
        "dma_desc_num": 3,
        "dma_frame_num": 96,
        "slot_bit_width": 32,
        "slot_mode": 2,
        "sample_time_assumption_id": 1,
        "ap_core": 0,
        "vp_core": 1,
        "ap_priority": 1,
        "vp_priority": 1,
        "vtask_delay_ticks": 1,
        "gdft_crossover_bin": 0,
        "gdft_lane4_enabled": False,
        "gdft_int64_magnitude": True,
        "gdft_int64_recurrence": True,
        "gdft_overflow_expected": False,
        "microphone_backend": "IM69D130_PDM",
        "microphone_slot": "RIGHT",
        "pdm_dsr": "16S",
        "max_transition_duration_ms": 3000,
    }
    for key, expected in exact.items():
        actual = contract.get(key)
        _require(
            type(actual) is type(expected) and actual == expected,
            f"runtime_contract.{key} must be {expected}",
        )
    _require(contract.get("gdft_backend") == "current_80_bin_direct_cross0", "runtime_contract.gdft_backend mismatch")
    _require("scene" not in contract, "runtime_contract.scene is unproven; bind it to device status before declaring it")
    streams = _require_mapping(contract.get("streams_running_during_capture"), "runtime_contract.streams_running_during_capture")
    for name in ("ap", "tempo", "frontend", "vp", "diagnostic", "vp_perf"):
        _require(streams.get(name) is False, f"stream {name} was not declared stopped")
    return dict(contract)


def _validate_flash_receipts(
    spec: dict[str, Any], base_dir: Path, builds: dict[str, dict[str, Any]]
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    records = _require_list(spec.get("flash_receipts"), "flash_receipts")
    _require(len(records) == 3, "exactly three A1/B/A2 flash receipts are required")
    expected = (("A1", "MIN"), ("B", "FULL"), ("A2", "MIN"))
    by_session: dict[str, dict[str, Any]] = {}
    expanded: list[dict[str, Any]] = []
    nonces: set[str] = set()
    timestamps: list[datetime] = []
    completion_times: list[int] = []
    for supplied, (session, role) in zip(records, expected, strict=True):
        record = _require_mapping(supplied, f"flash_receipts.{session}")
        receipt_path, receipt_hash = _resolve_evidence(record, "receipt", base_dir, f"flash_receipts.{session}")
        receipt = _load_json(receipt_path)
        _require(receipt.get("session") == session, f"flash receipt order/session mismatch for {session}")
        _require(receipt.get("build") == role, f"flash receipt build mismatch for {session}")
        _require(receipt.get("chip_id") == EXPECTED_DEVICE["chip_id"], f"flash receipt chip mismatch for {session}")
        _require(receipt.get("usb_serial") == EXPECTED_DEVICE["usb_serial"], f"flash receipt USB serial mismatch for {session}")
        _require(receipt.get("port_rediscovered") is True, f"flash receipt lacks port rediscovery for {session}")
        _require(receipt.get("identity_guard_pass") is True, f"identity guard did not pass for {session}")
        _require(isinstance(receipt.get("observed_port"), str) and receipt["observed_port"], f"flash receipt port missing for {session}")
        nonce = receipt.get("boot_nonce")
        _require(isinstance(nonce, str) and re.fullmatch(r"[0-9a-f]{16}", nonce) is not None, f"flash receipt boot nonce invalid for {session}")
        _require(nonce not in nonces, "A1, B and A2 must have three distinct flash/boot identities")
        nonces.add(nonce)
        _require(receipt.get("git_sha") == builds[role]["git_sha"], f"flash receipt git mismatch for {session}")
        _require(receipt.get("environment") == builds[role]["environment"], f"flash receipt environment mismatch for {session}")
        _require(
            _integer(receipt.get("build_epoch"), f"flash receipt build epoch for {session}")
            == _integer(builds[role]["build_epoch"], f"build epoch for {role}"),
            f"flash receipt build epoch mismatch for {session}",
        )
        _require(receipt.get("elf_sha256") == builds[role]["elf_sha256"], f"flash receipt ELF mismatch for {session}")
        timestamp = receipt.get("timestamp")
        _require(isinstance(timestamp, str), f"flash receipt timestamp missing for {session}")
        try:
            parsed_timestamp = datetime.fromisoformat(timestamp)
            _require(parsed_timestamp.tzinfo is not None, f"flash receipt timestamp lacks timezone for {session}")
            timestamps.append(parsed_timestamp)
        except ValueError as exc:
            raise EvidenceError(f"flash receipt timestamp invalid for {session}") from exc
        completed = _integer(receipt.get("flash_completed_monotonic_ms"), f"flash receipt completion for {session}")
        _require(completed > 0, f"flash receipt completion invalid for {session}")
        completion_times.append(completed)
        by_session[session] = receipt
        expanded.append({**receipt, "evidence": {"path": str(receipt_path), "sha256": receipt_hash}})
    _require(timestamps == sorted(timestamps) and len(set(timestamps)) == 3, "flash receipt timestamps are not three distinct ordered events")
    _require(completion_times == sorted(completion_times) and len(set(completion_times)) == 3, "flash monotonic completion order is not A1-B-A2")
    return by_session, expanded


def _comment_value(lines: list[str], prefix: str, label: str) -> str:
    values = [line[len(prefix) :] for line in lines if line.startswith(prefix)]
    _require(len(values) == 1 and values[0], f"{label} must contain exactly one {prefix!r} record")
    return values[0]


def _resolved_declared_raw_path(value: Any) -> Path:
    _require(isinstance(value, str) and value, "summary raw_log path missing")
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (ROOT / path).resolve()


def _compare_reparse_fields(
    declared: dict[str, Any], canonical: dict[str, Any], fields: Iterable[str], label: str
) -> None:
    for field in fields:
        _require(field in declared, f"{label} declared summary is missing {field}")
        _require(field in canonical, f"{label} canonical reparse is missing {field}")
        _require(declared[field] == canonical[field], f"{label} summary differs from raw reparse at {field}")


def _reject_malformed_prefixed_lines(lines: list[str], label: str) -> None:
    """Fail closed on near-miss marker/identity grammar; never silently ignore it."""

    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("# action_ts"):
            _require(_ACTION_RE.fullmatch(line) is not None, f"{label} contains a malformed paired action marker")
        elif stripped.startswith("# phase_ts"):
            _require(_PHASE_RE.fullmatch(line) is not None, f"{label} contains a malformed paired phase marker")
        elif stripped.startswith("# host_capture_window_"):
            _require(
                _HOST_WINDOW_RE.fullmatch(line) is not None,
                f"{label} contains a malformed host-window marker",
            )
        identity = line.strip()
        if identity.startswith("BUILD:"):
            _require(_BUILD_RE.fullmatch(identity) is not None, f"{label} contains a malformed BUILD record")
        elif identity.startswith("VERSION:"):
            _require(_VERSION_RE.fullmatch(identity) is not None, f"{label} contains a malformed VERSION record")
        elif identity.startswith("IMAGE_ID:"):
            _require(_IMAGE_RE.fullmatch(identity) is not None, f"{label} contains a malformed IMAGE_ID record")
        elif identity.startswith("RUNTIME_ID:"):
            _require(_RUNTIME_RE.fullmatch(identity) is not None, f"{label} contains a malformed RUNTIME_ID record")


def _parse_actions(lines: list[str], label: str) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for index, line in enumerate(lines):
        if line.startswith("# action_ts_monotonic_ms="):
            match = _ACTION_RE.fullmatch(line)
            _require(match is not None, f"{label} contains a malformed paired action marker")
            actions.append({
                "monotonic_ms": int(match.group(1)), "action": match.group(2),
                "phase": match.group(3), "pair_id": match.group(4),
                "serial_session_id": match.group(5), "line_index": index,
            })
    _require(actions, f"{label} has no timestamped action records")
    _require(
        all(a["monotonic_ms"] <= b["monotonic_ms"] for a, b in zip(actions, actions[1:])),
        f"{label} action timestamps regress",
    )
    return actions


def _single_action(actions: list[dict[str, Any]], token: str, label: str) -> dict[str, Any]:
    matches = [action for action in actions if action["action"] == token]
    _require(len(matches) == 1, f"{label} must contain exactly one action={token}")
    return matches[0]


def _action_response_lines(
    lines: list[str], actions: list[dict[str, Any]], action: dict[str, Any]
) -> list[str]:
    later = [item["line_index"] for item in actions if item["line_index"] > action["line_index"]]
    end = min(later) if later else len(lines)
    return lines[action["line_index"] + 1 : end]


def _require_action_ack(
    lines: list[str], actions: list[dict[str, Any]], token: str, expected: str, label: str,
) -> None:
    action = _single_action(actions, token, label)
    response = _action_response_lines(lines, actions, action)
    _require(expected in response, f"{label} {token} did not return exact acknowledgement {expected!r}")


def _parse_host_window(lines: list[str], label: str) -> tuple[int, int]:
    starts: list[int] = []
    ends: list[int] = []
    for line in lines:
        match = _HOST_WINDOW_RE.fullmatch(line)
        if match is None:
            continue
        if match.group(1) == "start":
            starts.append(int(match.group(2)))
        else:
            ends.append(int(match.group(2)))
    _require(len(starts) == 1, f"{label} must contain exactly one host window start")
    _require(len(ends) == 1, f"{label} must contain exactly one host window end")
    _require(ends[0] > starts[0], f"{label} host capture window is invalid")
    return starts[0], ends[0]


def _validate_raw_identity(
    lines: list[str], actions: list[dict[str, Any]], build: dict[str, Any], leg: dict[str, Any],
    kind: str, label: str,
) -> dict[str, Any]:
    builds = [(index, match) for index, line in enumerate(lines) if (match := _BUILD_RE.fullmatch(line.strip()))]
    versions = [(index, match) for index, line in enumerate(lines) if (match := _VERSION_RE.fullmatch(line.strip()))]
    images = [(index, match) for index, line in enumerate(lines) if (match := _IMAGE_RE.fullmatch(line.strip()))]
    runtimes = [(index, match) for index, line in enumerate(lines) if (match := _RUNTIME_RE.fullmatch(line.strip()))]
    expected_identity_count = 1 if kind == "compact" else 0
    _require(len(builds) == expected_identity_count, f"{label} BUILD record count is invalid for paired {kind}")
    _require(len(versions) == expected_identity_count, f"{label} VERSION record count is invalid for paired {kind}")
    _require(len(images) == expected_identity_count, f"{label} IMAGE_ID record count is invalid for paired {kind}")
    _require(len(runtimes) == 1, f"{label} must contain exactly one paired-session RUNTIME_ID record")
    nonce = runtimes[0][1].group(1)
    uptime = int(runtimes[0][1].group(2))
    _require(nonce == leg["boot_identity_start"], f"{label} raw boot nonce differs from leg")
    _require(leg["boot_identity_end"] == nonce, f"{label} leg boot identity changed")

    runtime_actions = [action for action in actions if action["action"] == "runtime_id"]
    _require(len(runtime_actions) == 1, f"{label} must issue exactly one paired-session runtime_id")
    runtime_response_line = lines[runtimes[0][0]]
    _require(
        runtime_response_line in _action_response_lines(lines, actions, runtime_actions[0]),
        f"{label} RUNTIME_ID response is outside its action-response window",
    )
    build_action_ms = image_action_ms = None
    if kind == "compact":
        build_index, build_match = builds[0]
        version_index, version_match = versions[0]
        image_index, image_match = images[0]
        _require(version_match.group(1) == build["firmware_version"], f"{label} VERSION mismatch")
        _require(build_match.group(1) == build["firmware_version"], f"{label} BUILD version mismatch")
        _require(build_match.group(2) == build["emitted_git_sha"], f"{label} BUILD git mismatch")
        _require(int(build_match.group(3)) == build["build_epoch"], f"{label} BUILD epoch mismatch")
        _require(build_match.group(4) == build["environment"], f"{label} BUILD environment mismatch")
        _require(image_match.group(1) == build["elf_sha256"], f"{label} IMAGE_ID does not match ELF SHA-256")
        version_action = _single_action(actions, "version", label)
        build_action = _single_action(actions, "build", label)
        image_action = _single_action(actions, "image_id", label)
        _require(
            lines[version_index] in _action_response_lines(lines, actions, version_action)
            and lines[build_index] in _action_response_lines(lines, actions, build_action)
            and lines[image_index] in _action_response_lines(lines, actions, image_action),
            f"{label} VERSION/BUILD/IMAGE response is outside its action-response window",
        )
        build_action_ms = build_action["monotonic_ms"]
        image_action_ms = image_action["monotonic_ms"]
    else:
        _require(not any(action["action"] in {"build", "image_id"} for action in actions), f"{label} repeats pre-session identity commands")
    port_header = _comment_value(lines, "# port=", label)
    _require(port_header.split()[0] == leg["observed_port"], f"{label} raw port header mismatch")
    serial_json = _comment_value(lines, "# serial_identity=", label)
    try:
        serial_identity = json.loads(serial_json)
    except json.JSONDecodeError as exc:
        raise EvidenceError(f"{label} serial identity JSON invalid") from exc
    _require(serial_identity.get("serial_number") == EXPECTED_DEVICE["usb_serial"], f"{label} raw USB serial mismatch")
    capture_start = _comment_value(lines, "# capture_start=", label)
    try:
        _require(datetime.fromisoformat(capture_start).tzinfo is not None, f"{label} capture timestamp lacks timezone")
    except ValueError as exc:
        raise EvidenceError(f"{label} capture timestamp invalid") from exc
    return {
        "boot_nonce": nonce,
        "uptime_ms": uptime,
        "reset_reason": int(runtimes[0][1].group(3)),
        "build_version": builds[0][1].group(1) if kind == "compact" else None,
        "capture_start": capture_start,
        "build_action_monotonic_ms": build_action_ms,
        "image_action_monotonic_ms": image_action_ms,
        "runtime_action_monotonic_ms": runtime_actions[0]["monotonic_ms"],
    }


def _validate_raw_fixture(
    lines: list[str], actions: list[dict[str, Any]], fixture: str, fixture_contract: dict[str, Any],
    require_settle: bool, label: str,
) -> dict[str, Any]:
    observed_output = _comment_value(lines, "# observed_output_device=", label)
    _require(observed_output == fixture_contract.get("output_device"), f"{label} output device mismatch")
    pre_roll = _raw_number(_comment_value(lines, "# pre_roll_seconds=", label), f"{label} pre-roll")
    _require(pre_roll == 10.0, f"{label} pre-roll declaration is not 10 seconds")
    if fixture == "music":
        _require(_comment_value(lines, "# track=", label) == EXPECTED_MUSIC_PATH, f"{label} raw track mismatch")
        _require(_comment_value(lines, "# track_sha256=", label) == EXPECTED_MUSIC_SHA256, f"{label} raw track hash mismatch")
        player = _comment_value(lines, "# player=", label)
        _require(player == "ffplay start_ms=0 playback_gain_db=0.0", f"{label} player settings mismatch")
        settle_token = "playback_start"
    else:
        _require(_comment_value(lines, "# track=", label) == "<none>", f"{label} quiet track marker mismatch")
        _require(_comment_value(lines, "# track_sha256=", label) in {"None", "<none>"}, f"{label} quiet track hash marker mismatch")
        _require(_comment_value(lines, "# player=", label) == "<disabled>", f"{label} quiet player marker mismatch")
        settle_token = "quiet_settle_start"
        _require(fixture_contract.get("output_quiet_confirmed") is True, f"{label} quiet output was not confirmed")
    settle_actions = [action for action in actions if action["action"] == settle_token]
    _require(len(settle_actions) == (1 if require_settle else 0), f"{label} paired fixture settle action count is invalid")
    return {
        "settle_monotonic_ms": settle_actions[0]["monotonic_ms"] if settle_actions else None,
        "observed_output_device": observed_output,
    }


def _validate_raw_timing(
    lines: list[str], actions: list[dict[str, Any]], arm_token: str, fixture_timing: dict[str, Any],
    expected_duration_ms: int, kind: str, label: str,
) -> dict[str, int]:
    arm = _single_action(actions, arm_token, label)
    host_start, host_end = _parse_host_window(lines, label)
    _require(0 <= arm["monotonic_ms"] - host_start <= 100, f"{label} host window did not start immediately before arm")
    _require(expected_duration_ms - 1000 <= host_end - host_start <= expected_duration_ms + 1000, f"{label} host capture duration mismatch")
    if kind == "compact":
        vp_stops = [action for action in actions if action["action"] == "vp_perf=stop" and action["line_index"] < arm["line_index"]]
        _require(len(vp_stops) == 2, f"{label} requires initial and final pre-pair vp_perf stops")
        final_stop = vp_stops[-1]
        settle_ms = fixture_timing["settle_monotonic_ms"]
        _require(final_stop["monotonic_ms"] <= settle_ms < arm["monotonic_ms"], f"{label} final stop/settle/arm order invalid")
        _require(arm["monotonic_ms"] - settle_ms >= 10000, f"{label} did not complete the 10-second pre-roll/quiet settle before arm")
        allowed = {arm_token, "playback_start", "quiet_settle_start"}
        in_window = [
            action for action in actions
            if final_stop["line_index"] < action["line_index"] and action["monotonic_ms"] <= host_end
        ]
        _require(all(action["action"] in allowed for action in in_window), f"{label} contains a prohibited/restarted action in the measured window")
    else:
        forbidden = {"build", "image_id", "playback_start", "quiet_settle_start", "vp_perf=stop", "vp_perf=start"}
        _require(not any(action["action"] in forbidden for action in actions), f"{label} repeats paired-session setup/pre-roll or restarts vp_perf")
    return {"host_start_monotonic_ms": host_start, "host_end_monotonic_ms": host_end}


def _parse_pair_headers(lines: list[str], expected_phase: str, label: str) -> dict[str, str]:
    values = {
        "schema_ver": _comment_value(lines, "# paired_capture_schema=", label),
        "pair_id": _comment_value(lines, "# pair_id=", label),
        "serial_session_id": _comment_value(lines, "# serial_session_id=", label),
        "fixture_session_id": _comment_value(lines, "# fixture_session_id=", label),
        "phase": _comment_value(lines, "# paired_phase=", label),
    }
    _require(values["schema_ver"] == PAIR_SCHEMA_VERSION, f"{label} is not authoritative paired-mode evidence")
    _require(values["phase"] == expected_phase, f"{label} paired phase mismatch")
    for key in ("pair_id", "serial_session_id", "fixture_session_id"):
        _require(re.fullmatch(r"\S+", values[key]) is not None, f"{label} {key} is invalid")
    return values


def _parse_phase_records(lines: list[str], label: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for index, line in enumerate(lines):
        if line.startswith("# phase_ts_monotonic_ms="):
            match = _PHASE_RE.fullmatch(line)
            _require(match is not None, f"{label} contains a malformed paired phase marker")
            records.append({
                "monotonic_ms": int(match.group(1)), "phase": match.group(2),
                "event": match.group(3), "pair_id": match.group(4),
                "serial_session_id": match.group(5), "line_index": index,
            })
    _require(records, f"{label} has no paired phase records")
    return records


def _parse_scene_responses(
    show_lines: list[str], secondary_lines: list[str], label: str,
) -> dict[str, Any]:
    _require(len(show_lines) == 4 and show_lines[0] == "SHOW_STATE", f"{label} SHOW_STATE block shape mismatch")
    primary = re.fullmatch(r"primary_mode=(-?\d+) palette=(-?\d+)", show_lines[1])
    secondary = re.fullmatch(r"secondary_mode=(-?\d+) palette=(-?\d+) enabled=(on|off)", show_lines[2])
    edge = re.fullmatch(r"edge enabled=(on|off) mode=(-?\d+) strength=(-?\d+\.\d{3})", show_lines[3])
    _require(primary is not None and secondary is not None and edge is not None, f"{label} SHOW_STATE grammar mismatch")
    expected_prefixes = (
        "SECONDARY_ENABLED: ", "SECONDARY_CONTROL: ", "SECONDARY_MODE: ",
        "SECONDARY_PHOTONS: ", "SECONDARY_CHROMA: ", "SECONDARY_MOOD: ",
        "SECONDARY_SATURATION: ", "SECONDARY_PRISM_COUNT: ",
        "SECONDARY_MIRROR_ENABLED: ", "SECONDARY_REVERSE_ORDER: ",
        "SECONDARY_BASE_COAT: ", "SECONDARY_PALETTE_MODE_ENABLED: ",
        "SECONDARY_PALETTE_INDEX: ",
    )
    _require(len(secondary_lines) == 14, f"{label} SECONDARY_STATUS block length mismatch")
    _require(
        all(line.startswith(prefix) for line, prefix in zip(secondary_lines[:13], expected_prefixes, strict=True)),
        f"{label} SECONDARY_STATUS field order mismatch",
    )
    _require(secondary_lines[13] == "NOTE: This command is deprecated, please use secondary_status instead", f"{label} SECONDARY_STATUS trailer mismatch")
    bool_pattern = r"(?:true|false)"
    _require(re.fullmatch(rf"SECONDARY_ENABLED: {bool_pattern}", secondary_lines[0]) is not None, f"{label} secondary enabled grammar mismatch")
    _require(re.fullmatch(rf"SECONDARY_CONTROL: {bool_pattern} \(encoders control (?:primary|secondary) channel\)", secondary_lines[1]) is not None, f"{label} secondary control grammar mismatch")
    mode = re.fullmatch(r"SECONDARY_MODE: (-?\d+) \((.+)\)", secondary_lines[2])
    _require(mode is not None, f"{label} secondary mode grammar mismatch")
    for index in (3, 4, 5, 6):
        _require(re.fullmatch(r"SECONDARY_[A-Z_]+: -?\d+\.\d{6}", secondary_lines[index]) is not None, f"{label} secondary decimal grammar mismatch")
    _require(re.fullmatch(r"SECONDARY_PRISM_COUNT: -?\d+\.\d{2}", secondary_lines[7]) is not None, f"{label} secondary prism grammar mismatch")
    for index in (8, 9, 10, 11):
        _require(re.fullmatch(rf"SECONDARY_[A-Z_]+: {bool_pattern}", secondary_lines[index]) is not None, f"{label} secondary boolean grammar mismatch")
    palette = re.fullmatch(r"SECONDARY_PALETTE_INDEX: (-?\d+)(?: \((.+)\))?", secondary_lines[12])
    _require(palette is not None, f"{label} secondary palette grammar mismatch")
    _require(int(secondary.group(1)) == int(mode.group(1)), f"{label} show/secondary mode responses disagree")
    _require(int(secondary.group(2)) == int(palette.group(1)), f"{label} show/secondary palette responses disagree")
    enabled_value = secondary_lines[0].endswith("true")
    _require((secondary.group(3) == "on") == enabled_value, f"{label} show/secondary enabled responses disagree")
    return {
        "primary_mode": int(primary.group(1)), "primary_palette": int(primary.group(2)),
        "secondary_mode": int(secondary.group(1)), "secondary_palette": int(secondary.group(2)),
        "secondary_enabled": enabled_value, "edge_enabled": edge.group(1) == "on",
        "edge_mode": int(edge.group(2)), "edge_strength": float(edge.group(3)),
    }


def _extract_scene_observation(
    lines: list[str], actions: list[dict[str, Any]], terminal_action: dict[str, Any], label: str,
) -> dict[str, Any]:
    show_action = _single_action(actions, "show_state", label)
    secondary_action = _single_action(actions, "secondary_status", label)
    dump_action = _single_action(actions, "dump", label)
    _require(
        show_action["line_index"] < secondary_action["line_index"] < dump_action["line_index"]
        < terminal_action["line_index"],
        f"{label} scene-observation command order is invalid",
    )
    show_lines = lines[show_action["line_index"] + 1 : secondary_action["line_index"]]
    secondary_lines = lines[secondary_action["line_index"] + 1 : dump_action["line_index"]]
    dump_lines = lines[dump_action["line_index"] + 1 : terminal_action["line_index"]]
    scene_fields = _parse_scene_responses(show_lines, secondary_lines, label)
    brightness_lines = [line for line in dump_lines if line.startswith("MASTER_BRIGHTNESS: ")]
    _require(len(brightness_lines) == 1, f"{label} dump must contain exactly one MASTER_BRIGHTNESS")
    brightness = _raw_number(
        brightness_lines[0].removeprefix("MASTER_BRIGHTNESS: "),
        f"{label} MASTER_BRIGHTNESS",
    )
    _require(0.0 <= brightness <= 1.0, f"{label} MASTER_BRIGHTNESS is outside [0,1]")
    scene_fields.update({
        "master_brightness": brightness,
        "transition_state": "settled_inferred",
        "transition_max_duration_ms": 3000,
    })
    return {
        "show_state_lines": show_lines,
        "secondary_status_lines": secondary_lines,
        "dump_response_sha256": hashlib.sha256(("\n".join(dump_lines) + "\n").encode("utf-8")).hexdigest(),
        "scene_fields": scene_fields,
    }


def _reparse_raw(
    path: Path, declared: dict[str, Any], build: dict[str, Any], fixture: str,
    fixture_contract: dict[str, Any], leg: dict[str, Any], kind: str, label: str,
) -> dict[str, Any]:
    lines = path.read_text(encoding="utf-8", errors="strict").splitlines()
    _reject_malformed_prefixed_lines(lines, label)
    _require(
        not any(
            "BAD COMMAND" in line.upper()
            or line.upper().startswith(("UNKNOWN", "ERROR:", "ERR:", "FAIL:"))
            for line in lines
        ),
        f"{label} raw transcript contains a rejected/unknown/error/failure response",
    )
    parser = _capture_parser()
    pair_headers = _parse_pair_headers(lines, kind, label)
    phase_records = _parse_phase_records(lines, label)
    actions = _parse_actions(lines, label)
    _require(
        all(
            action["pair_id"] == pair_headers["pair_id"]
            and action["serial_session_id"] == pair_headers["serial_session_id"]
            for action in actions
        ),
        f"{label} action markers do not share the paired serial session",
    )
    expected_duration = 120000 if kind == "compact" else 5000
    arm_token = f"apcad_soak={expected_duration}" if kind == "compact" else f"apcad_capture={expected_duration}"
    fixture_timing = _validate_raw_fixture(lines, actions, fixture, fixture_contract, kind == "compact", label)
    host_timing = _validate_raw_timing(lines, actions, arm_token, fixture_timing, expected_duration, kind, label)
    identity = _validate_raw_identity(lines, actions, build, leg, kind, label)
    if kind == "compact":
        _require(
            max(identity["build_action_monotonic_ms"], identity["image_action_monotonic_ms"], identity["runtime_action_monotonic_ms"])
            < host_timing["host_start_monotonic_ms"],
            f"{label} pre-pair identity commands were not completed before arm",
        )
        vp_stops = [action for action in actions if action["action"] == "vp_perf=stop"]
        _require(len(vp_stops) == 3, f"{label} must contain two pre-pair and one post-HWM vp_perf stops")
        preamble = [
            vp_stops[0],
            *[_single_action(actions, token, label) for token in (
                "apdbg=off", "tempo_stream=off", "ap_stream=off", "smart_assist=off",
                "beat_director=off", "queue_mode=off", "show_state", "secondary_status", "dump",
            )],
            vp_stops[1],
        ]
        arm_action = _single_action(actions, arm_token, label)
        settle_token = "playback_start" if fixture == "music" else "quiet_settle_start"
        expected_pre_arm_actions = [
            "stop", "version", "build", "image_id", "runtime_id", "apcad_abort=1",
            "apcad_clear=1", "vp_perf=stop", "apdbg=off",
            "tempo_stream=off", "ap_stream=off", "smart_assist=off", "beat_director=off",
            "queue_mode=off", "show_state", "secondary_status", "dump", "vp_perf=stop",
            settle_token,
        ]
        pre_arm_actions = [action for action in actions if action["line_index"] < arm_action["line_index"]]
        _require(
            [action["action"] for action in pre_arm_actions] == expected_pre_arm_actions
            and all(action["phase"] == "paired_setup" for action in pre_arm_actions),
            f"{label} runtime-control preamble is not the exact frozen sequence",
        )
        for token, acknowledgement in (
            ("apdbg=off", "AP_FRONTEND_DEBUG: off"),
            ("tempo_stream=off", "TEMPO_STREAM: off"),
            ("ap_stream=off", "AP_STREAM: off"),
            ("smart_assist=off", "SMART_ASSIST: off"),
            ("beat_director=off", "BEAT_DIRECTOR: off"),
            ("queue_mode=off", "QUEUE_MODE: off"),
        ):
            _require_action_ack(lines, actions, token, acknowledgement, label)
        for stop_action in vp_stops[:2]:
            _require(
                "VP_PERF: stopped" in _action_response_lines(lines, actions, stop_action),
                f"{label} vp_perf=stop did not prove stopped state",
            )
        first_arm_line = arm_action["line_index"]
        _require(
            not any(
                line.startswith(("BAD COMMAND", "UNKNOWN", "ERROR"))
                for line in lines[:first_arm_line]
            ),
            f"{label} preamble contains a rejected/unknown/error response",
        )
        _require(
            all(a["line_index"] < b["line_index"] for a, b in zip(preamble, preamble[1:])),
            f"{label} runtime-control preamble order is invalid",
        )
        _require(
            preamble[-1]["monotonic_ms"] <= fixture_timing["settle_monotonic_ms"],
            f"{label} runtime-control preamble was not complete before fixture settle",
        )
        final_preamble_stop = preamble[-1]
        identity["scene_observation"] = _extract_scene_observation(
            lines, actions, final_preamble_stop, f"{label}.pre_pair_scene",
        )
    else:
        _require(identity["runtime_action_monotonic_ms"] > host_timing["host_end_monotonic_ms"], f"{label} post-pair runtime identity was not taken after the buffered window")
        identity["scene_observation"] = _extract_scene_observation(
            lines, actions, _single_action(actions, "runtime_id", label), f"{label}.post_pair_scene",
        )
    if kind == "compact":
        _require(sum(line.startswith("APCAD_SOAK_BEGIN,") for line in lines) == 1, f"{label} requires one compact BEGIN")
        _require(sum(line.startswith("APCAD_SOAK_DONE,") for line in lines) == 1, f"{label} requires one compact DONE")
        soak, worst, metadata = parser.parse_soak_summary(lines)
        metadata.update({
            "mode": "compact_soak_from_raw",
            "status_done": True,
            "vp_perf_stack_hwm_words": parser.parse_vp_perf_stack_hwm(lines),
        })
        canonical = parser.summarise_soak(soak, worst, metadata, 12800, 96, 3)
        _compare_reparse_fields(declared, canonical, COMPACT_REPARSE_FIELDS, label)
        begin_index = next(index for index, line in enumerate(lines) if line.startswith("APCAD_SOAK_BEGIN,"))
        done_index = next(index for index, line in enumerate(lines) if line.startswith("APCAD_SOAK_DONE,"))
    else:
        _require(sum(line.startswith("APCAD_CAPTURE_BEGIN,") for line in lines) == 1, f"{label} requires one buffered BEGIN")
        _require(sum(line.startswith("APCAD_CAPTURE_DONE,") for line in lines) == 1, f"{label} requires one buffered DONE")
        rows, metadata = parser.parse_apcad_rows(lines)
        canonical = parser.summarise_rows(rows, metadata, 12800, 96, 3)
        parser.apply_capture_completion(canonical, True)
        canonical["schema_ver"] = metadata["begin"].get("schema_ver")
        canonical["stage_detail"] = metadata["begin"].get("stage_detail")
        _compare_reparse_fields(declared, canonical, BUFFERED_REPARSE_FIELDS, label)
        begin_index = next(index for index, line in enumerate(lines) if line.startswith("APCAD_CAPTURE_BEGIN,"))
        done_index = next(index for index, line in enumerate(lines) if line.startswith("APCAD_CAPTURE_DONE,"))
    arm_index = _single_action(actions, arm_token, label)["line_index"]
    host_start_index = next(index for index, line in enumerate(lines) if line.startswith("# host_capture_window_start_monotonic_ms="))
    host_end_index = next(index for index, line in enumerate(lines) if line.startswith("# host_capture_window_end_monotonic_ms="))
    measured_end_index = done_index
    forbidden_stream_prefixes = (
        "[AP] ", "APDBG,", "AP_STREAM,", "TEMPO,", "TEMPO_DBG,", "NOV,",
        "[VP] ", "VPF,", "VP_PERF: running", "sbs((agc_debug=",
    )
    _require(
        not any(
            line.startswith(forbidden_stream_prefixes)
            for line in lines[arm_index + 1 : measured_end_index + 1]
        ),
        f"{label} measured evidence contains a forbidden active stream record",
    )
    if kind == "compact":
        status_index = _single_action(actions, "apcad_soak_status=1", label)["line_index"]
        _require(host_start_index < arm_index < begin_index < host_end_index < status_index < done_index, f"{label} compact host/arm/BEGIN/END/status/DONE record order invalid")
        stack_start = _single_action(actions, "vp_perf=start", label)
        stack_stop = [action for action in actions if action["action"] == "vp_perf=stop"][-1]
        stack_lines = [
            index for index, line in enumerate(lines)
            if line.startswith("VP_PERF_STACK_HWM_WORDS:")
            and stack_stop["line_index"] < index < phase_records[3]["line_index"]
        ]
        _require(len(stack_lines) == 1, f"{label} requires exactly one audit-stop stack-HWM response")
        _require(done_index < stack_start["line_index"] < stack_stop["line_index"] < stack_lines[0], f"{label} stack HWM was not measured by post-window vp_perf start/stop")
        _require(
            any(line.startswith("VP_PERF: start budget_us=") for line in _action_response_lines(lines, actions, stack_start)),
            f"{label} vp_perf=start did not return its start acknowledgement",
        )
        _require(
            "VP_PERF: stopped" in _action_response_lines(lines, actions, stack_stop),
            f"{label} post-HWM vp_perf=stop did not prove stopped state",
        )
        _require(len(phase_records) == 4, f"{label} compact raw must contain compact and stack phase boundaries")
        _require(
            phase_records[0]["line_index"] < host_start_index
            and done_index < phase_records[1]["line_index"] < phase_records[2]["line_index"]
            < stack_start["line_index"] < stack_stop["line_index"] < stack_lines[0]
            < phase_records[3]["line_index"],
            f"{label} compact/stack phase markers do not enclose their operations",
        )
        _require(
            [(action["action"], action["phase"]) for action in actions if action["line_index"] >= arm_index]
            == [
                (arm_token, "paired_compact"),
                ("apcad_soak_status=1", "paired_compact"),
                ("vp_perf=start", "paired_stack_hwm"),
                ("vp_perf=stop", "paired_stack_hwm"),
            ],
            f"{label} compact measured/post-window action sequence is not frozen",
        )
    else:
        dump_index = _single_action(actions, "apcad_dump=1", label)["line_index"]
        _require(host_start_index < arm_index < host_end_index < dump_index < begin_index < done_index, f"{label} buffered host/arm/END/dump/BEGIN/DONE record order invalid")
        _require(
            [(action["action"], action["phase"]) for action in actions]
            == [
                (arm_token, "paired_buffered"), ("apcad_dump=1", "paired_buffered"),
                ("show_state", "paired_postflight"), ("secondary_status", "paired_postflight"),
                ("dump", "paired_postflight"), ("runtime_id", "paired_postflight"),
            ],
            f"{label} buffered paired action sequence is not frozen",
        )
        _require(len(phase_records) == 2, f"{label} buffered raw must contain one buffered phase boundary")
        _require(
            phase_records[0]["line_index"] < host_start_index
            and done_index < phase_records[1]["line_index"]
            < _single_action(actions, "show_state", label)["line_index"],
            f"{label} buffered phase markers do not enclose capture/dump",
        )
    return {
        **identity, **fixture_timing, **host_timing, "canonical_summary": canonical,
        "pair_headers": pair_headers, "phase_records": phase_records, "actions": actions,
    }


def _validate_pair_transaction(
    leg: dict[str, Any], base_dir: Path, label: str,
    compact_path: Path, compact_hash: str, compact_summary_path: Path, compact_summary_hash: str,
    buffered_path: Path, buffered_hash: str, buffered_summary_path: Path, buffered_summary_hash: str,
    compact: dict[str, Any], buffered: dict[str, Any], fixture: str,
) -> tuple[Path, str, dict[str, Any]]:
    manifest_path, manifest_hash = _resolve_evidence(leg, "paired_capture_manifest", base_dir, label)
    manifest = _load_json(manifest_path)
    _require(manifest.get("schema_ver") == PAIR_SCHEMA_VERSION, f"{label} paired manifest schema mismatch")
    identifiers = compact["pair_headers"]
    _require(buffered["pair_headers"] == {**identifiers, "phase": "buffered"}, f"{label} raw pair/session/fixture identifiers differ")
    for key in ("pair_id", "serial_session_id", "fixture_session_id"):
        _require(manifest.get(key) == identifiers[key], f"{label} paired manifest {key} mismatch")
    bindings = (
        ("compact_raw", compact_path, compact_hash),
        ("compact_summary", compact_summary_path, compact_summary_hash),
        ("buffered_raw", buffered_path, buffered_hash),
        ("buffered_summary", buffered_summary_path, buffered_summary_hash),
    )
    for prefix, path, digest in bindings:
        declared_path = _resolved_declared_raw_path(manifest.get(f"{prefix}_path"))
        _require(declared_path == path, f"{label} paired manifest {prefix} path mismatch")
        _require(manifest.get(f"{prefix}_sha256") == digest, f"{label} paired manifest {prefix} hash mismatch")
    expected_records = (
        ("paired_compact", "begin"), ("paired_compact", "end"),
        ("paired_stack_hwm", "begin"), ("paired_stack_hwm", "end"),
        ("paired_buffered", "begin"), ("paired_buffered", "end"),
    )
    records = [*compact["phase_records"], *buffered["phase_records"]]
    _require([(item["phase"], item["event"]) for item in records] == list(expected_records), f"{label} paired phase order is invalid")
    _require(
        all(item["pair_id"] == identifiers["pair_id"] and item["serial_session_id"] == identifiers["serial_session_id"] for item in records),
        f"{label} phase records do not share the paired serial session",
    )
    _require(all(a["monotonic_ms"] <= b["monotonic_ms"] for a, b in zip(records, records[1:])), f"{label} paired phase timestamps regress")
    compact_end = compact["host_end_monotonic_ms"]
    buffered_arm_action = _single_action(buffered["actions"], "apcad_capture=5000", label)
    buffered_arm = buffered_arm_action["monotonic_ms"]
    gap = buffered_arm - compact_end
    _require(0 <= gap <= 15000, f"{label} buffered capture did not immediately follow compact capture")
    _require(
        _integer(manifest.get("compact_end_monotonic_ms"), f"{label}.paired.compact_end_monotonic_ms") == compact_end,
        f"{label} paired compact end mismatch",
    )
    _require(
        _integer(
            manifest.get("buffered_host_start_monotonic_ms"),
            f"{label}.paired.buffered_host_start_monotonic_ms",
        ) == buffered["host_start_monotonic_ms"],
        f"{label} paired buffered host start mismatch",
    )
    _require(
        _integer(manifest.get("buffered_arm_monotonic_ms"), f"{label}.paired.buffered_arm_monotonic_ms") == buffered_arm,
        f"{label} paired buffered arm mismatch",
    )
    _require(
        _integer(manifest.get("continuity_gap_ms"), f"{label}.paired.continuity_gap_ms") == gap,
        f"{label} paired continuity gap mismatch",
    )
    compact_status = _single_action(compact["actions"], "apcad_soak_status=1", label)
    stack_start = _single_action(compact["actions"], "vp_perf=start", label)
    stack_stop = [action for action in compact["actions"] if action["action"] == "vp_perf=stop"][-1]
    buffered_dump = _single_action(buffered["actions"], "apcad_dump=1", label)
    post_show = _single_action(buffered["actions"], "show_state", label)
    _require(
        records[0]["monotonic_ms"] <= compact["host_start_monotonic_ms"]
        and records[1]["monotonic_ms"] >= compact_status["monotonic_ms"]
        and records[1]["monotonic_ms"] <= records[2]["monotonic_ms"] <= stack_start["monotonic_ms"]
        and records[3]["monotonic_ms"] >= stack_stop["monotonic_ms"]
        and records[4]["monotonic_ms"] <= buffered["host_start_monotonic_ms"]
        and records[5]["monotonic_ms"] >= buffered_dump["monotonic_ms"]
        and records[5]["monotonic_ms"] <= post_show["monotonic_ms"],
        f"{label} paired phase timestamps are not bounded by their host/action events",
    )
    _require(manifest.get("fixture") == fixture, f"{label} paired fixture mismatch")
    _require(manifest.get("observed_output_device") == compact["observed_output_device"], f"{label} paired output device mismatch")
    expected_player = "ffplay start_ms=0 playback_gain_db=0.0" if fixture == "music" else "<disabled>"
    _require(manifest.get("player") == expected_player, f"{label} paired player mismatch")
    transition_basis = {
        "transition_state": "settled_inferred",
        "transition_max_duration_ms": 3000,
        "minimum_mutation_free_pre_roll_ms": 10000,
        "no_scene_mutation_through_buffered_done": True,
        "device_settled_field_available": False,
    }
    _require(manifest.get("transition_inference_basis") == transition_basis, f"{label} transition inference basis mismatch")
    scene_pre = compact["scene_observation"]
    scene_post = buffered["scene_observation"]
    _require(scene_pre["scene_fields"] == scene_post["scene_fields"], f"{label} scene changed across paired capture")
    _require(manifest.get("scene_pre") == scene_pre, f"{label} paired pre-scene observation mismatch")
    _require(manifest.get("scene_post") == scene_post, f"{label} paired post-scene observation mismatch")
    scene_bytes = json.dumps(
        scene_pre["scene_fields"], sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    scene_status_sha256 = hashlib.sha256(scene_bytes).hexdigest()
    _require(manifest.get("scene_status_sha256") == scene_status_sha256, f"{label} paired scene-status hash mismatch")
    _require(manifest.get("boot_nonce") == compact["boot_nonce"], f"{label} paired boot nonce mismatch")
    _require(compact["boot_nonce"] == buffered["boot_nonce"], f"{label} rebooted within paired capture")
    _require(compact["reset_reason"] == buffered["reset_reason"], f"{label} reset reason changed within paired capture")
    _require(buffered["uptime_ms"] > compact["uptime_ms"], f"{label} runtime uptime did not increase across paired capture")
    return manifest_path, manifest_hash, manifest


def _validate_compact_summary(summary: dict[str, Any], role: str, fixture: str, label: str) -> None:
    detail = 0 if role == "MIN" else 1
    _require(
        _integer(summary.get("schema_ver"), f"{label}.schema_ver") == CAPTURE_SCHEMA_VERSION,
        f"{label} compact schema mismatch",
    )
    _require(_integer(summary.get("stage_detail"), f"{label}.stage_detail") == detail, f"{label} compact detail mode mismatch")
    for key in ("capture_complete", "capture_admissible", "timing_envelope_admissible", "stack_hwm_admissible"):
        _require(summary.get(key) is True, f"{label} compact {key} is not true")
    _require(summary.get("stage_attribution_applicable") is (detail == 1), f"{label} compact applicability mismatch")
    _require(summary.get("compact_soak_mode") is True, f"{label} is not a compact soak")
    _require(_integer(summary.get("duration_ms_requested"), f"{label}.duration_ms_requested") == 120000, f"{label} was not requested for 120 seconds")
    _require(_integer(summary.get("requested_duration_ms_device"), f"{label}.requested_duration_ms_device") == 120000, f"{label} device request was not 120 seconds")
    actual_duration = _integer(summary.get("duration_ms"), f"{label}.duration_ms")
    _require(119000 <= actual_duration <= 121000, f"{label} actual duration is outside the 120-second tolerance")
    row_count = _integer(summary.get("row_count"), f"{label}.row_count")
    _require(6000 <= row_count <= 17000, f"{label} row count cannot represent a complete 120-second AP soak")
    active_sum = _integer(summary.get("active_ap_work_sum_us"), f"{label}.active_ap_work_sum_us")
    active_mean = _number(summary.get("active_ap_work_mean_us"), f"{label}.active_ap_work_mean_us")
    max_consecutive = _integer(
        summary.get("max_consecutive_active_frames_over_7500"),
        f"{label}.max_consecutive_active_frames_over_7500",
    )
    _require(active_sum >= 0 and active_mean >= 0.0, f"{label} active work sum/mean is negative")
    _require(abs(active_mean - active_sum / row_count) <= 0.001, f"{label} active work sum/mean identity fails")
    over_count = _integer(summary.get("active_ap_work_over_7500_count"), f"{label}.active_over_7500")
    _require(
        (over_count == 0 and max_consecutive == 0)
        or (over_count > 0 and 1 <= max_consecutive <= over_count),
        f"{label} consecutive overrun count is invalid",
    )
    for key in ZERO_COMPACT_COUNTS:
        _require(key in summary, f"{label} compact summary is missing counter {key}")
        value = _integer(summary[key], f"{label}.{key}")
        _require(value >= 0, f"{label} compact counter is negative: {key}")
        _require(value == 0, f"{label} compact integrity failure: {key}")
    _require("compact_worst_count_mismatch" in summary, f"{label} compact summary is missing compact_worst_count_mismatch")
    _require(summary.get("compact_worst_count_mismatch") is False, f"{label} worst-row count mismatch")
    saturations = _require_mapping(summary.get("histogram_saturation"), f"{label}.histogram_saturation")
    for metric in METRICS:
        _require(
            _integer(saturations.get(metric), f"{label}.histogram_saturation.{metric}") == 0,
            f"{label} {metric} histogram saturated",
        )
    geometry = _require_mapping(summary.get("histogram_geometry"), f"{label}.histogram_geometry")
    _require(set(geometry) == {"bucket_us", "bucket_count"}, f"{label} histogram geometry mismatch")
    _require(
        _integer(geometry.get("bucket_us"), f"{label}.histogram_geometry.bucket_us") == 32
        and _integer(geometry.get("bucket_count"), f"{label}.histogram_geometry.bucket_count") == 512,
        f"{label} histogram geometry mismatch",
    )
    bounds = _require_mapping(summary.get("p99_bounds_us"), f"{label}.p99_bounds_us")
    percentiles = _require_mapping(summary.get("percentile_bounds_us"), f"{label}.percentile_bounds_us")
    maxima = _require_mapping(summary.get("observed_max_us"), f"{label}.observed_max_us")
    for metric in METRICS:
        interval = _require_mapping(bounds.get(metric), f"{label}.p99_bounds_us.{metric}")
        low = _number(interval.get("low"), f"{label}.{metric}.low")
        high = _number(interval.get("high"), f"{label}.{metric}.high")
        _require(0 <= low < high, f"{label} {metric} p99 interval is invalid")
        metric_percentiles = _require_mapping(percentiles.get(metric), f"{label}.percentile_bounds_us.{metric}")
        ordered_low: list[float] = []
        ordered_high: list[float] = []
        for percentile in ("p50", "p95", "p99"):
            percentile_interval = _require_mapping(metric_percentiles.get(percentile), f"{label}.{metric}.{percentile}")
            p_low = _number(percentile_interval.get("low"), f"{label}.{metric}.{percentile}.low")
            p_high = _number(percentile_interval.get("high"), f"{label}.{metric}.{percentile}.high")
            _require(p_low >= 0 and p_high - p_low == 32 and p_low % 32 == 0, f"{label} {metric} {percentile} is not a 32 us histogram bucket")
            ordered_low.append(p_low)
            ordered_high.append(p_high)
        _require(ordered_low == sorted(ordered_low) and ordered_high == sorted(ordered_high), f"{label} {metric} percentiles regress")
        _require(metric_percentiles["p99"] == interval, f"{label} {metric} p99 surfaces disagree")
        maximum = _number(maxima.get(metric), f"{label}.{metric}.max")
        _require(maximum >= ordered_low[-1], f"{label} {metric} max is below its p99 bucket")
    stack = _require_mapping(summary.get("vp_perf_stack_hwm_words"), f"{label}.vp_perf_stack_hwm_words")
    _require(_integer(stack.get("ap"), f"{label}.stack.ap") >= 512, f"{label} AP stack reserve below 512 words")
    _require(_integer(stack.get("vp"), f"{label}.stack.vp") >= 512, f"{label} VP stack reserve below 512 words")
    _exact_integer_list(summary.get("unique_sample_rate"), [12800], f"{label}.unique_sample_rate")
    _exact_integer_list(summary.get("unique_samples_per_chunk"), [96], f"{label}.unique_samples_per_chunk")
    _require(
        _integer(summary.get("active_tempo_decimation_mode"), f"{label}.active_tempo_decimation_mode") == 3,
        f"{label} novelty decimation mismatch",
    )
    rate = _number(summary.get("measured_ap_frame_rate_hz"), f"{label}.measured_ap_frame_rate_hz")
    derived_rate = 1000.0 * (row_count - 1) / actual_duration
    _require(abs(rate - derived_rate) <= 0.01, f"{label} AP rate/rows/duration identity fails")
    emitted = _integer(summary.get("measured_emitted_novelty_count"), f"{label}.measured_emitted_novelty_count")
    novelty_rate = _number(summary.get("measured_emitted_novelty_rate_hz"), f"{label}.measured_emitted_novelty_rate_hz")
    _require(abs(emitted - row_count / 3.0) <= 2.0, f"{label} novelty count is inconsistent with d3")
    _require(abs(novelty_rate - rate / 3.0) <= 0.2, f"{label} novelty rate is inconsistent with AP/d3")
    actions = _require_list(summary.get("actions"), f"{label}.actions")
    vp_stop_index = actions.index("vp_perf=stop") if "vp_perf=stop" in actions else -1
    arm_indices = [i for i, action in enumerate(actions) if isinstance(action, str) and action.startswith("apcad_soak=")]
    _require(vp_stop_index >= 0 and len(arm_indices) == 1 and vp_stop_index < arm_indices[0], f"{label} does not prove vp_perf stopped before arm")
    if fixture == "music":
        _require(summary.get("track_file") == EXPECTED_MUSIC_PATH, f"{label} track path mismatch")
        _require(summary.get("track_sha256") == EXPECTED_MUSIC_SHA256, f"{label} track SHA mismatch")
        _require(summary.get("player") == "ffplay start_ms=0 playback_gain_db=0.0", f"{label} player mismatch")
        _require(_integer(summary.get("start_ms"), f"{label}.start_ms") == 0, f"{label} playback start mismatch")
        _require(_number(summary.get("playback_gain_db"), f"{label}.playback_gain_db") == 0.0, f"{label} playback gain mismatch")
    else:
        _require(summary.get("track_file") is None, f"{label} unexpectedly has a track")
        _require(summary.get("track_sha256") is None, f"{label} unexpectedly has a track hash")
        _require(summary.get("player") == "<disabled>", f"{label} quiet player marker mismatch")
        _require(_integer(summary.get("start_ms"), f"{label}.start_ms") == 0, f"{label} quiet start_ms mismatch")
        _require(_number(summary.get("playback_gain_db"), f"{label}.playback_gain_db") == 0.0, f"{label} quiet gain mismatch")


def _validate_buffered_summary(summary: dict[str, Any], role: str, label: str) -> None:
    detail = 0 if role == "MIN" else 1
    _require(
        _integer(summary.get("schema_ver"), f"{label}.schema_ver") == CAPTURE_SCHEMA_VERSION,
        f"{label} buffered schema mismatch",
    )
    _require(_integer(summary.get("stage_detail"), f"{label}.stage_detail") == detail, f"{label} buffered detail mismatch")
    for key in ("capture_complete", "capture_admissible", "timing_envelope_admissible"):
        _require(summary.get(key) is True, f"{label} buffered {key} is not true")
    _require(summary.get("stage_attribution_applicable") is (detail == 1), f"{label} buffered applicability mismatch")
    for key in ZERO_BUFFERED_COUNTS:
        _require(key in summary, f"{label} buffered summary is missing counter {key}")
        value = _integer(summary[key], f"{label}.buffered.{key}")
        _require(value >= 0, f"{label} buffered counter is negative: {key}")
        _require(value == 0, f"{label} buffered integrity failure: {key}")
    _require(_integer(summary.get("early_stage_row_count"), f"{label}.early_stage_row_count") == 0, f"{label} buffered capture contains early-stage rows")
    row_count = _integer(summary.get("row_count"), f"{label}.buffered.row_count")
    _require(250 <= row_count <= 750, f"{label} buffered row count cannot represent five seconds")
    duration = _integer(summary.get("duration_ms"), f"{label}.buffered.duration_ms")
    rate = _number(summary.get("measured_ap_frame_rate_hz"), f"{label}.buffered.measured_ap_frame_rate_hz")
    _require(4500 <= duration <= 5500, f"{label} buffered duration is not five seconds")
    _require(abs(rate - 1000.0 * (row_count - 1) / duration) <= 0.05, f"{label} buffered rate/rows/duration identity fails")
    _require(
        _integer(summary.get("full_stage_row_count"), f"{label}.full_stage_row_count") == row_count,
        f"{label} buffered rows are not all full-loop rows",
    )
    if role == "FULL":
        _require(summary.get("stage_attribution_admissible") is True, f"{label} full attribution is inadmissible")
        _require(
            _integer(summary.get("stage_detail_full_row_count"), f"{label}.stage_detail_full_row_count") == row_count,
            f"{label} full detail row count mismatch",
        )
        _require(
            _integer(summary.get("stage_detail_minimal_row_count"), f"{label}.stage_detail_minimal_row_count") == 0,
            f"{label} contains minimal rows",
        )
    else:
        _require(summary.get("stage_attribution_admissible") is False, f"{label} MIN claims full attribution")
        _require(summary.get("perturbation_control_admissible") is True, f"{label} MIN envelope is inadmissible")
        _require(
            _integer(summary.get("stage_detail_minimal_row_count"), f"{label}.stage_detail_minimal_row_count") == row_count,
            f"{label} MIN detail row count mismatch",
        )
        _require(
            _integer(summary.get("control_stage_valid_row_count"), f"{label}.control_stage_valid_row_count") == row_count,
            f"{label} MIN envelope row count mismatch",
        )
    for key, expected in (
        ("unique_sample_rate", [12800]),
        ("unique_samples_per_chunk", [96]),
        ("unique_dma_desc_num", [3]),
        ("unique_dma_frame_num", [96]),
        ("unique_slot_bit_width", [32]),
        ("unique_slot_mode", [2]),
        ("unique_ap_core_id", [0]),
        ("unique_vp_core_id", [1]),
        ("sample_time_assumption_ids", [1]),
    ):
        _exact_integer_list(summary.get(key), expected, f"{label}.buffered.{key}")


def _interval_status(minimum: dict[str, Any], full: dict[str, Any]) -> tuple[str, dict[str, float]]:
    min_low = _number(minimum.get("low"), "minimum interval low")
    min_high = _number(minimum.get("high"), "minimum interval high")
    full_low = _number(full.get("low"), "full interval low")
    full_high = _number(full.get("high"), "full interval high")
    _require(0 < min_low < min_high and 0 <= full_low < full_high, "invalid comparison interval")
    regression_low_pp = 100.0 * (full_low / min_high - 1.0)
    regression_high_pp = 100.0 * (full_high / min_low - 1.0)
    if full_high <= 1.05 * min_low:
        status = "PASS"
    elif full_low > 1.05 * min_high:
        status = "FAIL"
    else:
        status = "INCONCLUSIVE"
    return status, {
        "minimum_low_us": min_low,
        "minimum_high_us": min_high,
        "full_low_us": full_low,
        "full_high_us": full_high,
        "regression_low_pp": regression_low_pp,
        "regression_high_pp": regression_high_pp,
    }


def _repeatability(first: dict[str, float], second: dict[str, float]) -> dict[str, Any]:
    first_low = first["regression_low_pp"]
    first_high = first["regression_high_pp"]
    second_low = second["regression_low_pp"]
    second_high = second["regression_high_pp"]
    minimum_delta_pp = max(0.0, first_low - second_high, second_low - first_high)
    maximum_delta_pp = max(abs(first_low - second_high), abs(first_high - second_low))
    pair_statuses = (first.get("pair_status"), second.get("pair_status"))
    if pair_statuses != ("PASS", "PASS"):
        status = "INCONCLUSIVE"
    elif maximum_delta_pp <= 2.0:
        status = "PASS"
    elif minimum_delta_pp > 2.0:
        status = "FAIL"
    else:
        status = "INCONCLUSIVE"
    return {
        "status": status,
        "admission_limit_pp": 2.0,
        "minimum_possible_delta_pp": minimum_delta_pp,
        "maximum_possible_delta_pp": maximum_delta_pp,
        "method": "conservative regression-interval separation",
    }


def _service_check(
    summary: dict[str, Any],
    contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    limits = service_limits_from_contract(contract)
    p99_limit = float(limits["ap_service_p99_max_us"])
    period_limit = float(limits["ap_arrival_period_us"])
    rate_min = float(limits["measured_ap_rate_min_hz"])
    rate_max = float(limits["measured_ap_rate_max_hz"])
    consecutive_limit = int(limits["ap_max_consecutive_over_period"])
    recovery_limit = int(limits["ap_recovery_hops_max"])

    p99 = _require_mapping(summary["p99_bounds_us"], "service p99 bounds")
    checks: dict[str, dict[str, Any]] = {}
    for metric in ("active_ap_work", "newest_sample_to_ap_publish"):
        interval = _require_mapping(p99[metric], f"service {metric}")
        low = _number(interval["low"], f"service {metric}.low")
        high = _number(interval["high"], f"service {metric}.high")
        status = "PASS" if high <= p99_limit else "FAIL" if low > p99_limit else "INCONCLUSIVE"
        checks[f"{metric}_p99"] = {
            "status": status,
            "limit_us": p99_limit,
            "low_us": low,
            "high_us": high,
        }

    soak = summary.get("compact_soak") if isinstance(summary.get("compact_soak"), dict) else {}
    mean = summary.get("active_ap_work_mean_us", soak.get("active_mean_us"))
    if isinstance(mean, (int, float)) and not isinstance(mean, bool):
        mean_value = _number(mean, "active AP work mean")
        checks["active_ap_work_mean"] = {
            "status": "PASS" if mean_value < period_limit else "FAIL",
            "limit_us": period_limit,
            "value_us": mean_value,
        }
    else:
        checks["active_ap_work_mean"] = {
            "status": "INCOMPLETE",
            "reason": "compact summary does not expose arithmetic mean",
        }

    over_count = _integer(summary.get("active_ap_work_over_7500_count"), "active over period count")
    consecutive = summary.get(
        "max_consecutive_active_frames_over_7500", soak.get("max_consecutive_active_over_7500")
    )
    recovery = summary.get("recovery_hops_after_active_over_7500", soak.get("recovery_hops"))
    if over_count == 0:
        consecutive = 0
        recovery = 0
    if isinstance(consecutive, (int, float)) and not isinstance(consecutive, bool):
        consecutive_value = _integer(consecutive, "max consecutive active frames over period")
        checks["max_consecutive_active_frames_over_7500"] = {
            "status": "PASS" if consecutive_value <= consecutive_limit else "FAIL",
            "limit": consecutive_limit,
            "value": consecutive_value,
        }
    else:
        checks["max_consecutive_active_frames_over_7500"] = {
            "status": "INCOMPLETE",
            "reason": "compact summary does not expose consecutive-run length",
        }
    if isinstance(recovery, (int, float)) and not isinstance(recovery, bool):
        recovery_value = _integer(recovery, "recovery hops")
        checks["recovery_hops"] = {
            "status": "PASS" if recovery_value <= recovery_limit else "FAIL",
            "limit": recovery_limit,
            "value": recovery_value,
        }
    else:
        checks["recovery_hops"] = {
            "status": "INCOMPLETE",
            "reason": "compact summary does not expose recovery hops",
        }

    rate = _number(summary.get("measured_ap_frame_rate_hz"), "measured AP rate")
    checks["measured_ap_rate"] = {
        "status": "PASS" if rate_min <= rate <= rate_max else "FAIL",
        "minimum_hz": rate_min,
        "maximum_hz": rate_max,
        "value_hz": rate,
    }
    return {"status": _worst_status(check["status"] for check in checks.values()), "checks": checks}


def evaluate_series(
    spec_path: Path,
    current_pio_config: Any | None = None,
    current_git_state: dict[str, str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Validate a series spec and return comparison plus expanded manifest."""

    spec_path = spec_path.resolve()
    spec = _load_json(spec_path)
    _require(
        _integer(spec.get("schema_version"), "series.schema_version") == SCHEMA_VERSION,
        "series schema_version mismatch",
    )
    _require(isinstance(spec.get("series_id"), str) and spec["series_id"], "series_id missing")
    evidence_output_root = _validate_evidence_output_root(spec)
    _require(
        spec.get("design_authority_sha") == "781c40a9b5aa20015196c28e054c436a0d9c5fb3",
        "design authority SHA mismatch",
    )
    device = _require_mapping(spec.get("device"), "device")
    _require(device.get("chip_id") == EXPECTED_DEVICE["chip_id"], "wrong device chip ID")
    _require(device.get("usb_serial") == EXPECTED_DEVICE["usb_serial"], "wrong USB serial")
    pio_config, pio_evidence = _validate_pio_config(spec, spec_path.parent, current_pio_config)
    builds = _validate_builds(spec, spec_path.parent, pio_config)
    git_state = _current_git_state() if current_git_state is None else current_git_state
    _require(git_state.get("head") == builds["MIN"]["git_sha"], "current git HEAD differs from captured build source")
    _require(
        _filter_worktree_status(git_state.get("tracked_status", ""), evidence_output_root) == "",
        "current first-party working tree is dirty or contains untracked source",
    )
    fixtures = _validate_fixture_contract(spec)
    runtime_contract = _validate_runtime_contract(spec)
    flash_receipts, expanded_flash_receipts = _validate_flash_receipts(spec, spec_path.parent, builds)
    legs_input = _require_list(spec.get("legs"), "legs")
    _require(len(legs_input) == len(EXPECTED_ORDER), "series must contain exactly eight legs")

    expanded_legs: list[dict[str, Any]] = []
    summaries: dict[tuple[int, str, str], dict[str, Any]] = {}
    role_elf_by_repetition: dict[str, set[str]] = {"MIN": set(), "FULL": set()}
    evidence_paths: set[Path] = set()
    raw_hashes: set[str] = set()
    scene_status_hashes: set[str] = set()
    boot_sessions: dict[str, set[tuple[str, int]]] = {"A1": set(), "B": set(), "A2": set()}
    leg_timings: dict[str, dict[str, Any]] = {}
    for index, (leg_raw, expected) in enumerate(zip(legs_input, EXPECTED_ORDER, strict=True), start=1):
        leg = _require_mapping(leg_raw, f"legs[{index - 1}]")
        expected_id, expected_role, expected_repeat, expected_fixture = expected
        _require(leg.get("id") == expected_id, f"leg {index} ID/order mismatch")
        _require(leg.get("build") == expected_role, f"{expected_id} build role mismatch")
        _require(_integer(leg.get("repetition"), f"{expected_id}.repetition") == expected_repeat, f"{expected_id} repetition mismatch")
        _require(leg.get("fixture") == expected_fixture, f"{expected_id} fixture/order mismatch")
        _require(leg.get("chip_id") == EXPECTED_DEVICE["chip_id"], f"{expected_id} chip ID mismatch")
        _require(leg.get("usb_serial") == EXPECTED_DEVICE["usb_serial"], f"{expected_id} USB serial mismatch")
        observed_port = leg.get("observed_port")
        _require(isinstance(observed_port, str) and observed_port, f"{expected_id} observed port missing")
        _require(leg.get("identity_revalidated_before_flash") is True, f"{expected_id} identity was not revalidated")
        boot_start = leg.get("boot_identity_start")
        _require(isinstance(boot_start, str) and boot_start, f"{expected_id} boot identity missing")
        _require(leg.get("boot_identity_end") == boot_start, f"{expected_id} boot identity changed")
        boot_epoch = _integer(leg.get("boot_epoch_start"), f"{expected_id}.boot_epoch_start")
        boot_epoch_end = _integer(leg.get("boot_epoch_end"), f"{expected_id}.boot_epoch_end")
        _require(boot_epoch == boot_epoch_end, f"{expected_id} reboot/reset discontinuity")
        _require(
            boot_epoch == _integer(builds[expected_role]["build_epoch"], f"{expected_role}.build_epoch"),
            f"{expected_id} boot/build epoch mismatch",
        )
        activities = _require_mapping(leg.get("prohibited_activity"), f"{expected_id}.prohibited_activity")
        for activity in FORBIDDEN_ACTIVITY_FIELDS:
            _require(activities.get(activity) is False, f"{expected_id} prohibited activity: {activity}")

        summary_path, summary_hash = _resolve_evidence(leg, "compact_summary", spec_path.parent, expected_id)
        compact_raw_path, compact_raw_hash = _resolve_evidence(leg, "compact_raw_log", spec_path.parent, expected_id)
        buffered_path, buffered_hash = _resolve_evidence(leg, "buffered_summary", spec_path.parent, expected_id)
        buffered_raw_path, buffered_raw_hash = _resolve_evidence(leg, "buffered_raw_log", spec_path.parent, expected_id)
        for raw_hash in (compact_raw_hash, buffered_raw_hash):
            _require(raw_hash not in raw_hashes, f"{expected_id} reuses raw capture bytes")
            raw_hashes.add(raw_hash)
        for evidence_path in (summary_path, compact_raw_path, buffered_path, buffered_raw_path):
            _require(evidence_path not in evidence_paths, f"{expected_id} reuses evidence path {evidence_path}")
            evidence_paths.add(evidence_path)
        summary = _load_json(summary_path)
        buffered = _load_json(buffered_path)
        _validate_compact_summary(summary, expected_role, expected_fixture, expected_id)
        _validate_buffered_summary(buffered, expected_role, expected_id)
        serial_identity = _require_mapping(summary.get("serial_identity"), f"{expected_id}.serial_identity")
        _require(serial_identity.get("serial_number") == EXPECTED_DEVICE["usb_serial"], f"{expected_id} summary USB serial mismatch")
        _require(summary.get("port") == observed_port, f"{expected_id} summary port mismatch")
        _require(buffered.get("port") == observed_port, f"{expected_id} buffered port mismatch")
        _require(_resolved_declared_raw_path(summary.get("raw_log")) == compact_raw_path, f"{expected_id} compact summary raw path mismatch")
        _require(_resolved_declared_raw_path(buffered.get("raw_log")) == buffered_raw_path, f"{expected_id} buffered summary raw path mismatch")
        compact_raw = _reparse_raw(
            compact_raw_path, summary, builds[expected_role], expected_fixture,
            fixtures[expected_fixture], leg, "compact", f"{expected_id}.compact",
        )
        buffered_raw = _reparse_raw(
            buffered_raw_path, buffered, builds[expected_role], expected_fixture,
            fixtures[expected_fixture], leg, "buffered", f"{expected_id}.buffered",
        )
        if expected_fixture == "music":
            confirmation_time = datetime.fromisoformat(
                fixtures["music"]["captain_audible_confirmation_not_after"]
            )
            for kind, capture in (("compact", compact_raw), ("buffered", buffered_raw)):
                capture_time = datetime.fromisoformat(capture["capture_start"])
                _require(
                    confirmation_time <= capture_time,
                    f"{expected_id} Captain audible confirmation occurs after {kind} capture",
                )
        pair_manifest_path, pair_manifest_hash, pair_manifest = _validate_pair_transaction(
            leg, spec_path.parent, expected_id,
            compact_raw_path, compact_raw_hash, summary_path, summary_hash,
            buffered_raw_path, buffered_raw_hash, buffered_path, buffered_hash,
            compact_raw, buffered_raw, expected_fixture,
        )
        scene_status_hashes.add(pair_manifest["scene_status_sha256"])
        _require(pair_manifest_path not in evidence_paths, f"{expected_id} reuses paired manifest path")
        evidence_paths.add(pair_manifest_path)
        role_elf_by_repetition[expected_role].add(builds[expected_role]["elf_sha256"])
        boot_group = "A1" if expected_id.startswith("A1_") else "A2" if expected_id.startswith("A2_") else "B"
        boot_sessions[boot_group].add((boot_start, leg["boot_epoch_start"]))
        receipt = flash_receipts[boot_group]
        _require(compact_raw["boot_nonce"] == receipt["boot_nonce"], f"{expected_id} raw boot identity differs from flash receipt")
        _require(observed_port == receipt["observed_port"], f"{expected_id} observed port differs from flash receipt")
        _require(compact_raw["host_start_monotonic_ms"] - receipt["flash_completed_monotonic_ms"] >= 60000, f"{expected_id} lacks the 60-second post-flash warm-up")
        leg_timings[expected_id] = {"compact": compact_raw, "buffered": buffered_raw}
        summaries[(expected_repeat, expected_fixture, expected_role)] = summary
        expanded_legs.append(
            {
                "sequence_index": index,
                "id": expected_id,
                "build_role": expected_role,
                "repetition": expected_repeat,
                "fixture": expected_fixture,
                "environment": builds[expected_role]["environment"],
                "git_sha": builds[expected_role]["git_sha"],
                "working_tree_state": builds[expected_role]["working_tree_state"],
                "resolved_build_flags": builds[expected_role]["resolved_build_flags"],
                "elf_path": builds[expected_role]["elf_path"],
                "elf_sha256": builds[expected_role]["elf_sha256"],
                "firmware_version_line": builds[expected_role]["firmware_version_line"],
                "firmware_version": builds[expected_role]["firmware_version"],
                "emitted_git_sha": builds[expected_role]["emitted_git_sha"],
                "schema_ver": CAPTURE_SCHEMA_VERSION,
                "stage_detail": 0 if expected_role == "MIN" else 1,
                "device": {"chip_id": leg["chip_id"], "usb_serial": leg["usb_serial"], "observed_port": observed_port},
                "boot": {"identity": boot_start, "epoch": leg["boot_epoch_start"], "continuous": True},
                "fixture_contract": fixtures[expected_fixture],
                "runtime_contract": runtime_contract,
                "prohibited_activity": activities,
                "capture": {
                    "requested_duration_ms": summary["duration_ms_requested"],
                    "actual_duration_ms": summary["duration_ms"],
                    "rows": summary["row_count"],
                    "emitted_rows": summary.get("measured_emitted_novelty_count"),
                },
                "evidence": {
                    "compact_summary": {"path": str(summary_path), "sha256": summary_hash},
                    "compact_raw_log": {"path": str(compact_raw_path), "sha256": compact_raw_hash},
                    "buffered_summary": {"path": str(buffered_path), "sha256": buffered_hash},
                    "buffered_raw_log": {"path": str(buffered_raw_path), "sha256": buffered_raw_hash},
                    "paired_capture_manifest": {"path": str(pair_manifest_path), "sha256": pair_manifest_hash},
                },
                "paired_capture": pair_manifest,
            }
        )
    _require(all(len(values) == 1 for values in role_elf_by_repetition.values()), "ELF identity changed within a build role")
    _require(len(scene_status_hashes) == 1, "fixed scene/status changed across the A-B-B-A series")
    _require(
        all(len(values) == 1 for values in boot_sessions.values()),
        "boot identity changed within an unreflashed A1, B1/B2, or A2 session",
    )
    _require(
        len({next(iter(values))[0] for values in boot_sessions.values()}) == 3,
        "A1, B and A2 must be three distinct boot identities",
    )
    ordered_starts = [leg_timings[leg_id]["compact"]["host_start_monotonic_ms"] for leg_id, *_ in EXPECTED_ORDER]
    _require(ordered_starts == sorted(ordered_starts) and len(set(ordered_starts)) == 8, "capture chronology does not match A-B-B-A order")
    for (previous_id, *_), (next_id, *__) in zip(EXPECTED_ORDER, EXPECTED_ORDER[1:]):
        _require(
            leg_timings[previous_id]["buffered"]["host_end_monotonic_ms"]
            <= leg_timings[next_id]["compact"]["settle_monotonic_ms"],
            f"capture legs overlap or run out of order at {previous_id}/{next_id}",
        )
    b1_end = max(
        leg_timings[leg_id]["buffered"]["host_end_monotonic_ms"]
        for leg_id in ("B1_music", "B1_no_playback")
    )
    b2_start = min(
        leg_timings[leg_id]["compact"]["host_start_monotonic_ms"]
        for leg_id in ("B2_music", "B2_no_playback")
    )
    _require(b2_start - b1_end >= 60000, "B1-to-B2 wait was shorter than 60 seconds")
    a1_end = max(leg_timings[leg_id]["buffered"]["host_end_monotonic_ms"] for leg_id in ("A1_no_playback", "A1_music"))
    b_end = max(leg_timings[leg_id]["buffered"]["host_end_monotonic_ms"] for leg_id in ("B1_music", "B1_no_playback", "B2_no_playback", "B2_music"))
    _require(a1_end < flash_receipts["B"]["flash_completed_monotonic_ms"] < b2_start, "FULL flash is not between the A1 and B capture sessions")
    _require(b_end < flash_receipts["A2"]["flash_completed_monotonic_ms"] < leg_timings["A2_music"]["compact"]["settle_monotonic_ms"], "final MIN flash is not between B and A2")

    pair_results: dict[str, Any] = {}
    repeat_inputs: dict[tuple[str, str], list[dict[str, float]]] = {}
    pair_statuses: list[str] = []
    for repetition in (1, 2):
        for fixture in ("music", "no_playback"):
            minimum = summaries[(repetition, fixture, "MIN")]
            full = summaries[(repetition, fixture, "FULL")]
            pair_key = f"{fixture}_repeat_{repetition}"
            metric_results: dict[str, Any] = {}
            for metric in METRICS:
                status, detail = _interval_status(
                    minimum["p99_bounds_us"][metric], full["p99_bounds_us"][metric]
                )
                metric_results[metric] = {"status": status, "admission_limit_percent": 5.0, **detail}
                repeat_inputs.setdefault((fixture, metric), []).append(
                    {**detail, "pair_status": status}
                )
                pair_statuses.append(status)
            pair_results[pair_key] = {
                "status": _worst_status(result["status"] for result in metric_results.values()),
                "metrics": metric_results,
            }

    repeatability: dict[str, Any] = {}
    repeat_statuses: list[str] = []
    for fixture in ("music", "no_playback"):
        fixture_result: dict[str, Any] = {}
        for metric in METRICS:
            values = repeat_inputs[(fixture, metric)]
            _require(len(values) == 2, f"missing repetition result for {fixture}/{metric}")
            result = _repeatability(values[0], values[1])
            fixture_result[metric] = result
            repeat_statuses.append(result["status"])
        repeatability[fixture] = fixture_result

    perturbation_status = _worst_status([*pair_statuses, *repeat_statuses])
    service_legs = {
        leg_id: _service_check(summaries[(repeat, fixture, role)])
        for leg_id, role, repeat, fixture in EXPECTED_ORDER
    }
    service_status = _worst_status(result["status"] for result in service_legs.values())
    comparison = {
        "schema_version": SCHEMA_VERSION,
        "series_id": spec["series_id"],
        "evidence_output_root": evidence_output_root,
        "design_authority_sha": spec["design_authority_sha"],
        "source_git_sha": builds["MIN"]["git_sha"],
        "perturbation_verdict": {
            "status": perturbation_status,
            "authorises_stage_instrument_as_evidence": perturbation_status == "PASS",
            "does_not_close_gate_2_or_promote_gdft": True,
        },
        "pairs": pair_results,
        "repeatability": repeatability,
        "service_contract": {
            "status": service_status,
            "separate_from_perturbation_verdict": True,
            "legs": service_legs,
        },
    }
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "series_id": spec["series_id"],
        "design_authority_sha": spec["design_authority_sha"],
        "source_spec": {"path": str(spec_path), "sha256": _sha256(spec_path)},
        "source_git_state": {
            "head": git_state.get("head"),
            "admission_status": _filter_worktree_status(
                git_state.get("tracked_status", ""), evidence_output_root,
            ),
            "exempt_untracked_root": evidence_output_root,
        },
        "device": dict(device),
        "platformio_config": pio_evidence,
        "builds": builds,
        "flash_receipts": expanded_flash_receipts,
        "fixtures": fixtures,
        "runtime_contract": runtime_contract,
        "legs": expanded_legs,
    }
    return comparison, manifest


def write_outputs(
    spec_path: Path,
    comparison_path: Path,
    manifest_path: Path,
    current_pio_config: Any | None = None,
    current_git_state: dict[str, str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Evaluate and atomically-shaped write the two deterministic JSON outputs."""

    comparison, manifest = evaluate_series(
        spec_path,
        current_pio_config=current_pio_config,
        current_git_state=current_git_state,
    )
    comparison_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    comparison_text = json.dumps(comparison, indent=2, sort_keys=True) + "\n"
    comparison_path.write_text(comparison_text, encoding="utf-8")
    manifest["comparison"] = {
        "path": str(comparison_path.resolve()),
        "sha256": hashlib.sha256(comparison_text.encode("utf-8")).hexdigest(),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return comparison, manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("series_spec", type=Path, help="A-B-B-A series specification JSON")
    parser.add_argument("--comparison-out", type=Path, required=True, help="deterministic comparison JSON")
    parser.add_argument("--manifest-out", type=Path, required=True, help="expanded evidence manifest JSON")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        comparison, _manifest = write_outputs(
            args.series_spec, args.comparison_out, args.manifest_out
        )
    except EvidenceError as exc:
        print(json.dumps({"status": "INADMISSIBLE", "reason": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(comparison["perturbation_verdict"], sort_keys=True))
    return 0 if comparison["perturbation_verdict"]["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
