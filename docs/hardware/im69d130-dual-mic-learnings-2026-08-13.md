---
abstract: "THE canonical end-to-end synthesis of everything learned about the dual IM69D130 microphone system (2026-08-05 → 2026-08-13): hardware topology and straps, the IM73D false-authority saga and quarantine, the RMS-cannot-separate finding, the joint crest×level silence gate and its 1.25→2.50→1.75 derivation saga, the calibrate-at-final-placement transfer rule, Stage 1b/Stage 2 dual-capsule results (H_C rejected — stereo visuals would be synthesised; H_C2 coherence is the real second-capsule value), consumer floors and profile 2, P5.B visual-pipeline proofs, method lessons, and open debt. Read this before ANY IM69D work; per-event receipts are linked, not duplicated."
---

# Dual IM69D130 — end-to-end learnings

> **P0.0/G1 correction (2026-08-15):** B489 absolute-level/calibration/silence measurements,
> cross-unit amplitude ratios and profile-wide thresholds require re-derivation. Static and
> programme-relative findings are not automatically invalidated. G1 maps ESP-IDF RIGHT to
> physical IM1 and stereo index 0; LEFT to physical IM2 and index 1. See
> `docs/forensics/P0_0_AP_INPUT_QUARANTINE_MANIFEST_2026-08-15.md`.

**Consolidated 2026-08-13** from the 2026-08-05 → 2026-08-13 programme (design → bring-up →
identity correction → gate derivation → transfer test → dual-capsule → floors → visual proof).
This is the synthesis document; every claim links to its receipt. Merged evidence: PR #43, #44, #45.

---

## 0. The one-paragraph version

The K1 bench fleet runs Infineon **IM69D130** PDM MEMS microphones — two capsules per board,
SELECT-strapped to opposite PDM slots. On this microphone, **RMS cannot distinguish music from a
room's noise floor** (music's median RMS reads *below* ambient's), so silence detection was
rebuilt as a **joint crest×level gate** (peakiness ≥ 2.10 AND level ≥ SSL × 1.75), scoped to
IM69D builds only. The gate's level fraction **transfers between units once each unit is
calibrated at its final placement** — the apparent per-unit difference was a stale-calibration
artefact. The second capsule **cannot deliver sensed stereo visuals** (inter-channel correlation
≥ 0.97 across the visual-driving bands at product SPL); its real value is **coherence-based
robustness** (music vs handling-noise/occlusion discrimination). All consumer floors are now
measured on IM69D silicon and carried by `K1_AUDIO_PROFILE_IM69D130_UNIT2`.

---

## 1. Hardware truth

### 1.1 The microphone

- **Part:** Infineon XENSIV IM69D130, digital PDM output, mono per capsule, slot selected by a
  hardware **SELECT** pin (SELECT=GND → LEFT half-period, SELECT=VDD → RIGHT).
- **Clocking:** the IM69D path runs **`I2S_PDM_DSR_16S` → 1.6384 MHz PDM clock** at the 12.8 kHz
  build-contract sample rate. The legacy IM73D path ran DSR_8S (819.2 kHz), which sits at or
  below the bottom of the normal XENSIV operating-clock range — **do not assume the IM69D
  tolerates sub-MHz clocking**; it was never run there.
- **Input gain:** `K1_MIC_IM69D_INPUT_GAIN` — Phase 0 proved silence latch at **G=4** on the
  bench (SSL=74); Unit 2 ships **G=8**. History lesson: the earlier 16→8→4 gain ladder was
  aimed at `threshold_loud_break`, a symbol with **zero read sites** — gain was halved twice to
  move a number that did nothing (see §8, dead-symbol lesson).

### 1.2 Board topology (two distinct hosts — never conflate)

