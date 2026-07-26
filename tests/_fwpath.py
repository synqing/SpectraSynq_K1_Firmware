"""Subdir-agnostic resolver for K1 firmware sources (Phase 1 restructure).

The firmware moved from a flat SPECTRASYNQ_K1_FIRMWARE/ into functional subdirs
(docs/refactor/k1-firmware-restructure-and-rebrand-plan.md). Tests that read
firmware files by name go through FwDir so they survive the move — and the later
Phase-4 folder rename (only the base path changes, in one place).

    FW = FwDir(ROOT / "SPECTRASYNQ_K1_FIRMWARE")
    text = (FW / "serial_menu.h").read_text()   # -> .../serial/serial_menu.h
    for p in FW.iterdir(): ...                   # recurses into subdirs
"""
import re
from pathlib import Path


class FwDir:
    def __init__(self, base):
        self._base = Path(base)

    def __truediv__(self, name):
        direct = self._base / name
        if direct.exists():
            return direct
        hits = sorted(self._base.rglob(Path(name).name))
        return hits[0] if hits else direct  # fall back to direct path for clear errors

    # Source files now live in subdirs, so directory walks must recurse.
    def iterdir(self):
        return (p for p in self._base.rglob("*") if p.is_file())

    def glob(self, pattern):
        return self._base.rglob(pattern)

    def rglob(self, pattern):
        return self._base.rglob(pattern)

    def exists(self):
        return self._base.exists()

    def __fspath__(self):
        return str(self._base)

    @property
    def base(self):
        return self._base


def read_serial_menu_surface(fw: FwDir) -> str:
    """serial_menu.h + serial_menu.cpp + serial_typed_dispatch.cpp (M2.1 R1/R2).
    Host/static tests that grep the serial command surface must search all three —
    the header is declarations + dispatch tables; bodies/handlers live in the .cpp TUs."""
    parts = [(fw / "serial_menu.h").read_text(encoding="utf-8")]
    for name in ("serial_menu.cpp", "serial_typed_dispatch.cpp", "serial_typed_cmd_table.def"):
        cpp = fw / name
        if cpp.exists():
            parts.append(cpp.read_text(encoding="utf-8"))
    return "\n".join(parts)


def read_serial_dispatch_surface(fw: FwDir) -> str:
    """Full typed-command dispatch surface: menu + typed dispatch + handlers + table."""
    parts = [read_serial_menu_surface(fw)]
    handlers = fw / "serial_cmd_handlers.cpp"
    if handlers.exists():
        parts.append(handlers.read_text(encoding="utf-8"))
    table = fw / "serial_typed_cmd_table.def"
    if table.exists():
        parts.append(table.read_text(encoding="utf-8"))
    return "\n".join(parts)


def typed_command_registered(surface: str, command_type: str) -> bool:
    """True if command is registered in the R2 typed table or legacy strcmp ladder."""
    if f'SERIAL_TYPED_CMD("{command_type}"' in surface:
        return True
    return f'strcmp(command_type, "{command_type}")' in surface


def typed_command_handler_body(surface: str, command_type: str) -> str:
    """Return handler body for a typed command (R2 handler fn or legacy strcmp branch)."""
    ladder = f'else if (strcmp(command_type, "{command_type}") == 0)'
    start = surface.find(ladder)
    if start >= 0:
        i = surface.find("{", start + len(ladder))
        depth = 1
        pos = i + 1
        while pos < len(surface) and depth:
            c = surface[pos]
            if c in "\"'":
                quote = c
                pos += 1
                while pos < len(surface) and surface[pos] != quote:
                    if surface[pos] == "\\":
                        pos += 1
                    pos += 1
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
            pos += 1
        return surface[start:pos]

    row = re.search(
        rf'SERIAL_TYPED_CMD\("{re.escape(command_type)}"\s*,\s*(\w+)',
        surface,
    )
    if not row:
        raise AssertionError(f"missing typed command handler for {command_type}")
    handler = row.group(1)
    marker = f"bool {handler}("
    start = surface.find(marker)
    if start < 0:
        raise AssertionError(f"missing handler function {handler} for {command_type}")
    i = surface.find("{", start)
    depth = 1
    pos = i + 1
    while pos < len(surface) and depth:
        c = surface[pos]
        if c in "\"'":
            quote = c
            pos += 1
            while pos < len(surface) and surface[pos] != quote:
                if surface[pos] == "\\":
                    pos += 1
                pos += 1
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        pos += 1
    return surface[start:pos]


def compile_guarded_typed_row(surface: str, guard: str, command_type: str) -> bool:
    """True if guard wraps a SERIAL_TYPED_CMD row or legacy strcmp branch."""
    legacy = (
        rf"(?s)#(?:if|ifdef)\s+{re.escape(guard)}\s*\n"
        rf".*?else if \(strcmp\(command_type, \"{re.escape(command_type)}\"\) == 0\)"
        rf".*?#endif"
    )
    if re.search(legacy, surface):
        return True
    typed = (
        rf"(?s)#(?:if|ifdef)\s+{re.escape(guard)}\s*\n"
        rf".*?SERIAL_TYPED_CMD\(\"{re.escape(command_type)}\""
        rf".*?#endif"
    )
    return re.search(typed, surface) is not None
