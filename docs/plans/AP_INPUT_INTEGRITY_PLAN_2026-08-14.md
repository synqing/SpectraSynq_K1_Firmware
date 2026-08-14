---
abstract: "REV B (Captain conditional-GO amendments incorporated). End-to-end plan after the 2026-08-14 wrong-PDM-slot finding. P0's dead/unpopulated-capsule diagnosis is REFUTED; G1 was RATIFIED on 2026-08-15 with physical IM1 / SELECT HIGH / ESP-IDF RIGHT as the future programme source. Pre-P4 T0.3 bench/diagnostic explicit-slot work is complete and protected production environments remain byte-identical; production slot promotion remains held until P4."
---

# AP Input Integrity — end-to-end execution plan · **REV B**

**Bench:** K1v2 `B489A500` on `/dev/cu.usbmodem12401`
**Authorisation:** `CONDITIONAL_GO_P0_MEASUREMENT_ONLY` (Captain, 2026-08-14).
Authorised and complete: **P0.0 · T0.1 · T0.1b · T0.2 · G1 · T0.3**. Captain authorised
Rev-B correction plus P1/P2 execution on 2026-08-15. Held: every production-environment
slot or health-default change until **P4**.

---

## 0. Why this plan exists

A fortnight of colour work was measured through an unintended physical capsule selected
under ambiguous, inherited slot naming. Both capsules are alive. The affected measurements
did not establish whether the selected input was suitable or acoustically responsive before
calibration and promotion. The deepest defect is therefore not a missing capsule — **the
system had no independent way to validate the identity, suitability and integrity of its
selected input**.

Ratified causal constraints for all later phases:

```text
DEAD_MIC_DIAGNOSIS                      = REFUTED
ALTERNATE_LIVE_CAPSULE_IS_HEALTH_FAULT = FALSE
AP_CONTRACT_VALUE_ROLES                 = 4
```

P1 detects transport/raw-integrity failures and challenge-proven liveness failures. Merely
selecting IM2 instead of the ratified IM1 programme source is a source-selection error, not a
microphone-health failure.

**Rev B exists because the first revision could have produced another convincing false
PASS.** Each amendment below closes a route by which a *new* instrument could be fooled by
the same class of ambiguity.

## 1. Rules of engagement (binding)

1. **P0 is blocking.** Nothing in P1+ is valid until hardware truth is ratified at G1.
2. **Every oracle must be shown to go RED**, via the mutation named in its execution-matrix
   row. A check never observed failing is not a check.
3. **The plate is the deliverable.** No task closes on AP telemetry where a render-output
   measurement is possible.
4. **One variable per leg**; re-assert measurement config after every reboot (identity is
   bin × config blob × knob store × cal profile).
5. **Flash success = script exit code + NEW epoch.** Never grep a gated pipeline.
6. **Calibration only after Captain's verbal silence confirmation.** Always.
7. **Production byte-inert until P4** — proven with `mic_stable_byte_gate.sh`, never asserted.
8. **Record falsifications**; re-fork rather than reinterpret.
9. **(Rev B)** Until `K1_MIC_HEALTH_V1` is operational, **every** P2/P3 capture receipt must
   open with a witnessed input challenge and carry `INPUT_SOURCE_PROVEN`, `SLOT_MAPPING`
   and `CAPTURE_EPOCH`. A capture without that header is inadmissible evidence.
10. **(Rev B)** Never infer physical population from software array activity. See T0.1b.

## 2. Captain gates (four)

| Gate | Position | Decision |
|---|---|---|
| **G1** | after T0.2, **before** T0.3 | **RATIFIED 2026-08-15** — IM1 / ESP-IDF RIGHT. |
| **G2** | T1.3 | Runtime behaviour on invalid input (see §P1). |
| **G3** | T3.4 | ONE pre-registered eyes-on. |
| **G4** | T4.3 | Promotion sign-off, production slot enablement, `:tune` decision. |

