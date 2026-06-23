---
abstract: "Closeout audit of the last 7 days (2026-06-03..2026-06-10) on wip/audio-saliency-recovery. Verdict: NOT closed out. Verified facts: 0/208 commits merged to main; host gate currently RED (2 stale-test failures from the VPML render-params refactor); test env fractured (.venv lacks pytest, Homebrew pytest lacks numpy/yaml); progress.md containment baseline (13ffe00) is stale — 17 production-firmware changes landed above it; 78 uncommitted paths; quarantine branch holds 6 unreviewed dirty lanes; ~8 eyes-on / device / VME gates open. Root cause (Theory of Constraints): the closeout-tracking ledger (spec-index/handoff) lags the work — 2026-06-09 VPML/Tab5/WS lanes are not registered. Read when deciding what to close out, merge, or re-test."
---

# Weekly Closeout Audit — 2026-06-03 → 2026-06-10

**Branch under audit:** `wip/audio-saliency-recovery` (HEAD `88a1bc3`)
**Method:** 4 parallel read-only recon agents (git / on-disk docs / test-gate / memory) under SSA launch contracts; all decision-critical claims personally re-run by the orchestrator (Map–Territory discipline under the active MEMORY TRUST FREEZE). claude-mem worker was down (port 37777, 485 stuck messages) — memory used as leads only.

**Raw per-agent evidence:** `docs/forensics/2026-06-10-weekly-closeout-audit/{A-git-archaeology, B-ondisk-status, C-test-gate, D-memory-recall}.md`.

## Verdict

**The last week's work is NOT closed out** (at audit time). It is a large body of **unmerged, partially-uncommitted, host-gate-red, eyes-on-pending** work sitting on one long-lived `wip` branch. No single feature from the week meets the project's own closeout bar (host-green + build-green + device eyes-on where required + merged/registered).

> **Update — 2026-06-10, post-audit (Captain-directed):** The gate was repaired (host pytest **310 passed**), the working tree was committed in 6 scoped units, and `wip/audio-saliency-recovery` was **merged to main** by fast-forward (`main` @ `1ad084e`, pushed to origin) after `pio run -e k1_hardware` and `pio run -e tab5` both **SUCCEEDED**. This closes the *source-integration + host-gate + build-gate* dimensions of closeout. It does **NOT** close **device eyes-on**, which remains the open gate for the forward-graft, effect modes 18/19/20/21, the WS control / noise-cal-arm path, and VPML. `main` is now a *compiles + host-green* baseline, not an eyes-on-validated release. The quarantine branch (6 dirty lanes) was deliberately left unmerged.

## Verified facts (orchestrator re-ran each — these are territory, not prose)

| # | Fact | Re-run command | Result |
|---|------|----------------|--------|
| 1 | **Nothing merged to main.** HEAD is 208 commits ahead, 0 behind; no commits on main since before 2026-06-03. | `git rev-list --left-right --count main...HEAD` | `0  208` |
| 2 | **Host gate is RED** — 2 real failures, both **stale test assertions** (not firmware regressions). | `.../pytest tests/test_boot_intro_static.py tests/test_vp_motion_lab_static.py -q` | `2 failed, 14 passed` |
| 3 | **Test env is fractured** — `.venv` (py3.14) has numpy 2.4.6 + yaml 6.0.3 but **no pytest**; Homebrew pytest (py3.11) has **neither**. Canonical `python3 -m pytest` cannot run clean on this machine without env repair. | `.venv/bin/python3 -m pytest --version` | `No module named pytest` |
| 4 | **progress.md containment baseline is STALE.** progress.md:11 claims empty firmware diff above `13ffe00`; actual = 17 production-firmware changes incl. 6 new shipping files (WS control facade, wireless control, noise-cal arm, vp_motion_lab.h). | `git diff --name-status 13ffe00..HEAD -- SPECTRASYNQ_K1_FIRMWARE platformio.ini` | 17 paths changed |
| 5 | **78 uncommitted paths** (20 modified-tracked, 0 staged, 58 untracked) — the most recent VPML/Tab5 continuation. | `git diff --name-only \| wc -l` etc. | 20 / 0 / 58 |
| 6 | **Quarantine branch exists**, holding 6 dirty June-7 lanes, unreviewed. | `git branch -a \| grep quarantine` | `wip/2026-06-07-unfinished-lanes-quarantine` |

