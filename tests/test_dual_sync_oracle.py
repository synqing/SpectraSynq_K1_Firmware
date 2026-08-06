"""Fail-closed host contract for dual-sync oracle schema v2."""

from __future__ import annotations

import dataclasses
import io
import json
import struct
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.dual_sync_probe import (
    capture,
    correlate,
    f2_capture,
    f2_flash,
    f2_ports,
    gate_eval,
    logfmt,
    synth,
)
from scripts.dual_sync_probe.synth import SynthParams

SEED = 20260708


def _clean(**overrides) -> SynthParams:
    return dataclasses.replace(SynthParams(), **overrides)


def _logs(params: SynthParams | None = None, seed: int = SEED):
    return synth.generate_log_pair(params or _clean(), seed=seed)


def _evaluate(params: SynthParams | None = None, **thresholds):
    leader, follower = _logs(params)
    return gate_eval.evaluate(
        leader, follower, strict_proof=True, **thresholds
    )


def _correlate(params: SynthParams | None = None):
    leader, follower = _logs(params)
    return correlate.correlate(
        logfmt.parse_log(leader, strict=True, expected_role="leader"),
        logfmt.parse_log(follower, strict=True, expected_role="follower"),
    )


def test_parser_keeps_legacy_grammar_permissive():
    assert logfmt.parse_line(
        "[k1_sync] clk est_offset_us=-42 rtt_us=8000 n=16"
    ) == logfmt.Clk(-42, 8000, 16)
    health = logfmt.parse_line(
        "[k1_sync] health fps=99.50 heap_min=60000 ap_p95_us=700 "
        "dial_linked=1 loss=0 dup=0"
    )
    assert health == logfmt.Health(99.5, 60000, 700, 1, 0, 0)


def test_parser_prefers_timestamped_clock_before_legacy_regex():
    line = (
        "host_us=10 [k1_sync] clk role=follower t_local_us=5000010 "
        "est_offset_us=5000000 rtt_us=4000 n=12"
    )
    assert logfmt.parse_line(line) == logfmt.Clk(
        5_000_000, 4000, 12, t_local_us=5_000_010, role="follower"
    )


def test_health_role_and_unknown_fields_are_preserved():
    line = (
        "host_us=1 [k1_sync] health role=leader fps=100.00 heap_min=60000 "
        "ap_p95_us=700 dial_linked=1 loss=0 dup=0 "
        "led_submit_deadline_miss=2"
    )
    health = logfmt.parse_line(line)
    assert isinstance(health, logfmt.Health)
    assert health.role == "leader"
    assert health.extra_int("led_submit_deadline_miss") == 2


@pytest.mark.parametrize(
    ("line", "role"),
    [
        (
            "[k1_sync] health fps=100 heap_min=60000 ap_p95_us=700 "
            "dial_linked=1 loss=0 dup=0",
            "leader",
        ),
        (
            "host_us=1 [k1_sync] clk role=follower "
            "est_offset_us=0 rtt_us=1 n=1",
            "follower",
        ),
        (
            "host_us=1 [k1_sync] health role=follower fps=100 "
            "heap_min=60000 ap_p95_us=700 dial_linked=0 loss=0 dup=0",
            "leader",
        ),
    ],
)
def test_strict_parser_rejects_missing_or_wrong_contract_fields(line, role):
    with pytest.raises(logfmt.LogContractError):
        logfmt.parse_log(line, strict=True, expected_role=role)


def test_strict_parser_rejects_recognised_line_without_host_timestamp():
    with pytest.raises(logfmt.LogContractError, match="host_us"):
        logfmt.parse_log(
            "[k1_sync] tx seq=1 t_leader_us=1",
            strict=True,
            expected_role="leader",
        )


@pytest.mark.parametrize(
    "line",
    [
        (
            "host_us=1 [k1_sync] health role=leader fps=0 fps=100 "
            "heap_min=60000 ap_p95_us=700 dial_linked=1 loss=0 dup=0"
        ),
        "noise host_us=1 [k1_sync] tx seq=1 t_leader_us=1",
        "host_us=1 host_us=2 [k1_sync] tx seq=1 t_leader_us=1",
        "host_us=1 [k1_sync] tx seq=1 t_leader_us=1 trailing",
    ],
)
def test_strict_parser_rejects_ambiguous_or_trailing_evidence(line):
    with pytest.raises(logfmt.LogContractError):
        logfmt.parse_log(line, strict=True, expected_role="leader")


def test_parse_log_accounts_for_recognised_reset_evidence():
    params = _clean(duration_s=10.0, noise_lines=25)
    leader, follower = _logs(params)
    for text, has_tx in ((leader, True), (follower, False)):
        parsed = logfmt.parse_log(text)
        reset_count = sum(
            isinstance(record, logfmt.Reset) for record in parsed.records
        )
        assert parsed.skipped_lines + reset_count == 25
        assert any(
            isinstance(record, logfmt.Tx) for record in parsed.records
        ) == has_tx


def test_clean_strict_link_ready_passes_without_leader_clock_records():
    verdict = _evaluate()
    assert verdict["schema_version"] == 2
    assert verdict["link_ready"]["status"] == gate_eval.PASS
    assert (
        verdict["link_ready"]["checks"]["follower_clk_records"]["value"] >= 10
    )
    leader, _ = _logs()
    assert not any(
        isinstance(record, logfmt.Clk)
        for record in logfmt.parse_log(leader).records
    )
    assert verdict["gate1_clock_err"]["status"] == gate_eval.PASS
    assert verdict["gate2_lateness"]["status"] == gate_eval.PASS
    assert (
        verdict["gate3_leader_stamp_to_follower_consume"]["status"]
        == gate_eval.PASS
    )


def test_missing_physical_glitch_instrument_keeps_overall_unmeasured():
    verdict = _evaluate()
    assert (
        verdict["gate4_health"]["subgates"]["physical_ws2812_glitch"]["status"]
        == gate_eval.UNMEASURED
    )
    assert verdict["overall_status"] == gate_eval.UNMEASURED
    assert verdict["overall_pass"] is False
    assert "overall" not in verdict


def test_firmware_health_cannot_manufacture_physical_glitch_pass():
    leader, follower = _logs()
    leader = leader.replace("loss=0 dup=0", "loss=0 dup=0 ws2812_glitch=0")
    follower = follower.replace("loss=0 dup=0", "loss=0 dup=0 ws2812_glitch=0")
    verdict = gate_eval.evaluate(
        leader, follower, strict_proof=True
    )
    physical = verdict["gate4_health"]["subgates"][
        "physical_ws2812_glitch"
    ]
    assert physical["status"] == gate_eval.UNMEASURED
    assert verdict["overall_status"] == gate_eval.UNMEASURED


@pytest.mark.parametrize(
    ("leader", "follower"),
    [
        ("", ""),
        (
            "host_us=1 [k1_sync] health role=leader fps=100 "
            "heap_min=60000 ap_p95_us=700 dial_linked=1 loss=0 dup=0\n",
            "host_us=1 [k1_sync] health role=follower fps=100 "
            "heap_min=60000 ap_p95_us=700 dial_linked=0 loss=0 dup=0\n",
        ),
    ],
)
def test_empty_or_health_only_logs_are_blocked(leader, follower):
    verdict = gate_eval.evaluate(leader, follower)
    assert verdict["link_ready"]["status"] == gate_eval.BLOCKED
    assert verdict["overall_status"] == gate_eval.BLOCKED
    assert verdict["overall_pass"] is False


def test_short_capture_with_zero_stream_cannot_pass():
    verdict = _evaluate(_clean(duration_s=0.01))
    assert verdict["link_ready"]["status"] == gate_eval.BLOCKED
    assert (
        verdict["link_ready"]["checks"]["transport_expected"]["value"] == 0
    )
    assert verdict["overall_status"] == gate_eval.BLOCKED


def test_disconnected_epochs_cannot_accumulate_to_link_ready():
    verdict = _evaluate(_clean(disconnect_at_s=20.0))
    epoch = verdict["link_ready"]["checks"]["single_link_epoch"]
    assert epoch["leader_up"] == 2
    assert epoch["follower_up"] == 2
    assert epoch["leader_down"] == 1
    assert verdict["link_ready"]["status"] == gate_eval.BLOCKED


def test_post_link_begin_is_a_session_boundary():
    leader, follower = _logs()
    leader += "host_us=70000000 [k1_sync] begin role=leader\n"
    verdict = gate_eval.evaluate(leader, follower, strict_proof=True)
    epoch = verdict["link_ready"]["checks"]["single_link_epoch"]
    assert epoch["post_link_begin"] == 1
    assert verdict["link_ready"]["status"] == gate_eval.BLOCKED


@pytest.mark.parametrize(
    "replacement",
    [
        "interval_units=0",
        "mtu=0",
        "phy_tx=0",
        "phy_rx=0",
    ],
)
def test_impossible_negotiated_values_block_link_ready(replacement):
    leader, follower = _logs()
    key = replacement.split("=", 1)[0]
    source = {
        "interval_units": "interval_units=6",
        "mtu": "mtu=247",
        "phy_tx": "phy_tx=2",
        "phy_rx": "phy_rx=2",
    }[key]
    leader = leader.replace(source, replacement)
    follower = follower.replace(source, replacement)
    verdict = gate_eval.evaluate(leader, follower, strict_proof=True)
    negotiated = verdict["link_ready"]["checks"]["negotiated_both_roles"]
    assert negotiated["values_valid"] is False
    assert verdict["link_ready"]["status"] == gate_eval.BLOCKED


