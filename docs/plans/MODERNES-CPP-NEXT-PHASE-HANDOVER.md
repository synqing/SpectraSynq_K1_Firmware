# K1 Modernes C++ next-phase execution handover

Prepared 10 November 2026, Australia/Perth. Receiving agent: a fresh Opus CLI session.

## 1. Mission and finish condition

Take over the remaining software corrections from the Modernes C++ investigation. Preserve the accepted fixes, repair the five defects specified below, verify the actual candidate and complete authorised local integration. This is an implementation task, not a request for another general audit or plan.

The previous agent delivered valuable fixes and passing software evidence, but incorrectly concluded that only a board test remained. A subsequent source review found unresolved lifetime, persistence, request-transfer, diagnostic and input-framing defects. The new phase closes those specific gaps and the conflicting test workflow.

**Finish when:** all five defects have an evidence-backed disposition and every applicable, repairable defect is implemented; focused acceptance checks and the required integrated checks support the exact final candidate; the test workflow follows current policy; the records accurately distinguish historical results, new results and missing hardware evidence. A genuine blocker stops only its dependent action. Keep executing independent work.

Do not manufacture changes if a later owner has already repaired a finding. Confirm the equivalent correction and its evidence, then close that item. Do not claim hardware qualification from software results or leave an executable software repair waiting for a board.

## 2. Start here: project, current state and authority

**Working directory:** `/Users/spectrasynq/SpectraSynq_K1_Firmware`

The final save/readback check while preparing this handover found:

| Item | Observed state | How to use it |
|---|---|---|
| Current branch | `fe/k1-fe-show-fixes` | Recheck ownership; do not switch back to the old release branch automatically. |
| Current HEAD | `8b202f46ac6fa612b914ea54cbf773e31be96531` | This includes the accepted fixes and later Gx board/power changes. |
| Tracked working/index changes | Uncommitted firmware, test and replay edits appeared during preparation | These were not made or reviewed by the handover author. Establish ownership and reconcile them before editing. |
| Untracked documents | `docs/plans/MODERNES-CPP-EXECUTION-PLAN.md`, `docs/plans/MODERNES-CPP-CLOSEOUT-REVIEW.md`, this handover | Preserve them and the additional source/test/evidence files described below. |
| Accepted historical correction | `e28dd9275ab2c21d20b551f9c0bf31dc842e7106` | Preserve its implementation; it is not the automatic deployment target. |
| Later board-support change | `c44172faf0d42bb3d868e5042fa4f51a704cb358` | Brings K1-FE-Gx support onto the release ancestry. |
| Local release tag | `fe-1.0.0-rc2` at `545f00e4` | Historical release identity; this new phase will create a different candidate if source changes. |

Paths below are relative to the working directory unless an absolute path is supplied. Firmware paths beginning `visual/`, `serial/`, `control/`, `persistence/`, `system/` or `calibration/` are under `SPECTRASYNQ_K1_FIRMWARE/`.

**Active-work notice:** the final check found edits in the main `.ino`, audio frame/authored-source/emulator-fixture/PRSM/access code, waveform effects, serial command tables/menu, `visual/led_utilities.h`, regression-harness serial tooling, native/static tests, and `tools/esp_emulator/{run.py,emu_blob.py,emu_capture.py}`. Untracked additions also included `audio/k1_prsm_rx.cpp`, `audio/k1_prsm_rx.h`, `tests/k1_prsm_rx_host.cpp`, `tests/test_k1_prsm_rx_native.py`, `tests/test_serial_cmd_persist_flags_static.py`, and `docs/forensics/runtime-evidence/20261110-fe-show-fixes/`. The audio paths here are relative to the firmware directory.

These changes overlap this handover's serial, diagnostic, audio and replay work. Treat them as another session's work until current ownership establishes otherwise; do not overwrite, revert or stage them wholesale. The source mechanisms and workflow observations below describe the reviewed snapshot, not certification of these intervening edits. Obtain a fresh status/diff, identify completed or in-progress corrections, and reconcile the existing owner's handoff before changing the affected files. Recheck the replay runner's actual interface: the intervening edits may already address part of Stage A. Continue independent reading/review while a write surface is occupied.

### Required read order

