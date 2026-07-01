---
abstract: "Session handover, 2026-06-30 (production-readiness lanes N1–N9). Builds on the earlier N2-freeze handover. SHIPPED on the product line lane/remoted-ble-midi-phase-f @ ad08ce1 (pushed): N2 freeze-fix, ACF over-budget root-fix, per-band AGC (N6 'louder→dimmer' fix), N5 release-eng+build-provenance, upload-guard hardening+drift-catcher. N7 OTA is a gated flag-OFF DRAFT on feat/n7-ota-receiver @ d4a7824. N8/N9 are decision memos. The feat/* stack (N3/N2b/N4a) is UN-MERGED and DIVERGED from the product line at N2 → reconcile via new decision D7. Open Captain decisions D1–D7; autonomous remainder = N4 factory-image/NVS tooling. READ before touching K1 firmware or flashing."
---

# K1 Firmware — Session Handover (2026-06-30): Production-Readiness Lanes N1–N9

> **TL;DR** — The two hard launch blockers (silent-idle freeze, over-budget audio loop) are **fixed, device-proven, and shipped**, and the visible "louder→dimmer" defect is **fixed and shipped**. Release-provenance tooling and an anti-brick guard shipped too. The biggest missing subsystem, **OTA**, is now a **built, host-gated, flag-OFF DRAFT** awaiting your enable/keys decision (D3). What's left is either **your decision** (D1–D7) or **clean ops-tooling handoff** (N4 factory-image/NVS). Read §6 (doctrine) before flashing anything. Companion: `docs/handover/2026-06-30-n2-freeze-remediation-and-session-handover.md` (the freeze incident) and `docs/architecture/production-readiness-lane.md` §10 (live lane status).

## 1. Canonical state (verify first — map-territory)
- **Product line = `lane/remoted-ble-midi-phase-f` @ `ad08ce1`** (pushed to origin). This is the canonical v1 line: BLE-MIDI + N2 freeze-fix + ACF spread + per-band AGC + N5 provenance + hardened guard + all memos.
- **Main K1**: chip `F887A500` / MAC `b4:3a:45:a5:87:f8`, on `/dev/cu.usbmodem2101`. **Runs the per-band-AGC production build** (`2e2800d`-era; ACF + AGC, device-proven, stable). It does **NOT** yet carry the N5 provenance/guard commits (`ad08ce1`) — those are build-time/tooling+docs; a reflash to `ad08ce1` is optional and only *adds* the serial `build` provenance command (no behaviour change). `main` is behind and Captain-gated.

## 2. Shipped this session (all host-gated; product line, pushed)
| # | Commit | What |
|---|---|---|
| N2 | `e2beac5` | I2S bounded read + task WDT — freeze fix (cherry-pick of `827d73a` onto the BLE line) |
| N2-root | `6880095` | **ACF work-spreading** promoted to production (`SB_TEMPO_ACF_SPREAD_V1`) — device A/B: active-AP p95 **9088→6784 µs**, over-budget frames **889/2667→0**, tempo lock **127.00 / 100%** |
| N6 | `2e2800d` | **Per-band AGC** promoted (`SB_AGC_PERBAND_V1`) — "louder→dimmer" fix; device A/B: cross-band gain spread **0.000→0.145** (treble ~2.6× brighter than bass on loud) |
| guard | `980c8a3` | Upload-guard: registered all 6 K1-chip-bound envs + **drift-catcher test** (found+closed 4 pre-existing cross-flash brick gaps) |
| N8/N9 | `bc96530` | Blocked/HELD memos + lane-doc §10 reality update + **D7** surfaced |
| N7 | `ce1b585` | OTA **D3 memo** + bench device-proof plan |
| N5 | `ad08ce1` | Release-eng: build-provenance injection (git hash/epoch/env), serial `build` cmd, read-only `make_release.py` (prints tag cmd, never pushes) |

**N7 OTA DRAFT** — branch **`feat/n7-ota-receiver` @ `d4a7824`** (pushed, **NOT merged**): flag-OFF (`SB_ENABLE_OTA=0`) on-device receiver (`esp_ota_*`) + anti-brick rollback. Flag-OFF build is **byte-identical to the shipped product line** (zero regression); flag-ON adds 1,872 B; 19 host tests pass. Class C — Captain-gated at D3.

## 3. The structural finding (load-bearing): two divergent lines → D7
The seven `feat/*` branches are ONE un-merged integration stack (tip `feat/gate-class-pio-prescripts`) carrying **N3 token-scrub + N2b bootloop-guard + N4a device-identity + build-config + commit-gate**. It **diverged from the product line at N2** (stack's `827d73a` vs the product line's cherry-picked `e2beac5`). A naive merge conflicts on `platformio.ini`, the upload guard (both lines edited it), and possibly the golden manifest (trust-root). **This is why N3/N2b are not yet on the product line** — it needs a deliberate reconciliation (D7), not a free merge.

