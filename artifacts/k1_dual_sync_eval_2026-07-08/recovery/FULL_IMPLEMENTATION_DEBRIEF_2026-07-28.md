# Dual-sync F0-F3 recovery — full implementation debrief

**Debrief date:** 2026-07-28
**Branch:** `lane/dual-sync-phase0`
**Repository HEAD:** `4d685a859f19f0a141028b739b49a54503ad56ad`
**Firmware source commit:** `a58203183208a4db7fcc7a30d060e6db14673ab1`
**Baseline before recovery:** `3a9724e`
**Canonical authority:** [recovery-plan.md](recovery-plan.md)
**Live checklist:** [task_plan.md](task_plan.md)
**Evidence ledger:** [progress.md](progress.md)
**Technical findings:** [findings.md](findings.md)

---

## 1. Executive verdict

The recovery implementation is **complete through the host, firmware-source,
build and pre-silicon evidence boundary**.

It is **not complete on silicon**.

The repaired firmware has not been flashed to either K1. Cases A, B and C have
not been run. There is therefore no valid claim yet that:

- SyncLink establishes on the repaired firmware;
- the dual-role leader can scan for K718 while advertising SyncLink;
- K718 control traffic coexists with SyncLink;
- Link Ready passes on real silicon;
- Gate-0 measures the intended product path;
- Phase 0 is complete.

The correct immediate status is:

> **APPROVED FOR F2 CASE-A EXECUTION AFTER CAPTAIN PHYSICAL ATTESTATION.**

The following are still explicitly forbidden:

- F3 work before A, B and C all pass and Captain gives a separate GO;
- describing the existing segmented runner as a real Gate-0;
- claiming delay5 or delay20 changes real consume timing;
- treating `ap_p95_us=0` as measured;
- treating a software LED-submit counter as physical WS2812 proof;
- cross-flashing `F887A500` and `B489A500`;
- running `start_noise_cal`;
- pivoting to ESP-NOW, M2 or a radio-manager product.

### Status at a glance

| Layer | Status | What is proven | What is not proven |
|---|---|---|---|
| Authority and branch routing | **COMPLETE** | One tracked recovery authority; local/origin parity | Nothing material outstanding |
| F0 host trust root | **COMPLETE** | Fail-closed oracle, coherent Link Ready, strict grammar and tests | Real-device Link Ready |
| F0b late-attach recovery | **COMPLETE** | Current lifecycle replay prevents false blocking after capture attaches | Behaviour on the repaired devices |
| F1 BLE hardening | **COMPLETE at source/build** | Defects A-E repaired; generation and Core-ownership defects closed; four builds green | Real advertisement, discovery and connection on the two K1s |
| F2a evidence controller | **COMPLETE** | Identity-guarded flash/capture, recursive evidence validation, attestations and causal Case-C contract | Actual A/B/C evidence |
| F2b runtime observability | **COMPLETE at source/build** | Image/runtime identity, scanner/dial counters, generation-bound queue and decoder reset | Live counter behaviour and dial causality |
| F2 silicon A/B/C | **NOT STARTED** | Read-only USB/chip mapping and negative cross-target guards | Every case verdict |
| Captain STOP | **PENDING** | Format and fail-closed production path exist | A populated/accepted STOP report |
| F3 real Gate-0 | **BLOCKED / NOT STARTED** | Scope and causal boundary are defined | Real delays, clock fault, AP p95, LED instrumentation, semantic payload and soak |
| Phase 0 | **NOT COMPLETE** | Recovery machinery exists | Product-level measuring Gate-0 |

---

## 2. What was taken over

The takeover began from `3a9724e` on `lane/dual-sync-phase0`. The original
Cursor plan had the right strategic sequence but was outside git and contained
several technical and proof-contract errors.

The starting situation included:

- a broken or unproven SyncLink run;
- a host oracle capable of producing misleading results from absent or
  incoherent evidence;
- a scratch Gate-0 runner that was not suitable as product proof;
- discarded NimBLE scan/advertising return values;
- a follower discovery path that relied on an incomplete callback surface;
- Remoted initialisation before SyncLink on the dual-role leader;
- no trustworthy way to distinguish current source, built image and running
  application;
- no causal proof that K718 detents became meaningful K1 mode changes;
- no A/B/C evidence pack;
- no safe path from F2 into F3.

The recovery deliberately did **not** retry the old Gate-0. It first repaired
the trust boundary, then the BLE link implementation, then the evidence
machinery required to touch silicon safely.

---

## 3. Scope delivered

From baseline `3a9724e` to current HEAD `4d685a8`, the recovery changed:

- **44 files**
- **10,754 insertions**
- **1,151 deletions**
- **11 narrow commits**

The changes cover:

1. tracked execution authority and cross-tool routing;
2. host log parsing, correlation and verdict semantics;
3. late-attaching lifecycle replay;
4. BLE advertisement, scan, discovery and connection hardening;
5. Core and connection-generation ownership;
6. exact build/upload identity;
7. F2 guarded flashing and recursive evidence production;
8. Case-B scanner proof and Case-C dial causality;
9. reconnect-safe BLE-MIDI decoding;
10. tests, build registrations and durable evidence ledgers.

---

## 4. Commit history and delivered value

| Order | Commit | Purpose | Outcome |
|---:|---|---|---|
| 1 | `fe634bb` | Canonise F0-F3 recovery authority | Removed Cursor-only authority ambiguity; routed all agents to the live lane |
| 2 | `4c1d482` | Fail-closed oracle, Link Ready and exact NimBLE pin | Closed vacuous PASS and incoherent-epoch proof paths |
| 3 | `a4c2408` | Replay current lifecycle before capture | Closed the healthy-persistent-link false-BLOCK path |
| 4 | `862aea8` | Harden SyncLink advertisement, scan and observability | Repaired defects A-E and connection/Core ownership |
| 5 | `66196a9` | Record F1 post-commit build evidence | Bound the three probe images to the F1 commit |
| 6 | `0a1100b` | Harden F2 evidence and upload contract | Replaced the forgeable runner with identity-checked evidence production |
| 7 | `3077b4d` | Bound periodic evidence inside endpoint snapshots | Closed a live-traffic false-BLOCK condition |
| 8 | `7320262` | Reject no-op Case-C dial evidence | Prevented duplicate accepted modes from impersonating detents |
| 9 | `acb9c40` | Require Case-B scanner evidence | Proved scanner coexistence rather than merely proving the dial was absent |
| 10 | `a582031` | Add F2 image and dial-causality firmware evidence | Added runtime identity, counters, generation safety and decoder reset |
| 11 | `4d685a8` | Record immutable F2b image evidence | Preserved final image hashes and moved the phase to physical attestation |

