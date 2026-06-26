# Pydantic Workflows Reference

## Contents
- Schema-first development workflow
- Parsing serial/file data
- pytest fixtures with models
- JSON schema export
- Migration V1 → V2 checklist

---

## Schema-First Development

Define the model before writing parsing or processing logic. This forces you to think about the data contract at the boundary.

```
1. Define BaseModel with all fields + constraints
2. Write model_validate call against a real sample
3. Run: python -c "from mymodule import M; M.model_validate(sample)"
4. Add field_validator for any transform logic
5. Only then write downstream consumers
```

---

## Parsing Serial / File Data

This project ingests diagnostic streams from firmware (see `scripts/regression-harness/apstream_ingest.py`). Validate at parse, not later.

```python
# new code to add
import json
from pathlib import Path
from pydantic import BaseModel, Field, ValidationError

class APFrame(BaseModel):
    ts: int
    band: int = Field(ge=0, lt=24)
    onset: float = Field(ge=0.0)
    agc_gain: float

def load_frames(path: Path) -> list[APFrame]:
    frames = []
    for line in path.read_text().splitlines():
        try:
            frames.append(APFrame.model_validate(json.loads(line)))
        except (json.JSONDecodeError, ValidationError):
            pass  # malformed lines are skipped, not propagated
    return frames
```

Never call `json.loads` and pass the raw dict around without validating — downstream code will silently receive garbage.

---

## pytest Fixtures with Models

See the **pytest** skill for full fixture patterns. Pydantic models make excellent typed fixtures:

```python
# new code to add — tests/conftest.py
import pytest
from pydantic import BaseModel

class BeatFixture(BaseModel):
    bpm: float = 120.0
    confidence: float = 0.85
    locked: bool = True

@pytest.fixture
def beat_state():
    return BeatFixture()

@pytest.fixture
def low_confidence_beat():
    return BeatFixture(confidence=0.2, locked=False)
```

Use `model_dump()` when a function under test expects a raw dict:

```python
def test_director_ignores_low_confidence(low_confidence_beat):
    result = director_route(low_confidence_beat.model_dump())
    assert result.mode_unchanged
```

---

## JSON Schema Export

Useful for generating firmware diagnostic packet specs or API contracts:

```python
# new code to add
import json
from pydantic import BaseModel

schema = APFrame.model_json_schema()
print(json.dumps(schema, indent=2))
```

Commit the schema alongside the model when it's used as a cross-system contract (firmware ↔ host harness).

---

## V1 → V2 Migration Checklist

Copy and track:

- [ ] Replace `@validator` → `@field_validator` (add `@classmethod`)
- [ ] Replace `@root_validator` → `@model_validator(mode="after"|"before")`
- [ ] Replace `.parse_obj()` → `.model_validate()`
- [ ] Replace `.parse_raw()` → `.model_validate_json()`
- [ ] Replace `.dict()` → `.model_dump()`
- [ ] Replace `.json()` → `.model_dump_json()`
- [ ] Replace `class Config:` → `model_config = ConfigDict(...)`
- [ ] Replace `schema()` → `model_json_schema()`
- [ ] Audit any `from pydantic import validator` imports — they will not raise at import time but fail silently

Validate after each replacement:

```
python -m pytest tests/ -x -q
```