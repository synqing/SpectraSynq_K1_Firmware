# Task Plan — dual-sync F0-F3 recovery

## Goal

Recover SyncLink through fail-closed host proof, observable BLE establishment,
scripted A/B/C silicon isolation and a real fault-evident Gate-0, stopping for
Captain after Case C.

## Current phase

Phase F0 — host trust root.

## Phases

### P-1: Canonical authority

- [x] Inspect live branch, HEAD, dirty tree and existing lane artefacts.
- [x] Capture the amended execution contract in `recovery-plan.md`.
- [x] Reconcile `AGENT_OS.md`, `.claude/handoff.md`, `docs/spec-index.md`,
  root `progress.md` and `repo-truth.sh`.
- [x] Review and stage only the owned documentation/source-truth files.
- [ ] Commit the verified P-1 checkpoint.
- **Status:** complete_pending_commit

### F0: Host trust root

- [ ] Exact NimBLE 2.5.0 pin and resolved-version evidence.
- [ ] Strict role/link/clock grammar and contract update.
- [ ] Coherent-epoch Link Ready and explicit status/exit schema.
- [ ] Per-role health and transport/apply loss split.
- [ ] Capture helper, segmented plumbing runner and A/B/C runner.
- [ ] Focused tests, full pytest, production and existing sync builds.
- [ ] Green F0 commit; push exact committed SHA and verify remote.
- **Status:** in_progress

### F1: Link hardening

- [ ] Advertising/scan defects A-E fixed with fail-closed diagnostics.
- [ ] Correct Remoted compile guards and sync-only leader.
- [ ] Mandatory build-wrapper and upload-guard registration/tests.
- [ ] Settled negotiated BLE values recorded.
- [ ] Focused tests, full pytest, production plus three sync builds.
- [ ] Green F1 commit.
- **Status:** pending

### F2: Silicon A/B/C

- [ ] Scripted, non-overwriting A/B/C harness and tracked evidence schema ready.
- [ ] Identity and wiring preflight.
- [ ] Case A PASS.
- [ ] Case B PASS.
- [ ] Case C PASS with real dial traffic.
- [ ] Tracked Captain STOP report.
- **Status:** pending

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
