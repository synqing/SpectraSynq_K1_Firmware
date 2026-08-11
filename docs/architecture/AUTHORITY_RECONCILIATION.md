---
abstract: "Authority reconciliation for the K1 VJ controller pivot from Deck-8-first BLE plan to Deck16 Tab5 BLE architecture revision K1_DECK16_TAB5_BLE_R1."
architecture_revision: "K1_DECK16_TAB5_BLE_R1"
date: "2026-08-06"
---

# K1 VJ Controller Authority Reconciliation

This file records which decisions from the old Deck-8 plan survive and which
are superseded by `K1_DECK16_TAB5_BLE_R1`.

| Old authority | New status | Implementation consequence |
|---|---|---|
| First surface is Deck-8 with one encoder row | Superseded | First meaningful integrated prototype is Deck16: Tab5 plus two Unit 8Encoder rows. Deck-8 is diagnostic/protocol mule only. |
| Existing 71-control BLE-MIDI map is canonical | Survives | Keep `docs/protocol/k1-ble-midi-map.json` and generated K1 decoder/facade path as command authority. |
| Zero K1-side changes for v1 | Superseded | Allow bounded K1 changes for identity, map/protocol negotiation, snapshots, confirmations, revisions, counters, and CC14 atomicity. |
| BLE only | Survives | BLE remains the only control transport. Same-connection state replication is allowed; WiFi SoftAP/WebSocket remains parked. |
| Name/service match is enough for the K1 central | Superseded | K1 must verify service, product identity, allowlisted `deck_id`, protocol version, and map/layout hashes. |
| Tab5 rejected because ESP32-P4 has no radio | Superseded | Tab5 can qualify through its internal ESP32-C6 via ESP-Hosted. If that fails, fallback radio moves to a dedicated ESP32-S3 while Tab5 remains HMI. |
| Second encoder row is later Deck-16 expansion | Superseded | Both rows exist from the first integrated prototype. Primary and secondary rows are never banked over each other. |
| Subjective instant latency is enough | Superseded | Acceptance uses latency distributions and counters: input-to-apply p95, p99, max, apply-to-confirmed-UI p95, AP cadence, heap stability, and hard zero counters. |
| Single 60-minute session promotes the lane | Superseded | Human VJ sessions happen after synthetic, recovery, RF, cold-boot, reconnect, and soak gates. |
| SMC-Mixer direct link comes before Deck16 | Superseded | SMC-Mixer is deferred behind Deck16 and requires its own provisioned identity. |
| IM69D on-device lane suspension while radio build is flashed | Survives | Registry and authority docs must state suspension/resume; no mic claims from radio builds. |
| Dual-K1 sync is out of scope | Survives | Do not reopen dual-sync work in this controller lane. |
| X-Touch Mini is parked | Survives | No USB-only control surface work in Deck16 v1. |

## Current Authority Chain

1. `docs/architecture/K1_DECK16_ARCHITECTURE_R1.md`
2. `docs/protocol/deck16-layout-v1.json`
3. `docs/protocol/k1-deck-identity-v1.md`
4. `docs/protocol/k1-deck-state-v1.md`
5. `docs/protocol/k1-ble-midi-map.json`

The superseded Deck-8 plan remains only as a pointer to this authority.
