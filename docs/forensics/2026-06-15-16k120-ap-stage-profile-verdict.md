# 2026-06-15 16 kHz / 120 / d3 AP Stage-Profile Verdict

## Verdict

`16000 / 120 / decim=3` is blocked first by the **tempo ACF/update stage** in
the full AP path.

The staged probes show:

- acquisition-only is clean;
- GDFT alone is heavy but survivable;
- novelty is negligible;
- snapshot, onset, and saliency still hold the declared AP cadence;
- adding tempo update drops AP cadence from `133.33 Hz` to about `123.15 Hz`
  and accepted novelty cadence from `44.44 Hz` to about `41.04 Hz`, with clean
  I2S and no byte mismatches.

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
| Chip ID | `F887A500` |
| Tuple | `16000 / 120 / decim=3` |
| AP/VP core contract | AP core `0`, VP core `1` |
| Capture dirs | `docs/forensics/runtime-evidence/20260615T0950-sample-rate-16k120-stage-probes/`, `docs/forensics/runtime-evidence/20260615T1000-sample-rate-16k120-tail-stage-probes/` |

Stage codes:

| Stage | Code | Stop point |
|---|---:|---|
| acquisition | `1` | after `calculate_vu()`, before `process_GDFT()` |
| GDFT | `2` | after `process_GDFT()` |
| novelty | `3` | after `calculate_novelty()` |
| snapshot | `4` | after `sb_audio_snapshot_update()` / read |
| onset | `5` | after `sb_onset_beat_update()` |
| saliency | `6` | after `sb_musical_saliency_update()` |
| tempo | `7` | after `sb_tempo_update()` |

## Evidence Matrix

| Probe | Rows | Stage | AP Hz | NOV Hz | I2S bad | Byte mismatch | GDFT median | Novelty median | Total median | Total p95 | Crash markers |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| acquisition | `2000` | `1` | `133.382` | n/a | `0` | `0` | `0 us` | `0 us` | `6690.5 us` | `13500 us` | zero after serial-yield fix |
| GDFT | `2000` | `2` | `133.356` | n/a | `0` | `0` | `3745 us` | `0 us` | `6461 us` | `9705 us` | zero |
| novelty | `2000` | `3` | `133.347` | n/a | `0` | `0` | `3688 us` | `29 us` | `6567.5 us` | `8959.1 us` | zero |
| snapshot | `1334` | `4` | `133.327` | n/a | `0` | `0` | `3761 us` | `29 us` | `6188.5 us` | `9300 us` | zero |
| onset | `1334` | `5` | `133.327` | n/a | `0` | `0` | `3713 us` | `29 us` | `6248.5 us` | `8400.35 us` | zero |
| saliency | `1334` | `6` | `133.313` | n/a | `0` | `0` | `3856 us` | `31 us` | `6351 us` | `8610.35 us` | zero |
| tempo | `1232` | `7` | `123.149` | `41.044` | `0` | `0` | `3740 us` | `31 us` | `5836.5 us` | `11265.7 us` | zero |

The tempo-stage classifier reports `B_ap_compute_overrun`; that is consistent
with the metric shape: I2S reads return immediately (`i2s_read_elapsed_us`
median `34 us`) while the AP cadence is slow and p95 loop time exceeds the
`7.5 ms` frame period.

## Full-AP WDT Correlation

The earlier full-AP probe still produced task-watchdog resets before usable
APCAD rows. Rebuilding the same non-shippable full probe and resolving the
captured WDT addresses maps the failure into:

```text
sb_tempo_update(SBAudioSnapshot const&) at audio/sb_tempo.cpp:529 / :1227
process_GDFT() at audio/GDFT.h:103
low_pass_array(...) in utilities.h:62, called from audio/GDFT.h:225
sbv2_band_flux(...) at audio/sb_onset_beat.cpp:137
sbv2_run(...) at audio/sb_onset_beat.cpp:266
sb_onset_beat_update(...) at audio/sb_onset_beat.cpp:550
```

The stage probes refine that stack: GDFT, novelty, snapshot, onset, and
saliency are survivable in isolation at 16 kHz/120; adding tempo is where the
captured live cadence collapses.

## Production Restore Proof

After the staged probes, main 1401 was restored to `k1_hardware`. Paired
production proof:

