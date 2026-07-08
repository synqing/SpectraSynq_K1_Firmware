"""Canonical serial log-line grammar shared by the P0.4 probe firmware and the
host oracle. Change a line's shape here and you MUST change the firmware emitter
in the same breath — this module is the single source of truth for both ends.

Every timestamp is a device-local ``micros()`` value, treated as an unsigned
64-bit integer (no wrap within a probe run). Lines may be interleaved with
arbitrary unrelated serial noise; the parser matches by tag and skips anything
it cannot fully parse (including truncated lines), counting the skips so a log
that is mostly garbage cannot masquerade as a clean capture.

Grammar (see artifacts/k1_dual_sync_eval_2026-07-08/probe-log-contract.md §2):

    [sync_oracle] trig_out seq=<n> t_us=<u64>
    [sync_oracle] trig_in seq=<n> t_us=<u64>
    [k1_sync] clk est_offset_us=<i64> rtt_us=<u32> n=<samples>
    [k1_sync] tx seq=<n> t_leader_us=<u64>
    [k1_sync] rx seq=<n> t_leader_us=<u64> t_local_us=<u64>
    [k1_sync] apply seq=<n> t_render_us=<u64>
    [k1_sync] health fps=<f> heap_min=<u32> ap_p95_us=<u32> dial_linked=<0|1> loss=<u32> dup=<u32>
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

# --------------------------------------------------------------------------- #
# Record types (one per grammar line).                                        #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class TrigOut:
    seq: int
    t_us: int


@dataclass(frozen=True)
class TrigIn:
    seq: int
    t_us: int


@dataclass(frozen=True)
class Clk:
    est_offset_us: int
    rtt_us: int
    n: int


@dataclass(frozen=True)
class Tx:
    seq: int
    t_leader_us: int


@dataclass(frozen=True)
class Rx:
    seq: int
    t_leader_us: int
    t_local_us: int


@dataclass(frozen=True)
class Apply:
    seq: int
    t_render_us: int


@dataclass(frozen=True)
class Health:
    fps: float
    heap_min: int
    ap_p95_us: int
    dial_linked: int
    loss: int
    dup: int


# --------------------------------------------------------------------------- #
# Line grammar (compiled once). ``search`` (not ``match``) so a line may carry #
# a leading timestamp/prefix from the serial monitor and still parse.          #
# --------------------------------------------------------------------------- #

_RE_TRIG_OUT = re.compile(r"\[sync_oracle\]\s+trig_out\s+seq=(\d+)\s+t_us=(\d+)")
_RE_TRIG_IN = re.compile(r"\[sync_oracle\]\s+trig_in\s+seq=(\d+)\s+t_us=(\d+)")
_RE_CLK = re.compile(
    r"\[k1_sync\]\s+clk\s+est_offset_us=(-?\d+)\s+rtt_us=(\d+)\s+n=(\d+)"
)
_RE_TX = re.compile(r"\[k1_sync\]\s+tx\s+seq=(\d+)\s+t_leader_us=(\d+)")
_RE_RX = re.compile(
    r"\[k1_sync\]\s+rx\s+seq=(\d+)\s+t_leader_us=(\d+)\s+t_local_us=(\d+)"
)
_RE_APPLY = re.compile(r"\[k1_sync\]\s+apply\s+seq=(\d+)\s+t_render_us=(\d+)")
_RE_HEALTH = re.compile(
    r"\[k1_sync\]\s+health\s+fps=([0-9]+(?:\.[0-9]+)?)\s+heap_min=(\d+)"
    r"\s+ap_p95_us=(\d+)\s+dial_linked=([01])\s+loss=(\d+)\s+dup=(\d+)"
)


def parse_line(line: str):
    """Parse a single serial line into a record, or return ``None`` if it does
    not match any known grammar (noise, or a truncated line whose fields are
    cut off). Cheap tag pre-check keeps the common noise case fast."""
    if "[sync_oracle]" in line:
        m = _RE_TRIG_OUT.search(line)
        if m:
            return TrigOut(int(m.group(1)), int(m.group(2)))
        m = _RE_TRIG_IN.search(line)
        if m:
            return TrigIn(int(m.group(1)), int(m.group(2)))
        return None
    if "[k1_sync]" in line:
        m = _RE_RX.search(line)  # try rx before tx: rx is a superset of tx's prefix
        if m:
            return Rx(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        m = _RE_TX.search(line)
        if m:
            return Tx(int(m.group(1)), int(m.group(2)))
        m = _RE_APPLY.search(line)
        if m:
            return Apply(int(m.group(1)), int(m.group(2)))
        m = _RE_CLK.search(line)
        if m:
            return Clk(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        m = _RE_HEALTH.search(line)
        if m:
            return Health(
                float(m.group(1)),
                int(m.group(2)),
                int(m.group(3)),
                int(m.group(4)),
                int(m.group(5)),
                int(m.group(6)),
            )
        return None
    return None


# --------------------------------------------------------------------------- #
# Parsed-log container.                                                        #
# --------------------------------------------------------------------------- #


@dataclass
class ParsedLog:
    """All records from one device's log, in capture order, plus the
    device-local-time anchors used to reconstruct the time of untimestamped
    lines (``clk`` / ``health``).

    ``anchors`` is a sorted list of ``(line_index, local_us)`` taken from every
    line that DOES carry a device-local timestamp. Because a single log belongs
    to a single device (one local clock), it is safe to treat every timestamp
    field in that file — trig t_us, rx t_local_us, apply t_render_us, tx
    t_leader_us — as samples of the same local clock for interpolation purposes.
    """

    records: List[object] = field(default_factory=list)
    anchors: List[Tuple[int, int]] = field(default_factory=list)
    total_lines: int = 0
    skipped_lines: int = 0

    def local_time_at(self, line_index: int) -> Optional[int]:
        """Reconstruct the device-local time of the line at ``line_index`` by
        linear interpolation between bracketing anchors. Returns ``None`` only
        if the log has no anchors at all."""
        return _interp_by_index(self.anchors, line_index)


def _local_anchor(rec) -> Optional[int]:
    """The device-local timestamp a record contributes, if any."""
    if isinstance(rec, (TrigOut, TrigIn)):
        return rec.t_us
    if isinstance(rec, Rx):
        return rec.t_local_us
    if isinstance(rec, Apply):
        return rec.t_render_us
    if isinstance(rec, Tx):
        return rec.t_leader_us
    return None  # Clk / Health have no timestamp


def parse_log(text) -> ParsedLog:
    """Parse a whole device log (a string, or an iterable of lines) into a
    :class:`ParsedLog`. Tolerant of noise and truncation by construction."""
    if isinstance(text, str):
        lines = text.splitlines()
    else:
        lines = list(text)

    out = ParsedLog()
    out.total_lines = len(lines)
    for idx, line in enumerate(lines):
        rec = parse_line(line)
        if rec is None:
            # A blank line is not a "skipped" data line worth flagging.
            if line.strip():
                out.skipped_lines += 1
            continue
        out.records.append(rec)
        anchor = _local_anchor(rec)
        if anchor is not None:
            out.anchors.append((idx, anchor))
    out.anchors.sort()
    return out


# --------------------------------------------------------------------------- #
# Deterministic interpolation helpers (shared by correlate.py).               #
# --------------------------------------------------------------------------- #


def _interp_by_index(anchors: List[Tuple[int, int]], line_index: int) -> Optional[int]:
    """Interpolate a device-local time for ``line_index`` from sorted
    ``(index, time)`` anchors. Clamps at the ends; ``None`` if no anchors."""
    if not anchors:
        return None
    if line_index <= anchors[0][0]:
        return anchors[0][1]
    if line_index >= anchors[-1][0]:
        return anchors[-1][1]
    lo, hi = 0, len(anchors) - 1
    while lo + 1 < hi:
        mid = (lo + hi) // 2
        if anchors[mid][0] <= line_index:
            lo = mid
        else:
            hi = mid
    x0, y0 = anchors[lo]
    x1, y1 = anchors[hi]
    if x1 == x0:
        return y0
    frac = (line_index - x0) / (x1 - x0)
    return y0 + frac * (y1 - y0)


def interp_xy(samples: List[Tuple[float, float]], x: float) -> Optional[float]:
    """Linear interpolation of ``y`` at ``x`` over a list of ``(x, y)`` samples.
    ``samples`` must be sorted by ``x``. Clamps at the ends; ``None`` if empty."""
    if not samples:
        return None
    if x <= samples[0][0]:
        return samples[0][1]
    if x >= samples[-1][0]:
        return samples[-1][1]
    lo, hi = 0, len(samples) - 1
    while lo + 1 < hi:
        mid = (lo + hi) // 2
        if samples[mid][0] <= x:
            lo = mid
        else:
            hi = mid
    x0, y0 = samples[lo]
    x1, y1 = samples[hi]
    if x1 == x0:
        return y0
    frac = (x - x0) / (x1 - x0)
    return y0 + frac * (y1 - y0)


# --------------------------------------------------------------------------- #
# Line constructors — the firmware-side format authority. Keeping the emit and #
# parse sides in one file guarantees they cannot drift.                        #
# --------------------------------------------------------------------------- #


def fmt_trig_out(seq: int, t_us: int) -> str:
    return f"[sync_oracle] trig_out seq={seq} t_us={t_us}"


def fmt_trig_in(seq: int, t_us: int) -> str:
    return f"[sync_oracle] trig_in seq={seq} t_us={t_us}"


def fmt_clk(est_offset_us: int, rtt_us: int, n: int) -> str:
    return f"[k1_sync] clk est_offset_us={est_offset_us} rtt_us={rtt_us} n={n}"


def fmt_tx(seq: int, t_leader_us: int) -> str:
    return f"[k1_sync] tx seq={seq} t_leader_us={t_leader_us}"


def fmt_rx(seq: int, t_leader_us: int, t_local_us: int) -> str:
    return f"[k1_sync] rx seq={seq} t_leader_us={t_leader_us} t_local_us={t_local_us}"


def fmt_apply(seq: int, t_render_us: int) -> str:
    return f"[k1_sync] apply seq={seq} t_render_us={t_render_us}"


def fmt_health(
    fps: float, heap_min: int, ap_p95_us: int, dial_linked: int, loss: int, dup: int
) -> str:
    return (
        f"[k1_sync] health fps={fps:.2f} heap_min={heap_min} "
        f"ap_p95_us={ap_p95_us} dial_linked={dial_linked} loss={loss} dup={dup}"
    )
