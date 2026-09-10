"""SCHEMA_LOCK v1.2 golden tests. Serial Studio dryRun is the oracle."""

from __future__ import annotations

import json
import socket
import sys
import uuid
from pathlib import Path

import pytest

SLOTS = (
    "bpm",
    "conf",
    "lock",
    "beat",
    "onset",
    "bass",
    "silence",
    "agc_gain",
    "peak_scaled",
    "ssl",
    "energy",
    "nov",
    "system_fps",
    "led_fps",
    "lightshow",
    "device_ms",
    "frame_ms",
    "host_parse_seq",
    "event_tid",
    "record_kind",
    "update_mask",
    "phase",
    "orbit_x",
    "orbit_y",
)
SLOT_INDEX = {name: i for i, name in enumerate(SLOTS)}
SCHEMA_LEN = 24
DEVICE_MS_SLOT_1BASED = 16

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PARSER_PATH = ROOT / "parsers" / "k1_ap_parser.js"
FIXTURE_DIR = HERE / "fixtures"
SS_UTILS = Path("/Users/spectrasynq/Serial-Studio/tests/utils")

REQUIRED_FIXTURES = (
    "bench_ap",
    "main_ap",
    "main_event_status",
    "system_fps",
    "led_fps",
    "version_build",
    "malformed",
    "missing_optional",
    "reboot_host_parse_seq",
    "historical_slot_bug",
    "held_value",
)


def mask_from_names(names) -> int:
    return sum(1 << SLOT_INDEX[n] for n in names)


def names_from_mask(mask: int):
    return [SLOTS[i] for i in range(SCHEMA_LEN) if mask & (1 << i)]


def load_fixture(path: Path) -> dict:
    data = json.loads(path.read_text())
    assert data["schema_lock"] == "1.2"
    assert "lines" in data and "expected_rows" in data
    return data


def fixture_paths():
    return [FIXTURE_DIR / f"{name}.json" for name in REQUIRED_FIXTURES]


def lines_to_ascii(lines) -> bytes:
    return "".join(ln.rstrip("\r\n") + "\n" for ln in lines).encode("ascii")


def published_rows(result: dict) -> list[list]:
    rows = []
    for frame in result.get("frames") or []:
        for row in frame.get("rows") or []:
            if row:
                rows.append(row)
    return rows


def api_listening(host: str = "127.0.0.1", port: int = 7777, timeout: float = 0.4) -> bool:
    sock = socket.socket()
    sock.settimeout(timeout)
    try:
        sock.connect((host, port))
        return True
    except OSError:
        return False
    finally:
        sock.close()


def _mini_command(command: str, params: dict, timeout: float = 8.0) -> dict:
    request_id = str(uuid.uuid4())
    message = {
        "type": "command",
        "id": request_id,
        "command": command,
        "params": params,
    }
    payload = (json.dumps(message, separators=(",", ":")) + "\n").encode("utf-8")
    sock = socket.create_connection(("127.0.0.1", 7777), timeout)
    sock.settimeout(timeout)
    try:
        sock.sendall(payload)
        buf = b""
        while True:
            chunk = sock.recv(65536)
            if not chunk:
                raise ConnectionError("Serial Studio closed the API socket")
            buf += chunk
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                if not line.strip():
                    continue
                response = json.loads(line.decode("utf-8"))
                if response.get("type") != "response" or response.get("id") != request_id:
                    continue
                if not response.get("success"):
                    error = response.get("error") or {}
                    raise RuntimeError(
                        f"{error.get('code', 'UNKNOWN')}: {error.get('message', response)}"
                    )
                return response.get("result") or {}
    finally:
        sock.close()


def dry_run(parser_code: str, raw: bytes) -> dict:
    params = {
        "code": parser_code,
        "language": 0,
        "inputBytesHex": raw.hex(),
        "decoderMethod": 0,
        "frameDetection": 0,
        "frameEnd": "0A",
        "hexadecimalDelimiters": True,
    }
    if SS_UTILS.is_dir():
        if str(SS_UTILS) not in sys.path:
            sys.path.insert(0, str(SS_UTILS))
        from api_client import SerialStudioClient

        with SerialStudioClient("127.0.0.1", 7777, timeout=8.0) as client:
            return client.command("project.frameParser.dryRun", params)
    return _mini_command("project.frameParser.dryRun", params)


