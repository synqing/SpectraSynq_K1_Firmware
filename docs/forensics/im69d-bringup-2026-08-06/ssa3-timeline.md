---
abstract: "SSA-3 forensic timeline of the IM69D130 bringup (2026-08-05, commits 8335b7f..db300db). Per-commit: what changed [FACT], what it implied for AP absolute level, and which downstream consumers of absolute signal level were NOT re-derived when mic gain went 16 -> 8 -> 4. Names five non-re-derived constants beyond the K1_SILENCE_RMS_ENTER/EXIT seed, with the sharpest being the noise-cal contamination guards (NOISE_CAL_SSL_PHASE_B_MAX_RAW 1500, TRUSTED_P90_MAX_RAW 650) which silently weakened 4x."
---

# SSA-3 — IM69D130 bringup timeline and non-re-derived AP level consumers

**Task ID:** SSA-3-TIMELINE · **Repo:** `/Users/spectrasynq/SpectraSynq_K1_Firmware`
**Branch:** `feat/ap-advice-phase0-im69d-gain8` @ `db300db` · **Date:** 2026-08-06
**Default verdict:** NOT_VERIFIED for any causal claim. `[FACT]` = visible in a diff or in current source. `[INFERENCE]` = my derivation, not in any diff.

---

## 0. Anchor verification

All eight anchors confirmed by `git log -1`. One correction to the brief: `db300db` is
`db300dbbf3c7f0195069e56986fd3ced511b8206` — "merge(main): integrate origin/main into AP advice
Phase 0–2 branch". Branch HEAD is `cf66e27` (one commit **after** `db300db`).

Re-run: `git rev-parse db300db && git log --oneline --merges -3`

Two commits in the chain were **not** in the brief but are load-bearing:

| sha | date | why it matters |
|---|---|---|
| `9013ed9` | 2026-08-05 | `docs(hardware): Phase 0 IM69D G=8 device-proof receipt` — the G=8 receipt later rewritten by `1ae9d4a` |
| `e220cd7` | 2026-08-05 | `docs(forensics): note_offset OOB read + bass-mode frame budget` — sits between `1ae9d4a` and `024591d` |

**Correction to the brief's framing:** the gain was **not** retuned `8 -> 4` in one step. It ran
**`16 -> 8 -> 4`**, and the `16 -> 8` step landed in a commit typed `docs(lane)`.

---

## 1. The gain ladder — three commits, one constant

`K1_MIC_IM69D_INPUT_GAIN` (`SPECTRASYNQ_K1_FIRMWARE/system/constants.h:~101`)

| commit | date | value | comment justification (verbatim gist) |
|---|---|---|---|
| `70b03e5` | 2026-08-05 22:45 | **16.0f** (born) | "G=1 music max_raw≈67–74 sat below SSL=120 … conservative first step G=16 clears SSL (pred. music max_raw≈1070–1180) … quiet pred. ≈256–416 (learnable SSL window)" |
| `7741dd3` | 2026-08-05 22:49 | **8.0f** | "G=16 quiet max_raw 307–1190 overflowed the SSL learn window [50,720] … Halve to G=8" |
| `1ae9d4a` | 2026-08-05 23:26 | **4.0f** | "G=8 cal ACCEPTED (SSL=111) but post-cal ambient max_raw mean ~214–296 stayed above SSL×1.2 (~133) … Halve again to G=4" |

Re-run: `git log --oneline -L 94,110:SPECTRASYNQ_K1_FIRMWARE/system/constants.h`

`[FACT]` **`7741dd3` is a firmware behaviour change shipped under a `docs(lane):` subject line.**
Its diffstat is `constants.h | 11 +-` plus one doc. A reviewer filtering the log for `feat(`/`fix(`
would not see the 2x gain change. Re-run: `git show --stat 7741dd3`.

`[FACT]` The extraction site is `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:530`:
`int32_t sample = (int32_t)((float)im69d_samples_i16[i] * K1_MIC_IM69D_INPUT_GAIN);`
Everything downstream of that line — sensitivity, clamp, DC removal, `waveform[]`,
`waveform_fixed_point[]`, `max_waveform_val_raw`, the GDFT, the noise-cal buffers and the RMS
silence gate — lives in a signal domain that scales **linearly** with this constant. A 16 -> 4
change is a **4x domain shift** for every absolute threshold below it.

---

## 2. Device numbers the commits themselves recorded

