from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "scripts" / "agent" / "tab5_protocol_parity_gate.py"

PARITY_FILES = (
    "docs/protocol/k1-ble-midi-map.json",
    "scripts/ble_midi/gen_k1_ble_midi_header.py",
    "SPECTRASYNQ_K1_FIRMWARE/network/k1_ble_midi_map.h",
    "SPECTRASYNQ_K1_FIRMWARE/network/k1_deck_identity_v1.h",
    "SPECTRASYNQ_K1_FIRMWARE/network/k1_claim_adv_v1.h",
    "tab5_firmware/src/k1_ble_midi_map.h",
    "tab5_firmware/src/deck_state_rx.cpp",
    "tab5_firmware/include/k1_deck_identity_v1.h",
    "tab5_firmware/include/k1_claim_adv_v1.h",
)


def run_gate(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", str(GATE), "--repo-root", str(repo), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def parity_fixture(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    for relative in PARITY_FILES:
        source = ROOT / relative
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    return repo


def test_current_protocol_sources_are_one_68_control_contract() -> None:
    result = run_gate(ROOT)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "TAB5_PROTOCOL_PARITY=PASS" in result.stdout
    assert "controls=68" in result.stdout
    assert "md5=9b5db3fbb17438367adeaceb541db03b" in result.stdout


def test_gate_kills_71_control_tab5_header_drift(tmp_path: Path) -> None:
    repo = parity_fixture(tmp_path)
    header = repo / "tab5_firmware/src/k1_ble_midi_map.h"
    header.write_text(
        header.read_text(encoding="utf-8").replace(
            "K1_BLE_MIDI_CONTROL_COUNT 68", "K1_BLE_MIDI_CONTROL_COUNT 71", 1
        ),
        encoding="utf-8",
    )

    result = run_gate(repo)
    assert result.returncode == 1
    assert "TAB5_HEADER_GENERATION_DRIFT" in result.stdout


def test_gate_kills_coherent_71_control_contract_before_generation(tmp_path: Path) -> None:
    repo = parity_fixture(tmp_path)
    contract_path = repo / "docs/protocol/k1-ble-midi-map.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    contract["entries"].extend(contract["entries"][-3:])
    contract["control_count"] = 71
    contract["registry_md5"] = "78fb9af9000000000000000000000000"
    contract_path.write_text(json.dumps(contract), encoding="utf-8")

    result = run_gate(repo)
    assert result.returncode == 1
    assert "CONTRACT_COUNT" in result.stdout


def test_gate_kills_identity_and_claim_drift(tmp_path: Path) -> None:
    repo = parity_fixture(tmp_path)
    identity = repo / "tab5_firmware/include/k1_deck_identity_v1.h"
    identity.write_text(
        identity.read_text(encoding="utf-8").replace(
            "9b5db3fbb17438367adeaceb541db03b",
            "78fb9af9000000000000000000000000",
            1,
        ),
        encoding="utf-8",
    )
    result = run_gate(repo)
    assert result.returncode == 1
    assert "TAB5_IDENTITY_DIGEST" in result.stdout

    shutil.copy2(
        ROOT / "tab5_firmware/include/k1_deck_identity_v1.h", identity
    )
    claim = repo / "tab5_firmware/include/k1_claim_adv_v1.h"
    claim.write_text(claim.read_text(encoding="utf-8") + "\n// drift\n", encoding="utf-8")
    result = run_gate(repo)
    assert result.returncode == 1
    assert "CLAIM_HEADER_DRIFT" in result.stdout


def test_gate_kills_receiver_count_drift(tmp_path: Path) -> None:
    repo = parity_fixture(tmp_path)
    receiver = repo / "tab5_firmware/src/deck_state_rx.cpp"
    receiver.write_text(
        receiver.read_text(encoding="utf-8").replace(
            "K1_BLE_MIDI_CONTROL_COUNT == 68",
            "K1_BLE_MIDI_CONTROL_COUNT == 71",
            1,
        ),
        encoding="utf-8",
    )
    result = run_gate(repo)
    assert result.returncode == 1
    assert "RECEIVER_COUNT" in result.stdout


def test_live_receipt_requires_armed_snapshot_and_zero_fault_counters(tmp_path: Path) -> None:
    good = tmp_path / "good.log"
    good.write_text(
        "[ble-midi] GATT advertising map_md5=9b5db3fbb17438367adeaceb541db03b\n"
        "[deck_state_rx] HELLO unit_proof=0C54FC00\n"
        "DECK_RX: phase=ARMED armed=1 live=0 gen=5 rev=0 map_mismatch=0 "
        "desync=0 recovery=0 snap_commit=1 snap_reject=0 invalid=0\n",
        encoding="utf-8",
    )
    result = run_gate(ROOT, "--serial-log", str(good))
    assert result.returncode == 0, result.stdout + result.stderr
    assert "TAB5_LIVE_PROTOCOL=PASS" in result.stdout

    bad = tmp_path / "bad.log"
    bad.write_text(good.read_text(encoding="utf-8").replace("invalid=0", "invalid=1"), encoding="utf-8")
    result = run_gate(ROOT, "--serial-log", str(bad))
    assert result.returncode == 1
    assert "LIVE_COUNTER_INVALID" in result.stdout


def test_fast_gate_is_wired_before_expensive_pytest_and_documented() -> None:
    hook = (ROOT / "scripts/hooks/pre-commit").read_text(encoding="utf-8")
    gate_call = "tab5_protocol_parity_gate.py"
    assert gate_call in hook
    assert hook.index(gate_call) < hook.index("run_pytest()")

    nested_contract = (ROOT / "tab5_firmware/AGENTS.md").read_text(encoding="utf-8")
    discipline = (
        ROOT / ".claude/skills/k1-deck16-session-discipline/SKILL.md"
    ).read_text(encoding="utf-8")
    assert gate_call in nested_contract
    assert gate_call in discipline
    assert "71-control" in discipline
    assert "live sender/receiver bytes" in discipline


def test_load_bearing_agent_canon_is_present_and_skill_mirrors_match() -> None:
    agent_standard = ROOT / "docs/agent/AGENT_EXECUTION_STANDARD.md"
    assert agent_standard.is_file()
    root_contract = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "docs/agent/AGENT_EXECUTION_STANDARD.md" in root_contract

    canonical = (
        ROOT / ".claude/skills/k1-deck16-session-discipline/SKILL.md"
    ).read_text(encoding="utf-8")
    for mirror in (
        ROOT / ".codex/skills/k1-deck16-session-discipline/SKILL.md",
        ROOT / ".cursor/skills/k1-deck16-session-discipline/SKILL.md",
    ):
        assert mirror.read_text(encoding="utf-8") == canonical
