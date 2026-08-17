# Gate 5 — Startup ratchet wired; causal trace not proven on device

**Date:** 2026-08-17

```text
G5_STARTUP_RATCHET = WIRED
G5_CAUSAL_TRACE    = NOT_PROVEN
```

`led_task` creation is latched: require, note_created, validate_handle. A failed create prints `STARTUP_RATCHET: degraded missing=led_task`. Host: `tests/test_k1_startup_ratchet.py`.

Capture→photon field list is enumerated in `gate0/contract.json` and the audio-frame identity prefix. No current-device trace with confirmed `rmt_complete_us` / `rmt_completion_source` was taken this session.

**G6 entry predicate:** the 2026-08-17 B489 A/B pack (`20260817T-g2g3-e2e-ab-b489`) shows Arm A (Cross0) quiet p99 11840 µs vs Arm B (Cross40+Lane-4) 7680 / 7776 µs. The tail tracks GDFT demand, not serial/control/service scheduling.

**Ship path for G5 causal:** named B489 GO for `k1_bench_scheduling_trace_dev` (or equivalent) capture. No F887 flash.
