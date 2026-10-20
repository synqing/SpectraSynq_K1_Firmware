"""Host tests for the emulator replay player (tools/esp_emulator/player.py).

The player must only animate accepted captures, carry the native values and
the report's display projection unchanged, and never attach audio whose bytes
differ from the PCM the case recorded.
"""

from __future__ import annotations

import json
import re
import struct
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "esp_emulator"))
sys.path.insert(0, str(ROOT / "tests"))

import emu_capture as ec  # noqa: E402
import player  # noqa: E402
from test_esp_emulator_acceptance import make_expect, make_uart  # noqa: E402


def _run(tmp_path: Path, status: str = "PASS", pcm: dict | None = None) -> Path:
    exp = make_expect(commands=[{"hop": 2, "text": "photons=0.25", "expect": "applied"}])
    (tmp_path / "c").mkdir()
    (tmp_path / "c" / "uart.txt").write_text(make_uart(exp))
    (tmp_path / "result.json").write_text(json.dumps({
        "invocation_id": "inv", "overall": "SOFTWARE COMPLETE", "source": {"head": "abc"},
        "cases": {"c": {"status": status, "purpose": "synthetic", "pcm": pcm or {},
                        "requested": {"capture": {"start_hop": 0, "end_hop": 8, "every": 1},
                                      "commands": exp.commands}}}}))
    return tmp_path


def _data(html: str) -> dict:
    return json.loads(re.search(r"const DATA = (\{.*?\});\nconst \$", html, re.S).group(1))


def test_player_carries_native_values_and_projection(tmp_path):
    run = _run(tmp_path)
    d = _data(player.build(run, ["c"]))
    c = d["cases"][0]
    cap = ec.decode((run / "c" / "uart.txt").read_text())
    assert c["frames"] == len(cap.frames) == 8 and c["hops"] == list(range(8))
    import base64
    native = base64.b64decode(c["native"])
    rgb8 = base64.b64decode(c["rgb8"])
    r16, g16, b16 = ec.wire_to_rgb16(cap.frames[3].B)[17]
    k = (3 * 2 + 1) * player.PX + 17
    assert struct.unpack_from("<HHH", native, k * 6) == (r16, g16, b16)
    assert tuple(rgb8[k * 3:k * 3 + 3]) == (player.proj(r16), player.proj(g16), player.proj(b16))
    assert c["commands"] == [{"hop": 2, "text": "photons=0.25", "via": "scheduled"}]
    assert c["audio"] is None and "no PCM identity" in c["audio_note"]


def test_player_refuses_a_case_that_was_not_accepted(tmp_path):
    with pytest.raises(player.PlayerError, match="only accepted captures"):
        player.build(_run(tmp_path, status="FAIL"), ["c"])


def test_player_drops_audio_whose_bytes_differ_from_the_record(tmp_path, monkeypatch):
    import run as runner
    run = _run(tmp_path, pcm={"id": "smoke", "sha256": "0" * 64})
    (run / "scenario.json").write_text((ROOT / "tools/esp_emulator/s3_music_regression.json").read_text())
    monkeypatch.setattr(runner, "load_asset", lambda sc, aid, cache, wd: (b"\x01\x00" * 768, {}))
    c = _data(player.build(run, ["c"]))["cases"][0]
    assert c["audio"] is None and "!= recorded" in c["audio_note"]
    import hashlib
    good = hashlib.sha256(b"\x01\x00" * 768).hexdigest()
    (tmp_path / "ok").mkdir()
    run2 = _run(tmp_path / "ok", pcm={"id": "smoke", "sha256": good})
    (run2 / "scenario.json").write_text((run / "scenario.json").read_text())
    c2 = _data(player.build(run2, ["c"]))["cases"][0]
    assert c2["audio"] and "exact case PCM" in c2["audio_note"]
