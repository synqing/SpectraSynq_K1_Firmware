# Progress — dual-sync F0-F3 recovery

## 2026-07-27 — P-1 authority committed

- Commit: `fe634bb docs(dual-sync): canonise F0-F3 recovery authority`
- Validation: `bash -n scripts/agent/repo-truth.sh`, direct
  `scripts/agent/repo-truth.sh`, `scripts/agent/session-bootstrap.sh` and the
  documentation pre-commit tier all passed.
- Pre-existing dirty files `docs/hardware/device-build-registry.md` and
  `scripts/agent/pio-build.sh` remained outside the commit.

## 2026-07-27 — F0 oracle contract first pass

- Implemented strict/permissive log parsing, coherent Link Ready epochs,
  follower-clock truth, explicit verdict states/exit codes, role-split health,
  and separate transport/apply integrity.
- Initial focused validation: `30 passed` in
  `tests/test_dual_sync_oracle.py`.
- SSA adversarial review status was `NOT_VERIFIED` after reproducing two
  false-PASS paths. The implementation now selects post-link epochs and blocks
  duplicate, reordered, reset and unexpected sequences; strict grammar rejects
  ambiguous prefixes/keys/trailing data.
- Added the testable shared-clock capture helper and `NOT_GATE0` segmented
  wrapper with exact fresh ACKs, exclusive output and acknowledged cleanup.
- A second adversarial review found post-link `begin`, invalid negotiated
  values and persistent-link segment-context gaps. All are now fail-closed,
  including cross-role negotiated-value agreement.
- Current focused validation: `63 passed`; both shell entry points pass
  `bash -n`.
- Final full repository regression: `731 passed, 1 skipped`.
- Build-wrapper results:
  `k1_hardware`, `k1_sync_probe_main` and `k1_sync_probe_bench` all SUCCESS.
- Both sync libdeps resolve `NimBLE-Arduino version=2.5.0`.
- Final SSA closure review: `VERIFIED`; host-side machinery only.
- Hardware remains untouched; these are compile and host proofs only.
- Hardware remains untouched.

## 2026-07-27 — Codex SSA orchestration takeover

- Captain authorised Codex to take over as SSA orchestrator.
- Loaded `ssa-management` and `planning-with-files`.
- Ran `scripts/agent/session-bootstrap.sh`.
- Confirmed branch `lane/dual-sync-phase0 @ 3a9724e`.
- Confirmed existing dirty tracked files:
  `docs/hardware/device-build-registry.md` and
  `scripts/agent/pio-build.sh`.
- Read the prior lane task plan, findings and progress.
- Canonicalised the amended recovery contract under `recovery/`.
- Reconciled the live dual-sync lane in `AGENT_OS.md`,
  `.claude/handoff.md`, `docs/spec-index.md` and root `progress.md`.
- Changed `repo-truth.sh` to validate the explicit
  `active_branch`/`active_authority` frontmatter instead of accepting stale
  IM73D text.
- First commit attempt stopped before `git commit` because
  `git diff --cached --check` found blank lines at EOF in two new recovery
  docs. The extra lines were removed; no commit was created by that attempt.
- No firmware, device, serial or hardware action performed.

## Delegation ledger

| ID | Task | Class | Status | Evidence | Orchestrator re-run | Consumed as |
|---|---|---|---|---|---|---|
| dual-sync-p1-authority-003 | Cross-tool lane authority audit | load-bearing | received | `recovery/ssa/p1_authority_contract.md` | `bash -n`; repo-truth; bootstrap; tracked-authority and staged-exclusion checks PASS | verified evidence |
| dual-sync-f0-host-003 | F0 host implementation map | load-bearing | received | `recovery/ssa/f0_host_contract.md` | focused baseline and implementation tests rerun | implementation contract |
| dual-sync-f1-fw-003 | F1 firmware/API/guard map | load-bearing | received | `recovery/ssa/f1_firmware_contract.md` | source/API checks pending F1 | F1 implementation input |
| dual-sync-f0-review-004/005/006/007 | Adversarial F0 implementation review | load-bearing | VERIFIED | `recovery/ssa/f0_implementation_review.md` | 63 focused tests plus negative wrapper probes PASS | verified host evidence |

## Test results

| Phase | Command | Result |
|---|---|---|
| Review baseline | `python3 -m pytest -p no:cacheprovider tests/test_dual_sync_oracle.py tests/test_dual_sync_probe_firmware_static.py -q` | 25 passed |
| P-1 syntax | `bash -n scripts/agent/repo-truth.sh` | PASS |
| P-1 authority | `bash scripts/agent/repo-truth.sh` | WARN only for pre-existing dirty registry; active authority/branch/status and all routers PASS |
| P-1 bootstrap | `bash scripts/agent/session-bootstrap.sh` | PASS with the same expected registry warning |
| P-1 staged diff | `git diff --cached --check` and explicit exclusion check | PASS; registry and `pio-build.sh` excluded |
| F0 focused current | `python3 -m pytest -p no:cacheprovider tests/test_dual_sync_oracle.py tests/test_dual_sync_probe_firmware_static.py -q` | 63 passed |
| F0 full regression final | `python3 -m pytest -p no:cacheprovider tests/ -q` | 731 passed, 1 skipped |
| F0 production build | `bash scripts/agent/pio-build.sh k1_hardware` | SUCCESS |
| F0 leader build | `bash scripts/agent/pio-build.sh k1_sync_probe_main` | SUCCESS; NimBLE 2.5.0 |
| F0 follower build | `bash scripts/agent/pio-build.sh k1_sync_probe_bench` | SUCCESS; NimBLE 2.5.0 |

## Next

Review the narrow F0 staged diff, commit, rebuild against the committed SHA,
then push and verify the remote SHA.
