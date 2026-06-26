# Pandas Patterns Reference

## Contents
- Time-Series Indexing
- Safe Transforms
- Anti-Patterns
- Integration with diag_helpers

---

## Time-Series Indexing

SensoryBridge diagnostic streams are timestamp-indexed at 133 Hz. Always establish a `DatetimeIndex` immediately after load — downstream rolling/resample ops require it.

```python
df = pd.read_csv(path)
df["t"] = pd.to_datetime(df["t_local"], unit="s")
df = df.set_index("t").sort_index()
```

**Why sort?** `apstream_ingest.py` has had timestamp ordering bugs (obs #58849). Unsorted indexes silently corrupt rolling windows.

---

## Safe Transforms with `assign()`

NEVER mutate a DataFrame in-place inside a diagnostic function — callers share the reference and silent corruption breaks A/B comparisons.

```python
# BAD — mutates caller's frame
def tag_locked(df):
    df["locked"] = df["confidence"] > 0.60  # side effect!

# GOOD — returns new frame
def tag_locked(df):
    return df.assign(locked=lambda x: x["confidence"] > 0.60)
```

---

## Window-Mask Application

`diag_helpers.py` had window-mask bugs (obs #58848) — masks applied after aggregation instead of before. Always filter THEN aggregate.

```python
# BAD — aggregates outside window, then masks (wrong result)
mean_conf = df["confidence"].rolling("500ms").mean()
windowed = mean_conf[mask]

# GOOD — restrict index first
windowed = df.loc[start:end, "confidence"].rolling("500ms").mean()
```

---

## NaN Alignment in Multi-Series Frames

AGC debug series have different sample rates than onset frames. Joining them naively produces NaN floods. Use `merge_asof` for nearest-timestamp alignment.

```python
# new code to add
merged = pd.merge_asof(
    onset_df.sort_index().reset_index(),
    agc_df.sort_index().reset_index(),
    on="timestamp",
    direction="nearest",
    tolerance=pd.Timedelta("10ms"),
)
```

From obs #58849: timestamp regex and AGC NaN alignment were both parser-layer bugs — fix at ingest, not downstream with `fillna`.

---

## WARNING: Chained Indexing

### WARNING: Chained Indexing (`df[mask]["col"] = val`)

**The Problem:**

```python
# BAD — silently writes to a copy, not the original
df[df["locked"] == True]["gain"] = 1.0
```

**Why This Breaks:**
1. Pandas may return a copy on the first `[]` — the assignment targets the copy, not `df`.
2. No error is raised; the data appears unchanged.
3. In replay notebooks, this produces metrics that look correct but aren't.

**The Fix:**

```python
# GOOD — single indexing operation
df.loc[df["locked"] == True, "gain"] = 1.0
```

---

## Integration with diag_helpers

`notebooks/diag_helpers.py` exposes `plot_ap_capture_summary()` and `plot_agc_debug()`. These expect DataFrames with specific column contracts:

| Function | Required columns | Index |
|----------|-----------------|-------|
| `plot_ap_capture_summary` | `confidence`, `density`, `locked` | DatetimeIndex |
| `plot_agc_debug` | `gain`, `rms`, `agc_mode` | DatetimeIndex |

Pass the raw ingest DataFrame through the tagging pipeline (`tag_locked`, window-mask) before calling these. See the **plotly** skill for visualisation layer details.