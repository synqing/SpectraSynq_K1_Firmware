# Candidate 5bb142bc (Modernes C++ session, branch mcpp/next-phase-fixes, parent a6bad318) — declared before running
Expected: G1–G4 PASS (exit 0) on --profile fe --mode 32, --profile scenario --mode 32 and --mode 18, matching a6bad318.
Reason: its receiver change (over-long ':' text line stays interactive) does not touch the PRSM frame path; set_mode/mode-request and look-table changes act outside prepared playback.
Any non-PASS is a finding against 5bb142bc.
