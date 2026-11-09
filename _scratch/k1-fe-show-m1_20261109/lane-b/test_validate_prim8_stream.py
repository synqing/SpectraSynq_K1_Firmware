"""Lane B gate: prepared Prim8 stream validator, differential oracle, and A02 timebase check.

Run once:  python3 -m pytest -v test_validate_prim8_stream.py
(Validator CLI is executed with python3.13 as the brief requires; pytest host is any python3.)
"""

from __future__ import annotations

import json
import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "oracle"))
import prim8_stream as ps  # noqa: E402
import py_device_model as dm  # noqa: E402
import validate_prim8_stream as vps  # noqa: E402

FIX = HERE / "fixtures"
RAW = HERE / "raw"
ORACLE = HERE / "oracle"
FW = ORACLE / "fw_407fdf6f"
PY313 = "/opt/homebrew/opt/python@3.13/bin/python3.13"
PRISM = Path.home() / "Workspace_Management/Software/.g5r-clean/PRISM.studio"
EXPECTED = json.loads((FIX / "expected.json").read_text())
NAMES = sorted(EXPECTED)
RAW.mkdir(exist_ok=True)


def _fixture_bytes(name):
    return (FIX / f"{name}.prsm").read_bytes()


def _sidecar(name):
    p = FIX / f"{name}.prsm.json"
    return json.loads(p.read_text()) if p.exists() else None


