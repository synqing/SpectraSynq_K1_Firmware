# Gate 2 service-demand decomposition and repair design

Date: 2026-08-15
Task: FRTOS-24
Scope: read-only design from the complete `gate2v3_*` matrix and current source
Source checkpoint represented by the captures: `35de4e53`
Current inspected HEAD: `2c0db532`

The application and DSP files cited below are identical between those two checkpoints.
Only `platformio.ini`, the APCAD capture parser and their host tests changed to complete
and record the controlled matrix. The timing rows therefore describe the current AP
implementation, while `2c0db532` is the exact source authority used for this design.

## Decision

```text
ACF_SPREAD_ROOT_FIX                 = STILL_VALID
ACF_IS_CURRENT_SOLE_BOTTLENECK      = NO
CURRENT_CROSSOVER_MATRIX            = CLOSED_NEGATIVE
CURRENT_AP_FRAME_STAGING_ALONE      = NOT_VIABLE
GDFT_BIN_STAGING_ACROSS_FRAMES      = REJECT
TEMPO_PRIVATE_WORK_STAGING          = CONDITIONAL_ONLY_AFTER_WORK_REDUCTION

FIRST_REPAIR_CANDIDATE              = HOP_INCREMENTAL_GDFT_BACKEND
CURRENT_X2_CROSSOVER                = KEEP_0
SPECTRAL_WINDOWS_AND_CENTRES        = PRESERVE
AP0_VP1_TOPOLOGY                    = PRESERVE
AP_HOP_AND_PRIORITY                 = PRESERVE
GATE3_PUBLICATION_WORK              = NOT_STARTED

GATE2_ENTRY_AFTER_IMPLEMENTATION    = NEW_PROBE_ONLY
PRODUCTION_PROMOTION                = NO
```

The remaining tail is not an ACF-spreading failure. The production 16-lag ACF
spreader removed the old one-shot ACF cliff, but the complete Gate-2 rows now show a
three-part emitted-frame bill: GDFT, tempo work and the rest of the AP semantic path.
No one part can be moved to another task or another core without violating the locked
architecture, and merely spreading the existing bill cannot make its three-frame total
fit the frozen 6,000 us-per-frame margin.

The smallest reversible candidate with enough theoretical leverage, while retaining
the current spectrum, is therefore a compile-gated **hop-incremental backend for the
existing GDFT**. It must update every safe bin with every one of the 96 newly acquired
samples, preserve each bin's current block size and rounded coefficient, and still
finish one complete spectrum on every AP frame. The current direct-recompute backend
remains the rollback and differential oracle.

This is not permission to implement a numerically convenient but different filter bank.
If the incremental backend cannot preserve the current response, corrected-overflow
behaviour and bounded numerical drift, it fails. The next legal path would then be a
deliberate Gate-0 feature/cadence contract decision, not priority, a larger hop, Core-1
DSP or a partial/mixed-age spectrum.

## Evidence admission

The analysis uses only the six corrected complete captures:

```text
gate2v3_no_playback_cross0_20260815_151934
gate2v3_no_playback_cross40_20260815_152104
gate2v3_no_playback_cross80_20260815_152349
gate2v3_music_cross0_20260815_152005
gate2v3_music_cross40_20260815_152252
gate2v3_music_cross80_20260815_152414
```

Every set has `BEGIN.count = parsed rows = DONE.count`, both device drop counters zero,
and no frame, capture-sequence, timestamp, I2S-status or byte-count failure. The music
fixture is the Captain-confirmed audible `Anchor Point` file recorded in the accepted
Gate-2 receipt. “No playback” means only that the host launched no player; it is not an
acoustic-silence claim.

`active` below means the checked-in parser's `total_us - i2s_us`. `total_us` starts
before knob/button/settings/serial service and is sampled after tempo publication
(`SPECTRASYNQ_K1_FIRMWARE.ino:817-838,1012-1035`; capture construction at
`:776-795`). `gdft_us` brackets `process_GDFT()` only (`:892-898`). Tempo-stage values
are meaningful as current-frame costs only where `emitted=1`: on the other two frames
`k1_tempo_update()` returns early and the diagnostic snapshot retains the preceding
emit's values (`audio/k1_tempo.cpp:1364-1383,1598-1607`).

One remaining instrumentation boundary matters for the next probe: APCAD samples before
`process_color_shift()` and `log_fps()` (`.ino:1030-1059`). The present matrix is a valid
negative witness because it already fails before that tail. A positive repair admission
must add a non-perturbing loop-tail/service span; it may not call the current endpoint a
complete Core-0 service measurement.

