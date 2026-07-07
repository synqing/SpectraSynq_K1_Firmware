---
abstract: "OTA closeout handover (2026-07-07). BLE OTA P1 is DEVICE-PROVEN end-to-end (signed 951 KB image over BLE → RSA-3072 verify → ACCEPT → reboot) and committed at feat/im73d-ota-bench @ 03721bd (pushed). This session closes 4 residual items via a phased SSA swarm: (1) rollback leg (bench-brick-risk), (2) IDLE-not-ADVERTISING one-liner, (3) merge → product line, (4) D3 ship-gate memo (Captain decides). CRITICAL: hardware is a SINGLE serial resource — swarm the non-hardware prep, run ONE serialised device loop. Inherits solved walls: macOS stale-bond → fresh random BLE address; WRITE_NR → 15 ms pacing; the 'panic' was a serial-open USB reset, not a crash. READ before touching OTA."
---

# K1 OTA Closeout — Phased-Swarm Handover (2026-07-07)

> **TL;DR** — BLE OTA P1 works end-to-end on silicon and is committed (`feat/im73d-ota-bench @ 03721bd`, pushed). Four items remain to make OTA shippable. They fit ONE long session IF you swarm the non-hardware prep and run a SINGLE serialised device loop (one bench = one radio = no parallel hardware). Everything that beat me last session is already solved and committed — do not re-fight it.

## 1. State — what is DONE and PROVEN (do not re-litigate)
- **OTA engine**: whole-image SHA-256 + RSA-3072 PKCS#1 v1.5 verify (`k1_ota_end`) against the embedded pubkey; boot slot flips only on verify; fail-closed. Proven on silicon both K1s (`:ota_selftest good=PASS tamper=REJECT verify=PASS`).
- **BLE OTA P1** (`03721bd`): NimBLE peripheral (`network/k1_ota_ble_service.cpp`) + coordinator (`system/k1_ota_mode.{h,cpp}`, lock-free atomic `OtaUiState`, render-hook takeover, deferred reboot, `:ota_ble` verb, boot mark-valid) + Reactor renderer (`visual/k1_ota_reactor.cpp`, centre-origin red→amber→green status arc + white-hot core). GATT contract: `docs/protocol/k1-ble-ota-contract.yaml`.
- **Device-proven on bench `B489A500`** (env `k1_bench_im73d_ota`): full **951 KB signed image over BLE → PROGRESS 0→100% → VERIFYING → INSTALLING → ACCEPT → boot-slot flip → reboot**. REJECT path proven (unsigned/incomplete → refused, brick-safe). IM73D audio + heap (147 KB free) healthy. Flag-OFF `k1_hardware` byte-identical (651038 B).
- Branch lineage: `feat/im73d-ota-bench` (this work) ← the im73d lane. OTA signing engine also on `feat/n7-ota-signing` (`c34a0e9`, `cf6d8cc`, pushed). Product line = `lane/remoted-ble-midi-phase-f`.

## 2. The FOUR closeout items
1. **Rollback leg** (bench-brick-risk — the load-bearing anti-brick proof). Build a **signed-but-broken** image: a VALID signature (so `k1_ota_end` accepts + flips the slot) over an app that **panics/hangs in `setup()` BEFORE `k1_ota_mark_app_valid_after_boot()`** — cleanest via a `-DK1_OTA_ROLLBACK_TEST` build flag. OTA-push it → it boots → never marks valid → **bootloader reverts to last-good slot** → confirm recovery. Confirm `CONFIG_BOOTLOADER_APP_ROLLBACK_ENABLE=y` is inherited (it is, on the OTA lineage `sdkconfig.defaults`). **DoD:** device pushes a signed-broken image, auto-recovers to last-good, logged in `docs/hardware/device-build-registry.md`. **BENCH `B489A500` ONLY, on a CLEAN known-good slot.**
2. **`IDLE`-not-`ADVERTISING`** (one-liner + smoke). In `k1_ota_ble_service.cpp` the `:ota_ble` start publishes `OtaUiState::ADVERTISING`, which makes `k1_ota_mode_active()` true → the render hook takes the plate to Reactor the instant OTA is armed. Change it to publish **`IDLE`** (or make `k1_ota_mode_active()` return false for `ADVERTISING`); Reactor then engages only at `BEGIN`/`DOWNLOADING` (`handle_begin`). Music keeps playing until a real update. **DoD:** device smoke — music runs while advertising, Reactor on first byte.
3. **Merge → product line** (`lane/remoted-ble-midi-phase-f`), flag-OFF byte-identical. **Phase-0 SSA maps the divergence FIRST** (conflict surface = `serial_menu.h`, `platformio.ini`, the `.ino` render hook). Wireless files (`network/`) must stay OUT of the production base `build_src_filter` — put them in the OTA env filter only (`test_token_scrub_static` guards this; it bit me once). **DoD:** merged, gate green (648+ tests, flag-OFF k1_hardware byte-identical), committed.
4. **D3 ship-gate memo** (Captain decides — NOT an agent decision). Draft the decision on the 3 human STOPs: (a) OTA in v1 scope? (b) signing-key custody model? (c) distribution/version server? **DoD:** decision-ready memo handed to Captain; do NOT flip `SB_ENABLE_OTA` in a shipping build without his go.

