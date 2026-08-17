# Gate 6 — Topology decision

**Date:** 2026-08-17  
**Authority:** G5 attribution from pack `docs/forensics/runtime-evidence/20260817T-g2g3-e2e-ab-b489/`

```text
G6 = NOT_REQUIRED
TOPOLOGY = TWO_TASK_RETAINED (Arduino loop on Core 0, led_task on Core 1)
REASON = B489 A/B tail moved with GDFT Cross0 vs Cross40+Lane-4 (11840 µs vs 7680/7776 µs), not with serial or control service contention.
```
