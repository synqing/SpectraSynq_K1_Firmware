# K1 × PRISM — from a track to a finished lightshow

**Execution brief · 9 November 2026 · Planning baseline, not a completion report**

## Decision in one sentence

Build one complete product loop: **import a recording → prepare its musical information → generate a show → shape it → play it in time on both K1 edges → save it → reopen and reproduce it**. Keep standalone live music response intact.

The first milestone is a repeatable physical demonstration, not a new analysis model, dashboard, controller or platform. A project that compiles but has no admitted visual consumer is not that demonstration.

## 1. The end state

### The ideal customer outcome

A user chooses a supported local recording in PRISM and a visual direction. PRISM performs the expensive analysis locally, produces a coherent starting show and lets the user hear the original recording while previewing it. The user can change which musical parts influence the top and bottom edges, adjust colour and motion, edit a transition, save the result, and reproduce it on K1 after restarting the application and device. Editing is optional. Analysis internals are available on demand, not required knowledge.

The show is scheduled from the actual music playback position. It survives pause, resume and seeking without stale cues, inconsistent scene state or brightness jumps. If a prepared-show connection fails while valid live audio is available, K1 returns to its approved live response. An unavailable audio input must be reported honestly; no system can react to music it is not receiving.

### Three experiences, one product

| Experience | User action | Expected outcome |
|---|---|---|
| **Listen** | Play music into K1's supported live input. | The existing approved automatic experience works without PRISM or track preparation. |
| **Prepare** | Import a supported recording and choose a visual direction. | PRISM generates an editable, track-specific show without mandatory manual transcription. |
| **Create** | Adjust musical emphasis, edge roles, scenes, palette and transitions. | The changes have clear physical consequences and can be saved and replayed. |

### First-release boundary

The initial prepared-show experience is **local PRISM playback plus one qualified K1 hardware/build profile**. PRISM owns the music transport; K1 owns final execution, LED mapping and electrical limits. First prove the existing reliable wired device path. Wireless controller commands remain a separate concern and need not carry the dense show stream.

The first release does not promise that a disconnected K1 can recognise an arbitrary song playing elsewhere. A locally stored show also does not, by itself, establish synchronisation with an unrelated player. Full standalone prepared playback would additionally require an authoritative audio playback/position source and sufficient verified storage.

### Three stopping points

| Milestone | Exact result | What it does not establish |
|---|---|---|
| **M1 — physical proof** | One 60–90-second passage, both real edges, a hand-authored cue sequence, measured timing and repeatable playback. | Automatic analysis quality, a finished editor or launch readiness. |
| **M2 — complete creator loop** | A full recording imports, generates a show, supports meaningful edits, saves, reopens and replays after application/device restart. | General musical superiority or user demand. |
| **M3 — bounded release candidate** | The advertised platform/profile passes the musical comparison, regression, lifecycle, usability and packaging checks in this brief. | Support for untested boards, all musical genres or all audio-output routes. |

## 2. What is established, and what still needs proving

Source inspection for this brief was read-only. The active PRISM umbrella, Core README, Core music-runtime README, lightshow-loop README, product charter and lock were read from the Mac. No builds, audio processing, firmware operations or physical acceptance tests were run for this brief.

Two existing families must be reconciled rather than casually combined:

| Existing foundation | Evidence and boundary | Required treatment |
|---|---|---|
| Trinity → ShowBundle / Prim8 | The retained August host plan defines `stem_features_v1`, a structured mapping profile, compiler/replay hashes, integer microsecond time and an unchanged VM. Its scope explicitly excludes physical visual/mode binding. [S1] | Locate current code and results. Preserve the admitted format and deterministic path; establish a real renderer binding before product claims. |
| Current PRISM-Core | The inspected Core documentation contains both K1 Live compiler/VM/Studio routes and a portable PCM → musical state → RGB16 runtime with independently owned renderers. Their presence does not prove a prepared-show adapter exists. [S2][S3] | Select the actual deployed consumer and its accepted features. Reuse it; do not pretend a music-state struct is already the old ShowBundle. |
| Hardware lanes | The umbrella explicitly separates Core, Kx-Titan, K1-S3, K1-DualMCU and K1-Remote. Historical gitlinks, local source and resident firmware are different identities. [S2][S4] | Qualify one primary lane. Other lanes are not automatically migrated or certified. |
| Capture and comparison | Existing lightshow-loop documentation links source audio, recorded analysis, native LED data and camera evidence. Its historical results are scoped, not current device certification. [S5] | Reuse the actual retained capture tools and source-bound recordings after checking availability. |

**Important:** the previous conversational numerical ratings are opinions about potential, not measured readiness. This brief uses observable gates instead.

## 3. Scope and non-goals

### Required in this programme

Local file import; repeatable media timing; cached offline analysis; appropriately chosen stem features; a shared, explicit AP–VP data contract; a useful automatic composition; meaningful editing in the existing Studio; deterministic compilation of frozen inputs; actual dual-edge playback; power-limited output; save/reopen/replay; measured synchronisation; failure recovery; live-mode regression; a fair physical A/B/C comparison.

### Explicit non-goals for the first release

| Non-goal | Why it is excluded / later admission condition |
|---|---|
| Perfect full-song note transcription or identification of every instrument | Not necessary for a convincing show. Admit note extraction only for an identified visual consumer with measured benefit. |
| Real-time stem separation or large-model inference on K1 | Heavy analysis belongs on the host for this workflow. |
| New controller hardware, FM-1 conversion or finishing the SMC-Mixer display first | None is necessary to prove the track-to-show loop. Controller work can follow the same accepted controls later. |
| A new dashboard, orchestrator, repository umbrella or parallel acceptance database | Extend existing Studio/Surface/Observatory and evidence structures. This HTML is a readable brief, not another runtime UI. |
| A forced hardware upgrade, new NPU/GPU purchase or NVIDIA dependency | First measure the existing Mac M4 Pro and selected K1 target. Any hardware change needs a demonstrated constraint and separate decision. |
| Replacing every existing effect or migrating every hardware family | One admitted renderer/profile first; preserve other lanes and existing controls. |
| Mandatory MIDI encoding of every internal value | MIDI is an adapter/import-export choice, not the definition of the musical data contract. |
| Arbitrary Spotify/streaming-service integration, acoustic song recognition or external-player chasing | A separate synchronisation and access problem. The first prepared mode owns playback of a local recording. |
| A marketplace, accounts, billing, cloud inference or public community backend | Prove local preparation and replay first. No external contacts are required for local R&D. |
| Re-distributing tracks or separated stems by default | The default portable show contains creative instructions and source identity; the recording remains a separately supplied asset. Distribution requirements are reviewed before distribution, not invented as a blocker to private experiments. |
| Headline model scores as success, browser-only beauty or test-count progress | Physical musical benefit and a complete user transaction are the primary acceptance evidence. |