# ---------------------------------------------------------------- real-firmware oracle
@pytest.fixture(scope="module")
def oracle_exe():
    cc = next((c for c in ("c++", "clang++", "g++") if shutil.which(c)), None)
    if cc is None:
        pytest.fail("no host C++ compiler: differential oracle BLOCKED")
    td = tempfile.mkdtemp(prefix="laneb_oracle_")
    exe = Path(td) / "device_oracle"
    cmd = [cc, "-std=c++17", "-O2", "-Wall", "-Wextra", f"-I{FW}", str(ORACLE / "device_oracle.cpp"),
           str(FW / "k1_prsm.cpp"), str(FW / "k1_authored_source.cpp"), "-o", str(exe)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return exe


@pytest.fixture(scope="module")
def oracle_out(oracle_exe):
    out = {}
    for n in NAMES:
        r = subprocess.run([str(oracle_exe), str(FIX / f"{n}.prsm")], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        out[n] = json.loads(r.stdout)
    (RAW / "oracle_c_output.json").write_text(json.dumps(out, indent=1) + "\n")
    return out


# ---------------------------------------------------------------- B4: validator verdicts
@pytest.mark.parametrize("name", NAMES)
def test_validator_verdict_matches_declared(name):
    exp = EXPECTED[name]
    v = vps.validate(_fixture_bytes(name), _sidecar(name))
    assert (v.status, v.rule, v.frame_index) == (exp["host"], exp["rule"], exp["frame"]), v.line()


@pytest.mark.parametrize("name", NAMES)
def test_validator_cli_exit_code(name):
    """Real negative inputs, run once: bad fixtures must make the CLI exit non-zero."""
    r = subprocess.run([PY313, str(HERE / "validate_prim8_stream.py"), str(FIX / f"{name}.prsm")],
                       capture_output=True, text=True)
    want = {"VALID": 0, "INVALID": 1, "UNSUPPORTED": 2}[EXPECTED[name]["host"]]
    assert r.returncode == want, r.stdout + r.stderr
    if want:
        assert f"rule={EXPECTED[name]['rule']}" in r.stderr
        frame = EXPECTED[name]["frame"]
        assert f"frame={'-' if frame is None else frame}" in r.stderr


def test_unconsumed_dims_warn():
    v = vps.validate(_fixture_bytes("unconsumed_dims"), _sidecar("unconsumed_dims"))
    assert v.ok and v.warnings and "heat" in v.warnings[0] and "gravity" in v.warnings[0]


# ---------------------------------------------------------------- differential oracle
@pytest.mark.parametrize("name", NAMES)
def test_diff_chunk_level_device_rules(name, oracle_out):
    """Device-level rules (magic, version, hz): real firmware vs Python model vs validator."""
    c = oracle_out[name]["chunks"]
    py = dm.chunk_verdicts(_fixture_bytes(name))
    assert c == py
    data = _fixture_bytes(name)
    val = [int(vps.device_frame_verdict(data[k * 34:(k + 1) * 34])[0]) for k in range(len(c))]
    assert [x["map"] for x in c] == val
    assert [x["k"] for x in c if not x["map"]] == EXPECTED[name]["device_rejects"]
    assert sum(x["map"] for x in c) == EXPECTED[name]["device_accepts"]


@pytest.mark.parametrize("name", NAMES)
def test_diff_byte_scanner(name, oracle_out):
    ev, fill = dm.scan_events(_fixture_bytes(name))
    c = oracle_out[name]
    strip = [{k: e[k] for k in ("off", "r", "b", "hz", "seq", "t_us") if k in e} for e in c["scan"]]
    assert strip == ev
    assert c["scanner_fill_at_eof"] == fill


@pytest.mark.parametrize("name", NAMES)
def test_diff_check_serial_demux(name, oracle_out):
    py = dm.demux(_fixture_bytes(name))
    assert oracle_out[name]["demux"] == py


def test_host_is_stricter_than_device(oracle_out):
    """Every chunk the device rejects is caught by the host; host device-rule failures land on
    a chunk the device also rejects."""
    for n in NAMES:
        exp = EXPECTED[n]
        rej = [x["k"] for x in oracle_out[n]["chunks"] if not x["map"]]
        if rej:
            assert exp["host"] != "VALID", n
        if exp["rule"] in vps.DEVICE_RULES:
            assert exp["frame"] in rej, n


def test_seq_discontinuity_is_not_a_device_rejection(oracle_out):
    for n in ("seq_discontinuity_undeclared", "seq_gap_2_undeclared", "backward_seek_undeclared",
              "non_monotonic_t_us"):
        frames = [e for e in oracle_out[n]["scan"] if e["r"] == "FRAME_OK"]
        assert len(frames) == 24
        assert all(e["authored_accept"] == 1 and e["state_after"] == "AUTHORED" for e in frames), n


def test_freshness_handback(oracle_out):
    assert oracle_out["constant"]["after_end"] == {"plus50": "AUTHORED", "plus51": "RECOVERY",
                                                   "plus52": "STANDALONE"}


def test_device_byte_leak_report(oracle_out):
    """Record (not gate) which fixture bytes would reach the hotkey dispatcher / command mode on
    the real device. Gate: valid streams must leak nothing."""
    rep = {}
    for n in NAMES:
        data = _fixture_bytes(n)
        d = oracle_out[n]["demux"]
        hk = dm.hotkey_report(data, d["leak_offsets"])
        rep[n] = {"frames_accepted": sum(f["mapped"] for f in d["frames_ok"]),
                  "frames_ok_unmapped": sum(1 - f["mapped"] for f in d["frames_ok"]),
                  "leaked_bytes": len(d["leak_offsets"]),
                  "hotkeys": "".join(c for _, c in hk["hotkeys"]),
                  "dangerous_hotkeys": "".join(c for _, c in hk["dangerous_hotkeys"]),
                  "command_mode_entries": len(d["command_mode_enter"]),
                  "commands_parsed": d["commands_parsed"],
                  "command_mode_at_eof": d["command_mode_at_eof"]}
        if EXPECTED[n]["host"] == "VALID":
            assert d["leak_offsets"] == [] and d["command_mode_enter"] == [], n
    (RAW / "device_leak_report.json").write_text(json.dumps(rep, indent=1) + "\n")


# ---------------------------------------------------------------- B5 / A02 timebase
def _js_math_round(x: float) -> int:
    r = math.floor(x)
    return r + 1 if x - r >= 0.5 else r


def _roundtrip_max_err(rate: int, seconds: int):
    n = np.arange(0, rate * seconds + 1, dtype=np.int64)
    t = (2 * n * 1_000_000 + rate) // (2 * rate)
    back = (2 * t * rate + 1_000_000) // 2_000_000
    return int(np.max(np.abs(back - n))), int(n[-1])


def test_a02_sample_us_sample_roundtrip():
    results = {}
    for rate in (44100, 48000):
        for label, secs in (("90s", 90), ("10min", 600)):
            err, last = _roundtrip_max_err(rate, secs)
            results[f"{rate}Hz_{label}"] = {"samples_checked": last + 1, "max_error_samples": err}
            assert err <= 1
    # spot checks match the scalar library functions
    for rate in (44100, 48000):
        for n in (0, 1, rate - 1, rate * 90, rate * 600, rate * 86400):
            assert ps.us_to_sample(ps.sample_to_us(n, rate), rate) == n
    # Trinity seconds path: n -> float seconds -> secondsToUs (JS Math.round) -> sample
    tri = {}
    for rate in (44100, 48000):
        worst = 0
        for n in list(range(0, rate * 600 + 1, 997)) + [rate * 600, rate * 86400 - 1]:
            sec = n / rate
            t_us = _js_math_round(sec * 1_000_000)
            worst = max(worst, abs(ps.us_to_sample(t_us, rate) - n))
        tri[f"{rate}Hz"] = worst
        assert worst <= 1
    # tick grid -> nearest sample: error bound is half a sample period
    grid = {}
    for rate in (44100, 48000):
        for hz in (120,):
            i = np.arange(0, hz * 600 + 1, dtype=np.int64)
            t = (i * 1_000_000 + hz // 2) // hz
            s = (2 * t * rate + 1_000_000) // 2_000_000
            t_back = (2 * s * 1_000_000 + rate) // (2 * rate)
            grid[f"{rate}Hz_{hz}Hz_10min"] = int(np.max(np.abs(t_back - t)))
            assert grid[f"{rate}Hz_{hz}Hz_10min"] <= math.ceil(1_000_000 / rate / 2)
    (RAW / "a02_timebase.json").write_text(json.dumps(
        {"sample_us_sample": results, "trinity_seconds_path_max_error_samples": tri,
         "tick_to_sample_to_us_max_error_us": grid}, indent=1) + "\n")


def test_hop_and_tick_constants():
    assert 96 / 12800 == 0.0075                    # device AP hop, config_types.h:37,41
    assert ps.tick_time_us(1, 120) == 8333          # PRSM tick at 120 Hz
    assert ps.tick_time_us(120, 120) == 1_000_000


# ---------------------------------------------------------------- cross-check against PRISM JS
@pytest.mark.skipif(shutil.which("node") is None, reason="node absent")
def test_encoder_and_tick_match_prism_js(tmp_path):
    """Lane B encoder vs PRISM.studio src/cdc.js makePrsmPacket and src/vm.js tickTimeUs (read-only)."""
    vectors = [(0, 0, [0] * 8, 120), (1, 8333, [32768, 1000, 20000, 4000, 0, 0, 8000, 0], 120),
               (0xFFFFFFFF, 600_000_000, [65535] * 8, 240), (77, 2**40 + 5, list(range(8)), 30)]
    js = f"""
const cdc = await import({json.dumps(str(PRISM / 'src/cdc.js'))});
const vm = await import({json.dumps(str(PRISM / 'src/vm.js'))});
const V = {json.dumps(vectors)};
const pk = V.map(([seq,t,p,hz]) => cdc.makePrsmPacket({{hz, seq, t_us:t, prim8_u16:p}}).toString('hex'));
const ticks = [];
for (const hz of [30, 60, 100, 120, 240]) for (const i of [0,1,2,3,7,119,120,121,72000,72001]) ticks.push([hz,i,vm.tickTimeUs(i,hz)]);
console.log(JSON.stringify({{pk, ticks}}));
"""
    f = tmp_path / "x.mjs"
    f.write_text(js)
    r = subprocess.run(["node", str(f)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    for (seq, t, p, hz), hexpk in zip(vectors, out["pk"]):
        assert ps.encode_frame(seq, t, p, hz).hex() == hexpk
    for hz, i, t in out["ticks"]:
        assert ps.tick_time_us(i, hz) == t, (hz, i)


# ---------------------------------------------------------------- prim8_stream library
def test_library_roundtrip(tmp_path):
    rows = [[k, 2 * k, 0, 0, 0, 0, 0, 0] for k in range(10)]
    asset = {"sha256": "a" * 64, "sample_rate": 44100, "sample_count": 44100 * 100, "channels": 2}
    start = 44100 * 12 + 5
    t0 = ps.first_tick_at_or_after_us(ps.sample_to_us(start, 44100), 120)
    fr = ps.build_frames(rows, 120, t0)
    side = ps.write_stream(tmp_path / "s.prsm", fr, asset=asset, passage_start_sample=start, hz=120)
    frames, side2, data = ps.read_stream(tmp_path / "s.prsm")
    assert side2 == json.loads(json.dumps(side)) and len(frames) == 10
    assert [f["prim8"] for f in frames] == rows
    assert vps.validate(data, side2).ok


# ---------------------------------------------------------------- resync preamble + byte audit
import audit_prsm_bytes as apb  # noqa: E402

_STREAM = (FIX / "constant.prsm").read_bytes()


def _stale(variant, f):
    if variant == "frame":
        return _STREAM[:f]
    return b"PRSM"[:min(f, 4)] + b"\xff" * max(0, f - 4)


@pytest.mark.parametrize("variant", ["frame", "ff"])
def test_preamble_safe_for_every_scanner_fill(variant):
    for f in range(34):
        r = apb.audit(_STREAM, preamble=True, fill=f, stale=_stale(variant, f))
        assert r["eligible"], (f, r["reasons"])
        assert r["actionable_hotkeys"] == 0 and r["command_mode_entries"] == 0
        assert r["frames_accepted"] == 24 and r["final"] == {"fill": 0, "command_mode": 0, "pending": 0}


def test_preamble_exits_command_mode():
    for pending in (0, 1, 20, 126):
        for f in (0, 4, 5, 6, 20, 33):
            r = apb.audit(_STREAM, preamble=True, fill=f, stale=_stale("frame", f), cmd=pending)
            assert r["eligible"], (pending, f, r["reasons"])
            assert r["pre_existing_line_executed"] == (pending > 0)


def test_partial_frame_hazard_without_preamble_confirmed():
    r = apb.audit(_STREAM, preamble=False, fill=20, stale=_stale("frame", 20))
    assert not r["eligible"] and r["actionable_hotkeys"] > 0 and r["command_mode_entries"] > 0
    for f in (1, 2, 3):   # partial magic self-resyncs on the next 'P'
        assert apb.audit(_STREAM, preamble=False, fill=f, stale=_stale("frame", f))["eligible"]


@pytest.mark.parametrize("name,flag,want", [("constant", [], 0), ("backward_seek", [], 0),
                                            ("bad_magic", [], 1), ("truncated_mid_stream", [], 1),
                                            ("bad_version", ["--allow-rejected-frames"], 0),
                                            ("bad_magic", ["--allow-rejected-frames"], 1)])
def test_audit_cli_exit(name, flag, want):
    r = subprocess.run([PY313, str(HERE / "audit_prsm_bytes.py"), str(FIX / f"{name}.prsm"), *flag],
                       capture_output=True, text=True)
    assert r.returncode == want, r.stdout + r.stderr


def test_resident_build_ed0aa984_has_identical_prsm_path():
    repo = HERE.parents[2]
    for f in ("serial/serial_menu.cpp", "serial/serial_menu.h", "audio/k1_prsm.cpp", "audio/k1_prsm.h",
              "audio/k1_authored_source.cpp", "audio/k1_authored_source.h"):
        blobs = [subprocess.run(["/usr/bin/git", "-C", str(repo), "rev-parse",
                                 f"{c}:SPECTRASYNQ_K1_FIRMWARE/{f}"], capture_output=True,
                                text=True).stdout.strip() for c in ("407fdf6f", "ed0aa984")]
        assert blobs[0] and blobs[0] == blobs[1], f


# ---------------------------------------------------------------- USB packet-loss exposure
@pytest.fixture(scope="module")
def loss_exe(tmp_path_factory):
    exe = tmp_path_factory.mktemp("loss") / "loss_exposure"
    r = subprocess.run(["c++", "-std=c++17", "-O2", f"-I{FW}", str(ORACLE / "loss_exposure.cpp"),
                        str(FW / "k1_prsm.cpp"), str(FW / "k1_authored_source.cpp"), "-o", str(exe)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return exe


def _loss_events(exe, path, guard, step=False):
    import os
    env = dict(os.environ, LOSS_STEP="1") if step else None
    r = subprocess.run([str(exe), str(path), str(guard)], capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stderr
    return [json.loads(x) for x in r.stdout.splitlines()]


def test_single_loss_unguarded_leaks_guarded_does_not(loss_exe):
    ev0 = _loss_events(loss_exe, FIX / "constant.prsm", 0)
    assert any(e.get("leaks") for e in ev0 if "k" in e)          # every frame: i=33 leaks 'R','S'
    ev30 = _loss_events(loss_exe, FIX / "constant.prsm", 30)
    body = [e for e in ev30 if "k" in e]
    assert body and all(not e["leaks"] and e["enters"] == 0 and e["resynced"] for e in body)
    assert ev30[-1]["summary"]["events"] == 23 * 64


def test_guard_induction_step_all_fills_all_prefixes(loss_exe):
    out = _loss_events(loss_exe, FIX / "ramp.prsm", 30, step=True)
    assert out[-1]["step_summary"]["runs_with_leaks"] == 0
    assert out[-1]["step_summary"]["runs"] == 2 * 34 * 3 * 65


def test_audit_cli_guard():
    r = subprocess.run([PY313, str(HERE / "audit_prsm_bytes.py"), str(FIX / "constant.prsm"),
                        "--guard", "30"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert all(len(p) == 64 for p in ps.wire_packets(_STREAM))
    assert len(ps.RESYNC_PREAMBLE) == 64
