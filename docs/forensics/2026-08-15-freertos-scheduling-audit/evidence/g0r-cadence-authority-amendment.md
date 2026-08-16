# G0R cadence-authority amendment (draft)

Date: 2026-08-16  
Status: `DRAFT_AWAITING_CAPTAIN`  
Deployed contract SHA-256 (verified): `d17aa7c66b05281b79bafed2178f40f823ce92c04463b920d51fae63df919849`  
Draft path: `docs/forensics/2026-08-15-freertos-scheduling-audit/gate0/amendments/G0R_2026-08-16.draft.json`

## Roles (do not collapse)

| Role | Path / meaning |
|---|---|
| DEPLOYED_CONTRACT | `gate0/contract.json` — 12800/96/d3/7500 µs; live `DEFAULT_CONTRACT` |
| STAMPED_TARGET | Pending Captain A–E stamp |
| CANDIDATE_ONLY | May exist after stamp B/C for named probe envs only; `promotion_status=NOT_PRODUCTION` until Gate 8 |

Live production pointer must **not** target this draft. Loader rule: pointer to `DRAFT_AWAITING_CAPTAIN` fails closed.

## Split rate schema (source-confirmed)

Confirmed against `SPECTRASYNQ_K1_FIRMWARE.ino` and `audio/k1_tempo.cpp` at inventory/amendment time:

| Field | Old (deployed 7.5 ms) | Notes |
|---|---|---|
| AP_ACQUISITION_RATE_HZ | 133.333 | 12800/96 |
| GDFT_INVOCATION_RATE_HZ | 133.333 | once per AP hop |
| SPECTRAL_FLUX_CALC_RATE_HZ | 133.333 | `calculate_novelty` per hop |
| ONSET_UPDATE_RATE_HZ | 133.333 | per hop |
| SEMANTIC_PUBLICATION_RATE_HZ | 133.333 | per hop |
| TEMPO_NOVELTY_INGEST_RATE_HZ | 44.444 | `K1_NOVELTY_DECIMATION=3` |
| TEMPO_HEAVY_UPDATE_RATE_HZ | 44.444 | emit frames only |
| TEMPO_PUBLICATION_RATE_HZ | heavy 44.444; flywheel may stale-clear republish on non-emit | not novelty-alone |
| AP_HEAVY_DSP_INVOCATION_PERIOD_US | 7500 | equals semantic period while binding below is true |

`fields.new` are all `null` in the draft. June hop128 numbers live only under `probe_candidates[]`.

## Heavy-transaction binding

```text
HEAVY_AP_TRANSACTION_ONCE_PER_SEMANTIC_PERIOD = true
```

GDFT + novelty calc + onset + semantic publication execute once per AP semantic period. Tempo heavy work is separately decimated. Service p99 therefore remains `0.8 × 7500 µs = 6000 µs` against the deployed contract until a stamped candidate is selected by env+tuple match.

## Loader

`scripts/regression-harness/k1_scheduling_gate0.py::select_contract()`:

1. No pointer → deployed 7.5 ms (`no_pointer_deployed_contract`)
2. Draft pointer → `Gate0Error` / `DRAFT_AWAITING_CAPTAIN`
3. Stamped candidate, wrong env or tuple → fail closed
4. Stamped candidate, matching env+tuple → `CANDIDATE_ONLY`
5. `promotion_status=PRODUCTION` → `production_promotion_not_authorised_before_gate8`

## Explicit non-claims

- This draft does not close Gate 2 or authorise flash.
- This draft does not move `DEFAULT_CONTRACT`.
- Gate 3 remains blocked.