def test_cross_role_negotiated_values_must_agree():
    leader, follower = _logs()
    follower = follower.replace("interval_units=6", "interval_units=12")
    verdict = gate_eval.evaluate(leader, follower, strict_proof=True)
    negotiated = verdict["link_ready"]["checks"]["negotiated_both_roles"]
    assert negotiated["values_valid"] is True
    assert negotiated["values_agree"] is False
    assert verdict["link_ready"]["status"] == gate_eval.BLOCKED


def _move_record_host(text: str, needle: str, host_us: int) -> str:
    lines = []
    for line in text.splitlines():
        if needle in line:
            _, payload = line.split(" ", 1)
            line = f"host_us={host_us} {payload}"
        lines.append(line)
    return "\n".join(lines) + "\n"


def test_prelink_records_cannot_be_laundered_into_link_ready():
    leader, follower = _logs()
    leader = _move_record_host(
        leader, "[k1_sync] link up", 100_000_000
    )
    follower = _move_record_host(
        follower, "[k1_sync] link up", 100_000_000
    )
    verdict = gate_eval.evaluate(leader, follower, strict_proof=True)
    assert verdict["link_ready"]["status"] == gate_eval.BLOCKED
    assert verdict["diagnostics"]["transport_expected"] == 0


def test_negotiation_must_follow_each_role_link_up():
    leader, follower = _logs()
    leader = _move_record_host(leader, "[k1_sync] negotiated", 0)
    follower = _move_record_host(follower, "[k1_sync] negotiated", 0)
    verdict = gate_eval.evaluate(leader, follower, strict_proof=True)
    negotiated = verdict["link_ready"]["checks"]["negotiated_both_roles"]
    assert negotiated["ok"] is False
    assert verdict["link_ready"]["status"] == gate_eval.BLOCKED


def test_role_local_epoch_numbers_need_not_match_across_devices():
    leader, follower = _logs()
    follower = follower.replace("role=follower epoch=1", "role=follower epoch=9")
    verdict = gate_eval.evaluate(leader, follower, strict_proof=True)
    assert verdict["link_ready"]["status"] == gate_eval.PASS


def test_duplicate_reordered_or_unexpected_follower_records_block_link_ready():
    leader, follower = _logs()
    follower += (
        "host_us=70000000 [k1_sync] rx seq=1 t_leader_us=1 "
        "t_local_us=5000001\n"
        "host_us=70000001 [k1_sync] apply seq=999999 "
        "t_render_us=75000001\n"
    )
    verdict = gate_eval.evaluate(leader, follower, strict_proof=True)
    integrity = verdict["link_ready"]["checks"]["follower_sequence_integrity"]
    assert integrity["ok"] is False
    assert integrity["rx_duplicate"] == 1
    assert integrity["rx_reorder"] == 1
    assert integrity["apply_unexpected"] == 1
    assert verdict["overall_status"] == gate_eval.BLOCKED


def test_leader_counter_reset_or_duplicate_blocks_link_ready():
    leader, follower = _logs()
    leader += "host_us=70000000 [k1_sync] tx seq=0 t_leader_us=70000000\n"
    verdict = gate_eval.evaluate(leader, follower, strict_proof=True)
    dense = verdict["link_ready"]["checks"]["leader_tx_dense"]
    assert dense["ok"] is False
    assert dense["duplicate"] == 1
    assert dense["reorder"] == 1


def test_dial_is_computed_from_leader_health_only():
    correlation = _correlate()
    assert correlation.health_by_role["leader"].dial_uptime == 1.0
    assert correlation.health_by_role["follower"].dial_uptime is None
    verdict = _evaluate()
    assert (
        verdict["gate4_health"]["subgates"]["dial_uptime"]["status"]
        == gate_eval.PASS
    )


def test_ap_zero_is_unmeasured_not_pass():
    verdict = _evaluate(_clean(ap_p95_us=0))
    assert (
        verdict["gate4_health"]["subgates"]["leader_ap_p95_us"]["status"]
        == gate_eval.UNMEASURED
    )
    assert (
        verdict["gate4_health"]["subgates"]["follower_ap_p95_us"]["status"]
        == gate_eval.UNMEASURED
    )
    assert verdict["overall_status"] == gate_eval.UNMEASURED


def test_silicon_shaped_drop_preserves_rx_and_fails_apply_loss_only():
    verdict = _evaluate(_clean(apply_drop_frac=0.10))
    assert (
        verdict["gate4_health"]["subgates"]["transport_loss"]["status"]
        == gate_eval.PASS
    )
    assert verdict["diagnostics"]["transport_missing"] == 0
    assert verdict["diagnostics"]["apply_missing"] > 0
    assert (
        verdict["gate4_health"]["subgates"]["apply_loss"]["status"]
        == gate_eval.FAIL
    )
    assert verdict["overall_status"] == gate_eval.FAIL


def test_transport_drop_fails_transport_loss():
    verdict = _evaluate(_clean(loss_frac=0.05))
    assert verdict["diagnostics"]["transport_missing"] > 0
    assert (
        verdict["gate4_health"]["subgates"]["transport_loss"]["status"]
        == gate_eval.FAIL
    )


def test_apply_delay_and_clock_bias_flip_their_independent_gates():
    clean = _evaluate(_clean(), lateness_p999_us=16000)
    delayed = _evaluate(
        _clean(apply_delay_us=5000),
        lateness_p999_us=16000,
    )
    clocked = _evaluate(_clean(clock_bias_us=6000))
    assert clean["gate2_lateness"]["status"] == gate_eval.PASS
    assert delayed["gate2_lateness"]["status"] == gate_eval.FAIL
    assert clocked["gate1_clock_err"]["status"] == gate_eval.FAIL


def test_gate3_name_is_honest_and_old_name_is_absent():
    verdict = _evaluate()
    assert "gate3_leader_stamp_to_follower_consume" in verdict
    assert "gate3_e2e" not in verdict
    assert "mic" not in gate_eval.format_summary(verdict).lower()


def test_summary_uses_explicit_status_not_string_truthiness():
    verdict = gate_eval.evaluate("", "")
    summary = gate_eval.format_summary(verdict)
    assert "OVERALL: BLOCKED" in summary
    assert "OVERALL: PASS" not in summary


def test_clean_wire_truth_recovers_offset_and_asymmetry():
    correlation = _correlate()
    offsets = [sample.offset_us for sample in correlation.rounds]
    assert len(offsets) > 100
    assert abs(correlate.mean(offsets) - 5_000_000) < 5.0
    asymmetry = correlate.mean(
        [sample.asymmetry_us for sample in correlation.rounds]
    )
    assert abs(asymmetry - 3.0) < 1.0


def test_clock_drift_recovery_still_detects_slope():
    params = _clean(
        duration_s=150.0,
        drift_us_per_s=40.0,
        clock_est_drift_us_per_s=0.0,
    )
    correlation = _correlate(params)
    slope = correlate.clock_error_slope_us_per_s(
        correlation.clock_error_series
    )
    assert slope is not None
    assert abs(slope - (-40.0)) < 5.0
    assert _evaluate(params)["gate1_clock_err"]["status"] == gate_eval.FAIL


def _write_logs(tmp_path: Path, params: SynthParams):
    leader, follower = _logs(params)
    leader_path = tmp_path / "leader.log"
    follower_path = tmp_path / "follower.log"
    leader_path.write_text(leader)
    follower_path.write_text(follower)
    return leader_path, follower_path


@pytest.mark.parametrize(
    ("params", "expected_exit"),
    [
        (_clean(clock_bias_us=6000), 1),
        (_clean(duration_s=0.01), 2),
        (_clean(), 3),
    ],
)
def test_cli_exit_codes_are_status_specific(
    tmp_path, capsys, params, expected_exit
):
    leader, follower = _write_logs(tmp_path, params)
    exit_code = gate_eval.main(
        ["--strict-proof", str(leader), str(follower)]
    )
    capsys.readouterr()
    assert exit_code == expected_exit


def test_cli_pass_exit_is_mapped_without_fabricating_device_evidence(
    tmp_path, monkeypatch, capsys
):
    leader = tmp_path / "leader.log"
    follower = tmp_path / "follower.log"
    leader.write_text("")
    follower.write_text("")
    monkeypatch.setattr(
        gate_eval,
        "evaluate",
        lambda *_args, **_kwargs: {
            "schema_version": 2,
            "overall_status": gate_eval.PASS,
            "overall_pass": True,
        },
    )
    assert gate_eval.main([str(leader), str(follower)]) == 0
    capsys.readouterr()


