"""FRTOS-32 ratchets for the one-variable stage-timing perturbation pair."""

from __future__ import annotations

import json
import hashlib
import importlib.util
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]
PIO = ROOT / "platformio.ini"
IDENTITIES = ROOT / "scripts" / "platformio" / "k1_device_identities.json"
INO = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "SPECTRASYNQ_K1_FIRMWARE.ino"
TELEMETRY_H = (
    ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "serial" / "k1_ap_capture_telemetry.h"
)
TELEMETRY_CPP = (
    ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "serial" / "k1_ap_capture_telemetry.cpp"
)
RUNNER = ROOT / "scripts" / "regression-harness" / "device_ap_cadence_capture.py"
COMPARATOR = (
    ROOT / "scripts" / "regression-harness" / "k1_stage_attribution_abba_compare.py"
)
COMPARATOR_TEST = ROOT / "tests" / "test_k1_stage_attribution_abba_compare.py"

BASELINE = "k1_bench_scheduling_baseline_probe"
MINIMUM = "k1_bench_scheduling_stage_min_probe"
FULL = "k1_bench_scheduling_stage_full_probe"
DETAIL_DEFINE = "K1_AP_STAGE_ATTRIBUTION_DETAIL"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _section(text: str, name: str) -> str:
    start = text.index(f"[env:{name}]")
    end = text.find("\n[env:", start + 1)
    return text[start : end if end >= 0 else len(text)]


