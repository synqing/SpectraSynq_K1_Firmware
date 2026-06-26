# Python Patterns Reference

## Contents
- Idiomatic Python for firmware tooling
- Mutable default argument trap
- Error handling conventions
- Async and subprocess patterns
- Numpy idioms for DSP data

---

## Idiomatic Python for Firmware Tooling

Tests here validate C++ firmware behavior via host-compiled harnesses. Keep Python code thin: parse binary output, assert on metrics, never re-implement DSP logic in Python.

```python
# GOOD — delegate computation to the compiled harness
result = subprocess.run(
    ["./build/k1_harness", "--mode", "onset", "--frames", "100"],
    capture_output=True, check=True
)
metrics = json.loads(result.stdout)
assert metrics["onset_rate"] > 0.3
```

```python
# BAD — reimplementing Goertzel in Python to "cross-check"
# Python float precision ≠ ESP32 fixed-point; you're testing the Python, not the firmware
def python_goertzel(samples, freq): ...  # DO NOT DO THIS
```

---

## WARNING: Mutable Default Arguments

**The Problem:**

```python
# BAD — shared across all calls
def make_frame(samples=[]):
    samples.append(0.0)
    return samples
```

**Why This Breaks:**
1. `samples` is created once at function definition, not per call
2. State leaks between test cases — the second call gets `[0.0]`, third gets `[0.0, 0.0]`
3. Flaky tests that pass in isolation but fail in suite order

**The Fix:**

```python
# GOOD
def make_frame(samples=None):
    if samples is None:
        samples = []
    samples.append(0.0)
    return samples
```

---

## WARNING: Bare `except` Clauses

**The Problem:**

```python
# BAD
try:
    result = parse_firmware_output(raw)
except:
    return None
```

**Why This Breaks:**
1. Catches `KeyboardInterrupt`, `SystemExit`, `MemoryError` — you can't Ctrl-C a hung test
2. Swallows `AssertionError` — pytest assertions inside the try block silently disappear
3. Hides real bugs: a `TypeError` on `raw` being `None` looks like "no result"

**The Fix:**

```python
# GOOD — catch only what you can handle
try:
    result = parse_firmware_output(raw)
except (ValueError, struct.error) as e:
    pytest.fail(f"Firmware output parse failed: {e}")
```

---

## Error Handling Conventions

Raise specific, informative exceptions at system boundaries (subprocess exit, file parse, network):

```python
def load_fixture(path: str) -> dict:
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Missing test fixture: {path}. Run: make fixtures")
    except json.JSONDecodeError as e:
        raise ValueError(f"Corrupt fixture {path}: {e}")
```

Never return `None` to signal failure when a caller will dereference the result — raise early.

---

## Subprocess Pattern for PlatformIO

```python
import subprocess

def pio_build(env: str = "k1_hardware") -> None:
    proc = subprocess.run(
        ["pio", "run", "-e", env],
        capture_output=True, text=True
    )
    if proc.returncode != 0:
        raise RuntimeError(f"PIO build failed:\n{proc.stderr}")
```

Always pass `check=False` and inspect `returncode` manually when you need the stderr for diagnostics. Use `check=True` only when you don't need the output.

---

## Numpy Idioms for DSP Data

```python
import numpy as np

# Audio frame: always float32 for consistency with firmware Q-format math
frame = np.zeros(96, dtype=np.float32)

# Frequency bins: 80 bins, match firmware GDFT_NUM_BINS
bins = np.zeros(80, dtype=np.float32)

# AVOID: implicit float64 (numpy default) — misrepresents firmware precision
frame = np.zeros(96)  # BAD — float64, not float32

# LED color comparison: uint8, shape (N, 3)
leds = np.zeros((128, 3), dtype=np.uint8)
assert np.allclose(leds[0], [255, 0, 128], atol=2)  # tolerance for rounding
```

Use `np.testing.assert_allclose` instead of `==` for float comparisons — firmware output has quantization noise.