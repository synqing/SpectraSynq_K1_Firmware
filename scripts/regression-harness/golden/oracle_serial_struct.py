#!/usr/bin/env python3
"""Structural-contract oracle for FUNCTION-CALL serial command handlers.

THE KEYSTONE GATE (Phase A · Lane 2). The replay oracle (oracle_serial_replay.py)
locks BEHAVIOUR by compiling + running parse_command() on the host. That works for
GLOBAL-WRITE handlers (they mutate inline globals the host can observe). It is BLIND
to the FUNCTION-CALL families — queue/transition, smart_*, edge_*, set_mode, ... —
because those call host-STUBBED subsystems (sb_queue_*, sb_smart_director_*,
sb_edgemixer_*, ...) whose real bodies drag FS/LittleFS/FreeRTOS and cannot host
compile. Locking them via replay would freeze only the echo shell, not the real
behaviour = the blind-lock the discipline forbids.

This oracle proves a VERBATIM LIFT of such a handler is behaviour-preserving WITHOUT
running the stubbed subsystem, by the TRIZ #13 (the-other-way-round) + #22
(blessing-in-disguise) argument: for a verbatim lift, STATEMENT-IDENTITY +
DISPATCH-ROUTING-PRESERVATION is behaviour-preserving BY CONSTRUCTION. The stubbed
subsystem sees a byte-identical call at a byte-identical control-flow position, so
whatever it does is unchanged — its behaviour is irrelevant to the proof. So instead
of observing behaviour we PIN STRUCTURE:

  per registered family command, capture the TRIPLE
    (a) normalized handler body  — the exact statements, comment/indent-insensitive
    (b) reachable                — is the command still routed from parse_command()
                                   (inline, OR via a dispatcher parse_command calls)
    (c) [implicit] presence       — body == None if the command_type branch vanished

A verbatim lift moves the `else if (strcmp(command_type, "X") == 0) { BODY }` block
from serial_menu.h's parse_command() ladder into a serial_cmd_dispatch_<family>()
in serial_cmd_handlers.cpp, and replaces the inline branch with ONE
`else if (serial_cmd_dispatch_<family>(command_type, command_data)) { }` call. The
captured triple is INVARIANT across that move: the normalized BODY is byte-identical
(verbatim), and `reachable` stays true (the dispatcher is called from parse_command).
So the frozen golden REPRODUCES after extraction — that identity IS the
behaviour-preservation proof. The golden does NOT record WHERE the body lives, only
WHAT it is and THAT it is routed; the move itself is invisible to the contract, which
is the whole point.

FAULT-EVIDENCE (the Gate-Fα teeth, proven by harness_selftest.py): the MUTATIONS list
plants real regressions a botched lift would introduce — an altered statement, a
mis-routed command_type string, a changed echo, a severed dispatcher call-site — each
MUST diverge the capture. A gate that cannot fail on those is blind and worse than
none.

NON-SHIPPING. Host-only, pure SOURCE PARSE (no compile, no device). Mirrors the
oracle PUBLIC INTERFACE (NAME / capture(firmware_root=None) / MUTATIONS), registered
in harness_selftest.ORACLE_MODULES, gated by test_golden_master.py.

SCOPE LOCK (Captain, 2026-06-25): function-call families ONLY. vp_profile / vp_all and
the control-facade (sb_k1_control_facade.cpp) profile logic are a SEPARATE architectural
lane and are explicitly OUT OF SCOPE here — no family below may reference them.
"""

import json
import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Repo layout (mirrors oracle_serial_replay.py)
# ---------------------------------------------------------------------------
ROOT     = Path(__file__).resolve().parents[3]            # SpectraSynq_K1_Firmware/
FIRMWARE = ROOT / "SPECTRASYNQ_K1_FIRMWARE"

NAME = "serial_struct"

