# Progress — plan fold

## 2026-08-16 — G0R map–territory

```text
G0_ORACLE_IMPLEMENTATION     = CLOSED
G0_CONTRACT_CONTENT          = REOPENED  (G0R)
G1_B489_SMOKE                = VALID_CURRENT_IMPLEMENTATION
G1_F887_PRODUCTION           = ABSENT
G2_7P5_CHARACTERISATION      = COMPLETE_ENOUGH_FOR_SERVICE_DEFICIT
G2_PRODUCT_SELECTION         = BLOCKED_BY_G0R
G3                           = BLOCKED
B489_ABBA_FLASH_NOW          = HOLD
HARNESS_FIRMWARE_PIN_SHA     = 14c53d239524aa891e71470880f6917d4adf2ea6
FINAL_ABBA_TOOLCHAIN_PIN_SHA = c1aba345603bc2cacc8cf30648768d346f572779
```

Authority: `docs/superpowers/plans/2026-08-16-g0r-cadence-authority.md`.
Deployed `gate0/contract.json` unchanged (7.5 ms). Draft amendment
`gate0/amendments/G0R_2026-08-16.draft.json` is `DRAFT_AWAITING_CAPTAIN` only.

## 2026-08-15

- Reloaded the reconciled audit, delegation contracts and named planning/system skills.
- Confirmed repository advanced beyond the audit SHA; exact provenance reconciliation
  is now Gate 0 work.
- Classified the two-slot lifetime issue as a required correction, not an optional
  enhancement.
- Registered two read-only review tasks before dispatch.
- Reconciled `b80e4ada` -> `8026807f` -> `15d3a85d`; inspected every changed
  decision-critical path between the audit and plan-fold SHAs.
- Re-read current snapshot, semantic aggregator, mode request, effect commit,
  task-creation and timestamp code with line-level evidence.
- Ran Agent Reach health check and bounded skills.sh verification; no installation.
- Folded the post-review into `EXECUTION_PLAN.md` and amended the original audit so
  its stale Gate 0-4 and two-slot language cannot be mistaken for authority.
- Built the retained-template System Design DOCX. The first packaged-render attempt
  failed because the chosen Python runtime lacks `pdf2image`; manual render QA is next.
- Received and reconciled FRTOS-07 and FRTOS-08. Their required amendments are now
  explicit invariants, forced-interleaving cases and independent gate ownership in
  `EXECUTION_PLAN.md`.
- Corrected the DOCX table-header contrast, architecture-heading pagination and the
  merged rollout-constraint row, then inspected all eight rendered pages.
- Re-ran the exact-head host gates: 112 focused architecture tests passed, all 5
  AP-input-integrity P2 tests passed, and production radio isolation was proven.
- Closed the plan-fold lane without production firmware, build, device, serial or GUI
  mutation. The next implementation branch remains inert until AP-P4 permits work.

## 2026-08-15 — implementation start

- Captain authorised full end-to-end implementation on the dedicated scheduling branch.
- Restored the committed planning ledger, ran session bootstrap and found a deliberate
  branch/active-lane mismatch: the feature branch existed but governance still named
  `main` and the AP-input lane.
- Classified Captain's directive as a scheduling implementation override, not a silent
  completion of the separate AP-input P4 promotion.
- Began the atomic active-handover/spec-index/handoff/progress update required to make
  repo-truth pass before source mutation.
- Committed and pushed the scheduling authority checkpoint as `82e20197`; subsequent
  `scripts/agent/repo-truth.sh` execution passed on
  `feat/k1-scheduling-generation-hardening`.
- Froze the Gate 0 first-party source population at 535 files. The sorted manifest
  SHA-256 is `06b03c3d0a3c6352e5383ffea151f579636adc66394c73b556add68f74c5e0b7`.
- Partitioned the manifest into seven deterministic round-robin read contracts and
  dispatched exhaustive read-only reviewers plus dedicated harness-inventory and
  adversarial fault-battery reviewers.
- Verified the ESP-IDF 5.4.1 FreeRTOS surface and searched the public skills index.
  No external package was installed: repository-specific evidence and the exact
  framework version remain the implementation authorities.
- Routed Atomic Agents out of the firmware runtime. Its useful contribution is the
  discipline of small typed units; adding a Python agent framework to an ESP32 hot
  path would create no product value.
- Completed the exhaustive seven-way source read: all 535 first-party source paths
  were read in full, with 535/535 ledger rows and zero failures. FRTOS-09 through
  FRTOS-15 are retained as evidence.
- Completed the existing-harness inventory and adversarial fault-battery review.
  Both independently identified the same missing Gate 0 unit: a fail-closed admission
  wrapper with a frozen trust root and explicit inner RED witnesses.
- Implemented the host-only Gate 0 contract, provenance snapshotter, admission oracle,
  frozen six-file trust root and oracle-only valid fixture. No production firmware or
  PlatformIO file changed.
- Expanded the required mutation battery from the plan's coarse classes to 21 exact
  witnesses: source/build/binary/identity drift, sample/mode drift, trace schema and
  ordering, generation corruption, final-byte/RMT proof, fixture/test-ledger evasion and
  perturbing output.
- Gate 0 focused qualification passed 30 tests; the good control is deterministic and
  every mutation rejected for its registered reason. Trust-root verification passed.
- The complete repository host gate passed: `1116 passed, 1 skipped` in 182.79 s. The
  one repository-wide skip is not part of the frozen required Gate 0 node inventory;
  Gate 0 itself had no skip, xfail or deselection in the final qualification command.
- Gate 0 remains `in progress` until the oracle unit is committed/pushed and an
  independent runner verifies the clean anchored commit and writes the acceptance
  receipt.
- Root review rejected the first anchored oracle commit `19047912` before independent
  acceptance: its focused test asserted that the live first-party source count must
  remain exactly 537. That would turn every later gate's required source/test addition
  into a false trust-root failure. The exact Gate 0 population remains anchored in the
  generated provenance artefact; the reusable test now proves deterministic manifest
  generation and first-party coverage while each gate freezes its own expected digest.
- The corrected oracle landed and was pushed as `68c9a51e`. Independent FRTOS-18
  acceptance then passed on the clean anchored commit: six-file trust root, 30 focused
  tests with no skip/xfail/deselection, 21/21 registered RED witnesses, three identical
  good-control validations and a clean 537-file provenance snapshot. Gate 0 is closed.
- Generated the durable Gate 0 implementation provenance at `68c9a51e`: source-content
  manifest SHA-256 `9cfc8357d7fcdabee4ce6499e3625bb1c2c34f7094d597cc7a1dcd6b9ae42ecf`.
- Completed the FastLED 3.10.3 RMT5 source audit for Gate 1/5. `FastLED.show()` is an
  asynchronous submit boundary, not RMT completion; two 160-pixel channels overlap at
  roughly 5.08 ms wire time each, and a too-fast free-running next frame can rewrite
  FastLED's internal non-DMA payload before the prior completion wait. The next trace
  unit must record official TX-done callbacks and cannot reuse `show_us` as completion.
- Added capture-only full-loop AP stage attribution after the exact four-lane probe
  remained above the Gate-2 service ceiling. The first independent review rejected an
  endpoint that omitted benchmark/encoder/debug service and a fail-open parser; both
  defects were repaired. Attempt 2 independently accepted thirteen ordered offsets,
  exact derived-span checks, explicit unavailable GDFT internal split and a FULL
  endpoint immediately before the deliberate scheduler wait. The complete host gate
  passed (`1165 passed, 1 skipped`), and production plus the bench baseline probe both
  build. Fresh complete B489A500 device capture remains the next proof boundary.
