#!/usr/bin/env python3
"""show_player — prepared Prim8 (PRSM) stream + original audio from ONE process (Lane C-emu C5).

Scheduling is copied from PRISM.studio src/playback.js (read-only source): every frame has an
absolute target on one monotonic clock, target = wall_start + (t_us - start_t_us); the sender
sleeps until shortly before the target and spins the remainder (playback.js uses setTimeout
with the same drift-corrected target; spinning only tightens the tail). Differences from
playback.js, deliberate and stated:
  * seq comes from the frozen stream file (seq == global tick index), so a start offset or a
    seek is a seq jump the device sees as a new epoch (ACQUIRE -> AUTHORED). playback.js resets
    seq to 0 on play() and keeps counting through seek().
  * no K1CT PARAM_SET frames: the FE firmware has no K1CT parser and its receive loop routes
    every byte outside an aligned PRSM frame to hotkeys ('K', '1', 'T' are hotkeys).
  * playback.js's comment about a 250 ms device freshness is stale: FE firmware uses 50 ms
    (audio/k1_authored_source.h:16).

Safety (hard): never changes system volume; before audio starts it refuses to run if any
afplay is playing and stops only a previous show_player it started itself (pid file); audio
and serial are always closed in finally/atexit/signal handlers. USB-CDC ignores baud; the
--baud value is passed to pyserial only because the API requires one.

Wire format (lead decision, 9 Nov; lane-b prim8_stream): every frame is ONE 64-byte write
(30 NUL guard + 34-byte frame); RESYNC_PREAMBLE (64 B, one write) precedes the first frame of the
session, of every seek epoch and of every resume after a watchdog pause. A signal only sets a flag:
the in-flight 64-byte write always completes; no frame is ever abandoned part-way.
Device-output watchdog (lane-b/B-P1-contract.md table): a reader thread on the same port logs every
device line (<log>.device.jsonl, monotonic us). NOISE_CAL armed / not armed (also in the first,
pre-boundary line) -> isolation FAILED: no writes for 5.5 s, then the session ENDS, exit 5 (review
fix 10 Nov: never resume the same stream); NOISE_CAL queued -> stop, exit 4 (CRITICAL); any other
listed or unexpected line -> stop, exit 2. It never sends Y, N or ':'.
Pacing: audio (default when audio plays) follows the output stream's DAC position; wall = playback.js.

EXIT CODES: 0 completed | 1 refused before start (pre-flight audit failed, asset/stream sha mismatch,
other playback running, bad arguments) | 2 stopped (watchdog stop line, unexpected device line,
signal, serial error) | 3 (retired 10 Nov: no automatic resume any more) | 4 CRITICAL: device
reported "NOISE_CAL: queued" (calibration during music) - recalibrate only under confirmed silence |
5 isolation failure: "NOISE_CAL: armed / not armed" seen; session stopped after a 5.5 s write hold.

Pre-flight: whenever frames are produced, the exact bytes to be sent (after any --rejected
transform) are written to <log>.sent.prsm and audited with lane-b/audit_prsm_bytes.py --guard 30
(plus --allow-rejected-frames with --rejected); the player refuses to start unless it exits 0.
Port open: the reader discards everything before the first newline it sees (the tail of a line
the device began before the port opened) and only then arms the watchdog; no byte is sent before
that boundary (or --boundary-timeout-s). The bench build prints "[AP] ..." at 1 Hz: pass
--allow-line "[AP]".

Modes:  --audio-only   audio with the same start/pacing/header logging; no frames, no port
        --rejected hz0|ver2  stream the v2 frames with byte 5 = 0 (hz0) or byte 4 = 2 (ver2)
        --start-delay-s N    wait N s after pre-flight and port open before audio/frames start
        --dry-run      no audio, no serial: scheduler + log only
        --no-audio     frames to --port, no audio
        (default)      audio (sounddevice/CoreAudio) + frames to --port
Log: JSON lines, one per frame: idx, seq, t_us, sched_us, send_us, done_us, err_us
     (all times monotonic microseconds from the play epoch), plus header/footer records with
     the audio-start timestamp and OS-reported output latency.
"""
from __future__ import annotations