## 3. Execution matrix (the machine-readable contract)

Every task carries these fields. Rows marked ⚠ were under-specified in Rev A.

| Task | Input identity | Oracle | RED witness | GREEN witness | Kill condition | Owner |
|---|---|---|---|---|---|---|
| P0.0 | n/a | manifest completeness vs epoch scan | an artefact from a bad epoch absent from the manifest | every bad-epoch artefact dispositioned | — | delegable |
| T0.1 | stereo env + epoch | per-channel floor + witnessed response | — | both channels characterised | — | orchestrator |
| T0.1b | as T0.1 | **independence** (static slot chain first; raw acoustic crossover only if still ambiguous) | swap decoder mapping ⇒ data must change | each slot uniquely attributable | ambiguous ⇒ agent-controlled raw-stereo capture, then electrical probe | orchestrator |
| T0.2 | T0.1b receipts | unambiguous slot↔mic statement | — | statement supported by data | contradicts strapping doc ⇒ escalate | delegable |
| T0.3 | bench envs only | ratchet: every IM69D env has exactly one explicit slot flag | delete a flag ⇒ red | all bench envs explicit **and** production byte-identical | production byte delta ≠ 0 ⇒ STOP | orchestrator |
| T1.2 | health build | raw-integrity states reachable | force each fault ⇒ its own state+reason | OK on known-good channel | — | orchestrator |
| T1.4 | health build | full fault battery §P1.4 | each battery case ⇒ expected state | no false positive on quiet room or low-level music | false positive ⇒ criteria re-derive | orchestrator |
| ⚠T2.2 | discovery capture | threshold sits outside both distribution tails | threshold inside a tail ⇒ red | validated on **held-out** capture | tails overlap ⇒ rms alone insufficient, use joint | orchestrator |
| T2.5 | render-output oracle | §T2.4 numeric criteria | pre-fix config **and** re-inserted mutation | post-split config | — | orchestrator |
| ⚠T3.1 | epoch manifest | every consumer of a bad-epoch artefact dispositioned | a live consumer with no disposition | manifest closed | — | delegable |
| ⚠T3.3 | verified-good input | full-axis + render-output metrics | prior config red | all axes pass | any axis red ⇒ no G3 | orchestrator |

---

## PHASE 0 — Hardware truth · BLOCKING · **authorised**

### P0.0 · Freeze and quarantine the contaminated evidence epoch ← *new in Rev B*
Anchor to the first known-bad **firmware/config epoch**, **not** the calendar range
2026-08-05..14. Calendar ranges miss constants copied later, cherry-picked values,
cal profiles generated inside the window, conclusions transferred into docs, and golden
artefacts still referenced elsewhere.

Manifest schema (one row per artefact):
```
artefact | originating build/config epoch | contamination mechanism |
current consumers | disposition: TOMBSTONED | RE-DERIVED | UNAFFECTED | replacement evidence
```
Quarantine or visibly tombstone: raw measurement files · derived constants · calibration
profiles · benchmark summaries · device-derived claims · golden screenshots/traces ·
documentation statements resting on them.

**Code-reasoned fixes do not require re-derivation, but every touched behaviour still needs
its acceptance rerun** — a sound code argument does not prove the fix behaved correctly on
a real input. This is where the project either breaks the
*carried-and-labelled becomes carried-and-trusted* pattern or repeats it.

### T0.1 · Simultaneous stereo capture
Flash `k1_bench_im69d_stereo` (exists). Capture both channels' raw floor and response to
`stimulus_35s_30s.wav`, witnessed by the MacBook mic (**resolved BY NAME** — its index
shifts on Bluetooth connect; one 08-14 leg silently recorded the wrong device).
Reuse `scripts/regression-harness/stereo_probe_decode.py`, `scratchpad/witness_ab.py`.

