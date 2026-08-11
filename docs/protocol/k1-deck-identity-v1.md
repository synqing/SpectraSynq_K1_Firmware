---
abstract: "Deck16 identity protocol v1 for the K1 VJ wireless controller. K1 accepts a controller only after service, product identity, deck_id, protocol version, and map/layout hashes match."
protocol: "k1-deck-identity-v1"
architecture_revision: "K1_DECK16_TAB5_BLE_R1"
date: "2026-08-06"
---

# K1 Deck Identity Protocol V1

## Purpose

BLE service UUID or advertised name alone is not identity. K1 must reject the
wrong controller before accepting any Deck16 command.

## BLE Roles

- Deck16 Tab5 is the BLE-MIDI peripheral/server.
- K1 is the central/client.
- Advertised name format is `K1-DECK16-<short_id>`, but the name is only a
  human hint.

## Identity Surface

Deck16 exposes a read-only identity characteristic:

- Service: `K1_DECK_IDENTITY_SERVICE_UUID = 9f3e5c10-1c7a-46b0-8d43-6d66e10a6d16`
- Characteristic: `K1_DECK_IDENTITY_V1_UUID = 9f3e5c11-1c7a-46b0-8d43-6d66e10a6d16`

Payload:

```text
identity_v1 {
  magic[6]              = "K1D16\0"
  version:u8            = 1
  product_id:u16        = 0xD016
  protocol_min:u8       = 1
  protocol_max:u8       = 1
  deck_id[16]           # provisioned unique id
  short_id:u32          # display/log shorthand
  ble_midi_registry_md5[16]
  deck16_layout_sha256[32]
  flags:u32
  payload_crc32:u32
}
```

`deck_id` must be provisioned per physical controller. `short_id` is derived
from `deck_id` for logs and advertised-name readability.

## K1 Acceptance Rules

K1 accepts a Deck16 controller only when all checks pass:

- BLE-MIDI service UUID is present.
- Deck identity characteristic is present and readable.
- `magic`, `version`, and `product_id` match this document.
- `deck_id` is allowlisted for the target K1.
- Protocol range overlaps K1 support.
- `ble_midi_registry_md5` matches the generated K1 BLE-MIDI map.
- `deck16_layout_sha256` matches the layout version K1 expects.
- No other controller is already active.

If any check fails, K1 disconnects or ignores notifications from that peer,
increments the relevant wrong-peer/mismatch counter, and applies no command.

## Active Controller Rule

`ACTIVE_CONTROLLER_COUNT=1` for v1. Deck16 counts as one controller even though
it contains two encoder modules. Simultaneous K718 plus Deck16 is a negative
test case, not an accepted operating mode.

## Bonding

Bonding may be added later, but it is not a replacement for this identity
surface. K1 must still check product identity, allowlisted `deck_id`, protocol,
and hashes after reconnect.