# ---------------------------------------------------------------------------
# Registered families. Each is a function-call handler group eligible for (or
# already moved by) a verbatim structural lift. `dispatcher` is the extracted
# function's name (serial_cmd_dispatch_<family>); pre-extraction it does not yet
# exist and the bodies are found inline — the contract is identical either way.
#
# To onboard a new function-call family: add an entry here, regen the golden under
# the ORIGINAL inline handlers (the LOCK commit), then extract (the EXTRACT commit)
# and confirm the golden REPRODUCES byte-for-byte. Never add a family that touches
# vp_profile/vp_all or the control-facade profile logic (SCOPE LOCK above).
# ---------------------------------------------------------------------------
FAMILIES = [
    {
        "name": "queue",
        "dispatcher": "serial_cmd_dispatch_queue",
        # The effects-queue / transition family (serial_menu.h spec §4): all ungated,
        # all calling only the host-stubbed sb_queue_* subsystem, zero facade coupling.
        "commands": [
            "queue_mode",
            "transition_style",
            "transition_dip_ms",
            "transition_xfade_ms",
            "commit_quantise",
        ],
    },
    {
        "name": "smart_director",
        "dispatcher": "serial_cmd_dispatch_smart_director",
        # Smart-director control (sb_smart_director_* config getters/setters +
        # sb_apply_smart_scene + sb_mode_selection_init); ungated, facade-free. The
        # config fns live in director/sb_smart_director.cpp (replay-oracle MODULE_CPPS);
        # the print/apply helpers are external-linkage in serial_menu.h.
        "commands": [
            "smart_assist",
            "smart_switching",
            "smart_confidence_floor",
            "smart_scene",
        ],
    },
    {
        "name": "smart_visual",
        "dispatcher": "serial_cmd_dispatch_smart_visual",
        # Visual-hooks toggle (sb_visual_hooks_* config); ungated, facade-free.
        "commands": [
            "smart_hooks",
        ],
    },
    {
        "name": "edge_mixer",
        "dispatcher": "serial_cmd_dispatch_edge_mixer",
        # Edge-mixer control (sb_edgemixer_lite_* config + sb_parse_edge_mode);
        # ungated, facade-free.
        "commands": [
            "edge_enabled",
            "edge_mode",
            "edge_strength",
        ],
    },
    {
        "name": "preset",
        "dispatcher": "serial_cmd_dispatch_preset",
        # "Set CONFIG preset" (serial_menu.h): the single "preset" command validates
        # command_data against 5 theme names, then calls set_preset() + save_config_delayed()
        # and echoes "ENABLED PRESET: <name>". Ungated, facade-free. set_preset() is an
        # external-linkage header-body fn in system/presets.h (included only by the .ino TU,
        # so the firmware links one definition; the handlers TU forward-declares it extern).
        # In the replay oracle it is a GUARANTEED-EXTERNAL driver stub (oracle_serial_replay
        # driver `void set_preset(char*) {}`), NOT a static-inline host stub — so the handlers
        # TU links free (no sb_queue_*-style -O0 link trap). save_config_delayed() is likewise
        # already a driver stub + already used by the extracted setter dispatchers.
        "commands": [
            "preset",
        ],
    },
]

# Files a function-call handler body can live in: inline in parse_command
# (serial_menu.h) pre-extraction, or in the dispatcher (serial_cmd_handlers.cpp)
# post-extraction. capture() searches both; the golden records neither (the move is
# invisible to the contract).
_MENU_REL     = ("serial", "serial_menu.h")
_HANDLERS_REL = ("serial", "serial_cmd_handlers.cpp")


# ---------------------------------------------------------------------------
# Source parsing
# ---------------------------------------------------------------------------
def _branch_regex(cmd: str) -> str:
    """Match `else if (strcmp(command_type, "<cmd>") == 0)` up to its opening brace."""
    return r'else\s+if\s*\(\s*strcmp\(\s*command_type\s*,\s*"' + re.escape(cmd) \
           + r'"\s*\)\s*==\s*0\s*\)\s*\{'


