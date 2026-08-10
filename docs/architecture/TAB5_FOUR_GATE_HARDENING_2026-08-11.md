# Tab5 four-gate production hardening

**Decision:** Conditional GO, approved by Captain on 2026-08-11.

**Baseline:** `21d0e593461af468d38394b140e2477bd58bf7f3` on the isolated
`fix/tab5-hardening-20260811` branch. The validated live WDT repair is imported
as an explicitly identified patch; it is not assumed to exist in the baseline.

**Scope:** Tab5 ESP32-P4 firmware, host/native verification, build provenance,
and identity-safe Tab5 silicon proof. No C6 flash, main-K1 intervention, blind
full71 run, IM69D/global authority rewrite, UI-look change, or promotion claim.

The gates are ordered and fail-closed. A later gate cannot waive an earlier
failure. Each gate writes a durable receipt under
`docs/receipts/tab5-hardening-20260811/`.

## Gate contract

| Gate | Purpose | Entry condition | Required exit | Receipt |
|---|---|---|---|---|
| **G0 — Source closure** | Recoverable, machine-independent source and toolchain baseline | Frozen baseline and reviewed source allowlist | Disposable empty-`PLATFORMIO_CORE_DIR` production and native builds from a clean clone using pinned, checksummed dependencies; no undeclared local material | `G0_SOURCE_CLOSURE.md` |
| **G1 — Fault harness** | Prove the oracle detects every targeted failure class | G0 PASS; clean positive control | Every named deliberate mutant is active and killed for its intended reason; no pass-everything or fail-everything oracle | `G1_MUTATION_RECEIPT.md` + `gate1_mutations.json` |
| **G2 — Behavioural hardening** | Close ownership, integrity, recovery, RSSI, and diagnostics defects | G1 PASS | All exact semantics below pass host/native tests and production build invariants | `G2_BEHAVIOURAL_HARDENING.md` |
| **G3 — Silicon release proof** | Prove the production image on the intended P4 | G0-G2 PASS; exclusive hardware window; identity gate PASS | 100 reconnect cycles, controlled fault run, 10-15 minute fault soak, and 45-60 minute ordinary soak meet every threshold below | `G3_SILICON_RELEASE.md` |

## G0 — Source closure

1. Capture a reviewed manifest of active Tab5 production/native source,
   configuration, generation inputs, licences, tests, and build scripts.
2. Exclude `.pio`, extracted toolchains, caches, logs, backups, retired fonts,
   historical Hosted-1.4 material, C6 flash utilities, and unrelated dirty K1
   files. Never use `git add tab5_firmware` or `git add -A`.
3. Record exact PlatformIO, platform, framework, SDK, compiler, and package
   versions; versions must be exact releases or immutable commits, never ranges,
   branches, or floating tags.
4. Record package name, version, source URL, licence, and SHA-256. Archive or
   use an approved internal mirror for nonstandard/fragile build inputs.
5. Prove production and native builds in a disposable clone with a fresh
   `PLATFORMIO_CORE_DIR`, not merely after deleting project `.pio`.
6. Run a second independent empty-core build. Exact binary equality is reported
   only if the hashes match; otherwise the non-deterministic input is identified
   and source/build reproducibility is claimed narrowly.
7. Confirm the live WDT fix is imported as a named diff from the frozen baseline
   and retains the live receipt's ownership semantics.

## G1 — Fault-evident harness

Every mutation has an unmutated positive control and a named finding delta.
Mutations run only against temporary copies and must prove that their target was
actually changed. An inert mutant is a gate failure.