From `git show 1ae9d4a -- docs/hardware/im69d130-phase0-gain8-device-proof-2026-08-05.md`
(the G=8 receipt from `9013ed9` was rewritten in place by `1ae9d4a`, so the "before" column
survives only in `git show 9013ed9`):

| quantity | G=8 (rejected) | G=4 (shipped) |
|---|---|---|
| cal `ssl_p50` / `ssl_p90` | 63 / 101 | **38 / 67** |
| learned `SSL = round(p90*1.10)` | 111 | **74** |
| loud-break (`SSL x 1.2`) | ~133 | **88.8** |
| quiet post-cal `max_raw` mean | 214–296 | (not tabulated) |
| music / stimulus `max_raw` | **1785** | **528** |
| quiet `silence=1` | 0% ("0 forever") | 100% of 30 s window |

These are the only absolute-level device measurements in the chain, and they are what the
"not re-derived" analysis below is measured against.

---

## 3. Per-commit timeline

### `8335b7f` — 2026-08-05 21:09 — `docs(lane): kill and shelve dual-K1 sync; route to IM69D130 mic eval`
- **Changed [FACT]:** docs/lane routing only. No firmware.
- **Implied for AP level:** none.
- **Not re-derived:** n/a.
- **Evidence:** `git show --stat 8335b7f`

### `5d5e9e4` — `test(harness): mic A/B comparison, interrupted-run recovery, IM69D role`
- **Changed [FACT]:** host harness gains an IM69D role and a mic A/B comparison path.
- **Implied:** establishes that IM73D and IM69D are meant to be **compared**, which is the moment
  a shared absolute-threshold audit was cheapest. It was not done.
- **Evidence:** `git show --stat 5d5e9e4`

### `2bb50c2` — 2026-08-05 22:12 — `docs(lane): activate IM69D authority`
- **Changed [FACT]:** lane authority docs + ignore rules. No firmware.

### `70b03e5` — 2026-08-05 22:45 — `chore: land remaining artefacts, IM69D env, skills, and STM bench`
- **Changed [FACT]:** creates the entire IM69D compile domain in `constants.h` (+41 lines):
  - mutual-exclusion `#error` for `K1_MIC_IM73D_PDM_V1` + `K1_MIC_IM69D_PDM_V1`
  - shared helper `K1_MIC_PDM_RX_ANY_V1`
  - `#ifdef K1_MIC_IM69D_PDM_V1` block: `NOISE_CAL_SSL_BOOT_FALLBACK_RAW 120U`,
    `K1_MIC_IM69D_INPUT_GAIN 16.0f`, `K1_MIC_IM69D_RAW_I16_NEAR_RAIL 30000`
  - IM69D GPIO map (CLK=14 / DIN=13 / SEL=12) + production-pinmap `#error` guard
- **Implied for AP level:** the block's own comment states the contract —
  *"Separate from IM73D — do NOT inherit `K1_MIC_IM73D_INPUT_GAIN` or the IM73D-widened SSL cal
  gates until measured."* `[FACT]`
- **What it did NOT re-derive [FACT]:** the block overrides **only** `BOOT_FALLBACK_RAW`. Because
  the two mic flags are mutually exclusive, the IM73D widening (`TRUSTED_P90_MAX_RAW 1000`,
  `MAX_VALID_RAW 1150`, `constants.h:73–76`) is **not compiled** on an IM69D build. The IM69D lane
  therefore silently inherits the **base SPH0645-domain** cal gates at `constants.h:34–40`:
  `PHASE_B_MAX_RAW 1500.0f`, `TRUSTED_P90_MAX_RAW 650.0f`, `MIN_VALID_RAW 50U`,
  `MAX_VALID_RAW 720U`, `MAX_P90_TO_P50_RATIO 2.50f`. The comment promises non-inheritance of the
  *IM73D* values; it is silent on inheritance of the *SPH* values, which is what actually happened.
- **Evidence:** `git show 70b03e5 -- SPECTRASYNQ_K1_FIRMWARE/system/constants.h`;
  `sed -n '25,60p;93,110p' SPECTRASYNQ_K1_FIRMWARE/system/constants.h`

### `7741dd3` — 2026-08-05 22:49 — `docs(lane): phase0 gain8 code-ready note and constants follow-up`
- **Changed [FACT]:** `K1_MIC_IM69D_INPUT_GAIN` **16.0f -> 8.0f** (2x domain shift) + one doc.
- **Implied:** every absolute threshold below line 530 of `i2s_audio.h` is now 2x too high
  relative to the signal.
