# Modernes C++ investigation and implementation plan

**Agent:** Opus. **Project:** `/Users/spectrasynq/SpectraSynq_K1_Firmware`.

**Objective:** extract useful, technically correct lessons from Modernes C++, apply them to actual K1 weaknesses, and deliver verified improvements. Execute this plan through implementation and closeout. Evidence that an existing implementation is already sound is a valid no-change result.

**Scope:** active ESP32-S3 Founders' Edition firmware and its existing emulator. Survey every catalogue topic family; investigate relevant articles deeply. Other platforms remain reference material unless current authority explicitly opens their implementation lane.

**Primary source:** https://www.modernescpp.com/index.php/table-of-content/

## Operating rules

- Preserve unrelated staged, unstaged and untracked work. The project was dirty when this plan was prepared; recheck it. HEAD alone does not identify a dirty candidate.
- Preserve musical response, visual language, actual device topology, protocol/persistence compatibility, brightness and power policy. Explain and verify any intentional correction to faulty behaviour.
- Follow current applicable project instructions and existing authority. Resolve old document conflicts against the active implementation and current direction. Do not invent another approval for authorised work.
- Carry forward the current restrictions on new development worktrees, planted-fault/mutation campaigns, wasteful whole-suite reruns, Wi-Fi product/control paths and new agent infrastructure. Check for an applicable superseding instruction before acting.
- Use existing tools, runners and evidence conventions. No speculative toolchain upgrade, new test platform or broad stylistic rewrite.
- Keep emulator and production-device procedures separate. Never flash an emulator image. Preserve applicable device identity, ownership, calibration and recovery requirements.
- Stop only a genuinely blocked dependent action; continue useful independent work. Do not stop after writing another plan when an in-scope correction can be implemented.

## Phase 1 — Establish the actual baseline

**Actions**

1. Read applicable `/Users/spectrasynq/.claude/CLAUDE.md`, repository `AGENTS.md`, `CLAUDE.md`, `.claude/CLAUDE.md`, `AGENT_OS.md`, and `docs/agent/AGENT_EXECUTION_STANDARD.md`. Follow the relevant current handoff from `docs/spec-index.md` and `.claude/handoff.md`.
2. Resolve the approved writable checkout and its owner. Start discovery in the project root; an existing repair worktree is not automatically your edit surface. Do not change another active agent's checkout or branch.
3. Record branch, commit, relevant working/index differences, selected profile and affected consumers. Resolve current HOLD/parking instructions; this task does not reopen Titan or other parked programmes.
4. Read `platformio.ini` and `tools/esp_emulator/README.md`. Establish effective compiler, SDK, language mode, optimisation and floating-point flags from real build configuration. Verify newly proposed facilities against that toolchain.
5. Use one existing task/evidence record for source identity, research coverage, findings and results. Add focused code/tests where warranted; do not create overlapping tracking systems.

Read-only discovery commands:

```bash
cd /Users/spectrasynq/SpectraSynq_K1_Firmware
/usr/bin/git branch --show-current
/usr/bin/git rev-parse HEAD
/usr/bin/git status --short
/usr/bin/git diff --name-status
/usr/bin/git diff --cached --name-status
/usr/bin/git worktree list --porcelain
```

**Load these skills from** `/Users/spectrasynq/Workspace_Management/Software/agent-skills/skills/<name>/SKILL.md`:

| When | Skills |
|---|---|
| Startup and build selection | `firmware-c-cpp`, `runtime-target-source-truth`, `spectrasynq-build-system` |
| Before replay | `k1-esp-emulator-replay`; also read `/Users/spectrasynq/Workspace_Management/Software/SpectraSynq-ESP-Emulator/docs/LESSONS.md` |
| Audio, concurrency or live-path changes | Relevant `spectrasynq-audio-pipeline`, `esp32-actor-model`, `esp32-render-path-safety` |
| Timing, DSP or interface claims | Relevant `firmware-profiling` or `dsp-performance-profiling`, `signal-processing-verification`, `protocol-contract-verification` |
| Effect changes or a reproducible failure | Relevant `k1-effect-development`, `systematic-debugging` |

Before audio, visual or core-timing changes, read the repository-local `.claude/skills/sensorybridge-doctrine/SKILL.md`. Load references when needed. Use Deja for a concrete recurring error or prior decision. Use Backplane only through an existing documented project integration; its installed launcher is not evidence of a firmware orchestration API.

**Complete when:** source identity, write ownership, applicable instructions and affected build/replay profiles are established.

## Phase 2 — Survey the catalogue and verify useful claims

**Actions**

1. Account for every topic family and substantive series in the catalogue. Mark each relevant to FE, relevant to host/replay, conditional, historical/unsupported, or outside scope. Record date and coverage limitations.
2. Read selected relevant articles, including code, corrections and related instalments needed to settle the question. Admit additional useful topics beyond the five starting themes below.
3. Verify consequential claims against primary language/compiler/vendor documentation matched to the actual target. Distinguish published guarantees, proposals, illustrative examples and recommendations.
4. Record each retained lesson as: `source → verified rule → K1 question/location → adopt/adapt/already covered/reject/defer → expected benefit and risk`.
5. Keep metadata screening separate from technical review. Report the coverage denominator. Retain concise original summaries and links; do not rehost articles or ingest the whole site into agent instructions.

