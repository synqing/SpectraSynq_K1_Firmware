"""Fail-closed host contract for dual-sync oracle schema v2."""

from __future__ import annotations

import dataclasses
import io
import json
from pathlib import Path

import pytest

from scripts.dual_sync_probe import (
    capture,
    correlate,
    f2_capture,
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
        if self.acknowledge:
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
    def __init__(self, chip_id, env, git_hash="abcdef0"):
        role = "leader" if "main" in env else "follower"
        super().__init__(role)
        self.chip_id = chip_id
        self.env = env
        self.git_hash = git_hash

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
            },
            "follower": {
                "chip_id": "B489A500",
                "env": "k1_sync_probe_bench",
                "source_sha": "abcdef012345",
            },
        },
        timeout_s=0.05,
    )
    assert observed["leader"]["chip_id"] == "F887A500"
    assert observed["follower"]["env"] == "k1_sync_probe_bench"


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
                "--leader-port",
                "leader",
                "--follower-port",
                "follower",
                "--leader-bin",
                "leader.bin",
                "--follower-bin",
                "follower.bin",
                "--segments",
                "delay5",
            ]
        )


def test_f2_order_blocks_direct_b_or_c(tmp_path):
    with pytest.raises(f2_capture.F2ContractError, match="invalid prior"):
        f2_capture.validate_case_order("B", tmp_path, "abc")
    case_a = tmp_path / "case_A"
    case_a.mkdir()
    (case_a / "MANIFEST.json").write_text(
        json.dumps({"case_status": "BLOCKED", "source_sha": "abc"})
    )
    with pytest.raises(f2_capture.F2ContractError, match="Case A PASS"):
        f2_capture.validate_case_order("B", tmp_path, "abc")


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
