---
abstract: "Canonical spec routing index for SensoryBridge K1 — active lanes, handover authority, device map, claude-mem recall conventions, and evidence bundles. Version-proof (survives claude-mem upgrades). Update when lane status or authority docs change."
active_lane: K1_SCHEDULING_HARDENING_20260815
active_authority: docs/handover/HANDOVER_2026-08-15_SCHEDULING_HARDENING_IMPLEMENTATION.md
active_branch: feat/k1-scheduling-generation-hardening
merged_lane: fix/tab5-phase1-softkey-wiring (merged to main 2026-08-11, Captain-authorised)
lane_branch: feat/k1-scheduling-generation-hardening
last_verified: 2026-08-17
---

<!-- british-english-guard: ignore — `artifacts/` is the literal on-disk directory name in this
     repo, so every path and link must spell it that way or the link breaks. Prose in this file
     uses "artefacts". -->

# SensoryBridge K1 — Spec Index

**Ship path required (Captain 2026-08-17):** never withhold ship / promote / close
without the remaining numbered path in the same answer. `/ship-path-required`.

## ⛔ DUAL-K1 SYNC IS DEAD — Captain decision, 2026-08-05

**The dual-sync lane is DEPRECATED and SHELVED. Do not resume it, do not plan
around it, and do not propose work that depends on it.** This supersedes every
"CURRENT" claim about dual-sync anywhere in this file or in
`artifacts/k1_dual_sync_eval_2026-07-08/`.

- Status: closed by Captain instruction, not by a technical failure or a gate.
- The artefacts and the `k1_sync_probe_*` envs are retained as **historical
  evidence only** — see
  [`artifacts/k1_dual_sync_eval_2026-07-08/DEPRECATED.md`](../artifacts/k1_dual_sync_eval_2026-07-08/DEPRECATED.md).
- The branch name `lane/dual-sync-phase0` is now only a container for unrelated
  in-flight work (IM69D130 mic eval, WB-3 STM, edgemixer). The branch name no
  longer describes what the lane is about.

**Current authority (2026-08-16 evening):** **K1 scheduling hardening — service p99
8000 µs restamp** —
[`docs/handover/HANDOVER_2026-08-15_SCHEDULING_HARDENING_IMPLEMENTATION.md`](handover/HANDOVER_2026-08-15_SCHEDULING_HARDENING_IMPLEMENTATION.md)
· Gate 0–8 plan [`docs/forensics/2026-08-15-freertos-scheduling-audit/EXECUTION_PLAN.md`](forensics/2026-08-15-freertos-scheduling-audit/EXECUTION_PLAN.md)
· **Live tasks** [`docs/superpowers/plans/2026-08-16-scheduling-hardening-g2-g8.md`](superpowers/plans/2026-08-16-scheduling-hardening-g2-g8.md)
· G0R plan [`docs/superpowers/plans/2026-08-16-g0r-cadence-authority.md`](superpowers/plans/2026-08-16-g0r-cadence-authority.md) (**SUPERSEDED for live execution**; stamp A closed 10 ms).
Gate 0 **oracle** is CLOSED. Hop remains 12800/96/d3/7.5 ms. AP service p99 = **8000 µs**
(6000 / 0.8 fraction STRUCK). Gate 2 close-out = Cross40+Lane4. Gate 3 UNBLOCKED after
G2 close-out. B489 flash only under named GO; F887 NO until G8. AP0/VP1 locked.
Separate AP-input-integrity P4 remains open.

