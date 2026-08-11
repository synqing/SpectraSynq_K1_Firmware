---
abstract: "Deck16 Tab5 session canon — HCI wire contract (ESP_HCI_IF=4), BLE diagnostic ladder, UI firmware-truth rules, protocol TX map, failure catalogue. Authority for agents before Tab5 flash/BLE/UI work."
date: 2026-08-07
architecture: K1_DECK16_TAB5_BLE_R1
status: LINK_PASS_HCI_FIXED
proof_pack: _scratch/deck16_tab5_k1_proof_20260807/
---

# Tab5 Deck16 Session Canon — 2026-08-07

**Load before:** Tab5 P4 flash, ESP-Hosted HCI debug, Deck16 operator UI edits, BLE-MIDI TX changes, or any claim that `BLE_HS_ETIMEOUT_HCI` ⇒ C6 reflash.

**Product truth:** Deck16 = **M5 Tab5 P4** (peripheral / GATT server) + **bench K1** (NimBLE central). **K718 Remoted dial is retired** for this lane — see [`docs/architecture/K1_DECK16_ARCHITECTURE_R1.md`](K1_DECK16_ARCHITECTURE_R1.md).

---

## Map vs territory

| Map (wrong) | Territory (right) | Evidence |
|-------------|-------------------|----------|
| `BLE_HS_ETIMEOUT_HCI` ⇒ **HARDWARE_BLOCKED** / must **flash C6 first** | Root cause was **host VHCI routing**: HCI Reset on **IF=3 (SERIAL)** not **IF=4 (HCI)** | [`H0_WIRE_CONTRACT.md`](../../_scratch/deck16_tab5_k1_proof_20260807/H0_WIRE_CONTRACT.md) — `hosted_vhci_drv.c` had `#define ESP_HCI_IF 3`; official 2.0.13 enum: `ESP_SERIAL_IF=3`, `ESP_HCI_IF=4` |
| Host **2.0.13** / C6 **1.4.1** skew ⇒ automatic C6 OTA/TTL flash | Skew was a **hypothesis**; **H0 IF fix** restored HCI RX + ADV + central connect on unchanged C6 1.4.1 | [`H0_WIRE_CONTRACT.md`](../../_scratch/deck16_tab5_k1_proof_20260807/H0_WIRE_CONTRACT.md) §6–8; [`LINK_PROOF.md`](../../_scratch/deck16_tab5_k1_proof_20260807/LINK_PROOF.md) |
| `transport_up(0)` ⇒ wrong pins (fixed earlier) | Pin map **PASS**; timeout class was **post-TX zero RX**, not SDIO dead | [`HCI_PATH_DIAGNOSIS.md`](../../_scratch/deck16_tab5_k1_proof_20260807/HCI_PATH_DIAGNOSIS.md) §4–6 |
| Drop host to M5 **1.4.0** fixes HCI | **1.4.0 A/B failed worse** — `transport_up(0)`, crash loop; does **not** prove 2.0.13 was the HCI bug | [`HOST_14x_AB.md`](../../_scratch/deck16_tab5_k1_proof_20260807/HOST_14x_AB.md) |
| Frame success as **K718 Remoted dial** pairing | Tab5 advertises `K1 Tab5`; K1 matches **Apple BLE-MIDI UUID** OR name; peer is bench `B489A500` | [`LINK_PROOF.md`](../../_scratch/deck16_tab5_k1_proof_20260807/LINK_PROOF.md) |

**Binding flags (current):**

```
DIRECT_C6_SERIAL_FLASH  = BLOCKED (P4 USB-C ≠ C6 ROM)
EXTERNAL_FLASH_REQUIRED = NOT PROVEN
BLE_ROOT_CAUSE          = ESTABLISHED (IF 3→4 on host VHCI)
LINK_TAB5_BENCH_K1      = PASS (photons control)
```

---

## Failure catalogue (symptom → wrong conclusion → falsifier → rule)

