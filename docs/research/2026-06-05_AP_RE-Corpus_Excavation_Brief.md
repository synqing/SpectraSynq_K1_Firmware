# CC-Agent Directive — RE-Corpus Excavation: Synesthesia + Auto-BPM → K1 AP Candidate Register

**Date:** 2026-06-05 · **Author:** Captain (via CTO/CPO synthesis) · **Status:** handoff brief, not yet dispatched
**delegation_id:** `RECORP-EXCAV-01` · **classification:** LOAD-BEARING (its register gates future AP architecture decisions)

---

## 0. Mission (one sentence)

Convert the Synesthesia and Auto-BPM reverse-engineered (RE) corpora into a **provenance-graded, portability-graded, gate-testable candidate register** for the K1 audio pipeline (AP) — surfacing **every** option with a recommend/reject justification — while **promoting nothing to canonical**. Promotion is a joint Captain decision held *after* this register exists.

---

## 1. Why this is constrained the way it is — the SynqMatrix inoculation (read before anything else)

The previous attempt to inherit from these apps ("SynqMatrix") did **not** fail on algorithms. It failed on **provenance and authority**. The prior audit (`Lightwave-Ledstrip/firmware-v3/docs/research/SynqMatrix_Synesthesia_Authority_Audit_2026-05-16.md`) established, with evidence:

- The chain *"Synesthesia → Family B → reference-grade → authoritative"* stands **only at link one**. "Family A/B" appears **nowhere** in the RE source — it is NotebookLM bundling metadata.
- The constants previously believed to be Synesthesia's — **Davies-3-promote / IBT ±46.4 ms / MIREX ±70 ms** — are **Tier-2 academic** (Davies & Plumbley, MIREX), *misattributed*. This exact **category error** is the failure mode you exist to prevent, not reproduce.
- The RE **self-rates 70–75 % confidence**, *"typical ranges, not app-specific."* Treat all RE parameter values as inferred, not measured, unless the source proves otherwise.
- The SpectraSynq Doctrine designates **Emotiscope** (the donor-v3 lineage), **not** Synesthesia, as K1's canonical upstream ancestor.
- V0 shipped with **zero** Synesthesia constants.

**Therefore the governing rule:** you *excavate and grade*; you **never anoint**. Authority is Captain's call, it has no written record, and only Captain can make it. An agent that writes "X is reference-grade" has already failed.

**One more load-bearing fact:** both apps are the **same algorithm family** as our current fork — autocorrelation/IOI tempo + a 0–1 confidence + exponential smoothing — and both carry the **same floored-confidence keystone** we are already fighting. Do **not** assume either app solves our actual bottleneck (a confidence metric reachable on real music). Any candidate claimed to fix confidence earns adversarial scrutiny, not adoption.

---

## 2. Operating contract you inherit (propagation — non-negotiable)

- Label every claim **[FACT] / [INFERENCE] / [HYPOTHESIS]**. `[FACT]` only if quoted/attributable to a source you read, or stable background knowledge. RE-author inferences are `[INFERENCE]` at best.
- **Challenge weak premises** in the corpora directly; do not launder a corpus assertion into a fact.
- **No retry-without-diagnosis.** Two failures of the same kind → stop, state mechanism, propose alternative.
- **Environment-verify before asserting.** Confirm paths resolve and the harness runs *before* relying on either.
- **Escalate, do not self-adjudicate.** When a decision is Captain's (see §8), surface it; do not answer it.
- **Ask Captain when genuinely blocked** on strategic direction or domain context — the questioning protocol applies to you too. "Do your own work" means do the excavation yourself; it does **not** mean suppress a real blocker.
- British English. No precision theatre. No motivational filler. Leverage over activity.

---

## 3. Scope

**Primary spine (highest signal):** tempo + beat + onset.
**Secondary (opportunistic, explicitly in scope):** the *entire* AP feature surface — novelty front-end, AGC / level handling, onset/transient semantics, harmonic/chord/saliency, the ControlBus contract edges, anything with a **credible, testable betterment case** for the AP as a whole. Captain's instruction: *"it would be foolish not to consider them."*

**Guard against sprawl:** secondary candidates must clear a **higher relevance bar** than primary ones — a secondary item is only worth a row if its betterment hypothesis is concrete and gate-testable. Vague "nice architecture" observations are rejected, not catalogued.

