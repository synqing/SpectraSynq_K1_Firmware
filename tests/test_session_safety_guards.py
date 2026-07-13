import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


target = load("k1_session_target_test", ROOT / "scripts/platformio/k1_session_target.py")
delegation = load("delegation_guard_test", ROOT / "scripts/agent/delegation_guard.py")

BENCH_PORTS = [
    {"device": "/dev/tty.usbmodem1401", "serial_number": "B4:3A:45:A5:89:B4"},
    {"device": "/dev/cu.usbmodem1401", "serial_number": "B4:3A:45:A5:89:B4"},
]


def make_pin(tmp_path, **overrides):
    args = dict(
        chip_id="B489A500",
        upload_port="/dev/tty.usbmodem1401",
        capture_port="/dev/cu.usbmodem1401",
        envs=["k1_bench_im73d", "k1_bench_ap_frontend_probe"],
        purpose="device eyes-on",
        state_path=tmp_path / "pin.json",
        ports=BENCH_PORTS,
        now=100,
        ttl_seconds=300,
        head="abc123",
    )
    args.update(overrides)
    return target.create_pin(**args), args["state_path"]


def test_session_pin_accepts_exact_live_target(tmp_path):
    _, path = make_pin(tmp_path)
    ok, message = target.validate_session_pin(
        "k1_bench_ap_frontend_probe", "/dev/cu.usbmodem1401",
        state_path=path, ports=BENCH_PORTS, now=200, head="abc123",
    )
    assert ok, message


@pytest.mark.parametrize(
    "env,port,ports,now,head,fragment",
    [
        ("k1_hardware", "/dev/cu.usbmodem1401", BENCH_PORTS, 200, "abc123", "not in"),
        ("k1_bench_im73d", "/dev/cu.usbmodem12401", BENCH_PORTS, 200, "abc123", "not in"),
        ("k1_bench_im73d", "/dev/cu.usbmodem1401", BENCH_PORTS, 401, "abc123", "expired"),
        ("k1_bench_im73d", "/dev/cu.usbmodem1401", BENCH_PORTS, 200, "def456", "HEAD drift"),
        ("k1_bench_im73d", "/dev/cu.usbmodem1401", [{"device": "/dev/cu.usbmodem1401", "serial_number": "B4:3A:45:A5:87:F8"}], 200, "abc123", "identity mismatch"),
    ],
)
def test_session_pin_fault_battery_rejects_drift(tmp_path, env, port, ports, now, head, fragment):
    _, path = make_pin(tmp_path)
    ok, message = target.validate_session_pin(env, port, state_path=path, ports=ports, now=now, head=head)
    assert not ok
    assert fragment in message


def test_delegation_guard_caps_active_launches_and_releases_on_close():
    state = {"schema_version": 1, "delegations": []}
    for index in (1, 2):
        delegation.register(state, delegation_id=f"d{index}", classification="optional",
                            checkpoint_seconds=60, artefact=f"a{index}", fallback="orchestrator-local", now=100)
    with pytest.raises(RuntimeError, match="cap is 2"):
        delegation.register(state, delegation_id="d3", classification="optional",
                            checkpoint_seconds=60, artefact="a3", fallback="orchestrator-local", now=100)
    delegation.update(state, "d1", "aborted", now=110, evidence="launch call stalled")
    delegation.register(state, delegation_id="d3", classification="optional",
                        checkpoint_seconds=60, artefact="a3", fallback="orchestrator-local", now=110)


def test_delegation_guard_detects_missing_launch_acknowledgement():
    state = {"schema_version": 1, "delegations": []}
    delegation.register(state, delegation_id="stalled", classification="load-bearing",
                        checkpoint_seconds=300, artefact="result", fallback="orchestrator-local", now=100)
    assert delegation.problems(state, 131) == ["stalled: launch acknowledgement deadline missed"]


def test_delegation_guard_rejects_unbounded_checkpoint():
    state = {"schema_version": 1, "delegations": []}
    with pytest.raises(RuntimeError, match="between 30 and 300"):
        delegation.register(state, delegation_id="long", classification="optional",
                            checkpoint_seconds=301, artefact="result", fallback="orchestrator-local", now=100)
