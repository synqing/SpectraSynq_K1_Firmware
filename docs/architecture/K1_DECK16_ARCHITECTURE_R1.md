---
abstract: "K1 VJ wireless controller architecture revision K1_DECK16_TAB5_BLE_R1. Final surface is Tab5 plus two M5 Unit 8Encoder rows, BLE-only control using the existing K1 BLE-MIDI map, K1-authoritative state confirmation, internal Tab5 ESP32-C6 radio as primary path, and a dedicated ESP32-S3 radio as the fallback path."
architecture_revision: "K1_DECK16_TAB5_BLE_R1"
decision: "GO_WITH_GATED_IMPLEMENTATION"
supersedes: "docs/k1-vj-wireless-controller-plan-2026-08-06.md Deck-8-first plan"
status: "active architecture plan"
date: "2026-08-06"
---

# K1 Deck16 Tab5 BLE Architecture R1

## Purpose

This is the active architecture authority for the K1 VJ wireless controller
pivot. It supersedes the Deck-8-first plan. The first meaningful integrated
controller is the final intended surface: a Tab5 HMI with two M5 Unit
8Encoder modules, one dedicated primary row and one dedicated secondary row.

The surviving core of the old plan is the K1-side control vocabulary: the
existing 71-control BLE-MIDI map remains the command protocol. The rejected
parts are the screenless Deck-8 product path, "zero K1-side changes", name-only
peer acceptance, subjective latency acceptance, and WiFi SoftAP/WebSocket
revival as a consequence of using Tab5.

## Verified Inputs

- Current repo map authority is `docs/protocol/k1-ble-midi-map.json` with
  `control_count=71`, `registry_version=2026-06-09`, and
  `registry_md5=78fb9af986da36922fae33cb09de3b4b`.
- Current K1 BLE receiver code is central-side and non-shippable:
  `SPECTRASYNQ_K1_FIRMWARE/network/ble_remoted_central.cpp` scans, connects,
  subscribes, decodes BLE-MIDI, queues records, and applies them through
  `k1_control_apply()`.
- Current control facade implementation is
  `SPECTRASYNQ_K1_FIRMWARE/control/k1_control_facade.cpp`; the active symbol is
  `k1_control_apply`, not `sb_k1_control_apply`.
- Current bench radio demo env is `[env:k1_bench_im73d_ble]` and uses
  `-DK1_BLE_REMOTED`. The old plan's `-DSB_K1_BLE_REMOTED` spelling is stale.
- M5Stack's current Tab5 documentation lists ESP32-P4, an ESP32-C6 wireless
  module, a 5 inch 1280x720 display, HY2.0-4P expansion, INA226 on the
  internal I2C bus at `0x41`, and external HY2.0 pins on P4 `G53/G54`.
- M5Stack's current Unit 8Encoder documentation lists an 8-channel I2C encoder
  unit at factory address `0x41`; any second-unit `0x42` address is a
  provisioning/proof requirement, not a stock assumption.
- Espressif's ESP-Hosted v3.0.6 examples prove the general ESP32-P4 host plus
  ESP32-C6 coprocessor BLE/NimBLE path. The Tab5-specific C6 path remains a
  gate, not an assumed fact.

References:

- M5Stack Tab5: https://docs.m5stack.com/en/core/Tab5
- M5Stack Unit 8Encoder: https://docs.m5stack.com/en/unit/8Encoder
- ESP-Hosted v3.0.6 BLE/NimBLE example: https://components.espressif.com/components/espressif/esp_hosted/versions/3.0.6/examples/bluetooth/esp_hosted_nimble/bleprph_wifi_coex/mcu_host?language=
- ESP32-P4 plus ESP32-C6 hosted guide: https://github.com/espressif/esp-hosted-mcu/blob/main/docs/esp32_p4_function_ev_board.md

## Final Architecture

```text
Top row M5 Unit 8Encoder
  address 0x41, 8 encoders, primary controls
        |
        | external I2C, 100 kHz initial qualification, Tab5 EXT5V controlled
        v
Tab5 ESP32-P4
  display, touch, deck scheduler, state mirror, identity, protocol hashes,
  layout manifest, latency counters, input recovery
        |
        | ESP-Hosted over SDIO/VHCI
        v
Tab5 internal ESP32-C6
  BLE controller path, WiFi disabled for Deck16 qualification
        |
        | BLE-MIDI commands plus same-connection K1 state writes
        v
K1 ESP32-S3 BLE central
  identity gate, BLE-MIDI decode, queue, k1_control_apply, K1-authoritative
  state snapshot and confirmations
        ^
        |
Bottom row M5 Unit 8Encoder
  provisioned/proven second address, target 0x42, secondary controls
```

If the internal C6 path fails its gates, the HMI does not change. The fallback
is a dedicated ESP32-S3 BLE coprocessor attached to Tab5 over a framed UART
link with length, CRC, sequence, heartbeat, and watchdog recovery.

## Authority Decisions

- **Control transport:** BLE only. WiFi SoftAP/WebSocket remains parked.
- **Command protocol:** existing K1 BLE-MIDI map remains canonical for control
  writes.
- **State authority:** K1 is authoritative. Tab5 displays K1-confirmed state;
  local movement is pending until K1 confirms it.
- **Controller identity:** the K1 must require BLE-MIDI service, Deck16 product
  identity, provisioned `deck_id`, supported protocol version, and matching
  map/layout hashes. Advertised name is informational only.