Existing no-rainbow rules, authored palettes, centre-origin/negative-space identity where applicable, final power limiting, existing safety limits, and source/firmware ownership remain intact. No new full-white load case or high-intensity flashing diagnostic is required by this plan. [S6]

## 4. The architecture and data contract

### Keep these four layers distinct

| Layer | Example | Owner / purpose |
|---|---|---|
| **Musical evidence** | Time-stamped bass energy, vocal activity, an onset, a beat estimate or note estimate. | Analysis. Describes what is observed or inferred, with validity/provenance. |
| **Creative mapping** | Bass shapes lower-edge width; vocal activity drives upper-edge movement. | PRISM. Defines the artistic relationship and transforms. |
| **Show instructions** | Scene, palette, parameter curves, edge roles, timed gestures, overrides and transitions. | Existing PRISM compiler/show representation and an explicitly admitted renderer binding. |
| **Physical output** | Final ordered LED values and actual light. | Hardware lane. Owns geometry, output scheduling, brightness and current protection. |

A range such as 0–1 is not enough. An observation, a musical inference and a brightness command may all use that range while having incompatible meanings. The accepted contract must state transformations exactly once, at the correct layer.

### Contract fields to establish in Phase 1

These are semantic requirements, **not a new mandatory wire schema**. Map them into the existing admitted contracts; use a versioned extension only for an actual gap.

| Subject | Required definition | Reject when |
|---|---|---|
| Asset identity | Original file hash; canonical decoded-audio identity; sample rate/count; channel layout; decode/resample/trim provenance; exact track edition. | A title, filename or BPM alone is treated as an exact match. |
| Timeline | Original sample position plus one explicit conversion to the existing show timebase; event time, availability time/lookahead and timeline epoch. | Seconds, samples, milliseconds and microseconds are mixed; seeks reuse an old epoch. |
| Evidence semantics | Name, source/stem, units, valid range, time resolution, normalisation scope, smoothing and delay. | A display-shaped number is labelled raw evidence, or a transform is applied twice. |
| Quality | Validity, missing/not-applicable reason and confidence only when actually produced or calibrated. | Missing data becomes plausible zeroes; an invented confidence score implies model certainty. |
| Events and curves | Stable event IDs, onset/end, interpolation, equal-time ordering, bounds, confidence where justified, gap/reset behavior. | Events are duplicated, unordered or interpolated as though they were continuous values. |
| Composition | Source feature → target parameter, units/ranges, ownership per edge, palette/effect IDs, precedence and provenance of authored edits. | A parameter has no active renderer consumer, or unavailable controls appear functional. |
| Execution | Compiler/renderer/profile versions, geometry, seed, checkpoints/warmup, scheduling rate and memory/bandwidth bounds. | A show loads onto an incompatible renderer or silently changes semantics. |
| State feedback | Requested, accepted, currently applied and saved revision identities; origin of manual overrides. | Host intent is reported as confirmed device state. |

### Representation choice

Use the existing admitted compact intent/control path when it produces the desired result within budget. Validate how universal Prim8 intent becomes an active effect input; do not put device parameter curves onto an unrelated historical intent-hash path. Preserve fixed dimension order and provenance rules where that legacy contract remains in use. [S1]

Pre-rendered frames are a **conditional alternative**, not an assumed implemented input. For 320 LEDs, uncompressed RGB8 at 60 fps is 57,600 bytes/s, or 17.28 MB for five minutes; RGB16 at 120 fps is 230,400 bytes/s, or 69.12 MB. These are payload calculations, excluding framing, indexes and buffering. Current storage capacity, usable throughput and the final pixel format must be measured. A full frame-stream solution is rejected if it only shifts an unresolved compute limit into an unresolved transport or storage limit.

A pinned native renderer or frame track can provide an exact *command* preview. Optical preview remains an approximation until compared with the actual film stack and camera conditions.

## 5. Execution order and ownership

**Critical path:** P0 baseline → P1 contract → P2 no-AI physical proof → P3 analysis → P4 automatic composition → P5 dependable playback → P6 editing/save/replay → P7 musical value → P8 robustness → P9 release qualification.

After P1 freezes the relevant interfaces, host analysis work may proceed alongside P2. It must not delay the simple playback proof. Use existing owners, one writer per shared branch/worktree and one owner of a physical device/serial connection. Do not introduce multiple competing brokers. A blocked hardware lane does not prevent host-side work, but host results cannot close its physical gate.

| Work owner | Responsibility |
|---|---|
| Integration owner | Resolves the actual source/contract/consumer chain, keeps this brief within the existing workstream, records decisions and integration evidence. |
| Analysis owner | Media identity, separation, feature extraction, cached evidence and analysis-quality checks. |
| PRISM owner | Mapping, automatic composition, compiler/VM integration, existing Studio editing and project persistence. |
| Hardware-lane owner | Device scheduling, scene-state restoration, output ordering, power limits, live fallback and physical evidence. |
| Independent verifier | Freezes expected checks before accepting candidate output; evaluates negative cases and repeatability. |
| Captain / pilot users | Bounded aesthetic and usability judgements, not routine serial captures or instrumentation. |

No firmware changes, flashes, purchases, public uploads, remote API work or external contact are performed or authorised merely by publishing this plan. Implementation follows the applicable existing lane authority. Existing paused sessions are not silently restarted.

## 6. Phase-by-phase work packages

Every phase records **input → actions → output → acceptance evidence → disposition** in the existing work record. `PASS`, `FAIL`, `BLOCKED` and `NOT RUN` are distinct. This brief starts every execution gate at **NOT RUN**; source/document discovery does not pass a runtime gate.


### P0 — Establish the real baseline and choose the proof target

**Goal:** Know exactly which software and physical device can run the experiment without sacrificing the working live experience.

**Owner:** Integration owner + hardware-lane owner  
**Depends on:** Existing workspace and lane authority; no new model or controller dependency.  
**Execution status:** NOT RUN

