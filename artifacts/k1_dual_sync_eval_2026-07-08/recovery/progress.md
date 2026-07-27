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

## 2026-07-27 — F0 committed and F0b reopened

- F0 committed and pushed as
  `4c1d48288fe99182748e67b0732275494210fccd`.
- Post-commit leader/follower builds resolved NimBLE exactly `2.5.0`; remote
  branch equality was verified.
- F1 adversarial capture review reproduced a healthy persistent link becoming
  `BLOCKED` when F2 attached after link-up and cleared its one-shot lifecycle
  records.
- Implemented a host-only F0b repair: fresh exact `:sync_status` snapshots,
  per-role proof-context boundaries and hashed `SYNC_STATUS.json` evidence.
- Focused current validation:
  `103 passed, 24 subtests passed`.
- Isolated staged-tree full regression:
  `737 passed, 1 skipped, 83 subtests passed`.
- Firmware serializer is implemented in the unstaged F1 work; hardware remains
  untouched.

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

## 2026-07-27 — F1 link hardening commit gate

- Fixed advertising/scan defects A-E, added the SyncLink-only Case-A leader,
  registered its exact build/upload identity and retained exact NimBLE 2.5.0.
- Added strict application-ready lifecycle publication, stable exact
  negotiated read-back, current-state `:sync_status` replay and checked
  steady-state failure diagnostics.
- Closed adversarial generation/concurrency defects: lifecycle transitions are
  generation-bound; central writes and periodic stream work have Core-1
  owners; leader advertising restart is deferred; clock responses preserve
  callback-time `t4` and connection generation.
- Embedded SSA final concurrency verdict: `APPROVE`.
- Focused validation: `103 passed, 24 subtests passed`.
- Full repository validation:
  `760 passed, 1 skipped, 86 subtests passed`.
- Wrapper builds SUCCESS:
  `k1_hardware`, `k1_sync_probe_main`,
  `k1_sync_probe_main_sync_only`, `k1_sync_probe_bench`.
- All three probe dependency graphs resolve NimBLE-Arduino `2.5.0`.
- Build provenance is still pre-commit `a4c2408`; post-commit rebuilds are
  required before any F2 flash.
- No firmware, device, serial or hardware action performed.

## 2026-07-27 — F1 committed and published

- F1 committed as
  `862aea89efc1c0c98035268a1b2ecf1bc1bab6f2`
  (`fix(dual-sync): harden SyncLink adv/scan observability (defects A–E)`).
- The commit hook passed and the commit membership was rechecked: 14 intended
  F1 files; the pre-existing dirty device registry and all F0 host files were
  excluded.
- Pushed `lane/dual-sync-phase0`; local and remote refs both resolved to the
  full F1 SHA.
- Rebuilt all three probe environments after the commit. Each build succeeded,
  resolved NimBLE-Arduino `2.5.0` and embeds `862aea8`.
- Firmware SHA-256:
  - sync-only leader:
    `e08c2e8629b8bf123489e8b5b6a44eb97ab49c9307ebfed036ff2279dbaaa861`
  - dual-role leader:
    `e5b7210b8468c79b96921b3b9e7c78594789c1744a849586ab822b504947452e`
  - follower:
    `a83e1b798b9cc1a2c9bbd5860ac1f794dfdb29518e7ca1846d63e2886c6dc11b`
- F1 is complete at the source/build boundary. No firmware has been flashed
  and no runtime or silicon claim has been made.

## 2026-07-27 — F2 read-only preflight and F2a host hardening

- Re-read the phase task plan and ran session bootstrap before F2.
- Read-only port inventory identified leader USB serial
  `B4:3A:45:A5:87:F8` and follower USB serial
  `B4:3A:45:A5:89:B4`.
- Upload-guard positive controls passed for the sync-only leader and follower;
  both cross-target negative controls failed closed with exit `2`.
- Independent host and embedded reviews returned `NO-GO` on the original F2
  evidence contract. No flash, manual serial command or hardware action was
  performed.
