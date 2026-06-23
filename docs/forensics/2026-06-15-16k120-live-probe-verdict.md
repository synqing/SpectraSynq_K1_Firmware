# 2026-06-15 16 kHz / 120 / d3 Live Probe Verdict

## Verdict

`16000 / 120 / decim=3` is **not promotable** from the current evidence.

The probe reached the correct compiled timing contract, but the main K1 then
hit repeated task-watchdog resets before any APCAD rows were captured. This
blocks any DSP/product retune work on `16000/120/d3` until the acquisition/AP
loop failure is isolated.

Production remains:

```text
12800 / 96 / decim=3
```

## Probe Scope

| Field | Value |
|---|---|
| Device | Main K1 / 1401 |
| Port | `/dev/cu.usbmodem12201` |
| USB serial | `B4:3A:45:A5:87:F8` |
| Probe env | `k1_ap_frontend_probe_matrix_16000_120_d3_ap0_vp1` |
| Tuple | `16000 / 120 / decim=3` |
| Expected AP cadence | `133.333 Hz` |
| Expected accepted novelty cadence | `44.444 Hz` |
| AP/VP core contract | AP core `0`, VP core `1` |
| Track | `build/audio-semantic-metrics/control-fixtures/control_127bpm_click_44k1.wav` |

No calibration, production DSP tuning, or bench-device flash occurred during
the probe.

## Evidence

Probe evidence:

- `docs/forensics/runtime-evidence/20260615T0920-sample-rate-16k120-probe/ap_cadence_matrix_20260615_092132__summary.json`
- `docs/forensics/runtime-evidence/20260615T0920-sample-rate-16k120-probe/c_16000_120_d3_ap0_vp1_20260615_092106__raw.log`
- `docs/forensics/runtime-evidence/20260615T0920-sample-rate-16k120-probe/c_16000_120_d3_ap0_vp1_20260615_092106__summary.json`

Key runtime facts:

```text
RUNTIME_TIMING_GUARD: timing_ok=1 sample_rate=16000 samples_per_chunk=120
tempo_decim=3 declared_ap_hz=133.333 declared_nov_hz=44.444
response_gain=3.000 dma_desc=3 ap_core=0 vp_core=1 core_ok=1
vp_task_created=1
```

The APCAD classifier could not produce cadence proof because the capture had no
rows:

```text
classification=F_not_yet_decidable
classification_reason=no APCAD rows parsed
row_count=0
APCAD_HEALTH health_ok=0 sample_rate=0 samples_per_chunk=0
```

The raw log contains repeated watchdog/reset markers:

```text
task_wdt: Task watchdog got triggered
IDLE0 (CPU 0)
CPU 0: loopTask
Backtrace:
rst:0xc (RTC_SW_CPU_RST)
```

## Restore Proof

The main unit was immediately restored to `k1_hardware`. A paired production
proof then confirmed both registered K1s were back on production timing:

- `docs/forensics/runtime-evidence/20260615T092202-snappiness-manifest.json`
- `docs/forensics/runtime-evidence/20260615T092202-snappiness-main-1401.log`
- `docs/forensics/runtime-evidence/20260615T092202-snappiness-bench-12201.log`

Restore proof summary:

| Device | Tuple | Gain | Calibration | Rows |
|---|---|---:|---|---|
| Main 1401 | `12800/96` | `3.0` | `CAL_SOURCE=config`, `CAL_VALID=1`, `DC=-4698`, `SSL=176` | AP `91`, VP `79` |
| Bench 12201 | `12800/96` | `1.0` | `CAL_SOURCE=config`, `CAL_VALID=1`, `DC=-828`, `SSL=180` | AP `79`, VP `79` |

Crash-marker grep on the restore logs returned zero matches.

## Decision Boundary

This result does **not** prove that 16 kHz is impossible for K1 hardware. It
does prove that the current full AP probe build at `16000/120/d3` is not stable
enough for promotion or product tuning.

The next legitimate 16 kHz research step is acquisition isolation: disable or
stub enough AP/visual work to decide whether the watchdog is caused by I2S/DMA
acquisition, GDFT/AP compute load, diagnostic capture overhead, or task-yield
behaviour.

## Follow-Up

The acquisition-isolation step has now been run:

- `docs/forensics/2026-06-15-16k120-acquisition-isolation-verdict.md`
- `docs/forensics/runtime-evidence/20260615T0937-sample-rate-16k120-acq-probe-yield/`

That follow-up captured `2000` acquisition-only rows at `16000/120` with
`i2s_status=0` for every row, no byte mismatches, no frame gaps, and no
crash-marker matches after adding a yield inside the APCAD serial dump. The
remaining blocker is therefore full AP DSP compute/yield budget, not basic I2S
byte integrity.
