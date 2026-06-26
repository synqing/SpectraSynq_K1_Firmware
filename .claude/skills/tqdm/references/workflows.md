# tqdm Workflows Reference

## Contents
- Adding tqdm to a new diagnostic script
- pytest harness integration
- Multi-stage pipeline bars
- Jupyter / notebook context
- Checklist

---

## Adding tqdm to a New Diagnostic Script

```python
# new code to add
#!/usr/bin/env python3
"""Batch onset scorer — wraps replay harness with progress reporting."""

import sys
from pathlib import Path
from tqdm.auto import tqdm

def run(input_dir: Path, verbose: bool = True):
    files = sorted(input_dir.glob("*.npz"))
    disable = not verbose or not sys.stdout.isatty()

    results = []
    with tqdm(files, desc="Onset replay", unit="file", disable=disable) as pbar:
        for f in pbar:
            pbar.set_description(f"Onset replay [{f.stem}]")
            result = score_file(f)
            results.append(result)
            pbar.set_postfix(onset_acc=f"{result['acc']:.2f}")

    return results
```

Key decisions:
- `tqdm.auto` — works unchanged in terminal and notebook
- `disable` tied to tty + `verbose` flag — CI gets no output, dev gets the bar
- `set_description` per file — gives live file-level feedback without extra prints

---

## pytest Harness Integration

NEVER let tqdm output bleed into pytest's captured stdout — it corrupts assertion diffs.

```python
# new code to add
# conftest.py
import pytest

@pytest.fixture(autouse=True)
def suppress_tqdm(monkeypatch):
    """Disable tqdm globally in all tests."""
    monkeypatch.setenv("TQDM_DISABLE", "1")
```

`TQDM_DISABLE=1` is checked by tqdm at import time — all bars silenced, zero overhead. Alternatively, pass `disable=True` explicitly in every call (more surgical, more verbose).

For tests that assert on diagnostic output, use `tqdm.write` in production code and capture stderr:

```python
# new code to add
def test_progress_output(capsys):
    run_with_tqdm(items)
    captured = capsys.readouterr()
    assert "Onset replay" not in captured.out  # bar must not leak into stdout
```

See the **pytest** skill for harness fixture conventions.

---

## Multi-Stage Pipeline Bars

For sequential stages where each has its own count:

```python
# new code to add
from tqdm.auto import tqdm

stages = [
    ("Load frames",   load_frames,   n_files),
    ("Score onset",   score_onset,   n_frames),
    ("Write results", write_results, n_results),
]

all_results = {}
for label, fn, total in tqdm(stages, desc="Pipeline", unit="stage"):
    tqdm.write(f"→ {label}")
    all_results[label] = fn(tqdm(..., total=total, desc=label, leave=False))
```

Outer bar tracks stages (`leave=True` default). Inner bars use `leave=False` so they disappear on completion and don't stack up.

---

## Jupyter / Notebook Context

`tqdm.auto` selects `tqdm.notebook` automatically when running inside Jupyter. No code change needed.

AVOID importing `tqdm.notebook` directly — it fails silently in terminal contexts.

```python
# BAD - notebook-only
from tqdm.notebook import tqdm

# GOOD - works everywhere
from tqdm.auto import tqdm
```

For the `audio_semantic_diagnostics.ipynb` notebook in this repo, `tqdm.auto` is the only safe import.

---

## Checklist: Adding Progress Bars to a New Script

Copy and track progress:

- [ ] Import `from tqdm.auto import tqdm` (not `from tqdm import tqdm`)
- [ ] Add `disable=not sys.stdout.isatty()` or `TQDM_DISABLE` env check
- [ ] Pass `total=` explicitly if wrapping a generator or file glob
- [ ] Use `tqdm.write()` for any in-loop diagnostic output (never bare `print`)
- [ ] Use `set_postfix()` for live scalar metrics (confidence, BPM, counts)
- [ ] Set `leave=False` on all inner/nested bars
- [ ] Verify pytest integration: run `pytest tests/ -v` and confirm no bar output in captured stdout

Iterate-until-pass:
1. Add tqdm to script
2. Validate: `python script.py | cat` — bar output must not corrupt piped output
3. Validate: `pytest tests/ -v 2>&1 | grep -c "100%"` — must return 0
4. If either fails, fix `disable` logic and repeat from step 2