- Implemented the bounded F2a host contract: guarded A/B-only uploader; Case C
  cannot upload; pre/post chip identity; preserved BIN/ELF and ESP application
  identity; exact command capture; recursive prior-case revalidation; tracked
  Captain attestations; causal Case-C dial proof; non-overwriting
  `CAPTAIN_STOP.md` with `decision: PENDING`.
- Current F2a focused validation:
  `75 passed` in `tests/test_dual_sync_oracle.py`; all three Python modules
  compile, both shell entry points pass `bash -n`, and `git diff --check`
  passes.
- Full repository regression:
  `775 passed, 1 skipped, 86 subtests passed` after the final adversarial
  closure additions.
- Final F2a adversarial reviewer verdict: `APPROVE`; all ten reproduced attack
  paths now fail closed, including a failed upload attempt being retained as a
  tracked `BLOCKED` write action.
- Hardware remains untouched. F2b firmware observability is still required
  before Case A.

## 2026-07-27 — F2a committed, then periodic-window correction

- F2a committed and published as
  `0a1100bc8525ecc1d3d29f64454b9e8e78f9dd19`
  (`fix(dual-sync): harden F2 evidence and upload contract`).
- Pre-silicon review reproduced a false-BLOCK path: the endpoint snapshots
  bracket the capture, but the first/last 1 Hz samples sit inside it, so their
  deltas cannot be exactly equal under live traffic.
- Replaced equality with cumulative endpoint bounds and retained an independent
  positive-periodic-traffic requirement for Case C.
- Focused host regression after the correction: `76 passed`.
- Full regression from an isolated staged tree:
  `776 passed, 1 skipped, 86 subtests passed`.
- F2a.1 committed and published as
  `3077b4d5dab10811963b99bafe47729068db3bcf`
  (`fix(dual-sync): bound F2 periodic evidence window`).
- Local and remote branch tips were verified equal at that SHA.

## 2026-07-27 — F2a.2 no-op dial-proof correction

- Independent F2b red-team review reproduced a false-PASS path: three accepted
  mode records that all retained the already-confirmed ordinal were counted as
  three physical mode changes.
- The host analyser now derives meaningful primary/secondary ordinal changes
  from the coherent baseline, requires at least three, and requires the
  `dial_mode_apply_ok` endpoint delta to match those events exactly.
- Added an adversarial duplicate/no-op regression. Current focused F2 gate:
  `126 passed, 24 subtests passed`.
- Full regression from an isolated staged tree:
  `777 passed, 1 skipped, 86 subtests passed`.
- This correction remains host-only. Firmware observability is uncommitted and
  no device, serial or hardware action has occurred.

## 2026-07-27 — F2a.3 scanner and BLE-MIDI batching contract

- F2b re-review remained `NO-GO`: Case B could pass without current Remoted
  scanner evidence, and Case C required three notifications even though one
  notification may legally carry multiple mode records.
- Extended the strict status/counter grammar with scanner-active, scanner-start
  success/failure and stale-generation-drop fields.
- Case B now requires sampled scanner activity, an observed successful start,
  and zero in-window restart/failure. Case C requires at least one notification
  but retains the three-record/three-meaningful-change requirement.
- Added scanner-inactive, scanner-restart and batched-notification regressions.
  Current host-focused validation: `78 passed`; firmware-static/upload focused
  validation: `49 passed, 24 subtests passed`.
- Full regression from an isolated staged tree:
  `778 passed, 1 skipped, 86 subtests passed`.
- No device, serial or hardware action has occurred.

## 2026-07-27 — F2b firmware observability ready to commit

- F2a.2 was committed and published as
  `7320262d98998f258c9e4f710744faad4ef0dc72`.
- F2a.3 was committed and published as
  `acb9c4002a1da2a4c9371a30187e25d614af0082`; local and remote refs were
  verified equal.
- Added exact application-image and per-boot runtime evidence, strict Remoted
  scanner/traffic/apply/confirmation counters and meaningful dial-mode events.
