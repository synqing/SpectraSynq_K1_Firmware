"""Fail-closed dual-SyncLink host capture.

This module owns serial I/O so the shell entry point stays a thin wrapper.
Both ports use one host-monotonic clock, remain open for the complete run, and
are restored to ``sync_fault=off`` before close whenever the follower opened.

The F0 segmented flow validates capture and oracle plumbing only. It is not a
Gate-0 silicon proof.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from . import gate_eval, logfmt

SUPPORTED_FAULTS = frozenset(("off", "delay5", "delay20", "drop10"))
SEGMENT_FAULTS = {
    "off": "off",
    "delay5": "delay5",
    "delay20": "delay20",
    "drop10": "drop10",
    "restored": "off",
}
DEFAULT_BAUD = 115200
_CHIP_ID_RE = re.compile(r"^[0-9A-Fa-f]{8}$")
_BUILD_RE = re.compile(
    r"^BUILD:\s+version=(\S+)\s+git=([0-9A-Za-z]+)\s+"
    r"epoch=(\d+)\s+env=(\S+)$"
)
_IMAGE_ID_RE = re.compile(r"IMAGE_ID: app_elf_sha256=([0-9a-f]{64})")
_RUNTIME_ID_RE = re.compile(
    r"RUNTIME_ID: boot_nonce=([0-9a-f]{16})\s+"
    r"uptime_ms=(\d+)\s+reset_reason=(-?\d+)"
)
_DIAL_STATUS_RE = re.compile(
    r"DIAL_STATUS: linked=(0|1)\s+generation=(\d+)"
    r"\s+notify=(\d+)\s+decoded=(\d+)\s+enqueued=(\d+)"
    r"\s+apply_ok=(\d+)\s+apply_fail=(\d+)"
    r"\s+queue_drops=(\d+)\s+decode_errors=(\d+)"
    r"\s+dial_mode_apply_ok=(\d+)"
    r"\s+confirm_write_ok=(\d+)\s+confirm_write_fail=(\d+)"
    r"\s+dial_confirm_write_ok=(\d+)"
    r"\s+last_confirm_pm=(\d+)\s+last_confirm_sm=(\d+)"
)
_SYNC_STATUS_RE = re.compile(
    r"^SYNC_STATUS:\s+role=(leader|follower)\s+linked=(0|1)$"
)


class CaptureContractError(RuntimeError):
    """Capture input, acknowledgement, or proof contract failure."""


def fault_for_segment(name: str) -> str:
    """Return the F0 firmware token for a segment label."""
    try:
        return SEGMENT_FAULTS[name]
    except KeyError as error:
        supported = ",".join(SEGMENT_FAULTS)
        raise CaptureContractError(
            f"unsupported F0 segment {name!r}; supported: {supported}; "
            "clockoff is F3-only"
        ) from error


def parse_segments(value: str) -> tuple[str, ...]:
    segments = tuple(part.strip() for part in value.split(",") if part.strip())
    if not segments:
        raise CaptureContractError("at least one segment is required")
    for segment in segments:
        fault_for_segment(segment)
    return segments


def _open_serial(port: str, baud: int):
    try:
        import serial
    except Exception as error:  # pragma: no cover - depends on host runtime
        raise CaptureContractError(f"pyserial unavailable: {error}") from error
    try:
        return serial.Serial(
            port,
            baud,
            timeout=0.01,
            write_timeout=1.0,
            exclusive=True,
        )
    except TypeError:  # pragma: no cover - Windows pyserial has no exclusive
        return serial.Serial(port, baud, timeout=0.01, write_timeout=1.0)


def _atomic_text(path: Path, text: str) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    with temporary.open("x", encoding="utf-8") as output:
        output.write(text)
        output.flush()
        os.fsync(output.fileno())
    os.replace(temporary, path)


@dataclass
class _RoleWriter:
    session_file: object
    segment_file: Optional[object] = None
    line_count: int = 0

    def write(self, line: str) -> None:
        self.session_file.write(line)
        self.session_file.flush()
        self.line_count += 1
        if self.segment_file is not None:
            self.segment_file.write(line)
            self.segment_file.flush()


class DualCapture:
    """Two open serial transports sharing one host-time origin."""

    def __init__(
        self,
        leader,
        follower,
        leader_writer: _RoleWriter,
        follower_writer: _RoleWriter,
        *,
        monotonic_ns: Callable[[], int] = time.monotonic_ns,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.streams = {"leader": leader, "follower": follower}
        self.writers = {
            "leader": leader_writer,
            "follower": follower_writer,
        }
        self._monotonic_ns = monotonic_ns
        self._sleep = sleep
        self._origin_ns = monotonic_ns()

    def host_us(self) -> int:
        return max(0, (self._monotonic_ns() - self._origin_ns) // 1000)

    def marker(self, name: str, phase: str) -> None:
        host_us = self.host_us()
        record = logfmt.fmt_segment(name, phase, host_us)
        line = f"host_us={host_us} {record}\n"
        for writer in self.writers.values():
            writer.write(line)

    def clear_pending_input(self) -> None:
        """Prevent a buffered acknowledgement from satisfying a new command."""
        for stream in self.streams.values():
            reset = getattr(stream, "reset_input_buffer", None)
            if callable(reset):
                reset()

    def _read_one(self, role: str) -> Optional[str]:
        raw = self.streams[role].readline()
        if not raw:
            return None
        if isinstance(raw, bytes):
            text = raw.decode("utf-8", errors="replace")
        else:
            text = str(raw)
        text = text.rstrip("\r\n")
        line = f"host_us={self.host_us()} {text}\n"
        self.writers[role].write(line)
        return text

    def pump(self, duration_s: float) -> None:
        deadline = self._monotonic_ns() + int(max(0.0, duration_s) * 1e9)
        while self._monotonic_ns() < deadline:
            received = False
            for role in ("leader", "follower"):
                received = self._read_one(role) is not None or received
            if not received:
                self._sleep(0.001)

    def set_fault(self, mode: str, timeout_s: float) -> None:
        if mode not in SUPPORTED_FAULTS:
            raise CaptureContractError(f"unsupported firmware fault {mode!r}")
        command = f":sync_fault={mode}\n".encode("ascii")
        self.streams["follower"].write(command)
        self.streams["follower"].flush()
        required = {f"SYNC_FAULT: {mode}", f"[k1_sync] fault={mode}"}
        seen: set[str] = set()
        deadline = self._monotonic_ns() + int(max(0.0, timeout_s) * 1e9)
        while self._monotonic_ns() < deadline and seen != required:
            received = False
            for role in ("leader", "follower"):
                line = self._read_one(role)
                received = line is not None or received
                if role == "follower" and line in required:
                    seen.add(line)
            if not received:
                self._sleep(0.001)
        missing = sorted(required - seen)
        if missing:
            raise CaptureContractError(
                f"fresh exact sync_fault={mode} ACK missing: {missing}"
            )

    def _query(self, role: str, command: str, matcher, timeout_s: float):
        self.streams[role].write(f":{command}\n".encode("ascii"))
        self.streams[role].flush()
        deadline = self._monotonic_ns() + int(max(0.0, timeout_s) * 1e9)
        while self._monotonic_ns() < deadline:
            received = False
            for read_role in ("leader", "follower"):
                line = self._read_one(read_role)
                received = line is not None or received
                if read_role == role and line is not None:
                    match = matcher(line)
                    if match is not None:
                        return match
            if not received:
                self._sleep(0.001)
        raise CaptureContractError(
            f"{role} :{command} response missing before timeout"
        )

    def verify_devices(
        self, expectations: dict[str, dict[str, str]], timeout_s: float
    ) -> dict[str, dict[str, str | int]]:
        """Read back chip and build identity from both already-open ports."""
        observed: dict[str, dict[str, str | int]] = {}
        self.clear_pending_input()
        for role in ("leader", "follower"):
            expected = expectations[role]
            chip = self._query(
                role,
                "chip_id",
                lambda line: line.upper() if _CHIP_ID_RE.fullmatch(line) else None,
                timeout_s,
            )
            if chip != expected["chip_id"].upper():
                raise CaptureContractError(
                    f"{role} chip mismatch: observed {chip}, "
                    f"expected {expected['chip_id'].upper()}"
                )

            def match_build(line):
                match = _BUILD_RE.fullmatch(line)
                return match.groups() if match else None

            version, git_hash, epoch, env = self._query(
                role, "build", match_build, timeout_s
            )
            expected_sha = expected["source_sha"].lower()
            if not expected_sha.startswith(git_hash.lower()) or len(git_hash) < 7:
                raise CaptureContractError(
                    f"{role} build git mismatch: observed {git_hash}, "
                    f"expected prefix of {expected_sha}"
                )
            if env != expected["env"]:
                raise CaptureContractError(
                    f"{role} build env mismatch: observed {env}, "
                    f"expected {expected['env']}"
                )
            expected_image = expected.get("app_elf_sha256")
            observed_image = self._query(
                role,
                "image_id",
                lambda line: (
                    _IMAGE_ID_RE.fullmatch(line).group(1)
                    if _IMAGE_ID_RE.fullmatch(line)
                    else None
                ),
                timeout_s,
            )
            if (
                expected_image is not None
                and observed_image != expected_image.lower()
            ):
                raise CaptureContractError(
                    f"{role} image mismatch: observed {observed_image}, "
                    f"expected {expected_image.lower()}"
                )
            runtime = self._query(
                role,
                "runtime_id",
                lambda line: (
                    _RUNTIME_ID_RE.fullmatch(line).groups()
                    if _RUNTIME_ID_RE.fullmatch(line)
                    else None
                ),
                timeout_s,
            )
            boot_nonce, uptime_ms, reset_reason = runtime
            observed[role] = {
                "chip_id": chip,
                "version": version,
                "git": git_hash,
                "epoch": int(epoch),
                "env": env,
                "app_elf_sha256": observed_image,
                "boot_nonce": boot_nonce,
                "uptime_ms": int(uptime_ms),
                "reset_reason": int(reset_reason),
            }
        return observed

    def set_leader_ble_stream(self, enabled: bool, timeout_s: float) -> None:
        """Enable exact Remoted counters on the leader and require its ACK."""
        value = "on" if enabled else "off"
        expected = f"BLE_STREAM: {value}"
        self._query(
            "leader",
            f"ble_stream={value}",
            lambda line: line if line == expected else None,
            timeout_s,
        )

    def query_leader_dial_status(self, timeout_s: float) -> dict[str, int]:
        keys = (
            "linked",
            "generation",
            "notify",
            "decoded",
            "enqueued",
            "apply_ok",
            "apply_fail",
            "queue_drops",
            "decode_errors",
            "dial_mode_apply_ok",
            "confirm_write_ok",
            "confirm_write_fail",
            "dial_confirm_write_ok",
            "last_confirm_pm",
            "last_confirm_sm",
        )

        def match_status(line: str):
            match = _DIAL_STATUS_RE.fullmatch(line)
            if match is None:
                return None
            return {
                key: int(value)
                for key, value in zip(keys, match.groups())
            }

        return self._query(
            "leader", "dial_status", match_status, timeout_s
        )

    @staticmethod
    def _strict_status_record(role: str, line: str):
        try:
            parsed = logfmt.parse_log(
                f"host_us=0 {line}\n",
                strict=True,
                expected_role=role,
            )
        except logfmt.LogContractError as error:
            raise CaptureContractError(
                f"{role} :sync_status emitted malformed lifecycle: {error}"
            ) from error
        if len(parsed.records) != 1:
            raise CaptureContractError(
                f"{role} :sync_status emitted unparseable lifecycle: {line}"
            )
        return parsed.records[0]

    def capture_sync_status(self, timeout_s: float) -> dict:
        """Request one fresh, coherent lifecycle snapshot from both roles.

        The firmware response contract is three exact lines per role, in any
        order:

        ``SYNC_STATUS: role=<role> linked=1``
        ``[k1_sync] link up ...``
        ``[k1_sync] negotiated ...``

        Input is cleared immediately before both commands, so lifecycle lines
        buffered before this request cannot certify the run. Every accepted
        response is still written to the continuous session log.
        """
        self.clear_pending_input()
        context_start_line = {
            role: self.writers[role].line_count
            for role in ("leader", "follower")
        }
        command = b":sync_status\n"
        for role in ("leader", "follower"):
            self.streams[role].write(command)
            self.streams[role].flush()

        state = {
            role: {"ack": False, "link_up": None, "negotiated": None}
            for role in ("leader", "follower")
        }
        deadline = self._monotonic_ns() + int(max(0.0, timeout_s) * 1e9)
        while self._monotonic_ns() < deadline:
            received = False
            for role in ("leader", "follower"):
                line = self._read_one(role)
                received = line is not None or received
                if line is None:
                    continue
                if line.startswith("SYNC_STATUS:"):
                    match = _SYNC_STATUS_RE.fullmatch(line)
                    if match is None:
                        raise CaptureContractError(
                            f"{role} :sync_status malformed ACK: {line}"
                        )
                    response_role, linked = match.groups()
                    if response_role != role:
                        raise CaptureContractError(
                            f"{role} :sync_status ACK role={response_role}"
                        )
                    if linked != "1":
                        raise CaptureContractError(
                            f"{role} :sync_status reports linked={linked}"
                        )
                    if state[role]["ack"]:
                        raise CaptureContractError(
                            f"{role} :sync_status duplicate ACK"
                        )
                    state[role]["ack"] = True
                    continue
                if "[k1_sync] link up" in line:
                    record = self._strict_status_record(role, line)
                    if not isinstance(record, logfmt.LinkUp):
                        raise CaptureContractError(
                            f"{role} :sync_status link-up type mismatch"
                        )
                    if state[role]["link_up"] is not None:
                        raise CaptureContractError(
                            f"{role} :sync_status duplicate link-up"
                        )
                    state[role]["link_up"] = record
                    continue
                if "[k1_sync] negotiated" in line:
                    record = self._strict_status_record(role, line)
                    if not isinstance(record, logfmt.Negotiated):
                        raise CaptureContractError(
                            f"{role} :sync_status negotiated type mismatch"
                        )
                    if state[role]["negotiated"] is not None:
                        raise CaptureContractError(
                            f"{role} :sync_status duplicate negotiated"
                        )
                    state[role]["negotiated"] = record

            complete = all(
                value["ack"]
                and value["link_up"] is not None
                and value["negotiated"] is not None
                for value in state.values()
            )
            if complete:
                break
            if not received:
                self._sleep(0.001)

        missing = {
            role: [
                name
                for name, value in role_state.items()
                if value is False or value is None
            ]
            for role, role_state in state.items()
        }
        missing = {role: fields for role, fields in missing.items() if fields}
        if missing:
            raise CaptureContractError(
                f"fresh exact :sync_status response missing: {missing}"
            )

        output = {"context_start_line": context_start_line}
        for role, role_state in state.items():
            link_up = role_state["link_up"]
            negotiated = role_state["negotiated"]
            if (
                negotiated.epoch != link_up.epoch
                or negotiated.mtu != link_up.mtu
            ):
                raise CaptureContractError(
                    f"{role} :sync_status lifecycle is incoherent"
                )
            output[role] = {
                "linked": True,
                "epoch": link_up.epoch,
                "handle": link_up.handle,
                "mtu": link_up.mtu,
                "interval_units": negotiated.interval_units,
                "latency": negotiated.latency,
                "phy_tx": negotiated.phy_tx,
                "phy_rx": negotiated.phy_rx,
            }
        return output


def _evaluate_segment(segment_dir: Path) -> tuple[dict, int]:
    leader_text = (segment_dir / "leader.log").read_text(
        encoding="utf-8", errors="replace"
    )
    follower_text = (segment_dir / "follower.log").read_text(
        encoding="utf-8", errors="replace"
    )
    try:
        verdict = gate_eval.evaluate(
            leader_text, follower_text, strict_proof=True
        )
    except (logfmt.LogContractError, ValueError) as error:
        raise CaptureContractError(
            f"{segment_dir.name}: oracle input contract error: {error}"
        ) from error
    exit_code = gate_eval.STATUS_EXIT[verdict["overall_status"]]
    if exit_code not in (0, 1, 2, 3):
        raise CaptureContractError(
            f"{segment_dir.name}: unknown oracle exit {exit_code}"
        )
    _atomic_text(
        segment_dir / f"verdict_{segment_dir.name}.json",
        gate_eval.to_json(verdict),
    )
    return verdict, exit_code


def _proof_text(
    session_text: str,
    segment_text: str,
    *,
    context_start_line: int = 0,
) -> str:
    """Carry captured connection context into one segment proof.

    Only boundary records before the segment are inherited. Prior stream,
    timing, GPIO and health observations are deliberately excluded, so a later
    fault segment cannot accumulate an earlier segment's measurements.
    """
    segment = logfmt.parse_log(segment_text)
    starts = [
        entry.record.t_host_us
        for entry in segment.entries
        if isinstance(entry.record, logfmt.HostSegment)
        and entry.record.phase == "start"
    ]
    if len(starts) != 1:
        raise CaptureContractError("segment has no unique start marker")
    start_us = starts[0]
    boundary_types = (
        logfmt.Begin,
        logfmt.LinkUp,
        logfmt.LinkDown,
        logfmt.Negotiated,
        logfmt.Reset,
    )
    context: list[str] = []
    for line_index, line in enumerate(session_text.splitlines()):
        if line_index < context_start_line:
            continue
        parsed = logfmt.parse_log(line)
        if len(parsed.entries) != 1:
            continue
        entry = parsed.entries[0]
        if (
            isinstance(entry.record, boundary_types)
            and entry.host_us is not None
            and entry.host_us < start_us
        ):
            context.append(line)
    body = segment_text.rstrip("\n")
    lines = context + ([body] if body else [])
    return "\n".join(lines) + "\n"


def run_segments(
    *,
    leader_port: str,
    follower_port: str,
    out_dir: Path,
    segments: tuple[str, ...],
    duration_s: float,
    ack_timeout_s: float,
    settle_s: float = 10.0,
    baud: int = DEFAULT_BAUD,
    serial_factory: Callable[[str, int], object] = _open_serial,
    identity_expectations: Optional[dict[str, dict[str, str]]] = None,
    leader_ble_stream: bool = False,
    leader_dial_status: bool = False,
) -> list[dict]:
    """Capture F0 plumbing segments without overwriting prior evidence."""
    for segment in segments:
        fault_for_segment(segment)
    out_dir.mkdir(parents=True, exist_ok=False)

    leader_session_path = out_dir / "leader_session.log"
    follower_session_path = out_dir / "follower_session.log"
    results: list[dict] = []
    leader = follower = None
    restoration_error: Optional[Exception] = None
    primary_error: Optional[BaseException] = None

    with leader_session_path.open("x", encoding="utf-8") as leader_session, (
        follower_session_path.open("x", encoding="utf-8")
    ) as follower_session:
        writers = {
            "leader": _RoleWriter(leader_session),
            "follower": _RoleWriter(follower_session),
        }
        try:
            leader = serial_factory(leader_port, baud)
            follower = serial_factory(follower_port, baud)
            capture = DualCapture(
                leader, follower, writers["leader"], writers["follower"]
            )
            if identity_expectations is not None:
                identity = capture.verify_devices(
                    identity_expectations, ack_timeout_s
                )
                _atomic_text(
                    out_dir / "IDENTITY.json",
                    json.dumps(identity, indent=2, sort_keys=True) + "\n",
                )
            sync_status = capture.capture_sync_status(ack_timeout_s)
            _atomic_text(
                out_dir / "SYNC_STATUS.json",
                json.dumps(sync_status, indent=2, sort_keys=True) + "\n",
            )
            if leader_ble_stream:
                capture.set_leader_ble_stream(True, ack_timeout_s)
            capture.pump(settle_s)
            dial_status: dict[str, dict[str, dict[str, int]]] = {}
            for segment in segments:
                baseline = (
                    capture.query_leader_dial_status(ack_timeout_s)
                    if leader_dial_status
                    else None
                )
                segment_dir = out_dir / segment
                segment_dir.mkdir(exist_ok=False)
                with (segment_dir / "leader_segment.log").open(
                    "x", encoding="utf-8"
                ) as leader_segment, (
                    segment_dir / "follower_segment.log"
                ).open("x", encoding="utf-8"
                ) as follower_segment:
                    writers["leader"].segment_file = leader_segment
                    writers["follower"].segment_file = follower_segment
                    capture.clear_pending_input()
                    capture.marker(segment, "start")
                    fault = fault_for_segment(segment)
                    capture.set_fault(fault, ack_timeout_s)
                    capture.pump(duration_s)
                    end_status = (
                        capture.query_leader_dial_status(ack_timeout_s)
                        if leader_dial_status
                        else None
                    )
                    capture.marker(segment, "end")
                    writers["leader"].segment_file = None
                    writers["follower"].segment_file = None
                if baseline is not None and end_status is not None:
                    dial_status[segment] = {
                        "baseline": baseline,
                        "end": end_status,
                    }
                leader_proof = _proof_text(
                    leader_session_path.read_text(
                        encoding="utf-8", errors="replace"
                    ),
                    (segment_dir / "leader_segment.log").read_text(
                        encoding="utf-8", errors="replace"
                    ),
                    context_start_line=sync_status["context_start_line"][
                        "leader"
                    ],
                )
                follower_proof = _proof_text(
                    follower_session_path.read_text(
                        encoding="utf-8", errors="replace"
                    ),
                    (segment_dir / "follower_segment.log").read_text(
                        encoding="utf-8", errors="replace"
                    ),
                    context_start_line=sync_status["context_start_line"][
                        "follower"
                    ],
                )
                _atomic_text(segment_dir / "leader.log", leader_proof)
                _atomic_text(segment_dir / "follower.log", follower_proof)
                verdict, exit_code = _evaluate_segment(segment_dir)
                results.append(
                    {
                        "segment": segment,
                        "fault": fault,
                        "status": verdict["overall_status"],
                        "link_ready": verdict["link_ready"]["status"],
                        "exit_code": exit_code,
                    }
                )
            if leader_dial_status:
                _atomic_text(
                    out_dir / "DIAL_STATUS.json",
                    json.dumps(dial_status, indent=2, sort_keys=True) + "\n",
                )
        except BaseException as error:
            primary_error = error
        finally:
            writers["leader"].segment_file = None
            writers["follower"].segment_file = None
            if follower is not None:
                try:
                    if leader is not None:
                        capture.marker("cleanup", "start")
                    capture.set_fault("off", ack_timeout_s)
                    if leader is not None:
                        capture.marker("cleanup", "end")
                except Exception as error:  # preserve original failure
                    restoration_error = error
            if leader_ble_stream and leader is not None and follower is not None:
                try:
                    capture.set_leader_ble_stream(False, ack_timeout_s)
                except Exception as error:
                    if restoration_error is None:
                        restoration_error = error
            for stream in (leader, follower):
                if stream is not None:
                    try:
                        stream.close()
                    except Exception:
                        pass

    index_lines = [
        "# Dual-sync segmented capture — NOT_GATE0",
        "",
        "F0 host plumbing only. Delay modes are timestamp-fake in current "
        "firmware and this evidence must not be cited as Gate-0 silicon.",
        "",
        "| Segment | Firmware fault | Link Ready | Overall | CLI exit |",
        "|---|---|---|---|---:|",
    ]
    for result in results:
        index_lines.append(
            f"| {result['segment']} | {result['fault']} | "
            f"{result['link_ready']} | {result['status']} | "
            f"{result['exit_code']} |"
        )
    if primary_error is not None:
        index_lines.extend(("", f"Capture error: `{primary_error}`"))
    if restoration_error is not None:
        index_lines.extend(("", f"Restoration error: `{restoration_error}`"))
    _atomic_text(out_dir / "INDEX.md", "\n".join(index_lines) + "\n")

    if primary_error is not None:
        raise primary_error
    if restoration_error is not None:
        raise CaptureContractError(
            f"capture completed but off restoration failed: {restoration_error}"
        )
    return results


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Capture dual-sync F0 plumbing segments (NOT Gate-0)."
    )
    parser.add_argument("--leader-port", required=True)
    parser.add_argument("--follower-port", required=True)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument(
        "--segments", default="off,delay5,delay20,drop10,restored"
    )
    parser.add_argument("--duration-s", type=float, default=60.0)
    parser.add_argument(
        "--settle-s",
        type=float,
        default=10.0,
        help="capture connection context before the first segment",
    )
    parser.add_argument("--ack-timeout-s", type=float, default=3.0)
    parser.add_argument("--baud", type=int, default=DEFAULT_BAUD)
    return parser


def main(argv=None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        segments = parse_segments(args.segments)
        results = run_segments(
            leader_port=args.leader_port,
            follower_port=args.follower_port,
            out_dir=args.out_dir,
            segments=segments,
            duration_s=args.duration_s,
            ack_timeout_s=args.ack_timeout_s,
            settle_s=args.settle_s,
            baud=args.baud,
        )
    except (CaptureContractError, FileExistsError, OSError) as error:
        parser.error(str(error))
    return 0 if all(result["status"] == gate_eval.PASS for result in results) else 2


if __name__ == "__main__":
    raise SystemExit(main())
