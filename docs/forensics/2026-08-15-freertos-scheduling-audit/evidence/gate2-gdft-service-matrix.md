# Gate 2 GDFT service-contract matrix checkpoint

Date: 2026-08-15
Branch: `feat/k1-scheduling-generation-hardening`
Parent checkpoint: `4f0630315eaf852be3da4241124aeb9788ab309f`

## Verdict

**Host/source/build matrix: PASS.**

**Gate 2 behaviour selection: NOT CLOSED.** The B489A500 bench is disconnected,
the production F887A500 is absent, and no Captain-confirmed audible real-music A/B has
been run. No candidate is promoted to the production environment by this checkpoint.

## Controlled variable

All three environments inherit the same B489A500 scalar scheduling baseline. Cross40
and cross80 add exactly one compile-time flag; the runtime crossover command and its
telemetry remain disabled.

| Environment | Crossover | Executed Goertzel inner-loop iterations | Bin-0 window | Text/data/BSS/total bytes |
|---|---:|---:|---:|---:|
| `k1_bench_scheduling_baseline_probe` | 0 | 34,254 | 1,956 samples / 152.813 ms | 520270 / 196856 / 1363005 / 2080131 |
| `k1_bench_scheduling_gdft_cross40_probe` | 40 | 18,550 | 978 samples / 76.406 ms | 520290 / 196856 / 1363005 / 2080151 |
| `k1_bench_scheduling_gdft_cross80_probe` | 80 | 17,109 | 978 samples / 76.406 ms | 520278 / 196856 / 1363005 / 2080139 |

The iteration counts cover bins 0..70, which are the bins that execute the resonator at
12.8 kHz. Bins 71..79 are rejected before the inner loop by
`k1_gdft_nyquist_safe_bin_hi()`. The older 34,484 full-table sum is therefore not a
truthful service-demand count for current `process_GDFT()`.

Cross40 retains the current larger windows from bin 40 upward, but introduces a window
step at the boundary: bin 39 is 102 samples and bin 40 is 194. Cross80 applies the
legacy x2 divisor to all 80 configured bins; bin 40 is 97 samples. These geometry facts
are product trade-offs, not a basis for perceptual acceptance.

Cross0 and cross40 retain the same worst representable centre error, 154.041 Hz at bin
67, and the same 609.524 Hz maximum resolution cell; cross40 doubles the minimum cell
width from 6.544 to 13.088 Hz. Cross80 widens the maximum cell to 1,280 Hz and worsens
the maximum representable centre error to 248.397 Hz at bin 70. Cross80 is therefore a
compute-leading, product-risk candidate, not a presumed semantic improvement.

## Commands and results

```bash
python3 -m pytest -q \
  tests/test_scheduling_gdft_service_matrix.py \
  tests/test_dev_instrumentation_boundary.py \
  tests/test_scheduling_trace_integration.py \
  tests/test_gdft_center_honesty.py \
  tests/test_nyquist_bin_hygiene_static.py \
  tests/test_spectral_honesty.py \
  tests/test_gdft_int64_magnitude.py \
  tests/test_gdft_int64_recurrence.py \
  tests/test_gdft_harness_schema_static.py \
  tests/test_golden_master.py \
  tests/test_rate_consistency.py \
  tests/test_onset_beat_replay.py \
  tests/test_semantic_state_replay.py \
  tests/test_chord_saliency_replay.py
```

Result: `107 passed`.

```bash
pio run -e k1_bench_scheduling_baseline_probe
pio run -e k1_bench_scheduling_gdft_cross40_probe
pio run -e k1_bench_scheduling_gdft_cross80_probe
```

Result: all three builds passed. They were built from the same dirty checkpoint with
provenance parent `4f063031`; no upload occurred.

The final whole-repository host run passed `1148` tests with one existing explicit skip.
Independent adversarial review accepted the matrix configuration and host identity guard
after two oracle repairs: resolved configuration rather than local section text, followed
by ordered define/duplicate checking rather than set comparison. That review independently
keeps live service and perception `NOT_VERIFIED`; see
`gate2-matrix-independent-review.md`.

## Remaining acceptance work

1. Reconnect and identity-verify B489A500.
2. Capture paired service, backlog and sample-age distributions for all three candidates.
3. With Captain-confirmed audible real music, compare novelty, onset, tempo, chord and
   visible musical response under a frozen fixture.
4. Select one candidate only if both compute and product contracts pass. Otherwise keep
   production cross0 and reopen cadence/feature requirements as required by the plan.

No priority, task topology, hop size, sample rate, AP-input default, production GDFT flag,
radio, persistence or calibration behaviour changed.
