# isort Patterns Reference

## Contents
- Section Detection and first-party config
- Profile selection
- ruff coexistence
- Anti-patterns
- Common errors

---

## Section Detection and First-Party Config

isort must know which modules are first-party or it will misclassify them as third-party, producing wrong section ordering.

**This repo's Python harness modules** (`tools/`, `tests/`, `scripts/`) should be declared first-party:

```toml
# pyproject.toml — new code to add
[tool.isort]
profile = "black"
known_first_party = ["sb_tab5", "tab5_k1_dashboard_harness", "tools"]
src_paths = ["tests", "tools", "scripts"]
```

isort also auto-detects first-party by scanning `src_paths`. Set both for reliability.

---

## Profile Selection

The `black` profile is the correct default for any project also running black or ruff-format:

```bash
# black profile sets: multi_line_output=3, include_trailing_comma=True,
# force_grid_wrap=0, use_parentheses=True, ensure_newline_before_comments=True, line_length=88
python -m isort --profile black file.py
```

Without `--profile black`, isort and black will reformat each other's output in a loop — this is the most common CI failure pattern.

---

## ruff Coexistence

**WARNING:** ruff's `I` ruleset reimplements isort. Running both on the same files causes conflicts unless they share config.

**The Fix — pick one path:**

**Path A: ruff only (preferred for new projects)**
```toml
# pyproject.toml
[tool.ruff.lint]
select = ["I"]  # enables isort rules inside ruff

# Do NOT run standalone isort; remove it from pre-commit
```

**Path B: isort only**
```toml
[tool.ruff.lint]
ignore = ["I"]  # disable ruff's isort rules
```

**Path C: both (requires config sync)**
```toml
[tool.isort]
profile = "black"

[tool.ruff.lint]
# ruff will defer to isort; still risk of divergence — avoid this path
```

See the **ruff** skill for ruff-side configuration.

---

## Anti-Patterns

### WARNING: Sorting Without a Profile

**The Problem:**
```python
# BAD — isort default multi_line_output=0 wraps differently than black
from foo import (bar, baz,
    qux)
```

**Why This Breaks:** black reformats isort's output, isort reformats black's output — CI loops forever on `--check`.

**The Fix:**
```bash
python -m isort --profile black file.py
```

---

### WARNING: Mixing `import` and `from import` in Wrong Order

**The Problem:**
```python
# BAD — isort will reorder these; committing before running isort
from pathlib import Path
import os
import sys
from typing import List
```

**Why This Breaks:** PR CI check fails with a confusing diff showing only import reordering. Wastes review cycles.

**The Fix:** Run `isort --check-only --diff` before committing. Add to pre-commit hook.

---

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `isort would make changes` in CI | Imports not sorted before commit | Run `isort` locally + add pre-commit hook |
| ruff `I001` conflicts with isort output | Both tools active with different configs | Disable one; see ruff coexistence above |
| Local modules sorted as third-party | `known_first_party` not set | Add to `pyproject.toml` |
| `--check` exits 1 on clean file | Line length mismatch with black | Set `line_length = 88` in isort config |