| | **Bench K1v2 (`B489A500`)** | **Bench Unit 2 (`0C54FC00`)** |
|---|---|---|
| Mic board | PCB3 dual-IM69D on the SPH pads | dual IM69D130, Data+CLK-only board |
| PDM pins | **CLK=GPIO14 / DATA=GPIO13** | **CLK=GPIO39 / DATA=GPIO38** (CAPTAIN_PIN_AUTH 2026-08-11) |
| Slot in use | LEFT (mic A) default; RIGHT (mic B) proven Stage 1b | **RIGHT** (explicit — the init `#error`s without a slot under `K1_UNIT2_IM69D_V1`) |
| SELECT | **Hard-strapped on-board with 0 Ω resistors** — IM1 HIGH (R7→PWR_1V8), IM2 LOW (R14→GND); R9/R13 DNP. Slots are opposite **by construction**; mono-A vs mono-B is purely a software `slot_mask` choice | Static hardware truth, **never firmware-driven**; GPIO12 is an escape-hatch pin only |
| LEDs | 160/160 | dual **206**-px WS2812B on GPIO 4/5, render canvas 160 |
| Envs | `k1_bench_im69d`(_ble/_micb/_stereo) | `k1_unit2_im69d_right`(_led160ab/_matrix) |

**Load-bearing rule:** identity is chip-ID/MAC, never port; both units are ESP32-S3 devboards
but their **GPIO maps differ — never cross-flash**. `SELECT` is decided by copper, not code —
the IM73D habit of driving an LR pin does not exist on the IM69D path.

### 1.3 What is still physically unproven

- **Unit 2's own dual-capsule topology** — only its RIGHT capsule path is evidenced. Stage 1b
  proved the **bench's** mic B. No complementary-SELECT measurement, shared-DATA contention
  proof, or per-capsule supply record exists for Unit 2's board.
- **Capsule spacing D** (design O-4) — unmeasured on both boards; a formality for interpreting
  ρ physically, not a blocker for the verdict in §6.

---

## 2. The identity saga — how the wrong mic got into the build, and the quarantine

**The defect chain:** `[env:k1_custom] extends = env:k1_bench_im73d_ble` compiled
`K1_MIC_IM73D_PDM_V1` — an **IM73D122** build — onto Unit 2, whose physical mic is dual
IM69D130. Every "Unit 2" measurement taken under that binary (2026-08-09 silence floors, tempo
lock 0.28, novelty ×4, M18 receipts) was **evidence under a poisoned mic premise**.

**Captain correction 2026-08-10:** Unit 2 = dual IM69D130; IM73D **deprecated**; the
inheritance is **false authority**. Resolution ran the runbook: pin receipt under
`CAPTAIN_PIN_AUTH` (CLK39/DATA38 RIGHT proven functional) → retarget to a purpose-built env
`k1_unit2_im69d_right` → **P2.B quarantine** (closed 2026-08-12):

- The Aug-9 IM73D consumer scars were **tombstone-deleted from executable source** (silence
  0.001/0.003, lock 0.28, REL 0.18, novelty ×4, effect lock-gate 0.55) with tripwire tests
  against reinstatement. Verdict: **zero IM73D-measured consumer values remain reachable**;
  surviving `K1_MIC_IM73D_PDM_V1` sites are driver/pins/cal-namespace/guard infrastructure in
  archive envs only. Inventory: `docs/forensics/audio-profile/2026-08-12-im73d-scar-inventory-p2b.md`.
- `k1_custom` recomposed onto `k1_bench_im69d_ble`; still guard-BLOCKED until a physical device
  is nominated and its mic receipted.

**The structural lesson (now enforced):** the IM73D constants escaped because they were **gated
on a mic flag, not on the unit they were measured on** — they reached eleven environments
including one named "prod". Its descendants: the fail-closed audio-profile guard
(`k1_audio_profile.h` — an uncharacterised mic is a **compile error**, not a silent SPH
fallback), and the binding rule that **floors are measured on the silicon they ship on,
calibrated at final placement — never ported, seeded, or "sanity-checked" across mics.**

---

## 3. The central DSP finding — RMS cannot separate music from a room on this mic

Measured on IM69D silicon (bench, G=4; `FINDING-rms-cannot-separate.md`):

