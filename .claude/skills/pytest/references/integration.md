# Integration Test Reference

## Contents
- Harness-Based Integration Tests
- Replay Pipeline Tests
- A/B Stimulus Tests
- Anti-Patterns

## Harness-Based Integration Tests

Integration tests wire multiple pipeline stages together using the Tab5/K1 harness scripts. They validate that DSP output flows correctly through the processing chain.

```python
# Pattern from test_tab5_dashboard_harness.py — verify harness protocol round-trip
def test_harness_connect_and_query(harness_session):
    resp = harness_session.query_state()
    assert resp["status"] == "ok"
    assert "beat_confidence" in resp
    assert "onset_rate" in resp
```

```python
# Verify that the transcript ingest pipeline processes a full stimulus file
def test_transcript_ingest_full_file():
    transcript = load_transcript("scripts/regression-harness/fixtures/wireless_ab_stimulus.wav")
    result = ingest_transcript(transcript)
    assert result["frames_processed"] > 0
    assert result["error_count"] == 0
```

## Replay Pipeline Tests

Replay tests run a recorded stimulus through the processing pipeline and compare output against a known-good baseline. These catch regressions in the AP/VP chain.

```python
# Pattern from test_tab5_dispatch_replay.py
def test_dispatch_replay_onset_preserved():
    frames = load_replay_fixture("tests/fixtures/tab5/")
    outputs = replay_pipeline(frames)
    onset_frames = [o for o in outputs if o["onset_detected"]]
    assert len(onset_frames) >= 10, (
        f"Expected >=10 onset frames, got {len(onset_frames)}"
    )
```

```python
# A/B regression: wireless ON must not degrade onset detection by >10%
def test_wireless_ab_onset_regression():
    baseline = run_replay("condition_a")
    wireless = run_replay("condition_b")
    ratio = wireless["onset_rate"] / baseline["onset_rate"]
    assert ratio >= 0.90, f"Wireless onset regression: {ratio:.2%} (threshold: 90%)"
```

## DO / DON'T

**DO: Use the harness session fixture for all harness-dependent tests**
```python
def test_state_query(harness_session):  # fixture injects session
    ...
```

**DON'T: Instantiate the harness directly in each test — setup/teardown leaks**
```python
# BAD
def test_state_query():
    h = Tab5SerialHarness("/dev/ttyUSB0")  # never cleaned up on failure
    ...
```

**DO: Assert specific numeric thresholds with tolerance, not just "not None"**
```python
assert result["peak_scaled"] >= 0.7  # meaningful gate
```

**DON'T: Soft assertions that always pass**
```python
assert result is not None  # proves nothing about correctness
```

## WARNING: Fixture File Coupling

Integration tests that depend on binary fixture files in `tests/fixtures/tab5/` will silently pass if the fixture is missing and the loader returns an empty list. Always assert `len(frames) > 0` before processing:

```python
def test_replay(fixture_path):
    frames = load_fixture(fixture_path)
    assert len(frames) > 0, f"Fixture empty or missing: {fixture_path}"
    ...
```

## Anti-Patterns

**NEVER import device drivers in integration tests** — integration tests run host-only. Any import of `serial`, `usb`, or hardware HAL must be behind a `pytest.importorskip` guard:

```python
serial = pytest.importorskip("serial", reason="serial not available in host CI")
```