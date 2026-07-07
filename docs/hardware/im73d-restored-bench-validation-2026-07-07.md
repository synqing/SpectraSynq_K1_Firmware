# IM73D Restored Bench Validation - 2026-07-07

## Verdict

The bench K1 is restored and validated on the **bench-reference firmware LED
map** with the IM73D PDM mic path active.

This closes the post-incident bench recovery validation for `k1_bench_im73d`.
It does **not** prove `k1_prod_im73d`, because `k1_prod_im73d` is the main/prod
LED-map env (`6/7`) while this restored bench validation is the bench-reference
LED-map env (`4/5`). Captain confirms both K1s are identical hardware; env
choice is configuration, not a physical hardware split.

## Scope

Bench target:

- USB serial/MAC: `B4:3A:45:A5:89:B4`
- Chip: `B489A500`
- Port during run: `/dev/cu.usbmodem1401`
- Build proved before validation: `BUILD: version=40103 git=f2f7c45 env=k1_bench_im73d`
- Mic path: IM73D PDM on `clk13/din12/LR14`
- LED path: bench-reference firmware GPIO map (`GPIO4/5`)

Main K1 was present only as SPH reference/control:

- USB serial/MAC: `B4:3A:45:A5:87:F8`
- Port during run: `/dev/cu.usbmodem12401`
- Not flashed.

## Safety Boundary

- Controlled track: `/Users/spectrasynq/Downloads/Tiësto-TheBusiness.mp3`
- Extracted stimulus window: offset `35 s`, duration `30 s`
- Full AP/raw capture volumes: `45`, `60`, `75`
- Repeats: 2 music repeats per volume, 2 quiet repeats
- AGC captures: volumes `45` and `60`, 20 s each
- No `start_noise_cal`
- No `N`/`Y`
- Serial writes were colon-prefixed only
- Pyserial opened with DTR/RTS low
- Mac output volume was restored after each harness run

## Evidence

AP/raw controlled-audio capture:

- `artifacts/im73d_bench_ledproof_2026-07-07/20260707T170922_restored_bench_full_music/summary.json`

AGC headroom captures:

- `artifacts/im73d_bench_ledproof_2026-07-07/20260707T171507_stream_agc_vol45/summary.json`
- `artifacts/im73d_bench_ledproof_2026-07-07/20260707T171632_stream_agc_vol60/summary.json`

## Bench AP / Raw Metrics

Raw pre-conditioning metrics are the decision basis. `max_raw` is retained as
context because it is downstream-conditioned.

| Condition | Usable | Reasons | `max_raw` p90 | raw RMS p90 | raw peak p90 | raw near pct max |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| quiet r1 | yes | none | 290.0 | 14.7 | 21.0 | 0.000 |
| quiet r2 | yes | none | 363.0 | 17.9 | 26.0 | 0.000 |
| music vol45 r1 | yes | none | 7960.0 | 303.3 | 572.0 | 0.000 |
| music vol45 r2 | yes | none | 5263.0 | 185.6 | 378.0 | 0.000 |
| music vol60 r1 | yes | none | 3774.0 | 157.2 | 271.0 | 0.000 |
| music vol60 r2 | yes | none | 405.0 | 18.2 | 29.0 | 0.000 |
| music vol75 r1 | no | `clip_pct_nonzero`, `near_pct_nonzero`, `input_trim_reduced` | 21911.0 | 896.3 | 2053.0 | 0.000 |
| music vol75 r2 | no | `clip_pct_nonzero`, `near_pct_nonzero`, `input_trim_reduced` | 19844.0 | 901.9 | 1895.0 | 0.000 |

Interpretation:

- Quiet baseline is live and non-railed.
- Volumes 45 and 60 produced usable bench captures with `raw_i16_near_pct=0`.
- Volume 75 is a front-end stress/fail condition for this setup. It is useful
  as a loud-guard boundary, but it is not acceptance evidence.
- The full-run repeatability flag is false because the capture set includes
  the rejected volume-75 stress legs and a low volume-60 repeat. The per-run
  quality gate is the relevant acceptance surface here.

## AGC Headroom

The `:stream_agc` gate is green at usable music levels:

| Volume | Bench AGC samples | Band 0 max | Band 1 max | Band 2 max | Band 3 max | All gains < 10 |
| ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 45 | 49 | 1.49 | 1.72 | 1.99 | 1.57 | yes |
| 60 | 45 | 1.47 | 1.62 | 1.84 | 1.55 | yes |

The AGC headroom margin is large: the highest observed bench gain was `1.99`,
well below the `<10` starvation ceiling.

## Corrected R3 State

What this proves:

- The bench-reference firmware LED map is restored and visually confirmed by
  Captain after the accidental `k1_prod_im73d` flash.
- The restored `k1_bench_im73d @ f2f7c45` runtime is alive.
- The IM73D PDM path is active and responds to controlled music.
- Raw pre-conditioning telemetry is non-railed at accepted playback levels.
- AGC gains are healthy at accepted playback levels.

What this does not prove:

- It does not prove `k1_prod_im73d` on the main/prod LED map (`GPIO6/7`).
- It does not authorise flashing `k1_prod_im73d` onto the bench/reference `4/5`
  configuration.
- It does not authorise the `k1_hardware` default flip.

Remaining requirement for production-env proof:

1. Use the existing env that matches the intended LED configuration.
2. Device-prove that selected env before any default flip.