1. Current `/Users/spectrasynq/.claude/CLAUDE.md` and applicable path-scoped rules.
2. Repository `AGENTS.md`, `CLAUDE.md`, `.claude/CLAUDE.md`, `AGENT_OS.md`, and `docs/agent/AGENT_EXECUTION_STANDARD.md`.
3. Current handoff and lane authority from `docs/spec-index.md`, `.claude/handoff.md`, and relevant `progress.md` entries. Resolve applicability; these files contain material from different dates and targets.
4. `docs/plans/MODERNES-CPP-CLOSEOUT-REVIEW.md` and `docs/forensics/modernes-cpp-lessons-2026-11-10.md`. The former corrects the latter's premature closeout. The essential findings are reproduced here, so no earlier chat is required.
5. `platformio.ini`, the relevant build/test entry points, and `tools/esp_emulator/README.md` before choosing commands.
6. Before device work: `docs/hardware/device-build-registry.md`, `scripts/platformio/k1_device_identities.json`, the current production programming procedure and `docs/handover/RECEIPT-FE-FW-2026-11-10.md`.

Use `/usr/bin/git`; the ordinary `git` command is wrapped on this Mac. Use `rg` for scoped searches. Current instructions identify `/opt/homebrew/opt/python@3.13/bin/python3.13` for tools affected by Python 3.14's missing XML module; use the interpreter/environment required by the actual tool.

### Working boundaries

- Own one approved write surface. Preserve other agents' work, staged state and device sessions. Do not reset, stash, clean, rebase or commit unrelated work.
- Current instructions prohibit inventing new development worktrees, sibling checkouts or clones. Use the existing ownership/branch process. An authorised temporary verification export is not a second development workspace.
- Do not switch a shared checkout to an old commit to run a baseline. Reuse the identified historical evidence or existing authorised export when needed.
- Active implementation scope is S3 FE and its existing replay/host dependencies. This handover does not reopen Titan, DualMCU, S31 porting or another parked programme.
- Preserve musical behaviour, target-specific geometry, existing colour/motion language, the rainbow prohibition, valid control/persistence compatibility and power/brightness policy. No full-white qualification requirement or raised power limits.
- Current instructions ban Wi-Fi paths and new agent infrastructure. Reuse approved tools and workflows. Make only the bounded existing test-workflow correction required below.
- Honour already-granted authority. Do not create a fresh approval step for ordinary authorised corrections. Device holds, unknown identity, native tool permissions and external publication restrictions remain real boundaries.

## 3. Required skills and existing tools

Canonical skill location:
`/Users/spectrasynq/Workspace_Management/Software/agent-skills/skills/<skill-name>/SKILL.md`

Read current skill instructions and relevant references when their work begins. Do not load every skill or carry superseded mutation instructions forward.

| Timing | Skill | Purpose |
|---|---|---|
| Startup | `firmware-c-cpp` | Embedded C++ conventions, actual toolchain, ownership and verification routing. |
| Baseline/build selection | `runtime-target-source-truth`, `spectrasynq-build-system` | Establish actual source, profile, build and target identity. |
| Ownership repairs | `esp32-actor-model`, `esp32-render-path-safety` | Respect task ownership, live-path constraints and render handoffs. |
| Audio/control-loop effects | `spectrasynq-audio-pipeline` | Preserve acquisition and processing contracts. |
| Persisted data or serial behaviour | `protocol-contract-verification` | Preserve format, framing, IDs, accepted semantics and client compatibility. |
| Before replay | `k1-esp-emulator-replay` | Real product code, declared adapters, deterministic inputs and evidence identity. |
| Numerical or resource claims | Relevant `signal-processing-verification`, `firmware-profiling` or `dsp-performance-profiling` | Choose evidence appropriate to the actual claim. |
| Diagnostic visuals | `k1-effect-development` | Preserve intended identify behaviour and the product visual language. |
| Failure diagnosis | `systematic-debugging` | Diagnose the actual mechanism before repeating a failed approach. |
| Delegation, if useful | `ssa-management`, `orchestrator-briefing-discipline` | Bounded work, source identity and one integration owner. |