Local and remote `lane/dual-sync-phase0` refs both resolve to
`4d685a859f19f0a141028b739b49a54503ad56ad`.

### Important provenance split

The repository HEAD and firmware source identity are intentionally different:

- host/controller/docs HEAD: `4d685a8`;
- firmware source and expected `:build` identity: `a582031`.

`4d685a8` is a documentation-only evidence commit created after the final
firmware build. F2 must expect the device to report `a582031`, not `4d685a8`.
Conflating these two identities was one of the evidence flaws found during
review.

---

## 5. Phase-by-phase implementation debrief

## 5.1 P-1 — authority and source-truth recovery

### Problem

The detailed recovery plan existed only under `~/.cursor/plans/`. The live
branch was dual-sync, but several tracked routers still pointed at the older
IM73D lane. `repo-truth.sh` could pass by finding stale text rather than
validating a declared branch authority.

### Work completed

- Created [recovery-plan.md](recovery-plan.md) as the sole tracked authority.
- Created and maintained:
  - [task_plan.md](task_plan.md)
  - [findings.md](findings.md)
  - [progress.md](progress.md)
- Reconciled:
  - [`AGENT_OS.md`](../../../AGENT_OS.md)
  - [`.claude/handoff.md`](../../../.claude/handoff.md)
  - [`docs/spec-index.md`](../../../docs/spec-index.md)
  - root [`progress.md`](../../../progress.md)
- Changed [`repo-truth.sh`](../../../scripts/agent/repo-truth.sh) to validate
  explicit `active_branch` and `active_authority` declarations.
- Preserved the pre-existing dirty registry instead of absorbing it into an
  unrelated commit.

### Result

Agents now have one tracked recovery work order. The original Cursor plan is a
superseded draft, not the execution authority.

### Remaining issue

The repository instructions reference
`docs/agent/AGENT_EXECUTION_STANDARD.md`, but that file is absent. The run used
`AGENT_OS.md`, `.claude/CLAUDE.md`, `AGENTS.md` and the tracked recovery
authority instead. This did not block the recovery, but the missing canon
remains a documentation-governance defect outside this lane.

---

## 5.2 F0 — fail-closed host trust root

### Problem

The original host oracle could not be trusted to distinguish:

- no evidence from passing evidence;
- a coherent connection from observations accumulated across reconnects;
- transport loss from application consume loss;
- leader dial state from follower placeholder state;
- a real AP timing sample from the sentinel value zero;
- software LED submission from a physical WS2812 result.

This made any subsequent Gate-0 number suspect.

### Work completed

#### Dependency stability

- Pinned all sync probe environments to
  `h2zero/NimBLE-Arduino@2.5.0`.
- Verified the resolved library version in the probe dependency graphs.

#### Proof vocabulary

Implemented a single explicit verdict contract:

`PASS | FAIL | BLOCKED | UNMEASURED`

with:

- `0=PASS`
- `1=FAIL`
- `2=BLOCKED`
- `3=UNMEASURED`
- `4=contract/input error`

String truthiness cannot produce a passing result.

#### Link Ready

Implemented a coherent post-settle connection epoch requiring:

- one leader and one follower LinkUp;
- no unexpected reset, reconnect, LinkDown or epoch change;
- leader TX at least 300;
- follower RX and apply at least 300;
- follower clock samples at least 10;
- at least 10 complete GPIO rounds;
- positive expected stream count;
- stable negotiated interval, latency, MTU and PHY evidence.

The leader is not incorrectly required to emit follower clock-estimator
samples.

#### Correlation and role ownership

- Leader health owns K718 dial metrics.
- Follower health owns transport/application loss.
- Transport expected/loss and apply expected/missing are separate.
- Multiple connection epochs cannot be accumulated into one PASS.
- Ordered evidence is preserved so duplicate or reordered records cannot be
  hidden by dictionary de-duplication.

#### Metric honesty

- `ap_p95_us=0` is `UNMEASURED`.
- Missing physical LED instrumentation is `UNMEASURED`.
- A firmware counter cannot be relabelled as physical
  `ws2812_glitch`.
- Gate 3 is named
  `gate3_leader_stamp_to_follower_consume`, not mic-to-LED.

#### Host runners

- Added a shared-clock capture helper.
- Added a segmented **host-plumbing** runner.
- Added a distinct A/B/C runner.
- Supported only the actual F0 fault verbs:
  `off`, `delay5`, `delay20`, `drop10`.
- Mapped the `restored` segment label to `off`.
- Rejected `clockoff` because firmware does not implement it.
- Added non-overwrite, exact ACK and restore-on-exit behaviour.

### Validation

- Baseline focused suite: `25 passed`.
- Final F0 focused suite: `63 passed`.
- Full repository suite: `731 passed, 1 skipped`.
- `k1_hardware`, sync leader and sync follower builds: SUCCESS.
- Independent adversarial closure: `VERIFIED`.

### Result

The host can no longer turn missing, stale, disconnected or incoherent
observations into a valid PASS.

### What F0 did not prove

F0 is host machinery. It does not prove the repaired firmware links on the two
K1s.

---

## 5.3 F0b — late-attaching capture repair

### Problem

F2 identity verification clears pending serial input before capture. On an
already-running healthy link, this could discard the only boot-time LinkUp and
negotiation records. The continuing stream, clock and GPIO data would then be
real, but the oracle would return `BLOCKED` because the lifecycle boundary was
missing.

This false-BLOCK path was reproduced.

### Work completed

- Added `:sync_status`.
- Required one exact current-state lifecycle response from each role.
- Required coherent role, epoch, link state, MTU and negotiation fields.
- Rejected missing, duplicated, malformed, unlinked or incoherent responses.
- Preserved raw status sessions and parsed `SYNC_STATUS.json` in evidence.

