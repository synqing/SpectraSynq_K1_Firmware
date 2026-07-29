# WB-3 red-team closure checklist

**RBDO:** GROUNDED as audit checklist; programme **not closed** while Captain decision and H2/H3 remain `INDETERMINATE`.

## Anti-patterns blocked

- [x] Stale ledger "not started / 42 bins" corrected in Lightwave `BACKLOG.md`
- [x] Authority map separates `f6cf78f` vs `d40114f`/`a9ff00c`
- [x] Source parity impossibility documented
- [x] VP spec rejects self-shadow / blank parity
- [x] Host `stm_vp_compare` negative-control tests present
- [ ] clangd Gate 0 verified before C++ convergence
- [ ] Independent 512 reference attested OR product-value criterion formally adopted
- [ ] Core-0 **MEASURED** bundle
- [ ] Hardware VP matrix with approved fixtures
- [ ] Captain decision record completed
- [ ] Selected-path convergence executed
- [ ] Production promotion or deliberate absence recorded

## Pre-mortem triggers (stop if observed)

- Cherry-picking `f6cf78f` onto main
- A==A or blank VP pass treated as parity
- Host replay reported as perceptual proof
- Post-hoc threshold edits
- Flash without MAC/registry/rollback
- Agent chooses product path or promotes `k1_hardware` without sign-off

## Closure rule

WB-3 investigation row may move to **closed** only when decision + evidence + selected-path state are independently reproducible from artefacts listed in `WB3_AUTHORITY_MAP.md`.
