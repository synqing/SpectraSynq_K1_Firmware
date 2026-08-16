"""Adversarial tests for the Gate-2 stage-attribution A-B-B-A comparator."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "regression-harness" / "k1_stage_attribution_abba_compare.py"
PARSER_PATH = ROOT / "scripts" / "regression-harness" / "device_ap_cadence_capture.py"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


abba = _load(MODULE_PATH, "k1_stage_attribution_abba_compare")
capture = _load(PARSER_PATH, "k1_stage_attribution_capture_parser")
_resolve_live_git_state = abba._current_git_state
_LIVE_GIT = _resolve_live_git_state()
GIT_STATE = {"head": _LIVE_GIT["head"], "tracked_status": ""}
abba._current_git_state = lambda: dict(GIT_STATE)
EMITTED_GIT = GIT_STATE["head"][:8]
FORGED_GIT = "ffffffff" if EMITTED_GIT != "ffffffff" else "00000000"


def _write(path: Path, value: object) -> str:
    if isinstance(value, (dict, list)):
        path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    else:
        path.write_text(str(value), encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _action(timestamp_ms: int, command: str, phase: str, pair_id: str, serial_session_id: str) -> str:
    helper = getattr(capture, "paired_action_marker", None)
    if helper is not None:
        return helper(command, phase, pair_id, serial_session_id, timestamp_ms)
    return (
        f"# action_ts_monotonic_ms={timestamp_ms} action={command} phase={phase} "
        f"pair_id={pair_id} serial_session_id={serial_session_id}"
    )


def _show_state_lines() -> list[str]:
    return [
        "SHOW_STATE", "primary_mode=1 palette=2",
        "secondary_mode=3 palette=2 enabled=on",
        "edge enabled=off mode=0 strength=0.000",
    ]


def _secondary_status_lines() -> list[str]:
    return [
        "SECONDARY_ENABLED: true",
        "SECONDARY_CONTROL: false (encoders control primary channel)",
        "SECONDARY_MODE: 3 (test)",
        "SECONDARY_PHOTONS: 0.500000",
        "SECONDARY_CHROMA: 0.500000",
        "SECONDARY_MOOD: 0.500000",
        "SECONDARY_SATURATION: 0.500000",
        "SECONDARY_PRISM_COUNT: 1.00",
        "SECONDARY_MIRROR_ENABLED: false",
        "SECONDARY_REVERSE_ORDER: false",
        "SECONDARY_BASE_COAT: false",
        "SECONDARY_PALETTE_MODE_ENABLED: true",
        "SECONDARY_PALETTE_INDEX: 2 (test)",
        "NOTE: This command is deprecated, please use secondary_status instead",
    ]


def _dump_lines() -> list[str]:
    return ["CONFIG.SAMPLE_RATE: 12800", "MASTER_BRIGHTNESS: 0.75", "stream_audio: 0"]


def _pio_snapshot() -> list[list[object]]:
    common = {
        "upload_speed": 460800,
        "build_src_filter": ["+<firmware>"],
        "build_unflags": ["-DARDUINO_RUNNING_CORE=1"],
        "platform": "pioarduino-54.03.20",
        "lib_deps": ["fastled/FastLED@3.10.3", "file://libraries/FixedPoints", "file://libraries/M5ROTATE8"],
    }
    rows = []
    for env, parent, flags in (
        (abba.BASE_ENV, "env:k1_bench_im69d", list(abba.EXACT_BASE_FLAGS)),
        (abba.MIN_ENV, f"env:{abba.BASE_ENV}", [*abba.EXACT_BASE_FLAGS, abba.DETAIL_FLAGS["MIN"]]),
        (abba.FULL_ENV, f"env:{abba.BASE_ENV}", [*abba.EXACT_BASE_FLAGS, abba.DETAIL_FLAGS["FULL"]]),
    ):
        rows.append([f"env:{env}", [["extends", [parent]], ["build_flags", flags], *[[key, value] for key, value in common.items()]]])
    return rows


def _base_headers(
    port: str, fixture: str, output: str, pair_id: str, serial_session_id: str,
    fixture_session_id: str, phase: str,
) -> list[str]:
    music = fixture == "music"
    return [
        "# capture_start=2026-08-16T04:00:00+08:00",
        f"# port={port} baud=115200 duration_ms={'120000' if phase == 'compact' else '5000'}",
        f"# track={abba.EXPECTED_MUSIC_PATH if music else '<none>'}",
        f"# track_sha256={abba.EXPECTED_MUSIC_SHA256 if music else 'None'}",
        "# player=ffplay start_ms=0 playback_gain_db=0.0" if music else "# player=<disabled>",
        "# pre_roll_seconds=10.0",
        f"# observed_output_device={output}",
        '# serial_identity={"serial_number": "B4:3A:45:A5:89:B4"}',
        f"# paired_capture_schema={abba.PAIR_SCHEMA_VERSION}",
        f"# pair_id={pair_id}",
        f"# serial_session_id={serial_session_id}",
        f"# fixture_session_id={fixture_session_id}",
        f"# paired_phase={phase}",
    ]


def _identity_lines(
    start_ms: int, env: str, git_sha: str, epoch: int, elf_sha: str, nonce: str,
    uptime_ms: int, pair_id: str, serial_session_id: str,
) -> list[str]:
    return [
        _action(start_ms - 20000, "stop", "paired_setup", pair_id, serial_session_id),
        _action(start_ms - 19800, "version", "paired_setup", pair_id, serial_session_id),
        "VERSION: 40103",
        _action(start_ms - 19600, "build", "paired_setup", pair_id, serial_session_id),
        f"BUILD: version=40103 git={git_sha[:8]} epoch={epoch} env={env}",
        _action(start_ms - 19400, "image_id", "paired_setup", pair_id, serial_session_id),
        f"IMAGE_ID: app_elf_sha256={elf_sha}",
        _action(start_ms - 19200, "runtime_id", "paired_setup", pair_id, serial_session_id),
        f"RUNTIME_ID: boot_nonce={nonce} uptime_ms={uptime_ms} reset_reason=1",
        _action(start_ms - 19000, "apcad_abort=1", "paired_setup", pair_id, serial_session_id),
        _action(start_ms - 18800, "apcad_clear=1", "paired_setup", pair_id, serial_session_id),
        _action(start_ms - 18600, "vp_perf=stop", "paired_setup", pair_id, serial_session_id),
        "VP_PERF: stopped",
        _action(start_ms - 18400, "apdbg=off", "paired_setup", pair_id, serial_session_id),
        "AP_FRONTEND_DEBUG: off",
        _action(start_ms - 18200, "tempo_stream=off", "paired_setup", pair_id, serial_session_id),
        "TEMPO_STREAM: off",
        _action(start_ms - 18000, "ap_stream=off", "paired_setup", pair_id, serial_session_id),
        "AP_STREAM: off",
        _action(start_ms - 17800, "smart_assist=off", "paired_setup", pair_id, serial_session_id),
        "SMART_ASSIST: off",
        _action(start_ms - 17600, "beat_director=off", "paired_setup", pair_id, serial_session_id),
        "BEAT_DIRECTOR: off",
        _action(start_ms - 17400, "queue_mode=off", "paired_setup", pair_id, serial_session_id),
        "QUEUE_MODE: off",
        _action(start_ms - 17200, "show_state", "paired_setup", pair_id, serial_session_id),
        *_show_state_lines(),
        _action(start_ms - 17000, "secondary_status", "paired_setup", pair_id, serial_session_id),
        *_secondary_status_lines(),
        _action(start_ms - 16800, "dump", "paired_setup", pair_id, serial_session_id),
        *_dump_lines(),
        _action(start_ms - 10500, "vp_perf=stop", "paired_setup", pair_id, serial_session_id),
        "VP_PERF: stopped",
    ]


def _metric_fields(prefix: str, p99: tuple[int, int]) -> dict[str, int]:
    return {
        f"{prefix}_p50_low_us": p99[0] - 160,
        f"{prefix}_p50_high_us": p99[0] - 128,
        f"{prefix}_p95_low_us": p99[0] - 64,
        f"{prefix}_p95_high_us": p99[0] - 32,
        f"{prefix}_p99_low_us": p99[0],
        f"{prefix}_p99_high_us": p99[1],
        f"{prefix}_hist_saturation": 0,
        f"{prefix}_max_us": p99[1] + 32,
    }


def _kv_line(prefix: str, values: dict[str, object]) -> str:
    return prefix + "," + ",".join(f"{key}={value}" for key, value in values.items())


def _compact_raw(
    path: Path,
    fixture: str,
    role: str,
    start_ms: int,
    env: str,
    git_sha: str,
    epoch: int,
    elf_sha: str,
    nonce: str,
    port: str,
    output: str,
    pair_id: str,
    serial_session_id: str,
    fixture_session_id: str,
    active_p99: tuple[int, int] = (4960, 4992),
) -> dict:
    detail = 0 if role == "MIN" else 1
    lines = _base_headers(
        port, fixture, output, pair_id, serial_session_id, fixture_session_id, "compact",
    )
    lines.extend(_identity_lines(
        start_ms, env, git_sha, epoch, elf_sha, nonce, 70000, pair_id, serial_session_id,
    ))
    settle = "playback_start" if fixture == "music" else "quiet_settle_start"
    lines.extend(
        [
            _action(start_ms - 10000, settle, "paired_setup", pair_id, serial_session_id),
            capture.paired_phase_marker("paired_compact", "begin", pair_id, serial_session_id, start_ms - 1),
            capture.paired_host_window_marker("start", start_ms, "paired_compact", pair_id, serial_session_id),
            _action(start_ms, "apcad_soak=120000", "paired_compact", pair_id, serial_session_id),
            f"APCAD_SOAK_BEGIN,schema_ver=2,stage_detail={detail},duration_ms=120000,compact=1",
            capture.paired_host_window_marker("end", start_ms + 120000, "paired_compact", pair_id, serial_session_id),
            _action(start_ms + 120100, "apcad_soak_status=1", "paired_compact", pair_id, serial_session_id),
        ]
    )
    done: dict[str, object] = {
        "schema_ver": 2,
        "stage_detail": detail,
        "active": 0,
        "rows": 12001,
        "emitted": 4000,
        "requested_duration_ms": 120000,
        "first_frame_ms": 1000,
        "last_frame_ms": 121000,
        "observed_duration_ms": 120000,
        "sample_rate": 12800,
        "samples_per_chunk": 96,
        "tempo_decim": 3,
        "meas_ap_hz": 100.0,
        "meas_nov_hz": 33.333,
        "i2s_not_ok": 0,
        "bytes_mismatch": 0,
        "frame_gap": 0,
        "timestamp_regression": 0,
        "core_bad": 0,
        "active_over_7500": 0,
        "emitted_active_over_7500": 0,
        "active_sum_us": 57604800,
        "active_mean_us": 4800.0,
        "max_consecutive_active_over_7500": 0,
        "active_p95_us": active_p99[0] - 32,
        "hist_bucket_us": 32,
        "hist_bucket_count": 512,
        **_metric_fields("active_ap_work", active_p99),
        **_metric_fields("newest_sample_to_ap_publish", (4608, 4640)),
        **_metric_fields("ap_read_return_interval", (9984, 10016)),
        "active_max_us": active_p99[1] + 32,
        "worst_count": 0,
    }
    lines.append(_kv_line("APCAD_SOAK_DONE", done))
    lines.extend(
        [
            capture.paired_phase_marker("paired_compact", "end", pair_id, serial_session_id, start_ms + 120200),
            capture.paired_phase_marker("paired_stack_hwm", "begin", pair_id, serial_session_id, start_ms + 120300),
            _action(start_ms + 120310, "vp_perf=start", "paired_stack_hwm", pair_id, serial_session_id),
            "VP_PERF: start budget_us=10000 render_budget_us=2000",
            _action(start_ms + 120400, "vp_perf=stop", "paired_stack_hwm", pair_id, serial_session_id),
            "VP_PERF: stopped",
            "VP_PERF_STACK_HWM_WORDS: ap=1024 vp=1536",
            capture.paired_phase_marker("paired_stack_hwm", "end", pair_id, serial_session_id, start_ms + 120500),
        ]
    )
    _write(path, "\n".join(lines) + "\n")
    soak, worst, metadata = capture.parse_soak_summary(lines)
    metadata.update({"status_done": True, "vp_perf_stack_hwm_words": capture.parse_vp_perf_stack_hwm(lines)})
    summary = capture.summarise_soak(soak, worst, metadata, 12800, 96, 3)
    summary.update(
        {
            "duration_ms_requested": 120000,
            "compact_soak_mode": True,
            "track_file": abba.EXPECTED_MUSIC_PATH if fixture == "music" else None,
            "track_sha256": abba.EXPECTED_MUSIC_SHA256 if fixture == "music" else None,
            "player": "ffplay start_ms=0 playback_gain_db=0.0" if fixture == "music" else "<disabled>",
            "start_ms": 0,
            "playback_gain_db": 0.0,
            "port": port,
            "serial_identity": {"serial_number": abba.EXPECTED_DEVICE["usb_serial"]},
            "actions": ["vp_perf=stop", "apcad_soak=120000"],
            "raw_log": str(path.resolve()),
        }
    )
    return summary


def _stage_row(sequence: int, detail: int) -> dict[str, object]:
    offsets = [100, 190, 250, 270, 3270, 3340, 3440, 3460, 3740, 4140, 4540, 5640, 5940]
    keys = (
        "stage_pre_i2s_end_us", "stage_i2s_end_us", "stage_frontend_end_us",
        "stage_gdft_start_us", "stage_gdft_end_us", "stage_novelty_start_us",
        "stage_novelty_end_us", "stage_snapshot_start_us", "stage_snapshot_end_us",
        "stage_onset_end_us", "stage_saliency_end_us", "stage_tempo_end_us", "stage_tail_end_us",
    )
    base_us = 1_000_000 + sequence * 10_000
    emitted = sequence % 3 == 0
    row: dict[str, object] = {
        "src": "buf", "frame": sequence, "t": sequence * 10, "stage": 0, "schema_ver": 2,
        "stage_detail": detail, "stage_timing_valid": 1, "sample_rate": 12800,
        "samples_per_chunk": 96, "tempo_decim": 3, "capture_seq": sequence,
        "i2s_read_start_us": base_us, "i2s_read_return_us": base_us + 70,
        "oldest_sample_estimate_us": base_us - 7421, "newest_sample_estimate_us": base_us,
        "ap_publish_us": base_us + 5600, "sample_time_assumption_id": 1,
        "i2s_ok": 1, "bytes_ok": 1, "i2s_status": 0, "i2s_us": 70,
        "gdft_us": 3000, "novelty_us": 100, "total_us": offsets[-1],
        "pre_i2s_service_us": 100, "post_i2s_frontend_us": 60, "post_gdft_service_us": 70,
        "pre_snapshot_config_us": 20, "snapshot_us": 280, "onset_us": 400,
        "saliency_us": 400, "tempo_total_us": 1100, "tempo_pre_timed_us": 100 if emitted else 0,
        "post_publish_tail_us": 300, "tempo_emit_us": 1000 if emitted else 0,
        "tempo_silence_us": 100 if emitted else 0, "tempo_acf_us": 400 if emitted else 0,
        "tempo_update_us": 300 if emitted else 0, "tempo_phase_us": 150 if emitted else 0,
        "tempo_publish_us": 50 if emitted else 0, "emitted": 1 if emitted else 0,
        "gdft_internal_split_valid": 0, "gdft_kernel_us": 0, "gdft_post_us": 0,
        "dma_desc": 3, "dma_frame": 96, "slot_bits": 32, "slot_mode": 2,
        "ap_core": 0, "vp_core": 1,
    }
    row.update(dict(zip(keys, offsets)))
    if detail == 0:
        for key in capture.DETAIL_ONLY_ZERO_KEYS:
            row[key] = 0
    return row


def _buffered_raw(
    path: Path,
    fixture: str,
    role: str,
    start_ms: int,
    env: str,
    git_sha: str,
    epoch: int,
    elf_sha: str,
    nonce: str,
    port: str,
    output: str,
    pair_id: str,
    serial_session_id: str,
    fixture_session_id: str,
) -> dict:
    detail = 0 if role == "MIN" else 1
    lines = _base_headers(
        port, fixture, output, pair_id, serial_session_id, fixture_session_id, "buffered",
    )
    lines.extend(
        [
            capture.paired_phase_marker("paired_buffered", "begin", pair_id, serial_session_id, start_ms - 1),
            capture.paired_host_window_marker("start", start_ms, "paired_buffered", pair_id, serial_session_id),
            _action(start_ms, "apcad_capture=5000", "paired_buffered", pair_id, serial_session_id),
            capture.paired_host_window_marker("end", start_ms + 5000, "paired_buffered", pair_id, serial_session_id),
            _action(start_ms + 5100, "apcad_dump=1", "paired_buffered", pair_id, serial_session_id),
            f"APCAD_CAPTURE_BEGIN,schema_ver=2,stage_detail={detail},count=500,capacity=2304,start_ms=1000,end_ms=6000,dropped=0",
        ]
    )
    rows = [_stage_row(index, detail) for index in range(1, 501)]
    lines.extend(_kv_line("APCAD", row) for row in rows)
    lines.extend(
        [
            f"APCAD_CAPTURE_DONE,schema_ver=2,stage_detail={detail},count=500,dropped=0",
            capture.paired_phase_marker("paired_buffered", "end", pair_id, serial_session_id, start_ms + 5200),
            _action(start_ms + 5300, "show_state", "paired_postflight", pair_id, serial_session_id),
            *_show_state_lines(),
            _action(start_ms + 5400, "secondary_status", "paired_postflight", pair_id, serial_session_id),
            *_secondary_status_lines(),
            _action(start_ms + 5500, "dump", "paired_postflight", pair_id, serial_session_id),
            *_dump_lines(),
            _action(start_ms + 5600, "runtime_id", "paired_postflight", pair_id, serial_session_id),
            f"RUNTIME_ID: boot_nonce={nonce} uptime_ms=198000 reset_reason=1",
        ]
    )
    _write(path, "\n".join(lines) + "\n")
    parsed_rows, metadata = capture.parse_apcad_rows(lines)
    summary = capture.summarise_rows(parsed_rows, metadata, 12800, 96, 3)
    capture.apply_capture_completion(summary, True)
    summary["schema_ver"] = metadata["begin"]["schema_ver"]
    summary["stage_detail"] = metadata["begin"]["stage_detail"]
    summary.update(
        {
            "port": port,
            "track_file": abba.EXPECTED_MUSIC_PATH if fixture == "music" else None,
            "track_sha256": abba.EXPECTED_MUSIC_SHA256 if fixture == "music" else None,
            "player": "ffplay" if fixture == "music" else None,
            "start_ms": 0,
            "playback_gain_db": 0.0,
            "raw_log": str(path.resolve()),
        }
    )
    return summary


def make_pack(tmp_path: Path) -> tuple[Path, list[list[object]]]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    pio = _pio_snapshot()
    pio_path = tmp_path / "pio-config.json"
    pio_hash = _write(pio_path, pio)
    git_sha = GIT_STATE["head"]
    output = "MacBook Pro Speakers"
    port = "/dev/cu.usbmodem12401"
    builds: dict[str, dict[str, object]] = {}
    for role, env, detail, epoch in (("MIN", abba.MIN_ENV, 0, 1786800001), ("FULL", abba.FULL_ENV, 1, 1786800002)):
        elf = tmp_path / f"{role.lower()}.elf"
        elf_hash = _write(elf, f"ELF {role}")
        builds[role] = {
            "environment": env, "stage_detail": detail, "schema_ver": 2,
            "working_tree_state": "clean", "git_sha": git_sha, "build_epoch": epoch,
            "resolved_build_flags": [*abba.EXACT_BASE_FLAGS, abba.DETAIL_FLAGS[role]],
            "elf_path": elf.name, "elf_sha256": elf_hash,
            "firmware_version": "40103", "emitted_git_sha": git_sha[:8],
            "firmware_version_line": "VERSION: 40103",
        }

    sessions = {
        "A1": {"role": "MIN", "nonce": "1111111111111111", "flash_ms": 100000},
        "B": {"role": "FULL", "nonce": "2222222222222222", "flash_ms": 500000},
        "A2": {"role": "MIN", "nonce": "3333333333333333", "flash_ms": 1230000},
    }
    flash_receipts = []
    receipt_timestamps = {"A1": "2026-08-16T04:00:00+08:00", "B": "2026-08-16T04:10:00+08:00", "A2": "2026-08-16T04:20:00+08:00"}
    for name in ("A1", "B", "A2"):
        session = sessions[name]
        build = builds[session["role"]]
        receipt = {
            "session": name, "build": session["role"], "chip_id": abba.EXPECTED_DEVICE["chip_id"],
            "usb_serial": abba.EXPECTED_DEVICE["usb_serial"], "observed_port": port,
            "port_rediscovered": True, "identity_guard_pass": True, "boot_nonce": session["nonce"],
            "git_sha": git_sha, "environment": build["environment"], "build_epoch": build["build_epoch"],
            "elf_sha256": build["elf_sha256"], "timestamp": receipt_timestamps[name],
            "flash_completed_monotonic_ms": session["flash_ms"],
        }
        receipt_path = tmp_path / f"flash-{name}.json"
        receipt_hash = _write(receipt_path, receipt)
        flash_receipts.append({"receipt_path": receipt_path.name, "receipt_sha256": receipt_hash})

    # Includes the mandatory B1-to-B2 wait and three post-flash warm-ups.
    starts = [170000, 320000, 570000, 720000, 920000, 1070000, 1300000, 1450000]
    legs = []
    for (leg_id, role, repetition, fixture), start_ms in zip(abba.EXPECTED_ORDER, starts, strict=True):
        group = "A1" if leg_id.startswith("A1_") else "A2" if leg_id.startswith("A2_") else "B"
        build = builds[role]
        compact_raw_path = tmp_path / f"{leg_id}.compact.log"
        buffered_raw_path = tmp_path / f"{leg_id}.buffered.log"
        pair_id = f"pair-{leg_id}"
        serial_session_id = f"serial-{leg_id}"
        fixture_session_id = f"fixture-{leg_id}"
        compact = _compact_raw(
            compact_raw_path, fixture, role, start_ms, build["environment"], git_sha,
            build["build_epoch"], build["elf_sha256"], sessions[group]["nonce"], port, output,
            pair_id, serial_session_id, fixture_session_id,
        )
        buffered_start = start_ms + 130000
        buffered = _buffered_raw(
            buffered_raw_path, fixture, role, buffered_start, build["environment"], git_sha,
            build["build_epoch"], build["elf_sha256"], sessions[group]["nonce"], port, output,
            pair_id, serial_session_id, fixture_session_id,
        )
        compact_path = tmp_path / f"{leg_id}.compact.json"
        buffered_path = tmp_path / f"{leg_id}.buffered.json"
        compact_hash = _write(compact_path, compact)
        buffered_hash = _write(buffered_path, buffered)
        compact_raw_hash = hashlib.sha256(compact_raw_path.read_bytes()).hexdigest()
        buffered_raw_hash = hashlib.sha256(buffered_raw_path.read_bytes()).hexdigest()
        show_state_lines = _show_state_lines()
        secondary_status_lines = _secondary_status_lines()
        scene_fields = {
            "primary_mode": 1, "primary_palette": 2, "secondary_mode": 3,
            "secondary_palette": 2, "secondary_enabled": True,
            "edge_enabled": False, "edge_mode": 0, "edge_strength": 0.0,
            "master_brightness": 0.75, "transition_state": "settled_inferred",
            "transition_max_duration_ms": 3000,
        }
        scene_observation = {
            "show_state_lines": show_state_lines,
            "secondary_status_lines": secondary_status_lines,
            "dump_response_sha256": hashlib.sha256(
                ("\n".join(_dump_lines()) + "\n").encode()
            ).hexdigest(),
            "scene_fields": scene_fields,
        }
        scene_status_hash = hashlib.sha256(
            json.dumps(scene_fields, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        pair_manifest = {
            "schema_ver": abba.PAIR_SCHEMA_VERSION,
            "pair_id": pair_id,
            "serial_session_id": serial_session_id,
            "fixture_session_id": fixture_session_id,
            "compact_raw_path": str(compact_raw_path.resolve()),
            "compact_raw_sha256": compact_raw_hash,
            "compact_summary_path": str(compact_path.resolve()),
            "compact_summary_sha256": compact_hash,
            "buffered_raw_path": str(buffered_raw_path.resolve()),
            "buffered_raw_sha256": buffered_raw_hash,
            "buffered_summary_path": str(buffered_path.resolve()),
            "buffered_summary_sha256": buffered_hash,
            "compact_end_monotonic_ms": start_ms + 120000,
            "buffered_host_start_monotonic_ms": buffered_start,
            "buffered_arm_monotonic_ms": buffered_start,
            "continuity_gap_ms": buffered_start - (start_ms + 120000),
            "fixture": fixture,
            "observed_output_device": output,
            "player": "ffplay start_ms=0 playback_gain_db=0.0" if fixture == "music" else "<disabled>",
            "boot_nonce": sessions[group]["nonce"],
            "scene_pre": scene_observation,
            "scene_post": scene_observation,
            "scene_status_sha256": scene_status_hash,
            "transition_inference_basis": {
                "transition_state": "settled_inferred",
                "transition_max_duration_ms": 3000,
                "minimum_mutation_free_pre_roll_ms": 10000,
                "no_scene_mutation_through_buffered_done": True,
                "device_settled_field_available": False,
            },
        }
        pair_manifest_path = tmp_path / f"{leg_id}.pair.json"
        pair_manifest_hash = _write(pair_manifest_path, pair_manifest)
        legs.append(
            {
                "id": leg_id, "build": role, "repetition": repetition, "fixture": fixture,
                "chip_id": abba.EXPECTED_DEVICE["chip_id"], "usb_serial": abba.EXPECTED_DEVICE["usb_serial"],
                "observed_port": port, "identity_revalidated_before_flash": True,
                "boot_identity_start": sessions[group]["nonce"], "boot_identity_end": sessions[group]["nonce"],
                "boot_epoch_start": build["build_epoch"], "boot_epoch_end": build["build_epoch"],
                "prohibited_activity": {key: False for key in abba.FORBIDDEN_ACTIVITY_FIELDS},
                "compact_summary_path": compact_path.name, "compact_summary_sha256": compact_hash,
                "compact_raw_log_path": compact_raw_path.name, "compact_raw_log_sha256": compact_raw_hash,
                "buffered_summary_path": buffered_path.name, "buffered_summary_sha256": buffered_hash,
                "buffered_raw_log_path": buffered_raw_path.name, "buffered_raw_log_sha256": buffered_raw_hash,
                "paired_capture_manifest_path": pair_manifest_path.name,
                "paired_capture_manifest_sha256": pair_manifest_hash,
            }
        )

    spec = {
        "schema_version": 1, "series_id": "gate2-test-series",
        "evidence_output_root": "docs/forensics/runtime-evidence/gate2-test-series",
        "design_authority_sha": "781c40a9b5aa20015196c28e054c436a0d9c5fb3",
        "device": dict(abba.EXPECTED_DEVICE),
        "platformio_config": {"snapshot_path": pio_path.name, "snapshot_sha256": pio_hash},
        "builds": builds, "flash_receipts": flash_receipts,
        "fixtures": {
            "music": {
                "track_path": abba.EXPECTED_MUSIC_PATH, "track_sha256": abba.EXPECTED_MUSIC_SHA256,
                "player": "ffplay", "start_ms": 0, "playback_gain_db": 0.0, "pre_roll_seconds": 10,
                "output_device": output,
                "captain_audible_confirmation_not_after": "2026-08-15T15:20:05+08:00",
            },
            "no_playback": {"host_playback": False, "output_quiet_confirmed": True, "output_device": output},
        },
        "runtime_contract": {
            "sample_rate": 12800, "samples_per_chunk": 96, "novelty_decimation": 3,
            "dma_desc_num": 3, "dma_frame_num": 96, "slot_bit_width": 32, "slot_mode": 2,
            "sample_time_assumption_id": 1, "ap_core": 0, "vp_core": 1, "ap_priority": 1,
            "vp_priority": 1, "vtask_delay_ticks": 1, "gdft_crossover_bin": 0,
            "gdft_lane4_enabled": False, "gdft_int64_magnitude": True,
            "gdft_int64_recurrence": True, "gdft_overflow_expected": False,
            "gdft_backend": "current_80_bin_direct_cross0", "microphone_backend": "IM69D130_PDM",
            "microphone_slot": "RIGHT", "pdm_dsr": "16S",
            "max_transition_duration_ms": 3000,
            "streams_running_during_capture": {name: False for name in ("ap", "tempo", "frontend", "vp", "diagnostic", "vp_perf")},
        },
        "legs": legs,
    }
    spec_path = tmp_path / "series.json"
    _write(spec_path, spec)
    return spec_path, pio


def _rewrite_spec(path: Path, spec: dict) -> None:
    _write(path, spec)


def _rehash_leg_file(spec: dict, tmp_path: Path, leg_index: int, key: str) -> Path:
    leg = spec["legs"][leg_index]
    path = tmp_path / leg[f"{key}_path"]
    leg[f"{key}_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    return path


def test_happy_pack_emits_deterministic_hash_bound_manifest(tmp_path: Path) -> None:
    spec_path, pio = make_pack(tmp_path)
    comparison_path = tmp_path / "comparison.json"
    manifest_path = tmp_path / "manifest.json"
    comparison, manifest = abba.write_outputs(spec_path, comparison_path, manifest_path, pio, GIT_STATE)
    assert comparison["perturbation_verdict"]["status"] == "PASS"
    assert comparison["perturbation_verdict"]["authorises_stage_instrument_as_evidence"] is True
    assert comparison["service_contract"]["separate_from_perturbation_verdict"] is True
    assert len(manifest["legs"]) == 8
    assert len(manifest["flash_receipts"]) == 3
    first = manifest_path.read_bytes()
    abba.write_outputs(spec_path, comparison_path, manifest_path, pio, GIT_STATE)
    assert manifest_path.read_bytes() == first


def test_non_paired_or_incomplete_pair_evidence_is_never_authoritative(tmp_path: Path) -> None:
    spec_path, pio = make_pack(tmp_path)
    spec = json.loads(spec_path.read_text())
    raw_path = tmp_path / spec["legs"][0]["compact_raw_log_path"]
    raw_path.write_text(raw_path.read_text().replace(f"# paired_capture_schema={abba.PAIR_SCHEMA_VERSION}\n", ""))
    raw_hash = hashlib.sha256(raw_path.read_bytes()).hexdigest()
    spec["legs"][0]["compact_raw_log_sha256"] = raw_hash
    pair_path = spec_path.parent / spec["legs"][0]["paired_capture_manifest_path"]
    pair = json.loads(pair_path.read_text())
    pair["compact_raw_sha256"] = raw_hash
    spec["legs"][0]["paired_capture_manifest_sha256"] = _write(pair_path, pair)
    _rewrite_spec(spec_path, spec)
    with pytest.raises(abba.EvidenceError, match="paired_capture_schema"):
        abba.evaluate_series(spec_path, pio)

    spec_path, pio = make_pack(tmp_path / "missing-manifest")
    spec = json.loads(spec_path.read_text())
    spec["legs"][0].pop("paired_capture_manifest_path")
    _rewrite_spec(spec_path, spec)
    with pytest.raises(abba.EvidenceError, match="paired_capture_manifest_path missing"):
        abba.evaluate_series(spec_path, pio)


def test_pair_session_and_scene_responses_are_bound_to_raw(tmp_path: Path) -> None:
    spec_path, pio = make_pack(tmp_path)
    spec = json.loads(spec_path.read_text())
    raw_path = tmp_path / spec["legs"][0]["buffered_raw_log_path"]
    raw_path.write_text(raw_path.read_text().replace("# serial_session_id=serial-A1_no_playback", "# serial_session_id=other-session"))
    spec["legs"][0]["buffered_raw_log_sha256"] = hashlib.sha256(raw_path.read_bytes()).hexdigest()
    _rewrite_spec(spec_path, spec)
    with pytest.raises(abba.EvidenceError, match="paired serial session|identifiers differ"):
        abba.evaluate_series(spec_path, pio)

    spec_path, pio = make_pack(tmp_path / "scene-forgery")
    spec = json.loads(spec_path.read_text())
    leg = spec["legs"][0]
    raw_path = spec_path.parent / leg["compact_raw_log_path"]
    raw_path.write_text(raw_path.read_text().replace("primary_mode=1 palette=2", "primary_mode=9 palette=2"))
    raw_hash = hashlib.sha256(raw_path.read_bytes()).hexdigest()
    leg["compact_raw_log_sha256"] = raw_hash
    pair_path = spec_path.parent / leg["paired_capture_manifest_path"]
    pair = json.loads(pair_path.read_text())
    pair["compact_raw_sha256"] = raw_hash
    leg["paired_capture_manifest_sha256"] = _write(pair_path, pair)
    _rewrite_spec(spec_path, spec)
    with pytest.raises(abba.EvidenceError, match="scene changed|pre-scene observation mismatch"):
        abba.evaluate_series(spec_path, pio)


def test_real_buffered_dump_order_and_single_preroll_are_mandatory(tmp_path: Path) -> None:
    spec_path, pio = make_pack(tmp_path)
    spec = json.loads(spec_path.read_text())
    raw_path = tmp_path / spec["legs"][0]["buffered_raw_log_path"]
    text = raw_path.read_text()
    begin = next(line for line in text.splitlines() if line.startswith("APCAD_CAPTURE_BEGIN,"))
    text = text.replace(begin + "\n", "").replace(
        "# host_capture_window_end_monotonic_ms=305000\n", begin + "\n# host_capture_window_end_monotonic_ms=305000\n",
    )
    raw_path.write_text(text)
    spec["legs"][0]["buffered_raw_log_sha256"] = hashlib.sha256(raw_path.read_bytes()).hexdigest()
    _rewrite_spec(spec_path, spec)
    with pytest.raises(abba.EvidenceError, match="buffered host/arm/END/dump/BEGIN/DONE"):
        abba.evaluate_series(spec_path, pio)

    spec_path, pio = make_pack(tmp_path / "second-preroll")
    spec = json.loads(spec_path.read_text())
    raw_path = spec_path.parent / spec["legs"][1]["buffered_raw_log_path"]
    raw_path.write_text(raw_path.read_text().replace(
        "# host_capture_window_start_monotonic_ms=450000",
        _action(449000, "playback_start", "paired_buffered", "pair-A1_music", "serial-A1_music")
        + "\n# host_capture_window_start_monotonic_ms=450000",
    ))
    spec["legs"][1]["buffered_raw_log_sha256"] = hashlib.sha256(raw_path.read_bytes()).hexdigest()
    _rewrite_spec(spec_path, spec)
    with pytest.raises(abba.EvidenceError, match="settle action count|repeats paired-session"):
        abba.evaluate_series(spec_path, pio)


def test_stack_hwm_requires_post_window_start_response_stop_order(tmp_path: Path) -> None:
    spec_path, pio = make_pack(tmp_path)
    spec = json.loads(spec_path.read_text())
    raw_path = tmp_path / spec["legs"][0]["compact_raw_log_path"]
    text = raw_path.read_text()
    hwm = "VP_PERF_STACK_HWM_WORDS: ap=1024 vp=1536\n"
    text = text.replace(hwm, "").replace(
        _action(290310, "vp_perf=start", "paired_stack_hwm", "pair-A1_no_playback", "serial-A1_no_playback") + "\n",
        hwm + _action(290310, "vp_perf=start", "paired_stack_hwm", "pair-A1_no_playback", "serial-A1_no_playback") + "\n",
    )
    raw_path.write_text(text)
    spec["legs"][0]["compact_raw_log_sha256"] = hashlib.sha256(raw_path.read_bytes()).hexdigest()
    _rewrite_spec(spec_path, spec)
    with pytest.raises(abba.EvidenceError, match="stack-HWM response|stack HWM was not measured"):
        abba.evaluate_series(spec_path, pio)


def test_current_untracked_source_and_impossible_overrun_run_length_fail_closed(tmp_path: Path) -> None:
    spec_path, pio = make_pack(tmp_path)
    with pytest.raises(abba.EvidenceError, match="untracked source"):
        abba.evaluate_series(spec_path, pio, {"head": GIT_STATE["head"], "tracked_status": "?? source.cpp\n"})
    root = "docs/forensics/runtime-evidence/gate2-test-series/"
    assert abba._filter_worktree_status(
        "?? docs/forensics/runtime-evidence/gate2-test-series/pair.json\n", root,
    ) == ""
    assert abba._filter_worktree_status(f"?? {abba.AUDIT_RECEIPT_PATH}\n", root) == ""
    assert "other-series" in abba._filter_worktree_status(
        "?? docs/forensics/runtime-evidence/other-series/pair.json\n", root,
    )

    spec = json.loads(spec_path.read_text())
    summary_path = tmp_path / spec["legs"][0]["compact_summary_path"]
    summary = json.loads(summary_path.read_text())
    summary["active_ap_work_over_7500_count"] = 1
    summary["max_consecutive_active_frames_over_7500"] = 0
    with pytest.raises(abba.EvidenceError, match="consecutive overrun count"):
        abba._validate_compact_summary(summary, "MIN", "no_playback", "adversarial")


def test_fixtures_derive_build_sha_from_live_checkout_head() -> None:
    live_head = _resolve_live_git_state()["head"]
    assert GIT_STATE["head"] == live_head
    assert len(live_head) == 40
    assert EMITTED_GIT == live_head[:8]
    assert re.fullmatch(r"[0-9a-f]{8}", EMITTED_GIT)


def test_production_git_probe_still_rejects_dirty_first_party_source(tmp_path: Path) -> None:
    spec_path, pio = make_pack(tmp_path)
    spec = json.loads(spec_path.read_text())
    live = _resolve_live_git_state()
    evidence_root = spec["evidence_output_root"].rstrip("/") + "/"
    if abba._filter_worktree_status(live["tracked_status"], evidence_root) == "":
        pytest.skip("working tree currently clean of first-party dirt")
    previous = abba._current_git_state
    abba._current_git_state = _resolve_live_git_state
    try:
        with pytest.raises(abba.EvidenceError, match="dirty or contains untracked source"):
            abba.evaluate_series(spec_path, pio)
    finally:
        abba._current_git_state = previous


def test_comparator_parses_exact_runner_marker_helpers() -> None:
    action = capture.paired_action_marker("apcad_soak=120000", "paired_compact", "pair-x", "serial-x", 1234)
    match = abba._ACTION_RE.fullmatch(action)
    assert match is not None
    assert match.groups() == ("1234", "apcad_soak=120000", "paired_compact", "pair-x", "serial-x")
    host = capture.paired_host_window_marker("start", 1234, "paired_compact", "pair-x", "serial-x")
    assert host == "# host_capture_window_start_monotonic_ms=1234"
    assert abba._parse_host_window([host, "# host_capture_window_end_monotonic_ms=2234"], "runner") == (1234, 2234)
    assert abba._parse_scene_responses(_show_state_lines(), _secondary_status_lines(), "runner")["secondary_enabled"] is True


@pytest.mark.parametrize(
    ("timestamp", "message"),
    [
        ("not-a-time", "not valid ISO-8601"),
        ("2026-08-16T05:00:00+08:00", "occurs after"),
        ("2026-08-16T03:00:00", "lacks timezone"),
    ],
)
def test_audible_confirmation_timestamp_must_precede_music_capture(
    tmp_path: Path, timestamp: str, message: str,
) -> None:
    spec_path, pio = make_pack(tmp_path)
    spec = json.loads(spec_path.read_text())
    spec["fixtures"]["music"]["captain_audible_confirmation_not_after"] = timestamp
    _rewrite_spec(spec_path, spec)
    with pytest.raises(abba.EvidenceError, match=message):
        abba.evaluate_series(spec_path, pio)


@pytest.mark.parametrize(
    "acknowledgement",
    [
        "AP_FRONTEND_DEBUG: off", "TEMPO_STREAM: off", "AP_STREAM: off",
        "SMART_ASSIST: off", "BEAT_DIRECTOR: off", "QUEUE_MODE: off",
    ],
)
def test_missing_runtime_control_acknowledgement_fails_closed(tmp_path: Path, acknowledgement: str) -> None:
    spec_path, pio = make_pack(tmp_path)
    spec = json.loads(spec_path.read_text())
    raw_path = tmp_path / spec["legs"][0]["compact_raw_log_path"]
    raw_path.write_text(raw_path.read_text().replace(acknowledgement + "\n", "", 1))
    spec["legs"][0]["compact_raw_log_sha256"] = hashlib.sha256(raw_path.read_bytes()).hexdigest()
    _rewrite_spec(spec_path, spec)
    with pytest.raises(abba.EvidenceError, match="did not return exact acknowledgement"):
        abba.evaluate_series(spec_path, pio)


@pytest.mark.parametrize(
    ("field", "message"),
    [
        ("phase", "action sequence"),
        ("pair", "paired serial session"),
        ("session", "paired serial session"),
    ],
)
def test_action_phase_pair_and_session_cannot_be_forged(
    tmp_path: Path, field: str, message: str,
) -> None:
    spec_path, pio = make_pack(tmp_path)
    spec = json.loads(spec_path.read_text())
    raw_path = tmp_path / spec["legs"][0]["compact_raw_log_path"]
    original = _action(
        170000, "apcad_soak=120000", "paired_compact",
        "pair-A1_no_playback", "serial-A1_no_playback",
    )
    replacement = _action(
        170000, "apcad_soak=120000",
        "paired_setup" if field == "phase" else "paired_compact",
        "wrong-pair" if field == "pair" else "pair-A1_no_playback",
        "wrong-session" if field == "session" else "serial-A1_no_playback",
    )
    raw_path.write_text(raw_path.read_text().replace(original, replacement, 1))
    spec["legs"][0]["compact_raw_log_sha256"] = hashlib.sha256(raw_path.read_bytes()).hexdigest()
    _rewrite_spec(spec_path, spec)
    with pytest.raises(abba.EvidenceError, match=message):
        abba.evaluate_series(spec_path, pio)


def test_status_delay_or_forged_phase_timestamp_cannot_escape_continuity(tmp_path: Path) -> None:
    spec_path, pio = make_pack(tmp_path)
    spec = json.loads(spec_path.read_text())
    raw_path = tmp_path / spec["legs"][0]["compact_raw_log_path"]
    text = raw_path.read_text().replace(
        "# action_ts_monotonic_ms=290100 action=apcad_soak_status=1",
        "# action_ts_monotonic_ms=310100 action=apcad_soak_status=1",
    )
    raw_path.write_text(text)
    spec["legs"][0]["compact_raw_log_sha256"] = hashlib.sha256(raw_path.read_bytes()).hexdigest()
    _rewrite_spec(spec_path, spec)
    with pytest.raises(abba.EvidenceError, match="timestamps regress|phase timestamps"):
        abba.evaluate_series(spec_path, pio)

    spec_path, pio = make_pack(tmp_path / "forged-phase")
    spec = json.loads(spec_path.read_text())
    raw_path = spec_path.parent / spec["legs"][0]["compact_raw_log_path"]
    raw_path.write_text(raw_path.read_text().replace(
        "# phase_ts_monotonic_ms=290200 phase=paired_compact event=end",
        "# phase_ts_monotonic_ms=170001 phase=paired_compact event=end",
    ))
    raw_hash = hashlib.sha256(raw_path.read_bytes()).hexdigest()
    spec["legs"][0]["compact_raw_log_sha256"] = raw_hash
    pair_path = spec_path.parent / spec["legs"][0]["paired_capture_manifest_path"]
    pair = json.loads(pair_path.read_text())
    pair["compact_raw_sha256"] = raw_hash
    spec["legs"][0]["paired_capture_manifest_sha256"] = _write(pair_path, pair)
    _rewrite_spec(spec_path, spec)
    with pytest.raises(abba.EvidenceError, match="phase timestamps"):
        abba.evaluate_series(spec_path, pio)


@pytest.mark.parametrize(
    "fatal_record",
    [
        "Bad command: injected-after-arm", "UNKNOWN command", "ERROR: injected",
        "ERR: injected", "FAIL: injected",
    ],
)
def test_post_arm_serial_error_cannot_pass_with_rehashed_evidence(
    tmp_path: Path, fatal_record: str,
) -> None:
    spec_path, pio = make_pack(tmp_path)
    spec = json.loads(spec_path.read_text())
    raw_path = tmp_path / spec["legs"][0]["buffered_raw_log_path"]
    raw_path.write_text(raw_path.read_text().replace(
        "APCAD_CAPTURE_DONE,", fatal_record + "\nAPCAD_CAPTURE_DONE,",
    ))
    raw_hash = hashlib.sha256(raw_path.read_bytes()).hexdigest()
    spec["legs"][0]["buffered_raw_log_sha256"] = raw_hash
    pair_path = tmp_path / spec["legs"][0]["paired_capture_manifest_path"]
    pair = json.loads(pair_path.read_text())
    pair["buffered_raw_sha256"] = raw_hash
    spec["legs"][0]["paired_capture_manifest_sha256"] = _write(pair_path, pair)
    _rewrite_spec(spec_path, spec)
    with pytest.raises(abba.EvidenceError, match="raw transcript contains"):
        abba.evaluate_series(spec_path, pio)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ((f"git={EMITTED_GIT}", f"git={EMITTED_GIT[:1]}"), "malformed BUILD"),
        ((f"git={EMITTED_GIT}", f"git={FORGED_GIT}"), "BUILD git mismatch"),
        (("BUILD: version=40103", "BUILD: version=forged"), "BUILD version mismatch"),
    ],
)
def test_build_identity_cannot_use_truncated_git_or_forged_version(
    tmp_path: Path, mutation: tuple[str, str], message: str,
) -> None:
    spec_path, pio = make_pack(tmp_path)
    spec = json.loads(spec_path.read_text())
    leg = spec["legs"][0]
    raw_path = tmp_path / leg["compact_raw_log_path"]
    raw_path.write_text(raw_path.read_text().replace(*mutation, 1))
    raw_hash = hashlib.sha256(raw_path.read_bytes()).hexdigest()
    leg["compact_raw_log_sha256"] = raw_hash
    pair_path = tmp_path / leg["paired_capture_manifest_path"]
    pair = json.loads(pair_path.read_text())
    pair["compact_raw_sha256"] = raw_hash
    leg["paired_capture_manifest_sha256"] = _write(pair_path, pair)
    _rewrite_spec(spec_path, spec)
    with pytest.raises(abba.EvidenceError, match=message):
        abba.evaluate_series(spec_path, pio)


def test_pre_arm_runtime_identity_response_cannot_be_relocated_after_soak(tmp_path: Path) -> None:
    spec_path, pio = make_pack(tmp_path)
    spec = json.loads(spec_path.read_text())
    leg = spec["legs"][0]
    raw_path = tmp_path / leg["compact_raw_log_path"]
    runtime = "RUNTIME_ID: boot_nonce=1111111111111111 uptime_ms=70000 reset_reason=1"
    text = raw_path.read_text().replace(runtime + "\n", "", 1)
    text = text.replace(
        "# phase_ts_monotonic_ms=290200 phase=paired_compact event=end",
        runtime + "\n# phase_ts_monotonic_ms=290200 phase=paired_compact event=end",
    )
    raw_path.write_text(text)
    raw_hash = hashlib.sha256(raw_path.read_bytes()).hexdigest()
    leg["compact_raw_log_sha256"] = raw_hash
    pair_path = tmp_path / leg["paired_capture_manifest_path"]
    pair = json.loads(pair_path.read_text())
    pair["compact_raw_sha256"] = raw_hash
    leg["paired_capture_manifest_sha256"] = _write(pair_path, pair)
    _rewrite_spec(spec_path, spec)
    with pytest.raises(abba.EvidenceError, match="outside its action-response window"):
        abba.evaluate_series(spec_path, pio)


@pytest.mark.parametrize(
    ("marker", "message"),
    [
        ("# action_ts_monotonic_ms=170100 action=vp_perf=start", "malformed paired action"),
        ("# phase_ts_monotonic_ms=170100 phase=paired_buffered event=begin", "malformed paired phase"),
        (
            "# host_capture_window_start_monotonic_ms=300100 phase=paired_buffered",
            "malformed host-window",
        ),
        ("# action_ts_ms=1", "malformed paired action"),
        ("# phase_ts=1", "malformed paired phase"),
        ("# host_capture_window_started_monotonic_ms=300100", "malformed host-window"),
        ("  # action_ts_monotonic_ms=170100 action=vp_perf=start phase=paired_buffered pair_id=p serial_session_id=s", "malformed paired action"),
    ],
)
def test_malformed_marker_prefixed_lines_fail_closed(
    tmp_path: Path, marker: str, message: str,
) -> None:
    spec_path, pio = make_pack(tmp_path)
    spec = json.loads(spec_path.read_text())
    leg = spec["legs"][0]
    raw_path = tmp_path / leg["buffered_raw_log_path"]
    raw_path.write_text(raw_path.read_text().replace(
        "APCAD_CAPTURE_DONE,", marker + "\nAPCAD_CAPTURE_DONE,", 1,
    ))
    raw_hash = hashlib.sha256(raw_path.read_bytes()).hexdigest()
    leg["buffered_raw_log_sha256"] = raw_hash
    pair_path = tmp_path / leg["paired_capture_manifest_path"]
    pair = json.loads(pair_path.read_text())
    pair["buffered_raw_sha256"] = raw_hash
    leg["paired_capture_manifest_sha256"] = _write(pair_path, pair)
    _rewrite_spec(spec_path, spec)
    with pytest.raises(abba.EvidenceError, match=message):
        abba.evaluate_series(spec_path, pio)


@pytest.mark.parametrize("field", ["stage_detail", *[f"saturation.{metric}" for metric in abba.METRICS]])
def test_boolean_substitution_cannot_masquerade_as_integer_zero(tmp_path: Path, field: str) -> None:
    spec_path, pio = make_pack(tmp_path)
    spec = json.loads(spec_path.read_text())
    leg = spec["legs"][0]
    summary_path = tmp_path / leg["compact_summary_path"]
    summary = json.loads(summary_path.read_text())
    if field == "stage_detail":
        summary["stage_detail"] = False
    else:
        summary["histogram_saturation"][field.removeprefix("saturation.")] = False
    summary_hash = _write(summary_path, summary)
    leg["compact_summary_sha256"] = summary_hash
    pair_path = tmp_path / leg["paired_capture_manifest_path"]
    pair = json.loads(pair_path.read_text())
    pair["compact_summary_sha256"] = summary_hash
    leg["paired_capture_manifest_sha256"] = _write(pair_path, pair)
    _rewrite_spec(spec_path, spec)
    with pytest.raises(abba.EvidenceError, match="must be an integer"):
        abba.evaluate_series(spec_path, pio)


@pytest.mark.parametrize("kind", ["compact", "buffered"])
@pytest.mark.parametrize(
    "record",
    [
        "[AP] SSL=1", "APDBG,t=1,foo=2", "AP_STREAM,t=1", "TEMPO,t=1",
        "TEMPO_DBG,t=1", "NOV,t=1", "[VP] profile=x", "VP_PERF: running",
        "VPF,ver=1,seq=1", "sbs((agc_debug=x))",
    ],
)
def test_active_stream_records_inside_measured_evidence_fail_closed(
    tmp_path: Path, kind: str, record: str,
) -> None:
    spec_path, pio = make_pack(tmp_path)
    spec = json.loads(spec_path.read_text())
    leg = spec["legs"][0]
    key = f"{kind}_raw_log"
    raw_path = tmp_path / leg[f"{key}_path"]
    marker = (
        "# host_capture_window_end_monotonic_ms=290000"
        if kind == "compact"
        else "APCAD_CAPTURE_DONE,"
    )
    raw_path.write_text(raw_path.read_text().replace(marker, record + "\n" + marker, 1))
    raw_hash = hashlib.sha256(raw_path.read_bytes()).hexdigest()
    leg[f"{key}_sha256"] = raw_hash
    pair_path = tmp_path / leg["paired_capture_manifest_path"]
    pair = json.loads(pair_path.read_text())
    pair[f"{kind}_raw_sha256"] = raw_hash
    leg["paired_capture_manifest_sha256"] = _write(pair_path, pair)
    _rewrite_spec(spec_path, spec)
    with pytest.raises(abba.EvidenceError, match="forbidden active stream"):
        abba.evaluate_series(spec_path, pio)

def test_summary_numbers_are_recomputed_from_hash_bound_raw(tmp_path: Path) -> None:
    spec_path, pio = make_pack(tmp_path)
    spec = json.loads(spec_path.read_text())
    summary_path = tmp_path / spec["legs"][0]["compact_summary_path"]
    summary = json.loads(summary_path.read_text())
    summary["p99_bounds_us"]["active_ap_work"] = {"low": 5024, "high": 5056}
    summary["percentile_bounds_us"]["active_ap_work"]["p99"] = {"low": 5024, "high": 5056}
    spec["legs"][0]["compact_summary_sha256"] = _write(summary_path, summary)
    _rewrite_spec(spec_path, spec)
    with pytest.raises(abba.EvidenceError, match="differs from raw reparse"):
        abba.evaluate_series(spec_path, pio)


def test_duplicate_raw_bytes_fail_closed(tmp_path: Path) -> None:
    spec_path, pio = make_pack(tmp_path)
    spec = json.loads(spec_path.read_text())
    source = tmp_path / spec["legs"][0]["compact_raw_log_path"]
    duplicate = tmp_path / spec["legs"][1]["compact_raw_log_path"]
    duplicate.write_bytes(source.read_bytes())
    spec["legs"][1]["compact_raw_log_sha256"] = hashlib.sha256(duplicate.read_bytes()).hexdigest()
    _rewrite_spec(spec_path, spec)
    with pytest.raises(abba.EvidenceError, match="reuses raw capture bytes"):
        abba.evaluate_series(spec_path, pio)



@pytest.mark.parametrize("counter", abba.ZERO_COMPACT_COUNTS)
def test_every_missing_compact_failure_counter_fails_closed(tmp_path: Path, counter: str) -> None:
    spec_path, pio = make_pack(tmp_path)
    spec = json.loads(spec_path.read_text())
    summary_path = spec_path.parent / spec["legs"][0]["compact_summary_path"]
    summary = json.loads(summary_path.read_text())
    summary.pop(counter)
    spec["legs"][0]["compact_summary_sha256"] = _write(summary_path, summary)
    _rewrite_spec(spec_path, spec)
    with pytest.raises(abba.EvidenceError, match=f"missing counter {counter}"):
        abba.evaluate_series(spec_path, pio)


@pytest.mark.parametrize("counter", abba.ZERO_BUFFERED_COUNTS)
def test_every_missing_buffered_failure_counter_fails_closed(tmp_path: Path, counter: str) -> None:
    spec_path, pio = make_pack(tmp_path)
    spec = json.loads(spec_path.read_text())
    summary_path = spec_path.parent / spec["legs"][0]["buffered_summary_path"]
    summary = json.loads(summary_path.read_text())
    summary.pop(counter)
    spec["legs"][0]["buffered_summary_sha256"] = _write(summary_path, summary)
    _rewrite_spec(spec_path, spec)
    with pytest.raises(abba.EvidenceError, match=f"missing counter {counter}"):
        abba.evaluate_series(spec_path, pio)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda spec: spec["runtime_contract"].__setitem__("gdft_backend", "lane4"), "gdft_backend mismatch"),
        (lambda spec: spec["runtime_contract"].__setitem__("gdft_overflow_expected", True), "gdft_overflow_expected must be False"),
        (lambda spec: spec["runtime_contract"].__setitem__("ap_priority", 2), "ap_priority must be 1"),
        (lambda spec: spec["runtime_contract"].__setitem__("microphone_slot", "LEFT"), "microphone_slot must be RIGHT"),
    ],
)
def test_conflicting_runtime_contract_never_passes(tmp_path: Path, mutation, message: str) -> None:
    spec_path, pio = make_pack(tmp_path)
    spec = json.loads(spec_path.read_text())
    mutation(spec)
    _rewrite_spec(spec_path, spec)
    with pytest.raises(abba.EvidenceError, match=message):
        abba.evaluate_series(spec_path, pio)


def test_unplanned_common_flag_or_resolved_config_drift_never_passes(tmp_path: Path) -> None:
    spec_path, pio = make_pack(tmp_path)
    snapshot = json.loads((tmp_path / "pio-config.json").read_text())
    for _name, options in snapshot:
        for option in options:
            if option[0] == "build_flags":
                option[1].append("-DUNPLANNED=1")
    spec = json.loads(spec_path.read_text())
    spec["platformio_config"]["snapshot_sha256"] = _write(tmp_path / "pio-config.json", snapshot)
    for build in spec["builds"].values():
        build["resolved_build_flags"].insert(-1, "-DUNPLANNED=1")
    _rewrite_spec(spec_path, spec)
    with pytest.raises(abba.EvidenceError, match="current resolved PlatformIO config differs|frozen contract"):
        abba.evaluate_series(spec_path, pio)


def test_single_boot_cannot_masquerade_as_three_flash_crossover(tmp_path: Path) -> None:
    spec_path, pio = make_pack(tmp_path)
    spec = json.loads(spec_path.read_text())
    first_receipt = json.loads((tmp_path / spec["flash_receipts"][0]["receipt_path"]).read_text())
    second_path = tmp_path / spec["flash_receipts"][1]["receipt_path"]
    second = json.loads(second_path.read_text())
    second["boot_nonce"] = first_receipt["boot_nonce"]
    spec["flash_receipts"][1]["receipt_sha256"] = _write(second_path, second)
    _rewrite_spec(spec_path, spec)
    with pytest.raises(abba.EvidenceError, match="three distinct"):
        abba.evaluate_series(spec_path, pio)


def test_arm_before_playback_and_vp_perf_restart_inside_window_are_rejected(tmp_path: Path) -> None:
    spec_path, pio = make_pack(tmp_path)
    spec = json.loads(spec_path.read_text())
    raw_path = tmp_path / spec["legs"][0]["compact_raw_log_path"]
    text = raw_path.read_text()
    arm = _action(170000, "apcad_soak=120000", "paired_compact", "pair-A1_no_playback", "serial-A1_no_playback")
    text = text.replace(
        arm,
        _action(169999, "vp_perf=start", "paired_compact", "pair-A1_no_playback", "serial-A1_no_playback")
        + "\n" + arm,
    )
    raw_path.write_text(text)
    spec["legs"][0]["compact_raw_log_sha256"] = hashlib.sha256(raw_path.read_bytes()).hexdigest()
    _rewrite_spec(spec_path, spec)
    with pytest.raises(abba.EvidenceError, match="prohibited/restarted"):
        abba.evaluate_series(spec_path, pio)

    spec_path, pio = make_pack(tmp_path / "arm-first")
    spec = json.loads(spec_path.read_text())
    raw_path = spec_path.parent / spec["legs"][1]["compact_raw_log_path"]
    text = raw_path.read_text()
    # Timestamp proves playback began after arm even if line order was doctored.
    text = text.replace("action_ts_monotonic_ms=310000 action=playback_start", "action_ts_monotonic_ms=320100 action=playback_start")
    raw_path.write_text(text)
    spec["legs"][1]["compact_raw_log_sha256"] = hashlib.sha256(raw_path.read_bytes()).hexdigest()
    _rewrite_spec(spec_path, spec)
    with pytest.raises(abba.EvidenceError, match="timestamps regress|final stop/settle/arm|pre-roll"):
        abba.evaluate_series(spec_path, pio)


def test_buffered_fixture_device_and_immediate_timing_are_bound(tmp_path: Path) -> None:
    spec_path, pio = make_pack(tmp_path)
    spec = json.loads(spec_path.read_text())
    raw_path = tmp_path / spec["legs"][0]["buffered_raw_log_path"]
    raw_path.write_text(raw_path.read_text().replace("# track=<none>", f"# track={abba.EXPECTED_MUSIC_PATH}"))
    spec["legs"][0]["buffered_raw_log_sha256"] = hashlib.sha256(raw_path.read_bytes()).hexdigest()
    _rewrite_spec(spec_path, spec)
    with pytest.raises(abba.EvidenceError, match="quiet track marker"):
        abba.evaluate_series(spec_path, pio)

    spec_path, pio = make_pack(tmp_path / "wrong-device")
    spec = json.loads(spec_path.read_text())
    raw_path = spec_path.parent / spec["legs"][0]["buffered_raw_log_path"]
    raw_path.write_text(raw_path.read_text().replace("B4:3A:45:A5:89:B4", "00:00:00:00:00:00"))
    spec["legs"][0]["buffered_raw_log_sha256"] = hashlib.sha256(raw_path.read_bytes()).hexdigest()
    _rewrite_spec(spec_path, spec)
    with pytest.raises(abba.EvidenceError, match="raw USB serial mismatch"):
        abba.evaluate_series(spec_path, pio)

    spec_path, pio = make_pack(tmp_path / "late-buffer")
    spec = json.loads(spec_path.read_text())
    raw_path = spec_path.parent / spec["legs"][0]["buffered_raw_log_path"]
    text = raw_path.read_text()
    # Delay the whole buffered invocation by 20 seconds without changing its
    # internally valid duration or device-derived summary.
    def shift(match):
        return match.group(1) + str(int(match.group(2)) + 20000)

    text = re.sub(r"(monotonic_ms=)(\d+)", shift, text)
    raw_path.write_text(text)
    buffered_raw_hash = hashlib.sha256(raw_path.read_bytes()).hexdigest()
    spec["legs"][0]["buffered_raw_log_sha256"] = buffered_raw_hash
    pair_path = spec_path.parent / spec["legs"][0]["paired_capture_manifest_path"]
    pair = json.loads(pair_path.read_text())
    pair["buffered_raw_sha256"] = buffered_raw_hash
    pair["buffered_host_start_monotonic_ms"] += 20000
    pair["buffered_arm_monotonic_ms"] += 20000
    pair["continuity_gap_ms"] += 20000
    spec["legs"][0]["paired_capture_manifest_sha256"] = _write(pair_path, pair)
    _rewrite_spec(spec_path, spec)
    with pytest.raises(abba.EvidenceError, match="did not immediately follow"):
        abba.evaluate_series(spec_path, pio)


def test_compact_geometry_rates_rows_and_actual_duration_are_mandatory(tmp_path: Path) -> None:
    spec_path, pio = make_pack(tmp_path)
    spec = json.loads(spec_path.read_text())
    summary_path = tmp_path / spec["legs"][0]["compact_summary_path"]
    summary = json.loads(summary_path.read_text())
    summary["percentile_bounds_us"]["active_ap_work"].pop("p50")
    spec["legs"][0]["compact_summary_sha256"] = _write(summary_path, summary)
    _rewrite_spec(spec_path, spec)
    with pytest.raises(abba.EvidenceError, match="p50"):
        abba.evaluate_series(spec_path, pio)

    spec_path, pio = make_pack(tmp_path / "duration")
    spec = json.loads(spec_path.read_text())
    raw_path = spec_path.parent / spec["legs"][0]["compact_raw_log_path"]
    text = raw_path.read_text().replace("observed_duration_ms=120000", "observed_duration_ms=5000")
    raw_path.write_text(text)
    spec["legs"][0]["compact_raw_log_sha256"] = hashlib.sha256(raw_path.read_bytes()).hexdigest()
    _rewrite_spec(spec_path, spec)
    with pytest.raises(abba.EvidenceError, match="differs from raw reparse|actual duration|capture_complete"):
        abba.evaluate_series(spec_path, pio)


def test_complete_statistic_surface_rejects_bad_geometry_max_rate_novelty_and_rows(tmp_path: Path) -> None:
    spec_path, _pio = make_pack(tmp_path)
    spec = json.loads(spec_path.read_text())
    summary_path = tmp_path / spec["legs"][0]["compact_summary_path"]
    original = json.loads(summary_path.read_text())
    mutations = (
        (lambda value: value.__setitem__("histogram_geometry", {"bucket_us": 128, "bucket_count": 128}), "geometry"),
        (lambda value: value["observed_max_us"].__setitem__("active_ap_work", 1), "max"),
        (lambda value: value.__setitem__("measured_ap_frame_rate_hz", 133.0), "rate/rows/duration"),
        (lambda value: value.__setitem__("measured_emitted_novelty_rate_hz", 1.0), "novelty rate"),
        (lambda value: value.__setitem__("measured_emitted_novelty_count", 1), "novelty count"),
        (lambda value: value.__setitem__("row_count", 1), "row count"),
    )
    for mutation, message in mutations:
        candidate = json.loads(json.dumps(original))
        mutation(candidate)
        with pytest.raises(abba.EvidenceError, match=message):
            abba._validate_compact_summary(candidate, "MIN", "no_playback", "adversarial")


def test_saturation_stack_and_buffered_coverage_defects_cannot_pass(tmp_path: Path) -> None:
    spec_path, pio = make_pack(tmp_path)
    spec = json.loads(spec_path.read_text())
    compact_path = tmp_path / spec["legs"][0]["compact_summary_path"]
    compact = json.loads(compact_path.read_text())
    compact["histogram_saturation"]["active_ap_work"] = 1
    spec["legs"][0]["compact_summary_sha256"] = _write(compact_path, compact)
    _rewrite_spec(spec_path, spec)
    with pytest.raises(abba.EvidenceError, match="histogram saturated"):
        abba.evaluate_series(spec_path, pio)

    spec_path, pio = make_pack(tmp_path / "stack")
    spec = json.loads(spec_path.read_text())
    compact_path = spec_path.parent / spec["legs"][0]["compact_summary_path"]
    compact = json.loads(compact_path.read_text())
    compact["vp_perf_stack_hwm_words"]["ap"] = 511
    spec["legs"][0]["compact_summary_sha256"] = _write(compact_path, compact)
    _rewrite_spec(spec_path, spec)
    with pytest.raises(abba.EvidenceError, match="AP stack reserve"):
        abba.evaluate_series(spec_path, pio)

    spec_path, pio = make_pack(tmp_path / "coverage")
    spec = json.loads(spec_path.read_text())
    buffered_path = spec_path.parent / spec["legs"][2]["buffered_summary_path"]
    buffered = json.loads(buffered_path.read_text())
    buffered["stage_coverage_failure_count"] = 1
    spec["legs"][2]["buffered_summary_sha256"] = _write(buffered_path, buffered)
    _rewrite_spec(spec_path, spec)
    with pytest.raises(abba.EvidenceError, match="stage_coverage_failure_count"):
        abba.evaluate_series(spec_path, pio)


def test_repeatability_uses_maximum_possible_delta_not_midpoint(tmp_path: Path) -> None:
    first = {
        "regression_low_pp": -0.65, "regression_high_pp": 0.65, "pair_status": "PASS"
    }
    second = dict(first)
    result = abba._repeatability(first, second)
    assert result["minimum_possible_delta_pp"] == 0.0
    assert result["maximum_possible_delta_pp"] == 1.3
    assert result["status"] == "PASS"
    wide = {
        "regression_low_pp": -2.6, "regression_high_pp": 2.6, "pair_status": "PASS"
    }
    result = abba._repeatability(wide, wide)
    assert result["maximum_possible_delta_pp"] == 5.2
    assert result["status"] == "INCONCLUSIVE"


def _frame_row(
    *,
    emitted: int = 0,
    onset_event: int = 0,
    active_ap_work_us: float = 1000.0,
    gdft_us: float = 400.0,
) -> dict:
    return {
        "emitted": emitted,
        "onset_event": onset_event,
        "active_ap_work_us": active_ap_work_us,
        "gdft_us": gdft_us,
    }


def test_exclusive_classes_partition_the_rows() -> None:
    rows = [
        _frame_row(emitted=0, onset_event=0),
        _frame_row(emitted=1, onset_event=0),
        _frame_row(emitted=0, onset_event=1),
        _frame_row(emitted=1, onset_event=1),
        _frame_row(emitted=1, onset_event=0),
    ]
    dist = abba.frame_class_distributions(rows)
    assert set(dist["exclusive"]) == {"neither", "tempo_only", "onset_only", "tempo_and_onset"}
    assert sum(dist["exclusive"][k]["n"] for k in dist["exclusive"]) == len(rows)
    assert dist["exclusive"]["neither"]["n"] == 1
    assert dist["exclusive"]["tempo_only"]["n"] == 2
    assert dist["exclusive"]["onset_only"]["n"] == 1
    assert dist["exclusive"]["tempo_and_onset"]["n"] == 1


def test_insufficient_n_does_not_emit_authoritative_p99() -> None:
    tiny_tempo_and_onset = [
        _frame_row(emitted=1, onset_event=1, active_ap_work_us=float(1000 + i))
        for i in range(5)
    ]
    dist = abba.frame_class_distributions(tiny_tempo_and_onset)
    assert dist["exclusive"]["tempo_and_onset"]["status"] == "INSUFFICIENT_N"
    assert "p99" not in dist["exclusive"]["tempo_and_onset"]["active_ap_work"]


def test_min_full_deltas_are_per_class() -> None:
    min_rows = [_frame_row(emitted=1, onset_event=0, active_ap_work_us=1000.0, gdft_us=400.0) for _ in range(120)]
    full_rows = [_frame_row(emitted=1, onset_event=0, active_ap_work_us=1100.0, gdft_us=450.0) for _ in range(120)]
    cmp = abba.compare_frame_classes(min_rows, full_rows)
    assert "tempo_only" in cmp
    assert {
        "active_ap_p99_delta_us",
        "gdft_p99_delta_us",
        "rate_delta_hz",
        "classification_changed",
    } <= set(cmp["tempo_only"])
    assert cmp["tempo_only"]["active_ap_p99_delta_us"] == pytest.approx(100.0)
    assert cmp["tempo_only"]["gdft_p99_delta_us"] == pytest.approx(50.0)


def test_perturbation_limits_are_frozen_from_deployed_contract() -> None:
    deployed_contract = abba.load_deployed_contract()
    limits = abba.perturbation_limits(deployed_contract)
    assert limits["ap_p99_delta_max_us"] == 375
    assert limits["instrumented_capture_drop_max"] == 0
    assert limits["throughput_delta_max_hz"] == abba.PERTURBATION_THROUGHPUT_DELTA_MAX_HZ


def test_service_check_limits_come_from_deployed_contract() -> None:
    limits = abba.service_limits_from_contract()
    assert limits["ap_arrival_period_us"] == 7500
    assert limits["ap_service_p99_max_us"] == 8000
    assert limits["measured_ap_rate_min_hz"] == pytest.approx(132.0)
    assert limits["measured_ap_rate_max_hz"] == pytest.approx(134.5)
