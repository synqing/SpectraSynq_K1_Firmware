"""Ensure tests/ is importable so test modules can `from _fwpath import FwDir`."""
import os
import sys
import subprocess

sys.path.insert(0, os.path.dirname(__file__))


def pytest_configure(config):
    # Lane R1 (DEF-001/DEF-002): `pytest -m tempo_gates` runs the tempo class gates M1-M5.
    config.addinivalue_line("markers", "tempo_gates: tempo-lock class gates M1-M5 (lane R1)")
    if sys.platform == "darwin" and hasattr(subprocess, "_PIPE_BUF"):
        # On this macOS host, 512-byte writes can block after pipe readiness
        # while the child waits for its stdout to drain. Reproduced outside
        # pytest on Python 3.12 and 3.14. Single-byte writes preserve the exact
        # protocol and let communicate() drain both directions. Session-local;
        # firmware, test inputs, assertions and other processes are unchanged.
        config._k1_original_pipe_buf = subprocess._PIPE_BUF
        subprocess._PIPE_BUF = 1


def pytest_unconfigure(config):
    if hasattr(config, "_k1_original_pipe_buf"):
        subprocess._PIPE_BUF = config._k1_original_pipe_buf
