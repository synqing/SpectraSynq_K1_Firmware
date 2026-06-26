# Ruff Patterns Reference

## Contents
- Rule Selection
- Suppression Patterns
- Anti-Patterns
- Integration with pytest Harnesses

---

## Rule Selection

Select rule sets deliberately. Enabling everything generates noise that drowns real issues.

**Recommended baseline for this repo** (test/tooling Python, not a library):

```toml
# new code to add — add to pyproject.toml
[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "F",   # pyflakes (undefined names, unused imports)
    "I",   # isort (import ordering)
    "UP",  # pyupgrade (modernise syntax)
    "N",   # pep8-naming
]
ignore = [
    "E501",  # line length — long lines in harness fixture dicts are acceptable
]
```

**DO:** Start with `E`, `F`, `I`. Add `UP` to catch Python 2 holdovers. Add `N` if naming consistency matters.

**DON'T:** Enable `ALL` — it activates opinionated rules (e.g. `ANN` type annotations, `D` docstrings) that are inappropriate for test/tooling files.

---

## Suppression Patterns

### Single-line suppression

```python
# Suppress one rule on one line
from typing import TYPE_CHECKING  # noqa: F401

# Suppress multiple rules
some_dict = dict(x=1, y=2)  # noqa: C408, UP034
```

### File-level suppression for test fixtures

```toml
# new code to add
[tool.ruff.lint.per-file-ignores]
"tests/*" = [
    "F811",  # redefinition of unused name — pytest fixtures do this intentionally
    "F401",  # imported but unused — conftest imports are side-effectful
]
"tools/*" = [
    "T201",  # print statements — diagnostic tools intentionally print
]
```

### WARNING: Blanket `# noqa` Without Code

**The Problem:**
```python
result = some_function()  # noqa
```

**Why This Breaks:**
1. Silences ALL rules on the line, including future rules you'd want to catch.
2. Makes the suppression reason invisible — future readers can't tell what was wrong.
3. Hides regressions when the original violation is fixed but new ones appear.

**The Fix:**
```python
result = some_function()  # noqa: F841
```

---

## Anti-Patterns

### WARNING: Suppressing F401 Instead of Fixing Imports

**The Problem:**
```python
import numpy as np  # noqa: F401  — added "just in case"
```

**Why This Breaks:**
1. Unused imports increase module load time.
2. Signals to readers that the import is intentional when it isn't.
3. Accumulates — files end up with 10+ suppressed ghost imports.

**The Fix:** Delete the import. If it's needed for side effects, add a comment:
```python
import sb_tab5_init  # registers serial handlers — side-effect import
```

### WARNING: Running `ruff check` Without `--fix` in a Loop

**The Problem:**
```bash
# Manually fixing what ruff can auto-fix
ruff check .
# reading output, manually editing files...
```

**Why This Breaks:**
1. Wastes time on mechanical changes ruff handles in milliseconds.
2. Introduces human error in whitespace/import-order fixes.

**The Fix:**
```bash
ruff check --fix . && ruff format .
```

---

## Integration with pytest Harnesses

This repo's test files (`tests/test_sb_tab5_*.py`, `tests/test_tab5_*.py`) follow a common pattern. Ruff should NOT flag these:

```python
# tests/conftest.py pattern — F401 is expected here
import pytest  # noqa: F401  — re-exported for harness consumers

# Fixture redefinition across files is intentional
@pytest.fixture
def harness():  # same name in multiple files — suppress F811 via per-file-ignores
    ...
```

Configure `per-file-ignores` in `pyproject.toml` rather than scattering `# noqa` comments across test files. One config entry covers all current and future test files.