def test_cli_contract_error_is_exit_4(tmp_path, capsys):
    leader = tmp_path / "leader.log"
    follower = tmp_path / "follower.log"
    leader.write_text("[k1_sync] tx seq=1 t_leader_us=1\n")
    follower.write_text("")
    assert (
        gate_eval.main(
            ["--strict-proof", str(leader), str(follower)]
        )
        == gate_eval.INPUT_ERROR_EXIT
    )
    assert "input contract error" in capsys.readouterr().err


def test_determinism_is_byte_identical():
    first = _evaluate()
    second = _evaluate()
    assert gate_eval.to_json(first) == gate_eval.to_json(second)
    parsed = json.loads(gate_eval.to_json(first))
    assert parsed["schema_version"] == 2


class _FakeSerial:
    def __init__(
        self,
        role,
        *,
        acknowledge=True,
        stale=(),
        status_mode="linked",
        status_epoch=7,
    ):
        self.role = role
        self.acknowledge = acknowledge
        self.status_mode = status_mode
        self.status_epoch = status_epoch
        self.lines = [f"{line}\n".encode() for line in stale]
        self.writes = []
        self.closed = False
        self.reset_count = 0

    def readline(self):
        return self.lines.pop(0) if self.lines else b""

    def write(self, payload):
        command = payload.decode().strip()
        self.writes.append(command)
        if command == ":sync_status":
            if self.status_mode == "silent":
                return len(payload)
            linked = "0" if self.status_mode == "unlinked" else "1"
            self.lines.append(
                f"SYNC_STATUS: role={self.role} linked={linked}\n".encode()
            )
            if linked == "1":
                mtu = 23 if self.status_mode == "incoherent" else 247
                link_suffix = (
                    " trailing=garbage"
                    if self.status_mode == "malformed"
                    else ""
                )
                self.lines.extend(
                    [
                        (
                            f"[k1_sync] link up role={self.role} "
                            f"epoch={self.status_epoch} handle=1 mtu=247"
                            f"{link_suffix}\n"
                        ).encode(),
                        (
                            f"[k1_sync] negotiated role={self.role} "
                            f"epoch={self.status_epoch} interval_units=6 "
                            f"latency=0 mtu={mtu} phy_tx=2 phy_rx=2\n"
                        ).encode(),
                    ]
                )
            return len(payload)
        if self.acknowledge and command.startswith(":sync_fault="):
            mode = command.split("=", 1)[1]
            self.lines.extend(
                [
                    f"SYNC_FAULT: {mode}\n".encode(),
                    f"[k1_sync] fault={mode}\n".encode(),
                ]
            )
        return len(payload)

    def flush(self):
        return None

    def reset_input_buffer(self):
        self.reset_count += 1
        self.lines.clear()

    def close(self):
        self.closed = True


class _IdentitySerial(_FakeSerial):
    def __init__(
        self,
        chip_id,
        env,
        git_hash="abcdef0",
        app_elf_sha256="a" * 64,
    ):
        role = "leader" if "main" in env else "follower"
        super().__init__(role)
        self.chip_id = chip_id
        self.env = env
        self.git_hash = git_hash
        self.app_elf_sha256 = app_elf_sha256

    def write(self, payload):
        command = payload.decode().strip()
        if command == ":chip_id":
            self.lines.append(f"{self.chip_id}\n".encode())
            return len(payload)
        if command == ":build":
            self.lines.append(
                (
                    f"BUILD: version=40103 git={self.git_hash} "
                    f"epoch=123 env={self.env}\n"
                ).encode()
            )
            return len(payload)
        if command == ":image_id":
            self.lines.append(
                (
                    "IMAGE_ID: app_elf_sha256="
                    f"{self.app_elf_sha256}\n"
                ).encode()
            )
            return len(payload)
        if command == ":runtime_id":
            self.lines.append(
                (
                    "RUNTIME_ID: boot_nonce=0123456789abcdef "
                    "uptime_ms=12345 reset_reason=1\n"
                ).encode()
            )
            return len(payload)
        return super().write(payload)


def _serial_factory(leader, follower):
    streams = {"leader": leader, "follower": follower}
    return lambda port, _baud: streams[port]


def test_capture_fault_mapping_is_bounded_and_restored_maps_to_off():
    assert capture.parse_segments("off,delay5,restored") == (
        "off",
        "delay5",
        "restored",
    )
    assert capture.fault_for_segment("restored") == "off"
    with pytest.raises(capture.CaptureContractError, match="F3-only"):
        capture.parse_segments("clockoff")


def test_capture_is_non_overwriting(tmp_path):
    out_dir = tmp_path / "existing"
    out_dir.mkdir()
    opened = False

    def forbidden_factory(_port, _baud):
        nonlocal opened
        opened = True
        raise AssertionError("serial must not open")

    with pytest.raises(FileExistsError):
        capture.run_segments(
            leader_port="leader",
            follower_port="follower",
            out_dir=out_dir,
            segments=("off",),
            duration_s=0,
            ack_timeout_s=0.01,
            settle_s=0,
            serial_factory=forbidden_factory,
        )
    assert opened is False


def test_capture_requires_fresh_exact_acks_and_restores_off(tmp_path):
    leader = _FakeSerial("leader")
    follower = _FakeSerial(
        "follower",
        stale=("SYNC_FAULT: delay5", "[k1_sync] fault=delay5")
    )
    results = capture.run_segments(
        leader_port="leader",
        follower_port="follower",
        out_dir=tmp_path / "capture",
        segments=("delay5", "restored"),
        duration_s=0,
        ack_timeout_s=0.05,
        settle_s=0,
        serial_factory=_serial_factory(leader, follower),
    )
    assert [result["status"] for result in results] == [
        gate_eval.BLOCKED,
        gate_eval.BLOCKED,
    ]
    assert follower.reset_count == 3
    assert follower.writes == [
        ":sync_status",
        ":sync_fault=delay5",
        ":sync_fault=off",
        ":sync_fault=off",
    ]
    index = (tmp_path / "capture" / "INDEX.md").read_text()
    assert "NOT_GATE0" in index
    assert "| restored | off |" in index
    assert leader.closed and follower.closed


def test_capture_ack_failure_still_attempts_off_restoration(tmp_path):
    leader = _FakeSerial("leader")
    follower = _FakeSerial("follower", acknowledge=False)
    with pytest.raises(capture.CaptureContractError, match="ACK missing"):
        capture.run_segments(
            leader_port="leader",
            follower_port="follower",
            out_dir=tmp_path / "capture",
            segments=("delay5",),
            duration_s=0,
            ack_timeout_s=0.01,
            settle_s=0,
            serial_factory=_serial_factory(leader, follower),
        )
    assert follower.writes == [
        ":sync_status",
        ":sync_fault=delay5",
        ":sync_fault=off",
    ]
    index = (tmp_path / "capture" / "INDEX.md").read_text()
    assert "Capture error:" in index
    assert "Restoration error:" in index


def test_segment_proof_inherits_only_captured_connection_context():
    session = "\n".join(
        [
            "host_us=0 [k1_sync] begin role=leader",
            "host_us=1 [k1_sync] link up role=leader epoch=1 handle=1 mtu=247",
            (
                "host_us=2 [k1_sync] negotiated role=leader epoch=1 "
                "interval_units=6 latency=0 mtu=247 phy_tx=2 phy_rx=2"
            ),
            "host_us=3 [k1_sync] tx seq=99 t_leader_us=3",
            (
                "host_us=10 [sync_host] segment name=delay5 phase=start "
                "t_host_us=10"
            ),
        ]
    )
    segment = "\n".join(
        [
            (
                "host_us=10 [sync_host] segment name=delay5 phase=start "
                "t_host_us=10"
            ),
            "host_us=11 [k1_sync] tx seq=0 t_leader_us=11",
            (
                "host_us=12 [sync_host] segment name=delay5 phase=end "
                "t_host_us=12"
            ),
            "",
        ]
    )
    proof = capture._proof_text(session, segment)
    assert "[k1_sync] begin role=leader" in proof
    assert "[k1_sync] link up role=leader" in proof
    assert "[k1_sync] negotiated role=leader" in proof
    assert "seq=99" not in proof
    assert "seq=0" in proof


def test_capture_probes_both_chip_and_build_identities():
    leader = _IdentitySerial(
        "F887A500", "k1_sync_probe_main_sync_only"
    )
    follower = _IdentitySerial("B489A500", "k1_sync_probe_bench")
    leader_output = io.StringIO()
    follower_output = io.StringIO()
    dual = capture.DualCapture(
        leader,
        follower,
        capture._RoleWriter(leader_output),
        capture._RoleWriter(follower_output),
    )
    observed = dual.verify_devices(
        {
            "leader": {
                "chip_id": "F887A500",
                "env": "k1_sync_probe_main_sync_only",
                "source_sha": "abcdef012345",
                "app_elf_sha256": "a" * 64,
            },
            "follower": {
                "chip_id": "B489A500",
                "env": "k1_sync_probe_bench",
                "source_sha": "abcdef012345",
                "app_elf_sha256": "a" * 64,
            },
        },
        timeout_s=0.05,
    )
    assert observed["leader"]["chip_id"] == "F887A500"
    assert observed["follower"]["env"] == "k1_sync_probe_bench"
    assert observed["leader"]["app_elf_sha256"] == "a" * 64
    assert observed["leader"]["boot_nonce"] == "0123456789abcdef"