| ID | Injected fault | Required detection |
|---|---|---|
| M1 | NimBLE callback calls Deck/LVGL, allocates `String`, logs bytes, or performs HCI/lifecycle work | Callback-ownership invariant fails |
| M2 | Both framework connect callbacks create logical connects | Exactly-once connection-owner invariant fails |
| M3 | Relevant state queue event is dropped or oversized without desynchronising | Fail-closed recovery invariant fails |
| M4 | Snapshot member mutates confirmed state/UI before validated END | Transactional-commit invariant fails |
| M5 | Corrupt count/length/CRC/generation/required member/duplicate/unknown/range | Whole snapshot is rejected with zero partial mutation |
| M6 | Partial, stale, out-of-order, gapped, or cross-generation delta batch | Whole batch is rejected; resnapshot required where specified |
| M7 | Unknown-handle or transient/fatal RSSI policy is removed | Fake-HCI state/call-count/backoff invariant fails |
| M8 | Production HCI or per-value diagnostics are enabled | Resolved-production-configuration gate fails |
| M9 | Required source/config disappears from the manifest | Source-closure check fails before build |

The harness is fault-evident for these classes only; green is not a proof that
unimagined firmware defects do not exist.

## G2 — Behavioural hardening

### Ownership and queue loss

- NimBLE callbacks may only copy bounded raw bytes or a tiny link record into
  static queues and increment atomic counters/flags. No heap allocation, Deck or
  LVGL mutation, advertising, Serial byte dump, HCI command, or connection-state
  mutation is allowed there.
- `loopTask` is the sole owner of connection lifecycle, confirmed Deck state,
  reassembly, staging, recovery, RSSI maintenance, and all LVGL mutation.
- There is exactly one active connection owner and one connection generation.
  Duplicate connect callbacks and stale completion events are idempotently
  discarded.
- Link/control events cannot be starved behind state payloads. Queues and drain
  work have static capacities and measured per-loop budgets.
- Any relevant queue overflow, event loss, oversized value, truncated
  transaction, framing error, revision gap, or generation discontinuity sets a
  desynchronised latch. The last valid committed snapshot remains visible; no
  later delta is accepted until a complete valid resnapshot commits.
- Only one loop-owned recovery operation may be in flight. Recovery disarms,
  clears pending/reassembly/staging, purges stale queued state, requests at most
  one disconnect for the fault epoch, and uses bounded advertising/reconnect
  backoff.

### Snapshot and delta transaction semantics

- Staging is static and bounded; receive and callback paths allocate no heap.
- Validate count, record and payload lengths, CRC, connection/session generation,
  required members, duplicate members, unknown members, value types/ranges,
  ordering, staleness, and generation wrap rules.
- CRC covers transaction metadata needed to bind the payload to its generation
  and declared count, not payload bytes alone.
- A snapshot changes no confirmed transport state, application state, latency
  marker, or LVGL object before every validation succeeds.
- One loop-owned commit applies the complete staged snapshot. One invalid member
  rejects the whole transaction. Last-known-good state survives resnapshot.
- A complete delta batch is staged and validated before the first confirmed
  value changes. A revision gap accepts no member and requires a fresh snapshot.
- Corrupt, incomplete, duplicate, stale, out-of-order, and cross-generation
  data can never reach `ARMED`/`LIVE`.

### RSSI maintenance

- UI reads cached RSSI only.
- At most one RSSI operation is in flight. There is no busy wait or synchronous
  retry loop. The operation has a bounded timeout and generation tag.
- Outcomes are classified as success, transient failure, unknown/invalid handle,
  disconnected, and fatal transport failure.
- Unknown handle enters controlled disconnect/resynchronisation. Transient
  failures use bounded backoff; fatal transport failures disarm and suspend HCI
  maintenance until host lifecycle recovery.
- Default cadence/backoff is measured, not assumed: initial sample interval
  2 seconds; transient 2/4/8 seconds capped at 30 seconds; advertising recovery
  250/500/1000/2000/4000 ms capped at 4 seconds. G3 may tune constants only from
  recorded occupancy and timing evidence.
- Stale completions from an older connection generation are discarded.
- Maximum loop and callback occupancy is recorded and must remain inside the
  watchdog/headroom thresholds below.