- Bound queued records and pending confirmation targets to the live connection
  generation with visible stale-generation rejection.
- Final adversarial review found one remaining reconnect path: partial CC14 or
  NRPN decoder state could survive into a new connection. Added an explicit
  partial-state reset before generation advancement, preserving the next
  record ID, plus host regressions for both protocol paths.
- Independent final firmware review verdict: `APPROVE`; no earlier blocker
  regressed.
- Focused validation:
  `134 passed, 24 subtests passed`.
- Canonical full repository validation:
  `786 passed, 1 skipped, 86 subtests passed`.
- An unscoped `pytest -q` attempt was rejected during collection because
  `_scratch/dual_sync_external_consult_20260727/04_HOST/tests` preserves
  duplicate module names. The scoped canonical `tests/` run above is green;
  consult evidence was not deleted.
- Wrapper builds SUCCESS:
  `k1_hardware`, `k1_sync_probe_main`,
  `k1_sync_probe_main_sync_only`, `k1_sync_probe_bench`.
- All probe builds resolved NimBLE-Arduino `2.5.0`. They currently embed the
  pre-F2b revision `acb9c40` and will be rebuilt after the F2b commit.
- No flash, serial command or hardware action occurred.

## Delegation ledger

| ID | Task | Class | Status | Evidence | Orchestrator re-run | Consumed as |
|---|---|---|---|---|---|---|
| dual-sync-p1-authority-003 | Cross-tool lane authority audit | load-bearing | received | `recovery/ssa/p1_authority_contract.md` | `bash -n`; repo-truth; bootstrap; tracked-authority and staged-exclusion checks PASS | verified evidence |
| dual-sync-f0-host-003 | F0 host implementation map | load-bearing | received | `recovery/ssa/f0_host_contract.md` | focused baseline and implementation tests rerun | implementation contract |
| dual-sync-f1-fw-003 | F1 firmware/API/guard map | load-bearing | received | `recovery/ssa/f1_firmware_contract.md` | source/API checks pending F1 | F1 implementation input |
| dual-sync-f0-review-004/005/006/007 | Adversarial F0 implementation review | load-bearing | VERIFIED | `recovery/ssa/f0_implementation_review.md` | 63 focused tests plus negative wrapper probes PASS | verified host evidence |
| dual-sync-f0-late-attach-008 | Adversarial F1/capture boundary review | load-bearing | received | persistent-link reproduction + unstaged F0b host patch | 103 focused tests and strict status negatives PASS | F0b repair input |
| dual-sync-f1-concurrency-009/010 | Adversarial connection-generation and Core ownership review | load-bearing | APPROVE | current source citations in SSA return | focused tests, four builds and full regression PASS | verified F1 evidence |
| dual-sync-f2-preflight-011/012/013 | F2 identity, evidence and dial-causality review | load-bearing | F2a APPROVE; F2b APPROVE after four review/repair cycles | current-source SSA returns | read-only USB/guard checks; full host gate; four builds; reconnect decoder regressions | verified F2a/F2b evidence |

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
| F0b focused current | `PYTHONPATH=. /Users/spectrasynq/miniforge3/bin/python -m pytest -q tests/test_dual_sync_probe_firmware_static.py tests/test_dual_sync_oracle.py tests/test_k1_upload_guard.py` | 103 passed, 24 subtests passed |
| F0b isolated staged tree | `PYTHONPATH=. /Users/spectrasynq/miniforge3/bin/python -m pytest -q tests/` | 737 passed, 1 skipped, 83 subtests passed |
| F1 focused current | `PYTHONPATH=. /Users/spectrasynq/miniforge3/bin/python -m pytest -q tests/test_dual_sync_probe_firmware_static.py tests/test_dual_sync_oracle.py tests/test_k1_upload_guard.py` | 103 passed, 24 subtests passed |
| F1 full current | `PYTHONPATH=. /Users/spectrasynq/miniforge3/bin/python -m pytest -q tests/` | 760 passed, 1 skipped, 86 subtests passed |
| F1 production build | `bash scripts/agent/pio-build.sh k1_hardware` | SUCCESS |
| F1 dual-role leader build | `bash scripts/agent/pio-build.sh k1_sync_probe_main` | SUCCESS; NimBLE 2.5.0 |
| F1 sync-only leader build | `bash scripts/agent/pio-build.sh k1_sync_probe_main_sync_only` | SUCCESS; NimBLE 2.5.0 |
| F1 follower build | `bash scripts/agent/pio-build.sh k1_sync_probe_bench` | SUCCESS; NimBLE 2.5.0 |
| F2 read-only guard map | correct leader/follower guard commands plus both cross-target negatives | PASS / negative exit 2 |
| F2a focused current | `PYTHONPATH=. python3 -m pytest -q tests/test_dual_sync_oracle.py` | 75 passed |
| F2a syntax | `python3 -m py_compile ...`; `bash -n run_f2_abc.sh run_f2_flash.sh`; `git diff --check` | PASS |
| F2a full current | `PYTHONPATH=. /Users/spectrasynq/miniforge3/bin/python -m pytest -q tests/` | 775 passed, 1 skipped, 86 subtests passed |
| F2a.1 focused current | `python3 -m pytest -q tests/test_dual_sync_oracle.py` | 76 passed |
| F2a.1 full isolated staged tree | `PYTHONPATH=. /Users/spectrasynq/miniforge3/bin/python -m pytest -q tests/` | 776 passed, 1 skipped, 86 subtests passed |
| F2a.2 focused current | `PYTHONPATH=. /Users/spectrasynq/miniforge3/bin/python -m pytest -q tests/test_dual_sync_oracle.py tests/test_dual_sync_probe_firmware_static.py tests/test_k1_upload_guard.py` | 126 passed, 24 subtests passed |
| F2a.2 full isolated staged tree | `PYTHONPATH=. /Users/spectrasynq/miniforge3/bin/python -m pytest -q tests/` | 777 passed, 1 skipped, 86 subtests passed |
| F2a.3 host focused current | `PYTHONPATH=. /Users/spectrasynq/miniforge3/bin/python -m pytest -q tests/test_dual_sync_oracle.py` | 78 passed |
| F2a.3 firmware-static/upload focused current | `PYTHONPATH=. /Users/spectrasynq/miniforge3/bin/python -m pytest -q tests/test_dual_sync_probe_firmware_static.py tests/test_k1_upload_guard.py` | 49 passed, 24 subtests passed |
| F2a.3 full isolated staged tree | `PYTHONPATH=. /Users/spectrasynq/miniforge3/bin/python -m pytest -q tests/` | 778 passed, 1 skipped, 86 subtests passed |
| F2b focused current | `PYTHONPATH=. /Users/spectrasynq/miniforge3/bin/python -m pytest -q tests/test_ble_midi_firmware_decoder.py tests/test_dual_sync_oracle.py tests/test_dual_sync_probe_firmware_static.py tests/test_k1_upload_guard.py` | 134 passed, 24 subtests passed |
| F2b full current | `PYTHONPATH=. /Users/spectrasynq/miniforge3/bin/python -m pytest -q tests/` | 786 passed, 1 skipped, 86 subtests passed |
| F2b production build | `bash scripts/agent/pio-build.sh k1_hardware` | SUCCESS |
| F2b dual-role leader build | `bash scripts/agent/pio-build.sh k1_sync_probe_main` | SUCCESS; NimBLE 2.5.0 |
| F2b sync-only leader build | `bash scripts/agent/pio-build.sh k1_sync_probe_main_sync_only` | SUCCESS; NimBLE 2.5.0 |
| F2b follower build | `bash scripts/agent/pio-build.sh k1_sync_probe_bench` | SUCCESS; NimBLE 2.5.0 |

## Next

Commit and publish the independently approved F2b firmware boundary, rebuild
all three immutable probe images with the committed revision and record their
hashes. Do not flash until Captain provides the physical GPIO/K718 attestation.