## What the complete rows say

### Whole-frame distributions

| Fixture | Cross | Rows | Active p50 | Active p95 | Active p99 | GDFT p50 | GDFT p99 | Over 7.5 ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| no playback | 0 | 485 | 8,470 | 10,537 | 10,816 | 7,134 | 7,487 | 485 |
| no playback | 40 | 667 | 5,445 | 7,645 | 7,941 | 4,048 | 4,377 | 65 |
| no playback | 80 | 667 | 5,083 | 7,317 | 7,571 | 3,693 | 3,989 | 10 |
| real music | 0 | 465 | 9,375 | 11,425 | 11,820 | 7,174 | 7,598 | 465 |
| real music | 40 | 640 | 6,431 | 8,534 | 8,721 | 4,095 | 4,404 | 162 |
| real music | 80 | 664 | 6,048 | 8,040 | 8,422 | 3,778 | 4,135 | 134 |

Units are microseconds except row counts. The frozen Gate-0 active-service p99 ceiling
is 6,000 us. Cross0's GDFT p99 alone exceeds that ceiling; no scheduler placement can
repair it. Cross40/80 lower the direct-recompute bill but change the analysis windows
and still leave the full emitted path above the ceiling.

### Emitted versus non-emitted work

| Fixture | Cross | Non-emit active p99 | Emit active p99 | Emit tempo p99 | Emit ACF p99 |
|---|---:|---:|---:|---:|---:|
| no playback | 40 | 5,630 | 8,041 | 2,485 | 1,227 |
| no playback | 80 | 5,299 | 7,682 | 2,591 | 1,253 |
| real music | 40 | 6,732 | 8,775 | 2,399 | 1,205 |
| real music | 80 | 6,426 | 8,477 | 2,436 | 1,226 |

The two cheap-path AP frames are not empty. They still acquire, calculate VU, run the
full spectrum, snapshot it, run onset and saliency, and execute the tempo early-return.
On every third frame, accepted novelty adds the tempo transaction. Production already
spreads 16 ACF lag rows per emit (`platformio.ini:155-162`;
`audio/k1_tempo.cpp:697-728,1425-1458`), but `k1_check_silence()`, two tempo-bin
Goertzel updates, whole-bank normalisation/winner/confidence work, phase and publication
remain in that emitted transaction (`audio/k1_tempo.cpp:1386-1483`).

### Tail composition

All top-one-percent rows in the four cross40/cross80 captures are emitted rows with an
active ACF spread cycle. Their mean decomposition is:

| Fixture | Cross | Top-1% active | GDFT | Complete tempo emit | Residual AP work |
|---|---:|---:|---:|---:|---:|
| no playback | 40 | 8,026 | 4,059 (50.6%) | 2,336 (29.1%) | 1,630 (20.3%) |
| no playback | 80 | 7,702 | 3,667 (47.6%) | 2,490 (32.3%) | 1,544 (20.1%) |
| real music | 40 | 8,803 | 4,176 (47.4%) | 2,143 (24.3%) | 2,484 (28.2%) |
| real music | 80 | 8,479 | 3,821 (45.1%) | 2,304 (27.2%) | 2,354 (27.8%) |

`tempo_emit` contains its ACF/update/phase/publish subspans; those subspans are not
additional to the complete tempo figure. The music residual is larger because the
non-silent onset/saliency path is genuinely data-dependent. For example, V2 onset
computes overlapping full/kick/snare/hihat log-flux loops on every non-silent AP frame
(`audio/k1_onset_beat.cpp:133-140,237-350`), whereas its silence path re-primes and
returns early (`:240-268,535-556`). This is a secondary exact-strength-reduction
opportunity, not enough by itself to close the contract.

Pearson correlations reinforce the phase attribution without pretending to prove
causality:

| Fixture | Cross | active vs emitted | active vs GDFT, all rows | active vs tempo, emitted rows | active vs ACF, emitted rows |
|---|---:|---:|---:|---:|---:|
| no playback | 40 | 0.951 | 0.044 | 0.909 | 0.817 |
| no playback | 80 | 0.954 | 0.035 | 0.956 | 0.830 |
| real music | 40 | 0.847 | 0.189 | 0.531 | 0.556 |
| real music | 80 | 0.875 | 0.091 | 0.556 | 0.537 |

