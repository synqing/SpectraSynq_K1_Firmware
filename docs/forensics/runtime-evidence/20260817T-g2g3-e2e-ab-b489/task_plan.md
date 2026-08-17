# B489 G2/G3 E2E A/B — execution pack

Decision: does `e911f86d` Cross40+Lane4+G3/G4 satisfy the already-defined B489
scheduling predicates under quiet and real music, versus the pre-restamp probe.

- Arm A: `8f53c48e` `k1_bench_scheduling_stage_full_probe`
- Arm B: `e911f86d` `k1_bench_scheduling_gdft_cross40_lane4_full_probe`
- Arm C: only if B fails numeric gate; G3 unflag, G4 held
- Eight primary legs, one process, flash on arm change only
- Score vs `service_limits_from_contract()` = 8000 µs, not 6000
- Historical 7712 µs is REFERENCE_ONLY_NOT_AN_ABBA_LEG
- Restore `k1_bench_im69d` @ `e911f86d` on B489; never flash F887
