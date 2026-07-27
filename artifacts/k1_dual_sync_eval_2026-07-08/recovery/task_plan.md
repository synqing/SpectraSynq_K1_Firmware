# Task Plan — dual-sync F0-F3 recovery

## Goal

Recover SyncLink through fail-closed host proof, observable BLE establishment,
scripted A/B/C silicon isolation and a real fault-evident Gate-0, stopping for
Captain after Case C.

## Current phase

Phase F2a.2 — reject no-op Case-C dial evidence before committing F2b
firmware observability.

## Phases

### P-1: Canonical authority

- [x] Inspect live branch, HEAD, dirty tree and existing lane artefacts.
- [x] Capture the amended execution contract in `recovery-plan.md`.
- [x] Reconcile `AGENT_OS.md`, `.claude/handoff.md`, `docs/spec-index.md`,
  root `progress.md` and `repo-truth.sh`.
- [x] Review and stage only the owned documentation/source-truth files.
- [x] Commit the verified P-1 checkpoint (`fe634bb`).
- **Status:** complete

### F0: Host trust root

- [x] Exact NimBLE 2.5.0 pin and resolved-version evidence.
- [x] Strict role/link/clock grammar and contract update.
- [x] Coherent-epoch Link Ready and explicit status/exit schema.
- [x] Per-role health and transport/apply loss split.
- [x] Capture helper, segmented plumbing runner and A/B/C runner.
- [x] Focused tests, full pytest, production and existing sync builds.
- [x] Green F0 commit; push exact committed SHA and verify remote
  (`4c1d48288fe99182748e67b0732275494210fccd`).
- **Status:** complete

### F0b: Late-attaching capture proof

- [x] Reproduce persistent healthy link becoming BLOCKED after serial input clear.
- [x] Require fresh exact `:sync_status` lifecycle snapshots from both roles.
- [x] Reject missing, unlinked, malformed, duplicate and incoherent snapshots.
- [x] Persist and hash `SYNC_STATUS.json` in F2 evidence.
- [x] Focused host tests and staged-boundary review.
- [x] Full pytest (`737 passed, 1 skipped`) in isolated staged-tree worktree.
- [x] Green host-only repair commit and verified push
  (`a4c2408696b84ebc4a860f69c8e86cf3adeb7db3`).
- **Status:** complete

### F1: Link hardening

- [x] Advertising/scan defects A-E fixed with fail-closed diagnostics.
- [x] Correct Remoted compile guards and sync-only leader.
- [x] Mandatory build-wrapper and upload-guard registration/tests.
- [x] Settled negotiated BLE values recorded.
- [x] Lifecycle snapshot serializer matches the F0b host contract.
- [x] Application-owned GATT I/O moved off the Core-0 audio loop.
- [x] Focused tests (`103 passed, 24 subtests passed`).
- [x] Full pytest (`760 passed, 1 skipped, 86 subtests passed`).
- [x] Production plus three sync builds SUCCESS; NimBLE exactly `2.5.0`.
- [x] Green F1 commit and verified push
  (`862aea89efc1c0c98035268a1b2ecf1bc1bab6f2`).
- [x] Three post-commit probe binaries rebuilt with embedded provenance
  `862aea8`.
- **Status:** complete

### F2: Silicon A/B/C

- [x] Independent host/firmware F2 preflight review completed; existing runner
  rejected as forgeable and insufficient for Case-C dial causality.
- [x] F2a guarded-upload and recursive evidence contract committed
  (`0a1100bc8525ecc1d3d29f64454b9e8e78f9dd19`).
- [x] F2a.1 periodic-counter window correction committed
  (`3077b4d5dab10811963b99bafe47729068db3bcf`).
- [x] F2a.2 meaningful-mode host contract and no-op regression validated.
- [ ] F2b application-image/dial-causality firmware observability committed.
- [x] Read-only USB serial/chip mapping and cross-target guard negatives.
- [ ] Captain physical GPIO/K718 attestation for the selected run.
- [ ] Case A PASS.
- [ ] Case B PASS.
- [ ] Case C PASS with real dial traffic.
- [ ] Tracked Captain STOP report.
- **Status:** f2a2_ready_to_commit_then_firmware

