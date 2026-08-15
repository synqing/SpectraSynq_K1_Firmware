# Gate 0 scheduling-harness inventory

**Delegation:** FRTOS-16  
**Scope read:** `tests/`, `scripts/regression-harness/`, `scripts/agent/`, `platformio.ini`  
**Audit posture:** source inspection only. No test, build, Git mutation, serial, device, upload or flash action was run. Commands below are exact proposed invocations, not execution evidence.

## Verdict

The repository already has a substantial deterministic/replay substrate, a real mutation self-test, useful AP timing parsers, framed-capture corruption checks, build provenance, and fail-closed device identity logic. These parts should be reused.

It does **not** yet have a scheduling Gate 0 oracle. In particular:

- no existing host executable forces producer/consumer interleavings through the current AP-to-VP publication primitive;
- no current-device trace spans newest sample -> AP publication -> VP frame-top acquisition -> RMT confirmed completion;
- no test distinguishes RMT submission from completion;
- no fail-closed admission runner proves that required tests were neither deleted nor skipped;
- the golden registry, oracle code, checksum manifest, tests and thresholds are co-located in the same writable repository, so the existing anti-gaming mechanism has no independent trust root;
- the active golden registry excludes `oracle_tempo`, `oracle_semantic_state` and `oracle_spectrum_novelty` even though a tempo golden remains hashed.

Therefore the existing harnesses are reusable evidence machinery, but they cannot close Gate 0 without a small independent admission/fault-battery wrapper and, in later gates, new boundary instrumentation plus a forced-interleaving host oracle.

## Boundary-to-oracle map

“Partial” means the existing oracle exercises only an internal mapping or proxy. It is not an end-to-end latency oracle.

