# F0 implementation review

Status: **NOT_VERIFIED**

Focused tests are green (`30 passed`), but the current implementation still has
two reproducible false-PASS paths and omits mandatory F0 runner/contract work.

## Decision-critical defects

### 1. Records outside the connection epoch can be laundered into Link Ready

- `correlate.py:109-204` correlates every record in both files; it never selects
  the post-settle epoch.
- `gate_eval.py:86-114` only counts one link-up, equal numeric epoch IDs and
  non-negative host-time overlap. It does not require negotiation or measured
  records to occur after link-up.
- `gate_eval.py:131-163` then applies whole-file TX/RX/apply/clock/GPIO counts.

Reproduction: moving both synthetic `link up` host timestamps to the end of the
capture, after negotiation and all measured records, still returned:

```text
prelink_launder PASS PASS {'ok': True, 'overlap_us': 0}
```

Required fix: select records bounded by each role's matched link-up and the
segment/capture end before correlation; require negotiation after link-up,
matching the selected role-local epoch; require a positive post-settle window.
Do not require leader and follower's local epoch counters to be numerically
equal as a substitute for host-time overlap.

Missing tests: all evidence before link-up; negotiation before link-up; records
after link-down; differing role-local epoch numbers for one overlapping link.

### 2. Duplication, reorder, counter reset and unexpected records can PASS

- `_integrity()` computes transport/apply duplication and reorder at
  `correlate.py:222-253`.
- Link Ready checks only leader density at `gate_eval.py:156-163`.
- Gate 4 checks only transport/apply *missing* counts at
  `gate_eval.py:303-314`; duplication and reorder remain diagnostics.
- `_index_records()` stores leader TX in a dictionary with `setdefault`
  (`correlate.py:83-106`), erasing duplicate/reset evidence before validation.
- RX without a corresponding leader TX and apply without a corresponding RX
  have no `unexpected` counters.

Reproduction: appending a duplicate, reordered follower RX record to an
otherwise clean strict capture returned:

```text
dup PASS 1 1
```

Required fix: preserve ordered leader TX records; block Link Ready on TX
duplicate/reset/non-monotonic order; gate transport/apply dup and reorder;
export and fail unexpected RX/apply. Counts used by Link Ready must be unique,
in-epoch, expected records.

Missing tests: leader counter reset without reconnect, duplicate TX/RX/apply,
out-of-order RX/apply, RX not in TX, apply not in RX.

### 3. A prohibited physical-glitch claim can manufacture overall PASS

- `correlate.py:266-283` accepts a firmware health extra named
  `ws2812_glitch`.
- `gate_eval.py:315-334` treats zero as measured PASS.
- `tests/test_dual_sync_oracle.py:151-154` obtains overall PASS by asking the
  synthesiser to emit that field.

This contradicts `recovery-plan.md`'s rule that a software submit/deadline
counter must never be labelled as a physical WS2812 glitch measurement.

Required fix: use honest per-device software metrics such as
`led_submit_deadline_miss`; keep physical glitch `UNMEASURED` unless supplied by
an explicit external physical-instrument evidence contract. Remove the test
that makes overall PASS from a synthetic firmware `ws2812_glitch=0`.

### 4. Strict parsing still accepts ambiguous evidence

- `_RE_HOST_PREFIX` is not start-anchored (`logfmt.py:140`).
- Health key/value parsing converts directly to a dictionary
  (`logfmt.py:192-220`), silently accepting duplicate keys with last-value wins.
- Most strict firmware regexes are searches without an end-of-record check.

Reproductions:

```text
duplicate_health_fps 100.0
nonanchored_prefix_records 1
```

The first input contained `fps=0 fps=100`; the second began with arbitrary text
before `host_us=`.

Required fix: strict mode requires `^host_us=<n> `, rejects duplicate keys and
requires full consumption of versioned records. Permissive archived parsing may
remain tolerant.

Missing tests: duplicate required health keys, multiple host prefixes,
non-leading host prefix, trailing garbage on every strict record type.

### 5. Mandatory F0 runner and tracked grammar work is absent

