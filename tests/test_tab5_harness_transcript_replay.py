"""Parse-only replay of captured Tab5 harness transcripts (L2 gate)."""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "tab5"
HARNESS = ROOT / "tools" / "tab5_k1_dashboard_harness.py"


def load_harness():
    spec = importlib.util.spec_from_file_location("tab5_k1_dashboard_harness", HARNESS)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def parse_transcript(path: Path) -> list[dict[str, str]]:
    events: list[dict[str, str]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^\d+\s+(tx|rx)\s+(.*)$", raw.strip())
        if not match:
            continue
        events.append({"dir": match.group(1), "line": match.group(2)})
    return events


def rx_after_tx(events: list[dict[str, str]], tx_line: str) -> list[str]:
    out: list[str] = []
    capture = False
    for event in events:
        if event["dir"] == "tx" and event["line"] == tx_line:
            capture = True
            continue
        if capture:
            if event["dir"] == "tx":
                break
            out.append(event["line"])
    return out


def test_manifest_matches_fixture() -> None:
    manifest = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))
    fixture_path = FIXTURES / manifest["fixture"]
    assert fixture_path.is_file()
    events = parse_transcript(fixture_path)
    tx_commands = [event["line"] for event in events if event["dir"] == "tx"]
    for entry in manifest["commands"]:
        assert entry["tx"] in tx_commands, f"missing tx {entry['tx']}"


def test_golden_smoke_transcript_replay() -> None:
    harness = load_harness()
    manifest = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))
    events = parse_transcript(FIXTURES / manifest["fixture"])

    for entry in manifest["commands"]:
        tx = entry["tx"]
        rx_lines = rx_after_tx(events, tx)
        assert rx_lines, f"no rx for {tx}"
        ok_prefix = entry["expect_ok"]
        ok_lines = [line for line in rx_lines if line.startswith(ok_prefix)]
        assert ok_lines, f"expected {ok_prefix} after {tx}, got {rx_lines[:3]}"
        fields = harness.parse_key_value_fields(ok_lines[0])
        for key in entry.get("fields", []):
            assert key in fields, f"{tx}: missing field {key} in {ok_lines[0][:120]}"
        k1_control = entry.get("k1_control")
        if k1_control:
            send_lines = [line for line in rx_lines if "[UI] Sending K1 control" in line]
            result_lines = [line for line in rx_lines if "[UI] K1 result ok=1" in line]
            assert send_lines, f"{tx}: missing send line"
            assert result_lines, f"{tx}: missing result line"
            send = harness.parse_tab5_send_line(send_lines[0])
            result = harness.parse_tab5_result_line(result_lines[0])
            assert send.get("control") == k1_control
            assert result.get("control") == k1_control
            assert send.get("id") == result.get("id")


def test_v2_fields_optional_on_legacy_fixture() -> None:
    manifest = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))
    events = parse_transcript(FIXTURES / manifest["fixture"])
    status_rx = rx_after_tx(events, "UI_STATUS")[0]
    harness = load_harness()
    fields = harness.parse_key_value_fields(status_rx)
    for optional in manifest["v2_optional_fields"]:
        if optional in fields:
            assert fields[optional]
