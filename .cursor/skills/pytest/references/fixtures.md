# Fixtures Reference

## Contents
- Project Fixture Conventions
- Session vs Function Scope
- Fixture Files on Disk
- Parametrized Fixtures
- Anti-Patterns

## Project Fixture Conventions

This repo uses two fixture kinds: **pytest fixtures** (Python objects with scope/teardown) and **fixture files** (binary/WAV/JSON in `tests/fixtures/`). Keep them distinct.

```
tests/
  fixtures/
    tab5/          ← binary frame dumps for replay tests
  tab5_harness_spec/  ← harness spec fixtures
scripts/
  regression-harness/
    fixtures/
      wireless_ab_stimulus.wav  ← A/B audio stimulus
```

## Session vs Function Scope

```python
# FUNCTION scope (default) — fresh state per test, safe for stateful objects
@pytest.fixture
def fresh_pipeline():
    return AudioPipeline()

# SESSION scope — expensive to construct, must be truly read-only
@pytest.fixture(scope="session")
def wav_frames():
    """Load once; all tests share the same immutable list."""
    return load_wav_frames("scripts/regression-harness/fixtures/wireless_ab_stimulus.wav")
```

**Rule:** Use `scope="session"` only for read-only data (loaded fixtures, compiled constants). Never for objects with mutable state.

## Fixture Files on Disk

Replay tests load frame dumps from `tests/fixtures/tab5/`. Always validate the file exists and is non-empty before running assertions:

```python
import os
import pytest

@pytest.fixture
def tab5_fixture_frames(request):
    path = request.param
    assert os.path.exists(path), f"Missing fixture: {path}"
    frames = load_binary_frames(path)
    assert len(frames) > 0, f"Empty fixture: {path}"
    return frames
```

## Parametrized Fixtures

```python
# Parametrize over all fixture files in a directory
import glob

@pytest.fixture(params=glob.glob("tests/fixtures/tab5/*.bin"))
def all_tab5_fixtures(request):
    return load_binary_frames(request.param)

def test_replay_all_fixtures(all_tab5_fixtures):
    results = replay_pipeline(all_tab5_fixtures)
    assert results["error_count"] == 0
```

## Harness Session Fixture

Tests in `test_tab5_dashboard_harness.py` and `test_tab5_harness_strict_mode.py` use a shared harness session. The fixture handles connect/disconnect:

```python
# new code to add — if not already present in conftest.py
@pytest.fixture(scope="module")
def harness_session():
    h = Tab5K1DashboardHarness(port=os.environ.get("TAB5_PORT", "/dev/null"))
    h.connect()
    yield h
    h.disconnect()
```

## DO / DON'T

**DO: Put shared fixtures in `conftest.py` at the appropriate directory level**
```
tests/
  conftest.py          ← fixtures shared across all tests
  tab5_harness_spec/
    conftest.py        ← fixtures scoped to harness spec tests only
```

**DON'T: Import fixtures from test files**
```python
# BAD — creates hidden coupling, breaks test isolation
from test_tab5_dashboard_harness import harness_session
```

**DO: Use `tmp_path` for any files written during tests**
```python
def test_transcript_write(tmp_path):
    out = tmp_path / "result.json"
    write_transcript_result(str(out), data)
    assert out.exists()
```

**DON'T: Write to the repo tree during tests** — leaves artifacts that fail the `git status` check in CI and pre-commit.

## WARNING: Fixture Scope Mismatch

```python
# BAD — session-scoped fixture depends on function-scoped fixture
@pytest.fixture(scope="session")
def pipeline(fresh_config):  # fresh_config is function-scoped: ERROR
    ...
```

pytest raises `ScopeMismatch` at collection time. A session fixture can only depend on fixtures of equal or wider scope.

## Related Skills

- See the **ruff** skill for auto-fixing import order in `conftest.py` files
- See the **aiofiles** skill when fixtures involve async file loading