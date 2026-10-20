"""Decode and accept K1 emulator replay captures.

Three separate steps, used by every run, comparison and planted negative case:

1. ``decode(uart_text)`` turns UART text into a structured capture. It refuses
   malformed text (duplicate keys, duplicate frames/sidecars, bad hex) but
   makes no judgement about whether the run was the requested one.
2. ``accept(decoded, expect, process)`` is the one acceptance function. It
   compares the decoded capture with the requested scenario and the process
   outcome and returns every reason for rejection.
3. ``native_payload`` / ``deterministic_view`` give the bytes and source
   metadata that repeat-equality and isolation comparisons use. Run ids and
   host wall-clock fields are never part of them.

The native trace boundary is the Lever-2 packed WS2816 wire before submission:
per logical pixel G_hi G_lo R_hi R_lo B_hi B_lo. The UART text is the existing
``rgb16hex`` dump, R16BE G16BE B16BE per pixel, a lossless reorder of it.
"""

from __future__ import annotations

import hashlib
import re
import zlib
from dataclasses import dataclass, field

PX = 160
EDGE_BYTES = PX * 6
HEX_PER_EDGE = PX * 12


class CaptureError(ValueError):
    """The UART text cannot be decoded as one capture."""


def parse_fields(text: str, where: str) -> dict[str, str]:
    """key=value tokens; a repeated key is an error, never an overwrite."""
    out: dict[str, str] = {}
    for token in text.split():
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        if key in out:
            raise CaptureError(f"{where}: duplicate key {key}")
        out[key] = value
    return out


def dump_hex_to_wire(hex_text: str) -> bytes:
    """rgb16hex (R16 G16 B16 big-endian) -> native wire (G16 R16 B16)."""
    if len(hex_text) != HEX_PER_EDGE:
        raise CaptureError(f"edge hex length {len(hex_text)} != {HEX_PER_EDGE}")
    try:
        raw = bytes.fromhex(hex_text)
    except ValueError as exc:
        raise CaptureError(f"edge hex is not hexadecimal: {exc}") from None
    out = bytearray(len(raw))
    for i in range(0, len(raw), 6):
        out[i:i + 2] = raw[i + 2:i + 4]      # G
        out[i + 2:i + 4] = raw[i:i + 2]      # R
        out[i + 4:i + 6] = raw[i + 4:i + 6]  # B
    return bytes(out)


def wire_to_rgb16(wire: bytes) -> list[tuple[int, int, int]]:
    """Native wire bytes -> per-pixel (r16, g16, b16)."""
    px = []
    for i in range(0, len(wire), 6):
        g = (wire[i] << 8) | wire[i + 1]
        r = (wire[i + 2] << 8) | wire[i + 3]
        b = (wire[i + 4] << 8) | wire[i + 5]
        px.append((r, g, b))
    return px


@dataclass
class Frame:
    index: int
    ms: int
    mode: int
    A: bytes
    B: bytes


@dataclass
class Sidecar:
    index: int
    generation: int
    admitted: int
    processed: int
    app_us: int
    limit_scale: int
    power_mw: int


@dataclass
class Meaning:
    """Audio meaning of one generation: producer view (p_*) and render-thread view (c_*)."""
    index: int
    p_generation: int
    p_onset_seq: int
    p_beat_seq: int
    p_onset_strength: str
    p_bpm: str
    p_phase: str
    p_confidence: str
    p_locked: int
    p_beat_tick: int
    c_generation: int
    c_onset_seq: int
    c_beat_seq: int
    c_onset_strength: str
    c_bpm: str
    c_phase: str
    c_confidence: str
    c_locked: int
    c_beat_tick: int

    def producer(self) -> tuple:
        return (self.p_generation, self.p_onset_seq, self.p_beat_seq, self.p_onset_strength, self.p_bpm,
                self.p_phase, self.p_confidence, self.p_locked, self.p_beat_tick)

    def consumed(self) -> tuple:
        return (self.c_generation, self.c_onset_seq, self.c_beat_seq, self.c_onset_strength, self.c_bpm,
                self.c_phase, self.c_confidence, self.c_locked, self.c_beat_tick)