---

## 4. Sources (verify access first)

**Reference corpora (the subject of excavation):**
- Synesthesia RE — `~/Workspace_Management/Software/Synesthesia/` *(Captain-confirmed reachable; verify on entry)*.
- Auto-BPM technical analysis — canonical path **TBC by Captain**; in-session upload was `docs_Auto_BPM_Technical_Analysis.md` (+ companion `00_/01_/05_` docs, some of which are Synesthesia.RE excerpts, e.g. `Synesthesia.RE/02_ALGORITHMS/05_Algorithm_Specifications.md`). Locate and confirm before relying.

**Prior art — READ FIRST, reconcile against, do NOT re-derive:**
- `Lightwave-Ledstrip/firmware-v3/docs/research/SynqMatrix_Synesthesia_Authority_Audit_2026-05-16.md` — the authority findings above.
- `Lightwave-Ledstrip/firmware-v3/docs/MusicAware_Audit_And_Gap_Analysis.md` — already contains a **Tier-1 (Synesthesia) / Tier-1 (Auto-BPM) / Tier-2 (Academic) front-end comparison table** (~lines 57–65). **Extend this table; do not start blank.**
- SynqMatrix RFC + handover (`SynqMatrix_Director_RFC_2026-05-15.md`, `SESSION_HANDOVER_20260515_SynqMatrix_RFC.md`).

**Our target reality (what any candidate must survive):**
- Fork AP: **12.8 kHz**, **GDFT/Goertzel** front-end, **96-sample hop → 133.3 Hz** AP frame rate, **ESP32-class MCU**, **causal/real-time**. (Contrast: Synesthesia/Auto-BPM are 44.1 kHz, 2048-FFT, Apple vDSP, desktop CPU.)
- Fork current implementation to cross-check against (do not re-map from scratch — the audit already did):
  - `SPECTRASYNQ_K1_FIRMWARE/audio/sb_tempo.cpp` (confidence = `peak²/(peak²+Σ out-of-lobe)` @ line ~35; lock `0.60` @ line ~40; "lost on real music" admission @ ~line 50).
  - `SPECTRASYNQ_K1_FIRMWARE/audio/sb_onset_beat.cpp`, `sb_musical_saliency.{h,cpp}`.
  - Known-issues audit: `docs/forensics/tempo_tracking_refactor/2026-06-05-tempo-beat-onset-known-issues.md`.
- The evaluation gate (and its known limit): `scripts/regression-harness/` — `tempo_accuracy.py`, `beat_semantic_metrics.py` (real HarmonixSet WAVs + gold beat GT), `novelty_from_wav.py`, `tempo_replay.py`. **Documented blind spot:** the harness feeds `sb_tempo` a *modelled* scipy novelty, **not** the device GDFT/AGC front-end. Any front-end candidate is therefore **not** fully testable on the current gate — say so explicitly when it applies.

---

## 5. Method — the excavation pipeline

**Stage 0 — Authority map.** Read the prior-art audits (§4). Produce a short *do-not-repeat ledger*: what has already been adjudicated, which constants are misattributed (Davies/IBT/MIREX), and what authority questions remain open. Nothing downstream may contradict this without flagging it.

**Stage 1 — Excavate.** Enumerate every distinct AP design element across both corpora — algorithm, parameter, data structure, inter-module contract. Each gets a stable candidate ID (`CAND-NN`). No silent omissions: if you read it and skip it, it still gets a row with `REJECT` + reason.

**Stage 2 — Grade** each candidate on five axes (schema in §6):
1. **Provenance** — `VERIFIED-from-RE-source` / `RE-author-INFERRED` / `academic-or-misattributed`.
2. **Portability** to 12.8 kHz / GDFT / ESP32 / causal — `portable` / `portable-with-rederivation` / `desktop-only`. Reference *structure*, never paste *constants*.
3. **Keystone relevance** — does it touch "confidence reachable on real music," or is it orthogonal polish? (Most will be orthogonal.)
4. **Betterment hypothesis** — the **specific measurable AP outcome** it would improve (e.g. "Acc1 in-range", "beat-F", "onset precision/recall", "harmonic-axis liveness"). If you cannot name one, it is not a candidate.
5. **Gate-testability** — the falsifiable test on the HarmonixSet harness, *with* the front-end caveat stamped where it applies. Untestable ⇒ stays `[HYPOTHESIS]`.

