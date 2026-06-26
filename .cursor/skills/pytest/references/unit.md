# Unit Test Reference

## Contents
- Writing Unit Tests for DSP Functions
- Assertion Patterns
- Anti-Patterns
- Naming Conventions

## Writing Unit Tests for DSP Functions

Unit tests in this repo test pure Python representations of DSP logic—spectrum processing, onset detection thresholds, palette mapping. Keep them fast (<10 ms each) and deterministic.

```python
# Test a pure transformation function
def test_octave_band_mapping():
    bins = [0.0] * 80
    bins[12] = 1.0  # single active bin
    bands = map_bins_to_octave_bands(bins)
    assert len(bands) == 24
    assert any(b > 0 for b in bands), "Active bin must map to at least one band"
```

```python
# Test boundary conditions explicitly — DSP functions fail silently at edges
def test_agc_zero_input():
    gain = compute_agc_gain(signal_rms=0.0, noise_floor=0.001)
    assert gain == pytest.approx(1.0, rel=0.01), "AGC must not divide by zero on silence"
```

## DO / DON'T

**DO: Test one invariant per test function**
```python
# GOOD — one assertion, clear failure message
def test_onset_threshold_not_negative():
    thresh = compute_onset_threshold(band_energy=0.5, alpha=0.9)
    assert thresh >= 0.0
```

**DON'T: Stack unrelated assertions in one test**
```python
# BAD — when this fails you don't know which invariant broke
def test_onset_stuff():
    thresh = compute_onset_threshold(band_energy=0.5, alpha=0.9)
    assert thresh >= 0.0
    assert thresh < 100.0
    assert compute_onset_threshold(0.0, 0.9) == 0.0
    assert compute_onset_threshold(1.0, 0.0) == 1.0
```

**DO: Use `pytest.approx` for floating-point DSP values**
```python
assert result["peak_scaled"] == pytest.approx(0.812, rel=0.01)
```

**DON'T: Use `==` for floats — will produce false failures on -ffast-math reassociation**

## WARNING: Test Isolation Failures

**The Problem:**
```python
# BAD — module-level mutable state bleeds between tests
_state = {"gain": 1.0}

def test_agc_ramp():
    _state["gain"] = apply_agc(_state["gain"], 0.5)
    assert _state["gain"] < 1.0
```

**Why This Breaks:**
1. Test order matters — pytest does not guarantee order without explicit markers
2. A failing test leaves dirty state that corrupts subsequent tests
3. `-x` (fail-fast) mid-suite leaves state permanently dirty

**The Fix:**
```python
def test_agc_ramp():
    initial_gain = 1.0
    result = apply_agc(initial_gain, 0.5)
    assert result < initial_gain
```

## Naming Conventions

Follow the existing repo pattern: `test_<module>_<what>_<condition>`:

```
test_onset_beat_replay.py       → replay of onset/beat DSP
test_sb_tab5_wireless_controller_static.py  → static analysis
test_tab5_harness_negatives.py  → negative/error path harness
```

Within files: `test_<function_name>_<scenario>`:
```python
def test_compute_onset_threshold_zero_energy(): ...
def test_compute_onset_threshold_max_alpha(): ...
```