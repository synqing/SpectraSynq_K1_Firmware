# P4-WIFI6 hop and AP service p99 — 2026-08-22

Chip `0743E200` on `/dev/cu.wchusbserial5AAF2781791` (USB `5AAF278179`). Console UART0 115200, DTR deasserted. Main RPL and bench S3 were not flashed.

## Hop (product binary, then probe)

On `k1_p4_wifi6` @ `65639525` epoch `1787391354`:

- `RUNTIME_TIMING_GUARD: timing_ok=1 sample_rate=12800 samples_per_chunk=96 tempo_decim=3 declared_ap_hz=133.333`
- `:dump` `CONFIG.SAMPLE_RATE: 12800` `CONFIG.SAMPLES_PER_CHUNK: 96` `CHIP ID: 0743E200`
- Boot pinmap: `LED pri=4 sec=5 proto=WS2812 160+160`

Evidence: `hop_dump_65639525.txt`

## AP service p99 (existing `apcad_soak` dump)

Product `k1_p4_wifi6` does not compile that dump. Probe `k1_p4_wifi6_apcad_probe` @ `61787c86` epoch `1787395530` compiles the same G2/G8 handlers. Flash was `k1-flash-verified.sh` on this WCH port only.

`IDENTITY OK: git=61787c86 env=k1_p4_wifi6_apcad_probe epoch=1787395530`

120 s compact soak (`:apcad_soak=120000` then `:apcad_soak_status=1`):

| Field | Value |
|---|---|
| rows | 15999 |
| observed_duration_ms | 119985 |
| sample_rate / chunk / d | 12800 / 96 / 3 |
| meas_ap_hz | 133.333 |
| meas_nov_hz | 44.444 |
| frame_gap / core_bad / i2s_not_ok | 0 / 0 / 0 |
| active_ap_work_p99_low_us | 1824 |
| active_ap_work_p99_high_us | **1856** |
| active_ap_work_max_us | 1904 |
| active_over_7500 | 0 |
| max_consecutive_active_over_7500 | 0 |

Gate is AP service p99 ≤ 8000 µs. Conservative bound `p99_high_us = 1856`. **PASS.**

Raw log: `apcad_soak_61787c86.log`

No `start_noise_cal`. Calibration still `default_invalid`. This is a dump receipt, not a product-look KEEP/KILL.

Product env restored after the soak: `IDENTITY OK: git=61787c86 env=k1_p4_wifi6 epoch=1787395821`.
