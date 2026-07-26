---
abstract: "Canonical amended execution authority for dual-sync F0-F3 recovery. Supersedes the Cursor-only recovery draft and the earlier Phase-0 retry path."
status: active
branch: lane/dual-sync-phase0
baseline_sha: 3a9724e
---

# Dual-sync F0-F3 recovery — canonical execution authority

## Decision

Retain the strategic sequence:

`F0 host trust → F1 link hardening → F2 silicon A/B/C → Captain STOP → F3 real Gate-0`

Locked boundaries:

- BLE GATT is not yet failed.
- No ESP-NOW, M2 work, radio manager, or transport pivot in this tranche.
- No reuse of `_scratch/dual_sync_p05_gate0_20260727/run_gate0.sh` as Gate-0.
- No cross-flash between `F887A500` and `B489A500`.
- Never run `start_noise_cal`.
- F0 and F1 remain separate commits.
- F3 requires A, B and C PASS plus explicit Captain GO.
- No device action substitutes for the scripted A/B/C evidence matrix.

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
6. Add a separate tracked F2 A/B/C runner; do not call it Gate-0.

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

## Phase F2 — scripted silicon isolation

Evidence root may contain raw captures under
`_scratch/dual_sync_f2_abc_<date>/`, but each case also produces a tracked
compact manifest with:

- source commit and environment
- chip identity and port at action time
- ELF/bin hashes
- exact commands
- raw-log hashes/locations
- Link Ready JSON
- negotiated BLE values
- reset/disconnect/epoch counts

Cases:

- A: sync-only leader + follower.
- B: full dual-role leader, K718 powered off.
- C: exact Case-B firmware with K718 powered on; no B→C reflash.

Case C additionally requires post-settle:

- 100% leader dial-linked health
- zero dial disconnect/reconnect events
- real dial turns with increasing notify/decode/apply counters
- confirmed mode/control feedback

F2 exit requires A PASS, B PASS and C PASS. A failure stops B/C. B or C
failure prevents F3. Write a tracked `CAPTAIN_STOP.md`; F3 requires explicit
Captain GO recorded there.

The device registry is updated after actual flashes, but its pre-existing dirty
content is never auto-committed or absorbed into another commit.

## Phase F3 — real Gate-0, only after F2 + Captain GO

F3a and F3b are mandatory separate commits.

### F3a host contract

- Replay stored F2 A/B/C captures and prove unchanged baseline verdicts.
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
