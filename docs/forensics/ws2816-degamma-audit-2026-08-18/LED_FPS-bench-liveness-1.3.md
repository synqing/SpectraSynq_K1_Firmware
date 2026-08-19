# 1.3 Bench `LED_FPS: 0.00` — dump-era liveness

**Date:** 2026-08-19  
**Dump:** `DUMP_bench_B489A500_2026-08-19.txt` (`SYSTEM_FPS: 138.88`, `LED_FPS: 0.00`, `next_save_time: 3129649` ≈ 52 min uptime)  
**Writer:** `SPECTRASYNQ_K1_FIRMWARE.ino:1698` (also `:1389` / `:1417` probe-only). Present in deployed `573206c0`.

## What this is not

A first-sample EMA seed bug. `LED_FPS = 0.95*old + 0.05*(1e6/Δt)`. From any non-zero interval the gauge leaves 0.00 within seconds. Seeding `last_frame_us` does not close a 52-minute zero.

Tonight (2026-08-19, music on both plates) is not evidence about that dump. The plates being on now does not prove the 19 Aug capture saw a live Core-1 writer.

## How the frame body can skip the writer

The production write is inside `if (led_thread_halt == false) { ... LED_FPS = ... }` (`.ino:1341–1698`).

| Candidate | Verdict for a 52 min zero |
|---|---|
| `K1_LED_PARK_V1` halt without unlock | **Ruled out as a latched freeze.** Self-heal force-resumes after 1 s (`.ino:1329–1331`). `K1_PERSIST_PARK_V1` is on `k1_hardware` and inherited by `k1_bench_im69d`. |
| Motion-probe / VPML `continue` | **Off** on ship IM69D envs. Those paths still write `LED_FPS` anyway. |
| `led_thread` never started / died before the first write | **Possible.** Global stays at `0.0`. Core 0 `loop()` (and `SYSTEM_FPS`) would keep running. |
| Halt window coinciding with `:dump` | **Possible only if the writer had never run** (boot 0.0). After any successful frame the EMA is non-zero even while parked for ≤1 s. |
| Cross-core visibility (`LED_FPS` is not `volatile`, Core 1 writes, Core 0 `:dump` reads) | **Possible for a torn/stale 0.00 snapshot**, weaker as a 52 min exclusive explanation unless Core 0 never observed a store. |

Named mechanism for the dump: **the Core-0-visible `LED_FPS` was never updated** — either Core 1 did not execute the `:1698` writer after boot, or Core 0 never observed those stores. Park/halt cannot hold for 52 minutes on this env.

## Discriminator (no flash)

`:dump` on B489 under music (serial GO).

- Non-zero `LED_FPS` → 19 Aug is dump-era only (thread death, dump-during-never-started, or a one-off visibility miss). Do not treat as a standing VP-idle defect.
- Still `0.00` while the plate moves → treat non-`volatile` `LED_FPS` plus a Core-1 heartbeat as the fix, **not** an EMA seed.

## Fix proposal (do not land in step 1)

1. `volatile` on `LED_FPS` (and consider `SYSTEM_FPS` for symmetry).
2. Optional Core-1 frame counter printed by `:dump`.
3. Do not claim a `last_frame_us` seed closed C3.

Preserve `last_frame_us > 0` semantics for effect-framework dt (`.ino:470`) if seed hygiene lands later for RPL boot-transient only.
