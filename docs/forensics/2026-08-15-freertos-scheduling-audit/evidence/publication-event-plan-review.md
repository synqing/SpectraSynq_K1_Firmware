# FRTOS-07 — publication, event and command plan review

**Date:** 2026-08-15
**Current checkout observed:** `main` / `15d3a85d6d26e9698039a5b0d39dbaa1569718b4`
**Scope:** source review and architecture contract only; no firmware, test, build,
device or git-state mutation
**Verdict:** **ACCEPT WITH REQUIRED AMENDMENTS**

## Blunt decision

Captain's **VP-local whole-frame copy under one short `portMUX` is the correct
first implementation candidate**. It closes the audit's two-slot lifetime defect:
after Core 1 copies the published value into task-local storage and releases the
spinlock, Core 0 may publish any number of later frames without touching the object
Core 1 is rendering.

The earlier literal “two slots + publish active index + VP retains a pointer” plan
must be rejected. With a 7.5 ms AP hop, a producer can revisit a slot in about
15 ms while a historically observed 38–40 ms VP stall may still own it. An atomic
index makes the selection coherent; it does not create reader ownership.

The local-copy plan is sufficient only when amended as follows:

1. the shared object contains **one complete musical generation**, published once
   after the last AP semantic stage;
2. VP acquires it once at frame-top and every consumer receives only that local
   `const` value/view;
3. continuous state, discrete musical edges, desired-state commands,
   non-idempotent commands and telemetry use different delivery semantics;
4. whole-frame lock hold/wait time is measured before promotion;
5. if that copy fails its timing margin, use explicit three-slot ownership, not an
   unowned two-slot pointer.

This is TRIZ separation by condition/data class: K1 needs freshness for state,
once-only observation for musical edges, ordering for irreversible commands, and
record preservation for forensics. One generic queue or mailbox cannot satisfy all
four without sacrificing either latency or correctness.

## Current-source evidence

The publication/control files are unchanged from audit reconciliation SHA
`8026807f`; the only decision-area source changed between that SHA and the current
checkout is `audio/i2s_audio.h`. The following publication findings therefore apply
to current HEAD:

- `K1AudioSnapshot` is already built as a local value and copied into/out of one
  shared object under a `portMUX`, but it has no generation
  (`audio/k1_audio_snapshot.cpp:28-121,124-129`; struct at
  `audio/k1_audio_snapshot.h:64-97`).
- AP currently publishes the audio snapshot, onset, saliency and tempo in sequence
  (`SPECTRASYNQ_K1_FIRMWARE.ino:951-1019`). The semantic aggregator then obtains
  tempo, onset and audio under three separate locks, so the aggregate has no
  common generation (`audio/k1_semantic_state.cpp:31-40`).
- VP consumers independently re-read those publications. Dense Forge performs
  three separate reads inside one effect (`effects/light_mode_dense_forge.cpp:98-100`).
  `get_smooth_spectrogram()` still reads the live, sequentially written
  `spectrogram[]` (`visual/lightshow_modes.h:19-28`), while the K1 waveform hybrid
  combines a snapshot value with the live peak global
  (`effects/light_mode_waveform_hybrid_k1.cpp:109-116`).
- Onset has an `event_id`, event time and per-channel event IDs
  (`audio/k1_audio_snapshot.h:99-130`), but the transient booleans are still
  published as current-frame/held state (`audio/k1_onset_beat.cpp:575-590,642-648`).
  Tempo exposes a one-publication `beat_tick` with no beat sequence
  (`audio/k1_tempo.h:22-29`); the producer explicitly clears it on intervening AP
  frames (`audio/k1_tempo.cpp:1364-1382`). A VP read between publications can miss
  that edge.
- The timestamp passed into the current snapshot is taken at loop entry, before
  knobs, buttons, settings, serial and the blocking I2S read
  (`SPECTRASYNQ_K1_FIRMWARE.ino:792-846,957`). It is not a sample-capture timestamp.
- Two mode writers publish readiness before payload
  (`control/k1_control_facade.cpp:473-483` and
  `serial/serial_cmd_handlers.cpp:1608-1624`); Core 1 consumes the flag and then
  destination (`visual/led_utilities.h:1683-1693`).
- The effect queue writes pending multi-field presets, then uses `volatile
  g_commit_request` as the publication protocol
  (`control/k1_effect_queue.cpp:49-70,486-508,585-605`). `volatile` provides
  neither transaction ordering nor a coherent two-channel scene.
- Core-0 arming currently reads Core-1-owned transition runtime to seed its pending
  preset (`control/k1_effect_queue.cpp:472-483`). That ownership reversal must not
  survive the mailbox redesign.
- The current diagnostic recorder copies the complete variable-sized payload while
  holding its `portMUX` (`diag/diagnostic_capture.cpp:133-172`), and stop changes a
  state flag without producer acknowledgement (`diag/diagnostic_capture.cpp:71-79`).
  Render trace similarly clears `s_armed` and immediately reads/dumps the buffer
  without proving an in-flight producer copy has completed
  (`visual/k1_render_trace.cpp:50-68,101-110`).

