---
abstract: "Canonical record for the k1_bench_im73d_ble DEMO build (2026-07-04): bench K1 running the IM73D122 PDM mic on the live production AP+VP PLUS the NimBLE BLE-MIDI central so the K718 Remoted dial controls it live for investor demos. SEPARATE workstream from IM73D eval/tuning (do NOT measure mic SNR on this radio build). Composes k1_bench_im73d + the 3 BLE deltas (no harness). Records the 4-SSA injection-point investigation, build/gate/flash/runtime evidence, and outstanding items. NON-SHIPPABLE (radio present). Verify against live git/device before trusting deployed state."
---

# IM73D + BLE-MIDI Demo Build — `k1_bench_im73d_ble` (2026-07-04)

## What this is (and what it is NOT)

Captain directed two **separate** workstreams (2026-07-04):

1. **IM73D122 eval / tuning / burn-in** → stays on the radio-free `k1_bench_im73d`. Mic SNR/tuning numbers are measured **there**. (See `im73d122-productionization-handover-2026-07-03.md`.)
2. **This demo build** → `k1_bench_im73d` **+ BLE-MIDI central** so the **K718 "Remoted" dial drives the K1 live** in front of investors. A *demo* build, not a *measurement* build.

> **Do NOT take mic SNR/tuning measurements on `k1_bench_im73d_ble`.** The BLE central runs a Core-0 task alongside the hard-real-time audio pipeline, and the 2.4 GHz interference A/B is still open — radio load can perturb audio timing. Measurement lives on `k1_bench_im73d` (radio-free).

## Build composition (the TRIZ resolution)

The two capabilities lived on **different inheritance branches**: IM73D on the *bench-reference* chain, BLE-MIDI (`k1_ble_remoted_probe`) on the *production+harness* chain. PlatformIO has no multiple inheritance, so the new env composes the bench+IM73D base with **only** the 3 BLE deltas — pointedly NOT extending the harness (zero diag/trace instrumentation, production stays byte-identical):

```ini
[env:k1_bench_im73d_ble]
extends = env:k1_bench_im73d          ; bench GPIO pinmap + -DK1_MIC_IM73D_PDM_V1
build_src_filter =
    ${env:k1_hardware.build_src_filter}
    +<network/ble_remoted_central.cpp>
    +<network/k1_ble_midi_decoder.cpp>
build_flags =
    ${env:k1_bench_im73d.build_flags}
    -DK1_BLE_REMOTED
lib_deps =
    ${env:k1_hardware.lib_deps}
    h2zero/NimBLE-Arduino@^2.5.0
```

Guard registration: `k1_bench_im73d_ble` added to the **bench K1 tuple** in `scripts/platformio/k1_upload_guard.py` (identity `B489A500` / `B4:3A:45:A5:89:B4`). Without registration the guard **fails open** (no GPIO protection) — registration is mandatory.

**Revert** = delete the `[env:k1_bench_im73d_ble]` block in `platformio.ini` + the `k1_bench_im73d_ble` line in `k1_upload_guard.py`. Additive only; `k1_hardware` / `k1_bench_reference` / `k1_bench_im73d` stay byte-identical.

## Injection-point investigation (4-SSA fan-out, all consumed per ssa-management)