Also read the repository-local `.claude/skills/sensorybridge-doctrine/SKILL.md` before audio, visual or core-timing work. Before replay read `/Users/spectrasynq/Workspace_Management/Software/SpectraSynq-ESP-Emulator/docs/LESSONS.md`. The executable replay implementation is in this firmware repository at `tools/esp_emulator/`; the separate emulator knowledge directory is not a replacement firmware repository.

Use Deja's registered context search for a concrete prior decision or recurring error, then open its sanitised cited evidence. History is not current authority. Backplane is installed at `/Users/spectrasynq/.local/bin/backplane`, but the inspected launcher only established desktop/hub/model-render functionality. Use a documented project integration if relevant; do not invent firmware-orchestration commands or start a second hub.

Parallel read-only review can help. Keep shared ownership changes under one integration owner and avoid concurrent writers invalidating the baseline or tests. Model agreement is not verification.

## 4. Preserve the work and evidence already accepted

Commit `e28dd927` corrected:

- LED-count writes that could exceed boot-sized buffers; the setter now checks the compiled count.
- Note-table indexing beyond the supported offset, including a boot-time clamp.
- Unterminated serial fields that could expose stack bytes.
- Non-finite/garbage values reaching many numeric setters.
- Calibration reset on the wrong core; an atomic request now causes the audio loop to perform that reset before acquisition.
- A compiler-flag regression that would remove NaN checks, plus narrow established static invariants.

Keep these corrections. The calibration change fixes that reset mechanism; it does not establish that every calibration display field is synchronized.

**Accepted historical evidence:** the saved checkout gate reports 2,070 passed, 2 skipped and a successful `k1_hardware` build. The final clean export identifies full `e28dd927`; its declared source paths were compared with the Git blobs, with no differences. Replay criteria SW01–SW11 and SW13 passed; SW12 was not applicable. Hardware/CI claims remained deferred.

Baseline2, candidate1 and final export have matching case names, frame counts and output hashes across 28 cases: 27 nonempty captures and one intentionally empty stall case. The justified `cfg-save` adjustment is 600 to 1200 tail hops, preserving exactly one save. The prior silence/debounce change explains the extra time. Do not undo it to recover an older duration.

These receipts prove their stated historical candidate and exercised paths. They do not prove new repairs, every interleaving, Gx hardware, or the current branch merely because it descends from that commit.

## 5. Execution sequence

Use the order below. Input/persistence work can be investigated independently of ownership work, but integrate against one stable candidate. Maintain one working record using the existing forensic record/evidence conventions; append new outcomes while preserving old receipts.

### Stage A — Take ownership and reconcile the test workflow

**Actions**

1. Confirm branch, HEAD, working/index state, current owner and affected profiles. Compare any intervening edits with this handover before applying a change.
2. Read the actual test entry points before invoking an automatic suite or hook. The October 22 instruction in `/Users/spectrasynq/.claude/CLAUDE.md` prohibits building firmware mutants and repeated wasteful full-suite runs, overriding older hooks/tables that require them.
3. Correct the conflicting existing execution path. The verified chain is `tests/test_harness_selftest.py` → `scripts/regression-harness/golden/harness_selftest.py::run_selftest()` → `_mutated_capture()` → copied firmware `.cpp/.h` files rewritten from `MUTATIONS` → compilation/capture. Five serial mutation substitutions were repointed by the previous phase. Their age does not authorise execution.
4. Preserve meaningful tests of real production behaviour. Retire or policy-disable the forbidden mutation invocation through the normal project test configuration, with an explicit reason and coverage accounting. Do not extend mutation tables, delete failed evidence, bypass the whole hook or use blanket `--no-verify`.
5. Distinguish genuine malformed-input/legacy-file tests from altered firmware mutants. Evaluate existing capture-corruption self-tests against current policy too; their historical label is not an automatic exemption.

**Known duplicate-run conflict:** inspected `tools/esp_emulator/run.py` exposes only `--scenario`, `--output`, `--suite` and `--profile`. It unconditionally invokes `host_checks()` before running cases, even for a narrow suite. `scripts/hooks/pre-commit` separately invokes `pytest tests/ -q` for firmware changes. There is no existing skip/reuse flag in the inspected runner.

