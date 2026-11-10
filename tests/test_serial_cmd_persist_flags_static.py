"""Every serial command row's CMD_PERSISTS flag must match what its handler does.

Origin (2026-11-10): ``set_mode`` in ``serial_typed_cmd_table.def`` declared
flags ``0`` while its handler (``serial_cmd_dispatch_mode``) calls
``save_config_delayed()``, so ``scripts/regression-harness/k1_serial_safety.py``
classified a flash-writing command as safe read-only. The audit that fixed the
tables also found the opposite error: 32 rows claimed CMD_PERSISTS while their
handlers only change RAM. Audit record:
``docs/forensics/runtime-evidence/20261110-fe-show-fixes/serial-cmd-persist-audit.md``.

How the check works (static, host-only, no build):

1. Parse every row of both X-macro tables, ``#if`` blocks included.
2. Index every function body in ``SPECTRASYNQ_K1_FIRMWARE`` (comments stripped).
3. For each row, start at its handler. A pure forwarding wrapper
   (``{ return f(...); }``) is followed for free. In a function whose first
   parameter is ``command_type``, only the code that runs for this name is kept:
   the ``strcmp(command_type, "<name>") == 0`` branches if there are any,
   otherwise the body minus the branches for other names.
4. Follow calls to firmware functions up to ``CALL_DEPTH`` levels and search the
   kept text for a persistence call (``PERSIST_RE``).
5. Assert ``flag == found``. Rows whose persistence the static walk cannot see
   (writes scheduled through the Core-1 frame tick or the serial byte stream, an
   I2C NVM write, or a call that is guarded off by state the harness forces) are
   in ``HAND_VERIFIED`` with the evidence that decided them.

A row that is in neither the automated set (its handler is indexed) nor
``HAND_VERIFIED`` fails the test, so a new row cannot slip through unchecked.
"""

from __future__ import annotations

import importlib.util
import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / "SPECTRASYNQ_K1_FIRMWARE"
TYPED_DEF = FW / "serial" / "serial_typed_cmd_table.def"
BARE_DEF = FW / "serial" / "serial_cmd_table.def"
SAFETY_MODULE = ROOT / "scripts" / "regression-harness" / "k1_serial_safety.py"

#: Call levels followed below the handler's dispatcher ("one or two call levels").
CALL_DEPTH = 2

#: Calls that write, delete or schedule a write of persistent storage.
PERSIST_RE = re.compile(
    r"\b(?:save_config|save_config_delayed|k1_show_state_save|slots_write_file"
    r"|k1_preset_slot_save|k1_look_fs_save|k1_persist_request_push"
    r"|nvs_set_\w+|nvs_commit|esp_partition_write|esp_partition_erase_range)\s*\("
    r"|\bLittleFS\s*\.\s*(?:remove|rename|format)\s*\("
    r"|\bFILE_WRITE\b|\bFILE_APPEND\b|\bPreferences\b"
)

#: Rows decided by reading the code, because the static call walk cannot see
#: the persistence path (or sees one that cannot run). name -> (persists, evidence).
#: Line numbers are as of 2026-11-10; serial_menu.cpp is cited by function name
#: because it is being edited in parallel.
HAND_VERIFIED: dict[str, tuple[bool, str]] = {
    "commit": (
        True,
        "serial/serial_menu.cpp cmd_queue_commit() -> serial_queue_commit() -> "
        "k1_queue_request_commit(); control/k1_effect_queue.cpp:597-602 the Core-1 "
        "frame tick starts the transition, :242 advance_transition() -> "
        "apply_preset_live() -> :139 save_config_delayed() for the primary channel. "
        "Deferred through the frame tick, so the call walk cannot reach it.",
    ),
    "slot_load": (
        True,
        "serial/serial_typed_dispatch.cpp:933 serial_queue_slot_load() -> "
        "serial/serial_menu.cpp serial_queue_slot_load() -> "
        "k1_queue_request_commit(false, ...) -> same frame-tick path -> "
        "control/k1_effect_queue.cpp:139 save_config_delayed(). Persists only for "
        "the primary channel with queue mode off (state-dependent; flagged "
        "conservatively).",
    ),
    "look_load": (
        True,
        "serial/serial_typed_dispatch.cpp:1199 'look_load=N,bytes' arms "
        "k1_look_rx_arm(); check_serial() in serial/serial_menu.cpp feeds the "
        "following bytes to k1_look_rx_push() (visual/k1_look_file.h:344), which "
        "calls k1_look_fs_save() at :353 (LittleFS FILE_WRITE at :285). "
        "'look_load=N' alone only reads (argument-dependent; flagged conservatively).",
    ),
    "pd_nvm_write": (
        True,
        "system/k1_fe_board.cpp:752 k1_fe_pd_nvm_write() -> :300 pd_nvm_write_all() "
        "(:219) erases and programs the STUSB4500 NVM over I2C (Wire, not LittleFS). "
        "K1_FE_BOARD_GX builds print 'unavailable' instead (build-dependent; "
        "flagged conservatively).",
    ),
    "gdft_agc_probe": (
        False,
        "serial/serial_cmd_handlers.cpp gdft_run_agc_probe() -> process_GDFT(). The "
        "only save_config() reachable there (audio/k1_gdft_core.cpp:422) sits under "
        "'if (noise_complete == false)' (:350); diag/gdft_harness.h:465 forces "
        "noise_complete = true for the probe and restores it afterwards.",
    ),
}

