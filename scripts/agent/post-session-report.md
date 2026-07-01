# Post-Session Report

Fill this at session end or on blocker. Decision-grade — no log dumps, no
file:line spam. Audit trail goes to git, changelogs, evidence manifests.

---

## Session Report

```text
session_objective:       <one-sentence goal of this session>
branch_head_at_start:    <branch> @ <short SHA>
branch_head_at_end:      <branch> @ <short SHA>
files_changed:           <list, or "none">
commands_run:            <verification commands only, with exit status>
validation_results:      <pytest: pass/fail; build: pass/fail/n-a; gate: pass/fail>
evidence_captured:       <paths to logs / manifests / captures, or "none">
blockers:                <unresolved issues, or "none">
generated_files_ignored: <confirm last-bootstrap.json / repo-truth-report.json stayed ignored>
safety_constraints:      <confirm: no upload, no flash, no erase, no serial-write, no unscoped edits>
next_recommended_action: <exact next step, or "await Captain decision: <decision>">
```

## Quality bar

- State what was done, what was verified, and what is still open.
- Distinguish "verified by gate" from "verified by device eyes-on".
- If evidence is missing, say so. Do not paper over gaps.
- If HEAD advanced during the session, state whether Devin caused it or observed it.
- Next action must be a concrete prompt or a framed Captain decision
  (current state → decision required → options → recommended → blast radius →
  default if no override).