def assert_expected_row(got: list, exp: dict, fixture_id: str, idx: int) -> None:
    assert len(got) == SCHEMA_LEN, (
        f"{fixture_id}[{idx}] SCHEMA_LOCK v1.2 requires {SCHEMA_LEN} slots, "
        f"got {len(got)}: {got!r}"
    )
    kind = int(float(got[SLOT_INDEX["record_kind"]]))
    seq = int(float(got[SLOT_INDEX["host_parse_seq"]]))
    mask = int(float(got[SLOT_INDEX["update_mask"]]))
    assert kind == exp["record_kind"], (
        f"{fixture_id}[{idx}] record_kind {kind} != {exp['record_kind']}"
    )
    assert seq == exp["host_parse_seq"], (
        f"{fixture_id}[{idx}] host_parse_seq {seq} != {exp['host_parse_seq']}"
    )
    written = set(exp["written"])
    unknown = written - set(SLOTS)
    assert not unknown, f"{fixture_id}[{idx}] unknown written slots {unknown}"
    for name in SLOTS:
        bit = 1 << SLOT_INDEX[name]
        if name in written:
            assert mask & bit, (
                f"{fixture_id}[{idx}] update_mask missing {name} "
                f"(bit {SLOT_INDEX[name]}); mask={mask} bits={names_from_mask(mask)}"
            )
        else:
            assert not (mask & bit), (
                f"{fixture_id}[{idx}] update_mask has {name} but line did not write it; "
                f"mask={mask} bits={names_from_mask(mask)}"
            )
    for name, expected in exp.get("values", {}).items():
        got_v = float(got[SLOT_INDEX[name]])
        assert got_v == pytest.approx(float(expected)), (
            f"{fixture_id}[{idx}] {name}={got_v} != {expected}"
        )


@pytest.fixture(scope="session")
def parser_code() -> str:
    assert PARSER_PATH.is_file(), f"missing parser {PARSER_PATH}"
    return PARSER_PATH.read_text()


def test_schema_lock_slot_table():
    assert len(SLOTS) == SCHEMA_LEN
    assert SLOTS[DEVICE_MS_SLOT_1BASED - 1] == "device_ms"
    assert SLOT_INDEX["record_kind"] == 19
    assert SLOT_INDEX["update_mask"] == 20
    assert SLOT_INDEX["host_parse_seq"] == 17
    assert SLOTS[14] == "lightshow"
    assert SLOT_INDEX["phase"] == 21
    assert SLOT_INDEX["orbit_x"] == 22
    assert SLOT_INDEX["orbit_y"] == 23


def test_orbit_trig_goldens():
    """Host check of the v1.2 orbit formula used by the parser and fixtures."""
    import math

    def orbit(peak: float, phase: float) -> tuple[float, float]:
        return (
            peak * math.cos(2 * math.pi * phase),
            peak * math.sin(2 * math.pi * phase),
        )

    ox, oy = orbit(0.35, 0.20)
    assert ox == pytest.approx(0.108156, abs=1e-6)
    assert oy == pytest.approx(0.332870, abs=1e-6)
    ox, oy = orbit(0.18, 0.10)
    assert ox == pytest.approx(0.145623, abs=1e-6)
    assert oy == pytest.approx(0.105801, abs=1e-6)
    ox, oy = orbit(0.0, 0.10)
    assert ox == pytest.approx(0.0)
    assert oy == pytest.approx(0.0)


def test_update_mask_python_decoder():
    """Always-on oracle: bit i (0-based) means slot i+1 was written this line."""
    ap_written = [
        "bpm",
        "conf",
        "lock",
        "beat",
        "onset",
        "bass",
        "silence",
        "agc_gain",
        "peak_scaled",
        "ssl",
        "lightshow",
        "host_parse_seq",
        "record_kind",
        "update_mask",
    ]
    ap_mask = mask_from_names(ap_written)
    assert names_from_mask(ap_mask) == ap_written
    assert ap_mask & (1 << SLOT_INDEX["bpm"])
    fps_mask = mask_from_names(
        ["system_fps", "host_parse_seq", "record_kind", "update_mask"]
    )
    assert not (fps_mask & (1 << SLOT_INDEX["bpm"]))
    assert fps_mask & (1 << SLOT_INDEX["system_fps"])
    held = names_from_mask(fps_mask)
    assert "bpm" not in held
    assert mask_from_names(["device_ms"]) == (1 << 15)