| Task | Required action |
|---|---|
| **P0.1** | Read active assignments and identify the current PRISM, Trinity/analysis, old ShowBundle, Core and hardware checkout owners. Separate historical documents from present implementation. |
| **P0.2** | Record full source commits, dirty changes, relevant lockfiles, compiled image identity, device-reported resident build, hardware revision and active rendering modes. Unknown device identity remains unknown until read back. |
| **P0.3** | Locate the current ShowBundle/Prim8 compiler, any K1 Live VM consumer, musical-state contract and actual scene-control endpoint. Produce a compatibility table: accepted today / adapter needed / unsupported. Do not select a path because both sides use the word PRISM. |
| **P0.4** | Verify retained binaries/configuration and the existing recovery procedure before any later device mutation. Do not overwrite a known-good image, calibrated state or someone else's working tree. |
| **P0.5** | Select one actual dual-edge 160+160 LED target with a functioning live baseline. Prefer the currently maintained, qualified path; a board with more compute is not automatically the proof target. |
| **P0.6** | Run the existing baseline checks and a controlled live passage. Record audio losses, deadlines, resets, output faults, memory/queue high-water marks, power-limiter behavior and current optical output. Pre-existing failures are isolated and retained, not relabelled as passing. |
| **P0.7** | Inventory the existing approved trance/EDM recordings and capture assets. Confirm exact file identities, edition, offsets and availability. Reuse BOOM/Dopex references only if the actual retained assets can be located and approved for this comparison; never reintroduce the banned song-0 fixture. |
| **P0.8** | Freeze the target-specific budget and relevant stricter pre-existing gates before running the candidate. Record any unresolved decision with the smallest check that resolves it. |

**Required output:** A current compatibility/baseline table, one selected target/profile, exact test assets, retrievable rollback material and the first bounded implementation assignment.

**PASS:** A working live baseline and real native output from both edges are witnessed; the source/build/device relationship and receiving control path are established.

**FAIL / REJECT:** No stable live baseline, unknown control consumer, an unverified rollback path or a substituted single-edge bench presented as dual-edge product proof.

**On failure:** Repair only the affected prerequisite or use another already-authorised eligible lane. Host analysis may continue, but M1 remains blocked.

### P1 — Freeze the music-to-show contract, clock and evidence rules

**Goal:** Make every numerical value and timestamp unambiguous before connecting new analysis to the renderer.

**Owner:** PRISM/Core owner + integration owner + verifier  
**Depends on:** P0 compatibility table and target budget.  
**Execution status:** NOT RUN

| Task | Required action |
|---|---|
| **P1.1** | Trace each intended visible behavior backwards to its active renderer input. Begin with a small usable set: intensity, motion/extent, palette/scene choice and edge role. Exclude inactive or unconsumed parameters. |
| **P1.2** | Specify evidence names, units, ranges, raw-versus-shaped domain, per-stem versus global normalisation, smoothing, missing-data behavior and discontinuity reset. Keep measured energy distinct from artistic gain. |
| **P1.3** | Bind the source audio sample timeline to the existing integer show timebase at one adapter boundary. Preserve sample count, padding/trim offsets and resample mapping. Define timestamp rounding and equal-time event ordering. |
| **P1.4** | Define audio playback as programme-time authority. Relate host monotonic time to device time, scheduled presentation and observed audible output. Specify epoch changes for seek/restart and cancellation of old queued data. |
| **P1.5** | Define source precedence: safety/power limit always wins; explicit blackout is deliberate; manual controls operate through the existing state authority; temporary overrides and recorded automation are distinguishable. Release overrides with a documented pickup or transition policy. |
| **P1.6** | Create small verifier-owned fixtures for a constant curve, ramp, single event, simultaneous edge events, silence, invalid value, missing stem, epoch change and backward seek. Mathematical stimuli are host-only unless separate approved physical test authority exists. |
| **P1.7** | Specify checkpoint/warmup requirements for history-dependent effects. A seek must recreate trails and envelopes, not only restore the current scalar values. |
| **P1.8** | Freeze transport/resource/timing test procedures and acceptance targets below. Version any genuine contract extension, preserve existing golden paths and add an incompatibility rejection test. |

**Required output:** A versioned interface decision within the existing contract/brief, a consumer map, reference fixtures and a timing/resource test definition.

**PASS:** An independent reader can reproduce the meaning of every chosen input; malformed data is rejected without state mutation; accepted current examples remain compatible.

**FAIL / REJECT:** A range has no meaning, timing is implicit, unavailable features are zero-filled as valid, a parameter has no visual consumer, or new data silently change an existing field's semantics.

**On failure:** Correct the seam before building more analysis or UI. Do not compensate for a contract mismatch with ad hoc gain multipliers.

### P2 — Prove a short physical show without machine learning

**Goal:** Demonstrate that a timed programme actually reaches both edges in sync before relying on automated analysis.

**Owner:** PRISM owner + hardware-lane owner  
**Depends on:** P1 contract; P0 healthy baseline and authorised target path.  
**Execution status:** NOT RUN

| Task | Required action |
|---|---|
| **P2.1** | Choose one retained 60–90-second real-music passage with a clear transition. Mark a small set of deliberate cues manually; preserve the original audio as the listening source. |
| **P2.2** | Use one admitted effect or a minimal already-supported scene combination, an approved palette and independent top/bottom assignments. Do not start by designing new effects. |
| **P2.3** | Compile those cues through the existing selected representation. Add only the missing, bounded adapter needed to connect it to the real receiving renderer. |
| **P2.4** | Implement or reuse scheduled preload/queue/acknowledgement behavior; do not fire un-timestamped UI events and call it synchronised playback. |
| **P2.5** | Play the original recording from PRISM's authoritative transport. Verify packet arrival, accepted/application times, final native LED buffers and the physical result as separate observations. |
| **P2.6** | Repeat playback three times from a known initial state. Compare canonical intent/control traces and final pixel output for the same renderer/build, then inspect actual light for geometry and timing faults. |
| **P2.7** | Test pause/resume and one backward/one forward seek, including a point with a visible trail. Old-epoch data must not appear after the new position. |
| **P2.8** | Restore the live baseline and verify that music still drives both edges. Retain the working candidate and evidence without overwriting the baseline. |

**Required output:** The first real dual-edge show, its source project/export, timed logs, three replay records, physical footage and a verified restoration result.

**PASS:** Both real edges execute the intended cues repeatedly, the defined timing check passes, seeks reconstruct state and live restoration works. This closes M1 only.

**FAIL / REJECT:** A browser simulation substitutes for the lamp, only one edge is verified, a transport acknowledgement substitutes for application, or the live baseline is lost.

**On failure:** Fix scheduling, mapping or receiver faults first. Additional stem models cannot repair this failure.

### P3 — Import, separate and analyse once; cache the result

**Goal:** Produce reusable musical evidence with known identity and timing, on the existing host.

**Owner:** Analysis owner  
**Depends on:** P1 data contract; P2 can run in parallel after interfaces are frozen.  
**Execution status:** NOT RUN

