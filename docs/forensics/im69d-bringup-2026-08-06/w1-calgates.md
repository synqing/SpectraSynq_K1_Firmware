---
abstract: "W1-CALGATE-OVERRIDES: independent derivation of IM69D130 noise-cal admission-gate overrides (NOISE_CAL_SSL_PHASE_B_MAX_RAW / TRUSTED_P90_MAX_RAW / MAX_VALID_RAW) at G=8 and G=4, checked against Captain's provisional corridor. Verdict: G=8 corridor separates true silence from the only measured contamination proxy; G=4 corridor separates LOUD/real music (projected) but does NOT reliably separate quiet/speech-level sound from silence — the only direct G=4 acoustic receipt (max=528, mean=73) is itself barely above the G=4 silence p90=67. Includes drafted constants.h block and static_assert ordering (compile-time macros only; K1_SILENCE_RMS_ENTER/EXIT are runtime-mutable inline floats and CANNOT be static_assert'd)."
---

# W1-CALGATE-OVERRIDES — IM69D130 noise-cal admission gate derivation

Repo: SpectraSynq_K1_Firmware @ db300db+ (branch feat/ap-advice-phase0-im69d-gain8)
Scope: read-only (Read/Grep/Bash git+grep). No edits, no device.

## 0. What's actually live (verified against current source, not memory)

`grep -n "NOISE_CAL_SSL_TRUSTED_P90_MAX_RAW\|MAX_VALID_RAW\|PHASE_B_MAX_RAW" SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h SPECTRASYNQ_K1_FIRMWARE/system/globals.h SPECTRASYNQ_K1_FIRMWARE/system/system.h`

- `i2s_audio.h:639` — per-frame Phase-B admission: `if (max_waveform_val_raw <= PHASE_B_MAX_RAW)` else frame excluded from ssl_cal_buf (counted `ssl_cal_rejected_samples`).
- `i2s_audio.h:672` — aggregate contamination reject: `if (p90 > TRUSTED_P90_MAX_RAW) reject(SSL_TOO_LOUD)`.
- `i2s_audio.h:676` — range reject: `learned_ssl < MIN_VALID_RAW || > MAX_VALID_RAW`.
- `globals.h:250-251`, `system.h:522-523` — same MIN/MAX_VALID_RAW re-checked at boot/profile-load for persisted-cal validity.

This is the ADMISSION gate for `start_noise_cal` (machine backstop behind Captain's verbal
silence-go). It is a **different gate** from the runtime silence LATCH (`K1_SILENCE_RMS_ENTER/EXIT`
Schmitt trigger, `i2s_audio.h:857-879`, `globals.h:704-705`) — that gate is run-time mutable
(`inline float`, serial-settable via `:silence_rms_enter/_exit`) and is a **separate, already-flagged
defect** (memory obs #89705, #89440: `threshold_loud_break` dead-code, ENTER/EXIT never re-derived
across the gain walk). Out of scope for this task; noted so the orchestrator doesn't conflate the two.

**Confirmed fact (matches SSA-1 and SSA-3 independently, re-verified myself by direct grep):** the
`#ifdef K1_MIC_IM69D_PDM_V1` block (`constants.h:94-110`) overrides ONLY `BOOT_FALLBACK_RAW`,
`INPUT_GAIN`, `RAW_I16_NEAR_RAIL`. `TRUSTED_P90_MAX_RAW` / `MAX_VALID_RAW` / `PHASE_B_MAX_RAW` /
`MIN_VALID_RAW` are NOT overridden for IM69D anywhere in the tree — the build silently inherits the
SPH0645-domain base values at `constants.h:31-40`: `PHASE_B_MAX_RAW=1500.0f`,
`TRUSTED_P90_MAX_RAW=650.0f`, `MIN_VALID_RAW=50U`, `MAX_VALID_RAW=720U`.

## 1. Receipts used (each traced to file + re-run command)

