"""Host tests for the pinned saved-app restore in k1_upload_guard.py.

No test opens a serial port or runs esptool. Device steps go through an injected
fake runner that models one ESP32-S3: its ROM MAC, its flash bytes, whether the
application answers `:build`, and who holds the port. Every refusal asserts that
the writer was never invoked.

Confinement does NOT rely on the guards under test. Incident 2026-10-14: a
mutation run of an earlier version of this file removed the fixture refusal,
the CLI test fell through to the real device path, and esptool really ran
against B489 (including one app0 write_flash of the pinned image). So this
module installs traps at the OS/subprocess boundary, in-process and in every
child it launches (sitecustomize on PYTHONPATH):
  * subprocess.Popen is blocked unless the argv is on a tiny allow-list
    (real `lsof` on a temp file; the helper under the child sandbox);
  * any open()/os.open() of /dev/cu.* or /dev/tty.* is blocked;
  * pyserial enumerates no ports and refuses to open.
Every blocked attempt is recorded, and tests assert the record is empty. The
`ConfinementTest` cases delete the admission checks at test level and prove the
real-default path is still stopped by the traps.
"""

import builtins
import hashlib
import importlib.util
import io
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GUARD_PATH = ROOT / "scripts" / "platformio" / "k1_upload_guard.py"
HELPER = ROOT / "scripts" / "agent" / "k1-flash-verified.sh"
BACKUP_DIR = ROOT / "_scratch" / "b489-ws2816-reference-20261013"
FULL_BACKUP = BACKUP_DIR / "original-flash-921600.bin"
PINNED_APP = BACKUP_DIR / "original-app-app0.bin"

SERIAL = "B4:3A:45:A5:89:B4"
APP_SIZE = 8192
APP_OFFSET = 0x10000


