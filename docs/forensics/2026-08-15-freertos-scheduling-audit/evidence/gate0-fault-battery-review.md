# FRTOS-17 — adversarial Gate 0 fault-battery review

**Date:** 2026-08-15

**Observed checkout:** `feat/k1-scheduling-generation-hardening` / `82e201972fcae6dcb8380f9aadeb3d54ad394a7c`

**Scope:** read-only review; no firmware, tests, harness, CI, build, git, serial or device action

**Verdict:** **GATE 0 NEEDS WORK — production source remains blocked until the battery below has produced an independently accepted receipt.**

A concurrent untracked draft, `gate0/contract.json`, appeared after the initial review
snapshot. It is assessed below as a draft input, not accepted evidence and not a Gate 0
receipt.

## 1. Blunt decision

The scheduling lane now has authority and a useful draft contract, but it does not yet
have a scheduling-specific, fault-evident trust root.

The active handover records Captain's direct implementation authority, limits it to this
scheduling programme, and explicitly says production source must wait until the Gate 0
harness, determinism contract and fault battery have demonstrated RED capability
(`docs/handover/HANDOVER_2026-08-15_SCHEDULING_HARDENING_IMPLEMENTATION.md:13-26,61-66`).
This supersedes the older scheduling hold without declaring the separate AP-input P4
complete. Therefore:

```text
SCHEDULING_IMPLEMENTATION_AUTHORITY = PRESENT
AP_INPUT_P4                         = OPEN, SEPARATE, NOT IMPLIED COMPLETE
PRODUCTION_SOURCE_ENTRY             = BLOCKED ON GATE_0 RECEIPT
CURRENT_GATE_0_RECEIPT              = ABSENT
```

The plan's Gate 0 list is directionally correct: it requires exact provenance, timing
contracts, frozen hashes, acceptance ownership and rejection of wrong provenance,
trace, generation, fixture, test, stream and identity inputs
(`EXECUTION_PLAN.md:320-354`). It is not executable yet. A prose list of faults is not a
fault battery.

### 1.1 Adversarial review of the concurrent contract draft

`docs/forensics/2026-08-15-freertos-scheduling-audit/gate0/contract.json` is a useful
start: it separates the AP-input P4 lane, locks AP0/VP1, declares the 12.8 kHz/96/d3
tuple, names whole-frame and feature boundaries, lists required trace fields and names
fault classes (`contract.json:1-27,28-55,57-167`). It is **not yet freezeable**:

1. provenance omits the authority handover digest/base SHA, full implementation SHA,
   source-manifest hash, platform URL, board/framework, resolved-flag digest, tool hashes,
   fixture hashes, required nodeids and physical/runtime identity tuple;
2. `production_tuple` omits DMA descriptor count and explicit AP/VP cores even though
   those are decision-critical compile inputs;
3. `required_trace_fields` omits AP stage spans and final quantised-byte identity, so a
   trace can jump from render start to RMT submission without proving which bytes were
   sent; it also has no explicit completion-observation kind, allowing submit time to be
   copied into a field named completion;
4. the required-fault list omits absent/drifted authority, dirty tree, trust-root drift,
   missing/deselected/xfail distinctions, deterministic repeatability, causal timestamp
   order, fabricated RMT completion and corrupt-generation subtypes;
5. numeric margins and feature budgets have no recorded owner or provenance. Some are
   defensible pre-registered safety margins, but `25,000 us`, `35,000 us`, p99 `6,000 us`,
   one miss/two recovery frames and the 2%/5% lock fractions cannot become product
   authority merely by appearing in JSON. Captain must ratify product-facing budgets;
   the independent harness owner must identify the engineering basis for internal
   margins. Gate 1 may bind measurements to pre-registered formulae but may not silently
   retrofit numbers after results.

The draft therefore becomes the canonical contract location after these amendments; do
not create a parallel contract in test fixtures.

## 2. Why existing machinery is insufficient

Reusable parts exist, but none closes scheduling Gate 0 by itself:

| Existing surface | Reuse | Disqualifying gap for scheduling Gate 0 |
|---|---|---|
| Golden-master manifest check | SHA-256 comparison and exact field-set comparison (`tests/test_golden_master.py:54-80`) | The golden, its manifest, the oracle registry and CI live in the same writable repository. Changing both file and manifest can pass unless an independently supplied trust SHA rejects the edit. |
| Generic Gate F-alpha self-test | Runs two captures for determinism and applies source mutations in a temporary firmware copy (`scripts/regression-harness/golden/harness_selftest.py:141-200`) | No scheduling oracle is registered. `oracle_semantic_state` is explicitly disabled pending repair (`harness_selftest.py:93-101`). |
| Wireless `gate0_selftest.py` | Good pattern: known-bad fixtures must be rejected and a good control admitted | It explicitly governs the wireless A/B admission lane, not scheduling (`scripts/regression-harness/gate0_selftest.py:2-22`). Reusing its name or receipt would create false authority. |
| Build provenance stamp | Runtime `git`, epoch and environment fields | It deliberately degrades git/environment to `unknown` and must never fail a build (`scripts/platformio/k1_build_provenance.py:10-19,34-55`). That is useful metadata, not fail-closed acceptance. It also carries a short SHA, not the required full implementation SHA. |
| Runtime build identity guard | Rejects git/environment/epoch mismatches (`scripts/regression-harness/k1_device_identity_guard.py:90-112`) | It does not establish USB serial or chip identity. It must be composed with the upload identity manifest/guard, not treated as complete identity. |
| Upload identity guard | Already rejects a wrong USB identity and proves its verdict tracks manifest data (`tests/test_k1_upload_guard_identity_static.py:68-71,108-127`) | It validates an environment-to-USB mapping before upload; it does not prove which binary is currently answering or that a capture came from the expected build epoch. |
| Current CI | Runs the golden/self-test pair and full pytest suite (`.github/workflows/ci.yml:13-34`) | No repository `CODEOWNERS` or in-repo branch-protection evidence was found. The workflow is therefore evidence, not an immutable trust root. Default pytest success also permits skips. |
| Stable-section byte gate | Correctly excludes known nondeterministic ELF sections (`scripts/regression-harness/mic_stable_byte_gate.sh:3-28`) | It performs builds, has an in-band `--update` path and governs byte-inert microphone environments. It is not the scheduling contract or a Gate 0 offline self-test. |

The current shipping tuple is visible in `platformio.ini`: default environment
`k1_hardware`, pioarduino `54.03.20`, ESP32-S3 N16R8 board, AP/Core 0,
VP/Core 1, DMA descriptor count 3, 12.8 kHz and 96 samples per chunk
(`platformio.ini:14-30,59-77`). Gate 0 must compare the **resolved** configuration,
not merely grep those lines; inheritance, unflags and later flags can change the actual
compile tuple.

## 3. Domain and contradiction resolution

- **Cynefin:** authority, hashes, identities, field presence, forbidden streams and
  test outcomes are clear-domain comparisons: exact match or RED. Concurrency
  ownership is complicated and belongs to the Gate 3 interleaving oracle. Scheduler
  interference and perceptual timing are complex and belong to paired device probes,
  not Gate 0 guesses.
- **TRIZ:** separate the approved expectation from the observed fact. The contract is
  frozen by the harness owner; the independent runner reads git/config/test/device
  state itself. A candidate may not submit both `expected` and `actual` values.
- **Systems:** a green unit test is not the trust loop. The closed loop is
  `frozen contract -> independent observation -> same evaluator -> signed receipt ->
  post-integration rerun`. Allowing the production lane to edit any earlier element
  creates a reinforcing self-certification failure.
- **Margin of safety:** identity, authority, schema, ordering and checksums have zero
  tolerance. Gate 0 must not invent AP/VP timing margins. Those values are frozen only
  after exact-head Gate 1 establishes distributions, tails and recovery sequences.

## 4. Minimum executable trust root

Create the first five inputs in one **harness-owner** commit before any
production-source commit. The independent runner produces the sixth file only after
acceptance; a receipt is output, never part of the oracle that accepts itself.