def _extract_block(source: str, cmd: str):
    """Return the brace-balanced BODY of the command_type branch, or None if absent.

    Brace-matches from the opening `{` of the `else if (strcmp(...)==0) {` branch,
    skipping braces inside string and char literals and // /* */ comments so a body
    containing `{`/`}` in a literal cannot unbalance the scan."""
    m = re.search(_branch_regex(cmd), source)
    if not m:
        return None
    i = m.end()          # first char after the opening brace
    depth = 1
    n = len(source)
    while i < n and depth:
        c = source[i]
        if c == '"' or c == "'":            # skip string / char literal
            quote = c
            i += 1
            while i < n and source[i] != quote:
                if source[i] == '\\':
                    i += 1
                i += 1
            i += 1
            continue
        if c == '/' and i + 1 < n and source[i + 1] == '/':   # line comment
            while i < n and source[i] != '\n':
                i += 1
            continue
        if c == '/' and i + 1 < n and source[i + 1] == '*':   # block comment
            i += 2
            while i + 1 < n and not (source[i] == '*' and source[i + 1] == '/'):
                i += 1
            i += 2
            continue
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
        i += 1
    if depth != 0:
        return None
    return source[m.end():i - 1]


def _normalize(body: str) -> str:
    """Comment- and indentation-insensitive token stream.

    Strips // and /* */ comments and collapses every whitespace run to one space so
    re-indentation by the lift is tolerated, while EVERY token, identifier, operator,
    string literal and numeric literal is preserved — a changed argument, echo string,
    branch or call diverges. (A literal carrying multiple consecutive spaces would have
    them collapsed; the registered families have none, and the MUTATIONS prove the
    normalization is not blind to a literal's CONTENT.)"""
    body = re.sub(r"/\*.*?\*/", "", body, flags=re.S)
    body = re.sub(r"//[^\n]*", "", body)
    body = re.sub(r"\s+", " ", body).strip()
    return body


def _routed(menu_src: str, dispatcher: str) -> bool:
    """True iff parse_command() invokes the dispatcher with the canonical arg names.

    `serial_cmd_dispatch_<x>(command_type, command_data)` (bare arg names) appears
    ONLY at the call-site; the definition/declaration carry typed parameters
    (`const char*`, `char*`), so this marker is unambiguous."""
    return f"{dispatcher}(command_type, command_data)" in menu_src