| statistic | quiet ambient | music |
|---|---|---|
| `rms_raw` p50 | 0.0072 | **0.0027** |
| `rms_raw` p95 | 0.0085 | 0.0171 |
| `rms_raw` max | 0.0092 | 0.0289 |

**Music's median RMS is LOWER than ambient's** — in both pre- and post-gain domains. Mechanism:
the room floor is dominated by **narrowband hum, crest ≈ 1.26** (RMS ≈ peak), while music is
peaky, **crest ≈ 3–5** (RMS ≪ peak). RMS is the one statistic on which steady hum *beats*
music. Consequences:

- The legacy SPH-style RMS Schmitt (enter 0.04 / exit 0.08) **can never fire** on this mic —
  the highest `rms_raw` ever observed (0.0364–0.0386) sits ~2.2× *below* the exit threshold.
- No RMS threshold fixes this at any gain, in any domain — it is a **shape** problem, not a
  level problem.
- Therefore silence detection on IM69D uses the **joint gate** (§4); SPH0645 production keeps
  its own HarmonixSet-calibrated Schmitt, untouched.

---

## 4. The joint silence gate — design, derivation saga, and the transfer rule

### 4.1 The mechanism (shipped, IM69D-scoped)

```
break_silence  =  (pky  ≥ K1_SILENCE_PEAKINESS_BREAK  [2.10])        — crest term
             AND  (max_raw ≥ SSL × K1_SILENCE_JOINT_LEVEL_SSL_FRAC [1.75])  — level term
```

**Both terms are required.** Measured: 42% of quiet frames clear the crest threshold unaided —
the level term rejects them; loud narrowband hum clears any level — the crest term rejects it
(hum crest 1.26 < 2.10, structurally). `pky` is a windowed max/mean peak ratio; `SSL`
(`SWEET_SPOT_MIN_LEVEL`) is the calibrated noise floor.

**SSL semantics (frequently misread):** SSL is *subtractive and a divisor floor* —
`drive = clamp0(peak − SSL) / max(follower, SSL)`. Signal below SSL is **annihilated, not
attenuated**. This is why every ratio in the system shifts when SSL is wrong (§4.2).

**Scoping:** the decision path compiles **only under `K1_MIC_IM69D_PDM_V1`**. It was originally
gated on *nothing* and compiled into every env including SPH production — one degree worse than
the IM73D escape (§2). Now pinned by `test_joint_silence_gate_is_scoped_to_im69d` plus a
behavioural table gate (`tests/test_im69d_consumer_floors_behavioural.py`) that live-parses the
constants and evaluates hum-rejection / quiet-transient / wake-margin cases, with a
usable-window ratchet (1.03 < FRAC < 2.13).

### 4.2 The fraction saga: 1.25 → 2.50 → 1.75 (the most instructive arc of the programme)

1. **Seed 1.25** derived on the bench (canon 2026-08-07), comment: *"per-unit, per-room — do
   not inherit."*
2. Unit 2's derivation produced **2.50** — double. Hypotheses, in suspicion order: LED-current
   coupling (206 px ≈ 29% more current), capsule sensitivity, PDM routing, stale calibration.
3. **Transfer test (full gamut, both units side-by-side):** music response statistically
   **identical** (ratio 0.92, p=0.67, n=179/side) — the delta lived **only in the quiet state**
   (Unit 2 quiet 1.54× hotter). LED-current ruled out *within-device* by a 320 px/412 px A/B.
4. **The discriminator:** predicted SSL-staleness factor from the quiet/music contrast = 1.67×.
   In-situ recalibration under Captain silence-go: **SSL 136 → 229 = 1.68×.** Prediction made
   *before* touching the calibration. Unit 2's SSL had been learned at its **previous placement**
   (boards >1 ft apart) and never re-learned after the move.
5. Final recalibration of **both** units under verified true silence (the leftover `pio` build
   fan — the agent's own process — had contaminated earlier "quiet" legs at −63.5 dBFS; killed,
   witness −68.2 dBFS mean, zero frames above −50 dBFS): **SSL 167 (Unit 2) / 187 (bench)**,
   both `cal_source=measured`, within 12% of each other.