def test_capture_rejects_postflash_image_identity_mismatch():
    leader = _IdentitySerial(
        "F887A500",
        "k1_sync_probe_main_sync_only",
        app_elf_sha256="b" * 64,
    )
    follower = _IdentitySerial("B489A500", "k1_sync_probe_bench")
    dual = capture.DualCapture(
        leader,
        follower,
        capture._RoleWriter(io.StringIO()),
        capture._RoleWriter(io.StringIO()),
    )
    with pytest.raises(capture.CaptureContractError, match="image mismatch"):
        dual.verify_devices(
            {
                "leader": {
                    "chip_id": "F887A500",
                    "env": "k1_sync_probe_main_sync_only",
                    "source_sha": "abcdef012345",
                    "app_elf_sha256": "a" * 64,
                },
                "follower": {
                    "chip_id": "B489A500",
                    "env": "k1_sync_probe_bench",
                    "source_sha": "abcdef012345",
                    "app_elf_sha256": "a" * 64,
                },
            },
            timeout_s=0.05,
        )


def test_dial_status_parser_requires_exact_complete_snapshot():
    leader = _FakeSerial("leader")
    follower = _FakeSerial("follower")
    status_line = (
        "DIAL_STATUS: linked=1 generation=4 scan_active=0 "
        "scan_start_ok=1 scan_start_fail=0 notify=3 decoded=3 "
        "enqueued=3 apply_ok=3 apply_fail=0 queue_drops=0 "
        "decode_errors=0 stale_generation_drops=0 "
        "dial_mode_apply_ok=3 confirm_write_ok=2 "
        "confirm_write_fail=0 dial_confirm_write_ok=1 "
        "last_confirm_pm=5 last_confirm_sm=2"
    )
    leader.lines.append(f"{status_line}\n".encode())
    dual = capture.DualCapture(
        leader,
        follower,
        capture._RoleWriter(io.StringIO()),
        capture._RoleWriter(io.StringIO()),
    )
    status = dual.query_leader_dial_status(timeout_s=0.05)
    assert status["generation"] == 4
    assert status["dial_confirm_write_ok"] == 1

    leader.lines.append(
        b"DIAL_STATUS: linked=1 generation=4 notify=3\n"
    )
    with pytest.raises(capture.CaptureContractError, match="response missing"):
        dual.query_leader_dial_status(timeout_s=0.01)


def test_capture_sync_status_discards_stale_lifecycle_and_records_fresh():
    stale = (
        "[k1_sync] link up role={role} epoch=99 handle=9 mtu=23",
        (
            "[k1_sync] negotiated role={role} epoch=99 interval_units=24 "
            "latency=4 mtu=23 phy_tx=1 phy_rx=1"
        ),
    )
    leader = _FakeSerial(
        "leader",
        stale=tuple(line.format(role="leader") for line in stale),
        status_epoch=7,
    )
    follower = _FakeSerial(
        "follower",
        stale=tuple(line.format(role="follower") for line in stale),
        status_epoch=8,
    )
    leader_output = io.StringIO()
    follower_output = io.StringIO()
    dual = capture.DualCapture(
        leader,
        follower,
        capture._RoleWriter(leader_output),
        capture._RoleWriter(follower_output),
    )
    status = dual.capture_sync_status(timeout_s=0.05)
    assert status["leader"]["epoch"] == 7
    assert status["follower"]["epoch"] == 8
    assert "epoch=99" not in leader_output.getvalue()
    assert "epoch=99" not in follower_output.getvalue()
    assert leader.writes == [":sync_status"]
    assert follower.writes == [":sync_status"]


@pytest.mark.parametrize(
    ("status_mode", "message"),
    (
        ("silent", "response missing"),
        ("unlinked", "reports linked=0"),
        ("malformed", "malformed lifecycle"),
        ("incoherent", "lifecycle is incoherent"),
    ),
)
def test_capture_sync_status_fails_closed(status_mode, message):
    leader = _FakeSerial("leader", status_mode=status_mode)
    follower = _FakeSerial("follower")
    dual = capture.DualCapture(
        leader,
        follower,
        capture._RoleWriter(io.StringIO()),
        capture._RoleWriter(io.StringIO()),
    )
    with pytest.raises(capture.CaptureContractError, match=message):
        dual.capture_sync_status(timeout_s=0.01)


def test_segment_proof_can_select_only_fresh_status_context():
    old = [
        "host_us=0 [k1_sync] link up role=leader epoch=1 handle=1 mtu=23",
        (
            "host_us=1 [k1_sync] negotiated role=leader epoch=1 "
            "interval_units=24 latency=4 mtu=23 phy_tx=1 phy_rx=1"
        ),
    ]
    fresh = [
        "host_us=2 [k1_sync] link up role=leader epoch=2 handle=2 mtu=247",
        (
            "host_us=3 [k1_sync] negotiated role=leader epoch=2 "
            "interval_units=6 latency=0 mtu=247 phy_tx=2 phy_rx=2"
        ),
    ]
    segment = "\n".join(
        [
            (
                "host_us=10 [sync_host] segment name=off phase=start "
                "t_host_us=10"
            ),
            "host_us=11 [k1_sync] tx seq=10 t_leader_us=11",
            (
                "host_us=12 [sync_host] segment name=off phase=end "
                "t_host_us=12"
            ),
            "",
        ]
    )
    proof = capture._proof_text(
        "\n".join(old + fresh) + "\n",
        segment,
        context_start_line=len(old),
    )
    assert "epoch=1" not in proof
    assert proof.count("[k1_sync] link up") == 1
    assert "epoch=2" in proof


def test_f2_parser_rejects_locked_capture_overrides():
    parser = f2_capture._build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(
            [
                "--case",
                "A",
                "--physical-state",
                "sync-only",
                "--out-root",
                "/tmp/evidence",
                "--run-id",
                "run",
                "--leader-port",
                "leader",
                "--follower-port",
                "follower",
                "--leader-bin",
                "leader.bin",
                "--firmware-sha",
                "a" * 40,
                "--flash-manifest",
                "flash.json",
                "--attestation",
                "attestation.json",
            ]
        )


def test_f2_order_rejects_minimal_forged_pass_manifest(tmp_path):
    raw_root = tmp_path / "_scratch" / "dual_sync_f2_abc_run"
    tracked_root = tmp_path / "artifacts" / "f2" / "run"
    tracked_root.mkdir(parents=True)
    (tracked_root / "case_A.json").write_text(
        json.dumps(
            {
                "case_status": gate_eval.PASS,
                "firmware_source_sha": "f" * 40,
                "host_source_sha": "h" * 40,
            }
        )
    )
    with pytest.raises(
        f2_capture.F2ContractError, match="schema_version"
    ):
        f2_capture.validate_case_order(
            "B",
            raw_root,
            tracked_root,
            "f" * 40,
            "h" * 40,
            tmp_path,
        )


def _remoted_counter_line(
    linked,
    value=0,
    *,
    notify_value=None,
    scan_active=None,
    scan_start_ok=1,
    scan_start_fail=0,
    stale_generation_drops=0,
):
    if notify_value is None:
        notify_value = value
    if scan_active is None:
        scan_active = 1 - linked
    return (
        "[ble_remoted] counters "
        f"linked={linked} scan_active={scan_active} "
        f"scan_start_ok={scan_start_ok} scan_start_fail={scan_start_fail} "
        f"notify={notify_value} decoded={value} enqueued={value} "
        "queue_drops=0 decode_errors=0 "
        f"stale_generation_drops={stale_generation_drops} "
        f"apply_ok={value} apply_fail=0 "
        f"link_up={linked} link_down=0 connect_fail=0 "
        f"confirm_ok={linked + (value > 0)} confirm_fail=0 "
        f"confirm_pm={5 if value else 4} confirm_sm=2"
    )


def _dial_status(
    linked,
    generation,
    value=0,
    *,
    notify_value=None,
    scan_active=None,
    scan_start_ok=1,
    scan_start_fail=0,
    stale_generation_drops=0,
):
    if notify_value is None:
        notify_value = value
    if scan_active is None:
        scan_active = 1 - linked
    return {
        "linked": linked,
        "generation": generation,
        "scan_active": scan_active,
        "scan_start_ok": scan_start_ok,
        "scan_start_fail": scan_start_fail,
        "notify": notify_value,
        "decoded": value,
        "enqueued": value,
        "apply_ok": value,
        "apply_fail": 0,
        "queue_drops": 0,
        "decode_errors": 0,
        "stale_generation_drops": stale_generation_drops,
        "dial_mode_apply_ok": value,
        "confirm_write_ok": linked + (value > 0),
        "confirm_write_fail": 0,
        "dial_confirm_write_ok": 1 if value > 0 else 0,
        "last_confirm_pm": 5 if value else 4,
        "last_confirm_sm": 2,
    }