| SSA | Evidence question | Verdict | Orchestrator re-run |
|-----|-------------------|---------|---------------------|
| 1 · linkage | Does BLE→`k1_control_apply` link & wire on the bench chain w/o harness or `k1_wireless.cpp`? | **VERIFIED** | re-grep'd `.ino` calls under `#ifdef K1_BLE_REMOTED`; `k1_control_apply()` (`control/k1_control_facade.cpp`) is **unconditional** (no ifdef strips it); **+ the actual compile** |
| 2 · RT/RF | Does a Core-0 NimBLE task confound the mic eval / perturb audio? | **VERIFIED (risk real)** | re-read `ble_remoted_central.cpp:229` (`xTaskCreatePinnedToCore(...,0)`) + NimBLE `nimconfig.h:213` (`CONFIG_BT_NIMBLE_PINNED_TO_CORE 0`) + the IM73D-specific I2S stall→silent-zero-fill branch. Both the app task **and** NimBLE host default to Core 0. Confound is real for *measurement*; moot for *demo* (separate workstreams). |
| 3 · K718 protocol | Can the K718 emit matching BLE-MIDI, or is control blocked on K718-side work? | **provisional (later overridden by runtime — see below)** | static source audit only; not orchestrator-verified. Claimed the K718 TX sketch (`~/Downloads/k718_halo_phase1_source/full_sketch`) was protocol-byte-exact but never compiled/flashed. |
| 4 · device/gate | Flash target + guard edit + gate safety? | **VERIFIED** | target = bench `B489A500` (NOT the drifted `1101=main` the *stale* registry claimed); 1 guard line; gate tests stay green on the clean bench chain (MUST-AVOID `extends=k1_ble_remoted_probe`). |

**Verified wiring path:** K718 dial → NimBLE notify → `k1_ble_midi_decode_packet` → queue → `k1_ble_remoted_poll()` (main loop) → `k1_control_apply()` → `CONFIG.*` mutation + `save_config_delayed()`.

## Evidence

**Build (host):** `pio run -e k1_bench_im73d_ble` → `[SUCCESS]`, `firmware.bin` ≈ 912 KB, **RAM 38.0% / Flash 13.9%** (NimBLE fits with large headroom). Env committed on `lane/im73d-pdm-eval`; device deployed at `d32770d`.

**Gates (host):** `pytest tests/test_dev_instrumentation_boundary.py tests/test_token_scrub_static.py` → **13/13 PASS**. The new env classifies as clean bench-chain production; no diag/radio tokens leak; production envs byte-identical.

**Flash (bench K1, 2026-07-04):** guard verdict `[k1-upload-guard] k1_bench_im73d_ble: /dev/tty.usbmodem1101 verified as 2nd bench K1 (B4:3A:45:A5:89:B4, chip B489A500, bench-reference GPIO)`. `Wrote 912224 bytes … Hash of data verified … Hard resetting … [SUCCESS]`.

**Runtime (passive, read-only serial — no bytes sent, cal policy intact):** boots clean, no panic/guru/bootloop/brownout over a 10 s capture; steady loop emitting:
```
[ble_remoted] counters linked=1 notify=0 decoded=0 enqueued=0 queue_drops=0 decode_errors=0 apply_ok=0 apply_fail=0
```
**`linked=1`** = the K1 central connected to a live BLE-MIDI peripheral advertising the "SpectraSynq Remoted" service. This **overrides SSA-3's provisional "K718 TX never flashed"** finding (on-silicon runtime > static source audit): a matching Remoted peripheral IS live and linked. `notify=0` = connected but **no control messages have flowed yet** — nobody has turned the dial.

## ⚠ Port re-scramble caught at flash time (registry correction)

Live enumeration at flash time (pyserial **and** the upload-guard, dual-source): `1101 = bench K1 (B489A500)`, `2101 = main K1 (F887A500)`, `101 = a third S3 (AC:A7:04:EE:57:7C)`. The registry's section-1 hint and its 2026-06-19 verification recorded `1101 = main K1` — **stale**; the ports re-scrambled again (exactly the registry's own "verify every session" warning). The flash was safe because the guard keys on USB serial, not port. Registry deployed-state table + section-1 hints updated accordingly.

## Outstanding

