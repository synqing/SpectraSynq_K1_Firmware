---
abstract: "Feasibility + realistic time projection for the 2026-06-10 Perceptual-Wins + Tri-MCU execution brief (lanes A–G). Verdict: S3 perceptual lanes (A,B,C,D,E1,G) are highly feasible — ~2–4 days of swarmable coding gated behind ~1–2 weeks of batched Captain eyes-on (eyes-on, not coding, is the binding constraint). Lane F (tri-MCU/P4) is feasible only as a 2–4 week hardware SPIKE: its 'port onto a validated P4 DSP lane' premise is FALSE — the P4 repo is a 2-day-old bring-up, its DSP is never validated on real music, and the conditioner/line-in/C6 are greenfield. Includes per-lane feasibility, two-clock time model, premise corrections, and Decision-Point recommendations. Grounded in a 4-agent source-verification fan-out + 2 orchestrator re-runs."
---

# Feasibility & Time Assessment — Perceptual Wins + Tri-MCU Platform Brief

**Assessed:** 2026-06-10 · **Subject brief:** `docs/handover/2026-06-10-perceptual-platform-execution-brief.md`
**Method:** 4-agent source-verification fan-out (firmware claims, P4 platform, governance/test-gate, prior-review recall) + orchestrator re-run of the two decision-critical artefacts (host-test count, P4 maturity/conditioner existence). SSA consumption discipline applied (`/ssa-management`).
**Bottom line:** The brief is **well-constructed and mostly source-grounded**. The perceptual lanes are feasible and the Captain's "swarm makes mincemeat of a week's coding" intuition is **correct for the coding clock** — but coding is not the bottleneck. Two premise corrections are load-bearing: **Lane F is a spike onto 2-day-old scaffolding, not a port onto validated IP**, and **eyes-on throughput, not agent hours, sets the schedule.**

---

## 1. The two-clock model (the core of the answer)

A multi-agent swarm collapses **Clock 1**. It cannot touch **Clock 2** — and Clock 2 is the binding constraint (Theory of Constraints: optimising the non-bottleneck does not move the finish line).

| | **Clock 1 — Swarmable coding** | **Clock 2 — Irreducible validation** |
|---|---|---|
| What | host firmware edits, host replay tests, schema doc, transport shim, design docs, sim harness | Captain on-device eyes-on; MabuTrace trace-dev timing proof; physical soldering; 1-hr soaks; real-music DSP validation; esp-hosted bring-up |
| Who | agents, in parallel | Captain + real hardware + real-time playback + physics |
| Compressible by more agents? | **Yes** | **No** |
| Realistic span | **~2–4 working days** for all S3 host coding (A,B,C,D,E1,G) | **~1–2 weeks** elapsed (batched eyes-on) for S3 lanes; **2–4 weeks** for Lane F hardware |

**Headline projection**
- **S3 perceptual program (A, B, C, D, E1, G):** ~2–4 days swarmed coding → PASS/FAIL verdicts gated behind **~1–2 weeks** of batched Captain eyes-on. Treat as a **1–2 week elapsed program**, paced by eyes-on, not keystrokes.
- **Lane F (tri-MCU):** **separate 2–4 week hardware spike**, premise re-scoped (below), Captain-gated at F1. Decouple from the perceptual wins (brief already mandates this).

---

## 2. Verification ledger (what the brief got right / wrong)

| Claim in brief | Verdict | Evidence |
|---|---|---|
| `sbv2_band_flux()` per-band flux computed-but-unpublished (`sb_onset_beat.cpp:133-141`) | **TRUE** | function exists; values transient, not in publish struct |
| `agc_envelope`/`agc_noise_floor` exist, unpublished (`globals.h:575-576`) | **TRUE** | `SQ15x16` globals; absent from `AudioSemanticState` |
| `sb_tempi_smooth[]`/`sb_acf_salience[]` = 96 bins, private statics, unpublished | **TRUE** | `SB_NUM_TEMPI=96`, file-private |
| Chord state has **zero** consumers | **PARTIAL** | zero *visual/render* consumers TRUE; but AP-saliency (`sb_musical_saliency.cpp`) already reads chord. Reframe: "no visual consumer," not "nothing reads it" |
| Snare/hihat dark to VP | **TRUE** | no consumers outside producers |
| (implied) percussive channels dark | **FALSE** | kick/transient already consumed by Pulse Prism + Smart Director |
| `novelty` only Dense Forge | **PARTIAL** | true for effects; Smart Director also reads novelty |
| Lane A beat fields (`beat_phase01,bpm,tempo_locked,tempo_confidence,beat_tick`) present + accessible | **TRUE** | all in `AudioSemanticState`, lock-safe accessor |
| Dual-channel = single shared state, no independence | **PARTIAL/STALE** | render state **already** independent (`ChannelEffectState`, 9 overrides). Real gap = both channels read the **same audio source**. **Lane D is smaller than briefed.** |
| Host gate "310-test" (F2) | **TRUE** | 40 files, ~313 test defs. (CLAUDE.md "136" is stale.) |
| VMEWT fail-closed / no-survivor-row contract real | **TRUE** | `docs/forensics/vme_l1/2026-06-07-vmewt-transport-incident.md` |
| Quarantine (mode-18 secondary-dark off-limits) real | **TRUE** | `wip/2026-06-07-unfinished-lanes-quarantine @ a40bdb8` |
| **P4 has a validated DSP lane to port onto** | **FALSE — see §4** | repo 2 days old; DSP unit-tested on synthetic fixtures only, never on real music; conditioner unbuilt; C6 + line-in greenfield |