| Quantity | G=8 | G=4 | Source | Re-run |
|---|---|---|---|---|
| Accepted-cal `ssl_p50`/`ssl_p90` | 63/101 | **38/67** | `docs/hardware/im69d130-phase0-gain8-device-proof-2026-08-05.md:21,53-54` (git-anchored via `1ae9d4a`) | `git show 1ae9d4a -- docs/hardware/im69d130-phase0-gain8-device-proof-2026-08-05.md` |
| Learned SSL | 111 | **74** | same doc | same |
| Music/stimulus `max_raw` (Mac `say`/Glass.aiff clip) | **1785** (max, PRE-recal capture, stale SSL=253) | **528** (max), mean **72.76**, n=21 | G=8: `_scratch/ap_advice_phase0_20260805/music_ambient_drive_summary.json`; G=4: `_scratch/ap_advice_phase0_20260805/gain4_music_stimulus_summary.json` | `cat` each file |
| Quiet post-cal `max_raw` mean | 214-296 | 21-45 (mean 40.2 in quiet leg) | phase0-gain8-device-proof doc + `gain4_music_stimulus_summary.json` `.quiet` | same |
| G=16 measured ambient `max_raw` p90, two legs | **1190 · 307** (this IS the "worst-case ambient" anchor) | — | `docs/hardware/im69d130-vs-main-k1-eval-2026-08-05.md:48-49` (§3 table) | `sed -n '44,70p' docs/hardware/im69d130-vs-main-k1-eval-2026-08-05.md` |
| G=16 music `max_raw` @ vol 45/60/75 (real music, volume-graded) | 3400/9800/17300 | — | same doc, §4 table | same |

**Method-risk flag on the G=8 "music_ambient_drive" receipt:** `music_ambient_drive_summary.json` and
`quiet_precal_summary.json` in the same evidence pack are **byte-identical** (same n=21, same
min/mean/max=422/993.9/1785, same stale `SSL=253` — i.e. captured BEFORE the G=8 cal was even
accepted, `epoch=1785941235` vs the accepted-cal build `epoch=1785942368`). Two different labels
pointing at one capture is a capture-script artefact, not two independently measured legs — I cannot
cleanly attribute this specific 994-mean/1785-max reading to "quiet" vs "music" at G=8.
Re-run: `diff _scratch/ap_advice_phase0_20260805/{quiet_precal,music_ambient_drive}_summary.json` (empty diff).

## 2. Projected worst-case silence p90 (linear gain scaling — [INFERENCE], not directly measured)

Only clean multi-leg ambient p90 data exists at G=16 (1190 · 307, vs-main-k1-eval doc). Signal is
linear in `K1_MIC_IM69D_INPUT_GAIN` below the extraction multiply (`i2s_audio.h:530`,
confirmed by SSA-3 §1), so scaling by gain ratio is a legitimate first-order projection, not a
fabricated round number:

- G=8 (÷2 from G=16): worse leg 1190/2 = **595 ≈ 600**
- G=4 (÷4 from G=16): worse leg 1190/4 = **297.5 ≈ 300**

This matches Captain's stated "worst silence p90 ~600" at G=8 exactly — it traces to a real receipt
via linear projection, not an assumed number. I did NOT independently verify "quiet-music floor
~1056" at G=8 to the same standard — the only candidate receipt (§1's ambiguous 994-mean capture) is
close in magnitude but not identical, and its provenance is compromised by the duplicate-file issue
above. Treat "~1056" as **NOT_VERIFIED** (plausible order of magnitude, not confirmed to a clean receipt).

## 3. Does the corridor separate silence from quiet-music? (the core ask)

### G=8 — Captain's 800 / 920(see §5) / 1000

- Worst-case silence p90 (projected): ~600. Margin to TRUSTED_P90=800: **+200 (33%)** — a real
  improvement over the base 650, which sits only **+50 (8%)** above the same worst-case projection
  (i.e. the base gate is at legitimate false-reject risk on a noisier-than-cal-day room; Captain's
  widening is justified).
- Contamination side: the only receipt (ambiguous, §1) has mean 994 > 800 → still rejected. The
  clean receipt (real music at any volume, PHASE_B per-frame max=1785) is caught by PHASE_B_MAX
  at 1500 already, and even more so at Captain's tightened 1000.
- **Verdict: SEPARATES**, with real (not cosmetic) margin, for every G=8 receipt available.

### G=4 — Captain's 400 / 460(see §5) / 500 — this is the SHIPPED gain, so this is the load-bearing case

- Worst-case silence p90 (projected): ~300. Margin to TRUSTED_P90=400: **+100 (33%)**, proportionally
  consistent with the G=8 case. Actual accepted-cal p90=67 sits far inside this — no false-reject risk
  from the one clean silence receipt available.