def test_f2_case_b_requires_dial_off_and_zero_counter_delta():
    lines = []
    for index in range(10):
        lines.extend(
            (
                (
                    f"host_us={index} [k1_sync] health role=leader fps=100 "
                    "heap_min=60000 ap_p95_us=0 dial_linked=0 loss=0 dup=0"
                ),
                f"host_us={index} {_remoted_counter_line(0)}",
            )
        )
    status = {
        "baseline": _dial_status(0, 0),
        "end": _dial_status(0, 0),
    }
    result = f2_capture._analyse_dial("B", "\n".join(lines), status)
    assert result["status"] == gate_eval.PASS

    scanner_inactive = [
        line.replace("scan_active=1", "scan_active=0")
        for line in lines
    ]
    inactive_status = {
        "baseline": _dial_status(0, 0, scan_active=0),
        "end": _dial_status(0, 0, scan_active=0),
    }
    inactive = f2_capture._analyse_dial(
        "B", "\n".join(scanner_inactive), inactive_status
    )
    assert inactive["status"] == gate_eval.FAIL

    restarted_status = {
        "baseline": _dial_status(0, 0, scan_start_ok=1),
        "end": _dial_status(0, 0, scan_start_ok=2),
    }
    restarted = f2_capture._analyse_dial(
        "B", "\n".join(lines), restarted_status
    )
    assert restarted["status"] == gate_eval.FAIL

    traffic = {
        "baseline": _dial_status(0, 0),
        "end": _dial_status(0, 0, 1),
    }
    failed = f2_capture._analyse_dial("B", "\n".join(lines), traffic)
    assert failed["status"] == gate_eval.FAIL

    hidden_activity = []
    for index in range(10):
        hidden_activity.extend(
            (
                (
                    f"host_us={index} [k1_sync] health role=leader fps=100 "
                    "heap_min=60000 ap_p95_us=0 dial_linked=0 loss=0 dup=0"
                ),
                (
                    f"host_us={index} "
                    f"{_remoted_counter_line(0, min(index, 3))}"
                ),
            )
        )
    split = f2_capture._analyse_dial(
        "B", "\n".join(hidden_activity), status
    )
    assert split["status"] != gate_eval.PASS


def test_f2_case_c_requires_causal_mode_confirmation():
    lines = []
    for index in range(10):
        value = min(index, 4)
        lines.extend(
            (
                (
                    f"host_us={index} [k1_sync] health role=leader fps=100 "
                    "heap_min=60000 ap_p95_us=0 dial_linked=1 loss=0 dup=0"
                ),
                f"host_us={index} {_remoted_counter_line(1, value)}",
            )
        )
    lines.extend(
        (
            (
                "host_us=20 [ble_remoted] mode_apply record_id=5 "
                "control=primary.mode accepted=5 apply_ok=3"
            ),
            (
                "host_us=21 [ble_remoted] mode_apply record_id=6 "
                "control=primary.mode accepted=6 apply_ok=4"
            ),
            (
                "host_us=22 [ble_remoted] mode_apply record_id=7 "
                "control=primary.mode accepted=7 apply_ok=5"
            ),
            (
                "host_us=23 [ble_remoted] mode_apply record_id=8 "
                "control=primary.mode accepted=8 apply_ok=6"
            ),
            (
                "host_us=24 [ble_remoted] confirm_write ok=1 "
                "cause=dial_mode record_id=8 generation=4 pm=8 sm=2"
            ),
        )
    )
    status = {
        "baseline": _dial_status(1, 4),
        "end": _dial_status(1, 4, 4),
    }
    status["end"]["last_confirm_pm"] = 8
    result = f2_capture._analyse_dial("C", "\n".join(lines), status)
    assert result["status"] == gate_eval.PASS

    without_confirmation = "\n".join(lines[:-1])
    blocked = f2_capture._analyse_dial(
        "C", without_confirmation, status
    )
    assert blocked["status"] == gate_eval.BLOCKED

    reversed_events = lines[:-2] + [lines[-1], lines[-2]]
    reversed_result = f2_capture._analyse_dial(
        "C", "\n".join(reversed_events), status
    )
    assert reversed_result["status"] == gate_eval.BLOCKED

    fixed_periodic = []
    for index in range(10):
        fixed_periodic.extend(
            (
                (
                    f"host_us={index} [k1_sync] health role=leader fps=100 "
                    "heap_min=60000 ap_p95_us=0 dial_linked=1 loss=0 dup=0"
                ),
                f"host_us={index} {_remoted_counter_line(1, 0)}",
            )
        )
    fixed_periodic.extend(lines[-5:])
    split = f2_capture._analyse_dial(
        "C", "\n".join(fixed_periodic), status
    )
    assert split["status"] == gate_eval.BLOCKED

    error_status = json.loads(json.dumps(status))
    error_status["end"]["decode_errors"] = 1
    failed = f2_capture._analyse_dial(
        "C", "\n".join(lines), error_status
    )
    assert failed["status"] == gate_eval.FAIL

    decreasing_gauge_lines = [
        line.replace("confirm_pm=4", "confirm_pm=5").replace(
            "confirm_pm=5", "confirm_pm=3"
        )
        for line in lines[:20]
    ]
    decreasing_gauge_lines.extend(
        (
            (
                "host_us=20 [ble_remoted] mode_apply record_id=5 "
                "control=primary.mode accepted=4 apply_ok=3"
            ),
            (
                "host_us=21 [ble_remoted] mode_apply record_id=6 "
                "control=primary.mode accepted=3 apply_ok=4"
            ),
            (
                "host_us=22 [ble_remoted] mode_apply record_id=7 "
                "control=primary.mode accepted=2 apply_ok=5"
            ),
            (
                "host_us=23 [ble_remoted] mode_apply record_id=8 "
                "control=primary.mode accepted=1 apply_ok=6"
            ),
            (
                "host_us=24 [ble_remoted] confirm_write ok=1 "
                "cause=dial_mode record_id=8 generation=4 pm=1 sm=2"
            ),
        )
    )
    decreasing_status = json.loads(json.dumps(status))
    decreasing_status["baseline"]["last_confirm_pm"] = 5
    decreasing_status["end"]["last_confirm_pm"] = 1
    gauge_result = f2_capture._analyse_dial(
        "C", "\n".join(decreasing_gauge_lines), decreasing_status
    )
    assert gauge_result["status"] == gate_eval.PASS


def test_f2_case_c_periodic_samples_may_sit_inside_endpoint_window():
    lines = []
    for index in range(10):
        value = min(index + 1, 3)
        lines.extend(
            (
                (
                    f"host_us={index} [k1_sync] health role=leader fps=100 "
                    "heap_min=60000 ap_p95_us=0 dial_linked=1 loss=0 dup=0"
                ),
                f"host_us={index} {_remoted_counter_line(1, value)}",
            )
        )
    lines.extend(
        (
            (
                "host_us=20 [ble_remoted] mode_apply record_id=5 "
                "control=primary.mode accepted=5 apply_ok=3"
            ),
            (
                "host_us=21 [ble_remoted] mode_apply record_id=6 "
                "control=primary.mode accepted=6 apply_ok=4"
            ),
            (
                "host_us=22 [ble_remoted] mode_apply record_id=7 "
                "control=primary.mode accepted=7 apply_ok=5"
            ),
            (
                "host_us=23 [ble_remoted] mode_apply record_id=8 "
                "control=primary.mode accepted=8 apply_ok=6"
            ),
            (
                "host_us=24 [ble_remoted] confirm_write ok=1 "
                "cause=dial_mode record_id=8 generation=4 pm=8 sm=2"
            ),
        )
    )
    status = {
        "baseline": _dial_status(1, 4),
        "end": _dial_status(1, 4, 4),
    }
    status["end"]["last_confirm_pm"] = 8
    result = f2_capture._analyse_dial("C", "\n".join(lines), status)
    assert result["status"] == gate_eval.PASS
    assert result["checks"]["counter_endpoint_bounded"] is True
    assert result["checks"]["counter_deltas"]["notify"] == 2
    assert result["checks"]["endpoint_deltas"]["notify"] == 4


def test_f2_case_c_allows_four_records_in_one_notification():
    lines = []
    for index in range(10):
        value = min(index, 4)
        lines.extend(
            (
                (
                    f"host_us={index} [k1_sync] health role=leader fps=100 "
                    "heap_min=60000 ap_p95_us=0 dial_linked=1 loss=0 dup=0"
                ),
                (
                    f"host_us={index} "
                    f"{_remoted_counter_line(1, value, notify_value=min(value, 1))}"
                ),
            )
        )
    lines.extend(
        (
            (
                "host_us=20 [ble_remoted] mode_apply record_id=5 "
                "control=primary.mode accepted=5 apply_ok=3"
            ),
            (
                "host_us=21 [ble_remoted] mode_apply record_id=6 "
                "control=primary.mode accepted=6 apply_ok=4"
            ),
            (
                "host_us=22 [ble_remoted] mode_apply record_id=7 "
                "control=primary.mode accepted=7 apply_ok=5"
            ),
            (
                "host_us=23 [ble_remoted] mode_apply record_id=8 "
                "control=primary.mode accepted=8 apply_ok=6"
            ),
            (
                "host_us=24 [ble_remoted] confirm_write ok=1 "
                "cause=dial_mode record_id=8 generation=4 pm=8 sm=2"
            ),
        )
    )
    status = {
        "baseline": _dial_status(1, 4),
        "end": _dial_status(1, 4, 4, notify_value=1),
    }
    status["end"]["last_confirm_pm"] = 8
    result = f2_capture._analyse_dial("C", "\n".join(lines), status)
    assert result["status"] == gate_eval.PASS
    assert result["checks"]["endpoint_deltas"]["notify"] == 1
    assert result["checks"]["endpoint_deltas"]["decoded"] == 4


