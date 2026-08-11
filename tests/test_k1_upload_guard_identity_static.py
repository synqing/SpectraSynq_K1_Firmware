"""N4a — device-identity hygiene gate.

Proves the upload guard fails CLOSED for protected K1 envs and that identity is
single-sourced in `k1_device_identities.json` (not buried only in code). This
pairs with the pre-existing `tests/test_k1_upload_guard.py`, which locks the
accept / cross-flash / 32k-block behaviour across the refactor (that file is the
behavioural LOCK; this file adds the fail-closed + quarantine + drift coverage).

Anti-gaming: `test_gate_falpha_*` proves the decision tracks the manifest data —
a mutated identity flips the verdict, so the guard cannot be silent theatre.
Scope: dev/bench identity hygiene only. NO SKU / NVS / efuse / factory image.
"""
import dataclasses
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUARD_PATH = ROOT / "scripts" / "platformio" / "k1_upload_guard.py"
MANIFEST = ROOT / "scripts" / "platformio" / "k1_device_identities.json"

QUARANTINED_SERIAL = "FC:01:2C:DA:2B:38"
MAIN = ("/dev/tty.usbmodem1401", "B4:3A:45:A5:87:F8")   # main K1 (F887A500)
BENCH = ("/dev/tty.usbmodem12201", "B4:3A:45:A5:89:B4")  # bench K1 (B489A500)