```text
scripts/agent/k1_scheduling_gate0.py
tests/test_scheduling_gate0_fault_battery.py
docs/forensics/2026-08-15-freertos-scheduling-audit/gate0/contract.json
docs/forensics/2026-08-15-freertos-scheduling-audit/gate0/known_good_trace.ndjson
docs/forensics/2026-08-15-freertos-scheduling-audit/gate0/required_nodeids.txt
independent output -> docs/forensics/2026-08-15-freertos-scheduling-audit/gate0/GATE0_RECEIPT.json
```

`k1_scheduling_gate0.py` is one evaluator with three entry points:

1. `evaluate(contract, observation) -> {verdict, reason_codes, evidence_digest}` —
   pure, no clock, RNG, network, serial or environment fallback;
2. `selftest` — copies the known-good package to a temporary directory, applies one
   mutation at a time, calls the same evaluator and records the **inner** verdict;
3. `verify` — production path; reads repo/config/JUnit/fixture facts itself. It must not
   expose `--observed-sha`, `--observed-flags`, `--observed-device` or another override
   with which a candidate can make expected and observed agree.

The top-level self-test exits 0 only when the good control is GREEN and **every injected
bad case made the inner gate exit 2/RED with its expected reason code**. The receipt must
retain those inner RED verdicts; a summary `pytest PASS` alone is inadequate evidence.

### 4.1 Frozen contract fields

At minimum the contract contains:

```text
authority_receipt_id, authority_handover_sha256, authorised_branch, authority_base_sha
source_manifest_sha256, clean_tree_required, implementation_full_sha_required
platform_url, board, framework, environment, resolved_build_flags_sha256
sample_rate_hz, samples_per_chunk, dma_descriptor_count, ap_core, vp_core
tool names + exact versions/hashes used by the accepting run
fixture paths + sha256, required pytest nodeids
capture leg, explicitly allowed streams, forbidden/perturbing streams
expected USB serial, chip id, role, runtime git prefix, environment and build epoch
required trace schema, timestamp ordering rules and generation invariants
```

`gate0_trust_sha` and the actual `implementation_full_sha` are deliberately absent as
literal values from the committed contract: a file cannot non-recursively contain the
SHA of the commit containing itself, and later candidates necessarily have later SHAs.
The independent orchestrator supplies the accepted trust SHA out of band, reads the
candidate HEAD itself before and after the run, and records both full SHAs in the
acceptance receipt.

The full implementation SHA is captured for every accepting HEAD; it is not permanently
hard-coded to the pre-production Gate 0 commit. A later decision-critical source,
configuration or fixture change invalidates the earliest affected receipt as required by
`EXECUTION_PLAN.md:101-104`.

### 4.2 Required causal trace schema

The minimal complete record is:

```text
boot_epoch
capture_sequence
i2s_read_return_us
oldest_sample_estimate_us
newest_sample_estimate_us
sample_time_assumption_id
ap_stage_spans_us
ap_generation
ap_publish_us
vp_acquire_us
render_start_us
final_quantised_bytes_sha256
rmt_submit_us
rmt_complete_us
```

For a record carrying generation `N`, every generation-stamped payload field must be
`N`. Times are monotonic within `boot_epoch`; `rmt_complete_us >= rmt_submit_us`, and
submission is never accepted as completion. These fields instantiate the plan's causal
identity (`EXECUTION_PLAN.md:223-238`) without claiming that their device producers exist
yet.

## 5. Minimum fault battery

One parametrised test function may carry all rows; “minimum” means one evaluator and one
mutation table, not one vague mutation per broad category. Field and tuple members are
parameterised individually so one working comparison cannot hide four dead comparisons.

