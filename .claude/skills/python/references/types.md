# Python Types Reference

## Contents
- Type annotations in test harness code
- Numpy dtype conventions
- TypedDict for structured firmware output
- Using `is` vs `==`
- Avoiding stringly-typed test parameters

---

## Type Annotations

Use annotations for function signatures in fixtures and helpers. They document intent and catch errors via static analysis (mypy or pyright if configured).

```python
from typing import Optional
import numpy as np

def parse_onset_log(raw: bytes) -> dict[str, float]:
    ...

def make_sine_frame(freq_hz: float, n_samples: int = 96) -> np.ndarray:
    ...
```

Avoid `Any` except at subprocess/JSON boundaries where the type is genuinely unknown.

---

## Numpy Dtype Conventions

| Data | dtype | Reason |
|------|-------|--------|
| Audio samples (I2S) | `np.int16` | Matches 12-bit ADC output range |
| DSP intermediate values | `np.float32` | Matches ESP32 FPU precision |
| Frequency bins (GDFT) | `np.float32` | 80 bins, float magnitude |
| LED color channels | `np.uint8` | 0–255 per channel |
| Tempo confidence | `np.float32` | 0.0–1.0 normalized |

Always specify `dtype` explicitly on `np.zeros`, `np.ones`, `np.array`. Relying on numpy defaults (float64) produces a silent precision mismatch with firmware output.

---

## TypedDict for Structured Firmware Output

When parsing JSON harness output, use `TypedDict` to document the schema:

```python
# new code to add
from typing import TypedDict

class OnsetMetrics(TypedDict):
    onset_rate: float
    confidence: float
    band_energy: list[float]

class TempoMetrics(TypedDict):
    bpm: float
    phase: float
    lock_confidence: float
```

This gives you IDE autocomplete and makes the expected schema explicit in the test file — critical when the harness output format changes.

---

## WARNING: `is` vs `==` for Value Comparison

**The Problem:**

```python
# BAD — identity check on interned integers works "accidentally" for small values
assert result["mode"] is 0   # passes for mode=0, fails for mode=257
assert state is True          # may fail on boxed bool from JSON parse
```

**Why This Breaks:**
CPython interns integers in `-5..256` and common strings, making `is` work accidentally in some ranges. Firmware mode IDs, beat confidence levels, and counts can exceed 256.

**The Fix:**

```python
# GOOD
assert result["mode"] == 0
assert state is True    # ONLY for None/True/False singletons — these are safe
assert value is None    # GOOD — None is always a singleton
```

Rule: use `is` ONLY for `None`, `True`, `False`. Use `==` for everything else.

---

## Avoiding Stringly-Typed Test Parameters

```python
# BAD — magic string, no IDE help, typo-prone
run_test(mode="onset_v2_fast_path")

# GOOD — use an enum or named constant
from enum import Enum

class TestMode(Enum):
    ONSET = "onset"
    TEMPO = "tempo"
    CHORD = "chord"

run_test(mode=TestMode.ONSET)
```

For firmware mode indices (0–24), define a mapping dict at the module level rather than scattering integer literals.