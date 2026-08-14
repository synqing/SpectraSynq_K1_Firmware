import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "audio" / "k1_mic_health.cpp"
HARNESS = ROOT / "scripts" / "regression-harness" / "mic_health_model_test.cpp"
INCLUDE = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "audio"


def _compile(tmp_path: Path, *defines: str) -> Path:
    compiler = shutil.which("c++") or shutil.which("clang++") or shutil.which("g++")
    assert compiler, "C++ compiler is required for the mic-health model gate"
    binary = tmp_path / ("mic-health-" + ("-".join(defines) if defines else "normal"))
    cmd = [compiler, "-std=c++17", "-Wall", "-Wextra", "-Werror"]
    cmd.extend(f"-D{define}" for define in defines)
    cmd.extend(["-I", str(INCLUDE), str(SRC), str(HARNESS), "-o", str(binary)])
    subprocess.run(cmd, check=True, cwd=ROOT)
    return binary


def test_mic_health_fault_battery(tmp_path):
    binary = _compile(tmp_path)
    result = subprocess.run([binary], capture_output=True, text=True, cwd=ROOT)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "MIC_HEALTH_MODEL PASS" in result.stdout


def test_mic_health_mutation_single_fault_goes_red(tmp_path):
    binary = _compile(tmp_path, "K1_MIC_HEALTH_FAULT_DEBOUNCE_FRAMES=1")
    result = subprocess.run([binary], capture_output=True, text=True, cwd=ROOT)
    assert result.returncode != 0, "fault-debounce mutation unexpectedly stayed green"
    assert "one short I2S fault is rejected by the debounce" in result.stderr