@dataclass
class Capture:
    header: dict[str, str]
    frames: list[Frame]
    sidecars: dict[int, Sidecar]
    armed: list[dict[str, str]]
    ends: list[dict[str, str]]
    commands: list[dict[str, str]]
    command_results: list[dict[str, str]]
    show_states: list[dict[str, str]]
    saves: list[dict[str, str]]
    rejects: list[str]
    power_limits: list[dict[str, str]]
    epochs: list[dict[str, str]]
    meanings: dict[int, Meaning]
    novelty: dict[int, tuple]
    render_state: dict[int, tuple]
    begin_count: int
    end_marker_count: int
    computed_crc32: int
    panics: list[str] = field(default_factory=list)


def decode(uart: str) -> Capture:
    begins = re.findall(r"\[RTRACE-BEGIN ([^\]]*)\]", uart)
    if not begins:
        raise CaptureError("no RTRACE-BEGIN")
    header = parse_fields(begins[0], "RTRACE-BEGIN")
    frames: list[Frame] = []
    sidecars: dict[int, Sidecar] = {}
    armed, ends, commands, results, states, saves, limits, epochs = [], [], [], [], [], [], [], []
    rejects: list[str] = []
    panics: list[str] = []
    seen_frames: set[int] = set()
    meanings: dict[int, Meaning] = {}
    novelty: dict[int, tuple] = {}
    render_state: dict[int, tuple] = {}
    for line in uart.splitlines():
        line = line.rstrip("\r")
        if line.startswith("F,"):
            parts = line.split(",")
            if len(parts) != 6:
                raise CaptureError(f"frame line has {len(parts)} fields, expected 6 (two edges)")
            try:
                index, ms, mode = int(parts[1]), int(parts[2]), int(parts[3])
            except ValueError:
                raise CaptureError(f"frame line has a non-integer field: {line[:60]}") from None
            if index in seen_frames:
                raise CaptureError(f"duplicate frame {index}")
            seen_frames.add(index)
            frames.append(Frame(index, ms, mode, dump_hex_to_wire(parts[4]), dump_hex_to_wire(parts[5])))
        elif line.startswith("S,"):
            parts = line.split(",")
            if len(parts) != 8:
                raise CaptureError(f"sidecar line has {len(parts)} fields, expected 8")
            try:
                values = [int(p) for p in parts[1:]]
            except ValueError:
                raise CaptureError(f"sidecar has a non-integer field: {line[:60]}") from None
            if values[0] in sidecars:
                raise CaptureError(f"duplicate sidecar {values[0]}")
            sidecars[values[0]] = Sidecar(*values)
        elif line.startswith("R,"):
            parts = line.split(",")
            if len(parts) != 9:
                raise CaptureError(f"render-state line has {len(parts)} fields, expected 9")
            if int(parts[1]) in render_state:
                raise CaptureError(f"duplicate render-state line {parts[1]}")
            render_state[int(parts[1])] = tuple(parts[2:])
        elif line.startswith("N,"):
            parts = line.split(",")
            if len(parts) != 6:
                raise CaptureError(f"novelty line has {len(parts)} fields, expected 6")
            gen = int(parts[1])
            if gen in novelty:
                raise CaptureError(f"duplicate novelty line {gen}")
            novelty[gen] = (float(parts[2]), float(parts[3]), int(parts[4]), parts[5])
        elif line.startswith("V,"):
            parts = line.split(",")
            if len(parts) != 20:
                raise CaptureError(f"meaning line has {len(parts)} fields, expected 20")
            try:
                ints = {1, 2, 3, 4, 9, 10, 11, 12, 13, 18, 19}
                vals = [int(v) if i in ints else v for i, v in enumerate(parts) if i > 0]
            except ValueError:
                raise CaptureError(f"meaning line has a non-integer field: {line[:60]}") from None
            if vals[0] in meanings:
                raise CaptureError(f"duplicate meaning line {vals[0]}")
            meanings[vals[0]] = Meaning(*vals)
        elif line.startswith("EMU_FIXTURE_ARMED "):
            armed.append(parse_fields(line[len("EMU_FIXTURE_ARMED "):], "EMU_FIXTURE_ARMED"))
        elif line.startswith("EMU_END "):
            ends.append(parse_fields(line[len("EMU_END "):], "EMU_END"))
        elif line.startswith("EMU_CMD_DONE "):
            results.append(parse_fields(line[len("EMU_CMD_DONE "):], "EMU_CMD_DONE"))
        elif line.startswith("EMU_CMD "):
            head, _, text = line[len("EMU_CMD "):].partition(" text=")
            entry = parse_fields(head, "EMU_CMD")
            entry["text"] = text
            commands.append(entry)
        elif line.startswith("EMU_SS "):
            states.append(parse_fields(line[len("EMU_SS "):], "EMU_SS"))
        elif line.startswith("EMU_SAVE "):
            saves.append(parse_fields(line[len("EMU_SAVE "):], "EMU_SAVE"))
        elif line.startswith("EMU_REJECT "):
            rejects.append(line[len("EMU_REJECT "):].strip())
        elif line.startswith("EMU_EPOCH "):
            epochs.append(parse_fields(line[len("EMU_EPOCH "):], "EMU_EPOCH"))
        elif line.startswith("EMU_POWER_LIMIT "):
            limits.append(parse_fields(line[len("EMU_POWER_LIMIT "):], "EMU_POWER_LIMIT"))
        elif "Guru Meditation" in line or "abort() was called" in line or "Backtrace:" in line:
            panics.append(line.strip()[:200])
    crc = 0
    for frame in sorted(frames, key=lambda f: f.index):
        crc = zlib.crc32(frame.A, crc)
        crc = zlib.crc32(frame.B, crc)
    return Capture(
        header=header, frames=frames, sidecars=sidecars, armed=armed, ends=ends,
        commands=commands, command_results=results, show_states=states, saves=saves,
        rejects=rejects, power_limits=limits, epochs=epochs, meanings=meanings, novelty=novelty, render_state=render_state, begin_count=len(begins),
        end_marker_count=uart.count("[RTRACE-END]"), computed_crc32=crc & 0xFFFFFFFF,
        panics=panics,
    )