### T0.1b · Channel-**independence** proof ← *new in Rev B*
> Rev A's kill criterion ("both channels respond ⇒ diagnosis refuted") is **too weak**.
> Both decoded channels can look plausible while only one real source exists: duplicated
> DMA/de-interleave output, slot-decoder leakage, one mic appearing in both arrays,
> inter-slot crosstalk, decoder semantic inversion, or a capture script reusing a channel.

Required receipts, as amended by Captain on 2026-08-15:
1. **Duplication check** — sample-by-sample equality/offset-copy test between arrays.
2. **Independence** — inter-channel correlation/coherence across silence *and* stimulus.
3. **Static physical-to-digital chain** — PCB SELECT strapping → IM69D SELECT convention →
   exact active-driver slot semantics → decoded PCM ordering.
4. **Decoder-mapping swap** — changing the mapping must change the **expressed result**,
   not merely relabel identical data.

If and only if those receipts do not produce one unambiguous mapping, run one
agent-controlled simultaneous raw-stereo capture with two directed source placements: IM1,
then IM2. The agent calculates matched-window RMS, dominance ratio, duplication,
correlation and clipping. Captain is not the measurement instrument and is not asked to
infer identity from Primary versus Secondary plate behaviour.

Acoustic occlusion is not a baseline requirement. It is an optional fallback only when the
raw-channel crossover remains ambiguous and the additional ambiguity it resolves is stated
before the test. The plate remains an end-to-end render-output oracle, but it has no
identifying power for mic-to-slot mapping because both render channels consume shared audio
features.