**Precondition flagged twice independently (P0):** the brief was authored against a **dirty working tree at non-canonical HEAD `a21a30f`** (spec-index authority = `f0c6808`). Reconcile to a clean named baseline (~1 h) **before** any lane edits, or everything builds on uncommitted sand.

---

## 3. Per-lane feasibility & time

| Lane | Feasible? | Clock-1 coding (swarmed) | Clock-2 gate | Notes / landmines |
|---|---|---|---|---|
| **A** anticipatory beat A/B | **High** | ~½ day | 1–2 Captain eyes-on sessions | **Risk:** phase-extrapolation may expose a flywheel publish bug → doctrine gate before any `sb_tempo` edit (blast radius). The thesis-falsification value is high — do this early. |
| **B** Tier-1 consumers | **High** | ~1 day | eyes-on on harmonically-rich material | **B1 needs a chord-quality HOST gate FIRST:** flat chroma reads as a confident major triad (conf ≈0.625); naive chord→colour will look wrong and burn an eyes-on cycle. Gate on `chord_confidence` variance over real fixtures before device. B2/B3 clean. |
| **C** Tier-2 publish surface | **High (host) / device-gated (safety)** | ~1 day (C0 schema + C1/C2/C3) | **MabuTrace trace-dev** | Touches Core-0 publish path. `test_rate_consistency.py` is a **text cadence guard, not timing proof** — frame-time safety is **not host-closable**; needs MabuTrace on trace-dev. Don't overclaim host-green as frame-time-safe. |
| **D** true dual-channel | **High — smaller than briefed** | ~1 day | eyes-on ("independent dual-channel" doctrine criterion) | Render state already independent; real work = **per-channel audio-axis assignment** + stereo hook in channel config. `render_replay.py --dual` already exists for host validation. RAM-budget check (report numbers). |
| **E** dramaturgy | **Feasible, two-phase** | E1 design+sim ~1–2 days | **two** Captain gates: design-review → full-track eyes-on (3+ min) | E2 firmware gated on Lane A PASS. No Smart Director edits before design sign-off. Genuinely the most open-ended lane. |
| **F** tri-MCU | **Spike only — see §4** | code ~2–3 days | **weeks** (solder, soak, real-music DSP validation, esp-hosted) | Premise correction is load-bearing. Long pole. Decouple. |
| **G** validation rig | **High (if camera exists)** | ~1 day | one end-to-end A/B capture | **Highest leverage — build FIRST.** It is the only lane that attacks the actual constraint (eyes-on throughput) by making eyes-on asynchronous/repeatable. |

---

## 4. Lane F premise correction (decision-critical)

The brief frames F2 as "port the validated K1 engine onto the P4's conditioned float-mono DSP input lane, replacing scaffolding." Verification (2 agents + orchestrator re-run) shows:

