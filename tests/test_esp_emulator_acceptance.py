"""Host tests for the K1 emulator replay acceptance contract (no emulator needed).

The same ``emu_capture.accept`` function is used by real runs, comparisons and
the runner's planted cases. These tests build captures exactly as the fixture
prints them and require the right rejection reason for each defect.
"""

from __future__ import annotations

import json
import re
import struct
import sys
import zlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "esp_emulator"))

import emu_blob  # noqa: E402
import emu_capture as ec  # noqa: E402
import run as runner  # noqa: E402

RUN_ID = "0123456789abcdef0123456789abcdef"
CRC = 0x1D5BDFB1
EPOCH = 1_000_000


def wire_to_dump(wire: bytes) -> str:
    return "".join(wire[i + 2:i + 4].hex() + wire[i:i + 2].hex() + wire[i + 4:i + 6].hex()
                   for i in range(0, len(wire), 6))


def make_expect(**over) -> ec.Expect:
    base = dict(run_id=RUN_ID, payload_crc32=CRC, real_samples=96 * 8, pad_samples=0, rate_hz=12800,
                hop_samples=96, capture_start_hop=0, capture_end_hop=8, capture_every=1, recovery=False,
                commands=[], epoch_policy="declared", declared_epoch_us=EPOCH)
    base.update(over)
    return ec.Expect(**base)


def make_uart(exp: ec.Expect, *, end_reason: str = "eof") -> str:
    hops = exp.captured_hops()
    lines = (["EMU_CLIENT_READY trace=uart1 tx=6 rx=7"] if exp.client_transport else []) + [
             "EMU_FS_BEGIN PASS",
             f"EMU_FIXTURE_ARMED run={exp.run_id} source=blob valid=1 invalid=- rate={exp.rate_hz} "
             f"hop={exp.hop_samples} real_samples={exp.real_samples} pad_samples={exp.pad_samples} "
             f"total_hops={exp.total_hops} capture={exp.capture_start_hop}..{exp.capture_end_hop} "
             f"every={exp.capture_every} recovery={int(exp.recovery)} commands={len(exp.commands)} "
             f"client_commands={len(exp.client_commands)} "
             f"transport={'client' if exp.client_transport else 'scheduled'} "
             f"payload_crc32={exp.payload_crc32:08x} stall_ms=20000 clock=hop_end_us epoch={exp.epoch_policy} "
             f"mode=lockstep rng=xorshift32:9e3779b9",
             "EMU_SS gen=0 when=boot hop=0 hex=00",
             f"EMU_EPOCH policy={exp.epoch_policy} epoch_us={exp.declared_epoch_us or 0} boot_us=79561 pre_audio_shows=0"]
    gates: dict[int, int] = {}
    for c in exp.client_commands:
        gates[c["hop"]] = gates.get(c["hop"], 0) + 1
    for hop, n_lines in gates.items():
        lines.append(f"EMU_CLIENT_GATE hop={hop} expect={n_lines}")
        for c in (c for c in exp.client_commands if c["hop"] == hop):
            lines.append(f"EMU_HCMD hop={hop} sample={hop * 96} text={c['text']}")
            rej = 1 if c.get("expect") == "rejected" else 0
            lines.append(f"EMU_HCMD_DONE hop={hop} rejected={rej} photons=1.0 secondary_photons=1.0 mode=3 "
                         f"secondary_mode=18 max_current_ma=2500")
        lines.append(f"EMU_CLIENT_GATE_DONE hop={hop} received={n_lines}")
    for c in exp.commands:
        lines.append(f"EMU_CMD hop={c['hop']} sample={c['hop'] * 96} text={c['text']}")
        rej = 1 if c.get("expect") == "rejected" else 0
        lines.append(f"EMU_CMD_DONE hop={c['hop']} rejected={rej} photons=1.0 secondary_photons=1.0 mode=3 "
                     f"secondary_mode=18 max_current_ma=2500")
    n = exp.total_hops
    rejects = sum(1 for c in exp.commands + exp.client_commands if c.get("expect") == "rejected")
    lines.append(f"EMU_END reason={end_reason} where=poll run={exp.run_id} admitted={exp.real_samples} "
                 f"processed={n * 96} staged_hops={n} total_hops={n} published={n} last_generation={n} "
                 f"consumed={n} shown={n} last_shown={n} pre_audio_shows=113 captured={len(hops)} "
                 f"commands={len(exp.commands)} host_commands={len(exp.client_commands)} rejects={rejects} "
                 f"saves=0 unstaged_admits=0 publications_without_hop=0 app_us=1")
    frames = []
    crc = 0
    for i, hop in enumerate(hops):
        a = bytes(((i * 7 + k) & 0xFF) for k in range(960))
        b = bytes(((i * 13 + 2 * k) & 0xFF) for k in range(960))
        crc = zlib.crc32(b, zlib.crc32(a, crc))
        processed = (hop + 1) * 96
        app = (EPOCH if exp.epoch_policy == "declared" else 0) + processed * 1_000_000 // 12800
        meaning = f"{hop + 1},{i},{i // 2},0.5000,127.000,0.2500,0.9000,1,0"
        frames.append(f"V,{i},{meaning},{meaning}")
        frames.append(f"S,{i},{hop + 1},{min(processed, exp.real_samples)},{processed},{app},255,0")
        frames.append(f"F,{i},{app // 1000},18,{wire_to_dump(a)},{wire_to_dump(b)}")
    lines.append(f"[RTRACE-BEGIN frames={len(hops)} every=1 px=160 fmt=rgb16hex bpp=16 edges=2 crc32={crc:08x}]")
    lines += frames
    lines.append("[RTRACE-END]")
    return "\n".join(lines) + "\n"


