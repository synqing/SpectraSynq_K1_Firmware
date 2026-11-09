#!/usr/bin/env python3
"""Classify loss_exposure.cpp events (one JSON line per dirty event) into outcome classes.

Hotkey effects from serial_menu.cpp serial_handle_hotkey() at 407fdf6f (== ed0aa984), lines 1998-2260;
helper side effects verified in source (see B-P1-contract.md, "Loss exposure").
usage: analyze_loss.py EVENTS.jsonl FW_SERIAL_DIR OUT.json
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

PERSIST = {  # key -> what persists
    "S": "show state save (k1_show_state_save: LittleFS + save_config)",
    **{k: "preset slot save (k1_preset_slot_save, LittleFS)" for k in "!@#$%^&*()"},
    **{k: "save_config_delayed (SQUARE_ITER / SENSITIVITY)" for k in "qQwW"},
    **{k: "save_config_delayed via serial_adjust_target_float (primary target)" for k in "iIoOpjJkKlL"},
    "/": "save_config_delayed (palette mode toggle)",
    **{k: "preset slot load -> apply_preset_live -> save_config_delayed (primary)" for k in "1234567890"},
}
MODE = set("[],.\\U")           # queue / mode / palette change (persistence not verified)
RUNTIME = set("eErRtTgG=-+_uym ")  # visible, RAM-only
STREAMS = set("asdf")           # serial stream toggles
INFO = set("h;")
IMMEDIATE = set("gGuym-=_+ hN;Y[]0123456789!@#$%^&*()\\UiIoOpPjJkKlLqQwWeErRtT,./asSdf") | set("zZv")


def command_names(serial_dir: Path):
    names = set()
    for f in ("serial_cmd_table.def", "serial_typed_cmd_table.def"):
        for m in re.finditer(r'"([^"\\]{1,40})"', (serial_dir / f).read_text(errors="replace")):
            names.add(m.group(1))
    menu = (serial_dir / "serial_menu.cpp").read_text(errors="replace")
    for m in re.finditer(r'strcmp\((?:command_type|command_buf)\s*,\s*"([^"]+)"\)', menu):
        names.add(m.group(1))
    return names


def classify_cmd(raw: bytes, names) -> str:
    cstr = raw.split(b"\x00", 1)[0]
    name = re.split(rb"[=]", cstr, maxsplit=1)[0][:32]
    head = cstr.split(b" ", 1)[0]
    try:
        n = name.decode("ascii")
        h = head.decode("ascii")
    except UnicodeDecodeError:
        return "bad_command"
    if n in names or (b" " in cstr and h in names):
        return f"EXECUTES:{n if n in names else h}"
    return "bad_command"


def main():
    ev_path, serial_dir, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    names = command_names(serial_dir)
    cls = Counter()
    keys = Counter()
    cmd_cls = Counter()
    worst = {}
    summary = None
    n_events = 0
    for line in ev_path.open():
        e = json.loads(line)
        if "summary" in e:
            summary = e["summary"]
            continue
        n_events += 1
        seq = [chr(b) for b, _ in e["leaks"]]
        act = [ch for ch in seq if ch in IMMEDIATE]
        tags = set()
        if "N" in act:
            first_n = act.index("N")
            tags.add("CAL_QUEUED" if "Y" in act[first_n + 1:] else "N_arm_only")
        elif "Y" in act:
            tags.add("Y_without_N")
        for ch in act:
            keys[ch] += 1
            if ch in PERSIST:
                tags.add("PERSIST")
            elif ch in MODE:
                tags.add("mode_palette_change")
            elif ch in RUNTIME:
                tags.add("runtime_visual_change")
            elif ch in STREAMS:
                tags.add("serial_stream_toggle")
            elif ch in INFO:
                tags.add("info_print")
        if e["enters"]:
            tags.add("command_mode")
        for h in e["cmds"]:
            c = classify_cmd(bytes.fromhex(h), names)
            cmd_cls[c] += 1
            if c.startswith("EXECUTES"):
                tags.add("COMMAND_EXECUTES")
        if e["pending"]:
            tags.add("left_in_command_mode")
        if e["garbage"]:
            tags.add("garbage_frame_accepted")
        if not act and not e["enters"] and not e["garbage"]:
            tags.add("inert_bytes_only")
        for t in tags:
            cls[t] += 1
        score = (("CAL_QUEUED" in tags) * 1000 + ("COMMAND_EXECUTES" in tags) * 500 +
                 ("PERSIST" in tags) * 100 + len(act))
        for t in tags:
            if t not in worst or score > worst[t]["score"]:
                worst[t] = {"score": score, "k": e["k"], "i": e["i"], "keys": "".join(act),
                            "commands": len(e["cmds"]), "packets_to_resync": e["packets"]}
    by_i = Counter()
    for line in ev_path.open():
        e = json.loads(line)
        if "summary" in e:
            continue
        act = [chr(b) for b, _ in e["leaks"] if chr(b) in IMMEDIATE]
        if any(ch in PERSIST for ch in act) or ("N" in act and "Y" in act[act.index("N") + 1:]):
            by_i[e["i"]] += 1
    res = {"summary": summary, "dirty_events_classified": n_events, "outcome_counts": dict(cls),
           "hotkey_byte_counts": dict(keys.most_common()), "command_line_classes": dict(cmd_cls),
           "critical_or_persist_events_by_truncation_i": dict(sorted(by_i.items())),
           "worst_by_class": worst, "command_names_considered": len(names)}
    out.write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({k: res[k] for k in ("summary", "outcome_counts", "command_line_classes")}, indent=1))


if __name__ == "__main__":
    main()
