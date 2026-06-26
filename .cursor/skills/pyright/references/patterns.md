# Pyright Patterns Reference

## Contents
- Configuring pyright for this project
- Numpy/scipy type patterns
- Anti-patterns
- Common errors and fixes

---

## Configuring Pyright for This Project

The host Python layer lives in `tests/`, `scripts/`, and `notebooks/`. These mix pytest fixtures, numpy-heavy DSP helpers, and ingest scripts — each with different annotation needs.

Recommended `pyrightconfig.json` at repo root (new code to add):

```json
{
  "include": ["tests", "scripts", "notebooks"],
  "exclude": ["**/__pycache__", ".pio", ".venv"],
  "typeCheckingMode": "standard",
  "reportMissingImports": true,
  "reportMissingTypeStubs": false,
  "pythonVersion": "3.9",
  "venvPath": ".",
  "venv": ".venv"
}
```

Set `reportMissingTypeStubs: false` because several C-extension modules (FastLED simulator stubs, serial libs) lack stubs and will produce noise at `strict`.

---

## Numpy / Scipy Type Patterns

Use `numpy.typing` (available numpy >= 1.20) for all array annotations. Avoid bare `np.ndarray` — it loses dtype information and produces `Unknown` downstream.

```python
# GOOD
from numpy.typing import NDArray
import numpy as np

def band_rms(frames: NDArray[np.float32]) -> np.float32: ...

# BAD — pyright treats np.ndarray as NDArray[Any], defeating type checking
def band_rms(frames: np.ndarray) -> float: ...
```

For scipy functions that return `ndarray` with unknown dtype:

```python
from numpy.typing import NDArray
import numpy as np
from scipy.signal import butter, sosfilt

def make_bandpass(lo: float, hi: float, fs: float) -> NDArray[np.float64]:
    sos = butter(4, [lo, hi], btype="band", fs=fs, output="sos")
    return sos  # pyright: ignore[reportReturnType]  # scipy stubs incomplete
```

---

## TypedDict for Packet / Frame Structs

`diag_helpers.py` and `apstream_ingest.py` pass dicts between stages. Untyped dicts become `dict[str, Any]` and propagate Unknown everywhere. Use `TypedDict` at module level:

```python
# new code to add — diag_helpers.py
from typing import TypedDict

class TempoFrame(TypedDict):
    ts_ms: int
    bpm: float
    confidence: float
    locked: bool

class OnsetEvent(TypedDict):
    ts_ms: int
    band: int
    flux: float
```

Then annotate parser return types:

```python
def parse_tempo_line(line: str) -> TempoFrame | None: ...
```

---

### WARNING: Bare `dict` for Structured Packets

**The Problem:**

```python
# BAD — dict[str, Any] silences all downstream type errors
def parse_packet(raw: bytes) -> dict:
    return {"ts": ..., "bpm": ..., "locked": ...}
```

**Why This Breaks:**
1. Callers can access any key without pyright complaining — typos (`"locekd"`) go undetected until runtime.
2. Refactoring field names requires grep; there's no static guarantee callers are updated.
3. In regression harnesses where 136+ test cases run offline, a silent key mismatch produces wrong metrics rather than a hard failure.

**The Fix:** Use `TypedDict` (above).

---

## Optional Fields and `total=False`

For packets where some fields are conditionally present:

```python
class OnsetPacketOptional(TypedDict, total=False):
    phase_lock_ms: int  # only present when PLL is locked
```

Or use `Required`/`NotRequired` (Python 3.11+, or `typing_extensions`):

```python
from typing import Required, NotRequired

class TempoFrame(TypedDict):
    ts_ms: Required[int]
    bpm: Required[float]
    phase_offset: NotRequired[float]
```

---

## Type Narrowing Instead of `# type: ignore`

```python
# BAD — suppresses the error but hides real bugs
val = config.get("threshold")  # type: ignore

# GOOD — narrows explicitly
val = config.get("threshold")
if not isinstance(val, float):
    raise ValueError(f"threshold must be float, got {type(val)}")
use_threshold(val)  # pyright now knows val: float
```

---

## Common Errors and Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `reportUnknownVariableType` on scipy return | Incomplete stubs | `pyright: ignore` on that line only |
| `reportMissingModuleSource` for `.pyd` | C extension, no source | `reportMissingModuleSource: false` in config |
| `Cannot access member X for type None` | Unguarded optional | Add `assert x is not None` or `if x is None: return` |
| `Type NDArray[float32] not assignable to NDArray[float64]` | Dtype mismatch | Cast with `.astype(np.float64)` |