OK = ec.Process(0, True)


def reasons_for(text: str, exp: ec.Expect, proc: ec.Process = OK) -> list[str]:
    try:
        cap = ec.decode(text)
        err = None
    except ec.CaptureError as exc:
        cap, err = None, str(exc)
    return ec.accept(cap, exp, proc, err)


def test_complete_capture_is_accepted():
    exp = make_expect()
    assert reasons_for(make_uart(exp), exp) == []


def test_r2_malformed_counterexample_is_rejected_for_geometry_and_process():
    reasons = reasons_for(runner.r2_counterexample(), make_expect(), ec.Process(1, False))
    joined = " | ".join(reasons)
    assert "process exit code 1" in joined
    assert "header px='999' != 160" in joined
    assert "header bpp='8' != 16" in joined
    assert "header edges='7' != 2" in joined


def _edit_first(text: str, prefix: str, fn) -> str:
    out, done = [], False
    for line in text.splitlines():
        if not done and line.startswith(prefix):
            done = True
            r = fn(line)
            if r is not None:
                out.extend(r if isinstance(r, list) else [r])
        else:
            out.append(line)
    return "\n".join(out) + "\n"


@pytest.mark.parametrize("name,mutate,needle", [
    ("missing sidecar", lambda t: _edit_first(t, "S,", lambda l: None), "without a sidecar"),
    ("duplicate sidecar", lambda t: _edit_first(t, "S,", lambda l: [l, l]), "duplicate sidecar"),
    ("missing channel", lambda t: _edit_first(t, "F,", lambda l: ",".join(l.split(",")[:5])), "two edges"),
    ("corrupted payload", lambda t: _edit_first(t, "F,", lambda l: l[:-1] + ("0" if l[-1] != "0" else "1")),
     "native crc"),
    ("missing terminal", lambda t: t.replace("[RTRACE-END]", ""), "RTRACE-END count 0"),
    ("duplicate header key", lambda t: t.replace("[RTRACE-BEGIN frames=", "[RTRACE-BEGIN px=160 frames="),
     "duplicate key px"),
    ("dropped frame", lambda t: _edit_first(t, "F,3,", lambda l: None), "frames=7 != expected 8"),
    ("wrong progression", lambda t: _edit_first(t, "S,2,", lambda l: l.replace("S,2,3,", "S,2,4,")),
     "generation/processed/admitted/app_us"),
    ("stale epoch", lambda t: t.replace("epoch_us=1000000", "epoch_us=0"), "declared epoch 1000000"),
])
def test_targeted_defects_are_rejected(name, mutate, needle):
    exp = make_expect()
    reasons = reasons_for(mutate(make_uart(exp)), exp)
    assert any(needle in r for r in reasons), (name, reasons)


def test_wrong_invocation_and_failed_process():
    exp = make_expect()
    text = make_uart(exp)
    other = make_expect(run_id="f" * 32)
    assert any("armed run=" in r for r in reasons_for(text, other))
    assert any("process exit code 1" in r for r in reasons_for(text, exp, ec.Process(1, True)))
    assert any("exit-on" in r for r in reasons_for(text, exp, ec.Process(0, False)))


def test_counts_follow_window_and_cadence_not_a_fixed_135():
    exp = make_expect(real_samples=96 * 20, capture_start_hop=4, capture_end_hop=20, capture_every=3)
    assert exp.captured_hops() == [4, 7, 10, 13, 16, 19]
    assert reasons_for(make_uart(exp), exp) == []


