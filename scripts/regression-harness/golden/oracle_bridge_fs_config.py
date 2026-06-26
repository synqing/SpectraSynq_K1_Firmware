#!/usr/bin/env python3
"""Structural-contract oracle for the PERSISTED-CONFIG decision logic in
persistence/bridge_fs.h (production-readiness Lane N1 · anti-gaming LOCK).

THE PROBLEM. The persisted-config load/validate path (`load_config()`,
`load_configuration()`, `update_config_filename()`) makes a cluster of
SAFETY-RELEVANT decisions — open-failure fallback, raw-load + per-field sanitise,
a DEAD factory-reset recovery branch, version-stamped filename migration, and
per-field truncation/validation error accumulation. A later production-readiness
FIX will almost certainly touch these very sites (e.g. wire up the dead
`load_configuration()`, harden the truncation guard, change the migration
filename). Without a lock, such a change could SILENTLY alter the decision
behaviour and slip through a host build (these functions drag LittleFS/FreeRTOS
and do not host-compile; the existing replay/struct serial oracles never reach
them). This oracle is the missing teeth.

THE ARGUMENT (same TRIZ #13/#22 shape as oracle_serial_struct.py). We cannot run
this code on the host, so instead of observing behaviour we PIN STRUCTURE: per
named decision-bearing function, capture the PAIR

  (a) normalized body  — the exact statements, comment/indent-insensitive
  (b) reachable         — is the function still invoked from the load path
                          (init_fs() -> load_config()/update_config_filename();
                          load_configuration() currently has NO caller — that
                          dead-code fact is itself pinned, so wiring it up later
                          flips `reachable` and forces an explicit golden re-pin)

For a behaviour-preserving refactor the captured pair is INVARIANT: re-indentation
and comment edits are tolerated by _normalize, but EVERY statement, literal,
operator, branch and call is preserved, and `reachable` tracks the call graph. So
the frozen golden REPRODUCES across a clean refactor; a decision-site change
diverges the body, and a re-routing change diverges `reachable`. That divergence
IS the alarm — the gate goes RED until the golden is re-pinned ON PURPOSE.

THE PINNED SITES (per the lane brief, all in persistence/bridge_fs.h):
  1. load_config() open-failure fallback     — `if (!file) { ...; return; }`
  2. load_config() raw-load + sanitise       — memcpy(&CONFIG,...) + light_mode/
                                                registry_sanitize_persisted block
  3. load_config() DEAD factory-reset branch — `bool queue_factory_reset=false;`
                                                + `if (queue_factory_reset==true)`
  4. load_configuration() validation accrual — `config_error=true;` sites +
                                                PALETTE_INDEX>=gGradientPaletteCount
                                                reset + the -1/-2 returns
  + update_config_filename() — the version-stamped migration filename (the
    `/CONFIG_%05lu.BIN` format) that selects WHICH persisted file is loaded.
Sites 1-3 + the raw-load sanitise all live inside load_config()'s body; site 4
lives inside load_configuration()'s body; the migration filename inside
update_config_filename()'s body — so capturing those three normalized bodies pins
every enumerated decision site, and any single-site edit diverges the enclosing
record. The golden does NOT record line numbers or whitespace, only the statement
stream + reachability, so a faithful refactor survives.

FAULT-EVIDENCE (the Gate-Fα teeth, proven by harness_selftest.py): the MUTATIONS
list plants one real regression for EACH of the lane's five decision classes —
(valid/load) memcpy size, (fallback) the queue_factory_reset recovery test,
(version/migrate) the migration filename format, (truncated) the first read()-size
guard, (error-accept) a config_error flag flip — each MUST diverge the capture.
Each anchor matches EXACTLY ONCE across the firmware tree
(tests/test_mutation_anchor_uniqueness_static.py rglob count==1).

NON-SHIPPING. Host-only, pure SOURCE PARSE (no compile, no device). Mirrors the
oracle PUBLIC INTERFACE (NAME / capture(firmware_root=None) / MUTATIONS),
registered in harness_selftest.ORACLE_MODULES, gated by test_golden_master.py.
"""

import json
import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Repo layout (mirrors oracle_serial_struct.py / oracle_serial_replay.py)
# ---------------------------------------------------------------------------
ROOT     = Path(__file__).resolve().parents[3]            # SpectraSynq_K1_Firmware/
FIRMWARE = ROOT / "SPECTRASYNQ_K1_FIRMWARE"

NAME = "bridge_fs_config"

# The single source file the persisted-config decision logic lives in.
_BRIDGE_FS_REL = ("persistence", "bridge_fs.h")

