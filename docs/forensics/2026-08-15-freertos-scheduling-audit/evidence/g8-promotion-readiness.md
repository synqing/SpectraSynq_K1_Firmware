# Gate 8 — Promotion readiness

**Status:** `OPEN` — host units G2–G7A are in source; device G7B and F887 remain holds.

## Included units (this HEAD series)

1. Phase 0 restamp — AP service p99 ≤ 8000 µs; G2 = Cross40+Lane4
2. G2 — Cross40+Lane4 on `k1_hardware`; `G2_DEVICE = CLOSED` on `k1_bench_im69d` @ `e911f86d`
3. G3 Candidate A — coherent `K1AudioFrame` + sidecar freeze (lock-margin capture not taken)
4. G4 — command channels, dual-scene publish/apply
5. G5 — startup ratchet wired; causal trace NOT_PROVEN
6. G6 — `NOT_REQUIRED` (two-task topology retained)
7. G7A — persistence request boundary (no filesystem)

## Explicit holds

```text
G2_DEVICE               = CLOSED (bench B489, e911f86d)
G3_LOCK_MARGIN_CAPTURE  = NOT_TAKEN (needs B489_G3_FLASH)
G5_CAUSAL_TRACE         = NOT_PROVEN
G7B                     = NOT_STARTED (needs B489_G7B_FLASH)
F887_FLASH              = NO (requires separate Captain GO = F887_PRODUCTION_FLASH)
TEN_MS_AP_HOP           = still NO
```

## Rollback

- G2: delete Cross40 + Lane4 flags on `k1_hardware`
- G3: delete `-DK1_AUDIO_FRAME_V1=1`
- G4: delete `-DK1_COMMAND_CHANNELS_V1=1`
- G7A: remove `persistence/k1_persistence_request.cpp` from `build_src_filter`

Main-unit ship stamp: named `F887_PRODUCTION_FLASH` after G7B close.
