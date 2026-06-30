#!/usr/bin/env python3
"""Lane N5 release manifest generator (READ-ONLY, PRINT-ONLY).

Produces a release manifest for a K1 firmware tag and PRINTS the exact
``git-tag -a`` command for the Captain to run. This script NEVER creates a tag
and NEVER pushes: tag creation/push is a Captain-gated (D-class) action. It only
reads the tree and prints.

What it does:
  1. Reads ``FIRMWARE_VERSION`` from the .ino.
  2. Reads the current short commit (``git rev-parse --short HEAD``); degrades to
     "unknown" if git is unavailable — it is a manifest, not a gate.
  3. Asserts CHANGELOG.md carries non-empty content under ``## [Unreleased]``
     (a release with an empty changelog is refused).
  4. Prints a manifest: version, derived tag, commit, default prod env, date,
     and the latest device-build-registry deployed-state line.
  5. Prints the exact ``git-tag -a v<MAJOR>.<MINOR>.<PATCH> -m "..."`` command
     the Captain runs by hand.

Usage:  python3 scripts/release/make_release.py
Exit:   0 on a clean manifest; non-zero only if a precondition fails (e.g. an
        empty [Unreleased] changelog, or the .ino version cannot be read).
"""
from __future__ import annotations

import datetime
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INO = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "SPECTRASYNQ_K1_FIRMWARE.ino"
CHANGELOG = ROOT / "CHANGELOG.md"
DEVICE_REGISTRY = ROOT / "docs" / "hardware" / "device-build-registry.md"
DEFAULT_PROD_ENV = "k1_hardware"


def read_firmware_version() -> int:
    """Parse the integer from `#define FIRMWARE_VERSION <int>` in the .ino."""
    text = INO.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"#define\s+FIRMWARE_VERSION\s+(\d+)", text)
    if not m:
        raise SystemExit("make_release: could not find FIRMWARE_VERSION in %s" % INO)
    return int(m.group(1))


def derive_semver(version: int) -> str:
    """Map the packed FIRMWARE_VERSION integer to a vMAJOR.MINOR.PATCH tag.

    The firmware versions as a packed decimal: 40103 -> 4.01.03 -> v4.1.3.
    Convention (last two digit-pairs are minor/patch); printed in the manifest
    so the Captain can override if a release wants a different semver.
    """
    s = str(version)
    if len(s) >= 5:
        major = int(s[:-4])
        minor = int(s[-4:-2])
        patch = int(s[-2:])
    elif len(s) >= 3:
        major = int(s[:-4] or "0")
        minor = int(s[-4:-2] or "0")
        patch = int(s[-2:])
    else:
        major, minor, patch = 0, 0, version
    return "v%d.%d.%d" % (major, minor, patch)


def short_commit() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(ROOT),
            stderr=subprocess.DEVNULL,
        )
        return out.strip().decode("utf-8", "replace") or "unknown"
    except Exception:
        return "unknown"


def unreleased_changelog_body() -> str:
    """Return the text under `## [Unreleased]` up to the next `## ` heading."""
    if not CHANGELOG.exists():
        raise SystemExit("make_release: CHANGELOG.md not found at %s" % CHANGELOG)
    text = CHANGELOG.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"^##\s*\[Unreleased\]\s*$", text, re.MULTILINE | re.IGNORECASE)
    if not m:
        raise SystemExit("make_release: no '## [Unreleased]' heading in CHANGELOG.md")
    rest = text[m.end():]
    nxt = re.search(r"^##\s+", rest, re.MULTILINE)
    return (rest[: nxt.start()] if nxt else rest).strip()


def latest_deployed_state_line() -> str:
    """Return the first data row under '## 2. Deployed state' in the registry."""
    if not DEVICE_REGISTRY.exists():
        return "(device-build-registry not found at %s)" % DEVICE_REGISTRY
    text = DEVICE_REGISTRY.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"^##\s*2\..*Deployed state.*$", text, re.MULTILINE)
    if not m:
        return "(no '## 2. Deployed state' section in registry)"
    for line in text[m.end():].splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue
        if set(s) <= set("|-: "):  # markdown separator row
            continue
        if s.lower().startswith("| device"):  # header row
            continue
        # Compact to the leading columns (Device | Commit | Build/env); the full
        # row carries paragraphs of soak evidence not wanted in a one-line manifest.
        cols = [c.strip() for c in s.strip("|").split("|")]
        head = " | ".join(cols[:3]) if len(cols) >= 3 else s
        return (head[:200] + " …") if len(head) > 200 else head
    return "(no deployed-state rows found in registry)"


def main() -> int:
    version = read_firmware_version()
    tag = derive_semver(version)
    commit = short_commit()
    body = unreleased_changelog_body()
    if not body:
        raise SystemExit(
            "make_release: '## [Unreleased]' in CHANGELOG.md is empty — "
            "a release needs documented changes. Refusing to emit a manifest."
        )
    today = datetime.date.today().isoformat()
    deployed = latest_deployed_state_line()
    changelog_lines = len([ln for ln in body.splitlines() if ln.strip()])

    print("=" * 72)
    print("K1 FIRMWARE RELEASE MANIFEST (read-only — no tag is created)")
    print("=" * 72)
    print("  FIRMWARE_VERSION : %d" % version)
    print("  proposed tag     : %s   (override at the git tag step if needed)" % tag)
    print("  commit           : %s" % commit)
    print("  prod env         : %s" % DEFAULT_PROD_ENV)
    print("  date             : %s" % today)
    print("  changelog        : %d non-empty line(s) under [Unreleased]" % changelog_lines)
    print("  deployed-state   : %s" % deployed)
    print("-" * 72)
    print("CAPTAIN ACTION — run this by hand to cut the tag (this script will NOT):")
    print()
    print('  git tag -a %s %s -m "K1 firmware %s (FIRMWARE_VERSION %d)"'
          % (tag, commit, tag, version))
    print()
    print("  (then, when ready and authorised, publish it — that step is yours.)")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
