"""Stage F (Modernes C++ next phase, 10 Nov 2026): oversized serial fields and
lines are rejected whole — no prefix executes, no suffix becomes a hotkey, no
commit/save/reboot — and the next valid line works.

Two real production paths, each driven directly:
* parse_command() (serial_menu.cpp + serial_cmd_handlers.cpp) through the
  existing golden serial oracle, which records CONFIG deltas, save/reboot flags
  and bad_command;
* the byte receiver audio/k1_prsm_rx.cpp, which turns bytes into hotkey /
  command-line / frame events for check_serial().
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "regression-harness" / "golden"))
import oracle_serial_replay as oracle  # noqa: E402

FW = ROOT / "SPECTRASYNQ_K1_FIRMWARE"

NOTE_OFFSET_LONG = "note_offset=" + "0" * 93 + "12"      # value 95 chars
SATURATION_LONG = "saturation=0." + "0" * 91 + "junk"   # value 97 chars
VALUE_AT_LIMIT = "photons=0." + "0" * 90 + "5"           # value exactly 93 chars
VALUE_OVER_LIMIT = "photons=0." + "0" * 91 + "5"         # 94 chars
NAME_OVER_LIMIT = "x" * 32 + "=1"


@pytest.fixture(scope="module")
def replay():
    corpus = [NOTE_OFFSET_LONG, SATURATION_LONG, VALUE_OVER_LIMIT, NAME_OVER_LIMIT,
              VALUE_AT_LIMIT, "saturation=0.5"]
    saved = oracle.CORPUS
    oracle.CORPUS = corpus
    try:
        out = oracle.capture()
    finally:
        oracle.CORPUS = saved
    rows = [json.loads(line) for line in out.splitlines() if line.strip()]
    assert [r["cmd"] for r in rows] == corpus
    return {r["cmd"]: r for r in rows}


@pytest.mark.parametrize("cmd", [NOTE_OFFSET_LONG, SATURATION_LONG, VALUE_OVER_LIMIT, NAME_OVER_LIMIT])
def test_oversized_field_rejected_without_commit_save_or_reboot(replay, cmd):
    row = replay[cmd]
    assert row["bad_command"] is True, row
    assert row["config_delta"] == {}, row
    assert not row["save_config"] and not row["save_config_delayed"] and not row["reboot"], row


def test_field_at_limit_and_next_valid_command_still_commit(replay):
    at = replay[VALUE_AT_LIMIT]
    assert at["bad_command"] is False and "PHOTONS" in at["config_delta"], at
    ok = replay["saturation=0.5"]
    assert ok["bad_command"] is False and ok["config_delta"].get("SATURATION") == 0.5, ok


RX_DRIVER = r"""
#include "k1_prsm_rx.h"
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>
struct Out { std::vector<std::string> cmds; std::string hotkeys; int sessions = 0; };
static void feed(k1_prsm_rx_t* rx, const std::string& bytes, uint32_t& t, Out& o, size_t chunk) {
  for (size_t i = 0; i < bytes.size(); i++) {
    k1_prsm_rx_event_t ev;
    k1_prsm_rx_push(rx, (uint8_t)bytes[i], t, &ev);
    if (ev.kind == K1_PRSM_RX_COMMAND) o.cmds.push_back(ev.line);
    if (ev.kind == K1_PRSM_RX_HOTKEY) o.hotkeys += (char)ev.byte;
    if ((i + 1) % chunk == 0) { k1_prsm_rx_burst_end(rx, &ev); t += 1; }
  }
  k1_prsm_rx_event_t ev; k1_prsm_rx_burst_end(rx, &ev);
  o.sessions = rx->binary_session ? 1 : 0;
}
#define CHECK(c, t) do { if (!(c)) { std::printf("FAIL %s line %d\n", t, __LINE__); return 1; } } while (0)
int main() {
  const std::string max_line = ":" + std::string(K1_PRSM_RX_CMD_MAX - 1, 'a');   // 127 text chars: fits
  const std::string long_line = ":" + std::string(130, '0') + "mnSRP";          // over, hotkey-like tail
  for (size_t chunk : {size_t(1), size_t(7), size_t(64), size_t(4096)}) {
    for (const char* eol : {"\n", "\r\n"}) {
      k1_prsm_rx_t rx; k1_prsm_rx_reset(&rx);
      uint32_t t = 1000; Out o;
      feed(&rx, long_line + eol + ":chroma=0.5" + eol, t, o, chunk);
      CHECK(o.hotkeys.empty(), "no_hotkeys_from_suffix");
      CHECK(o.cmds.size() == 1 && o.cmds[0] == "chroma=0.5", "only_next_line_runs");
      CHECK(o.sessions == 0, "stays_interactive");
      Out o2;
      feed(&rx, max_line.substr(0, 127) + eol, t, o2, chunk);   // 126 chars after ':' fit
      CHECK(o2.cmds.size() == 1 && o2.cmds[0].size() == 126, "at_limit_line_runs");
    }
  }
  std::printf("ok\n");
  return 0;
}
"""


def test_receiver_discards_overlong_line_and_accepts_next():
    cxx = shutil.which("clang++") or shutil.which("g++")
    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / "rx.cpp"
        src.write_text(RX_DRIVER, encoding="utf-8")
        exe = Path(td) / "rx"
        r = subprocess.run([cxx, "-std=c++17", "-fsanitize=address,undefined", "-I", str(FW / "audio"),
                            str(src), str(FW / "audio" / "k1_prsm_rx.cpp"), str(FW / "audio" / "k1_prsm.cpp"),
                            "-o", str(exe)], text=True, capture_output=True)
        assert r.returncode == 0, r.stderr[-3000:]
        run = subprocess.run([str(exe)], text=True, capture_output=True, timeout=60)
    assert run.returncode == 0 and run.stdout.startswith("ok"), run.stdout + run.stderr