Choose one authoritative complete host run for the final candidate and avoid launching it again through the other entry point. Prefer the normal pre-commit gate after implementation and focused checks. If no current documented mechanism coordinates these obligations, make the smallest bounded change to the existing replay runner/receipt flow to consume that result with validation. This is an implementation step, not an option already available.

Any reuse must verify the actual source, tests, fixtures/goldens, relevant build configuration, harness and test selection, plus tool/environment identity and successful nonempty outcomes. Confirm inputs did not change during the originating run. Reconcile pre-commit content identity with the resulting commit; HEAD alone is insufficient. Reject missing, stale, incomplete or mismatched evidence. Distinguish a validated reused result from a newly executed check. Preserve every required non-host criterion and affected-target build. Do not build a general caching framework or make skipped checks appear passed.

Use focused checks while implementing where they answer a real uncertainty; repeat only after a relevant change or diagnosed failure. No automatic 20-run campaign. If a genuinely unresolved policy conflict prevents an integrated gate, name it and continue independent source corrections rather than bypassing it.

**Exit:** an owned baseline and a documented, policy-compliant verification path that can finish without building mutants or blindly running the full host suite twice.

### Stage B — Fix dynamic look-table lifetime

**Entry points:** `visual/k1_look_file.h` (`k1_look_free_slot_ram`, `k1_look_install_parsed`, `k1_look_fs_clear`); `visual/k1_look.h` (`k1_look_publish`, `k1_look_publish_sec`, `k1_look_apply_u16`); typed serial and binary-upload callers.

**Established mechanism:** clear frees storage before removing the published table. Replacement unpublishes then immediately frees, without waiting for a reader that already holds the old pointer. Rendering dereferences dynamic RGB/matrix/cube storage directly. The typed command's disruptive flag is metadata; its dispatcher provides no outer render park.

**Implement**

1. Trace every active reader and install/clear/reload/upload entry point, including primary, secondary and secondary-inherits-primary selection.
2. Prepare and fully validate replacement storage before changing a working slot. Allocation, file I/O and parsing stay outside render/interrupt critical sections.
3. Transfer the complete descriptor and ownership using the existing suitable synchronization pattern. Reclaim old storage only after every possible reader of that generation has finished.
4. Use acknowledged exclusion or a render-owned switch with completion acknowledged back to the reclaiming owner. An atomic pointer or publishing a fallback first does not revoke a pointer already held by a reader.
5. Treat timeout, allocation failure, malformed input, cancellation and repeated clear as explicit outcomes. Preserve a valid old state on failed replacement. Success responses must mean the operation completed; do not silently acknowledge installation while it remains pending.

Once a request has been published, a caller timeout does not cancel it or return ownership of its storage. Correlate acknowledgements with the request/generation; reject stale acknowledgements. Retain pending payloads until consumption or cancellation is acknowledged. Do not free a new payload merely because its caller stopped waiting, or report the old state preserved while a timed-out request can still commit later.

**Critical trap:** `system/globals.h::lock_leds()` returns after a 100 ms acknowledgement timeout without reporting failure. Wrapping a free in that function is insufficient. Avoid casually changing its contract for every existing caller; scope the needed correction and audit any affected callers. Never hold a spinlock/critical section across waits, allocation, filesystem access, logging or rendering.

**Acceptance:** exercise a reader holding the old payload while a legitimate clear/replacement arrives; verify no early free/reuse, correct publication, no leak and defined failure handling. Include both edges, inheritance, timeout followed by a late acknowledgement, and cancellation while a request is pending. Use the actual implementation and controlled scheduling/lifecycle seams, not a rewritten illustrative queue. Existing look tests and appropriate native lifetime instrumentation may support this; a static text assertion alone cannot establish it.

**Target boundary:** `k1_fe` includes `K1_LOOK_LIB_V1`; `k1_fe_bench_b489` explicitly removes it and uses the WS2812 look path. A B489 pass cannot close dynamic FE LUT lifetime correctness.

### Stage C — Validate old saved configuration and show state

**Entry points:** `persistence/bridge_fs.h` (`save_config`, `load_config`, `init_fs`), `persistence/bridge_fs_config_codec.h`, `control/k1_show_state.cpp` and `control/k1_effect_queue.cpp` capture/apply paths.