6. **Re-derivation at true calibration:** usable window = worst quiet p95 (**1.03×SSL**) to
   worst music p25 (**2.13×SSL**). Shipping value **1.75** — ~70% above the quiet ceiling,
   ~18% under the music floor, deliberately more willing to wake than the rescaled old value
   (2.04) because low-volume music sat marginal. Both units then held silence **100%** under
   true silence and **0%** under music — the first clean 100% of the programme. **Captain
   eyes-on PASS at 1.75.**

### 4.3 The corrected transfer rule (supersedes "per-unit, do not inherit")

> **Calibrate at final placement; the fraction then TRANSFERS.** Placement is carried by SSL —
> which is exactly what SSL is for. A per-unit constant was being used to compensate for a
> stale per-placement calibration.

Corollary (HF-40): recalibrate only when **gain, mic identity, pin map, or placement** changes —
and *placement* is the one that was being forgotten.

### 4.4 Wake/drain behaviour at product SPL (P5.B, canonical fixture)

- **Wake:** 100% of frames awake at Bose vol 40/55/70 — no fails-to-wake margin at any tested
  product volume (`max_raw` med 2.2× / 5.5× / 11.7× SSL).
- **Drain (music stop → silence latch):** **9.1 s** at product SPL — inside the pre-registered
  15 s bound. An earlier 18.6 s "failure" was **fixture-induced** (weak laptop stimulus +
  ambient resetting the dwell). Residuals that are real: sparse post-latch output flashes
  (pmax 37–38 at ~15/19 s) and an 18/21 (DF-secondary) drain that did not latch within 25 s —
  both filed under the **dwell/persistence gate debt** (recommended, still unimplemented).

---

## 5. Calibration & measurement discipline (what the mic taught us about measuring it)

- **The room is part of the instrument.** Two separate contaminations were caught by the
  independent witness mic (laptop, resolved **by name** every run — ffmpeg avfoundation indices
  shift on Bluetooth connect/disconnect): the agent's own build-fan (−63.5 dBFS "quiet"), and
  typing transients resetting silence dwell during drain measurement.
- **The 5× SPL trap is real and now numeric:** laptop speakers @100% (witness −48 dBFS) left
  Unit 2 **silence-latched for 75% of music frames** — tempo conf/lock collapse to zero and any
  floor derived from such a leg is garbage. Product-SPL evidence comes from the Bose.
- **The canonical stimulus fixture is `~/Music/PioneerDJ/Demo Tracks/Demo Track 1.mp3`**
  (the `transfer_leg.py` default; every verified leg used it). An ad-hoc track pick during the
  2026-08-13 session was caught by Captain and corrected; both leg runners now default to the
  canonical. An ambient/beatless track additionally skews tempo-lock statistics low.
- **Cal namespace isolation prevents cross-poisoning:** IM69D persists to
  `/cal_profile_im69d.bin` + `CONFIG_IM69_*`; IM73D used `/cal_profile_pdm.bin`. A shared file
  is the poison-cal blast radius. Both mic flags together are a compile error.
- **`start_noise_cal` is Captain-verbal-gated, always** (N then Y hotkeys; the typed command is
  disabled). The entire 2026-08-12/13 device campaign ran **zero** calibrations — raw
  pre-conditioning telemetry (`raw_i16_*`) needs no cal, which is why Stage 1b/2 could run
  freely.

---

## 6. The dual-capsule question — answered

### 6.1 Stage 1b — both capsules independently alive (bench)

`k1_bench_im69d_micb` (= base + `-DK1_MIC_IM69D_SLOT_RIGHT`): boot banner
`I2S PDM RX INIT: PASS slot=RIGHT`; quiet floor rms 7–10 (peak ≤ 21, far from the 30 000
near-rail); 100%-volume noise burst → rms 10 → **55** (5.5×), peak 19 → **192**, clean return
to floor. **A live RIGHT-slot read with real acoustic response is itself the strap-topology
proof** — an absent or LEFT-strapped mic B would read zeros. G4 (both mics proven
independently) closed: mic A/LEFT had run every prior leg. Receipt:
`docs/forensics/im69d-stage1b-stage2-2026-08-12/stage1b-receipt.md`.