| ID | Mutation applied to a temporary copy / synthetic observation | Required inner result |
|---|---|---|
| `AUTH-01` | Remove the Captain scheduling authority receipt or change its digest. | RED `AUTHORITY_MISSING_OR_DRIFTED`. |
| `AUTH-02` | Set branch outside `feat/k1-scheduling-generation-hardening` or make HEAD not descend from authority base `82e20197...`. | RED `AUTHORITY_LINEAGE_MISMATCH`. |
| `PROV-01` | Change one hex digit of observed full HEAD SHA; also exercise `unknown`/short SHA. | RED `IMPLEMENTATION_SHA_MISMATCH`. |
| `PROV-02` | Present a dirty decision-critical path after the runner captures HEAD. | RED `WORKTREE_NOT_CLEAN`; uncommitted evidence is not admissible. |
| `PROV-03[*]` | Mutate platform URL, board, framework, environment, one resolved build flag or tool version/hash, one member at a time. | RED `BUILD_PROVENANCE_MISMATCH`. |
| `TUPLE-01[*]` | Individually mutate `12800`, `96`, DMA `3`, AP core `0`, VP core `1`. | RED `EXECUTION_TUPLE_MISMATCH` for every member. |
| `FIX-01` | Flip one byte in a frozen fixture while leaving the expected digest unchanged. | RED `FIXTURE_HASH_MISMATCH`. |
| `TRUST-01` | Change the evaluator, its fault test, required-node ledger, CI gate or contract relative to the independently supplied `gate0_trust_sha`. | RED `TRUST_ROOT_DRIFT`. |
| `TEST-01` | Delete one required nodeid or make collection return fewer nodeids. | RED `REQUIRED_TEST_MISSING`. |
| `TEST-02` | Mark one required test skipped, xfailed, deselected or non-strict XPASS in synthetic JUnit. | RED `REQUIRED_TEST_NOT_EXECUTED`. |
| `TEST-03` | Give a required test failure/error or a pytest non-zero collection/run exit. | RED `REQUIRED_TEST_FAILED`. |
| `TRACE-01[*]` | Delete each required trace field in turn. | RED `TRACE_SCHEMA_INCOMPLETE` for every field. |
| `TRACE-02` | Reorder/regress one causal timestamp or set RMT completion earlier than submission. | RED `TRACE_CAUSAL_ORDER_INVALID`. |
| `TRACE-03` | Copy submit time into completion without an independently marked completion observation. | RED `RMT_COMPLETION_UNPROVEN`. |
| `GEN-01` | Stamp one payload field `N-1` inside generation `N`. | RED `MIXED_GENERATION`. |
| `GEN-02` | Move an accepted generation backwards within one boot epoch. | RED `GENERATION_REGRESSION`. |
| `GEN-03` | Publish two different payload digests under the same AP generation. | RED `GENERATION_REUSED`. |
| `PERT-01` | Enable any stream in the minimally instrumented control leg. | RED `PERTURBING_STREAM_ENABLED`. |
| `PERT-02` | Enable an undeclared stream in the instrumented leg. | RED `UNDECLARED_STREAM_ENABLED`. |
| `ID-01[*]` | Individually mismatch USB serial, chip ID or nominated role. | RED `PHYSICAL_IDENTITY_MISMATCH`. |
| `ID-02[*]` | Individually mismatch runtime git prefix, environment or build epoch. | RED `RUNTIME_IDENTITY_MISMATCH`. The prefix must uniquely resolve to the independently recorded full HEAD; `unknown` is never admissible. |
| `DET-01` | Evaluate the untouched good package 20 times, then the complete mutation table twice. | Good verdict/digest byte-identical on all 20 runs; each fault's verdict/reason/digest byte-identical across both passes, else RED `NONDETERMINISTIC_GATE`. |
| `CTRL-01` | Untouched, hash-valid, complete known-good synthetic package. | GREEN. This kills an always-reject gate and proves the fault battery is not merely a denial mechanism. |

The required node ledger starts with the complete new scheduling fault module plus these
reusable teeth:

```text
tests/test_golden_master.py::GoldenMasterTest::test_manifest_integrity
tests/test_k1_device_identity_guard.py::test_foreign_build_is_rejected_on_git
tests/test_k1_device_identity_guard.py::test_foreign_build_is_rejected_on_env
tests/test_k1_device_identity_guard.py::test_epoch_mismatch_is_caught
tests/test_k1_upload_guard_identity_static.py::test_wrong_identity_rejected
tests/test_k1_upload_guard_identity_static.py::test_gate_falpha_decision_tracks_identity_data
```