**Established mechanism:** old ordinary setters admitted non-finite values. Normal saves wrote those bytes with a correct CRC. The configuration loader validates format/integrity then adopts raw values. Show-state decoding restores raw channel floats and applies them after configuration loading. Thus a repaired CONFIG can be overwritten by an invalid saved show.

**Implement**

1. Enumerate affected persisted fields and their existing authoritative defaults/ranges. Distinguish ordinary CONFIG fields from primary/secondary show-preset fields. `response_gain` is RAM-only; do not invent a persisted migration for it.
2. Validate or repair at both real adoption boundaries before values reach live consumers. Share a small validator where that prevents contradictory rules; do not introduce a generic configuration framework.
3. Preserve healthy values and unrelated settings, existing special values, schema/version/CRC handling and missing-file behaviour. Do not tighten ranges without a demonstrated requirement.
4. Keep recovery consistent with the existing RAM-first anti-brick policy. No factory reset, unsolicited reboot, file deletion or indiscriminate defaults rewrite. If repaired data should be saved, use the existing persistence policy and avoid unnecessary repeated boot writes.
5. Check the final state after CONFIG **and then** show restoration. Account for any other actual adoption path using the same preset representation.

**Acceptance:** exercise old-firmware-compatible, CRC-valid invalid configuration and show fixtures through the real loaders. Prefer the existing pre-fix writer/export or demonstrate equivalent encoding with the production codec; do not mutate current firmware. Cover primary CONFIG, primary show overlay and secondary show values, plus healthy controls. Verify finite/allowed live values after the entire restoration order, preserved unrelated settings and unchanged malformed/truncated-file policy. Test the adoption behaviour, not just the checksum classifier.

### Stage D — Transfer complete mode and preset requests

**Entry points:** `serial/serial_cmd_handlers.cpp::serial_cmd_dispatch_mode`, `visual/led_utilities.h::run_transition_fade`, and `control/k1_effect_queue.cpp` (`k1_queue_arm_begin`, `k1_queue_request_commit`, `k1_effect_queue_frame_tick`). Inspect any active facade callers; do not make an unreachable facade the sole proof of product coverage.

**Established mechanism:** a mode request flag is raised before its destination is written, while the consumer also clears shared request state. A mutable pending preset is exposed while the render task copies it. A request can disappear or a mixed preset can become the lasting/saved state; there is no proven one-frame recovery.

**Implement**

1. Establish intended staging, replacement/latest-wins, quantisation, transition and persistence semantics from current contracts and consumers. Do not treat accidental race outcomes as the contract.
2. Publish a complete request/preset and its metadata coherently. Define which owner may edit each payload and when it may be reused.
3. Make consume-and-clear one coherent operation. Prevent the producer from editing an object being consumed. Render and persist outside the protected region.
4. Preserve both channels and established queue/capacity behaviour. Define acceptance/replacement/rejection explicitly for back-to-back commands.

**Traps:** making individual fields atomic does not make a snapshot coherent. Writing the flag last alone does not prevent payload reuse or consumer-clear races. Do not solve a data race by adding an arbitrary delay or allocating a new unbounded queue.

**Acceptance:** exercise legitimate rapid requests around consumption, edits during transitions and quantised commit. Each accepted request has its policy-defined disposition; each applied/saved preset equals one complete submitted version. Verify the final mode, both channels, persistence and no lost update from a clear/store race. Source checks may supplement real behavioural coverage but cannot replace it.

### Stage E — Give diagnostics correct ownership

**Entry points:** `serial/serial_menu.cpp::cmd_identify/cmd_vp_out_test`, `visual/led_utilities.h::blocking_flash`, `visual/lightshow_modes.h::vp_run_output_probe`, and the acquisition/render loops in `SPECTRASYNQ_K1_FIRMWARE.ino`.

**Established mechanism:** identify overwrites render-owned data after setting a halt flag without waiting for acknowledgement, and blocks the acquisition/serial loop with four programmed 150 ms delays. The output probe relies on a fixed 10 ms delay before changing shared state. The existing render park can force-resume after one second. The inspected probe renders and hashes software buffers; it does not itself call `show_leds()`.

**Implement**