import argparse
import atexit
import hashlib
import json
import os
import signal
import struct
import subprocess
import sys
import threading
import time
from pathlib import Path

FRAME_LEN = 34
HERE = Path(__file__).resolve().parent
PIDFILE = HERE / ".show_player.pid"
SPIN_NS = 0                  # bench fix 9 Nov: no spin; a Python spin holds the GIL the audio callback needs


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_stream(path: Path, sidecar: Path):
    data = path.read_bytes()
    side = json.loads(sidecar.read_text())
    if len(data) % FRAME_LEN:
        raise SystemExit("stream has a trailing partial frame")
    if hashlib.sha256(data).hexdigest() != side["stream_sha256"]:
        raise SystemExit("stream sha256 differs from its sidecar")
    frames = []
    for k in range(0, len(data), FRAME_LEN):
        b = data[k:k + FRAME_LEN]
        magic, ver, hz, seq, t_us = struct.unpack_from("<4sBBIQ", b)
        frames.append((t_us, seq, b))
    return frames, side


def raise_thread_qos() -> int:
    """macOS: run the sending thread at QOS_CLASS_USER_INTERACTIVE (0x21) to limit timer coalescing."""
    try:
        import ctypes
        lib = ctypes.CDLL("/usr/lib/libSystem.dylib")
        return lib.pthread_set_qos_class_self_np(0x21, 0)
    except Exception:
        return -1


def other_playback() -> list[str]:
    out = subprocess.run(["pgrep", "-lx", "afplay"], capture_output=True, text=True).stdout.strip()
    return [l for l in out.splitlines() if l]


def stop_previous_player() -> str | None:
    if not PIDFILE.exists():
        return None
    try:
        pid = int(PIDFILE.read_text().strip())
    except ValueError:
        PIDFILE.unlink(missing_ok=True)
        return None
    cmd = subprocess.run(["ps", "-p", str(pid), "-o", "command="], capture_output=True, text=True).stdout
    if "show_player.py" in cmd and pid != os.getpid():
        os.kill(pid, signal.SIGTERM)
        PIDFILE.unlink(missing_ok=True)
        return f"stopped previous show_player pid {pid}"
    PIDFILE.unlink(missing_ok=True)
    return None