- **NOT re-derived [FACT]:** `NOISE_CAL_SSL_BOOT_FALLBACK_RAW` (120U, sized in `70b03e5` for the
  G=16 prediction "quiet pred. ≈256–416"), `NOISE_CAL_SSL_PHASE_B_MAX_RAW`,
  `NOISE_CAL_SSL_TRUSTED_P90_MAX_RAW`, `NOISE_CAL_SSL_MIN_VALID_RAW`,
  `K1_SILENCE_RMS_ENTER/EXIT`. The diff touches **only** the gain define — nothing else in the
  file changed. `git show 7741dd3 -- SPECTRASYNQ_K1_FIRMWARE/system/constants.h` is 11 lines,
  10 of them comment.
- **Process note [FACT]:** behaviour change under a `docs(` subject (see §1).

### `9013ed9` — `docs(hardware): Phase 0 IM69D G=8 device-proof receipt`
- **Changed [FACT]:** records the G=8 device run as **GATE FAIL on `silence=1`**.

### `1ae9d4a` — 2026-08-05 23:26 — `feat(audio): close Phase 0 IM69D silence at gain 4`
- **Changed [FACT]:** `K1_MIC_IM69D_INPUT_GAIN` **8.0f -> 4.0f**; `device-build-registry.md`
  deployed-state line; the G=8 receipt rewritten in place to GATE PASS.
- **Implied:** cumulative **4x** reduction from the `70b03e5` seed.
- **Diffstat [FACT]:** `constants.h | 12 +-` — **7 insertions, 5 deletions, all inside the one
  `#define` and its comment block.** No other firmware file in the commit.
- **NOT re-derived — this is the core answer to the brief's question:**

| consumer | value | domain it was sized in | direction of harm at G=4 |
|---|---|---|---|
| `K1_SILENCE_RMS_ENTER` / `_EXIT` | `0.04f` / `0.08f` (`globals.h:704–705`) | **2026-07-10, IM73D/SPH bench** (`f87709d`) | **SEED (given).** Absolute post-mic-gain RMS. Unchanged across a 4x domain shift. |
| `NOISE_CAL_SSL_PHASE_B_MAX_RAW` | `1500.0f` (`constants.h:34`) | SPH0645 | **Guard silently disarmed.** At G=8 music `max_raw`=1785 **exceeded** 1500, so music frames were rejected from the cal window. At G=4 the same music is ~528 — **well under** 1500, so music-contaminated frames now **pass** the Phase-B admission gate. |
| `NOISE_CAL_SSL_TRUSTED_P90_MAX_RAW` | `650.0f` (`constants.h:36`) | SPH0645 | **Contamination rejection weakened 4x.** This is the guard that rejects a cal run polluted by music. At G=4 a music-contaminated window's p90 is far below 650 and is accepted as "trusted silence". |
| `NOISE_CAL_SSL_MIN_VALID_RAW` | `50U` (`constants.h:38`) | SPH0645 | **Margin halved.** Accept requires `p90*1.1 >= 50`, i.e. `p90 >= 45.5`. Measured G=8 p90=101 (2.2x margin); G=4 p90=67 (**1.47x margin**). A marginally quieter room or a quieter unit now trips `NOISE_CAL_REJECT_SSL_RANGE`. |
| `NOISE_CAL_SSL_BOOT_FALLBACK_RAW` | `120U` (`constants.h:99`, IM69D block) | sized in `70b03e5` for **G=16** | Boot fallback now sits ~**1.6x above the learned SSL** (74) instead of below it. An uncalibrated IM69D boots with a silence floor higher than a calibrated one. |
| `K1_LOUD_GUARD_NEAR_RAIL_RAW` | `28000.0f` (`constants.h:~115`) | SPH0645 | Direction-safe but **inert**: measured peak `max_raw` 528 at G=4 is ~53x below the rail, so the loud-room guard can no longer engage on this mic. |

- **Correctly gain-independent (no re-derivation needed) [FACT]:**
  - `SILENCE_ENTER_SSL_FRAC 0.35f` / `SILENCE_EXIT_SSL_FRAC 0.55f` (`globals.h:692–693`) and
    `threshold_loud_break = SWEET_SPOT_MIN_LEVEL * 1.20` (`i2s_audio.h:686`) are **ratios of the
    learned SSL**, so they self-scale with the gain. This is the pattern the absolute constants
    above should have followed.
  - `K1_MIC_IM69D_RAW_I16_NEAR_RAIL 30000` is applied at `i2s_audio.h:450` **before** the gain
    multiply — correctly a pre-gain telemetry guardrail.
  - `NOISE_CAL_SSL_MAX_P90_TO_P50_RATIO 2.50f` is dimensionless.

