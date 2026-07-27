# SSA Dispatch — F2 C1/C2 evidence and status model

```text
delegation_id:           dual-sync-f2c-evidence-status-016
role:                    fail-closed host-oracle specialist
task:                    Implement immutable C1/C2 attestation/feedback validation and aggregate F2 status finalisation.
classification:          load-bearing
expected_output:         New evidence/finalisation module and focused tests on disjoint files; concise SSA return contract.
source_scope:            scripts/dual_sync_probe/f2_capture.py, gate_eval.py, existing F2 tests and recovery authority
write_scope:             scripts/dual_sync_probe/f2_status.py, tests/test_f2_status.py only
forbidden_actions:       upload, flash, erase, serial/device access, build, commit, edit existing controller files, edit docs/registry/firmware
checkpoint_timeout:      20 minutes
bounded_retry:           one 5-minute request for a useful partial
fallback_owner:          orchestrator-local
final_answer_dependency: no; orchestrator can replace locally
escalation_condition:    missed checkpoint or status rule ambiguity
consumption_rule:        orchestrator audits and integrates into capture/finalise path; reruns all tests
```

Required behaviour: separate pre-run and post-run immutable files, C1/C2
software and physical status, collection/acceptance matrix, STOP hashing, and
`f3_authorised=false` until a separate Captain decision file exists.
