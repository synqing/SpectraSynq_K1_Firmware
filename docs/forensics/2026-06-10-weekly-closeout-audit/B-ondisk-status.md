---
abstract: "On-disk closeout audit 2026-06-10: active lanes, declared status, open gates, and runtime-evidence failures from progress.md, handoff.md, spec-index.md, and forensics."
---

# On-Disk Closeout Audit — 2026-06-10

**Evidence gathered:** progress.md (356 lines), .claude/handoff.md (84 lines), docs/spec-index.md (144 lines), forensics/vp_motion_lab/*.md (5 files, 2026-06-09), runtime-evidence/*.frame-gate.json and *.session-error.json.

---

## Active Lanes Table

| LANE/FEATURE | Declared status (quoted) | Source doc:line | Open gates / pending items | Claimed DONE or IN-FLIGHT? |
|---|---|---|---|---|
| VME L1 Waveform sandbox | "Sandbox/shadow only; target Waveform Fast, Waveform, and Waveform Tempo; next valid step is fail-closed transport proof before hardware" | spec-index.md:26 | Hardware capture frozen. Reopen gate: fail-closed parser tests, framed CRC transport, zero dropped/corrupt/overflow, paired final-byte records modes 7/8/18 primary+secondary | IN-FLIGHT (blocked) |
| VMEWT transport incident | "Hardware VMEWT capture frozen; failed sandbox survivor rows are not runtime proof" | spec-index.md:25, progress.md:9 | Must produce fail-closed transport proof before any hardware work resumes | IN-FLIGHT (blocked, containment committed) |
| Dense Forge (mode 21) | "Source committed + exact `a5ce32e` flashed to 1401 and locked to mode 21; Captain eyes-on PASS was on repair build before exact-source reflash" | spec-index.md:27, progress.md:27 | None for source; K1 1401 may have probe firmware from VME incident — "Restore or verify normal `k1_hardware` on the exact device before product testing" (spec-index:66) | DONE (source + eyes-on), device state uncertain |
| Secondary dark-state (mode 18) | "Fix flashed to 1401; Captain eyes-on re-test **pending**" | spec-index.md:28, progress.md:33 | Captain eyes-on re-test pending; secondary fix in `light_mode_waveform_tempo.cpp` (dark gate + history drain) flashed as `F887A500` but re-test not completed | IN-FLIGHT (eyes-on pending) |
| Scene Policy v2 | "Serial A/B state gate done; visual product judgement **open**" | spec-index.md:29, progress.md:45 | Visual product judgement open — state gate PASS but no camera/video device attached during two-K1 A/B. Weak-lock residual `loreen_127` scoped P2. Device matrix is "PARTIAL, not production-green" (progress.md:42) | IN-FLIGHT (blocked on visual A/B) |
| AP0/VP1 closeout | "Historical; do not reopen without new evidence" | spec-index.md:30 | None — closed lane | DONE (historical) |
| Tempo primitive / audio-semantic forward-graft | "Octave/confidence SOLVED; modes 18/19/20 host-green" | spec-index.md:31 | Device eyes-on was the one remaining gate as of 2026-06-05. Promoted to k1_hardware but "DEVICE eyes-on = the one remaining gate" per MEMORY.md | DONE (host gate GREEN), device eyes-on tracking follow-up |
| VP Motion Lab (VPML) | Not in spec-index Active Lanes table (added 2026-06-09 commits). Roadmap deferred Page 4 "Promotion + Regression Ledger"; intro_bounce_loop programme present | forensics/vp_motion_lab/ (2026-06-09 docs) | Page 4 deferred until real promoted candidates exist. Session-error failure on one capture run. Frame-gate intermittently failing (see runtime-evidence section) | IN-FLIGHT (new lane, MVP active, deferred sub-pages) |
| K1 AV Regression v2 | "evidence-assembled, not release-promoted: weak-lock confidence evidence still needs matrix reconciliation, and product fit is deferred to Scene Policy v2" | progress.md:39 | Matrix reconciliation pending; `loreen_127` weak-lock unresolved; production promotion gated on Scene Policy v2 A/B | IN-FLIGHT (deferred) |
| Dirty lanes quarantine | "all unfinished June 7 dirty work on quarantine branch `wip/2026-06-07-unfinished-lanes-quarantine` at `a40bdb8`" | handoff.md:19, progress.md:19 | Secondary dark-state anti-creep, Tempo Comet, VP chroma, trace-dev config, evidence — all quarantined. "Remaining dirty lanes require separate acceptance decisions; do not bundle." | QUARANTINED (not accepted, not closed) |

---

## Open Gates / Pending Items (explicit, unresolved)

1. **Secondary dark-state eyes-on re-test** — `progress.md:33`: "Captain eyes-on re-test **pending**"; `spec-index.md:28`: "Fix flashed to 1401; Captain eyes-on re-test **pending**"
2. **VME hardware capture frozen** — `progress.md:14`: "VME hardware capture is frozen. Reopen only from corrupt-log red tests, fail-closed parser gates, bounded deferred diagnostic records with sequence/length/CRC, zero dropped/corrupt/overflow, and paired current-vs-VME final-byte records for modes 7/8/18 primary and secondary."
3. **Produce baseline packet + primitive map for modes 7, 8, 18** — `handoff.md:64`: "Produce the baseline packet and primitive map for modes 7, 8, and 18." (next step 4)
4. **Define shadow VME port + paired final-byte probe** — `handoff.md:65`: "Define the shadow VME port and paired final-byte probe before any production patch."
5. **1401 device state** — `handoff.md:52`: "K1 1401 was flashed with non-shippable probe builds during the failed lane. If the next use is product eyes-on, a regression sentinel, or handing the device back as trusted, restore or verify normal `k1_hardware` on the exact device."
6. **Scene Policy v2 visual product judgement** — `spec-index.md:29`: "visual product judgement **open**"; `progress.md:42`: "Fresh device matrix is `PARTIAL`, not production-green"
7. **K1 AV Regression v2 production promotion deferred** — `progress.md:39`: "product fit is deferred to Scene Policy v2 A/B validation"; `progress.md:42`: weak-lock classifications remain unresolved
8. **`loreen_127` weak-lock P2 residual** — `progress.md:43`: "remains weak-lock because bounded replay still has zero high-confidence/locked warm rows"
9. **Dense Forge exact-source eyes-on gap** — `handoff.md:25`: "Captain eyes-on PASS was on the repair build before exact-source reflash" (not after exact-source reflash)
10. **Dirty lane quarantine acceptance decisions** — `handoff.md:54`: "Remaining dirty lanes require separate acceptance decisions; do not bundle." Quarantined: anti-creep, Tempo Comet, VP chroma, trace-dev config
11. **VP Motion Lab Page 4 deferred** — `vp_motion_lab/2026-06-09-vp-motion-lab-onwards-roadmap.md:34,254,559`: "Deferred Page 4: Promotion + Regression Ledger" until real promoted candidates exist
12. **VMEWT incident containment** — `handoff.md:83`: "Release NOT accepted: telemetry PASS, eyes-on FAIL pre-fix on secondary; post-fix eyes-on pending."

---

## Runtime-Evidence Failures (last 7 days)

| Session file | Type | Passed? | Error |
|---|---|---|---|
| `20260609T212727-vpml-intro-bounce-loop-1401.frame-gate.json` | frame-gate | **false** | (no error string) |
| `20260609T213624-vpml-live-intro-bounce-loop-em1401.frame-gate.json` | frame-gate | true | — |
| `20260609T214319-vpml-intro-bounce-loop-1401.frame-gate.json` | frame-gate | **false** | (no error string) |
| `20260609T214319-vpml-intro-bounce-loop-1401.session-error.json` | session-error | **false** | `":vpml=status missing response containing 'VPML status', 'active=1', 'intro_bounce_loop'; observed: no response"` |
| `20260609T214857-vpml-intro-bounce-loop-1401.frame-gate.json` | frame-gate | true | — |
| `20260609T220729-vpml-intro-bounce-loop-1401.frame-gate.json` | frame-gate | true | — |
| `20260609T232714-vpml-control-path-em1401.frame-gate.json` | frame-gate | true | — |

**Pattern:** 2 of 5 `intro_bounce_loop` frame-gates on 1401 failed on 2026-06-09 (T212727, T214319). One session-error (T214319): `:vpml=status` command received no response from device. Later runs the same evening passed, suggesting intermittent device-response issue or probe-firmware state, not a permanent regression.

---

## Source docs read

- `/Users/spectrasynq/SensoryBridge-main 9/progress.md` (356 lines)
- `/Users/spectrasynq/SensoryBridge-main 9/.claude/handoff.md` (84 lines)
- `/Users/spectrasynq/SensoryBridge-main 9/docs/spec-index.md` (144 lines)
- `/Users/spectrasynq/SensoryBridge-main 9/docs/forensics/vp_motion_lab/2026-06-09-vp-motion-lab-mvp-decision.md`
- `/Users/spectrasynq/SensoryBridge-main 9/docs/forensics/vp_motion_lab/2026-06-09-vp-motion-lab-onwards-roadmap.md`
- Runtime-evidence `*.frame-gate.json` and `*.session-error.json` (last 7 days)

---

**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-06-10 | agent:claude-code | Created: on-disk closeout audit for SSA brief |