Current `scripts/dual_sync_probe/` contains no capture helper, segmented runner
or A/B/C runner, and `probe-log-contract.md` is unchanged. Consequently the
green suite has no tests for:

- supported/unsupported fault mapping and `clockoff` rejection;
- fresh exact ACKs and stale-ACK rejection;
- `restored` mapping to `off`;
- exclusive/non-overwriting outputs;
- restoration after failure/signal;
- shell handling of evaluator exits 0-4 without `set -e` abort;
- shared monotonic origin from actual dual-port capture.

F0 cannot be committed or published until these canonical deliverables exist
and are tested.

## Verification run

```bash
python3 -m pytest -p no:cacheprovider tests/test_dual_sync_oracle.py -q
# 30 passed in 0.55s; NOT sufficient because the cases above are absent.
```

## Re-review — 2026-07-27

Status remains **NOT_VERIFIED**.

The five original findings were materially addressed:

- pre-link evidence now produces `BLOCKED/BLOCKED` with
  `transport_expected=0`;
- duplicate/reordered and unexpected follower records produce
  `BLOCKED/BLOCKED`;
- all four strict-ambiguity probes are rejected;
- a firmware `ws2812_glitch=0` field leaves physical glitch and overall
  `UNMEASURED`;
- the tracked grammar, capture helper, segmented wrapper and capture tests now
  exist.

Exact focused result:

```text
python3 -m pytest -p no:cacheprovider tests/test_dual_sync_oracle.py -q
43 passed in 0.90s
```

Three decision-critical gaps remain.

### R1. A post-link `begin` boundary does not block Link Ready

`logfmt.py` parses `Begin`, but `gate_eval.py:106-115` checks only link-down and
`Reset`; `_epoch_view()` retains a later `Begin` as ordinary evidence.

Adversarial result after appending
`host_us=70000000 [k1_sync] begin role=leader`:

```text
postlink_begin PASS UNMEASURED
```

Link Ready must be `BLOCKED`: a second `begin` is a reboot/session boundary even
when the ESP-IDF `rst:` line was missed. Add begin-count/order diagnostics and a
test for a post-link begin on either role.

### R2. Impossible negotiated values satisfy the negotiation gate

`gate_eval.py:116-122` checks record counts and role-local epoch only. It does
not validate ranges or the settled cross-role relationship.

Replacing both negotiated records with
`interval_units=0 mtu=0 phy_tx=0 phy_rx=0` returned:

```text
zero_negotiated PASS
```

Require valid settled values: interval units in the BLE-valid range, MTU at
least the ATT minimum, supported PHY values, valid latency, and cross-role
agreement (leader TX PHY equals follower RX PHY and vice versa). Add zero,
out-of-range and mismatched-role tests.

### R3. Segmented capture loses the connection proof it later requires

`capture.py:247-265` creates fresh per-segment logs, clears serial buffers, and
evaluates each segment independently. A stable link emits `link up` and
negotiated values once. Therefore:

- a link established before capture is discarded by
  `clear_pending_input()` (`capture.py:130-135,257`);
- only a segment containing the original link transition can contain its
  proof;
- every later segment on the same healthy persistent link lacks `link up` and
  negotiation and is necessarily `BLOCKED`.

The current capture tests intentionally accept `BLOCKED` segments and do not
exercise a persistent link context (`tests/test_dual_sync_oracle.py:530-557`).
Evaluate bounded segments from the continuous session log while retaining the
preceding active link/negotiation context, or carry a verified immutable epoch
preamble into each segment without fabricating device records. Add a two-segment
persistent-link test in which both segments obtain Link Ready from one
connection.

The separate F2 entry point is still an exit-2 stub
(`run_f2_abc.sh:1-12`), not the canonical scripted A/B/C evidence runner. Its
fail-closed behaviour is safe, but F0's runner deliverable is incomplete.

## Final re-review — 2026-07-27

Status: **NOT_VERIFIED**

The oracle and persistent-link segment fixes now pass the adversarial battery:

```text
R1 BLOCKED 1
R2_zero BLOCKED
R2_mismatch BLOCKED
R3 PASS 1320
ORIG_prelink BLOCKED 0
ORIG_dup BLOCKED 1
ORIG_unexpected BLOCKED 1
ORIG_strict 4 of 4 rejected
ORIG_physical UNMEASURED UNMEASURED
```

Focused regression:

```text
python3 -m pytest -p no:cacheprovider tests/test_dual_sync_oracle.py -q
50 passed in 1.14s
```

Both shell entry points pass `bash -n`. R1-R3 and every original false-PASS
reproduction are therefore verified fixed.

One load-bearing F0 exit defect remains: the F2 wrapper is not a bounded A/B/C
evidence contract.

### F4. F2 wrapper permits contract override and out-of-order cases

`run_f2_abc.sh:26-29` forwards every unrecognised argument after its own
`--out-dir ... --segments off` arguments (`:50-53`). `argparse` uses the last
occurrence, so callers can override both load-bearing constraints:

```text
F2_override_segments delay5
F2_override_outdir elsewhere
```

The wrapper also:

- permits Case B or C without a prior A/B PASS;
- does not require or record expected chip IDs, environments, source SHA,
  binary hashes or physical-state evidence;
- does not create the canonical compact per-case manifest or Captain STOP
  input;
- has no focused wrapper tests. Only its invalid case/state pairing was
  exercised (`exit 2`).

Required fix: explicitly parse an allow-list of capture arguments and reject
`--segments`/`--out-dir`; lock every case to `off` and its case directory;
require case metadata and identity/build evidence inputs; enforce A→B→C from
prior PASS manifests; write the compact manifest; add subprocess tests for
valid command construction, reserved-option injection, direct B/C attempts,
non-overwrite and invalid mappings.

Until that is done, the canonical F0 item “capture helper, segmented plumbing
runner and A/B/C runner” is incomplete even though the host oracle itself is
verified against the requested exploit battery.

## F2 wrapper closure re-review — 2026-07-27

Status: **VERIFIED**

The replacement controller closes F4:

- `f2_capture.py:195-210` exposes an explicit argument allow-list. There is no
  `--segments` or `--out-dir` option, and the focused parser test rejects a
  reserved `--segments` injection.
- `f2_capture.py:135-146` derives the case directory internally and hard-codes
  `segments=("off",)`. `capture.py:340` refuses an existing case directory, so
  evidence cannot be silently overwritten.
- `f2_capture.py:71-84` requires the immediately preceding case to have a PASS
  manifest from the same source SHA. Case C additionally requires the exact
  Case-B leader and follower binary hashes (`:113-121`). Case/state and
  environment mappings are fixed in `CASE_CONTRACT`.
- Before capture, the controller fixes the expected chip IDs, environments and
  source SHA (`f2_capture.py:123-146`). `capture.py:208-253` queries both
  `:chip_id` and `:build`, rejects chip/SHA/environment mismatch, and writes the
  observed identity to `IDENTITY.json`.
- `f2_capture.py:148-191` writes an atomic per-case manifest containing Link
  Ready status, physical-state declaration, source SHA, ports, chip IDs,
  environments, binary paths and SHA-256 hashes, plus hashes of the session,
  verdict and identity evidence.
- `run_f2_abc.sh` is now only a strict shell entry point into that controller.
  Source inspection found no flash, upload, `start_noise_cal`, or noise
  calibration command. The only device mutations in the reused capture path
  are the locked `sync_fault=off` request and its fail-closed cleanup.

Verification:

```text
python3 -m pytest -q \
  tests/test_dual_sync_oracle.py \
  tests/test_dual_sync_probe_firmware_static.py
63 passed in 1.12s

bash -n scripts/dual_sync_probe/run_f2_abc.sh
PASS

F2_CONTRACT_PROBE PASS cases=A,B,C locked_segments=off manifests=3
```

This verifies the host-side F0/F2 evidence controller only. It does not claim
that any device was flashed, that silicon Cases A/B/C have run, or that Captain
has accepted Case C; the F2 STOP and F3 prohibition remain intact.