1. Preserve `:identify` and its intended animation using a request consumed by the render owner. Advance it by the existing time/frame mechanism; return control to acquisition without the blocking delay sequence.
   The audio/acquisition loop must also continue while acknowledgement, probe completion or diagnostic output is pending. Do not replace the old delays with a synchronous wait for the render task or blocked serial output. Report completion only after the operation finishes through an appropriate existing deferred-response path.
2. Identify every live input, history, configuration and output object the probe changes. Executing it on the render core alone is insufficient if it still overwrites audio-owned data.
3. Use isolated probe inputs/history or an acknowledged ownership transfer consistent with current architecture. Ensure forced park recovery cannot invalidate the exclusive interval.
4. Preserve valid command/response behaviour and define busy, completion and timeout handling. Restore intended settings/history without overwriting a newer accepted control update.
5. Apply the current diagnostic build boundary. Removing a command is not the only ownership fix; do not defer a repair solely to ask whether the user wants the command deleted. If a real compatibility/build-policy conflict remains, identify the exact conflict and complete independent corrections.

**Acceptance:** show the command is accepted and completed through the real dispatch path, acquisition is not blocked by the programmed flash delays, render/state ownership is correct and normal output resumes. Check relevant repeated/busy/timeout behaviour and legitimate controls during the operation. Probe hashes establish software-buffer behaviour only. A target timing claim requires target evidence; host timing is insufficient.

### Stage F — Reject oversized serial fields and lines

**Entry points:** `serial/serial_menu.cpp::parse_command/check_serial` and existing serial oracle/scanner tests.

**Established mechanism:** the input layer accepts a longer line than the 93 value characters copied into the metadata buffer. Numeric validation therefore sees a truncated prefix. The full-line limit also dispatches its buffered prefix and leaves command mode, allowing remaining bytes to enter other interpretation paths.

**Implement**

1. Detect field overflow before dispatch/commit; preserve null termination and reject the complete invalid request rather than accepting its prefix.
2. On whole-line overflow, discard the remainder through its CR/LF terminator. Do not execute the prefix or reinterpret discarded suffix bytes as hotkeys or another protocol.
3. Reset the scanner correctly at LF/CRLF, and accept the next complete request. Preserve legitimate framing, supported command lengths and established valid numeric semantics.
4. Keep rejection side effects within the current command contract. In particular, there must be no setting commit, save or reboot caused by a truncated value.

**Acceptance through the actual parser/scanner:**

- `note_offset=` followed by 93 zeroes and `12` is rejected, rather than saving offset zero and rebooting.
- `saturation=0.` followed by 91 zeroes and `junk` is rejected, rather than saving a truncated zero.
- Exact supported field/line limits and one character beyond each behave as documented.
- An oversized line with hotkey-like suffix bytes causes no hotkey or unintended command action.
- The next valid command succeeds after LF and after CRLF, including input arriving in multiple chunks.

The existing test for a 40-character unknown command name is not this coverage. Exercise the byte scanner as well as direct `parse_command()` calls.

## 6. Verification plan and execution boundaries

### Existing surfaces to inspect and extend

These files were verified present. Select by the changed mechanism; this is not a command to run them all separately:

| Work | Existing test entry points |
|---|---|
| LUT | `tests/test_look_file.py`, `test_look_apply.py`, `test_look_cube.py`, `test_look_lib_static.py` |
| Persistence/show | `tests/test_show_state_static.py`, `test_k1_persistence_request_boundary.py`, existing production-code golden oracles reached by `test_golden_master.py` |
| Mode/presets | `tests/test_effect_queue_static.py` and relevant real-code host/replay seams |
| Diagnostics/ownership | `tests/test_k1_serial_safety.py`, `test_dev_instrumentation_boundary.py`, `test_k1_persist_park_static.py` |
| Serial | `tests/test_serial_input_validation.py`, `test_serial_hotkeys_static.py`, `test_serial_typed_dispatch_table_static.py`, `test_serial_menu_odr_static.py` |

Names marked static generally inspect structure. Add or extend focused behavioural checks where necessary to establish the missing property. Do not write tests that merely mirror implementation text or count a copied toy algorithm as the product.

Use actual affected profiles: `k1_fe` and `k1_fe_emu` are the expected FE pair. Include `k1_fe_bench_b489`, `k1_hardware`, Main RPL or another consumer when the dependency map or current integration gate requires it. Do not assume one successful environment covers different macros and paths.

