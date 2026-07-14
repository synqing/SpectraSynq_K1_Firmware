import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "scripts" / "regression-harness"
sys.path.insert(0, str(HARNESS))


def load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, HARNESS / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


capture = load_module("device_novelty_buffer_capture", "device_novelty_buffer_capture.py")
scorer = load_module("device_novelty_corpus_score", "device_novelty_corpus_score.py")


def test_novelty_dump_integrity_passes_complete_contiguous_buffer():
    lines = [
        "NOV_CAPTURE_BEGIN,count=3,capacity=6144,dropped=0,start_ms=100,end_ms=200",
        "NOV,t=110,emit=10,nov=0.1,src=buf",
        "NOV,t=132,emit=11,nov=0.2,src=buf",
        "NOV,t=155,emit=12,nov=0.3,src=buf",
        "NOV_CAPTURE_DONE,count=3,dropped=0",
    ]
    summary, errors = capture.validate_novelty_dump(lines)
    assert errors == []
    assert summary["row_count"] == 3


def test_novelty_dump_integrity_rejects_drop_and_emit_gap():
    lines = [
        "NOV_CAPTURE_BEGIN,count=2,capacity=6144,dropped=1,start_ms=100,end_ms=200",
        "NOV,t=110,emit=10,nov=0.1,src=buf",
        "NOV,t=132,emit=12,nov=0.2,src=buf",
        "NOV_CAPTURE_DONE,count=2,dropped=1",
    ]
    _, errors = capture.validate_novelty_dump(lines)
    assert any("dropped 1" in error for error in errors)
    assert any("emit-counter gaps" in error for error in errors)


def test_corpus_scorer_uses_last_half_mode_and_relative_tolerance(tmp_path):
    trajectory = tmp_path / "trajectory.log"
    rows = []
    for index in range(20):
        bpm = 90.0 if index < 10 else 128.0
        rows.append(f"T {index * 1000} {bpm:.1f} 0.8 1 0.0 0")
    trajectory.write_text("\n".join(rows) + "\n")

    scored = scorer.score_trajectory(trajectory, 128.0)
    assert scored["det_bpm"] == 128.0
    assert scored["acc1"] is True
    assert scored["acc2"] is True
    assert scored["locked_frac"] == 1.0


def test_corpus_scorer_last_half_is_relative_to_nonzero_device_uptime(tmp_path):
    trajectory = tmp_path / "device-uptime-trajectory.log"
    rows = []
    for index in range(20):
        bpm = 90.0 if index < 10 else 128.0
        locked = 0 if index < 10 else 1
        rows.append(f"T {300000 + index * 1000} {bpm:.1f} 0.8 {locked} 0.0 0")
    trajectory.write_text("\n".join(rows) + "\n")

    scored = scorer.score_trajectory(trajectory, 128.0)
    assert scored["det_bpm"] == 128.0
    assert scored["acc1"] is True
    assert scored["locked_frac"] == 1.0


def test_aggregate_emits_empty_bucket_as_not_applicable():
    aggregate = scorer.aggregate_set(
        [
            {
                "acc1": True,
                "acc2": True,
                "locked_frac": 0.5,
                "in_range": True,
                "bucket": "120-140",
            }
        ]
    )
    assert aggregate["buckets"]["120-140"]["n"] == 1
    assert aggregate["buckets"]["060-080"]["acc1"] is None


def test_runtime_identity_requires_exact_chip_and_build_environment():
    observed, errors = capture.validate_runtime_identity(
        [
            "BUILD: version=40103 git=b02fc16 epoch=1783934884 env=k1_bench_ap_frontend_probe",
            "CHIP_ID: B489A500",
        ],
        "B489A500",
        "k1_bench_ap_frontend_probe",
    )
    assert errors == []
    assert observed["chip_id"] == "B489A500"


def test_runtime_identity_accepts_firmware_native_bare_chip_line():
    observed, errors = capture.validate_runtime_identity(
        [
            "BUILD: version=40103 git=52a21db epoch=1784039780 env=k1_bench_ap_frontend_probe",
            "B489A500",
        ],
        "B489A500",
        "k1_bench_ap_frontend_probe",
    )
    assert errors == []
    assert observed["chip_line"] == "B489A500"
    assert observed["chip_id"] == "B489A500"


def test_runtime_identity_rejects_chip_id_embedded_in_unrelated_output():
    _, errors = capture.validate_runtime_identity(
        [
            "BUILD: version=40103 git=52a21db epoch=1784039780 env=k1_bench_ap_frontend_probe",
            "debug expected_chip=B489A500",
        ],
        "B489A500",
        "k1_bench_ap_frontend_probe",
    )
    assert any("runtime chip mismatch" in error for error in errors)