_TYPED_ROW = re.compile(
    r'^\s*SERIAL_TYPED_CMD\(\s*"([^"]+)"\s*,\s*(\w+)\s*,\s*(\w+)\s*,\s*([^)]*)\)', re.M
)
_BARE_ROW = re.compile(
    r'^\s*SERIAL_CMD\(\s*"([^"]+)"\s*,\s*[^,]+,\s*(\w+)\s*,\s*(\w+)\s*,\s*([^,]*),', re.M
)
_FUNC_DEF = re.compile(
    r"^[A-Za-z_][\w:<>\*&\s]*?[\s\*&](\w+)\s*\(([^;{}]*?)\)\s*(?:const\s*)?\{", re.M
)
_CALL = re.compile(r"(?<![\.\w>])(\w+)\s*\(")
_FORWARDER = re.compile(r"\{\s*return\s+(\w+)\s*\([^;]*\)\s*;\s*\}")
_KEYWORDS = {"if", "for", "while", "switch", "return", "sizeof", "else", "catch",
             "do", "defined"}


# ---------------------------------------------------------------------------
# Source handling
# ---------------------------------------------------------------------------

def _strip_comments(text: str) -> str:
    """Blank out // and /* */ comments; keep string literals and line numbers."""
    out = []
    i, n = 0, len(text)
    while i < n:
        if text.startswith("//", i):
            j = text.find("\n", i)
            j = n if j < 0 else j
            out.append(" " * (j - i))
            i = j
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
            out.append(re.sub(r"[^\n]", " ", text[i:j]))
            i = j
        elif text[i] in "\"'":
            quote, j = text[i], i + 1
            while j < n and text[j] != quote and text[j] != "\n":
                j += 2 if text[j] == "\\" else 1
            out.append(text[i:j + 1])
            i = j + 1
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


def _mask_literals(text: str) -> str:
    """Same length, string/char literal contents blanked (for brace matching)."""
    return re.sub(
        r'"(?:\\.|[^"\\\n])*"|\'(?:\\.|[^\'\\\n])*\'',
        lambda m: m.group()[0] + " " * (len(m.group()) - 2) + m.group()[0],
        text,
    )


def _match_brace(masked: str, open_idx: int) -> int:
    depth = 0
    for k in range(open_idx, len(masked)):
        if masked[k] == "{":
            depth += 1
        elif masked[k] == "}":
            depth -= 1
            if depth == 0:
                return k
    return len(masked) - 1


@lru_cache(maxsize=1)
def function_index() -> dict:
    """name -> list of {path, line, body, masked, first_param} for every definition."""
    index: dict = {}
    for path in sorted(FW.rglob("*")):
        if path.suffix not in (".cpp", ".h", ".hpp", ".ino") or "_scratch" in path.parts:
            continue
        text = _strip_comments(path.read_text(encoding="utf-8", errors="replace"))
        masked = _mask_literals(text)
        for m in _FUNC_DEF.finditer(masked):
            name = m.group(1)
            if name in _KEYWORDS:
                continue
            p0 = re.match(r"\s*(?:const\s+)?[\w:]+\s*[\*&]?\s*(\w+)", text[m.start(2):m.end(2)])
            open_idx = m.end() - 1
            close_idx = _match_brace(masked, open_idx)
            index.setdefault(name, []).append({
                "path": path,
                "line": text.count("\n", 0, m.start()) + 1,
                "body": text[open_idx:close_idx + 1],
                "masked": masked[open_idx:close_idx + 1],
                "first_param": p0.group(1) if p0 else None,
            })
    return index


def parse_rows(typed_text: str, bare_text: str) -> list[dict]:
    """Every row of both tables (``#if`` blocks included)."""
    rows = []
    for table, text, rx in (("typed", typed_text, _TYPED_ROW), ("bare", bare_text, _BARE_ROW)):
        for m in rx.finditer(text):
            rows.append({
                "table": table,
                "name": m.group(1),
                "handler": m.group(2),
                "line": text.count("\n", 0, m.start()) + 1,
                "persists_flag": "CMD_PERSISTS" in m.group(4),
            })
    return rows


