"""Seeded strict-log generator for the dual-sync oracle fault battery."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List, Optional, Tuple

from . import logfmt


@dataclass
class SynthParams:
    duration_s: float = 60.0
    stream_hz: float = 33.0
    trig_hz: float = 4.0
    clk_hz: float = 2.0
    health_hz: float = 1.0

    true_offset_us: int = 5_000_000
    drift_us_per_s: float = 0.0
    clock_est_drift_us_per_s: Optional[float] = None
    clock_bias_us: float = 0.0
    clock_est_noise_us: float = 300.0

    isr_latency_us: float = 3.0
    base_latency_us: float = 11_000.0
    latency_jitter_us: float = 2_000.0
    lateness_tail_us: float = 0.0
    lateness_tail_frac: float = 0.01
    render_jitter_us: float = 500.0
    apply_delay_us: float = 0.0

    # Transport drop removes RX and apply. Application drop preserves RX and
    # removes apply, matching the current silicon drop10 behaviour.
    loss_frac: float = 0.0
    apply_drop_frac: float = 0.0
    dup_frac: float = 0.0

    fps: float = 100.0
    fps_noise: float = 2.0
    heap_min: int = 60_000
    ap_p95_us: int = 700
    dial_drop_frac: float = 0.0

    interval_units: int = 6
    latency: int = 0
    mtu: int = 247
    phy_tx: int = 2
    phy_rx: int = 2

    # A reconnect makes Link Ready fail; records are intentionally retained so
    # the test proves counts cannot accumulate across epochs.
    disconnect_at_s: Optional[float] = None
    reconnect_after_s: float = 1.0

    noise_lines: int = 0
    host_prefix: bool = True


DeviceLine = Tuple[float, int, str]


def _o_true(params: SynthParams, t_leader_us: float) -> float:
    return params.true_offset_us + params.drift_us_per_s * (
        t_leader_us / 1_000_000.0
    )


def _o_est(params: SynthParams, t_leader_us: float) -> float:
    estimated_drift = (
        params.drift_us_per_s
        if params.clock_est_drift_us_per_s is None
        else params.clock_est_drift_us_per_s
    )
    return params.true_offset_us + estimated_drift * (
        t_leader_us / 1_000_000.0
    )


_NOISE_TEMPLATES = [
    "I (12345) wifi: some unrelated esp-idf chatter",
    "[k1_sync] garbled line missing fields",
    "rst:0x1 (POWERON),boot:0x8",
    "[sync_oracle] trig_out seq= t_us=",
    "load:0x3fce3810,len:0x1234",
]


def _append(
    target: List[DeviceLine], local_us: float, host_us: float, line: str
) -> None:
    target.append((local_us, int(round(host_us)), line))


def _render(lines: List[DeviceLine], host_prefix: bool) -> str:
    lines.sort(key=lambda item: item[0])
    if host_prefix:
        return "\n".join(
            f"host_us={host_us} {line}" for _, host_us, line in lines
        ) + "\n"
    return "\n".join(line for _, _, line in lines) + "\n"


def generate_log_pair(
    params: SynthParams, seed: int = 0
) -> Tuple[str, str]:
    rng = random.Random(seed)
    p = params
    leader: List[DeviceLine] = []
    follower: List[DeviceLine] = []
    duration_us = p.duration_s * 1_000_000.0
    follower_zero = _o_true(p, 0.0)
    # Keep proof observations strictly after link-up/negotiation. Without this
    # settle offset, sequence zero exists before the connection epoch and the
    # fail-closed oracle correctly rejects the otherwise "clean" fixture.
    settle_us = 10_000.0

    # Strict connection/negotiation proof.
    _append(leader, 0.0, 0.0, logfmt.fmt_begin("leader"))
    _append(follower, follower_zero, 0.0, logfmt.fmt_begin("follower"))
    _append(leader, 1.0, 1.0, logfmt.fmt_link_up("leader", 1, 1, p.mtu))
    _append(
        follower,
        follower_zero + 1.0,
        1.0,
        logfmt.fmt_link_up("follower", 1, 1, p.mtu),
    )
    _append(
        leader,
        2.0,
        2.0,
        logfmt.fmt_negotiated(
            "leader",
            1,
            p.interval_units,
            p.latency,
            p.mtu,
            p.phy_tx,
            p.phy_rx,
        ),
    )
    _append(
        follower,
        follower_zero + 2.0,
        2.0,
        logfmt.fmt_negotiated(
            "follower",
            1,
            p.interval_units,
            p.latency,
            p.mtu,
            p.phy_tx,
            p.phy_rx,
        ),
    )

    if p.disconnect_at_s is not None:
        down_host = p.disconnect_at_s * 1_000_000.0
        follower_down = down_host + _o_true(p, down_host)
        _append(
            leader,
            down_host,
            down_host,
            logfmt.fmt_link_down("leader", 1, 19),
        )
        _append(
            follower,
            follower_down,
            down_host,
            logfmt.fmt_link_down("follower", 1, 19),
        )
        up_host = down_host + p.reconnect_after_s * 1_000_000.0
        follower_up = up_host + _o_true(p, up_host)
        _append(leader, up_host, up_host, logfmt.fmt_link_up("leader", 2, 2, p.mtu))
        _append(
            follower,
            follower_up,
            up_host,
            logfmt.fmt_link_up("follower", 2, 2, p.mtu),
        )

    rounds = int(p.duration_s * p.trig_hz)
    for seq in range(rounds):
        physical = settle_us + (seq / p.trig_hz) * 1_000_000.0
        offset = _o_true(p, physical)
        isr = p.isr_latency_us
        _append(
            leader,
            physical,
            physical,
            logfmt.fmt_trig_out(seq, int(round(physical))),
        )
        _append(
            leader,
            physical + isr,
            physical + isr,
            logfmt.fmt_trig_in(seq, int(round(physical + isr))),
        )
        _append(
            follower,
            physical + offset,
            physical,
            logfmt.fmt_trig_out(seq, int(round(physical + offset))),
        )
        _append(
            follower,
            physical + offset + isr,
            physical + isr,
            logfmt.fmt_trig_in(seq, int(round(physical + offset + isr))),
        )

    packets = int(p.duration_s * p.stream_hz)
    for seq in range(packets):
        tx_host = settle_us + (seq / p.stream_hz) * 1_000_000.0
        offset = _o_true(p, tx_host)
        jitter = rng.uniform(-p.latency_jitter_us, p.latency_jitter_us)
        tail_random = rng.random()
        render_random = rng.uniform(0.0, p.render_jitter_us)
        transport_drop_random = rng.random()
        apply_drop_random = rng.random()
        duplicate_random = rng.random()

        transport = p.base_latency_us + jitter
        if tail_random < p.lateness_tail_frac:
            transport += p.lateness_tail_us
        arrival_host = tx_host + transport
        arrival_local = arrival_host + offset
        apply_host = arrival_host + render_random + p.apply_delay_us
        apply_local = apply_host + offset

        _append(
            leader,
            tx_host,
            tx_host,
            logfmt.fmt_tx(seq, int(round(tx_host))),
        )
        if transport_drop_random < p.loss_frac:
            continue
        rx_line = logfmt.fmt_rx(
            seq, int(round(tx_host)), int(round(arrival_local))
        )
        _append(follower, arrival_local, arrival_host, rx_line)
        if apply_drop_random >= p.apply_drop_frac:
            apply_line = logfmt.fmt_apply(seq, int(round(apply_local)))
            _append(follower, apply_local, apply_host, apply_line)
        if duplicate_random < p.dup_frac:
            _append(follower, arrival_local, arrival_host, rx_line)
            if apply_drop_random >= p.apply_drop_frac:
                _append(follower, apply_local, apply_host, apply_line)

    clocks = int(p.duration_s * p.clk_hz)
    for sample in range(clocks):
        host_time = settle_us + (sample / p.clk_hz) * 1_000_000.0
        local_time = host_time + _o_true(p, host_time)
        noise = rng.uniform(-p.clock_est_noise_us, p.clock_est_noise_us)
        estimate = _o_est(p, host_time) + p.clock_bias_us + noise
        _append(
            follower,
            local_time,
            host_time,
            logfmt.fmt_clk(
                int(round(estimate)),
                4000,
                sample + 1,
                t_local_us=int(round(local_time)),
                role="follower",
            ),
        )

    health_samples = int(p.duration_s * p.health_hz)
    for sample in range(health_samples):
        host_time = settle_us + (sample / p.health_hz) * 1_000_000.0
        leader_fps = p.fps + rng.uniform(-p.fps_noise, p.fps_noise)
        follower_fps = p.fps + rng.uniform(-p.fps_noise, p.fps_noise)
        dial_linked = 0 if rng.random() < p.dial_drop_frac else 1
        _append(
            leader,
            host_time,
            host_time,
            logfmt.fmt_health(
                leader_fps,
                p.heap_min,
                p.ap_p95_us,
                dial_linked,
                0,
                0,
                role="leader",
            ),
        )
        follower_local = host_time + _o_true(p, host_time)
        _append(
            follower,
            follower_local,
            host_time,
            logfmt.fmt_health(
                follower_fps,
                p.heap_min,
                p.ap_p95_us,
                0,
                0,
                0,
                role="follower",
            ),
        )

    for _ in range(p.noise_lines):
        leader_host = rng.uniform(0.0, duration_us)
        follower_host = rng.uniform(0.0, duration_us)
        _append(
            leader,
            leader_host,
            leader_host,
            _NOISE_TEMPLATES[rng.randrange(len(_NOISE_TEMPLATES))],
        )
        _append(
            follower,
            follower_host + _o_true(p, follower_host),
            follower_host,
            _NOISE_TEMPLATES[rng.randrange(len(_NOISE_TEMPLATES))],
        )

    return _render(leader, p.host_prefix), _render(follower, p.host_prefix)
