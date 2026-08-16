# G0R Captain decision card (A–E) — HARD STOP

Date: 2026-08-16  
Status: **decision card ready; awaiting Captain stamp**  
Do **not** start R7/R8. Do **not** flash. Do **not** invent a stamp.

## Pins and artefacts

```text
G0R_INVENTORY_PATH
  docs/forensics/2026-08-15-freertos-scheduling-audit/evidence/g0r-cadence-authority-inventory.md

G0R_DRAFT_AMENDMENT_PATH
  docs/forensics/2026-08-15-freertos-scheduling-audit/gate0/amendments/G0R_2026-08-16.draft.json

HARNESS_FIRMWARE_PIN_SHA (H)
  14c53d239524aa891e71470880f6917d4adf2ea6

RECEIPT_IDENTIFYING_H (R)
  6b48c51ece1a56c4bb99765fccc9f60a6e557dd1

FINAL_ABBA_TOOLCHAIN_PIN_SHA (T)
  c1aba345603bc2cacc8cf30648768d346f572779

DEPLOYED_CONTRACT_SHA256
  d17aa7c66b05281b79bafed2178f40f823ce92c04463b920d51fae63df919849
  (12800 / 96 / d3 / 7500 µs; p99 6000 µs)

STRONGEST_ON_DISK_10MS_HIT
  path: docs/forensics/tempo_tracking_refactor/2026-06-06-ap0-vp1-implementation-handover.md §7
  classification: PROBE_CANDIDATE (June click-pass; explicitly not the immediate next move)
```

## Ask Captain to stamp exactly one of

```text
A) 7.5 ms AP semantic hop remains controlling (deployed contract)
B) 10 ms AP semantic hop at 12.8 kHz / 128 / tempo_decim=2 (50 Hz tempo ingest)
C) 10 ms AP semantic hop at 12.8 kHz / 128 / tempo_decim=3 (33.333 Hz tempo ingest)
D) 10 ms meant a non-hop surface (state which)
E) 16 kHz/160 or 24 kHz/240 — NOT this lane
```

## Recommendation from on-disk evidence (not a stamp)

**A** matches the frozen deployed contract and Gate 0 close lineage.  
**B/C** are June **probe** candidates unless Captain reissues them as product.  
Do not auto-pick B to make Gate 2 look greener.  
Irregular rational to keep 44.444 Hz novelty ingest is rejected unless Captain overrides.  
A **C** stamp must not be executed on a d2 environment.

## Flash / Gate policy until stamp

```text
FLASH REMAINS HOLD UNTIL THAT STAMP PLUS A SEPARATE FLASH GO
G3_IMPLEMENTATION = BLOCKED
F887_FLASH = NO
B489_ABBA_FLASH_NOW = HOLD
production pointer = gate0/contract.json (unchanged)
draft status = DRAFT_AWAITING_CAPTAIN (not live)
```

## Executor stop line

R0–R6 complete through this card. **HARD STOP.**  
R7/R8 require an explicit Captain A–E stamp (and R8 also a separate B489 flash GO).
