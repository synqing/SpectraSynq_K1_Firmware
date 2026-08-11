# G1 fault-harness receipt

**Gate:** G1 — Fault harness  
**Result:** PASS  
**Recorded:** 2026-08-11 (Australia/Perth)  
**Harness commit:** `c0713b9`  
**Machine-readable evidence:** `gate1_mutations.json`  
**Evidence SHA-256:** `ff597751ca684121f136d054298703fe7b1945b0291476f4a121824d9f18e8b0`

## Result

The positive reference oracle passes. Thirty-five disposable active mutants
cover M1-M9; every mutation changed its intended target and every mutant was
killed with its named finding present. The oracle also passed the explicit
non-fail-everything check.

| Finding | Active variants | Result |
|---|---:|---|
| M1 callback ownership | 6 | 6/6 killed |
| M2 duplicate connection owner | 1 | 1/1 killed |
| M3 queue loss/oversize | 2 | 2/2 killed |
| M4 early snapshot apply | 1 | 1/1 killed |
| M5 snapshot validation | 8 | 8/8 killed |
| M6 delta integrity/order | 5 | 5/5 killed |
| M7 RSSI state/backoff | 5 | 5/5 killed |
| M8 production diagnostics | 2 | 2/2 killed |
| M9 source closure/parity | 5 | 5/5 killed |

M9 includes the exact defect that reopened G0: missing protocol authority,
generated 68/71 map drift, JSON/header drift, and identity-digest drift.

Commands:

```sh
python3 tab5_firmware/scripts/tab5_gate1_mutation.py \
  --repo-root . \
  --json docs/receipts/tab5-hardening-20260811/gate1_mutations.json
python3 -m pytest tab5_firmware/tests/test_tab5_gate1_mutation.py -q
```

Output:

```text
TAB5_G1_MUTATION_GATE=PASS mutants=35 coverage=M1,M2,M3,M4,M5,M6,M7,M8,M9
4 passed
```

## Claim boundary

G1 proves the oracle is fault-evident for the enumerated failure classes. It
does **not** claim the frozen firmware already conforms. At G1 entry the source
still contains the expected G2 defects: callback allocation/log/lifecycle work,
silent queue loss, early snapshot mutation, incomplete validation, gap apply,
synchronous UI RSSI, and unenforced verbose diagnostics. G2 must make the real
source conform and must rerun this harness unchanged. A fixture-only green G1
cannot waive a red production-conformance check.

G2 may begin.