| Required boundary | Existing reusable oracle/gate | What it actually proves | Gate 0 status / blind spot |
|---|---|---|---|
| raw peak/VU: named sample/acoustic origin -> first intended visible change | `golden/oracle_gdft.py`; `golden/oracle_render.py`; `tests/test_loop.py`; `vpab_gate.py` | Deterministic GDFT output; deterministic Bloom/spectrum-river rendering; repeatable seeded render; rendered-byte/timing envelope | **Partial.** Separate producer and renderer taps. No shared sample timestamp, generation, frame-top acquire, first changed LED or photon endpoint. Render golden covers only two modes with synthetic state. |
| transient/onset: acoustic transient or accepted event -> first visible response | `golden/oracle_onset_beat.py`; `tests/test_onset_beat_replay.py`; `tests/test_visual_hooks_replay.py` | Real onset/beat DSP under deterministic input and host replay of downstream decisions | **Partial.** Accepted-event behaviour is reusable; acoustic origin, AP publication age, VP acquire and output completion are absent. |
| bass energy: analysis-window reference -> first bass-driven output | `golden/oracle_gdft.py`; `tests/test_semantic_state_replay.py`; `device_novelty_replay.py` | Spectral/semantic calculations and replayable AP telemetry | **Partial.** No analysis-window reference carried into the consumed visual frame. `oracle_spectrum_novelty` is present but deliberately not registered in the golden/self-test trust set. |
| tempo/beat phase: accepted beat/phase event -> phase-aligned output | `golden/oracle_onset_beat.py`; `golden/oracle_smart_director.py`; `tests/test_onset_beat_replay.py`; `tests/test_smart_director_replay.py`; `device_novelty_replay.py` | Deterministic onset/beat and director decisions; device telemetry replay can check lock continuity | **Partial and weakened.** `tempo.golden.jsonl` is checksum-protected, but `oracle_tempo` is disabled in `ORACLE_MODULES` for cross-platform instability. No event sequence delta or accepted-event-to-output timing. |
| chord colour: harmonic-window reference -> intended colour change | `golden/oracle_chord.py`; `tests/test_chord_saliency_replay.py`; semantic/director replay tests | Host-compiles the real chord detector and freezes chord output under deterministic chroma; downstream state replay | **Partial.** No harmonic-window timestamp is joined to the rendered colour generation or RMT completion. |
| AP freshness: newest-sample estimate -> AP publication | `tests/test_rate_consistency.py`; `device_ap_cadence_capture.py`; `device_ap_cadence_matrix.py`; `k1_real_music_corpus_capture.py` | Tuple/rate consistency; AP frame/timestamp gaps; I2S status/byte health; stage duration and `total_us - i2s_us` CPU-work proxy | **Missing endpoint contract.** `N/Fs` and `active_us` are not sample age or publication latency. Existing records lack an authoritative newest-sample estimate and AP publish timestamp. |
| VP generation age: AP publication -> VP frame-top acquire | `vpab_frame_gate.py`; `k1_vpab_visual_sync.py`; `tests/test_dual_sync_oracle.py` | Capture framing, CRC, sequence/drop/corrupt/overflow rejection; historical generation/sequence parser patterns | **Missing for the current local AP->VP path.** Transport integrity is not coherent frame publication. No enclosing generation stamp on every field, frame-top single acquire, mixed-generation counter or AP-publish-to-acquire age. |
| RMT output: submit -> confirmed completion | `vpab_gate.py`; VP performance capture flags in `k1_hardware_harness` | Render/show-related timing and final rendered bytes, depending on emitted capture | **Missing.** No existing oracle provides a hardware-confirmed RMT completion timestamp. `FastLED.show()` return/submission must not be relabelled completion. |
| physical product: acoustic reference -> first visible photon | `k1_real_music_corpus_capture.py`; `k1_paired_snappiness_capture.py`; `k1_vpab_visual_sync.py` | Real-music/device telemetry, paired capture structure and visual-state capture | **Missing.** These are telemetry/visual-state tools, not acoustic-to-photodiode measurement. Physical admission remains Captain-confirmed audible real music plus a named optical measurement/witness. |
| deterministic frame/control mapping | active golden registry; replay suite; serial/config/codec/bootloop oracles | Frozen output, repeatability, exact/discrete comparisons, bounded float tolerance | **Reusable.** Strong for the boundaries each oracle reaches; it does not establish timing, concurrency or physical correctness. |
| concurrency ownership/interleavings | `tests/test_dual_sync_oracle.py` patterns only | Historical transport sequence, generation, drop/delay and deterministic-output checks | **Missing for scheduling.** No current-primitive host executable, pause point matrix, early-generation/two-slot/direct-global/lost-event mutants or 40 ms VP-stall property. |
| task/timing/freshness | `k1_trace_l1_gate.py`; AP cadence/corpus capture; VPAB timing gates | p95/p99/max summaries, AP stage timings, old `vp_bus_read`/`vp_visual_hooks_tick` limits, I2S and frame health | **Partial.** No paired release/probe trace with pre-registered perturbation margin, task runtime share, stack high-water, WDT/IDLE health, queue depth, publication age and RMT completion. |
| provenance / wrong SHA, flags, tuple, device | `test_build_provenance_static.py`; `test_dev_instrumentation_boundary.py`; `test_rate_consistency.py`; upload/device identity tests; `k1-flash-verified.sh` | Build defines/wiring, production-vs-probe flags, 12.8 kHz/96/d3/AP0/VP1 contract, manifest-driven USB identity, runtime git/env/epoch matching | **Reusable but not one admission decision.** Static provenance test is fail-soft when Git is unavailable; runtime identity requires a device. No single manifest binds source SHA, resolved flags, binary epoch, tuple, fixture hashes and trace schema. |

## Existing oracle inventory

### Frozen deterministic and mutation-tested goldens

The active registry is `scripts/regression-harness/golden/harness_selftest.py::ORACLE_MODULES`. `tests/test_golden_master.py` imports that same registry, checks the SHA-256 manifest, re-captures each oracle, compares integers/booleans exactly and floats at `1e-3`, and checks record/field sets. The self-test captures each oracle twice and mutates a copied firmware tree for every declared mutation. `tests/test_mutation_anchor_uniqueness_static.py` adds source-anchor uniqueness checks.

Active registered oracles:

| Oracle | Form | Scheduling reuse | Important limitation |
|---|---|---|---|
| `oracle_onset_beat` | host-compiled behavioural replay | transient/beat semantic preservation | synthetic/internal boundary only |
| `oracle_chord` | host-compiled behavioural replay | chord semantic preservation | no rendered colour timing |
| `oracle_smart_director` | deterministic decision replay | mode/director mapping | no concurrent state acquire |
| `oracle_render` | host-compiled fixed-`dt` render, CRC and samples | render determinism | Bloom and spectrum-river only; 40 synthetic frames |
| `oracle_gdft` | host-compiled real GDFT | source/model behavioural tap | not sample-age/service-time proof |
| `oracle_serial_replay` | command -> text/config/side-effect replay | control mapping regression | serial facade, not transactional concurrency |
| `oracle_serial_struct` | source-structure contract | banned-route/ownership pattern | text/structure, not behaviour |
| `oracle_bridge_fs_config` | source-structure persistence decisions | ownership/static pattern | deliberately not behavioural |
| `oracle_ble_midi_map` | source-derived control map | differential control pattern | unrelated ingress and registry binding has a separate `--gate` |
| `oracle_ble_midi_diff` | BLE-MIDI/WS differential machinery | differential/property and decoder fault-battery pattern | golden capture only freezes enabled-mode roster; `--gate` and `--selftest` are separate invocations |
| `oracle_bridge_fs_codec` | host-compiled real pure codec | executable decision-core pattern | persistence codec, not scheduler |
| `oracle_k1_bootloop` | host-compiled pure boot decision core | forced-scenario/fault pattern | startup only |

Checksum manifest entries also include `tempo.golden.jsonl`, but its oracle is not active. The code comments explicitly leave these three outside the trust set:

- `oracle_tempo`: cross-platform discrete-field instability;
- `oracle_semantic_state`: mutation redirect bypass from import-time paths;
- `oracle_spectrum_novelty`: mutations target the driver rather than firmware.

That distinction is load-bearing: a hashed golden file is not an executed oracle.

### Deterministic replay and host executables outside the frozen registry

- `tests/test_rate_consistency.py`: static/model contract for firmware and host replicas, including explicit 2x and 0.5x in-memory mutations. Reuse for tuple/rate admission, not latency.
- `tests/test_loop.py`: compiles the real render path, uses a fixed seed, and requires two runs to be byte-identical. It may skip without a C++ compiler and does not vary interleavings.
- `tests/test_onset_beat_replay.py`, `test_chord_saliency_replay.py`, `test_semantic_state_replay.py`, `test_smart_director_replay.py`, `test_visual_hooks_replay.py`: useful semantic regression portfolio.
- `golden/oracle_agc_perband.py` with `tests/test_agc_perband_independence.py`: a hand-written property/characterisation executable compiling the real GDFT twice with identical input. It proves the repo can express deterministic differential properties, but it is intentionally outside the golden registry and is unrelated to scheduling publication.
- `golden/oracle_ble_midi_diff.py --gate` / `--selftest`: reusable design pattern for differential equivalence plus known-bad decoder mutations.
- `tests/test_dual_sync_oracle.py`: reusable schema, generation, sequence, delay/drop and deterministic-byte patterns from a historical transport lane; it is not authority for the present Core-0/Core-1 local publication primitive.

No Hypothesis-style generative test or current AP-to-VP metamorphic interleaving executable was found in the audited scope. Existing “property” coverage uses bounded, hand-authored deterministic scenarios.

### Static ownership and safety checks

- `tests/test_i2s_watchdog_static.py`: bounded I2S read, degrade-to-silence, task-WDT registration and render WDT source checks. Its own contract is structural; runtime efficacy is outside scope.
- `tests/test_dev_instrumentation_boundary.py`: production excludes diagnostics and pins AP0/VP1, DMA descriptor 3, 12800/96/d3; harness/trace environments own non-shipping instrumentation.
- `tests/test_build_provenance_static.py`: PlatformIO provenance pre-script, serial build line and release-script restrictions. Runtime provenance is outside host scope.
- `tests/test_build_config_policy_static.py`: resolved WDT/brownout/coredump drift comparison and mutations. It loudly **skips** if authoritative resolved artefacts are unavailable, which is unacceptable unless a Gate 0 runner converts that skip to failure.
- `tests/test_k1_upload_guard.py`, `tests/test_k1_upload_guard_identity_static.py`: manifest-driven accept/reject, stale-port, wrong-device, quarantine and mutation coverage.
- `tests/test_k1_device_identity_guard.py`: runtime `BUILD:` parser and fail-closed git/env/epoch comparison using mocked input.
- `tests/test_ap_input_integrity_p2.py`: separate P4 AP-input host mutation pattern. Reusable as fault-injection design, not as K1 scheduler proof.

