# Gate 2 lane-4 exact GDFT service probe

Date: 2026-08-15
Task: FRTOS-28
Implementation base: `2c0db532`
Verdict: **HOST-EXACT REUSABLE PROBE; DEVICE SERVICE ADMISSION RED**

## Decision

The prior scalar, cross40 and cross80 matrix proved that changing window geometry
alone does not meet the pre-registered 6 ms AP active-work p99 ceiling. This
implementation therefore tests a different, reversible hypothesis: preserve every
current direct Goertzel recurrence and result, but expose four independent recurrence
chains to the compiler while loading their common sample-age prefix once.

This is a non-shippable B489A500 probe, not a production default. The host phase did
not upload it. A later identity-guarded B489A500 device screen is recorded below; it
rejects promotion under the existing Gate-2 admission rules.

## Implementation contract

`K1_GDFT_LANE4_PROBE=1` selects the candidate. Without that flag, the existing scalar
loop remains verbatim under the `#else` branch.

For each ascending group of up to four Nyquist-safe bins:

1. Cache each bin's `coeff_q14`, `block_size`, `q1` and `q2` in lane-local state.
2. Set `common_prefix` to the smallest block size in the group.
3. For sample ages `0..common_prefix-1`, load the sample once and advance all live
   lanes with the current int64 multiply, arithmetic right shift by 14, input shift by
   6 and `q2=q1; q1=q0` order.
4. Execute each bin's residual tail in its original ascending sample-age order.
5. Commit magnitude, normalisation and EMA in ascending bin order using the current
   int64 magnitude expression and unchanged post-transform operations.
6. Zero the same above-Nyquist canvas bins as the scalar path.

The candidate deliberately rejects builds without both current int64 GDFT flags and
rejects spectral windowing. It preserves the optional `ENABLE_GDFT_HARNESS` q0-range
counter at the same post-recurrence-expression site. No task, mutex, priority, cadence,
hop, sample rate, DMA, bin, publication or semantic change is present.

## Exactness proof

`tests/test_gdft_lane4_exact_probe.py` compiles the real firmware GDFT translation
unit twice with the current 12.8 kHz / 96 / d3 / int64 contract: scalar, then lane-4.
Comparison has no float tolerance.

- Existing GDFT golden-oracle fixture: complete stdout byte equality.
- Exact-state differential: 120 frames covering four silence frames, twelve sustained
  440 Hz resonance frames, nine adversarial histories, 24 deterministic random
  histories, and one tone history for every one of the 71 Nyquist-safe bins.
- The same 120-frame exact-state differential also runs with crossover 41, which
  creates a non-monotonic block-size jump between bins 40 and 41 inside one lane and
  proves the grouping does not assume descending block sizes.
- Compared fields for all 80 canvas bins on every frame: integer raw magnitude; IEEE
  bit patterns of normalised, EMA, final and low-pass arrays; exact `SQ15x16`
  spectrogram storage; novelty; AGC envelope/floor/gate state.
- Result: one-code differences fail the test; observed result was exact equality.

## Operation-count lock

The source-truth frequency model gives 34,254 recurrence steps for the current cross0
geometry over 71 safe bins. Lane grouping preserves all 34,254 steps. It changes only
the number of sample-age loads:

```text
scalar recurrence steps / sample-age loads = 34,254 / 34,254
lane-4 recurrence steps                    = 34,254
lane-4 modelled sample-age loads           = 10,753
eliminated repeated sample-age loads       = 23,501
groups                                     = 18 (17 full + one 3-bin tail)
```

ESP32-S3 object disassembly confirms the compiler inlined the common-prefix kernel
and emitted four independent `mull`/`mulsh` recurrence chains before the residual-tail
loop. It also shows the cost of exposing those chains: the `process_GDFT` stack frame
increases from 112 to 192 bytes and its IRAM section from 2,259 to 2,735 bytes. The
common loop retains three `lane_count` branches and spills lane state to the stack.
This is assembly-shape evidence only; the modelled load reduction does not establish a
net service win. Device timing remains the performance arbiter.

## Build proof