### Validation

- Focused suite: `103 passed, 24 subtests passed`.
- Isolated staged-tree suite:
  `737 passed, 1 skipped, 83 subtests passed`.

### Result

A late-attaching capture can prove the current connection without relying on
boot-log archaeology.

### Residual limitation

Clearing input at a segment boundary can still split an in-flight stream set
and conservatively produce `BLOCKED`. It cannot manufacture PASS. F2 therefore
uses one bounded `off` capture rather than a multi-segment product claim.

---

## 5.4 F1 — BLE advertisement, scan and connection hardening

### Problem

Five source-confirmed defects existed:

1. scan state was latched before knowing whether `start()` succeeded;
2. advertising return values were discarded;
3. scan response was not enabled before adding the name;
4. follower discovery relied only on `onResult`;
5. Remoted started before SyncLink on the dual-role leader.

Further review found deeper connection-generation and Core-ownership defects
that were not explicit in the original Cursor plan.

### Work completed

#### Scan behaviour

- Removed the pre-emptive software scan latch.
- Derived scan state from `isScanning()`.
- Checked `start()` in both SyncLink and Remoted scan loops.
- Added bounded retry and diagnostic counters.

#### Leader advertising

- Enabled scan response before setting the name.
- Checked UUID, name, start and active advertising results.
- Kept the service UUID as the matching authority; the name is diagnostic.
- Prevented advertising restart from `onConnect`.
- Deferred checked restart after disconnect to the Core-1 owner.

#### Follower discovery

- Added shared service-UUID consideration from both `onDiscovered` and
  `onResult`.
- Logged connection, service discovery, characteristic discovery and
  subscription failures.

#### Initialisation and environments

- Started SyncLink before Remoted on the dual-role leader.
- Correctly guarded every Remoted declaration and use.
- Added `k1_sync_probe_main_sync_only`.
- Registered the new environment in:
  - [`pio-build.sh`](../../../scripts/agent/pio-build.sh)
  - [`k1_upload_guard.py`](../../../scripts/platformio/k1_upload_guard.py)
  - upload-guard tests.

#### Application-ready LinkUp

A raw GAP connection no longer becomes Link Ready.

- Leader readiness requires both CCCDs plus a valid clock request.
- Follower readiness requires service/characteristic discovery, both
  subscriptions and stable negotiated values.
- Negotiated values are checked separately from request acceptance.

Accepted transport values are:

- interval units: `6` = 7.5 ms;
- latency: `0`;
- MTU: `247`;
- TX/RX PHY: `2M`.

DLE remains `REQUESTED_UNVERIFIED`.

#### Connection generation and Core ownership

Review found that a pointer snapshot could survive while a reconnect replaced
the live characteristic. It also found that application GATT work was occurring
from the wrong timing context.

The repair:

- generation-binds lifecycle publication;
- moves periodic GATT writes/notifies to Core 1;
- generation-checks central characteristic use;
- queues callback-time clock timestamps without losing `t4`;
- defers serial lifecycle output from callback context.

### Validation

- Focused suite: `103 passed, 24 subtests passed`.
- Full suite: `760 passed, 1 skipped, 86 subtests passed`.
- Builds:
  - `k1_hardware`: SUCCESS
  - `k1_sync_probe_main`: SUCCESS
  - `k1_sync_probe_main_sync_only`: SUCCESS
  - `k1_sync_probe_bench`: SUCCESS
- All probe builds resolved NimBLE-Arduino `2.5.0`.
- Independent concurrency verdict: `APPROVE`.

### Result

Defects A-E and the review-discovered generation/Core hazards are repaired at
source and build level.

### What F1 did not prove

The repaired images have not been flashed. Advertisement, discovery and LinkUp
on the actual pair remain unverified.

---

## 5.5 F2a — guarded silicon evidence controller

### Problem

The first F2 runner was not trustworthy enough for silicon decisions. It could:

- trust a caller-supplied build identity;
- accept a BIN hash as proof of the installed application;
- accept self-authored prior-case JSON;
- fail to recursively revalidate referenced raw evidence;
- treat a physical K718 state string as truth;
- accept traffic without proving meaningful dial changes;
- let a documentation commit invalidate otherwise correct firmware provenance.

Independent host and firmware reviews returned `NO-GO`.

### Work completed

#### Single guarded writer

[`f2_flash.py`](../../../scripts/dual_sync_probe/f2_flash.py) is the only F2
writer.

It:

- builds through the approved wrapper;
- applies the existing upload guard;
- records the attempted write before upload;
- preserves exact BIN and ELF artefacts;
- records exact commands and return codes;
- performs post-flash chip, build, image and runtime read-back;
- produces a fail-closed upload manifest.

Case C has no flash path.

#### Identity model

Evidence now distinguishes:

1. host/controller source;
2. firmware source commit;
3. BIN hash;
4. raw ELF hash;
5. ESP application-descriptor ELF identity extracted from BIN;
6. device-reported application identity;
7. per-boot runtime nonce, uptime and reset reason;
8. chip identity and USB serial at action time.

#### Recursive case ordering

- Case A must pass before B.
- Case B must recursively rehash, reparse and re-evaluate A.
- Case C must recursively revalidate A and B.
- Referenced raw files are rehashed.
- Case C must continue the exact Case-B boot on both devices.

#### Physical attestations

Every case requires a tracked Captain-confirmed attestation under the selected
run ID. A caller-supplied phrase cannot substitute for physical state.

#### Fail-closed evidence stance

- Missing samples or counter regression: `BLOCKED`.
- Observed forbidden behaviour: `FAIL`.
- Partial upload attempts remain recorded as `BLOCKED`.
- No overwritten evidence.

### Validation

- F2a focused: `75 passed`.
- F2a full: `775 passed, 1 skipped, 86 subtests passed`.
- Ten adversarial attack paths reproduced and closed.
- Final F2a reviewer verdict: `APPROVE`.

### Result

F2 has a bounded, identity-first evidence path suitable for hardware execution.

---

## 5.6 F2a.1-F2a.3 — corrections found by adversarial review

