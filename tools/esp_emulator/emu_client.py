"""Client transport for one emulator case: an existing control client drives the
emulated product through its real USBSerial and production parser.

    existing client  <->  run-owned pty  <->  esp-emu stdin/stdout (--console usb-jtag, EP1)
    fixture trace    <--  esp-emu --uart1-tcp 127.0.0.1:<port>  (UART1, read by this module)

The bridge forwards bytes unchanged in both directions. It never writes into the
product stream itself, never fabricates a reply and never opens any serial path
other than the pty it allocated for this run. The client's keyboard is a second
pty owned by this module: the client is typed at exactly as an operator would,
and only after the fixture announces the replay hop the line belongs to
(EMU_CLIENT_GATE). Every process it starts belongs to the run and is stopped by
its own handle; esp-emu is stopped with SIGINT so --save-state writes the flash
back as on an orderly exit.

Measured esp-emu 0.49.0 behaviour this depends on (README "Client transport"):
--console usb-jtag carries EP1 on stdio and discards UART0; --uart-tcp
disconnects stdio entirely; --uart1-tcp leaves stdio on EP1; output on a TCP
UART before a client connects is dropped, so the fixture waits for K1EMU-GO.
"""

from __future__ import annotations

import errno
import os
import re
import select
import signal
import socket
import subprocess
import time
import tty
from dataclasses import dataclass, field
from pathlib import Path

READY_LINE = b"K1EMU-GO\n"
TERMINAL_STRING = b"[RTRACE-END]"
# The product's framed replies (serial_tx.cpp tx_begin/tx_end): sbr{{ ... }} or sberr[[ ... ]].
REPLY_FRAME = re.compile(rb"sbr\{\{.*?\}\}|sberr\[\[.*?\]\]", re.S)
REPLY_WAIT_S = 5.0
# The client prints this once its serial port is open (pio device monitor / miniterm).
CLIENT_OPEN_MARKERS = (b"--- Terminal on", b"--- Miniterm on", b"Quit: Ctrl+C")
# Options the runner owns. A scenario client argv carrying one of them could
# select a project environment (whose monitor_port names a physical device) or
# another port, so it is refused.
RUNNER_OWNED_OPTIONS = ("--port", "-p", "--project-dir", "-d", "--environment", "-e")


class ClientSpecError(ValueError):
    pass


def check_client_argv(argv: list[str]) -> None:
    if not argv or not all(isinstance(a, str) and a for a in argv):
        raise ClientSpecError("client argv must be a non-empty list of strings")
    for a in argv:
        if a in RUNNER_OWNED_OPTIONS or any(a.startswith(o + "=") for o in RUNNER_OWNED_OPTIONS if o.startswith("--")):
            raise ClientSpecError(f"client argv may not set {a!r}; the runner supplies the run-owned pty and project dir")


@dataclass
class ClientLine:
    hop: int
    text: str
    expect: str = "applied"


@dataclass
class ClientResult:
    exit_code: int
    terminal_observed: bool
    reasons: list[str]
    record: dict = field(default_factory=dict)


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _set_nonblock(fd: int) -> None:
    os.set_blocking(fd, False)


class _Out:
    """Pending bytes for one non-blocking destination; partial writes are kept."""

    def __init__(self, fd: int | None = None, sock: socket.socket | None = None):
        self.fd, self.sock, self.buf, self.total = fd, sock, bytearray(), 0

    def push(self, data: bytes) -> None:
        self.buf += data

    def flush(self) -> None:
        while self.buf:
            try:
                n = self.sock.send(self.buf) if self.sock is not None else os.write(self.fd, self.buf)
            except (BlockingIOError, InterruptedError):
                return
            if n <= 0:
                return
            del self.buf[:n]
            self.total += n


