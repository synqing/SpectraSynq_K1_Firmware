#!/usr/bin/env python3
"""Shared host-compile-and-run substrate for the golden-master oracle (Phase F / L1).

Compiles real firmware ``.cpp`` on the host against a minimal ``Arduino.h`` shim
plus a numeric-emitting C++ driver, runs it, and returns stdout. This is the
trusted substrate the behaviour-equivalence oracle rides on; it reuses the exact
host-compile pattern already proven by ``scripts/regression-harness/*_replay.py``.

Determinism contract:
- Compiled at ``-O0`` (NOT the production ``-O3 -ffast-math``) so the reference
  is clean IEEE arithmetic. The oracle locks ALGORITHM STRUCTURE, which is what a
  behaviour-preserving refactor must keep identical. ``-ffast-math`` numeric
  policy is a separate, ticketed concern (see the audit).
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "SPECTRASYNQ_K1_FIRMWARE").is_dir())
FIRMWARE = ROOT / "SPECTRASYNQ_K1_FIRMWARE"

# Minimal Arduino/ESP shim: just enough for the DSP TUs to compile off-device.
ARDUINO_STUB = r"""
#pragma once
#include <stdint.h>
struct portMUX_TYPE {};
#define portMUX_INITIALIZER_UNLOCKED portMUX_TYPE{}
static inline void portENTER_CRITICAL(portMUX_TYPE*) {}
static inline void portEXIT_CRITICAL(portMUX_TYPE*) {}
"""


def _include_dirs():
    return [d for d in sorted(FIRMWARE.iterdir()) if d.is_dir()]


def find_compiler(preferred=None):
    return preferred or shutil.which("clang++") or shutil.which("g++")


def host_compile_run(module_cpps, driver_cpp, defines=(), compiler=None, firmware_root=None):
    """Compile ``module_cpps`` + ``driver_cpp`` and run the result.

    Returns ``(returncode, stdout, stderr)``. ``firmware_root`` lets the harness
    self-test point the include/source resolution at a mutated *copy* of the
    firmware tree without touching the real one.
    """
    firmware = Path(firmware_root) if firmware_root else FIRMWARE
    cxx = find_compiler(compiler)
    if not cxx:
        raise RuntimeError("no C++ compiler (clang++/g++) found on PATH")

    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        stub = work / "stub"
        stub.mkdir()
        (stub / "Arduino.h").write_text(ARDUINO_STUB, encoding="utf-8")
        driver = work / "driver.cpp"
        driver.write_text(driver_cpp, encoding="utf-8")
        binary = work / "oracle_bin"

        srcs = [str(next(firmware.rglob(name))) for name in module_cpps]
        cmd = [cxx, "-std=c++17", "-O0", *[f"-D{d}" for d in defines],
               "-I", str(stub), "-I", str(firmware)]
        for d in sorted(p for p in firmware.iterdir() if p.is_dir()):
            cmd += ["-I", str(d)]
        cmd += srcs + [str(driver), "-o", str(binary)]

        c = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
        if c.returncode != 0:
            return c.returncode, c.stdout, "COMPILE-ERROR:\n" + c.stderr
        r = subprocess.run([str(binary)], cwd=ROOT, text=True, capture_output=True)
        return r.returncode, r.stdout, r.stderr
