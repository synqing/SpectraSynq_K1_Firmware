#!/usr/bin/env python3
"""Convert the K1 sketch (.ino) to C++ for the ESP-IDF build, as PlatformIO's converter does.

PlatformIO compiles <sketch>.ino.cpp: `#include <Arduino.h>`, the sketch text, and forward
declarations of the sketch's own functions inserted before the first function definition,
with #line directives so diagnostics point at the .ino. This does the same, declaring only
functions the sketch uses before it defines them (the rest need no declaration).

usage: k1_ino_to_cpp.py <sketch.ino> <out.cpp>
"""
import re
import sys
from pathlib import Path

DEF = re.compile(
    r"^(?!(?:if|for|while|switch|return|else|do|case|typedef|struct|class|enum|namespace)\b)"
    r"([A-Za-z_][\w:<>,\s\*&]*?[\s\*&])([A-Za-z_]\w*)\s*\("
    r"([^;{}()]*(?:\([^()]*\)[^;{}()]*)*)\)\s*(?:const\s*)?\{",
    re.M)


def convert(ino: Path) -> str:
    text = ino.read_text()
    defs = []
    for m in DEF.finditer(text):
        line = text.count("\n", 0, m.start()) + 1
        defs.append((m.start(), line, " ".join(m.group(1).split()), m.group(2), " ".join(m.group(3).split())))
    if not defs:
        raise SystemExit(f"k1_ino_to_cpp: no function definitions found in {ino}")
    first_pos, first_line = defs[0][0], defs[0][1]
    protos = []
    for pos, _line, ret, name, args in defs:
        if re.search(r"\b%s\b" % re.escape(name), text[:pos]):
            protos.append(f"{ret} {name}({args});")
    lines = text.splitlines(keepends=True)
    q = str(ino).replace("\\", "\\\\").replace('"', '\\"')
    head = "".join(lines[: first_line - 1])
    tail = "".join(lines[first_line - 1:])
    return ("#include <Arduino.h>\n"
            f'#line 1 "{q}"\n' + head
            + "\n".join(protos) + ("\n" if protos else "")
            + f'#line {first_line} "{q}"\n' + tail)


def main() -> int:
    ino, out = Path(sys.argv[1]), Path(sys.argv[2])
    data = convert(ino)
    if not out.exists() or out.read_text() != data:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(data)
    return 0


if __name__ == "__main__":
    sys.exit(main())