**Last verified:** 2026-07-08 (git `lane/im73d-pdm-eval`; active lane = IM73D122 productionization - **Phase-1 firmware DONE**, R1 knob-persistence proof CLOSED, raw AP telemetry landed, controlled-audio DSR evidence captured, bench recovery proved, and sensitivity/telemetry schema hardening in progress). Vibrancy + IM73D mic-eval lanes are consolidated; `k1_prod_im73d` main/prod build path shipped (byte-identical-OFF, guard-mapped to main K1). Main `F887A500` is `k1_hardware @ 67227da` and remains the SPH reference/control. Bench `B489A500` proves the IM73D PDM mic path on the ratified `clk13/din12/LR14` pins. Captain has confirmed both K1s are identical hardware; env choice is configuration: `k1_bench_im73d` uses the bench-reference LED map `4/5`, while `k1_prod_im73d` uses the main/prod LED map `6/7`. A 2026-07-07 bench flash made both LED channels dark because the `6/7` env was used on the unit restored/proven as the `4/5` env; that is wrong-env evidence, not a physical hardware split. Bench was restored to radio-free `k1_bench_im73d @ f2f7c45`; read-only proof confirms `env=k1_bench_im73d`, chip `B489A500`, `CAL_SOURCE: persisted_profile`, `CAL_VALID: 1`, `CONFIG.CHROMA: 0.100000`, `CONFIG.SENSITIVITY: 0.870005`, and `AUDIO_RESPONSE_GAIN: 1.000000` on `/dev/cu.usbmodem1401`. **N2c watchdog correction:** a 2026-07-08 live `IDLE0` task-WDT on `B489A500` proved the bounded-read/loop-watchdog guard still needs a real idle-task slot; the audio loop tail now uses `vTaskDelay(1)` instead of `yield()`, and a 28 s recovery readback crossed the prior failure point with no WDT/backtrace/reboot markers. Raw pre-conditioning AP telemetry now exists as `raw_i16_abs_peak`, `raw_i16_rms`, and `raw_i16_near_pct`. Controlled-audio DSR16 vs DSR8 showed no raw rail risk, but quiet raw RMS rose and music raw-RMS-over-quiet response fell at every tested volume, so **DSR_16S is rejected** and `DSR_8S` remains the default. `global.sensitivity` now uses the same `0.10..20.0` scale as serial/hotkeys, and `:stream_agc` now separates legacy `floor` from active AGC `active_floor`. **Resume authority:** [`docs/hardware/im73d-dsr16-controlled-audio-evidence-2026-07-06.md`](hardware/im73d-dsr16-controlled-audio-evidence-2026-07-06.md) + [`docs/hardware/im73d-dsr16-quiet-only-evidence-2026-07-06.md`](hardware/im73d-dsr16-quiet-only-evidence-2026-07-06.md) + [`docs/hardware/im73d-r2-main-k1-swap-decision-handoff-2026-07-06.md`](hardware/im73d-r2-main-k1-swap-decision-handoff-2026-07-06.md) + [`docs/hardware/im73d-audio-pipeline-purity-audit-2026-07-06.md`](hardware/im73d-audio-pipeline-purity-audit-2026-07-06.md) + [`docs/hardware/im73d-codex-resume-handover-2026-07-06.md`](hardware/im73d-codex-resume-handover-2026-07-06.md) -> [`docs/hardware/im73d122-productionization-handover-2026-07-03.md`](hardware/im73d122-productionization-handover-2026-07-03.md) §§10-11. The `k1_bench_im73d_ble` IM73D+BLE-MIDI demo build remains a parallel deliverable; do not measure mic SNR on the radio build. The earlier 2026-06-10 / 2026-06-15 status below is preserved for context but is NOT the current active lane; verify any claim against current git before acting.

> 2026-06-15 live supersession: newer K1 production and effects-lane status lives
> in [progress.md](../progress.md) and
> [docs/forensics/2026-06-15-post-16k-gate-calibration-and-vp-evidence.md](forensics/2026-06-15-post-16k-gate-calibration-and-vp-evidence.md).
> Production is accepted at `12800/96/d3`; the 2026-06-11 effects repair
> blockers are closed in current source; modes 24-27 have partial VP smoke
> evidence only; modes 28-29 are still unproven by that smoke.

> 2026-07-02 IM73D lane: the current active lane is the IM73D122 PDM mic graft
> (flag `K1_MIC_IM73D_PDM_V1`, bench `B489A500` only). Authority docs:
> [docs/hardware/im73d122-ap-vp-migration-plan.md](hardware/im73d122-ap-vp-migration-plan.md),
> [docs/hardware/im73d122-graft-handover-2026-07-02.md](hardware/im73d122-graft-handover-2026-07-02.md),
> [docs/hardware/device-build-registry.md](hardware/device-build-registry.md).

## Agent read order (load-bearing)