| # | Symptom | Wrong conclusion | Falsifier | Rule |
|---|---------|------------------|-----------|------|
| 1 | `BLE_HS_ETIMEOUT_HCI` / `ogf=0x03 ocf=0x0003` | Flash C6 / hardware dead | `esp_hosted_tx rc=0` but **zero** `hci_rx_handler`; log showed `ESP_HCI_IF=3` not 4 | Run **H0** wire contract before any C6 write |
| 2 | `esp_hosted_get_coprocessor_fwversion` → 1.4.1 | Must align C6 to host 2.0.13 | After IF=4 fix: **same C6 1.4.1**, HCI Command Complete + ADV + link | Version skew ≠ flash mandate ([#212](https://github.com/espressif/esp-hosted-mcu/issues/212)) |
| 3 | `transport_up(0)` on 1.4.0 host A/B | 2.0.13 integration broken | Restore 2.0.13: SDIO ready + fwversion RPC in &lt;3 s | Host downgrade is **not** a drop-in fix |
| 4 | Tab5 TX logged, K1 `CONFIG` unchanged | BLE broken | `notify/decoded/enqueued/apply_ok` climb; `CONFIG.PHOTONS` tracks Tab5 `b=` | Prove **K1 apply path**, not Tab5 send log alone |
| 5 | Invented UI palette/mode names | Cosmetic only | `MODE_PALETTE_AUDIT.md`: **32/33 modes**, **43/44 palettes** wrong vs firmware | Regen from `deck_ui_assets.py`; never hand-curate names |
| 6 | Brightness via CC7 | “CC7 is volume” | Map: `primary.photons` = **CC14 MSB/LSB 1/33**; CC7 MSB on ch0 is `incandescent_filter` territory | **CC7 danger** — never TX brightness as CC7 |
| 7 | `linked=0` on K1 | Wrong peripheral / need K718 | Tab5 `connected=yes` + K1 `linked=1` simultaneous; UUID `03B80E5A-…` match | **K718 retired** — scan for Tab5 / service UUID |
| 8 | INIT capability bitmap absent | BT not in C6 image | HCI events on `if_type=4` + GATT notify after IF fix | Capability print optional; **HCI RX** is the gate |

---

## BLE diagnostic ladder (order is load-bearing)

```
H0  Wire contract (IF enum + HCI Reset packing on host 2.0.13)
      ↓ PASS required
H1  Stock/minimal host_nimble_bleprph VHCI on 2.0.13 + live C1.4.1  [Captain go]
      ↓ if still failing
H2  Host 1.4.0 A/B (tab5_p4_hosted_14x) — compare transport class only
      ↓ only after H0–H2 exhausted + explicit Captain go
C6  External flash / OTA / TTL  — NOT from timeout alone
```

### H0 — ESP-Hosted 2.0.13 wire contract

**Artefacts:** [`H0_WIRE_CONTRACT.md`](../../_scratch/deck16_tab5_k1_proof_20260807/H0_WIRE_CONTRACT.md), `tab5_serial_h0_wire.log`, `h0_serial_excerpts.txt`

**Pass criteria:**

- `_Static_assert(ESP_HCI_IF == 4)` + runtime `ABI ESP_HCI_IF=4`
- HCI Reset: `if_type=4`, `hci_pkt_type=0x01`, payload `03 0C 00`
- `hci_rx_handler if_type=4` → Command Complete `04 0E …`
- NimBLE ADV + `[ble-midi] central connected`

**Code anchors:** `tab5_firmware/include/esp_hosted_interface.h`, `tab5_firmware/src/hosted_vhci_drv.c`

### H1 — Stock VHCI reference

Not executed 2026-08-07. Use Espressif minimal NimBLE host-only VHCI on **2.0.13** + Tab5 SDIO pins before blaming application layer.

### H2 — Host 1.4.0 A/B

**Artefacts:** [`HOST_14x_AB.md`](../../_scratch/deck16_tab5_k1_proof_20260807/HOST_14x_AB.md), `serial_hosted_14x_ab.log`

**Result:** BLE never reached HCI; **worse** than 2.0.13 baseline. `EXTERNAL_FLASH_REQUIRED` unchanged.

### C6 — last resort

`DIRECT_C6_SERIAL_FLASH = BLOCKED`. In-band OTA API exists on 2.0.13 but **unproven** as HCI cure ([#212](https://github.com/espressif/esp-hosted-mcu/issues/212)). No C6 flash in this session.

---

## UI rules (operator MAIN)

| Rule | Implementation | Proof |
|------|----------------|-------|
| **Firmware-truth names** | `python3 tab5_firmware/tools/deck_ui_assets.py` → `deck_names.h`, `deck_palette_stops.h` from `Palettes.h` + `system.h` `set_mode_name()` | [`MODE_PALETTE_AUDIT.md`](../../_scratch/deck16_tab5_k1_proof_20260807/MODE_PALETTE_AUDIT.md), [`P4_UI_RECEIPT.md`](../../_scratch/deck16_tab5_k1_proof_20260807/P4_UI_RECEIPT.md) |
| **Fixed `%02u` index column** | Palette/mode number width locked to glyph width of `"40"`; name clips in remainder | `MODE_PALETTE_AUDIT.md` §Summary |
| **HTML / audit before firmware thrash** | Run asset regen + `MODE_PALETTE_AUDIT.md` diff; Captain pixel review before claiming UI fixed | No invented `EMBERWASH` / `SPECTRUM`-as-mode-0 |
| **Spectrum bar = same index as name** | `deck_palette_strip(same_index)` | `P4_UI_RECEIPT.md` §Captain FAIL #3 |
| **Skip disabled modes in step** | Display **real firmware ordinal** + name | `config_types.h` `light_mode_is_enabled()` |

**Do not** edit `deck_names.h` by hand — always regen.

### Amendment — 2026-08-07 afternoon (Captain override)

**Countach Display Register.** Countach Bold is for **hero numerals only** — the mode/palette
`%02u` index glyphs. **All words remain Berkeley Mono:** mode names, palette names, labels, keys,
brand text. **Do not apply Countach to mode/palette name strings.** Trial Countach remains
**bench-only** (no production flash on that basis).

### Amendment — 2026-08-07 evening (native sim)

**UI craft iterates on `native_sdl` first; flash only after sim proof.**

- In-repo env: `tab5_firmware` `[env:native_sdl]` — LVGL 9.3 + SDL2, same `deck_ui` sources, BLE stubbed.
- Inventory: [`DECK_UI_SURFACE_INVENTORY.md`](../../_scratch/deck16_tab5_k1_proof_20260807/DECK_UI_SURFACE_INVENTORY.md)
- Receipt / PNGs: [`DECK_UI_SIM_DEPLOY_RECEIPT.md`](../../_scratch/deck16_tab5_k1_proof_20260807/DECK_UI_SIM_DEPLOY_RECEIPT.md)
- Run: `cd tab5_firmware && pio run -e native_sdl && ./.pio/build/native_sdl/program --linked`
- Tab5.DSP/simulator remains theme-preview only (does not import `deck_ui`).
- Device-only: real HCI/BLE TX, K1 `apply_ok`, serial encoderless (unless later wired into sim).

---

## Protocol — map-generated TX

| Topic | Canon |
|-------|-------|
| **Authority map** | [`docs/protocol/k1-ble-midi-map.json`](../protocol/k1-ble-midi-map.json) — `generated_by: oracle_ble_midi_map.py` |
| **Tab5 embed** | `tab5_firmware/src/k1_ble_midi_map.h` — must stay aligned with JSON oracle |
| **TX path** | `ble_midi_transport.cpp` → `sendMappedNumber(path, …)` / map lookup — **no ad-hoc CC bytes** |
| **`primary.photons`** | **CC14** MSB=**1**, LSB=**33** (ch0); range 0.05–1.0 |
| **CC7 danger** | `midi: "cc7"` in map = **enum/bool** controls (palette index, incandescent flags) — **not** brightness. Sending brightness as CC7 hits wrong K1 fields. |
| **Link proof** | Tab5 `tx CC ch=1 cc=1` + `cc=33` → K1 `apply_ok` + `CONFIG.PHOTONS` | [`LINK_PROOF.md`](../../_scratch/deck16_tab5_k1_proof_20260807/LINK_PROOF.md) |

```45:54:docs/protocol/k1-ble-midi-map.json
      "path": "primary.photons",
      "channel": 0,
      "type": "float",
      "midi": "cc14",
      "cc_msb": 1,
      "cc_lsb": 33,
      "min": 0.05,
      "max": 1.0,
      "encode": "v14 = round((value-min)/(max-min)*16383)"
```

**K718 retired:** Do not plan Deck16 around `JC3636_K718_REMOTED_BLE_V1` or `SpectraSynq Remoted` dial framing. Bench K1 central (`k1_bench_im69d_ble`) links to Tab5 peripheral.

---

## Proof pack index (`_scratch/deck16_tab5_k1_proof_20260807/`)

| File | Role |
|------|------|
| [`HCI_PATH_DIAGNOSIS.md`](../../_scratch/deck16_tab5_k1_proof_20260807/HCI_PATH_DIAGNOSIS.md) | Pre-H0 timeout forensics; binding flags |
| [`H0_WIRE_CONTRACT.md`](../../_scratch/deck16_tab5_k1_proof_20260807/H0_WIRE_CONTRACT.md) | **Smoking gun** IF=3→4; HCI RX restored |
| [`HOST_14x_AB.md`](../../_scratch/deck16_tab5_k1_proof_20260807/HOST_14x_AB.md) | Host 1.4.0 A/B negative result |
| [`LINK_PROOF.md`](../../_scratch/deck16_tab5_k1_proof_20260807/LINK_PROOF.md) | Tab5↔bench K1 photons PASS |
| [`MODE_PALETTE_AUDIT.md`](../../_scratch/deck16_tab5_k1_proof_20260807/MODE_PALETTE_AUDIT.md) | UI name truth table |
| [`P4_UI_RECEIPT.md`](../../_scratch/deck16_tab5_k1_proof_20260807/P4_UI_RECEIPT.md) | Operator UI build/flash receipt |
| [`DECK_UI_SURFACE_INVENTORY.md`](../../_scratch/deck16_tab5_k1_proof_20260807/DECK_UI_SURFACE_INVENTORY.md) | Full MAIN / entry / harness inventory |
| [`DECK_UI_SIM_DEPLOY_RECEIPT.md`](../../_scratch/deck16_tab5_k1_proof_20260807/DECK_UI_SIM_DEPLOY_RECEIPT.md) | native_sdl deploy + run command |
| `DECK_UI_SIM_MAIN.png` | Operator MAIN SDL proof (linked) |
| [`BENCH_BLE_ACTIVE.md`](../../_scratch/deck16_tab5_k1_proof_20260807/BENCH_BLE_ACTIVE.md) | K1 `k1_bench_im69d_ble` radio baseline |
| `tab5_serial_h0_wire.log` | H0 serial capture |
| `k1_photons_live_delta.log` | End-to-end photons counters |

---

## Red-team box: refute “timeout ⇒ flash C6”

**Claim:** NimBLE `BLE_HS_ETIMEOUT_HCI` on Tab5 means the ESP32-C6 coprocessor firmware must be re-flashed (TTL, esptool, or OTA) before any further software work.

**Refutation:**

1. **Transport alive:** SDIO enum, `transport TX ready`, `fwversion 1.4.1 (rc=0)` — dead C6 cannot answer version RPC ([`HCI_PATH_DIAGNOSIS.md`](../../_scratch/deck16_tab5_k1_proof_20260807/HCI_PATH_DIAGNOSIS.md) §2–4).
2. **TX without RX:** `esp_hosted_tx rc=0` with **zero** `hci_rx_handler` events matches **wrong IF routing**, not bricked radio ([`H0_WIRE_CONTRACT.md`](../../_scratch/deck16_tab5_k1_proof_20260807/H0_WIRE_CONTRACT.md) §Smoking gun).
3. **Fix without C6 touch:** Changing host VHCI to `ESP_HCI_IF=4` on **unchanged C6 1.4.1** produced Command Complete, ADV, central connect, and photons control ([`LINK_PROOF.md`](../../_scratch/deck16_tab5_k1_proof_20260807/LINK_PROOF.md)).
4. **External precedent:** Espressif [#212](https://github.com/espressif/esp-hosted-mcu/issues/212) — HCI timeout persisted **after** successful C6 OTA; timeout ≠ reflash cure.
5. **Host A/B negative:** Matching factory host 1.4.0 **did not** restore BLE and regressed transport ([`HOST_14x_AB.md`](../../_scratch/deck16_tab5_k1_proof_20260807/HOST_14x_AB.md)).

**Required before C6 write:** H0 PASS documented, H1/H2 exhausted or waived by Captain, explicit flash authorisation, device registry update.

---

## Related authority

- Architecture: [`K1_DECK16_ARCHITECTURE_R1.md`](K1_DECK16_ARCHITECTURE_R1.md)
- IM69D + boot cross-canon: [`docs/canon/SESSION_CANON_2026-08-07_im69d_peakiness_deck16_boot.md`](../canon/SESSION_CANON_2026-08-07_im69d_peakiness_deck16_boot.md)
- Skill: [`.claude/skills/tab5-hosted-ble-debug/SKILL.md`](../../.claude/skills/tab5-hosted-ble-debug/SKILL.md)
- Guardrails: [`.cursor/rules/tab5-deck16-guardrails.mdc`](../../.cursor/rules/tab5-deck16-guardrails.mdc)