| Task | Required action |
|---|---|
| **P3.1** | Import a bounded initial set of formats with tested decoders. Retain the original recording and hash; decode a canonical analysis asset with known sample rate/count and channel layout. Never silently trim leading silence, add time-stretching or normalise the source. |
| **P3.2** | Create cache keys from source/decode identity, preprocessing, analysis parameters, model-weight digest and code/backend versions. An edit to a palette must not invalidate separation; a change to analysis settings must invalidate the dependent evidence. |
| **P3.3** | Run full-mix analysis as the simple baseline. Measure useful energy envelopes, band activity and onset evidence; use beat/section inference only where reliable enough for the selected consumer. |
| **P3.4** | Evaluate the existing separator on the Mac before installing alternatives. Preserve floating-point stem amplitude or record reversible gain changes. Check sample alignment and duration. A separator's artefacts and overlapping sources are not ground-truth isolated instruments. [S7] |
| **P3.5** | Extract appropriate stem evidence: percussion transients/activity; bass envelope and optional notes; vocal activity/phrases; accompaniment energy/texture. Every retained feature must name the intended visual control or debugging question. |
| **P3.6** | Run optional MIDI/pitch extraction only for a selected note-driven effect. Benchmark against envelope/onset-only control and imported known MIDI where available. One successful instrument transcription does not certify arbitrary mixtures. [S8] |
| **P3.7** | Retain low-confidence, missing and unsupported states honestly. Permit an edit/correction layer without altering the original analysis. Do not let a weak pitch model block a show that can use stronger energy/timing evidence. |
| **P3.8** | Measure cold/warm preparation time, peak RAM, disk use and backend behavior on the M4 Pro. Confirm cached projects can reopen without network access. Record downloadable dependencies and their provenance; no paid API or outside contact is a prerequisite. |
| **P3.9** | Exercise interrupted processing, cancellation, corrupt input, disk-full behavior and stale cache. Use temporary writes and atomic publication; preserve the previous valid result. |

**Required output:** Canonical media/evidence assets with identities, reusable stem/features cache, quality labels, host resource measurements and an extraction-to-consumer table.

**PASS:** A supported recording yields valid time-aligned evidence; cache reuse is correct; failures preserve prior work; preparation fits the frozen host budget or is explicitly labelled experimental.

**FAIL / REJECT:** Hidden time shifts, unrecoverable independent stem normalisation, hallucinated instrument labels, repeated heavy processing for visual edits, or a mandatory backend that cannot run on the selected host.

**On failure:** Use the full-mix/envelope path, reduce the feature set or replace only the failing extractor. Do not weaken the timing/identity contract.

### P4 — Generate a coherent automatic show and prove its controls

**Goal:** Turn musical evidence into an immediately useful starting composition, not merely more moving numbers.

**Owner:** PRISM owner + verifier  
**Depends on:** P2 working consumer; P3 valid evidence.  
**Execution status:** NOT RUN

| Task | Required action |
|---|---|
| **P4.1** | Choose one initial visual direction using admitted effects and approved palettes. Define the intended role of each edge, negative space, transitions, peak response and decay. Do not make every feature dominate at once. |
| **P4.2** | Map each selected evidence field to a supported renderer input with an explicit transform and bounded range. Keep the raw evidence inspectable and artistic gain reversible. |
| **P4.3** | Use sections/phrases for large changes and continuous stem features for local movement. If section inference is uncertain, use a simpler evidence-driven composition or explicit authored marks, not invented verse/chorus certainty. |
| **P4.4** | Allow offline anticipation deliberately, recording that it uses future context. Live mode remains causal; an offline lookahead result is not a live-beat-detector benchmark. |
| **P4.5** | Prevent silence/noise amplification and constant saturation. Test quiet intros, breakdowns and tails. Limit colliding gestures and preserve clear hierarchy instead of clipping everything at maximum. |
| **P4.6** | Compile from frozen evidence, mapping, seed and versions twice. Require identical canonical show bytes and deterministic intent trace. Neural analysis itself need not be bit-identical across hardware; its retained output is the frozen input to this test. |
| **P4.7** | Prove each control by changing only it, observing native output and then actual light. For general Prim8 mappings preserve real/authored/neutral provenance; the August contract specifically rejects an Impact-only claim of a richer real mapping. [S1] |
| **P4.8** | Create an ablation set: same live-style renderer driven by prepared full-mix evidence; same mapping with stems; then an authored version. Keep current live mode as an additional product baseline. |

**Required output:** One auto-generated full-song project, an explicit mapping/consumer coverage record, deterministic compile proof and the comparison candidates.

**PASS:** The automatic route produces a complete bounded show, every exposed control has a visible consumer and the same frozen inputs produce the same compiled/replayed intent.

**FAIL / REJECT:** Unused musical features are advertised as contributing, controls silently do nothing, fake sinusoids substitute for analysis, or the output is continuously pinned at limits.

**On failure:** Simplify or repair the mapping. Admit a more sophisticated model only when a measured mapping defect actually requires it.

### P5 — Make full-song playback, seeking and recovery dependable

**Goal:** Turn the short proof into a reliable performance path under real output, transport and lifecycle conditions.

**Owner:** Hardware-lane owner + PRISM playback owner  
**Depends on:** P2 physical proof; P4 candidate exports.  
**Execution status:** NOT RUN

| Task | Required action |
|---|---|
| **P5.1** | Extend the existing package with necessary asset/profile/revision identities, bounds and integrity checks. Stage then validate before activation; retain the previous valid show/configuration. |
| **P5.2** | Measure the actual target's compute, memory, storage and usable transport. Choose resident cues or a bounded lookahead stream. Use a frame track only if the compact path cannot deliver the selected look within the frozen budget. |
| **P5.3** | Implement clock mapping and scheduled execution from audio playback time. Use the selected audio backend's output timing information and physical calibration; a browser animation clock is not the authoritative audio presentation clock. [S9] |
| **P5.4** | Characterise the current verified audio-output route first. A change to speaker/output route invalidates its offset calibration until checked; Bluetooth-speaker output is not assumed equivalent to wired output. |
| **P5.5** | Define buffer low-water marks, underflow handling, duplicate/out-of-order suppression, sequence gaps and epoch reset. No stale cue is replayed to catch up after reconnection. |
| **P5.6** | Add checkpoints or a bounded warmup for history-dependent renderers. Test linear playback versus seek-to-the-same-time from multiple starting positions. Resume audio only once coherent state is ready, or expose a bounded resynchronising state. |
| **P5.7** | Keep manual changes and power limits in the same state authority. Preview the final limited command stream where possible; power clipping must not be hidden behind an ideal pre-limit simulation. |
| **P5.8** | Run controlled disconnect/reconnect, host sleep/wake, wrong track, wrong build/profile, pause, seek, restart and device reboot cases. Restore live visualisation whenever healthy live audio is present; absent audio selects the explicit idle policy, not fabricated responsiveness. |
| **P5.9** | Measure at least 100 reference cue presentations across a ten-minute programme, plus a full-song repeat/seek campaign and recovery tests. Retain signed offset, jitter, drift and measurement uncertainty rather than one average latency. |

