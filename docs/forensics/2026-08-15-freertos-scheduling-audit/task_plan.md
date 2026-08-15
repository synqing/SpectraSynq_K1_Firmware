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
| 8. Gate 0: provenance, contracts, deterministic oracle and RED fault battery | complete | independently accepted at `68c9a51e`; 21/21 RED witnesses |
| 9. Gate 1: exact-head AP/VP baseline | in progress — production hardware/music leg externally blocked; bench RMT smoke PASS and AP service RED | admitted quiet/music/crossfade timing evidence |
| 10. Gate 2: GDFT service contract | blocked — corrected complete six-run matrix proves all candidates miss the 6 ms p99 tail margin; Captain rejected 20 s sequential product A/B as inconclusive and requires two simultaneous authorised units for 30–60 min / multiple tracks | measured retain/change decision |
| 11. Gate 3: coherent AP frame and event semantics | dependency-blocked by open Gate 2 | host interleavings + device lock/freshness proof |
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
| Full Gate-1 regression found two diagnostic envs outside the non-shippable name/label contract and a stale serial-safety registry | 1 | Rename the scalar env with the `probe` marker, put the trace label inside its section, regenerate the command literal and blob SHA; focused gate 63/63 PASS |
| Main scheduling trace exceeded internal DRAM by 1200 bytes at link | 1 | Preserve the 64-record ISR rings; reduce only the duplicate serial-export staging buffer to 16 records and drain it iteratively; focused tests 14/14 and main trace link PASS |
| Independent review proved the first CRC could be unrelated to FastLED's submitted bytes | 1 | Remove CRCs from the caller API; hash the actual ESP-IDF payload inside `__wrap_rmt_transmit`; add payload-mutation proof and mark the pre-fix device CRC fields inadmissible |
| First Gate-2 matrix oracle inspected only local INI sections and manifest ownership | 1 | Resolve PlatformIO's effective graph and execute the real upload guard for authorised B489A500 and rejected F887A500 identities |
| Second Gate-2 matrix oracle converted flags to sets, hiding duplicate/conflicting define order | 2 | Preserve the ordered flag list, require exact baseline-plus-one equality and assert one occurrence/value for every decision-critical macro |
| First Gate-2 device upload lost its final acknowledgement at 921600 after writing 100% | 1 | Do not blindly retry; prove running build/chip identity, then hold every matrix environment at the same conservative 460800 transport speed; four subsequent guarded uploads PASS |
| Single-unit 20-second sequential product A/B could not expose meaningful nuance | 1 | Mark inconclusive; require two simultaneous authorised K1 units, different builds, multiple real tracks and 30–60 minutes before product selection |
| Initial 15-second APCAD acquisitions did not finish serial export | 1 | Downgrade all six to partial negative witnesses; make incomplete export fail visibly and non-zero; rerun a complete five-second matrix with a bounded 90-second dump wait and exact begin/done/row reconciliation |
| Bare `pytest` collected vendored ESP-IDF/PlatformIO test trees and stopped on 223 missing vendor dependencies | 1 | Use the canonical project boundary `python3 -m pytest -q tests`; 1,152 passed and 1 skipped |