## Required continuous-state publication contract

The first candidate should have exactly three storage objects:

```text
Core 0 stack/static owner: producer_next
Shared internal RAM:       published
Core 1 task owner:         vp_frame
```

Core 0 builds `producer_next` outside the critical section. After onset, saliency
and tempo have updated, it enters the shared mux, copies the complete POD frame to
`published`, increments/publishes the generation, and exits. Core 1 enters the same
mux once at VP frame-top, copies payload plus generation to `vp_frame`, records its
acquire time, and exits. No pointer/reference to `published` escapes either API.

### Mandatory invariants

| ID | Invariant |
|---|---|
| PUB-01 | One AP acquisition produces at most one published generation; generation is monotonic within an explicit boot/session epoch. |
| PUB-02 | `published.payload` and `published.ap_generation` are written and read under the same mux; generation changes only after the candidate is complete. |
| PUB-03 | The mux encloses only fixed-size POD copy, generation and minimal timing counters—never DSP, smoothing, logging, allocation, derived computation or I/O. |
| PUB-04 | VP acquires once per render frame. `vp_frame` is immutable until that render, both channel renders and any crossfade passes finish. |
| PUB-05 | All effects/directors/hooks receive the same `const K1AudioFrame&` or approved derived view. Core-1 source cannot read live AP globals or call independent audio/onset/tempo readers. |
| PUB-06 | `mixed_generation_count == 0`. `vp_generation` never moves backwards; skipped generations are permitted and counted. |
| PUB-07 | AP publication never waits on a queue, heap or consumer acknowledgement. Lock hold/wait p50/p95/p99/max are measured on producer and consumer. |
| PUB-08 | The frame is static, bounded and trivially copyable; `sizeof(K1AudioFrame)` and its internal-RAM placement are asserted/reported. |
| PUB-09 | Timestamp names describe their actual boundaries: at minimum capture sequence, I2S-read return, oldest/newest sample estimate with assumptions, AP publish and VP acquire. Loop-entry time is not labelled capture time. |
| PUB-10 | No nested acquisition of existing snapshot/onset/tempo muxes occurs while holding the publication mux. Build the candidate first, then take the one publication lock. |

This eliminates the two-slot lifetime race by construction. Its remaining risk is
bounded spinlock cost, not object lifetime. If measured producer wait/hold or AP
service tails fail the chosen margin, the fallback is three slots with explicit
`FREE -> WRITING -> PUBLISHED -> READING -> FREE` ownership (or equivalent
sequence/ref ownership). A slot may not return to `WRITING` while VP owns it.

## Discrete musical events are not ordinary state

Newest-complete-frame semantics are correct for spectrum, chroma, VU, peak,
silence, tempo estimate, phase and confidence. They are insufficient for onset and
beat edges because VP may skip AP publications.

The unified frame should carry cumulative, reset-aware identity rather than only a
one-frame boolean:

```text
event_epoch
onset_sequence_total
last_onset_time_us
last_onset_strength
beat_sequence_total
last_beat_time_us
beat_phase01
tempo_bpm
tempo_confidence
```

VP retains the last consumed onset/beat sequence. A non-zero unsigned delta means
new events exist. The render contract must explicitly choose the coalescer when the
delta is greater than one: one visual trigger with count-scaled energy, latest
strength, or a specified accumulator. A per-publication count alone is not enough
because overwritten AP publications cannot be summed by VP.

If maximum strength, every timestamp or every event record matters, use a separate
bounded event ring. Do not pretend the latest-state frame preserves event history.
The current onset `event_id` and per-channel event IDs are useful starting resources;
tempo requires a real beat sequence because `beat_tick` alone can be missed.

### Event invariants

- sequence advances exactly once per accepted edge, never once per reader;
- a state-only update cannot retrigger an edge;
- VP consumes each observed sequence delta once, even when the boolean has cleared;
- reset/boot has an epoch so a counter reset is not interpreted as a vast event burst;
- sequence wrap arithmetic and maximum permitted unobserved delta are specified;
- ring-backed event telemetry is ordered, bounded and has an explicit drop policy
  and `dropped_event_records` counter; it never blocks AP.

## Command contracts by semantic class

| Class | Required primitive | Rule |
|---|---|---|
| Complete desired state (`set mode/palette/brightness`, complete channel preset) | Static depth-one latest-wins mailbox | Build immutable payload locally; under a short mux copy payload and increment generation. Overwrite is intentional and counted when unconsumed. |
| Complete two-channel scene | One immutable scene payload plus one scene generation | Both channels become one transaction and are applied on the same VP frame boundary. Never use independent channel-ready flags. |
| Non-idempotent edge (`increment`, `trigger once`, `clear calibration`, fault acknowledgement) | Small bounded ordered queue with sequence | Preserve order and at-most-once consume. On full, reject visibly or apply the command-specific documented policy; never silently overwrite. |
| Persistence request (`store preset`, save configuration) | Bounded service-owner command/result channel | Keep flash ownership separate from VP transition ownership; coalesce only operations explicitly declared idempotent. |
| Diagnostics/history | Per-producer bounded ring where practical | Reserve slot, copy payload outside the commit critical section, publish slot sequence last, count drops. Merge AP/VP streams offline by timestamps/generation. |