- Contamination side — **this is where the corridor does NOT separate cleanly**: the only direct G=4
  acoustic receipt is `gain4_music_stimulus_summary.json` — max **528**, mean **72.76**, n=21. Its
  MEAN (72.76) is barely above the silence p90 (**67**) and far under every proposed ceiling (400/460/500).
  A cal window dominated by sound at this level would compute a p90 nowhere near 400 — **none of
  Captain's three proposed numbers, nor the unmodified base 650/720/1500, would catch it.** This is
  the exact SSA-3 finding (obs #89703) independently reproduced from the raw JSON, not taken on trust.
- Real/loud music, projected ÷4 from the G=16 volume-graded table (§1): vol45→**850**, vol60→**2450**,
  vol75→**4325** (max_raw). All three clear PHASE_B_MAX=500 and TRUSTED_P90=400 with margin — so LOUD
  music would still be caught at G=4 under Captain's numbers.
- **Verdict: PARTIAL SEPARATION.** The G=4 corridor (Captain's proposal or the base gates — no
  numeric fix changes this) reliably rejects loud/real music but does **not** reliably reject
  quiet/speech-level sound, because at G=4 that sound's signature (mean~73, max~528) sits close to
  true silence's own p90 (67) — a 4x gain cut compresses the machine-backstop's dynamic range 4x
  along with everything else. **SAY SO, per the task brief:** at G=4 the human verbal silence-go
  confirmation (Calibration Command Policy, `.claude/CLAUDE.md`) is carrying proportionally MORE of
  the contamination-prevention burden than it was at G=8 or G=16 — no admission-gate retune alone
  closes this gap. This is a structural consequence of the gain cut, not a numbers-picking error.

## 4. Derivation summary (why each number, not just "Captain said so")

| Const | G=8 | G=4 | Derivation |
|---|---|---|---|
| `TRUSTED_P90_MAX_RAW` | 800 | 400 | Worst-case-silence-p90 (projected §2) × ~1.33, giving the same proportional margin (33%) the base 650 gate lacked (only 8% over its own worst-case). Exact halving G8→G4 matches the linear gain-domain relationship confirmed in §2. |
| `MAX_VALID_RAW` | **920** (not Captain's 880) | **460** (not Captain's 440) | Captain's exact `TRUSTED_P90×1.10` (880/440) sits AT the float-truncation boundary: `learned_ssl=(uint32_t)(p90*1.10f+0.5f)` with `p90` up to exactly the TRUSTED_P90 ceiling yields `learned_ssl` landing exactly on 880/440 — one FP epsilon of drift rejects a cal that legitimately passed TRUSTED_P90. IM73D's own override (`constants.h:75-76`) already establishes the precedent of a buffer above the exact 1.10× line (1150 vs exact-1100). Mirroring that ratio (`×1.15`) removes the edge case: 800×1.15=920, 400×1.15=460. |
| `PHASE_B_MAX_RAW` | 1000 | 500 | Captain's numbers, endorsed as-is. Per-frame ceiling; real silence frames at G=8/G=4 cluster far below (p90 101/67), so tightening from base 1500 only screens OUT more contamination with negligible false-reject risk to the measured silence receipts. |

## 5. Draft constants.h override block

Style-matched to the existing `#ifdef K1_MIC_IM73D_PDM_V1` block (`constants.h:72-76`): `#undef`
then `#define`, each with its own dated provenance comment. Both gain variants included so the
orchestrator drops in whichever Captain confirms; **delete the unused variant's lines before merge**
(only one gain define should be active in the final tree — this drafts both for review only).

```cpp
#ifdef K1_MIC_IM69D_PDM_V1
// IM69D130 PDM domain (bench eval, 2026-08-05). Separate from IM73D — do NOT inherit
// K1_MIC_IM73D_INPUT_GAIN or the IM73D-widened SSL cal gates until measured.
// SEED SSL fallback into a PDM-plausible band (never 0 at runtime).
#undef  NOISE_CAL_SSL_BOOT_FALLBACK_RAW
#define NOISE_CAL_SSL_BOOT_FALLBACK_RAW 120U

// PDM cal-gate window (W1-CALGATE-OVERRIDES, 2026-08-06, bench-measured + gain-scaled projection).
// The base 650/720/1500 SPH0645-domain gates silently inherited by IM69D (no prior override existed
// — confirmed by grep, constants.h:94-110 only touches BOOT_FALLBACK_RAW/INPUT_GAIN/NEAR_RAIL) were
// derived for a different mic family and do not track this gain's silence/contamination bands.
//
// Receipts (docs/hardware/im69d130-phase0-gain8-device-proof-2026-08-05.md;
// docs/hardware/im69d130-vs-main-k1-eval-2026-08-05.md §3-4;
// _scratch/ap_advice_phase0_20260805/{gain4_music_stimulus,music_ambient_drive}_summary.json):
//   accepted-cal ssl_p90:        G=8 101   / G=4 67
//   worst-case ambient p90 (projected, linear from G=16 measured 1190): G=8 ~600 / G=4 ~300
//   real-music max_raw @ vol45/60/75 (projected ÷ from G=16 measured 3400/9800/17300):
//                                 G=8 1700/4900/8600 / G=4 850/2450/4325
// CAVEAT (load-bearing — read before retuning further): the only DIRECT G=4 acoustic receipt
// (a brief speech/chime stimulus, not sustained music) reads mean=73/max=528 — barely above the
// G=4 silence p90 of 67. No admission-gate number closes that specific gap; the Captain verbal
// silence-go confirmation (Calibration Command Policy) is the primary defence against
// quiet/speech-level contamination at this gain. This corridor reliably rejects LOUD/real music.
//
// #if K1_MIC_IM69D_INPUT_GAIN == 8.0f variant — USE ONLY IF SHIPPING AT G=8:
#undef  NOISE_CAL_SSL_TRUSTED_P90_MAX_RAW
#define NOISE_CAL_SSL_TRUSTED_P90_MAX_RAW 800.0f
#undef  NOISE_CAL_SSL_MAX_VALID_RAW
#define NOISE_CAL_SSL_MAX_VALID_RAW 920U
#undef  NOISE_CAL_SSL_PHASE_B_MAX_RAW
#define NOISE_CAL_SSL_PHASE_B_MAX_RAW 1000.0f

// #if K1_MIC_IM69D_INPUT_GAIN == 4.0f variant — USE ONLY IF SHIPPING AT G=4 (current tree default):
// #undef  NOISE_CAL_SSL_TRUSTED_P90_MAX_RAW
// #define NOISE_CAL_SSL_TRUSTED_P90_MAX_RAW 400.0f
// #undef  NOISE_CAL_SSL_MAX_VALID_RAW
// #define NOISE_CAL_SSL_MAX_VALID_RAW 460U
// #undef  NOISE_CAL_SSL_PHASE_B_MAX_RAW
// #define NOISE_CAL_SSL_PHASE_B_MAX_RAW 500.0f

// Pre-sensitivity input gain...
#ifndef K1_MIC_IM69D_INPUT_GAIN
#define K1_MIC_IM69D_INPUT_GAIN 4.0f
#endif

#define K1_MIC_IM69D_RAW_I16_NEAR_RAIL 30000

// --- Compile-time ordering guard (W1-CALGATE-OVERRIDES) ---
// Only covers macros (#define, compile-time constants). K1_SILENCE_RMS_ENTER/EXIT are
// runtime-mutable `inline float` (globals.h:704-705, serial-settable via :silence_rms_enter/_exit)
// and CANNOT appear in a static_assert — they are not constant expressions. Their ordering needs a
// runtime guard at the serial-write site instead (see note below), not a compile-time check here.
static_assert(NOISE_CAL_SSL_MIN_VALID_RAW < NOISE_CAL_SSL_BOOT_FALLBACK_RAW,
              "IM69D: boot fallback must sit above the admission floor");
static_assert(NOISE_CAL_SSL_BOOT_FALLBACK_RAW < (uint32_t)NOISE_CAL_SSL_TRUSTED_P90_MAX_RAW,
              "IM69D: boot fallback must sit below the contamination ceiling");
static_assert((uint32_t)NOISE_CAL_SSL_TRUSTED_P90_MAX_RAW < (uint32_t)NOISE_CAL_SSL_PHASE_B_MAX_RAW,
              "IM69D: p90 contamination ceiling must be tighter than the per-frame admission ceiling");
static_assert((uint32_t)NOISE_CAL_SSL_PHASE_B_MAX_RAW < K1_MIC_IM69D_RAW_I16_NEAR_RAIL,
              "IM69D: per-frame cal ceiling must sit below the raw ADC near-rail guard");
#endif
```

**Domain caveat on the last assert:** `K1_MIC_IM69D_RAW_I16_NEAR_RAIL` (30000) is a **pre-gain**
int16 rail guard (`i2s_audio.h:450`, applied before the `K1_MIC_IM69D_INPUT_GAIN` multiply — SSA-1
confirmed), while `PHASE_B_MAX_RAW` is **post-gain** AC-corrected. They are different domains and
this comparison is a coarse sanity floor (catches a gross typo, e.g. `PHASE_B_MAX_RAW=50000`), not a
tight ordering proof — say so in the comment rather than imply it's load-bearing precision.

**Where it compiles:** inside the `#ifdef K1_MIC_IM69D_PDM_V1` block itself, placed AFTER all four
overridden macros and `K1_MIC_IM69D_RAW_I16_NEAR_RAIL` are defined, BEFORE that block's closing
`#endif` — this is the only point where every symbol used is (a) already `#define`d and (b) still
inside the flag guard, so it only compiles/fires on an actual IM69D build. Mirroring this same
pattern inside the `K1_MIC_IM73D_PDM_V1` block (against ITS OWN 1000/1150/1500/30000) is a natural
follow-up but is out of this task's scope — flagging as a clean, low-risk next step.

**Runtime guard needed for ENTER<EXIT (separate task, cross-referencing memory obs #89703/#89440):**
since these are serial-writable, the correct enforcement point is wherever `:silence_rms_enter` /
`:silence_rms_exit` are parsed (per SSA-3, two dispatch sites post-PR#38:
`serial/serial_typed_dispatch.cpp:559,565` and `serial/serial_menu.cpp:3245,3249`) — reject or clamp
a write that would leave `K1_SILENCE_RMS_ENTER >= K1_SILENCE_RMS_EXIT`. Not drafted here (out of
W1's scope; the RMS ENTER/EXIT gate is the separate defect class already flagged by #89705/#89440,
not the noise-cal admission gate this task covers).

## 6. IM73D 8-run gate methodology (commit 96d908a) — for W1's finalisation protocol to mirror

`git show 96d908a` (`fix(im73d): PDM-domain cal-gate window — Outcome B from 8 measured bench runs`):
- **8 device runs** on 2026-07-02/03, logged at `_scratch/im73d_bringup/{watch_and_cal*,silence_cal_ny}.log`.
- Measured bands at the SHIPPED gain (G=16 for IM73D): true silence (Captain-confirmed silence-go
  run) `ssl_p90=807`, historical pass `645`; quiet-ish ambient `880-922`; audible music `1040-1219`.
- Chose `TRUSTED_P90_MAX_RAW=1000` — **between** the measured silence band (≤922) and the measured
  music band (≥1040), i.e. picked from the actual gap in 8 real runs, not a formula.
- Chose `MAX_VALID_RAW=1150` — `p90×1.1 ≤ 1100`, plus buffer (the same edge-case margin issue I
  flagged in §4 for Captain's exact 880/440).
- Base `#define`s left untouched (flag-off SPH builds byte-identical; static pytest pins on base
  lines still hold) — the override is 100% additive inside the `#ifdef K1_MIC_IM73D_PDM_V1` block.

**Gap vs this task:** IM73D's 1000/1150 corridor was chosen from **8 independent runs spanning
silence→ambient→music at the actual shipped gain**. IM69D currently has **one** accepted-cal run per
gain (G=8: 1 run; G=4: 1 run) plus a single ambiguous/duplicated "music_ambient_drive" capture and
one non-representative speech/chime stimulus — not an 8-run spread. **Recommend before finalising:**
replicate the IM73D protocol at G=4 specifically — 8 bench runs covering true-silence (Captain
silence-go, multiple takes to see the p90 SPREAD not just one value), quiet-ambient, and **real
sustained music at low/medium/high volume** (not a spoken-word clip) — before treating any TRUSTED_P90
number as final. §3's "PARTIAL SEPARATION" verdict at G=4 is exactly the kind of gap that an 8-run
spread would either confirm or refute with real data instead of a single 21-frame speech capture.

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-08-06 | agent:claude-fable-5 (W1-CALGATE-OVERRIDES) | Created — independent derivation of IM69D130 noise-cal admission-gate overrides at G=8/G=4, cross-checked against SSA-1/SSA-3 memory findings and re-verified from raw JSON receipts and git-anchored docs. |

---

## 7. REVISION (2026-08-06, checkpoint) — real paired bench data supersedes §1-5 for the numbers

Team-lead supplied live bench receipts taken AFTER my initial return, same build (`k1_bench_im69d`
@ G=4), same room, paired same-session (music and ambient legs from the same acoustic setup, so the
×2 projection to G=8 is a same-acoustics gain-only scale, not a cross-session guess):

| Leg | n / window | max_raw | rms_raw | raw_i16_rms |
|---|---|---|---|---|
| MUSIC, Captain's listening level, G=4 | 50 frames / 45 s | p50 294 · p90 **933** · p95 1033 · max 1331 | p50 0.0027 · p90 0.0128 · max 0.0289 | p50 15.0 · p90 61.2 · max 85.2 |
| ROOM AMBIENT, G=4 | 26 frames / 20 s | ~275-505 (range) | p50 0.0072 · p95 0.0085 · max 0.0092 | p50 25.8 · max 35.2 |
| MUSIC, G=8 (×2 projection, same acoustics) | — | p90 **1866** · max 2662 | — | — |
| ROOM AMBIENT, G=8 (×2 projection) | — | max ~1010 | — | — |

**This supersedes my §1-5 G=8 derivation (800/920/1000).** That number was built from a cross-session
G=16→G=8 projection (vs-main-k1-eval doc, different day, flagged with its own room-variance caveat).
The new paired G=4 data, scaled ×2, puts ambient max at **~1010 — ABOVE my proposed 800 ceiling**.
An 800 TRUSTED_P90 at G=8 would have **falsely rejected valid room-ambient silence**. Discarding it.

### 7.1 Why PHASE_B_MAX_RAW cannot do the real separation work (new finding, both gains)

Music `p50=294` (G=4) sits **inside** the ambient range (275-505) — a single quiet-moment music frame
is statistically indistinguishable from a single ambient frame. There is **no per-frame threshold**
that separates "this one frame is music" from "this one frame is ambient" — separation is visible
**only in the aggregate** (music has enough loud frames, p90=933, to pull the percentile up; ambient
does not). This means `PHASE_B_MAX_RAW`'s job is what its own source comment already says — "reject
frames too loud to be silence" as a coarse **isolated-transient** guard (a slammed door skewing the
percentile) — it is **not** and **cannot be** a redundant defence against sustained music. `TRUSTED_P90_MAX_RAW`
is the sole load-bearing gate against sustained-music contamination at any gain. Do not oversell
PHASE_B tightening as adding real redundancy against this failure class.

### 7.2 Revised corridor — picked from the measured gap, both directions checked

**G=4:**
- `TRUSTED_P90_MAX_RAW = 700.0f` — sits at ~geometric mean of ambient-ceiling(505) and music-p90(933)
  (`sqrt(505*933)=686`, chose 700 for a clean number). Margin: **+195 (39%) above ambient**, **-233
  (33%) below music p90**. ADMITS ambient, REJECTS this music. Separation ratio achieved: same 1.85x
  gap the data provides, split ~evenly.
- `NOISE_CAL_SSL_MAX_VALID_RAW = 800U` — `learned_ssl=(uint32_t)(700*1.10+0.5)=770` at the TRUSTED_P90
  boundary; 800 gives a 30-unit buffer over that truncation edge (same edge-case class flagged in §4
  for Captain's original exact-880/440).
- `PHASE_B_MAX_RAW = 1000.0f` — ~2x ambient ceiling (transient headroom for true silence), strips only
  the top ~5-10% tail of this specific music sample (p95=1033 barely exceeds it) — see §7.1, this is
  NOT the primary defence, TRUSTED_P90 is.

**G=8** (×2 of the above, matching the ×2 acoustic projection — same ratios by construction):
- `TRUSTED_P90_MAX_RAW = 1400.0f` — margin +390 (39%) above ambient(1010), -466 (33%) below music
  p90(1866).
- `NOISE_CAL_SSL_MAX_VALID_RAW = 1610U` — boundary at `(uint32_t)(1400*1.10+0.5)=1540`, 70-unit buffer.
- `PHASE_B_MAX_RAW = 2000.0f` — ~2x ambient ceiling, same transient-guard role as G4.

### 7.3 Separation ratio (explicit, as required)

Both gains: **ambient-ceiling : corridor-centre : music-p90 = 505 : 700 : 933 (G4)** and
**1010 : 1400 : 1866 (G8)** — identical 1.386x / 1.333x split on each side of the corridor at both
gains (invariant under linear gain scaling, as it must be for a domain that is purely
`raw × K1_MIC_IM69D_INPUT_GAIN`). **A corridor that separates true silence from this measured music
DOES exist at both gains** — unlike my earlier concern from the non-representative speech-clip
receipt (§3), which was a weak stimulus, not real music.

### 7.4 Residual risk NOT closed by any single-number corridor (say-so, per the brief)

This corridor is validated against exactly **one** measured music loudness (Captain's own listening
level) and **one** 20 s/26-frame ambient sample per gain; the G=8 figures are the stated ×2
projection, not an independent measurement. A **quieter background-music** cal attempt — somewhere
between the ambient ceiling (505/1010) and this measured music's p90 (933/1866) — is **not provably
caught** by 700/1400 or by any other single number in that gap; a lower-volume session could compute
a p90 anywhere in the untested 505-933 band. This is the exact "volume-dependent" gap flagged in the
checkpoint message, and it is not something a constants-only fix can fully close — it narrows with a
tighter corridor at the cost of ambient false-reject risk, and only an IM73D-style multi-run spread
(varying music volume, not just one listening level) can locate the true safe ceiling with confidence.
Recommend, before finalising: repeat the paired ambient/music capture at 2-3 volume steps (quiet
background, moderate, listening-level) at whichever gain ships — mirroring the `96d908a` 8-run
protocol — before treating 700/1400 as final rather than "best available from one data point."

### 7.5 Revised constants.h block (replaces §5's numbers; style/placement unchanged)

```cpp
// G=4 variant (current tree default):
#undef  NOISE_CAL_SSL_TRUSTED_P90_MAX_RAW
#define NOISE_CAL_SSL_TRUSTED_P90_MAX_RAW 700.0f
#undef  NOISE_CAL_SSL_MAX_VALID_RAW
#define NOISE_CAL_SSL_MAX_VALID_RAW 800U
#undef  NOISE_CAL_SSL_PHASE_B_MAX_RAW
#define NOISE_CAL_SSL_PHASE_B_MAX_RAW 1000.0f

// G=8 variant:
// #undef  NOISE_CAL_SSL_TRUSTED_P90_MAX_RAW
// #define NOISE_CAL_SSL_TRUSTED_P90_MAX_RAW 1400.0f
// #undef  NOISE_CAL_SSL_MAX_VALID_RAW
// #define NOISE_CAL_SSL_MAX_VALID_RAW 1610U
// #undef  NOISE_CAL_SSL_PHASE_B_MAX_RAW
// #define NOISE_CAL_SSL_PHASE_B_MAX_RAW 2000.0f
```

Provenance comment for the tree: cite `_scratch/<checkpoint-evidence-pack>/{music_listening_level,room_ambient}_summary.json`
(team-lead's raw capture, not yet filed under a docs/hardware/ receipt — recommend the orchestrator
land a dated receipt doc mirroring `im69d130-phase0-gain8-device-proof-2026-08-05.md`'s format before
this ships, so the numbers trace to a committed file, not just a chat message).

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-08-06 | agent:claude-fable-5 (W1-CALGATE-OVERRIDES) | §7 revision — real paired music/ambient bench data (team-lead checkpoint) supersedes the §1-5 G=8 numbers; new corridor picked from measured gap (700/800/1000 @G4, 1400/1610/2000 @G8); identified that PHASE_B_MAX_RAW structurally cannot separate sustained music (p50 overlaps ambient range) — TRUSTED_P90 is the sole load-bearing gate; flagged residual quiet-background-music gap as unclosed by any single-number corridor. |
