# Pyright Workflows Reference

## Contents
- Type-check workflow
- Fixing errors iteratively
- CI integration
- Annotating existing untyped modules

---

## Type-Check Workflow

The verified command from this repo:

```bash
bun run check-types
```

This should run pyright over the Python host layer. If that target isn't scoped to Python files, run directly:

```bash
pyright tests/ scripts/ notebooks/diag_helpers.py
```

**Iterate-until-pass loop:**

1. Run `bun run check-types`
2. Fix the first error category (group by error code, not by file)
3. Re-run — do not fix error A then break error B
4. Only commit when exit code is 0

---

## Fixing Errors by Priority

Fix in this order to avoid cascading noise:

1. **Missing imports / stubs** — add `reportMissingTypeStubs: false` or install stubs (`pip install pandas-stubs`)
2. **`Unknown` type from untyped returns** — annotate the return type explicitly or use `cast()`
3. **`None` not handled** — add guards; never use `# type: ignore` for None access
4. **Incompatible assignments** — fix the type, not the annotation

```bash
# See only errors (not warnings)
pyright --outputjson | python -c "
import sys, json
d = json.load(sys.stdin)
errs = [e for e in d['generalDiagnostics'] if e['severity']=='error']
for e in errs: print(e['file'], e['range']['start']['line'], e['message'])
"
```

---

## Annotating `diag_helpers.py` (Existing Untyped Module)

Checklist — work top-to-bottom, commit at each green checkpoint:

```
- [ ] Add `from __future__ import annotations` at top (deferred evaluation, no runtime cost)
- [ ] Annotate all function signatures (params + return)
- [ ] Replace bare `dict` returns with TypedDict
- [ ] Replace bare `list` with `list[TempoFrame]` etc.
- [ ] Run `bun run check-types` — fix errors before moving to next function
- [ ] Remove any `# type: ignore` that is now unnecessary
```

Example progression:

```python
# Before (untyped)
def load_capture(path):
    with open(path) as f:
        return json.load(f)

# After (annotated)
import json
from pathlib import Path
from .types import TempoFrame  # new code to add

def load_capture(path: Path | str) -> list[TempoFrame]:
    with open(path) as f:
        data = json.load(f)
    return data  # pyright will verify shape if TempoFrame is TypedDict
```

---

## Annotating `apstream_ingest.py`

This file ingests audio stream packets from the K1 device. Key annotation targets:

```python
# new code to add — top of apstream_ingest.py
from typing import Generator
from numpy.typing import NDArray
import numpy as np

def stream_packets(port: str, baud: int) -> Generator[OnsetPacket, None, None]:
    ...

def frames_to_array(packets: list[OnsetPacket]) -> NDArray[np.float32]:
    ...
```

---

## WARNING: Suppressing Errors Globally

**The Problem:**

```python
# BAD — in pyrightconfig.json
{
  "reportUnknownVariableType": "none",
  "reportUnknownMemberType": "none"
}
```

**Why This Breaks:**
1. These two rules together suppress ~60% of real type errors in numpy-heavy code.
2. The regression harness silently passes wrong-shaped arrays to DSP functions — errors surface as wrong metrics, not exceptions.
3. Once suppressed globally, future contributors cannot tell which `Unknown` types are intentional.

**The Fix:** Suppress per-line with `# pyright: ignore[reportUnknownVariableType]` only where a specific C-extension or incomplete stub forces it.

---

## CI Integration

If adding pyright to CI, scope it tightly:

```yaml
# new code to add — .github/workflows or equivalent
- name: Type check Python host layer
  run: |
    pip install pyright
    pyright tests/ scripts/ notebooks/diag_helpers.py --outputjson > pyright-out.json
    python -c "
    import json, sys
    d = json.load(open('pyright-out.json'))
    errs = [e for e in d['generalDiagnostics'] if e['severity']=='error']
    if errs:
        for e in errs: print(e['file'], e['message'])
        sys.exit(1)
    "
```

Gate on errors only, not warnings — warnings in numpy-heavy code are noisy until stubs mature.

---

## Related Skills

- See the **pytest** skill for how type annotations interact with fixture injection
- See the **numpy** skill for `NDArray` dtype patterns
- See the **python** skill for `__future__` annotations and `TypedDict` compatibility