def load_guard():
    spec = importlib.util.spec_from_file_location("k1_upload_guard_restore", GUARD_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


G = load_guard()


# ── OS/subprocess-boundary traps ─────────────────────────────────────────────
_DEV_PREFIXES = ("/dev/cu.", "/dev/tty.")
TRAP_HITS = []
_REAL = {}
SANDBOX = Path(tempfile.mkdtemp(prefix="k1-restore-test-sandbox-"))
SANDBOX_TRAP_LOG = SANDBOX / "child-trap.log"


def _is_dev(path):
    try:
        text = os.fsdecode(path)
    except TypeError:
        return False
    return text.startswith(_DEV_PREFIXES)


def _block(kind, what):
    TRAP_HITS.append((kind, what))
    raise PermissionError(f"k1 restore test trap blocked {kind}: {what}")


def _popen_allowed(argv, env):
    tmp = os.path.realpath(tempfile.gettempdir())
    if len(argv) == 2 and argv[0] == "lsof" and not _is_dev(argv[1]):
        return os.path.realpath(argv[1]).startswith(tmp + os.sep)
    sandboxed = bool(env) and env.get("K1_TEST_TRAP_LOG") == str(SANDBOX_TRAP_LOG) \
        and env.get("PYTHONPATH", "").split(os.pathsep)[0] == str(SANDBOX / "py")
    if argv[:2] == ["bash", str(HELPER)] or argv[:2] == ["bash", "-c"] or argv[:2] == [sys.executable, "-c"]:
        return sandboxed
    return False


class _TrapPopen(subprocess.Popen):
    def __init__(self, args, *a, **kw):
        argv = [str(x) for x in args] if isinstance(args, (list, tuple)) else [str(args)]
        if not _popen_allowed(argv, kw.get("env")):
            self._child_created = False
            _block("subprocess", argv)
        super().__init__(args, *a, **kw)


def _trap_open(file, *a, **kw):
    if _is_dev(file):
        _block("open", os.fsdecode(file))
    return _REAL["open"](file, *a, **kw)


def _trap_os_open(path, *a, **kw):
    if _is_dev(path):
        _block("os.open", os.fsdecode(path))
    return _REAL["os.open"](path, *a, **kw)


class _TrapSerial:
    def __init__(self, *a, **kw):
        _block("serial.Serial", repr(a))


_CHILD_SITECUSTOMIZE = textwrap.dedent(
    '''
    # K1 restore test sandbox: blocks every subprocess and every /dev serial open.
    import builtins, io, json, os, subprocess
    _LOG = os.environ["K1_TEST_TRAP_LOG"]
    _OPEN, _OS_OPEN = builtins.open, os.open
    def _hit(kind, what):
        with _OPEN(_LOG, "a") as f:
            f.write(json.dumps([kind, what]) + "\\n")
        raise PermissionError("k1 restore test sandbox blocked %s: %s" % (kind, what))
    def _dev(p):
        try:
            return os.fsdecode(p).startswith(("/dev/cu.", "/dev/tty."))
        except TypeError:
            return False
    def _open(f, *a, **k):
        if _dev(f):
            _hit("open", os.fsdecode(f))
        return _OPEN(f, *a, **k)
    def _os_open(p, *a, **k):
        if _dev(p):
            _hit("os.open", os.fsdecode(p))
        return _OS_OPEN(p, *a, **k)
    class _Popen(subprocess.Popen):
        def __init__(self, args, *a, **k):
            self._child_created = False
            _hit("subprocess", [str(x) for x in args] if isinstance(args, (list, tuple)) else [str(args)])
    builtins.open = io.open = _open
    os.open = _os_open
    subprocess.Popen = _Popen
    K1_RESTORE_TEST_SANDBOX = True
    '''
)


def _write_child_sandbox():
    py = SANDBOX / "py"
    (py / "serial" / "tools").mkdir(parents=True, exist_ok=True)
    (py / "sitecustomize.py").write_text(_CHILD_SITECUSTOMIZE)
    (py / "serial" / "__init__.py").write_text(
        "class SerialException(Exception):\n    pass\n\n"
        "class Serial:\n    def __init__(self, *a, **k):\n"
        "        raise PermissionError('k1 restore test sandbox: no serial')\n"
    )
    (py / "serial" / "tools" / "__init__.py").write_text("")
    (py / "serial" / "tools" / "list_ports.py").write_text("def comports():\n    return []\n")
    bindir = SANDBOX / "bin"
    bindir.mkdir(exist_ok=True)
    for tool in ("pio", "esptool", "esptool.py", "lsof"):
        script = bindir / tool
        script.write_text(f"#!/bin/sh\necho {tool} >> '{SANDBOX / 'path-tool-ran'}'\nexit 2\n")
        script.chmod(0o755)
    (SANDBOX / "home").mkdir(exist_ok=True)


def sandbox_env():
    return dict(
        os.environ,
        PATH=f"{SANDBOX / 'bin'}:{os.environ['PATH']}",
        HOME=str(SANDBOX / "home"),
        PYTHONPATH=os.pathsep.join([str(SANDBOX / "py"), os.environ.get("PYTHONPATH", "")]).rstrip(os.pathsep),
        K1_TEST_TRAP_LOG=str(SANDBOX_TRAP_LOG),
    )


def child_trap_hits():
    if not SANDBOX_TRAP_LOG.exists():
        return []
    return [json.loads(line) for line in SANDBOX_TRAP_LOG.read_text().splitlines() if line.strip()]


def setUpModule():
    _write_child_sandbox()
    _REAL.update({"Popen": subprocess.Popen, "open": builtins.open, "io.open": io.open, "os.open": os.open,
                  "list_serial_ports": G.list_serial_ports})
    subprocess.Popen = _TrapPopen
    builtins.open = io.open = _trap_open
    os.open = _trap_os_open
    G.list_serial_ports = lambda: []
    try:
        import serial
        import serial.tools.list_ports as list_ports

        _REAL["serial.Serial"], _REAL["comports"] = serial.Serial, list_ports.comports
        serial.Serial = _TrapSerial
        list_ports.comports = lambda: []
    except ImportError:
        pass


def tearDownModule():
    subprocess.Popen = _REAL["Popen"]
    builtins.open = _REAL["open"]
    io.open = _REAL["io.open"]
    os.open = _REAL["os.open"]
    G.list_serial_ports = _REAL["list_serial_ports"]
    if "serial.Serial" in _REAL:
        import serial
        import serial.tools.list_ports as list_ports

        serial.Serial, list_ports.comports = _REAL["serial.Serial"], _REAL["comports"]
    shutil.rmtree(SANDBOX, ignore_errors=True)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def make_app(elf=b"\x7e" * 32, magic=0xE9, size=APP_SIZE):
    data = bytearray(b"\xff" * size)
    data[0] = magic
    data[1] = 1
    struct.pack_into("<I", data, 32, 0xABCD5432)
    data[32 + 144 : 32 + 176] = elf
    return bytes(data)


def ota_entry(seq, crc=None, state=0xFFFFFFFF):
    if crc is None:
        crc = G.esp_rom_crc32_le(0xFFFFFFFF, struct.pack("<I", seq))
    return struct.pack("<I20xII", seq, state, crc)


def make_otadata(e0=(1, None), e1=(0, None)):
    data = bytearray(b"\xff" * 8192)
    if e0 is not None:
        data[0:32] = ota_entry(*e0)
    if e1 is not None:
        data[4096:4128] = ota_entry(*e1)
    return bytes(data)


def make_partition(app0=(APP_OFFSET, APP_SIZE)):
    rows = [(1, 0, 0xE000, 0x2000, b"otadata"), (0, 0x10, *app0, b"app0"), (0, 0x11, 0x650000, APP_SIZE, b"app1")]
    data = bytearray(b"\xff" * 3072)
    for i, (ptype, sub, off, size, label) in enumerate(rows):
        struct.pack_into("<HBBII16sI", data, i * 32, 0x50AA, ptype, sub, off, size, label, 0)
    return bytes(data)


class Fixture:
    """A synthetic pinned profile backed by temp files, plus a fake device."""

    def __init__(self, tmp: Path):
        self.root = tmp
        self.app = make_app()
        self.otadata = make_otadata()
        self.partition = make_partition()
        (tmp / "img").mkdir()
        (tmp / "img" / "app0.bin").write_bytes(self.app)
        self.profile = dict(G.SAVED_APP_PROFILES["b489-original-app0-20261013"])
        self.profile.update(
            image="img/app0.bin",
            sha256=sha(self.app),
            size=APP_SIZE,
            elf_sha256=(b"\x7e" * 32).hex(),
            otadata_sha256=sha(self.otadata),
            partition_sha256=sha(self.partition),
        )
        self.profiles = {"test": self.profile}
        self.declared = {
            "port": "/dev/cu.usbmodemK1TESTFAKE",
            "image": "img/app0.bin",
            "sha256": self.profile["sha256"],
            "size": APP_SIZE,
            "slot": 0,
            "offset": APP_OFFSET,
            "expect_git": "eff9bf47",
            "expect_env": "k1_bench_im69d_led150",
            "expect_chip": "B489A500",
            "expect_usb_serial": SERIAL,
        }


class FakeDevice:
    def __init__(self, fx: Fixture, *, mac=SERIAL, app=None, lsof=(1, "", ""), port_names=None):
        self.flash = bytearray(b"\xff" * (0x10000 + APP_SIZE + 0x1000))
        self.flash[0x8000 : 0x8000 + 3072] = fx.partition
        self.flash[0xE000 : 0xE000 + 8192] = fx.otadata
        self.flash[APP_OFFSET : APP_OFFSET + APP_SIZE] = make_app(elf=b"\x11" * 32)  # broken candidate
        self.mac = mac
        self.app = app  # (git, env) or None for a silent application
        self.answer_after_write = ("eff9bf47", "k1_bench_im69d_led150")
        self.lsof = lsof
        self.port_names = list(port_names or ["/dev/cu.usbmodemK1TESTFAKE"])
        self.calls = []
        self.writes = []
        self.write_rc = 0
        self.corrupt_write = False
        self.hooks = {}
        self.enumerations = 0
        self.sessions = []
        self.read_faults = {}  # offset -> "rc" | "missing" | "short"
        self.current = self.port_names[0]

    def ports(self):
        """One schedule entry per enumeration: a name (B489 there), None (B489
        absent, as during a USB re-enumeration) or a raw port list."""
        entry = self.port_names[0] if len(self.port_names) == 1 else self.port_names.pop(0)
        self.enumerations += 1
        if entry is None:
            self.current = None
            return []
        if isinstance(entry, list):
            hits = [p["device"] for p in entry if p["serial_number"] == SERIAL]
            self.current = hits[0] if len(hits) == 1 else None
            return entry
        self.current = entry
        return [{"device": entry, "serial_number": SERIAL}]

    def device_of(self, argv):
        return argv[argv.index("--port") + 1] if "--port" in argv else None

    def runner(self, argv, timeout):
        self.calls.append(list(argv))
        if argv[0] == "lsof":
            return self.lsof
        if argv[1].endswith("k1_device_identity_guard.py"):
            if self.app is None:
                return 1, "", "IDENTITY FAIL: no BUILD line"
            git, env = self.app
            return 0, f"IDENTITY OK: git={git} env={env} epoch=1\n", ""
        cmd = argv[argv.index("--after") + 2]
        self.sessions.append((cmd, self.device_of(argv)))
        if self.device_of(argv) != self.current:
            # A stale node: esptool cannot open a port that is not enumerated now.
            return 2, "", f"could not open port {self.device_of(argv)}"
        hook = self.hooks.get(cmd)
        if hook:
            hook()
        if cmd == "read_mac":
            return 0, f"Chip is ESP32-S3 (QFN56)\nMAC: {self.mac.lower()}\n", ""
        if cmd == "read_flash":
            off, size, out = int(argv[-3], 16), int(argv[-2]), argv[-1]
            fault = self.read_faults.get(off)
            if fault == "rc":
                return 2, "", "A fatal error occurred: read timed out"
            if fault == "missing":
                return 0, "", ""
            data = bytes(self.flash[off : off + size])
            Path(out).write_bytes(data[: size // 2] if fault == "short" else data)
            return 0, "", ""
        if cmd == "write_flash":
            self.writes.append(argv)
            if self.write_rc:
                return self.write_rc, "", "A fatal error occurred: interrupted"
            off, data = int(argv[-2], 16), Path(argv[-1]).read_bytes()
            if self.corrupt_write:
                data = b"\x00" * len(data)
            self.flash[off : off + len(data)] = data
            self.app = self.answer_after_write
            return 0, "", ""
        raise AssertionError(f"unexpected esptool command {argv}")

    def esptool_calls(self):
        return [c for c in self.calls if c[0] == "py"]


class RestoreTestBase(unittest.TestCase):
    def setUp(self):
        TRAP_HITS.clear()
        self._tmp = tempfile.TemporaryDirectory()
        self.fx = Fixture(Path(self._tmp.name))
        self.log = []

    def tearDown(self):
        self._tmp.cleanup()
        self.assertEqual(TRAP_HITS, [], "a live subprocess/port path was attempted")

    def run_restore(self, dev, declared=None, **kw):
        args = dict(
            profile_name="test",
            profiles=self.fx.profiles,
            root=self.fx.root,
            runner=dev.runner,
            ports_provider=dev.ports,
            sleep=lambda s: None,
            esptool_prefix=["py", "-m", "esptool"],
            log=self.log.append,
        )
        args.update(kw)
        return G.run_saved_app_restore(declared or self.fx.declared, **args)


class RestoreFlowTest(RestoreTestBase):
    def test_recovers_when_application_never_answers_before_write(self):
        dev = FakeDevice(self.fx, app=None)
        self.assertEqual(self.run_restore(dev), G.RESTORE_OK, "\n".join(self.log))
        self.assertEqual(len(dev.writes), 1)
        write = dev.writes[0]
        tail = write[write.index("write_flash") :]
        self.assertEqual(
            tail[:7], ["write_flash", "--flash_mode", "keep", "--flash_freq", "keep", "--flash_size", "keep"]
        )
        self.assertEqual(tail[7], hex(APP_OFFSET))
        self.assertEqual(len(tail), 9, "exactly one address/file pair")
        for forbidden in ("--erase-all", "-e", "erase_region", "erase_flash"):
            self.assertNotIn(forbidden, write)
        self.assertEqual(bytes(dev.flash[APP_OFFSET : APP_OFFSET + APP_SIZE]), self.fx.app)
        self.assertEqual(bytes(dev.flash[0xE000 : 0xE000 + 8192]), self.fx.otadata)
        esptool_sessions = dev.esptool_calls()
        self.assertGreaterEqual(len(esptool_sessions), 6)
        for argv in esptool_sessions:
            self.assertEqual(argv[argv.index("--after") + 1], "hard_reset", argv)

    def test_bytes_verified_but_application_silent_is_not_success(self):
        dev = FakeDevice(self.fx, app=None)
        dev.answer_after_write = None
        self.assertEqual(self.run_restore(dev), G.RESTORE_APP_SILENT)
        self.assertEqual(len(dev.writes), 1)
        self.assertTrue(any("BYTES VERIFIED" in line for line in self.log))

    def test_wrong_post_restore_app_identity_fails(self):
        dev = FakeDevice(self.fx, app=None)
        dev.answer_after_write = ("be0a97e", "k1_b489_ws2816_reference_capture")
        self.assertEqual(self.run_restore(dev), G.RESTORE_READBACK_MISMATCH)

    def test_readback_mismatch_fails_without_second_write(self):
        dev = FakeDevice(self.fx, app=("x", "y"))
        dev.corrupt_write = True
        self.assertEqual(self.run_restore(dev), G.RESTORE_READBACK_MISMATCH)
        self.assertEqual(len(dev.writes), 1)

    def test_interrupted_write_then_rerun_of_same_pin_recovers(self):
        dev = FakeDevice(self.fx, app=None)
        dev.write_rc = 2
        self.assertEqual(self.run_restore(dev), G.RESTORE_WRITE_FAILED)
        self.assertEqual(len(dev.writes), 1)
        self.assertTrue(any("rerunning this same pinned restore" in line for line in self.log))
        dev.write_rc = 0
        self.assertEqual(self.run_restore(dev), G.RESTORE_OK)
        self.assertEqual(len(dev.writes), 2)
        self.assertEqual(dev.writes[0][-2], dev.writes[1][-2])

    def test_port_name_drift_with_same_serial_is_accepted(self):
        dev = FakeDevice(self.fx, app=None, port_names=[
            "/dev/cu.usbmodemK1TESTFAKE", "/dev/cu.usbmodemK1TESTFAKE2", "/dev/cu.usbmodemK1TESTFAKE2",
            "/dev/cu.usbmodemK1TESTFAKE3", "/dev/cu.usbmodemK1TESTFAKE3",
        ])
        self.assertEqual(self.run_restore(dev), G.RESTORE_OK, "\n".join(self.log))
        self.assertTrue(any("port drift:" in line for line in self.log), "\n".join(self.log))

    def test_port_vanishes_and_drifts_between_write_and_readback(self):
        # Learn the enumeration count at the write on a clean device, then make
        # B489 disappear for three polls right after the write and come back
        # under a new name. Readback must follow it, never use the stale node.
        probe = FakeDevice(self.fx, app=None)
        self.run_restore(probe)
        writes_at = next(i for i, (cmd, _d) in enumerate(probe.sessions) if cmd == "write_flash")
        enum_before_readback = self._enumerations_before_session(probe, writes_at)
        self.log.clear()
        old, new = "/dev/cu.usbmodemK1TESTFAKE", "/dev/cu.usbmodemK1TESTFAKE2"
        schedule = [old] * enum_before_readback + [None, None, None] + [new]
        dev = FakeDevice(self.fx, app=None, port_names=schedule)
        sleeps = []
        rc = self.run_restore(dev, sleep=sleeps.append)
        self.assertEqual(rc, G.RESTORE_OK, "\n".join(self.log))
        sessions = dict(enumerate(dev.sessions))
        self.assertEqual(sessions[writes_at], ("write_flash", old))
        self.assertEqual(sessions[writes_at + 1], ("read_flash", new))
        self.assertEqual(len(dev.writes), 1)
        self.assertEqual(sleeps.count(0.5), 3, "bounded re-enumeration polls")
        self.assertTrue(any(f"port drift: {old} -> {new}" in line for line in self.log))

    def _enumerations_before_session(self, dev, session_index):
        # Re-run with a counting provider: enumerations made before session N.
        counts = []
        probe = FakeDevice(self.fx, app=None)
        real_runner = probe.runner

        def runner(argv, timeout):
            if argv[0] == "py" and len(probe.sessions) == session_index:
                counts.append(probe.enumerations)
            return real_runner(argv, timeout)

        probe.runner = runner
        self.run_restore(probe)
        self.log.clear()
        return counts[0]

    def test_port_that_never_returns_after_write_is_not_reported_untouched(self):
        probe = FakeDevice(self.fx, app=None)
        self.run_restore(probe)
        writes_at = next(i for i, (cmd, _d) in enumerate(probe.sessions) if cmd == "write_flash")
        n = self._enumerations_before_session(probe, writes_at)
        dev = FakeDevice(self.fx, app=None, port_names=["/dev/cu.usbmodemK1TESTFAKE"] * n + [None])
        sleeps = []
        self.assertEqual(self.run_restore(dev, sleep=sleeps.append), G.RESTORE_WRITE_FAILED)
        self.assertEqual(len(sleeps), 20, "re-enumeration wait is bounded")
        self.assert_write_attempted_not_verified()

    def assert_write_attempted_not_verified(self):
        text = "\n".join(self.log)
        self.assertIn("WRITE ATTEMPTED, NOT VERIFIED", text)
        self.assertNotIn("chip not written", text)

    def test_post_write_failures_are_write_failed_not_refused(self):
        def timeout():
            raise subprocess.TimeoutExpired("esptool", 900)

        def boom():
            raise ValueError("decoder broke")

        cases = {
            "write-timeout": lambda d: d.hooks.__setitem__("write_flash", timeout),
            "readback-rc": lambda d: d.read_faults.__setitem__(APP_OFFSET, "rc"),
            "readback-missing-file": lambda d: d.read_faults.__setitem__(APP_OFFSET, "missing"),
            "readback-short": lambda d: d.read_faults.__setitem__(APP_OFFSET, "short"),
        }
        for name, arm in cases.items():
            with self.subTest(case=name):
                self.log.clear()
                dev = FakeDevice(self.fx, app=None)
                arm(dev)
                self.assertEqual(self.run_restore(dev), G.RESTORE_WRITE_FAILED, "\n".join(self.log))
                self.assertEqual([c for c, _d in dev.sessions].count("write_flash"), 1)
                self.assert_write_attempted_not_verified()
        # An unexpected exception after the write, e.g. in the otadata-after read.
        self.log.clear()
        dev = FakeDevice(self.fx, app=None)
        reads = {"n": 0}

        def on_read():
            reads["n"] += 1
            if reads["n"] == 4:  # otadata, partition, readback, then otadata-after
                boom()

        dev.hooks["read_flash"] = on_read
        self.assertEqual(self.run_restore(dev), G.RESTORE_WRITE_FAILED)
        self.assert_write_attempted_not_verified()

    def test_pre_write_failures_are_refused_and_say_writer_never_invoked(self):
        def broken_ports():
            raise RuntimeError("pyserial list_ports unavailable")

        dev = FakeDevice(self.fx, app=None)
        self.assertEqual(self.run_restore(dev, ports_provider=broken_ports), G.RESTORE_REFUSED)
        self.assertIn("writer never invoked", "\n".join(self.log))
        self.log.clear()
        dev = FakeDevice(self.fx, app=None)
        dev.read_faults[0xE000] = "rc"
        self.assertEqual(self.run_restore(dev), G.RESTORE_REFUSED)
        self.assertEqual(dev.writes, [])
        self.assertIn("writer never invoked", "\n".join(self.log))

    def test_requested_port_drift_is_logged_and_chip_id_marked_derived(self):
        dev = FakeDevice(self.fx, app=None, port_names=["/dev/cu.usbmodemK1TESTFAKE2"])
        self.assertEqual(self.run_restore(dev), G.RESTORE_OK, "\n".join(self.log))
        text = "\n".join(self.log)
        self.assertIn("requested port /dev/cu.usbmodemK1TESTFAKE not enumerated; using /dev/cu.usbmodemK1TESTFAKE2", text)
        self.assertIn("derived from that MAC, not an independent silicon register read", text)

    def test_reenumeration_refuses_duplicate_or_swapped_serial(self):
        old = "/dev/cu.usbmodemK1TESTFAKE"
        cases = {
            "duplicate": [{"device": old, "serial_number": SERIAL}, {"device": "/dev/cu.dup", "serial_number": SERIAL}],
            "swapped": [{"device": old, "serial_number": "B4:3A:45:A5:87:90"},
                        {"device": "/dev/cu.usbmodemK1TESTFAKE2", "serial_number": SERIAL}],
        }
        for name, ports in cases.items():
            with self.subTest(case=name):
                self.log.clear()
                dev = FakeDevice(self.fx, app=None, port_names=[old, ports])
                self.assertEqual(self.run_restore(dev), G.RESTORE_REFUSED, "\n".join(self.log))
                self.assertEqual(dev.writes, [])


class RestoreRefusalTest(RestoreTestBase):
    def assert_refused_without_write(self, dev, declared=None, reason=None, any_esptool=True):
        rc = self.run_restore(dev, declared)
        self.assertEqual(rc, G.RESTORE_REFUSED, "\n".join(self.log))
        self.assertEqual(dev.writes, [])
        if not any_esptool:
            self.assertEqual(dev.esptool_calls(), [])
        if reason:
            self.assertTrue(any(reason in line for line in self.log), "\n".join(self.log))

    def declared(self, **changes):
        d = dict(self.fx.declared)
        d.update(changes)
        return d

    def test_declared_values_must_equal_pin_and_never_touch_device(self):
        cases = {
            "sha256": "0" * 64,
            "size": APP_SIZE + 1,
            "slot": 1,
            "offset": 0x650000,
            "expect_git": "be0a97e3",
            "expect_env": "k1_b489_ws2816_reference_capture",
            "expect_chip": "F887A500",
            "expect_usb_serial": "B4:3A:45:A5:87:F8",
        }
        for key, value in cases.items():
            with self.subTest(key=key):
                dev = FakeDevice(self.fx)
                self.assert_refused_without_write(dev, self.declared(**{key: value}), any_esptool=False)
                self.assertEqual(dev.calls, [], "refused before any device or lsof call")

    def test_substitute_image_path_refused(self):
        other = self.fx.root / "img" / "other.bin"
        other.write_bytes(self.fx.app)
        dev = FakeDevice(self.fx)
        self.assert_refused_without_write(dev, self.declared(image=str(other)), "not the pinned file", any_esptool=False)

    def test_changed_image_file_refused(self):
        (self.fx.root / "img" / "app0.bin").write_bytes(make_app(elf=b"\x22" * 32))
        dev = FakeDevice(self.fx)
        self.assert_refused_without_write(dev, reason="image sha256", any_esptool=False)

    def test_image_swapped_between_plan_and_write_refused(self):
        dev = FakeDevice(self.fx)
        swap = lambda: (self.fx.root / "img" / "app0.bin").write_bytes(make_app(elf=b"\x33" * 32))
        calls = {"n": 0}

        def on_read_flash():
            calls["n"] += 1
            if calls["n"] == 2:  # after otadata+partition were read, before the write
                swap()

        dev.hooks["read_flash"] = on_read_flash
        self.assert_refused_without_write(dev, reason="pinned source file changed")

    def test_wrong_magic_and_wrong_elf_refused_even_with_matching_hash(self):
        for bad in (make_app(magic=0xE8), make_app(elf=b"\x44" * 32)):
            with self.subTest(magic=bad[0]):
                (self.fx.root / "img" / "app0.bin").write_bytes(bad)
                self.fx.profile["sha256"] = sha(bad)
                dev = FakeDevice(self.fx)
                self.assert_refused_without_write(dev, self.declared(sha256=sha(bad)), any_esptool=False)

    def test_wrong_usb_serial_at_requested_port_refused(self):
        dev = FakeDevice(self.fx)
        dev.ports = lambda: [
            {"device": "/dev/cu.usbmodemK1TESTFAKE", "serial_number": "B4:3A:45:A5:87:90"},
            {"device": "/dev/cu.usbmodemK1TESTOTHER", "serial_number": SERIAL},
        ]
        self.assert_refused_without_write(dev, reason="not B4:3A:45:A5:89:B4", any_esptool=False)

    def test_serial_absent_or_duplicated_refused(self):
        for ports in ([], [{"device": "/dev/cu.a", "serial_number": SERIAL}, {"device": "/dev/cu.b", "serial_number": SERIAL}]):
            with self.subTest(n=len(ports)):
                dev = FakeDevice(self.fx)
                dev.ports = lambda ports=ports: ports
                self.assert_refused_without_write(dev, self.declared(port=None), "need exactly 1", any_esptool=False)

    def test_rom_mac_mismatch_refused_before_write(self):
        dev = FakeDevice(self.fx, mac="B4:3A:45:A5:87:90")
        self.assert_refused_without_write(dev, reason="ROM MAC")

    def test_ota_and_partition_refusals(self):
        cases = {
            "erased": (make_otadata(None, None), None, "no valid entry"),
            "equal-seq": (make_otadata((1, None), (1, None)), None, "equal sequence"),
            "slot-1": (make_otadata((2, None), (1, None)), None, "selects slot 1"),
            "bad-crc": (make_otadata((1, 0x1234), (0, 0x5678)), None, "no valid entry"),
            "invalid-state": (make_otadata((1, None, 3), (0, None)), None, "not bootable"),
            "app0-moved": (None, make_partition(app0=(0x20000, APP_SIZE)), "app ota_0 is 0x20000"),
            "partition-hash": (None, make_partition()[:-1] + b"\x00", "partition sha256"),
            "otadata-hash": (make_otadata((1, None), None), None, "otadata sha256"),
        }
        for name, (ota, part, reason) in cases.items():
            with self.subTest(case=name):
                self.log.clear()
                dev = FakeDevice(self.fx)
                if ota is not None:
                    dev.flash[0xE000 : 0xE000 + 8192] = ota
                if part is not None:
                    dev.flash[0x8000 : 0x8000 + 3072] = part
                self.assert_refused_without_write(dev, reason=reason)

    def test_port_owner_and_lsof_errors_refuse(self):
        cases = {
            "owner": ((0, "screen 123 user 3u CHR /dev/cu.usbmodemK1TESTFAKE\n", ""), "open by another process"),
            "error": ((1, "", "lsof: status error on /dev/cu.usbmodemK1TESTFAKE: No such file"), "could not establish"),
            "odd-rc": ((2, "", ""), "could not establish"),
        }
        for name, (result, reason) in cases.items():
            with self.subTest(case=name):
                self.log.clear()
                dev = FakeDevice(self.fx, lsof=result)
                self.assert_refused_without_write(dev, reason=reason, any_esptool=False)

    def test_missing_lsof_refuses(self):
        dev = FakeDevice(self.fx)

        def runner(argv, timeout):
            if argv[0] == "lsof":
                raise FileNotFoundError("lsof")
            return dev.runner(argv, timeout)

        rc = G.run_saved_app_restore(
            self.fx.declared, profile_name="test", profiles=self.fx.profiles, root=self.fx.root,
            runner=runner, ports_provider=dev.ports, sleep=lambda s: None,
            esptool_prefix=["py"], log=self.log.append,
        )
        self.assertEqual(rc, G.RESTORE_REFUSED)
        self.assertEqual(dev.writes, [])


class RealLsofConventionTest(unittest.TestCase):
    """The real lsof: exit 1 with no output means no owner, not an error."""

    def setUp(self):
        if shutil.which("lsof") is None:
            self.skipTest("lsof not installed")
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "node"
        self.path.write_bytes(b"x")

    def tearDown(self):
        self._tmp.cleanup()

    def test_unowned_file_is_free(self):
        G.check_port_free(str(self.path), G._real_runner)

    def test_owned_file_refuses(self):
        with open(self.path, "rb"):
            with self.assertRaisesRegex(G.RestoreRefused, "open by another process"):
                G.check_port_free(str(self.path), G._real_runner)

    def test_missing_node_refuses(self):
        with self.assertRaisesRegex(G.RestoreRefused, "could not establish"):
            G.check_port_free(str(self.path) + "-missing", G._real_runner)


class PureFunctionTest(unittest.TestCase):
    def test_rom_crc_matches_reference_vector(self):
        self.assertEqual(G.esp_rom_crc32_le(0, b"123456789"), 0xCBF43926)
        self.assertEqual(G.esp_rom_crc32_le(0xFFFFFFFF, b"\x00" * 4), 0xFFFFFFFF)

    def test_chip_id_from_mac(self):
        self.assertEqual(G.chip_id_from_mac("b4:3a:45:a5:89:b4"), "B489A500")
        self.assertEqual(G.chip_id_from_mac("B4:3A:45:A5:87:F8"), "F887A500")

    def test_restore_sessions_cannot_leave_chip_in_download_mode(self):
        for after in ("no_reset", "no_reset_stub", "soft_reset"):
            with self.assertRaises(G.RestoreRefused):
                G._esptool(["py"], "/dev/cu.x", after, "read_mac")

    def test_forbidden_esptool_arguments_cannot_be_built(self):
        # hard_reset, so the after-check passes and only the forbidden-arg check can refuse.
        for command in (("write_flash", "--erase-all", "0x10000", "f"), ("write_flash", "-e", "0x10000", "f"),
                        ("erase_region", "0x9000", "0x5000"), ("erase_flash",), ("write_flash", "--encrypt", "0x10000", "f")):
            with self.subTest(command=command[0:2]):
                with self.assertRaisesRegex(G.RestoreRefused, "forbidden esptool argument"):
                    G._esptool(["py"], "/dev/cu.usbmodemK1TESTFAKE", "hard_reset", *command)
        argv = G._esptool(["py"], "/dev/cu.usbmodemK1TESTFAKE", "hard_reset", "read_mac")
        self.assertEqual(argv[-1], "read_mac")


class FakeSConsEnv:
    """The parts of a PlatformIO SCons env the upload pre-action reads."""

    def __init__(self, pioenv, extra_images, port="/dev/cu.usbmodemK1TESTFAKE"):
        self.vars = {"$PIOENV": pioenv, "$UPLOAD_PORT": port, "$BUILD_DIR": "/fake/build"}
        self.extra = extra_images

    def subst(self, text):
        for key, value in self.vars.items():
            text = str(text).replace(key, value)
        return text

    def get(self, key, default=None):
        return self.extra if key == "FLASH_EXTRA_IMAGES" else default


class ForwardSegmentTest(unittest.TestCase):
    """The pinned env's upload pre-action must hash the files the upload sends."""

    ENV = "k1_b489_ws2816_reference_capture"

    def setUp(self):
        TRAP_HITS.clear()
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.boot, self.part, self.ota = b"B" * 64, b"P" * 32, b"O" * 16
        for name, data in (("bootloader.bin", self.boot), ("partitions.bin", self.part), ("boot_app0.bin", self.ota)):
            (self.dir / name).write_bytes(data)
        self.profile = dict(G.SAVED_APP_PROFILES["b489-original-app0-20261013"])
        self.profile.update(bootloader_sha256=sha(self.boot), partition_sha256=sha(self.part), otadata_sha256=sha(self.ota))
        self.saved = (G.SAVED_APP_PROFILES, G.validate_upload_target)
        G.SAVED_APP_PROFILES = {"b489-original-app0-20261013": self.profile}
        G.validate_upload_target = lambda env, port: (True, f"{env}: fake port ok")

    def tearDown(self):
        G.SAVED_APP_PROFILES, G.validate_upload_target = self.saved
        self._tmp.cleanup()
        self.assertEqual(TRAP_HITS, [])

    def images(self, **override):
        files = {"0x0": self.dir / "bootloader.bin", "0x8000": self.dir / "partitions.bin",
                 "0xe000": self.dir / "boot_app0.bin"}
        files.update(override)
        return [(off, str(path)) for off, path in files.items() if path is not None]

    def run_action(self, env):
        import contextlib

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            G._guard_upload_action(None, None, env)
        return out.getvalue()

    def test_pinned_env_reports_the_exact_files_the_upload_sends(self):
        out = self.run_action(FakeSConsEnv(self.ENV, self.images()))
        for name in ("bootloader.bin", "partitions.bin", "boot_app0.bin"):
            self.assertIn(str(self.dir / name), out)
        self.assertEqual(out.count("= pin"), 3)

    def test_pinned_env_refuses_changed_missing_or_extra_segments(self):
        changed = self.dir / "boot_app0_other.bin"
        changed.write_bytes(b"Z" * 16)
        cases = {
            "changed boot_app0": (self.images(**{"0xe000": changed}), "otadata"),
            "missing partitions": (self.images(**{"0x8000": None}), "no partition table"),
            "unreadable bootloader": (self.images(**{"0x0": self.dir / "nope.bin"}), "unreadable"),
            "extra segment": (self.images() + [("0x9000", str(self.dir / "boot_app0.bin"))], "unpinned extra"),
        }
        for name, (images, reason) in cases.items():
            with self.subTest(case=name):
                with self.assertRaises(SystemExit) as ctx:
                    self.run_action(FakeSConsEnv(self.ENV, images))
                self.assertIn("saved-app restore would be impossible", str(ctx.exception))
                self.assertIn(reason, str(ctx.exception))

    def test_other_envs_keep_their_semantics(self):
        changed = self.dir / "boot_app0_other.bin"
        changed.write_bytes(b"Z" * 16)
        out = self.run_action(FakeSConsEnv("k1_hardware", self.images(**{"0xe000": changed})))
        self.assertIn("fake port ok", out)
        self.assertNotIn("= pin", out)

    def test_identity_refusal_still_comes_first(self):
        G.validate_upload_target = lambda env, port: (False, "wrong serial")
        with self.assertRaises(SystemExit) as ctx:
            self.run_action(FakeSConsEnv(self.ENV, self.images()))
        self.assertIn("wrong serial", str(ctx.exception))


@unittest.skipUnless(FULL_BACKUP.is_file() and PINNED_APP.is_file(), "frozen B489 backup not on this host")
class PinnedBackupTest(unittest.TestCase):
    """The real pin, the real backup, the real CLI. Still no device."""

    PIN = [
        "--image", "_scratch/b489-ws2816-reference-20261013/original-app-app0.bin",
        "--sha256", "3d3b929e71b0d1ddc471f64f263a30c85aa38fc5a6c261dcef6087f376f9c226",
        "--size", "6553600", "--slot", "0", "--offset", "0x10000",
        "--expect-git", "eff9bf47", "--expect-env", "k1_bench_im69d_led150",
        "--expect-chip", "B489A500", "--expect-usb-serial", SERIAL,
    ]

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.dir = Path(cls._tmp.name)
        flash = FULL_BACKUP.read_bytes()
        (cls.dir / "ota.bin").write_bytes(flash[0xE000 : 0xE000 + 8192])
        (cls.dir / "part.bin").write_bytes(flash[0x8000 : 0x8000 + 3072])
        (cls.dir / "ports.json").write_text(json.dumps([{"device": "/dev/cu.usbmodem99999", "serial_number": SERIAL}]))
        cls.marker = SANDBOX / "path-tool-ran"

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def setUp(self):
        TRAP_HITS.clear()

    def tearDown(self):
        self.assertEqual(TRAP_HITS, [], "a live subprocess/port path was attempted in-process")

    def fixtures(self):
        return ["--otadata-file", str(self.dir / "ota.bin"), "--partition-file", str(self.dir / "part.bin"),
                "--ports-json", str(self.dir / "ports.json")]

    def helper(self, *args):
        """Run the real shell helper inside the child sandbox and prove nothing live was tried."""
        for stale in (self.marker, SANDBOX_TRAP_LOG):
            if stale.exists():
                stale.unlink()
        proc = subprocess.run(["bash", str(HELPER), "--restore-saved-app", *args], cwd=ROOT,
                              env=sandbox_env(), capture_output=True, text=True, timeout=60)
        out = proc.stdout + proc.stderr
        self.assertEqual(child_trap_hits(), [], out)
        self.assertFalse(self.marker.exists(), "a PATH tool (pio/esptool/lsof) ran: " + out)
        return proc.returncode, out

    def test_real_backup_selects_slot0_and_plans_one_app_write(self):
        flash = FULL_BACKUP.read_bytes()
        plan = G.plan_saved_app_restore(
            G.SAVED_APP_PROFILES["b489-original-app0-20261013"],
            image_bytes=PINNED_APP.read_bytes(),
            otadata=flash[0xE000 : 0xE000 + 8192],
            partition=flash[0x8000 : 0x8000 + 3072],
        )
        self.assertEqual(plan["writes"], [{"offset": 0x10000, "length": 6553600,
                                           "sha256": "3d3b929e71b0d1ddc471f64f263a30c85aa38fc5a6c261dcef6087f376f9c226"}])
        self.assertFalse(plan["erase_all"])
        self.assertEqual(plan["elf_sha256"], "7edb88488c521da72d1d6bbeef3b1bfa24b6cacb134323560ebbfe6d87aaf104")
        self.assertEqual(flash[0x10000 : 0x10000 + 6553600], PINNED_APP.read_bytes())

    def test_helper_plan_only_passes_without_running_any_tool(self):
        rc, out = self.helper("--plan-only", "--port", "/dev/cu.usbmodem99999", *self.PIN, *self.fixtures())
        self.assertEqual(rc, 0, out)
        self.assertIn("PLAN ONLY (no device opened, nothing written)", out)
        self.assertFalse(self.marker.exists(), "pio/esptool must not run")

    def test_helper_plan_only_refuses_candidate_identity(self):
        pin = list(self.PIN)
        pin[pin.index("--expect-git") + 1] = "be0a97e3"
        rc, out = self.helper("--plan-only", *pin, *self.fixtures())
        self.assertEqual(rc, 2, out)
        self.assertFalse(self.marker.exists())

    def test_helper_refuses_fixtures_for_a_real_write(self):
        rc, out = self.helper("--port", "/dev/cu.usbmodem99999", *self.PIN, *self.fixtures())
        self.assertEqual(rc, 2, out)
        self.assertIn("fixture files cannot authorise a device write", out)
        self.assertFalse(self.marker.exists())

    def test_helper_plan_only_requires_all_fixtures(self):
        rc, out = self.helper("--plan-only", *self.PIN, "--ports-json", str(self.dir / "ports.json"))
        self.assertEqual(rc, 2, out)
        self.assertFalse(self.marker.exists())

    def test_cli_fixture_refusal_in_process_with_device_traps(self):
        reached = []

        def trap(*a, **k):
            # Recorded, not only raised: the restore's own error handling would
            # turn a bare exception into an ordinary refusal and hide it.
            reached.append(a)
            raise AssertionError("real device path reached")

        saved = (G.list_serial_ports, G._real_runner, G._esptool_prefix)
        G.list_serial_ports = G._real_runner = G._esptool_prefix = trap
        try:
            rc = G._main(["--restore-saved-app", "--port", "/dev/cu.usbmodem99999", *self.PIN, *self.fixtures()])
        finally:
            G.list_serial_ports, G._real_runner, G._esptool_prefix = saved
        self.assertEqual(rc, G.RESTORE_REFUSED)
        self.assertEqual(reached, [], "fixture refusal must stop before any device path")


_CHILD_ESCAPE_SCRIPT = textwrap.dedent(
    '''
    # Every admission check deleted; only the OS/subprocess boundary remains.
    import importlib.util, json, os, sys
    spec = importlib.util.spec_from_file_location("g", os.environ["K1_GUARD_PATH"])
    g = importlib.util.module_from_spec(spec); sys.modules["g"] = g; spec.loader.exec_module(g)
    fx = json.loads(os.environ["K1_ESCAPE_FIXTURE"])
    for name in ("check_declared_against_profile", "check_image_against_profile", "check_port_free"):
        setattr(g, name, lambda *a, **k: None)
    g.locate_port_by_serial = lambda *a, **k: "/dev/cu.usbmodemK1TESTFAKE"
    g.await_device = lambda *a, **k: "/dev/cu.usbmodemK1TESTFAKE"
    g._esptool_prefix = lambda: [sys.executable, "-m", "esptool"]
    g.validate_upload_target = lambda *a, **k: (True, "deleted")
    g.read_app_identity = lambda *a, **k: None
    g.read_rom_identity = lambda *a, **k: fx["serial"]
    g.read_flash_region = lambda *a, **k: b""
    g.plan_saved_app_restore = lambda *a, **k: {"writes": [{"offset": 0x10000}], "slot": 0}
    rc = g.run_saved_app_restore(fx["declared"], profile_name="test",
                                 profiles={"test": fx["profile"]}, root=__import__("pathlib").Path(fx["root"]))
    print("RETURNED", rc)
    '''
)


class ConfinementTest(unittest.TestCase):
    """Delete the admission checks at test level; the traps must still stop everything."""

    def setUp(self):
        TRAP_HITS.clear()
        self._tmp = tempfile.TemporaryDirectory()
        self.fx = Fixture(Path(self._tmp.name))

    def tearDown(self):
        TRAP_HITS.clear()
        self._tmp.cleanup()

    def test_in_process_traps_block_subprocess_and_serial_nodes(self):
        with self.assertRaises(PermissionError):
            subprocess.run(["esptool.py", "version"], capture_output=True)
        with self.assertRaises(PermissionError):
            open("/dev/cu.usbmodemK1TESTFAKE", "rb")
        with self.assertRaises(PermissionError):
            os.open("/dev/tty.usbmodemK1TESTFAKE", os.O_RDWR)
        self.assertEqual([k for k, _ in TRAP_HITS], ["subprocess", "open", "os.open"])
        self.assertEqual(G.list_serial_ports(), [])

    def test_child_sandbox_is_loaded_by_the_same_python3_the_helper_execs(self):
        if SANDBOX_TRAP_LOG.exists():
            SANDBOX_TRAP_LOG.unlink()
        probe = ("import sitecustomize, subprocess; print('SANDBOX', sitecustomize.K1_RESTORE_TEST_SANDBOX, "
                 "sitecustomize.__file__); subprocess.run(['true'])")
        proc = subprocess.run(["bash", "-c", f'python3 -c "{probe}"'], env=sandbox_env(),
                              capture_output=True, text=True, timeout=60)
        self.assertIn(f"SANDBOX True {SANDBOX / 'py' / 'sitecustomize.py'}", proc.stdout, proc.stderr)
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(child_trap_hits(), [["subprocess", ["true"]]])

    def _delete_checks(self, stack):
        patches = {
            "check_declared_against_profile": lambda *a, **k: None,
            "check_image_against_profile": lambda *a, **k: None,
            "check_port_free": lambda *a, **k: None,
            "locate_port_by_serial": lambda *a, **k: "/dev/cu.usbmodemK1TESTFAKE",
            "await_device": lambda *a, **k: "/dev/cu.usbmodemK1TESTFAKE",
            "validate_upload_target": lambda *a, **k: (True, "deleted"),
            "_esptool_prefix": lambda: [sys.executable, "-m", "esptool"],
        }
        patches.update(stack)
        saved = {name: getattr(G, name) for name in patches}
        for name, value in patches.items():
            setattr(G, name, value)
        return saved

    def test_in_process_real_defaults_with_checks_deleted_are_trapped_at_each_step(self):
        stages = [
            ({}, "k1_device_identity_guard.py", G.RESTORE_REFUSED),
            ({"read_app_identity": lambda *a, **k: None}, "read_mac", G.RESTORE_REFUSED),
            ({"read_app_identity": lambda *a, **k: None, "read_rom_identity": lambda *a, **k: SERIAL,
              "read_flash_region": lambda *a, **k: b"",
              "plan_saved_app_restore": lambda *a, **k: {"writes": [{"offset": APP_OFFSET}], "slot": 0}},
             "write_flash", G.RESTORE_WRITE_FAILED),
        ]
        for extra, blocked_step, expected_rc in stages:
            with self.subTest(step=blocked_step):
                TRAP_HITS.clear()
                saved = self._delete_checks(extra)
                try:
                    # No runner, ports provider or esptool prefix injected: real defaults.
                    # The trap's PermissionError is reported, and a blocked
                    # writer still counts as an attempted write.
                    rc = G.run_saved_app_restore(self.fx.declared, profile_name="test", profiles=self.fx.profiles,
                                                 root=self.fx.root, sleep=lambda s: None, log=lambda m: None)
                finally:
                    for name, value in saved.items():
                        setattr(G, name, value)
                self.assertEqual(rc, expected_rc)
                self.assertEqual(len(TRAP_HITS), 1, TRAP_HITS)
                kind, argv = TRAP_HITS[0]
                self.assertEqual(kind, "subprocess")
                self.assertTrue(any(blocked_step in part for part in argv), argv)

    def test_child_process_with_checks_deleted_is_trapped_before_write(self):
        for stale in (SANDBOX_TRAP_LOG, SANDBOX / "path-tool-ran"):
            if stale.exists():
                stale.unlink()
        env = sandbox_env()
        env["K1_GUARD_PATH"] = str(GUARD_PATH)
        env["K1_ESCAPE_FIXTURE"] = json.dumps({
            "declared": self.fx.declared, "profile": self.fx.profile,
            "root": str(self.fx.root), "serial": SERIAL,
        })
        proc = subprocess.run([sys.executable, "-c", _CHILD_ESCAPE_SCRIPT], env=env, cwd=ROOT,
                              capture_output=True, text=True, timeout=60)
        out = proc.stdout + proc.stderr
        self.assertEqual(proc.returncode, 0, out)
        self.assertIn("RETURNED 1", out, "blocked writer must be reported as an attempted write")
        self.assertIn("PermissionError: k1 restore test sandbox blocked subprocess", out)
        hits = child_trap_hits()
        self.assertEqual(len(hits), 1, out)
        self.assertEqual(hits[0][0], "subprocess")
        self.assertIn("write_flash", hits[0][1])
        self.assertFalse((SANDBOX / "path-tool-ran").exists())
        self.assertEqual(TRAP_HITS, [])


if __name__ == "__main__":
    unittest.main()