Static checks are ownership/banned-path guards only. They must not substitute for a host executable where the real primitive can be exercised.

### Timing, framed-capture and device gates

| Tool | Reusable evidence | Limitation / safety boundary |
|---|---|---|
| `device_ap_cadence_capture.py` | exact tuple expectations; AP sequence/timestamp gaps; I2S status/bytes; stage distributions; parser-only `--from-raw-log` mode | `active_us = total_us - i2s_us` is CPU-work proxy, not sample freshness or end-to-end latency; default fixture is a click track, not physical real-music proof |
| `device_ap_cadence_matrix.py` | variant comparison and p95/DMA-cushion gating | can upload and change runtime configuration; historical candidates are not current authority; never invoke as a read-only parser |
| `k1_real_music_corpus_capture.py` | exact tuple, I2S/frame/crash checks, AP active-work ceiling under real local music | live-device/audio action; Captain audible confirmation is an external admission fact, not encoded by the script |
| `k1_trace_l1_gate.py` | JSON trace p95/p99/max and baseline widening comparison | only `vp_bus_read`, `vp_visual_hooks_tick` and two render counters; no AP freshness, generation coherence or RMT completion |
| `vpab_frame_gate.py` + `tests/test_vpab_frame_gate.py` | strict begin/end schema, chunks, sequence, CRC, dropped/corrupt/overflow and required-channel failures | transport integrity only |
| `vpab_gate.py` + tests | VPAB metric thresholds/render budget/final bytes | no shared generation or physical endpoint |
| `k1_vpab_visual_sync.py` | harness-only live visual sync capture | device action and fixture-specific; not photon timing |
| `k1_paired_snappiness_capture.py` | paired telemetry capture and tuple parity | hard-coded default ports can become stale; comparison is not strict latency proof |
| `device_novelty_buffer_capture.py` / `device_novelty_replay.py` | AP semantic buffer capture and offline replay | AP-only; no VP/RMT join |
| `gate0_selftest.py` | strong known-bad admission pattern for wireless capture | explicitly belongs to a different wireless A/B “Gate 0”; it must not be mistaken for scheduling Gate 0 |

Adjacent reusable tooling and its narrow disposition:

- `onset_beat_replay.py`, `onset_v2_replay.py`, `tempo_replay.py`, `chord_saliency_replay.py`, `semantic_state_replay.py`, `smart_director_replay.py`, `visual_hooks_replay.py`, `render_replay.py` and `loop.py` are the executable replay substrates behind several tests above. Reuse them through their tests unless a Gate 0 manifest pins a direct CLI contract.
- `k1_stm_replay.py` with `tests/test_k1_stm_replay.py` host-compiles the real STM producer and tests deterministic warm-up, steady/modulated spectra and silence honesty. It can protect semantic behaviour under later scheduler work, but it has no publication timing.
- `replay_device_apdbg.py` reconstructs accepted APDBG novelty for the host tempo harness. It is useful cross-boundary replay, but reconstructs transport and does not preserve true sample/publication age.
- `beat_aware_director_device_proof.py` has both fixture-only and live-device modes and checks beat-boundary switching. It is a later product-semantic device gate, not a scheduler freshness oracle.
- `k1_phase345_runtime_proof.py` with `tests/test_phase345_runtime_proof.py` exercises event-status fields and preset queue commit via a restricted serial command set. It is reusable for later event/control transaction gates; it does not force concurrency.
- `k1_trace_capture.py`, `tests/test_trace_dev_static.py`, `tests/test_render_trace_static.py` and `tests/test_diag_capture_static.py` protect the trace-dev/diagnostic boundary. Capture is live-device and the present L1 schema remains too narrow.
- `vp_capture.py` provides a deterministic seeded synthetic VP device probe; `vpab_frame_capture.py`, `vpab_post_switch_capture.py` and `vpab_runtime_matrix.py` acquire deferred/current-state VPAB records; `vpml_runtime_summary.py` and its test explicitly prove transport/final-byte coverage only. These are acquisition/transport building blocks, not timing completion.
- `smart_edge_runtime_capture.py`, `analyse_smart_edge_runtime_capture.py` and `tests/test_smart_edge_runtime_analysis.py` provide live capture plus offline summaries. `smart_auto_product_ab_capture.py` and `tests/test_smart_auto_product_ab_capture.py` provide paired product A/B structure. Both are useful templates for paired control/candidate evidence, but their current schemas do not carry the scheduling boundary chain.
- `k1_paired_snappiness_capture.py` and `tests/test_k1_paired_snappiness_capture.py`, `k1_real_music_corpus_capture.py` and its tests, and `k1_vpab_visual_sync.py` have unit-tested parser/control scaffolding. Their device defaults and fixture semantics must be rebound to the frozen Gate 0 manifest before use.
- `sample_rate_32k_migration_model.py` is a read-only planning model for a non-current 32 kHz candidate. It is not authority for the exact-current 12.8 kHz/96/d3 baseline.
- `ap_capture_leg.py`, `device_stm_telem_soak.py` and `k1_loud_guard_ab_capture.py` contain useful capture/soak patterns but embed stale absolute paths, device ports, tones or workstation volume changes. They are not admissible scheduling commands without redesign and Captain authority.
- `colour_baseline_capture.py` usefully fails when command readback or acoustic-path evidence is missing. It mutates runtime mode/configuration and is a colour-lane device tool, not a Gate 0 timing gate.

### PlatformIO evidence surfaces

- `[env:k1_hardware]` is the shipping default and pins platform, board, memory, AP core 0, LED core 1, DMA descriptor 3 and 12800/96/d3. It registers source-includes, upload-identity and build-provenance pre-scripts.
- `[env:k1_bench_reference_harness]` provides deterministic rounded-k GDFT probing on the bench device.
- `[env:k1_hardware_harness]` inherits production and enables VP performance, AP stream, frame dump, VP probe, GDFT, diagnostic capture, VPAB and pin evidence. It is explicitly non-shippable.
- `[env:k1_hardware_trace_dev]` and related trace environments are explicitly non-shippable.
- `[env:k1_ap_frontend_probe*]` and timing-matrix/stage-profiler variants provide AP clock, raw-input, replay and stage timing surfaces.

There is no current dedicated scheduling trace environment whose schema carries the whole required boundary chain or proves that ordinary/perturbing streams are disabled in the release control.

### Agent wrappers and operational gates

- `scripts/agent/pio-build.sh` accepts exactly one allow-listed environment and forbids target/upload/erase/monitor/device/shell metacharacters. It is a useful safe-build boundary, but its allow-list excludes the current harness/trace and most AP timing environments.
- `scripts/agent/k1-flash-verified.sh` is the sanctioned build -> identity-before -> guarded flash -> runtime git/env verification path and refuses dirty firmware/platform configuration. It is device-mutating and therefore not a Gate 0 inventory action.
- `scripts/agent/k1-session-preflight.sh` checks branch base, prior art, live identities and concurrent worktrees, but is advisory, performs a network fetch/device reads, and exits zero on warnings.
- `scripts/agent/repo-truth.sh` checks lane/branch/repository authority, but despite its “read-only” comment it creates/writes `.devin/repo-truth-report.json`.
- `scripts/agent/session-bootstrap.sh` likewise writes `.devin/last-bootstrap.json` and invokes `repo-truth.sh`; it is not a pure read-only admission check.

## Exact reusable commands

These are proposed commands for the independent gate owner. **None was run during FRTOS-16.** Run from `/Users/spectrasynq/SpectraSynq_K1_Firmware` only after the trust-root manifest and required-test list are frozen.

### Host deterministic, mutation and replay portfolio

