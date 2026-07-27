# SSA Dispatch — F2 ports and controlled reboot

```text
delegation_id:           dual-sync-f2c-ports-reboot-015
role:                    ESP32 runtime identity and continuity specialist
task:                    Implement chained port manifests and the controlled two-device C2 reboot controller.
classification:          load-bearing
expected_output:         New controller modules plus focused tests on disjoint files; concise SSA return contract.
source_scope:            scripts/dual_sync_probe/capture.py, f2_capture.py, serial identity helpers, existing F2 tests
write_scope:             scripts/dual_sync_probe/f2_ports.py, scripts/dual_sync_probe/f2_reboot.py, tests/test_f2_ports_reboot.py only
forbidden_actions:       upload, flash, erase, serial write to real devices, build, commit, edit existing controller files, edit docs/registry/firmware
checkpoint_timeout:      20 minutes
bounded_retry:           one 5-minute request for a useful partial
fallback_owner:          orchestrator-local
final_answer_dependency: no; orchestrator can replace locally
escalation_condition:    missed checkpoint, real-device access, or API contradiction
consumption_rule:        orchestrator audits interfaces, integrates callers and reruns all tests
```

Required behaviour: USB-serial-first rebinding followed by chip verification,
hash-linked non-overwriting `ports_*.json`, A→B and B→C1 continuity, and
C1→C2 same-image/new-nonce enforcement after typed `:reset`.
