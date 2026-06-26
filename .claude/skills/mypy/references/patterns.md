# mypy Patterns Reference

## Contents
- Annotation patterns for this codebase
- Anti-patterns
- Suppression discipline
- Third-party stub handling

---

## Annotation Patterns for This Codebase

### diag_helpers.py — helper return types

```python
# new code to add
from typing import Any
import numpy as np
from numpy.typing import NDArray

def load_capture(path: str) -> dict[str, Any]:
    ...

def band_energy_array(snapshot: dict[str, Any]) -> NDArray[np.float32]:
    ...
```

### apstream_ingest.py — IO boundary annotation

```python
# new code to add
from pathlib import Path
from typing import Iterator

def iter_frames(capture_path: Path) -> Iterator[dict[str, float]]:
    ...
```

### pytest fixtures — return type annotation

```python
# new code to add
import pytest
from typing import Generator

@pytest.fixture
def audio_snapshot() -> Generator[dict[str, float], None, None]:
    snap = {"bpm": 120.0, "confidence": 0.8}
    yield snap
```

---

## WARNING: Bare `# type: ignore` Without Error Code

**The Problem:**

```python
# BAD - silences ALL mypy errors on this line
result = some_untyped_lib.get()  # type: ignore
```

**Why This Breaks:**
1. Hides future real errors introduced on the same line
2. Makes grep for suppressed errors useless — you can't audit by error class
3. Fails mypy's `--warn-unused-ignores` if the error is later fixed

**The Fix:**

```python
# GOOD - scoped to the specific error
result = some_untyped_lib.get()  # type: ignore[no-any-return]
```

**When You Might Be Tempted:** When a third-party library (e.g., an untyped plotting helper) returns `Any` everywhere. Use stubs or `cast()` instead.

---

## WARNING: `Any` as a Crutch

**The Problem:**

```python
# BAD - defeats type checking for the entire call chain
def process(data: Any) -> Any:
    return data["bpm"] * 2
```

**Why This Breaks:**
1. mypy stops checking everything downstream — errors propagate silently
2. Callers lose autocomplete and inference
3. One `Any` function poisons all callers to `Any`

**The Fix:**

```python
# GOOD - narrow the type at the boundary
from typing import TypedDict

class BeatData(TypedDict):
    bpm: float

def process(data: BeatData) -> float:
    return data["bpm"] * 2
```

---

## Suppression Discipline

- **NEVER** suppress without the error code: `# type: ignore[<code>]`
- **ALWAYS** add a comment explaining why: `# type: ignore[attr-defined]  # pandas-stubs incomplete`
- **Audit suppressions** when upgrading mypy or stubs — `--warn-unused-ignores` catches stale ones

---

## Third-Party Stub Handling

| Library | Stub package | Notes |
|---------|-------------|-------|
| numpy | bundled in numpy ≥1.20 | Use `numpy.typing.NDArray` |
| pandas | `pandas-stubs` | Install separately; incomplete coverage |
| scipy | `types-scipy` or inline `Any` | Sparse stubs; cast at boundary |
| plotly | no stubs | Use `# type: ignore[import]` at import only |

```python
# new code to add — at import for unstubbed libraries
import plotly.graph_objects as go  # type: ignore[import]
```