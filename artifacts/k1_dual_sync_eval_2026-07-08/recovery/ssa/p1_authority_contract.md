# P-1 authority contract audit

Status: **NOT_VERIFIED**. The intended dual-sync authority is locally coherent,
but it is not yet durable or cross-tool current.

## Observed authority conflict

- Git is on `lane/dual-sync-phase0` at
  `3a9724e5e4b7f871454f2dee154ac034854fb43d`.
- `AGENT_OS.md:51-62` declares `lane/im73d-pdm-eval` and IM73D as current.
- `.claude/handoff.md:3-8` declares IM73D current and names the stale branch.
- `docs/spec-index.md:7,16-20,34-40` declares IM73D current/active.
- `progress.md:4` declares IM73D as the current focus.
- `scripts/agent/repo-truth.sh:36-81` validates IM73D capability and mere
  IM73D/PDM substring presence; it does not compare Git's branch with a declared
  active-lane authority. Its unconditional `exit 0` at line 172 also makes
  direct invocations return success after an internally reported FAIL.
- `recovery/recovery-plan.md:92-93` calls the recovery documents tracked, but
  `git ls-files --error-unmatch` rejects them. All four recovery documents are
  untracked, `lane/dual-sync-phase0` has no upstream, and
  `git ls-remote --heads origin lane/dual-sync-phase0` returns no head.
- Pre-existing tracked modifications are
  `docs/hardware/device-build-registry.md` and `scripts/agent/pio-build.sh`.
  They are not P-1 authority work and must remain unstaged.

## Minimal patch map

1. **Track the authority first:** include
   `recovery-plan.md`, `task_plan.md`, `findings.md`, and recovery `progress.md`
   in the owned P-1 set. An ignored, untracked, or local-only authority is not
   published evidence.
2. **`docs/spec-index.md`:** add one machine-readable pointer near the top:
   `- **Active lane authority:** \`artifacts/k1_dual_sync_eval_2026-07-08/recovery/recovery-plan.md\``.
   Add dual-sync as the first active-lane row. Retitle the existing IM73D
   "current active lane" prose and row as retained prior/product authority;
   preserve its decisions, evidence links, pin maps, and device history.
3. **`AGENT_OS.md`:** replace the hard-coded IM73D current-lane block with the
   active-authority pointer and a generic rule: the authority document's
   `branch:` must equal the checked-out Git branch. Retain IM73D under a
   historical/product-authority subsection. Change the bootstrap description
   from "missing IM73D env/guard/plan" to "active authority missing, untracked,
   inactive, or branch-mismatched".
4. **`.claude/handoff.md`:** prepend a compact dual-sync current-lane block
   containing the same authority pointer, `lane/dual-sync-phase0`, baseline
   SHA, P-1 status, dirty-file exclusions, and next action. Rename the existing
   IM73D current-lane heading to "retained prior authority"; do not delete or
   rewrite its closed decisions.
5. **Root `progress.md`:** prepend a dated dual-sync current-focus entry with
   the authority pointer and P-1 state. Relabel the existing IM73D current-focus
   line as retained prior-lane status; preserve the historical chronology.
6. **`scripts/agent/repo-truth.sh`:** derive the authority path from the exact
   `Active lane authority` marker in `docs/spec-index.md`; fail if the pointer
   is missing, outside the repo, absent, untracked, not `status: active`, or its
   frontmatter `branch:` differs from Git. Require `AGENT_OS.md`,
   `.claude/handoff.md`, and root `progress.md` to contain that same derived
   authority path. Remove the IM73D-substring freshness checks at lines 58-81.
   Keep the IM73D env/guard/plan checks, but label them retained production
   invariants rather than current-lane proof. Exit nonzero when
   `OVERALL=FAIL`.

This avoids embedding a transient branch in the checker: the only lane switch
is the tracked index pointer; the checker derives branch and status from the
pointed authority document.

## Staging exclusions

Stage only the five routers plus the four recovery authority documents. Reject
the staged set if it contains either pre-existing dirty tracked file:

```text
docs/hardware/device-build-registry.md
scripts/agent/pio-build.sh
```

Also exclude `.devin/`, `_scratch/`, the Cursor-local plan, unrelated
`artifacts/k1_dual_sync_eval_2026-07-08/*`, and all pre-existing untracked
tool/skill/config files. Use explicit paths; never `git add .`, `git add -A`,
or a directory-wide add.

## Orchestrator re-run

Run after applying and narrowly staging the P-1 patch:

```bash
bash -n scripts/agent/repo-truth.sh &&
bash scripts/agent/repo-truth.sh &&
test "$(git branch --show-current)" = "$(sed -n 's/^branch:[[:space:]]*//p' artifacts/k1_dual_sync_eval_2026-07-08/recovery/recovery-plan.md | head -1)" &&
git ls-files --error-unmatch artifacts/k1_dual_sync_eval_2026-07-08/recovery/recovery-plan.md artifacts/k1_dual_sync_eval_2026-07-08/recovery/task_plan.md artifacts/k1_dual_sync_eval_2026-07-08/recovery/findings.md artifacts/k1_dual_sync_eval_2026-07-08/recovery/progress.md &&
git diff --cached --name-only &&
! git diff --cached --name-only | grep -Ex 'docs/hardware/device-build-registry\.md|scripts/agent/pio-build\.sh'
```

After the docs-only commit, durability additionally requires an explicit,
successful push of that exact commit and:

```bash
git rev-parse --abbrev-ref --symbolic-full-name '@{upstream}' &&
test "$(git rev-parse HEAD)" = "$(git rev-parse '@{upstream}')" &&
git ls-remote --exit-code --heads origin lane/dual-sync-phase0
```

Until both checks pass, the appropriate claim is `NOT_VERIFIED`: local routing
may be corrected, but another tool or checkout cannot reliably discover it.
