# Mocking Reference

## Contents
- When to Mock vs. When Not to
- Patching Serial/Hardware Interfaces
- Mocking Audio Input
- Anti-Patterns

## When to Mock vs. When Not to

**Mock:** hardware interfaces (serial, USB, I2S), time-dependent calls (`time.sleep`, `time.time`), external process spawns.

**Do NOT mock:** pure DSP math functions, numpy operations, fixture loading. Mocking these produces tests that validate the mock, not the logic.

## Patching Serial/Hardware Interfaces

The harness scripts (`tools/tab5_k1_dashboard_harness.py`) communicate over serial. Mock at the transport boundary, not at the harness level.

```python
from unittest.mock import patch, MagicMock

def test_harness_send_command():
    mock_serial = MagicMock()
    mock_serial.readline.return_value = b'{"status": "ok"}\n'
    
    with patch("tools.tab5_k1_dashboard_harness.serial.Serial", return_value=mock_serial):
        harness = Tab5K1DashboardHarness(port="/dev/null")
        result = harness.query_state()
    
    assert result["status"] == "ok"
    mock_serial.write.assert_called_once()
```

```python
# Mock time for deterministic timeout testing
from unittest.mock import patch

def test_harness_timeout():
    with patch("time.time", side_effect=[0.0, 0.0, 5.1]):  # simulate timeout
        with pytest.raises(TimeoutError):
            wait_for_ready(timeout=5.0)
```

## Mocking Audio Input

Audio fixture files in `scripts/regression-harness/fixtures/` replace live I2S input. Do not mock the WAV loader—it is the ground truth. Mock only the transport that would normally deliver frames from hardware.

```python
# new code to add
def make_mock_audio_source(fixture_path: str):
    """Returns a callable that yields frames from a fixture file."""
    frames = load_wav_frames(fixture_path)
    return iter(frames)
```

## DO / DON'T

**DO: Use `pytest.fixture` with `autouse=False` for optional mocks**
```python
@pytest.fixture
def mock_serial_port():
    with patch("tools.tab5_k1_dashboard_harness.serial.Serial") as m:
        m.return_value.readline.return_value = b'{"status":"ok"}\n'
        yield m
```

**DON'T: Patch at the wrong layer**
```python
# BAD — patches the module reference, not the imported name
with patch("serial.Serial"):  # harness already imported serial; this has no effect
    ...

# GOOD — patch where it is used
with patch("tools.tab5_k1_dashboard_harness.serial.Serial"):
    ...
```

## WARNING: Over-Mocking DSP Logic

**The Problem:**
```python
# BAD — mocking the function under test
with patch("dsp.compute_onset_threshold", return_value=0.5):
    result = pipeline.process_frame(frame)
    assert result["onset"] == True
```

**Why This Breaks:**
1. The test validates the mock contract, not the actual computation
2. Regressions in `compute_onset_threshold` will not be caught
3. When the mock return value drifts from reality, tests silently lie

**The Fix:** Use real fixtures (recorded DSP inputs/outputs) and call the real function. Reserve mocks for I/O boundaries only.

## WARNING: Mock `assert_called` Without `assert_called_once`

```python
# BAD — passes even if called 100 times or zero times after the first call
mock.assert_called()

# GOOD — enforces exactly one write per command
mock_serial.write.assert_called_once_with(expected_payload)
```