### On the host-gate failures (fact #2 detail)
Both failures are test-debt from the VPML render-params + dual-program refactor; firmware logic is intact (arguably improved — parameterized):
- `test_boot_intro_static::test_intro_has_warm_centre_origin_bounce` — asserts literal `intro_bounce_radius(t - 0.06f, …)`; code now uses parameterized `intro_bounce_radius(t - (params.secondary_phase * 0.60f), …)`.
- `test_vp_motion_lab_static::test_vpml_header_is_non_shippable_and_render_safe` — asserts fixed-constant `vp_intro_render_frame(vpml_frame, VPML_INTRO_BOUNCE_FRAMES)`; code now uses dynamic `vpml_frame_count_for_program(...)` and added `INTRO_BOUNCE_LOOP`. The NON-SHIPPABLE / no-forbidden-render-call safety half still passes.

Agent C's original verdict ("RED, 4 failures, dependency-broken") was an artifact of running the **wrong interpreter** (Homebrew pytest, missing numpy/yaml). The orchestrator re-run corrected it to **2 real failures**, both benign stale assertions — which `amend-broken-gates` says must be fixed-as-a-class before the next gated commit.

## Closeout punch-list (grouped by state, owner-classified)

Owner key: **[A]** = autonomous (host-only, no product judgement) · **[C]** = Captain-gated (device / product / decision) · **[I]** = needs investigation (delegable).

### Blocking the gate (do first — `amend-broken-gates`)
| Item | Owner | Action |
|------|-------|--------|
| Host gate RED — 2 stale test assertions | **[A]** | Update both assertions to the parameterized / dynamic-frame-count forms; re-run to green. |
| Test env fractured (no pytest in `.venv`) | **[A]** | `pip install pytest` into `.venv` (which already has numpy/yaml), OR document the canonical run env. Currently the gate can't be cleanly executed. |

### Tracking-ledger drift (the systemic gap — see Root Cause)
| Item | Owner | Action |
|------|-------|--------|
| `spec-index.md` Active Lanes omits 2026-06-09 lanes (VPML, Tab5 wireless controller, K1 WS control facade) | **[A]** | Register the three lanes with status + open gates. |
| `progress.md:11` containment baseline stale (17 firmware changes above 13ffe00) | **[A]** | Correct the containment statement to reflect the WS-facade/wireless/noise-cal-arm/VPML firmware landings, or re-baseline. |
| `handoff.md` last synced 2026-06-07 | **[A]** | Re-point active session to current state. |

### Committed on wip, host-done, **device eyes-on OPEN**
| Feature | Owner | Open gate |
|---------|-------|-----------|
| Audio-semantic forward-graft (modes 18/19/20, v2 DSP) | **[C]** | Device eyes-on never confirmed (tracked non-blocking follow-up, never closed). |
| Tempo River / Beat Palette / Tempo Comet (modes 19/20/21, `af9d129`) | **[C]** | Host-green; Captain eyes-on pending. |
| Secondary dark-state fix (mode 18 / Waveform Tempo) | **[C]** | Flashed to 1401; eyes-on re-test pending. |
| Dense Forge (mode 21, `a5ce32e`) | **[C]** | Eyes-on PASS was on a *repair* build, not the exact-source reflash. |

### Device / hardware integrity
| Item | Owner | Open gate |
|------|-------|-----------|
| K1 1401 may hold non-shippable VME probe firmware | **[C]** | Verify identity + restore `k1_hardware` before any product eyes-on. |
| VME L1 hardware capture FROZEN (transport incident) | **[C]** | Reopen needs: fail-closed parser, framed CRC/seq/len, zero dropped/corrupt, paired final-byte records modes 7/8/18. |
| VPML `intro_bounce_loop` runtime FAILs on 1401 (2026-06-09: 2 frame-gate fails + 1 session-error "no response to VPML status") | **[I]** | Intermittent; later runs passed. Root-cause device-response vs probe-firmware state. |

