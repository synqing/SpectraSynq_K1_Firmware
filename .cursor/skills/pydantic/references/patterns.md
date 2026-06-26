# Pydantic Patterns Reference

## Contents
- Field constraints
- Validators
- Serialization
- Config and strict mode
- Anti-patterns

---

## Field Constraints

Use `Field` for all boundary-enforced values. Constraints are checked at parse time — fail fast, not silently.

```python
from pydantic import BaseModel, Field

class GDFTBand(BaseModel):
    index: int = Field(ge=0, lt=24, description="Octave band index")
    energy: float = Field(ge=0.0, le=1.0)
    label: str = Field(default="", max_length=32)
```

`ge`/`le`/`gt`/`lt` cover numeric ranges. `min_length`/`max_length` cover strings. Do not validate these manually after parsing — that's Pydantic's job.

---

## Validators

### Field-level transform

```python
from pydantic import field_validator

class TempoState(BaseModel):
    bpm: float

    @field_validator("bpm")
    @classmethod
    def round_bpm(cls, v: float) -> float:
        return round(v, 2)
```

### Model-level cross-field check

```python
from pydantic import model_validator

class Window(BaseModel):
    start: int
    end: int

    @model_validator(mode="after")
    def check_order(self) -> "Window":
        if self.end <= self.start:
            raise ValueError("end must be > start")
        return self
```

`mode="after"` receives the populated model instance. Use `mode="before"` to transform raw input dicts before field parsing.

---

## Serialization

```python
obj = TempoState(bpm=127.5)

# To dict (default: includes all fields)
d = obj.model_dump()

# Exclude unset / None fields — keeps payloads minimal
d = obj.model_dump(exclude_none=True, exclude_unset=True)

# To JSON string
j = obj.model_dump_json()

# Round-trip
obj2 = TempoState.model_validate_json(j)
```

For lists of models, use `TypeAdapter`:

```python
from pydantic import TypeAdapter
ta = TypeAdapter(list[TempoState])
states = ta.validate_python(raw_list)
```

---

## Config and Strict Mode

```python
from pydantic import ConfigDict

class StrictFrame(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)
    band: int
    value: float
```

`strict=True` — no coercion (string `"3"` won't become int `3`). Use at deserialization boundaries where type confusion is a bug.  
`frozen=True` — immutable after construction; safe to hash and cache.

---

## WARNING: V1 Anti-Patterns

### WARNING: Using `@validator` (V1 API)

**The Problem:**
```python
# BAD - V1 only, raises error under V2
from pydantic import validator

class Bad(BaseModel):
    @validator("bpm")
    def check(cls, v): ...
```

**Why This Breaks:** V2 removed `@validator`. It silently does nothing in some import paths or crashes at runtime.

**The Fix:**
```python
# GOOD
from pydantic import field_validator

class Good(BaseModel):
    @field_validator("bpm")
    @classmethod
    def check(cls, v): ...
```

---

### WARNING: `parse_obj` / `parse_raw` (V1 API)

**The Problem:**
```python
# BAD
obj = MyModel.parse_obj(data)
```

**The Fix:**
```python
# GOOD
obj = MyModel.model_validate(data)
obj = MyModel.model_validate_json(json_str)
```

---

### WARNING: Mutable default values in fields

**The Problem:**
```python
# BAD - shared list across all instances
class Bad(BaseModel):
    tags: list[str] = []
```

**Why This Breaks:** Pydantic V2 actually copies defaults correctly, but the pattern looks like the classic Python mutable-default bug and confuses readers. Always be explicit:

```python
# GOOD
from pydantic import Field
class Good(BaseModel):
    tags: list[str] = Field(default_factory=list)
```