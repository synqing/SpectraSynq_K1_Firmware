# Pandas Workflows Reference

## Contents
- Diagnostic Notebook Workflow
- A/B Regression Workflow
- Ingest Pipeline Checklist
- Anti-Patterns in Notebook Workflows

---

## Diagnostic Notebook Workflow

Used in `notebooks/audio_semantic_diagnostics.ipynb` for audio-semantic forward-graft validation.

```
1. Ingest raw AP stream CSV via apstream_ingest.py helpers
2. Establish DatetimeIndex, sort
3. Apply window mask (crop to test window)
4. Compute rolling metrics
5. Tag derived columns via assign()
6. Pass to diag_helpers plot functions
7. Export aggregate summary dict for memo
```

Copy this checklist and track progress:
- [ ] Load CSV, set DatetimeIndex, sort
- [ ] Verify no NaN in `confidence` / `density` columns before window
- [ ] Apply start/end mask before any aggregation
- [ ] Compute per-metric rolling means
- [ ] Tag `locked` column (`confidence > 0.60`)
- [ ] Call `plot_ap_capture_summary()` and verify axes
- [ ] Export summary stats to validation memo

---

## A/B Regression Workflow

Compares `sb_tempo` final vs baseline metrics. Used to confirm forward-graft improvements (density 5.6 → 97.2%, obs #58840).

```python
# new code to add
import pandas as pd

def load_ab(final_path: str, baseline_path: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    def load(p):
        df = pd.read_csv(p, parse_dates=["timestamp"])
        return df.set_index("timestamp").sort_index()
    return load(final_path), load(baseline_path)

def summarize_ab(final, baseline, metrics=("confidence", "density")):
    rows = {}
    for m in metrics:
        rows[m] = {
            "baseline_mean": baseline[m].mean(),
            "final_mean": final[m].mean(),
            "delta": final[m].mean() - baseline[m].mean(),
        }
    return pd.DataFrame(rows).T
```

Validate: delta on `density` should be strongly positive post-graft. If negative, the window mask is misapplied — check start/end crop.

---

## Ingest Pipeline Checklist

For `apstream_ingest.py` — runs before notebook analysis:

- [ ] Timestamp regex matches log format (obs #58849 — regex was broken)
- [ ] `t_local` column parsed to datetime, not left as string
- [ ] AGC series aligned to onset series via `merge_asof`, not naive join
- [ ] Warning deduplication active (obs #58845 — duplicate warnings inflated row counts)
- [ ] Output CSV sorted by timestamp before write

Iterate-until-pass:
1. Run ingest on a known fixture
2. Assert: `df.index.is_monotonic_increasing`
3. Assert: `df["confidence"].isna().sum() == 0` in the test window
4. If either fails, fix ingest layer — not the notebook

---

## WARNING: plt.show() in Headless Jupyter

**The Problem:**

```python
# BAD — blocks non-interactive kernel (obs #58838)
import matplotlib.pyplot as plt
plt.show()
```

**Why This Breaks:** The project Jupyter kernel runs non-interactively in some diagnostic flows. `plt.show()` hangs indefinitely.

**The Fix:** Use plotly (preferred in this project) or save figures explicitly:

```python
# GOOD — plotly (preferred), see the plotly skill
import plotly.express as px
fig = px.line(df, y="confidence")
fig.write_html("output.html")

# GOOD — matplotlib fallback
fig.savefig("output.png", dpi=150)
plt.close(fig)
```

---

## WARNING: Running Analysis Outside Project venv

**The Problem:** pandas installed system-wide may be a different version than the project-local install (obs #58835 — Jupyter installed project-locally only).

**The Fix:**

```bash
# Always activate project environment first
source .venv/bin/activate   # or: uv run jupyter notebook
jupyter notebook notebooks/audio_semantic_diagnostics.ipynb
```

Never run `jupyter` from the system Python path for this project. Version mismatches silently produce different DataFrame dtypes and break column contracts expected by `diag_helpers.py`.