- **Controller count:** one active controller for v1. The two encoder modules
  are one Deck16 peripheral surface behind Tab5. Multi-controller arbitration is
  out of scope.
- **HMI:** Tab5 is the final first surface, not a later upgrade. The 16 encoder
  cells must be visible at all times: top row primary, bottom row secondary.
- **Input:** encoder cumulative counters are authoritative. Read-and-clear
  registers are diagnostic only unless proven lossless under the recovery tests.
- **K1 firmware changes:** bounded changes are allowed for identity, map
  negotiation, K1 state snapshot/deltas, state revisions, CC14 atomicity, and
  recovery counters. Do not create a parallel K1 control facade.

## Implementation Slices

### K1 Firmware

- Add a gated Deck16 BLE env after the current baseline is re-proven; do not
  mutate the active IM69D mic lane while it is the authority for mic evaluation.
- Extend the existing BLE central path with Deck16 identity checks, protocol
  negotiation, map hash checks, and state-confirmation writes.
- Enforce CC14 atomicity before facade application: MSB-only applies nothing,
  malformed pairs increment `malformed_cc14`, and interleaved pairs are rejected.
- Add counters for state confirmations, stale revisions, map mismatch lockout,
  wrong-peer rejection, malformed CC14, and first-touch prevention.

### Tab5 P4

- Own input scanning, cumulative counter rebasing, acceleration curves,
  debouncing, scheduler coalescing, layout manifest, display rendering, pending
  state, confirmed state, diagnostics, latency probes, and recovery UI.
- Keep the scheduler idle when no controls move. First movement sends
  immediately; repeated movement coalesces to no more than 30 Hz per control.
- Use absolute targets derived from K1-confirmed state plus pending local delta.
  Do not replay unconfirmed movement after disconnect.

### Tab5 C6 Primary Radio

- Run the C6 as controller/radio path through ESP-Hosted. For Deck16
  qualification, WiFi must be disabled.
- Tab5-specific proof must cover boot determinism, HCI/SDIO recovery, C6 reset
  recovery, BLE reconnect, latency, and K1 workload coexistence.

### ESP32-S3 Fallback Radio

- If the C6 path fails repeatably, move only the radio role to a dedicated
  ESP32-S3. Preserve Tab5 as display/input/state owner and preserve the same
  BLE-MIDI and K1 state protocols.
- The P4-to-S3 link is a framed UART protocol with length, CRC, sequence,
  heartbeat, and watchdog reset semantics.

## Protocol Artefacts

- `docs/protocol/deck16-layout-v1.json` defines the first fixed 16-control
  layout against the existing BLE-MIDI map.
- `docs/protocol/k1-deck-state-v1.md` defines the same-connection K1 state
  replication contract.
- `docs/protocol/k1-deck-identity-v1.md` defines Deck16 identity and lockout.
- `docs/protocol/protocol-map-hashes.json` records the current map and layout
  hashes used by this architecture revision.

Evidence directories are created only when real captures exist. Empty evidence
trees are not proof.

## Execution Gates

1. **P0 - Current BLE baseline:** record current head and map hashes, create or
   verify the correct bench BLE env, ensure radio upload guard fail-closed,
   suspend IM69D on-device claims while the bench wears a radio build, and
   re-prove the current K718 BLE chain through notify, decoded, enqueued,
   apply_ok, and visible K1 config change.
2. **P1 - Tab5/C6 feasibility:** prove Tab5 unit revision, BSP/ESP-IDF/
   ESP-Hosted/C6 firmware pins, WiFi disabled, BLE-MIDI advertisement, one K1
   control write, one K1 state write, and C6 reset recovery.
3. **P2 - Dual 8Encoder input:** prove both units, second address provisioning,
   cumulative counters, debounce, acceleration, simultaneous movement, bus
   recovery, EXT5V power cycle recovery, and zero lost/duplicate detents.
4. **P3 - K1 state authority:** implement Deck16 identity, map negotiation,
   full snapshot, confirmed deltas, revisions, stale rejection, map mismatch
   lockout, and first-touch-jump prevention.
5. **P4 - UI:** render 16 persistent control cells plus global strip. Every cell
   shows parameter name, channel, confirmed value, pending state, push function,
   stale/disabled/mismatch status, and link health.
6. **P5 - Synthetic/recovery/RF:** run 16 controls at up to 30 updates/s/control
   for 30 minutes, cold boot campaigns, forced reconnects, C6 resets, encoder
   bus power cycles, wrong-peer campaign, RF campaign, full K1 workload, real
   audio, and 4-hour soak.
7. **P6 - Human VJ trial:** after P5, run at least three sessions of at least
   60 minutes covering normal, busy 2.4 GHz, and performance arrangement.
8. **P7 - Radio decision:** keep the internal C6 only if it passes boot,
   reconnect, HCI/SDIO recovery, latency, AP cadence, and 4-hour soak gates.
   Activate the S3 fallback on repeatable C6 path failures.

## Stop Rules

- No K1 flash, upload, serial write, or noise calibration without Captain
  approval and identity-first target proof.
- No mic SNR/timing claims from radio builds.
- No Deck16 promotion from compile success, demo success, or a single live
  session. Promotion requires the listed gates.
- No dual-K1 sync, X-Touch, SMC-Mixer, or WiFi/WebSocket revival inside Deck16
  v1.

## Immediate Next Mechanical Step

Run P0 only: re-prove the current K1 BLE baseline at the live repo head, fix the
bench BLE env/guard mismatch if present, and leave the IM69D lane explicitly
suspended on-device while the bench K1 wears a radio build.
