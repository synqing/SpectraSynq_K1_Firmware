---
abstract: "Superseded K1 VJ wireless controller plan. The Deck-8-first approach is replaced by K1_DECK16_TAB5_BLE_R1: Tab5 plus two M5 Unit 8Encoder rows, BLE-only command transport, K1-authoritative state, and gated C6/S3 radio decision."
status: "superseded"
superseded_by: "docs/architecture/K1_DECK16_ARCHITECTURE_R1.md"
date: "2026-08-06"
---

# K1 VJ Wireless Controller Plan - Superseded

This file is intentionally retained at the original plan path because earlier
notes and prompts referenced it directly. It is no longer the implementation
authority.

Active authority:

- `docs/architecture/K1_DECK16_ARCHITECTURE_R1.md`
- `docs/architecture/AUTHORITY_RECONCILIATION.md`
- `docs/architecture/RADIO_FALLBACK_DECISION.md`
- `docs/protocol/deck16-layout-v1.json`
- `docs/protocol/k1-deck-identity-v1.md`
- `docs/protocol/k1-deck-state-v1.md`
- `docs/protocol/protocol-map-hashes.json`

## Superseded Decisions

- Deck-8 is not the first product path.
- Zero K1-side changes is no longer a constraint.
- Name/service-only BLE identity is rejected.
- Tab5 is not deferred behind Deck-8 or SMC-Mixer.
- WiFi SoftAP/WebSocket remains parked despite Tab5 being the HMI.
- Subjective latency and one-session reliability are not enough for promotion.

## Current Decision

Proceed with `K1_DECK16_TAB5_BLE_R1` under gated implementation:

- Final control surface: Tab5 plus two M5 Unit 8Encoder modules.
- Primary row: 8 dedicated encoders on Unit 8Encoder factory address `0x41`.
- Secondary row: 8 dedicated encoders on a provisioned/proven second address,
  target `0x42`.
- Final HMI: Tab5 5 inch display.
- Primary radio: Tab5 internal ESP32-C6 via ESP-Hosted, WiFi disabled during
  Deck16 qualification.
- Fallback radio: dedicated ESP32-S3 BLE coprocessor over framed UART.
- Command protocol: existing K1 71-control BLE-MIDI map.
- State authority: K1-confirmed state only.
- Multi-controller arbitration: out of scope for v1.

## Immediate Next Step

Run only P0 from the active architecture: re-prove the current K1 BLE baseline
at live repo head, fix the bench BLE env/guard mismatch if present, and leave
the IM69D lane explicitly suspended on-device while the bench K1 wears a radio
build.
