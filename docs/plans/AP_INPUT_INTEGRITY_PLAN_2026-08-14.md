---
abstract: "End-to-end execution plan after the 2026-08-14 finding that the bench IM69D was read on the wrong PDM slot for ~9 days, invalidating every device-measured constant in that window. Five phases, each with a falsifiable oracle: P0 establish hardware truth (can KILL the diagnosis), P1 mic-health integrity gate (the permanent fix), P2 split the overloaded SSL into three derived values (the spastic fix) + a plate-level twitch oracle, P3 re-verify the colour lane selectively, P4 promotion. Four Captain gates total. Read the Rules of Engagement before executing any task."
---

# AP Input Integrity — end-to-end execution plan

**Created:** 2026-08-14 · **Bench:** K1v2 `B489A500` on `/dev/cu.usbmodem12401`
**Origin:** the wrong-PDM-slot finding (PR #62) and the plate measurements that refuted
"the audio front end is healthy".

---

## 0. Why this plan exists (one paragraph, read it)

A fortnight of colour work was measured through a microphone input that was reading a
channel with nothing on it. The fixes were reasoned from code and may well be correct; the
**measurements** taken in that window are not trustworthy. The deepest defect is not the
wrong slot — it is that **nothing in the system asks whether its input is real**. A dead
input presents as "a quiet room with a high floor", and the firmware calibrates around it
and carries on. Every symptom chased for days (calibration rejecting 112/112 frames,
silence never latching, a locked 115 BPM in a dead-silent room, the plate more active in
silence than with music) is downstream of that single gap.

## 1. Rules of engagement (binding on every task below)

1. **P0 is blocking.** No task in P1+ is valid until the hardware truth is written down and
   Captain-ratified. Measuring anything else first repeats the mistake this plan exists to
   correct.
2. **Every oracle must be shown to go RED.** A check never observed failing is not a check.
   Each task states its mutation: break the thing, watch the right test fail, restore.
3. **The plate is the deliverable.** AP telemetry alone misled for a full session. No task
   closes on AP numbers where a plate-level measurement is possible (see T2.4).
4. **One variable per measurement leg**, and re-assert measurement config after every
   reboot — firmware identity is bin × config blob × knob store × cal profile.
5. **Flash success = script exit code + a NEW epoch.** Never grep a gated pipeline.
6. **Calibration only after Captain's verbal silence confirmation.** Always. No exceptions.
7. **Production stays byte-inert** until P4. Prove it with
   `scripts/regression-harness/mic_stable_byte_gate.sh`, not by assertion.
8. **Record falsifications.** If a task's kill criterion fires, write it down and re-fork
   the plan rather than reinterpreting the result.

## 2. Captain gates (only four — everything else is autonomous)

| Gate | Where | What is being asked |
|------|-------|---------------------|
| **G1** | end of P0 | Confirm which microphones are populated/working on this board revision, and ratify the shipped slot. |
| **G2** | T1.3 | Product decision: what the K1 *does* when its microphone is unhealthy. |
| **G3** | T3.4 | ONE eyes-on of the colour lane on a verified-good input. |
| **G4** | T4.3 | Promotion sign-off + golden A/B (needs explicit esptool GO). |

Everything else — builds, flashes, measurement legs, ratchets, docs — is agent-autonomous.

---

## PHASE 0 — Establish hardware truth · BLOCKING

**Goal:** know, in writing, which physical microphone this board presents on which PDM
slot. **This phase can kill the current diagnosis** — that is its job.

### T0.1 · Read both channels simultaneously
- **Do:** flash `k1_bench_im69d_stereo` (exists; extends `k1_bench_im69d`). Capture both
  channels' raw int16 floor and their response to the lane stimulus
  (`stimulus_35s_30s.wav`) with the MacBook mic as an independent witness.
- **Reuse, do not rebuild:** `scripts/regression-harness/stereo_probe_decode.py`,
  `scratchpad/witness_ab.py` (resolves the witness BY NAME — its index shifts whenever a
  Bluetooth device connects, and one leg on 08-14 silently recorded the wrong device).
- **Oracle:** per-channel quiet floor and per-channel dB response to a witnessed room change.
- **KILL CRITERION (pre-registered):** if **both** channels show a plausible floor and a
  real response, the "one mic is dead/unpopulated" diagnosis is **REFUTED**. Stop, record
  it, and re-fork: the fault is then in slot *semantics* (driver-version inversion, as
  documented for the SPH0645 in `i2s_audio.h` ~L18-34), not in a dead part.
- **Owner:** orchestrator (device). **Effort:** ~1 h.

### T0.2 · Map slot → physical mic
- **Do:** reconcile T0.1 against the board strapping recorded in `constants.h`
  ("SELECT is hard-strapped on-board (IM1 HIGH / IM2 LOW)") and the PCB3 documentation.
- **Oracle:** a single unambiguous statement of the form *"IM<n> is populated and presents
  on slot <LEFT|RIGHT>; IM<m> is <absent|dead|present-but-unused>"*, supported by T0.1 data.
- **Trap:** the current LEFT default is inherited from the SPH0645, whose SELECT is tied to
  3V3 — a cross-hardware-era port that was never re-derived. Do not treat any inherited
  slot/pin value as truth for this board.
- **Owner:** delegable (analysis, read-only). **Effort:** ~30 min.

### T0.3 · Write it into the registry and make the slot explicit
- **Do:** record board revision → populated mic → slot in
  `docs/hardware/device-build-registry.md`. Replace the *implicit* slot default with an
  **explicit** `-DK1_MIC_IM69D_SLOT_<LEFT|RIGHT>` on every IM69D env, so no env ever again
  depends on a driver default.
- **Oracle:** a ratchet asserting every IM69D env carries exactly one explicit slot flag.
  **Mutation:** delete the flag from one env → test goes red.
- **Owner:** orchestrator (edits) + delegable (ratchet). **Effort:** ~1 h.

### 🚦 GATE G1 — Captain confirms the board truth and ratifies the shipped slot.

---

## PHASE 1 — Mic health integrity gate · the permanent fix

**Goal:** the system can tell when its own input is not a working microphone, and says so.
This is the highest-leverage item in the plan: it converts a failure class that cost ~9 days
into one that announces itself in seconds, and it protects every future bring-up.

### T1.1 · Derive the health criteria from measurement
- **Do:** on the confirmed-good channel, measure the quiet-room floor band and the
  response-to-stimulus band (witnessed). Derive: plausible floor range, minimum response,
  staleness window.
- **Oracle:** criteria stated as measured numbers with the capture that produced them —
  **never guessed constants.** (The SSL cal gates were SPH-domain constants carried into an
  IM69D chain and were structurally unreachable; do not repeat that.)
- **Effort:** ~2 h.

### T1.2 · Implement `K1_MIC_HEALTH_V1`
- **Do:** Core-0-safe, O(1) per frame, no heap/FS/serial in the hot path. Publish a health
  state + reason on the `[AP]` line and to a status surface.
- **States:** `OK` · `FLOOR_IMPLAUSIBLE` · `NO_RESPONSE` · `STALE_I2S` · `UNKNOWN` (boot).
- **Trap:** health must be computed from the **raw pre-gain samples**, not from any value
  the pipeline derives — a check reading a derived value inherits its blind spots.
- **Effort:** ~1 day. **Owner:** orchestrator (hot path).

### T1.3 · 🚦 GATE G2 — fault behaviour (Captain decision)
- **Options:** (a) telemetry only; (b) telemetry + refuse to calibrate; (c) b + a visible
  operator signal on the plate.
- **Recommendation: (b).** It cannot produce a false product behaviour, and it directly
  blocks the specific failure that wasted this fortnight — calibrating against a dead input.
  (c) needs a separate product-truth decision about what the plate is allowed to say.

### T1.4 · Prove the gate can fire
- **Do:** force each fault state on hardware — wrong slot (now trivially reproducible),
  and an induced stale-I2S condition.
- **Oracle:** each condition produces its **own** state and reason; `OK` is reported on the
  known-good channel. **This is a fault battery: cases expected to be RED must be observed
  going red**, or the gate is undemonstrated.
- **Effort:** ~half day.

### T1.5 · CI ratchet
- Pin: health is computed from raw samples; every state is reachable; the flag does not
  leak into shippable envs pre-promotion. **Mutation-verify each.**

---

## PHASE 2 — AP drive contract · the spastic fix

**Goal:** the drive represents the room. Quiet room ⇒ ~zero drive ⇒ dark plate, without
reinstating any dimming path.

### T2.1 · Split the overloaded value
`SWEET_SPOT_MIN_LEVEL` currently serves four incompatible roles: measured noise floor,
silence-gate input, drive subtrahend, and follower floor. One measurement, three derived
values:

| value | source | measured 2026-08-14 |
|---|---|---|
| `mic_noise_floor` | calibration, as measured | 52 |
| `drive_threshold` | floor × margin | needs ≈ 450 to behave |
| `silence_threshold` | its own derivation | (T2.2) |

- **Trap:** this is HF-49 already in the canon ("SSL is drive normaliser AND gate input —
  don't knob-tune hybrids"). Fix the structure; do not tune the hybrid further.
- **Effort:** ~1 day.

### T2.2 · Derive the margins from the measured bands
- Quiet vs music separate by roughly 20× at the plate-relevant statistic
  (`max_raw` p50 **50** quiet vs **948** music; `rms_raw` **0.0015** vs **0.0180**).
- **Oracle:** the chosen threshold sits between the measured bands **with both bands shown**.
  A threshold justified only by "it makes silence latch" is rejected — that is tuning to
  make a red light green.

### T2.3 · Decide go-dark: recommend NO new dimming path
`silent_scale` is pinned to 1.0f every frame by Captain's 2026-08-09 STANDBY_DIMMING strike.
With a correct `drive_threshold` the plate darkens because there is nothing to draw — dark
*because silent*, not dimmed by a timer. This respects the prior decision and reverses
nothing. **Do not reinstate dimming without a fresh Captain decision.**

### T2.4 · Build the plate-level twitch oracle ← *the missing instrument*
- **Do:** an automated leg that measures **LED behaviour**, not AP telemetry: lit-pixel
  count distribution and frame-to-frame delta, in silence and under music.
- **Why this is mandatory:** on 2026-08-14 the AP numbers looked healthy while the plate was
  0→128 lit in a silent room. **AP telemetry is not a proxy for the plate**, and every
  future perceptual claim must be gated on this.
- **Pass criteria (pre-registered):** silence ⇒ lit p50 ≈ 0 and small frame-to-frame delta;
  music ⇒ lit clearly above silence. Both measured in the same session.
- **Note:** the 1 Hz `[AP]`/HUEAUD cadence undersamples a 133 Hz loop by 133×. Either raise
  the cadence for the leg or use the render trace; do not draw motion conclusions from 1 Hz.
- **Effort:** ~1 day. **Owner:** delegable (harness) + orchestrator (criteria).

### T2.5 · Verify and ratchet
- Silence leg + music leg through T2.4. Mutation: revert `drive_threshold` to the raw floor
  → the twitch oracle must go red.

---

## PHASE 3 — Re-verify the colour lane on a real input

**Goal:** establish which colour-lane results survive, cheaply — not repeat the lane.

### T3.1 · Inventory what is actually suspect
- **Do:** list every colour-lane constant/threshold **derived from bench measurement**
  between 2026-08-05 and 2026-08-14. Code-reasoned fixes and palette-derived references are
  *not* suspect; device-measured numbers are.
- **Oracle:** each entry marked `code-reasoned` | `palette-derived` | `device-measured`.
  Only the last class needs re-derivation.
- **Owner:** delegable (audit, read-only). **Effort:** ~2 h.

### T3.2 · Re-derive only the device-measured entries.

### T3.3 · Full-axis metric legs
Per the existing promotion plan and HF-50: coverage · temporal stability (hue velocity) ·
silence rest · music coupling · brightness dynamics — modes 32 and GDFT, ≥2 palettes
including a flagged dark-attractor one. **Now including the T2.4 plate oracle.**

### T3.4 · 🚦 GATE G3 — ONE Captain eyes-on
One pre-registered look, one variable. Not a ladder.

---

## PHASE 4 — Promotion

- **T4.1** Close the five gates in `docs/forensics/colour-fix-promotion-plan-2026-08-13.md`.
- **T4.2** Byte-inertness proof + golden side-by-side (needs explicit Captain esptool GO).
- **T4.3** 🚦 **GATE G4** — promotion sign-off. Decide at the same time whether the
  `:tune` registry ships to production (currently bench-gated by design).

---

## PHASE 5 — Parked, with reasons (do not start these)

| Item | Why parked |
|---|---|
| Auto-sensitivity (`K1_MIC_AUTO_SENSE_V1`) | An adaptive gain loop on a drive chain that amplifies noise to full scale reduces predictability, and determinism is the stated goal. It also stalled mid-debug chasing a "gain chain ceiling" with `raw_i16_near=0` — a symptom shaped like the dead input just found. **Revisit only after P2, and re-check that hypothesis on known-good input first.** |
| IM73D deprecation cleanup | Its only auto-sense envs target a retired mic; fold into P4 housekeeping. |
| `:tune` in production | Deliberate decision at G4, not a default. |

---

## Effort summary

| Phase | Effort | Blocking? |
|---|---|---|
| P0 hardware truth | ~half day | **yes — everything** |
| P1 integrity gate | ~2 days | shipping |
| P2 drive contract | ~2–3 days | the visible symptom |
| P3 re-verify colour | ~1–2 days | promotion |
| P4 promotion | ~1 day + gates | — |

**Critical path to "Captain sees a good plate": P0 → P2 → T3.3 → G3.**
P1 is parallel to P2 and blocks *shipping*, not *seeing*.

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-08-14 | agent:claude-code | Created after the wrong-PDM-slot finding — five phases, four Captain gates, pre-registered kill criterion in P0, plate-level twitch oracle added as mandatory machinery. |