### F2a.1: periodic counter window

#### Failure

The baseline status snapshot occurs before capture and the endpoint snapshot
after capture, while the first and last 1 Hz samples necessarily occur inside
that interval. Requiring equal endpoint and periodic deltas creates a
false-BLOCK whenever traffic occurs outside the sampled interior.

#### Repair

- Require periodic cumulative counters to remain inside baseline/end bounds.
- Retain an independent positive periodic-traffic requirement.
- Keep regressed endpoints `BLOCKED`.
- Treat endpoint/periodic contradictions as `FAIL`.

#### Validation

`776 passed, 1 skipped, 86 subtests passed`.

### F2a.2: no-op dial evidence

#### Failure

Three accepted mode records could all repeat the currently confirmed ordinal.
They were traffic, but not three meaningful detents. The original logic could
call this a Case-C PASS.

#### Repair

- Reconstruct per-control ordinal changes from the coherent baseline.
- Count only actual ordinal transitions.
- Require at least three meaningful events.
- Require the `dial_mode_apply_ok` endpoint delta to equal emitted meaningful
  mode events.

#### Validation

`777 passed, 1 skipped, 86 subtests passed`.

### F2a.3: scanner proof and BLE-MIDI packetisation

#### Failure 1

Case B could pass with `dial_linked=0` even if the Remoted scanner had silently
stopped. That would fail to test the intended scan/advertise coexistence.

#### Repair 1

Require:

- scanner active in both coherent endpoints;
- scanner active in every periodic sample;
- at least one successful scan start;
- no in-window restart or scan-start failure.

#### Failure 2

Case C required three notifications for three detents, but BLE-MIDI may batch
multiple records in one notification.

#### Repair 2

- Require at least one notification.
- Independently require at least three decoded, enqueued, applied and
  meaningful records.

#### Validation

`778 passed, 1 skipped, 86 subtests passed`.

---

## 5.7 F2b — runtime and dial-causality observability

### Problem

The host contract could not be valid until firmware exposed the same identity,
scanner, traffic, generation and confirmation state.

Review also found that adding counters alone could create heap pressure or
cross-generation contamination.

### Work completed

#### Runtime identity commands

Added:

- `:image_id`
- `:runtime_id`
- gated `:dial_status`

These expose exact application identity, boot identity, reset context and
strict dial/scanner counters.

#### Scanner and dial counters

Firmware now exposes:

- scanner active;
- successful/failed scan starts;
- notification count;
- decoded count;
- enqueued count;
- applied count;
- meaningful dial-mode applications;
- confirmation attempts/success;
- connection generation;
- stale-generation drops.

#### Generation-bound work

- Queued control records carry their connection generation.
- Pending mode-confirmation targets carry their generation.
- Stale work is rejected before apply.
- Generation is rechecked after apply before confirmation.
- Rejections increment a visible fail-closed counter.

#### Decoder reconnect boundary

The final review found a subtle remaining defect:

> an old-generation CC14 MSB or partial NRPN sequence could survive reconnect
> and combine with a new-generation remainder.

The repair:

- clears every partial CC14/NRPN accumulator before advancing the connection
  generation;
- preserves the monotonic next record ID;
- tests old-MSB/new-LSB and old-NRPN/new-data contamination;
- proves a complete new-generation sequence still emits exactly one record.

#### Allocation-safe diagnostics

Remoted variable lines use checked fixed-size stack formatting and
`Serial.print`. Long `Serial.printf` and callback-time serial output were
removed from the reviewed Remoted path.

### Validation

- Focused F2b suite:
  `134 passed, 24 subtests passed`.
- Full suite:
  `786 passed, 1 skipped, 86 subtests passed`.
- Current focused rerun on 2026-07-28:
  `134 passed, 24 subtests passed`.
- Builds on final source:
  - production: SUCCESS
  - dual-role leader: SUCCESS
  - sync-only leader: SUCCESS
  - follower: SUCCESS
- Independent final firmware verdict: `APPROVE`.

### Result

The firmware exposes the evidence required by the F2 controller without
retaining known cross-generation dial state.

### What F2b did not prove

No live K718 traffic or SyncLink connection has been observed from these
images.

---

## 6. Validation and immutable build evidence

### Latest test evidence

| Gate | Result |
|---|---|
| Current focused F2b rerun | `134 passed, 24 subtests passed` |
| Last full repository run on final code | `786 passed, 1 skipped, 86 subtests passed` |
| Session bootstrap | PASS with expected dirty-registry warning |
| F2b independent firmware review | `APPROVE` |
| Staged diff checks | PASS |
| Commit hook | PASS |
| Local/origin branch parity | PASS |

The full test was run before the documentation-only `4d685a8` commit. The code
at HEAD is unchanged from the tested firmware commit.

### Build evidence

| Environment | Purpose | Result | Embedded source |
|---|---|---|---|
| `k1_hardware` | Production regression boundary | SUCCESS | final F2b source, pre-commit provenance during validation |
| `k1_sync_probe_main_sync_only` | Case-A leader | SUCCESS | `a582031` |
| `k1_sync_probe_main` | Case-B/C dual-role leader | SUCCESS | `a582031` |
| `k1_sync_probe_bench` | Follower | SUCCESS | `a582031` |

Every probe dependency graph resolves NimBLE-Arduino `2.5.0`.

### Immutable flashable image identities

| Image | BIN SHA-256 | ELF/application SHA-256 |
|---|---|---|
| Sync-only leader | `8750774afbd2e2ff233015946a337757259efc1c38895accc64318731dc95c61` | `f062eab2e3416da94e18d1a2f3b4acb999dfcec8d4c50a458c0e1a6514503b9a` |
| Dual-role leader | `732fb6afbbe84baa1a504b94760d0c65ba6527b1e49714769bc576a1ac7e8874` | `03f93e9704e771adb602fbf6c084c7c3d061d38ef00195aa3e8282da0f736a63` |
| Follower | `3552db9f108dca29be2b27c156676290a28216c397666805a39cd9ebb5c34c7f` | `3e2ccf6136425c453103023697b53c9995b0f2ffb7e8b80b4a147197b8901740` |

