"""Prove the APCAD worst-row host drain closes the vp_perf=start race."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def _load():
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "regression-harness"
        / "apcad_worst_row_drain.py"
    )
    spec = importlib.util.spec_from_file_location("apcad_worst_row_drain", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


drain = _load()


class Clock:
    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t

    def advance(self, dt: float) -> None:
        self.t += dt


class ScriptedUART:
    def __init__(self, clock: Clock, events: list[tuple[float, bytes]]) -> None:
        self.clock = clock
        self.events = list(events)

    def read_bytes(self) -> bytes:
        due: list[bytes] = []
        remaining: list[tuple[float, bytes]] = []
        now = self.clock()
        for when, payload in self.events:
            if when <= now:
                due.append(payload)
            else:
                remaining.append((when, payload))
        self.events = remaining
        return b"".join(due)

    def sleep(self, dt: float) -> None:
        self.clock.advance(dt)


def _soak_done(count: int = 16) -> str:
    return f"APCAD_SOAK_DONE,schema_ver=2,stage_detail=1,rows=100,worst_count={count}"


def _worst_row(rank: int) -> str:
    return (
        f"APCAD_SOAK_WORST,schema_ver=2,stage_detail=1,rank={rank},"
        f"frame={1000 + rank},t={2000 + rank},active_us=12000,total_us=12040"
    )


def _drain(
    clock: Clock,
    uart: ScriptedUART,
    lines: list[str],
    *,
    timeout_s: float,
    carry: str = "",
    sleep=None,
) -> str:
    return drain.drain_declared_worst_rows(
        uart.read_bytes,
        lines,
        timeout_s=timeout_s,
        initial_carry=carry,
        monotonic=clock,
        sleep=sleep or uart.sleep,
        poll_s=0.001,
    )


def test_final_worst_row_arriving_more_than_5ms_after_soak_done_is_accepted():
    clock = Clock()
    lines = [_soak_done(16)]
    payload = "".join(_worst_row(rank) + "\n" for rank in range(16)).encode()
    uart = ScriptedUART(clock, [(0.006, payload)])
    carry = _drain(clock, uart, lines, timeout_s=1.0)
    assert carry == ""
    assert clock() >= 0.006
    rows = drain.newline_complete_worst_rows(lines)
    assert len(rows) == 16
    assert all(row.startswith("APCAD_SOAK_WORST,") for row in rows)


def test_final_worst_row_fragmented_across_serial_reads_is_accepted():
    clock = Clock()
    lines = [_soak_done(16)]
    complete = "".join(_worst_row(rank) + "\n" for rank in range(15))
    prefix, suffix = _worst_row(15)[:40], _worst_row(15)[40:] + "\n"
    uart = ScriptedUART(
        clock,
        [
            (0.0, complete.encode() + prefix.encode()),
            (0.003, suffix.encode()),
        ],
    )
    saw_incomplete = {"value": False}

    def sleep(dt: float) -> None:
        if clock() < 0.003:
            assert len(drain.newline_complete_worst_rows(lines)) == 15
            saw_incomplete["value"] = True
        uart.sleep(dt)

    carry = _drain(clock, uart, lines, timeout_s=1.0, sleep=sleep)
    assert saw_incomplete["value"] is True
    assert carry == ""
    assert clock() >= 0.003
    rows = drain.newline_complete_worst_rows(lines)
    assert len(rows) == 16
    assert rows[-1].startswith("APCAD_SOAK_WORST,")
    assert "rank=15" in rows[-1]


def test_declared_worst_row_never_arriving_is_timeout_fail_closed():
    clock = Clock()
    lines = [_soak_done(16)]
    uart = ScriptedUART(clock, [])
    with pytest.raises(drain.WorstRowDrainError, match="timeout/fail-closed"):
        _drain(clock, uart, lines, timeout_s=0.05)
    assert drain.newline_complete_worst_rows(lines) == []
    assert clock() >= 0.05