def test_runtime_identity_rejects_plausible_wrong_board_output():
    _, errors = capture.validate_runtime_identity(
        [
            "BUILD: version=40103 git=b02fc16 epoch=1783934884 env=k1_ap_frontend_probe",
            "CHIP_ID: F887A500",
        ],
        "B489A500",
        "k1_bench_ap_frontend_probe",
    )
    assert any("build env mismatch" in error for error in errors)
    assert any("runtime chip mismatch" in error for error in errors)


def test_capture_cli_can_retain_ap_and_tempo_streams(monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "device_novelty_buffer_capture.py",
            "--track",
            "/tmp/track.mp3",
            "--port",
            "/dev/cu.usbmodem112401",
            "--expected-chip-id",
            "B489A500",
            "--expected-build-env",
            "k1_bench_ap_frontend_probe",
            "--capture-ap-stream",
            "--capture-tempo-stream",
            "--set-mode",
            "23",
            "--expected-mode-ordinal",
            "23",
            "--event-status-period-ms",
            "250",
            "--eyes-on-countdown-ms",
            "10000",
        ],
    )
    args = capture.parse_args()
    assert args.capture_ap_stream is True
    assert args.capture_tempo_stream is True
    assert args.set_mode == 23
    assert args.event_status_period_ms == 250
    assert args.eyes_on_countdown_ms == 10000
    assert args.leave_effect_selected is False


def test_capture_has_explicit_eyes_on_arm_start_stop_markers():
    source = (HARNESS / "device_novelty_buffer_capture.py").read_text()
    assert "EYES_ON_ARMED effect=" in source
    assert "EYES_ON_START effect=" in source
    assert "EYES_ON_STOP effect=" in source


def test_numeric_mode_requires_explicit_ordinal_expectation(monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "device_novelty_buffer_capture.py",
            "--track",
            "/tmp/track.mp3",
            "--port",
            "/dev/cu.usbmodem112401",
            "--expected-chip-id",
            "B489A500",
            "--expected-build-env",
            "k1_bench_ap_frontend_probe",
            "--set-mode",
            "23",
        ],
    )
    try:
        capture.parse_args()
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("numeric mode selection must fail without an ordinal expectation")


def test_effect_catalog_resolves_captain_corrected_ordinals():
    catalog = capture.load_legacy_effect_catalog(ROOT)
    assert catalog["ember"]["ordinal"] == 16
    assert catalog["waveform_tempo"]["ordinal"] == 18
    assert catalog["dense_forge"]["ordinal"] == 21
    assert catalog["dense_forge_chord"]["ordinal"] == 24
    assert catalog["percussion_burst"]["ordinal"] == 26
    assert catalog["waveform_hybrid_k1"]["ordinal"] == 32


def test_mode_readback_uses_raw_config_ordinal_not_mode_echo():
    observed, errors = capture.validate_mode_readback(
        ["CONFIG.LIGHTSHOW_MODE: 26", "MODE: 18 (PERCUSSION BURST)"], 26
    )
    assert observed == 26
    assert errors == []


def test_mode_readback_rejects_wrong_render_ordinal():
    _, errors = capture.validate_mode_readback(
        ["CONFIG.LIGHTSHOW_MODE: 18", "MODE: 18"], 26
    )
    assert errors == ["mode ordinal mismatch: expected 26, observed 18"]


def test_get_mode_readback_requires_expected_runtime_ordinal():
    observed, errors = capture.validate_get_mode_readback(["MODE: 18"], 18)
    assert observed == 18
    assert errors == []

    _, errors = capture.validate_get_mode_readback(["MODE: 32"], 18)
    assert errors == ["runtime mode ordinal mismatch: expected 18, observed 32"]


def test_effect_selection_restores_previous_mode_by_default():
    source = (HARNESS / "device_novelty_buffer_capture.py").read_text()
    assert 'send(ser, "get_mode")' in source
    assert 'send(ser, f"set_mode={initial_mode_ordinal}")' in source
    assert "MODE_SNAPSHOT initial_ordinal=" in source
    assert "MODE_RESTORE verdict=" in source
    assert "not args.leave_effect_selected" in source


def test_leave_effect_selected_requires_explicit_cli_opt_in(monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "device_novelty_buffer_capture.py",
            "--track",
            "/tmp/track.mp3",
            "--port",
            "/dev/cu.usbmodem112401",
            "--expected-chip-id",
            "B489A500",
            "--expected-build-env",
            "k1_bench_ap_frontend_probe",
            "--set-effect",
            "waveform_tempo",
            "--leave-effect-selected",
        ],
    )
    args = capture.parse_args()
    assert args.leave_effect_selected is True


def test_corpus_scorer_renders_exact_rerun_command(tmp_path):
    ledger = tmp_path / "commands.json"
    ledger.write_text(
        '{"entry_command":"python3 scripts/regression-harness/device_novelty_corpus_run.py corpus.json --port /dev/cu.usbmodem1401"}'
    )
    lines, command = scorer.reproduction_section(ledger)
    assert command is not None
    assert "/dev/cu.usbmodem1401" in command
    assert "```bash" in lines
    assert any(str(ledger) in line for line in lines)
