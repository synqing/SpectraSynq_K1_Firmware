#!/usr/bin/env python3
"""Structural-contract oracle for FUNCTION-CALL serial command handlers.

THE KEYSTONE GATE (Phase A · Lane 2). The replay oracle (oracle_serial_replay.py)
locks BEHAVIOUR by compiling + running parse_command() on the host. That works for
GLOBAL-WRITE handlers (they mutate inline globals the host can observe). It is BLIND
to the FUNCTION-CALL families — queue/transition, smart_*, edge_*, set_mode, ... —
because those call host-STUBBED subsystems (k1_queue_*, k1_smart_director_*,
k1_edgemixer_*, ...) whose real bodies drag FS/LittleFS/FreeRTOS and cannot host
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
the control-facade (k1_control_facade.cpp) profile logic are a SEPARATE architectural
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
        # all calling only the host-stubbed k1_queue_* subsystem, zero facade coupling.
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
        # Smart-director control (k1_smart_director_* config getters/setters +
        # k1_apply_smart_scene + k1_mode_selection_init); ungated, facade-free. The
        # config fns live in director/k1_smart_director.cpp (replay-oracle MODULE_CPPS);
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
        # Visual-hooks toggle (k1_visual_hooks_* config); ungated, facade-free.
        "commands": [
            "smart_hooks",
        ],
    },
    {
        "name": "edge_mixer",
        "dispatcher": "serial_cmd_dispatch_edge_mixer",
        # Edge-mixer control (k1_edgemixer_* config + k1_parse_edge_mode);
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
        # TU links free (no k1_queue_*-style -O0 link trap). save_config_delayed() is likewise
        # already a driver stub + already used by the extracted setter dispatchers.
        "commands": [
            "preset",
        ],
    },
    {
        "name": "mode",
        "dispatcher": "serial_cmd_dispatch_mode",
        # set_mode + secondary_mode (gated-families lane, Increment A 2026-06-26). Both
        # are UNGATED else-if branches (always present) whose BODIES carry an INTERNAL
        # #ifdef K1_EFFECT_REGISTRY_V1 / #else (registry dense-index vs legacy
        # light_mode_next_enabled). Function-call + global-write (mode_destination /
        # SECONDARY_LIGHTSHOW_MODE / mode_transition_queued / ENABLE_SECONDARY_LEDS;
        # set_mode also save_config_delayed()). The real CONFIG.LIGHTSHOW_MODE write is
        # DEFERRED to led_utilities.h's transition FSM (this lane does not touch it), so a
        # verbatim lift is behaviour-preserving BY CONSTRUCTION — the structural gate pins
        # it without modelling the async write (replay-locking it would be a blind-lock
        # trap; the replay oracle EXCLUDES set_mode for exactly this reason). The internal
        # #ifdef rides verbatim inside the captured body (the oracle does NOT preprocess),
        # so the registry-gated statements are pinned too. beat_director (fully
        # #ifdef K1_EFFECT_FRAMEWORK_V1, production-OFF, gate-MATCHED dispatcher) is a
        # SEPARATE increment (B) — different gate, do not fold it in here.
        "commands": [
            "set_mode",
            "secondary_mode",
        ],
    },
    {
        "name": "beat_director",
        "dispatcher": "serial_cmd_dispatch_beat_director",
        # beat_director toggle (gated-families lane, Increment B 2026-06-26). The WHOLE
        # else-if is wrapped in #ifdef K1_EFFECT_FRAMEWORK_V1 (serial_menu.h ~3076-3095) —
        # production-OFF (k1_hardware defines neither the framework nor registry flag). Pure
        # function-call: bad_director_set_enabled() (director/beat_aware_director.cpp, a
        # framework-env TU) + serial_print_beat_director_status() (external-linkage free fn
        # at serial_menu.h:395, itself inside #ifdef K1_EFFECT_FRAMEWORK_V1) + vp_parse_bool.
        # GATE-MATCHED extraction: the dispatcher decl, def, AND call-site are ALL behind
        # #ifdef K1_EFFECT_FRAMEWORK_V1 (the tempo_stream straddle scar — a single-flag
        # handler must never land under a different/combined gate). The oracle is pure parse
        # (no preprocessing), so it captures + locks the body regardless of the gate; the
        # BUILD enforces the gate-match (k1_hardware byte-identical; framework/registry envs
        # compile the dispatcher). The host replay oracle compiles handlers.cpp WITHOUT the
        # flag, so the gated dispatcher is preprocessed out there — no host-link surgery.
        "commands": [
            "beat_director",
        ],
    },
    {
        "name": "gdft_harness",
        "dispatcher": "serial_cmd_dispatch_gdft_harness",
        # GDFT synthetic-probe diagnostic family (gated-out probe lane, 2026-06-26). THREE
        # commands under ONE contiguous #ifdef ENABLE_GDFT_HARNESS (serial_menu.h ~2630-2689) —
        # production-OFF (k1_hardware defines the flag nowhere; only the NON-SHIPPABLE
        # k1_bench_reference_harness / k1_hardware_harness envs set -DENABLE_GDFT_HARNESS=1).
        # Pure function-call: gdft_probe->gdft_run_single, gdft_sweep->gdft_run_sweep,
        # gdft_agc_probe->gdft_run_agc_probe — all `inline` in diag/gdft_harness.h (#pragma once,
        # ODR-safe, NOT self-flag-guarded; the gate is caller-only, exactly the beat_director
        # model). Read-only diagnostic: the backing fns snapshot/halt/restore GDFT state and run
        # process_GDFT() UNMODIFIED (the handler adds no CONFIG/global write). GATE-MATCHED
        # extraction: the dispatcher decl, def, the guarded #include "gdft_harness.h", AND the
        # call-site are ALL behind #ifdef ENABLE_GDFT_HARNESS (the tempo_stream straddle scar — a
        # single-flag handler must never land under a different/combined gate). The oracle is pure
        # parse (no preprocessing), so it captures + locks the body regardless of the gate; the
        # BUILD enforces the gate-match (k1_hardware code/data byte-identical; the harness envs
        # compile the dispatcher with the flag ON). The host replay oracle compiles handlers.cpp
        # WITHOUT the flag, so the gated dispatcher + its include preprocess out there — no
        # host-link surgery. The OUTPUT SCHEMA row-prefixes (GDFTP / GDFTP5 / GDFTAGC) live in the
        # UNTOUCHED gdft_harness.h; this structural golden pins the handler BODY + routing, and the
        # row-prefix tokens are pinned separately by tests/test_gdft_harness_schema_static.py (the
        # diagnostic-is-product schema lock — byte-identity is necessary but NOT sufficient).
        "commands": [
            "gdft_probe",
            "gdft_sweep",
            "gdft_agc_probe",
        ],
    },
]

# Files a function-call handler body can live in: inline in parse_command
# (serial_menu.h) pre-extraction, or in the dispatcher (serial_cmd_handlers.cpp)
# post-extraction. capture() searches both; the golden records neither (the move is
# invisible to the contract).
_MENU_REL     = ("serial", "serial_menu.h")
_MENU_CPP_REL = ("serial", "serial_menu.cpp")
_HANDLERS_REL = ("serial", "serial_cmd_handlers.cpp")
_TYPED_REL    = ("serial", "serial_typed_dispatch.cpp")
_TABLE_REL    = ("serial", "serial_typed_cmd_table.def")


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


def _routed(menu_src: str, typed_src: str, table_src: str, cmd: str, dispatcher: str) -> bool:
    """True iff the command is routed from parse_command to its dispatcher.

    Pre-R2: parse_command called serial_cmd_dispatch_<x>(command_type, command_data).
    Post-R2 (M2.1): SERIAL_TYPED_CMD table -> typed wrapper -> dispatcher."""
    if f"{dispatcher}(command_type, command_data)" in menu_src:
        return True
    if not re.search(rf'SERIAL_TYPED_CMD\("{re.escape(cmd)}"', table_src):
        return False
    return f"return {dispatcher}(command_type, command_data)" in typed_src


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
    menu_src = (fw.joinpath(*_MENU_REL)).read_text(encoding="utf-8")
    menu_cpp = (fw.joinpath(*_MENU_CPP_REL)).read_text(encoding="utf-8") \
               if (fw.joinpath(*_MENU_CPP_REL)).exists() else ""
    menu_src = menu_src + "\n" + menu_cpp
    handlers_src = (fw.joinpath(*_HANDLERS_REL)).read_text(encoding="utf-8") \
                   if (fw.joinpath(*_HANDLERS_REL)).exists() else ""
    typed_src = (fw.joinpath(*_TYPED_REL)).read_text(encoding="utf-8") \
                if (fw.joinpath(*_TYPED_REL)).exists() else ""
    table_src = (fw.joinpath(*_TABLE_REL)).read_text(encoding="utf-8") \
                if (fw.joinpath(*_TABLE_REL)).exists() else ""

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
                # routed if the body lives in the dispatcher AND parse_command still
                # reaches it (direct call-site or R2 typed-table wrapper).
                reachable = bool(moved is not None and _routed(menu_src, typed_src, table_src, cmd, dispatcher))
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
        r'(else if \(strcmp\(command_type, "queue_mode"\) == 0\) \{\s*if \(strcmp\(command_data, "on"\) == 0\) \{\s*)k1_queue_set_mode_enabled\(true\);',
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
    # 4. SEVER THE ROUTING (M2.1 R2): rename the typed-wrapper return so capture()'s
    #    `_routed` check no longer finds it. The queue bodies still live in the
    #    dispatcher, but every queue command flips reachable:true->false.
    (
        r"else if \(serial_cmd_dispatch_queue\(command_type, command_data\)\)",
        r"else if (serial_cmd_dispatch_queue_SEVERED(command_type, command_data))",
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
    #    on the unique K1VisualHookConfig fetch. (a)
    (
        r"(K1VisualHookConfig config = k1_visual_hooks_config\(\);\s*)config\.enabled = value;",
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
        r"return serial_cmd_dispatch_smart_director\(command_type, command_data\);",
        r"return serial_cmd_dispatch_smart_director_SEVERED(command_type, command_data);",
        "smart_director_call_site_severed (routing/reachable divergence)",
    ),
    (
        r"return serial_cmd_dispatch_smart_visual\(command_type, command_data\);",
        r"return serial_cmd_dispatch_smart_visual_SEVERED(command_type, command_data);",
        "smart_visual_call_site_severed (routing/reachable divergence)",
    ),
    (
        r"return serial_cmd_dispatch_edge_mixer\(command_type, command_data\);",
        r"return serial_cmd_dispatch_edge_mixer_SEVERED(command_type, command_data);",
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
    # 15. SEVER THE ROUTING (added with the EXTRACT, once the call-site exists): rename
    #     the parse_command call so capture()'s `_routed` check no longer finds it. The
    #     "preset" body still lives in the dispatcher, but reachable flips true->false ->
    #     divergence. Bare-arg form `(command_type, command_data)` matches ONLY the
    #     call-site (the def/decl carry typed params), so the rglob lands there.
    (
        r"return serial_cmd_dispatch_preset\(command_type, command_data\);",
        r"return serial_cmd_dispatch_preset_SEVERED(command_type, command_data);",
        "preset_call_site_severed (routing/reachable divergence)",
    ),
    # ---- mode family (set_mode + secondary_mode) teeth (Increment A, LOCK 2026-06-26) --
    # The call-site-sever tooth (#20) is added in the EXTRACT commit, once
    # serial_cmd_dispatch_mode's parse_command call-site exists — at LOCK its anchor would
    # be count==0 and the mutation-anchor guard (test_mutation_anchor_uniqueness_static.py)
    # would fail. The four below anchor on text that is count==1 whether the bodies are
    # still inline in serial_menu.h (LOCK) or already in serial_cmd_handlers.cpp (EXTRACT).
    # 16. DROP set_mode's DEFERRED save: the async/deferred-save sever the Captain required.
    #     Anchored on set_mode's unique "// CONFIG.LIGHTSHOW_MODE" comment so the rglob is
    #     count==1; dropping the call removes a statement -> the normalized body of
    #     "set_mode" diverges (the comment itself is stripped by _normalize, so what
    #     diverges is the MISSING save_config_delayed(), not the anchor text). Channel (a).
    (
        r'save_config_delayed\(\);(\s+tx_begin\(\);\s+// CONFIG\.LIGHTSHOW_MODE)',
        r'\1',
        "set_mode_deferred_save_dropped (async/deferred-save sever divergence)",
    ),
    # 17. MIS-ROUTE set_mode: rename its strcmp -> "set_mode_MUT". capture() can no longer
    #     find the branch -> body null + reachable false. Channel (b)/(c) routing/identity.
    (
        r'strcmp\(command_type, "set_mode"\)',
        r'strcmp(command_type, "set_mode_MUT")',
        "set_mode_command_type_renamed (routing/identity divergence)",
    ),
    # secondary_mode gets a routing tooth (below) but NO separate body tooth: every
    # statement-anchored candidate (e.g. serial_print_mode_line("SECONDARY_MODE", ...))
    # ALSO appears at serial_menu.h:1272, so a count=1 rglob is ambiguous — the
    # mutation-anchor guard (test_mutation_anchor_uniqueness_static.py) correctly rejects
    # it. One family-level BODY tooth (#16 set_mode_deferred_save) already proves the gate
    # is not blind to a body change, and the golden REPRODUCE test pins secondary_mode's
    # full normalized body regardless. Matches the 1-body-tooth-per-family shape of
    # preset / smart_director.
    # 18. MIS-ROUTE secondary_mode: rename its strcmp -> "secondary_mode_MUT". Exact
    #     closing `"` => matches only "secondary_mode", not the strncmp("secondary_",10)
    #     prefix-router or the 14 already-extracted secondary_* setters. Channel (b)/(c).
    (
        r'strcmp\(command_type, "secondary_mode"\)',
        r'strcmp(command_type, "secondary_mode_MUT")',
        "secondary_mode_command_type_renamed (routing/identity divergence)",
    ),
    # 19. SEVER THE ROUTING (added with the EXTRACT, once the call-site exists): rename
    #     the parse_command call so capture()'s `_routed` check no longer finds it. BOTH
    #     set_mode + secondary_mode bodies still live in the dispatcher, but reachable
    #     flips true->false for both -> divergence. Proves the `reachable` field is not
    #     blind. Bare-arg form `(command_type, command_data)` matches ONLY the call-site
    #     (the def/decl carry typed params), so the rglob lands there. count==1.
    (
        r"return serial_cmd_dispatch_mode\(command_type, command_data\);",
        r"return serial_cmd_dispatch_mode_SEVERED(command_type, command_data);",
        "mode_call_site_severed (routing/reachable divergence)",
    ),
    # ---- beat_director family teeth (Increment B, LOCK 2026-06-26) ----
    # The call-site-sever tooth (#22) is added in the EXTRACT commit (count==0 until the
    # dispatcher call-site exists; the mutation-anchor guard would fail at LOCK otherwise).
    # Both below anchor on text that is count==1 whether beat_director is still inline in
    # serial_menu.h (LOCK) or already in serial_cmd_handlers.cpp (EXTRACT) — the oracle and
    # the anchor guard read RAW text, so the #ifdef K1_EFFECT_FRAMEWORK_V1 wrapper is
    # transparent to both.
    # 20. ALTER beat_director's body: bad_director_set_enabled(value) -> (false). The
    #     normalized body of "beat_director" diverges on the subsystem-call argument,
    #     proving the gate pins the framework-gated statements too. Channel (a).
    (
        r'bad_director_set_enabled\(value\);',
        r'bad_director_set_enabled(false);',
        "beat_director_subsystem_arg_value_to_false (statement-identity divergence)",
    ),
    # 21. MIS-ROUTE beat_director: rename its strcmp -> "beat_director_MUT". capture() can
    #     no longer find the branch -> body null + reachable false. Channel (b)/(c).
    (
        r'strcmp\(command_type, "beat_director"\)',
        r'strcmp(command_type, "beat_director_MUT")',
        "beat_director_command_type_renamed (routing/identity divergence)",
    ),
    # 22. SEVER THE ROUTING (added with the EXTRACT, once the gate-matched call-site exists):
    #     rename the parse_command call so capture()'s `_routed` check no longer finds it —
    #     beat_director's body still lives in the dispatcher, but reachable flips
    #     true->false -> divergence. Bare-arg form matches ONLY the call-site (the def/decl
    #     carry typed params). count==1 (the call-site is inside serial_menu.h's
    #     #ifdef K1_EFFECT_FRAMEWORK_V1, but the oracle/guard read raw text — gate-transparent).
    (
        r"return serial_cmd_dispatch_beat_director\(command_type, command_data\);",
        r"return serial_cmd_dispatch_beat_director_SEVERED(command_type, command_data);",
        "beat_director_call_site_severed (routing/reachable divergence)",
    ),
    # ---- gdft_harness family teeth (gated-out probe lane, LOCK 2026-06-26) ----
    # The call-site-sever tooth (#27) is added in the EXTRACT commit (count==0 until the
    # gate-matched dispatcher call-site exists; the mutation-anchor guard would fail at LOCK
    # otherwise). The four below anchor on text that is count==1 whether the three commands are
    # still inline in serial_menu.h (LOCK) or already in serial_cmd_handlers.cpp (EXTRACT) — the
    # oracle + anchor guard read RAW text, so the #ifdef ENABLE_GDFT_HARNESS wrapper is
    # transparent to both.
    # 23. ALTER gdft_agc_probe's body: gdft_run_agc_probe(amp) -> (1.0f). The normalized body of
    #     "gdft_agc_probe" diverges on the backing-call argument, proving the gate pins the
    #     gated statements too. Channel (a) statement-identity. (`gdft_run_agc_probe(amp)` is
    #     count==1 — the inline def in gdft_harness.h is `(float amp_scale)`, not `(amp)`.)
    (
        r'gdft_run_agc_probe\(amp\);',
        r'gdft_run_agc_probe(1.0f);',
        "gdft_agc_probe_arg_amp_to_1.0f (statement-identity divergence)",
    ),
    # 24. MIS-ROUTE gdft_probe: rename its strcmp -> "gdft_probe_MUT". capture() can no longer
    #     find the branch -> body null + reachable false. Channel (b)/(c). The exact closing `"`
    #     => matches only "gdft_probe", never the "gdft_agc_probe" literal.
    (
        r'strcmp\(command_type, "gdft_probe"\)',
        r'strcmp(command_type, "gdft_probe_MUT")',
        "gdft_probe_command_type_renamed (routing/identity divergence)",
    ),
    # 25. MIS-ROUTE gdft_sweep: rename its strcmp -> "gdft_sweep_MUT". Channel (b)/(c).
    (
        r'strcmp\(command_type, "gdft_sweep"\)',
        r'strcmp(command_type, "gdft_sweep_MUT")',
        "gdft_sweep_command_type_renamed (routing/identity divergence)",
    ),
    # 26. MIS-ROUTE gdft_agc_probe: rename its strcmp -> "gdft_agc_probe_MUT". Channel (b)/(c).
    (
        r'strcmp\(command_type, "gdft_agc_probe"\)',
        r'strcmp(command_type, "gdft_agc_probe_MUT")',
        "gdft_agc_probe_command_type_renamed (routing/identity divergence)",
    ),
    # 27. SEVER THE ROUTING (added with the EXTRACT, once the gate-matched call-site exists):
    #     rename the parse_command call so capture()'s `_routed` check no longer finds it — all
    #     three gdft bodies still live in the dispatcher, but reachable flips true->false for
    #     each -> divergence. Proves the `reachable` field is not blind. Bare-arg form
    #     `(command_type, command_data)` matches ONLY the call-site (the def/decl carry typed
    #     params), so the rglob lands there. count==1 (the call-site is inside serial_menu.h's
    #     #ifdef ENABLE_GDFT_HARNESS, but the oracle/guard read raw text — gate-transparent).
    (
        r"return serial_cmd_dispatch_gdft_harness\(command_type, command_data\);",
        r"return serial_cmd_dispatch_gdft_harness_SEVERED(command_type, command_data);",
        "gdft_harness_call_site_severed (routing/reachable divergence)",
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
