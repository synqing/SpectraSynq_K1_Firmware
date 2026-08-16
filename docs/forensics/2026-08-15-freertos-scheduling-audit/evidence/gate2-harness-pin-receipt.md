# Gate-2 harness pin receipt (commit R)

```text
harness_commit_sha: 14c53d239524aa891e71470880f6917d4adf2ea6
receipt_commit_sha: SELF_NOT_EMBEDDED
parent_of_harness_sha: be8dd1aa76dbf408d7c664a5df15742803479694
HARNESS_FIRMWARE_PIN_SHA: 14c53d239524aa891e71470880f6917d4adf2ea6
admissible_as: MEASUREMENT_HARNESS_PIN_NOT_G2_CLOSE
B489_ABBA_FLASH_NOW: HOLD_FOR_G0R
contract_id_still_controlling: K1_SCHEDULING_GATE0_2026_08_15
production_tuple_at_H: 12800/96/d3/7500
```

## Binary and source hashes (tree that became H)

```text
firmware_bin_sha256.k1_hardware: 467ac102b356eb7b9ffef12c4973a41c4428c6a483eb1c25d513fa92bd561647
firmware_bin_sha256.k1_bench_scheduling_stage_min_probe: c66c9dafd8e141d91878e6d98cc59a2ff778ea2f20876447ec4ceb3e0a325da2
firmware_bin_sha256.k1_bench_scheduling_stage_full_probe: 9fec6e2514945262df510da47afbb168ae000c86cbfec62730301a556898aa9a
platformio_ini_sha256: 7829b14088b9022b023f13c8a9112ccdd6a1f57a9b1e45d2d858cd38b13a600a
capture_runner_sha256: bc0684dae1da9dfc5d735084302e578f963c425019a84f254d5208f57f9c6ad1
initial_comparator_sha256: 6acc226249cf2a57b5976c3e08c2db3d5f64e4c2437f00e0f7013f7ffd8cbf77
pio_build_sh_sha256: ec3c7a36cfc45f73400b1ee9fd220b1ca64a4ec9bde2979b470c2addcc53b206
```

Receipt R identifies H. R is not the measurement pin. Initial host runner/comparator at H will be superseded for ABBA by toolchain pin T after frame-class work (R5).

## Gate results

```text
focused_pytest_result: 179 passed in 33.34s (exit 0)
full_pytest_result: 1282 passed, 1 skipped in 225.23s (exit 0)
k1_hardware_build: SUCCESS
k1_bench_scheduling_stage_min_probe_build: SUCCESS
k1_bench_scheduling_stage_full_probe_build: SUCCESS
pre_commit_gate_on_H: GATE PASSED (pytest 1282 passed, 1 skipped; pio k1_hardware SUCCESS)
```

## Excluded unpaired 5 s pack (not in H or R)

```text
path: docs/forensics/runtime-evidence/20260816T-gate2-stage-attribution-781c40a9/
capture_classification: B_ap_compute_overrun (unpaired 5 s dumps)
reason_excluded_from_Gate-2_proof: not frozen A-B-B-A; ADMISSIBLE_AS=7P5_STRESS_CHARACTERISATION_ONLY; keep out of measurement-toolchain pin

files:
  stage_attr_noplay_5s_20260816_031519__apcad.log
    size_bytes: 751283
    sha256: 44ffa4009b776f3f11231ad6b3524c8b63945a5a258d706e0f38eba9cc9900a1
  stage_attr_noplay_5s_20260816_031519__summary.json
    size_bytes: 9046
    sha256: 98759b8483fb30ed101585bf28ba532a1394525062a5fea4083a0802c871a825
  stage_attr_anchorpoint_5s_20260816_031555__apcad.log
    size_bytes: 747500
    sha256: 6967c568c6325da39c028e7e3dc436c560c7c833b74189c24465f703942c363a
  stage_attr_anchorpoint_5s_20260816_031555__summary.json
    size_bytes: 9350
    sha256: ae8714856bebc9c12311bca278875c9369a5c879e24456e9c3f991cf34a0c0a9
```
