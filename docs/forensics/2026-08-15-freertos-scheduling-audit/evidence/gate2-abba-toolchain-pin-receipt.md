# Gate-2 ABBA toolchain pin receipt (identifies T)

```text
toolchain_commit_sha: c1aba345603bc2cacc8cf30648768d346f572779
receipt_commit_sha: SELF_NOT_EMBEDDED
harness_commit_sha: 14c53d239524aa891e71470880f6917d4adf2ea6
FINAL_ABBA_TOOLCHAIN_PIN_SHA: c1aba345603bc2cacc8cf30648768d346f572779
HARNESS_FIRMWARE_PIN_SHA: 14c53d239524aa891e71470880f6917d4adf2ea6
admissible_as: FINAL_ABBA_TOOLCHAIN_PIN_NOT_FLASH_GO
B489_ABBA_FLASH_NOW: HOLD
contract_id_still_controlling: K1_SCHEDULING_GATE0_2026_08_15
production_tuple_at_H: 12800/96/d3/7500
```

T is the ABBA host comparator/runner pin after frame-class work. H remains the measurement firmware pin. One SHA does not own both.

## Paths frozen at T

```text
comparator_sha256: a96fbe6d0dba5dcf6377a9fc01c9f79d79fb874e309e0c915fb62812953ebf43
capture_runner_sha256: bc0684dae1da9dfc5d735084302e578f963c425019a84f254d5208f57f9c6ad1
```

Symbols required at T: `frame_class_distributions`, `compare_frame_classes`, `perturbation_limits`, `EXCLUSIVE_FRAME_CLASSES`.

Perturbation limits frozen from deployed contract (7.5 ms): `ap_p99_delta_max_us=375` (0.05×7500). Do not retune after R8 numbers.

## Gate results

```text
full_pytest_result: 1298 passed, 1 skipped
```
