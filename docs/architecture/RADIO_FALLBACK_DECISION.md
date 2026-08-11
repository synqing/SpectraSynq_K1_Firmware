---
abstract: "Radio decision record for K1 Deck16 Tab5 BLE R1: qualify Tab5 internal ESP32-C6 over ESP-Hosted first, activate a dedicated ESP32-S3 BLE coprocessor only on measured C6 failure."
architecture_revision: "K1_DECK16_TAB5_BLE_R1"
date: "2026-08-06"
---

# Deck16 Radio Fallback Decision

## Decision

Use the Tab5 internal ESP32-C6 over ESP-Hosted as the primary Deck16 BLE radio
path. Keep a dedicated ESP32-S3 BLE coprocessor as the defined fallback. The
fallback changes only the radio implementation; Tab5 remains the HMI, input
owner, scheduler, state mirror, and diagnostics surface.

## Primary Path

- Tab5 ESP32-P4 runs the app, input scheduler, UI, state mirror, and NimBLE host.
- Tab5 internal ESP32-C6 provides the BLE controller path through ESP-Hosted
  over SDIO/VHCI.
- WiFi is disabled during Deck16 qualification.
- K1 remains BLE central and receives the existing BLE-MIDI command stream.
- K1 writes confirmed state to the Tab5-hosted Deck16 state characteristic.

## Fallback Path

- A dedicated ESP32-S3 becomes the BLE peripheral/radio coprocessor.
- Tab5 P4 talks to the S3 over framed UART with length, CRC, sequence,
  heartbeat, and watchdog semantics.
- The same Deck16 identity, BLE-MIDI command map, state-confirmation protocol,
  scheduler policy, UI, and acceptance gates remain in force.

## Keep The C6 Only If

- 100 controller cold boots and 50 forced reconnects complete without manual
  intervention.
- 20 C6 resets recover automatically and return to a K1-confirmed state.
- No repeatable HCI, SDIO, VHCI, or controller wedge occurs during the RF and
  soak campaigns.
- Input-to-apply latency meets p95, p99, and max gates while the K1 runs full
  visual/audio workload.
- AP cadence and heap stability stay inside the accepted envelope.
- The 4-hour soak finishes with zero WDT, panic, brownout, reboot, queue drop,
  decode error, malformed CC14, wrong peer, stale replay, first-touch jump, and
  state mismatch counters.

## Activate The S3 Fallback If

- The internal C6 path has repeatable boot nondeterminism.
- ESP-Hosted/SDIO/VHCI recovery cannot be made automatic.
- Latency or K1 coexistence fails under the RF or full-workload gates.
- C6 reset recovery needs manual intervention.
- WiFi cannot stay disabled or isolated in the Deck16 qualification build.

## Non-Negotiables

- Do not revive WiFi SoftAP/WebSocket as the Deck16 v1 control path.
- Do not remove K1 identity checks to make fallback easier.
- Do not allow the fallback radio to become state authority.
- Do not call C6 failure a Tab5 HMI failure; only the radio path changes.
