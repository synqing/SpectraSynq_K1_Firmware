---
name: tab5-hosted-ble-debug
description: >-
  Tab5 P4 ESP-Hosted + NimBLE VHCI diagnostic ladder. Use when BLE_HS_ETIMEOUT_HCI,
  HCI RX missing, advertising fails, or before any C6 flash proposal on Deck16.
allowed-tools: Read, Grep, Glob, Bash
---

# Tab5 hosted BLE debug

**Canon:** `docs/architecture/TAB5_DECK16_SESSION_CANON_2026-08-07.md`  
**Proof pack:** `_scratch/deck16_tab5_k1_proof_20260807/`

Announce: "Using tab5-hosted-ble-debug against TAB5_DECK16_SESSION_CANON."

## Stop rules

- **No C6 flash/OTA** from timeout alone.
- **No** `flash_c6_official.sh` / TTL without Captain go.
- **K718 retired** — peer is bench K1 central, not Remoted dial.

## Ladder (execute in order)

### H0 — Wire contract (do this first)

1. Read `tab5_firmware/src/hosted_vhci_drv.c` — confirm **no** local `#define ESP_HCI_IF 3`.
2. Build `tab5_p4`; grep serial for:
   - `ABI ESP_SERIAL_IF=3 ESP_HCI_IF=4`
   - `esp_hosted_tx ACTUAL if_type=4`
   - `hci_rx_handler if_type=4` after HCI Reset
3. **PASS:** Command Complete `04 0E`, ADV, optional central connect.
4. **FAIL at H0:** fix IF enum / header packing before H1/H2/C6.

Reference: `_scratch/.../H0_WIRE_CONTRACT.md`

### H1 — Stock VHCI (Captain go)

Minimal Espressif `host_nimble_bleprph` VHCI on host **2.0.13**, Tab5 SDIO pins 12/13/11/10/9/8, rst 15.

### H2 — Host 1.4.0 A/B

Env `tab5_p4_hosted_14x` — compare transport class only. Known result: `transport_up(0)` — **not** a drop-in fix.

### C6 — last resort

Only after H0–H2 + explicit Captain authorisation.

## Symptom → action

| Serial pattern | Action |
|----------------|--------|
| `esp_hosted_tx(ESP_HCI_IF=3)` or `if_type=3` on HCI Reset | **H0 fail** — fix to IF=4 |
| `rc=0`, zero `hci_rx_handler` | H0 wire contract |
| `transport_up(0)` | Pins / early-init race — not HCI IF fix |
| `fwversion 1.4.1 (rc=0)` + HCI timeout | Version skew hypothesis only — **run H0** |
| ADV + `central connected` | Link layer OK — debug map TX / K1 apply |

## Link proof (after H0 PASS)

Tab5: `[ble-midi] tx CC … cc=1` + `cc=33` for `primary.photons`  
K1: `DIAL_STATUS linked=1`, `apply_ok` climbs, `CONFIG.PHOTONS` tracks.

**Never** brightness via CC7 — map says CC14 1/33.

## Key files

- `tab5_firmware/include/esp_hosted_interface.h`
- `tab5_firmware/src/hosted_vhci_drv.c`
- `tab5_firmware/src/ble_midi_transport.cpp`
- `docs/protocol/k1-ble-midi-map.json`
