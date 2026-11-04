---
abstract: "Host-test freeze 2026-09-08. The 2026-09-07 four failures were against a dirty BLE-iPhone leftover tree. On HEAD cd38c7f3 plus this session's PCM overflow tests, those four PASS. No new host failures in the PCM/ST25/RPL slice."
---

# Host-test freeze

## Historical (2026-09-07 dirty tree) — do not re-litigate as current

From `docs/forensics/runtime-evidence/20260907T-pcm1808-st25-bringup/BASE_TEST_FAILURES.txt`:

1. `tests/test_k1_serial_safety.py::test_literal_sets_match_a_fresh_parse_of_both_defs` extra `ble_iphone`
2. `tests/test_k1_serial_safety.py::test_row1_bare_table_membership_matches_fresh_parse` extra `ble_iphone`
3. `tests/test_k1_serial_safety.py::test_recorded_def_blob_shas_are_current` sha `88c54825` vs `7d13ad05`
4. `tests/test_k1_upload_guard.py::K1UploadGuardTest::test_all_k1_chip_bound_envs_are_registered_in_guard` extra `k1_ble_iphone_probe`

Cause: leftover BLE-iPhone probe in the working tree, **not** in committed `cd38c7f3`. Unrelated dirty files still travel with the tree and must not be committed.

## Current (2026-09-08, this session)

Command:

```
python3 -m pytest tests/test_pcm1808_probe_env_static.py \
  tests/test_pcm1808_unpack_static.py \
  tests/test_pcm1808_clock_gate_static.py \
  tests/test_pcm1808_resampler_static.py \
  tests/test_st25_probe_env_static.py \
  tests/test_main_rpl_env_static.py \
  tests/test_k1_serial_safety.py \
  tests/test_k1_upload_guard.py -q
```

Result: **56 passed**. The four historical failures are **not** red on committed source.

New this session: overflow-witness static tests inside `test_pcm1808_probe_env_static.py` (callback before enable, ISR has no printf/heap).

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-09-08 | agent:grok | Froze historical vs current host-test status. |
