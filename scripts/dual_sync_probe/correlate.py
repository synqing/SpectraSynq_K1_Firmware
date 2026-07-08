"""Correlate a leader + follower log pair into the raw series the gate
evaluator scores. Pure and deterministic over captured text — no clocks of its
own, no randomness, no I/O.

The measurement chain (see probe-log-contract.md §2):

  (a) Wire-truth offset. The wired GPIO cross-trigger is a radio-independent
      clock bridge. Per round ``seq=n`` BOTH directions fire:
        dir1 (leader->follower):  leader trig_out @ t_L_out ; follower trig_in @ t_F_in
        dir2 (follower->leader):  follower trig_out @ t_F_out ; leader trig_in @ t_L_in
      With wire delay ~ns and per-side ISR latency eps:
        D1 = t_F_in  - t_L_out = O + eps_follower
        D2 = t_F_out - t_L_in  = O - eps_leader
      so  offset  O_hat = (D1 + D2) / 2      (ISR latency cancels if symmetric)
      and asymmetry bound = (D1 - D2) / 2    (the residual wire+ISR uncertainty)
      where O is the true (follower_local - leader_local) offset at that instant.
      Sampling every round tracks drift; the two directions bound the asymmetry.

  (b) Radio clock-estimate error = est_offset_us - O_hat interpolated at the
      clk line's (reconstructed) time. This is what Gate 1 scores.

  (c) Apply-lateness = (follower apply time mapped to leader clock) - t_leader_us
      for each stream packet. Gates 2 and 3 score this.

  (d) Loss / dup / reorder from the follower stream seq order.

  (e) Health mins + dial-link uptime from health lines.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from . import logfmt
from .logfmt import (
    Apply,
    Clk,
    Health,
    ParsedLog,
    Rx,
    TrigIn,
    TrigOut,
    Tx,
    interp_xy,
)


@dataclass
class RoundSample:
    """One matched cross-trigger round (both directions present)."""

    seq: int
    leader_mid_us: float  # round time in the leader clock
    follower_mid_us: float  # round time in the follower clock
    offset_us: float  # O_hat = follower_local - leader_local
    asymmetry_us: float  # (D1 - D2)/2 : wire+ISR residual


@dataclass
class Correlation:
    rounds: List[RoundSample] = field(default_factory=list)
    # (follower_time_us, error_us) — est_offset minus wire truth.
    clock_error_series: List[Tuple[float, float]] = field(default_factory=list)
    # apply-lateness values (leader clock, µs) per applied packet.
    apply_lateness_us: List[float] = field(default_factory=list)
    # stream integrity
    stream_expected: int = 0
    loss: int = 0
    dup: int = 0
    reorder: int = 0
    # health aggregates (None if no health lines)
    health_samples: int = 0
    fps_min: Optional[float] = None
    heap_min: Optional[int] = None
    ap_p95_max: Optional[int] = None
    dial_uptime: Optional[float] = None
    health_loss_max: int = 0
    health_dup_max: int = 0
    # diagnostics / provenance
    incomplete_rounds: int = 0
    unmatched_apply: int = 0

    # ----- wire-truth interpolation in either clock domain ----------------- #
    def _offset_by_follower(self) -> List[Tuple[float, float]]:
        return sorted((r.follower_mid_us, r.offset_us) for r in self.rounds)

    def offset_at_follower(self, t_follower_us: float) -> Optional[float]:
        return interp_xy(self._offset_by_follower(), t_follower_us)


def _index_records(records: List[object]):
    """Bucket records by type and by seq for O(1) round pairing."""
    trig_out: Dict[int, int] = {}
    trig_in: Dict[int, int] = {}
    tx: Dict[int, int] = {}
    rx: List[Rx] = []
    apply: List[Apply] = []
    clk: List[Clk] = []
    health: List[Health] = []
    for rec in records:
        if isinstance(rec, TrigOut):
            trig_out.setdefault(rec.seq, rec.t_us)
        elif isinstance(rec, TrigIn):
            trig_in.setdefault(rec.seq, rec.t_us)
        elif isinstance(rec, Tx):
            tx.setdefault(rec.seq, rec.t_leader_us)
        elif isinstance(rec, Rx):
            rx.append(rec)
        elif isinstance(rec, Apply):
            apply.append(rec)
        elif isinstance(rec, Clk):
            clk.append(rec)
        elif isinstance(rec, Health):
            health.append(rec)
    return trig_out, trig_in, tx, rx, apply, clk, health


def correlate(leader: ParsedLog, follower: ParsedLog) -> Correlation:
    """Fuse a leader + follower :class:`ParsedLog` into a :class:`Correlation`."""
    c = Correlation()

    (l_trig_out, l_trig_in, l_tx, _l_rx, _l_apply, _l_clk, _l_health) = _index_records(
        leader.records
    )
    (f_trig_out, f_trig_in, _f_tx, f_rx, f_apply, f_clk, f_health) = _index_records(
        follower.records
    )

    # (a) wire-truth offset per matched round -------------------------------- #
    all_seqs = (
        set(l_trig_out) & set(f_trig_in) & set(f_trig_out) & set(l_trig_in)
    )
    # count rounds that appear in some direction but are not fully paired
    seen = set(l_trig_out) | set(f_trig_in) | set(f_trig_out) | set(l_trig_in)
    c.incomplete_rounds = len(seen) - len(all_seqs)
    for seq in sorted(all_seqs):
        t_l_out = l_trig_out[seq]
        t_f_in = f_trig_in[seq]
        t_f_out = f_trig_out[seq]
        t_l_in = l_trig_in[seq]
        d1 = t_f_in - t_l_out  # O + eps_follower
        d2 = t_f_out - t_l_in  # O - eps_leader
        offset = (d1 + d2) / 2.0
        asymmetry = (d1 - d2) / 2.0
        leader_mid = (t_l_out + t_l_in) / 2.0
        follower_mid = (t_f_in + t_f_out) / 2.0
        c.rounds.append(
            RoundSample(seq, leader_mid, follower_mid, offset, asymmetry)
        )

    offset_by_follower = sorted((r.follower_mid_us, r.offset_us) for r in c.rounds)

    # (b) radio clock-estimate error ---------------------------------------- #
    # clk lines carry no timestamp: reconstruct the follower-local time from the
    # line's position between timestamped neighbours, then diff est_offset
    # against wire truth.
    for rec, t_follower in _reconstruct_times(follower.records, Clk):
        wire = interp_xy(offset_by_follower, t_follower)
        if wire is None:
            continue  # no wire truth to compare against — cannot score this clk
        c.clock_error_series.append((t_follower, rec.est_offset_us - wire))

    # (c) apply-lateness ----------------------------------------------------- #
    # leader stamp per seq: prefer the leader tx log, fall back to the follower
    # rx line's echoed t_leader_us.
    rx_leader_stamp: Dict[int, int] = {}
    for r in f_rx:
        rx_leader_stamp.setdefault(r.seq, r.t_leader_us)
    for a in f_apply:
        t_leader_stamp = l_tx.get(a.seq)
        if t_leader_stamp is None:
            t_leader_stamp = rx_leader_stamp.get(a.seq)
        if t_leader_stamp is None:
            c.unmatched_apply += 1
            continue
        wire = interp_xy(offset_by_follower, a.t_render_us)
        if wire is None:
            c.unmatched_apply += 1
            continue
        apply_leader = a.t_render_us - wire  # follower clock -> leader clock
        c.apply_lateness_us.append(apply_leader - t_leader_stamp)

    # (d) loss / dup / reorder from the follower rx stream ------------------- #
    _stream_integrity(l_tx, f_rx, c)

    # (e) health ------------------------------------------------------------- #
    _health_aggregate(f_health, c)

    return c


def _reconstruct_times(records, kind):
    """Yield ``(record, reconstructed_local_time)`` for every record of type
    ``kind`` (the untimestamped ``clk`` / ``health`` lines).

    Records are appended in capture (line) order, so a record's ordinal in the
    list is a faithful stand-in for its line position. We build a map from the
    ordinals of timestamped records to their device-local times and linearly
    interpolate the untimestamped targets between their bracketing neighbours.
    """
    timed: List[Tuple[int, int]] = []
    targets: List[Tuple[int, object]] = []
    for ordinal, rec in enumerate(records):
        t = logfmt._local_anchor(rec)
        if t is not None:
            timed.append((ordinal, t))
        if isinstance(rec, kind):
            targets.append((ordinal, rec))
    out = []
    for ordinal, rec in targets:
        t = logfmt._interp_by_index(timed, ordinal)
        if t is not None:
            out.append((rec, float(t)))
    return out


def _stream_integrity(l_tx: Dict[int, int], f_rx: List[Rx], c: Correlation) -> None:
    """Loss/dup/reorder from the follower rx seq stream, scoped to the seq range
    the leader actually transmitted when a tx log is present."""
    rx_seqs = [r.seq for r in f_rx]
    if l_tx:
        lo, hi = min(l_tx), max(l_tx)
        expected = hi - lo + 1
    elif rx_seqs:
        lo, hi = min(rx_seqs), max(rx_seqs)
        expected = hi - lo + 1
    else:
        return
    c.stream_expected = expected

    seen: Dict[int, int] = {}
    for s in rx_seqs:
        seen[s] = seen.get(s, 0) + 1
    received_unique = sum(1 for s in range(lo, hi + 1) if s in seen)
    c.loss = expected - received_unique
    c.dup = sum(v - 1 for v in seen.values() if v > 1)

    reorder = 0
    peak = None
    for s in rx_seqs:
        if peak is not None and s < peak:
            reorder += 1
        else:
            peak = s
    c.reorder = reorder


def _health_aggregate(f_health: List[Health], c: Correlation) -> None:
    if not f_health:
        return
    c.health_samples = len(f_health)
    c.fps_min = min(h.fps for h in f_health)
    c.heap_min = min(h.heap_min for h in f_health)
    c.ap_p95_max = max(h.ap_p95_us for h in f_health)
    c.dial_uptime = sum(1 for h in f_health if h.dial_linked == 1) / len(f_health)
    c.health_loss_max = max(h.loss for h in f_health)
    c.health_dup_max = max(h.dup for h in f_health)


# --------------------------------------------------------------------------- #
# Deterministic percentile (numpy-free). Linear interpolation between the two  #
# nearest ranks, matching numpy's default 'linear' method.                    #
# --------------------------------------------------------------------------- #


def percentile(values: List[float], q: float) -> Optional[float]:
    """The ``q``-th percentile (0..100) of ``values`` by linear interpolation.
    Returns ``None`` for an empty input. Deterministic and stdlib-only."""
    if not values:
        return None
    if len(values) == 1:
        return float(values[0])
    s = sorted(values)
    if q <= 0:
        return float(s[0])
    if q >= 100:
        return float(s[-1])
    rank = (q / 100.0) * (len(s) - 1)
    lo = int(rank)
    hi = min(lo + 1, len(s) - 1)
    frac = rank - lo
    return float(s[lo] + (s[hi] - s[lo]) * frac)


def mean(values: List[float]) -> Optional[float]:
    if not values:
        return None
    return sum(values) / len(values)


def clock_error_slope_us_per_s(series: List[Tuple[float, float]]) -> Optional[float]:
    """Least-squares slope of the clock-error series in µs of error per second
    of (follower-clock) elapsed time. Used to characterise a drift-tracking
    failure. ``None`` if fewer than two points or zero time span."""
    if len(series) < 2:
        return None
    xs = [t / 1_000_000.0 for t, _ in series]  # seconds
    ys = [e for _, e in series]
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0:
        return None
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    return sxy / sxx
