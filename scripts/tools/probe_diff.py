#!/usr/bin/env python3
"""Prove a probe env actually differs from its base — before you measure anything.

HF-69 (2026-08-14): a DSR-clock "probe" env re-declared `-DK1_MIC_IM69D_DSR_16S_V1`, which
its base env ALREADY defined. It therefore built a functionally identical binary: there was
no variable under test. The null result was then written up as "inconclusive — confounded
legs", a plausible mechanism authored for an experiment that never existed.

A probe whose variable is already set everywhere cannot fail. This tool makes that
detectable in one second instead of a device session.

Usage:
  probe_diff.py <probe_env>                  # delta vs its `extends` base
  probe_diff.py <probe_env> <base_env>       # explicit pair
  probe_diff.py <probe_env> --expect FLAG    # assert FLAG is the (or a) differing flag
  probe_diff.py --self-test                  # prove this tool can go RED

Exit 0 = the envs differ in at least one build flag (and FLAG if --expect given).
Exit 1 = NO-OP PROBE, or the expected flag is not part of the delta.
Exit 2 = usage/parse error.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INI = ROOT / "platformio.ini"


def sections(text):
    out = {}
    for m in re.finditer(r"^\[env:([^\]]+)\]\n(.*?)(?=^\[|\Z)", text, re.M | re.S):
        out[m.group(1)] = m.group(2)
    return out


def option_flags(body, option):
    """Return -D names from one PlatformIO option and its indented continuations."""
    match = re.search(
        rf"^{re.escape(option)}\s*=\s*(.*(?:\n[ \t]+.*)*)",
        body,
        re.M,
    )
    if not match:
        return set()
    uncommented = "\n".join(
        line for line in match.group(1).splitlines()
        if not line.lstrip().startswith(("#", ";"))
    )
    return set(re.findall(r"-D([A-Za-z0-9_]+)", uncommented))


def effective_flags(env, secs, seen=None):
    """All -D flags for an env, resolved through the whole `extends` chain.

    Comment lines are stripped: prose mentioning a flag must not count as defining it,
    and prose is exactly where the HF-69 probe's justification lived.
    """
    seen = seen or set()
    if env in seen or env not in secs:
        return set()
    seen.add(env)
    body = secs[env]
    flags = set()
    ext = re.search(r"^extends\s*=\s*env:(\S+)", body, re.M)
    if ext:
        flags = effective_flags(ext.group(1), secs, seen)
    flags |= option_flags(body, "build_flags")
    flags -= option_flags(body, "build_unflags")
    return flags


def base_of(env, secs):
    m = re.search(r"^extends\s*=\s*env:(\S+)", secs.get(env, ""), re.M)
    return m.group(1) if m else None


def compare(probe, base, secs, expect=None, quiet=False):
    for e in (probe, base):
        if e not in secs:
            print(f"probe_diff: unknown env '{e}'")
            return 2
    pf, bf = effective_flags(probe, secs), effective_flags(base, secs)
    added, removed = sorted(pf - bf), sorted(bf - pf)
    if not quiet:
        print(f"probe : {probe}")
        print(f"base  : {base}")
        print(f"added   ({len(added)}): {added if added else '—'}")
        print(f"removed ({len(removed)}): {removed if removed else '—'}")
    if not added and not removed:
        if not quiet:
            print("\n✗ NO-OP PROBE — the two envs resolve to identical build flags.")
            print("  There is no variable under test. Any result from this pair is")
            print("  meaningless, and a null result must NOT be explained as a finding.")
        return 1
    if expect and expect not in (set(added) | set(removed)):
        if not quiet:
            print(f"\n✗ '{expect}' is NOT part of the delta — it is already defined in the")
            print("  base chain, or is not set here at all. This is the HF-69 shape.")
        return 1
    if not quiet:
        print("\n✓ probe differs from base" + (f" in {expect}" if expect else ""))
    return 0


SELF_TEST_INI = """
[env:base]
build_flags = -DA -DB

[env:noop_probe]
extends = env:base
build_flags =
    ${env:base.build_flags}
    -DB

[env:real_probe]
extends = env:base
build_flags =
    ${env:base.build_flags}
    -DC

[env:comment_probe]
extends = env:base
# -DD is only mentioned in prose here
build_flags =
    ${env:base.build_flags}

[env:unflag_probe]
extends = env:base
build_unflags =
    -DB
build_flags =
    ${env:base.build_flags}
    -DC
"""


def self_test():
    """A fault battery. Cases expected to be RED must be OBSERVED going red, or the
    tool is only documentation (HF-80)."""
    secs = sections(SELF_TEST_INI)
    cases = [
        ("noop_probe", "base", None, 1, "re-declares a flag the base already defines"),
        ("real_probe", "base", None, 0, "adds a genuinely new flag"),
        ("real_probe", "base", "C", 0, "expected flag is in the delta"),
        ("real_probe", "base", "B", 1, "expected flag is already in the base"),
        ("comment_probe", "base", None, 1, "flag mentioned only in a comment"),
        ("unflag_probe", "base", "B", 0, "removes an inherited flag"),
        ("unflag_probe", "base", "C", 0, "adds while removing an inherited flag"),
    ]
    ok = True
    for probe, base, expect, want, why in cases:
        got = compare(probe, base, secs, expect, quiet=True)
        mark = "ok " if got == want else "FAIL"
        if got != want:
            ok = False
        print(f"  [{mark}] {probe:14s} expect={str(expect):5s} "
              f"want={want} got={got}   ({why})")
    print("\nself-test:", "PASS — the tool can go red for the right reasons" if ok
          else "FAIL — this tool cannot be trusted")
    return 0 if ok else 1


def main():
    args = [a for a in sys.argv[1:]]
    if "--self-test" in args:
        sys.exit(self_test())
    expect = None
    if "--expect" in args:
        i = args.index("--expect")
        try:
            expect = args[i + 1]
        except IndexError:
            print("probe_diff: --expect needs a flag name")
            sys.exit(2)
        del args[i:i + 2]
    if not args:
        print(__doc__)
        sys.exit(2)
    secs = sections(INI.read_text(encoding="utf-8"))
    probe = args[0]
    base = args[1] if len(args) > 1 else base_of(probe, secs)
    if base is None:
        print(f"probe_diff: '{probe}' has no `extends` — give an explicit base env")
        sys.exit(2)
    sys.exit(compare(probe, base, secs, expect))


if __name__ == "__main__":
    main()