**Stage 3 — Cross-check the fork.** For each candidate, state what the fork **already** does: nothing / a variant / the same thing. Kill any "discovery" of capability we already ship.

**Stage 4 — Test the testable.** For `PROMOTE-to-test` candidates that are host-only and non-destructive, run the specified harness test and record the result. If the harness is not runnable in your environment (off-mount gold GT) or the candidate needs firmware/device work, **specify-and-defer** — do not flash, do not touch device (§8).

**Stage 5 — Recommend.** Rank by leverage. For **both** recommends **and** rejects, give justification. Prepare a sit-down agenda: top promotes, "tempting but reject" items (with why), and the open authority questions only Captain can close.

---

## 6. Deliverable — the candidate register (schema)

A single markdown ledger, one row per candidate:

| Field | Content |
|---|---|
| `id` | CAND-NN |
| `source` | app + citation (file:line / section) |
| `ap_layer` | front-end / onset / tempo / beat / harmonic-saliency / contract / other |
| `what_it_is` | 1 line, plain |
| `provenance` | VERIFIED / RE-INFERRED / ACADEMIC-or-MISATTRIBUTED |
| `portability` | portable / rederive / desktop-only |
| `keystone_relevance` | direct / adjacent / orthogonal |
| `fork_current_state` | nothing / variant / already-have |
| `betterment_hypothesis` | the measurable AP outcome improved |
| `gate_test` | the falsifiable HarmonixSet test (+ front-end caveat if applicable) |
| `recommendation` | PROMOTE-to-test / REFERENCE-only / REJECT |
| `justification` | reasoning for the call (required for rejects too) |

Plus an **executive summary**: the do-not-repeat ledger (Stage 0), top ~5 promotes, top ~5 tempting-rejects, and the open authority questions for the joint session.

---

## 7. Hard prohibitions

- **Promote nothing to canonical.** Do not write any candidate into a reference doc, spec, config, or firmware as authoritative. The register is a *proposal*, not a decision.
- **Never paste desktop constants** (44.1 kHz / 2048-FFT / vDSP values) into the 12.8 kHz/GDFT/ESP32 pipeline.
- **Read-only on firmware and device.** No firmware edits, no flashing, no serial-write, no device tests. Host-harness only.
- **Do not re-litigate Synesthesia authority.** Surface the question; do not answer it.
- **Do not reimplement DSP** to "test" an idea in a way that forks logic — use the existing harness seams (the codebase already suffers from duplicated-logic / load-bearing-edge damage).
- **No git commits, tags, or pushes.**
- **Write scope:** you may create/modify **only** your register deliverable and your own working notes under `docs/research/`. Everything else is read-only.

---

## 8. Escalate to Captain (do not decide these yourself)

- Any **promotion to canonical** — all of it; that is the joint session.
- Any **authority/provenance ambiguity** (the "is this Synesthesia's or academic?" question).
- Any candidate that requires a **firmware change or device test** to evaluate.
- Any **contradiction** — corpus vs corpus, or corpus vs fork — that you cannot bound with evidence.
- Any **access gap** (RE path unreachable, Auto-BPM path unconfirmed, harness un-runnable).
- Any candidate whose **betterment cannot be tested** on the gate (so the promote decision is eyes-only).

---

## 9. Definition of done

The register exists; **every** AP-relevant element you read is graded (no silent omissions); rejects are justified; testable promotes have a result or an explicit specify-and-defer; the executive summary + sit-down agenda + open authority questions are prepared. You have promoted **nothing**. You have surfaced **everything**.

---

## 10. Report-back contract

- **Expected output:** the register file + executive summary, path reported back.
- **Checkpoint:** report progress at Stage-0-complete (authority map) and Stage-2-complete (all candidates graded) before running Stage-4 tests.
- **If blocked** (access/harness): report `blocked` with the specific cause and the partial register so far — do not silently stall, do not paper over with a workaround.
- **Consumption rule:** Captain consumes the register in a joint promotion session; no candidate is live until that session promotes it.