@pytest.mark.parametrize("path", fixture_paths(), ids=REQUIRED_FIXTURES)
def test_fixture_mask_matches_written_list(path: Path):
    data = load_fixture(path)
    for i, row in enumerate(data["expected_rows"]):
        expected_mask = mask_from_names(row["written"])
        decoded = names_from_mask(expected_mask)
        assert set(decoded) == set(row["written"]), (
            f"{path.stem}[{i}] written list is not a unique SCHEMA_LOCK slot set: "
            f"{row['written']} -> {decoded}"
        )
        if "bpm" in row.get("values", {}) and "bpm" not in row["written"]:
            assert not (expected_mask & 1), (
                f"{path.stem}[{i}] held bpm must not set update_mask bit 0"
            )


def test_required_fixtures_present():
    missing = [name for name in REQUIRED_FIXTURES if not (FIXTURE_DIR / f"{name}.json").is_file()]
    assert not missing, f"missing fixtures: {missing}"
    extra = sorted(p.stem for p in FIXTURE_DIR.glob("*.json") if p.stem not in REQUIRED_FIXTURES)
    assert extra == [], f"unexpected fixtures (SCHEMA_LOCK set is closed): {extra}"


def test_historical_slot_bug_fixture_documents_slot_16():
    data = load_fixture(FIXTURE_DIR / "historical_slot_bug.json")
    row = data["expected_rows"][0]
    assert row["values"]["device_ms"] == 4242
    assert "device_ms" in row["written"]
    assert SLOT_INDEX["device_ms"] == 15


def test_held_value_fixture_bpm_bit_clear_on_system_fps():
    data = load_fixture(FIXTURE_DIR / "held_value.json")
    second = data["expected_rows"][1]
    assert second["record_kind"] == 3
    assert second["values"]["bpm"] == 120.0
    assert second["values"]["system_fps"] == 30
    assert "bpm" not in second["written"]
    assert not (mask_from_names(second["written"]) & 1)


@pytest.mark.parametrize("path", fixture_paths(), ids=REQUIRED_FIXTURES)
def test_dryrun_golden(path: Path, parser_code: str):
    if not api_listening():
        pytest.skip("Serial Studio API 127.0.0.1:7777 down; dryRun not executed")

    data = load_fixture(path)
    raw = lines_to_ascii(data["lines"])
    assert raw, f"{path.stem} encoded to empty bytes"
    result = dry_run(parser_code, raw)
    assert result.get("ok") is True, f"{path.stem} dryRun not ok: {result!r}"
    got_rows = published_rows(result)
    expected = data["expected_rows"]
    assert len(got_rows) == len(expected), (
        f"{path.stem} published {len(got_rows)} rows, expected {len(expected)}. "
        f"got={got_rows!r}"
    )
    for i, (got, exp) in enumerate(zip(got_rows, expected)):
        assert_expected_row(got, exp, path.stem, i)
        if path.stem == "historical_slot_bug":
            assert float(got[15]) == pytest.approx(4242)
            assert len(got) == SCHEMA_LEN
        if path.stem == "held_value" and i == 1:
            mask = int(float(got[SLOT_INDEX["update_mask"]]))
            assert int(float(got[SLOT_INDEX["record_kind"]])) == 3
            assert not (mask & 1), (
                f"held bpm update_mask bit 0 must be 0; mask={mask} row={got}"
            )
            assert float(got[SLOT_INDEX["bpm"]]) == pytest.approx(120.0)
        if path.stem == "reboot_host_parse_seq" and i == 3:
            assert float(got[SLOT_INDEX["device_ms"]]) == pytest.approx(12)
            assert int(float(got[SLOT_INDEX["host_parse_seq"]])) == 4
