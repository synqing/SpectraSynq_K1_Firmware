# Gate 7A — Persistence request boundary (no filesystem)

**Date:** 2026-08-17

```text
G7A = CLOSED
G7B = NOT_STARTED (needs B489_G7B_FLASH GO)
```

`k1_persistence_request` is a bounded coalescing mailbox. Idempotent `SAVE_CONFIG` coalesces; non-idempotent requests occupy their own slot; full queue rejects with a counter. The TU contains no LittleFS/NVS/fopen call. Host: `tests/test_k1_persistence_request_boundary.py`.

`save_config_delayed()` also pushes a persist request. The Arduino loop drains the stub (`k1_persist_service_stub_once`) without writing flash. The existing `save_config()` path still performs the real write. G7B is the gate that proves cache-disable / park / real write coexistence.

**Ship path:** G7B under named `B489_G7B_FLASH` GO, then G8 + F887 GO.