## 3. Phased swarm (the strategy)
**Hardware is a SINGLE serial resource** (one bench K1, one BLE radio). Parallel SSAs must NEVER touch the device — they collide. So:
- **Phase 0 — Recon/lock** (parallel, no hw, ~5 SSAs): branch-divergence map (de-risks the merge — the biggest unknown); rollback mechanics + signed-broken-image design (`-DK1_OTA_ROLLBACK_TEST`); the IDLE fix; the D3 memo draft.
- **Phase 1 — Build/host-gate** (parallel, sandboxed, no hw): implement IDLE + rollback-test flag; build merged branch; adversarial verify + full suite + flag-OFF byte-identity per artefact.
- **Phase 2 — SERIAL hardware spine** (ORCHESTRATOR ONLY): (a) IDLE smoke; (b) rollback proof (brick-risk, clean slot); (c) accept/reject regression on the final build. Captain signs the broken image.
- **Phase 3 — Close** (parallel where possible): merge → product line, gate, commit; finalise D3 memo → Captain.

Realistic outcome: **items 1–3 CLOSE in-session; item 4 is prepared (memo), Captain closes on his timeline.**

## 4. Inherited solutions — DO NOT RE-FIGHT (all committed)
- **macOS connect failure was a stale CoreBluetooth bond** (`Code 14`), NOT a firmware crash. The `reset_reason=4` "panic" was a **serial-open USB reset** (`reset_reason=11`). **Fix already in the firmware:** the service advertises from a **fresh random BLE address** (`NimBLEDevice::setOwnAddrType(BLE_OWN_ADDR_RANDOM)` + `deleteAllBonds()` in `start()`), so any central sees a bondless peer. No Mac interaction needed. `blueutil --unpair` NO-OPS on this macOS (Sequoia) — don't rely on it.
- **WRITE_NR flow control**: bleak has no flow-control API; pace **~15 ms/chunk** (chunk = MTU-3 ≈ 480). Device absorbs ~34 KB/s → ~33 s for a 951 KB image. Faster pacing silently drops chunks → `REJECT size_mismatch`.
- **No-pairing posture**: `setSecurityAuth(false,false,false)` + `setSecurityIOCap(NO_INPUT_OUTPUT)` are in place (they are NO-OPS re-asserting NimBLE defaults — the fresh address is the real fix; keep them for explicitness).
- **Deferred reboot**: ACCEPT reboots via a FreeRTOS one-shot timer (not `delay()` on the host task) so the ACCEPT notify flushes first.

## 5. Guardrails (NON-NEGOTIABLE)
1. **Hardware is serial** — parallel SSAs analyse/build/verify; ONE orchestrator runs the device loop.
2. **Rollback / brick-risk → BENCH `B489A500` ONLY**, clean known-good slot; NEVER the main K1 `F887A500`.
3. **Identity by chip-ID, not port** — flash only `pio run -e <env> -t upload --upload-port <port>`; guard verifies MAC, aborts on mismatch. Ports drift (`1401`/`12401` seen); confirm via `pio device list`.
4. **Signing** — agents verify with the PUBLIC key. To sign, invoke `openssl dgst -sha256 -sign ~/.k1_secrets/k1_ota_signing_PRIVATE.pem` IN PLACE — never copy/log/commit the key. The `.sig` is safe.
5. **`SB_ENABLE_OTA` stays default-0**; flip is Captain's D3 call. Flag-OFF `k1_hardware` MUST stay byte-identical; `network/` wireless files stay OUT of the base filter.
6. **hardware-test-before-commit**; **contract-first** (update `k1-ble-ota-contract.yaml` before wire changes); **verify claims first-hand**.

## 6. Key paths / commands
- Worktree (recreate if pruned): `git -C /Users/spectrasynq/SpectraSynq_K1_Firmware worktree add /private/tmp/k1_im73d_ota feat/im73d-ota-bench`
- Build+flash (isolated dir): `cd /private/tmp/k1_im73d_ota && PLATFORMIO_BUILD_DIR=$PWD/.pio_isolated ~/.platformio/penv/bin/pio run -e k1_bench_im73d_ota -t upload --upload-port <bench port>`
- Bench `B489A500` (verify: `~/.platformio/penv/bin/pio device list`). Main `F887A500` — do NOT use for brick-risk.
- Sign: `openssl dgst -sha256 -sign ~/.k1_secrets/k1_ota_signing_PRIVATE.pem -out /private/tmp/ota_fw.sig <firmware.bin>` then verify vs `SPECTRASYNQ_K1_FIRMWARE/certs/k1_ota_signing_PUBLIC.pem`.
- BLE client (recreate from this doc if scratchpad pruned): `bleak` in `~/.platformio/penv`; scan `Lightwave-Update`; control char `3a058b4a-…` opcodes `BEGIN=0x01+u32 size`, `SIG=0x02+u16 off+frag`, `END=0x03`, `ABORT=0x04`; data char `6cc82419-…` WRITE_NR; status notify `PROGRESS=0x10+u8`, `VERIFYING=0x11`, `INSTALLING=0x12`, `ACCEPT=0x13`, `REJECT=0x14+u8 reason`.
- Residual latent (not blocking): NimBLE double-init seam only bites a combined `SB_ENABLE_OTA`+`SB_K1_BLE_REMOTED` env (absent here).

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-07-07 | agent:claude-opus-4-8 (CTO) | Created. OTA closeout phased-swarm handover: 4 items (rollback / IDLE / merge / D3), swarm phasing (parallel prep → serial hardware → close), inherited solved walls (macOS fresh-address, WRITE_NR 15 ms pacing, panic-was-USB-reset), guardrails, paths. Off BLE OTA P1 device-proven @ 03721bd. |