def run_client_case(*, emu_argv: list[str], client_argv: list[str], lines: list[ClientLine],
                    run_dir: Path, timeout_s: float, ready_timeout_s: float = 60.0) -> ClientResult:
    """Run one client-transport case. emu_argv must not choose a console or UART bridge."""
    check_client_argv(client_argv)
    for a in emu_argv:
        if a in ("--console", "--uart-tcp", "--uart1-tcp", "--exit-on"):
            raise ClientSpecError(f"emulator argv may not set {a}; the client transport owns it")
    reasons: list[str] = []
    events: list[dict] = []
    t0 = time.monotonic()

    def note(kind: str, **kw) -> None:
        events.append({"t": round(time.monotonic() - t0, 3), "event": kind, **kw})

    port = _free_port()
    argv = [*emu_argv, "--console", "usb-jtag", "--uart1-tcp", f"127.0.0.1:{port}"]
    trace = bytearray()           # fixture trace (UART1)
    ep1_out = bytearray()         # product USBSerial -> client
    ep1_in = bytearray()          # client -> product USBSerial
    terminal = bytearray()        # what the client displayed on its terminal
    typed: list[dict] = []
    stderr_path = run_dir / "emu-stderr.txt"
    proc = client = None
    sock = None
    bridge_m = bridge_s = kb_m = kb_s = None
    emu_code: int | None = None
    client_code: int | None = None
    terminal_observed = False
    pty_path = None
    try:
        with stderr_path.open("wb") as se:
            proc = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=se,
                                    start_new_session=True)
        note("emulator_started", pid=proc.pid)
        deadline = time.monotonic() + 10
        while sock is None:
            try:
                sock = socket.create_connection(("127.0.0.1", port), timeout=0.2)
            except OSError:
                if proc.poll() is not None or time.monotonic() > deadline:
                    raise RuntimeError("could not connect to the emulator's UART1 trace bridge")
                time.sleep(0.01)
        sock.setblocking(False)
        note("trace_connected", port=port)

        # The run-owned pty the client opens. Nothing else is ever offered to it.
        bridge_m, bridge_s = os.openpty()
        tty.setraw(bridge_s)
        pty_path = os.ttyname(bridge_s)
        if not pty_path.startswith("/dev/tty") or os.stat(pty_path).st_rdev != os.fstat(bridge_s).st_rdev:
            raise RuntimeError(f"allocated pty {pty_path!r} does not resolve to this run's descriptor")
        kb_m, kb_s = os.openpty()
        proj = run_dir / "client-project"
        proj.mkdir()
        full_client = [*client_argv, "--project-dir", str(proj), "--port", pty_path]
        env = dict(os.environ, TERM="dumb", PLATFORMIO_NO_ANSI="true", PYTHONUNBUFFERED="1")
        client = subprocess.Popen(full_client, stdin=kb_s, stdout=kb_s, stderr=kb_s, cwd=str(proj),
                                  env=env, start_new_session=True, close_fds=True)
        os.close(kb_s)
        kb_s = None
        note("client_started", pid=client.pid, argv=full_client)
        for fd in (bridge_m, kb_m, proc.stdout.fileno()):
            _set_nonblock(fd)
        stdin_fd = proc.stdin.fileno()
        _set_nonblock(stdin_fd)
        to_emu = _Out(fd=stdin_fd)
        to_client_pty = _Out(fd=bridge_m)
        to_keyboard = _Out(fd=kb_m)
        to_trace = _Out(sock=sock)

        client_open = False
        ready_sent = False
        pending: list[ClientLine] = []
        by_hop: dict[int, list[ClientLine]] = {}
        for ln in lines:
            by_hop.setdefault(ln.hop, []).append(ln)
        line_buf = bytearray()
        stop_at = time.monotonic() + timeout_s
        ready_by = time.monotonic() + ready_timeout_s
        trace_eof = False

        # Operator pacing: the next line is typed once the parser has finished the
        # previous one (EMU_HCMD_DONE on the trace) and the client has displayed
        # the product's reply frame, or after REPLY_WAIT_S without one (then the
        # readback check reports the missing reply). The replay hop is held at
        # the gate meanwhile, so pacing never changes where a line applies.
        awaiting: dict = {}

        def type_next() -> None:
            ln = pending.pop(0)
            to_keyboard.push(b":" + ln.text.encode("ascii") + b"\r")
            typed.append({"hop": ln.hop, "text": ln.text, "expect": ln.expect,
                          "terminal_offset": len(terminal), "ep1_out_offset": len(ep1_out)})
            awaiting.update(offset=len(terminal), done=False, at=time.monotonic())
            note("typed", hop=ln.hop, text=ln.text)

        def maybe_type_next() -> None:
            if not pending:
                return
            if awaiting:
                replied = REPLY_FRAME.search(bytes(terminal[awaiting["offset"]:])) is not None
                if not (awaiting["done"] and (replied or time.monotonic() - awaiting["at"] > REPLY_WAIT_S)):
                    return
            type_next()

        while True:
            now = time.monotonic()
            if now > stop_at:
                reasons.append(f"client case exceeded {timeout_s:.0f} s")
                break
            if not client_open and now > ready_by:
                reasons.append("client did not report an open port")
                break
            rlist = [bridge_m, kb_m, proc.stdout.fileno()]
            if not trace_eof:
                rlist.append(sock)
            wlist = [o.sock or o.fd for o in (to_emu, to_client_pty, to_keyboard, to_trace) if o.buf]
            try:
                r, w, _ = select.select(rlist, wlist, [], 0.2)
            except InterruptedError:
                continue
            for o in (to_emu, to_client_pty, to_keyboard, to_trace):
                if o.buf:
                    o.flush()
            if sock in r:
                try:
                    d = sock.recv(65536)
                except BlockingIOError:
                    d = None
                if d == b"":
                    trace_eof = True
                    note("trace_eof")
                elif d:
                    trace += d
                    line_buf += d
                    while b"\n" in line_buf:
                        raw, _, rest = line_buf.partition(b"\n")
                        line_buf = bytearray(rest)
                        s = bytes(raw).rstrip(b"\r")
                        if s.startswith(b"EMU_CLIENT_GATE "):
                            hop = int(dict(t.split(b"=", 1) for t in s.split()[1:] if b"=" in t)[b"hop"])
                            note("gate", hop=hop)
                            awaiting.clear()
                            pending.extend(by_hop.pop(hop, []))
                        elif s.startswith(b"EMU_HCMD_DONE ") and awaiting:
                            awaiting["done"] = True
                    if TERMINAL_STRING in trace and not terminal_observed:
                        terminal_observed = True
                        note("terminal_string")
            if proc.stdout.fileno() in r:
                try:
                    d = os.read(proc.stdout.fileno(), 65536)
                except BlockingIOError:
                    d = None
                if d:
                    ep1_out += d
                    to_client_pty.push(d)
            if bridge_m in r:
                try:
                    d = os.read(bridge_m, 65536)
                except BlockingIOError:
                    d = None
                except OSError as exc:  # EIO once the client closes its side
                    if exc.errno != errno.EIO:
                        raise
                    d = None
                if d:
                    ep1_in += d
                    to_emu.push(d)
            if kb_m in r:
                try:
                    d = os.read(kb_m, 65536)
                except BlockingIOError:
                    d = None
                except OSError as exc:
                    if exc.errno != errno.EIO:
                        raise
                    d = None
                if d:
                    terminal += d
                    if not client_open and any(m in terminal for m in CLIENT_OPEN_MARKERS):
                        client_open = True
                        note("client_port_open")
            if client_open and not ready_sent:
                to_trace.push(READY_LINE)
                ready_sent = True
                note("ready_sent")
            maybe_type_next()
            if terminal_observed:
                break
            if proc.poll() is not None:
                reasons.append(f"emulator exited ({proc.returncode}) before the terminal string")
                break
            if client.poll() is not None:
                reasons.append(f"client exited ({client.returncode}) before the run finished")
                break
        if by_hop:
            reasons.append(f"declared client lines never reached a gate: {sorted(by_hop)}")
        if pending:
            reasons.append(f"client lines not delivered: {[p.text for p in pending]}")
    except Exception as exc:  # recorded, never swallowed silently
        reasons.append(f"client transport error: {type(exc).__name__}: {exc}")
    finally:
        # Stop the emulator first (SIGINT: orderly exit, --save-state writes flash).
        if proc is not None:
            if proc.poll() is None:
                proc.send_signal(signal.SIGINT)
                try:
                    proc.wait(timeout=60)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
                    reasons.append("emulator ignored SIGINT and was killed")
            emu_code = proc.returncode
            try:
                rest = proc.stdout.read() or b""
                ep1_out += rest
            except Exception:
                pass
            note("emulator_stopped", code=emu_code)
        if client is not None:
            if client.poll() is None and kb_m is not None:
                try:
                    os.write(kb_m, b"\x03")  # the client's own quit key
                except OSError:
                    pass
                try:
                    client.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    client.terminate()
                    try:
                        client.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        client.kill()
                        client.wait()
            client_code = client.returncode
            note("client_stopped", code=client_code)
            if kb_m is not None:
                try:
                    while True:
                        d = os.read(kb_m, 65536)
                        if not d:
                            break
                        terminal += d
                except OSError:
                    pass
        for fd in (bridge_m, bridge_s, kb_m, kb_s):
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass
        if sock is not None:
            sock.close()
    (run_dir / "uart.txt").write_bytes(bytes(trace))
    (run_dir / "usb-device-to-client.bin").write_bytes(bytes(ep1_out))
    (run_dir / "usb-client-to-device.bin").write_bytes(bytes(ep1_in))
    (run_dir / "client-terminal.txt").write_bytes(bytes(terminal))
    record = {
        "transport": "client", "emulator_argv": argv[1:], "client_argv": client_argv,
        "client_full_argv": [*client_argv, "--project-dir", str(run_dir / "client-project"), "--port", pty_path],
        "pty": pty_path, "trace_port": port, "emulator_exit": emu_code, "client_exit": client_code,
        "terminal_string_observed_on": "uart1-tcp" if terminal_observed else None,
        "bytes": {"trace": len(trace), "device_to_client": len(ep1_out), "client_to_device": len(ep1_in),
                  "client_terminal": len(terminal)},
        "typed": typed, "events": events,
    }
    return ClientResult(exit_code=emu_code if emu_code is not None else -9,
                        terminal_observed=terminal_observed, reasons=reasons, record=record)