### 6.2 Stage 2 — the stereo instrument

`k1_bench_im69d_stereo` (`-DK1_MIC_IM69D_STEREO_V1`): both slots read as interleaved L/R int16;
**the DSP chain still consumes LEFT only** (behaviour Stage-1-identical); RIGHT exists purely
for measurement. Capture instrument per the telemetry discipline (arm→tick→dump, never live
printf on the audio path): 24 s PSRAM ring (2.4 MB), O(n) memcpy per chunk, CRC32-framed hex
dump over `:scap_arm/:scap_status/:scap_dump` (CMD_HARNESS), offline decoder
(`stereo_probe_decode.py`) computing per-band ρ + Welch coherence with **pre-registered**
criteria — self-tested on synthetic identical/independent/corrupted controls before touching
device data.

### 6.3 The verdict — H_C (stereo visuals) SUBSTANTIALLY REJECTED

Pre-registered kill criterion: ρ > 0.95 across the visual-driving bands ⇒ the channels carry
the same information. Measured (Bose vol 60, canonical fixture, SNR ≈ 7×):

| band (Hz) | 55–110 | 110–220 | 220–440 | 440–880 | 880–1.7k | 1.7–3.5k | 3.5–6.4k |
|---|---|---|---|---|---|---|---|
| ρ (music) | **0.9995** | **0.9995** | **0.996** | **0.988** | **0.969** | **0.981** | 0.867 |
| coherence | 0.999 | 0.999 | 0.993 | 0.975 | 0.937 | 0.959 | 0.777 |

Six of seven bands clear the kill line, most at 0.99+. The one below (3.5–6.4 kHz) is where
music energy — and therefore SNR — is lowest, and noise dilution biases ρ *down*, so the true
acoustic correlation there is, if anything, higher. **Conclusion: at this capsule spacing in a
diffuse room field, visually distinct primary/secondary edge behaviour driven by the two mics
would be synthesised, not sensed.** This is the outcome the design predicted and demanded be
reported as a clean negative rather than papered over with "stereo visuals" that would actually
be decorrelation noise.

Two SPL-confounded earlier captures (laptop, SNR ~4×) showing mid/high decorrelation are
retained as evidence of exactly that confound — low SNR *spuriously rescues* the stereo
hypothesis.

### 6.4 What the second capsule is actually for — H_C2 stands

**Coherence separates music from local disturbance decisively**: music 0.94–0.999 vs quiet
0.73–0.79 in the low-mid bands. A capsule covered by a hand, handling noise, or enclosure
knocks breaks inter-channel coherence instantly even when ρ(music) ≈ 1. **Robustness/occlusion
discrimination — not stereo visuals — is the measured product justification for the second
microphone.** (Hand-occlusion leg itself not yet run; needs a hand at the bench.)

### 6.5 Instrument residuals (named, not hidden)

- **Capture duty 56%** — the stereo read fills ~56% of wall-clock frames (chunk splices;
  suspected DMA descriptor sizing: `dma_frame_num` is mono-sized while stereo doubles bytes per
  frame). L/R stay sample-aligned within every chunk (single interleaved read), so zero-lag ρ
  is valid; Welch coherence is mildly biased down. Fix before any phase-sensitive use.
- **Spacing D unmeasured** (O-4). **Unit 2 dual-capsule topology unproven** (§1.3).

---

## 7. Consumer floors — measured, closed, and carried by profile 2

### 7.1 Distributions (Unit 2, SSL=167 measured, canonical fixture, witnessed)

