---
abstract: "Canonical amended execution authority for dual-sync F0-F3 recovery. Supersedes the Cursor-only recovery draft and the earlier Phase-0 retry path."
status: active
branch: lane/dual-sync-phase0
baseline_sha: 3a9724e
---

# Dual-sync F0-F3 recovery — canonical execution authority

## Decision

Retain the strategic sequence:

`F0 host trust → F1 link hardening → F2 silicon A/B/C1/C2 → Captain STOP → F3 real Gate-0`

Locked boundaries:

- BLE GATT is not yet failed.
- No ESP-NOW, M2 work, radio manager, or transport pivot in this tranche.
- No reuse of `_scratch/dual_sync_p05_gate0_20260727/run_gate0.sh` as Gate-0.
- No cross-flash between `F887A500` and `B489A500`.
- Never run `start_noise_cal`.
- F0 and F1 remain separate commits.
- F3 requires A, B, C1 and C2 software PASS, required physical feedback,
  complete evidence collection and explicit Captain GO.
- No device action substitutes for the scripted A/B/C1/C2 evidence matrix.

This file is the sole recovery execution authority. The Cursor plan
`~/.cursor/plans/dual-sync_f0-f3_recovery_ff1ff901.plan.md` is a superseded
working draft. The older `../phase0-plan.md` remains historical product design
context and is not the recovery work order.

## Hardware identity

| Role | Chip | Environment | LED map | Mic |
|---|---|---|---|---|
| Leader | `F887A500` | `k1_sync_probe_main` | GPIO 6/7 | SPH0645 |
| Follower | `B489A500` | `k1_sync_probe_bench` | GPIO 4/5 | IM73D |

GPIO oracle: Main15→Bench16, Bench15→Main16, GND↔GND. Pulse generation remains
link-gated.

## Proof vocabulary

Every gate and overall verdict uses:

`PASS | FAIL | BLOCKED | UNMEASURED`

- `overall_status` is the enum.
- `overall_pass` is a derived boolean equal to
  `overall_status == "PASS"`.
- CLI exit codes: `0=PASS`, `1=FAIL`, `2=BLOCKED`, `3=UNMEASURED`,
  `4=contract/input error`.
- No caller may use enum-string truthiness.
- `n == 0` is `BLOCKED`.
- Missing instrumentation is `UNMEASURED`.
- Required `UNMEASURED` subgates prevent overall PASS.

## Link Ready contract

Evaluate one coherent post-settle connection epoch only. Do not aggregate
across reconnects or resets.

PASS requires all of:

1. One leader `link up` and one follower `link up` in the selected epoch.
2. No unexpected `link down`, reconnect, reset, sequence epoch change, or
   non-monotonic stream counter after settling.
3. Leader `tx >= 300`.
4. Follower `rx >= 300` and `apply >= 300`.
5. Follower clock estimator has at least 10 valid samples. The leader does not
   emit estimator samples and is not required to do so.
6. At least 10 complete, sequence-paired GPIO rounds.
7. `stream_expected > 0`.
8. Final negotiated BLE values are recorded: connection interval, latency,
   MTU and PHY. Request submission and negotiated values are separate fields.
   DLE remains `REQUESTED_UNVERIFIED` unless lower-level proof is added.

## Role-specific health

- Both roles: FPS, internal heap minimum, reset/disconnect counters and
  measured AP timing when available.
- Leader only: K718 dial link and dial traffic.
- Follower only: transport loss/duplication and application consume loss.
- LED submit/deadline counters are per device.
- Never label a software submit/deadline counter as a physical
  `ws2812_glitch` measurement.

## Phase P-1 — authority reconciliation

Deliverables:

- This tracked canonical plan.
- Tracked `task_plan.md`, `findings.md`, and `progress.md` under `recovery/`.
- Dual-sync lane routing in `AGENT_OS.md`, `.claude/handoff.md`,
  `docs/spec-index.md`, and root `progress.md`.
- `repo-truth.sh` validates an explicit branch authority rather than merely
  finding stale IM73D text.
- Preserve the existing dirty registry and build-wrapper changes; stage only
  explicitly owned files.

Exit:

- Documentation/source-truth diff reviewed.
- Docs-only commit created.
- No registry or existing dirty wrapper change included.

## Phase F0 — host trust root

### F0.1 Dependency pin

Pin `h2zero/NimBLE-Arduino@2.5.0` in both existing sync environments. Record
the resolved `library.properties` version and build hashes. Because
`platformio.ini` changes, F0 is firmware-affecting for commit-gate purposes.

