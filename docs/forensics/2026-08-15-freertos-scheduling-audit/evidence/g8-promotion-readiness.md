# Gate 8 — Promotion readiness

**Status:** `DEFERRED` — G2–G7A locked on branch and bench; G7B is the next bench phase; main K1 is offsite.

## Included units (this HEAD series)

1. Phase 0 restamp — AP service p99 ≤ 8000 µs; G2 = Cross40+Lane4
2. G2 — Cross40+Lane4 on `k1_hardware`; `G2_DEVICE = CLOSED`
3. G3 Candidate A — coherent `K1AudioFrame` + sidecar freeze; Captain perceptual PASS on `c671ddf3`
4. G4 — command channels, dual-scene publish/apply
5. G5 — startup ratchet wired; causal trace NOT_PROVEN
6. G6 — `NOT_REQUIRED` (two-task topology retained)
7. G7A — persistence request boundary (no filesystem)

## Explicit holds

```text
G2_DEVICE               = CLOSED (bench B489)
G3_DEVICE_PERCEPTUAL    = CLOSED (c671ddf3)
G5_CAUSAL_TRACE         = NOT_PROVEN
G7B                     = NEXT_ON_B489
F887_UNIT               = OFFSITE_CONSULTANCY_2026_08_17
F887_FLASH              = DEFERRED until a replacement main unit exists
TEN_MS_AP_HOP           = still NO
```

Main-unit ship stamp when a replacement exists: named `F887_PRODUCTION_FLASH` after G7B close.
