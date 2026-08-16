# G0R Captain decision card (A–E) — STAMPED A

Date: 2026-08-16 AWST  
Status: **Captain stamped A.** R7A consequences applied. This stamp is **not** B489 flash authorisation.

## Pins and artefacts

```text
G0R_INVENTORY_PATH
  docs/forensics/2026-08-15-freertos-scheduling-audit/evidence/g0r-cadence-authority-inventory.md

G0R_AMENDMENT_PATH
  docs/forensics/2026-08-15-freertos-scheduling-audit/gate0/amendments/G0R_2026-08-16.draft.json
  status = CAPTAIN_STAMPED (A); fields.new = fields.old

HARNESS_FIRMWARE_PIN_SHA (H)
  14c53d239524aa891e71470880f6917d4adf2ea6

RECEIPT_IDENTIFYING_H (R)
  6b48c51ece1a56c4bb99765fccc9f60a6e557dd1

FINAL_ABBA_TOOLCHAIN_PIN_SHA (T)
  c1aba345603bc2cacc8cf30648768d346f572779

DEPLOYED_CONTRACT_SHA256
  d17aa7c66b05281b79bafed2178f40f823ce92c04463b920d51fae63df919849
  (12800 / 96 / d3 / 7500 µs; p99 6000 µs) — BYTE-FOR-BYTE UNCHANGED

STRONGEST_ON_DISK_10MS_HIT
  path: docs/forensics/tempo_tracking_refactor/2026-06-06-ap0-vp1-implementation-handover.md §7
  classification: PROBE_CANDIDATE (not product authority; stamp A)
```

## Stamp recorded

```text
G0R_CAPTAIN_STAMP                = A
CAPTAIN_AUTHORITY_DATE           = 2026-08-16 AWST
TEN_MS_AP_HOP_AUTHORISED         = NO
CONTROLLING_SAMPLE_RATE_HZ       = 12800
CONTROLLING_CHUNK_SAMPLES        = 96
CONTROLLING_TEMPO_DECIMATION     = 3
CONTROLLING_AP_HOP_US            = 7500
GATE2_SERVICE_P99_LIMIT_US       = 6000
GATE2_RAW_DEADLINE_US            = 7500
```

## Flash / Gate policy after stamp A

```text
G2_SERVICE                       = RED against 6 ms p99 (do not green via a larger hop)
G3_IMPLEMENTATION                = BLOCKED
F887_FLASH                       = NO
B489_ABBA_FLASH_NOW              = HOLD
B489_ABBA_PLAN_ON_7P5_MIN_FULL   = UNHELD_AWAITING_SEPARATE_FLASH_GO
production pointer               = gate0/contract.json (unchanged)
```

R8 / device A-B-B-A must not begin until a **distinct** `B489_ABBA_FLASH_NOW=GO`.
