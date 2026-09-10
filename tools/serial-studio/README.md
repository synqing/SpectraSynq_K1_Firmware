---
abstract: "SpectraSynq engineering instrument: Serial Studio dual-UART K1 observability. Dashboard is not evidence."
---

# Serial Studio — K1 engineering instrument

Stamp: **K1 SERIAL STUDIO INSTRUMENT — LIVE CAPTURE OPERATIONAL**. Dual UART, device clocks, Historian, raw bytes, project snapshot, read-only watcher: PASS. Immutable snapshot hashing and mixed-frame freshness: OPEN (hardening tranche). Dashboard is not evidence.

Serial Studio is the live front end for K1 lab work. It is not MATLAB and it is not a hard-real-time DAQ.

EdgeAI silicon: when this app holds USB, gates talk `localhost:7777` (`k1_gate`). See `SpectraSynq-EdgeAI-Lab/docs/mir/SERIAL_STUDIO.md`. GATE profile disables 250 ms polls.

| Layer | Job |
|-------|-----|
| K1 firmware | device timestamps, counters, measurements |
| Serial Studio | acquire, parse, display, record (CSV / Historian) |
| `scorer/` | verdict from SQLite / CSV |

## Layout

```
tools/serial-studio/
  README.md
  TELEMETRY_SCHEMA.md
  parsers/k1_ap_parser.js
  apply_engineering_project.py   # patches the live Serial Studio project via :7777
  scorer/subscribe_readonly.py   # read-only continuity / skew printer
  scorer/session_receipt.py      # SQLite → PASS/FAIL JSON
  captures/                      # gitignored DBs and CSVs
```

The live `.ssproj` is exported from the running app (API `project.save` cannot choose a path on v4.0.3). Copy is also kept next to the Serial Studio checkout at `examples/K1 Dual UART/`.

## Run

1. Serial Studio Pro 4.0.3 with API server on (ports 7777 and 8888).
2. `python3 apply_engineering_project.py` — parser, clocks, transforms, workspaces, Historian on, reconnect.
3. `python3 scorer/subscribe_readonly.py` — watch parse_seq gaps and device-vs-host skew. No device writes.
4. After a run: `python3 scorer/session_receipt.py --db <session.db>`.

## Policy locks

- CSV row interval = 0 ms.
- Do not align Bench and Main on host UART arrival time.
- Do not flash firmware from this folder.
- Screenshot ≠ evidence.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-08-31 | agent:grok | Engineering-instrument layout and run path. |
| 2026-08-31 | agent:grok | LIVE CAPTURE OPERATIONAL stamp; GATE vs OBSERVE pointer. |
