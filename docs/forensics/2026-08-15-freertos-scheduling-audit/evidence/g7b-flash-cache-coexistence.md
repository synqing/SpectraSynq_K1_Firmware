# Gate 7B — Real flash and cache coexistence

**Date:** 2026-08-17

```text
G7B_HOST          = CLOSED
G7B_DEVICE        = CLOSED
G7B_FLASH         = B489A500 k1_bench_im69d @ 1d457740 epoch 1786962873
G7B_CAPTAIN       = SAVE_PARK_PASS_2026-08-17
F887              = OFFSITE_CONSULTANCY (G8 production flash deferred until a replacement main unit exists)
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

## Device proof (Captain 2026-08-17)

Captain save-park PASS on bench `B489A500` / `k1_bench_im69d` @ `1d457740` (epoch `1786962873`): setting change, ~5 s debounce, lights parked then resumed, config survived reboot, music look held vs G3.

Named residuals (not required to close G7B): instrumented write-duration histogram, cache-disable trace, AP discontinuity across the write. G5 causal remains `NOT_PROVEN`.

## Ship path

1. Already: G2+G3+G7B CLOSED on bench `k1_bench_im69d` @ `1d457740` epoch `1786962873`.
2. Agent: G8 host integration (manifest, full suite, rollback artefact). No flash.
3. Captain: when a replacement main unit exists, issue `F887_PRODUCTION_FLASH`.
4. Agent: named production flash of that unit. **That flash is shipped.**