| leg | witness | awake | conf med | conf p25–p75 | lock duty | max_raw med |
|---|---|---|---|---|---|---|
| quiet-ambient (working room) | −67.8 dBFS | 100% (never latched — ambient, not silence) | 0.21 | 0.07–0.40 · **p95 0.58** | ~0 (excursions to 1) | 155 |
| music Bose 40 | −50.9 | **100%** | 0.39 | 0.24–0.62 | 9% | 363 |
| music Bose 55 | −41.3 | **100%** | **0.81** | 0.56–0.97 | 27% | 912 |
| music Bose 70 | −33.0 | **100%** | 0.75 | 0.61–0.87 | 18% | 1950 |

### 7.2 The floors

- **Silence:** closed — the joint gate (§4). No separate enter/exit constants exist for IM69D;
  the RMS Schmitt is bypassed by design on this mic.
- **Tempo lock:** `K1_LOCK_CONFIDENCE = 0.60` **retained, now measurement-cited** — the
  ambient-quiet conf ceiling (p95 0.58) sits just below it; music conf p75 (0.87–0.97) sits
  well above. Lowering admits ambient false-locks; raising starves real locks. **The low lock
  *duty* (9–27% despite conf medians 0.75–0.81) is a tempo-FSM acquire/hold dynamics question,
  not a mic-floor question** — routed to the tempo lane, deliberately not tuned here.
- **Dense Forge presence:** the gate is proven live (inject 1.0 on every non-latched frame,
  quiet-live and at product SPL); no separate floor change required.
- **`K1_AUDIO_PROFILE_IM69D130_UNIT2` populated 2026-08-13** per its own written
  populate-condition (transfer test closed); the `UNCHARACTERISED_ACK` exposure flag is
  removed from the IM69D env chain (IM73D envs keep their fail-closed ACK; the tombstone
  tripwires stand — **never port these numbers to another mic**).

---

## 8. Visual-pipeline proof under IM69D (P5.B) and the audit machinery

Witnesses (`K1_MATRIX_AUDIT_V1`, env `k1_unit2_im69d_right_matrix`, non-shippable): per-channel
max + lit-count scanned from the **final post-gamma output buffers** on Core 1 immediately
before `FastLED.show()` — the artefact boundary, what the strips actually receive — plus DF
`inject_scale`, on the 1 Hz AP line. Predicates pre-registered before every run.

| predicate | result at product SPL |
|---|---|
| 18/18 both-channel lit duty ≥95% while awake | **PASS — 95.9% / 95.9%** |
| 18/21 DF secondary not black under an 18 primary (≥50%) | **PASS — 100%** (primary 98%) |
| DF quiet-live inject not stuck 0 | **PASS — 1.0 on 32/32 frames** |
| drain to silence latch ≤ 15 s | **PASS — 9.1 s** (laptop 18.6 s FAIL was fixture-induced) |
| 18/21 drain (observational) | no latch in 25 s — filed with the dwell debt |

---

## 9. Method lessons this programme paid for (generalisable)

1. **A stale calibration masquerades as a hardware difference.** The entire per-unit/per-room
   debate dissolved into one recalibration. Predict the correction factor *before* firing the
   recal (1.67× predicted, 1.68× measured) — that is what makes the resolution evidence rather
   than coincidence.
2. **Pre-register predicates, then keep the reds.** The 18.6 s drain FAIL was recorded as a
   fail, then *root-caused to the fixture* and re-run — not tuned away. The pre-registration is
   what made the later PASS trustworthy.
3. **The second-registry trap fires in this codebase.** `scap_*` rows compiled into the typed
   command **table** but live dispatch is the `parse_command` strcmp **ladder** — the ELF
   contained the strings and the device answered `Bad command`. Now ratcheted
   (`test_scap_dispatch_reaches_the_parse_command_ladder`).
4. **Prove instruments against controls before trusting them on the device**: the ρ decoder was
   fed synthetic identical (ρ=1.0), independent (ρ≈0), and corrupted (CRC fail) captures first.
   Indicators must be seen RED before their green means anything.