### F0.2 Grammar and strict proof mode

- Add `role=leader|follower` to health records.
- Keep legacy parser compatibility for archived fixtures.
- F2/F3 strict proof mode rejects missing roles.
- Add explicit local timestamps to follower `clk` records.
- Parse link up/down events and reset/epoch boundaries.
- Update `probe-log-contract.md` in the same commit.

### F0.3 Correlation

- Preserve per-role health instead of discarding leader health.
- Split:
  - `transport_expected`, `transport_loss`: leader TX → follower RX.
  - `apply_expected`, `apply_missing`: follower RX → follower apply.
- Export coherent epoch diagnostics and complete GPIO rounds.

### F0.4 Verdict implementation

Implement the proof vocabulary and CLI exit contract above. Summary, JSON,
runner and tests must compare statuses explicitly.

### F0.5 Host runners

1. Add a testable capture helper.
2. Add a segmented plumbing runner with supported F0 verbs only:
   `off,delay5,delay20,drop10`.
3. `restored` is a segment label mapped to `sync_fault=off`.
4. `clockoff` is rejected until F3.
5. Keep both serial sessions open, require exact ACKs, insert segment markers,
   never overwrite, restore `off` in an exit trap, and treat non-PASS CLI codes
   without accidental shell abort.
6. Add a separate tracked F2 A/B/C1/C2 runner; do not call it Gate-0.

### F0.6 Required tests

- Empty and health-only logs are `BLOCKED`.
- String statuses cannot produce a truthy PASS or exit 0.
- Full synthetic coherent link passes Link Ready.
- Multiple disconnected epochs cannot accumulate to PASS.
- Follower dial state cannot affect leader dial uptime.
- AP p95 zero is `UNMEASURED`.
- Zero expected stream is `BLOCKED`.
- Silicon-shaped `drop10`: RX present, apply absent.
- Supported/unsupported fault-token mapping and ACK failure.
- Non-overwrite and restored→off behaviour.
- Old grammar parses outside strict mode; strict mode rejects missing role.

### F0 exit

- Focused oracle/runner tests PASS.
- Full `pytest tests/` PASS.
- `bash scripts/agent/pio-build.sh k1_hardware` PASS.
- Existing sync main and bench builds PASS.
- Exact NimBLE version and build hashes recorded.
- Narrow staged diff reviewed.
- Green F0 commit.
- Push only after the commit; verify remote SHA equals local F0 SHA and record
  it in `progress.md`.

## Phase F1 — SyncLink hardening

### F1.1 Scan and advertising

- Retry scan from `isScanning()` state in both translation units; check
  `start()` returns.
- Enable scan response before setting the name.
- Check UUID/name/start/active advertising results.
- Match service UUID in shared `onDiscovered`/`onResult` logic.
- Do not restart advertising in `onConnect`; checked restart on disconnect.

### F1.2 Fail-closed initialisation

- Check `NimBLEDevice::init()` and return before using server/scan APIs on
  failure.
- Check `xTaskCreatePinnedToCore() == pdPASS`.
- Distinguish request returns from negotiated connection values.
- Log settled MTU/interval/latency/PHY through callbacks or queried
  `NimBLEConnInfo`.

### F1.3 Correct init guards

Leader order:

1. Start SyncLink when `SB_K1_SYNC_PROBE && K1_SYNC_ROLE_LEADER`.
2. Start Remoted only when `SB_K1_BLE_REMOTED`.
3. Start follower SyncLink only in the follower build.

Guard both declaration and use of `sb_k1_ble_remoted_is_linked()` with
`SB_K1_BLE_REMOTED`. A sync-only leader emits `dial_linked=0` with the metric
marked not applicable.

### F1.4 Case-A environment

Add `k1_sync_probe_main_sync_only` without Remoted sources or flag.

Mandatory registrations:

- `scripts/agent/pio-build.sh`
- `scripts/platformio/k1_upload_guard.py` as main `F887A500`
- upload-guard tests for correct target and both cross-target rejections

Unknown/unmapped sync environments are an F1 failure.

### F1 exit

- Focused static/oracle/upload-guard tests PASS.
- Full `pytest tests/` PASS.
- `k1_hardware`, sync main, sync bench and sync-only builds PASS through the
  wrapper.
- Production radio-isolation boundary PASS.
- Exact dependency/build hashes recorded.
- Narrow staged diff reviewed.
- Green F1 commit.

