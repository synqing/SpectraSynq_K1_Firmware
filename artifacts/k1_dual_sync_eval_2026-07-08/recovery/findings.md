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
