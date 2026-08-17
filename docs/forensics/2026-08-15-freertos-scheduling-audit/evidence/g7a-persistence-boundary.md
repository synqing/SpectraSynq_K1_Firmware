# Gate 7A — Persistence request boundary (no filesystem)

**Date:** 2026-08-17

```text
G7A = CLOSED
G7B = NEXT_ON_B489 (Captain 2026-08-17: this phase locked; progress to G7B)
F887 = OFFSITE_CONSULTANCY (G8 deferred until a replacement main unit exists)
```

`k1_persistence_request` is a bounded coalescing mailbox. Idempotent `SAVE_CONFIG` coalesces; non-idempotent requests occupy their own slot; full queue rejects with a counter. The TU contains no LittleFS/NVS/fopen call. Host: `tests/test_k1_persistence_request_boundary.py`.

`save_config_delayed()` also pushes a persist request. The Arduino loop drains the stub (`k1_persist_service_stub_once`) without writing flash. The existing `save_config()` path still performs the real write. G7B park is now wired in source (`K1_PERSIST_PARK_V1`); device coexistence proof still needs `B489_G7B_FLASH`.

**Ship path:** G7B on bench `B489A500`. G8 waits for a replacement main unit, then `F887_PRODUCTION_FLASH`.