**Required output:** A full-song player with integrity validation, calibrated timing, safe state transitions, resource measurements and failure/recovery evidence.

**PASS:** Physical timing meets the frozen acceptance limits, seeking reproduces the intended state, malformed/incompatible packages do not activate, resource bounds hold and live fallback remains intact.

**FAIL / REJECT:** Two free-running clocks drift, a stale package/epoch resumes, seeking loses trails, the device requires unbounded queues, or a transport fault silently kills healthy live music response.

**On failure:** Reduce package complexity, improve scheduling/buffering or use the alternative representation only after measuring it. Never trade away safety or current live-mode requirements.

### P6 — Complete the creator transaction in the existing Studio

**Goal:** Let a person produce and keep a meaningful edit without knowing MIDI messages or internal feature names.

**Owner:** PRISM/Studio owner  
**Depends on:** P4 automatic composition; P5 coherent state and feedback.  
**Execution status:** NOT RUN

| Task | Required action |
|---|---|
| **P6.1** | Extend the current Studio/Surface workflow: import, preparation state, original-audio playback, top/bottom preview, section timeline, musical-layer emphasis, visual controls and save. Reuse Observatory for evidence inspection rather than making another dashboard. |
| **P6.2** | Offer a generated starting show before advanced editing. Name controls by audible/visible consequence; make unsupported features unavailable with a reason, not decorative sliders. |
| **P6.3** | Implement three essential edit transactions: alter one stem's visual influence; alter one edge's look or palette; move or shape a transition. Include undo/redo and reset to the generated version. |
| **P6.4** | Keep analysis, mappings and authored edits separate. Regenerating a show must preserve locked edits or create a new revision/branch with a clear comparison; never silently destroy the creator's work. |
| **P6.5** | Send edits through the real control authority, distinguish requested/applied/saved values and confirm the current show revision on the device. Do not infer successful application solely from a browser value. |
| **P6.6** | Save atomically, close the application, reboot the device, reopen the project, resolve the same recording by identity and replay the same result. Test a missing/moved file and the wrong edition of the same song. |
| **P6.7** | Export/import a portable project without absolute workstation paths or embedded copyrighted recordings by default. Include versions, identities and sufficient instructions for a compatible renderer; missing media produces a useful relink flow. |
| **P6.8** | Add SMC-Mixer control/automation capture only after the above loop passes. Reuse current channel-plus-message mappings and collision checks, preserve feedback/pickup and keep the optional display out of the critical path. |

**Required output:** A working import/generate/edit/undo/save/reopen/export/replay transaction and concise user-facing instructions within the existing PRISM application.

**PASS:** All three defined edits visibly work on both relevant consumer paths, survive save/reopen and do not trigger unnecessary reanalysis. This closes M2 when full-song replay and restart are also proven.

**FAIL / REJECT:** A polished editor changes only the preview, state feedback is inferred, saving omits active mappings or regeneration overwrites authored work.

**On failure:** Fix the broken transaction before adding more controls or controller hardware. A smaller complete editor is preferred to a broad incomplete one.

### P7 — Prove that preparation improves the physical experience

**Goal:** Establish visual value separately from correctness, analysis scores and novelty.

**Owner:** Verifier/capture owner + Captain for bounded aesthetic review  
**Depends on:** M2; frozen candidates, mappings and reference assets.  
**Execution status:** NOT RUN

| Task | Required action |
|---|---|
| **P7.1** | Freeze three approved real tracks with two 60–90-second passages each. Cover strong rhythmic sections, sustained/vocal passages and transitions. Keep at least one additional approved track held out during tuning. |
| **P7.2** | Define A as current live output, B0 as prepared full-mix evidence with matched renderer/mapping, B1 as matched stem-aware automatic output, and C as B1 plus deliberate edits. B0 versus B1 tests separation value; A versus B1 tests the product experience; B1 versus C tests authorship. |
| **P7.3** | Match master level, calibrated output, palette policy, camera position/exposure/white balance, room light and audio playback level. Log actual current/limiter activity. A brighter or more saturated candidate is not automatically a better musical interpretation. |
| **P7.4** | Randomise coded viewing order for musical comparisons. Record separate judgements for musical relationship, visual quality/comfort and preference; retain reasons/timestamps. Do not collapse them into an invented combined engagement score. |
| **P7.5** | Retain the exact audio position, analysis revision, intended controls, accepted controls, final native pixel frames and original camera/audio recording for each comparison. Edited marketing footage is not the acceptance master. |
| **P7.6** | Verify that each authored change has its intended consequence. For the creative-control test, the user must be able to choose a direction and predict the change, not merely notice that something changed. |
| **P7.7** | Apply the musical-value gate below, then run the held-out material without retuning. Record genre/passage limitations honestly. Founder preference is a local design decision, not evidence of universal audience demand. |
| **P7.8** | Reject unnecessary processing: if stems or note transcription do not improve the intended result, remove them from the default preparation path while retaining usable research evidence. |

**Required output:** A linked A/B0/B1/C evidence set, separate numerical and aesthetic findings, held-out results and a decision on each expensive analysis stage.

**PASS:** The predefined musical-value and authorship criteria are met on physical K1 output without trading away comfort, identity or reliability.

**FAIL / REJECT:** Only cherry-picked screenshots look better, superiority comes from extra brightness, extra features are not consumed, or the held-out track reveals unacceptable failure.

**On failure:** Determine whether the defect is analysis, mapping, timing or optics. Revise only the affected layer and rerun the relevant controlled comparisons.

### P8 — Harden lifecycle, budgets and existing live behaviour

**Goal:** Make the accepted experience dependable beyond its best demonstration.

**Owner:** Hardware and PRISM owners + verifier  
**Depends on:** Musically accepted candidate; frozen resources and failure policies.  
**Execution status:** NOT RUN

