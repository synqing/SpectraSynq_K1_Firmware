"""Seeded synthetic log-pair generator for the Gate-0 fault battery.

Produces a leader + follower log pair from an explicit ground-truth model, so a
test can inject a KNOWN fault and assert the oracle reports it within tolerance
and flips the right gate. Determinism is a hard contract: the ONLY entropy
source is ``random.Random(seed)``, and the number of draws per packet/sample is
fixed regardless of which fault is active — so a clean run and a faulted run at
the same seed share the same underlying jitter realisations and differ ONLY by
the injected fault. That is what makes "measured value ≈ injected truth" exact.

Model (all times µs; leader clock is the reference, running 0..duration):

    O_true(t)        = true_offset_us + drift_us_per_s * t/1e6   (follower - leader)
    follower_local   = t + O_true(t)

Cross-trigger round i at leader time t_r fires in both directions at the same
physical instant, with a symmetric per-side ISR latency ``isr_latency_us``:

    leader   trig_out @ t_r                       ; trig_in  @ t_r + isr
    follower trig_out @ t_r + O                    ; trig_in  @ t_r + O + isr

Stream packet j at leader time t_tx: transport = base + jitter (+ tail); the
follower applies at arrival + render jitter + apply_delay (the injected fault).
Radio clock estimate: est = true_offset + est_drift*t + bias + noise.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List, Optional, Tuple

from . import logfmt


@dataclass
class SynthParams:
    # --- run shape ---
    duration_s: float = 60.0
    stream_hz: float = 33.0
    trig_hz: float = 4.0
    clk_hz: float = 2.0
    health_hz: float = 1.0

    # --- clock model ---
    true_offset_us: int = 5_000_000
    drift_us_per_s: float = 0.0
    # est_drift defaults to tracking the true drift; set != drift to model a
    # clock-sync that fails to track drift.
    clock_est_drift_us_per_s: Optional[float] = None
    clock_bias_us: float = 0.0
    clock_est_noise_us: float = 300.0

    # --- wire/ISR ---
    isr_latency_us: float = 3.0

    # --- transport / apply ---
    base_latency_us: float = 11_000.0
    latency_jitter_us: float = 2_000.0
    lateness_tail_us: float = 0.0
    lateness_tail_frac: float = 0.01
    render_jitter_us: float = 500.0
    apply_delay_us: float = 0.0  # the injected apply-delay fault

    # --- stream integrity faults ---
    loss_frac: float = 0.0
    dup_frac: float = 0.0

    # --- health ---
    fps: float = 100.0
    fps_noise: float = 2.0
    heap_min: int = 60_000
    ap_p95_us: int = 700
    dial_drop_frac: float = 0.0

    # --- noise injection (parser robustness) ---
    noise_lines: int = 0


def _o_true(p: SynthParams, t_leader_us: float) -> float:
    return p.true_offset_us + p.drift_us_per_s * (t_leader_us / 1_000_000.0)


def _o_est(p: SynthParams, t_leader_us: float) -> float:
    est_drift = (
        p.drift_us_per_s
        if p.clock_est_drift_us_per_s is None
        else p.clock_est_drift_us_per_s
    )
    return p.true_offset_us + est_drift * (t_leader_us / 1_000_000.0)


_NOISE_TEMPLATES = [
    "I (12345) wifi: some unrelated esp-idf chatter",
    "[k1_sync] garbled line missing fields",
    "rst:0x1 (POWERON),boot:0x8",
    "[sync_oracle] trig_out seq= t_us=",  # truncated / malformed
    "load:0x3fce3810,len:0x1234",
]


def generate_log_pair(
    params: SynthParams, seed: int = 0
) -> Tuple[str, str]:
    """Return ``(leader_text, follower_text)`` for the given ground-truth model."""
    rng = random.Random(seed)
    p = params

    # (leader_emit_us, line) and (follower_emit_us, line) — sorted before join
    leader: List[Tuple[float, str]] = []
    follower: List[Tuple[float, str]] = []

    dur_us = p.duration_s * 1_000_000.0

    # --- cross-trigger rounds ---
    n_rounds = int(p.duration_s * p.trig_hz)
    for i in range(n_rounds):
        t_r = (i / p.trig_hz) * 1_000_000.0
        o = _o_true(p, t_r)
        isr = p.isr_latency_us
        # leader
        leader.append((t_r, logfmt.fmt_trig_out(i, int(round(t_r)))))
        leader.append((t_r + isr, logfmt.fmt_trig_in(i, int(round(t_r + isr)))))
        # follower
        follower.append((t_r + o, logfmt.fmt_trig_out(i, int(round(t_r + o)))))
        follower.append(
            (t_r + o + isr, logfmt.fmt_trig_in(i, int(round(t_r + o + isr))))
        )

    # --- stream packets ---
    n_pkts = int(p.duration_s * p.stream_hz)
    for j in range(n_pkts):
        t_tx = (j / p.stream_hz) * 1_000_000.0
        o = _o_true(p, t_tx)
        # fixed draw order regardless of active fault (determinism contract)
        jitter = rng.uniform(-p.latency_jitter_us, p.latency_jitter_us)
        tail_u = rng.random()
        render_u = rng.uniform(0.0, p.render_jitter_us)
        loss_u = rng.random()
        dup_u = rng.random()

        transport = p.base_latency_us + jitter
        if tail_u < p.lateness_tail_frac:
            transport += p.lateness_tail_us
        arrival = t_tx + o + transport
        apply_t = arrival + render_u + p.apply_delay_us

        leader.append((t_tx, logfmt.fmt_tx(j, int(round(t_tx)))))
        if loss_u < p.loss_frac:
            continue  # packet lost: no rx, no apply on the follower
        rx_line = logfmt.fmt_rx(j, int(round(t_tx)), int(round(arrival)))
        apply_line = logfmt.fmt_apply(j, int(round(apply_t)))
        follower.append((arrival, rx_line))
        follower.append((apply_t, apply_line))
        if dup_u < p.dup_frac:
            follower.append((arrival, rx_line))
            follower.append((apply_t, apply_line))

    # --- radio clock estimates (follower) ---
    n_clk = int(p.duration_s * p.clk_hz)
    for k in range(n_clk):
        t_c = (k / p.clk_hz) * 1_000_000.0
        noise = rng.uniform(-p.clock_est_noise_us, p.clock_est_noise_us)
        est = _o_est(p, t_c) + p.clock_bias_us + noise
        emit_follower = t_c + _o_true(p, t_c)
        follower.append(
            (emit_follower, logfmt.fmt_clk(int(round(est)), 4000, 8))
        )

    # --- health telemetry (follower) ---
    n_health = int(p.duration_s * p.health_hz)
    loss_running = 0
    for h in range(n_health):
        t_h = (h / p.health_hz) * 1_000_000.0
        fps_n = rng.uniform(-p.fps_noise, p.fps_noise)
        dial_u = rng.random()
        dial_linked = 0 if dial_u < p.dial_drop_frac else 1
        emit_follower = t_h + _o_true(p, t_h)
        follower.append(
            (
                emit_follower,
                logfmt.fmt_health(
                    p.fps + fps_n,
                    p.heap_min,
                    p.ap_p95_us,
                    dial_linked,
                    loss_running,
                    0,
                ),
            )
        )

    # --- optional noise lines (parser robustness) ---
    for _ in range(p.noise_lines):
        t_n = rng.uniform(0.0, dur_us)
        tmpl = _NOISE_TEMPLATES[rng.randrange(len(_NOISE_TEMPLATES))]
        leader.append((t_n, tmpl))
        t_n2 = rng.uniform(0.0, dur_us)
        tmpl2 = _NOISE_TEMPLATES[rng.randrange(len(_NOISE_TEMPLATES))]
        follower.append((t_n2, tmpl2))

    leader.sort(key=lambda x: x[0])
    follower.sort(key=lambda x: x[0])
    leader_text = "\n".join(line for _, line in leader) + "\n"
    follower_text = "\n".join(line for _, line in follower) + "\n"
    return leader_text, follower_text