For each image, the ESP application-descriptor identity extracted from the BIN
equals the raw ELF SHA-256.

### Build warnings that remain

Builds succeed, but warnings remain for:

- `++` on `volatile`-qualified generation/state counters;
- conflicting IRAM section attributes on existing GDFT declarations.

These warnings did not fail the configured gate. They should not be confused
with silicon proof, and they may merit a separate narrow hardening task after
the recovery critical path.

---

## 7. Hardware and runtime status

### Identity mapping last observed

| Role | Chip truth | USB serial | Last observed port |
|---|---|---|---|
| Leader | `F887A500` | `B4:3A:45:A5:87:F8` | `/dev/cu.usbmodem112401` |
| Follower | `B489A500` | `B4:3A:45:A5:89:B4` | `/dev/cu.usbmodem11401` |

Positive upload-guard checks passed. Both cross-target negative controls
failed closed with exit code `2`.

Ports can drift. Every future action must resolve identity from USB serial and
chip ID again; a port pathname is never role authority.

### Last recorded deployed firmware

The uncommitted device registry records both devices on the older
`3a9724e` probe images. No live serial read-back was performed for this debrief,
so that is a last-recorded state, not a 2026-07-28 runtime verification.

The repaired `a582031` images have not been flashed.

### Physical state still required

Before Case A, Captain must confirm:

- Main GPIO15 → Bench GPIO16;
- Bench GPIO15 → Main GPIO16;
- GND ↔ GND;
- logic level is 3V3 only;
- wiring is secure;
- K718 is irrelevant/off for Case A.

Software cannot prove this physical wiring before exercising it. The attestation
is a genuine human boundary, not an agent chore.

---

## 8. What currently works

The word “works” here means proven at the stated layer, not inferred end to end.

### Proven host behaviour

- Empty logs cannot pass.
- Health-only logs cannot pass.
- Zero expected stream cannot pass.
- Missing AP/LED instruments remain unmeasured.
- Reconnects and multiple epochs cannot accumulate into PASS.
- Duplicate, reordered, reset and unexpected records fail closed.
- Leader and follower health are not mixed.
- Transport loss and apply loss are separate.
- The late-attaching lifecycle replay is strict and test-covered.
- F2 evidence is non-overwriting and recursively revalidated.
- Prior-case JSON cannot be accepted without raw-file rehash and re-evaluation.
- Case C cannot flash.
- Case-C no-op modes cannot count as detents.
- BLE-MIDI batching does not create a false BLOCK.

### Proven firmware-source behaviour

- Scan starts are checked and retried from actual NimBLE state.
- Advertising setup returns are checked.
- Scan response is enabled.
- Discovery matches the SyncLink service UUID.
- Link Ready is published only after application-level readiness.
- GATT work is generation-bound.
- Periodic application GATT operations have a Core-1 owner.
- Remoted queue residue is rejected across reconnects.
- Partial CC14 and NRPN state is reset across reconnects.
- Runtime, image, scanner and dial evidence commands compile in the intended
  environments.

### Proven build/identity behaviour

- Production and all three probe environments compile.
- NimBLE is exactly pinned.
- Sync-only leader excludes Remoted.
- Upload guard maps the correct chips.
- Both cross-flash directions are rejected.
- Final flashable images embed the intended firmware commit.
- BIN, ELF and application-descriptor identities are available for read-back.

---

## 9. What does not work or remains unproven

## 9.1 Repaired SyncLink on silicon

**Status:** unproven.

No Case-A flash or capture has occurred. The original BLE failure class remains
unknown until A/B/C isolates it.

Interpretation after future tests:

- A fails: base SyncLink advertisement/scan/connect path still fails;
- A passes, B fails: dual-role scan/advertise coexistence fails;
- A and B pass, C fails: K718 link/control coexistence fails;
- A, B and C pass: bounded link recovery is proven and F3 can be considered.

## 9.2 Case A/B/C evidence

**Status:** absent.

No `_scratch/dual_sync_f2_abc_<run-id>/` evidence root exists. There is no
Link Ready JSON, negotiated-value pack, case manifest or `CAPTAIN_STOP.md`.

## 9.3 Real delay5 and delay20

**Status:** not implemented.

Current firmware changes only the printed `t_render_us` value:

- delay5 adds 5,000 µs to the stamp;
- delay20 adds 20,000 µs to the stamp.

It does not hold application consume in a real pending queue. These modes are
host-plumbing tests only and cannot be cited as Gate-0 fault evidence.

## 9.4 Clockoff

**Status:** not implemented.

`set_fault()` accepts only:

- `off`
- `delay5`
- `delay20`
- `drop10`

The host correctly rejects `clockoff` before F3.

## 9.5 Product semantic payload

**Status:** not implemented.

The stream remains two batched 12-byte dummy-replay records: a 24-byte probe
payload. It is not the planned approximately 39-byte semantic packet.

## 9.6 Gate 3 end-to-end causal meaning

**Status:** deliberately limited.

The valid name remains:

`leader_stamp_to_follower_consume`

There is no proven chain from:

`leader audio snapshot → packet → follower state publication → renderer consume → LED submit`

and no physical LED-latch proof. It must not be labelled mic-to-LED.

## 9.7 AP p95

**Status:** unmeasured.

Firmware emits `ap_p95_us=0` because no real Core-0 AP profiler is connected to
the probe. The oracle correctly reports this as `UNMEASURED`.

## 9.8 Physical WS2812 behaviour

**Status:** unmeasured.

No physical instrument observes the WS2812 waveform or LED latch. Software
submit/deadline evidence may be added in F3, but physical glitch remains
unmeasured without an explicit instrument.

## 9.9 DLE

**Status:** `REQUESTED_UNVERIFIED`.

MTU, interval, latency and PHY have a stable read-back contract. Data Length
Extension does not yet have equivalent lower-level proof.

## 9.10 Core-0 radio cost

**Status:** unmeasured.

F1 removed application-owned periodic GATT work from Core 0. NimBLE
host/controller callback cost is not claimed eliminated. F3 must measure real
AP p95 and soak behaviour.

---

## 10. Failures encountered, what was tried and what was learned

