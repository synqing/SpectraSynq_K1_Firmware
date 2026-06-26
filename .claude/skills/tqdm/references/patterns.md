# tqdm Patterns Reference

## Contents
- CI / non-interactive safety
- Postfix metrics
- pandas integration
- WARNING: bare `print` inside tqdm
- WARNING: missing `total` on generators

---

## CI / Non-Interactive Safety

NEVER unconditionally emit a progress bar in pytest or CI pipelines — tty detection handles this cleanly:

```python
# new code to add
import sys
from tqdm.auto import tqdm

def process(items, verbose=True):
    disable = not verbose or not sys.stdout.isatty()
    for item in tqdm(items, desc="Processing", disable=disable):
        handle(item)
```

`disable=True` makes tqdm a zero-overhead pass-through — the loop runs at full speed and produces no output. Use this everywhere pytest calls your functions directly.

---

## Postfix Metrics

Attach live diagnostic values to the bar without extra print statements:

```python
# new code to add
from tqdm.auto import tqdm

with tqdm(frames, desc="Beat replay", unit="frame") as pbar:
    for frame in pbar:
        confidence = score(frame)
        pbar.set_postfix(conf=f"{confidence:.3f}", bpm=current_bpm)
```

`set_postfix` accepts keyword args; values are stringified. Use for confidence, BPM, onset counts — any scalar that benefits from live feedback during a diagnostic run.

---

## pandas Integration

```python
# new code to add
import pandas as pd
from tqdm import tqdm

tqdm.pandas(desc="Applying scorer")
df["score"] = df["frame_data"].progress_apply(score_frame)
```

Call `tqdm.pandas()` once at module level (or in `conftest.py`). After that, `progress_apply` / `progress_map` / `progress_aggregate` are available on all DataFrames. See the **pandas** skill for DataFrame conventions.

---

## WARNING: bare `print` inside tqdm loops

**The Problem:**

```python
# BAD - destroys bar rendering
for item in tqdm(items):
    result = process(item)
    print(f"result: {result}")  # clobbers the bar line
```

**Why This Breaks:**
1. `print` writes to stdout, which tqdm also owns during the loop — lines interleave randomly.
2. The bar is redrawn on the same line via carriage return; a bare newline from `print` shifts the cursor permanently.
3. On CI (no tty), output is buffered differently and the corruption is non-deterministic.

**The Fix:**

```python
# GOOD - use tqdm.write for in-loop output
from tqdm.auto import tqdm

for item in tqdm(items, desc="Scanning"):
    result = process(item)
    tqdm.write(f"result: {result}")  # thread-safe, bar-aware
```

---

## WARNING: missing `total` on generators

**The Problem:**

```python
# BAD - shows spinner instead of bar; no ETA
for frame in tqdm(frame_generator()):
    process(frame)
```

**Why This Breaks:**
tqdm cannot infer length from a generator. You get an indefinite spinner with no ETA or percentage — useless for long diagnostic runs.

**The Fix:**

```python
# GOOD
total = compute_expected_frame_count(source)
for frame in tqdm(frame_generator(), total=total, desc="Replay", unit="frame"):
    process(frame)
```

If total is genuinely unknown, log it as a known limitation with `tqdm.write("total unknown — ETA unavailable")` at the start.