# ---------------------------------------------------------------------------
# Registered decision-bearing functions. Each `entry` names a function whose body
# carries one or more of the lane's enumerated decision sites; `callers` lists the
# functions whose body must invoke it for it to be reachable from the load path.
# `init_fs` is the firmware load entry point (init_fs() -> load_config(),
# update_config_filename(); see persistence/bridge_fs.h init_fs()). To onboard a
# new persisted-config decision function: add an entry here, regen the golden (the
# LOCK commit), then any later edit to that function's decision sites — or a change
# to whether the load path still calls it — diverges its record.
# ---------------------------------------------------------------------------
FUNCTIONS = [
    {
        # SITE 1 (open-failure fallback `if (!file){...return;}`), SITE 2 (raw-load
        # memcpy + per-field light_mode/registry_sanitize_persisted block) and SITE 3
        # (the DEAD `bool queue_factory_reset=false;` + `if (queue_factory_reset==true)
        # { factory_reset(); }` recovery branch) all live in load_config()'s body.
        "name": "load_config",
        "callers": ["init_fs"],
    },
    {
        # SITE 4: the validation-accumulation function — per-field read()-size
        # truncation guards (`!= sizeof(...) -> config_error=true`), the
        # PALETTE_INDEX>=gGradientPaletteCount reset, and the -1/-2 returns. Currently
        # has NO caller in the firmware (dead code); `reachable` pins that fact, so a
        # later fix that wires it into the load path flips it and forces a re-pin.
        "name": "load_configuration",
        "callers": ["init_fs", "load_config"],
    },
    {
        # The version-stamped migration filename: update_config_filename(input)
        # snprintf's "/CONFIG_%05lu.BIN" from `input`, selecting WHICH persisted CONFIG
        # file load_config() opens. init_fs() calls update_config_filename(FIRMWARE_VERSION)
        # before load_config(), so the migration constant governs the loaded decision.
        "name": "update_config_filename",
        "callers": ["init_fs"],
    },
]


# ---------------------------------------------------------------------------
# Source parsing — comment-aware brace matching, lifted from oracle_serial_struct.py
# so this oracle uses the IDENTICAL literal/comment-skipping scan (no divergent
# parser). The only difference is the OPENER: a free-function signature
# `<ret> <name>( ... ) {` instead of an `else if (strcmp(...)) {` branch.
# ---------------------------------------------------------------------------
def _func_open_regex(name: str) -> str:
    """Match a free-function definition opener `<ret> <name>(...) {` up to its
    opening brace. Anchored on the bare `<name>(` at a definition position (a
    return type / qualifier precedes it on the line, never `.`/`->`/`::`), so it
    lands on the DEFINITION, not a call-site like `load_config();`."""
    return r'(?:^|[;\}\)]|\b(?:void|int|bool|static)\b)[^\n;{}]*\b' \
           + re.escape(name) + r'\s*\([^;{}]*\)\s*\{'


def _extract_function_body(source: str, name: str):
    """Return the brace-balanced BODY of function `name`, or None if absent.

    Brace-matches from the opening `{` of the function definition, skipping braces
    inside string and char literals and // /* */ comments so a body containing
    `{`/`}` in a literal cannot unbalance the scan. (Identical scan to
    oracle_serial_struct._extract_block; only the opener regex differs.)"""
    m = re.search(_func_open_regex(name), source, flags=re.M)
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
    """Comment- and indentation-insensitive token stream (identical to
    oracle_serial_struct._normalize).

    Strips // and /* */ comments and collapses every whitespace run to one space so
    re-indentation by a refactor is tolerated, while EVERY token, identifier,
    operator, string literal and numeric literal is preserved — a changed argument,
    echo string, branch, size or call diverges. The MUTATIONS prove the
    normalization is not blind to a literal's CONTENT (e.g. the migration filename)."""
    body = re.sub(r"/\*.*?\*/", "", body, flags=re.S)
    body = re.sub(r"//[^\n]*", "", body)
    body = re.sub(r"\s+", " ", body).strip()
    return body


def _calls(caller_body: str, callee: str) -> bool:
    """True iff `caller_body` contains a `<callee>(` call. The DEFINITION opener of
    `callee` lives in a DIFFERENT function's body, so within `caller_body` a
    `<callee>(` token can only be a call-site (or a forward-decl, which is also a
    legitimate reference for reachability). Anchored on a non-member boundary
    (start / non-identifier, not `.`/`->`) so a struct field of the same name
    cannot false-positive."""
    return re.search(r'(?:^|[^\w.>])' + re.escape(callee) + r'\s*\(', caller_body) is not None