| Task | Required action |
|---|---|
| **P8.1** | Run all applicable existing host/compiler/VM/renderer/transport regressions without silently rewriting golden expectations. Separate pre-existing failures and fix any that invalidate this path. |
| **P8.2** | Run at least a one-hour active playback/control soak and one 30-minute healthy live-auto regression on the selected target. Include both edges, active output limiting and representative full-song state changes. |
| **P8.3** | Run the lifecycle/fault matrix below: pause/seek/restart, disconnection at critical moments, corrupt show, missing audio, invalid values, incompatible profile, low storage, host/device restart and late/duplicate/out-of-order messages. |
| **P8.4** | Measure peak and sustained CPU, deadline tails, queue depths, memory/stack high-water marks and storage/transport. Report worst cases as well as percentiles; no growing queue or memory leak is acceptable. |
| **P8.5** | Exercise manual brightness changes during the show and power-limiter engagement. All prepared, manual and fallback routes must pass through the same final electrical protection. |
| **P8.6** | Verify correct startup/restoration for session-only versus persistent state. The saved show identity, selected effect/palette and feedback must agree after recovery. |
| **P8.7** | Restore the known-good baseline through the documented route and rerun the minimal live check. A rollback description without an actual restoration result remains unqualified. |
| **P8.8** | Freeze the accepted build/profile and dependency identities. A later change to firmware, separator, mapping, compiler, geometry or audio-output route invalidates only its relevant evidence and triggers the corresponding regression. |

**Required output:** Fault-matrix results, soak traces, measured resource/power records, complete regression report and demonstrated rollback.

**PASS:** No new capture losses, output faults, unbounded resource growth, stale control application or power-limit bypass; all mandatory failure behaviors pass.

**FAIL / REJECT:** A success demo depends on ignoring a failing relevant regression, hardware counters substitute for visible output, or recovery replays stale data.

**On failure:** Hold the candidate. Keep the current known-good experience available while repairing only affected mechanisms.

### P9 — Qualify a bounded customer-facing release

**Goal:** Demonstrate that the advertised experience is usable and reproducible outside the implementation session.

**Owner:** Product/integration owner + pilot users after local qualification  
**Depends on:** P7 and P8 pass; no outside contact required before local work is exhausted.  
**Execution status:** NOT RUN

| Task | Required action |
|---|---|
| **P9.1** | Package one tested host setup and one K1 hardware/build profile. List supported media formats, audio-output routes, preparation limits and optional features truthfully. |
| **P9.2** | Test installation/startup on a clean user environment, dependency/model discovery, cancellation/recovery, updates and offline cached replay. Do not require undocumented terminal commands for the normal workflow. |
| **P9.3** | Provide one legitimate distributable demonstration asset or a private test asset for private trials, plus a project/template that exercises the real workflow. Keep original recordings out of public exports unless separately cleared. |
| **P9.4** | Run the defined task with five pilot users after local proof: import, generate, make one desired change, save, close, reopen and replay. Record intervention, task success, confusion and whether they choose to repeat the experience. |
| **P9.5** | Target at least four of five completing the core task unaided within the stated active-interaction budget, excluding measured background preparation. Report this as directional usability evidence, not a population estimate. |
| **P9.6** | Resolve all data-loss, wrong-track, uncontrolled-output, sync and silent-no-op issues before release. Keep genuinely optional analysis features off by default if their benefit or reliability is unproven. |
| **P9.7** | Review actual dependency/model/source obligations and asset handling before any distribution. Do not contact vendors or invent commercial licensing work solely to conduct private R&D. |
| **P9.8** | Produce a reproducible release package, compatibility statement, concise recovery instructions and a demonstration captured from the accepted build. Keep raw evidence distinct from marketing edits. |

**Required output:** A scoped release candidate with install/replay evidence, pilot findings, known limitations, recovery package and truthful demonstration assets.

**PASS:** All mandatory engineering gates and the defined usability gate pass for the advertised configuration. This closes M3 for that scope only.

**FAIL / REJECT:** The experience still needs an engineer to finish a normal task, the advertised hardware/output route was not tested, or show/data recovery remains unreliable.

**On failure:** Reduce the advertised scope or repair the failed transaction. Do not relabel an engineering preview as a generally qualified product.


## 7. Acceptance matrix — freeze before implementation measurements

**The numbers below are proposed engineering/product targets, not observed results, perceptual laws or promises of current performance.** P0/P1 bind them to the selected target before candidate evaluation. Existing stricter accepted requirements remain in force. For example, prepared-show alignment tolerances do not relax the Core documentation's separate live-latency/render-time targets. [S3]

A gate passes only when its evidence exists for the actual receiving consumer. An unavailable instrument or device produces BLOCKED, not PASS. A threshold may be revised prospectively with rationale and a new test revision; it may not be weakened retrospectively to make a recorded result pass.

