# Findings — dual-sync recovery

## Current source truth

- Live branch: `lane/dual-sync-phase0`.
- Baseline HEAD: `3a9724e`.
- Existing dirty tracked files at takeover:
  - `docs/hardware/device-build-registry.md`
  - `scripts/agent/pio-build.sh`
- The dirty registry records the current dual-sync probe flashes and must not be
  auto-committed.
- The dirty wrapper already adds the two existing sync environments; F1 will
  overlap that file and requires explicit narrow staging/ownership treatment.
- The detailed Cursor recovery plan is outside git.
- Most `artifacts/k1_dual_sync_eval_2026-07-08/` documents are currently
  untracked; only `probe-log-contract.md` is tracked.
- The remote has no `lane/dual-sync-phase0` head at takeover.

## Decision-critical defects inherited from review

1. Both-sided clock readiness is impossible; only the follower estimates and
   emits clock samples.
2. The proposed sync-only leader calls and links Remoted symbols without
   `SB_K1_BLE_REMOTED`.
3. String statuses can become truthy PASS/exit 0 unless every consumer is
   migrated explicitly.
4. An unmapped Case-A environment bypasses upload identity enforcement.
5. Existing `drop10` logs RX before suppressing apply, so transport loss alone
   cannot witness the fault.
6. F0 runner tokens `clockoff` and literal `restored` are unsupported by the
   current firmware.
7. F0/F1 as drafted omit the full repository and production-build commit gates.
8. F3 needs codec, semantic-state, renderer, LED-submit and AP instrumentation
   seams beyond `k1_sync_link.*`.

## Authority conflict

`AGENT_OS.md`, `.claude/handoff.md`, `docs/spec-index.md` and root
`progress.md` still route agents to IM73D despite the live dual-sync branch.
`repo-truth.sh` accepts stale IM73D text rather than validating an explicit
branch authority.

## Validation baseline

- Session bootstrap: PASS with warning for the pre-existing dirty registry.
- Focused current tests before implementation:
  `tests/test_dual_sync_oracle.py` +
  `tests/test_dual_sync_probe_firmware_static.py` = 25 passed.
- This is a baseline only and does not prove the amended recovery contract.

## Memory boundary

Historical memory reinforces that Gate-0 needs a fault-evident harness and
paired controls. Current git, files and live silicon evidence remain higher
authority.

## F0 host-trust findings

- NimBLE resolves to exactly `2.5.0` in both existing sync environments after
  replacing the compatible-range specifier with an exact pin.
- A sole numeric epoch match is not proof: role-local epoch values may differ.
  Shared host-time overlap, post-link negotiated state and bounded evidence are
  the proof.
- `Begin` after `link up` is a session boundary even if the ESP-IDF reset line
  was missed.
- Duplicate, reordered, reset and unexpected sequences must remain ordered
  evidence; dictionary de-duplication can hide a false-PASS path.
- A firmware counter named `ws2812_glitch` cannot prove a physical glitch.
  Physical WS2812 evidence remains `UNMEASURED`.
- Persistent-link segment proofs must inherit only captured connection boundary
  records. They must not inherit an earlier segment's stream, GPIO, timing or
  health observations.

## F0b late-attach finding

- `verify_devices()` clears pending serial input before querying chip/build
  identity. On already-running F2 devices that can discard the only boot/link
  transition records while stream, clock and GPIO continue normally.
- A reproduced healthy persistent link without those one-shot lifecycle lines
  returns `BLOCKED` (`leader_up=0`, `follower_up=0`), so F2 requires an explicit
  current-state replay rather than log archaeology.
- The host now sends `:sync_status` to both roles after identity verification
  and accepts only one exact linked ACK, LinkUp and Negotiated record per role
  with coherent role/epoch/MTU. The raw session and parsed
  `SYNC_STATUS.json` remain evidence.
- Per-segment input clearing still presents a conservative false-BLOCK risk if
  it bisects an in-flight TX/RX/apply set. It cannot manufacture PASS and is
  retained until a firmware nonce or sequence-aware boundary exists; F2 uses
  one `off` segment only.

## F1 link-hardening findings

- `NimBLEService::start()` is a deprecated no-op in pinned NimBLE-Arduino
  2.5.0; advertising start invokes the server start. Re-adding the service call
  would add theatre, not readiness proof.
- A raw GAP connection cannot be Link Ready. Leader publication now requires
  both CCCDs plus a valid follower clock request; follower publication requires
  service/characteristic discovery, both subscriptions and a stable exact
  negotiated snapshot.
- Accepted transport values are exact: interval units `6`, latency `0`, MTU
  `247`, TX/RX PHY `2M`. Request acceptance and negotiated read-back remain
  separate diagnostics; DLE stays explicitly `UNMEASURED`.
- Central characteristic writes can cross reconnect generations if the audio
  loop snapshots a pointer while a Core-1 task reconnects. Sync clock writes
  and Remoted confirmations are now owned by their Core-1 connection tasks.
- Leader advertising restart is deferred to the same Core-1 owner as periodic
  stream notify. A generation-bound handle snapshot therefore cannot be
  delivered into a replacement pre-ready connection.
- Clock response `t4` must be stamped in the NimBLE callback. Stamping when the
  Core-1 queue drains can bias the offset by half the scheduling delay and
  invalidate a 4 ms gate.
- NimBLE host/controller callback cost on Core 0 is not claimed eliminated.
  F3 must measure real AP p95, heap and soak effects; F1 only removes
  application-owned periodic GATT work from the Core-0 audio loop.