def test_f2_case_c_rejects_duplicate_noop_mode_records():
    lines = []
    for index in range(10):
        value = min(index, 3)
        lines.extend(
            (
                (
                    f"host_us={index} [k1_sync] health role=leader fps=100 "
                    "heap_min=60000 ap_p95_us=0 dial_linked=1 loss=0 dup=0"
                ),
                f"host_us={index} {_remoted_counter_line(1, value)}",
            )
        )
    for record_id in (5, 6, 7):
        lines.append(
            f"host_us={20 + record_id} [ble_remoted] mode_apply "
            f"record_id={record_id} control=primary.mode "
            f"accepted=5 apply_ok={record_id - 2}"
        )
    lines.append(
        "host_us=30 [ble_remoted] confirm_write ok=1 "
        "cause=dial_mode record_id=7 generation=4 pm=5 sm=2"
    )
    status = {
        "baseline": _dial_status(1, 4),
        "end": _dial_status(1, 4, 3),
    }
    status["baseline"]["last_confirm_pm"] = 5
    status["end"]["last_confirm_pm"] = 5
    result = f2_capture._analyse_dial("C", "\n".join(lines), status)
    assert result["status"] != gate_eval.PASS
    assert result["checks"]["meaningful_mode_change_count"] == 0


def test_f2_dial_status_is_fail_closed_on_missing_or_regressed_snapshot():
    lines = []
    for index in range(10):
        lines.extend(
            (
                (
                    f"host_us={index} [k1_sync] health role=leader fps=100 "
                    "heap_min=60000 ap_p95_us=0 dial_linked=1 loss=0 dup=0"
                ),
                f"host_us={index} {_remoted_counter_line(1, 3)}",
            )
        )
    missing = f2_capture._analyse_dial("C", "\n".join(lines), None)
    assert missing["status"] == gate_eval.BLOCKED

    regressed = {
        "baseline": _dial_status(1, 4, 3),
        "end": _dial_status(1, 4, 2),
    }
    result = f2_capture._analyse_dial(
        "C", "\n".join(lines), regressed
    )
    assert result["status"] == gate_eval.BLOCKED


def test_f2_runtime_continuity_blocks_same_image_reflash_between_b_and_c():
    identity = {
        role: {
            "app_elf_sha256": (
                "a" * 64 if role == "leader" else "b" * 64
            ),
            "git": "c" * 7,
            "env": (
                "k1_sync_probe_main"
                if role == "leader"
                else "k1_sync_probe_bench"
            ),
            "boot_nonce": "0123456789abcdef",
            "uptime_ms": 3000,
            "reset_reason": 1,
        }
        for role in ("leader", "follower")
    }
    flash_payload = {
        "uploads": {
            role: {
                "env": (
                    "k1_sync_probe_main"
                    if role == "leader"
                    else "k1_sync_probe_bench"
                ),
                "app_elf_sha256": (
                    "a" * 64 if role == "leader" else "b" * 64
                ),
                "postflash_readback": {
                    "boot_nonce": "0123456789abcdef",
                    "uptime_ms": 1000,
                    "reset_reason": 1,
                }
            }
            for role in ("leader", "follower")
        }
    }
    prior = {
        role: {
            "boot_nonce": "0123456789abcdef",
            "uptime_ms": 2000,
            "reset_reason": 1,
        }
        for role in ("leader", "follower")
    }
    _runtime, result = f2_capture._runtime_continuity(
        identity,
        flash_payload,
        prior,
        case_name="C1",
        firmware_sha="c" * 40,
    )
    assert result["status"] == gate_eval.PASS

    identity["leader"]["boot_nonce"] = "fedcba9876543210"
    _runtime, reset = f2_capture._runtime_continuity(
        identity,
        flash_payload,
        prior,
        case_name="C1",
        firmware_sha="c" * 40,
    )
    assert reset["status"] == gate_eval.BLOCKED


def test_f2_case_status_preserves_observed_failures():
    assert (
        f2_capture._case_status(
            gate_eval.PASS, gate_eval.FAIL, gate_eval.PASS
        )
        == gate_eval.FAIL
    )
    assert (
        f2_capture._case_status(
            gate_eval.PASS, gate_eval.BLOCKED, gate_eval.PASS
        )
        == gate_eval.BLOCKED
    )


def test_f2_firmware_sha_is_separate_ancestor_of_harness_head():
    """Firmware SHA must be a strict ancestor of harness HEAD (distinct).

    CI host-regression uses checkout fetch-depth: 2 so HEAD^ resolves.
    On a depth-1 shallow clone (or missing parent), skip rather than fail —
    the invariant still runs whenever history is deep enough.
    """
    repo_root = Path(__file__).resolve().parents[1]
    host_sha = f2_capture._git_head(repo_root)
    try:
        parent_sha = f2_capture._resolve_commit(repo_root, f"{host_sha}^")
    except f2_capture.F2ContractError as error:
        pytest.skip(
            "parent of HEAD unavailable (shallow clone?): "
            f"{error}"
        )
    f2_capture._require_ancestor(repo_root, parent_sha, host_sha)


def _write_test_partition_table(path: Path) -> None:
    app_entry = struct.pack(
        "<HBBII16sI",
        0x50AA,
        0,
        0x10,
        0x10000,
        0x640000,
        b"app0".ljust(16, b"\0"),
        0,
    )
    path.write_bytes(app_entry + b"\xff" * (0xC00 - len(app_entry)))


def _make_f2_image_set(tmp_path, firmware_sha="a" * 40):
    from scripts.dual_sync_probe import f2_image_set

    frozen = tmp_path / "_scratch" / "frozen-images"
    frozen.mkdir(parents=True)
    partition_path = frozen / "partitions.bin"
    _write_test_partition_table(partition_path)
    images = {}
    app_identities = {}
    for env in f2_image_set.REQUIRED_ENVS:
        env_root = frozen / env
        env_root.mkdir()
        bin_path = env_root / "firmware.bin"
        elf_path = env_root / "firmware.elf"
        bin_path.write_bytes(
            f"{env}-reviewed-bin-{firmware_sha[:7]}".encode()
        )
        elf_path.write_bytes(f"{env}-reviewed-elf".encode())
        app_identity = f2_capture._sha256(elf_path)
        app_identities[str(bin_path)] = app_identity
        images[env] = {
            "role": (
                "follower"
                if env == "k1_sync_probe_bench"
                else "leader"
            ),
            "required_chip": (
                "B489A500"
                if env == "k1_sync_probe_bench"
                else "F887A500"
            ),
            "available": True,
            "bin_path": f"{env}/firmware.bin",
            "bin_sha256": f2_capture._sha256(bin_path),
            "elf_path": f"{env}/firmware.elf",
            "elf_sha256": app_identity,
            "app_elf_sha256": app_identity,
        }
    payload = {
        "schema_version": 2,
        "status": "READY",
        "blockers": [],
        "firmware_source_sha": firmware_sha,
        "raw_pack_relative_path": "_scratch/frozen-images",
        "esptool_package": f2_image_set.ESPTOOL_PACKAGE,
        "package_provenance": {
            "platformio": "6.1.19",
            "python": "3.12.0",
            "platform": "54.03.20",
            "framework_arduino": "3.2.0",
            "framework_espidf_libraries": "5.4.0+sha.2f7dcd862a",
            "toolchain_xtensa": "14.2.0+20241119",
            "toolchain_riscv": "14.2.0+20241119",
            "nimble_arduino": "2.5.0",
            "fastled": "3.10.3",
            "fixedpoints": "1.1.2",
            "m5rotate8": "0.4.1",
        },
        "partition_table": {
            "path": "partitions.bin",
            "sha256": f2_capture._sha256(partition_path),
            "offset": 0x8000,
            "size": 0xC00,
            "application_label": "app0",
            "application_offset": 0x10000,
            "application_size": 0x640000,
        },
        "images": images,
    }
    manifest_path = frozen / "image-set.json"
    manifest_path.write_text(json.dumps(payload))
    return manifest_path, app_identities