```text
environment = k1_bench_scheduling_gdft_lane4_probe
base         = k1_bench_scheduling_baseline_probe
only delta   = -DK1_GDFT_LANE4_PROBE=1
target       = B489A500 only
build        = PASS
text/data/bss= 520746 / 196856 / 1363553 bytes
host-phase upload = NOT RUN
```

The build emitted the repository's existing `IRAM_ATTR` section-conflict warning for
the `process_GDFT` declaration/definition and the existing volatile-increment warning
in `system.h`; neither was introduced as a new error and linking completed.

## Commands and validation

```bash
python3 -m pytest -vv tests/test_gdft_lane4_exact_probe.py
# 6 passed

python3 -m pytest -q \
  tests/test_gdft_lane4_exact_probe.py \
  tests/test_scheduling_gdft_service_matrix.py \
  tests/test_gdft_int64_recurrence.py \
  tests/test_gdft_int64_magnitude.py \
  tests/test_golden_master.py \
  tests/test_dev_instrumentation_boundary.py
# 35 passed

pio run -e k1_bench_scheduling_gdft_lane4_probe
# PASS

pio run -e k1_bench_scheduling_gdft_lane4_probe -t size
# PASS
```

## Device addendum — complete five-second B489A500 screen

The orchestrator subsequently uploaded the candidate through the identity guard to
the authorised bench K1 only and ran the same bounded APCAD procedure as the corrected
v3 matrix. The two captures are complete and admissible:

| Fixture | Begin | Rows | Done | Drops begin/done | AP Hz | Active median / p95 / p99 | Active >7.5 ms | GDFT median / p95 / p99 | Newest-to-publish p99 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| no host playback | 631 | 631 | 631 | 0 / 0 | 126.08 | 6,246 / 8,449.5 / 8,622.9 us | 179 | 4,849 / 5,000.5 / 5,015.7 us | 8,555.7 us |
| Captain-confirmed real music | 632 | 632 | 632 | 0 / 0 | 126.30 | 6,305.5 / 8,407 / 8,589.76 us | 173 | 4,896 / 4,999 / 5,013.76 us | 8,507 us |

Both logs contain exact `APCAD_CAPTURE_BEGIN.count = parsed APCAD rows =
APCAD_CAPTURE_DONE.count`, with device and completion drop counters zero. Both have
zero frame gaps, capture-sequence gaps, timestamp-order failures, timestamp
regressions, I2S failures and byte-count failures. Every row carries sample-time
assumption ID 1 and the effective tuple is 12,800 Hz / 96 samples / d3 x 96 / AP0 /
VP1. Identity is `/dev/cu.usbmodem12401`, USB serial
`B4:3A:45:A5:89:B4` (B489A500).

The no-playback fixture proves that the host launched no player; it is not an acoustic
silence claim. The music fixture used `afplay` with the Captain-confirmed audible
`Anchor Point` track, SHA-256
`02925982cf3900d1925fa0338db8e26432c265f7ca18ee93a06818dd4079a938`.

### Artefact hashes

```text
458cbb5988def91396a0abd1c6d00824e948651d914e7d6189f990dac57395b5  gate2_lane4_no_playback_20260815_172428__apcad.log
df7b0c5c821f95a50ea97eadbf77fc3d09e10bae2416a828c88b83ea67c1ebb0  gate2_lane4_no_playback_20260815_172428__summary.json
6bd60f843f229eab6c381ffba59ea330653c26b0a1956206981da7a8a7650b1b  gate2_lane4_music_20260815_172502__apcad.log
b4e57623a5e1978b04936455ee55eb75386c1d9f88cb520c092d7d6c640c10fb  gate2_lane4_music_20260815_172502__summary.json
```

### Gate-2 disposition

The candidate materially reduces current cross0 GDFT demand, but the governing margin
is complete AP active work, not GDFT median or average cadence. Gate 0 fixes a 7,500 us
arrival period and a 6,000 us active-work p99 ceiling. Both candidate active-work p99
values exceed 8.5 ms, 173–179 frames exceed the arrival period, newest-sample freshness
p99 exceeds 8.5 ms, and measured AP cadence remains roughly 126 Hz rather than the
declared 133.33 Hz. Therefore:

```text
CAPTURE_COMPLETENESS             = PASS
DEVICE_IDENTITY_AND_TUPLE        = PASS
HOST_NUMERIC_EXACTNESS           = PASS
GDFT_INNER_SERVICE_REDUCTION     = OBSERVED
AP_ACTIVE_WORK_P99_MAX_6MS       = FAIL_BOTH_FIXTURES
AP_133HZ_SUSTAINABILITY          = FAIL_BOTH_FIXTURES
LANE4_GATE2_PROMOTION            = REJECT
GATE2_SELECTION                  = BLOCKED_OPEN
GATE3_ENTRY                      = BLOCKED_BY_GATE2
```

This is a clean falsification, not a failed implementation artefact. The exact lane-4
kernel and differential harness remain reusable machinery for future service studies,
but this particular device result does not earn production mutation or Gate-3 entry.

After the screen, the orchestrator restored scalar cross0 on the same authorised
bench. Transcript readback:

```text
BUILD: version=40103 git=2c0db532 epoch=1786786833 env=k1_bench_scheduling_baseline_probe
```

The restored build line has orchestrator-transcript provenance; it is not asserted as
a field inside either APCAD artefact.

## FRTOS-29 independent device review

Independent readback of the two `__apcad.log` files and their parsed summaries accepts
the device addendum and its RED disposition.

- The no-playback artefact has `BEGIN.count = rows = DONE.count = 631`; the music
  artefact has `632 = 632 = 632`. Both begin/done drop counters are zero and both
  summaries declare `capture_complete=true` and `capture_admissible=true`.
- Direct row inspection found one invariant tuple throughout each capture: 12,800 Hz,
  96 samples, DMA descriptor count 3, DMA frame count 96, novelty d3, AP0, VP1,
  32-bit slot width, slot mode 2 and sample-time assumption ID 1. Frame and capture
  sequences are contiguous; every I2S status is zero and every read is 192/192 bytes.
- Independently recomputed SHA-256 values for both APCAD logs and both summaries match
  the four hashes recorded above exactly.
- Parser-derived device metrics match the receipt exactly. No playback measured
  126.0756 Hz, active p99 8,622.9 us, GDFT p99 5,015.7 us and freshness p99
  8,555.7 us. Real music measured 126.3010 Hz, active p99 8,589.76 us, GDFT p99
  5,013.76 us and freshness p99 8,507 us. The independently counted active-work
  overruns above 7,500 us are 179 and 173 respectively.

The corrected complete scalar-cross0 captures are an admissible directional baseline.
Between their `35de4e53` source checkpoint and this probe's `2c0db532` implementation
base, the only tracked runtime-build-area difference was a conservative upload-speed
setting; no application or GDFT source changed. Relative to scalar cross0, lane-4
reduced GDFT p99 by 33.0% without playback and 34.0% with music, while active-work p99
fell by 20.3% and 27.3% and measured AP cadence rose by 30.2% and 36.0%. The optimisation
hypothesis therefore produced a real service reduction, but not enough to satisfy the
gate.

The final disposition is consequently correct:

```text
INDEPENDENT_CAPTURE_ADMISSION       = PASS
INDEPENDENT_HASH_RECONCILIATION     = PASS
SCALAR_BASELINE_COMPARISON          = PASS_DIRECTIONAL
LANE4_SERVICE_REDUCTION             = CONFIRMED
AP_ACTIVE_WORK_P99_MAX_6MS          = FAIL_BOTH_FIXTURES
AP_ARRIVAL_PERIOD_7P5MS             = FAIL_BOTH_FIXTURES
LANE4_GATE2_PROMOTION               = REJECT
GATE2_SELECTION                     = BLOCKED_OPEN
GATE3_ENTRY                         = BLOCKED_BY_GATE2
```

One provenance boundary does not weaken the negative decision: the raw APCAD sessions
record device identity and `VERSION: 40103`, but do not themselves encode the candidate
Git SHA or PlatformIO environment. Candidate-image attribution therefore relies on the
orchestrator's guarded upload transcript. Even without that attribution, both complete
captures independently fail the service ceiling and arrival-period contract, so they
cannot be used to promote lane-4 or open Gate 3.
