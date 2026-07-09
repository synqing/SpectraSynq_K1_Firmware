# IM73D DSR_16S Quiet-Only Evidence - 2026-07-06

## Verdict

DSR_16S is not promoted.

The quiet/ambient-only comparison is useful rail-safety and noise-floor evidence,
but it is not a controlled acoustic stimulus or music-response proof. It can
show that the raw telemetry surface is alive and non-railed; it cannot prove the
advertised +2 dB SNR benefit under signal.

Production default remains `DSR_8S` on `k1_bench_im73d`.

## Device State

Bench K1 only:

- USB serial/MAC: `B4:3A:45:A5:89:B4`
- Chip: `B489A500`
- Port during run: `/dev/cu.usbmodem101`
- DSR16 eval flash: `k1_bench_im73d_dsr16 @ bc53ceb`
- Restored flash after eval: `k1_bench_im73d @ bc53ceb`

Main K1 was present as the SPH reference on `/dev/cu.usbmodem1101` but was not
flashed or otherwise modified.

## Safety Boundary

- No speaker playback.
- Harness mode: `--quiet-only`
- Recorded metadata: `no_speaker_playback=true`, `volumes=[]`, `track=null`,
  `stimulus=null`.
- No `start_noise_cal`.
- No `N`/`Y`.
- Serial preflight used only colon-prefixed read-only `:build` and `:dump`.
- Harness opened pyserial with DTR/RTS low.

## Evidence

DSR16 quiet-only:

- `artifacts/im73d_dsr_eval_2026-07-06/20260706T162130_dsr16_quiet_only/summary.json`
- Bench build line: `BUILD: version=40103 git=bc53ceb epoch=1783325710 env=k1_bench_im73d_dsr16`
- Repeatability: `true`
- Bench usable runs: 3/3

Restored DSR8 quiet-only:

- `artifacts/im73d_dsr_eval_2026-07-06/20260706T162406_dsr8_quiet_only_restored/summary.json`
- Bench build line: `BUILD: version=40103 git=bc53ceb epoch=1783326213 env=k1_bench_im73d`
- Repeatability: `true`
- Bench usable runs: 3/3

Raw-metric comparison report:

- `artifacts/im73d_dsr_eval_2026-07-06/dsr8_vs_dsr16_quiet_compare.json`

## Bench Metrics

The comparison uses raw pre-conditioning metrics first, not AP `max_raw` alone.

| Metric | DSR8 mean | DSR16 mean | DSR16/DSR8 | DSR8 max | DSR16 max |
| --- | ---: | ---: | ---: | ---: | ---: |
| `raw_i16_rms` p90 | 23.13 | 18.23 | 0.788 | 24.4 | 21.6 |
| `raw_i16_abs_peak` p90 | 35.00 | 31.67 | 0.905 | 36.0 | 36.0 |
| `raw_i16_near_pct` max | 0.000 | 0.000 | n/a | 0.000 | 0.000 |
| `max_raw` p90 | 487.00 | 440.67 | 0.905 | 501.0 | 501.0 |
| `input_trim` min | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| `clip_pct` p90 | 0.000 | 0.000 | n/a | 0.000 | 0.000 |
| `near_pct` p90 | 0.000 | 0.000 | n/a | 0.000 | 0.000 |
| `peak_pin` p90 | 0.147 | 0.136 | 0.925 | 0.162 | 0.158 |

Quality:

- DSR8: 3/3 usable, no reasons, no warnings.
- DSR16: 3/3 usable, no reasons, one `conditioned_peak_pin_high` warning.

## Interpretation

What this proves:

- The new raw `raw_i16_*` telemetry is present in live AP rows.
- Neither DSR8 nor DSR16 showed raw near-rail risk in quiet/ambient conditions.
- The bench was restored to radio-free DSR8 after the eval.
- DSR16 did not worsen the quiet-room rail/headroom safety envelope.

What this does not prove:

- It does not prove DSR16 improves SNR under music.
- It does not prove DSR16 improves visual responsiveness.
- It does not justify a default flip.

## Next Decision Gate

DSR16 can only be reconsidered after a controlled acoustic stimulus or speaker
playback window is available. The required comparison remains:

1. Same bench K1 by MAC.
2. Same front-end state from `:dump`.
3. Same track/volume/duration/start offset, or a documented calibrated stimulus.
4. Raw `raw_i16_rms`, `raw_i16_abs_peak`, and `raw_i16_near_pct`.
5. Conditioned quality: `input_trim=1.000`, `clip_pct=0.000`, `near_pct=0.000`.
6. Repeatability within the chosen CV threshold.