def _resolved_envs() -> dict[str, dict[str, object]]:
    result = subprocess.run(
        ["pio", "project", "config", "--json-output"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return {
        name.removeprefix("env:"): dict(options)
        for name, options in json.loads(result.stdout)
        if name.startswith("env:")
    }


def test_resolved_sibling_envs_differ_only_by_the_explicit_detail_value():
    ini = PIO.read_text(encoding="utf-8")
    expected_flags = {
        MINIMUM: f"-D{DETAIL_DEFINE}=0",
        FULL: f"-D{DETAIL_DEFINE}=1",
    }
    for name, expected_flag in expected_flags.items():
        section = _section(ini, name)
        assert "non-shippable" in section.lower()
        assert f"extends = env:{BASELINE}" in section
        assert f"${{env:{BASELINE}.build_flags}}" in section
        added = [line.strip() for line in section.splitlines() if line.strip().startswith("-")]
        assert added == [expected_flag]

    resolved = _resolved_envs()
    baseline = resolved[BASELINE]
    minimum = resolved[MINIMUM]
    full = resolved[FULL]
    baseline_flags = list(baseline["build_flags"])
    assert all(DETAIL_DEFINE not in flag for flag in baseline_flags)
    assert list(minimum["build_flags"]) == baseline_flags + [expected_flags[MINIMUM]]
    assert list(full["build_flags"]) == baseline_flags + [expected_flags[FULL]]
    assert minimum["extends"] == full["extends"] == [f"env:{BASELINE}"]
    assert {
        key: value for key, value in minimum.items() if key != "build_flags"
    } == {
        key: value for key, value in full.items() if key != "build_flags"
    }


def test_pair_is_allowlisted_only_for_the_b489a500_bench():
    manifest = json.loads(IDENTITIES.read_text(encoding="utf-8"))
    pair = {MINIMUM, FULL}
    owners = {
        row["chip_id"]: pair.intersection(row["envs"])
        for row in manifest["authorized"]
    }
    assert owners["B489A500"] == pair
    assert all(not envs for chip_id, envs in owners.items() if chip_id != "B489A500")


def test_minimum_keeps_the_common_envelope_and_full_adds_only_seven_timer_reads():
    source = INO.read_text(encoding="utf-8")
    header = TELEMETRY_H.read_text(encoding="utf-8")
    assert f"#define {DETAIL_DEFINE} 0" in header
    assert f"{DETAIL_DEFINE} != 0 && {DETAIL_DEFINE} != 1" in header

    detail_endpoints = (
        "pre_i2s_end_us",
        "i2s_end_us",
        "post_i2s_frontend_end_us",
        "snapshot_start_us",
        "snapshot_end_us",
        "onset_end_us",
        "saliency_end_us",
    )
    for endpoint in detail_endpoints:
        assignment = f"ap_cadence_stage_timing.{endpoint} = (uint64_t)esp_timer_get_time();"
        position = source.index(assignment)
        gate = source.rfind("#if ", 0, position)
        runtime_guard = source.rfind("if (ap_cadence_timing_active)", gate, position)
        assert DETAIL_DEFINE in source[gate : source.find("\n", gate)]
        assert gate < runtime_guard < position

    common_endpoints = (
        "loop_start_us",
        "gdft_start_us",
        "gdft_end_us",
        "novelty_start_us",
        "novelty_end_us",
        "tempo_end_us",
        "loop_tail_end_us",
    )
    for endpoint in common_endpoints:
        position = source.index(f"ap_cadence_stage_timing.{endpoint} =")
        gate = source.rfind("#if ", 0, position)
        assert DETAIL_DEFINE not in source[gate : source.find("\n", gate)]

    full_tail = source.index("ap_cadence_stage_timing.loop_tail_end_us =")
    capture = source.index("k1_ap_cadence_capture_frame(", full_tail)
    wait = source.index("vTaskDelay(1);", capture)
    assert "K1_AP_STAGE_FULL" in source[capture:wait]
    assert DETAIL_DEFINE not in source[source.rfind("#if ", 0, full_tail):full_tail]
    assert "if (!stage_timing.valid)" not in source


def test_schema_mode_common_scalars_and_vp_perf_exclusion_are_explicit():
    source = TELEMETRY_CPP.read_text(encoding="utf-8")
    assert "sample.stage_detail = timing.detail_enabled ? 1U : 0U;" in source
    assert "sample.stage_timing_valid = timing.valid ? 1U : 0U;" in source

    for marker in (
        '"APCAD_CAPTURE_BEGIN,schema_ver=2,stage_detail="',
        '"APCAD,schema_ver=2,stage_detail="',
        '"APCAD_CAPTURE_DONE,schema_ver=2,stage_detail="',
        '"APCAD_SOAK_BEGIN,schema_ver=2,stage_detail="',
        '"APCAD_SOAK_DONE,schema_ver=2,stage_detail="',
        '"APCAD_SOAK_WORST,schema_ver=2,stage_detail="',
    ):
        assert marker in source

    common_block = source[source.index("if (timing.valid) {") : source.index(
        "if (timing.valid && timing.detail_enabled) {"
    )]
    for field in (
        "post_gdft_service_elapsed_us",
        "post_publish_tail_elapsed_us",
        "stage_gdft_start_offset_us",
        "stage_gdft_end_offset_us",
        "stage_novelty_start_offset_us",
        "stage_novelty_end_offset_us",
        "stage_tempo_end_offset_us",
        "stage_tail_end_offset_us",
    ):
        assert field in common_block

    for function_name in ("ap_cad_capture_arm", "ap_cad_soak_arm"):
        start = source.index(f"bool {function_name}(")
        end = source.index("\n}", start)
        body = source[start:end]
        assert "#if ENABLE_VP_PERF_AUDIT" in body
        assert "vp_perf.running = false;" in body
        assert body.index("vp_perf.running = false;") < body.index("AP_CAD_", body.index("vp_perf.running = false;"))


def test_compact_soak_has_bounded_conservative_p99_surfaces_and_saturation():
    source = TELEMETRY_CPP.read_text(encoding="utf-8")
    header = TELEMETRY_H.read_text(encoding="utf-8")
    assert "#define AP_CAD_SOAK_HIST_BUCKET_US 32UL" in header
    assert "#define AP_CAD_SOAK_HIST_BUCKETS 512" in header
    assert "esp_timer_get_time" not in source
    for histogram in (
        "AP_CAD_SOAK_ACTIVE_HIST",
        "AP_CAD_SOAK_FRESHNESS_HIST",
        "AP_CAD_SOAK_READ_RETURN_INTERVAL_HIST",
    ):
        assert f"{histogram}[AP_CAD_SOAK_HIST_BUCKETS]" in header
        assert f"{histogram}[AP_CAD_SOAK_HIST_BUCKETS]" in source

    assert "*low_us = (uint32_t)i * AP_CAD_SOAK_HIST_BUCKET_US;" in source
    assert "*high_us = ((uint32_t)i + 1UL) * AP_CAD_SOAK_HIST_BUCKET_US;" in source
    for field in (
        "active_ap_work_p50_low_us",
        "active_ap_work_p50_high_us",
        "active_ap_work_p95_low_us",
        "active_ap_work_p95_high_us",
        "active_ap_work_p99_low_us",
        "active_ap_work_p99_high_us",
        "active_ap_work_hist_saturation",
        "active_ap_work_max_us",
        "newest_sample_to_ap_publish_p50_low_us",
        "newest_sample_to_ap_publish_p50_high_us",
        "newest_sample_to_ap_publish_p95_low_us",
        "newest_sample_to_ap_publish_p95_high_us",
        "newest_sample_to_ap_publish_p99_low_us",
        "newest_sample_to_ap_publish_p99_high_us",
        "newest_sample_to_ap_publish_hist_saturation",
        "newest_sample_to_ap_publish_max_us",
        "ap_read_return_interval_p50_low_us",
        "ap_read_return_interval_p50_high_us",
        "ap_read_return_interval_p95_low_us",
        "ap_read_return_interval_p95_high_us",
        "ap_read_return_interval_p99_low_us",
        "ap_read_return_interval_p99_high_us",
        "ap_read_return_interval_hist_saturation",
        "ap_read_return_interval_max_us",
    ):
        assert f'USBSerial.print(",{field}=");' in source


def test_production_env_does_not_enable_or_link_the_probe_surface_by_configuration():
    resolved = _resolved_envs()["k1_hardware"]
    flags = list(resolved["build_flags"])
    assert all(DETAIL_DEFINE not in flag for flag in flags)
    telemetry = TELEMETRY_CPP.read_text(encoding="utf-8")
    first_include = telemetry.index('#include "k1_ap_capture_telemetry.h"')
    feature_gate = telemetry.index("#if ENABLE_TEMPO_STREAM && ENABLE_AP_FRONTEND_DEBUG")
    assert feature_gate < first_include


def test_paired_marker_grammar_is_shared_with_the_fail_closed_comparator():
    runner = _load_module(RUNNER, "apcad_pair_runner_markers")
    comparator = _load_module(COMPARATOR, "apcad_pair_comparator_markers")
    action = runner.paired_action_marker(
        "apcad_soak=120000",
        "paired_compact",
        "pair-abc",
        "serial-def",
        12345,
    )
    match = comparator._ACTION_RE.fullmatch(action)
    assert match is not None
    assert match.groups() == (
        "12345",
        "apcad_soak=120000",
        "paired_compact",
        "pair-abc",
        "serial-def",
    )
    assert runner.paired_host_window_marker(
        "start", 12340, "paired_compact", "pair-abc", "serial-def"
    ) == "# host_capture_window_start_monotonic_ms=12340"


def test_paired_action_contract_has_one_setup_one_fixture_and_no_calibration():
    runner = _load_module(RUNNER, "apcad_pair_runner_contract")
    assert runner.paired_action_contract() == [
        "stop",
        "version",
        "build",
        "image_id",
        "runtime_id",
        "apcad_abort=1",
        "apcad_clear=1",
        "vp_perf=stop",
        "apdbg=off",
        "tempo_stream=off",
        "ap_stream=off",
        "smart_assist=off",
        "beat_director=off",
        "queue_mode=off",
        "show_state",
        "secondary_status",
        "dump",
        "vp_perf=stop",
        "apcad_soak=120000",
        "apcad_soak_status=1",
        "vp_perf=start",
        "vp_perf=stop",
        "apcad_capture=5000",
        "apcad_dump=1",
        "show_state",
        "secondary_status",
        "dump",
        "runtime_id",
        "apcad_abort=1",
        "stop",
    ]
    assert not any("calibr" in action for action in runner.paired_action_contract())
    source = RUNNER.read_text(encoding="utf-8")
    assert source.count("subprocess.Popen(") == 1
    assert source.count("raw_lines.extend(read_lines(ser, args.pre_roll_seconds))") == 1
    assert "start_noise_cal" not in source


def test_paired_headers_bind_both_phases_to_one_serial_and_fixture_session():
    runner = _load_module(RUNNER, "apcad_pair_runner_headers")
    compact = runner.paired_raw_header("pair-a", "serial-a", "fixture-a", "compact")
    buffered = runner.paired_raw_header("pair-a", "serial-a", "fixture-a", "buffered")
    assert compact[:4] == buffered[:4]
    assert compact[4] == "# paired_phase=compact"
    assert buffered[4] == "# paired_phase=buffered"
    assert all(" " not in line.split("=", 1)[1] for line in compact[1:4])
    assert runner.paired_fixture_name(False) == "music"
    assert runner.paired_fixture_name(True) == "no_playback"


def test_hash_helper_and_scene_hash_bind_exact_bytes(tmp_path: Path):
    runner = _load_module(RUNNER, "apcad_pair_runner_hashes")
    payload = b"paired evidence\nwith exact bytes\n"
    evidence = tmp_path / "evidence.log"
    evidence.write_bytes(payload)
    assert runner.sha_file_if_exists(evidence) == hashlib.sha256(payload).hexdigest()
    assert runner.sha_file_if_exists(tmp_path / "missing.log") is None

    scene = {
        "primary_mode": 7,
        "primary_palette": 2,
        "secondary_mode": 9,
        "secondary_palette": 4,
        "secondary_enabled": True,
        "edge_enabled": False,
        "edge_mode": 0,
        "edge_strength": 0.0,
        "master_brightness": 0.5,
        "transition_state": "settled_inferred",
        "transition_max_duration_ms": 3000,
    }
    canonical = json.dumps(scene, sort_keys=True, separators=(",", ":")).encode()
    assert runner.scene_status_digest(scene) == hashlib.sha256(canonical).hexdigest()


def test_scene_parser_uses_real_stripped_transport_and_requires_brightness():
    runner = _load_module(RUNNER, "apcad_pair_runner_scene")
    show = [
        "SHOW_STATE",
        "primary_mode=7 palette=2",
        "secondary_mode=9 palette=4 enabled=on",
        "edge enabled=off mode=0 strength=0.000",
    ]
    secondary = ["SECONDARY_ENABLED: true"]
    dump = ["MASTER_BRIGHTNESS: 0.500000"]
    fields = runner.parse_scene_fields(show, secondary, dump)
    assert fields["primary_mode"] == 7
    assert fields["master_brightness"] == 0.5
    assert fields["transition_state"] == "settled_inferred"
    with pytest.raises(RuntimeError, match="brightness"):
        runner.parse_scene_fields(show, secondary, [])


def test_paired_ffplay_has_no_time_cap_and_early_exit_fails_closed():
    runner = _load_module(RUNNER, "apcad_pair_runner_player")

    class Args:
        player = "ffplay"
        start_ms = 0
        duration_ms = 15000
        playback_gain_db = 0.0

    command = runner.build_playback_command(Args(), Path("fixture.wav"), duration_ms=0)
    assert "-stream_loop" in command
    assert "-t" not in command

    class ExitedPlayer:
        @staticmethod
        def poll():
            return 1

    with pytest.raises(RuntimeError, match="exited during paired buffered window"):
        runner.ensure_player_running(ExitedPlayer(), "buffered window")


def test_paired_control_acknowledgements_and_command_errors_fail_closed():
    runner = _load_module(RUNNER, "apcad_pair_runner_acks")
    for command, acknowledgement in (
        ("apdbg=off", "AP_FRONTEND_DEBUG: off"),
        ("tempo_stream=off", "TEMPO_STREAM: off"),
        ("ap_stream=off", "AP_STREAM: off"),
        ("vp_perf=stop", "VP_PERF: stopped"),
        ("smart_assist=off", "SMART_ASSIST: off"),
        ("beat_director=off", "BEAT_DIRECTOR: off"),
        ("queue_mode=off", "QUEUE_MODE: off"),
    ):
        runner.validate_paired_command_response(command, [acknowledgement])
        with pytest.raises(RuntimeError, match="exact acknowledgement"):
            runner.validate_paired_command_response(command, [])

    with pytest.raises(RuntimeError, match="failed"):
        runner.validate_paired_command_response("apdbg=off", ["BAD COMMAND: apdbg"])
    with pytest.raises(RuntimeError, match="command errors"):
        runner.reject_paired_command_errors(["ERROR: capture arm rejected"])


def test_runner_common_summary_schema_matches_paired_artifact_vocabulary():
    runner = _load_module(RUNNER, "apcad_pair_runner_summary")
    base = {
        "port": "/dev/cu.usbmodem12401",
        "baud": 115200,
        "player": "ffplay",
        "start_ms": 0,
        "playback_gain_db": 0.0,
        "pre_roll_seconds": 10.0,
    }
    scene = {"scene_fields": {"transition_state": "settled_inferred"}}
    music = runner.paired_common_summary_metadata(
        SimpleNamespace(**base, no_playback=False),
        track_file="music.mp3",
        track_sha256="a" * 64,
        serial_identity_value={"serial_number": "B4:3A:45:A5:89:B4"},
        observed_output_device="MacBook Pro Speakers",
        scene_pre=scene,
        scene_post=scene,
        scene_status_sha256="b" * 64,
    )
    assert music["port"] == base["port"]
    assert music["serial_identity"]["serial_number"] == "B4:3A:45:A5:89:B4"
    assert music["player"] == "ffplay start_ms=0 playback_gain_db=0.0"
    assert music["start_ms"] == 0
    assert music["playback_gain_db"] == 0.0

    quiet = runner.paired_common_summary_metadata(
        SimpleNamespace(**base, no_playback=True),
        track_file=None,
        track_sha256=None,
        serial_identity_value={"serial_number": "B4:3A:45:A5:89:B4"},
        observed_output_device="MacBook Pro Speakers",
        scene_pre=scene,
        scene_post=scene,
        scene_status_sha256="b" * 64,
    )
    assert quiet["player"] == "<disabled>"
    assert quiet["track_file"] is None

    full_scene = {
        "show_state_lines": ["SHOW_STATE"],
        "secondary_status_lines": ["SECONDARY_ENABLED: true"],
        "dump_response_sha256": "c" * 64,
        "scene_fields": {"transition_state": "settled_inferred"},
    }
    manifest_fields = runner.paired_manifest_runtime_fields(
        full_scene,
        full_scene,
        "d" * 64,
        [{"boot_nonce": "1" * 16, "uptime_ms": 1, "reset_reason": 1}],
    )
    assert manifest_fields["transition_inference_basis"] == {
        "transition_state": "settled_inferred",
        "transition_max_duration_ms": 3000,
        "minimum_mutation_free_pre_roll_ms": 10000,
        "no_scene_mutation_through_buffered_done": True,
        "device_settled_field_available": False,
    }
    assert (
        manifest_fields["runtime_contract"]["transition_inference_basis"]
        == manifest_fields["transition_inference_basis"]
    )


def test_runner_shaped_summary_metadata_passes_comparator_contract(tmp_path: Path):
    runner = _load_module(RUNNER, "apcad_pair_runner_integration")
    comparator = _load_module(COMPARATOR, "apcad_pair_comparator_integration")
    fixtures = _load_module(COMPARATOR_TEST, "apcad_pair_comparator_fixtures")
    spec_path, _ = fixtures.make_pack(tmp_path)
    spec = json.loads(spec_path.read_text(encoding="utf-8"))

    for leg in spec["legs"][:2]:
        fixture = leg["fixture"]
        compact_path = tmp_path / leg["compact_summary_path"]
        buffered_path = tmp_path / leg["buffered_summary_path"]
        compact_raw_path = tmp_path / leg["compact_raw_log_path"]
        buffered_raw_path = tmp_path / leg["buffered_raw_log_path"]
        manifest_path = tmp_path / leg["paired_capture_manifest_path"]
        compact = json.loads(compact_path.read_text(encoding="utf-8"))
        buffered = json.loads(buffered_path.read_text(encoding="utf-8"))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        no_playback = fixture == "no_playback"
        args = SimpleNamespace(
            port=compact["port"],
            baud=115200,
            player="ffplay",
            start_ms=0,
            playback_gain_db=0.0,
            pre_roll_seconds=10.0,
            no_playback=no_playback,
        )
        common = runner.paired_common_summary_metadata(
            args,
            track_file=None if no_playback else comparator.EXPECTED_MUSIC_PATH,
            track_sha256=None if no_playback else comparator.EXPECTED_MUSIC_SHA256,
            serial_identity_value=compact["serial_identity"],
            observed_output_device=manifest["observed_output_device"],
            scene_pre=manifest["scene_pre"],
            scene_post=manifest["scene_post"],
            scene_status_sha256=manifest["scene_status_sha256"],
        )
        compact.update(common)
        compact["actions"] = runner.paired_action_tokens(
            compact_raw_path.read_text(encoding="utf-8").splitlines()
        )
        buffered.update(common)
        buffered["actions"] = runner.paired_action_tokens(
            buffered_raw_path.read_text(encoding="utf-8").splitlines()
        )
        comparator._validate_compact_summary(compact, "MIN", fixture, leg["id"])
        comparator._validate_buffered_summary(buffered, "MIN", leg["id"])
