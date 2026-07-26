"""Static schema-lock for the GDFT synthetic-probe diagnostic family.

THE DIAGNOSTIC IS THE PRODUCT (Captain, 2026-06-26). The gdft_* probe family is
production-OFF (gated by ENABLE_GDFT_HARNESS), so a verbatim strangler-fig lift of its
handler is production-byte-identical BY CONSTRUCTION — but the family is EVIDENCE
infrastructure. Its serial output is a wire contract: scripts/regression-harness/
gdft_check.py and the offline notebooks grep the row prefixes GDFTP / GDFTP5 / GDFTAGC.
A lift (or any future edit) that silently renamed, fragmented, or dropped one of those
rows would flash green on production byte-identity while breaking every analyzer — the
LayerSense failure mode. Byte-identity is NECESSARY BUT NOT SUFFICIENT.

oracle_serial_struct.py (the serial_struct golden) pins the handler BODY + the command ->
backing-fn ROUTING. This test pins what the golden does not: the row-prefix TOKENS in
their source-of-truth header (diag/gdft_harness.h, which the lift never touches) and the
inline backing-fn definitions that emit them. Together they are the two-pronged
diagnostic-is-product bar.

Home-agnostic by construction: the routing assertion finds the dispatcher wherever it
currently lives — serial_cmd_dispatch_gdft_harness() in serial_cmd_handlers.cpp once
extracted, or the inline #ifdef ENABLE_GDFT_HARNESS block in serial_menu.h before then —
so this single UNCHANGED test passes at BOTH the LOCK commit (inline) and the EXTRACT
commit (dispatcher). Block extraction is brace/quote-aware (mirrors
test_k1_loud_guard_static.typed_command_block) so an adjacent handler cannot unbalance the
scan (the over-capture class-bug fixed 2026-06-26)."""

import unittest
from pathlib import Path
from _fwpath import FwDir, read_serial_menu_surface


ROOT = Path(__file__).resolve().parents[1]
FW_DIR = FwDir(ROOT / "SPECTRASYNQ_K1_FIRMWARE")
FW = ROOT / "SPECTRASYNQ_K1_FIRMWARE"
GDFT_HARNESS = (FW / "diag" / "gdft_harness.h").read_text(encoding="utf-8")
SERIAL = read_serial_menu_surface(FW_DIR)
HANDLERS = (FW / "serial" / "serial_cmd_handlers.cpp").read_text(encoding="utf-8")

# command_type -> the inline backing fn (diag/gdft_harness.h) it must route to. The lift
# must preserve this mapping; oracle_serial_struct.py pins the exact per-branch body, this
# test pins that each command + its backing fn co-occur in the SAME dispatcher.
GDFT_ROUTES = {
    "gdft_probe": "gdft_run_single",
    "gdft_sweep": "gdft_run_sweep",
    "gdft_agc_probe": "gdft_run_agc_probe",
}

# The three telemetry row prefixes that ARE the diagnostic wire contract. Quoted so a bare
# comment mention cannot satisfy the assertion — the literal must open a string.
GDFT_ROW_PREFIXES = ('"GDFTP,', '"GDFTP5,', '"GDFTAGC,')


def _balanced_block(text, start):
    """Return text[start:close+1] brace-balanced from the first `{` at/after start.

    String/char literals AND // and /* */ comments are skipped so neither a brace nor an
    apostrophe inside a literal or comment can unbalance the scan — e.g. the dispatcher's
    `// ...let parse_command's ladder continue` comment, whose apostrophe would otherwise be
    read as a char-literal opener. This mirrors the oracle's _extract_block discipline; the
    over-capture class-bug fixed in test_k1_loud_guard_static (2026-06-26) is the precedent."""
    i = text.find("{", start)
    assert i != -1, "no opening brace after dispatcher signature"
    depth = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c == '"' or c == "'":            # string / char literal
            quote = c
            i += 1
            while i < n and text[i] != quote:
                if text[i] == "\\":
                    i += 1
                i += 1
            i += 1
            continue
        if c == '/' and i + 1 < n and text[i + 1] == '/':   # line comment
            while i < n and text[i] != '\n':
                i += 1
            continue
        if c == '/' and i + 1 < n and text[i + 1] == '*':   # block comment
            i += 2
            while i + 1 < n and not (text[i] == '*' and text[i + 1] == '/'):
                i += 1
            i += 2
            continue
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
        i += 1
    raise AssertionError("unbalanced braces in gdft dispatcher block")


def gdft_dispatch_source():
    """The gdft handler text, wherever it currently lives.

    EXTRACT: serial_cmd_dispatch_gdft_harness() in serial_cmd_handlers.cpp.
    LOCK (pre-extract): the inline #ifdef ENABLE_GDFT_HARNESS block in serial_menu.h that
    carries the strcmp branches (NOT the earlier help-text #ifdef block)."""
    marker = "bool serial_cmd_dispatch_gdft_harness("
    start = HANDLERS.find(marker)
    if start != -1:
        return _balanced_block(HANDLERS, start)
    # fallback: the inline handler #ifdef block (the one containing the gdft_probe strcmp)
    g = SERIAL.find("#ifdef ENABLE_GDFT_HARNESS")
    while g != -1:
        end = SERIAL.find("#endif", g)
        block = SERIAL[g:end] if end != -1 else SERIAL[g:]
        if 'strcmp(command_type, "gdft_probe")' in block:
            return block
        g = SERIAL.find("#ifdef ENABLE_GDFT_HARNESS", g + 1)
    raise AssertionError("no gdft handler block found in handlers.cpp or serial_menu.h")


class GdftHarnessSchemaStaticTest(unittest.TestCase):
    def test_row_prefix_tokens_present_in_backing_header(self):
        # The schema lives in the UNTOUCHED backing header; pin it so a FUTURE edit cannot
        # silently drop/rename a telemetry row while staying production-byte-identical.
        for prefix in GDFT_ROW_PREFIXES:
            self.assertIn(
                prefix, GDFT_HARNESS,
                f"GDFT schema row-prefix {prefix} missing from diag/gdft_harness.h",
            )

    def test_backing_fns_defined_inline_in_header(self):
        # The three serial-facing backing fns must stay inline in gdft_harness.h (the
        # ODR-safe, #pragma-once, caller-only-gated home) — a rename here breaks routing.
        for fn in GDFT_ROUTES.values():
            self.assertIn(
                f"inline void {fn}(", GDFT_HARNESS,
                f"backing fn `inline void {fn}(...)` missing from diag/gdft_harness.h",
            )

    def test_each_command_routes_to_its_backing_fn(self):
        src = gdft_dispatch_source()
        for cmd, fn in GDFT_ROUTES.items():
            self.assertIn(
                f'strcmp(command_type, "{cmd}")', src,
                f"command {cmd} is not routed in the gdft dispatcher",
            )
            self.assertIn(
                f"{fn}(", src,
                f"command {cmd} no longer calls its backing fn {fn}() in the dispatcher",
            )

    def test_gate_flag_is_caller_only_not_self_guarded(self):
        # Lift invariant: the gate is at the CALLER (#ifdef ENABLE_GDFT_HARNESS around the
        # dispatcher decl/def/include/call-site), never inside gdft_harness.h. If the header
        # ever self-guards on the flag, the always-compilable inline contract is broken.
        self.assertIn("#pragma once", GDFT_HARNESS)
        self.assertNotIn("#ifdef ENABLE_GDFT_HARNESS", GDFT_HARNESS)
        self.assertNotIn("#if ENABLE_GDFT_HARNESS", GDFT_HARNESS)


if __name__ == "__main__":
    unittest.main()