- **Evidence:** `git show 1ae9d4a -- SPECTRASYNQ_K1_FIRMWARE/system/constants.h`;
  `git show 9013ed9`; `sed -n '655,700p;845,880p' SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h`;
  `git log --oneline -L 700,710:SPECTRASYNQ_K1_FIRMWARE/system/globals.h`

### `e220cd7` — `docs(forensics): note_offset OOB read + bass-mode frame budget`
- **Changed [FACT]:** forensic doc only. Records an OOB read on `note_offset` — the same
  `note_offset` that `024591d` then makes load-bearing for the Nyquist bin bound.

### `024591d` — 2026-08-05 23:45 — `feat(audio): retire Nyquist ghost bins as resolution`
- **Changed [FACT]:** adds `sb_gdft_nyquist_safe_bin_hi(sample_rate, note_offset)` doc contract in
  `constants.h`; `k1_gdft_core.cpp` skips Goertzel for bins `[hi, NUM_FREQS)`; **nine effect files**
  re-bounded to `hi` instead of `NUM_FREQS`; host `render_host_globals.cpp`; golden `gdft` +
  `render` JSONL + `MANIFEST.sha256` regenerated; new `test_nyquist_bin_hygiene_static.py`.
  Default profile `fs=12800 / NOTE_OFFSET=12 -> hi=71`, retiring bins 71..79.
- **Implied for AP level/timing:** **frequency-axis**, not level-axis. Removes 9 aliased bins from
  the analysis and from every consumer's normalisation denominator.
- **NOT re-derived [INFERENCE]:** any per-band statistic whose normaliser assumed 80 live bins
  (AGC per-band, spectral-flux/onset sums, chroma folding) now sums over 71. The commit regenerated
  the **goldens** rather than re-deriving the constants, which locks in whatever shift occurred.
  The golden JSONL churn (`gdft.golden.jsonl | 24 ++--`, `render.golden.jsonl | 40 ++--`) is the
  visible footprint of that shift. This is a change of the same *class* as the gain retune —
  a domain shift absorbed by regenerating the oracle instead of re-deriving the thresholds.
- **Evidence:** `git show --stat 024591d`; `git show 024591d -- SPECTRASYNQ_K1_FIRMWARE/system/constants.h`

### `24989e5` — 2026-08-05 23:57 — `feat(audio): drop GDFT x2 for 1-semitone Rayleigh sizing`
- **Changed [FACT]:** `K1_GDFT_X2_CROSSOVER_BIN` (default **0u** = global drop of the legacy x2
  Goertzel window); optional bench-only `K1_GDFT_X2_AB_V1` runtime override
  `inline volatile uint8_t k1_gdft_x2_crossover_bin`; `i2s_audio.h` (+25), `system.h` (+14),
  `platformio.ini` (+2); host oracles `oracle_gdft.py` / `oracle_agc_perband.py` /
  `gdft_center_honesty_model.py`; goldens + manifest regenerated.
- **Implied for AP level/timing [FACT-adjacent]:** halving each Goertzel window **halves the
  integration time** and therefore the accumulated energy per bin. This is a **level-domain**
  change stacked on top of the 4x mic-gain reduction, on the same day.
- **NOT re-derived [INFERENCE]:** the same absolute thresholds listed in `1ae9d4a` above are
  downstream of GDFT magnitude for the AGC/onset path. Neither the `1ae9d4a` gain commit nor this
  one cross-references the other. The two commits are 31 minutes apart and both move absolute
  signal level; no commit in the chain re-derives a threshold against their **combined** effect.
- **Concurrency note [FACT]:** `inline volatile uint8_t k1_gdft_x2_crossover_bin` is a mutable
  cross-core scalar written from the serial path. Its comment restricts it to bench envs; the
  `#if defined(K1_GDFT_X2_AB_V1)` guard is what enforces that.
- **Evidence:** `git show 24989e5 -- SPECTRASYNQ_K1_FIRMWARE/system/constants.h platformio.ini`