| Failure or rejected approach | Why it failed | Repair/experiment | Current result |
|---|---|---|---|
| Re-run the old Gate-0 | Oracle and link state were untrustworthy | Stopped and repaired F0/F1 first | Correctly forbidden |
| Cursor-only plan as authority | Other agents/checkouts could not discover it | Added tracked canonical recovery authority | Resolved |
| Stale IM73D routing | Repo truth could validate irrelevant text | Explicit branch/authority frontmatter validation | Resolved |
| Both roles required clock samples | Leader does not run the estimator | Made follower clock truth explicit | Resolved |
| Enum strings used as booleans | Any non-empty status could look true | Explicit status comparisons and exit codes | Resolved |
| Multiple epochs accumulated | Disconnected fragments could satisfy floors | One coherent post-settle epoch only | Resolved |
| Duplicate/reordered records hidden | De-duplication erased evidence of corruption | Preserve ordered records and fail closed | Resolved |
| Late capture lost LinkUp | Input clear removed one-shot lifecycle lines | Added strict current `:sync_status` replay | Resolved |
| Add `svc->start()` as proof | NimBLE 2.5.0 implements it as deprecated no-op | Use checked advertising/server path instead | Rejected as theatre |
| Scan latch before `start()` result | A failed start could wedge software state | Derive from `isScanning()` and retry | Resolved at source |
| Restart advertisement in callback | Cross-generation/Core ownership unsafe | Defer to Core-1 owner after disconnect | Resolved at source |
| Current HEAD as device identity | Docs commits can change HEAD without firmware changes | Separate host and firmware provenance | Resolved |
| BIN hash as installed-app proof | BIN name/hash alone does not prove running app | Compare ELF, app descriptor and device read-back | Resolved in controller |
| Self-authored previous-case JSON | Could forge A→B→C order | Recursive manifest/raw evidence validation | Resolved |
| Equal periodic/endpoint deltas | Sampling windows are nested, not identical | Require bounded cumulative values | Resolved |
| Count every accepted mode as detent | No-op repeats could manufacture Case-C PASS | Count meaningful ordinal transitions only | Resolved |
| Case B used only dial-off evidence | Scanner could be stopped and still pass | Require continuous scanner-active evidence | Resolved |
| Three notifications for three detents | BLE-MIDI may batch records | Separate notification and decoded-record floors | Resolved |
| Generation-tag queue only | Decoder half-messages could survive reconnect | Reset partial CC14/NRPN state before generation advance | Resolved |
| Long diagnostic `printf` | Arduino formatting may allocate for long lines | Checked fixed stack buffers plus `Serial.print` | Resolved in Remoted path |
| Unscoped `pytest -q` | `_scratch` consult pack contains duplicate test module names | Preserve evidence and scope to `pytest -q tests/` | Canonical suite works |
| Initial docs commit had EOF whitespace | `git diff --cached --check` stopped it | Corrected docs and reran gate | Resolved before commit |

### Principal lessons

1. **Absence is not success.** Empty, missing or uninstrumented data must have
   explicit non-PASS states.
2. **A connection is not application readiness.** GAP connected is weaker than
   subscribed, negotiated and clock-capable.
3. **Evidence needs identity at every layer.** Source SHA, build image, app
   descriptor, chip and boot instance are different facts.
4. **Counters need causal meaning.** Traffic, accepted commands, meaningful
   state changes and physical display feedback are not interchangeable.
5. **Connection generation must include parser state.** Tagging queued output
   is insufficient if partial input state survives.
6. **Packetisation is not event count.** BLE notifications may batch semantic
   records.
7. **Sampling geometry matters.** Interior periodic samples cannot be required
   to equal larger endpoint windows.
8. **Host proof and silicon proof are different bars.** Tests and builds can
   approve a flash experiment; they cannot approve a product result.
9. **A fail-closed false BLOCK is still a defect.** It does not corrupt a PASS,
   but it can waste the entire hardware run and therefore deserves repair.
10. **Stopping before hardware was correct.** The review cycles found multiple
    paths that could have produced a false Captain decision.

---

## 11. Continuing blockers and why they continue

| Blocker | Type | Why it still exists | Who can clear it | What clears it |
|---|---|---|---|---|
| Physical GPIO/K718 attestation | Human/physical | Software cannot see passive wiring before exercising it | Captain | Explicit confirmation of wiring, ground, 3V3 and Case-A K718 state |
| Case-A silicon result | Hardware/runtime | Final images have not been flashed | Orchestrator after attestation | Guarded flash plus 60 s evidence capture and Link Ready PASS |
| Case-B silicon result | Hardware/runtime | Forbidden until A passes | Orchestrator after A | Dual-role leader flash with K718 off; scanner and Link Ready PASS |
| Case-C silicon result | Hardware/human | Forbidden until B passes; needs physical dial action | Orchestrator + Captain | No reflash; K718 on; at least three meaningful detents during capture |
| Captain STOP | Decision | No A/B/C evidence exists | Orchestrator then Captain | Generated tracked report followed by explicit acceptance/rejection |
| F3 implementation | Deliberate phase gate | Building faults before transport isolation would mix causes | Captain after Case C | Explicit F3 GO |
| AP p95 and LED proof | Instrumentation | Current probe has no real surfaces | F3 firmware/host work | Defined counters/instrument contract plus fault-sensitive tests |

The current blocker is not lack of code. It is the intentionally required
physical attestation before an irreversible device write.

---

## 12. Outstanding work

## 12.1 Immediate critical path — F2

### Task 1: Captain physical attestation

Create `case_A.json` only after Captain confirms the exact physical state.

### Task 2: Re-run preflight immediately before flash

- Re-read [task_plan.md](task_plan.md).
- Run `session-bootstrap.sh`.
- Re-enumerate ports.
- Resolve USB serial and chip identity.
- Verify no target-specific serial holder.
- Run both correct-target guards.
- Retain cross-target negative behaviour.

### Task 3: Case A — base SyncLink