def test_zero_tail_keeps_admitted_and_advances_processed():
    exp = make_expect(pad_samples=96 * 4, capture_end_hop=12, epoch_policy="zero", declared_epoch_us=None)
    assert exp.total_hops == 12
    text = make_uart(exp)
    assert reasons_for(text, exp) == []
    cap = ec.decode(text)
    last = cap.sidecars[len(cap.frames) - 1]
    assert (last.admitted, last.processed, last.app_us) == (768, 1152, 90000)
    assert cap.sidecars[0].app_us == 7500


def test_command_schedule_and_rejection_are_checked():
    cmds = [{"hop": 2, "text": "photons=not-a-number", "expect": "rejected"}]
    exp = make_expect(commands=cmds)
    assert reasons_for(make_uart(exp), exp) == []
    claimed_applied = make_expect(commands=[{"hop": 2, "text": "photons=not-a-number", "expect": "applied"}])
    assert any("rejected=True, expected applied" in r for r in reasons_for(make_uart(exp), claimed_applied))
    moved = make_expect(commands=[{"hop": 3, "text": "photons=not-a-number", "expect": "rejected"}])
    assert any("commands executed" in r for r in reasons_for(make_uart(exp), moved))


def test_recovery_run_must_not_issue_commands():
    exp = make_expect(recovery=True)
    text = make_uart(exp).replace("EMU_SS gen=0", "EMU_CMD hop=0 sample=0 text=save_show\nEMU_SS gen=0")
    assert any("recovery run issued" in r for r in reasons_for(text, exp))


# ---- client transport (existing client -> pty -> USBSerial -> production parser) ----

CLIENT_LINES = [{"hop": 2, "text": "photons=0.25", "expect": "applied"},
                {"hop": 5, "text": "photons=not-a-number", "expect": "rejected"}]


def test_client_lines_are_accepted_at_their_gates():
    exp = make_expect(client_commands=CLIENT_LINES, client_transport=True)
    assert reasons_for(make_uart(exp), exp) == []


@pytest.mark.parametrize("name,mutate,needle", [
    ("parsed at another hop", lambda t: t.replace("EMU_HCMD hop=2 ", "EMU_HCMD hop=3 "), "client commands parsed"),
    ("different text", lambda t: t.replace("text=photons=0.25", "text=photons=0.30"), "client commands parsed"),
    ("missing result", lambda t: _edit_first(t, "EMU_HCMD_DONE hop=2", lambda l: None), "no EMU_HCMD_DONE"),
    ("outcome flipped", lambda t: t.replace("EMU_HCMD_DONE hop=5 rejected=1", "EMU_HCMD_DONE hop=5 rejected=0"),
     "rejected=False, expected rejected"),
    ("no gate", lambda t: _edit_first(t, "EMU_CLIENT_GATE hop=2", lambda l: None), "client gates"),
    ("gate incomplete", lambda t: t.replace("EMU_CLIENT_GATE_DONE hop=5 received=1",
                                            "EMU_CLIENT_GATE_DONE hop=5 received=0"), "client gates completed"),
    ("not ready", lambda t: _edit_first(t, "EMU_CLIENT_READY", lambda l: None), "EMU_CLIENT_READY count 0"),
    ("host count", lambda t: t.replace("host_commands=2", "host_commands=1"), "end host_commands"),
    ("scheduled transport", lambda t: t.replace("transport=client", "transport=scheduled"), "armed transport"),
])
def test_client_defects_are_rejected(name, mutate, needle):
    exp = make_expect(client_commands=CLIENT_LINES, client_transport=True)
    reasons = reasons_for(mutate(make_uart(exp)), exp)
    assert any(needle in r for r in reasons), (name, reasons)


def test_undeclared_client_line_is_rejected():
    exp = make_expect()
    text = make_uart(exp).replace("EMU_SS gen=0", "EMU_HCMD hop=1 sample=96 text=photons=0.1\nEMU_SS gen=0")
    assert any("client commands parsed" in r for r in reasons_for(text, exp))


def test_recovery_run_must_not_take_client_lines():
    exp = make_expect(recovery=True)
    text = make_uart(exp).replace("EMU_SS gen=0", "EMU_HCMD hop=0 sample=0 text=save_show\nEMU_SS gen=0")
    assert any("recovery run issued" in r for r in reasons_for(text, exp))