The runner executes explicit nodeids with `xfail_strict=true`, writes JUnit, requires
`tests == ledger count`, `skipped == errors == failures == 0`, and rejects any pytest
collection/run return code. Ordinary `pytest tests/` is additive coverage, not a
substitute for this exact-ledger check.

## 6. Exact candidate commands

These commands are the required future harness-owner/independent-runner sequence. They
were **not** run in this read-only review.

```bash
cd /Users/spectrasynq/SpectraSynq_K1_Firmware
test "$(git rev-parse --show-toplevel)" = "/Users/spectrasynq/SpectraSynq_K1_Firmware"
test "$(git branch --show-current)" = "feat/k1-scheduling-generation-hardening"
git merge-base --is-ancestor 82e201972fcae6dcb8380f9aadeb3d54ad394a7c HEAD
test -z "$(git status --porcelain --untracked-files=all)"

K1_GATE0_TMP="$(mktemp -d)"
python3 -m pytest -q -o xfail_strict=true \
  tests/test_scheduling_gate0_fault_battery.py \
  --junitxml="$K1_GATE0_TMP/fault-battery.junit.xml"

python3 scripts/agent/k1_scheduling_gate0.py selftest \
  --contract docs/forensics/2026-08-15-freertos-scheduling-audit/gate0/contract.json \
  --repeat 20 \
  --junit "$K1_GATE0_TMP/fault-battery.junit.xml" \
  --receipt "$K1_GATE0_TMP/gate0-selftest.json"
```

After the harness-owner commit is independently reviewed, the orchestrator records its
full commit as `K1_GATE0_TRUST_SHA` outside candidate-controlled input and runs:

```bash
cd /Users/spectrasynq/SpectraSynq_K1_Firmware
K1_GATE0_TRUST_SHA="<full independently accepted harness commit SHA>"

git diff --exit-code "$K1_GATE0_TRUST_SHA" -- \
  scripts/agent/k1_scheduling_gate0.py \
  tests/test_scheduling_gate0_fault_battery.py \
  docs/forensics/2026-08-15-freertos-scheduling-audit/gate0/contract.json \
  docs/forensics/2026-08-15-freertos-scheduling-audit/gate0/known_good_trace.ndjson \
  docs/forensics/2026-08-15-freertos-scheduling-audit/gate0/required_nodeids.txt \
  docs/handover/HANDOVER_2026-08-15_SCHEDULING_HARDENING_IMPLEMENTATION.md \
  .github/workflows/ci.yml

pio project config --json-output > "$K1_GATE0_TMP/platformio-resolved.json"

python3 scripts/agent/k1_scheduling_gate0.py verify \
  --repo /Users/spectrasynq/SpectraSynq_K1_Firmware \
  --contract docs/forensics/2026-08-15-freertos-scheduling-audit/gate0/contract.json \
  --trust-sha "$K1_GATE0_TRUST_SHA" \
  --resolved-platformio "$K1_GATE0_TMP/platformio-resolved.json" \
  --receipt "$K1_GATE0_TMP/gate0-acceptance.json"
```

`verify` must itself run the required-node ledger and parse its JUnit result; the command
must not trust a candidate-provided statement that tests ran. The final accepted receipt
is copied into the named Gate 0 receipt only by the independent gate runner after checking
that the evidence digest matches.

No upload, flash, serial open or device command belongs in this Gate 0 self-test. `ID-*`
uses synthetic observations to prove the admission logic. At Gate 1 and later, the same
logic must consume independently read USB/chip identity plus the runtime `:build` reply
before admitting a device capture.

## 7. Acceptance ownership and anti-gaming