1. **Control proof (the demo's real acceptance):** turn the K718 dial while capturing serial read-only; confirm `notify → decoded → enqueued → apply_ok` climb and a matching `CONFIG.*` change on the K1. Until then, "linked" is proven but "dial drives K1" is not.
2. **K718-side (largely confirmed):** `linked=1` = a live "SpectraSynq Remoted" peripheral. The device registry §1 identifies the K718 on `/dev/cu.usbmodem101` (MAC `ac:a7:04:ee:57:7c`) running `JC3636_K718_REMOTED_BLE_V1` (knob repo `~/Workspace_Management/Software/JC3636K518CN_knob_EN-bleremote/custom/JC3636_K718_REMOTED_BLE_V1`, bench-PASS in its `HARDWARE_VERIFY.md`) — so the controller half is real and flashed, **not** the never-built `k718_halo_phase1_source` sketch SSA-3 pointed at. Remaining: confirm the on-bus K718 is that build and close the live dial→K1 loop (item 1).
3. **Demo-robustness (non-gating):** BLE task is on Core-0 with audio; worst case is an *audible* dropout under heavy BLE traffic. Cheap mitigation = pin the app task to Core-1, but `ble_remoted_central.cpp:229` is **shared** with the interference-A/B probe — do NOT edit it globally; gate any Core-1 move behind a flag so the A/B ON-condition stays intact. Only pursue if the demo shows glitching.
4. **Commit placement:** landed on `lane/im73d-pdm-eval` with full commit gate (`pytest tests/` + `pio run -e k1_hardware`).
5. **Productionization bench-state note:** this flash **replaced** the bench K1's prior `k1_bench_im73d` productionization state. The IM73D Phase 1.1 device-proof (per `im73d122-productionization-handover-2026-07-03.md`) now needs a **reflash to the radio-free `k1_bench_im73d`** for a clean measurement run.

## Update — 2026-07-05: Core-0 BLE DRAM crash on noise-cal (SSA-2 risk materialized)

A **concurrent session** found that on this build the **first accepted noise-cal aborts on Core 0**: `save_config()`'s `LittleFS.open()` allocates a recursive mutex (a FreeRTOS queue — **internal RAM only**); with BLE pinned to Core 0 leaving internal DRAM tight, newlib calls `abort()` from **inside `fopen()`** (`locks.c: lock_init_generic`) — *before* `open()` returns, so the `if (!file)` guards can't catch it → hard reboot. This is exactly the **Core-0 BLE contention SSA-2 flagged, now materialized on-silicon** — as heap exhaustion, not audio jitter.

- The fix **landed as `1ac840a`** (`fix(im73d): guard LittleFS writes vs internal-RAM abort on cal-complete`, 2026-07-05) — an internal-RAM precondition guard in `persistence/bridge_fs.h` + `system/system.h`.
- **Fix deployed and device-proven (2026-07-05):** bench reflashed to `d32770d` (`1ac840a` + `:ble_stream` telemetry). Captain silence-go cal **ACCEPTED** with 0 abort/backtrace (K718 **unlinked**, `notify=0`). ⚠ **Crash-condition repro still owed:** original abort had K718 linked+streaming (`notify=32`); light-load cal would have passed pre-fix too. Guard makes writes fail-safe either way.
- Core-0 robustness remains load-bearing for investor demos under full BLE+WiFi load — see registry §2 top row.

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-07-04 | agent:claude-opus-4-8 | Created — `k1_bench_im73d_ble` demo build: composition, 4-SSA injection-point investigation, build/gate/flash/runtime evidence (BLE `linked=1`), port re-scramble correction, outstanding items. |
| 2026-07-05 | agent:claude-opus-4-8 | Recorded the Core-0 BLE DRAM crash on noise-cal (concurrent-session on-silicon finding); fix committed as `1ac840a` (`bridge_fs.h`/`system.h` internal-RAM guard). Deployed demo build (`1c14990`) predates it → rebuild+reflash owed. Vindicates SSA-2. |
| 2026-07-05 | agent:cursor | Bench reflashed to `d32770d`; cal-abort fix device-proven (K718 unlinked silence-go cal). Env commit landing; K718-linked crash-condition repro still outstanding. |