### Product / promotion decisions
| Item | Owner | Open gate |
|------|-------|-----------|
| Scene Policy v2 | **[C]** | Serial A/B state gate done; visual product judgement open (no camera A/B). |
| K1 AV Regression v2 | **[C]** | Evidence-assembled, not release-promoted; `loreen_127` weak-lock P2 residual; deferred to Scene Policy v2. |
| Quarantine branch — 6 dirty lanes (anti-creep, mode-18-secondary, Tempo Comet, VP chroma, trace-dev config, evidence) | **[C]** | Each needs a per-lane accept / kill decision; none made. |
| Whole `wip/audio-saliency-recovery` branch (208 commits) | **[C]** | Merge-to-main strategy undecided; branch accreting since ~May 25. |

### Build / wiring debt (not strictly "last week" but adjacent, open)
| Item | Owner | Note |
|------|-------|------|
| `SB_CHORD_V2` / `SB_SEMANTIC_STATE` promoted but **inert** — no Director consumer | **[C/I]** | Flags shipped; Smart Director still beat-blind. Wiring is a build lane, not closeout. |
| 78 uncommitted paths | **[C]** | Intent unknown — new commit vs WIP residue. Needs direction before staging. |

## Root cause (Theory of Constraints) + the contradiction (TRIZ)

The recurring closeout failure is **not** engineering throughput — it's the **closeout-tracking ledger lagging the work**. Evidence: the 2026-06-09 VPML/Tab5/WS-facade lanes aren't in the Active Lanes table at all, and `progress.md`'s containment baseline is two commits' worth of firmware out of date. Features don't just strand at the eyes-on gate — **some are never registered as needing one.** The constraint is *ledger update cadence*, not coding.

The project already resolves the core TRIZ contradiction — *"host-green closes the work"* vs *"device eyes-on is the real proof"* — by **separation-in-condition** (commit host-green, eyes-on as a tracked non-blocking follow-up). That resolution is sound; the **"tracked" half is failing.** The fix is *Preliminary Action (#10) + Self-Service (#25)*: a single canonical closeout ledger that every lane must appear in, updated **at commit time**, with an explicit `eyes-on: pending|pass|n/a` field — so the follow-up cannot silently fall off. This audit doc is the first instance of that ledger.

## Recommended sequence
1. **[A]** Fix the 2 stale tests + repair `.venv` pytest → restore green, canonical gate runnable. *(safe, no product judgement)*
2. **[A]** Reconcile spec-index / progress.md / handoff to register the 3 unregistered lanes + correct the containment baseline. *(closes the systemic gap)*
3. **[C]** Captain decides the **device eyes-on batch** (forward-graft, modes 18/19/20/21, Dense Forge exact-source) — these are the long pole; group them into one bench session.
4. **[C]** Captain decides **quarantine disposition** (6 lanes: accept/kill each) and the **merge-to-main strategy** for the wip branch.
5. **[C]** VME reopen + 1401 firmware restore are their own hardware lane, gated on the transport-proof criteria.

## Delegation ledger (SSA discipline)

| ID | Agent | Claim | Class | Status | Re-run result | CONSUMED AS |
|----|-------|-------|-------|--------|---------------|-------------|
| A | git archaeology | 0/208 merged; 78 uncommitted | decision-critical | verified | `0 208` confirmed; untracked corrected 35→58 | verified evidence (counts corrected) |
| B | on-disk docs | ~9 lanes in-flight/blocked, eyes-on pending | load-bearing | verified | quarantine branch + containment spot-checked | verified evidence |
| C | test gate | "RED, 4 failures, dependency-broken" | decision-critical | **contradicted → corrected** | re-ran: 2 real (stale tests) + 2 env-artifacts of wrong interpreter | corrected-after-rerun |
| D | memory/recall | 17 open threads; worker down | optional/provisional | partial | leads cross-checked vs git/docs; several promoted | provisional → key items verified |

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-06-10 | agent:claude-code | Created — weekly closeout audit; 4-agent recon + orchestrator re-runs; verified merge state, host-gate (RED, stale tests), env fracture, stale containment baseline; owner-classified punch-list + Theory-of-Constraints root cause. |
