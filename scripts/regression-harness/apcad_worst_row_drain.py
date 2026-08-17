"""Drain UART until the declared APCAD soak worst-row set is newline-complete.

This is a host-only capture-runner correction. It must not send ``vp_perf=start``
and it must not wait an arbitrary interval in place of completion.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Optional


SOAK_DONE_MARKER = "APCAD_SOAK_DONE,"
SOAK_WORST_MARKER = "APCAD_SOAK_WORST,"


class WorstRowDrainError(RuntimeError):
    """Fail-closed: timeout or declared/parsed worst-row mismatch."""


def collect_lines(existing: list[str], chunk: str, carry: str) -> str:
    text = carry + chunk
    parts = text.splitlines()
    if text.endswith(("\n", "\r")):
        carry = ""
    elif parts:
        carry = parts.pop()
    else:
        carry = text
    for raw in parts:
        line = raw.strip()
        if line:
            existing.append(line)
    return carry


def _soak_done_payload(lines: list[str]) -> Optional[str]:
    for line in reversed(lines):
        marker = line.find(SOAK_DONE_MARKER)
        if marker >= 0:
            return line[marker + len(SOAK_DONE_MARKER) :]
    return None


def declared_worst_count(lines: list[str]) -> Optional[int]:
    payload = _soak_done_payload(lines)
    if payload is None:
        return None
    for part in payload.split(","):
        if part.startswith("worst_count="):
            try:
                return int(part.split("=", 1)[1])
            except ValueError as exc:
                raise WorstRowDrainError(f"unparsable worst_count in {part!r}") from exc
    raise WorstRowDrainError("APCAD_SOAK_DONE is missing worst_count")


def newline_complete_worst_rows(lines: list[str]) -> list[str]:
    return [line for line in lines if line.startswith(SOAK_WORST_MARKER)]


def drain_declared_worst_rows(
    read_bytes: Callable[[], bytes],
    lines: list[str],
    *,
    timeout_s: float,
    initial_carry: str = "",
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    poll_s: float = 0.001,
) -> str:
    """Append UART lines until ``worst_count`` complete worst rows are present.

    Completion requires:
    - ``APCAD_SOAK_DONE`` with a declared ``worst_count``
    - exactly that many newline-complete ``APCAD_SOAK_WORST`` rows
    - empty carry (no partial buffered line)

    Returns the (empty) carry on success. Does not emit host commands.
    """
    if timeout_s <= 0:
        raise WorstRowDrainError("worst-row drain timeout must be positive")
    carry = initial_carry
    deadline = monotonic() + timeout_s
    while True:
        declared = declared_worst_count(lines)
        complete = newline_complete_worst_rows(lines)
        if declared is not None:
            if len(complete) > declared:
                raise WorstRowDrainError(
                    f"worst-row count mismatch: declared={declared} parsed={len(complete)}"
                )
            if len(complete) == declared and not carry.strip():
                return carry
        if monotonic() >= deadline:
            parsed = len(newline_complete_worst_rows(lines))
            raise WorstRowDrainError(
                "worst-row drain timeout/fail-closed: "
                f"declared={declared} parsed={parsed} carry={bool(carry.strip())}"
            )
        chunk = read_bytes()
        if not chunk:
            sleep(poll_s)
            continue
        carry = collect_lines(lines, chunk.decode("utf-8", errors="replace"), carry)