Only the owner of transition runtime may inspect it. Therefore relative commands
that depend on in-flight visual state must be resolved by Core 1 from an ordered
command, or converted upstream into a complete desired scene from an independently
owned desired-state model. Core 0 must not keep reading `g_transition[]`.

For state mailboxes, the consumer acknowledges the consumed generation so
`overwritten_unconsumed` is measurable. For ordered queues, use static capacity,
head/tail sequence and explicit `queue_high_water`, `enqueue_rejects`, `sequence_gap`
and `apply_failures`. Do not route newest-only audio frames through that FIFO.

## Forced-interleaving verification battery

These are Gate-0 host/oracle cases, not optional unit-test decoration:

| Test | Forced schedule | Required observation |
|---|---|---|
| FI-01 old-or-new | Pause producer while building `producer_next`, before lock; run consumer. | Consumer sees the complete previous generation; private partial work is invisible. |
| FI-02 producer mid-copy | Pause producer after each payload quarter while it owns mux; start consumer. | Consumer cannot enter until commit completes, then sees complete new payload and matching generation. |
| FI-03 consumer mid-copy | Pause consumer after each payload quarter while it owns mux; start producer. | Producer cannot overwrite; consumer receives complete old generation. |
| FI-04 stalled VP lifetime | Consumer unlocks with local frame N, then stalls 40 ms while producer publishes N+1…N+5. | Every field used during stalled render remains N; next frame may acquire N+5 and records four skipped generations. |
| FI-05 payload/generation boundary | Pause after shared payload assignment but before generation increment, inside mux. | No consumer observes new payload with old generation. |
| FI-06 mixed-field oracle | Stamp every test field with its producer generation and force scheduling at every copy boundary. | Every consumed field stamp equals the enclosing generation; `mixed_generation_count=0`. |
| FI-07 two event edges | Publish two onset/beat edges between VP acquisitions, clearing booleans between them. | Sequence delta is two; VP applies the declared coalescer once and advances its consumed sequence without losing identity. |
| FI-08 concurrent event | Pause immediately before and after sequence commit while VP acquires. | Event is observed either this frame or next, exactly once—not zero times or twice. |
| FI-09 state overwrite | Publish desired states A, B, C before VP consumes. | VP applies complete C only; overwrite count records A/B and no field from either leaks into C. |
| FI-10 scene atomicity | Pause publication between each primary/secondary scene field. | VP applies either previous scene or complete new scene; never primary-new/secondary-old. |
| FI-11 ordered edges | Fill ordered queue around wrap, interleave producer/consumer, then force full. | Accepted commands execute once in sequence; full policy is visible and drop/reject counters match. |
| FI-12 telemetry commit | Pause after slot reservation, during payload copy and before sequence commit. | Consumer never reads an uncommitted slot; committed records preserve sequence or expose an explicit gap/drop. |
| FI-13 capture stop | Issue stop during an in-flight record copy. | Producer acknowledges quiescence before drain/CRC; dump cannot race the last write. |
| FI-14 epoch/wrap | Reset event epoch and exercise counter/generation wrap. | No backward-frame acceptance, phantom burst or duplicate edge. |

Each fault-injection case must first be shown to fail against a deliberately unsafe
publication implementation, then pass the candidate. Instrumentation-on versus
minimally instrumented paired runs are required because the proof harness can itself
create contention.

## Structural ratchets

Promotion should add static/host guards for these exact rules:

- no Core-1 references to `spectrogram[]`, `waveform_peak_scaled` or other live
  AP-owned globals;
- no effect/director-level calls to `k1_audio_snapshot_read()`,
  `k1_onset_beat_read()`, `k1_tempo_read()` or `audio_semantic_read()`;
- one approved VP frame-top acquire call and one immutable frame parameter path;
- no `volatile`-only multi-field commit protocol;
- payload-before-generation under the approved primitive;
- one scene generation for both channels;
- no heap, blocking wait or FIFO audio-frame queue in AP;
- event-bearing frames expose sequences, not boolean-only edges;
- telemetry rings expose capacity, high-water and drops;
- required task-creation failure becomes a latched, visible degraded/fail-safe state
  (current LED creation result is printed but not made an operating state at
  `SPECTRASYNQ_K1_FIRMWARE.ino:721-752`).

## Acceptance gate and residual boundary

Accept the VP-local copy implementation only when all forced interleavings pass and
current hardware measurement reports producer/consumer lock hold and wait
p50/p95/p99/max, AP service/cadence/backlog, VP generation age/skips, whole-frame
time and stack watermarks under the worst enabled dual-channel crossfade. Define a
margin against the chosen AP/VP contracts; “it still usually fits” is not a safety
criterion.

This review proves the ownership model closes the pointer lifetime defect. It does
**not** prove the copy is cheap enough on device, that current timestamp estimates
represent real sample age, or that event coalescing gives the best perceptual result.
Those remain measured P4/post-P4 gates. Production remains byte-inert before P4.
