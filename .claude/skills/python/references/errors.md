# Python Errors Reference

## Contents
- Common failure modes in the test harness
- Subprocess and build errors
- numpy shape/dtype errors
- pytest collection errors
- Fixture teardown errors

---

## Subprocess and Build Errors

### PlatformIO build failure in test setup

```
RuntimeError: PIO build failed:
Error: No such file or directory: platformio.ini
```

**Cause:** Test or fixture invokes `pio run` but `cwd` is `tests/`, not the project root.

**Fix:**
```python
subprocess.run(
    ["pio", "run", "-e", "k1_hardware"],
    cwd=Path(__file__).parent.parent,  # project root
    check=True
)
```

### Harness binary not found

```
FileNotFoundError: [Errno 2] No such file or directory: './build/k1_harness'
```

**Fix:** Build before running, or skip with a clear message if binary is absent:
```python
harness = Path(__file__).parent.parent / "build" / "k1_harness"
if not harness.exists():
    pytest.skip("Harness binary not built — run: pio run -e k1_hardware_harness")
```

---

## Numpy Shape and Dtype Errors

### Broadcasting failure

```
ValueError: operands could not be broadcast together with shapes (96,) (128,)
```

**Cause:** Frame size mismatch — test fixture uses 96 samples, but harness expects 128.

**Fix:** Always derive frame size from a single constant:
```python
GOERTZEL_FRAME_SIZE = 96  # 12800 / (48000 / 400) — do not hardcode 96 elsewhere
frame = np.zeros(GOERTZEL_FRAME_SIZE, dtype=np.float32)
```

### Silent dtype promotion

```python
# Symptom: assertion passes on host, firmware produces different output
frame = np.array([0.5, 0.3, 0.8])        # float64
frame_fw = np.array([0.5, 0.3, 0.8], dtype=np.float32)  # matches firmware
# np.allclose(frame, frame_fw) is True, but quantization noise differs
```

Always use `dtype=np.float32` for DSP data. Use `np.testing.assert_array_equal` only on integer arrays; use `np.testing.assert_allclose(rtol=1e-5)` on float arrays.

---

## pytest Collection Errors

### `ImportError` at collection time

```
ImportError while importing test module 'tests/test_foo.py'.
ModuleNotFoundError: No module named 'tools.tab5_k1_dashboard_harness'
```

**Fix:** Add `sys.path` insertion in `tests/conftest.py` (see [modules.md](modules.md)).

### Fixture not found

```
fixture 'audio_frame' not found
```

**Cause:** Fixture defined in a test file, not `conftest.py`, so it's invisible to sibling files.

**Fix:** Move shared fixtures to the appropriate `conftest.py`.

---

## WARNING: Fixture Teardown Exceptions

**The Problem:**

```python
@pytest.fixture
def temp_output(tmp_path):
    out = tmp_path / "result.json"
    yield out
    out.unlink()  # BAD — raises FileNotFoundError if test deleted it already
```

**Why This Breaks:**
Teardown exceptions mask the original test failure. pytest reports the teardown error, not the assertion that failed, making debugging harder.

**The Fix:**

```python
@pytest.fixture
def temp_output(tmp_path):
    out = tmp_path / "result.json"
    yield out
    out.unlink(missing_ok=True)  # Python 3.8+
```

Use `missing_ok=True` on `Path.unlink()` in all fixture teardown. Let pytest's `tmp_path` handle directory cleanup automatically — don't `shutil.rmtree` manually.

---

## WARNING: Catching `AssertionError` in Tests

**The Problem:**

```python
# BAD — swallows pytest assertions
try:
    validate_onset_metrics(metrics)
except Exception:
    pass  # "optional validation"
```

**Why This Breaks:**
`AssertionError` is a subclass of `Exception`. This silently passes tests that should fail.

**The Fix:**
Never catch `Exception` or `BaseException` in test code. If validation is genuinely optional, use `pytest.warns` or check a condition explicitly:

```python
if metrics.get("onset_rate") is not None:
    assert metrics["onset_rate"] > 0.1, f"onset_rate too low: {metrics}"
```