- `docs/forensics/runtime-evidence/20260615T100859-snappiness-manifest.json`
- `docs/forensics/runtime-evidence/20260615T100859-snappiness-main-1401.log`
- `docs/forensics/runtime-evidence/20260615T100859-snappiness-bench-12201.log`

Restore proof summary:

| Device | Tuple | Gain | Calibration | Rows | Crash scan |
|---|---|---:|---|---:|---|
| Main 1401 | `12800/96` | `3.0` | `CAL_SOURCE=config`, `CAL_VALID=1`, `DC=-4698`, `SSL=176` | AP `96`, VP `79` | zero matches |
| Bench 12201 | `12800/96` | `1.0` | `CAL_SOURCE=config`, `CAL_VALID=1`, `DC=-828`, `SSL=180` | AP `79`, VP `79` | zero matches |

The manifest reports `timing_parity=true`.

After this source/evidence slice was committed as
`6d5b476 test(audio): profile 16k AP stage budget`, both registered K1s were
flashed from that committed HEAD:

- main 1401: `k1_hardware` on `/dev/cu.usbmodem12201`
- bench 12201: `k1_bench_reference` on `/dev/cu.usbmodem12401`

Committed-deployment proof:

- `docs/forensics/runtime-evidence/20260615T101430-snappiness-manifest.json`
- `docs/forensics/runtime-evidence/20260615T101430-snappiness-main-1401.log`
- `docs/forensics/runtime-evidence/20260615T101430-snappiness-bench-12201.log`

Committed-deployment proof summary:

| Device | Commit/env | Tuple | Gain | Calibration | Rows | Crash scan |
|---|---|---|---:|---|---:|---|
| Main 1401 | `6d5b476` / `k1_hardware` | `12800/96` | `3.0` | `CAL_SOURCE=config`, `CAL_VALID=1`, `DC=-4698`, `SSL=176` | AP `98`, VP `79` | zero matches |
| Bench 12201 | `6d5b476` / `k1_bench_reference` | `12800/96` | `1.0` | `CAL_SOURCE=config`, `CAL_VALID=1`, `DC=-828`, `SSL=180` | AP `88`, VP `79` | zero matches |

## Decision Boundary

Closed:

- Basic 16 kHz I2S/DMA acquisition is clean under the isolated probe.
- GDFT at 16 kHz/120 costs about `3.7-3.9 ms` median and is a large steady
  budget item, but it does not by itself collapse AP cadence.
- `calculate_novelty()` is not the blocker.
- snapshot, onset, and musical saliency are not the first hard blocker in this
  staged run.
- `sb_tempo_update()` / ACF update is the first demonstrated 16 kHz AP cadence
  blocker.

Still open:

- 16 kHz promotion remains blocked.
- Next engineering slice must reduce or amortise tempo ACF/update cost before
  another full-AP 16 kHz promotion probe.
- GDFT cost still needs attention for margin, but tempo is the immediate
  gating constraint.

## Next Slice

Implement a non-shippable 16 kHz tempo-cost experiment that preserves product
semantics at `12800/96` and tests one of these isolated changes at `16000/120`:

1. amortise `sb_compute_acf_salience()` so it runs less often than every
   accepted novelty emit;
2. reduce or bound the ACF lag window under the stage probe;
3. profile `sb_compute_acf_salience()` separately from `sb_update_tempo()` and
   flywheel work before choosing a production algorithmic change.

Do not retune product DSP or promote 16 kHz until a full AP/VP probe holds
declared AP and novelty cadence without crash markers.

## Follow-Up: Tempo Internal Profile

The follow-up internal tempo profile is recorded in
`docs/forensics/2026-06-15-16k120-tempo-internal-profile-verdict.md`.

It narrows the stage-7 blocker from broad `sb_tempo_update()` cost to
`sb_compute_acf_salience()` specifically:

- `tempo_acf_elapsed_us` median `4736 us`, p95 `4876 us`;
- `tempo_emit_elapsed_us` median `5422 us`, p95 `5617 us`;
- AP cadence `120.124 Hz`, novelty cadence `40.056 Hz`;
- `i2s_not_ok_count=0`, `bytes_mismatch_count=0`, `frame_gap_count=0`;
- zero crash-marker matches in raw/APCAD logs.

The next slice should therefore test ACF amortisation or bounding under a
non-shippable 16 kHz probe before considering any product retune.
