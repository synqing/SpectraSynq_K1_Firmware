"""Correlate a dual-sync leader/follower capture into raw proof series."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from . import logfmt
from .logfmt import Apply, Clk, Health, ParsedLog, Rx, TrigIn, TrigOut, Tx, interp_xy


@dataclass
class RoundSample:
    seq: int
    leader_mid_us: float
    follower_mid_us: float
    offset_us: float
    asymmetry_us: float


@dataclass
class HealthAggregate:
    samples: int = 0
    fps_min: Optional[float] = None
    heap_min: Optional[int] = None
    ap_p95_max: Optional[int] = None
    dial_uptime: Optional[float] = None
    loss_max: int = 0
    dup_max: int = 0


@dataclass
class Correlation:
    rounds: List[RoundSample] = field(default_factory=list)
    clock_error_series: List[Tuple[float, float]] = field(default_factory=list)
    apply_lateness_us: List[float] = field(default_factory=list)

    leader_tx_count: int = 0
    follower_rx_count: int = 0
    follower_apply_count: int = 0
    follower_clk_records: int = 0

    transport_expected: int = 0
    transport_missing: int = 0
    transport_dup: int = 0
    transport_reorder: int = 0
    apply_expected: int = 0
    apply_missing: int = 0
    apply_dup: int = 0
    apply_reorder: int = 0
    transport_unexpected: int = 0
    apply_unexpected: int = 0
    leader_tx_gap: int = 0
    leader_tx_dup: int = 0
    leader_tx_reorder: int = 0

    health_by_role: Dict[str, HealthAggregate] = field(default_factory=dict)
    incomplete_rounds: int = 0
    unmatched_apply: int = 0

    # Compatibility aliases for archived analysis code. New proof code uses
    # the explicit transport/apply names above.
    @property
    def stream_expected(self) -> int:
        return self.transport_expected

    @property
    def loss(self) -> int:
        return self.transport_missing

    @property
    def dup(self) -> int:
        return self.transport_dup

    @property
    def reorder(self) -> int:
        return self.transport_reorder

    def _offset_by_follower(self) -> List[Tuple[float, float]]:
        return sorted((sample.follower_mid_us, sample.offset_us) for sample in self.rounds)

    def offset_at_follower(self, t_follower_us: float) -> Optional[float]:
        return interp_xy(self._offset_by_follower(), t_follower_us)


def _index_records(records: List[object]):
    trig_out: Dict[int, int] = {}
    trig_in: Dict[int, int] = {}
    tx: List[Tx] = []
    rx: List[Rx] = []
    apply: List[Apply] = []
    clk: List[Clk] = []
    health: List[Health] = []
    for record in records:
        if isinstance(record, TrigOut):
            trig_out.setdefault(record.seq, record.t_us)
        elif isinstance(record, TrigIn):
            trig_in.setdefault(record.seq, record.t_us)
        elif isinstance(record, Tx):
            tx.append(record)
        elif isinstance(record, Rx):
            rx.append(record)
        elif isinstance(record, Apply):
            apply.append(record)
        elif isinstance(record, Clk):
            clk.append(record)
        elif isinstance(record, Health):
            health.append(record)
    return trig_out, trig_in, tx, rx, apply, clk, health


def correlate(leader: ParsedLog, follower: ParsedLog) -> Correlation:
    correlation = Correlation()
    (
        leader_trig_out,
        leader_trig_in,
        leader_tx,
        _leader_rx,
        _leader_apply,
        _leader_clk,
        leader_health,
    ) = _index_records(leader.records)
    (
        follower_trig_out,
        follower_trig_in,
        _follower_tx,
        follower_rx,
        follower_apply,
        follower_clk,
        follower_health,
    ) = _index_records(follower.records)

    leader_tx_by_seq: Dict[int, int] = {}
    for record in leader_tx:
        leader_tx_by_seq.setdefault(record.seq, record.t_leader_us)
    correlation.leader_tx_count = len(leader_tx_by_seq)
    correlation.follower_rx_count = len({record.seq for record in follower_rx})
    correlation.follower_apply_count = len(
        {record.seq for record in follower_apply}
    )
    correlation.follower_clk_records = len(follower_clk)

    complete = (
        set(leader_trig_out)
        & set(follower_trig_in)
        & set(follower_trig_out)
        & set(leader_trig_in)
    )
    seen = (
        set(leader_trig_out)
        | set(follower_trig_in)
        | set(follower_trig_out)
        | set(leader_trig_in)
    )
    correlation.incomplete_rounds = len(seen) - len(complete)
    for seq in sorted(complete):
        leader_out = leader_trig_out[seq]
        follower_in = follower_trig_in[seq]
        follower_out = follower_trig_out[seq]
        leader_in = leader_trig_in[seq]
        d1 = follower_in - leader_out
        d2 = follower_out - leader_in
        correlation.rounds.append(
            RoundSample(
                seq=seq,
                leader_mid_us=(leader_out + leader_in) / 2.0,
                follower_mid_us=(follower_in + follower_out) / 2.0,
                offset_us=(d1 + d2) / 2.0,
                asymmetry_us=(d1 - d2) / 2.0,
            )
        )

    offset_by_follower = correlation._offset_by_follower()
    for entry in follower.entries:
        record = entry.record
        if not isinstance(record, Clk):
            continue
        local_time = record.t_local_us
        if local_time is None:
            local_time = follower.local_time_at(entry.line_index)
        if local_time is None:
            continue
        wire = interp_xy(offset_by_follower, float(local_time))
        if wire is None:
            continue
        correlation.clock_error_series.append(
            (float(local_time), record.est_offset_us - wire)
        )

    rx_leader_stamp: Dict[int, int] = {}
    for record in follower_rx:
        rx_leader_stamp.setdefault(record.seq, record.t_leader_us)
    for record in follower_apply:
        leader_stamp = leader_tx_by_seq.get(
            record.seq, rx_leader_stamp.get(record.seq)
        )
        if leader_stamp is None:
            correlation.unmatched_apply += 1
            continue
        wire = interp_xy(offset_by_follower, record.t_render_us)
        if wire is None:
            correlation.unmatched_apply += 1
            continue
        apply_leader = record.t_render_us - wire
        correlation.apply_lateness_us.append(apply_leader - leader_stamp)

    _integrity(leader_tx, follower_rx, follower_apply, correlation)
    correlation.health_by_role["leader"] = _health_aggregate(
        leader_health, fallback_role="leader"
    )
    correlation.health_by_role["follower"] = _health_aggregate(
        follower_health, fallback_role="follower"
    )
    return correlation


def _duplicates_and_reorder(sequences: List[int]) -> Tuple[int, int]:
    seen: Dict[int, int] = {}
    for seq in sequences:
        seen[seq] = seen.get(seq, 0) + 1
    duplicates = sum(count - 1 for count in seen.values() if count > 1)
    reorder = 0
    peak: Optional[int] = None
    for seq in sequences:
        if peak is not None and seq < peak:
            reorder += 1
        else:
            peak = seq
    return duplicates, reorder


def _integrity(
    leader_tx: List[Tx],
    follower_rx: List[Rx],
    follower_apply: List[Apply],
    correlation: Correlation,
) -> None:
    ordered_tx_sequences = [record.seq for record in leader_tx]
    tx_sequences = sorted(set(ordered_tx_sequences))
    rx_sequences = [record.seq for record in follower_rx]
    apply_sequences = [record.seq for record in follower_apply]
    correlation.leader_tx_dup, correlation.leader_tx_reorder = (
        _duplicates_and_reorder(ordered_tx_sequences)
    )
    if tx_sequences:
        low, high = tx_sequences[0], tx_sequences[-1]
        dense_expected = set(range(low, high + 1))
        tx_set = set(tx_sequences)
        correlation.leader_tx_gap = len(dense_expected - tx_set)
        correlation.transport_expected = len(tx_set)
        correlation.transport_missing = len(tx_set - set(rx_sequences))
        correlation.transport_unexpected = len(set(rx_sequences) - tx_set)
    elif rx_sequences:
        correlation.transport_unexpected = len(set(rx_sequences))
    correlation.transport_dup, correlation.transport_reorder = _duplicates_and_reorder(
        rx_sequences
    )

    rx_unique = set(rx_sequences)
    apply_unique = set(apply_sequences)
    correlation.apply_expected = len(rx_unique)
    correlation.apply_missing = len(rx_unique - apply_unique)
    correlation.apply_unexpected = len(apply_unique - rx_unique)
    correlation.apply_dup, correlation.apply_reorder = _duplicates_and_reorder(
        apply_sequences
    )


def _health_aggregate(
    health: List[Health], *, fallback_role: str
) -> HealthAggregate:
    selected = [
        record
        for record in health
        if record.role in (None, fallback_role)
    ]
    if not selected:
        return HealthAggregate()
    return HealthAggregate(
        samples=len(selected),
        fps_min=min(record.fps for record in selected),
        heap_min=min(record.heap_min for record in selected),
        ap_p95_max=max(record.ap_p95_us for record in selected),
        dial_uptime=(
            sum(1 for record in selected if record.dial_linked == 1) / len(selected)
            if fallback_role == "leader"
            else None
        ),
        loss_max=max(record.loss for record in selected),
        dup_max=max(record.dup for record in selected),
    )


def percentile(values: List[float], q: float) -> Optional[float]:
    if not values:
        return None
    if len(values) == 1:
        return float(values[0])
    ordered = sorted(values)
    if q <= 0:
        return float(ordered[0])
    if q >= 100:
        return float(ordered[-1])
    rank = (q / 100.0) * (len(ordered) - 1)
    low = int(rank)
    high = min(low + 1, len(ordered) - 1)
    fraction = rank - low
    return float(ordered[low] + (ordered[high] - ordered[low]) * fraction)


def mean(values: List[float]) -> Optional[float]:
    return None if not values else sum(values) / len(values)


def clock_error_slope_us_per_s(
    series: List[Tuple[float, float]]
) -> Optional[float]:
    if len(series) < 2:
        return None
    xs = [time_us / 1_000_000.0 for time_us, _ in series]
    ys = [error for _, error in series]
    count = len(xs)
    mean_x = sum(xs) / count
    mean_y = sum(ys) / count
    sum_xx = sum((value - mean_x) ** 2 for value in xs)
    if sum_xx == 0:
        return None
    sum_xy = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    return sum_xy / sum_xx
