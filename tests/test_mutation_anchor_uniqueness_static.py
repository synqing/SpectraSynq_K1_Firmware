#!/usr/bin/env python3
"""Static guard: every golden-oracle mutation anchor must match EXACTLY ONCE across
the firmware tree, and no dispatcher comment may carry a raw command literal.

WHY (load-bearing, added 2026-06-26 after the preset defect):
Gate Fα (harness_selftest.py) proves each oracle MUTATION by copying the firmware,
applying `re.sub(pattern, replacement, count=1)` to the FIRST rglob match, and
asserting the re-capture diverges. That proof has a blind spot the harness cannot
self-detect: if a mutation's anchor matches MORE THAN ONCE, the count=1 rglob may
land on a DECOY occurrence instead of the live code, leaving the capture unchanged
so the tooth silently goes blind. Two real instances of this class:
  * 2026-06-25 preset defect — a dispatcher COMMENT carrying the literal
    `strcmp(command_type, "preset")` preceded the real branch; the command_type-rename
    tooth mutated the comment and went blind (Gate Fα FAILED, correctly, only once the
    anchor became non-unique).
  * the saturation-echo-label hazard documented in oracle_serial_replay.py (the bare
    label appears in both the dump_info status block and the setter) — the same
    count>=2 decoy trap, avoided there only by hand-anchoring on setter-specific text.

Gate Fα catches count==0 (MISSED). It does NOT reliably catch count>=2 (masked).
This test makes the missing half machine-checked, so correctness no longer relies on
a reviewer remembering the placeholder convention:
  (1) ANCHOR UNIQUENESS — every MUTATION pattern in every registered oracle matches
      EXACTLY ONCE across SPECTRASYNQ_K1_FIRMWARE/**/*.{cpp,h} (the same tree + glob
      the harness rglob walks).
  (2) COMMENT PLACEHOLDER — no `//` comment in serial_cmd_handlers.cpp may contain a
      raw `strcmp(command_type, "<literal>")`; it must use the "<name>" placeholder
      (the direct cause of the preset defect, enforced at the source before a mutation
      even exists).

NON-SHIPPING host test. Oracle-driven: scales automatically as families/mutations are
added — no per-command maintenance.
"""
import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIRMWARE = ROOT / "SPECTRASYNQ_K1_FIRMWARE"
GOLDEN_DIR = ROOT / "scripts" / "regression-harness" / "golden"

# Oracles whose MUTATIONS anchor on firmware source via the rglob-count=1 mechanism.
ORACLE_MODULES = [
    "oracle_serial_replay",
    "oracle_serial_struct",
]


def _load_oracle(name):
    spec = importlib.util.spec_from_file_location(name, GOLDEN_DIR / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _firmware_sources():
    return [
        (p, p.read_text(encoding="utf-8", errors="ignore"))
        for p in sorted(FIRMWARE.rglob("*"))
        if p.suffix in (".cpp", ".h") and p.is_file()
    ]


def _raw_command_literals_in_comments(text):
    """Return [(lineno, literal), ...] for every `//` comment carrying a
    `strcmp(command_type, "<literal>")` whose literal is NOT a "<name>" placeholder.

    Shared by the real guard and its self-test so the proof exercises the SAME logic.
    Line comments only — the dispatcher comments in serial_cmd_handlers.cpp are all
    `//`; a real command literal inside a `/* */` block would still be caught by the
    count!=1 anchor-uniqueness test, which scans the whole file text."""
    out = []
    for lineno, line in enumerate(text.splitlines(), 1):
        pos = line.find("//")
        if pos < 0:
            continue
        comment = line[pos:]
        for m in re.finditer(r'strcmp\(command_type,\s*"([^"]*)"\)', comment):
            literal = m.group(1)
            if not literal.startswith("<"):
                out.append((lineno, literal))
    return out


def test_every_mutation_anchor_matches_exactly_once():
    """A count!=1 anchor can be MISSED (0) or masked by a decoy (>=2), silently
    blinding a Gate-Fα tooth. Assert the harness's count=1 rglob is unambiguous."""
    srcs = _firmware_sources()
    failures = []
    for oracle_name in ORACLE_MODULES:
        mod = _load_oracle(oracle_name)
        for entry in getattr(mod, "MUTATIONS", []):
            pattern = entry[0]
            desc = entry[2] if len(entry) > 2 else pattern
            total = sum(len(re.findall(pattern, txt)) for _, txt in srcs)
            if total != 1:
                failures.append(
                    f"{oracle_name}: anchor matches {total}x across firmware "
                    f"(expected 1) -> [{desc}]  pattern={pattern!r}"
                )
    assert not failures, (
        "Mutation anchor uniqueness violated — the Gate-Fα count=1 rglob is ambiguous; "
        "a decoy (comment/dup) can mask a real tooth:\n  " + "\n  ".join(failures)
    )


def test_dispatcher_comments_use_command_type_placeholder():
    """No comment in serial_cmd_handlers.cpp may carry a raw
    `strcmp(command_type, "<literal>")` — it must use the "<name>" placeholder. This is
    the direct cause of the 2026-06-25 preset defect; enforce it at the source so a
    real command literal in a comment can never again steal a count=1 mutation rglob."""
    handlers = FIRMWARE / "serial" / "serial_cmd_handlers.cpp"
    offenders = _raw_command_literals_in_comments(handlers.read_text(encoding="utf-8"))
    assert not offenders, (
        "serial_cmd_handlers.cpp comment carries a raw command literal that can steal a "
        "count=1 mutation rglob (preset-defect class) — use the \"<name>\" placeholder:\n"
        + "\n".join(f'  line {ln}: strcmp(command_type, "{lit}")' for ln, lit in offenders)
    )


def test_guard_itself_catches_a_decoy_comment():
    """Prove the guard is NOT blind (no reliance on reviewer memory): the SAME scan the
    real test uses must flag a synthetic decoy comment, and must NOT flag the approved
    "<name>" placeholder."""
    decoy = '    // keeps the branch `else if (strcmp(command_type, "preset") == 0)` intact\n'
    assert _raw_command_literals_in_comments(decoy) == [(1, "preset")], (
        "guard scan failed to flag a raw-literal decoy comment"
    )
    placeholder = '    // `else if (strcmp(command_type, "<name>") == 0)` opener\n'
    assert _raw_command_literals_in_comments(placeholder) == [], (
        "guard scan wrongly flagged the approved \"<name>\" placeholder"
    )