Within one fixed crossover, GDFT duration has a narrow range; that is why its row-level
correlation is small even though its absolute bill is the largest component. Across the
three crossover builds, executed inner-loop work falls from 34,254 to 18,550 to 17,109
iterations and music GDFT median falls from 7,174 to 4,095 to 3,778 us. The controlled
cross-build response, not the within-build correlation, establishes direct recomputation
as the largest service lever.

## Why more frame staging is not the repair

### The conservation bound

For every complete novelty cycle, I grouped one `k1_frame_ctr=0` emitted frame with its
following `1` and `2` frames. Replacing all three values by their arithmetic mean is an
optimistic lower bound for **perfect** placement of the current work: it assumes zero
staging overhead and ignores precedence constraints.

| Fixture | Cross | Triplet-mean p50 | Triplet-mean p95 | Triplet-mean p99 | Perfect-level result |
|---|---:|---:|---:|---:|---:|
| no playback | 0 | 8,965 | 9,225 | 9,388 | fail |
| no playback | 40 | 5,919 | 6,216 | 6,344 | fail |
| no playback | 80 | 5,573 | 5,826 | 5,926 | arithmetically possible only here |
| real music | 0 | 9,762 | 10,168 | 10,287 | fail |
| real music | 40 | 6,785 | 7,083 | 7,136 | fail |
| real music | 80 | 6,429 | 6,796 | 6,856 | fail |

Therefore no measured real-music candidate can meet 6,000 us by rearranging its current
work. Cross80 would still need at least 856 us less **average active work per AP frame**
at p99 even under impossible perfect levelling. Cross40 needs 1,136 us; cross0 needs
4,287 us. Smaller ACF batches move cost between frames but do not change this sum.

### Staging disposition by stage

| Proposed staging | Decision | Reason |
|---|---|---|
| GDFT bins over different AP frames | reject | either mixes sample-window generations or freezes a large window and reduces spectrum publication/freshness; both weaken the current spectral contract |
| snapshot/onset/saliency over later frames | reject | creates mixed-age continuous state and risks event loss; this is precisely the Gate-3 problem, not a Gate-2 service repair |
| separate FreeRTOS task per stage | reject | adds queues/context switches without CPU capacity and violates the locked single AP transaction |
| ACF private lag rows on the two tempo cheap frames | conditionally safe | the previous complete ACF can remain published while private rows advance, but total work is unchanged |
| other private tempo work across the three AP frames | conditional after work reduction | possible only if the measured triplet total is already <=18,000 us at p99 and accepted-event-to-output remains <=25,000 us |

Tempo staging is not the first candidate. Current real-music triplets fail its necessary
conservation test, and deferring winner/phase publication by one or two AP frames consumes
7.5-15 ms of the frozen 25 ms tempo/beat-phase transport budget. It may be reconsidered
only after a work-reduction candidate passes the `triplet_total_p99 <= 18,000 us`
precondition and a trace proves the feature latency. GDFT itself must never publish a
partially updated bin set.

## First repair candidate — hop-incremental GDFT

### Why this candidate

The current source recomputes every safe bin from the entire per-bin history on every AP
frame (`audio/k1_gdft_core.cpp:101-219`). At the production crossover `0`, 71
representable bins execute 34,254 recurrence iterations per frame. Yet acquisition
advances the window by only 96 new samples.

A hybrid hop-incremental backend can retain direct recomputation for bins whose window
is no longer than the hop and update longer-window resonators with all 96 entering and
96 expiring samples. The source-derived recurrence-step envelope becomes:

```text
sum(min(block_size_i, 96)), safe bins 0..70

cross0 direct current = 34,254 steps/frame
cross0 hybrid bound   =  6,134 steps/frame
step-count reduction  = 82.1%
```

This is the only contained candidate in the present decomposition with enough potential
to retain cross0 and remove several milliseconds per frame. A simple guarded-int32
micro-optimisation is insufficient: the historical corrected-arithmetic A/B measured
only about 310 us of GDFT delta, while cross0 real-music active p99 is 5,820 us above the
frozen service ceiling. Likewise, onset/snapshot common-subexpression removal is worth
doing only if new spans prove its value; it cannot rescue a 7.598 ms GDFT p99.

The linear fit of this matrix's music medians against executed direct-recurrence steps is
approximately `0.197 us/step + 0.419 ms fixed`, which would project about 1.63 ms for
6,134 equal-cost steps. That projection is deliberately optimistic: a sliding update
has entering/expiring-sample arithmetic and state maintenance. It is a go/no-go sizing
argument, not runtime proof.