5. **Byte-identity is the licence for shared-source probes.** Every flag-gated addition
   (stereo, matrix audit) was proven against `k1_hardware`'s three reproducible ELF sections
   (`.dram0.data/.iram0.text/.iram0.vectors` — `72417182/afa23c99/d383aa70` unchanged
   throughout). The `.bin` hash is NOT a byte-identity test (embedded self-hashes churn).
6. **Fixture identity is part of the measurement.** Track, speaker, volume, distance, witness —
   fixed and recorded, or the numbers don't compose across sessions.
7. **A dead symbol can steer real engineering:** the 16→8→4 gain ladder chased
   `threshold_loud_break`, which had zero read sites. Grep the consumers before tuning a
   constant.

---

## 10. Open debt (named, owned)

| item | state |
|---|---|
| **Dwell/persistence gate** (post-latch flashes; 18/21 drain non-latch; tempo-flywheel persistence) | recommended, unimplemented — the one product-behaviour red thread left |
| Lock **duty** 9–27% at product SPL | routed to the tempo-FSM lane (acquire/hold dynamics) |
| Stereo capture duty 56% | DMA descriptor sizing under stereo — fix before phase-sensitive use |
| Unit 2 dual-capsule topology | single-path evidenced (RIGHT only) |
| Capsule spacing D | unmeasured (formality for ρ interpretation) |
| Hand-occlusion H_C2 leg | not run (needs a hand at the bench) |
| `k1_unit2_im69d_right_led160ab` env | keep-or-remove call pending (served the LED-current A/B) |
| `k1_custom` | recomposed, guard-BLOCKED pending device nomination + mic receipt |
| AOP/loudness ladder (P3.D) | not run (radio-free, non-limiting speaker required) |

---

## 11. Evidence index

**Merged PRs:** #43 (gate scoping + fraction 1.75), #44 (P2.B + Stage 1b/2 + floors + matrix),
#45 (profile 2 + decisive Bose round).
**Key commits:** `a8b1912a` (scope + 1.75), `9599714b` (recal resolution), `5dcbfc07` (eyes-on),
`975071a7` (P2.B), `fa164732` (Stage 1b/2 firmware), `019086c8` (dispatch fix), `947e2be8`
(matrix audit), `d1fae012` (profile 2 + Bose round).

| topic | receipt |
|---|---|
| Design + approach decision | `docs/hardware/im69d130-dual-mic-eval-design-2026-08-05.md` |
| RMS finding | `docs/forensics/im69d-bringup-2026-08-06/FINDING-rms-cannot-separate.md` |
| Pin receipt (Unit 2) | `docs/hardware/im69d130-unit2-pin-receipt-2026-08-11.md` |
| Transfer test | `docs/forensics/unit2-bench-transfer-full-2026-08-12.md` |
| Device-evidence canon (HF-29…40) | `docs/canon/SESSION_CANON_2026-08-12_device_evidence_integrity.md` |
| Joint-gate canon + amendment | `docs/canon/SESSION_CANON_2026-08-07_im69d_peakiness_deck16_boot.md` |
| IM73D scar inventory (P2.B) | `docs/forensics/audio-profile/2026-08-12-im73d-scar-inventory-p2b.md` |
| Stage 1b receipt | `docs/forensics/im69d-stage1b-stage2-2026-08-12/stage1b-receipt.md` |
| Stage 2 + P5.B receipts | `docs/forensics/im69d-stage1b-stage2-2026-08-12/stage2-and-matrix-receipt.md` |
| Consumer baseline + floors | `docs/forensics/im69d-consumer-baseline-2026-08-12/IM69D_CONSUMER_BASELINE.md` |
| Profile 2 | `SPECTRASYNQ_K1_FIRMWARE/audio/k1_audio_profile.h` |
| Behavioural gate | `tests/test_im69d_consumer_floors_behavioural.py` |
| Device↔env truth | `docs/hardware/device-build-registry.md` |

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-08-13 | agent:claude-code | Created — canonical end-to-end synthesis of the dual-IM69D130 programme (2026-08-05 → 2026-08-13), Captain-requested. |
