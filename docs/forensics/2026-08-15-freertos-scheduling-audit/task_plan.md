# Scheduling hardening implementation

## Goal

Implement and verify the complete K1 scheduling hardening Gate 0-8 programme under
Captain's 2026-08-15 unrestricted implementation authority.

## Constraints

- Current source and on-disk lane authority outrank historical evidence.
- Captain's new directive authorises scheduling-source mutation after Gate 0; the
  separate AP-input P4 slot/health promotion remains open.
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
| 7. Activate implementation authority and branch routing | complete | active handover; repo-truth PASS; commit `82e20197` |
| 8. Gate 0: provenance, contracts, deterministic oracle and RED fault battery | in progress | independently accepted Gate 0 receipt |
| 9. Gate 1: exact-head AP/VP baseline | pending | admitted quiet/music/crossfade timing evidence |
| 10. Gate 2: GDFT service contract | pending | measured retain/change decision |
| 11. Gate 3: coherent AP frame and event semantics | pending | host interleavings + device lock/freshness proof |
| 12. Gate 4: transactional controls and scenes | pending | ordered/state/scene transaction proof |
| 13. Gate 5: causal trace and startup visibility | pending | one identity through RMT completion |
| 14. Gate 6: conditional explicit audio-task A/B | pending | PASS or NOT_REQUIRED receipt |
| 15. Gate 7A/7B: service requests and flash/cache safety | pending | independently closed selected scope |
| 16. Gate 8: one-HEAD integration and promotion | pending | full gates, rollback and Captain sign-off |

## Errors encountered

| Error | Attempt | Resolution |
|---|---:|---|
| Full-history spawn rejected an explicit agent type | 1 | Relaunched with inherited agent type and received an agent id |
| Packaged DOCX renderer lacked `pdf2image` in the selected Python runtime | 1 | Use the skill's documented manual LibreOffice -> PDF -> PNG render path; do not install dependencies |
| Bootstrap repo-truth rejected the implementation branch because `docs/spec-index.md` still named `main`/AP input as current | 1 | Record Captain's new authority in a scheduling handover and atomically update the active branch/lane pointers before source work |
| Source-manifest command was rejected because it used `rm -f` on a temporary glob | 1 | Use a fresh `mktemp -d` manifest directory and create no pre-existing targets |
| First anchored Gate 0 test froze the live source-file count at 537 | 1 | Reject commit `19047912` before acceptance; keep the exact historical population in the provenance artefact and make the reusable manifest test deterministic while allowing later gate source/tests |