- Flash `k1_sync_probe_main_sync_only` to `F887A500`.
- Flash `k1_sync_probe_bench` to `B489A500`.
- Preserve upload manifests and immutable images.
- Capture at least 60 seconds.
- Require:
  - exact build/image/runtime identities;
  - checked leader advertising;
  - follower discovery and connection;
  - both LinkUp records;
  - at least 300 TX/RX/apply;
  - at least 10 follower clock samples;
  - at least 10 complete GPIO rounds;
  - no reset/reconnect loop;
  - Link Ready PASS.

If A does not pass, stop. Do not run B or C.

### Task 4: Case B — dual-role leader, K718 off

- Revalidate Case A recursively.
- Flash only the leader to `k1_sync_probe_main`.
- Reuse the validated follower.
- Confirm K718 off.
- Require continuous Remoted scanner activity with no dial traffic.
- Require Link Ready PASS.

If B does not pass, stop. Do not run C.

### Task 5: Case C — dual-role leader, K718 on

- Revalidate A and B recursively.
- Do not reflash either device.
- Prove the exact Case-B boot continues.
- Power/link K718.
- Captain commits to and turns at least three meaningful mode detents during
  the active capture.
- Require:
  - 100% post-settle dial-linked health;
  - no dial reconnect/disconnect;
  - positive notify/decode/enqueue/apply movement;
  - at least three meaningful ordinal changes;
  - causal mode-apply to confirmation-write evidence;
  - Link Ready PASS.

### Task 6: Captain STOP

Generate tracked `CAPTAIN_STOP.md` with:

- A/B/C verdicts;
- Link Ready counts;
- stream counts;
- GPIO rounds;
- dial evidence;
- image/runtime identity;
- unresolved physical K718 feedback;
- `decision: PENDING`.

Stop and wait for Captain. Do not begin F3.

---

## 12.2 F3a — host contract, only after Captain GO

Outstanding host work:

- replay A/B/C stored captures and preserve their baseline verdicts;
- define the real approximately 39-byte packet grammar;
- define delay-queue and overflow/late/reset tokens;
- define `clockoff` evidence;
- define BLE-sequence-before-GPIO pairing;
- define Delay Line D at 30,000 µs;
- define leader audio snapshot, follower publication, renderer consume and LED
  submit timestamps;
- define real AP p95;
- define honest LED submit/deadline metrics;
- add fault fixtures;
- prove every injected fault flips only its intended gate;
- keep physical WS2812 state unmeasured without physical instrumentation;
- commit host contract separately before firmware behaviour.

---

## 12.3 F3b — firmware behaviour, only after F3a

Outstanding firmware work:

1. fixed-capacity, static, O(1) delay queue;
2. real +5 ms/+20 ms consume scheduling;
3. wrap-safe deadlines;
4. bounded records drained per poll;
5. overflow, late and reset counters;
6. real `clockoff` bias of follower radio offset only;
7. preserved GPIO wire truth;
8. BLE sequence published before GPIO pulse;
9. Delay Line D = 30,000 µs scheduled apply;
10. semantic packet with versioned byte layout and `static_assert`;
11. leader audio-feature snapshot timestamp;
12. follower scheduled consume/publication timestamp;
13. renderer and LED-submit timestamps;
14. real Core-0 AP p95;
15. honest LED deadline/submit metric;
16. no heap, mutex, blocking delay or unbounded drain on Core 0.

F3a and F3b remain separate commits.

---

## 12.4 F3 silicon qualification

After F3a/F3b:

1. clean Case-C baseline;
2. delay5;
3. restored baseline;
4. delay20;
5. restored baseline;
6. drop10;
7. restored baseline;
8. clockoff;
9. restored baseline;
10. idle;
11. music;
12. active K718 control;
13. approximately 39-byte semantic-payload soak.

The first unacknowledged, uncaught or misclassified fault stops qualification.
Required gates may not remain `UNMEASURED`.

Phase 0 completes only after this battery, the soak, a tracked evidence manifest
and Captain acceptance.

---

## 12.5 Secondary non-critical work

These are real issues but should not displace F2:

- decide whether to add a pytest ignore rule for the preserved `_scratch`
  consult tests so bare `pytest` does not collect duplicate module names;
- remove or modernise `volatile++` warnings in a separate reviewed change;
- reconcile GDFT IRAM declaration attributes;
- restore or replace the missing
  `docs/agent/AGENT_EXECUTION_STANDARD.md`;
- update and commit the device-build registry only after actual successful F2
  flashes;
- decide whether DLE needs a lower-level proof surface.

The large unrelated untracked workspace is not an active recovery task. It must
remain untouched unless separately scoped.

---

## 13. Exact resume boundary

### Required Captain statement

> Main GPIO15 is connected to Bench GPIO16. Bench GPIO15 is connected to Main
> GPIO16. The K1s share GND. The interconnect is 3V3 logic only and secure.
> K718 is irrelevant/off for Case A.

Only after that statement may the orchestrator create the tracked Case-A
attestation.

### Required variables

```bash
RUN_ID="<immutable-run-id>"
LEADER_PORT="<identity-resolved-leader-port>"
FOLLOWER_PORT="<identity-resolved-follower-port>"
FIRMWARE_SHA="a58203183208a4db7fcc7a30d060e6db14673ab1"
```

`FIRMWARE_SHA` is the firmware commit, not documentation HEAD.

### Case-A guarded flash

```bash
bash scripts/dual_sync_probe/run_f2_flash.sh \
  --case A \
  --run-id "$RUN_ID" \
  --firmware-sha "$FIRMWARE_SHA" \
  --attestation \
    "artifacts/k1_dual_sync_eval_2026-07-08/recovery/f2/$RUN_ID/attestations/case_A.json" \
  --leader-port "$LEADER_PORT" \
  --follower-port "$FOLLOWER_PORT"
```

### Case-A capture

```bash
bash scripts/dual_sync_probe/run_f2_abc.sh \
  --case A \
  --physical-state sync-only \
  --out-root "_scratch/dual_sync_f2_abc_$RUN_ID" \
  --run-id "$RUN_ID" \
  --leader-port "$LEADER_PORT" \
  --follower-port "$FOLLOWER_PORT" \
  --firmware-sha "$FIRMWARE_SHA" \
  --flash-manifest \
    "artifacts/k1_dual_sync_eval_2026-07-08/recovery/f2/$RUN_ID/uploads/flash_A.json" \
  --attestation \
    "artifacts/k1_dual_sync_eval_2026-07-08/recovery/f2/$RUN_ID/attestations/case_A.json"
```

