#!/usr/bin/env python3
"""Move non-inline function/variable definitions from serial_menu.h -> serial_menu.cpp."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HEADER = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "serial" / "serial_menu.h"
CPP = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "serial" / "serial_menu.cpp"

SKIP = frozenset(
    {
        "serial_table_all_have_handlers",
        "serial_cstr_eq",
        "serial_table_no_duplicate_names",
        "serial_table_no_dangerous_hotkey",
    }
)

DEF_RE = re.compile(r"^\s*(?:const\s+)?[\w\s\*]+\s+(\w+)\s*\([^)]*\)\s*\{\s*$")
VAR_RE = re.compile(r"^bool\s+(TEMPO_STREAM_ENABLED)\s*=")


def brace_close(text: str, open_i: int) -> int:
    depth = 0
    i = open_i
    sq = dq = bc = lc = 0
    while i < len(text):
        c = text[i]
        if lc:
            if c == "\n":
                lc = 0
            i += 1
            continue
        if bc:
            if c == "*" and i + 1 < len(text) and text[i + 1] == "/":
                bc = 0
                i += 2
                continue
            i += 1
            continue
        if dq:
            if c == "\\":
                i += 2
                continue
            if c == '"':
                dq = 0
            i += 1
            continue
        if sq:
            if c == "\\":
                i += 2
                continue
            if c == "'":
                sq = 0
            i += 1
            continue
        if c == "/" and i + 1 < len(text):
            if text[i + 1] == "/":
                lc = 1
                i += 2
                continue
            if text[i + 1] == "*":
                bc = 1
                i += 2
                continue
        if c == '"':
            dq = 1
            i += 1
            continue
        if c == "'":
            sq = 1
            i += 1
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise ValueError("unbalanced")


def line_starts(text: str) -> list[int]:
    starts = [0]
    for i, c in enumerate(text):
        if c == "\n":
            starts.append(i + 1)
    return starts


def line_index(starts: list[int], pos: int) -> int:
    lo, hi = 0, len(starts) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if starts[mid] <= pos:
            lo = mid + 1
        else:
            hi = mid - 1
    return hi


def immediate_if_wrapper(lines: list[str], start: int, end: int) -> tuple[int, int]:
    """Include only a tight #if..#endif that wraps this definition alone."""
    j = start - 1
    while j >= 0 and lines[j].strip() == "":
        j -= 1
    if j < 0 or not lines[j].lstrip().startswith("#if"):
        return start, end
    k = end + 1
    while k < len(lines) and lines[k].strip() == "":
        k += 1
    if k < len(lines) and lines[k].lstrip().startswith("#endif"):
        return j, k
    return start, end


def to_decl(sig: str) -> str:
    sig = sig.strip()
    if sig.endswith("{"):
        sig = sig[:-1].rstrip()
    if "TEMPO_STREAM_ENABLED" in sig:
        return "extern bool TEMPO_STREAM_ENABLED;"
    return sig + ";"


def find_defs(text: str) -> list[tuple[int, int, str, str]]:
    lines = text.splitlines()
    starts = line_starts(text)
    spans: list[tuple[int, int, str, str]] = []
    for li, line in enumerate(lines):
        st = line.lstrip()
        if st.startswith("static ") or "constexpr" in st:
            continue
        vm = VAR_RE.match(st)
        if vm:
            name = vm.group(1)
            end_li = li
            while end_li < len(lines) and ";" not in lines[end_li]:
                end_li += 1
            s, e = immediate_if_wrapper(lines, li, end_li)
            spans.append((s, e, name, lines[li].rstrip()))
            continue
        m = DEF_RE.match(st)
        if not m:
            continue
        name = m.group(1)
        if name in SKIP:
            continue
        open_pos = starts[li] + line.index("{")
        close_pos = brace_close(text, open_pos)
        end_li = line_index(starts, close_pos)
        s, e = immediate_if_wrapper(lines, li, end_li)
        spans.append((s, e, name, lines[li].rstrip()))
    spans.sort()
    merged: list[tuple[int, int, str, str]] = []
    for sp in spans:
        if merged and sp[0] <= merged[-1][1]:
            continue
        merged.append(sp)
    return merged


def apply_move(header: str, cpp: str, spans: list[tuple[int, int, str, str]]) -> tuple[str, str, list[str]]:
    lines = header.splitlines(keepends=True)
    names: list[str] = []
    chunks: list[str] = []
    for s, e, name, sig in reversed(spans):
        block_lines = lines[s : e + 1]
        block = "".join(block_lines)
        if (
            block_lines
            and block_lines[0].lstrip().startswith("#if")
            and block_lines[-1].lstrip().startswith("#endif")
        ):
            decl_block = block_lines[0] + to_decl(sig) + "\n" + block_lines[-1]
        else:
            decl_block = to_decl(sig) + "\n"
        lines[s : e + 1] = [decl_block]
        chunks.insert(0, block if block.endswith("\n") else block + "\n\n")
        names.insert(0, name)
    marker = "// --- R1 bulk move (r1_move_serial_menu_defs.py) ---\n"
    end_marker = "// --- end R1 bulk move ---\n"
    if marker.strip() in cpp:
        pre, _, rest = cpp.partition(marker)
        _, _, post = rest.partition(end_marker)
        cpp = pre + marker + "".join(chunks) + end_marker + post
    else:
        cpp = cpp.rstrip() + "\n\n" + marker + "".join(chunks) + end_marker
    return "".join(lines), cpp, names


def main() -> int:
    header = HEADER.read_text(encoding="utf-8")
    cpp = CPP.read_text(encoding="utf-8")
    spans = find_defs(header)
    # skip already-declaration-only header
    if not spans:
        print("no definitions found")
        return 1
    new_h, new_cpp, names = apply_move(header, cpp, spans)
    HEADER.write_text(new_h, encoding="utf-8")
    CPP.write_text(new_cpp, encoding="utf-8")
    print(f"moved {len(names)} items")
    return 0


if __name__ == "__main__":
    sys.exit(main())
