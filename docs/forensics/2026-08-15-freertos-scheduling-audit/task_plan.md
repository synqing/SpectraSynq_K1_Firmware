# Scheduling hardening plan-fold task

## Goal

Fold Captain's post-review recommendations into the reconciled K1 FreeRTOS
execution plan without changing firmware or crossing the active P4 boundary.

## Constraints

- Current source and on-disk lane authority outrank historical evidence.
- Production firmware remains byte-inert.
- The result must distinguish state, discrete events, commands and telemetry.
- No task extraction is an assumed destination.
- Every implementation gate must have an external, fault-evident acceptance gate.

## Phases

| Phase | Status | Output |
|---|---|---|
| 1. Restore authority and reconcile SHAs | complete | provenance ledger |
| 2. Adversarially review publication and command semantics | complete | FRTOS-07 evidence |
| 3. Convert recommendations into gated system design | complete | FRTOS-08 evidence |
| 4. Amend the audit and write the standalone execution plan | complete | Markdown authorities |
| 5. Produce and visually verify the retained-template document | complete | final DOCX; 8/8 pages inspected |
| 6. Run structural/document validation and close proof ledger | complete | current-HEAD host and document gates |

## Errors encountered

| Error | Attempt | Resolution |
|---|---:|---|
| Full-history spawn rejected an explicit agent type | 1 | Relaunched with inherited agent type and received an agent id |
| Packaged DOCX renderer lacked `pdf2image` in the selected Python runtime | 1 | Use the skill's documented manual LibreOffice -> PDF -> PNG render path; do not install dependencies |
