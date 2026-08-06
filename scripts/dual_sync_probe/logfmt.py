"""Versioned dual-sync serial grammar.

The parser is deliberately permissive by default so archived July captures
remain readable. ``strict=True`` activates the F2/F3 proof contract: role,
clock timestamp and shared host timestamp omissions become input errors rather
than quietly degrading a verdict.

Strict capture lines are prefixed by the host capture helper:

    host_us=<u64> <firmware line>

The common ``monotonic_ns()`` origin lets the oracle prove that the selected
leader and follower link epochs overlap.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


class LogContractError(ValueError):
    """Raised when strict proof input violates the versioned grammar."""


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
    # Keep the first three fields positional for archived callers.
    est_offset_us: int
    rtt_us: int
    n: int
    t_local_us: Optional[int] = None
    role: Optional[str] = None


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
    # Keep the original six fields positional for archived callers.
    fps: float
    heap_min: int
    ap_p95_us: int
    dial_linked: int
    loss: int
    dup: int
    role: Optional[str] = None
    extras: Tuple[Tuple[str, str], ...] = ()

    def extra_int(self, key: str) -> Optional[int]:
        for name, value in self.extras:
            if name == key:
                try:
                    return int(value)
                except ValueError:
                    return None
        return None


@dataclass(frozen=True)
class Begin:
    role: str


@dataclass(frozen=True)
class LinkUp:
    role: str
    epoch: int
    handle: int
    mtu: int


@dataclass(frozen=True)
class LinkDown:
    role: str
    epoch: int
    reason: int


@dataclass(frozen=True)
class Negotiated:
    role: str
    epoch: int
    interval_units: int
    latency: int
    mtu: int
    phy_tx: int
    phy_rx: int


@dataclass(frozen=True)
class Reset:
    reason: str


@dataclass(frozen=True)
class HostSegment:
    name: str
    phase: str
    t_host_us: int


@dataclass(frozen=True)
class ParsedEntry:
    record: object
    line_index: int
    host_us: Optional[int]


_RE_HOST_PREFIX = re.compile(r"(?:^|\s)host_us=(\d+)\s+")
_RE_STRICT_HOST_PREFIX = re.compile(r"^host_us=(\d+)\s+")
_RE_TRIG_OUT = re.compile(r"\[sync_oracle\]\s+trig_out\s+seq=(\d+)\s+t_us=(\d+)")
_RE_TRIG_IN = re.compile(r"\[sync_oracle\]\s+trig_in\s+seq=(\d+)\s+t_us=(\d+)")
# New clock grammar MUST be attempted before legacy: the legacy expression is
# not end-anchored and would otherwise discard t_local_us without warning.
_RE_CLK_V2 = re.compile(
    r"\[k1_sync\]\s+clk\s+role=(leader|follower)\s+t_local_us=(\d+)"
    r"\s+est_offset_us=(-?\d+)\s+rtt_us=(\d+)\s+n=(\d+)"
)
_RE_CLK_V1 = re.compile(
    r"\[k1_sync\]\s+clk\s+est_offset_us=(-?\d+)\s+rtt_us=(\d+)\s+n=(\d+)"
)
_RE_TX = re.compile(r"\[k1_sync\]\s+tx\s+seq=(\d+)\s+t_leader_us=(\d+)")
_RE_RX = re.compile(
    r"\[k1_sync\]\s+rx\s+seq=(\d+)\s+t_leader_us=(\d+)\s+t_local_us=(\d+)"
)
_RE_APPLY = re.compile(r"\[k1_sync\]\s+apply\s+seq=(\d+)\s+t_render_us=(\d+)")
_RE_HEALTH_HEAD = re.compile(r"\[k1_sync\]\s+health\s+(.+)$")
_RE_BEGIN = re.compile(r"\[k1_sync\]\s+begin\s+role=(leader|follower)\b")
_RE_LINK_UP = re.compile(
    r"\[k1_sync\]\s+link\s+up\s+role=(leader|follower)\s+epoch=(\d+)"
    r"\s+handle=(\d+)\s+mtu=(\d+)"
)
_RE_LINK_DOWN = re.compile(
    r"\[k1_sync\]\s+link\s+down\s+role=(leader|follower)\s+epoch=(\d+)"
    r"\s+reason=(-?\d+)"
)
_RE_NEGOTIATED = re.compile(
    r"\[k1_sync\]\s+negotiated\s+role=(leader|follower)\s+epoch=(\d+)"
    r"\s+interval_units=(\d+)\s+latency=(\d+)\s+mtu=(\d+)"
    r"\s+phy_tx=(\d+)\s+phy_rx=(\d+)"
)
_RE_SEGMENT = re.compile(
    r"\[sync_host\]\s+segment\s+name=([A-Za-z0-9_.-]+)"
    r"\s+phase=(start|end)\s+t_host_us=(\d+)"
)
_RE_KV = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)=([^\s]+)")

_STRICT_PREFIXES = (
    "[sync_oracle] trig_out",
    "[sync_oracle] trig_in",
    "[k1_sync] clk",
    "[k1_sync] tx",
    "[k1_sync] rx",
    "[k1_sync] apply",
    "[k1_sync] health",
    "[k1_sync] link up",
    "[k1_sync] link down",
    "[k1_sync] negotiated",
)


def _parse_health(line: str) -> Optional[Health]:
    match = _RE_HEALTH_HEAD.search(line)
    if not match:
        return None
    values = dict(_RE_KV.findall(match.group(1)))
    required = ("fps", "heap_min", "ap_p95_us", "dial_linked", "loss", "dup")
    if any(key not in values for key in required):
        return None
    role = values.get("role")
    if role not in (None, "leader", "follower"):
        return None
    try:
        extras = tuple(
            sorted(
                (key, value)
                for key, value in values.items()
                if key not in set(required) | {"role"}
            )
        )
        return Health(
            float(values["fps"]),
            int(values["heap_min"]),
            int(values["ap_p95_us"]),
            int(values["dial_linked"]),
            int(values["loss"]),
            int(values["dup"]),
            role=role,
            extras=extras,
        )
    except ValueError:
        return None


def _strict_syntax_error(
    record: object, payload: str, host_us: Optional[int]
) -> Optional[str]:
    """Require complete, unambiguous consumption of a versioned record."""
    patterns = {
        TrigOut: _RE_TRIG_OUT,
        TrigIn: _RE_TRIG_IN,
        Clk: _RE_CLK_V2,
        Tx: _RE_TX,
        Rx: _RE_RX,
        Apply: _RE_APPLY,
        Begin: _RE_BEGIN,
        LinkUp: _RE_LINK_UP,
        LinkDown: _RE_LINK_DOWN,
        Negotiated: _RE_NEGOTIATED,
        HostSegment: _RE_SEGMENT,
    }
    if isinstance(record, Health):
        prefix = "[k1_sync] health "
        if not payload.startswith(prefix):
            return "Health does not use the versioned grammar"
        tokens = payload[len(prefix) :].split()
        if not tokens or any(_RE_KV.fullmatch(token) is None for token in tokens):
            return "Health has malformed or trailing fields"
        keys = [token.split("=", 1)[0] for token in tokens]
        if len(keys) != len(set(keys)):
            return "Health contains duplicate keys"
        return None
    pattern = patterns.get(type(record))
    if pattern is not None and pattern.fullmatch(payload) is None:
        return f"{type(record).__name__} has trailing or malformed fields"
    if (
        isinstance(record, HostSegment)
        and host_us is not None
        and record.t_host_us != host_us
    ):
        return "HostSegment t_host_us does not match host_us prefix"
    return None


def parse_line(line: str):
    """Parse one firmware or host marker line; return ``None`` for noise."""
    match = _RE_SEGMENT.search(line)
    if match:
        return HostSegment(match.group(1), match.group(2), int(match.group(3)))
    if "rst:" in line:
        return Reset(line.strip())
    if "[sync_oracle]" in line:
        match = _RE_TRIG_OUT.search(line)
        if match:
            return TrigOut(int(match.group(1)), int(match.group(2)))
        match = _RE_TRIG_IN.search(line)
        if match:
            return TrigIn(int(match.group(1)), int(match.group(2)))
        return None
    if "[k1_sync]" not in line:
        return None

    match = _RE_RX.search(line)
    if match:
        return Rx(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    match = _RE_TX.search(line)
    if match:
        return Tx(int(match.group(1)), int(match.group(2)))
    match = _RE_APPLY.search(line)
    if match:
        return Apply(int(match.group(1)), int(match.group(2)))
    match = _RE_CLK_V2.search(line)
    if match:
        return Clk(
            int(match.group(3)),
            int(match.group(4)),
            int(match.group(5)),
            t_local_us=int(match.group(2)),
            role=match.group(1),
        )
    match = _RE_CLK_V1.search(line)
    if match:
        return Clk(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    health = _parse_health(line)
    if health is not None:
        return health
    match = _RE_LINK_UP.search(line)
    if match:
        return LinkUp(
            match.group(1),
            int(match.group(2)),
            int(match.group(3)),
            int(match.group(4)),
        )
    match = _RE_LINK_DOWN.search(line)
    if match:
        return LinkDown(match.group(1), int(match.group(2)), int(match.group(3)))
    match = _RE_NEGOTIATED.search(line)
    if match:
        return Negotiated(
            match.group(1),
            int(match.group(2)),
            int(match.group(3)),
            int(match.group(4)),
            int(match.group(5)),
            int(match.group(6)),
            int(match.group(7)),
        )
    match = _RE_BEGIN.search(line)
    if match:
        return Begin(match.group(1))
    return None


@dataclass
class ParsedLog:
    records: List[object] = field(default_factory=list)
    entries: List[ParsedEntry] = field(default_factory=list)
    anchors: List[Tuple[int, int]] = field(default_factory=list)
    total_lines: int = 0
    skipped_lines: int = 0
    contract_errors: List[str] = field(default_factory=list)

    def local_time_at(self, line_index: int) -> Optional[int]:
        return _interp_by_index(self.anchors, line_index)

    def host_times(self) -> List[int]:
        return [entry.host_us for entry in self.entries if entry.host_us is not None]


def _local_anchor(record) -> Optional[int]:
    if isinstance(record, (TrigOut, TrigIn)):
        return record.t_us
    if isinstance(record, Rx):
        return record.t_local_us
    if isinstance(record, Apply):
        return record.t_render_us
    if isinstance(record, Tx):
        return record.t_leader_us
    if isinstance(record, Clk):
        return record.t_local_us
    return None


def _strict_error_for(
    record: object,
    payload: str,
    host_us: Optional[int],
    expected_role: Optional[str],
) -> Optional[str]:
    if host_us is None and isinstance(
        record,
        (
            TrigOut,
            TrigIn,
            Clk,
            Tx,
            Rx,
            Apply,
            Health,
            Begin,
            LinkUp,
            LinkDown,
            Negotiated,
            Reset,
            HostSegment,
        ),
    ):
        return "recognised proof line is missing host_us prefix"
    role = getattr(record, "role", None)
    if isinstance(record, (Health, Clk)) and role is None:
        return f"{type(record).__name__} is missing role"
    if expected_role is not None and role is not None and role != expected_role:
        return f"record role={role} does not match expected_role={expected_role}"
    if isinstance(record, Clk) and record.t_local_us is None:
        return "Clk is missing t_local_us"
    if isinstance(record, Health) and record.dial_linked not in (0, 1):
        return "Health dial_linked is not 0 or 1"
    return _strict_syntax_error(record, payload, host_us)


def parse_log(
    text,
    *,
    strict: bool = False,
    expected_role: Optional[str] = None,
) -> ParsedLog:
    """Parse a device log.

    Permissive mode preserves archived input. Strict mode raises
    :class:`LogContractError` after collecting every contract error.
    """
    lines = text.splitlines() if isinstance(text, str) else list(text)
    output = ParsedLog(total_lines=len(lines))
    for index, line in enumerate(lines):
        strict_host_match = _RE_STRICT_HOST_PREFIX.match(line)
        host_match = strict_host_match or _RE_HOST_PREFIX.search(line)
        host_us = int(host_match.group(1)) if host_match else None
        payload = (
            line[strict_host_match.end() :]
            if strict_host_match is not None
            else line
        )
        record = parse_line(line)
        if record is None:
            if line.strip():
                output.skipped_lines += 1
                if strict and any(prefix in line for prefix in _STRICT_PREFIXES):
                    output.contract_errors.append(
                        f"line {index + 1}: malformed required record: {line.strip()}"
                    )
            continue
        output.records.append(record)
        output.entries.append(ParsedEntry(record, index, host_us))
        anchor = _local_anchor(record)
        if anchor is not None:
            output.anchors.append((index, anchor))
        if strict:
            if strict_host_match is None:
                error = "recognised proof line must start with host_us prefix"
            elif _RE_HOST_PREFIX.search(payload):
                error = "record contains multiple host_us prefixes"
            else:
                error = _strict_error_for(
                    record, payload, host_us, expected_role
                )
            if error:
                output.contract_errors.append(f"line {index + 1}: {error}")
    output.anchors.sort()
    if strict and output.contract_errors:
        raise LogContractError("; ".join(output.contract_errors))
    return output


def _interp_by_index(
    anchors: List[Tuple[int, int]], line_index: int
) -> Optional[int]:
    if not anchors:
        return None
    if line_index <= anchors[0][0]:
        return anchors[0][1]
    if line_index >= anchors[-1][0]:
        return anchors[-1][1]
    low, high = 0, len(anchors) - 1
    while low + 1 < high:
        middle = (low + high) // 2
        if anchors[middle][0] <= line_index:
            low = middle
        else:
            high = middle
    x0, y0 = anchors[low]
    x1, y1 = anchors[high]
    if x1 == x0:
        return y0
    fraction = (line_index - x0) / (x1 - x0)
    return int(round(y0 + fraction * (y1 - y0)))


def interp_xy(samples: List[Tuple[float, float]], x: float) -> Optional[float]:
    if not samples:
        return None
    if x <= samples[0][0]:
        return samples[0][1]
    if x >= samples[-1][0]:
        return samples[-1][1]
    low, high = 0, len(samples) - 1
    while low + 1 < high:
        middle = (low + high) // 2
        if samples[middle][0] <= x:
            low = middle
        else:
            high = middle
    x0, y0 = samples[low]
    x1, y1 = samples[high]
    if x1 == x0:
        return y0
    fraction = (x - x0) / (x1 - x0)
    return y0 + fraction * (y1 - y0)


def fmt_trig_out(seq: int, t_us: int) -> str:
    return f"[sync_oracle] trig_out seq={seq} t_us={t_us}"


def fmt_trig_in(seq: int, t_us: int) -> str:
    return f"[sync_oracle] trig_in seq={seq} t_us={t_us}"


def fmt_clk(
    est_offset_us: int,
    rtt_us: int,
    n: int,
    *,
    t_local_us: Optional[int] = None,
    role: Optional[str] = None,
) -> str:
    if role is None and t_local_us is None:
        return (
            f"[k1_sync] clk est_offset_us={est_offset_us} "
            f"rtt_us={rtt_us} n={n}"
        )
    if role is None or t_local_us is None:
        raise ValueError("strict clk grammar requires both role and t_local_us")
    return (
        f"[k1_sync] clk role={role} t_local_us={t_local_us} "
        f"est_offset_us={est_offset_us} rtt_us={rtt_us} n={n}"
    )


def fmt_tx(seq: int, t_leader_us: int) -> str:
    return f"[k1_sync] tx seq={seq} t_leader_us={t_leader_us}"


def fmt_rx(seq: int, t_leader_us: int, t_local_us: int) -> str:
    return (
        f"[k1_sync] rx seq={seq} t_leader_us={t_leader_us} "
        f"t_local_us={t_local_us}"
    )


def fmt_apply(seq: int, t_render_us: int) -> str:
    return f"[k1_sync] apply seq={seq} t_render_us={t_render_us}"


def fmt_health(
    fps: float,
    heap_min: int,
    ap_p95_us: int,
    dial_linked: int,
    loss: int,
    dup: int,
    *,
    role: Optional[str] = None,
    extras: Optional[dict] = None,
) -> str:
    role_field = "" if role is None else f"role={role} "
    extra_fields = ""
    if extras:
        extra_fields = " " + " ".join(
            f"{key}={value}" for key, value in sorted(extras.items())
        )
    return (
        f"[k1_sync] health {role_field}fps={fps:.2f} heap_min={heap_min} "
        f"ap_p95_us={ap_p95_us} dial_linked={dial_linked} "
        f"loss={loss} dup={dup}{extra_fields}"
    )


def fmt_begin(role: str) -> str:
    return f"[k1_sync] begin role={role}"


def fmt_link_up(role: str, epoch: int, handle: int, mtu: int) -> str:
    return (
        f"[k1_sync] link up role={role} epoch={epoch} "
        f"handle={handle} mtu={mtu}"
    )


def fmt_link_down(role: str, epoch: int, reason: int) -> str:
    return f"[k1_sync] link down role={role} epoch={epoch} reason={reason}"


def fmt_negotiated(
    role: str,
    epoch: int,
    interval_units: int,
    latency: int,
    mtu: int,
    phy_tx: int,
    phy_rx: int,
) -> str:
    return (
        f"[k1_sync] negotiated role={role} epoch={epoch} "
        f"interval_units={interval_units} latency={latency} mtu={mtu} "
        f"phy_tx={phy_tx} phy_rx={phy_rx}"
    )


def fmt_segment(name: str, phase: str, t_host_us: int) -> str:
    return (
        f"[sync_host] segment name={name} phase={phase} "
        f"t_host_us={t_host_us}"
    )
