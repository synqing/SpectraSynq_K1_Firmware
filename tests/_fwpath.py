"""Subdir-agnostic resolver for K1 firmware sources (Phase 1 restructure).

The firmware moved from a flat SPECTRASYNQ_K1_FIRMWARE/ into functional subdirs
(docs/refactor/k1-firmware-restructure-and-rebrand-plan.md). Tests that read
firmware files by name go through FwDir so they survive the move — and the later
Phase-4 folder rename (only the base path changes, in one place).

    FW = FwDir(ROOT / "SPECTRASYNQ_K1_FIRMWARE")
    text = (FW / "serial_menu.h").read_text()   # -> .../serial/serial_menu.h
    for p in FW.iterdir(): ...                   # recurses into subdirs
"""
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
    """serial_menu.h + serial_menu.cpp (M2.1 R1 bulk move). Host/static tests that
    grep the serial command surface must search both — the header is declarations
    + dispatch table only after R1 close-out."""
    parts = [(fw / "serial_menu.h").read_text(encoding="utf-8")]
    cpp = fw / "serial_menu.cpp"
    if cpp.exists():
        parts.append(cpp.read_text(encoding="utf-8"))
    return "\n".join(parts)
