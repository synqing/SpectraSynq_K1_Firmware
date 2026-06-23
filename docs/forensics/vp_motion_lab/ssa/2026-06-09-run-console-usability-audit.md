# VPML Run Console Usability Audit - 2026-06-09

Task ID: `VPML-RUN-CONSOLE-USABILITY-AUDIT-2026-06-09`

## Verdict

From the visual evidence, I observe a functional two-column local console with labelled controls, status cards, and an evidence table. It is **partially usable** for a basic host-side capture launch, but **not yet usable as a dense local engineering console** because the page does not stage identity/run state, does not show live run progress, and makes evidence triage slower than the source data allows.

No hardware or serial port was opened. I rendered the page by GET-only localhost inspection.

## Visual Evidence

- Desktop Playwright snapshot at 1280px showed the Run Capture form at 420px wide and the evidence side at 694px wide. The Capture Index table occupied about 1515px vertical height for 9 captures.
- Mobile Playwright snapshot at 390px showed the form stacking correctly, but the page became about 4922px tall and the Capture Index table alone became about 3334px tall. Individual capture rows were about 340-416px high because long capture IDs and filenames wrap inside a fixed table.
- The latest evidence summary was visible: capture `20260609T220729-vpml-intro-bounce-loop-1401`, byte status `byte clean`, chip `F887A500`, records `48`, mode counts `{"250": 48}`, visual status `eyes on pending`.
- Colour contrast checks passed for declared foreground/background pairs: muted text on white `5.31:1`, OK badge `5.21:1`, warning badge `5.18:1`, bad badge `5.98:1`, action button `7.27:1`.
- Browser console showed only `/favicon.ico` 404; not a functional issue.

## Top 3 Issues And Fixes

1. **Identity/run safety is presented as a single live action, not a staged workflow.**
   - Evidence: the form defaults to a serial port (`scripts/regression-harness/vpml_run_console_server.py:23`), derives defaults from latest evidence (`scripts/regression-harness/vpml_run_console_server.py:267-274`), and renders an enabled `Run Capture` submit button immediately (`scripts/regression-harness/vpml_run_console_server.py:349-384`). POST `/run` directly calls the runner path (`scripts/regression-harness/vpml_run_console_server.py:471-493`).
   - Why it matters: the page-flow spec says device-write controls must be disabled until port plus chip identity are verified (`docs/forensics/vp_motion_lab/2026-06-09-vp-motion-lab-page-flow-spec.md:73-75`) and lists identify/status/capture as separate host-service events (`docs/forensics/vp_motion_lab/2026-06-09-vp-motion-lab-page-flow-spec.md:134-140`).
   - Fix: convert the left panel into a compact staged state strip: `Evidence loaded -> Port selected -> Identity verified -> VPML status OK -> Capture enabled`. Keep `Run Capture` disabled until a same-session identity/status result matches expected chip and VPML availability. Show the verified port, observed chip, timestamp, and last status beside the action.

2. **Run execution is blocking and opaque.**
   - Evidence: `run_capture_from_form()` accumulates lines and only writes/refreshes outputs after `run_vpml_session()` returns or throws (`scripts/regression-harness/vpml_run_console_server.py:121-144`). `do_POST()` returns the next HTML page only after that work completes (`scripts/regression-harness/vpml_run_console_server.py:479-493`). The rendered HTML is static and has no progress region, log stream, cancel/stop affordance, disabled pending state, or retry state (`scripts/regression-harness/vpml_run_console_server.py:276-412`).
   - Why it matters: a dense engineering console should expose current phase and failure point while serial capture is running; otherwise a hung or slow capture looks like a frozen browser. The plan explicitly allows localhost event streaming for this host service, not K1 AP WebSocket (`docs/forensics/vp_motion_lab/2026-06-09-vp-motion-lab-page-flow-spec.md:116`).
   - Fix: run captures as host-side jobs with a job id. Add a live progress/log panel with phases `identity`, `status`, `play`, `capture`, `gate`, `summary`, `dashboard refresh`; include counters, last serial line, elapsed time, cancel/stop, and an `aria-live="polite"` result region.

3. **Evidence triage is too lossy and not dense on small screens.**
   - Evidence: each capture row renders only capture id, byte gate, visual status, programme, summary link, and raw link (`scripts/regression-harness/vpml_run_console_server.py:181-207`). The latest summary cards show only six high-level fields (`scripts/regression-harness/vpml_run_console_server.py:390-405`). However the evidence model already exposes gate flags, stream counts, readbacks, failures, observations, and motion readability (`scripts/regression-harness/vpml_evidence_page.py:634-668`). CSS uses `table-layout: fixed` and the mobile media query stacks grids but does not adapt the table (`scripts/regression-harness/vpml_run_console_server.py:320-333`).
   - Why it matters: the user has to open JSON/log files to answer "why did this fail?" or "which capture is the clean candidate?", and the mobile view becomes a long wrapped filename ledger rather than a dense tool surface.
   - Fix: replace the flat table with a compact evidence matrix: columns for state, programme, chip match, records/chunks, dropped/corrupt/overflow, channel coverage, dark samples, first failure reason, summary/raw links. Add filters for `byte_clean`, `transport_failed`, `missing_files`, and `dark_sample_warning`; on narrow screens render each capture as a two-line row or expandable detail, not a six-column filename table.

## Accessibility Assessment

- Labels are present for form controls, headings are hierarchical, and contrast ratios measured above meet WCAG AA for normal text.
- Remaining accessibility gaps: no skip link, no explicit focus styling beyond browser defaults, no `aria-live` result/progress region for async run feedback, and the long mobile table creates excessive keyboard traversal.

## Required Re-run Command

Host-only render command used:

```bash
python3 scripts/regression-harness/vpml_run_console_server.py --host 127.0.0.1 --port 8877 --evidence-dir docs/forensics/runtime-evidence --dashboard-dir docs/forensics/vp_motion_lab
```

Then open `http://127.0.0.1:8877/` with GET only. Do not POST `/run` during this audit.