class Audio:
    """Original recording through CoreAudio at the CURRENT system volume (never changed)."""

    def __init__(self, asset: Path, rate: int, start_s: float, silent: bool = False, gain_db: float = 0.0):
        import numpy as np
        import sounddevice as sd
        self.sd, self.np = sd, np
        if silent:
            self.pcm = np.zeros((int(rate * 200), 2), dtype=np.float32)
        else:
            raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(asset), "-map", "0:a:0",
                                  "-f", "f32le", "-ac", "2", "-ar", str(rate), "-"],
                                 check=True, capture_output=True).stdout
            self.pcm = np.frombuffer(raw, dtype="<f4").reshape(-1, 2)
            # 10 Nov 2026 (lead): digital attenuation of the file data only, for the volume-dependence
            # test. Never louder than the recording (gain_db <= 0); system volume is never touched.
            if gain_db < 0.0:
                self.pcm = (self.pcm * np.float32(10.0 ** (gain_db / 20.0))).astype(np.float32)
        self.rate = rate
        self.pos = int(round(start_s * rate))
        self.first_dac = None          # stream time of the first sample's DAC output
        self.first_cb_wall_ns = None
        self.dac_samples: list[tuple[int, float, int]] = []
        self.underflows = 0
        self.map = None
        # Bench fix (lead, 9 Nov 21:40): 64-frame "low" buffers on the Bluetooth output were starved
        # by the GIL (pacing spin + camera encoder) and the Captain heard stutter (M0 log: 3200-frame
        # spans took up to 112 ms instead of 73 ms). 4096-frame buffers (~93 ms) give the callback
        # >18x the 5 ms GIL switch interval; the audio clock still comes from outputBufferDacTime.
        self.stream = sd.OutputStream(samplerate=rate, channels=2, dtype="float32", callback=self._cb,
                                      blocksize=4096, latency="high")

    def _cb(self, out, frames, tinfo, status):
        now = time.monotonic_ns()
        if status.output_underflow:
            self.underflows += 1
        chunk = self.pcm[self.pos:self.pos + frames]
        out[:len(chunk)] = chunk
        out[len(chunk):] = 0
        if self.first_dac is None:
            self.first_dac = tinfo.outputBufferDacTime
            self.first_cb_wall_ns = now
            self.first_cb_stream_time = tinfo.currentTime
        # Audio clock: the first sample of this buffer (content time pos/rate) reaches the DAC
        # at monotonic now + (outputBufferDacTime - currentTime). Published as one tuple.
        self.map = (now + int((tinfo.outputBufferDacTime - tinfo.currentTime) * 1e9), self.pos)
        if len(self.dac_samples) < 200000:
            self.dac_samples.append((self.pos, tinfo.outputBufferDacTime - tinfo.currentTime, now))
        self.pos += frames

    def seek(self, s: float):
        # Review fix 10 Nov: discard audio already queued in PortAudio so the heard audio jumps
        # with the stream (abort drops pending buffers; restart maps the new position). Audio held
        # inside the Bluetooth device itself (~0.16-0.18 s reported) is outside PortAudio's control.
        try:
            self.stream.abort()
        except Exception:
            pass
        self.pos = int(round(s * self.rate))
        self.map = None
        self.stream.start()

    def target_ns(self, t_us: int):
        """Monotonic time at which content time t_us is at the DAC (latest callback mapping)."""
        m = self.map
        if m is None:
            return None
        return m[0] + (t_us * self.rate - m[1] * 1_000_000) * 1000 // self.rate

    def start(self):
        self.stream.start()

    def close(self):
        try:
            self.stream.stop()
            self.stream.close()
        except Exception:
            pass


# Lane B watchdog table (lane-b/B-P1-contract.md, "Host-side device-output watchdog"). Prefix match.
# reaction: pause = stop writes >= 5.5 s then resume with RESYNC_PREAMBLE + new epoch;
#           critical = stop the show (exit 4); stop = stop the show (exit 2).
WATCHDOG = [
    ("NOISE_CAL: queued", "critical"),
    # Review fix 10 Nov: calibration activity means stream isolation FAILED. Stop and investigate;
    # never resume the same stream. The player holds all writes >= 5.5 s before exiting (exit 5).
    ("NOISE_CAL: armed", "isolation"),
    ("NOISE_CAL: not armed", "isolation"),
    ("SHOW_STATE_SAVED", "stop"),
    ("SLOT ", "stop"),
    ("QUEUE: ", "stop"), ("COMMIT", "stop"), ("QUEUE MODE", "stop"),
    ("HOTKEY ", "stop"),
    ("CONFIG.SQUARE_ITER: ", "stop"), ("CONFIG.SENSITIVITY: ", "stop"),
    ("PALETTE_MODE: ", "stop"), ("SECONDARY_PALETTE_MODE: ", "stop"),
    ("SECONDARY_CONTROL: ", "stop"),
    ("EDGE_", "stop"),
    ("VP_WAVEFORM_SHIFT_RATE: ", "stop"), ("VP_BLOOM_SHIFT_SCALE: ", "stop"), ("VP_BLOOM_ALPHA: ", "stop"),
    ("AP_STREAM: ", "stop"), ("VP_STREAM: ", "stop"), ("STREAM_AGC_DEBUG: ", "stop"), ("STREAMS: ", "stop"),
    ("K1 HOTKEYS", "stop"), ("K1 HOTKEY STATUS", "stop"),
    ("Bad command: ", "stop"),
]
PAUSE_NS = 5_500_000_000
EXIT_OK, EXIT_STOPPED, EXIT_RESUMED_AFTER_INCIDENT, EXIT_CRITICAL = 0, 2, 3, 4
EXIT_ISOLATION = 5  # NOISE_CAL armed / not armed seen: isolation failure, session stopped


