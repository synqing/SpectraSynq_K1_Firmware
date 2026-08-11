"""Compile and execute the real bounded Deck-state transaction receiver."""

from __future__ import annotations

import subprocess
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TAB5 = REPO_ROOT / "tab5_firmware"


def test_real_receiver_is_transactional_and_fail_closed(tmp_path: Path) -> None:
    binary = tmp_path / "deck_state_rx_transaction"
    command = [
        "/usr/bin/clang++",
        "-std=c++17",
        "-Wall",
        "-Wextra",
        "-Werror",
        "-DTAB5_BLE_VERBOSE_DIAG=0",
        f"-I{TAB5 / 'tests/transaction_stubs'}",
        f"-I{TAB5 / 'include'}",
        f"-I{TAB5 / 'src'}",
        str(TAB5 / "src/deck_state_rx.cpp"),
        str(TAB5 / "src/k1_deck_state_v1.cpp"),
        str(TAB5 / "src/k1_deck_identity_v1.cpp"),
        str(TAB5 / "tests/deck_state_rx_transaction_harness.cpp"),
        "-o",
        str(binary),
    ]
    compile_result = subprocess.run(command, capture_output=True, text=True, check=False)
    assert compile_result.returncode == 0, compile_result.stdout + compile_result.stderr

    run_result = subprocess.run([str(binary)], capture_output=True, text=True, check=False)
    assert run_result.returncode == 0, run_result.stdout + run_result.stderr
    assert "deck_state_rx_transaction_harness: PASS" in run_result.stdout


def test_receiver_keeps_static_storage_and_production_value_logs_off() -> None:
    source = (TAB5 / "src/deck_state_rx.cpp").read_text(encoding="utf-8")
    code_only = re.sub(r'"(?:\\.|[^"\\])*"', '""', source)
    code_only = re.sub(r"//.*?$|/\*.*?\*/", "", code_only, flags=re.MULTILINE | re.DOTALL)
    assert not re.search(
        r"\b(?:malloc|calloc|realloc)\s*\(|\bString\s+[A-Za-z_]|\bnew\s+(?:\(|[A-Za-z_:])",
        code_only,
    )
    assert "K1DeckStateValue gSnapshotStage[K1_BLE_MIDI_CONTROL_COUNT]" in source
    assert "K1DeckStateValue gDeltaStage[K1_BLE_MIDI_CONTROL_COUNT]" in source
    assert source.count("#if TAB5_BLE_VERBOSE_DIAG") >= 2
    assert "canonical 68-control map" in source
    assert 'kCanonicalRegistryMd5[] = "9b5db3fbb17438367adeaceb541db03b"' in source


def test_latency_per_value_logs_are_compile_time_diagnostic_only() -> None:
    source = (TAB5 / "src/deck_latency.cpp").read_text(encoding="utf-8")
    assert "#ifndef TAB5_BLE_VERBOSE_DIAG" in source
    assert source.count("#if TAB5_BLE_VERBOSE_DIAG") >= 3