| ID | Requirement | Proposed pass criterion | Failure / rejection |
|---|---|---|---|
| A01 | Source identity | Exact recording/decode/profile identities retained and checked at load. Wrong edition or incompatible decoder result is rejected or explicitly reprocessed. | Matching by title/BPM alone, silent substitution or stale cache. |
| A02 | Timing preservation | Known sample/time mapping through decode, separation and resampling; representational rounding ≤1 canonical sample; no unrecorded trim/padding. | Unknown offset, drift or duration change. Model event-detection error is evaluated separately, not hidden in this gate. |
| A03 | Input integrity | All required fields valid; finite/ranged values; stable event ordering; corrupt packages rejected before activation with previous valid state preserved. | Partial corrupt activation, valid-looking fabricated zero channels or unsafe resource allocation. |
| A04 | Deterministic compilation | Same frozen evidence + edits + seed + versions compile twice to identical canonical bundle and intent trace. Runtime manifests/timestamps live outside deterministic content. | Hash drift without an explained input change. |
| A05 | Renderer repeatability | Same profile/build/state/time sequence yields identical final native pixel payloads across repeated runs. Cross-platform differences require pre-frozen numerical tolerance and separate approval. | Stateful drift, order-dependent behavior or broadening a tolerance after seeing a failure. |
| A06 | Physical cue alignment | Over ≥100 scheduled reference cues, p95 absolute presentation error ≤25 ms and maximum ≤50 ms, after one fixed calibration for the selected audio route. Include measured timing uncertainty in the bound. | Average-only results, per-event offset fitting, uncalibrated camera timing or coarse evidence presented as a fine measurement. |
| A07 | Long-run drift | Residual systematic offset change ≤10 ms over ten minutes after fixed initial calibration, while A06 also holds. | Free-running clocks diverge; a long-run average masks drift. |
| A08 | Measurement quality | Timing measurement uncertainty ≤5 ms for A06/A07 certification. Prefer simultaneous audible-output and light-sensor capture on a common acquisition clock. | 50-fps footage alone is claimed to prove sub-frame timing; such footage is coarse/optical evidence only. |
| A09 | Pause/seek/restart | 20 cycles each; correct epoch, no stale event, coherent scene after forward/backward seek. Cached seek returns to a ready coherent state within 500 ms; paused audio remains paused until ready. | Old cues fire, trails start incorrectly, or seek silently resumes the wrong revision. |
| A10 | Control responsiveness | Supported cached visual edits visibly apply within 100 ms at p95 over ≥50 actions, excluding intentional artistic smoothing; device acknowledgement and render application distinguished. | Screen-only change, silent no-op or unbounded lag. |
| A11 | Resource headroom | Preserve stricter current lane budgets. Initial target: worst observed normal render work ≤70% of its frame period, no deadline miss in the nominal soak, ≥25% declared usable RAM reserve, bounded queues; exact accounting frozen at P1. | OOM, growing queue/leak, or a design requiring all resources with no measured reserve. |
| A12 | Transport/storage | Package size and peak data rate fit the measured target, with a queue/lookahead bound and documented stall budget. Storage/transport beyond the supported bound is refused before playback. | “USB/Bluetooth supports it” replaces actual throughput/buffering proof. |
| A13 | Host preparation | Initial prototype cap: cold preparation real-time factor ≤2 on the selected M4 Pro configuration; record RAM/disk, backend and per-stage time. Editing a palette/curve reuses separation and evidence. | Mandatory repeated inference, unsupported CUDA-only path or claimed fast mode without measurements. Exceeding the cap requires an explicit experimental label or optimisation, not a false pass. |
| A14 | Power/output safety | All final outputs respect the existing lane electrical limit and calibration under both-edge activity, manual gain and fallback. Show files cannot raise that limit. | Pre-rendered or override path bypasses limiting; software sums are presented as measured amperes. |
| A15 | Fault recovery | 20 link-loss/recovery cycles across active sections. With valid live audio, enter approved live response within 500 ms of detected show-stream invalidity/underflow; no stale replay or uncommanded blackout. | Frozen silent failure, violent brightness jump or stale queue replay. Actual RF-loss detection time is also measured and reported separately. |
| A16 | Persistence | 10 full save/close/reopen/device-restart cycles reproduce the accepted project/revision and final output for the same media/profile. Undo/redo and missing-media recovery preserve edits. | Browser save alone is treated as device persistence or authored work is lost. |
| A17 | Nominal reliability | One-hour prepared-show/control soak plus 30-minute healthy live regression: zero new capture losses, resets, native output faults or skipped required releases; no unbounded memory/queue growth. | Ignored fault counters, missing physical observation or relevant existing regressions remain unresolved. |
| A18 | Prepared-show musical value | On six frozen passages, Captain rates prepared automatic output better than live for musical relationship in ≥4, not worse for visual comfort/quality in ≥5; no unacceptable failure on the held-out track. Report individual reasons, not a synthetic combined score. | Improvement is brightness-only, cherry-picked or unrepeatable. This is local product judgement, not universal market validation. |
| A19 | Added-analysis value | For each optional stage, matched ablation shows a useful difference for its named effect without an unacceptable regression. Removing a stage with no benefit is a successful engineering decision. | Model scores or plausible labels alone justify complexity. |
| A20 | Authorship | The three defined edits each achieve their intended visible consequence and survive reopening; desired direction is specified before comparison. | “It changed” substitutes for “it changed as intended.” |
| A21 | Usability | After local qualification, ≥4/5 pilot users import/generate/edit/save/reopen/replay unaided; target ≤10 minutes active interaction, excluding logged offline processing. Record failures and intervention. | Engineers operate the system for users or preparation wait is hidden. |
| A22 | Release truth | Only tested host, media, renderer, board and audio routes are advertised; cached operation works offline; restore procedure and known limitations included. | A different board or build is shown as equivalent without evidence. |

### Timing measurement cautions

Measure **scheduled cue time versus actual audible-output-relative light presentation**, not model discovery delay. Offline lookahead deliberately permits advance preparation. A correctly scheduled artistic anticipation is not a synchronisation error; use dedicated reference cues with defined intended times to measure timing.

A Sony capture at 50 fps has a 20 ms frame interval. It is useful for composition, gross alignment and optical faults, but cannot alone establish a 5 ms uncertainty bound. Existing higher-resolution instrumentation should be used when available; do not invent sub-frame accuracy or force a purchase before checking the existing bench. Calibrate sensor/capture delay and retain uncertainty. A 50-fps review can proceed while the fine-timing gate remains blocked.

For browser audio, W3C distinguishes audio context time, output latency and output timestamps. Those facilities support clock mapping, but their presence is not a measurement of the entire speaker-to-light path. [S9]

## 8. Failure and lifecycle test matrix

| Test case | Required behaviour | Retained witness |
|---|---|---|
| Silence or very quiet recording | No noise-normalisation explosion; defined decay/idle; no fake beats. | Evidence curves and actual limited output. |
| Strong peak / dense mix | Musical hierarchy remains usable; bounded output; no overload. | Final pixel data, limiter activity and footage. |
| No vocals / poor stem | Missing/uncertain state is explicit; show uses a valid alternative. | Feature validity and mapped consumer state. |
| Wrong/remastered/trimmed track | Refuse automatic exact-match replay; relink/reanalyse explicitly. | Identity mismatch and unchanged active project. |
| Corrupt/truncated package | Reject before activation; preserve last working state. | Validation result and active revision. |
| NaN/Inf/out-of-range parameter | Reject or apply the pre-specified safe range policy atomically. | Before/after state and no output mutation on rejection. |
| Unavailable effect/palette/profile | Report incompatibility; never silently substitute a different look. | Capability handshake and UI state. |
| Pause/resume and rapid repeated seeks | No old-epoch events; correct history reconstruction; coherent resume. | Transport epochs, state snapshots and payload comparisons. |
| Duplicate/out-of-order/late packet | Drop or resolve under frozen policy; no double trigger. | Sequence/application log. |
| Stream starvation / controller disconnect | Preserve autonomy; fall back according to valid audio and explicit operator state. | Loss-detection time, transition time and physical output. |
| Device restart | Re-identify build/profile; no replay until fresh state/epoch is negotiated. | Boot identity and restored show/state acknowledgement. |
| Host sleep / audio route switch | Stop stale scheduling; re-establish clock relationship/calibration. | Clock mapping revision and first valid resumed presentation. |
| Manual fader disagrees with automation | Defined pickup/override behavior; no surprise jump; accepted value displayed. | Requested/applied values and visible output. |
| Save interruption / disk full | Previous project intact; incomplete file never replaces it. | Old/new hashes and recovery test. |
| Power limiting during a prepared peak | Both edges remain inside the qualified cap; no alternate bypass. | Final-output path trace and electrical measurement. |
| Return to auto mode | Same accepted live behavior and controls as the baseline. | Matched baseline/candidate live capture. |

## 9. Cost, complexity and feature admission decisions