**Oracle (replaces Rev A's):** *each decoded slot has been shown to correspond uniquely to
a physical source, OR the unused slot has been shown to contain no independent microphone
signal.* If ambiguous: inspect the PDM data electrically, or re-fork into the
driver-semantics lane (the SPH0645 inversion documented at `i2s_audio.h` ~L18-34).

### T0.2 · Physical mic ↔ slot mapping
Reconcile T0.1b against the board strapping ("SELECT hard-strapped IM1 HIGH / IM2 LOW") and
PCB3 documentation. Output one unambiguous statement.
**Trap:** the current LEFT default is inherited from the SPH0645 (SELECT tied 3V3) — a
cross-hardware-era port never re-derived. No inherited slot/pin value is truth for this board.

### 🚦 G1 — **RATIFIED 2026-08-15**

Authority: `docs/forensics/G1_AP_INPUT_SLOT_RATIFICATION_2026-08-15.md`.
No further physical microphone test is authorised.

### T0.3 · Make the slot explicit — **two-stage** ← *amended in Rev B*

**Pre-P4 stage: COMPLETE 2026-08-15.** Receipt:
`docs/forensics/G1_AP_INPUT_SLOT_RATIFICATION_2026-08-15.md`.
Rev A conflicted with Rule 7: "every IM69D env gets the correct explicit flag" cannot
co-exist with production byte-inertness if the correct slot ≠ the current production default.

**Before P4:** bench/diagnostic IM69D envs made explicit; ratchet added for those envs;
production change **prepared but promotion-gated**; existing production env **proven
byte-identical**. If an explicit flag compiles byte-identical because it matches the
current default, **demonstrate that with the byte gate** rather than assuming it.
**At P4:** enable the explicit production slot; run byte-delta/golden comparison; treat the
slot correction as the only authorised production audio-input delta alongside health.

G1 has passed. T0.3 may change bench/diagnostic configuration only; it does not authorise
any production slot change or promotion.

---

## PHASE 1 — Mic health · **two contracts, not one** ← *restructured in Rev B*

> A dead microphone and an acoustically silent room are **observationally equivalent**. A
> runtime system cannot conclude "no response" merely because nothing happened recently.

### T1.1a · Raw-stream integrity — continuously evaluable, no stimulus required
I2S freshness · stuck samples · impossible rails/DC · implausible floor statistics ·
repeated buffers · impossible entropy/variance · decoder/data-path discontinuity.

### T1.1b · Acoustic liveness — **proven only after a known excitation**
Controlled lane stimulus at bring-up · explicit diagnostic challenge · (optionally) a
sufficiently unambiguous real-world transient, if production policy allows.

**State semantics:**
```
UNKNOWN / LIVENESS_UNPROVEN   RAW_IMPLAUSIBLE   STALE_I2S   LIVENESS_PROVEN   OK
```
`NO_RESPONSE` is **redefined**: *a known challenge occurred and the microphone failed to
exhibit the required response.* It must **never** mean *the room has been quiet.*
Liveness proof is **per boot or per capture epoch**.

Health is computed from **raw pre-gain samples** — a check reading a derived value inherits
its blind spots.

### T1.2 · Implement `K1_MIC_HEALTH_V1`
Core-0 safe, O(1)/frame, no heap/FS/serial in the hot path. Publish state + reason on `[AP]`
and a status surface.

### T1.3 · 🚦 G2 — runtime behaviour on invalid input ← *expanded in Rev B*
**Captain's selection: (b) expanded.** Telemetry/status reason **+ refuse calibration
+ invalidate audio-derived feature publication while health is invalid.** A gate that logs
an error while continuing to publish invalid features reproduces the same pathological plate.

Downstream behaviour:
- do not publish new audio features as valid;
- drive audio-reactive energy to zero after a **bounded debounce**;
- do not hold stale tempo/chromagram/onset values indefinitely;
- leave non-audio modes and control operation unaffected;
- **no special plate fault animation in this lane**;
- expose the fault via AP/status/controller surfaces;
- resume only after raw integrity is restored **and** liveness re-established.

This is **fail-closed suppression of invalid input**, not a reinstatement of standby dimming.

### T1.4 · Fault battery ← *expanded in Rev B*
boot→OK · OK→fault · fault→recovery · short-transient rejection · **genuinely quiet room
(false-positive)** · **low-volume music (false-positive)** · repeated-buffer / stale-DMA ·
**CPU-cycle and loop-budget impact**.

**Cross-unit constraint:** a permanent product health classifier must not be promoted from
one B489A500 floor range. B489A500 establishes the bench implementation; **production
thresholds must be conservative impossible-state checks or receive cross-unit validation
before shipping.**

---

## PHASE 2 — AP drive contract · **four values** ← *corrected in Rev B*

Rev A listed four roles but only three replacements, leaving the old coupling a route to
survive under a new name. All four are defined explicitly, even if two later prove equal:

```
mic_noise_floor      drive_threshold      silence_threshold      follower_floor
```

Each requires: **source statistic · units/domain · derivation · valid range · consumer list
· reset/update policy · calibrated|fixed|derived · an assertion preventing cross-use.**
Names should carry units/domain where ambiguity is possible — a normalised RMS threshold and
an integer raw-peak threshold must not look interchangeable in code.
**No alias may be introduced merely because two values are numerically equal on one capture.**

### T2.2 · Threshold derivation from **distributions** ← *amended in Rev B*
Medians are insufficient. Use: quiet **p95/p99** · low-level-music **p05/p10** ·
ordinary-music distribution · **at least one held-out capture not used to choose the value.**

```
discovery capture → choose derivation/margin → FREEZE → independent validation capture → mutation test
```
**Do not tune and validate against the same trace.** Include a **low-level music leg**: a
threshold can make silence beautifully dark while silently deleting quiet programme material.

### T2.3 · No new dimming path
`silent_scale` stays pinned (Captain 2026-08-09). With a correct `drive_threshold` the plate
darkens because there is nothing to draw. Do not reinstate dimming without a fresh decision.

### T2.4 · **Render-output oracle** ← *renamed + numerically defined in Rev B*
Primary authority: the **final render buffer immediately before LED transmission** — what
the plate was commanded to display, avoiding AP-proxy error. It is a **render-output
oracle, not a physical-light oracle**; G3 eyes-on (or a camera capture) remains the
authority for optical appearance.

Freeze numerically: capture point · duration + warm-up · effective frame rate · mode,
palette, brightness, knob state · per-pixel luminance/channel threshold defining "lit" ·
frame-to-frame delta definition · silence **p50/p95** limits · music-vs-silence separation ·
permitted boundary transitions · whether first post-mode-change frames are excluded.

**Test order (RED first):**
```
1 run the CURRENT bad configuration → observe RED
2 apply the structural split
3 observe GREEN
4 re-insert raw-floor-as-drive-threshold → observe RED again
```

---

## PHASE 3 — Re-verify the colour lane

**T3.1** consumes the **P0.0 epoch manifest** (not a calendar scan). Disposition every
artefact; re-derive only `device-measured` entries; rerun acceptance for every touched
behaviour regardless of provenance.
**T3.3** full-axis metrics (coverage · temporal stability · silence rest · music coupling ·
brightness dynamics), modes 32 and GDFT, ≥2 palettes incl. a flagged dark-attractor one,
**plus the T2.4 render-output oracle**, all under Rule 9 capture receipts.
**T3.4 · 🚦 G3** — one pre-registered eyes-on.

## PHASE 4 — Promotion

**T4.1 — pin the dependencies** ← *new in Rev B*: a mutable pathname is not promotion
authority. Pin the referenced promotion plan's **commit hash**, the **gate identifiers**,
expected artefacts and exact required results, before P4 starts.
**T4.2** production slot enablement + health enablement + byte-delta/golden A/B (explicit
Captain esptool GO).
**T4.3 · 🚦 G4** — promotion sign-off + `:tune` production decision.

## PHASE 5 — Parked, with reasons

| Item | Why |
|---|---|
| Auto-sensitivity | Adaptive gain on a chain that amplifies noise to full scale reduces predictability; determinism is the goal. Stalled chasing a "gain chain ceiling" with `raw_i16_near=0` — a symptom previously misclassified under the now-refuted dead-microphone diagnosis. Revisit after P2, re-checking that hypothesis on known-good input. |
| IM73D deprecation cleanup | Its only auto-sense envs target a retired mic; fold into P4 housekeeping. |
| `:tune` in production | Decided at G4. |

## Critical path

`P0.0 → T0.1 → T0.1b → T0.2 → G1 → T0.3 → P2 → T3.3 → G3`
P1 runs parallel after G1 and blocks **shipping**, not **seeing** — with Rule 9 receipts
standing in for it until it is operational.

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-08-15 | Captain / agent:codex | G1 ratified: both capsules alive; IM1 / SELECT HIGH / ESP-IDF RIGHT / PCM 0 chosen as the future programme source; T0.3 bench work authorised with production held byte-inert until P4. |
| 2026-08-15 | agent:codex | Captain amendment: static slot chain is primary; raw-stereo near-field crossover only if ambiguity remains; plate comparison removed from slot identity; occlusion made optional fallback. |
| 2026-08-15 | Captain / agent:codex | Corrective execution authorised: freeze the dead-mic refutation, exclude the alternate live capsule from P1 fault semantics, retain four AP roles, and execute P1/P2 without a production change. |
| 2026-08-14 | agent:claude-code | Created — five phases, four gates, P0 kill criterion, plate oracle. |
| 2026-08-14 | agent:claude-code | **REV B** — Captain conditional-GO amendments 1-11: P0.0 epoch-anchored quarantine; T0.1b channel-independence proof; G1 moved before T0.3; T0.3 split so production stays byte-inert; health split into raw-integrity vs challenge-based liveness with NO_RESPONSE redefined; G2 bound to fail-closed feature suppression + expanded battery + cross-unit constraint; AP contract restored to four values; distribution-tail thresholds with held-out validation and a low-level-music leg; render-output oracle numerically defined with RED-first ordering; promotion dependencies pinned; execution matrix added. |
