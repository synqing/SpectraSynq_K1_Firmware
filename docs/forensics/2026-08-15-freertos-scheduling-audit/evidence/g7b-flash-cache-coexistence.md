# Gate 7B — Real flash and cache coexistence

**Date:** 2026-08-17

```text
G7B_HOST          = WIRED
G7B_DEVICE        = PENDING_B489_G7B_FLASH
F887              = OFFSITE_CONSULTANCY (G8 deferred until a replacement main unit exists)
REVERT            = delete -DK1_PERSIST_PARK_V1=1 from [env:k1_hardware]
```

## What landed in source

Shipping `k1_hardware` (and inheriting `k1_bench_im69d`) now compiles the existing CL-1 ack-barrier without enabling `K1_EFFECT_FRAMEWORK_V1`.

- `lock_leds()` / `unlock_leds()` wait for Core 1 to park at frame-top before LittleFS/NVS writes.
- `led_task` parks, publishes `render_thread_parked`, and self-heals a stuck halt after 1 s.
- Failed `LittleFS.open` paths in `save_config`, `load_config`, and noise-cal save/load always `unlock_leds()`.
- Boot `init_fs()` does not spin 100 ms per nested lock: `lock_leds()` returns immediately when `led_task` is still null.
- G7A mailbox stays a request boundary. `check_settings()` still owns the 5 s debounce and is the real writer. The Arduino loop still drains `k1_persist_service_stub_once()` without writing flash. A G7B red can delete the park flag without invalidating G7A.

Host: `tests/test_k1_persist_park_static.py` plus the existing persist-boundary test.

## Device proof still owed (named `B489_G7B_FLASH` only)

Record measurement, not intention, on bench `B489A500` / `k1_bench_im69d`:

```text
cache-disable behaviour during a real flash write
render and cache safety while the write is in flight
park acknowledgement from the render owner before the write begins
measured write duration / park ack
AP discontinuity across the write
config survives reboot
```

A red rolls back flash servicing (delete the park flag and restore the last known-good bench binary) without invalidating G7A.

## Ship path

1. Already: G2+G3 on bench `k1_bench_im69d` @ `c671ddf3`; G7B park in `k1_hardware` source on this branch.
2. Agent: host/build green, then named bench flash of the G7B HEAD to `B489A500` only (`B489_G7B_FLASH`).
3. Captain: confirm a real config save parks lights, write completes, lights resume, config survives reboot.
4. G8 waits until Captain has a replacement main unit, then a separate `F887_PRODUCTION_FLASH`. That flash is shipped.