def readback_segments(terminal: bytes, typed: list[dict]) -> list[dict]:
    """The client's displayed reply to each typed line: terminal text from that
    line's typing to the next one's (or the end)."""
    out = []
    for i, t in enumerate(typed):
        end = typed[i + 1]["terminal_offset"] if i + 1 < len(typed) else len(terminal)
        seg = terminal[t["terminal_offset"]:end].decode("utf-8", "replace")
        out.append({"text": t["text"], "expect": t["expect"], "reply": seg})
    return out


def check_readback(terminal: bytes, typed: list[dict]) -> tuple[list[str], list[dict]]:
    """Each applied line shows a product reply without a rejection; each rejected
    line shows the product's 'Bad command' reply naming it."""
    reasons = []
    segs = readback_segments(terminal, typed)
    for s in segs:
        name = s["text"].split("=", 1)[0]
        framed = REPLY_FRAME.search(s["reply"].encode("utf-8", "replace")) is not None
        if s["expect"] == "rejected":
            if f"Bad command: {name}" not in s["reply"]:
                reasons.append(f"client saw no rejection for {s['text']!r}")
        else:
            if "Bad command" in s["reply"]:
                reasons.append(f"client saw a rejection for applied {s['text']!r}")
            elif not framed:
                reasons.append(f"client saw no reply for {s['text']!r}")
    return reasons, segs