def _code_for_name(fn: dict, name: str) -> str:
    """The part of ``fn`` that runs for command ``name``."""
    body = fn["body"]
    if fn["first_param"] != "command_type":
        return body
    blocks = []
    for m in re.finditer(r'strcmp\(\s*command_type\s*,\s*"([^"]+)"\s*\)\s*==\s*0\s*\)\s*\{', body):
        open_idx = m.end() - 1
        blocks.append((m.group(1), open_idx, _match_brace(fn["masked"], open_idx) + 1))
    if not blocks:
        return body
    mine = [body[a:b] for label, a, b in blocks if label == name]
    if mine:
        return "\n".join(mine)
    kept, pos = [], 0
    for _label, a, b in sorted(blocks, key=lambda blk: blk[1]):
        if a < pos:
            continue
        kept.append(body[pos:a])
        pos = b
    kept.append(body[pos:])
    return "".join(kept)


def persistence_hits(name: str, handler: str, index: dict, depth: int = CALL_DEPTH) -> list:
    """(function, matched call) pairs for persistence reachable from the row."""
    seen: set = set()
    while handler in index and len(index[handler]) == 1:
        fwd = _FORWARDER.fullmatch(index[handler][0]["body"].strip())
        if not fwd:
            break
        seen.add(handler)
        handler = fwd.group(1)
    hits, frontier = [], [handler]
    for _level in range(depth + 1):
        following = []
        for func in frontier:
            if func in seen or func not in index:
                continue
            seen.add(func)
            for fn in index[func]:
                code = _code_for_name(fn, name)
                hits.extend((func, m.group(0)) for m in PERSIST_RE.finditer(code))
                for call in _CALL.finditer(_mask_literals(code)):
                    callee = call.group(1)
                    if callee in index and callee not in seen and callee not in _KEYWORDS:
                        following.append(callee)
        frontier = following
    return hits


def flag_mismatches(typed_text: str, bare_text: str, index: dict) -> list[str]:
    """One message per row whose CMD_PERSISTS flag disagrees with its handler."""
    problems = []
    for row in parse_rows(typed_text, bare_text):
        where = f"{row['table']} .def line {row['line']} {row['name']!r}"
        if row["name"] in HAND_VERIFIED:
            expected, why = HAND_VERIFIED[row["name"]]
        elif row["handler"] in index:
            hits = persistence_hits(row["name"], row["handler"], index)
            expected = bool(hits)
            why = ", ".join(sorted({f"{f}: {c.strip()}" for f, c in hits})) or "no persistence call reached"
        else:
            problems.append(
                f"{where}: handler {row['handler']} not found in firmware source and the "
                "row is not in HAND_VERIFIED; resolve it or hand-verify it"
            )
            continue
        if row["persists_flag"] != expected:
            problems.append(
                f"{where}: CMD_PERSISTS={'set' if row['persists_flag'] else 'absent'} but the "
                f"handler path {'persists' if expected else 'does not persist'} ({why})"
            )
    return problems


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_every_row_persist_flag_matches_its_handler():
    problems = flag_mismatches(
        TYPED_DEF.read_text(encoding="utf-8"),
        BARE_DEF.read_text(encoding="utf-8"),
        function_index(),
    )
    assert not problems, "CMD_PERSISTS drift:\n  " + "\n  ".join(problems)


def test_hand_verified_rows_all_exist():
    names = {r["name"] for r in parse_rows(TYPED_DEF.read_text(encoding="utf-8"),
                                           BARE_DEF.read_text(encoding="utf-8"))}
    stale = sorted(set(HAND_VERIFIED) - names)
    assert not stale, f"HAND_VERIFIED names no longer in either .def: {stale}"


def test_set_mode_handler_is_seen_to_persist():
    """The originating defect: the walk must find set_mode's save_config_delayed()."""
    hits = persistence_hits("set_mode", "serial_typed_wrap_mode", function_index())
    assert any("save_config_delayed" in call for _f, call in hits), hits
    # ...and secondary_mode, the other branch of the same dispatcher, must not.
    assert not persistence_hits("secondary_mode", "serial_typed_wrap_mode", function_index())


def test_authored_status_resolves_automatically_and_does_not_persist():
    """authored_status (bare row, 2026-11-10) only prints counters."""
    index = function_index()
    assert "authored_status" not in HAND_VERIFIED
    assert "cmd_authored_status" in index
    assert not persistence_hits("authored_status", "cmd_authored_status", index)


def test_safety_module_persisting_set_matches_audited_tables():
    """k1_serial_safety.PERSISTING_COMMANDS is the corrected CMD_PERSISTS set."""
    spec = importlib.util.spec_from_file_location("k1_serial_safety", SAFETY_MODULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    flagged = {r["name"] for r in parse_rows(TYPED_DEF.read_text(encoding="utf-8"),
                                             BARE_DEF.read_text(encoding="utf-8"))
               if r["persists_flag"]}
    assert set(module.PERSISTING_COMMANDS) == flagged
    assert "set_mode" not in module.SAFE_READONLY_COMMANDS
