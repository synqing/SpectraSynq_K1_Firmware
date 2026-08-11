---
abstract: "K1 Deck16 state replication protocol v1. K1 remains state authority; Tab5 displays confirmed K1 state and treats local movement as pending until confirmed."
protocol: "k1-deck-state-v1"
architecture_revision: "K1_DECK16_TAB5_BLE_R1"
date: "2026-08-06"
---

# K1 Deck State Protocol V1

## Scope

This protocol carries K1-confirmed controller state back to the Deck16 Tab5
surface. It is not a second command plane. Commands remain the existing
BLE-MIDI map. K1 remains the state authority.

## BLE Roles

- Tab5 Deck16 advertises as a BLE-MIDI peripheral and GATT server.
- K1 remains BLE central/client.
- Commands use the existing BLE-MIDI service/characteristic.
- K1 state replication uses an additional Tab5-hosted characteristic on the
  same BLE connection:
  - Service: `K1_DECK_STATE_SERVICE_UUID = 9f3e5c20-1c7a-46b0-8d43-6d66e10a6d16`
  - Characteristic: `K1_STATE_V1_RX_UUID = 9f3e5c21-1c7a-46b0-8d43-6d66e10a6d16`
  - Properties: write and write-without-response

## Connection Sequence

1. K1 connects only after Deck16 identity checks pass.
2. K1 reads Deck16 protocol, map hash, layout hash, and `deck_id`.
3. K1 writes `HELLO`.
4. K1 writes `SNAPSHOT_BEGIN`.
5. K1 writes one `STATE_ITEM` for every visible or layout-relevant control.
6. K1 writes `SNAPSHOT_END` with item count and CRC.
7. Tab5 enters `ARMED`.
8. First valid confirmation after a local command moves Tab5 to `LIVE`.

Tab5 must never show stale local sent values as confirmed. If the snapshot is
missing, fails CRC, has the wrong count, or has a map/layout mismatch, Tab5
stays disarmed and sends no controls.

## Packet Framing

All state writes are little-endian binary packets.

```text
packet {
  magic[4]        = "K1DS"
  version:u8      = 1
  flags:u8
  record_count:u8
  reserved:u8     = 0
  sequence:u16
  payload_len:u16
  payload_crc32:u32
  records[]
}

record {
  type:u8
  flags:u8
  revision:u32
  payload_len:u16
  payload[]
}
```

Record types:

| Type | Name | Direction | Purpose |
|---:|---|---|---|
| 1 | `HELLO` | K1 to Tab5 | K1 device identity, supported state protocol, BLE-MIDI map hash, layout hash, **session_generation** |
| 2 | `SNAPSHOT_BEGIN` | K1 to Tab5 | Starts an authoritative state snapshot |
| 3 | `STATE_ITEM` | K1 to Tab5 | One confirmed value keyed by BLE-MIDI map index |
| 4 | `SNAPSHOT_END` | K1 to Tab5 | Snapshot item count and CRC |
| 5 | `DELTA_BATCH` | K1 to Tab5 | Confirmed changes after command apply, clamp, reject, or local K1 change |
| 6 | `HEALTH` | K1 to Tab5 | Counters and link health |

## HELLO Payload

`HELLO` record payload (little-endian). Amended 2026-08-08 for R2
`session_generation` (wrap/reboot must invalidate prior Tab5 baseline):

```text
hello_v1 {
  protocol_min:u8
  protocol_max:u8
  flags:u16                 # reserved; 0 for v1
  session_generation:u32    # MUST change across K1 reboot / new link session
  ble_midi_registry_md5[16]
  deck16_layout_sha256[32]
  deck_id[16]               # K1's view of admitted peer (echo of identity)
  short_id:u32
}
```

Tab5 MUST disarm and discard any prior confirmed baseline when
`session_generation` differs from the last accepted HELLO. Matching map/layout
hashes alone is not sufficient across a generation change.


`STATE_ITEM` and `DELTA_BATCH` use map indices from
`docs/protocol/k1-ble-midi-map.json`. The map hash must match before any index
is accepted.

```text
state_value {
  map_index:u16
  value_type:u8       # 1=bool, 2=enum, 3=cc7, 4=cc14, 5=nrpn, 6=program
  status:u8           # 0=accepted, 1=clamped, 2=rejected, 3=unavailable
  value_i32:i32       # canonical integer value; cc14 uses 0..16383
}
```

## Revision Rules

- K1 increments `state_revision` after every accepted or rejected command that
  affects visible controller state.
- Tab5 ignores stale revisions.
- Tab5 records revision gaps and requests a fresh snapshot by disconnecting and
  waiting for K1 to reconnect.
- On disconnect, Tab5 discards pending deltas, marks values stale, and does not
  replay unconfirmed controls.
- Pending confirmations are keyed by `map_index` (u16). A delayed DELTA for an
  older request MUST NOT clear or confirm a newer pending value for the same
  `map_index` (R2 MUST).
- `session_generation` on HELLO invalidates prior baseline (see HELLO Payload).

## Required Counters

K1 and Tab5 diagnostics must expose:

- `state_confirmations`
- `state_revision_gaps`
- `stale_confirmations`
- `snapshot_crc_fail`
- `snapshot_count_fail`
- `map_mismatch`
- `layout_mismatch`
- `unconfirmed_discarded`
- `first_touch_prevented`
- `apply_ok`
- `apply_fail`
- `queue_drops`
- `decode_errors`
- `malformed_cc14`

## Acceptance

The protocol passes P3 only when cold connect, reconnect, K1-side value change,
clamp/reject, map mismatch, incomplete snapshot, stale revision, disconnect,
and wrong-peer scenarios all behave as specified here.
