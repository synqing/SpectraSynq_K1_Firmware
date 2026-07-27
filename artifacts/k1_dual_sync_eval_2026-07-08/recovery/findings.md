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

## F2 preflight findings

- Current USB enumeration maps leader chip `F887A500` to USB serial
  `B4:3A:45:A5:87:F8` and follower chip `B489A500` to
  `B4:3A:45:A5:89:B4`. Both correct-target upload-guard probes passed and both
  cross-target negative controls exited `2`. These are read-only observations,
  not flash authority.
- The former F2 runner bound runtime `:build` to current HEAD while the
  post-F1 binaries embedded the earlier F1 commit. A documentation checkpoint
  could therefore invalidate sound binaries without changing firmware.
  Firmware provenance and host-controller provenance must be separate fields.
- Minimal self-authored prior-case JSON could satisfy A→B→C ordering. Every
  prior manifest and every referenced raw file must be rehashed, reparsed and
  re-evaluated before the next case.
- A BIN file hash alone does not identify the application installed on the
  ESP32. F2 now requires the ESP application descriptor ELF identity extracted
  from the preserved image and read back from the running device.
- K718 power and physical dial turns cannot be inferred from a caller-supplied
  string. Each case requires a tracked Captain attestation; Case C additionally
  requires a pre-run commitment to at least three detents and causal
  mode-apply→confirmation-write evidence. The BLE write proves K1 submission,
  not K718 receipt, so physical display feedback remains pending in
  `CAPTAIN_STOP.md`.
- Missing samples or reset/regressed counters are `BLOCKED`. Observed dial
  traffic in Case B, reconnect/lifecycle changes, stream loss or error deltas in
  Case C are `FAIL`; neither may be laundered into a generic absence of proof.
- Case B reuses the validated Case-A follower upload event and writes only the
  dual-role leader. Both required Case-A builds/guards complete before its
  first upload; partial write attempts produce a tracked `BLOCKED` action
  event. Case C has no upload path.
- A per-boot runtime nonce and monotonic uptime bind capture to the post-flash
  process. Case C must continue the exact Case-B boot on both devices, closing
  the same-image reflash/reset ambiguity that build and image hashes cannot
  detect.
- No device was flashed and no manual serial command was sent during this
  preflight.

## F2a.1 periodic-window finding

- A baseline `:dial_status` snapshot precedes the segment and the end snapshot
  follows its capture, while the first and last 1 Hz counter lines necessarily
  sit inside that interval. Exact equality between their deltas is therefore
  impossible whenever traffic occurs before the first periodic sample or after
  the last.
- The evidence contract now requires each cumulative periodic counter to stay
  between its coherent baseline and end values. Case C separately requires
  positive periodic notify/decode/enqueue/apply movement, so endpoint-only
  traffic cannot manufacture PASS.
- Regressed endpoint snapshots remain `BLOCKED`; a monotonic endpoint window
  contradicted by periodic cumulative values is `FAIL`.

## F2a.2 meaningful-mode finding

- The first F2b implementation labelled every accepted primary/secondary mode
  record as a dial-mode application, even when the accepted ordinal already
  matched the committed mode. Three duplicate no-op records plus one
  confirmation could therefore satisfy the Case-C host contract without three
  real mode changes.
- Case-C evidence now derives a per-control ordinal sequence from the coherent
  baseline `last_confirm_pm`/`last_confirm_sm`, counts only changes, requires at
  least three meaningful events, and requires the endpoint
  `dial_mode_apply_ok` delta to equal that event count.
- This remains evidence of K1 accepting distinct mode changes, not proof that
  K718 displayed the confirmation. Physical display acceptance remains a
  Captain decision at the STOP.