- **The P4 repo is a 2-day-old bring-up** (commits 2026-06-09 → 2026-06-10). Maturity tier **(b): working demo, not a proven engine.**
- **Genuinely proven:** ES8311 24-bit/48 kHz capture integrity (CRC'd, `read_errors=0` — but a **2.0 s** capture, not a soak); A-weighting biquad cascade; actor-stats telemetry; DSP code **compiles + passes synthetic-fixture unit tests**.
- **NOT built / aspirational:** the `p4_audio_conditioner` graft target (**plan only**, unwritten); DC/rumble/AGC conditioning of the reusable stream; **all** C6/WiFi6 radio code; **all** line-in/aux analogue input.
- **Never validated on real music:** tempo/chroma/onset *quality* on live audio is unproven — the exact validation campaign that took the K1 engine weeks.

**Therefore:** F2 is not "port onto a better lane." It is **port the K1 validated *concepts* onto 2-day scaffolding + a net-new real-music DSP-validation campaign**, fronted by **greenfield analogue input (F1)** and trailed by **greenfield radio (F5)**. The K1 engine *is* the validated IP (so the port direction is right), but **budget for re-validation; do not treat the P4's existing metrics as meaningful yet.** Scope F as a 2–4 week spike with its own resourcing, not a fast graft.

Binding constraints in F that no swarm removes: F1 wiring is **Captain-gated before soldering**; F3 requires a **1-hour zero-defect soak** (VMEWT zero-tolerance → expect iterations); F4 needs a **physical latency rig**; F5 esp-hosted bring-up is greenfield and fiddly.

---

## 5. Critical path & recommended sequencing

```
P0 reconcile dirty a21a30f → clean named baseline        (~1 h, precondition)
   │
   ├─ G harness FIRST (if camera) ── attacks the eyes-on bottleneck ── multiplies every verdict below
   │
   ├─ A (thesis falsification) ─┐
   ├─ B1+B2+B3  (B1 host-gate)  ├─ batch into ONE Captain eyes-on session set
   ├─ D (per-channel audio-axis)┘     (with the already-open forward-graft eyes-on gate)
   │
   ├─ C0 schema → C1/C2/C3 (device frame-time proof via MabuTrace, separate gate)
   │
   ├─ E1 design+sim → Captain design-review → (E2 only if A passes)
   │
   └─ F (parallel hardware spike, Captain-gated at F1, weeks, decoupled)
```

Sequencing rationale (Leverage Points): G first, because the schedule is set by eyes-on throughput; everything else is gated on it. A early, because it falsifies the time-thesis cheaply and gates E2.

---

## 6. Decision-Point recommendations (brief §8)

| # | Decision | Recommendation |
|---|---|---|
| 1 | F1 aux wiring approval | **Cannot approve yet** — agent must produce the schematic-derived wiring diagram first (greenfield). Gate all of F behind producing + approving it; do not start F2 assuming F1. |
| 2 | Port K1 engine onto P4 vs evolve P4 lane | **Port the K1 engine — but reframe as a spike, not a graft.** Neither lane is validated on real music; the P4 conditioner is unwritten. Port K1 (it's the validated IP) and **budget for full real-music re-validation**; don't assume P4 metrics transfer. |
| 3 | C3 24-bin vs 96-bin tempo surface | **24-bin for v1.** Arrays are private statics with no struct/frame-time budget assertions today; start decimated, measure struct growth + frame-time on trace-dev before considering 96. |
| 4 | Camera for Lane G | **Yes if at all feasible — and build G first.** It is the single highest-leverage item because it relieves the real bottleneck (Captain eyes-on throughput). Design-only is a weak second. |
| 5 | Batch A/B/D eyes-on with existing gate | **Yes, batch.** It is the only way to respect Captain throughput and the Founder Execution Boundary (the founder's bench is not an iterative debug harness). |

---

## 7. Net feasibility verdict

- **S3 perceptual wins (A, B, C-host, D, E1, G): FEASIBLE, high confidence.** ~2–4 days swarmed coding; **1–2 week elapsed** program gated on batched eyes-on. The swarm genuinely makes the coding "mincemeat" — but plan the calendar around eyes-on sessions and the MabuTrace device gate (Lane C), not the keystrokes.
- **Lane C frame-time safety, Lane E firmware:** feasible but **device/Captain-gated**, not host-closable. Don't let host-green masquerade as timing/perceptual proof.
- **Lane F (tri-MCU): FEASIBLE AS A SPIKE ONLY.** Re-scope before resourcing: 2–4 weeks, greenfield analogue + greenfield radio + net-new real-music DSP validation on a 2-day-old codebase. Highest risk, longest pole, correctly decoupled.
- **Three load-bearing fixes before kickoff:** (1) reconcile the dirty `a21a30f` baseline; (2) put a chord-quality host gate ahead of Lane B1; (3) correct the Lane F2 "validated IP" premise in the brief.

---

**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-06-10 | agent:claude-code | Created — feasibility + two-clock time projection for the perceptual-platform brief; grounded in a 4-agent verification fan-out + 2 orchestrator re-runs (test count, P4 maturity). |
