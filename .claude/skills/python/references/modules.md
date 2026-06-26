# Python Modules Reference

## Contents
- Project module structure (tests/, tools/)
- conftest.py placement and scope
- Import discipline
- Key third-party modules in use
- Adding new tooling modules

---

## Project Module Structure

```
tests/
  conftest.py                     # project-wide fixtures
  test_sb_tab5_wireless_controller_static.py
  test_tab5_dashboard_harness.py
  tab5_harness_spec/              # spec-driven harness tests
  fixtures/tab5/                  # test fixture data
tools/
  tab5_k1_dashboard_harness.py    # diagnostic dashboard harness
scripts/
  regression-harness/
    tab5_transcript_ingest.py     # transcript replay ingestion
    fixtures/wireless_ab_stimulus.wav
```

Tests live in `tests/`. Reusable harness tooling lives in `tools/`. Scripts for one-off or CI operations live in `scripts/`.

---

## conftest.py Placement and Scope

pytest discovers `conftest.py` hierarchically. Place fixtures at the highest scope they're needed:

```
tests/conftest.py           # shared across ALL test files
tests/tab5_harness_spec/conftest.py  # shared within that subdirectory only
```

```python
# tests/conftest.py — project-wide audio frame fixtures
import pytest
import numpy as np

@pytest.fixture(scope="session")
def sample_rate() -> int:
    return 48000

@pytest.fixture
def silence_frame(sample_rate) -> np.ndarray:
    return np.zeros(96, dtype=np.float32)
```

Use `scope="session"` for expensive fixtures (loaded WAV files, compiled harness paths). Use default `scope="function"` for mutable state that must not leak between tests.

---

## Import Discipline

Only import what the file uses. Do not wildcard-import (`from module import *`) — it pollutes namespace and makes grep for symbols unreliable.

```python
# GOOD
import numpy as np
from pathlib import Path
import subprocess

# BAD
from numpy import *   # shadows builtins like 'any', 'all', 'sum'
```

For project-local modules in `tools/`, add `tests/` parent to sys.path via `conftest.py`:

```python
# tests/conftest.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))
```

---

## Key Third-Party Modules in Use

| Module | Purpose | Notes |
|--------|---------|-------|
| `pytest` | Test runner and fixture system | See the **pytest** skill |
| `numpy` | Audio frame math, bin arrays, LED color arrays | Always specify dtype |
| `pathlib.Path` | File paths (prefer over `os.path`) | Cross-platform, chainable |
| `subprocess` | Invoke PIO build, run harness binaries | Use `capture_output=True` |
| `json` | Parse harness stdout as structured metrics | Validate schema with TypedDict |
| `struct` | Binary frame parsing from firmware log files | Use `struct.unpack_from` |
| `aiofiles` | Async fixture file loading (optional) | See the **aiofiles** skill |

---

## WARNING: Circular Imports in Test Helpers

**The Problem:**
Splitting test helpers into multiple modules and having them import each other causes `ImportError` at collection time — pytest fails before running a single test.

**The Fix:**
Keep test helpers flat. If `tests/helpers/audio.py` and `tests/helpers/firmware.py` both need shared types, extract the types to `tests/helpers/types.py` and import from there. Never import a test file from another test file.

---

## Adding New Tooling Modules

When adding a new script to `tools/` or `scripts/`:

1. Add a module docstring stating purpose and expected inputs/outputs
2. Guard executable code with `if __name__ == "__main__":`
3. Accept paths via `argparse`, never hardcode absolute paths
4. Return exit code 0 on success, non-zero on failure (CI-compatible)

```python
# new code to add — tools/my_new_tool.py
"""Parse firmware trace output and emit CSV metrics."""
import argparse
from pathlib import Path

def main(input_path: Path, output_path: Path) -> int:
    ...
    return 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    raise SystemExit(main(args.input, args.output))
```