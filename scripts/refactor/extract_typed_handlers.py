#!/usr/bin/env python3
"""Extract Stage-B strcmp arms from serial_menu.cpp into typed handler stubs."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MENU_CPP = ROOT / "SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.cpp"

START = "    // Now react accordingly:"
END = "    // Add backward compatibility for old commands"

DISPATCH_RE = re.compile(
    r"else if \(serial_cmd_dispatch_(\w+)\(command_type, command_data\)\) \{\s*\n\s*// handled[^\n]*\n\s*\}"
)

def main() -> None:
    text = MENU_CPP.read_text(encoding="utf-8")
    start = text.index(START)
    end = text.index(END, start)
    ladder = text[start:end]

    # Remove dispatch fan-out blocks (replaced by table wrappers)
    ladder = DISPATCH_RE.sub("", ladder)

    # Convert if/else if strcmp arms to function bodies
    arms = re.split(r"\n    (?=else if \(strcmp\(command_type,)", ladder)
    print(f"Found {len(arms)} arm chunks")

if __name__ == "__main__":
    main()