# ---------------------------------------------------------------------------
# capture() — the public oracle interface
# ---------------------------------------------------------------------------
def capture(firmware_root=None) -> str:
    """Return deterministic JSON-lines: one record per family command.

    Record = {family, cmd, body (normalized | null), reachable}. Pure source parse —
    no compile, no device. `body` is found inline (pre-extraction) or in the
    dispatcher (post-extraction); `reachable` is true inline, or true-iff-routed once
    moved to a dispatcher. Both are invariant across a verbatim lift, so the golden
    reproduces; a botched lift diverges body or reachable."""
    fw = Path(firmware_root) if firmware_root else FIRMWARE
    menu_src     = (fw.joinpath(*_MENU_REL)).read_text(encoding="utf-8")
    handlers_src = (fw.joinpath(*_HANDLERS_REL)).read_text(encoding="utf-8") \
                   if (fw.joinpath(*_HANDLERS_REL)).exists() else ""

    lines = []
    for fam in FAMILIES:
        dispatcher = fam["dispatcher"]
        for cmd in fam["commands"]:
            inline = _extract_block(menu_src, cmd)
            if inline is not None:
                body = _normalize(inline)
                reachable = True                       # inline in parse_command's ladder
            else:
                moved = _extract_block(handlers_src, cmd)
                body = _normalize(moved) if moved is not None else None
                # routed only if the body now lives in the dispatcher AND
                # parse_command actually calls that dispatcher.
                reachable = bool(moved is not None and _routed(menu_src, dispatcher))
            rec = {"family": fam["name"], "cmd": cmd, "body": body, "reachable": reachable}
            lines.append(json.dumps(rec, sort_keys=True, separators=(",", ":")))
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Mutations — the Gate-Fα teeth. Each plants a regression a botched verbatim lift
# would introduce and MUST diverge the capture. Applied by harness_selftest.py to a
# firmware COPY (rglob, count=1) and re-captured. The anchors are unique whether the
# handler is still inline (Phase A) or already in the dispatcher (Phase B) — the
# `else if (strcmp(command_type, "X")...)` block text is identical in both homes.
# ---------------------------------------------------------------------------
MUTATIONS = [
    # 1. ALTER A STATEMENT: flip the queue_mode subsystem call argument true->false.
    #    The normalized body of "queue_mode" diverges. Channel (a) statement-identity.
    (
        r'(else if \(strcmp\(command_type, "queue_mode"\) == 0\) \{\s*if \(strcmp\(command_data, "on"\) == 0\) \{\s*)sb_queue_set_mode_enabled\(true\);',
        r'\1sb_queue_set_mode_enabled(false);',
        "queue_mode_arg_true_to_false (statement-identity divergence)",
    ),
    # 2. MIS-ROUTE A COMMAND_TYPE: rename commit_quantise -> commit_quantize in its
    #    strcmp. capture() can no longer find "commit_quantise" -> body becomes null +
    #    reachable false. Exactly the routing/identity regression. Channel (b)/(c).
    (
        r'strcmp\(command_type, "commit_quantise"\)',
        r'strcmp(command_type, "commit_quantize")',
        "commit_quantise_command_type_renamed (routing/identity divergence)",
    ),
    # 3. CHANGE AN ECHO STRING: transition_style "dip" echo text mutated. The
    #    normalized body of "transition_style" diverges on the literal's CONTENT,
    #    proving normalization is not blind to string literals. Channel (a).
    (
        r'USBSerial\.println\("TRANSITION_STYLE: dip"\);',
        r'USBSerial.println("TRANSITION_STYLE: DIP");',
        "transition_style_echo_text_changed (statement/echo divergence)",
    ),
    # 4. SEVER THE ROUTING (added in the EXTRACT commit, once the dispatcher call-site
    #    exists): rename the parse_command call so capture()'s `_routed` check no longer
    #    finds it. The queue bodies still live in the dispatcher, but every queue
    #    command flips reachable:true->false -> divergence. Proves the `reachable`
    #    field is not blind. The bare-arg form `(command_type, command_data)` matches
    #    ONLY the call-site (the def/decl carry typed params), so the rglob lands there.
    (
        r"serial_cmd_dispatch_queue\(command_type, command_data\)",
        r"serial_cmd_dispatch_queue_SEVERED(command_type, command_data)",
        "queue_dispatcher_call_site_severed (routing/reachable divergence)",
    ),
    # ---- smart_director / smart_visual / edge_mixer body + routing-by-name teeth ----
    # 5. smart_confidence_floor clamp 1.0->0.5: alters the smart_director body. (a)
    (
        r"config\.confidence_floor = constrain\(value, 0\.0f, 1\.0f\);",
        r"config.confidence_floor = constrain(value, 0.0f, 0.5f);",
        "smart_confidence_floor_clamp_1.0_to_0.5 (statement-identity divergence)",
    ),
    # 6. smart_assist command_type rename: capture can't find "smart_assist" -> body
    #    null. Routing/identity (b)/(c).
    (
        r'strcmp\(command_type, "smart_assist"\)',
        r'strcmp(command_type, "smart_assist_MUT")',
        "smart_assist_command_type_renamed (routing/identity divergence)",
    ),
    # 7. smart_hooks enabled flip value->false: alters the smart_visual body. Anchored
    #    on the unique SBVisualHookConfig fetch. (a)
    (
        r"(SBVisualHookConfig config = sb_visual_hooks_config\(\);\s*)config\.enabled = value;",
        r"\1config.enabled = false;",
        "smart_hooks_enabled_value_to_false (statement-identity divergence)",
    ),
    # 8. edge_strength clamp 1.0->0.5: alters the edge_mixer body. (a)
    (
        r"config\.strength = constrain\(value, 0\.0f, 1\.0f\);",
        r"config.strength = constrain(value, 0.0f, 0.5f);",
        "edge_strength_clamp_1.0_to_0.5 (statement-identity divergence)",
    ),
    # 9. edge_mode command_type rename: capture can't find "edge_mode" -> body null.
    #    Routing/identity (b)/(c).
    (
        r'strcmp\(command_type, "edge_mode"\)',
        r'strcmp(command_type, "edge_mode_MUT")',
        "edge_mode_command_type_renamed (routing/identity divergence)",
    ),
    # ---- routing-sever teeth (added with the EXTRACT; call-sites now exist) ----
    # 10-12. sever each dispatcher call in parse_command -> that family's commands flip
    #        reachable:true->false. Bare-arg form matches ONLY the call-site.
    (
        r"serial_cmd_dispatch_smart_director\(command_type, command_data\)",
        r"serial_cmd_dispatch_smart_director_SEVERED(command_type, command_data)",
        "smart_director_call_site_severed (routing/reachable divergence)",
    ),
    (
        r"serial_cmd_dispatch_smart_visual\(command_type, command_data\)",
        r"serial_cmd_dispatch_smart_visual_SEVERED(command_type, command_data)",
        "smart_visual_call_site_severed (routing/reachable divergence)",
    ),
    (
        r"serial_cmd_dispatch_edge_mixer\(command_type, command_data\)",
        r"serial_cmd_dispatch_edge_mixer_SEVERED(command_type, command_data)",
        "edge_mixer_call_site_severed (routing/reachable divergence)",
    ),
    # ---- preset body + routing-by-name teeth (family added 2026-06-25) ----
    # 13. ALTER THE ECHO: "ENABLED PRESET: " -> "ENABLED PRESET! ". The normalized body
    #     of "preset" diverges on the string literal's CONTENT (proves normalization is
    #     not blind to the echo). Channel (a) statement-identity. Anchor is unique and
    #     home-agnostic (inline serial_menu.h pre-extract, dispatcher post-extract).
    (
        r'USBSerial\.print\("ENABLED PRESET: "\);',
        r'USBSerial.print("ENABLED PRESET! ");',
        "preset_echo_text_changed (statement/echo divergence)",
    ),
    # 14. MIS-ROUTE THE COMMAND_TYPE: rename the "preset" strcmp -> "preset_MUT".
    #     capture() can no longer find the branch -> body null + reachable false.
    #     Channel (b)/(c) routing/identity. Exact closing `"` => matches only "preset".
    (
        r'strcmp\(command_type, "preset"\)',
        r'strcmp(command_type, "preset_MUT")',
        "preset_command_type_renamed (routing/identity divergence)",
    ),
]


