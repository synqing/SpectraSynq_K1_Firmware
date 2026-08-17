"""Host interleave battery for Gate-4 command channels."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CTRL = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "control"
DRIVER = ROOT / "scripts" / "regression-harness" / "k1_command_channels_host_driver.cpp"


def _compile(work: Path) -> Path:
    binary = work / "k1_cmd_host"
    cmd = [
        "c++",
        "-std=c++17",
        "-O0",
        "-DK1_CMD_HOST_TEST=1",
        f"-I{CTRL}",
        str(DRIVER),
        str(CTRL / "k1_command_channels.cpp"),
        "-o",
        str(binary),
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return binary


def test_command_channel_interleaves_pass():
    with tempfile.TemporaryDirectory(prefix="k1_cmd_") as td:
        binary = _compile(Path(td))
        result = subprocess.run([str(binary)], capture_output=True, text=True, check=False)
        assert result.returncode == 0, result.stdout + result.stderr
        assert "ALL_PASS" in result.stdout
