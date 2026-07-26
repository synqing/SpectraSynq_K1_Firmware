"""Fail-closed dual-sync gate evaluator (schema version 2)."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Dict, Iterable, Optional

from . import correlate as _corr
from . import logfmt

PASS = "PASS"
FAIL = "FAIL"
BLOCKED = "BLOCKED"
UNMEASURED = "UNMEASURED"
STATUS_EXIT = {PASS: 0, FAIL: 1, BLOCKED: 2, UNMEASURED: 3}
INPUT_ERROR_EXIT = 4

DEFAULT_CLOCK_ERR_P95_US = 4000
DEFAULT_LATENESS_P999_US = 30000
DEFAULT_E2E_US = 50000
DEFAULT_D_US = 30000
DEFAULT_FPS_FLOOR = 90.0
DEFAULT_HEAP_MIN_FLOOR = 20000
DEFAULT_AP_P95_US_MAX = 7500
DEFAULT_DIAL_UPTIME_MIN = 1.0
DEFAULT_STREAM_LOSS_MAX = 0
DEFAULT_APPLY_LOSS_MAX = 0
DEFAULT_MIN_TX = 300
DEFAULT_MIN_RX = 300
DEFAULT_MIN_APPLY = 300
DEFAULT_MIN_CLK = 10
DEFAULT_MIN_GPIO_ROUNDS = 10


def _r_us(value: Optional[float]) -> Optional[int]:
    return None if value is None else int(round(value))


def _r6(value: Optional[float]) -> Optional[float]:
    return None if value is None else round(value, 6)


def _status_from_children(statuses: Iterable[str]) -> str:
    statuses = list(statuses)
    if any(status == FAIL for status in statuses):
        return FAIL
    if any(status == BLOCKED for status in statuses):
        return BLOCKED
    if any(status == UNMEASURED for status in statuses):
        return UNMEASURED
    return PASS


def _records(parsed: logfmt.ParsedLog, kind):
    return [record for record in parsed.records if isinstance(record, kind)]


def _entry_host(parsed: logfmt.ParsedLog, target: object) -> Optional[int]:
    for entry in parsed.entries:
        if entry.record is target:
            return entry.host_us
    return None


def _epoch_view(parsed: logfmt.ParsedLog) -> logfmt.ParsedLog:
    """Select evidence at or after the sole role-local link-up."""
    link_ups = _records(parsed, logfmt.LinkUp)
    if len(link_ups) != 1:
        return logfmt.ParsedLog(total_lines=parsed.total_lines)
    start = _entry_host(parsed, link_ups[0])
    if start is None:
        return logfmt.ParsedLog(total_lines=parsed.total_lines)
    entries = [
        entry
        for entry in parsed.entries
        if entry.host_us is not None and entry.host_us >= start
    ]
    line_indexes = {entry.line_index for entry in entries}
    return logfmt.ParsedLog(
        records=[entry.record for entry in entries],
        entries=entries,
        anchors=[
            anchor for anchor in parsed.anchors if anchor[0] in line_indexes
        ],
        total_lines=parsed.total_lines,
        skipped_lines=parsed.skipped_lines,
        contract_errors=list(parsed.contract_errors),
    )


def link_ready(
    leader: logfmt.ParsedLog,
    follower: logfmt.ParsedLog,
    leader_epoch: logfmt.ParsedLog,
    follower_epoch: logfmt.ParsedLog,
    correlation: _corr.Correlation,
    *,
    min_tx: int = DEFAULT_MIN_TX,
    min_rx: int = DEFAULT_MIN_RX,
    min_apply: int = DEFAULT_MIN_APPLY,
    min_clk: int = DEFAULT_MIN_CLK,
    min_gpio_rounds: int = DEFAULT_MIN_GPIO_ROUNDS,
) -> dict:
    leader_up = _records(leader, logfmt.LinkUp)
    follower_up = _records(follower, logfmt.LinkUp)
    leader_down = _records(leader, logfmt.LinkDown)
    follower_down = _records(follower, logfmt.LinkDown)
    resets = _records(leader, logfmt.Reset) + _records(follower, logfmt.Reset)
    leader_negotiated = _records(leader_epoch, logfmt.Negotiated)
    follower_negotiated = _records(follower_epoch, logfmt.Negotiated)
    post_link_begins = _records(leader_epoch, logfmt.Begin) + _records(
        follower_epoch, logfmt.Begin
    )

    coherent_up = len(leader_up) == 1 and len(follower_up) == 1
    no_break = not leader_down and not follower_down and not resets
    negotiated = (
        len(leader_negotiated) == 1
        and len(follower_negotiated) == 1
        and coherent_up
        and leader_negotiated[0].epoch == leader_up[0].epoch
        and follower_negotiated[0].epoch == follower_up[0].epoch
    )
    negotiated_values_valid = negotiated and all(
        6 <= record.interval_units <= 3200
        and 0 <= record.latency <= 499
        and record.mtu >= 23
        and record.phy_tx in (1, 2, 3)
        and record.phy_rx in (1, 2, 3)
        for record in leader_negotiated + follower_negotiated
    )
    negotiated_values_agree = (
        negotiated_values_valid
        and leader_negotiated[0].interval_units
        == follower_negotiated[0].interval_units
        and leader_negotiated[0].latency == follower_negotiated[0].latency
        and leader_negotiated[0].mtu == follower_negotiated[0].mtu
        and leader_negotiated[0].phy_tx == follower_negotiated[0].phy_rx
        and leader_negotiated[0].phy_rx == follower_negotiated[0].phy_tx
    )

    overlap_us: Optional[int] = None
    if coherent_up:
        leader_start = _entry_host(leader, leader_up[0])
        follower_start = _entry_host(follower, follower_up[0])
        leader_times = leader.host_times()
        follower_times = follower.host_times()
        if (
            leader_start is not None
            and follower_start is not None
            and leader_times
            and follower_times
        ):
            overlap_us = min(max(leader_times), max(follower_times)) - max(
                leader_start, follower_start
            )
    host_overlap = overlap_us is not None and overlap_us > 0

    checks: Dict[str, dict] = {
        "single_link_epoch": {
            "ok": coherent_up and no_break and not post_link_begins,
            "leader_up": len(leader_up),
            "follower_up": len(follower_up),
            "leader_down": len(leader_down),
            "follower_down": len(follower_down),
            "resets": len(resets),
            "post_link_begin": len(post_link_begins),
        },
        "host_epoch_overlap": {"ok": host_overlap, "overlap_us": overlap_us},
        "negotiated_both_roles": {
            "ok": negotiated_values_agree,
            "leader_records": len(leader_negotiated),
            "follower_records": len(follower_negotiated),
            "values_valid": negotiated_values_valid,
            "values_agree": negotiated_values_agree,
        },
        "leader_tx": {
            "ok": correlation.leader_tx_count >= min_tx,
            "value": correlation.leader_tx_count,
            "minimum": min_tx,
        },
        "follower_rx": {
            "ok": correlation.follower_rx_count >= min_rx,
            "value": correlation.follower_rx_count,
            "minimum": min_rx,
        },
        "follower_apply": {
            "ok": correlation.follower_apply_count >= min_apply,
            "value": correlation.follower_apply_count,
            "minimum": min_apply,
        },
        "follower_clk_records": {
            "ok": correlation.follower_clk_records >= min_clk,
            "value": correlation.follower_clk_records,
            "minimum": min_clk,
        },
        "gpio_complete_rounds": {
            "ok": len(correlation.rounds) >= min_gpio_rounds,
            "value": len(correlation.rounds),
            "minimum": min_gpio_rounds,
        },
        "transport_expected": {
            "ok": correlation.transport_expected > 0,
            "value": correlation.transport_expected,
        },
        "leader_tx_dense": {
            "ok": (
                correlation.leader_tx_gap == 0
                and correlation.leader_tx_dup == 0
                and correlation.leader_tx_reorder == 0
            ),
            "missing": correlation.leader_tx_gap,
            "duplicate": correlation.leader_tx_dup,
            "reorder": correlation.leader_tx_reorder,
        },
        "follower_sequence_integrity": {
            "ok": (
                correlation.transport_dup == 0
                and correlation.transport_reorder == 0
                and correlation.transport_unexpected == 0
                and correlation.apply_dup == 0
                and correlation.apply_reorder == 0
                and correlation.apply_unexpected == 0
            ),
            "rx_duplicate": correlation.transport_dup,
            "rx_reorder": correlation.transport_reorder,
            "rx_unexpected": correlation.transport_unexpected,
            "apply_duplicate": correlation.apply_dup,
            "apply_reorder": correlation.apply_reorder,
            "apply_unexpected": correlation.apply_unexpected,
        },
    }
    status = PASS if all(check["ok"] for check in checks.values()) else BLOCKED
    return {"status": status, "checks": checks}


def _timing_gate(
    value: Optional[float], threshold: int, sample_count: int
) -> dict:
    if sample_count == 0 or value is None:
        status = BLOCKED
    else:
        status = PASS if value <= threshold else FAIL
    return {
        "status": status,
        "value_us": _r_us(value),
        "threshold_us": threshold,
        "n": sample_count,
    }


def _floor_subgate(value, floor, *, missing=BLOCKED) -> dict:
    if value is None:
        status = missing
    else:
        status = PASS if value >= floor else FAIL
    return {"status": status, "value": value, "floor": floor}


def _ceiling_subgate(
    value, ceiling, *, zero_unmeasured: bool = False, missing=BLOCKED
) -> dict:
    if value is None:
        status = missing
    elif zero_unmeasured and value == 0:
        status = UNMEASURED
    else:
        status = PASS if value <= ceiling else FAIL
    return {"status": status, "value": value, "ceiling": ceiling}


def _blocked_gate() -> dict:
    return {"status": BLOCKED, "value_us": None, "threshold_us": None, "n": 0}


def evaluate(
    leader_text,
    follower_text,
    clock_err_p95_us: int = DEFAULT_CLOCK_ERR_P95_US,
    lateness_p999_us: int = DEFAULT_LATENESS_P999_US,
    e2e_us: int = DEFAULT_E2E_US,
    d_us: int = DEFAULT_D_US,
    fps_floor: float = DEFAULT_FPS_FLOOR,
    heap_min_floor: int = DEFAULT_HEAP_MIN_FLOOR,
    ap_p95_us_max: int = DEFAULT_AP_P95_US_MAX,
    dial_uptime_min: float = DEFAULT_DIAL_UPTIME_MIN,
    stream_loss_max: int = DEFAULT_STREAM_LOSS_MAX,
    apply_loss_max: int = DEFAULT_APPLY_LOSS_MAX,
    *,
    strict_proof: bool = False,
) -> dict:
    del d_us  # retained CLI compatibility; gate 2 threshold is authoritative.
    leader = logfmt.parse_log(
        leader_text, strict=strict_proof, expected_role="leader"
    )
    follower = logfmt.parse_log(
        follower_text, strict=strict_proof, expected_role="follower"
    )
    leader_epoch = _epoch_view(leader)
    follower_epoch = _epoch_view(follower)
    correlation = _corr.correlate(leader_epoch, follower_epoch)
    ready = link_ready(
        leader, follower, leader_epoch, follower_epoch, correlation
    )

    if ready["status"] != PASS:
        gate1 = _blocked_gate()
        gate2 = _blocked_gate()
        gate3 = _blocked_gate()
    else:
        absolute_error = [
            abs(error) for _, error in correlation.clock_error_series
        ]
        gate1 = _timing_gate(
            _corr.percentile(absolute_error, 95.0),
            clock_err_p95_us,
            len(absolute_error),
        )
        gate2 = _timing_gate(
            _corr.percentile(correlation.apply_lateness_us, 99.9),
            lateness_p999_us,
            len(correlation.apply_lateness_us),
        )
        gate3 = _timing_gate(
            max(correlation.apply_lateness_us)
            if correlation.apply_lateness_us
            else None,
            e2e_us,
            len(correlation.apply_lateness_us),
        )

    leader_health = correlation.health_by_role.get(
        "leader", _corr.HealthAggregate()
    )
    follower_health = correlation.health_by_role.get(
        "follower", _corr.HealthAggregate()
    )
    if ready["status"] != PASS:
        gate4 = {"status": BLOCKED, "health_samples": 0, "subgates": {}}
    else:
        subgates = {
            "leader_fps_min": _floor_subgate(
                None
                if leader_health.fps_min is None
                else round(leader_health.fps_min, 2),
                fps_floor,
            ),
            "follower_fps_min": _floor_subgate(
                None
                if follower_health.fps_min is None
                else round(follower_health.fps_min, 2),
                fps_floor,
            ),
            "leader_heap_min": _floor_subgate(
                leader_health.heap_min, heap_min_floor
            ),
            "follower_heap_min": _floor_subgate(
                follower_health.heap_min, heap_min_floor
            ),
            "leader_ap_p95_us": _ceiling_subgate(
                leader_health.ap_p95_max,
                ap_p95_us_max,
                zero_unmeasured=True,
            ),
            "follower_ap_p95_us": _ceiling_subgate(
                follower_health.ap_p95_max,
                ap_p95_us_max,
                zero_unmeasured=True,
            ),
            "dial_uptime": _floor_subgate(
                _r6(leader_health.dial_uptime),
                dial_uptime_min,
                missing=UNMEASURED,
            ),
            "transport_loss": _ceiling_subgate(
                correlation.transport_missing
                if correlation.transport_expected > 0
                else None,
                stream_loss_max,
            ),
            "apply_loss": _ceiling_subgate(
                correlation.apply_missing
                if correlation.apply_expected > 0
                else None,
                apply_loss_max,
            ),
            "physical_ws2812_glitch": _ceiling_subgate(
                None,
                0,
                missing=UNMEASURED,
            ),
        }
        gate4 = {
            "status": _status_from_children(
                subgate["status"] for subgate in subgates.values()
            ),
            "health_samples": leader_health.samples + follower_health.samples,
            "subgates": subgates,
        }

    gate3_key = "gate3_leader_stamp_to_follower_consume"
    gate_statuses = [
        gate1["status"],
        gate2["status"],
        gate3["status"],
        gate4["status"],
    ]
    overall_status = (
        BLOCKED
        if ready["status"] != PASS
        else _status_from_children(gate_statuses)
    )
    verdict = {
        "schema_version": 2,
        "link_ready": ready,
        "gate1_clock_err": gate1,
        "gate2_lateness": gate2,
        gate3_key: gate3,
        "gate4_health": gate4,
        "overall_status": overall_status,
        "overall_pass": overall_status == PASS,
        "diagnostics": {
            "trig_rounds": len(correlation.rounds),
            "incomplete_rounds": correlation.incomplete_rounds,
            "transport_expected": correlation.transport_expected,
            "transport_missing": correlation.transport_missing,
            "transport_dup": correlation.transport_dup,
            "transport_reorder": correlation.transport_reorder,
            "transport_unexpected": correlation.transport_unexpected,
            "apply_expected": correlation.apply_expected,
            "apply_missing": correlation.apply_missing,
            "apply_dup": correlation.apply_dup,
            "apply_reorder": correlation.apply_reorder,
            "apply_unexpected": correlation.apply_unexpected,
            "leader_tx_duplicate": correlation.leader_tx_dup,
            "leader_tx_reorder": correlation.leader_tx_reorder,
            "apply_unmatched": correlation.unmatched_apply,
            "wire_asymmetry_p95_us": _r_us(
                _corr.percentile(
                    [abs(sample.asymmetry_us) for sample in correlation.rounds],
                    95.0,
                )
            ),
            "leader_lines_total": leader.total_lines,
            "leader_lines_skipped": leader.skipped_lines,
            "follower_lines_total": follower.total_lines,
            "follower_lines_skipped": follower.skipped_lines,
        },
    }
    return verdict


def to_json(verdict: dict) -> str:
    return json.dumps(verdict, sort_keys=True, indent=2) + "\n"


def format_summary(verdict: dict) -> str:
    lines = ["Dual-K1 sync gate verdict", "=" * 48]
    lines.append(f"  [{verdict['link_ready']['status']}] Link Ready")
    gate_names = (
        ("gate1 clock-err p95", "gate1_clock_err"),
        ("gate2 lateness p99.9", "gate2_lateness"),
        (
            "gate3 leader-stamp→follower-consume",
            "gate3_leader_stamp_to_follower_consume",
        ),
    )
    for label, key in gate_names:
        gate = verdict[key]
        value = "n/a" if gate["value_us"] is None else f"{gate['value_us']} µs"
        lines.append(
            f"  [{gate['status']}] {label}: {value} "
            f"(limit {gate['threshold_us']}, n={gate['n']})"
        )
    gate4 = verdict["gate4_health"]
    lines.append(
        f"  [{gate4['status']}] gate4 health "
        f"(samples={gate4['health_samples']})"
    )
    for name, subgate in sorted(gate4["subgates"].items()):
        lines.append(f"        [{subgate['status']}] {name}: {subgate['value']}")
    lines.extend(("-" * 48, f"  OVERALL: {verdict['overall_status']}"))
    return "\n".join(lines)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gate_eval",
        description="Evaluate fail-closed dual-K1 sync proof logs.",
    )
    parser.add_argument("leader_log")
    parser.add_argument("follower_log")
    parser.add_argument("--clock-err-p95-us", type=int, default=DEFAULT_CLOCK_ERR_P95_US)
    parser.add_argument("--lateness-p999-us", type=int, default=DEFAULT_LATENESS_P999_US)
    parser.add_argument("--e2e-us", type=int, default=DEFAULT_E2E_US)
    parser.add_argument("--d-us", type=int, default=DEFAULT_D_US)
    parser.add_argument("--fps-floor", type=float, default=DEFAULT_FPS_FLOOR)
    parser.add_argument("--heap-min-floor", type=int, default=DEFAULT_HEAP_MIN_FLOOR)
    parser.add_argument("--ap-p95-us-max", type=int, default=DEFAULT_AP_P95_US_MAX)
    parser.add_argument("--dial-uptime-min", type=float, default=DEFAULT_DIAL_UPTIME_MIN)
    parser.add_argument("--stream-loss-max", type=int, default=DEFAULT_STREAM_LOSS_MAX)
    parser.add_argument("--apply-loss-max", type=int, default=DEFAULT_APPLY_LOSS_MAX)
    parser.add_argument("--strict-proof", action="store_true")
    parser.add_argument("--summary", action="store_true")
    return parser


def main(argv=None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        with open(args.leader_log, "r", encoding="utf-8", errors="replace") as file:
            leader_text = file.read()
        with open(args.follower_log, "r", encoding="utf-8", errors="replace") as file:
            follower_text = file.read()
        verdict = evaluate(
            leader_text,
            follower_text,
            clock_err_p95_us=args.clock_err_p95_us,
            lateness_p999_us=args.lateness_p999_us,
            e2e_us=args.e2e_us,
            d_us=args.d_us,
            fps_floor=args.fps_floor,
            heap_min_floor=args.heap_min_floor,
            ap_p95_us_max=args.ap_p95_us_max,
            dial_uptime_min=args.dial_uptime_min,
            stream_loss_max=args.stream_loss_max,
            apply_loss_max=args.apply_loss_max,
            strict_proof=args.strict_proof,
        )
    except (OSError, logfmt.LogContractError, ValueError) as error:
        sys.stderr.write(f"gate_eval input contract error: {error}\n")
        return INPUT_ERROR_EXIT
    sys.stdout.write(to_json(verdict))
    if args.summary:
        sys.stderr.write(format_summary(verdict) + "\n")
    return STATUS_EXIT[verdict["overall_status"]]


if __name__ == "__main__":
    raise SystemExit(main())