These commands are shown for the next execution agent. They are not authority
to flash before physical attestation and fresh identity checks.

---

## 14. Repository state and ownership boundary

### Tracked recovery state

- Current HEAD: `4d685a8`.
- Origin parity: `0 ahead / 0 behind`.
- Recovery commits are published.

### Pre-existing dirty tracked file

`docs/hardware/device-build-registry.md` remains modified and intentionally
uncommitted.

Its current changes record the earlier `3a9724e` dual-sync probe flashes and
port mapping. They were not absorbed into recovery commits because:

- they pre-date the final F2 images;
- the registry should be updated after actual F2 flashes;
- unrelated dirty content belongs to Captain unless explicitly adopted.

### Untracked workspace

The repository contains many unrelated untracked skills, artefacts, settings
and research files. None were deleted, staged or claimed by this recovery.

`ssa/f1_firmware_contract.md` also exists locally but is not tracked. Its
decision-critical findings were incorporated into firmware, tests and the
tracked progress ledger, so this is not a proof blocker. It should be reviewed
and committed separately only if the raw SSA contract itself is required for
long-term audit.

---

## 15. Evidence index

### Governing documents

- [Canonical recovery authority](recovery-plan.md)
- [Current task plan](task_plan.md)
- [Findings ledger](findings.md)
- [Progress/test/build ledger](progress.md)
- [F2 evidence contract](f2/README.md)
- [Probe log contract](../probe-log-contract.md)

### Host/oracle implementation

- [`logfmt.py`](../../../scripts/dual_sync_probe/logfmt.py)
- [`correlate.py`](../../../scripts/dual_sync_probe/correlate.py)
- [`gate_eval.py`](../../../scripts/dual_sync_probe/gate_eval.py)
- [`capture.py`](../../../scripts/dual_sync_probe/capture.py)
- [`f2_capture.py`](../../../scripts/dual_sync_probe/f2_capture.py)
- [`f2_flash.py`](../../../scripts/dual_sync_probe/f2_flash.py)
- [`run_f2_abc.sh`](../../../scripts/dual_sync_probe/run_f2_abc.sh)
- [`run_f2_flash.sh`](../../../scripts/dual_sync_probe/run_f2_flash.sh)
- [`run_gate0_segments.sh`](../../../scripts/dual_sync_probe/run_gate0_segments.sh)

### Firmware implementation

- [`k1_sync_link.cpp`](../../../SPECTRASYNQ_K1_FIRMWARE/network/k1_sync_link.cpp)
- [`k1_sync_link.h`](../../../SPECTRASYNQ_K1_FIRMWARE/network/k1_sync_link.h)
- [`ble_remoted_central.cpp`](../../../SPECTRASYNQ_K1_FIRMWARE/network/ble_remoted_central.cpp)
- [`ble_remoted_central.h`](../../../SPECTRASYNQ_K1_FIRMWARE/network/ble_remoted_central.h)
- [`k1_ble_midi_decoder.cpp`](../../../SPECTRASYNQ_K1_FIRMWARE/network/k1_ble_midi_decoder.cpp)
- [`k1_ble_midi_decoder.h`](../../../SPECTRASYNQ_K1_FIRMWARE/network/k1_ble_midi_decoder.h)
- [`serial_menu.h`](../../../SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h)
- [`serial_cmd_table.def`](../../../SPECTRASYNQ_K1_FIRMWARE/serial/serial_cmd_table.def)

### Tests

- [`test_dual_sync_oracle.py`](../../../tests/test_dual_sync_oracle.py)
- [`test_dual_sync_probe_firmware_static.py`](../../../tests/test_dual_sync_probe_firmware_static.py)
- [`test_ble_midi_firmware_decoder.py`](../../../tests/test_ble_midi_firmware_decoder.py)
- [`test_k1_upload_guard.py`](../../../tests/test_k1_upload_guard.py)

### Independent review evidence

- [F0 implementation review](ssa/f0_implementation_review.md)
- [F0 host contract](ssa/f0_host_contract.md)
- [P-1 authority contract](ssa/p1_authority_contract.md)
- [F1 firmware contract](ssa/f1_firmware_contract.md)

---

## 16. Final hand-off

The recovery did what it was supposed to do before hardware:

- it made false PASS materially harder;
- it repaired the known BLE defects;
- it found and repaired several deeper lifecycle and evidence defects;
- it produced immutable, identity-verifiable probe images;
- it created a bounded A/B/C experiment that can distinguish the remaining
  failure class;
- it preserved the hard Captain STOP before product-level fault work.

The honest current statement is:

> **The recovery machinery is ready. The recovery result is not yet known.**

The next useful action is not more host refactoring or another speculative BLE
change. It is Captain's physical wiring attestation followed by one guarded
Case-A run. Every later action depends on that evidence.

---

## 17. Debrief verification record

This debrief was reconciled against the live workspace on 2026-07-28 using:

```bash
git status --short
git branch --show-current
git rev-parse HEAD
git log --oneline --decorate -15
git diff --shortstat 3a9724e..4d685a8
git diff --name-only 3a9724e..4d685a8
git rev-list --left-right --count \
  HEAD...origin/lane/dual-sync-phase0
bash scripts/agent/session-bootstrap.sh
```

The current focused proof suite was rerun:

```bash
PYTHONPATH=. /Users/spectrasynq/miniforge3/bin/python -m pytest -q \
  tests/test_ble_midi_firmware_decoder.py \
  tests/test_dual_sync_oracle.py \
  tests/test_dual_sync_probe_firmware_static.py \
  tests/test_k1_upload_guard.py
```

Result:

```text
134 passed, 24 subtests passed
```

The document itself passed:

- `git diff --check`;
- local Markdown-link existence validation: 48 links checked, none missing;
- placeholder scan;
- branch/local-origin parity check;
- direct source checks for current fault verbs, stamp-fake delays, dummy
  24-byte payload, AP sentinel zero and Gate-3 naming.

No serial command, upload, reset, GPIO action or other hardware mutation was
performed while producing this debrief.
