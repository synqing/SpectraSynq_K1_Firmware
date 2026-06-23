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
