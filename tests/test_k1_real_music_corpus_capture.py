from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "regression-harness" / "k1_real_music_corpus_capture.py"

spec = importlib.util.spec_from_file_location("k1_real_music_corpus_capture", MODULE_PATH)
assert spec is not None
k1_real_music_corpus_capture = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = k1_real_music_corpus_capture
spec.loader.exec_module(k1_real_music_corpus_capture)


def test_select_reference_ids_defaults_to_present_real_music_refs() -> None:
    corpus = {
        "references": [
            {"id": "eric-clapton-wonderful-tonight-95bpm"},
            {"id": "tie-sto-thebusiness-120bpm"},
            {"id": "unrelated-999bpm"},
        ]
    }

    assert k1_real_music_corpus_capture.select_reference_ids(corpus, None) == [
        "eric-clapton-wonderful-tonight-95bpm",
        "tie-sto-thebusiness-120bpm",
    ]


def test_select_reference_ids_rejects_unknown_id() -> None:
    corpus = {"references": [{"id": "known"}]}

    try:
        k1_real_music_corpus_capture.select_reference_ids(corpus, ["missing"])
    except k1_real_music_corpus_capture.RealCorpusCaptureError as exc:
        assert "unknown reference id" in str(exc)
    else:
        raise AssertionError("missing id was not rejected")


def test_role_paths_default_excludes_metronome() -> None:
    class FakeP4:
        @staticmethod
        def stems_for_roles(reference: dict, *, include_roles: set[str] | None = None) -> list[Path]:
            assert reference["id"] == "ref"
            if include_roles is None:
                return [Path("drums.wav"), Path("other.wav")]
            return [Path(f"{role}.wav") for role in sorted(include_roles)]

    stems, roles = k1_real_music_corpus_capture.role_paths_for_capture(
        FakeP4(),
        {"id": "ref"},
        {"mix_roles": ["metronome"]},
        "all_musical",
    )

    assert stems == [Path("drums.wav"), Path("other.wav")]
    assert roles == ["all_musical_excluding_metronome"]


def test_role_paths_profile_uses_explicit_mix_roles() -> None:
    class FakeP4:
        @staticmethod
        def stems_for_roles(reference: dict, *, include_roles: set[str] | None = None) -> list[Path]:
            assert include_roles == {"drums", "other"}
            return [Path("drums.wav"), Path("other.wav")]

    stems, roles = k1_real_music_corpus_capture.role_paths_for_capture(
        FakeP4(),
        {"id": "ref"},
        {"mix_roles": ["drums", "other"]},
        "profile",
    )

    assert stems == [Path("drums.wav"), Path("other.wav")]
    assert roles == ["drums", "other"]


def test_default_render_parent_is_ignored_build_storage() -> None:
    assert k1_real_music_corpus_capture.DEFAULT_RENDER_PARENT.parts[-2:] == (
        "build",
        "k1-real-music-rendered",
    )


def test_hard_failures_rejects_runtime_tuple_and_health_faults() -> None:
    summary = {
        "row_count": 10,
        "active_sample_rate_mode": 12800,
        "active_samples_per_chunk_mode": 96,
        "active_tempo_decimation_mode": 3,
        "i2s_not_ok_count": 1,
        "bytes_mismatch_count": 0,
        "core_bad_count": 1,
        "frame_gap_count": 2,
        "timestamp_regression_count": 0,
        "active_ap_work_over_7500_count": 3,
        "emitted_active_ap_work_over_7500_count": 0,
    }

    failures = k1_real_music_corpus_capture.hard_failures(summary, 16000, 120, 3)

    assert "sample_rate_mismatch" in failures
    assert "samples_per_chunk_mismatch" in failures
    assert "i2s_not_ok_count" in failures
    assert "core_bad_count" in failures
    assert "frame_gap_count" in failures
    assert "active_ap_work_over_7500_count" in failures


def test_hard_failures_passes_clean_candidate_summary() -> None:
    summary = {
        "row_count": 2267,
        "active_sample_rate_mode": 16000,
        "active_samples_per_chunk_mode": 120,
        "active_tempo_decimation_mode": 3,
        "i2s_not_ok_count": 0,
        "bytes_mismatch_count": 0,
        "core_bad_count": 0,
        "frame_gap_count": 0,
        "timestamp_regression_count": 0,
        "active_ap_work_over_7500_count": 0,
        "emitted_active_ap_work_over_7500_count": 0,
    }

    assert k1_real_music_corpus_capture.hard_failures(summary, 16000, 120, 3) == []