## Phase F2 — provenance-split A/B/C1/C2 silicon isolation

F2 retains two independent authorities:

```text
HOST_EXECUTION_SHA=<clean committed controller HEAD>
FIRMWARE_SOURCE_SHA=a58203183208a4db7fcc7a30d060e6db14673ab1
```

The host SHA may be a documentation/controller descendant. It must never
replace the firmware SHA. Device `:build` remains `a582031…`; device
`:image_id` must match the reviewed application identity.

### Image gate

The reviewed dual-role leader and follower images are preserved. The reviewed
sync-only leader image is missing and three bounded reproductions failed its
BIN/ELF hashes. The tracked image-set ledger is therefore `BLOCKED`.

No hardware write is allowed until the original reviewed sync-only artefact is
recovered or Captain separately authorises a complete new frozen image set.
Normal PlatformIO upload is forbidden because it rebuilds.

### Controllers

- `f2_image_set.py`: complete reviewed-image and package provenance.
- `f2_ports.py`: USB-serial-first binding and immutable
  `pre_A→A→B→C1→C2` port chain.
- `f2_flash.py`: positive/negative guards, partition read-back and pinned
  application-only esptool write for A/B.
- `f2_capture.py`: recursive A/B/C1/C2 capture and oracle revalidation.
- `f2_reboot.py`: Captain-authorised typed dual reset for C2, ACK capture,
  non-consuming USB-serial rebinding, two-role cold-start establishment
  capture and same-image/new-nonce proof.
- `f2_status.py`: immutable C1/C2 pre-attestation and feedback validation,
  separate software/physical/acceptance status and Captain STOP.

Every controller binds `HOST_EXECUTION_SHA`, `FIRMWARE_SOURCE_SHA`, the image
set, prior port manifest and immutable run root.

### Cases

- A: reviewed sync-only leader plus follower; both flashed.
- B: reviewed dual-role leader; follower neither flashed nor reset; K718 off.
- C1: continuing Case-B boots; K718 late joins; no flash or reset.
- C2: same application images after a controlled reset with K718 already
  powered/advertising; both boot nonces must be new.

A non-PASS forbids B. B non-PASS forbids C1. C1 non-PASS forbids C2.
C1 and C2 each require four causal mode changes and separate physical
feedback. C1 proves late join only; broad cold-start coexistence requires C2.

### F2 exit

Software, physical feedback, evidence collection and Captain acceptance are
separate fields. Both physical feedback results PASS still leave acceptance
PENDING until Captain writes a separate immutable decision.

The STOP and its sidecar remain immutable and always state
`f3_authorised=false`. F3 requires a later explicit Captain decision. The
pre-existing dirty device registry remains excluded from controller commits.

## Phase F3 — real Gate-0, only after F2 + Captain GO

F3a and F3b are mandatory separate commits.

### F3a host contract

- Replay stored F2 A/B/C1/C2 captures and prove unchanged baseline verdicts.
- Add real fault fixtures and require every fault to flip its intended
  independent gate.
- Full host gate before commit.

### F3b firmware

- Fixed-capacity static O(1) delay queue; no heap, mutex, blocking delay or
  unbounded drain on Core 0.
- Wrap-safe deadlines, bounded records per poll, overflow/late/reset counters.
- Exact versioned semantic packet byte layout, endianness and `static_assert`.
- Delay5/20 alter scheduled consume deadlines, not printed timestamps.
- Clockoff biases radio offset estimate only.
- GPIO uses BLE sequence before pulse.
- Distinct transport and application loss.
- Real AP p95 definition and instrumentation.
- Honest LED-submit/deadline metric; physical glitch stays `UNMEASURED` unless
  physically instrumented.

### Causal boundary

Gate 3 remains `leader_stamp_to_follower_consume` until one sequence is proven:

`leader audio snapshot → packet → follower state publication → renderer consume → LED submit`

Any mic-capture→LED or cross-core causal claim requires a non-shippable
MabuTrace capture. FastLED submission alone is not physical latch proof.

### F3 qualification

1. Clean Case-C baseline.
2. Each fault ACKed and independently detected.
3. Restored passing baseline after every fault.
4. First uncaught, unacknowledged or misclassified fault stops qualification.
5. Only then run idle, music, dial and soak measurements.
6. Required gates may not remain `UNMEASURED`.

Phase 0 is complete only after a tracked evidence manifest and Captain
acceptance. Compile or flash success is not completion.