def test_client_argv_may_not_choose_a_port_or_environment():
    import emu_client
    emu_client.check_client_argv(["pio", "device", "monitor", "--baud", "115200"])
    for bad in (["pio", "device", "monitor", "--port", "/dev/cu.usbmodem1401"],
                ["pio", "device", "monitor", "-e", "k1_main_rpl_im69d"],
                ["pio", "device", "monitor", "--project-dir=/tmp"], []):
        with pytest.raises(emu_client.ClientSpecError):
            emu_client.check_client_argv(bad)
    with pytest.raises(emu_client.ClientSpecError):
        emu_client.run_client_case(emu_argv=["esp-emu", "--console", "uart0"], client_argv=["pio"],
                                   lines=[], run_dir=Path("/nonexistent"), timeout_s=1)


def test_client_readback_needs_the_products_reply():
    import emu_client
    term = (b"boot\r\n" + b"sbr{{\r\nCONFIG.PHOTONS: 0.250000\r\n}}\r\n"
            + b"sberr[[\r\nBad command: photons=not-a-number\r\n]]\r\n")
    typed = [{"text": "photons=0.25", "expect": "applied", "terminal_offset": 6},
             {"text": "photons=not-a-number", "expect": "rejected", "terminal_offset": 6 + 38}]
    reasons, segs = emu_client.check_readback(term, typed)
    assert reasons == [] and "0.250000" in segs[0]["reply"]
    swapped = [dict(typed[0], expect="rejected"), dict(typed[1], expect="applied")]
    bad, _ = emu_client.check_readback(term, swapped)
    assert any("no rejection" in r for r in bad) and any("rejection for applied" in r for r in bad)
    silent, _ = emu_client.check_readback(b"", [dict(typed[0], terminal_offset=0)])
    assert any("no reply" in r for r in silent)


def test_client_scenario_rejections(tmp_path):
    sc = json.loads(SCENARIO.read_text())
    sc["cases"]["client-a"]["client"]["commands"][0]["text"] = "reboot=1"
    with pytest.raises(runner.ScenarioError, match="unsupported command"):
        runner.load_scenario(_write(tmp_path, sc))
    sc = json.loads(SCENARIO.read_text())
    sc["client"]["argv"] += ["--port", "/dev/cu.usbmodem1401"]
    with pytest.raises(runner.ScenarioError, match="may not set"):
        runner.load_scenario(_write(tmp_path, sc))
    sc = json.loads(SCENARIO.read_text())
    sc["cases"]["client-comp-recover"]["client"] = {"commands": [{"hop": 0, "text": "photons=1"}]}
    with pytest.raises(runner.ScenarioError, match="recovery run may not"):
        runner.load_scenario(_write(tmp_path, sc))


def test_stall_before_first_hop_needs_no_epoch_but_complete_runs_do():
    exp = make_expect(end_reason="stall")
    text = make_uart(exp, end_reason="stall")
    text = "\n".join(l for l in text.splitlines() if not l.startswith(("EMU_EPOCH", "S,", "V,", "F,")))
    text = text.replace("staged_hops=8", "staged_hops=0").replace("captured=8", "captured=0")
    text = re.sub(r"\[RTRACE-BEGIN [^\]]*\]", "[RTRACE-BEGIN frames=0 crc32=0]", text) + "\n"
    assert reasons_for(text, exp) == []
    eof = make_expect()
    no_epoch = "\n".join(l for l in make_uart(eof).splitlines() if not l.startswith("EMU_EPOCH")) + "\n"
    assert any("EMU_EPOCH count 0" in r for r in reasons_for(no_epoch, eof))


def test_stall_end_requires_reported_positions():
    exp = make_expect(end_reason="stall")
    text = make_uart(exp, end_reason="stall")
    assert reasons_for(text, exp) == []
    stripped = text.replace(" consumed=8", "")
    assert any("does not report consumed" in r for r in reasons_for(stripped, exp))


# ---- scenario schema --------------------------------------------------------

SCENARIO = ROOT / "tools" / "esp_emulator" / "s3_music_regression.json"


def _write(tmp_path: Path, sc: dict) -> Path:
    p = tmp_path / "sc.json"
    p.write_text(json.dumps(sc))
    return p


def test_maintained_scenario_loads():
    sc = runner.load_scenario(SCENARIO)
    assert sc["profile"]["product_env"] == "k1_main_rpl_im69d"
    assert set(sc["suites"]["default"]) <= set(sc["cases"])