def _load_guard():
    spec = importlib.util.spec_from_file_location("k1_upload_guard_n4a", GUARD_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


GUARD = _load_guard()


def _ports(*pairs):
    return [
        {"device": dev, "serial_number": ser, "location": "x", "hwid": ser}
        for dev, ser in pairs
    ]


# 1 — single structured identity source (manifest, not code)
def test_manifest_is_the_single_identity_source():
    assert MANIFEST.exists(), "k1_device_identities.json missing"
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert {"authorized", "quarantined", "blocked_envs"} <= set(data)
    src = GUARD_PATH.read_text(encoding="utf-8")
    assert "k1_device_identities.json" in src and "load_identities" in src
    # no second source: the manifest serials are exactly what the guard exposes
    man_serials = {a["usb_serial"] for a in data["authorized"]}
    guard_serials = {t.usb_serial for t in GUARD.K1_TARGETS}
    assert man_serials == guard_serials, (man_serials, guard_serials)


# 2 — an authorized identity is accepted for its env
def test_authorized_identity_accepted_for_its_env():
    ok, msg = GUARD.validate_upload_target("k1_hardware", MAIN[0], _ports(MAIN, BENCH))
    assert ok and "F887A500" in msg, msg
    ok2, msg2 = GUARD.validate_upload_target("k1_bench_reference", BENCH[0], _ports(MAIN, BENCH))
    assert ok2 and "B489A500" in msg2, msg2


# 3 — wrong identity rejected
def test_wrong_identity_rejected():
    ok, msg = GUARD.validate_upload_target("k1_hardware", BENCH[0], _ports(MAIN, BENCH))
    assert not ok and "has USB serial" in msg and "expected" in msg, msg


# 4 — quarantined 4th S3 rejected with an explicit message
def test_quarantined_device_rejected_explicitly():
    quar = ("/dev/tty.usbmodem1401", QUARANTINED_SERIAL)
    ok, msg = GUARD.validate_upload_target("k1_hardware", quar[0], _ports(quar))
    assert not ok, msg
    assert "KNOWN_QUARANTINED" in msg and "not authorized" in msg, msg


# 5 — unknown ESP32-S3 rejected for a protected env
def test_unknown_serial_rejected_for_protected_env():
    unknown = ("/dev/tty.usbmodem1401", "AA:BB:CC:DD:EE:FF")
    ok, msg = GUARD.validate_upload_target("k1_hardware", unknown[0], _ports(unknown))
    assert not ok and "expected" in msg, msg


def test_unmapped_k1_environment_fails_closed():
    ok, msg = GUARD.validate_upload_target(
        "k1_bench_im69d_ble_typo",
        BENCH[0],
        _ports(MAIN, BENCH),
    )
    assert not ok and "upload blocked" in msg, msg
    assert "unmapped K1 environment" in msg, msg


# 6 — a stale/default upload_port cannot bypass the serial identity check
def test_stale_default_port_cannot_bypass_serial():
    # 1401 is the configured-default port for main K1, but it now physically
    # hosts the WRONG device (bench serial). Identity-by-serial must still reject.
    stale = ("/dev/tty.usbmodem1401", "B4:3A:45:A5:89:B4")
    ok, msg = GUARD.validate_upload_target("k1_hardware", stale[0], _ports(stale))
    assert not ok and "has USB serial" in msg, msg


# 7 — Gate-Fα: the verdict tracks the manifest data (anti-theatre)
def test_gate_falpha_decision_tracks_identity_data():
    targets, quarantined, blocked = GUARD.load_identities()
    # mutate main K1's authoritative serial -> the real device is now "wrong"
    mutated = tuple(
        dataclasses.replace(t, usb_serial="00:00:00:00:00:00") if t.role == "main K1" else t
        for t in targets
    )
    ok, _ = GUARD.validate_upload_target(
        "k1_hardware", MAIN[0], _ports(MAIN),
        targets=mutated, quarantined=quarantined, blocked=blocked,
    )
    assert not ok, "guard accepted main K1 after its authoritative serial was mutated — gate is theatre"
    # removing the quarantine entry changes the verdict path (still reject, generic msg)
    quar = ("/dev/tty.usbmodem1401", QUARANTINED_SERIAL)
    ok2, msg2 = GUARD.validate_upload_target(
        "k1_hardware", quar[0], _ports(quar),
        targets=targets, quarantined={}, blocked=blocked,
    )
    assert not ok2 and "KNOWN_QUARANTINED" not in msg2, msg2


# 8 — --list-identities prints the manifest, no device I/O
def test_list_identities_dump_has_no_device_io():
    text = GUARD.format_identities()
    assert "main K1" in text
    assert "KNOWN_QUARANTINED" in text and QUARANTINED_SERIAL in text
    assert "k1_sample_rate_32k_spike" in text


# 9 — blocked_envs OVERRIDES the authorized env mapping (precedence)
def test_blocked_env_overrides_authorized_mapping():
    """A blocked env that is ALSO authorized-mapped is rejected even on the
    correct device identity — `blocked` is checked before the target lookup."""
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    env = "k1_sample_rate_32k_spike"
    # precondition: this env IS mapped to an authorized unit AND is blocked
    assert any(env in a["envs"] for a in data["authorized"]), "env must be authorized-mapped"
    assert env in data["blocked_envs"], "env must be blocked"
    assert GUARD.expected_target_for_env(env) is not None, "env would otherwise resolve to a target"
    # even with the CORRECT main-K1 identity at its port, blocked WINS -> reject
    ok, msg = GUARD.validate_upload_target(env, MAIN[0], _ports(MAIN))
    assert not ok and "upload blocked" in msg, msg


# 10 — guard loads as a PlatformIO build PRE-SCRIPT (no __file__ in SCons exec)
def test_guard_loads_without_dunder_file():
    """Regression: PlatformIO execs this file as a build pre-script WITHOUT
    `__file__`; a module-scope `Path(__file__)` NameError crashes every
    `pio run` before compilation (broke the production build once). Faithfully
    simulate: module registered in sys.modules (so @dataclass resolves), no
    `__file__`, cwd == project root (as PlatformIO runs it)."""
    import os
    import types

    src = GUARD_PATH.read_text(encoding="utf-8")
    mod = types.ModuleType("k1_upload_guard_nofile")  # ModuleType sets no __file__
    sys.modules["k1_upload_guard_nofile"] = mod
    cwd = os.getcwd()
    try:
        os.chdir(ROOT)  # PlatformIO runs the pre-script with cwd == project root
        exec(compile(src, str(GUARD_PATH), "exec"), mod.__dict__)  # must NOT NameError
    finally:
        os.chdir(cwd)
        sys.modules.pop("k1_upload_guard_nofile", None)
    assert mod.__dict__.get("K1_TARGETS"), "K1_TARGETS empty when loaded without __file__"
    assert "FC:01:2C:DA:2B:38" in mod.__dict__.get("QUARANTINED", {})
