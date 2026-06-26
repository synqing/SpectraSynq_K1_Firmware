# Dash Workflows Reference

## Contents
- Standing up a new diagnostic dashboard
- Wiring firmware telemetry via serial/WebSocket
- Promoting a notebook plot to a dashboard panel
- Running alongside pytest regression harness
- Deployment checklist

---

## Standing Up a New Diagnostic Dashboard

Copy this checklist:
- [ ] Install: `pip install dash plotly pandas`
- [ ] Create `scripts/dashboard/app.py` (never at project root)
- [ ] Define `PANEL_IDS` dict mapping metric name → component id
- [ ] Build `make_layout()` returning `html.Div` tree
- [ ] Add `dcc.Interval` as the single refresh trigger
- [ ] Wire one multi-output callback per data source (not per panel)
- [ ] Validate: `python scripts/dashboard/app.py` → open `http://localhost:8050`
- [ ] Add `prevent_initial_call=True` where data may not be available at startup

---

## Wiring Firmware Telemetry via Serial

The firmware emits diagnostic packets on USB CDC (115200 baud). Feed them into a thread-safe buffer:

```python
# new code to add
import serial, threading, collections

SERIAL_PORT = "/dev/tty.usbmodem*"  # glob or explicit
buf = collections.deque(maxlen=500)
lock = threading.Lock()

def serial_reader(port: str):
    with serial.Serial(port, 115200, timeout=1) as s:
        while True:
            line = s.readline().decode(errors="ignore").strip()
            if line:
                with lock:
                    buf.append(parse_line(line))

threading.Thread(target=serial_reader, args=(SERIAL_PORT,), daemon=True).start()
```

Then in the Dash callback, `with lock: snapshot = list(buf)`. See the **python** skill for threading patterns.

---

## Wiring via apstream / VPAB Packets

The regression harness (`scripts/regression-harness/apstream_ingest.py`) already parses VPAB packets. Reuse its parser:

```python
# new code to add — import existing parser, do NOT duplicate
import sys
sys.path.insert(0, "scripts/regression-harness")
from apstream_ingest import parse_vpab_line, VPABRecord

# Feed parsed records into the shared buffer used by Dash callbacks
```

NEVER duplicate the packet parsing logic. One canonical parser, shared by both the harness and the dashboard.

---

## Promoting a Notebook Plot to a Dashboard Panel

1. In the notebook (`notebooks/audio_semantic_diagnostics.ipynb`), extract the figure-building function into `notebooks/diag_helpers.py`.
2. Import that helper in the dashboard:

```python
# new code to add
sys.path.insert(0, "notebooks")
from diag_helpers import plot_agc_debug, plot_ap_capture_summary
```

3. Wrap in a callback:

```python
@app.callback(Output("panel-agc-trace", "figure"), Input("refresh", "n_intervals"))
def agc_panel(_):
    with lock:
        snap = list(buf)
    return plot_agc_debug(snap)  # existing helper, unchanged
```

Do not copy-paste plot logic into the dashboard. If `diag_helpers.py` needs an update, update it once — both notebook and dashboard pick it up. See the **jupyter** skill for notebook extraction patterns and the **matplotlib** skill if converting matplotlib figures to Plotly.

---

## Running Alongside pytest Regression Harness

The pytest harness (`pytest tests/ -v`) writes replay metrics to `docs/measurements/`. The dashboard can load these as a static post-run view:

```bash
# Run harness, then launch dashboard against its output
pytest tests/ -v
python scripts/dashboard/app.py --replay docs/measurements/tempo-octave-baseline.tracks.csv
```

Iterate-until-pass for dashboard validation:
1. Change callback or layout
2. Restart: `python scripts/dashboard/app.py`
3. Open `http://localhost:8050`, verify panel renders correctly
4. If blank panel: check browser console + server stderr for callback exception
5. Repeat from step 1 until all panels show valid data

---

## Deployment Checklist

For a shared diagnostic dashboard (e.g., on the bench machine):

- [ ] Use gunicorn: `gunicorn scripts.dashboard.app:server -b 0.0.0.0:8050`
- [ ] Set `debug=False` in `app.run()` — never expose debug mode on a network interface
- [ ] Bind to loopback (`127.0.0.1`) unless intentionally sharing on LAN
- [ ] Add `--workers 1` if the dashboard uses thread-local serial state (multi-worker breaks shared buffer)
- [ ] NEVER commit device serial ports or MAC addresses as hardcoded strings — use env vars or CLI args