def test_continue_on_failure_stops_only_for_capture_or_crash_failures() -> None:
    assert k1_real_music_corpus_capture.should_stop_after_failures([], True) is False
    assert k1_real_music_corpus_capture.should_stop_after_failures(["active_ap_work_over_7500_count"], False) is True
    assert k1_real_music_corpus_capture.should_stop_after_failures(["active_ap_work_over_7500_count"], True) is False
    assert k1_real_music_corpus_capture.should_stop_after_failures(["capture_command_failed"], True) is True
    assert k1_real_music_corpus_capture.should_stop_after_failures(["crash_marker"], True) is True


def test_crash_marker_hits_ignores_expected_usb_reset(tmp_path: Path) -> None:
    raw_log = tmp_path / "raw.log"
    raw_log.write_text(
        "rst:0x15 (USB_UART_CHIP_RESET)\n"
        "Task watchdog got triggered\n"
        "normal line\n",
        encoding="utf-8",
    )

    assert k1_real_music_corpus_capture.crash_marker_hits(str(raw_log)) == [
        "Task watchdog got triggered"
    ]


def test_build_capture_command_forces_explicit_real_track_and_tuple() -> None:
    command = k1_real_music_corpus_capture.build_capture_command(
        capture_script=Path("device_ap_cadence_capture.py"),
        rendered_wav=Path("/tmp/p4-real.wav"),
        port="/dev/cu.usbmodem12201",
        duration_ms=17000,
        start_ms=34000,
        post_wait_ms=1500,
        out_dir=Path("/tmp/out"),
        label="p4_real",
        expected_sample_rate=16000,
        expected_samples_per_chunk=120,
        expected_novelty_decimation=3,
        player="ffplay",
        playback_gain_db=0.0,
    )

    assert "--track" in command
    assert "/tmp/p4-real.wav" in command
    assert "--player" in command
    assert "ffplay" in command
    assert "--start-ms" in command
    assert "34000" in command
    assert "--expected-sample-rate" in command
    assert "16000" in command
    assert "--expected-samples-per-chunk" in command
    assert "120" in command
    assert "--compact-soak" not in command


def test_build_capture_command_can_use_compact_soak_for_long_real_music_runs() -> None:
    command = k1_real_music_corpus_capture.build_capture_command(
        capture_script=Path("device_ap_cadence_capture.py"),
        rendered_wav=Path("/tmp/p4-real.wav"),
        port="/dev/cu.usbmodem12201",
        duration_ms=120000,
        start_ms=0,
        post_wait_ms=1500,
        out_dir=Path("/tmp/out"),
        label="p4_real_soak",
        expected_sample_rate=16000,
        expected_samples_per_chunk=120,
        expected_novelty_decimation=3,
        player="ffplay",
        playback_gain_db=0.0,
        compact_soak=True,
    )

    assert "--compact-soak" in command
    assert "--duration-ms" in command
    assert "120000" in command
    assert "--start-ms" in command
    assert "0" in command


def test_segmented_aggregate_fails_if_any_segment_fails() -> None:
    render = {
        "reference_id": "ref",
        "expected_bpm": 120.0,
        "corpus_role": "steady",
        "profile_id": "steady_phase",
        "mix_policy": "all_musical",
        "mix_roles": ["all_musical_excluding_metronome"],
        "window": {"id": "main"},
        "rendered_wav": "/tmp/ref.wav",
    }
    segments = [
        {
            "hard_failures": [],
            "crash_marker_hits": [],
            "summary_extract": {
                "row_count": 2267,
                "active_sample_rate_mode": 16000,
                "active_samples_per_chunk_mode": 120,
                "active_tempo_decimation_mode": 3,
                "measured_ap_frame_rate_hz": 133.33,
                "measured_emitted_novelty_rate_hz": 44.44,
                "active_ap_work_p95_us": 6900,
                "active_ap_work_max_us": 7300,
                "active_ap_work_over_7500_count": 0,
            },
        },
        {
            "hard_failures": ["active_ap_work_over_7500_count"],
            "crash_marker_hits": [],
            "summary_extract": {
                "row_count": 2267,
                "active_sample_rate_mode": 16000,
                "active_samples_per_chunk_mode": 120,
                "active_tempo_decimation_mode": 3,
                "measured_ap_frame_rate_hz": 133.32,
                "measured_emitted_novelty_rate_hz": 44.43,
                "active_ap_work_p95_us": 7100,
                "active_ap_work_max_us": 7600,
                "active_ap_work_over_7500_count": 1,
            },
        },
    ]

    aggregate = k1_real_music_corpus_capture.aggregate_segment_entries(render, segments)

    assert aggregate["passed_runtime_gate"] is False
    assert aggregate["segment_count"] == 2
    assert aggregate["hard_failures"] == ["active_ap_work_over_7500_count"]
    assert aggregate["summary_extract"]["row_count"] == 4534
    assert aggregate["summary_extract"]["active_ap_work_max_us"] == 7600
