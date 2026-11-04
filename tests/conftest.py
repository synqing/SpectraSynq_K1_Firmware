"""Ensure tests/ is importable so test modules can `from _fwpath import FwDir`."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))


def pytest_configure(config):
    # Lane R1 (DEF-001/DEF-002): `pytest -m tempo_gates` runs the tempo class gates M1-M5.
    config.addinivalue_line("markers", "tempo_gates: tempo-lock class gates M1-M5 (lane R1)")