| Owner | Owns | May not do |
|---|---|---|
| Captain | scheduling authority, product timing definitions, physical/audible/perceptual authority | Be represented by an agent-created inference or a stale handover. |
| Harness owner | evaluator, known-good fixtures, mutation table, node ledger and initial trust-root commit | Author or accept the production scheduling unit it will judge. |
| Independent gate runner/orchestrator | clean-worktree observation, explicit test execution, trust-SHA comparison, evidence digest and acceptance receipt | Accept candidate-supplied `actual` values or waive a RED/skip/nondeterministic result. |
| Production lane agent | one bounded scheduling implementation unit and its ordinary tests | Modify the evaluator, fixtures, required-node ledger, acceptance thresholds, CI gate, authority receipt or accepted trust SHA; self-certify; rebaseline. |
| CI | reproduce host checks on the integrated HEAD | Count as the sole trust root until the required job and its workflow are protected outside production-lane write authority. |

The in-repo checksum manifest is useful corruption detection, not sufficient anti-gaming.
The independently supplied accepted commit SHA is the bootstrap trust anchor. Any intended
change to a protected path is a separate harness-owner change, repeats the full battery,
and produces a new Gate 0 trust receipt before production resumes.

## 8. Binary stop rules

Stop the entire production fleet before the first production-source edit when any of the
following is true:

1. the good control is not GREEN;
2. any injected fault returns GREEN, the wrong RED reason, crashes, or is not executed;
3. any deterministic replay differs across the required repetitions;
4. the current HEAD/branch/authority lineage is ambiguous, dirty or not the recorded one;
5. a required test is absent, skipped, xfailed, deselected, non-strict XPASS, failed or
   unreported;
6. the trust-root diff is non-empty or `K1_GATE0_TRUST_SHA` is absent/candidate-supplied;
7. resolved build provenance/tuple is absent, `unknown` or mismatched; the accepting
   receipt lacks a full HEAD, or a runtime git prefix does not uniquely resolve to it;
8. a fixture, schema, trace, generation, stream or device/build identity fault is admitted;
9. a production lane asks to update a golden, threshold, manifest or receipt to make its
   candidate pass;
10. the independent runner cannot reproduce the self-test and evidence digest in a clean
    post-integration worktree.

An uncaught fault is an oracle defect, not a waiver discussion. Return to Gate 0, repair
the smallest blind spot, rerun the complete battery, and issue a new trust receipt. A RED
production candidate is reverted as one atomic unit; do not weaken the gate or combine it
with a behaviour-change ticket.

## 9. Residual gaps after this battery passes

Passing this battery would prove only that the Gate 0 admission machinery rejects the
named fault classes in its measured envelope. It would **not** prove:

- real ESP32 `portMUX` contention, cache-disable behaviour, WDT/IDLE health or task
  scheduling;
- AP service demand, sample age, backlog recovery, 120 FPS whole-frame performance,
  lock/copy cost or RMT completion timing;
- that the future generation/event implementation is correct under forced interleaving;
- that a USB identity cannot be spoofed, or that a runtime build reply is sufficient
  without an independently read chip identity;
- that instrumentation is non-perturbing merely because forbidden streams are absent;
  paired minimal/instrumented device legs remain required;
- acoustic-to-photon latency, musical responsiveness, colour quality or Captain-visible
  product value;
- faults outside the injected classes, including errors in an apparently valid frozen
  contract.

Those are deliberate later gates. Gate 0 must not absorb them into a cathedral-sized
harness or claim them from host fixtures. Its job is narrower and binary: establish
authority, freeze a deterministic trust root, and prove that the gate can say **NO** for
every required bad input before production code is allowed to exist.

## 10. Review proof

**Files changed:** only this review.

**Build/tests/device:** not run; prohibited by FRTOS-17.

**Current blocker:** the concurrent contract draft is incomplete and unaccepted; no
scheduling-specific evaluator, frozen trust SHA, deterministic self-test receipt or
independently accepted Gate 0 receipt exists yet.

**Next mechanical truth:** harness owner implements the five protected inputs above;
independent runner captures `CTRL-01=GREEN`, every fault row's inner verdict as RED, and
`DET-01` as byte-identical before the first production-source unit begins.
