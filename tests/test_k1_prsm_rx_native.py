"""Host gate for the prepared-show serial receiver (audio/k1_prsm_rx.cpp).

Compiles the firmware's own scanner, receiver and authored-source units with
tests/k1_prsm_rx_host.cpp and runs them: packet loss at every byte of every
frame (no host guard), damaged first frames, garbage and hostile text between
frames, the exit line, command-line aborts, PRSM v2 length/CRC and the
applied-frame bookkeeping. The same program takes a .prsm file as an argument
for running the loss cases on a real stream.
"""
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
AUDIO = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "audio"
HOST = Path(__file__).parent / "k1_prsm_rx_host.cpp"


def _compiler():
    for cc in ("c++", "clang++", "g++"):
        if shutil.which(cc):
            return cc
    raise AssertionError("C++17 host compiler required")


def _build(tmp_path):
    exe = tmp_path / "k1_prsm_rx_host"
    cmd = [_compiler(), "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror", f"-I{AUDIO}",
           str(HOST), str(AUDIO / "k1_prsm.cpp"), str(AUDIO / "k1_prsm_rx.cpp"),
           str(AUDIO / "k1_authored_source.cpp"), "-o", str(exe)]
    built = subprocess.run(cmd, capture_output=True, text=True)
    assert built.returncode == 0, built.stdout + built.stderr
    return exe


def test_receiver_isolation_on_host(tmp_path):
    ran = subprocess.run([str(_build(tmp_path))], capture_output=True, text=True)
    assert ran.returncode == 0, ran.stdout + ran.stderr
    values = dict(line.split(" ", 1) for line in ran.stdout.splitlines() if " " in line)
    assert "PASS k1_prsm_rx" in ran.stdout
    # 600 frames x every kept prefix 0..33 (v1) and 0..38 (v2).
    assert values["loss_v1_synthetic_events"] == "20400"
    assert values["loss_v2_synthetic_events"] == "23400"
    for label in ("loss_v1_synthetic", "loss_v2_synthetic"):
        assert values[f"{label}_hotkeys"] == "0"
        assert values[f"{label}_commands"] == "0"
        assert values[f"{label}_corrupt_frames"] == "0"


def test_check_serial_has_no_second_input_path():
    """Nothing but the receiver's events may reach hotkeys or the parser."""
    text = (ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "serial" / "serial_menu.cpp").read_text(encoding="utf-8")
    body = text.split("void check_serial(uint32_t t_now)", 1)[1].split("void stream_agc_data", 1)[0]
    assert "serial_handle_hotkey" not in body
    assert "parse_command" not in body
    assert "k1_authored_on_frame" not in body
    assert body.count("k1_serial_rx_act(rx_event, t_now)") == 2
