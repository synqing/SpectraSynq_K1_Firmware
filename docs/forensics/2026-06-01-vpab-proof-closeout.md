---
abstract: "VPAB proof closeout for the parallel K1 closeout wave. Latest available VPAB-capable logs show healthy diagnostic capture counters, but remain self-shadow instrumentation smoke rather than final-byte visual-memory proof. Render-budget breaches remain visible."
evidence-tier: "static-and-existing-runtime-log-review"
created: "2026-06-01"
---

# VPAB Proof Closeout

## Scope

[FACT] This closeout is read-only with respect to firmware and hardware. No
serial monitor, upload, erase, calibration, or device-write action was used.

[FACT] Sources inspected:

- `scripts/regression-harness/vpab_gate.py`
- `tests/test_vpab_gate.py`
- latest VPAB-capable logs under `docs/forensics/runtime-evidence/`

[FACT] The current `2026-06-01` Smart Auto evidence files do not contain
`VPAB,`, `VPAB_RECORDS:`, or `VPAB_DUMP:` rows. The latest useful
VPAB-capable logs are still the `2026-05-28` VPABB/context captures.

## Gate Semantics Checked

[FACT] `vpab_gate.py` now separates:

- final-byte visual proof: `visual_gate`
- diagnostic capture health: `diagnostic_capture`
- render budget: `render_budget`

[FACT] By default, `render_us > 2000` is reported under `render_budget` as a
warning, not hidden and not folded into final-byte visual proof. With
`--strict-render-budget`, the same `render_us` breaches fail the overall gate.

[FACT] `self_shadow` or `memory_metrics=absent` rows are rejected as
instrumentation smoke unless `--allow-self-shadow-smoke` is explicitly supplied.

## Commands Run

| Command | Result |
|---|---|
| `python3 -m pytest tests/test_vpab_gate.py -q` | PASS: `12 passed` |
| `rg -n '^VPAB,\|^VPAB_RECORDS:\|^VPAB_DUMP:' docs/forensics/runtime-evidence/2026-06-01*.log docs/forensics/runtime-evidence/2026-06-01*.md` | No matches |
| `python3 scripts/regression-harness/vpab_gate.py --summary <2026-05-28 VPAB-capable log>` | FAIL for inspected latest logs |
| `python3 scripts/regression-harness/vpab_gate.py --strict-render-budget --summary docs/forensics/runtime-evidence/2026-05-28-k1-smart-edge-vpabb-context-product-floor-v2.log` | FAIL: 73 render failures |

## Current Verdict

| Evidence lane | Verdict | Reason |
|---|---|---|
| Final-byte visual proof | `blocked-pending-capture` | Latest useful rows are `scenario=self_shadow` and/or `memory_metrics=absent`; they prove parser/capture smoke, not real visual-memory proof |
| Diagnostic capture health | `passed-for-inspected-logs` | Inspected summaries report zero dropped/corrupt/overflowed rows |
| Render budget | `open-warning-default-strict-failure` | Latest logs still contain `render_us > 2000`; cleanest latest max observed by the worker was `2803us` |

[INFERENCE] The current logs should not be consumed as runtime final-byte visual
proof. A new VPAB runtime log with non-self-shadow A/B rows and memory metrics
present is required before the VPAB lane can unblock VME/final-byte promotion.

[INFERENCE] The render-budget lane remains open. Existing trace-dev notes say
the current VPAB `render_us` scalar can mix effect code cost with wall-envelope
or scheduling-gap semantics, but that does not make the warning safe to ignore.

## Changelog

| Date | Change |
|---|---|
| 2026-06-01 | Added VPAB proof closeout from parallel sandbox lane B. |