def _flash_args(tmp_path, case, run_id, image_set):
    tracked_root = tmp_path / f2_capture.TRACKED_F2_REL / run_id
    tracked = tracked_root / "attestations"
    tracked.mkdir(parents=True)
    attestation = tracked / f"case_{case}.json"
    attestation.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "case": case,
                "confirmed_by": "Captain",
                "gpio_wiring_confirmed": True,
                "common_ground_confirmed": True,
                "logic_voltage": "3V3",
                "k718_state": "irrelevant" if case == "A" else "off",
            }
        )
    )
    runtime = tracked_root / "runtime"
    f2_ports.write_ports_manifest(
        "pre_A",
        runtime,
        {
            "leader": {
                "port": "leader-port",
                "usb_serial": f2_capture.LEADER_USB_SERIAL,
                "chip_id": f2_capture.LEADER_CHIP,
            },
            "follower": {
                "port": "follower-port",
                "usb_serial": f2_capture.FOLLOWER_USB_SERIAL,
                "chip_id": f2_capture.FOLLOWER_CHIP,
            },
        },
        host_execution_sha="b" * 40,
        firmware_source_sha="a" * 40,
        created_at_utc="2026-07-28T01:00:00Z",
    )
    return SimpleNamespace(
        case=case,
        run_id=run_id,
        host_execution_sha="b" * 40,
        firmware_source_sha="a" * 40,
        image_set_manifest=image_set,
        ports_manifest=runtime / "ports_pre_A.json",
        run_root=tmp_path / "_scratch" / f"dual_sync_f2_abc_{run_id}",
        attestation=attestation,
        leader_port="leader-port",
        follower_port="follower-port",
        readback_timeout_s=0.01,
    )


def _prepare_f2_flash_test(monkeypatch, app_identities):
    from scripts.dual_sync_probe import f2_image_set

    monkeypatch.setattr(f2_flash, "_require_clean_inputs", lambda _root: None)
    monkeypatch.setattr(f2_capture, "_git_head", lambda _root: "b" * 40)
    monkeypatch.setattr(
        f2_capture, "_resolve_commit", lambda _root, value: value
    )
    monkeypatch.setattr(
        f2_capture, "_require_ancestor", lambda *_values: None
    )
    monkeypatch.setattr(
        f2_image_set,
        "_app_elf_sha256",
        lambda path: app_identities[str(path)],
    )
    monkeypatch.setattr(
        f2_capture,
        "_app_elf_sha256",
        lambda path: app_identities[str(path)],
    )


def _write_f2_guard_result(command, log_path, append):
    mode = "a" if append else "x"
    if command[:2] != [
        "python3",
        "scripts/platformio/k1_upload_guard.py",
    ]:
        return None
    env = command[command.index("--env") + 1]
    port = command[command.index("--upload-port") + 1]
    positive = (
        port == "leader-port"
        and env in ("k1_sync_probe_main", "k1_sync_probe_main_sync_only")
    ) or (port == "follower-port" and env == "k1_sync_probe_bench")
    with log_path.open(mode) as output:
        if positive:
            output.write("verified as target\n")
        else:
            output.write("USB serial mismatch; expected cross target\n")
    return 0 if positive else 2


def _f2_startup_reader(args):
    def reader(case_name, *, output_dir, repo_root, timeout_s):
        del timeout_s
        logs = {}
        for role in ("leader", "follower"):
            path = output_dir / f"case_{case_name}_startup_{role}.log"
            path.write_text(f"{role} startup proof\n")
            logs[role] = f2_capture._evidence_record(path, repo_root)
        return (
            {
                "leader": {
                    "port": args.leader_port,
                    "usb_serial": f2_capture.LEADER_USB_SERIAL,
                    "chip_id": f2_capture.LEADER_CHIP,
                },
                "follower": {
                    "port": args.follower_port,
                    "usb_serial": f2_capture.FOLLOWER_USB_SERIAL,
                    "chip_id": f2_capture.FOLLOWER_CHIP,
                },
            },
            {
                "status": gate_eval.PASS,
                "checks": {
                    "leader_advertising_ready": True,
                    "follower_scan_started": True,
                    "follower_uuid_discovered": True,
                    "leader_link_ready_snapshot": True,
                    "follower_link_ready_snapshot": True,
                },
                "logs": logs,
            },
        )

    return reader


def test_f2_image_set_requires_exact_complete_reviewed_set(
    tmp_path, monkeypatch,
):
    from scripts.dual_sync_probe import f2_image_set

    manifest_path, app_identities = _make_f2_image_set(tmp_path)
    monkeypatch.setattr(
        f2_image_set,
        "_app_elf_sha256",
        lambda path: app_identities[str(path)],
    )
    loaded = f2_image_set.load(manifest_path, repo_root=tmp_path)
    assert loaded["firmware_source_sha"] == "a" * 40
    assert set(loaded["images"]) == set(f2_image_set.REQUIRED_ENVS)
    assert loaded["partition_table"]["application_offset"] == 0x10000
    assert "host_execution_sha" not in loaded

    payload = json.loads(manifest_path.read_text())
    payload["host_execution_sha"] = "b" * 40
    manifest_path.write_text(json.dumps(payload))
    with pytest.raises(
        f2_image_set.F2ImageSetError, match="host execution"
    ):
        f2_image_set.load(manifest_path, repo_root=tmp_path)


def test_f2_image_set_rejects_missing_or_mutated_images(
    tmp_path, monkeypatch,
):
    from scripts.dual_sync_probe import f2_image_set

    manifest_path, app_identities = _make_f2_image_set(tmp_path)
    monkeypatch.setattr(
        f2_image_set,
        "_app_elf_sha256",
        lambda path: app_identities[str(path)],
    )
    payload = json.loads(manifest_path.read_text())
    del payload["images"]["k1_sync_probe_main_sync_only"]
    manifest_path.write_text(json.dumps(payload))
    with pytest.raises(f2_image_set.F2ImageSetError, match="exactly"):
        f2_image_set.load(manifest_path, repo_root=tmp_path)

    manifest_path, app_identities = _make_f2_image_set(
        tmp_path / "second"
    )
    monkeypatch.setattr(
        f2_image_set,
        "_app_elf_sha256",
        lambda path: app_identities[str(path)],
    )
    (
        manifest_path.parent
        / "k1_sync_probe_bench"
        / "firmware.bin"
    ).write_bytes(b"mutated")
    with pytest.raises(f2_image_set.F2ImageSetError, match="hash mismatch"):
        f2_image_set.load(manifest_path, repo_root=tmp_path / "second")


def test_f2_image_set_blocked_status_stops_before_artifact_access(
    tmp_path,
):
    from scripts.dual_sync_probe import f2_image_set

    manifest_path, _app_identities = _make_f2_image_set(tmp_path)
    payload = json.loads(manifest_path.read_text())
    payload["status"] = "BLOCKED"
    payload["blockers"] = ["sync-only image missing"]
    manifest_path.write_text(json.dumps(payload))
    with pytest.raises(
        f2_image_set.F2ImageSetError,
        match="reviewed image set is BLOCKED",
    ):
        f2_image_set.load(manifest_path, repo_root=tmp_path)


def test_f2_flash_parser_requires_image_set_and_has_no_case_c_path():
    parser = f2_flash._build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(
            [
                "--case", "C",
                "--host-execution-sha", "b" * 40,
                "--firmware-source-sha", "a" * 40,
                "--image-set-manifest", "image-set.json",
                "--ports-manifest", "ports.json",
                "--run-root", "_scratch/dual_sync_f2_abc_run",
                "--attestation", "attestation.json",
            ]
        )
    with pytest.raises(SystemExit):
        parser.parse_args(
            [
                "--case", "A",
                "--host-execution-sha", "b" * 40,
                "--firmware-source-sha", "a" * 40,
                "--ports-manifest", "ports.json",
                "--run-root", "_scratch/dual_sync_f2_abc_run",
                "--attestation", "attestation.json",
            ]
        )


def test_f2_flash_validates_both_partitions_before_app_only_writes(
    tmp_path, monkeypatch,
):
    manifest_path, app_identities = _make_f2_image_set(tmp_path)
    args = _flash_args(tmp_path, "A", "app_only", manifest_path)
    _prepare_f2_flash_test(monkeypatch, app_identities)
    commands = []
    expected_partition = (manifest_path.parent / "partitions.bin").read_bytes()

    def runner(command, log_path, *, append):
        commands.append(command)
        guard_result = _write_f2_guard_result(
            command, log_path, append
        )
        if guard_result is not None:
            return guard_result
        mode = "a" if append else "x"
        with log_path.open(mode) as output:
            output.write("esptool operation\n")
        if "read_flash" in command:
            Path(command[-1]).write_bytes(expected_partition)
        return 0

    def postflash(usb_serial, expected, _timeout):
        port = (
            args.leader_port
            if usb_serial == f2_capture.LEADER_USB_SERIAL
            else args.follower_port
        )
        return {
            "port": port,
            "chip_id": expected["chip_id"],
            "version": "40103",
            "git": "a" * 7,
            "epoch": 1,
            "env": expected["env"],
            "app_elf_sha256": expected["app_elf_sha256"],
            "boot_nonce": "0123456789abcdef",
            "uptime_ms": 1000,
            "reset_reason": 1,
        }

    result = f2_flash.run(
        args,
        command_runner=runner,
        identity_reader=postflash,
        preflash_reader=lambda port, usb, chip, _timeout: {
            "port": port,
            "usb_serial": usb,
            "chip_id": chip,
        },
        startup_reader=_f2_startup_reader(args),
        repo_root_override=tmp_path,
    )
    first_write = next(
        index for index, command in enumerate(commands)
        if "write_flash" in command
    )
    assert sum("read_flash" in command for command in commands[:first_write]) == 2
    assert sum(
        command[:2]
        == ["python3", "scripts/platformio/k1_upload_guard.py"]
        for command in commands[:first_write]
    ) == 4
    guard_calls = {
        (
            command[command.index("--env") + 1],
            command[command.index("--upload-port") + 1],
        )
        for command in commands[:first_write]
        if command[:2]
        == ["python3", "scripts/platformio/k1_upload_guard.py"]
    }
    assert guard_calls == {
        ("k1_sync_probe_main_sync_only", "leader-port"),
        ("k1_sync_probe_bench", "leader-port"),
        ("k1_sync_probe_bench", "follower-port"),
        ("k1_sync_probe_main_sync_only", "follower-port"),
    }
    assert not any(
        command[:2] == ["bash", "scripts/agent/pio-build.sh"]
        or command[:2] == ["pio", "run"]
        for command in commands
    )
    writes = [command for command in commands if "write_flash" in command]
    assert len(writes) == 2
    assert writes[0][-1].endswith("k1_sync_probe_bench/firmware.bin")
    assert writes[1][-1].endswith(
        "k1_sync_probe_main_sync_only/firmware.bin"
    )
    assert all(
        command[command.index("write_flash") + 1] == "0x10000"
        for command in writes
    )
    assert all(
        command[
            command.index("--package") + 1
        ] == "tool-esptoolpy@4.8.9"
        for command in writes
    )
    assert result["host_execution_sha"] == "b" * 40
    assert result["firmware_source_sha"] == "a" * 40
    assert "upload_controller_sha" not in result


