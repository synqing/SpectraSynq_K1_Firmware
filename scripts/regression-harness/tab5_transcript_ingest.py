#!/usr/bin/env python3
"""Normalize Tab5 harness evidence logs into tests/fixtures/tab5/."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FIXTURES = REPO / "tests" / "fixtures" / "tab5"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_log", type=Path, help="evidence/.../tab5_serial.log")
    parser.add_argument("--name", required=True, help="fixture basename without path")
    args = parser.parse_args()

    FIXTURES.mkdir(parents=True, exist_ok=True)
    dest = FIXTURES / args.name
    shutil.copy2(args.source_log, dest)
    manifest_path = FIXTURES / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["fixture"] = args.name
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