@pytest.mark.parametrize("mutate,needle", [
    (lambda s: s["cases"]["smoke-a"].__setitem__("bogus", 1), "unknown field"),
    (lambda s: s["cases"]["ctl-a"]["commands"][0].__setitem__("text", "reboot=1"), "unsupported command"),
    (lambda s: s["cases"]["smoke-a"].__setitem__("capture", {"start_hop": 10, "end_hop": 5}), "end_hop"),
    (lambda s: s["cases"]["smoke-a"].__setitem__("epoch", {"policy": "declared"}), "'us' is required"),
    (lambda s: s["cases"]["comp-recover"].__setitem__("commands", [{"hop": 0, "text": "photons=1"}]),
     "recovery run may not"),
    (lambda s: s["cases"]["smoke-a"].__setitem__("pcm", "nope"), "unknown pcm"),
    (lambda s: s["time"].__setitem__("hop_samples", 128), "time contract"),
])
def test_scenario_rejections(tmp_path, mutate, needle):
    sc = json.loads(SCENARIO.read_text())
    mutate(sc)
    with pytest.raises(runner.ScenarioError, match=needle):
        runner.load_scenario(_write(tmp_path, sc))


def test_duplicate_json_key_is_rejected(tmp_path):
    p = tmp_path / "dup.json"
    p.write_text('{"schema": "k1-emu-scenario/2", "schema": "x"}')
    with pytest.raises(runner.ScenarioError, match="duplicate JSON key"):
        runner.load_scenario(p)


# ---- blob layout (mirrors BlobHeader in k1_emu_fixture.cpp) ------------------

def test_blob_header_layout_and_crcs():
    spec = emu_blob.BlobSpec(run_id=RUN_ID, sample_rate=12800, hop_samples=96, pcm=b"\x01\x00" * 100,
                             pad_samples=96, capture_start_hop=0, capture_end_hop=3, capture_every=1,
                             recovery=False, commands=[(1, "photons=0.5")], stall_ms=1234,
                             epoch_policy="declared", declared_epoch_us=1_000_000)
    blob, crc = emu_blob.build_blob(spec)
    h = struct.unpack_from("<8sII48s14IQ124sI", blob, 0)
    assert h[0] == b"K1EMUSC2" and h[1] == 2 and h[2] == 256
    names = ["rate", "hop", "real", "pad", "cs", "ce", "every", "flags", "ncmd", "cmd_off", "pcm_off", "stall",
             "bytes", "pcrc"]
    f = dict(zip(names, h[4:18]))
    assert (f["rate"], f["hop"], f["real"], f["pad"], f["ncmd"], f["stall"]) == (12800, 96, 100, 96, 1, 1234)
    assert f["flags"] == emu_blob.FLAG_DECLARED_EPOCH and h[18] == 1_000_000
    assert f["bytes"] == len(blob) and f["pcrc"] == crc == zlib.crc32(blob[256:])
    assert h[20] == zlib.crc32(blob[:252])
    assert blob[f["cmd_off"] + 8:f["cmd_off"] + 8 + 11] == b"photons=0.5"
    # Real samples are padded to a hop boundary inside the blob; padding is not counted as real.
    assert len(blob) - f["pcm_off"] == 2 * 192
    # Scheduled records keep kind 0 (the word older blobs always wrote as zero).
    assert struct.unpack_from("<II", blob, f["cmd_off"]) == (1, emu_blob.CMD_SCHEDULED)


def test_blob_client_lines_need_the_client_transport():
    base = dict(run_id=RUN_ID, sample_rate=12800, hop_samples=96, pcm=b"\x00\x00" * 96, pad_samples=0,
                capture_start_hop=0, capture_end_hop=1, capture_every=1, recovery=False, stall_ms=1000)
    with pytest.raises(ValueError, match="client transport"):
        emu_blob.build_blob(emu_blob.BlobSpec(commands=[(0, "photons=0.5", emu_blob.CMD_CLIENT)], **base))
    blob, _ = emu_blob.build_blob(emu_blob.BlobSpec(commands=[(0, "photons=0.5", emu_blob.CMD_CLIENT)],
                                                    client_transport=True, **base))
    h = struct.unpack_from("<8sII48s14IQ124sI", blob, 0)
    assert h[4 + 7] & emu_blob.FLAG_CLIENT_TRANSPORT
    assert struct.unpack_from("<II", blob, h[4 + 9]) == (0, emu_blob.CMD_CLIENT)


def test_show_state_oracle_round_trip():
    hexs = ("534253530100000003010000803f00000000cdcc4c3d0000803f0000803f000000000000000100000000280112010000803f"
            "00000000cdcc4c3d0000803f0000803f0000003f0000000100000000280101036666263f21020001014b01de22")
    d = runner._decode_show_state(hexs)
    assert d["crc_ok"] and d["primary"]["lightshow_mode"] == 3 and d["secondary"]["lightshow_mode"] == 18
    assert d["primary"]["palette_index"] == 40 and d["bytes"] == 95
    assert runner._encode_show_state(d) == hexs
