# Jupyter Patterns Reference

## Contents
- Headless rendering
- Notebook cell structure
- diag_helpers conventions
- Anti-patterns

## Headless Rendering

**ALWAYS** set backend before importing pyplot. The K1 diagnostic kernel runs without a display server.

```python
# GOOD — backend set before pyplot
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
```

```python
# BAD — plt.show() in headless kernel silently does nothing, figure lost
import matplotlib.pyplot as plt
plt.plot(data)
plt.show()  # No-op. Data lost.
```

Save every figure explicitly:

```python
fig.savefig('notebooks/output/agc_debug_run.png', dpi=150, bbox_inches='tight')
plt.close(fig)  # Prevent memory accumulation across cells
```

## Notebook Cell Structure

Keep notebooks executable top-to-bottom with no hidden state. Each diagnostic section:

1. **Import cell** — all imports, backend config
2. **Load cell** — ingest data via `apstream_ingest.py`
3. **Plot cells** — one concern per cell, save output
4. **Summary cell** — scalar metrics only (no figures)

NEVER scatter imports across cells. A notebook that fails mid-run leaves partial output indistinguishable from complete output.

## diag_helpers.py Conventions

Existing functions (verified from repo):
- `plot_ap_capture_summary(df, window_mask=None, ax=None)` — AP capture overview
- `plot_agc_debug(df, window_mask=None, ax=None)` — AGC gain + NaN-aligned series

**Pattern all helpers follow:**

```python
def plot_<series>(df, window_mask=None, ax=None):
    # 1. Create figure if no ax provided (composable)
    if ax is None:
        fig, ax = plt.subplots(figsize=(12, 4))
    else:
        fig = ax.get_figure()

    # 2. Apply window mask before any computation
    if window_mask is not None:
        df = df[window_mask]

    # 3. Plot using t_local (NOT raw timestamp)
    ax.plot(df['t_local'], df['value'])

    # 4. Always label axes
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('<series label>')
    return fig, ax
```

**Why `t_local`:** raw timestamps from apstream_ingest have offset drift; `t_local` is the normalized relative time aligned to capture window start.

## WARNING: Mutable Default Arguments in Plot Helpers

**The Problem:**

```python
# BAD — shared mutable default
def plot_series(df, channels=['L', 'R']):
    channels.append('debug')  # Mutates across calls
```

**The Fix:**

```python
# GOOD
def plot_series(df, channels=None):
    if channels is None:
        channels = ['L', 'R']
```

## WARNING: Modifying Notebooks with Write Tool

NEVER use the `Write` tool to overwrite `.ipynb` files — it corrupts cell metadata and output arrays. Use `NotebookEdit` for cell edits or `jupyter nbconvert` for full re-execution.

## apstream_ingest.py Parser Facts

Key fixes landed 2026-06-05 (verified in repo):
- Timestamp regex corrected (previously missed sub-second precision)
- AGC NaN alignment fixed (gain column now aligns to AP frame boundaries)
- Warning deduplication bug fixed

When parsing fails, check: timestamp format in the raw log matches the current regex, and that AGC rows have the expected field count before NaN-fill.