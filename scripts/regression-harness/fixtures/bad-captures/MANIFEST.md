---
abstract: "Gate-0 fault-injection suite for wireless_ab_bench.py validity-admission gates (the HARNESS fault-evidence gate — NOT the K718 battery SoC gate). Frozen real captures (cb1 DOWNLOAD-reset, cb2 USB-wedge) that INVALIDated both BLE-coexistence counterbalanced retests, plus the gate0_selftest synthetic isolators. The hardened bench must mark every bad capture INVALID and admit every valid one. Read before changing the admission gates."
---

# Gate-0 bad-capture fixture set (harness fault-injection)

> **Naming:** "Gate 0" / "GREEN" here = the **harness** fault-evidence selftest.
> This is NOT the **K718/Remoted battery state-of-charge** gate — a separate
> physical lane that stays unresolved unless explicitly closed elsewhere.

Purpose: prove the `wireless_ab_bench.py` validity-admission gates are
**fault-evident** — they reject corrupted captures instead of laundering a
capture-harness / native-USB-JTAG fault into an A/B PASS/FAIL. Run by
`../../gate0_selftest.py`. A human signs Gate 0 off the green result **before**
any counterbalanced BLE retest.

These are VALIDITY gates (does this capture even count?), not the pre-registered
A/B pass/fail thresholds — those are untouched.

## Frozen real evidence (the captures that broke the retests)

| File | Origin | Why INVALID | Caught by |
|---|---|---|---|
| `good_test1_on_1.json` | test1 ABAB, ON run 1 | valid (positive control) | — admitted |
| `bad_cb1_off2_download_reset.json` | cb1 counterbalanced, OFF run 2 | native USB-JTAG dropped to DOWNLOAD mode mid-capture; 36 AP samples + ROM-reset markers | `AP_FLOOR` (U4) + `RESET` (U6); `DOWNLOAD` (U6) with log |
| `bad_cb2_off1_usb_wedge.json` | cb2 redo, OFF run 1 | total USB wedge; identity probe failed; 0 AP samples; `peak_scaled=None` | `FAILURE`+`IDENTITY`+`AP_FLOOR`+`COMPLETENESS` |

`raw_log` is nulled in the vendored copies (the original scratchpad logs are
session-local); the JSON-derived gates reject these without a log. The synthetic
log-gated cases (U3 app-ready, U6 DOWNLOAD-in-log) live inline in
`gate0_selftest.py`.

Each fixture carries a `_gate0: {expect_admitted, expect_reasons}` block the
self-test asserts against — a rejection caught for the *wrong* reason is a
failure too.

## Synthetic isolators (in gate0_selftest.py)

`truncated` (U4 floor) · `no_render` / `peak_none` (U5 completeness) ·
`wrong_device` (U6 identity) · `post_run_dead` (U7 liveness) ·
`no_ap_before_afplay` (U3 app-ready) · `download_in_log` (U6 download marker) ·
`good_minimal` / `app_ready_ok` (positive controls).

## The rule

An **uncaught** bad capture is not a pass — it is a located oracle blind spot.
Widen the gate (add the missed signal) until the suite is GREEN again. Never
relax a gate or delete a check to make a capture pass: that re-opens the
silent-admit hole (the cb1/cb2 failure mode).

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-06-27 | agent:claude-code | Created with the harness-hardening pass: vendored the real cb1/cb2 bad captures + good control as the Gate-0 fixture set; documented expected rejections and the no-relax rule. |
| 2026-06-27 | agent:claude-code | Renamed "Gate-0 battery" → "fault-injection suite / fixture set" + added the naming callout, per Captain: disambiguate from the K718/Remoted battery SoC gate (different lane, not closed here). |