A proposed feature is accepted only if it has an identified user/renderer consumer, makes a useful difference in a matched physical comparison or closes a necessary reliability gap, fits the frozen resource budget and can be maintained within the existing architecture.

| Candidate | Admit when | Defer or reject when |
|---|---|---|
| Stem separation by default | It improves a desired layer/transition enough to justify measured preparation cost. | Full-mix evidence is as good for the chosen direction. |
| MIDI/note transcription | An active note-driven gesture improves; wrong notes and correction burden are acceptable. | No consumer, high false-note artifacts or envelope-based movement works better. |
| Additional model | It fixes a demonstrated analysis deficiency that affects physical light. | It is only newer, larger or better on an unrelated benchmark. |
| Pre-rendered frame export | It enables a selected look that compact execution cannot afford, and storage/transport/power-qualified playback fits. | It prevents needed interaction or exceeds real playback resources. |
| New compute hardware | Measured constraints cannot be resolved by caching, scheduling, representation or scoped simplification at acceptable cost. | The proposal is speculative or duplicates host-side capacity. |
| SMC screen / recording controls | The creator loop works, mappings are real and the accessory materially improves operation. | It delays the core loop or merely adds a display without authoritative state. |
| Wireless show transport | Measured delivery, buffering and resynchronisation meet the same gates. | Only controller-message BLE support has been shown. |
| Shared-show features | Local export/relink/replay is dependable; source identity and asset handling are defined. | A public service is being built before a portable show works. |

Measure model load/preparation, cache reuse, RAM/storage, show size, device work and user correction separately. Do not substitute one “value score” for those tradeoffs. Costs here include founder effort and maintenance, not only component price.

## 10. Evidence and completion rules

### Evidence record required for a claimed pass

Reuse the owning lane's existing evidence/receipt format. At minimum retain requirement ID, pre-frozen procedure, exact inputs and source/build identities, actual device/profile, command/configuration, timebase, observed result, expected result, uncertainty where relevant, raw artefact location/hash, known limitations, reviewer disposition and recovery result.

A hash is useful only when the underlying bytes remain accessible. Preserve raw audio/camera evidence outside source control where appropriate, linked from the existing work record. Do not publish private media or credentials to make a report look complete.

### Evidence strength is claim-specific

| Evidence | Can establish | Cannot establish on its own |
|---|---|---|
| Documentation/source inspection | Architecture and candidate code exist. | Runtime correctness or installed state. |
| Host numerical tests | Contract, numerical behavior and deterministic host replay. | Device timing, electrical limits or optical appeal. |
| Device application/readback | A specific device applied a specific input/revision. | Correct actual light or musical value. |
| Final native LED payload | What values were emitted in what order. | That LEDs, guides and optics displayed them correctly. |
| Common-clock audio/light measurement | Actual alignment within stated uncertainty. | Aesthetic quality or usability. |
| Matched physical footage/review | Visible faults, composition and bounded preference judgements. | Precise timing below capture resolution or broad market demand. |
| Unassisted user task | Usability of the tested workflow. | Commercial market size or all-user success. |

### Final handback, problems first

Lead with: **what works; what fails; what is blocked; decisions genuinely required; next executable task**. Then link the source/project, accepted show package, exact build/profile, measurements, raw comparison evidence and rollback material. Preserve unsuccessful candidates and reasons. Do not mark a phase complete merely because its files exist, its tests were launched or its report was generated.

### Immediate implementation handoff

Begin at P0 in the existing workspace. Resolve the ShowBundle/Prim8-to-current-renderer compatibility question, choose one qualified dual-edge target, retain its baseline/recovery material, freeze the smallest contract and prove P2's hand-authored short show. P3 host analysis may run in parallel once that interface is fixed. Do not begin with a model shopping exercise, complete all controllers first, or create a new project umbrella.

**The first major acceptance is one complete, repeatable performance on the real K1. The final acceptance is that another person can prepare, change, save and replay their own performance without an engineer operating it for them.**

## 11. Sources and inspection boundary

The sources establish existing constraints and technical considerations; they do not certify implementation of this new programme. Public references were checked for this brief. No “latest model” claim or tool-selection bake-off was performed.

- **[S1] Retained host-plan evidence:** `2026-08-16-instrument-spine-g5.md`, retrieved from the user's Library. It defines the historical Trinity adapter, structured `prim8_natural_v1` mapping, ShowBundle compiler, integer timebase, provenance and intent-trace checks. It explicitly stops before device visual/mode binding. Treat source lineage and current integration as P0 checks; do not rerun its old repository-creation instructions.
- **[S2] Current local navigation inspected:** `/Users/spectrasynq/Workspace_Management/Software/SpectraSynq-PRISM/README.md`, `AGENTS.md` and `PRISM-Core/README.md`. These distinguish lane ownership, old gitlinks, current checkouts, device identity and the established Studio/Surface/Observatory route. They are documentation, not freshly executed tests.
- **[S3] Current local runtime documentation inspected:** `SpectraSynq-PRISM/PRISM-Core/music/README.md`. It distinguishes musical state, independently owned renderers, live timing targets, validity, discontinuities, unadmitted features, the final output limit and lane-owned electrical limits. This brief does not claim current target qualification from the README.
- **[S4] Retained ownership brief:** `PRISM_Titan_Workspace_Reorganisation_Astra_Execution_Brief_2026-10-15.md`, retrieved from the Library. It requires independent lane ownership, preserved evidence and source-bound status.
- **[S5] Existing experiment route inspected:** `SpectraSynq-PRISM/docs/lightshow-loop/README.md`. Historical capture and restoration records are useful precedents; present installed-device state still needs P0 verification.
- **[S6] Product constraints inspected:** `SpectraSynq-PRISM/docs/product-charter.md`, its lock and `docs/asymmetric-capability-leverage.md`. Relevant constraints include no rainbow, meaningful controls, real physical evidence, existing UI/ownership, no fake completion metrics and no unnecessary parallel systems. The lock was read; its file hash was not independently recomputed during this read-only planning task.
- **[S7] Demucs primary documentation:** `https://github.com/facebookresearch/demucs` and its README. Describes four principal stem outputs and warns that per-stem rescaling can affect relative levels. It is a technical example, not a newly selected dependency or assertion of latest/best separation quality.
- **[S8] Spotify Basic Pitch primary documentation:** `https://github.com/spotify/basic-pitch`. Describes audio-to-MIDI/pitch-bend output and best performance on one instrument at a time. It is an optional extractor example, not a prerequisite.
- **[S9] W3C Web Audio specification:** `https://www.w3.org/TR/webaudio/`, especially audio context time, `getOutputTimestamp()` and `outputLatency`. Browser support and the selected audio route require implementation-specific checks and physical calibration.