# ---------------------------------------------------------------------------
# Standalone regen / self-check (mirrors oracle_serial_replay.py __main__).
# Regenerate the golden:  python3 oracle_serial_struct.py > tests/golden/serial_struct.golden.jsonl
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse
    import shutil
    import sys
    import tempfile

    parser = argparse.ArgumentParser(description="structural-contract oracle for function-call serial handlers.")
    parser.add_argument("--verify-mutations", action="store_true")
    args = parser.parse_args()

    baseline = capture()
    print(baseline, end="")

    if capture() != baseline:
        print("DETERMINISM FAILURE: two runs differ.", file=sys.stderr)
        sys.exit(1)
    print(f"\n# golden_record_count={len(baseline.strip().splitlines())}", file=sys.stderr)
    print("# determinism=OK (two runs byte-identical)", file=sys.stderr)

    if args.verify_mutations:
        print("\n# --- Mutation verification ---", file=sys.stderr)
        all_caught = True
        for pattern, replacement, desc in MUTATIONS:
            with tempfile.TemporaryDirectory() as td:
                dst = Path(td) / "SPECTRASYNQ_K1_FIRMWARE"
                shutil.copytree(FIRMWARE, dst)
                target = None
                for f in dst.rglob("*"):
                    if f.suffix in (".cpp", ".h") and f.is_file():
                        txt = f.read_text(encoding="utf-8", errors="ignore")
                        if re.search(pattern, txt):
                            f.write_text(re.sub(pattern, replacement, txt, count=1), encoding="utf-8")
                            target = f
                            break
                caught = target is not None and capture(firmware_root=dst) != baseline
                all_caught = all_caught and caught
                print(f"#  [{'CAUGHT' if caught else 'MISSED'}] {desc}", file=sys.stderr)
        print("# all mutations caught." if all_caught
              else "# WARNING: a mutation was not caught.", file=sys.stderr)
        sys.exit(0 if all_caught else 1)
