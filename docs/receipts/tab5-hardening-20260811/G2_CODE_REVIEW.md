# G2 code review — 2026-08-11

**Verdict: APPROVE for the reviewed G2 source/build gate.** No remaining
correctness blocker was found in the final CLAMPED/REJECTED/UNAVAILABLE recovery
change. This is not a claim of device, radio, WDT, or physical-control validation.

Scope: final current uncommitted G2 diff on `fix/tab5-hardening-20260811`, HEAD
`3ed04d7a5ccbba65968698c953f45171b959dbb1`. Final re-review was limited to the
prior pending-state blocker and regressions introduced by its closure.

## Decision evidence

### APPROVED — Non-ACCEPTED deltas fail closed before mutation

`tab5_firmware/src/deck_state_rx.cpp:446-509` decodes and validates the complete
delta batch, then sends every status other than ACCEPTED through `fail_closed()`
at lines 489-495. This occurs before the first mutation at lines 505-506 and
before revision/LIVE advancement at lines 507-509. REJECTED, CLAMPED, and
UNAVAILABLE therefore cannot clear, confirm, or overwrite an uncorrelated newer
pending request.

The former exact-value reconciliation APIs and sheet-bool reject path are absent
from `deck_state.*`, `deck_ui_internal.h`, and `deck_ui_sheets.cpp`, eliminating
the identical-value ABA defect. The receiver harness at
`tab5_firmware/tests/deck_state_rx_transaction_harness.cpp:321-348` proves both
REJECTED and CLAMPED cause recovery without applying state or advancing revision;
the shared `status != ACCEPTED` branch also covers UNAVAILABLE.

Decision/re-run commands:

```bash
cd /Users/spectrasynq/SpectraSynq_K1_Tab5_Hardening && nl -ba tab5_firmware/src/deck_state_rx.cpp | sed -n '446,509p' && nl -ba tab5_firmware/tests/deck_state_rx_transaction_harness.cpp | sed -n '321,348p' && rg -n 'reject_pending|reject_bool' tab5_firmware/src tab5_firmware/include tab5_firmware/tests
```

```bash
cd /Users/spectrasynq/SpectraSynq_K1_Tab5_Hardening && PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider -q tab5_firmware/tests/test_deck_state_rx_transaction.py tab5_firmware/tests/test_tab5_g2_transport_static.py
```

## Validation and method risk

- Independent focused rerun: `7 passed in 0.71s`.
- The parent gate reports the broader targeted suite at `25/25` and a successful
  P4 production build; those results were not independently repeated in this
  final narrow re-review.
- No flash, serial access, radio stress, or on-device WDT validation was performed.
  Those physical/runtime surfaces remain `NOT_VERIFIED` and are not part of this
  source/build approval.
- Repository lane metadata points to an older active branch; the delegated brief
  explicitly selected this isolated checkout, so that mismatch remains a recorded
  method risk rather than approval evidence.

