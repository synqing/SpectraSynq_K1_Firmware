"""Gate 2 ratchets for bounded APCAD stage attribution."""

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "regression-harness" / "device_ap_cadence_capture.py"
INO = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "SPECTRASYNQ_K1_FIRMWARE.ino"
TELEMETRY_CPP = (
    ROOT
    / "SPECTRASYNQ_K1_FIRMWARE"
    / "serial"
    / "k1_ap_capture_telemetry.cpp"
)

STAGE_KEYS = (
    "stage_pre_i2s_end_us",
    "stage_i2s_end_us",
    "stage_frontend_end_us",
    "stage_gdft_start_us",
    "stage_gdft_end_us",
    "stage_novelty_start_us",
    "stage_novelty_end_us",
    "stage_snapshot_start_us",
    "stage_snapshot_end_us",
    "stage_onset_end_us",
    "stage_saliency_end_us",
    "stage_tempo_end_us",
    "stage_tail_end_us",
)


def load_capture_module():
    spec = importlib.util.spec_from_file_location("device_ap_cadence_capture_stage", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_stage_row(sequence: int) -> dict[str, object]:
    offsets = [100, 190, 250, 270, 3270, 3340, 3440, 3460, 3740, 4140, 4540, 5640, 5940]
    row: dict[str, object] = {
        "frame": sequence,
        "t": sequence * 8,
        "stage": 0,
        "schema_ver": 2,
        "stage_detail": 1,
        "stage_timing_valid": 1,
        "sample_rate": 12800,
        "samples_per_chunk": 96,
        "tempo_decim": 3,
        "capture_seq": sequence,
        "i2s_read_start_us": 1_000_000,
        "i2s_read_return_us": 1_000_070,
        "oldest_sample_estimate_us": 992_579,
        "newest_sample_estimate_us": 1_000_000,
        "ap_publish_us": 1_005_600,
        "sample_time_assumption_id": 1,
        "i2s_ok": 1,
        "bytes_ok": 1,
        "i2s_status": 0,
        "i2s_us": 70,
        "gdft_us": 3000,
        "novelty_us": 100,
        "total_us": offsets[-1],
        "pre_i2s_service_us": 100,
        "post_i2s_frontend_us": 60,
        "post_gdft_service_us": 70,
        "pre_snapshot_config_us": 20,
        "snapshot_us": 280,
        "onset_us": 400,
        "saliency_us": 400,
        "tempo_total_us": 1100,
        "tempo_pre_timed_us": 100,
        "post_publish_tail_us": 300,
        "tempo_emit_us": 1000,
        "tempo_silence_us": 100,
        "tempo_acf_us": 400,
        "tempo_update_us": 300,
        "tempo_phase_us": 150,
        "tempo_publish_us": 50,
        "emitted": 1,
        "gdft_internal_split_valid": 0,
        "gdft_kernel_us": 0,
        "gdft_post_us": 0,
    }
    assert len(STAGE_KEYS) == len(offsets)
    row.update(dict(zip(STAGE_KEYS, offsets)))
    return row


def capture_metadata(count: int, detail: int = 1) -> dict[str, object]:
    return {
        "begin": {"count": count, "schema_ver": 2, "stage_detail": detail},
        "done": {
            "count": count,
            "dropped": 0,
            "schema_ver": 2,
            "stage_detail": detail,
        },
    }


def test_stage_summary_reports_complete_ordered_attribution_and_visible_gdft_boundary():
    module = load_capture_module()
    rows = [make_stage_row(1), make_stage_row(2)]
    summary = module.summarise_rows(rows, {}, 12800, 96, 3)

    assert summary["stage_timing_row_count"] == 2
    assert summary["stage_timing_missing_count"] == 0
    assert summary["stage_timestamp_order_failure_count"] == 0
    assert summary["stage_tail_total_mismatch_count"] == 0
    assert summary["stage_duration_consistency_failure_count"] == 0
    assert summary["stage_nonempty_failure_count"] == 0
    assert summary["stage_coverage_failure_count"] == 0
    assert summary["gdft_internal_split_available"] is False
    assert summary["timing_us"]["acquire_sample_chunk_total_elapsed_us"]["median"] == 90
    assert summary["timing_us"]["acquire_sample_chunk_non_read_residual_elapsed_us"]["median"] == 20
    assert summary["timing_us"]["pre_gdft_entry_overhead_elapsed_us"]["median"] == 20
    assert summary["timing_us"]["audio_snapshot_elapsed_us"]["median"] == 280
    assert summary["timing_us"]["tempo_pre_timed_history_scale_and_gate_elapsed_us"]["median"] == 100
    assert summary["timing_us"]["post_publication_complete_loop_tail_elapsed_us"]["median"] == 300
    assert summary["timing_us"]["process_GDFT_kernel_elapsed_us"]["median"] is None


def test_missing_or_misordered_stage_spans_fail_closed_after_complete_dump():
    module = load_capture_module()
    missing = make_stage_row(1)
    missing.pop("stage_snapshot_end_us")
    summary = module.summarise_rows(
        [missing], capture_metadata(1), 12800, 96, 3
    )
    module.apply_capture_completion(summary, True)
    assert summary["stage_timing_missing_count"] == 1
    assert summary["capture_complete"] is True
    assert summary["capture_admissible"] is False
    assert summary["classification"] == "F_stage_attribution_invalid"

    misordered = make_stage_row(1)
    misordered["stage_snapshot_end_us"] = 3300
    summary = module.summarise_rows(
        [misordered], capture_metadata(1), 12800, 96, 3
    )
    assert summary["stage_timestamp_order_failure_count"] == 1


def test_missing_duration_or_zero_full_attribution_cannot_pass_as_zero_spans():
    module = load_capture_module()
    missing_duration = make_stage_row(1)
    missing_duration.pop("snapshot_us")
    summary = module.summarise_rows(
        [missing_duration],
        capture_metadata(1),
        12800,
        96,
        3,
    )
    module.apply_capture_completion(summary, True)
    assert summary["stage_duration_missing_count"] == 1
    assert summary["capture_admissible"] is False
    assert summary["classification"] == "F_stage_attribution_invalid"

    zero = make_stage_row(1)
    for key in STAGE_KEYS:
        zero[key] = 0
    for key in module.FULL_STAGE_REQUIRED_SCALAR_KEYS:
        zero[key] = 0
    summary = module.summarise_rows(
        [zero], capture_metadata(1), 12800, 96, 3
    )
    module.apply_capture_completion(summary, True)
    assert summary["stage_nonempty_failure_count"] == 1
    assert summary["capture_admissible"] is False


def test_duration_endpoint_mismatch_fails_but_early_stage_stop_remains_admissible():
    module = load_capture_module()
    mismatch = make_stage_row(1)
    mismatch["snapshot_us"] += 1
    summary = module.summarise_rows(
        [mismatch], capture_metadata(1), 12800, 96, 3
    )
    module.apply_capture_completion(summary, True)
    assert summary["stage_duration_consistency_failure_count"] == 1
    assert summary["capture_admissible"] is False

    impossible_nested_i2s = make_stage_row(1)
    impossible_nested_i2s["i2s_us"] = 91
    summary = module.summarise_rows(
        [impossible_nested_i2s],
        capture_metadata(1),
        12800,
        96,
        3,
    )
    module.apply_capture_completion(summary, True)
    assert summary["stage_duration_consistency_failure_count"] == 1
    assert summary["capture_admissible"] is False

    early = make_stage_row(1)
    early["stage"] = 4
    for key in (*STAGE_KEYS, *module.FULL_STAGE_REQUIRED_SCALAR_KEYS):
        early.pop(key, None)
    early.pop("stage_timing_valid", None)
    summary = module.summarise_rows(
        [early], capture_metadata(1), 12800, 96, 3
    )
    module.apply_capture_completion(summary, True)
    assert summary["full_stage_row_count"] == 0
    assert summary["early_stage_row_count"] == 1
    assert summary["capture_admissible"] is True


def test_explicit_minimal_control_is_admissible_but_mixed_or_implicit_control_fails_closed():
    module = load_capture_module()
    control = make_stage_row(1)
    control["stage_detail"] = 0
    for key in module.DETAIL_ONLY_ZERO_KEYS:
        control[key] = 0

    summary = module.summarise_rows(
        [control], capture_metadata(1, detail=0), 12800, 96, 3
    )
    module.apply_capture_completion(summary, True)
    assert summary["schema_ver"] == 2
    assert summary["stage_detail"] == 0
    assert summary["capture_admissible"] is True
    assert summary["stage_attribution_admissible"] is False
    assert summary["perturbation_control_admissible"] is True
    assert summary["control_stage_valid_row_count"] == 1

    contradictory_done = capture_metadata(1, detail=0)
    contradictory_done["done"]["stage_detail"] = 1
    summary = module.summarise_rows([control], contradictory_done, 12800, 96, 3)
    module.apply_capture_completion(summary, True)
    assert summary["stage_header_mode_mismatch_count"] >= 1
    assert summary["capture_admissible"] is False

    mixed = [make_stage_row(1), dict(control, frame=2)]
    summary = module.summarise_rows(
        mixed, capture_metadata(2), 12800, 96, 3
    )
    module.apply_capture_completion(summary, True)
    assert summary["capture_admissible"] is False

    implicit_control = dict(control)
    implicit_control.pop("schema_ver")
    implicit_control.pop("stage_detail")
    summary = module.summarise_rows(
        [implicit_control],
        capture_metadata(1, detail=0),
        12800,
        96,
        3,
    )
    module.apply_capture_completion(summary, True)
    assert summary["invalid_stage_attribution_mode_count"] == 1
    assert summary["capture_admissible"] is False

    missing_header_mode = make_stage_row(1)
    summary = module.summarise_rows(
        [missing_header_mode],
        {"begin": {"count": 1}, "done": {"count": 1, "dropped": 0}},
        12800,
        96,
        3,
    )
    module.apply_capture_completion(summary, True)
    assert summary["stage_header_mode_mismatch_count"] >= 1
    assert summary["capture_admissible"] is False


def test_compact_soak_requires_schema_mode_bounded_p99_and_zero_saturation():
    module = load_capture_module()
    soak = {
        "schema_ver": 2,
        "stage_detail": 0,
        "active": 0,
        "rows": 16000,
        "emitted": 5333,
        "start_ms": 1000,
        "end_ms": 121000,
        "requested_duration_ms": 120000,
        "first_frame_ms": 1008,
        "last_frame_ms": 121000,
        "observed_duration_ms": 119992,
        "sample_rate": 12800,
        "samples_per_chunk": 96,
        "tempo_decim": 3,
        "hist_bucket_us": 32,
        "hist_bucket_count": 512,
        "meas_ap_hz": 133.33,
        "meas_nov_hz": 44.44,
        "i2s_not_ok": 0,
        "bytes_mismatch": 0,
        "frame_gap": 0,
        "timestamp_regression": 0,
        "core_bad": 0,
        "active_over_7500": 0,
        "emitted_active_over_7500": 0,
        "active_p95_us": 5888,
        "active_max_us": 6200,
        "active_sum_us": 67200000,
        "active_mean_us": 4200.0,
        "max_consecutive_active_over_7500": 0,
        "worst_count": 1,
        "active_ap_work_p99_low_us": 5888,
        "active_ap_work_p99_high_us": 5920,
        "active_ap_work_p50_low_us": 4096,
        "active_ap_work_p50_high_us": 4128,
        "active_ap_work_p95_low_us": 5632,
        "active_ap_work_p95_high_us": 5664,
        "active_ap_work_hist_saturation": 0,
        "active_ap_work_max_us": 6200,
        "newest_sample_to_ap_publish_p99_low_us": 5760,
        "newest_sample_to_ap_publish_p99_high_us": 5792,
        "newest_sample_to_ap_publish_p50_low_us": 3968,
        "newest_sample_to_ap_publish_p50_high_us": 4000,
        "newest_sample_to_ap_publish_p95_low_us": 5504,
        "newest_sample_to_ap_publish_p95_high_us": 5536,
        "newest_sample_to_ap_publish_hist_saturation": 0,
        "newest_sample_to_ap_publish_max_us": 6100,
        "ap_read_return_interval_p99_low_us": 7424,
        "ap_read_return_interval_p99_high_us": 7456,
        "ap_read_return_interval_p50_low_us": 7296,
        "ap_read_return_interval_p50_high_us": 7328,
        "ap_read_return_interval_p95_low_us": 7296,
        "ap_read_return_interval_p95_high_us": 7328,
        "ap_read_return_interval_hist_saturation": 0,
        "ap_read_return_interval_max_us": 7800,
    }
    worst = [{"schema_ver": 2, "stage_detail": 0, "active_us": 6200}]
    complete_metadata = {
        "status_done": True,
        "begin": {
            "schema_ver": 2,
            "stage_detail": 0,
            "duration_ms": 120000,
            "compact": 1,
        },
        "begin_record_count": 1,
        "done_record_count": 1,
        "vp_perf_stack_hwm_words": {"ap": 1024, "vp": 1536},
    }
    summary = module.summarise_soak(soak, worst, complete_metadata, 12800, 96, 3)
    assert summary["capture_admissible"] is True
    assert summary["timing_envelope_admissible"] is True
    assert summary["stage_attribution_applicable"] is False
    assert summary["p99_bounds_us"]["active_ap_work"] == {"low": 5888, "high": 5920}
    assert summary["percentile_bounds_us"]["active_ap_work"]["p50"] == {
        "low": 4096,
        "high": 4128,
    }
    assert summary["observed_max_us"]["ap_read_return_interval"] == 7800
    assert summary["active_ap_work_mean_us"] == 4200.0
    assert summary["max_consecutive_active_frames_over_7500"] == 0

    saturated = dict(soak, active_ap_work_hist_saturation=1)
    summary = module.summarise_soak(
        saturated, worst, complete_metadata, 12800, 96, 3
    )
    assert summary["capture_admissible"] is False
    assert summary["classification"] == "F_compact_timing_contract_invalid"
    assert summary["histogram_saturation"]["active_ap_work"] == 1

    mismatched_begin = {
        **complete_metadata,
        "begin": {**complete_metadata["begin"], "stage_detail": 1},
    }
    summary = module.summarise_soak(soak, worst, mismatched_begin, 12800, 96, 3)
    assert summary["compact_begin_mode_mismatch"] is True
    assert summary["capture_admissible"] is False

    incomplete = module.summarise_soak(
        soak,
        worst,
        {**complete_metadata, "status_done": False},
        12800,
        96,
        3,
    )
    assert incomplete["capture_complete"] is False
    assert incomplete["capture_admissible"] is False

    wrong_worst_count = dict(soak, worst_count=2)
    incomplete = module.summarise_soak(
        wrong_worst_count, worst, complete_metadata, 12800, 96, 3
    )
    assert incomplete["compact_worst_count_mismatch"] is True
    assert incomplete["capture_admissible"] is False

    shallow_stack = module.summarise_soak(
        soak,
        worst,
        {"status_done": True, "vp_perf_stack_hwm_words": {"ap": 511, "vp": 1536}},
        12800,
        96,
        3,
    )
    assert shallow_stack["stack_hwm_admissible"] is False
    assert shallow_stack["capture_admissible"] is False

    assert module.parse_vp_perf_stack_hwm(
        ["noise", "VP_PERF_STACK_HWM_WORDS: ap=900 vp=1200"]
    ) == {"ap": 900, "vp": 1200}

    raw_lines = [
        "APCAD_SOAK_BEGIN,schema_ver=2,stage_detail=0,duration_ms=120000,compact=1",
        "APCAD_SOAK_DONE," + ",".join(f"{key}={value}" for key, value in soak.items()),
        "APCAD_SOAK_WORST,schema_ver=2,stage_detail=0,active_us=6200",
        "VP_PERF_STACK_HWM_WORDS: ap=1024 vp=1536",
    ]
    parsed_soak, parsed_worst, parsed_metadata = module.parse_soak_summary(raw_lines)
    parsed_metadata.update(
        {
            "status_done": any("APCAD_SOAK_DONE," in line for line in raw_lines),
            "vp_perf_stack_hwm_words": module.parse_vp_perf_stack_hwm(raw_lines),
        }
    )
    replay = module.summarise_soak(
        parsed_soak, parsed_worst, parsed_metadata, 12800, 96, 3
    )
    assert replay["capture_admissible"] is True

    duplicate_begin = [raw_lines[0], raw_lines[0], *raw_lines[1:]]
    parsed_soak, parsed_worst, parsed_metadata = module.parse_soak_summary(
        duplicate_begin
    )
    parsed_metadata.update(
        {
            "status_done": True,
            "vp_perf_stack_hwm_words": {"ap": 1024, "vp": 1536},
        }
    )
    duplicate = module.summarise_soak(
        parsed_soak, parsed_worst, parsed_metadata, 12800, 96, 3
    )
    assert duplicate["compact_begin_mode_mismatch"] is True
    assert duplicate["capture_admissible"] is False

    truncated_soak = dict(
        soak,
        last_frame_ms=6008,
        observed_duration_ms=5000,
    )
    truncated = module.summarise_soak(
        truncated_soak, worst, complete_metadata, 12800, 96, 3
    )
    assert truncated["capture_complete"] is False
    assert truncated["capture_admissible"] is False


def test_capture_runner_stops_vp_perf_before_arm_and_samples_stack_after_soak():
    source = SCRIPT.read_text(encoding="utf-8")
    command_sequence = source.index('("vp_perf=stop", 0.4)')
    pre_roll = source.index("raw_lines.extend(read_lines(ser, args.pre_roll_seconds))", command_sequence)
    arm = source.index("send_action(arm_cmd)", pre_roll)
    status = source.index('send_action("apcad_soak_status=1")', arm)
    post_window_start = source.index('send_action("vp_perf=start")', status)
    post_window_stop = source.index('send_action("vp_perf=stop")', post_window_start)
    abort = source.index('send_action("apcad_abort=1")', post_window_stop)
    assert command_sequence < pre_roll < arm < status < post_window_start < post_window_stop < abort


def test_full_endpoint_is_after_optional_loop_service_and_immediately_before_scheduler_wait():
    source = INO.read_text(encoding="utf-8")
    loop_start = source.index("void loop()")
    benchmark = source.index("if (benchmark_running)", loop_start)
    encoders = source.index("check_encoders(t_now)", benchmark)
    debug = source.index("debug_function_timing(t_now)", encoders)
    tail = source.index("ap_cadence_stage_timing.loop_tail_end_us", debug)
    capture = source.index("K1_AP_STAGE_FULL", tail)
    scheduler_wait = source.index("vTaskDelay(1);", capture)
    assert benchmark < encoders < debug < tail < capture < scheduler_wait


def test_timer_reads_are_probe_compiled_and_runtime_guarded_when_capture_is_inactive():
    source = INO.read_text(encoding="utf-8")
    loop_gate = source.index("#if ENABLE_TEMPO_STREAM && ENABLE_AP_FRONTEND_DEBUG", source.index("void loop()"))
    active_decl = source.index("const bool ap_cadence_timing_active = ap_cad_timing_active();", loop_gate)
    first_timer = source.index("esp_timer_get_time()", active_decl)
    guard = source.rfind("if (ap_cadence_timing_active)", active_decl, first_timer)
    assert loop_gate < active_decl < guard < first_timer
    assert "if (!stage_timing.valid) {\n    return;\n  }" not in source
    capture_helper = source[source.index("static void k1_ap_cadence_capture_frame"):source.index("// Loop, runs forever")]
    assert "completed_timing.loop_start_us" in capture_helper
    assert "completed_timing.loop_tail_end_us" in capture_helper


def test_dump_schema_keeps_all_attribution_fields_and_does_not_fabricate_gdft_split():
    source = TELEMETRY_CPP.read_text(encoding="utf-8")
    for field in (
        "pre_i2s_service_us",
        "post_i2s_frontend_us",
        "snapshot_us",
        "onset_us",
        "saliency_us",
        "tempo_total_us",
        "tempo_pre_timed_us",
        "post_publish_tail_us",
        *STAGE_KEYS,
    ):
        assert f'USBSerial.print(",{field}=");' in source
    assert 'USBSerial.print(",gdft_kernel_us=0,gdft_post_us=0");' in source
    assert "sample.gdft_internal_split_valid = 0U;" in source
