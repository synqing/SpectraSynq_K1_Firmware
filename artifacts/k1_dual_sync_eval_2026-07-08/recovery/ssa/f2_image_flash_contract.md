# SSA Dispatch — F2 exact image and flash controller

```text
delegation_id:           dual-sync-f2c-image-flash-014
role:                    firmware provenance and flash-controller specialist
task:                    Implement exact reviewed-image validation and app-only guarded F2 flashing without a PlatformIO rebuild.
classification:          load-bearing
expected_output:         Code and focused tests on the assigned image/flash surface; concise SSA return contract.
source_scope:            scripts/dual_sync_probe/f2_flash.py, scripts/platformio/k1_upload_guard.py, platformio.ini, existing F2 tests and image evidence
write_scope:             scripts/dual_sync_probe/f2_image_set.py, scripts/dual_sync_probe/f2_flash.py, tests/test_dual_sync_oracle.py only
forbidden_actions:       upload, flash, erase, serial write, build, commit, edit authority/planning docs, edit firmware, touch device registry
checkpoint_timeout:      20 minutes
bounded_retry:           one 5-minute request for a useful partial
fallback_owner:          orchestrator-local
final_answer_dependency: no; orchestrator can replace locally
escalation_condition:    missed checkpoint or unsafe hardware action
consumption_rule:        orchestrator audits diff and reruns every focused/full gate
```

Required behaviour: separate host/firmware SHAs, validate a frozen image-set
manifest, forbid build-coupled upload, read back the partition table, write only
the application image with the pinned esptool, and preserve non-overwriting
failure evidence.