## 4. Decision register — needs Captain (accept/reject; defaults in the lane doc/memos)
- **D7 (new):** reconcile the two divergent lines. *Recommend:* cherry-pick the discrete N3/N2b artifacts onto the product line (lower blast radius than a divergent-line merge); product line stays canonical. Unblocks N3 + N2b.
- **D3:** enable OTA in v1? + **signing-key custody** (Class D secret — never auto-committed) + distribution server. DRAFT built; *recommend* enable **with** signing. See `docs/architecture/n7-ota-d3-memo.md`.
- **D2:** shipping visual — effect-framework-v3 vs current look (the concrete AGC defect is already fixed).
- **D5:** promote GDFT int64? *Recommend stays HELD* — `docs/architecture/n9-gdft-int64-held-memo.md` (obs #72837 showed the overflow was NOT the AGC cause).
- **D6:** K1 reset-button GPIO assignment — unblocks N8 (`docs/architecture/n8-field-recovery-blocked-memo.md`).
- **D4:** per-unit serial/SKU scheme (release script prints `v4.1.3` placeholder; override at tag).
- **D1:** Tab5 wireless ship in v1? (default OFF, token-scrubbed — couples to N3/D7).

## 5. Autonomous remainder (resumable, no decision needed)
- **N4-remainder** (Class A, fresh): factory-image (`esptool merge_bin`) + per-unit NVS provisioning (`nvs_partition_gen`) + flashing runbook. ~1 SSA.
- **N2b**: staged on its branch; **device-proof reflash owed** (per `0b273da`). Lands with the D7 cherry-pick.
- **Optional**: reflash the main K1 to `ad08ce1` to get the serial `build` provenance command on-device.
- **Registry-hygiene nit**: the latest flash (`2e2800d`) is in the device-build-registry *changelog* but not its top deployed-state *table* row — `make_release.py` reads the table row; tidy when convenient.

## 6. Operating doctrine — NON-NEGOTIABLE (carry forward)
1. **NEVER blind-flash the only K1. Host-green ≠ device-proof.** Bench-first; behaviour-changing work on its own branch, flag default-OFF, device/perceptual checkpoint before any default flip.
2. **The gate is the harness, run on the post-merge HEAD:** `python3 -m pytest tests/test_golden_master.py tests/test_harness_selftest.py -q` (golden + Gate-0) then the full suite; the change must touch **zero** files under `tests/golden/`, `tests/test_harness_selftest.py`, `.github/`. A new env rooting at `k1_hardware` MUST be registered in `k1_upload_guard.py` (the drift-catcher enforces it).
3. **Device identity = chip-ID `F887A500`, not the port** (ports re-enumerate). Flash via `pio run -e <env> -t upload --upload-port <port>` wrapped in `script -q <log>`; confirm `Hash of data verified` + `Hard resetting`. Bench unit = `B489A500`; K718 BLE dial (`ac:a7:04:ee:57:7c`) shares the USB bus — never cross-flash (the guard now blocks it).
4. **Class C/D lanes STOP at the Captain decision** (D-register). Never enable OTA, commit a signing key, bake a SKU, or assign hardware pins autonomously.
5. **SSA lesson (this session):** one build-SSA died on an API `ConnectionRefused` mid-gate. Mitigation that worked: instruct build-SSAs to **commit to their branch BEFORE running the long gates** (work survives a drop); the orchestrator then preserves → gates → integrates. Isolated worktrees held (no leak to the product line). Recovering a dead SSA's worktree is cheap; re-spawning into an unstable API is not.
6. **Verify numbers before asserting** (a unit confusion — KiB vs bytes — nearly produced a false "15K leak" finding this session; the flag-OFF build was byte-identical). Map-territory: check the territory, don't trust the remembered map.

## 7. Branch / worktree map
- Canonical: `lane/remoted-ble-midi-phase-f @ ad08ce1` (pushed).
- DRAFT: `feat/n7-ota-receiver @ d4a7824` (pushed, do not merge — D3).
- Released-tooling staged: `feat/n5-release-eng @ ad08ce1` (merged to product; branch can be deleted).
- Divergent stack (D7): tip `feat/gate-class-pio-prescripts` (+ `feat/n3-token-scrub`, `feat/n2b-bootloop-guard`, `feat/n4a-*`, `feat/build-config-drift-gate`).
- `/private/tmp/*` worktrees are EPHEMERAL; branches persist. `/Users/spectrasynq/SpectraSynq_K1_Firmware_n7` and `_n5` worktrees can be `git worktree remove`'d (branches are pushed).

## 8. Evidence
- Lane status (live): `docs/architecture/production-readiness-lane.md` §10.
- Memos: `docs/architecture/n7-ota-d3-memo.md`, `n8-field-recovery-blocked-memo.md`, `n9-gdft-int64-held-memo.md`.
- Freeze incident: `docs/handover/2026-06-30-n2-freeze-remediation-and-session-handover.md`; `docs/forensics/2026-06-15-16k120-acf-work-spreading-plan.md` (ACF A/B + ship).
- Device-build registry: `docs/hardware/device-build-registry.md` (ACF + AGC ship rows).

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-06-30 | agent:claude-opus-4-8 (CTO) | Created. Production-readiness lanes session handover: N2+ACF+N6-AGC+N5+guard shipped (product line `ad08ce1`); N7 OTA flag-OFF DRAFT (`d4a7824`) + D3 memo; N8/N9 memos; D7 divergent-line finding; decision register D1–D7; autonomous remainder (N4 tooling); operating doctrine incl. the SSA-die-recovery + verify-before-assert lessons. |