def classify(line: str, allow: list[str]) -> str | None:
    if not line.strip():
        return None
    for pre, kind in WATCHDOG:
        if line.startswith(pre):
            return kind
    if any(line.startswith(a) for a in allow):
        return None
    return "stop"          # any other unexpected line during the show


class DeviceReader(threading.Thread):
    """Reads the K1's text output on the same port while frames stream; logs and classifies lines."""

    def __init__(self, ser, t0_ns: int, path: Path, allow: list[str]):
        super().__init__(daemon=True)
        self.ser, self.t0, self.allow = ser, t0_ns, allow
        self.fh = path.open("w")
        self.incidents: list[dict] = []
        self.pending = None            # first unhandled incident
        self.last_seq = None
        self.halt = threading.Event()
        self.armed = threading.Event()     # set at the first newline after open
        self.discarded = None
        self.buf = b""

    def run(self):
        while not self.halt.is_set():
            try:
                data = self.ser.read(256)
            except Exception as exc:          # port gone: treat as a stop incident
                self._incident(f"<serial read error {exc!r}>", "stop")
                return
            if not data:
                continue
            self.buf += data
            while b"\n" in self.buf:
                raw, self.buf = self.buf.split(b"\n", 1)
                line = raw.rstrip(b"\r").decode("utf-8", "replace")
                if not self.armed.is_set():
                    # Tail of a line the device began before the port opened: log it, never classify it.
                    self.discarded = line
                    self.fh.write(json.dumps({"t_us": (time.monotonic_ns() - self.t0) // 1000, "line": line,
                                              "watchdog": None, "discarded_partial_before_boundary": True}) + "\n")
                    self.fh.flush()
                    self.armed.set()
                    # Review fix 10 Nov: a calibration reply in that first line still counts —
                    # a calibration armed just before this session must stop it (substring match,
                    # because the line may be a tail).
                    if "NOISE_CAL" in line:
                        self._incident(line, "critical" if "queued" in line else "isolation")
                    continue
                now = time.monotonic_ns()
                kind = classify(line, self.allow)
                self.fh.write(json.dumps({"t_us": (now - self.t0) // 1000, "line": line, "watchdog": kind,
                                          "last_seq_sent": self.last_seq}) + "\n")
                self.fh.flush()
                if kind:
                    self._incident(line, kind)

    def _incident(self, line, kind):
        inc = {"t_us": (time.monotonic_ns() - self.t0) // 1000, "line": line, "kind": kind,
               "last_seq_sent": self.last_seq}
        self.incidents.append(inc)
        if self.pending is None or kind == "critical":
            self.pending = inc