### `db300db` — 2026-08-06 — `merge(main): integrate origin/main into AP advice Phase 0–2 branch`
- **Changed [FACT]:** merge bringing in PR#38 (serial-menu decomposition) and PR#39 (save-show hotkey).
- **Implied [FACT]:** PR#38's decomposition means `K1_SILENCE_RMS_ENTER/EXIT` now have **two**
  serial write sites — `serial/serial_typed_dispatch.cpp:559,565` **and**
  `serial/serial_menu.cpp:3245,3249`. Duplicate dispatch surfaces for a threshold that is already
  mis-scaled.
- **Evidence:** `grep -n "K1_SILENCE_RMS_ENTER" SPECTRASYNQ_K1_FIRMWARE/serial/*.cpp`

---

## 4. The causal claim in `1ae9d4a` that the diff does not support

`1ae9d4a`'s device-proof doc states the silence path as:

> 3. `silence = true` only after **≥10 s** continuous in that state (~L795–801)
> 4. Any `max_waveform_val_raw > threshold_loud_break` **immediately** clears silence and resets the timer (~L786–794)

and tabulates the fix as loud-break moving `~133 -> 88.8`.

**What the current source actually does [FACT]:**
`i2s_audio.h:856–878` — `silence` is written **only** from `k1_rms_silent_state`, a Schmitt on
`k1_silence_rms_raw` against `K1_SILENCE_RMS_ENTER` / `K1_SILENCE_RMS_EXIT`. The block carries an
in-source comment stating it *"Replaces the SSL/sweet_spot_state==-1 gate"* and *"deliberately does
NOT re-use the peak-based loud_sound_detected veto (threshold_loud_break = SSL*1.2 … which would
veto silence every frame)"*. I checked for a compile-time switch between the two paths:
`awk '/^\s*#(if|ifdef|else|endif)/' ` over lines 640–880 shows the RMS block has **no preprocessor
guard** — it compiles on every environment including `k1_bench_im69d`.

**Verdict: NOT_VERIFIED.** The doc's stated mechanism (SSL x 1.2 loud-break) is the path the source
comment says was retired; the live writer of `silence` is the RMS Schmitt whose thresholds
`1ae9d4a` did not touch. Two readings survive and I cannot separate them from git alone:

- `[INFERENCE-A]` The fix is real but **misattributed** — lowering the gain moved `k1_silence_rms_raw`
  under `K1_SILENCE_RMS_ENTER`, and the SSL x 1.2 arithmetic in the doc is post-hoc narrative.
- `[INFERENCE-B]` `K1_SILENCE_RMS_ENTER/EXIT` were mutated over serial during the device session
  (both are runtime-writable `inline float`), in which case the shipped 0.04/0.08 defaults are
  **not** what produced the GATE PASS receipt at all.

Either way the receipt is **not reproducible from the committed tree**, because the constants that
gate `silence` are runtime-mutable and the doc records no `:dump` of their values at capture time.
Cheapest refuting test: re-flash `k1_bench_im69d` at `db300db`, `:dump` `K1_SILENCE_RMS_ENTER/EXIT`
before the quiet window, and log `k1_silence_rms_raw` alongside `silence`.

One magnitude I deliberately do **not** assert: I could not pin
`k1_audio_response_gain_effective()` (`i2s_audio.h:228`), which multiplies the waveform before the
RMS normalise-by-32768. The *proportionality* of `k1_silence_rms_raw` to `K1_MIC_IM69D_INPUT_GAIN`
is `[FACT]` from the code path; the *absolute* ratio of the quiet floor to `0.04f` is not, and the
G=8 receipt ("silence 0 forever") is evidence against my first estimate. Flagged, not smoothed over.

---

## 5. Uncommitted lane work — `stash@{0}`