The existing full replay command template, usable **after** Stage A reconciliation, is:

```bash
python3 tools/esp_emulator/run.py \
  --profile fe \
  --scenario tools/esp_emulator/s3_music_regression.json \
  --output _scratch/esp-emulator/<fresh-candidate-run>
```

Replace the output placeholder, use the required interpreter and follow any newly implemented/documented receipt option. Do not pass an invented option. The directory must be new. Default profile selection is Main RPL unless FE is explicitly selected. Narrowing `--suite` alone does not avoid the host checks.

Bind evidence to exact candidate content, profile/macros, toolchain, scenario/input bytes, initial state, time/random seams, control events, capture intervals, topology and power policy. Hold source stable during execution. An editor changing a manifest mid-test invalidates that test's source attribution.

Use exact output comparison where representation/operation order should remain identical. For legitimate differences, define the expected behaviour and justified tolerance first. Validate record counts, dimensions, generations and time/event alignment before numeric comparisons; handle NaN/infinity explicitly. Do not realign or average away lost/shifted events. Update golden expectations only for explained intentional contract changes.

Use available sanitizer/lifetime support where it answers the mechanism. Do not claim that sanitizer timing represents production timing or that a clean stress run proves every interleaving. Apply the current instrumentation policy: causal timing/ownership claims may require the existing dev-trace/MabuTrace path. Keep diagnostic code out of shipping configurations; if a required evidence capability is unavailable, label that criterion accurately.

### Acceptance matrix

| Criterion | Required result |
|---|---|
| Baseline/ownership | Exact current source, owner and edit surface recorded; unrelated work preserved. |
| Test policy | No prohibited firmware-mutant execution; no silent gate bypass or falsely passed exclusion. |
| LUT lifetime | No reclamation while any reader can use the payload; safe switch/failure/timeout behaviour on the actual FE feature. |
| Persistence | Invalid legacy CONFIG and show values cannot reach live consumers; healthy values and compatibility survive. |
| Requests | Complete coherent mode/preset transfers with policy-defined disposition and correct persisted outcome. |
| Diagnostics | Correct ownership and completion; identify no longer blocks acquisition with its delay sequence; probe state isolated/restored correctly. |
| Serial overflow | No prefix execution or suffix hotkeys; no commit/save/reboot on rejection; next valid line works. |
| Product/build | Actual affected consumers build; valid music/control/visual behaviour and limits remain within their contracts. |
| Integration/replay | Final candidate and required export/gate/replay receipts agree; reused host evidence is explicitly validated and labelled. |
| Hardware claims | Claimed physical properties have matching target evidence; unavailable physical checks remain explicitly open. |

Use PASS, FAIL, BLOCKED, NOT TESTED or NOT APPLICABLE with evidence and reasons. Empty intended captures, stale files, missing samples, skipped records or unrelated passing tests do not close a criterion. An intentionally empty stall case remains a distinct, legitimate lifecycle case.

## 7. Hardware and release limits

Hardware availability is not required to begin the five software fixes. Recheck actual connected devices and ownership when a device step becomes necessary; old connection records are historical.

The inspected current `k1_fe` profile targets Gx and is blocked from Main RPL. It drives a pin that conflicts with Main RPL's microphone wiring. Do not transfer the old `k1_fe` allowlist or an earlier GPIO map to the current image, bypass the guard, or borrow another lane's device connection.

B489 uses `k1_fe_bench_b489` with its own wiring. Its microphone/line-in tests do not establish Gx pin/power behaviour, and its disabled dynamic LUT feature cannot validate Stage B. FE emulator microphone replay does not qualify physical PCM1808 capture, line switching, power sequencing, LED transmission or optical behaviour.

If current authority and the right hardware permit a required check, use the established production procedure: exact target identity and configuration, agreed connection ownership, relevant recovery preparation, programming, runtime readback and leave-state record. Never flash an emulator image. Never auto-start silence-dependent calibration without the required confirmed silence window. No new per-image approval is needed when standing authority already covers the action.

Obtain only device measurements required by the changed property. Report sample count, conditions, observed distributions/maxima and misses where timing matters. A finite-run maximum is not a proven worst-case bound. An LED buffer or current-limiter calculation is not a physical optical/current measurement.