@dataclass
class Expect:
    """What the requested scenario case says the run must show."""
    run_id: str
    payload_crc32: int
    real_samples: int
    pad_samples: int
    rate_hz: int
    hop_samples: int
    capture_start_hop: int
    capture_end_hop: int        # exclusive, already clipped to total_hops
    capture_every: int
    recovery: bool
    commands: list[dict]        # [{"hop": int, "text": str, "expect": "applied"|"rejected"}]
    end_reason: str = "eof"
    saves: int | None = None     # exact EMU_SAVE count when declared
    epoch_policy: str = "boot_monotonic"
    declared_epoch_us: int | None = None

    @property
    def total_hops(self) -> int:
        return -(-self.real_samples // self.hop_samples) + self.pad_samples // self.hop_samples

    def captured_hops(self) -> list[int]:
        end = min(self.capture_end_hop, self.total_hops)
        return list(range(self.capture_start_hop, end, self.capture_every))


@dataclass
class Process:
    exit_code: int
    exit_on_found: bool


def _int(fields: dict[str, str], key: str, reasons: list[str], where: str) -> int | None:
    if key not in fields:
        reasons.append(f"{where}: missing {key}")
        return None
    try:
        return int(fields[key], 0) if fields[key].startswith("0x") else int(fields[key])
    except ValueError:
        reasons.append(f"{where}: {key}={fields[key]!r} is not an integer")
        return None


def accept(cap: Capture | None, expect: Expect, process: Process, decode_error: str | None = None) -> list[str]:
    """Return every reason the run is not the requested complete capture. Empty = accepted."""
    reasons: list[str] = []
    if process.exit_code != 0:
        reasons.append(f"process exit code {process.exit_code}")
    if not process.exit_on_found:
        reasons.append("emulator did not report the exit-on terminal string")
    if decode_error is not None:
        reasons.append(f"decode: {decode_error}")
    if cap is None:
        return reasons
    if cap.panics:
        reasons.append(f"firmware panic text: {cap.panics[0]}")
    # Header geometry and precision.
    h = cap.header
    if cap.begin_count != 1:
        reasons.append(f"RTRACE-BEGIN count {cap.begin_count} != 1")
    if cap.end_marker_count != 1:
        reasons.append(f"RTRACE-END count {cap.end_marker_count} != 1")
    empty_partial = expect.end_reason != "eof" and h.get("frames") == "0" and not cap.frames
    for key, want in (("px", str(PX)), ("bpp", "16"), ("edges", "2"), ("fmt", "rgb16hex"), ("every", "1")):
        if empty_partial:
            break  # a failure before the first capture dumps an empty trace
        if h.get(key) != want:
            reasons.append(f"header {key}={h.get(key)!r} != {want}")
    header_frames = _int(h, "frames", reasons, "header")
    try:
        header_crc = int(h.get("crc32", "x"), 16)
    except ValueError:
        header_crc = None
        reasons.append(f"header crc32={h.get('crc32')!r} is not hexadecimal")
    if header_crc is not None and header_crc != cap.computed_crc32:
        reasons.append(f"native crc {cap.computed_crc32:08x} != header {header_crc:08x}")
    hops = expect.captured_hops()
    complete = expect.end_reason == "eof"
    if header_frames is not None and header_frames != len(cap.frames):
        reasons.append(f"header frames={header_frames} but {len(cap.frames)} frame lines")
    if complete and len(cap.frames) != len(hops):
        reasons.append(f"frames={len(cap.frames)} != expected {len(hops)} from the declared window and cadence")
    if [f.index for f in cap.frames] != list(range(len(cap.frames))):
        reasons.append("frame indices are not ordered 0..n-1")
    missing = [f.index for f in cap.frames if f.index not in cap.sidecars]
    extra = sorted(set(cap.sidecars) - {f.index for f in cap.frames})
    if missing:
        reasons.append(f"frames without a sidecar: {missing[:5]}")
    no_meaning = [f.index for f in cap.frames if f.index not in cap.meanings]
    if no_meaning:
        reasons.append(f"frames without a meaning line: {no_meaning[:5]}")
    for f in cap.frames:
        m, s = cap.meanings.get(f.index), cap.sidecars.get(f.index)
        if m and s and (m.p_generation != s.generation or m.c_generation != s.generation):
            reasons.append(f"frame {f.index} meaning generations P{m.p_generation}/C{m.c_generation} != {s.generation}")
            break
    if extra:
        reasons.append(f"sidecars without a frame: {extra[:5]}")
    for f in cap.frames:
        if len(f.A) != EDGE_BYTES or len(f.B) != EDGE_BYTES:
            reasons.append(f"frame {f.index} edge length A={len(f.A)} B={len(f.B)}")
            break
    # Epoch hand-off into the processed-sample clock.
    epoch_us = None
    if len(cap.epochs) != 1:
        reasons.append(f"EMU_EPOCH count {len(cap.epochs)} != 1")
    else:
        ep = cap.epochs[0]
        epoch_us = _int(ep, "epoch_us", reasons, "epoch")
        boot_us = _int(ep, "boot_us", reasons, "epoch")
        if ep.get("policy") != expect.epoch_policy:
            reasons.append(f"epoch policy={ep.get('policy')!r} != {expect.epoch_policy!r}")
        elif expect.epoch_policy == "zero" and epoch_us != 0:
            reasons.append(f"zero epoch reported epoch_us={epoch_us}")
        elif expect.epoch_policy == "declared" and epoch_us != expect.declared_epoch_us:
            reasons.append(f"declared epoch {expect.declared_epoch_us} but firmware used {epoch_us}")
        elif expect.epoch_policy == "boot_monotonic" and epoch_us != boot_us:
            reasons.append(f"boot epoch {epoch_us} != boot clock {boot_us}")
    # Source/admitted/processed progression for each captured hop. Hop-end time:
    # app_us = epoch + processed * 1e6 / rate (the trace field is 32-bit).
    if not complete:
        hops = [ (cap.sidecars[f.index].processed // expect.hop_samples - 1) if f.index in cap.sidecars else -1
                 for f in cap.frames ]
    for f, hop in zip(cap.frames, hops):
        side = cap.sidecars.get(f.index)
        if side is None:
            continue
        processed = (hop + 1) * expect.hop_samples
        admitted = min(processed, expect.real_samples)
        app_us = ((epoch_us or 0) + processed * 1_000_000 // expect.rate_hz) & 0xFFFFFFFF
        got = (side.generation, side.processed, side.admitted, side.app_us)
        want = (hop + 1, processed, admitted, app_us)
        if got != want:
            reasons.append(
                f"frame {f.index} (hop {hop}) generation/processed/admitted/app_us {got} != {want}")
            break
    # Run identity and the scenario the firmware actually read.
    if len(cap.armed) != 1:
        reasons.append(f"EMU_FIXTURE_ARMED count {len(cap.armed)} != 1")
    else:
        a = cap.armed[0]
        checks = {
            "run": expect.run_id, "source": "blob", "valid": "1",
            "rate": str(expect.rate_hz), "hop": str(expect.hop_samples),
            "real_samples": str(expect.real_samples), "pad_samples": str(expect.pad_samples),
            "total_hops": str(expect.total_hops),
            "capture": f"{expect.capture_start_hop}..{expect.capture_end_hop}",
            "every": str(expect.capture_every), "recovery": "1" if expect.recovery else "0",
            "commands": str(len(expect.commands)), "payload_crc32": f"{expect.payload_crc32:08x}",
            "clock": "hop_end_us", "mode": "lockstep", "epoch": expect.epoch_policy,
        }
        for key, want in checks.items():
            if a.get(key) != want:
                reasons.append(f"armed {key}={a.get(key)!r} != {want!r}")
        if not str(a.get("rng", "")).startswith("xorshift32:"):
            reasons.append(f"armed rng={a.get('rng')!r}: product randomness is not on the declared seeded generator")
    if not cap.show_states or cap.show_states[0].get("when") != "boot":
        reasons.append("no boot show-state readback before the first hop")
    # Terminal event and counters.
    if len(cap.ends) != 1:
        reasons.append(f"EMU_END count {len(cap.ends)} != 1")
    else:
        e = cap.ends[0]
        n = expect.total_hops
        want_end = {
            "reason": expect.end_reason, "run": expect.run_id,
            "admitted": str(expect.real_samples), "processed": str(n * expect.hop_samples),
            "staged_hops": str(n), "total_hops": str(n), "published": str(n),
            "last_generation": str(n), "consumed": str(n), "shown": str(n), "last_shown": str(n),
            "captured": str(len(hops)), "commands": str(len(expect.commands)),
            "rejects": str(sum(1 for c in expect.commands if c.get("expect") == "rejected")),
            "unstaged_admits": "0", "publications_without_hop": "0",
        }
        if expect.end_reason != "eof":
            # A failure end must still report where everything stood.
            want_end = {"reason": expect.end_reason, "run": expect.run_id, "captured": str(len(cap.frames))}
            for key in ("admitted", "processed", "published", "consumed", "shown", "last_shown"):
                if key not in e:
                    reasons.append(f"failure end does not report {key}")
        if expect.saves is not None:
            want_end["saves"] = str(expect.saves)
        for key, want in want_end.items():
            if e.get(key) != want:
                reasons.append(f"end {key}={e.get(key)!r} != {want!r}")
    # Scheduled production commands: requested order, position and result.
    got_cmds = [(int(c.get("hop", -1)), c.get("text", "")) for c in cap.commands]
    want_cmds = [(int(c["hop"]), c["text"]) for c in expect.commands]
    if got_cmds != want_cmds:
        reasons.append(f"commands executed {got_cmds[:4]} != requested {want_cmds[:4]}")
    elif len(cap.command_results) != len(expect.commands):
        reasons.append("a command has no EMU_CMD_DONE result")
    else:
        for res, req in zip(cap.command_results, expect.commands):
            rejected = res.get("rejected") == "1"
            if rejected != (req.get("expect") == "rejected"):
                reasons.append(f"command {req['text']!r} rejected={rejected}, expected {req.get('expect', 'applied')}")
    if expect.recovery and (cap.commands or cap.saves):
        reasons.append(f"recovery run issued commands={len(cap.commands)} saves={len(cap.saves)}")
    return reasons


def native_payload(cap: Capture) -> list[tuple[bytes, bytes]]:
    return [(f.A, f.B) for f in cap.frames]


def deterministic_view(cap: Capture) -> list[tuple]:
    """Payload plus source/generation metadata; excludes run id and wall clock."""
    out = []
    for f in cap.frames:
        s = cap.sidecars.get(f.index)
        meta = None if s is None else (s.generation, s.admitted, s.processed, s.app_us, s.limit_scale, s.power_mw)
        out.append((f.index, f.mode, f.A, f.B, meta))
    return out


def payload_sha256(cap: Capture) -> str:
    h = hashlib.sha256()
    for a, b in native_payload(cap):
        h.update(a)
        h.update(b)
    return h.hexdigest()


def frame_hop(cap: Capture, frame: Frame, hop_samples: int) -> int | None:
    s = cap.sidecars.get(frame.index)
    return None if s is None else s.processed // hop_samples - 1