**Carry forward these source corrections:** the [volatile article](https://www.modernescpp.com/index.php/ongoing-optimization-locks/) does not establish portable synchronization or cache coherence; the [spinlock example](https://www.modernescpp.com/index.php/acquire-release-semantic/) has no two-thread threshold requiring stronger ordering; the [C++20 contracts post](https://www.modernescpp.com/index.php/c-core-guidelines-a-detour-to-contracts/) is historical; the [array article](https://www.modernescpp.com/index.php/std-array-dynamic-memory-no-thanks/) misnames the exception, which is `std::out_of_range`; [`constexpr`](https://www.modernescpp.com/index.php/constexpr-functions/) alone does not force compile-time execution or flash placement. Relevant primary references appear at the end. These are source corrections, not established K1 defects.

**Complete when:** all catalogue families have a disposition and useful retained claims have verified applicability.

## Phase 3 — Map lessons to real K1 findings

**Actions**

1. Trace acquisition → processing → feature publication → rendering → packing/output, plus control and persistence paths that affect them.
2. Map actual boundaries: producer/consumer, task/ISR/DMA/core context, payload, owner, publication/reuse, capacity, overload/reset policy and timing requirement.
3. Establish actual sample rate, block/window/hop sizes, frame geometry and output cadence. Use implementation evidence, not stale descriptions or assumed FFT architecture.
4. Classify each finding: **DEFECT**, **MISSING PROTECTION**, **MISSING EVIDENCE**, **ALREADY COVERED**, **INAPPLICABLE**, or **DEFERRED**.
5. For each actionable finding state: requirement, exact location, mechanism, evidence, smallest correction, affected consumers and acceptance check. For uncertainty, name the check that would confirm or disprove it.

Prioritise consequential correctness/lifecycle defects, demonstrated resource or determinism problems, then proportionate safeguards. A search match for `volatile`, `new`, `atomic` or a raw pointer is not itself a defect.

**Complete when:** research has become bounded, code-specific work packages with clear decisions.

## Phase 4 — Establish the relevant before-state

**Actions**

1. Reuse existing evidence only when source, dirty inputs, profile, fixture and conditions match. Otherwise run the smallest existing build/check that establishes the required baseline. Separate pre-existing failures.
2. Bind comparisons to exact input/PCM, rate/format, initial state, time, random seed where applicable, control events, capture interval, topology, brightness and power policy.
3. Declare exact comparisons or justified numerical tolerances before judging the candidate. Define intentional differences for bug corrections independently of candidate output.
4. Establish resource/timing baselines only where changes affect them. Derive release intervals from the actual block/hop and sample rate; the analysis window is not automatically the scheduling interval.

Existing FE replay command template; replace the output placeholder and use the interpreter required by the current tool:

```bash
python3 tools/esp_emulator/run.py \
  --profile fe \
  --scenario tools/esp_emulator/s3_music_regression.json \
  --output _scratch/esp-emulator/<fresh-run-name>
```

The default replay profile is Main RPL. Explicit FE selection matters. Inspect current runner/options/scenario before execution, including conflicts between older planted-negative/repeat instructions and current policy. Use a new output directory and existing result/capture/build-log machinery.

FE microphone replay does not qualify physical PCM1808 acquisition, resampling, jack switching, power sequencing or LED transmission.

**Complete when:** each proposed correction has the baseline needed to judge its effect.

## Phase 5 — Implement justified improvements

Work through the following areas. Additional applicable themes receive the same source evidence, minimum-change and acceptance treatment. Group edits by cause; verify each dependent change before adding another.

| Area | Investigate and implement | Required proof |
|---|---|---|
| Ownership and concurrency | Writers/readers; complete compound operations; publish/consume ordering; reuse and DMA completion; coherent settings; reset/generation; ISR and atomic legality. Repair the existing suitable primitive. Do not casually replace an RTOS queue with custom lock-free code. | Relevant empty/full/wraparound/lifecycle cases; payload identity, uniqueness and permitted ordering; accounted acceptance/rejection/completion/drop/in-flight states. Balanced totals alone cannot exclude paired loss and duplication. |
| Memory and lifetime | Startup versus steady-state allocation; transitive calls/destruction; asynchronous lifetime; fixed storage, stack/linker placement, alignment and DMA eligibility. Use scoped or move-only ownership where it fixes a real gap. | Correct cleanup/exhaustion, no premature reuse and established memory/stack budgets. Allocation claims require inspection or a complete scoped trace, not only before/after free-heap readings. |
| Configuration | Trace constants to authority; add narrow, overflow-safe assertions for real relationships. Preserve dynamic checks and generated configuration. Require power-of-two sizes only where the actual algorithm needs them. | Supported affected configurations build. Assertions encode established requirements. Claimed constant-evaluation/placement gains appear in actual output. |
| Types and interfaces | Distinguish meaningful domains/units. Parse, validate before narrowing, then commit. Preserve IDs, widths, byte order, scaling, framing, saved settings and transaction behaviour. | Existing valid fixtures remain compatible; relevant unknown, truncated, out-of-range and non-finite inputs follow policy without partial state corruption. |
| Replay and numerical behaviour | Execute production code through existing input/time/random/output seams. Preserve history/reset, warm-up, event ordering, EOF, rounding, saturation and actual arithmetic flags. Localise differences to the earliest affected stage. | Controlled replay covers the intended records and actual candidate. Check dimensions, identities, timestamps and non-finite values before tolerances. Reject truncated or misaligned comparisons; do not hide shifted events with averaging or realignment. |

Do not blindly change algorithms, sample rate, effect tuning or arithmetic order. The inspected configuration already included `-ffast-math` followed by `-fno-finite-math-only`; investigate effective product objects rather than assuming an old problem persists. Host tests must not substitute a safer reimplementation for the product code under review.

**Complete when:** in-scope defects/protection gaps are repaired and focused checks pass; no-change findings are closed with evidence.

## Phase 6 — Verify the final candidate

Run affected builds and relevant regression/replay checks. Run the required integrated gate at the appropriate integration point. Diagnose failures before repeating; broaden testing only for a concrete remaining risk or mandatory gate.

| Criterion | Pass requirement |
|---|---|
| Identity and scope | Results identify the actual candidate, dirty inputs, profile and preserved unrelated work. |
| Build and compatibility | Required consumers compile/link; protocols, settings and supported configurations retain their contract. |
| Correctness and resources | Changed ownership/lifetime/input paths pass meaningful cases and established budgets. |
| Replay | Intended nonempty coverage ran; controlled comparisons meet predeclared criteria. |
| Timing and device behaviour, where required | Correct identified target, production-representative conditions, established deadline/drop policy and preserved product behaviour. |
| Integration | Final accepted source is reproduced by the applicable project gate/export procedure. |

Use PASS, FAIL, BLOCKED, NOT TESTED or NOT APPLICABLE with evidence and reasons. Missing records, stale output, empty cases or skipped parsing cannot pass. Preserve failed results; never relax criteria after seeing a failure.

Use existing sanitizer support for relevant correctness questions. Apply the current instrumentation policy; when causal attribution requires the existing dev-trace/MabuTrace lane, use it or mark the dependent claim blocked. Keep diagnostic builds separate from production. Instrumented host runs do not establish target timing, DMA coherence or physical output.

If hardware checks are required and authorised, follow `docs/hardware/device-build-registry.md` and the current production procedure: exact identity/configuration, coordinated connection ownership, applicable recovery/calibration rules, runtime readback and restoration. Do not use stale device mappings from this plan or automatically initiate silence-dependent calibration.

Report observed timing with workload, sample count, distribution, maximum and misses; do not call a finite-run maximum worst-case execution time. Preserve actual topology, musical output, rainbow prohibition and brightness/power limits; no sustained full-white requirement.

**Complete when:** required checks for the actual candidate pass; any unavailable evidence is explicitly bounded.

## Phase 7 — Integrate and hand back the result

1. Review the final diff and complete authorised local integration. Stage only owned changes; follow current commit/publication rules. Any required clean export must include the accepted candidate, including relevant previously dirty inputs.
2. Add durable verified guidance beside the relevant existing project contract/tests. Avoid new global skills, hooks or parallel documentation systems.
3. Finish the single working record: catalogue coverage, retained/rejected claims, findings, changes, commands, outcomes and evidence locations. Separate source, host, emulator and device claims.
4. Report in plain English: **what improved; what was already correct; what passed; what remains**. Include exact changed paths, candidate identity and repository/device leave-state.
5. For every blocker give the prerequisite, completed work, next owner/role, exact action and evidence needed to resume. If all applicable requirements are already satisfied, report an evidence-backed no-change result.

**Finish condition:** useful applicable findings have been implemented and verified, or each dependent remainder has a concrete blocker and resumption path. A research-only summary or another plan does not complete executable implementation work.

## Primary verification references

- [C++ Core Guidelines](https://isocpp.github.io/CppCoreGuidelines/CppCoreGuidelines)
- [GCC volatile semantics](https://gcc.gnu.org/onlinedocs/gcc/Volatiles.html)
- [Atomic ordering](https://eel.is/c++draft/atomics.order) and [atomic_flag](https://eel.is/c++draft/atomics.flag)
- [Sequence access requirements](https://eel.is/c++draft/sequence.reqmts) and [constexpr rules](https://eel.is/c++draft/dcl.constexpr)
- [ESP32-S3 C++ support](https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-guides/cplusplus.html), [FreeRTOS](https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-reference/system/freertos_idf.html), and [memory synchronization](https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-reference/system/mm_sync.html)

Match online language/vendor references to the pinned implementation before applying version-specific behaviour. This plan can be executed without access to earlier chat or the longer HTML brief.
