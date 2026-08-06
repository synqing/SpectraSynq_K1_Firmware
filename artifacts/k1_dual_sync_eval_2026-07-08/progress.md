---
abstract: "Session log for the dual-K1 sync lane (2026-07-08). Chronological record of actions, workflow runs, and gate results."
---

# Progress — Dual-K1 Sync Lane

## Session 2026-07-08
- Lane opened by Captain: dual-K1 sync → 320-LED widened display, BLE MIDI piggyback hypothesis.
- Skills loaded: find-skills, ssa-management, planning-with-files, thinking-model-router.
- Ultracode Understand-phase workflow launched (9 parallel read-only SSAs); all 9 returned (1.39M tokens, 293 tool calls). Evidence in findings/.
- Captain answers: transport = evaluate all; audio truth + pairing UX = evaluation decides; scope = plan + visual mockup, no firmware edits.
- Orchestrator re-ran decision-critical claims (BLE central-only, canvas/mirror geometry, radio-free prod filter, UF2, LED counts) — all confirmed.
- sensorybridge-doctrine gate invoked; DRAFT v0.1 evaluation+plan written.
- Red-team workflow (4 adversarial lenses) returned: perceptual FLAWED (KILL: mechanism conflation — "2x detail + zero work" false; effects render upper-half only), timing 2 KILLs (identical-inputs violation → replay contract; Phase-0 gate mis-specified → 4-number gate), engineering+doctrine SOUND_WITH_FIXES. Decisive attacks re-verified by orchestrator (ember half-canvas write, calibration.* in facade allowlist, CONFIG_BT_CTRL_PINNED_TO_CORE=0, only-two-K1s registry).
- v1.0 plan written: M1 twin sync (full roster, ships first) → M2 widened (contingent on day-zero physical seam trial + measured budget); forks F1–F5 for Captain.
- Seam-geometry mockup built, headless-rendered, inspected, corrected (SEAM label, honest captions, M1/M2 badges), re-rendered, published as a hosted artefact page.

## Phase 0 execution (2026-07-08, Captain green-light end-to-end)
- Branch `lane/dual-sync-phase0` opened from 628f69b. Devices offline at start (physical checklist owed: plug both K1s, jumper wires, K718 power, music).
- P0.2 DONE: commits 4826841 (fix: `:ble_stream` help/handler shipped `[ble_remoted]` strings in production rodata — compile-gated; radio isolation back to PROVEN) + 5bbbf76 (probe envs `k1_sync_probe_main`/`k1_sync_probe_bench`, `network/k1_sync_link.*` stub, guard tokens incl. `esp_now_init` tripwire, upload-guard + registry registration, test alignment). Gate: pytest 653 green, 4 envs build, isolation PROVEN.
- P0.3 DONE (2deb957): timing oracle — probe-log-contract.md (pins TRIG_OUT=15/TRIG_IN=16 both maps + serial grammar), scripts/dual_sync_probe/ (logfmt, correlate, gate_eval, synth), Gate-0 fault battery 16 tests green (orchestrator re-run).
- P0.4 DONE: K1-SyncLink probe firmware — dual-role NimBLE (leader keeps K718 central), CI 7.5 ms/MTU 247/2M PHY requested+logged, 33.3 Hz stream, RTT min-filter clock sync, causal ping-echo cross-trigger (IRAM ISR, SPSC ring), 1 Hz health, :sync_fault Gate-0 injection. Orchestrator gate re-run: both probe envs + prod SUCCESS, isolation PROVEN, pytest 678 green. Compile ≠ runtime — P0.5 owns silicon proof.
- REMAINING = physical: both K1s on USB, GPIO15↔16 crossed jumpers + GND, K718 powered, music; then P0.5 (on-silicon Gate-0 → idle/music/dial/soak scenarios → four gate numbers) and P0.0 seam photos (M2 only).

## Session 2026-07-27 — P0.5 Gate-0 silicon attempt (SSA dual-sync-p05-gate0-complete)
- Branch tip confirmed `lane/dual-sync-phase0` @ `3a9724e`.
- Live identity: Main `F887A500` / `k1_sync_probe_main` on `/dev/cu.usbmodem112401`; Bench `B489A500` / `k1_sync_probe_bench` on `/dev/cu.usbmodem11401`. **No reflash** (already on probe).
- Attempted Gate-0 + idle envelope with dual serial capture + `scripts/dual_sync_probe/gate_eval.py`.
- **BLOCKED:** BLE SyncLink never linked (`link up`=0; zero `trig_*` / `tx` / `rx` / `apply` / `clk` over multi-minute captures). Health ~200 fps present on both — **not** treated as sync lock.
- Oracle fail-closed: gate1/2/3 n=0; gate4 FAIL (dial_uptime=0). Evidence: `_scratch/dual_sync_p05_gate0_20260727/` (`summary.md`, `gate0_results.json`, serial captures, `run_gate0.sh`).
- Music / K718 dial / soak / M2 seam: skipped (blocked on link).
- Registry: already records probe deploy @ 3a9724e (2026-07-27); left dirty, no commit.
- NEXT: firmware/debug dual-role advertise vs `ble_remoted` continuous scan on leader; then re-run `bash _scratch/dual_sync_p05_gate0_20260727/run_gate0.sh`.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-07-27 | agent:cursor-embedded | P0.5 Gate-0 silicon attempt BLOCKED — SyncLink never linked; evidence under `_scratch/dual_sync_p05_gate0_20260727/`. |
| 2026-07-08 | agent:claude-code | Created — session log opened. |