1. [progress.md](../progress.md) — rolling status (last 7 days)
2. [.claude/handoff.md](../.claude/handoff.md) — active session pointer
3. **This file** → Active Lanes table below
4. Lane-specific handover (linked from table)
5. claude-mem search (prior sessions) — see [Recall conventions](#recall-conventions-claude-mem)

On-disk handover **beats** claude-mem for **current lane status**. Memory is for prior-session context and recurrence patterns.

---

## Session canon (immune memory)

**Load before silence-gate / IM69D soak / Tab5 BLE / boot-default work:**
[`docs/canon/SESSION_CANON_2026-08-07_im69d_peakiness_deck16_boot.md`](canon/SESSION_CANON_2026-08-07_im69d_peakiness_deck16_boot.md)
· skill [`k1-vj-session-discipline`](../.claude/skills/k1-vj-session-discipline/SKILL.md).

Encodes HARD FAILs from the peakiness×joint-break×crash-loop×Deck16-HCI×boot-show
session so agents do not replay crest-only OP hunting, RMS learner admit, K718
framing, prediction-free soaks, or safe-mode null-LED intro crashes.

**Load BEFORE Deck16 BLE backend / identity digests / deck_state haunt / 68↔71 map drift /
C6 soak / dark-fade / MAIN glass authority / Mirror·STANDBY claims:**
[`docs/canon/SESSION_CANON_2026-08-09_deck16_ble_backend_haunt_latency.md`](canon/SESSION_CANON_2026-08-09_deck16_ble_backend_haunt_latency.md)
· [Tab5 failures + 68-control recovery canon](canon/TAB5_SESSION_FAILURES_AND_ENGINEERING_CANON_2026-08-11.md)
· skill [`k1-deck16-session-discipline`](../.claude/skills/k1-deck16-session-discipline/SKILL.md)
· gate `bash scripts/agent/deck16-first-contact-gate.sh`
· parity gate `python3 scripts/agent/tab5_protocol_parity_gate.py --repo-root .`
· handover [`_scratch/deck16_session_handover_20260809/HANDOVER.md`](../_scratch/deck16_session_handover_20260809/HANDOVER.md).
Encodes HF-14…HF-31 (stale digests, 68/71 drift, host-RTT lies, false MAIN approval, Core-0
pin, haunt clear, exclusive soak, absent-peer STOP). Captain released the merge
gate on 2026-08-11 (lane merged to `main`); the authority claim block stays
`PRODUCTION_READY=NO` and promotion to production remains held pending device
proof — merged is not proven.

**Load BEFORE any SpectraSynq UI design→code (LVGL / fonts / product HTML sizes):**
[`docs/canon/SESSION_CANON_2026-08-09_ui_precode_optical_gate.md`](canon/SESSION_CANON_2026-08-09_ui_precode_optical_gate.md)
· process [`SPECTRASYNQ-UI-PRECODE-OPTICAL-GATE.md`](process/SPECTRASYNQ-UI-PRECODE-OPTICAL-GATE.md)
· skill [`spectrasynq-ui-precode-optical-gate`](../.claude/skills/spectrasynq-ui-precode-optical-gate/SKILL.md)
· red-team [`UI_PRECODE_GATE_REDTEAM.md`](../_scratch/precision_bay_r1/UI_PRECODE_GATE_REDTEAM.md).
UI look edits without `OPTICAL_GATE_RECEIPT.md` + SHA-pinned `MEASURED.json` = **BLOCKED**
(AGENT_OS §7a). `G0_PASS ≠ OPTICAL_PASS`.

| Inbound | Authority | When |
|---------|-----------|------|
| **Tab5 Deck16 HCI / BLE / operator UI** | [`docs/architecture/TAB5_DECK16_SESSION_CANON_2026-08-07.md`](architecture/TAB5_DECK16_SESSION_CANON_2026-08-07.md) · **[backend/haunt/latency canon 2026-08-09](canon/SESSION_CANON_2026-08-09_deck16_ble_backend_haunt_latency.md)** · **[failures + 68-control recovery canon](canon/TAB5_SESSION_FAILURES_AND_ENGINEERING_CANON_2026-08-11.md)** · skill [`k1-deck16-session-discipline`](../.claude/skills/k1-deck16-session-discipline/SKILL.md) · skill [`tab5-hosted-ble-debug`](../.claude/skills/tab5-hosted-ble-debug/SKILL.md) · guardrails [`.cursor/rules/tab5-deck16-guardrails.mdc`](../.cursor/rules/tab5-deck16-guardrails.mdc) | Before Tab5 P4 flash, identity-hash claims, deck_state pending TX, full-map/C6 soak, 68/71 compatibility, dark-fade, MAIN authority, `BLE_HS_ETIMEOUT_HCI` triage, ESP_HCI_IF wire work, `deck_ui_assets.py` / BLE-MIDI TX edits. Proof: `_scratch/deck16_tab5_k1_proof_20260807/` + `_scratch/deck16_session_handover_20260809/`. |
| **UI optical / typography / layout look** | [session canon 2026-08-09](canon/SESSION_CANON_2026-08-09_ui_precode_optical_gate.md) · skill [`spectrasynq-ui-precode-optical-gate`](../.claude/skills/spectrasynq-ui-precode-optical-gate/SKILL.md) · rule [`.cursor/rules/spectrasynq-ui-precode-optical-gate.mdc`](../.cursor/rules/spectrasynq-ui-precode-optical-gate.mdc) | Before any `deck_ui*` / font / type-token / geometry / product-HTML-size edit. |

## Tab5 GATE 0 — reproducible source baseline (BLOCKING)

**Captain-frozen 2026-08-11.** Tab5 hardening Gates 1–4 are **blocked** until
[`docs/process/TAB5-GATE-0-REPRODUCIBLE-SOURCE-BASELINE.md`](process/TAB5-GATE-0-REPRODUCIBLE-SOURCE-BASELINE.md)
closes. 0.1 (calibration tombstone) and 0.2 (vendor inventory) are DONE; 0.4
project-cold PASS; **0.3 / 0.5 / 0.6 OPEN**. The authoritative gate is 0.5
environment-cold (clean clone + empty `PLATFORMIO_CORE_DIR`) — a warm build is
evidence, not proof. End-state is non-negotiable: Tab5 is a pinned,
clean-clone-buildable, CI-compiled target; "source-only CI" is not a destination.

## Active lanes (updated 2026-08-16)

| Lane | Authority doc | Status | Evidence anchor |
|------|---------------|--------|-----------------|
| **K1 scheduling hardening** | [active handover](handover/HANDOVER_2026-08-15_SCHEDULING_HARDENING_IMPLEMENTATION.md) · [Gate 0-8 plan](forensics/2026-08-15-freertos-scheduling-audit/EXECUTION_PLAN.md) | **CURRENT. G2+G3 CLOSED 2026-08-17. Bench `B489A500` / `k1_bench_im69d` @ `c671ddf3`. Next = G7B on bench. Main K1 `F887A500` OFFSITE (consultancy) — G8 deferred until a replacement unit exists.** AP0/VP1 locked. | `docs/forensics/2026-08-15-freertos-scheduling-audit/` |
| **K1 AP input integrity** | [handover](handover/HANDOVER_2026-08-14b_AP_INPUT_INTEGRITY.md) · [Rev B plan](plans/AP_INPUT_INTEGRITY_PLAN_2026-08-14.md) · [G1 receipt](forensics/G1_AP_INPUT_SLOT_RATIFICATION_2026-08-15.md) | **PARALLEL AUTHORITY. G1 RATIFIED; T0.3 COMPLETE.** No further physical mic test; AP P4 slot/health promotion remains open and separate. | `_scratch/p0_stereo_20260814/`; `scripts/tools/probe_diff.py`; `scripts/regression-harness/mic_stable_byte_gate.sh` |
| **IM69D130 dual-mic / AP advice (Phases 0–2)** | [docs/hardware/im69d130-vs-main-k1-eval-2026-08-05.md](hardware/im69d130-vs-main-k1-eval-2026-08-05.md) · [design](hardware/im69d130-dual-mic-eval-design-2026-08-05.md) · **[session canon 2026-08-07](canon/SESSION_CANON_2026-08-07_im69d_peakiness_deck16_boot.md)** | **SUPERSEDED as current authority.** B489 mono-default device evidence is dispositioned by the P0.0 quarantine manifest; source-reasoned work retains only its stated scope. | `docs/forensics/P0_0_AP_INPUT_QUARANTINE_MANIFEST_2026-08-15.md`; historical env and receipts retained for provenance |
| **Deck16 Tab5 BLE R1** | [docs/architecture/K1_DECK16_ARCHITECTURE_R1.md](architecture/K1_DECK16_ARCHITECTURE_R1.md) · [radio](architecture/RADIO_FALLBACK_DECISION.md) · **[Tab5 session canon 2026-08-07](architecture/TAB5_DECK16_SESSION_CANON_2026-08-07.md)** · **[backend/haunt/latency canon 2026-08-09](canon/SESSION_CANON_2026-08-09_deck16_ble_backend_haunt_latency.md)** · **[68-control recovery canon](canon/TAB5_SESSION_FAILURES_AND_ENGINEERING_CANON_2026-08-11.md)** · skill [`k1-deck16-session-discipline`](../.claude/skills/k1-deck16-session-discipline/SKILL.md) | **ACTIVE architecture + ACTIVE immune memory.** Current protocol is **68 controls / `9b5db3...`**; 71/`78fb9a...` is historical only. Source recovery merged; identity + snapshot proof passed on Unit2/Tab5. Bidirectional delta, long soak, assigned CID, and UNIT-default production claim remain open. **K718 Remoted dial retired.** PRODUCTION_READY=NO. | `docs/protocol/k1-ble-midi-map.json`; `tab5_firmware/`; `scripts/agent/deck16-first-contact-gate.sh`; `scripts/agent/tab5_protocol_parity_gate.py` |
| **M2.1 serial_menu decomposition + save-show** | [docs/refactor/serial-menu-decomposition-plan-2026-07-26.md](refactor/serial-menu-decomposition-plan-2026-07-26.md) | **COMPLETE 2026-07-26** on main. R1+R2 typed dispatch; Shift+S / `:save_show` host-green. | `serial/serial_typed_cmd_table.def`, `control/k1_show_state.*` |
| ~~**Dual-sync F0-F3 recovery**~~ | [DEPRECATED notice](../artifacts/k1_dual_sync_eval_2026-07-08/DEPRECATED.md) | **⛔ DEAD — SHELVED by Captain 2026-08-05.** Artefacts retained as historical evidence only. | `artifacts/k1_dual_sync_eval_2026-07-08/DEPRECATED.md` |
| **IM73D + BLE-MIDI demo build (`k1_bench_im73d_ble`)** | [docs/hardware/im73d-ble-midi-demo-build-2026-07-04.md](hardware/im73d-ble-midi-demo-build-2026-07-04.md) | **Parallel deliverable, not current bench proof target.** The bench was historically reflashed to radio-free `k1_bench_im73d @ 6f2f1ec` for R1 knob-persistence proof; after the controlled-audio DSR lane and the 2026-07-07 LED-pinmap incident, the bench is radio-free `k1_bench_im73d @ f2f7c45` and runtime-proven. Reflash `k1_bench_im73d_ble` only when BLE demo work resumes. SEPARATE from mic eval - no SNR on the radio build. | `docs/hardware/device-build-registry.md`; `platformio.ini` `[env:k1_bench_im73d_ble]` + `k1_upload_guard.py` |
| **IM73D122 productionization** | [docs/hardware/im73d-restored-bench-validation-2026-07-07.md](hardware/im73d-restored-bench-validation-2026-07-07.md) · [docs/hardware/im73d-dsr16-controlled-audio-evidence-2026-07-06.md](hardware/im73d-dsr16-controlled-audio-evidence-2026-07-06.md) · [docs/hardware/im73d-dsr16-quiet-only-evidence-2026-07-06.md](hardware/im73d-dsr16-quiet-only-evidence-2026-07-06.md) · [docs/hardware/im73d-r2-main-k1-swap-decision-handoff-2026-07-06.md](hardware/im73d-r2-main-k1-swap-decision-handoff-2026-07-06.md) · [docs/hardware/im73d-audio-pipeline-purity-audit-2026-07-06.md](hardware/im73d-audio-pipeline-purity-audit-2026-07-06.md) · [docs/hardware/im73d122-productionization-handover-2026-07-03.md](hardware/im73d122-productionization-handover-2026-07-03.md) | **Mic Captain-ratified as the K1 production mic 2026-07-03.** Phase-1 firmware shipped; R1 radio-free bench device proof CLOSED; raw AP telemetry landed; controlled-audio DSR16 check captured. **DSR status:** DSR16 is rejected; keep `DSR_8S`. **Restored bench status:** radio-free `k1_bench_im73d @ f2f7c45` is green for the IM73D mic/PDM path at usable playback levels; volume 45/60 AP/raw captures are usable and AGC gains stay below 2.0. Volume 75 is a front-end stress/fail condition. **Current blocker:** choose the intended existing env per configured unit (`k1_bench_im73d` for 4/5, `k1_prod_im73d` for 6/7), device-prove, then Captain eyes-on before default flip. | `docs/hardware/device-build-registry.md`; `lane/im73d-pdm-eval`; `artifacts/im73d_bench_ledproof_2026-07-07/20260707T170922_restored_bench_full_music/summary.json`; `artifacts/im73d_bench_ledproof_2026-07-07/20260707T171632_stream_agc_vol60/summary.json`; `artifacts/im73d_dsr_audio_eval_2026-07-06/dsr8_vs_dsr16_controlled_audio_compare.json`; `artifacts/im73d_recovery_2026-07-07/readonly_build_dump_20260707.json`; `_scratch/im73d_r1_knob_persistence_20260706/` |
| **IM73D122 PDM mic graft (superseded by productionization)** | [docs/hardware/im73d122-ap-vp-migration-plan.md](hardware/im73d122-ap-vp-migration-plan.md) · [docs/hardware/im73d122-graft-handover-2026-07-02.md](hardware/im73d122-graft-handover-2026-07-02.md) | **DONE, committed, host-gated GREEN, device-proven end-to-end on bench `B489A500`** (flag `K1_MIC_IM73D_PDM_V1`, bench-only). SPH0645 stays byte-identical product default. Continued in the productionization lane above. | `docs/hardware/device-build-registry.md` (bench row, `c3584fa`); commits `545d331` + `c3584fa` + `49b0393` on `lane/im73d-pdm-eval` |
| VMEWT transport incident | [docs/forensics/vme_l1/2026-06-07-vmewt-transport-incident.md](forensics/vme_l1/2026-06-07-vmewt-transport-incident.md) | Hardware VMEWT capture frozen; failed sandbox survivor rows are not runtime proof | Reported failed VMEWT summaries: nonzero rejected records, ignored fragments, parser issues, secondary-only coverage, weak-confidence-only scenarios |
| VME L1 Waveform sandbox | [docs/handover/2026-06-07-vme-l1-waveform-sandbox-handover.md](handover/2026-06-07-vme-l1-waveform-sandbox-handover.md) | Sandbox/shadow only; target Waveform Fast, Waveform, and Waveform Tempo; next valid step is fail-closed transport proof before hardware | [docs/forensics/vme_l1/2026-06-07-vmewt-transport-incident.md](forensics/vme_l1/2026-06-07-vmewt-transport-incident.md), [docs/forensics/2026-05-26-level1-visual-memory-engine-sandbox-plan.md](forensics/2026-05-26-level1-visual-memory-engine-sandbox-plan.md), [docs/architecture/visual-event-bus-stage-2-proposal-v0.1.md](architecture/visual-event-bus-stage-2-proposal-v0.1.md) |
| Dense Forge closeout | [docs/handover/2026-06-07-dense-forge-closeout.md](handover/2026-06-07-dense-forge-closeout.md) | Source committed + exact `a5ce32e` flashed to 1401 and locked to mode 21; Captain eyes-on PASS was on repair build before exact-source reflash | [docs/forensics/runtime-evidence/2026-06-07-dense-forge-a5ce32e-build.log](forensics/runtime-evidence/2026-06-07-dense-forge-a5ce32e-build.log), [docs/forensics/runtime-evidence/2026-06-07-dense-forge-a5ce32e-upload.log](forensics/runtime-evidence/2026-06-07-dense-forge-a5ce32e-upload.log), [docs/forensics/runtime-evidence/2026-06-07-dense-forge-a5ce32e-post-upload.log](forensics/runtime-evidence/2026-06-07-dense-forge-a5ce32e-post-upload.log), [docs/forensics/runtime-evidence/2026-06-07-dense-forge-a5ce32e-mode21-setup.log](forensics/runtime-evidence/2026-06-07-dense-forge-a5ce32e-mode21-setup.log) |
| Secondary dark-state | [docs/handover/2026-06-07-secondary-dark-state-handover.md](handover/2026-06-07-secondary-dark-state-handover.md) | Fix flashed to 1401; Captain eyes-on re-test **pending** | [docs/forensics/runtime-evidence/2026-06-07-secondary-dark-state-last-writer-verdict.md](forensics/runtime-evidence/2026-06-07-secondary-dark-state-last-writer-verdict.md) |
| Scene Policy v2 | [docs/forensics/scene_policy_v2/2026-06-07-scene-policy-v2-handover.md](forensics/scene_policy_v2/2026-06-07-scene-policy-v2-handover.md) | Serial A/B state gate done; visual product judgement **open** | [docs/forensics/runtime-evidence/2026-06-07-scene-policy-v2-serial-ab-state-gate.md](forensics/runtime-evidence/2026-06-07-scene-policy-v2-serial-ab-state-gate.md) |
| AP0/VP1 closeout | [docs/forensics/tempo_tracking_refactor/2026-06-06-ap0-vp1-p0-closeout-handover.md](forensics/tempo_tracking_refactor/2026-06-06-ap0-vp1-p0-closeout-handover.md) | Historical; do not reopen without new evidence | `docs/forensics/tempo_tracking_refactor/` ledger |
| Tempo primitive | [docs/handover/2026-06-05-cto-session-handover-3.md](handover/2026-06-05-cto-session-handover-3.md) | Octave/confidence SOLVED; modes 18/19/20 host-green; **device eyes-on still open** (tracked non-blocking follow-up, never formally closed) | `docs/research/validation/2026-06-04-RECONCILIATION.md` + handover #3 |
| K1 wireless control (WS v2) | feat(k1) `e6a6fbb` + AP WebSocket `k1.*` protocol (`b748678`, `59b6023`) | WS control facade + protocol v2 + safe noise-cal arm path landed on wip; host static tests pass; device integration + eyes-on **open** | `SPECTRASYNQ_K1_FIRMWARE/control/sb_k1_control_facade.*`, `network/sb_k1_wireless.*`; [docs/forensics/sb-tab5-control/2026-06-08-tab5-k1-ui-wireless-integration-investigation.md](forensics/sb-tab5-control/2026-06-08-tab5-k1-ui-wireless-integration-investigation.md) |
| Tab5 wireless controller | [docs/forensics/sb-tab5-control/2026-06-09-tab5-onwards-roadmap.md](forensics/sb-tab5-control/2026-06-09-tab5-onwards-roadmap.md) | **PORTED IN-REPO 2026-08-06.** Canonical PlatformIO root is now `tab5_firmware/` in this repository. Current direction is BLE MIDI, not STA Wi-Fi/OSC; repo-local `tab5_p4` build and flash to Tab5 `/dev/tty.usbmodem11401` succeeded, with serial proof of inverse landscape, Berkeley Mono, disabled waiting overlay, and BLE-MIDI command output. BLE GATT bearer remains pending on hosted NimBLE availability. | `tab5_firmware/README.md`; `tab5_firmware/src/ble_midi_transport.cpp`; `tab5_firmware/src/net.cpp` |
| VP Motion Lab (VPML) | [docs/forensics/vp_motion_lab/2026-06-09-vp-motion-lab-mvp-decision.md](forensics/vp_motion_lab/2026-06-09-vp-motion-lab-mvp-decision.md) | **Host-authoring/workbench slice CLOSED 2026-06-10 (Captain)**: compiler, param editor, preset A/B recall, host-only recipe-deck authoring, save/load/compile variants, hard command-length gate vs firmware parser cap (66/93, 85/93 ok), workbench **Device-Disabled by default** (no K1 without `--allow-device`); verified py-clean, home/compile `200`, recipe `host_manual` / `device_sequencing=false`. **Boundary:** does NOT close visual acceptance, VPAB proof, production promotion, or live-K1 recipe-run — bench K1 access Captain-blocked. (Earlier: 2 `intro_bounce_loop` frame-gate FAILs + 1 1401 no-response, 2026-06-09.) | [docs/forensics/vp_motion_lab/2026-06-09-vp-motion-lab-onwards-roadmap.md](forensics/vp_motion_lab/2026-06-09-vp-motion-lab-onwards-roadmap.md); `docs/forensics/runtime-evidence/20260610T*-12201-snappy-*`, `evidence/vpml-recipes/` |

**Parallel lanes:** Secondary dark-state and Scene Policy v2 are independent. Do not conflate Dense Forge (mode 21 primary) with secondary darkness (mode 18).

---

## Supersession map

| Doc | Use for | Do **not** use for |
|-----|---------|-------------------|
| `2026-06-07-vmewt-transport-incident.md` | VME hardware-capture stop order, invalid-evidence correction, transport reopen gate | Payload proof, production VME promotion, or survivor-row analysis |
| `2026-06-07-vme-l1-waveform-sandbox-handover.md` | VME Level 1 Waveform-family sandbox start, target modes 7/8/18, quarantine rules | Production VME promotion or dirty-lane acceptance |
| `2026-06-07-dense-forge-closeout.md` | Dense Forge source closeout, exact-flash blocker, sentinel matrix | Secondary/anti-creep patch acceptance |
| `2026-06-07-secondary-dark-state-handover.md` | Silence creep, secondary dark, Dense Forge historical lane routing | Current Dense Forge source status after `a5ce32e` |
| `2026-06-05-cto-session-handover-3.md` | Tempo/octave/confidence, modes 18/19/20 | Current silence/secondary state (superseded on those topics) |
| `2026-06-04-cto-session-handover-2.md` | Historical session context | Octave/confidence claims (**stale**) |
| `2026-06-04-cto-session-handover.md` | Saliency experiment origin | Any current lane status |

---

## Device identity quick-ref

**CANONICAL device↔env↔build truth lives in [docs/hardware/device-build-registry.md](hardware/device-build-registry.md) — read it before ANY flash, erase, or serial-write.** Summary (the registry's deployed-state table is authoritative and updated on every flash):

| Device | Chip ID | Permitted envs by configured route |
|--------|---------|------------------------------------|
| 1401 (main K1) | `F887A500` | `k1_hardware`; `k1_prod_im73d` only when this unit is intentionally configured for the IM73D `6/7` route |
| 12201 (bench K1v2) | `B489A500` | `k1_bench_reference`; non-shippable/IM73D variants `k1_bench_im73d`, `k1_bench_im73d_ble`, `k1_custom` when explicitly selected |

> **Ports drift every session — identity is USB serial / chip-ID, never the port name.** As of the 2026-07-06 R1 run: bench `B489A500` = `/dev/cu.usbmodem101`, main `F887A500` = `/dev/cu.usbmodem1101`. Registry §2 deployed-state table is authoritative.

The two envs differ by GPIO map — never cross-flash. Identity = chip ID, never the port name. The earlier VMEWT-incident caveat is superseded by the registry's deployed-state table.

---

## Recall conventions (claude-mem)

**Worker version at index time:** 12.4.9 (pre-13.4 upgrade). Operational claims (worker up/down, queue routes) are **historical** unless verified live in the current session.

### Project tags

| Project | Approx. obs | When to use |
|---------|------------|-------------|
| `SensoryBridge-main 9` | ~2,850 | Current repo work (2026-06+) |
| `Lightwave-Ledstrip` | ~21,000 | Legacy K1 history, pre-rename |

### Search vocabulary

Use **effect names and file paths**, not forensic shorthand:

| Symptom / topic | Good search terms | Weak terms (often 0 results) |
|-----------------|-------------------|------------------------------|
| Secondary stays lit in silence | `Waveform Tempo`, `mode 18`, `dark gate` | `1401 dark gate`, `secondary throttle` |
| Primary Dense Forge dead | `Dense Forge`, `inject_scale`, `mode 21` | `dforge 1401` alone |
| Scene Policy / Smart Auto | `Smart Auto`, `scene policy`, `SmartDirector` | `scene policy v2` alone |
| Silence / AGC creep | `agc_gated`, `silence creep`, `gate_gain` | `anti-creep` alone |

### 3-layer workflow (always)

1. `search(query, project="SensoryBridge-main 9", dateStart="YYYY-MM-DD")` — index with IDs
2. `timeline(anchor=ID)` — context around hit
3. `get_observations(ids=[...])` — full detail only for filtered IDs

### Corpus build (deferred until claude-mem 13.4)

Empty corpora on 12.4.9 + validation errors on query-only builds. After upgrade, rebuild with structured filters:

```
build_corpus
  name="k1_secondary_throttle_forensics"
  project="SensoryBridge-main 9"
  files="SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_dense_forge.cpp,SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_waveform_tempo.cpp,docs/handover/"
  types="bugfix,discovery,change,refactor"
  dateStart="2026-06-06"
  limit=200
```

Then `prime_corpus` / `reprime_corpus`. See [docs/agent-memory/claude-mem-pre-13.4-checklist.md](agent-memory/claude-mem-pre-13.4-checklist.md).

---

## Evidence bundle index

### `evidence/20260607T025458Z-secondary-throttle-ab/`

| Subpath | Contents |
|---------|----------|
| `analysis/` | Parity verdict, trace summaries, instrumentation diffs |
| `dforge_patch/` | VU gate patch proof, build/flash logs, before/after trace tables |
| `dforge_trace/` | Mode 21 trace captures and summaries |
| `captures/` | Secondary A/B serial captures |
| `baseline/` | Pre-patch runtime and upload logs |

### Key runtime-evidence docs (repo root under `docs/forensics/runtime-evidence/`)

- `2026-06-07-secondary-dark-state-last-writer-verdict.md` — secondary dark root cause
- `2026-06-07-silence-anti-creep-verdict.md` — primary anti-creep closure
- `2026-06-07-scene-policy-v2-serial-ab-state-gate.md` — Scene Policy v2 state gate
- `2026-06-07-ap-vp-visualisation-semantic-canon.md` — AP/VP visualisation semantics, proof boundaries, and experiment matrix

---

## Maintenance

When a lane closes or a new handover supersedes an old one:

1. Update **Active lanes** table and **Supersession map**
2. Update [.claude/handoff.md](../.claude/handoff.md) pointer
3. Append [progress.md](../progress.md) (newest section first)
4. Bump **Last verified** date and git HEAD in this file's header