### F3: Real Gate-0

- [ ] Explicit Captain GO after A+B+C PASS.
- [ ] F3a host fault contract commit.
- [ ] F3b fixed-capacity firmware implementation commit.
- [ ] Fault qualification, restored controls, measurement and soak.
- **Status:** blocked_on_F2_and_Captain

## Decisions

| Decision | Rationale |
|---|---|
| Retain F0→F1→F2→Captain→F3 | Correctly separates oracle trust, link repair, silicon isolation and product proof. |
| Canonical authority lives in `recovery/recovery-plan.md` | The Cursor plan is outside git and cannot govern other checkouts or agents. |
| Orchestrator owns edits, gates, commits and device actions | SSA returns are hypotheses until re-run. |
| Existing dirty registry and wrapper edits are preserved | They pre-date this takeover and must not be silently absorbed. |
| Reopen F0 with a narrow F0b commit | Late-attaching F2 capture otherwise discards the only lifecycle transition and falsely blocks a healthy persistent link. |
| Split F2 readiness into F2a host and F2b firmware commits | The former runner trusted self-declared binaries/prior PASS JSON and could not prove causal K718 dial traffic or the flashed application image. |
| Count only meaningful Case-C mode changes | Accepted records that leave the confirmed ordinal unchanged are traffic, not physical detent proof; three no-op records must not satisfy the Captain commitment. |

## Stop conditions

- Any empty or missing-instrument capture appears as PASS.
- Any sync environment lacks upload-guard mapping.
- Any F0/F1 full commit gate fails.
- Any A/B/C identity mismatch, reset, reconnect, or incoherent epoch.
- Any attempt to enter F3 before A+B+C PASS and Captain GO.

## Errors encountered

| Error | Attempt | Resolution |
|---|---:|---|
| Governing `docs/agent/AGENT_EXECUTION_STANDARD.md` is referenced but absent | 1 | Use `AGENT_OS.md`, `.claude/CLAUDE.md`, AGENTS instructions and record the missing canon; do not invent it. |
| P-1 staged `git diff --check` found blank lines at EOF in two new recovery docs | 1 | Removed the extra blank lines with `apply_patch`; restage and rerun the same gate. |
| F0 adversarial SSA review reproduced pre-link and duplicate/reorder false-PASS paths | 1 | Select post-link role-local epochs, require positive overlap and post-link negotiation, preserve ordered TX evidence, and block on duplicate/reorder/unexpected records. Added reproductions to the focused suite. |
| First post-epoch focused run blocked the clean fixture because sequence zero preceded link-up | 1 | Moved synthetic proof observations behind an explicit settle offset; retained the fail-closed epoch selection. |
| Strict capture marker check mistook `t_host_us` for a second `host_us` prefix | 1 | Match a complete `host_us` token instead of a substring; rerun focused suite. |
| Final F0 wrapper review found locked-argument and A/B/C-order bypasses | 1 | Replaced the forwarding shell with a typed controller that derives case semantics, probes chip/build identity, enforces A→B→C and hashes its manifest evidence. |
| F1 adversarial review found lifecycle lines were one-shot before F2 attached | 1 | Added a fresh, fail-closed `:sync_status` capture contract and F2 evidence hash before firmware is committed. |
| F1 concurrency review found cross-generation characteristic writes and lossy clock callback timing | 1 | Moved periodic application GATT I/O to Core 1, made lifecycle publication generation-bound, deferred leader advertising restart, and queued callback-time clock timestamps with generation. |
| Initial F2 entry point was named incorrectly during read-only preflight | 1 | Located the committed `run_f2_abc.sh` → `f2_capture.py` path; no serial or device action was attempted. |
| Independent F2 reviews returned NO-GO on evidence provenance and dial causality | 1 | Added bounded F2a/F2b closure commits before any flash; Case A remains forbidden until both validate. |
| F2b adversarial review reproduced a Case-C no-op false PASS | 1 | Bind host evidence to three ordinal changes from the coherent baseline and require the firmware meaningful-mode counter delta to match emitted events exactly. |
