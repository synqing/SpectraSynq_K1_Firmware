import pathlib
import subprocess


ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_palette_flow_executable(tmp_path):
    executable = tmp_path / "palette_flow_harness"
    subprocess.run(
        [
            "clang++",
            "-std=c++17",
            "-Wall",
            "-Wextra",
            "-Werror",
            f"-I{ROOT / 'include'}",
            str(ROOT / "src/palette_flow.cpp"),
            str(ROOT / "tests/palette_flow_harness.cpp"),
            "-o",
            str(executable),
        ],
        check=True,
    )
    result = subprocess.run([str(executable)], check=True, text=True, capture_output=True)
    assert "palette_flow PASS" in result.stdout


def test_palette_flow_hot_path_is_static():
    source = (ROOT / "src/palette_flow.cpp").read_text()
    for forbidden in ("malloc(", "calloc(", "realloc(", "new ", "std::vector", "String"):
        assert forbidden not in source
