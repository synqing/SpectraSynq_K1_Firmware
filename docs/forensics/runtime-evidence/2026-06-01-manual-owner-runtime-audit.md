---
abstract: "Manual-owner runtime audit for Smart Auto on the second bench K1 after guarded current-firmware upload."
evidence-tier: "hardware-runtime"
created: "2026-06-01"
---

# Manual-Owner Runtime Audit

## Scope

[FACT] Target hardware for the runtime audit was the second bench K1:
`/dev/tty.usbmodem1401`, USB serial `B4:3A:45:A5:87:F8`, chip `F887A500`.

[FACT] No calibration, erase, factory reset, or remote publication was run.

[FACT] The first audit attempt exposed a source/runtime mismatch: the bench K1
was still running firmware that marked `secondary_status` as manual owner. The
current canonical source already fixed that behaviour, so a guarded
`k1_hardware` upload was required before the runtime audit could honestly close.

[FACT] Guarded upload command:

```sh
pio run -e k1_hardware -t upload --upload-port /dev/tty.usbmodem1401
```

[FACT] The command exited `0`, and the post-upload identity check returned
`VERSION: 40103` and chip ID `F887A500`.

## Evidence Files

- Pre-upload mismatch log:
  `docs/forensics/runtime-evidence/2026-06-01-manual-owner-runtime-audit-bench-k1.log`
- Post-upload audit log:
  `docs/forensics/runtime-evidence/2026-06-01-manual-owner-runtime-audit-bench-k1-v2.log`

## Post-Upload Results

| Command surface | Expected | Observed |
|---|---|---|
| `smart_scene=auto` baseline | Clears manual owner | `SMART_MANUAL_OWNER_ACTIVE: 0` |
| `secondary_status` | Read-only, does not mark manual owner | `SMART_MANUAL_OWNER_ACTIVE: 0` |
| `edge_status` | Read-only, does not mark manual owner | `SMART_MANUAL_OWNER_ACTIVE: 0` |
| `palette_index=29` | Visual mutation marks manual owner | `SMART_MANUAL_OWNER_ACTIVE: 1` |
| `auto_color_shift=on` | Visual command family marks manual owner before parser rejection | `SMART_MANUAL_OWNER_ACTIVE: 1` |
| `preset=__audit_invalid__` | Preset command family marks manual owner before parser rejection | `SMART_MANUAL_OWNER_ACTIVE: 1` |
| `edge_strength=0.650` | Edge visual mutation marks manual owner | `SMART_MANUAL_OWNER_ACTIVE: 1` |
| `vp_wave_shift=__audit_invalid__` | VP wave command family marks manual owner before parser rejection | `SMART_MANUAL_OWNER_ACTIVE: 1` |
| final `smart_scene=auto` | Clears manual owner | `SMART_MANUAL_OWNER_ACTIVE: 0` |

## Verdict

[FACT] Manual-owner runtime audit passed on the flashed second bench K1 for the
tested read-only, visual mutation, edge, VP wave, and Smart scene control
surfaces.

[INFERENCE] This closes the manual-owner audit for the current Smart Auto demo
surface on the second bench K1. It does not prove every possible typed command
or every future serial command family.

## Changelog

| Date | Change |
|---|---|
| 2026-06-01 | Added post-upload manual-owner runtime audit closeout. |
