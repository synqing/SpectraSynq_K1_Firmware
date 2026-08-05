---
abstract: "Memory-recall evidence for the dual-K1 sync lane (2026-07-08): no lane before 2026-07-07 discussed dual-K1 display sync or K1-to-K1 comms; BLE MIDI 71 lane reached live 268/268 apply proof on 2026-06-28 but the interference A/B is device-blocked; production firmware is radio-free with WiFi AP-only doctrine; EdgeMixer handover open, with an on-IM73D port branch (1ccebe9) already existing. Cites file:line and observation IDs."
---

# Memory Recall — Dual-K1 Sync Prior Art (2026-07-08)

Read-only recall pass across on-disk authority docs, artefact lanes, git branches/worktrees, and the claude-mem SQLite store (queried read-only, single terms: `sync`, `dual`, `MIDI`, `BLE`, `widen`, `ESP-NOW`, `pairing`). Default-refute stance; every claim below carries a citation.

## (a) Has any prior session/lane discussed dual-K1 sync or K1-to-K1 comms?

**No lane before 2026-07-07 discussed dual-K1 display sync or any K1-to-K1 link.** Every claude-mem hit for `sync`+`dual`+`widen` in this project dated 2026-07-07 (obs #76107, #76108, #76109, #76114, #76118, #76125) belongs to THIS lane's own opening session, not prior art. Their content, for continuity:

- **Concept origin (obs #76108):** Captain requested a deep investigation/planning session — two K1s online enter "sync" mode, combined 160+160 = 320 LEDs behave as one display, device 1 = left half, device 2 = right half; the centre-origin mandate per device transforms into left-anchor/right-anchor roles.
- **Mandate (obs #76107, #76114):** feasibility study first, "understand first, design second"; BLE MIDI is the *candidate* transport, not a decision. Discovery/pairing/handshake/state-sync/partitioning all identified as open architectural questions.
- **Constraint framing (obs #76109):** centre-origin addressing is symmetric around the 160-LED midpoint; sync needs a coordinate-space transform (left K1 seam at its rightmost LED, right K1 seam at its leftmost); open question whether BLE MIDI bandwidth/latency suffices or a dedicated BLE GATT channel is preferable.
- **Lane scaffolding (obs #76118, #76125):** this artefact directory, 5-phase plan, 8/9-SSA understand fan-out; non-negotiables = no Core-0 blocking/mutex, <50 ms audio-to-LED, imperceptible seam jitter, no device writes during research. Clarifying questions (transport scope, audio truth, pairing UX) were issued to Captain — **no recorded Captain answers yet** (`artifacts/k1_dual_sync_eval_2026-07-08/progress.md`).

**Related multi-device prior art that DOES exist (none is display sync):**

1. **K718 Remoted dial → K1 over BLE MIDI** (control-plane ingress, K1 = NimBLE central, K718 = peripheral) — see (b). This is the only proven wireless K1 control link over BLE.
2. **Tab5 → K1 over WiFi WebSocket** — K1 runs as WiFi AP, Tab5 joins as control client, `k1.*` protocol v2 (`docs/spec-index.md:48-49`; `SPECTRASYNQ_K1_FIRMWARE/network/sb_k1_wireless.cpp`, 30.4 KB). Device integration + eyes-on still open per the lane row.
3. **Paired two-K1 measurement harnesses** — both K1s captured simultaneously over USB serial for A/B evidence (`_scratch/im73d_bringup/snappiness/dual_ap_capture.py`, `progress.md:74-79`; paired snappiness manifests throughout `progress.md`). Serial-only; the devices never talk to each other.
4. **K1 BLE OTA lanes** (K1 = BLE *peripheral*): branches `feat/n7-ota-receiver`, `feat/n7-ota-signing`, `feat/im73d-ota-bench` with worktrees at `/private/tmp/k1_im73d_ota`, `/private/tmp/k1_ota_sign`, `~/SpectraSynq_K1_Firmware_n7` (`git worktree list`, 2026-07-08). Obs #75868/#75878 (2026-07-07, project Lightwave-Ledstrip): SMP stale-bond panic fixed via `NimBLEDevice::deleteAllBonds()` + random own-address in `k1_ota_ble_service.cpp`; WRITE_NR pacing and USB-reset false-panic findings recorded. Untracked `k1_ota_signing_PUBLIC.pem` at repo root corroborates. **Prior art relevance: the K1 has run as both BLE central (Remoted) and BLE peripheral (OTA) — but never central+peripheral to another K1.**
5. **ESP-NOW: no implementation exists.** Hits are only the current lane's SSA scope (obs #76125) and a 2026-06-26 licence-triage note (obs #70401). Obs #70747 (2026-06-26) confirms K1 firmware had zero BLE references before the Remoted lane.
6. **LED-topology precedent for reshaping the surface:** obs #75316/#75308 (2026-07-05, `k1_custom` wall-unit lane): primary K1 output is already single-channel WS2812B (the `LED_NEOPIXEL_X2` split mode is dead code for the current config), and a single-channel-225 variant needed only 3 flag-gated edits — evidence the LED surface shape is malleable via compile-time config.

## (b) BLE MIDI 71 lane — current state + Captain decisions

Two phases, then parked:

**Phase F/G (2026-06-28, `artifacts/ble_midi_71_20260628/`):** status `PARTIAL_COMPLETE_DEVICE_BLOCKED` (`phase_g_device_proof/20260628_1529/final_manifest.json` `status` field). Branch `lane/remoted-ble-midi-phase-f` (impl base `476b4ec`); knob repo `JC3636K518CN_knob_EN-bleremote` branch `feat/ble-remoted-71control-knob`.
- **Contract:** 71 controls, generated header `SPECTRASYNQ_K1_FIRMWARE/network/k1_ble_midi_map.h` from `docs/protocol/k1-ble-midi-map.json`, K1/knob JSON byte-match true (README.md:7, final_manifest `contract`).
- **All host gates PASS** incl. production radio-isolation (`scripts/ble_midi/guard_k1_radio_isolation.py`; `logs/k1_radio_isolation_guard.log` exit 0).
- **Live device proof PASS:** 71-control sweep/stress on the *main* K1 (`F887A500`, flashed `k1_ble_remoted_probe`): knob sent 268 items, K1 counters `linked=1 notify=268 decoded=268 enqueued=268 apply_ok=268 apply_fail=0 queue_drops=0 decode_errors=0`; 16 protected calibration items `protected_skip` by design (`ab_ble_active_summary.json`).
- **Blocked half:** BLE interference A/B `DEVICE_BLOCKED` — the K718 enumerated but stopped booting/responding; the AB summary explicitly limits its claim to "scalar AP cadence comparison only; no causal RF attribution".

**Demo-build phase (2026-07-04/05, `docs/hardware/im73d-ble-midi-demo-build-2026-07-04.md`):** env `k1_bench_im73d_ble` = `k1_bench_im73d` + 3 BLE deltas (`network/ble_remoted_central.cpp`, `network/k1_ble_midi_decoder.cpp`, `-DSB_K1_BLE_REMOTED`, NimBLE-Arduino ^2.5.0); RAM 38.0% / Flash 13.9%; flashed to bench `B489A500`, `linked=1` to the live K718 "SpectraSynq Remoted" peripheral, `notify=0` → **dial-turn control proof still pending** (doc §Outstanding 1). The SSA-2 Core-0 risk **materialised on-silicon 2026-07-05**: first accepted noise-cal aborted inside `fopen()` (LittleFS mutex needs internal DRAM; BLE on Core 0 left DRAM tight); fixed by `1ac840a` internal-RAM guard, device-proven under light load; **K718-linked crash repro still owed** (doc §Update 2026-07-05).

**Current deployed state:** the bench was restored radio-free (`k1_bench_im73d @ 27d0ccf`, 2026-07-08 handover); the BLE demo build is on no device. Spec-index lane row: "Parallel deliverable, not current bench proof target… Reflash `k1_bench_im73d_ble` only when BLE demo work resumes" (`docs/spec-index.md:38`).

**Captain decisions on this lane:** (i) demo and measurement are **separate workstreams** — never measure mic SNR on the radio build (doc §What this is; project memory `k1-im73d-ble-demo-build`); (ii) "bench K1 firmware" = `k1_bench_im73d_ble` ALWAYS when Captain says so (Captain 2026-07-06, project memory); (iii) `ble_remoted_central.cpp:229` Core-pinning is shared with the interference A/B — any Core-1 move must be flag-gated (doc §Outstanding 3).

## (c) Captain decisions constraining transports / WiFi topology / BLE usage

1. **Production firmware is radio-free.** `k1_hardware` passes a radio-isolation guard on every gate run (`scripts/ble_midi/guard_k1_radio_isolation.py`); every BLE env is non-shippable/demo ("NON-SHIPPABLE (radio present)" — demo-build doc abstract). Developer Instrumentation Boundary (`.claude/CLAUDE.md`) keeps probe/harness code out of production. **Any shipped dual-K1 transport implies revisiting the radio-free production stance — a Captain-level decision.**
2. **WiFi topology:** "K1 runs WiFi AP-only; the Tab5 joins the K1 AP as the control client… Do not add K1 STA fallback" (root `CLAUDE.md` §Platform-Native Production Patterns 5, corrected 2026-06-15). Note the global memory-freeze record says the old "AP-only compile lock" claim is false and dual-mode shipped 2026-05-17 (`ab8ef0ae`) — that commit is not in this repo's history; the repo doc is authoritative here. Flagged as an open question.
3. **Core-0 sanctity:** no mutex/blocking/malloc on the audio core (root `CLAUDE.md`); NimBLE host and the BLE app task both default to Core 0 (`ble_remoted_central.cpp:229`, `nimconfig.h:213` per demo doc SSA-2) and the contention risk is *proven*, not theoretical (2026-07-05 DRAM abort).
4. **Latency/perception doctrine:** <50 ms audio-to-LED; architecture subordinate to perceptual impact (`/sensorybridge-doctrine` gate before AP/VP changes).
5. **Device/env discipline:** identity = chip ID/USB MAC, never port; guard registration mandatory (an unregistered env "fails open — no GPIO protection", demo doc); the dirty `k1_upload_guard.py` edit currently **blocks `k1_prod_im73d` uploads** because no 6/7-wired IM73D unit exists yet (2026-07-08 handover §Current Worktree Ledger) — any dual-unit flashing plan must account for it.
6. **IM73D decision closed:** IM73D122 IS the production mic, pins `clk13/din12/LR14`, never re-open (Captain 2026-07-03, project memory); DSR_16S rejected, `DSR_8S` default (`docs/spec-index.md:7`).
7. **Cal silence gate never waived; serial typed commands need `:` prefix** (project memory; handover §Non-Negotiable Safety Rules).

## (d) EdgeMixer context handover status

`docs/handover/2026-07-08-im73d-bench-restore-and-edgemixer-context-handover.md`:

- **Recovery closed:** bench unit (`B4:3A:45:A5:89:B4` / `B489A500`, IM73D122, LEDs GPIO 4/5) restored to `k1_bench_im73d @ 27d0ccf`; 22 s readback clean (0 bad markers, no WDT/backtrace).
- **Root cause of the blackout:** the EdgeMixer worktree lacked the IM73D env, so a clean `k1_bench_reference` flash used the wrong build family for the physical unit (handover §Why The LED Blackout Happened).
- **EdgeMixer worktree:** `/private/tmp/k1_edgemixer_colour_port`, branch `feat/edgemixer-colour-port @ 329b371` ("stabilise live control firmware"), with an **uncommitted** `.ino` edit changing the task-WDT idle-core mask `0x1u → 0x0u` — not validated, must be red/green tested. Validated before the map confusion: EdgeMixer keys/typed controls responded on serial; N2c loop-tail `vTaskDelay(1)` correction has a static regression test.
- **Open items (handover):** commit-or-revert the guard edit; rebase/port EdgeMixer onto `lane/im73d-pdm-eval` or abandon; never flash `k1_bench_reference` as an IM73D substitute; no loud-audio/cal tests without a Captain window.
- **Advancement the handover does not record:** branch `feat/edgemixer-on-im73d` already exists at `1ccebe9` ("live keystroke control onto IM73D122 bench base", on top of `d0f532d` colour-port matrix, based on `27d0ccf`), worktree `/private/tmp/k1_edgemixer_on_im73d` (`git worktree list`). The port the handover asks for has been started; its validation state is unverified.
- **Interaction with dual-K1 sync:** EdgeMixer is the dual-channel (primary + secondary edge) blending layer (`director/sb_edgemixer_lite.*`, root `CLAUDE.md` project structure). Each K1 drives **two** 160-LED channels, so "one widened surface" must be defined per channel: the widened plane is 160+160 across units on a given channel, while each unit still composes primary vs secondary locally. Any seam/partition model must compose with EdgeMixer semantics.

## Numbers

| Quantity | Value | Citation |
|---|---|---|
| Primary LEDs per K1 | 160 (`LED_STRIP_MODE 3` → `LED_COUNT_VALUE 160`) | `system/config_types.h:124,139` |
| Secondary LEDs per K1 | 160 | `system/globals.h:825` |
| `NATIVE_RESOLUTION` (centre-origin canvas) | 160; mirror anchor at 80; `NUM_FREQS = 80` | `system/constants.h:107-109` |
| Widened virtual surface (per channel) | 320 = 160 + 160 — brief's numbers VERIFIED | derived from above |
| BLE MIDI contract size | 71 controls | `ble_midi_71` final_manifest `contract.control_count` |
| Live BLE control proof | 268 sent / 268 decoded / 268 apply_ok / 0 drops / 0 errors | `ab_ble_active_summary.json` |
| BLE demo build cost | RAM 38.0% / Flash 13.9%, firmware ≈ 912 KB | demo-build doc §Evidence |
| Audio pipeline | 133 Hz frames, 12.8 kHz, 96-sample chunks; <50 ms budget; 100 FPS render | root `CLAUDE.md` §Core Timing |

## Risks

- The BLE interference A/B (radio load vs audio timing) is **unresolved** — the single most load-bearing unknown for any BLE-based sync transport (final_manifest `ble_interference_ab.status=DEVICE_BLOCKED`).
- Core-0 BLE contention has already crashed a device once (DRAM abort on cal, 2026-07-05); a sustained sync stream is heavier than dial turns.
- Production is radio-free by guard; shipping sync means a Captain decision on the radio stance.
- WiFi AP-only vs dual-mode canon tension (repo doc vs global CANONICAL_DECISIONS) unresolved for transport planning.
- claude-mem worker was not queried via MCP (SQLite read-only fallback used per brief); FTS single-term queries only — compound-topic misses possible.

## Open questions

1. Captain's answers to the lane's clarifying questions (transport scope, audio truth — one master's AudioSemanticState vs per-device audio, pairing UX) are not yet on disk.
2. Is the existing K1-central NimBLE stack usable K1-to-K1 (one K1 advertising as a Remoted-like peripheral), or is a second protocol surface needed?
3. Which WiFi stance is current product truth for a K1-to-K1 link: repo AP-only doctrine, or the 2026-05-17 dual-mode decision recorded in the global canon (different repo lineage)?
4. Validation state of `feat/edgemixer-on-im73d @ 1ccebe9` — ported but unproven?
5. Does "widened display" apply to both channels (primary and secondary) or primary only? EdgeMixer semantics make this a real design fork.

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-07-08 | agent:claude-code (SSA memory-recall) | Created — prior-art recall across on-disk docs, artefact lanes, git worktrees, and claude-mem SQLite (read-only) for the dual-K1 sync lane. |
