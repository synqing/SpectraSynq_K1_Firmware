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
    offsets = [100, 170, 230, 230, 3230, 3300, 3400, 3420, 3700, 4100, 4500, 5600, 5900]
    row: dict[str, object] = {
        "frame": sequence,
        "t": sequence * 8,
        "stage": 0,
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
    assert summary["gdft_internal_split_available"] is False
    assert summary["timing_us"]["audio_snapshot_elapsed_us"]["median"] == 280
    assert summary["timing_us"]["tempo_pre_timed_history_scale_and_gate_elapsed_us"]["median"] == 100
    assert summary["timing_us"]["post_publication_complete_loop_tail_elapsed_us"]["median"] == 300
    assert summary["timing_us"]["process_GDFT_kernel_elapsed_us"]["median"] is None


def test_missing_or_misordered_stage_spans_fail_closed_after_complete_dump():
    module = load_capture_module()
    missing = make_stage_row(1)
    missing.pop("stage_snapshot_end_us")
    summary = module.summarise_rows(
        [missing], {"begin": {"count": 1}, "done": {"count": 1, "dropped": 0}}, 12800, 96, 3
    )
    module.apply_capture_completion(summary, True)
    assert summary["stage_timing_missing_count"] == 1
    assert summary["capture_complete"] is True
    assert summary["capture_admissible"] is False
    assert summary["classification"] == "F_stage_attribution_invalid"

    misordered = make_stage_row(1)
    misordered["stage_snapshot_end_us"] = 3300
    summary = module.summarise_rows(
        [misordered], {"begin": {"count": 1}, "done": {"count": 1, "dropped": 0}}, 12800, 96, 3
    )
    assert summary["stage_timestamp_order_failure_count"] == 1


def test_missing_duration_or_zero_full_attribution_cannot_pass_as_zero_spans():
    module = load_capture_module()
    missing_duration = make_stage_row(1)
    missing_duration.pop("snapshot_us")
    summary = module.summarise_rows(
        [missing_duration],
        {"begin": {"count": 1}, "done": {"count": 1, "dropped": 0}},
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
        [zero], {"begin": {"count": 1}, "done": {"count": 1, "dropped": 0}}, 12800, 96, 3
    )
    module.apply_capture_completion(summary, True)
    assert summary["stage_nonempty_failure_count"] == 1
    assert summary["capture_admissible"] is False


def test_duration_endpoint_mismatch_fails_but_early_stage_stop_remains_admissible():
    module = load_capture_module()
    mismatch = make_stage_row(1)
    mismatch["snapshot_us"] += 1
    summary = module.summarise_rows(
        [mismatch], {"begin": {"count": 1}, "done": {"count": 1, "dropped": 0}}, 12800, 96, 3
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
        [early], {"begin": {"count": 1}, "done": {"count": 1, "dropped": 0}}, 12800, 96, 3
    )
    module.apply_capture_completion(summary, True)
    assert summary["full_stage_row_count"] == 0
    assert summary["early_stage_row_count"] == 1
    assert summary["capture_admissible"] is True


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
    assert "if (!stage_timing.valid) {\n    return;\n  }" in source


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