```bash
python3 -m pytest -q \
  tests/test_golden_master.py \
  tests/test_harness_selftest.py \
  tests/test_mutation_anchor_uniqueness_static.py

python3 scripts/regression-harness/golden/harness_selftest.py

python3 -m pytest -q \
  tests/test_rate_consistency.py \
  tests/test_onset_beat_replay.py \
  tests/test_chord_saliency_replay.py \
  tests/test_semantic_state_replay.py \
  tests/test_smart_director_replay.py \
  tests/test_visual_hooks_replay.py \
  tests/test_loop.py
```

### Provenance, tuple, safety and identity portfolio

```bash
python3 -m pytest -q \
  tests/test_build_provenance_static.py \
  tests/test_build_config_policy_static.py \
  tests/test_dev_instrumentation_boundary.py \
  tests/test_i2s_watchdog_static.py \
  tests/test_k1_upload_guard.py \
  tests/test_k1_upload_guard_identity_static.py \
  tests/test_k1_device_identity_guard.py
```

The future Gate 0 runner must reject any skip. Pytest by itself treats skips as non-failures, so a green process exit is not sufficient.

### Framing and existing timing parsers

```bash
python3 -m pytest -q \
  tests/test_vpab_frame_gate.py \
  tests/test_vpab_gate.py \
  tests/test_k1_trace_l1_gate.py

python3 scripts/regression-harness/device_ap_cadence_capture.py \
  --from-raw-log <raw-ap-log> \
  --expected-sample-rate 12800 \
  --expected-samples-per-chunk 96 \
  --expected-novelty-decimation 3

python3 scripts/regression-harness/k1_trace_l1_gate.py \
  <candidate-trace.json> \
  --baseline <control-trace.json> \
  --hook-p99-widening-threshold <pre-registered-percent>

python3 scripts/regression-harness/vpab_frame_gate.py \
  <framed-capture.log> \
  --require-channel primary \
  --require-channel secondary
```

`<...>` values are intentionally unresolved because substituting a guessed path, margin, identity or device would invalidate the evidence. Device acquisition must use the current identity registry and the sanctioned guarded workflow, after Captain/device authority; it was forbidden in this audit.

## Trust-root and acceptance ownership

| Artefact / decision | Current owner/source | Required Gate 0 owner | Trust finding |
|---|---|---|---|
| feature meaning, acoustic fixture and physical acceptance | Captain and Gate 0 contract ledger | Captain | Correctly human-owned; cannot be inferred by a test author. |
| production SHA/env/flags/tuple | Git/PlatformIO source plus build provenance scripts | independent gate runner using frozen manifest | Pieces exist, but no single fail-closed admission manifest binds them. |
| device identity | `scripts/platformio/k1_device_identities.json`, upload guard, runtime `BUILD:` line | independent runner; Captain grants device window | Strong fail-closed logic, but only live readback proves the running binary. |
| golden fixtures | `tests/golden/*.golden.jsonl` and `MANIFEST.sha256` | independent harness owner, frozen before implementation | Hashes catch fixture edits only while the manifest itself is trusted. Manifest and fixtures are co-writable. |
| oracle registry/code/mutations | `harness_selftest.py` and `golden/oracle_*.py` | independent harness owner | Good mutation design; implementation lanes must not edit it. Registry deletion can otherwise shrink coverage. |
| required tests and no-skip policy | currently implicit in pytest selection | independent runner, enumerated and hashed | **Absent.** No audited mechanism catches deleted/renamed tests or a critical `pytest.skip`. |
| timing thresholds/margins | dispersed scripts and historical constants | pre-registered Gate 0 manifest; Captain owns product-facing limits | Existing limits are not the full new contract and must not be inherited silently. |
| current-device trace acceptance | capture scripts and parser tests | separate capture operator and independent gate runner | Existing tooling is useful, but schema lacks required boundaries and paired perturbation control. |
| physical acoustic-to-photon claim | none | Captain plus named measurement operator | No host/device telemetry tool may promote this claim. |

## Blind spots that must remain explicit

