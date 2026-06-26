# Dash Patterns Reference

## Contents
- Callback anti-patterns
- Layout composition
- Data ingestion patterns
- Multi-output callbacks
- Error handling in callbacks

---

## Callback Anti-Patterns

### WARNING: Global mutable state mutated inside callbacks

**The Problem:**
```python
# BAD — race condition under concurrent users / rapid interval ticks
history = []

@app.callback(Output("plot", "figure"), Input("tick", "n_intervals"))
def update(_):
    history.append(get_latest())  # mutates module-level list
    return make_figure(history)
```

**Why This Breaks:**
1. Dash can serve multiple sessions; callbacks run in threads — `history` is shared and unsynchronized.
2. Under `dcc.Interval` at 500ms, appends accumulate unboundedly → memory leak.
3. In multi-worker gunicorn, each worker has its own `history` → sessions see inconsistent state.

**The Fix:**
```python
# GOOD — read from an externally managed, lock-protected buffer
@app.callback(Output("plot", "figure"), Input("tick", "n_intervals"))
def update(_):
    with data_lock:
        snapshot = list(shared_buffer)  # copy, don't mutate
    return make_figure(snapshot)
```

---

### WARNING: Returning `None` from a callback without `no_update`

**The Problem:**
```python
# BAD — returns None when condition not met, clears the component
@app.callback(Output("graph", "figure"), Input("btn", "n_clicks"))
def on_click(n):
    if not n:
        return  # implicitly None → Dash sets figure=None → layout breaks
```

**Why This Breaks:**
Dash serializes `None` as JSON null and pushes it to the component, replacing the existing figure with nothing.

**The Fix:**
```python
from dash import no_update

@app.callback(Output("graph", "figure"), Input("btn", "n_clicks"),
              prevent_initial_call=True)
def on_click(n):
    if not n:
        return no_update  # preserves current state
    return build_figure()
```

---

## Layout Composition

Prefer named `id` strings that match the metric domain — they become the callback contract:

```python
# new code to add
PANEL_IDS = {
    "agc":    "panel-agc-trace",
    "tempo":  "panel-tempo-confidence",
    "onset":  "panel-onset-density",
}

def make_layout():
    return html.Div([
        html.H2("K1 Audio Diagnostics"),
        html.Div(
            [dcc.Graph(id=v, style={"height": "250px"}) for v in PANEL_IDS.values()],
            style={"display": "grid", "gridTemplateColumns": "1fr 1fr 1fr", "gap": "8px"},
        ),
        dcc.Interval(id="refresh", interval=500, max_intervals=-1),
    ])
```

---

## Data Ingestion Patterns

### Feeding from a pytest replay result (offline)

```python
# new code to add — load regression replay CSV into dashboard
import pandas as pd

def load_replay(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["t"] = df["frame"] / 133.0  # 133 Hz AP rate
    return df

# In callback:
@app.callback(Output(PANEL_IDS["tempo"], "figure"), Input("refresh", "n_intervals"))
def show_tempo(_):
    df = load_replay("docs/measurements/tempo-octave-baseline.tracks.csv")
    fig = go.Figure(go.Scatter(x=df["t"], y=df["confidence"], mode="lines",
                               name="tempo confidence"))
    fig.update_layout(yaxis_range=[0, 1], xaxis_title="s", yaxis_title="conf")
    return fig
```

See the **pandas** skill for DataFrame manipulation and the **plotly** skill for figure construction.

---

## Multi-Output Callbacks

AVOID one callback per panel when all panels share the same trigger — that fires N serial round-trips.

```python
# GOOD — one callback, multiple outputs
@app.callback(
    Output(PANEL_IDS["agc"],   "figure"),
    Output(PANEL_IDS["tempo"], "figure"),
    Output(PANEL_IDS["onset"], "figure"),
    Input("refresh", "n_intervals"),
)
def update_all(_):
    with data_lock:
        snap = snapshot()
    return build_agc(snap), build_tempo(snap), build_onset(snap)
```

---

## Error Handling in Callbacks

Unhandled exceptions in callbacks crash that update silently in production. Surface them explicitly:

```python
# new code to add
import traceback
from dash import no_update

@app.callback(Output("graph", "figure"), Input("tick", "n_intervals"))
def safe_update(n):
    try:
        return build_figure()
    except Exception:
        traceback.print_exc()
        return no_update  # keep last good state; don't blank the panel
```

For dev mode (`debug=True`), Dash renders the exception in the browser — disable for any shared/device-connected dashboard.