# 2026-06-10 Current K1 Snappiness Telemetry Verdict

Status: partial but decisive for the measured AP/VP telemetry question.

## Evidence

| Run | Manifest | Result |
| --- | --- | --- |
| 20260610T204541 | `docs/forensics/runtime-evidence/20260610T204541-snappiness-manifest.json` | Successful 30 s paired capture, but invalid for direct snappiness comparison because 1401 applied mode 22 while 12201 stayed mode 18. |
| 20260610T204719 | `docs/forensics/runtime-evidence/20260610T204719-snappiness-manifest.json` | Mode-locked paired capture: both devices at 12800 / 96, both Smart applied mode 18, Smart Assist off. Capture ended early when 12201 serial dropped with `SerialException: write failed: [Errno 6] Device not configured`. |

`lsof` after the drop showed Cursor holding `/dev/tty.usbmodem12201`, so the long 12201 CDC capture path was not single-owner and should not be extended without releasing Cursor from the port.

## Device Identity

| Device | Port | Expected chip | Observed chip | Firmware |
| --- | --- | --- | --- | --- |
| 1401 | `/dev/cu.usbmodem1401` | `F887A500` | `F887A500` | `40103` |
| 12201 | `/dev/cu.usbmodem12201` | `B489A500` | `B489A500` | `40103` |

## Locked Mode 18 Results

From `20260610T204719-snappiness-manifest.json`:

| Metric | 1401 | 12201 | Interpretation |
| --- | ---: | ---: | --- |
| `CONFIG.SAMPLE_RATE` | 12800 | 12800 | Timing parity. |
| `CONFIG.SAMPLES_PER_CHUNK` | 96 | 96 | Timing parity. |
| `SMART_APPLIED_MODE` last | 18 | 18 | Mode parity achieved. |
| AP rows | 14 | 11 | Partial capture, enough for a directional runtime check. |
| VP rows | 13 | 10 | Partial capture, enough for a directional runtime check. |
| `peak_scaled` mean | 0.529429 | 0.294909 | 1401 had stronger mean AP drive in this window. |
| `max_raw` mean | 966.0 | 811.636364 | 1401 had higher mean AP raw activity in this window. |
| `render_us` mean | 593.384615 | 2184.8 | 1401 VP render was much faster on paper. |
| `render_us` last | 597 | 2098 | Same direction at the end of capture. |
| `render_max` last | 2292 | 5603 | 12201 had the larger VP render max. |
| DC / SSL | `-4994 / 259` | `-900 / 479` | DC baselines differ, but both calibrations were valid. |

## Verdict

The current telemetry does **not** support "12201 is snappier than 1401" as a lower-render-time or stronger-AP-drive claim.

In the only mode-parity capture achieved before the 12201 serial endpoint dropped, 1401 was:

- faster in VP timing (`render_us` mean 593 us vs 2185 us);
- stronger in mean AP drive (`peak_scaled` mean 0.529 vs 0.295);
- on the same DSP timing contract (`12800 / 96`);
- on the same applied mode (`18`);
- with Smart Assist off on both devices.

If 12201 still looks snappier by eye, the current measured evidence points away from raw VP render speed and away from weaker 1401 AP drive. The next valid capture requires releasing Cursor's hold on `/dev/tty.usbmodem12201` before another long paired run.

