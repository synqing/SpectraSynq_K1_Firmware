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
- [x] Commit the verified P-1 checkpoint (`fe634bb`).
- **Status:** complete

### F0: Host trust root

- [x] Exact NimBLE 2.5.0 pin and resolved-version evidence.
- [x] Strict role/link/clock grammar and contract update.
- [x] Coherent-epoch Link Ready and explicit status/exit schema.
- [x] Per-role health and transport/apply loss split.
- [x] Capture helper, segmented plumbing runner and A/B/C runner.
- [x] Focused tests, full pytest, production and existing sync builds.
- [ ] Green F0 commit; push exact committed SHA and verify remote.
- **Status:** commit_ready

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
| F0 adversarial SSA review reproduced pre-link and duplicate/reorder false-PASS paths | 1 | Select post-link role-local epochs, require positive overlap and post-link negotiation, preserve ordered TX evidence, and block on duplicate/reorder/unexpected records. Added reproductions to the focused suite. |
| First post-epoch focused run blocked the clean fixture because sequence zero preceded link-up | 1 | Moved synthetic proof observations behind an explicit settle offset; retained the fail-closed epoch selection. |
| Strict capture marker check mistook `t_host_us` for a second `host_us` prefix | 1 | Match a complete `host_us` token instead of a substring; rerun focused suite. |
| Final F0 wrapper review found locked-argument and A/B/C-order bypasses | 1 | Replaced the forwarding shell with a typed controller that derives case semantics, probes chip/build identity, enforces A→B→C and hashes its manifest evidence. |