## 8. Correct and extend the record

Use the existing record at `docs/forensics/modernes-cpp-lessons-2026-11-10.md`, supported by `_scratch/modernes-cpp_20261110/LEDGER.md` and the existing evidence conventions. Keep historical receipts, failures and original source identities intact. Append dated next-phase findings and results rather than overwriting history.

Correct these specific closeout discrepancies:

- The old phrase “only board validation remains” did not account for the five software defects. Replace it with accurate dispositions as each closes.
- Baseline2's host log observed source changes during execution: new parser compilation errors, a changed constants hash and mismatched consecutive source manifests. Those three host failures are not proof of defects in a clean `e2e83e53` baseline. Its separately identified replay captures and the later clean-export pass remain useful.
- The research record contains **19 retained lessons, four partially verified** (L7, L12, L16 and L17). Do not repeat “19 verified” without further evidence. Reconcile the small 396/398 link-count discrepancy from existing records; do not restart the catalogue review.
- Record that the prior gate executed actual firmware mutants despite the current prohibition; document the bounded reconciliation. Do not relabel it as harmless anchor editing.

Historical evidence packet:

- `_scratch/modernes-cpp_20261110/commit_gate.log`
- `_scratch/modernes-cpp_20261110/catalogue/CATALOGUE.md`
- `_scratch/modernes-cpp_20261110/audit-concurrency/findings.md`
- `_scratch/modernes-cpp_20261110/audit-interfaces/findings.md`
- `_scratch/esp-emulator/mcpp-final-export-e28dd927/_out/fe-final/result.json`
- `_scratch/esp-emulator/mcpp-baseline2-fe-e2e83e53-cfgtail/result.json` and `host-pytest.log`
- `_scratch/esp-emulator/mcpp-candidate1-fe/result.json`
- `docs/handover/RECEIPT-FE-FW-2026-11-10.md`

The public source is https://www.modernescpp.com/index.php/table-of-content/. Earlier research is context; revisit a source only when a remaining implementation decision requires it. Article claims and comments do not override the actual language/platform contracts.

## 9. Integration, stopping rules and final handback

Review the final diff, affected interfaces and evidence. Use an independent reviewer on the actual accepted candidate where required; give them the five failure mechanisms and raw results, not just the previous agent's summary. Resolve substantive findings within scope.

Complete authorised local Git integration with only owned changes. Do not push, merge another owner's branch or publish a release unless current authority includes that action. Preserve current device/image state when no device operation is required.

| Real blocker | Stop this dependent action | Continue / resume condition |
|---|---|---|
| Contested source or writer ownership | Writes/integration in that surface | Continue permitted inspection; resume when ownership and baseline are resolved. |
| Required invariant/check fails | Promotion of that candidate | Diagnose and repair; resume with the same meaningful acceptance requirement satisfied. |
| Gate still invokes prohibited work or evidence cannot be attributed | That invocation/completion claim | Reconcile the specific existing workflow; continue independent implementation. |
| Target identity, owner, recovery prerequisite or authority missing | Device action | Continue software checks; resume through the current verified device procedure. |
| Required hardware/tool evidence unavailable | Only the claim that needs it | State the exact missing evidence, next action and responsible role. |

Do not treat a required software correction as optional because a generic suite passed or a board is absent. Do not relax thresholds after failure. Do not repeat a failed method without new evidence or a relevant change.

**Final delivery, in this order:**

1. A short plain-English outcome: what improved, what is now verified and what remains.
2. Disposition of all five defects and the test-workflow conflict, with exact changed paths and candidate identity.
3. Acceptance results and evidence locations, separating executed, validly reused and untested coverage.
4. Material interface, ownership, persistence or command-behaviour changes and their compatibility evidence.
5. Repository leave-state and preserved unrelated work; device leave-state if touched.
6. Any remaining numbered hardware/integration path: prerequisite, next role/owner, exact action and evidence that closes it. Do not invent an assigned person if ownership is unresolved.

Before compaction or handoff, preserve the current source identity, decisions, failed receipts, unresolved findings and the next executable action in the existing working record. The receiving agent must be able to resume without reconstructing this chat.