### Non-negotiable implementation contract

Use a single non-shippable flag, provisionally:

```text
K1_GDFT_HOP_INCREMENTAL_PROBE=1
```

The probe environment must inherit `k1_bench_scheduling_baseline_probe` and add only
that flag. It must **not** define a crossover override. Required properties:

1. Keep `K1_GDFT_X2_CROSSOVER_BIN=0`, the same 80-bin canvas, safe-bin clamp, per-bin
   `block_size`, rounded coefficient, normalisation and current one-frame publication.
2. Consume every newly acquired sample exactly once for every active long-window bin;
   remove the corresponding expiring sample from that bin's exact current window.
3. Preserve the corrected overflow behaviour. Loud near-resonance input must never fall
   back to the legacy wrapped/zeroed magnitude.
4. Keep state in fixed-size internal RAM. No heap, queue, task, mutex, blocking call or
   Core-1 dependency enters the AP path.
5. Leave all post-magnitude processing in `process_GDFT()` in the current order: noise
   policy, smoothing, AGC, chroma/spectrogram writes and downstream consumers are not
   retuned in this unit.
6. Reseed on boot, sample discontinuity, I2S short/error frame, sample-rate/chunk change,
   note-offset/coefficient/window change and explicit diagnostic reset. One reseed may
   use the current direct backend only if the existing max-consecutive-over-period and
   two-hop recovery rules are met and a visible reseed counter reconciles it.
7. Publish only after all safe bins for the current capture sequence are complete. A
   stale, partly advanced or missed-sample state must fail visible and reseed; it must
   never masquerade as a fresh spectrum.
8. Provide bounded drift detection. A periodic full rebase that creates a hidden service
   spike is not acceptable. If stable equivalence requires such a spike, reject the
   backend or prove the rebase itself fits the service contract.

The exact incremental recurrence is an implementation research item, not something this
receipt invents. A conventional sliding-Goertzel/DFT formula is acceptable only after
the differential oracle below proves it represents the current quantised rounded-k
response. “Same labelled frequency” is not enough.

## Admission plan

### A. Instrumentation repair before candidate judgement

Add non-shippable scalar spans for:

```text
pre-I2S controls/service
post-I2S VU/sweet-spot work
GDFT recurrence/magnitude kernel
GDFT post-processing/AGC
snapshot
onset
saliency
tempo pre-timed history/scale work
tempo silence / ACF / update / phase / publish
post-publication colour/log loop tail
```

Retain current capture/sample timestamps. MabuTrace is mandatory for nested causal
attribution; APCAD remains the bounded scalar distribution surface. The timing build
must not run a full direct shadow calculation in the measured frame. Use a separate
correctness build/offline replay for differential output, then compare minimally
instrumented and traced candidates under the Gate-0 <=5% p99 perturbation rule.

### B. Host and model gates

Before any device upload:

1. Freeze direct-backend golden outputs for all 71 safe bins over silence, impulses,
   steps, deterministic broadband fixtures, bin-centre tones, half-cell tones and loud
   sustained resonance.
2. Differentially feed identical chunk sequences into direct and incremental backends.
   Assert identical safe-bin winner/ordering and pre-register a magnitude error bound no
   looser than one downstream quantisation code. Zero/NaN/Inf divergence is an immediate
   failure.
3. Run long drift/wrap sequences substantially beyond the longest planned device soak;
   inject missed/duplicate chunks, capture-sequence wrap, short reads and coefficient /
   block-size changes. Every discontinuity must be detected and reconciled by the reseed
   counter.
4. Carry both backends through the existing GDFT golden, int64 recurrence/magnitude,
   centre-honesty, Nyquist hygiene, onset, chord, semantic-state and tempo replay gates.
   Event IDs/counts and locked/unlocked decisions must match the frozen fixture unless a
   separately owned numeric-tolerance record explains an output within the one-code
   spectral bound.
5. Lock the source-derived operation model: cross0 direct 34,254 versus hybrid 6,134
   recurrence opportunities. Fail if an implementation silently omits an entering
   sample, safe bin or required reseed case.
6. Fault mutations must be caught for: no expiring-sample subtraction, wrong window
   length, wrong coefficient, skipped chunk, early generation, state reused after config
   change, above-Nyquist work, disabled overflow correction and hidden partial publish.