def test_f2_flash_partition_mismatch_blocks_without_write_and_never_overwrites(
    tmp_path, monkeypatch,
):
    manifest_path, app_identities = _make_f2_image_set(tmp_path)
    args = _flash_args(tmp_path, "A", "partition_fail", manifest_path)
    _prepare_f2_flash_test(monkeypatch, app_identities)
    commands = []

    def runner(command, log_path, *, append):
        commands.append(command)
        guard_result = _write_f2_guard_result(
            command, log_path, append
        )
        if guard_result is not None:
            return guard_result
        mode = "a" if append else "x"
        with log_path.open(mode) as output:
            output.write("esptool operation\n")
        if "read_flash" in command:
            Path(command[-1]).write_bytes(b"wrong partition table")
        return 0

    with pytest.raises(f2_flash.F2FlashError, match="partition"):
        f2_flash.run(
            args,
            command_runner=runner,
            preflash_reader=lambda port, usb, chip, _timeout: {
                "port": port,
                "usb_serial": usb,
                "chip_id": chip,
            },
            repo_root_override=tmp_path,
        )
    assert not any("write_flash" in command for command in commands)
    failure_path = (
        tmp_path / f2_capture.TRACKED_F2_REL / args.run_id
        / "uploads" / "flash_A.json"
    )
    blocked = json.loads(failure_path.read_text())
    assert blocked["status"] == gate_eval.BLOCKED
    assert blocked["write_actions"] == []
    original = failure_path.read_bytes()
    with pytest.raises(f2_flash.F2FlashError, match="overwrite"):
        f2_flash.run(
            args,
            command_runner=runner,
            preflash_reader=lambda *_values: pytest.fail(
                "device action after existing evidence"
            ),
            repo_root_override=tmp_path,
        )
    assert failure_path.read_bytes() == original


def test_f2_flash_cross_target_guard_must_reject_before_write(
    tmp_path, monkeypatch,
):
    manifest_path, app_identities = _make_f2_image_set(tmp_path)
    args = _flash_args(tmp_path, "A", "cross_guard_fail", manifest_path)
    _prepare_f2_flash_test(monkeypatch, app_identities)
    commands = []

    def runner(command, log_path, *, append):
        commands.append(command)
        with log_path.open("a" if append else "x") as output:
            output.write("verified as target\n")
        return 0

    with pytest.raises(
        f2_flash.F2FlashError, match="cross-target guard did not fail closed"
    ):
        f2_flash.run(
            args,
            command_runner=runner,
            preflash_reader=lambda port, usb, chip, _timeout: {
                "port": port,
                "usb_serial": usb,
                "chip_id": chip,
            },
            repo_root_override=tmp_path,
        )
    assert not any("read_flash" in command for command in commands)
    assert not any("write_flash" in command for command in commands)


def test_f2_flash_manifest_binds_preserved_images_and_preflash_identity(
    tmp_path, monkeypatch,
):
    manifest_path, app_identities = _make_f2_image_set(tmp_path)
    args = _flash_args(tmp_path, "A", "consumer", manifest_path)
    _prepare_f2_flash_test(monkeypatch, app_identities)
    partition = (manifest_path.parent / "partitions.bin").read_bytes()

    def runner(command, log_path, *, append):
        guard_result = _write_f2_guard_result(
            command, log_path, append
        )
        if guard_result is not None:
            return guard_result
        with log_path.open("a" if append else "x") as output:
            output.write("esptool operation\n")
        if "read_flash" in command:
            Path(command[-1]).write_bytes(partition)
        return 0

    def postflash(usb_serial, expected, _timeout):
        port = (
            args.leader_port
            if usb_serial == f2_capture.LEADER_USB_SERIAL
            else args.follower_port
        )
        return {
            "port": port,
            "chip_id": expected["chip_id"],
            "version": "test",
            "git": "a" * 7,
            "epoch": 1,
            "env": expected["env"],
            "app_elf_sha256": expected["app_elf_sha256"],
            "boot_nonce": (
                "0123456789abcdef"
                if port == args.leader_port
                else "fedcba9876543210"
            ),
            "uptime_ms": 1000,
            "reset_reason": 1,
        }

    flash = f2_flash.run(
        args,
        command_runner=runner,
        identity_reader=postflash,
        preflash_reader=lambda port, usb, chip, _timeout: {
            "port": port,
            "usb_serial": usb,
            "chip_id": chip,
        },
        startup_reader=_f2_startup_reader(args),
        repo_root_override=tmp_path,
    )
    tracked_root = (
        tmp_path / f2_capture.TRACKED_F2_REL / args.run_id
    )
    result, binaries = f2_capture._validate_flash_manifest(
        tracked_root / "uploads" / "flash_A.json",
        case_name="A",
        firmware_sha="a" * 40,
        host_sha="b" * 40,
        out_root=args.run_root,
        tracked_root=tracked_root,
        repo_root=tmp_path,
        ports={
            "leader": args.leader_port,
            "follower": args.follower_port,
        },
    )
    assert result == flash
    assert binaries["leader"]["bin_sha256"] == flash["uploads"][
        "leader"
    ]["bin_sha256"]
    assert all(
        "run" not in upload.get("write_command", [])
        for upload in flash["uploads"].values()
    )


def test_f2_evidence_rejects_intermediate_and_prior_manifest_symlinks(
    tmp_path,
):
    outside = tmp_path / "outside"
    outside.mkdir()
    evidence = outside / "evidence.json"
    evidence.write_text("{}")
    tracked_root = tmp_path / "tracked" / "run"
    tracked_root.mkdir(parents=True)
    (tracked_root / "uploads").symlink_to(outside, target_is_directory=True)
    with pytest.raises(f2_capture.F2ContractError, match="symlink"):
        f2_capture._require_direct_file(
            tracked_root / "uploads" / "evidence.json",
            tracked_root / "uploads",
            "evidence",
        )

    prior_target = outside / "case_A.json"
    prior_target.write_text("{}")
    (tracked_root / "case_A.json").symlink_to(prior_target)
    with pytest.raises(f2_capture.F2ContractError, match="symlink"):
        f2_capture.validate_case_order(
            "B",
            tmp_path / "_scratch" / "dual_sync_f2_abc_run",
            tracked_root,
            "a" * 40,
            "a" * 40,
            tmp_path,
        )


def _persistent_segment_pair(name: str, host_offset: int):
    leader, follower = synth.generate_log_pair(
        _clean(duration_s=10.0), seed=SEED
    )

    def split(text, role):
        context = []
        measurements = []
        for line in text.splitlines():
            record = logfmt.parse_line(line)
            if isinstance(
                record, (logfmt.Begin, logfmt.LinkUp, logfmt.Negotiated)
            ):
                context.append(line)
            else:
                prefix, payload = line.split(" ", 1)
                host_us = int(prefix.split("=", 1)[1]) + host_offset
                measurements.append(f"host_us={host_us} {payload}")
        start = host_offset + 5
        end = host_offset + 10_100_000
        start_line = (
            f"host_us={start} [sync_host] segment name={name} "
            f"phase=start t_host_us={start}"
        )
        end_line = (
            f"host_us={end} [sync_host] segment name={name} "
            f"phase=end t_host_us={end}"
        )
        session = "\n".join(context + [start_line]) + "\n"
        segment = "\n".join([start_line] + measurements + [end_line]) + "\n"
        return capture._proof_text(session, segment)

    return split(leader, "leader"), split(follower, "follower")


def test_two_segments_reuse_one_captured_connection_without_prior_metrics():
    for name, offset in (("delay5", 0), ("restored", 20_000_000)):
        leader, follower = _persistent_segment_pair(name, offset)
        verdict = gate_eval.evaluate(
            leader, follower, strict_proof=True
        )
        assert verdict["link_ready"]["status"] == gate_eval.PASS
        assert verdict["diagnostics"]["transport_expected"] == 330