`git stash show -p stash@{0}` ("pr40-unblock: aside post-lane dirty (note-offset helpers etc)
2026-08-06") is **unreviewed and unflashed**. Two items visible in the head of the diff:

- `audio/i2s_audio.h`: I2S DMA comments de-hardcoded from `96` / `384 B` to "compile-time tuple
  dependent". `[INFERENCE]` cosmetic, but it removes the only in-source statement of the read size
  that the freeze-guard timeout was sized against.
- `audio/k1_stm.cpp:2`: the module header re-derivation string changes
  **`125->133.33 Hz` to `125->100 Hz`**. `[FACT]` This is a frame-rate claim inside the STM bench
  TU, contradicting the repo's documented 133 Hz audio frame rate (`CLAUDE.md`, "96-sample chunks
  @ 12.8 kHz"). Whether the code or only the comment changed needs the full stash diff — the
  working tree also shows `k1_stm.cpp/.h`, `sb_tempo.cpp`, `sb_onset_beat.cpp`,
  `sb_semantic_state.cpp/.h` modified.

`[INFERENCE]` A 133.33 -> 100 Hz re-derivation in a tempo/onset-adjacent TU is a **timing**-domain
shift landing on top of the level-domain shifts of §3, still uncommitted. Full audit of the stash
was out of my remaining budget and is the highest-value next probe.

Re-run: `git stash show -p stash@{0}` · `git stash show -p stash@{0} --stat`

---

## 6. Answer to the brief's specific question

**When the mic changed and the gain was retuned (16 -> 8 -> 4), which downstream consumers of
absolute signal level were re-derived?**

**Re-derived: exactly one — `K1_MIC_IM69D_INPUT_GAIN` itself.** Every one of the three gain commits
(`70b03e5`, `7741dd3`, `1ae9d4a`) touches that single `#define` and its comment. No commit in the
chain modifies any other absolute-level constant. `[FACT]`

**Left at inherited values:** `K1_SILENCE_RMS_ENTER/EXIT` (IM73D/SPH, 2026-07-10) — the given seed;
plus `NOISE_CAL_SSL_PHASE_B_MAX_RAW`, `NOISE_CAL_SSL_TRUSTED_P90_MAX_RAW`,
`NOISE_CAL_SSL_MIN_VALID_RAW`, `NOISE_CAL_SSL_MAX_VALID_RAW` (all SPH0645-domain base values,
reached because IM73D/IM69D are mutually exclusive so the IM73D widening never compiles), and
`NOISE_CAL_SSL_BOOT_FALLBACK_RAW` (IM69D-specific but sized for G=16 and never resized). `[FACT]`

**Sharpest consequence [INFERENCE], and the one that matters most given the load-bearing
Calibration Command Policy:** the two guards whose entire job is to reject a **music-contaminated**
noise calibration — `PHASE_B_MAX_RAW 1500` and `TRUSTED_P90_MAX_RAW 650` — were sized against a
signal domain that is now 4x hotter than the one they police. At G=8, music at `max_raw` 1785
tripped the 1500 admission gate. At G=4 the same music reads ~528 and sails through both. The
`start_noise_cal` silence gate is a **human** verbal confirmation; these constants were the
**machine** backstop behind it, and the gain retune quietly removed most of their authority.

---

## 7. Verification commands (one per claim class)

```
git rev-parse db300db
git log --oneline -L 94,110:SPECTRASYNQ_K1_FIRMWARE/system/constants.h
git show --stat 7741dd3
git show 70b03e5 -- SPECTRASYNQ_K1_FIRMWARE/system/constants.h
git show 1ae9d4a -- SPECTRASYNQ_K1_FIRMWARE/system/constants.h
git show 9013ed9 -- docs/hardware/im69d130-phase0-gain8-device-proof-2026-08-05.md
git show --stat 024591d
git show 24989e5 -- SPECTRASYNQ_K1_FIRMWARE/system/constants.h platformio.ini
git log --oneline -L 700,710:SPECTRASYNQ_K1_FIRMWARE/system/globals.h
git stash show -p stash@{0} --stat
sed -n '25,60p;93,110p' SPECTRASYNQ_K1_FIRMWARE/system/constants.h
sed -n '520,535p;655,700p;845,880p' SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h
awk 'NR>=640 && NR<=880 && /^\s*#(if|ifdef|ifndef|else|elif|endif)/ {print NR": "$0}' SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h
```

---

## 8. Method risk

- Scope was git history + current source only, as briefed. No build, no device, no edits.
- `024591d` / `24989e5` level implications are `[INFERENCE]`: I read the constants and diffstats but
  did not trace every per-band normaliser through `k1_gdft_core.cpp` and the AGC path.
- `stash@{0}` was inspected only at `--stat` depth plus the first hunks. The `125->100 Hz` STM
  string is `[FACT]`; its blast radius is not established.
- The `k1_audio_response_gain_effective()` multiplier is unresolved (see §4) and bounds how far the
  RMS-threshold magnitude argument can be pushed.

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-08-06 | agent:deep-technical-analyst (SSA-3-TIMELINE) | Created — commit-anchored IM69D bringup timeline; identified five non-re-derived absolute-level constants beyond the seed; flagged the `1ae9d4a` silence-path causal claim as NOT_VERIFIED. |