If numeric equivalence cannot be held without relaxing spectral/event acceptance, stop.
That would be a feature-contract proposal, not this repair.

### C. Device timing matrix

The first timing matrix is paired and one-variable:

| Leg | Environment delta | Purpose |
|---|---|---|
| A | current cross0 direct baseline | rollback and exact-current control |
| B | A + `K1_GDFT_HOP_INCREMENTAL_PROBE=1` | service-demand candidate |
| C | B in trace-dev form, same runtime behaviour | causal attribution and perturbation bound |

Do not rerun cross40/cross80 in this first repair matrix. They are already dominated for
the stated “no spectral weakening” constraint and would confound the backend comparison.

On the identity-verified B489A500 bench, run complete captures with no host playback and
Captain-confirmed audible real music. Use at least 120 seconds per leg/fixture so p99 and
consecutive-tail behaviour are not decided by seven rows. Add a multi-track real-music
service corpus after the first track passes. Ordinary streams stay off; no calibration,
radio, persistence, priority, task, hop or rate change is admitted.

Device compute admission requires all of:

```text
AP active service p99                         <= 6000 us
newest-sample-to-AP-publication p99           <= 6000 us
arithmetic mean                               < 7500 us
max consecutive active frames over 7500 us   <= 1
recovery                                      <= 2 hops
frame/capture gaps, I2S/byte errors           = 0
unreconciled incremental discontinuities      = 0
partial/stale spectrum publications            = 0
incremental reseeds                            = expected and reconciled
instrumented-vs-minimal p99 regression         <= 5%
IDLE0/TWDT and stack margins                   pass existing Gate-0 formulas
```

Also record GDFT-kernel and post-GDFT spans separately. A lower mean with a failed p99,
freshness or drift gate is still RED.

The production F887A500 leg is required after the bench candidate is green and before
promotion. If any differential fixture or Captain eyes-on comparison exposes a visible
change, apply Captain's corrected product procedure: at least two authorised K1s
simultaneously on different builds, multiple real tracks and approximately 30-60
minutes. Do not spend that product session until compute and semantic admission pass.

### D. Conditional tempo-placement experiment

Only if the incremental backend reduces work but a measured emitted-frame tail remains:

1. Recompute complete three-frame novelty-cycle totals.
2. Admit a private tempo placement probe only when `triplet_total_p99 <= 18,000 us` and
   a concrete fixed phase allocation can keep every phase <=6,000 us.
3. Keep the previous complete tempo event published while private ACF/tempo work is
   incomplete; never publish a partial table or winner.
4. Trace the original accepted novelty/beat/phase timestamp through the delayed publish
   and RMT completion. The existing 25,000 us tempo/beat-phase budget remains binding.
5. Remove the experiment if it does not materially improve full AP p99. Do not convert
   it into another task.

This conditional experiment remains Gate 2 private-work scheduling. It does not create
the Gate-3 unified frame, event sequences or VP acquisition contract.

## Stop rules

Stop and retain cross0 direct if any of these occurs:

- incremental response needs a shorter window, fewer bins, fewer input samples or a
  lower spectrum publication rate;
- corrected near-resonance behaviour regresses;
- numerical drift requires an unbounded or hidden rebase spike;
- host semantic/event gates diverge outside the frozen one-code spectral bound;
- complete device service/freshness remains above 6,000 us p99;
- the candidate moves work rather than reducing the complete novelty-cycle total;
- causal trace attributes the remaining tail to a different stage and the backend does
  not earn its complexity.

After a RED candidate, do not add priority, `vTaskDelayUntil()`, a larger hop, a Core-1
DSP worker or GDFT stage actors. Present Captain with one explicit product contract
trade-off and rerun Gate 0 if accepted.

## Bottom line

ACF spreading should stay. It solved the old full-refresh cliff and current evidence does
not justify reversing it. The present bottleneck is the sum of a full-history GDFT on
every AP frame, a substantial non-silent semantic path, and the every-third-frame tempo
transaction.

The corrected matrix also falsifies “spread it more” as a complete answer: even perfect
three-frame levelling fails every real-music candidate. The next Gate-2 implementation
should therefore reduce work at the only locus with enough measured leverage while
preserving the product spectrum: replace direct full-window recomputation with a
reversible, differentially proven hop-incremental GDFT backend. Only measured green
service, freshness, drift and semantic evidence can admit it; Gate 3 remains blocked.