# ---------------------------------------------------------------------------
# capture() — the public oracle interface
# ---------------------------------------------------------------------------
def capture(firmware_root=None) -> str:
    """Return deterministic JSON-lines: one record per registered decision function.

    Record = {func, body (normalized | null), reachable}. Pure source parse — no
    compile, no device. `body` is the function's normalized statement stream
    (carrying every enumerated decision site); `reachable` is true iff a listed
    caller's body still invokes it (the init_fs() load path). Both are invariant
    across a behaviour-preserving refactor, so the golden reproduces; a decision-site
    edit diverges `body`, a re-routing diverges `reachable`."""
    fw = Path(firmware_root) if firmware_root else FIRMWARE
    src = (fw.joinpath(*_BRIDGE_FS_REL)).read_text(encoding="utf-8")

    lines = []
    for fn in FUNCTIONS:
        body_raw = _extract_function_body(src, fn["name"])
        body = _normalize(body_raw) if body_raw is not None else None
        # reachable: the function is present AND at least one listed caller's body
        # invokes it. (If the function body itself is absent it cannot be reached.)
        reachable = False
        if body_raw is not None:
            for caller in fn["callers"]:
                cbody = _extract_function_body(src, caller)
                if cbody is not None and _calls(cbody, fn["name"]):
                    reachable = True
                    break
        rec = {"func": fn["name"], "body": body, "reachable": reachable}
        lines.append(json.dumps(rec, sort_keys=True, separators=(",", ":")))
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Mutations — the Gate-Fα teeth. One per lane decision class. Each plants a real
# regression a botched config-load fix would introduce and MUST diverge the capture.
# Applied by harness_selftest.py to a firmware COPY (rglob, count=1) and re-captured.
# Every anchor matches EXACTLY ONCE across the firmware tree
# (tests/test_mutation_anchor_uniqueness_static.py).
# ---------------------------------------------------------------------------
MUTATIONS = [
    # 1. (valid/load) ALTER THE RAW-LOAD SIZE: load_config() copies one byte fewer
    #    from the persisted buffer into CONFIG. SITE 2. The normalized body of
    #    load_config diverges on the memcpy size argument — proving the gate pins the
    #    raw-load decision. Anchor is count==1 (only this memcpy reads into &CONFIG).
    (
        r'memcpy\(&CONFIG, config_buffer, sizeof\(CONFIG\)\);',
        r'memcpy(&CONFIG, config_buffer, sizeof(CONFIG) - 1);',
        "load_config_raw_load_size_short_by_one (valid/load decision divergence)",
    ),
    # 2. (fallback) INVERT THE RECOVERY TEST: flip the DEAD factory-reset guard
    #    `if (queue_factory_reset == true)` -> `!= true`, which would fire
    #    factory_reset() on the (currently-false) flag. SITE 3. The normalized body of
    #    load_config diverges on the recovery branch condition. count==1.
    (
        r'if \(queue_factory_reset == true\) \{',
        r'if (queue_factory_reset != true) {',
        "load_config_factory_reset_recovery_test_inverted (fallback decision divergence)",
    ),
    # 3. (version/migrate) CHANGE THE MIGRATION FILENAME: update_config_filename()
    #    stamps a DIFFERENT persisted file path, so load_config() would open the wrong
    #    (or a non-existent) CONFIG file. The normalized body of update_config_filename
    #    diverges on the format literal's CONTENT — proving normalization is not blind
    #    to the migration filename. count==1.
    (
        r'"/CONFIG_%05lu\.BIN"',
        r'"/CONFIG_%05lu.DAT"',
        "update_config_filename_migration_path_changed (version/migrate decision divergence)",
    ),
    # 4. (truncated) FLIP THE TRUNCATION GUARD: load_configuration()'s first read()
    #    size check `!= sizeof(...)` -> `== sizeof(...)`, inverting truncated-read
    #    detection for BASE_COAT_INTENSITY. SITE 4. The normalized body of
    #    load_configuration diverges on the guard operator. count==1 (the doubled
    #    `sizeof(CONFIG.BASE_COAT_INTENSITY)` makes this read-guard unique).
    (
        r'sizeof\(CONFIG\.BASE_COAT_INTENSITY\)\) != sizeof\(CONFIG\.BASE_COAT_INTENSITY\)',
        r'sizeof(CONFIG.BASE_COAT_INTENSITY)) == sizeof(CONFIG.BASE_COAT_INTENSITY)',
        "load_configuration_basecoat_truncation_guard_inverted (truncated decision divergence)",
    ),
    # 5. (error-accept) ACCEPT AN INVALID PALETTE: load_configuration() resets an
    #    out-of-bounds PALETTE_INDEX but then flips `config_error = true;` -> `false`,
    #    so the -2 "config error" return is suppressed and the invalid load is silently
    #    accepted. SITE 4. The normalized body of load_configuration diverges. Anchored
    #    on the unique `CONFIG.PALETTE_INDEX = 0;` reset that immediately precedes this
    #    flag (the bare `config_error = true;` appears many times; this two-line anchor
    #    is count==1).
    (
        r'CONFIG\.PALETTE_INDEX = 0; // Reset to default if out of bounds\s*\n\s*config_error = true;',
        r'CONFIG.PALETTE_INDEX = 0; // Reset to default if out of bounds\n    config_error = false;',
        "load_configuration_palette_reset_error_accept (error-accept decision divergence)",
    ),
]


# ---------------------------------------------------------------------------
# Standalone regen / self-check (mirrors oracle_serial_struct.py __main__).
# Regenerate the golden:
#   python3 oracle_bridge_fs_config.py > tests/golden/bridge_fs_config.golden.jsonl
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse
    import shutil
    import sys
    import tempfile

    parser = argparse.ArgumentParser(description="structural-contract oracle for the persisted-config decision logic.")
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
