# FRTOS-18 — independent Gate 0 acceptance

**Date:** 2026-08-15  
**Owner:** FRTOS-18, independent Gate 0 acceptance runner  
**Verdict:** **REJECT**

The Gate 0 checks are reproducibly green at the exact anchored commit
`190479128fcfb907c2b04749ea8a43d3d36be322` on
`feat/k1-scheduling-generation-hardening`. The checkout was clean at entry and the
branch was exactly `0/0` relative to its configured upstream. All six trust-root files
matched, all 30 scheduling Gate 0 tests passed, all 21 registered mutations were
rejected for their registered inner reason, and three good-control CLI runs produced
identical stdout and exit status. Those green results are insufficient for acceptance:
the source-population test hard-codes the **current live source count** to `537`, so the
Gate 0 suite will reject any legitimate later Gate source or test addition. The oracle
therefore cannot remain green while admitting the authorised Gate 1-8 implementation
programme.

This receipt rejects the **host Gate 0 oracle and its frozen contract**. It is not
firmware-build, device-runtime, physical-RMT, acoustic-to-photon, latency, scheduling,
or perceptual evidence.

## BLOCKER — correctness: self-invalidating source-population gate

`scripts/regression-harness/k1_scheduling_gate0.py:33-34,99-117` enumerates every
matching source under `SPECTRASYNQ_K1_FIRMWARE/`, `scripts/`, and `tests/`, plus
`platformio.ini`. `tests/test_scheduling_gate0.py:97-101` then requires the live result
to remain exactly `537`:

```python
manifest = oracle.source_manifest(ROOT)
assert manifest["count"] == 537
```

Why this blocks: the accepted programme explicitly proceeds to later production and
host-test units. Adding even one legitimate `.cpp`, `.h`, `.py`, `.sh`, `.ino`, `.def`,
or `.ini` file below those roots changes the count to `538` and makes the Gate 0 module
RED. The only ways forward would be to weaken/rebaseline a trust-root-owned oracle for
ordinary implementation work or to avoid legitimate new source files. Both violate the
Gate 0 ownership model and block the authorised lane.

Required correction before a fresh acceptance: preserve the anchored `537` population
as historical provenance of this Gate 0 qualification, but do not assert that every
future candidate HEAD has the same source count. Current candidate drift must be bound
by a deterministic per-run path/content manifest and the intended protected trust-root
semantics, not by a permanent global file-count ceiling. FRTOS-18 did not repair this
defect.

## 1. Read contract

The following inputs were read completely before the verdict:

- `docs/forensics/2026-08-15-freertos-scheduling-audit/gate0/contract.json`
- `docs/forensics/2026-08-15-freertos-scheduling-audit/gate0/trust_root.json`
- `scripts/regression-harness/k1_scheduling_gate0.py`
- `tests/test_scheduling_gate0.py`
- `tests/fixtures/scheduling_gate0/valid_oracle_run.json`
- `docs/forensics/2026-08-15-freertos-scheduling-audit/evidence/gate0-harness-inventory.md`
- `docs/forensics/2026-08-15-freertos-scheduling-audit/evidence/gate0-fault-battery-review.md`
- `docs/handover/HANDOVER_2026-08-15_SCHEDULING_HARDENING_IMPLEMENTATION.md`
- Gate 0 section, lines 319-357, of
  `docs/forensics/2026-08-15-freertos-scheduling-audit/EXECUTION_PLAN.md`

The repository execution standard, `AGENT_OS.md`, `.claude/CLAUDE.md`, and the
`code-review` skill were also loaded before acceptance work.

## 2. Repository anchor

Exact command:

```bash
bash scripts/agent/repo-truth.sh
```

Result: exit `0`, `OVERALL: PASS`.

```text
branch           : feat/k1-scheduling-generation-hardening
active branch    : feat/k1-scheduling-generation-hardening
active lane      : K1_SCHEDULING_HARDENING_20260815
HEAD             : 19047912
dirty files      : no
untracked files  : no
```

Exact commands:

```bash
git status --short --branch
git rev-parse HEAD
git branch --show-current
git rev-list --left-right --count '@{upstream}...HEAD'
git status --porcelain=v1
```

Results:

```text
## feat/k1-scheduling-generation-hardening...origin/feat/k1-scheduling-generation-hardening
190479128fcfb907c2b04749ea8a43d3d36be322
feat/k1-scheduling-generation-hardening
0    0
<empty porcelain output>
```

## 3. Trust root and tests

Exact command:

```bash
python3 scripts/regression-harness/k1_scheduling_gate0.py verify-trust-root docs/forensics/2026-08-15-freertos-scheduling-audit/gate0/trust_root.json
```

Result: exit `0`.

```text
GATE0_TRUST_ROOT PASS files=6
```

The trust root binds the contract, oracle, valid fixture, test module, harness
inventory, and prior fault-battery review. The anchored full Git SHA supplied to this
independent run is the external trust anchor for the in-repository trust-root file.

Exact command:

```bash
python3 -m pytest tests/test_scheduling_gate0.py -q
```

Result: exit `0`.

```text
..............................                                           [100%]
30 passed in 0.14s
```

There was no skip, xfail, or deselection summary: all 30 collected cases passed. The
30 comprise the good-control, determinism, trust-root, source-population, contract,
production-boundary, CLI-battery checks and the 21 independently parametrised fault
cases. The valid fixture also records `required_count=12` with deleted, skipped,
xfailed, and deselected counts all zero; the validator requires those zero counts at
`k1_scheduling_gate0.py:293-299`. This green run proves present-head execution only; it
does not cure the self-invalidating source-population assertion above.

## 4. Fault battery and inner reasons

Exact command:

```bash
python3 scripts/regression-harness/k1_scheduling_gate0.py fault-battery tests/fixtures/scheduling_gate0/valid_oracle_run.json
```

Result: exit `0`.

```text
GATE0_FAULT_BATTERY PASS caught=21 names=wrong_git_sha,wrong_source_manifest,wrong_platformio_ini,wrong_build_flags,wrong_firmware_binary,wrong_device_identity_manifest,wrong_device_identity,wrong_sample_tuple,wrong_mode_stress_contract,missing_trace_field,regressed_timestamp,corrupt_generation,missing_final_bytes_crc,unconfirmed_rmt_completion,changed_frozen_fixture,changed_test_inventory_hash,deleted_required_test,skipped_required_test,xfailed_required_test,deselected_required_test,perturbing_stream_enabled
```

I additionally imported the anchored oracle in a read-only Python process, applied
each value returned by `fault_mutations()` to a fresh deep copy, called
`validate_run()`, and compared the raised `Gate0Error` text to
`FAULT_EXPECTED_REASON[name]`. Result: exit `0`, `mutation_count=21`,
`all_registered_inner_reasons_match=true`.

| Mutation | Registered inner reason | Observed result |
|---|---|---|
| `wrong_git_sha` | `mismatch:git_sha` | rejected, exact match |
| `wrong_source_manifest` | `mismatch:source_manifest_sha256` | rejected, exact match |
| `wrong_platformio_ini` | `mismatch:platformio_ini_sha256` | rejected, exact match |
| `wrong_build_flags` | `mismatch:effective_build_flags_sha256` | rejected, exact match |
| `wrong_firmware_binary` | `mismatch:firmware_bin_sha256` | rejected, exact match |
| `wrong_device_identity_manifest` | `mismatch:device_identity_manifest_sha256` | rejected, exact match |
| `wrong_device_identity` | `wrong_device_identity` | rejected, exact match |
| `wrong_sample_tuple` | `production_tuple:samples_per_chunk` | rejected, exact match |
| `wrong_mode_stress_contract` | `wrong_mode_stress_contract` | rejected, exact match |
| `missing_trace_field` | `trace[0].missing:rmt_complete_us` | rejected, exact match |
| `regressed_timestamp` | `trace[0].timestamp_order` | rejected, exact match |
| `corrupt_generation` | `trace[1].non_monotonic:ap_generation` | rejected, exact match |
| `missing_final_bytes_crc` | `trace[0].primary_bytes` | rejected, exact match |
| `unconfirmed_rmt_completion` | `trace[0].rmt_unconfirmed` | rejected, exact match |
| `changed_frozen_fixture` | `mismatch:fixture_manifest_sha256` | rejected, exact match |
| `changed_test_inventory_hash` | `mismatch:test_inventory_sha256` | rejected, exact match |
| `deleted_required_test` | `deleted_required_test` | rejected, exact match |
| `skipped_required_test` | `skipped_required_test` | rejected, exact match |
| `xfailed_required_test` | `xfailed_required_test` | rejected, exact match |
| `deselected_required_test` | `deselected_required_test` | rejected, exact match |
| `perturbing_stream_enabled` | `perturbing_stream_enabled` | rejected, exact match |

The CLI does not merely count exceptions: `run_fault_battery()` rejects a wrong inner
reason at `k1_scheduling_gate0.py:419-438` before it can print PASS.

## 5. Deterministic good control

The following exact CLI was run three times by one read-only `subprocess.run()` wrapper:

```bash
python3 scripts/regression-harness/k1_scheduling_gate0.py validate tests/fixtures/scheduling_gate0/valid_oracle_run.json
```

Result:

```text
run=1 exit=0 stdout='GATE0_VALIDATE PASS checks=90 records=2' stderr=''
run=2 exit=0 stdout='GATE0_VALIDATE PASS checks=90 records=2' stderr=''
run=3 exit=0 stdout='GATE0_VALIDATE PASS checks=90 records=2' stderr=''
identical_stdout_and_exit=true
```

This kills both an always-reject oracle and a nondeterministic stdout/exit contract for
the admitted host fixture.

## 6. Fresh `/tmp` provenance snapshot

Exact creation commands:

```bash
K1_GATE0_ACCEPT_TMP="$(mktemp -d /tmp/k1-gate0-acceptance.XXXXXX)"
SNAPSHOT_PATH="$K1_GATE0_ACCEPT_TMP/provenance.json"
python3 scripts/regression-harness/k1_scheduling_gate0.py snapshot --output "$SNAPSHOT_PATH"
```

Result: snapshot CLI exit `0`.

```text
GATE0_SNAPSHOT PASS files=537 content_sha256=2968246b2210a1c34855bde23f4f5275c9b9db8f23fadacb39f2303050e74e05
snapshot=/tmp/k1-gate0-acceptance.eAlLcM/provenance.json
```

A read-only JSON assertion then verified:

```text
head=190479128fcfb907c2b04749ea8a43d3d36be322
branch=feat/k1-scheduling-generation-hardening
dirty=false dirty_paths=[]
source_count=537
path_argument_is_under_tmp=true
resolved_path_is_macos_tmp=true
dirty_is_false=true
dirty_paths_empty=true
head_matches=true
branch_matches=true
source_count_matches=true
```

Operator note: the first ad-hoc path assertion incorrectly required
`Path.resolve()` to remain below literal `/tmp`; on macOS it resolves to
`/private/tmp`, so that post-check exited `1` even though snapshot creation had passed.
The corrected assertion checked both the supplied `/tmp/...` path and its canonical
`/private/tmp/...` mapping, and exited `0`. No repository file was written by either
post-check.

## 7. Trace semantics and threshold ownership

The contract defines the whole-frame endpoint as `rmt_completion_confirmed`
(`contract.json:28-42`). Required trace fields include:

```text
rmt_submit_us
rmt_complete_us
primary_final_bytes_crc
secondary_final_bytes_crc
rmt_completion_confirmed
rmt_completion_source
trace_crc
```

The validator checks the causal timestamp order through `rmt_complete_us`, requires
both final-byte CRCs to be non-empty, requires confirmation to be literal `true`, and
accepts only `driver_completion_callback` or `driver_wait_tx_done` as completion source
(`k1_scheduling_gate0.py:191-225,315-326`). The good fixture exercises both allowed RMT
completion sources (`valid_oracle_run.json:54-107`). The `missing_final_bytes_crc` and
`unconfirmed_rmt_completion` mutants independently kill those acceptance teeth.

Threshold ownership is outside production units:

```text
product_contract_owner=Captain
oracle_owner=independent_harness_owner
acceptance_runner=independent_gate_runner
production_unit_may_edit_thresholds=false
change_rule=separate_authorised_contract_commit_then_complete_gate0_requalification_before_candidate_measurement
```

This is explicit in `contract.json:57-63`, protected by the trust root, asserted by
`test_scheduling_gate0.py:104-113`, and no production source imports the oracle
(`test_scheduling_gate0.py:124-127`).

## 8. Commit boundary

Exact commands:

```bash
git show --no-ext-diff --format=fuller --stat 190479128fcfb907c2b04749ea8a43d3d36be322
git diff-tree --no-commit-id --name-status -r 190479128fcfb907c2b04749ea8a43d3d36be322
```

Result: commit `19047912` changes 19 paths: audit documentation/evidence, the Gate 0
contract/trust root, one regression-harness script, one host fixture, and one host test.
A mechanical path filter over the same `git diff-tree` output returned:

```text
changed_path_count=19
production_or_platformio_changed=false
production_or_platformio_paths=[]
```

No path under `SPECTRASYNQ_K1_FIRMWARE/` and no `platformio.ini` path changed in the
reviewed commit.

## 9. Acceptance boundary and next gate

**Proven green but not accepted:** authority/branch/HEAD anchor, six-file trust-root
hashes, host good-control admission, three-run deterministic CLI output, the exact
21-fault membership and inner reasons, zero skip/xfail/deselection in the 30-case run,
trace-schema teeth, threshold ownership, and absence of production/PlatformIO mutation
in `19047912`.

**Blocking rejection:** the hard-coded live source count makes the oracle incompatible
with legitimate future source/test additions and therefore unable to govern Gate 1-8.

**Not proven:** any live ESP32 behaviour; AP/VP service demand; 120 FPS whole-frame
performance; actual final LED-byte CRC production; actual RMT completion; task/WDT/IDLE
health; sample freshness; generation coherence under real interleavings; acoustic-to-
photon latency; instrumentation perturbation; or perceptual quality. The fixture labels
itself `HOST_ORACLE_ONLY_NOT_DEVICE_EVIDENCE`. Those claims remain for Gate 1 and later
gates.

**Files changed by FRTOS-18:** only this acceptance receipt.  
**Build/PlatformIO/device/serial/upload/flash:** not run.  
**Git mutation:** none; no commit or push.  
**Next mechanical truth:** repair the source-manifest semantics in a new, authorised
oracle commit, freeze the exact Gate 0 snapshot as historical provenance, and rerun this
complete independent acceptance against the new clean anchored HEAD. Production work
must not enter Gate 1 on `19047912`.