def main() -> int:
    import threading as _t  # noqa: F401  (kept explicit for readers)
    sys.path.insert(0, str(HERE.parent.parent / "lane-b"))
    import prim8_stream as ps
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--stream", required=True)
    ap.add_argument("--sidecar")
    ap.add_argument("--asset", help="original recording; sha256 must equal the sidecar asset.sha256")
    ap.add_argument("--port", help="serial device path (USB-CDC ignores baud)")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--start-s", type=float, help="original-recording start time (default: stream start)")
    ap.add_argument("--stop-after-s", type=float, help="stop sending after this many seconds of play")
    ap.add_argument("--seek", action="append", default=[],
                    help="AT_S:TO_S in play-elapsed seconds -> original seconds (new epoch, seq jump)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-audio", action="store_true")
    ap.add_argument("--silent-audio", action="store_true", help="play an all-zero stream (clock probe only)")
    ap.add_argument("--log", required=True)
    ap.add_argument("--pacing", choices=("audio", "wall"), default=None,
                    help="audio (default when audio plays): follow the output stream's DAC position; "
                         "wall: playback.js drift-corrected monotonic schedule")
    ap.add_argument("--audio-only", action="store_true",
                    help="play the passage with identical audio start/pacing/logging; send no frames, open no port")
    ap.add_argument("--rejected", choices=("hz0", "ver2"),
                    help="send rejected-input frames: hz0 = byte 5 set to 0, ver2 = byte 4 set to 2")
    ap.add_argument("--gain-db", type=float, default=0.0,
                    help="digital attenuation of the recording (<= 0 dB only; system volume never touched)")
    ap.add_argument("--start-delay-s", type=float, default=0.0,
                    help="seconds to wait after pre-flight/port open before audio and frames start")
    ap.add_argument("--boundary-timeout-s", type=float, default=3.0,
                    help="max wait for the first device newline after open before sending anything")
    ap.add_argument("--allow-line", action="append", default=[],
                    help="device-output line prefix known to be benign during a show (default: none)")
    args = ap.parse_args()

    stream = Path(args.stream)
    frames, side = load_stream(stream, Path(args.sidecar or str(stream) + ".json"))
    asset_ok = None
    if args.asset:
        got = sha256_file(Path(args.asset))
        asset_ok = got == side["asset"]["sha256"]
        if not asset_ok:
            raise SystemExit(f"asset sha256 {got} != sidecar {side['asset']['sha256']}; refusing to play")
    elif not (args.dry_run or args.no_audio):
        raise SystemExit("--asset is required when audio plays")
    if args.audio_only and (args.dry_run or args.no_audio or args.rejected):
        raise SystemExit("--audio-only excludes --dry-run, --no-audio and --rejected")
    if args.audio_only and not args.asset:
        raise SystemExit("--audio-only needs --asset")
    port = None if args.audio_only else args.port
    if not (args.dry_run or args.audio_only) and not port:
        raise SystemExit("--port is required unless --dry-run or --audio-only")
    audio_wanted = not (args.dry_run or args.no_audio) or args.silent_audio

    # Bench wire format (lead decision 9 Nov): each frame is ONE 64-byte write = 30 NUL guard + frame;
    # RESYNC_PREAMBLE (64 B, one write) before the first frame of every session and every epoch.
    source_bytes = b"".join(b for _, _, b in frames)

    def transform(b: bytes) -> bytes:
        x = bytearray(b)
        if args.rejected == "hz0":
            x[5] = 0
        elif args.rejected == "ver2":
            x[4] = 2
        return bytes(x)
    frames = [(t, seq, transform(b)) for t, seq, b in frames]
    sent_bytes = b"".join(b for _, _, b in frames)
    transform_rec = {"rejected": args.rejected,
                     "rule": {"hz0": "byte 5 (hz) = 0", "ver2": "byte 4 (version) = 2"}.get(args.rejected),
                     "source_stream_sha256": hashlib.sha256(source_bytes).hexdigest(),
                     "sent_stream_sha256": hashlib.sha256(sent_bytes).hexdigest()}
    preflight = None
    if not args.audio_only:
        sent_path = Path(str(Path(args.log)) + ".sent.prsm")
        sent_path.write_bytes(sent_bytes)
        audit = HERE.parent.parent / "lane-b" / "audit_prsm_bytes.py"
        cmd = [sys.executable, str(audit), str(sent_path), "--guard", str(ps.FRAME_GUARD_BYTES),
               "--json", str(sent_path) + ".audit.json"] + (["--allow-rejected-frames"] if args.rejected else [])
        res = subprocess.run(cmd, capture_output=True, text=True)
        preflight = {"argv": cmd[1:], "exit": res.returncode, "verdict": (res.stdout.strip().splitlines() or [""])[0],
                     "sent_file": str(sent_path)}
        if res.returncode != 0:
            Path(args.log).write_text(json.dumps({"kind": "refused", "preflight": preflight, "transform": transform_rec}) + "\n")
            raise SystemExit(f"pre-flight audit refused the bytes to be sent: {preflight['verdict']}")
    by_t = {}
    for t, seq, b in frames:
        pkt = ps.wire_packets(b)[0]
        assert len(pkt) == 64
        by_t[t] = (seq, pkt)
    preamble = ps.RESYNC_PREAMBLE
    assert len(preamble) == 64
    ts = [t for t, _, _ in frames]
    start_us = int(round(args.start_s * 1e6)) if args.start_s is not None else ts[0]
    seeks = sorted((float(a), float(b)) for a, b in (s.split(":") for s in args.seek))

    pacing = args.pacing or ("audio" if audio_wanted else "wall")
    if pacing == "audio" and not audio_wanted:
        raise SystemExit("--pacing audio needs audio (or --silent-audio)")
    log_path = Path(args.log)
    log = log_path.open("w")
    state = {"audio": None, "ser": None, "closed": False, "stop": None, "reader": None}

    def cleanup(*_):
        if state["closed"]:
            return
        state["closed"] = True
        if state["reader"] is not None:
            state["reader"].halt.set()
            state["reader"].join(timeout=1.0)
        if state["audio"] is not None:
            state["audio"].close()
        if state["ser"] is not None:
            try:
                state["ser"].close()
            except Exception:
                pass
        if PIDFILE.exists() and PIDFILE.read_text().strip() == str(os.getpid()):
            PIDFILE.unlink(missing_ok=True)

    atexit.register(cleanup)

    def on_signal(signum, _frame):
        # Only record the request: the loop finishes the in-flight 64-byte write, then stops.
        state["stop"] = f"signal {signum}"
    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, on_signal)

    def write_whole(b: bytes):
        ser = state["ser"]
        if ser is None:
            return
        n = ser.write(b)                 # pyserial loops internally until all bytes are written
        if n != len(b):
            raise IOError(f"short write {n}/{len(b)}")

    header = {"kind": "header", "stream": str(stream), "stream_sha256": side["stream_sha256"],
              "asset_sha256_verified": asset_ok, "port_opened": port if not args.dry_run else None,
              "port_arg": args.port, "baud_note": "USB-CDC ignores baud",
              "mode": "audio-only" if args.audio_only else ("dry-run" if args.dry_run else (
                  "silent-audio" if args.silent_audio else ("no-audio" if args.no_audio else "audio"))),
              "transform": transform_rec, "preflight": preflight, "start_delay_s": args.start_delay_s,
              "start_us": start_us, "seeks": seeks, "hz": side["hz"], "pacing": pacing,
              "wire": {"packet_bytes": 64, "guard_nul": ps.FRAME_GUARD_BYTES, "preamble_bytes": len(preamble),
                       "preamble_sha256": hashlib.sha256(preamble).hexdigest(), "k1ct_frames": "never built"},
              "watchdog": {"table": WATCHDOG, "allow_line": args.allow_line, "pause_s": PAUSE_NS / 1e9}}
    exit_code = EXIT_OK
    try:
        if audio_wanted:
            notes = [stop_previous_player()]
            busy = other_playback()
            if busy:
                raise SystemExit(f"other audio playback is running ({busy}); not started, nothing stopped")
            header["prior_playback_check"] = {"afplay": busy, "previous_player": notes[0]}
        PIDFILE.write_text(str(os.getpid()))
        if port and not args.dry_run:
            import serial
            state["ser"] = serial.Serial(port, args.baud, timeout=0.05, write_timeout=0.25)
        if audio_wanted:
            state["audio"] = Audio(Path(args.asset) if args.asset else Path("/dev/null"), side["asset"]["sample_rate"],
                                   start_us / 1e6, silent=args.silent_audio, gain_db=min(0.0, args.gain_db))
        header["thread_qos_rc"] = raise_thread_qos()
        t_open = time.monotonic_ns()
        if state["ser"] is not None:
            state["reader"] = DeviceReader(state["ser"], t_open, Path(str(log_path) + ".device.jsonl"), args.allow_line)
            state["reader"].start()
            # Nothing is sent before the first line boundary after open (or the timeout).
            got = state["reader"].armed.wait(args.boundary_timeout_s)
            header["line_boundary"] = {"seen": got, "wait_us": (time.monotonic_ns() - t_open) // 1000,
                                       "discarded_partial": state["reader"].discarded}
        if args.start_delay_s > 0:
            end = time.monotonic_ns() + int(args.start_delay_s * 1e9)
            while time.monotonic_ns() < end and not state["stop"]:
                time.sleep(0.01)
        t0 = time.monotonic_ns()
        header["t0_after_open_us"] = (t0 - t_open) // 1000
        if state["audio"] is not None:
            state["audio"].start()
            header["audio_start_monotonic_us"] = (time.monotonic_ns() - t0) // 1000
            header["os_output_latency_s"] = state["audio"].stream.latency
            dev = state["audio"].sd.query_devices(kind="output")
            header["output_device"] = {"name": dev["name"], "default_low_output_latency_s": dev["default_low_output_latency"]}
        log.write(json.dumps(header) + "\n")
        a = state["audio"]
        rd = state["reader"]
        anchor_wall_ns, anchor_us = t0, start_us
        pause_shift_ns = 0                      # wall pacing: frames resume at the current timeline point
        k = next(i for i, t in enumerate(ts) if t >= start_us)
        seek_i = idx = skipped = preambles = 0
        need_preamble = True
        epoch = 0
        stop_ns = t0 + int(args.stop_after_s * 1e9) if args.stop_after_s else None

        def target_of(i):
            if pacing == "audio":
                return a.target_ns(ts[i])
            return anchor_wall_ns + (ts[i] - anchor_us) * 1000

        while k < len(ts):
            if state["stop"]:
                log.write(json.dumps({"kind": "stop", "reason": state["stop"], "last_seq_sent": rd.last_seq if rd else None}) + "\n")
                exit_code = max(exit_code, EXIT_STOPPED)
                break
            if rd is not None and rd.pending is not None:
                inc, rd.pending = rd.pending, None
                log.write(json.dumps({"kind": "watchdog", "reaction": inc["kind"], "t_us": inc["t_us"],
                                      "line": inc["line"], "last_seq_sent": inc["last_seq_sent"]}) + "\n")
                if inc["kind"] == "critical":
                    exit_code = EXIT_CRITICAL
                    break
                if inc["kind"] == "stop":
                    exit_code = max(exit_code, EXIT_STOPPED)
                    break
                if inc["kind"] == "isolation":
                    # no writes for >= 5.5 s so an armed calibration expires, then end the session
                    until = time.monotonic_ns() + PAUSE_NS
                    while time.monotonic_ns() < until:
                        if rd.pending is not None and rd.pending["kind"] == "critical":
                            exit_code = EXIT_CRITICAL
                            break
                        time.sleep(0.01)
                    if exit_code != EXIT_CRITICAL:
                        exit_code = EXIT_ISOLATION
                    log.write(json.dumps({"kind": "isolation_stop", "held_ns": PAUSE_NS}) + "\n")
                    break
                # pause: no writes for >= 5.5 s (so an armed calibration expires); never send any key.
                until = time.monotonic_ns() + PAUSE_NS
                while time.monotonic_ns() < until:
                    if rd.pending is not None and rd.pending["kind"] in ("critical", "stop"):
                        break
                    time.sleep(0.01)
                if rd.pending is not None and rd.pending["kind"] in ("critical", "stop"):
                    continue
                exit_code = max(exit_code, EXIT_RESUMED_AFTER_INCIDENT)
                need_preamble = True
                epoch += 1
                now = time.monotonic_ns()
                if pacing == "wall":
                    pass                        # absolute schedule: skip to the frame due now
                while k < len(ts) and (target_of(k) or now) < now:
                    k += 1
                log.write(json.dumps({"kind": "resume", "epoch": epoch, "next_index": k}) + "\n")
                continue
            t = ts[k]
            if pacing == "audio":
                while a.target_ns(t) is None:          # first callback / after a seek
                    time.sleep(0.0005)
            target = target_of(k)
            if seek_i < len(seeks) and target >= t0 + int(seeks[seek_i][0] * 1e9):
                at, to = seeks[seek_i]
                seek_i += 1
                anchor_wall_ns, anchor_us = t0 + int(at * 1e9), int(round(to * 1e6))
                k = next((i for i, tt in enumerate(ts) if tt >= anchor_us), len(ts))
                if a is not None:
                    a.seek(to)
                need_preamble = True
                epoch += 1
                log.write(json.dumps({"kind": "seek", "at_s": at, "to_s": to, "next_index": k, "epoch": epoch}) + "\n")
                continue
            if stop_ns is not None and target >= stop_ns:
                break
            now = time.monotonic_ns()
            # Late-drop: send only the newest due frame, never a catch-up burst.
            nxt = target_of(k + 1) if k + 1 < len(ts) else None
            if nxt is not None and nxt <= now and \
                    not (seek_i < len(seeks) and nxt >= t0 + int(seeks[seek_i][0] * 1e9)):
                skipped += 1
                k += 1
                continue
            if target - now > SPIN_NS:
                time.sleep((target - now - SPIN_NS) / 1e9)
                if pacing == "audio":
                    target = a.target_ns(t) or target   # refresh from the newest callback
            # Review fix 10 Nov: no busy-wait at all. Sleep the remainder (the refreshed audio-clock
            # target may have moved later); a Python spin holds the GIL the audio callback needs.
            while True:
                rem = target - time.monotonic_ns()
                if rem <= 0 or (rd is not None and rd.pending is not None):
                    break
                time.sleep(rem / 1e9)
            if state["stop"] or (rd is not None and rd.pending is not None):
                continue                        # last check before the write: handled at loop top
            seq, pkt = by_t[t]
            pre_us = None
            if args.audio_only:
                send = time.monotonic_ns()
                rec = {"idx": idx, "seq": seq, "t_us": t, "sent": False, "sched_us": (target - t0) // 1000,
                       "send_us": (send - t0) // 1000, "err_us": (send - target) // 1000}
                if a is not None and a.map is not None:
                    m = a.map
                    rec["audio_align_us"] = int((m[1] * 1_000_000) // a.rate + (send - m[0]) // 1000 - t)
                log.write(json.dumps(rec) + "\n")
                idx += 1
                k += 1
                continue
            if need_preamble:
                pre_at = time.monotonic_ns()
                write_whole(preamble)
                preambles += 1
                need_preamble = False
                pre_us = (pre_at - t0) // 1000
            send = time.monotonic_ns()
            write_whole(pkt)
            done = time.monotonic_ns()
            if rd is not None:
                rd.last_seq = seq
            rec = {"idx": idx, "seq": seq, "t_us": t, "epoch": epoch, "sched_us": (target - t0) // 1000,
                   "send_us": (send - t0) // 1000, "done_us": (done - t0) // 1000,
                   "err_us": (send - target) // 1000}
            if pre_us is not None:
                rec["preamble_us"] = pre_us
            if a is not None and a.map is not None:
                m = a.map
                rec["audio_align_us"] = int((m[1] * 1_000_000) // a.rate + (send - m[0]) // 1000 - t)
            log.write(json.dumps(rec) + "\n")
            idx += 1
            k += 1
        footer = {"kind": "footer", "frames_sent": idx, "frames_skipped_late": skipped, "preambles_sent": preambles,
                  "epochs": epoch + 1, "elapsed_us": (time.monotonic_ns() - t0) // 1000, "exit_code": exit_code,
                  "watchdog_incidents": rd.incidents if rd else None}
        if a is not None and a.first_dac is not None:
            footer["audio_first_callback_monotonic_us"] = (a.first_cb_wall_ns - t0) // 1000
            footer["audio_first_buffer_dac_minus_current_s"] = a.first_dac - a.first_cb_stream_time
            footer["audio_callbacks"] = len(a.dac_samples)
            footer["audio_output_underflows"] = a.underflows
            footer["audio_dac_trace"] = a.dac_samples[::50]
        log.write(json.dumps(footer) + "\n")
    finally:
        cleanup()
        log.close()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