1. **No deletion/skip detector.** A required test can disappear, be deselected, or loudly skip while an ordinary pytest command exits zero.
2. **Co-located trust roots.** Golden data, hashes, registry, oracles, mutations and accepting tests can be changed together. File permissions/independent lane ownership are procedural, not enforced by the audited code.
3. **Disabled scheduling-relevant oracles.** Tempo, semantic-state and spectrum-novelty oracle files are not active in `ORACLE_MODULES`.
4. **Static-test ceiling.** I2S/WDT, instrumentation, source ownership and many flag checks prove text/configuration shape, not scheduling behaviour.
5. **Compiler-dependent skips.** Host-compile tests such as render replay may skip when prerequisites are absent; build-config policy explicitly skips when resolved artefacts are unavailable.
6. **No current concurrency model.** There is no real-primitive forced-interleaving harness for acquire/build/publish, event epochs/sequences, wrap, stalls or slot reuse.
7. **Timing proxies are mislabel-prone.** AP frame period and `active_us` do not express newest-sample age, AP publication latency, VP generation age or acoustic-to-visual latency.
8. **No RMT completion oracle.** Render time, `show()` time, final bytes or successful submission do not confirm physical output completion.
9. **Trace perturbation is not bounded.** Existing trace/harness envs are non-shipping, but no paired control proves the instrumentation stream stayed disabled in the release control or quantifies probe widening across all required metrics.
10. **Fixture authority is incomplete in code.** The real-music tool knows corpus paths; it does not cryptographically bind Captain audible confirmation, volume/output route, room condition or physical measurement setup.
11. **Historical tooling can look current.** `gate0_selftest.py`, dual-sync and AP timing-matrix scripts contain valuable patterns but belong to other lanes/variants. Their labels and old thresholds are not scheduling authority.
12. **Operational scripts have side effects.** “Preflight”, “repo truth” and “bootstrap” are not uniformly read-only; the cadence matrix and live captures can flash/configure/play audio. They require explicit operational classification.

## Smallest missing Gate 0 harness

Add one **fail-closed admission/fault-battery runner**, owned outside implementation lanes. It need not duplicate the existing DSP/render goldens. Its minimum responsibilities are:

1. read one frozen manifest containing exact Git SHA, PlatformIO environment, resolved flag digest, 12800/96/d3/AP0/VP1 tuple, device identity, build epoch, fixture hashes, trace-schema hash, threshold/margin version, required test node IDs and hashes of the golden manifest/oracle registry;
2. collect the required node IDs and fail if any is missing, deselected, xfailed or skipped;
3. invoke the existing golden reproduction and mutation self-test, then require every registered oracle and mutation count to equal the frozen manifest;
4. validate capture metadata before metrics and reject wrong SHA, flags, device, tuple, fixture, missing field, corrupt generation, enabled perturbing stream and wrong runtime identity;
5. run an internal synthetic known-bad battery that flips each admission field, deletes one required node from a temporary collected-node list, marks one result skipped, changes one fixture byte, removes one trace field, exposes generation before payload, and enables the perturbing stream; every mutant must make the runner RED;
6. emit a machine-readable decision ledger naming trust-root digest, collected tests, skips, oracle/mutation counts, capture pair IDs and exact rejection reason.

This is the smallest Gate 0 addition because it wraps and hardens existing machinery instead of replacing it. It still cannot prove scheduling correctness. Gate 3 separately needs a small host C++ forced-interleaving executable against the real publication primitive, and Gate 1/device gates need a new paired trace schema carrying sample, publication, generation, VP and RMT-completion timestamps. Physical closure remains Captain-witnessed acoustic-to-photon evidence.

## Gate 0 disposition

**REUSE:** golden/self-mutation core, replay tests, rate consistency, framed-capture CRC/sequence checks, AP timing parsers, identity/provenance gates and guarded flash workflow.  
**DO NOT PROMOTE:** static checks to behavioural proof; AP cadence to freshness; render/show timing to RMT completion; telemetry to photon proof; historical wireless “Gate 0” to this scheduling gate.  
**BLOCK:** production scheduling mutation until the frozen manifest, no-skip admission runner and fault battery are RED-proven, and until AP-P4/current-device authority is received.