### Production diagnostics invariant

- Production `tab5_p4` resolves HCI path and per-value verbose diagnostics OFF.
- Diagnostic tracing exists only in an explicitly non-shippable environment.
- A production configuration assertion and release inspection fail closed if
  verbose HCI/per-value diagnostics are enabled.
- Production retains bounded cumulative health counters and a low-rate summary,
  not per-packet logs.

## G3 — Silicon release proof

### Identity and flash

- Run the Deck16 first-contact gate.
- Verify the explicit selected port maps to Tab5 P4 MAC
  `30:ed:a0:e0:c1:a0` immediately before writing.
- Flash the P4 application image only. No C6/main-K1/erase operation.
- Record source commit, environment, binary/ELF hashes, port, MAC, time, and
  post-flash identity/readback.

### 100-cycle reconnect test

Each successful cycle must prove one active owner, no duplicate connect attempt,
a fresh connection generation, HELLO admission, one complete valid snapshot
commit, and zero stale completion from an earlier generation.

Acceptance across all cycles:

- 100/100 valid cycles commit exactly one complete snapshot.
- Zero partial UI or confirmed-state mutation on corrupt/incomplete snapshots.
- Zero accepted deltas after revision loss until a valid resnapshot.
- Zero watchdog, panic, assertion, deadlock, unexpected reboot, or reconnect storm.
- Zero normal-run state drops; injected loss produces deterministic desync and
  one recovery state machine, never silent continuation.
- Exactly one active connection owner and bounded connection-object/task counts.
- State queue high-water mark at or below 75% of capacity in ordinary cycles.
- No unbounded growth in free-heap loss, largest-block fragmentation, queue
  occupancy, task count, or connection objects.
- Production HCI/per-value diagnostic streams remain absent.

### Fault and soak envelope

1. **Dense fault run, 10-15 minutes:** corrupt/missing/middle-dropped snapshot,
   revision gap, queue saturation in a diagnostic/fake path, abrupt peer loss,
   unknown RSSI handle, transient/fatal RSSI outcomes, and recovery.
2. **Ordinary production soak, 45-60 minutes:** normal linked operation with
   production diagnostics off after the fault run.

Pass thresholds:

- No WDT/LVGL assertion/panic/reboot/deadlock.
- No partial transaction commit, stale owner, haunt TX, or false `ARMED` state.
- RSSI request rate at or below 0.5 Hz in steady state; no immediate retry loop.
- Callback hot path performs no heap/log/HCI work.
- Maximum queue drain is 8 state chunks or 1 ms per ingress pass, whichever
  occurs first, unless G2 tests establish a lower safe bound.
- Post-warm free DRAM has no monotonic loss above 2 KiB; largest free block,
  queue HWM, task count, and connection-object count stabilise. Any threshold
  miss leaves G3 `NOT_VERIFIED` and triggers root-cause analysis, not capacity
  masking.

## Stop conditions

Stop and reassess before continuing if:

- a complete snapshot cannot fit bounded static staging memory;
- RSSI cannot be bounded without blocking the loop;
- one clean connection owner cannot be represented by the loop-owned state machine;
- an active mutant survives or a positive control fails;
- a clean-clone build depends on undeclared local material;
- the 100-cycle test exposes accumulating lifecycle state that cannot be fixed
  without clearer task isolation.

Only a stop condition may reopen the deferred dedicated transport/RSSI actor
architecture. Queue depth is capacity tuning after correctness, never the fix.

## Authority claim block

```text
DECK16_B1_B2_CORE_FUNCTIONAL_PASS=PASS
EXTENDED_RECOVERY_HARDENING=PASS
STANDBY_DIMMING=STRUCK
PRODUCTION_READY=NO
MERGE_OR_PROMOTION=HOLD
```

No gate in this programme upgrades `PRODUCTION_READY` or promotion authority.
