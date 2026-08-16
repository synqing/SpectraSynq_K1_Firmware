# G0R cadence-authority amendment — Captain stamp A

Date: 2026-08-16 AWST  
Status: `CAPTAIN_STAMPED` (`A`)  
Deployed contract SHA-256 (verified, unchanged): `d17aa7c66b05281b79bafed2178f40f823ce92c04463b920d51fae63df919849`  
Amendment path: `docs/forensics/2026-08-15-freertos-scheduling-audit/gate0/amendments/G0R_2026-08-16.draft.json`

## Captain authority (verbatim)

> **Captain authority — 2026-08-16 AWST:**
> **A — The deployed 12.8 kHz / 96-sample / tempo-decimation-3 / 7.5 ms AP hop remains controlling. No authoritative product decision has been established that supersedes it with a 10 ms AP hop. The June 12.8 kHz / 128-sample and 16 kHz / 160-sample results remain probe evidence, not product authority. Do not alter the service thresholds or use a larger hop to green Gate 2.**

```text
G0R_CAPTAIN_STAMP                = A
TEN_MS_AP_HOP_AUTHORISED         = NO
CONTROLLING_SAMPLE_RATE_HZ       = 12800
CONTROLLING_CHUNK_SAMPLES        = 96
CONTROLLING_TEMPO_DECIMATION     = 3
CONTROLLING_AP_HOP_US            = 7500
GATE2_SERVICE_P99_LIMIT_US       = 6000
GATE2_RAW_DEADLINE_US            = 7500
B489_ABBA_FLASH_NOW              = HOLD
F887_PRODUCTION_FLASH            = NO
G3_DEVICE_IMPLEMENTATION         = BLOCKED
```

## Roles (do not collapse)

| Role | Path / meaning |
|---|---|
| DEPLOYED_CONTRACT | `gate0/contract.json` — 12800/96/d3/7500 µs; live `DEFAULT_CONTRACT`; **byte-for-byte unchanged** |
| STAMPED_TARGET | Affirmed as the same deployed tuple (stamp A). This amendment is **not** a selectable candidate contract. |
| CANDIDATE_ONLY | **Not created.** Stamp A does not authorise a 10 ms hop or hop128 probe pair. |

Live production pointer remains `gate0/contract.json`. A pointer targeting this stamped amendment must fail closed (`scope=NONE`).

## Cadence fields

Every `fields.new` equals the corresponding `fields.old`. No 10 ms AP-hop decision was located or reissued.

| Field | Old = new |
|---|---|
| AP_ACQUISITION_RATE_HZ | 133.333 |
| GDFT_INVOCATION_RATE_HZ | 133.333 |
| SPECTRAL_FLUX_CALC_RATE_HZ | 133.333 |
| ONSET_UPDATE_RATE_HZ | 133.333 |
| SEMANTIC_PUBLICATION_RATE_HZ | 133.333 |
| TEMPO_NOVELTY_INGEST_RATE_HZ | 44.444 |
| TEMPO_HEAVY_UPDATE_RATE_HZ | 44.444 |
| TEMPO_PUBLICATION_RATE_HZ | heavy 44.444; flywheel may stale-clear republish on non-emit |
| AP_HEAVY_DSP_INVOCATION_PERIOD_US | 7500 |
| AP_ARRIVAL_PERIOD_US | 7500 |
| AP_SERVICE_P99_MAX_US | 6000 |

June hop128 / 16 kHz numbers remain under `probe_candidates[]` only.

## Gate consequences

- Gate 2 remains **red** against the frozen 6 ms active-work p99. Cross0/40/80 and lane-4 results are valid 7.5 ms characterisation, not 10 ms proof.
- Gate 3 remains **blocked**.
- The 7.5 ms min/full A-B-B-A *plan* at pin `H` is unheld; **flash still requires a separate GO**. This stamp is not that GO.
- Unpaired five-second attribution captures remain stress/diagnostic evidence only.
