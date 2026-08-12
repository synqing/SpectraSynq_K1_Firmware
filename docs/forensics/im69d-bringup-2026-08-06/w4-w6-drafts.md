---
abstract: "W4/W6 exact patch drafts. W4a: the K1_STM #else arm — verdict is LOUD BYPASS, not a fabricated SPH0645 RMS, because the missing thing is the 12/50 bench normaliser, not the RMS. W4b: k1_mic_auto_sense.cpp needs no IM69D arm (dormant + self-bypasses correctly). W6: two git-doctrine stanza steps (PREFIX, READ-SITE). Read-only; no edits applied."
---

# W4 / W6 — exact patch drafts (READ-ONLY, nothing applied)

Repo: `/Users/spectrasynq/SpectraSynq_K1_Firmware` @ branch `feat/ap-advice-phase0-im69d-gain8`

---

## W4(a) — the missing `#else` in the `K1_STM` loudness block

### Blast-radius correction (load-bearing, contradicts the brief's framing)

The brief warns "a wrong `#else` arm changes behaviour on shipping builds". It does **not**.
The whole block is inside `#ifdef K1_STM`. Only two envs define `K1_STM`:

| env | mic defines | `raw_rms_for_stm` | verdict |
|---|---|---|---|
| `k1_hardware_stm` (`platformio.ini:227`, extends `env:k1_hardware`) | **neither** → SPH0645 | stays `0.0f` | **BROKEN** |
| `k1_bench_im73d_stm` (`platformio.ini:345`, extends `env:k1_bench_im73d`) | `K1_MIC_IM73D_PDM_V1` | `im73d_raw_i16_rms` | correct |

`k1_hardware`, `k1_bench_reference`, `k1_prod_im73d` leave `K1_STM` undefined — the block
compiles out entirely. Blast radius is the **bench lane `k1_hardware_stm` only**. Both
K1_STM envs are documented NON-SHIPPABLE. This is a bench-lane defect, not a shipping defect.

### Failure mechanism (verified)

`i2s_audio.h:464` `raw_rms_for_stm = 0.0f` → no arm fires on SPH0645 →
`k1_stm_ln = (0 - 12)/50 = -0.24` → clamped to `0.0` → `agc_loudness_norm = 0` every frame.

Consumer, `k1_edgemixer.cpp:971-972`:
```
const float k1_stm_loud = k1_edge_clamp_float01(float(agc_loudness_norm));
const float depth = strength * k1_stm_loud;
```
`depth = 0` → `scale = 1.0f - 0*(1-energy) = 1.0` → `buf[i]` multiplied by 1 →
**STM modes 7 (STM_DUAL) and 8 (STM_SPECTRAL_MAP) are inert on `k1_hardware_stm`.**

### Which fix applies: **LOUD BYPASS**. No honest SPH0645 equivalent exists.

Searched the SPH domain for a per-chunk raw RMS. Findings:

1. **No raw statistic is computed at all on the SPH path.** The raw-telemetry block at
   `i2s_audio.h:424-456` has an IM73D arm and an IM69D arm and **no `#else`** — the SPH
   path computes no peak, no RMS, no near-rail count before line 457.
2. `max_waveform_val_raw` is **not** a substitute: it is a *peak* (not RMS), it is
   *post*-gain/clamp/DC-offset, and it is zeroed at `:506` and filled at `:570` — i.e.
   **after** the K1_STM block at `:457-475`, so reading it there yields the previous frame.
3. **The real missing artefact is the normaliser, not the RMS.** The constants `12.0f`
   and `50.0f` are bench-derived for the PDM int16 raw domain (comment `:459-462`:
   silence ~8, EDM ~32-60, peaks ~144). An RMS over `i2s_samples_raw` is trivially
   computable, but SPH raw int32 samples live ~6 decades higher (implied by the pedestal
   math at `:532`, `sample = raw*0.000512 + 56000 - 5120`). Pushing any SPH statistic
   through `(x - 12)/50` pins `k1_stm_ln` at `1.0` **permanently** — the inverted failure
   (always full-depth instead of always-inert). Re-deriving the SPH constants requires a
   bench measurement session; it cannot be done from source.

### Update — 2026-08-06: live bench constraint (supersedes any "derive an SPH RMS" option)

Bench measurement supplied after this analysis began: **RMS does not separate music from room
noise in ANY gain domain.** Music p50 RMS `0.0027` vs ambient p50 `0.0072` — music is *lower*;
~75% of music frames sit at or below the loudest ambient frame. Cause: the room floor is
narrowband hum (crest ~1.26, RMS≈peak) while music is peaky (crest 3-5, RMS≪peak).

Two consequences:

1. **Deriving an SPH0645 RMS is now excluded on two independent grounds**, not one. It was
   already excluded because the `12/50` normaliser is unportable; it is *additionally* excluded
   because RMS cannot perform the discrimination the gate exists to perform. **Would an SPH raw
   RMS be load-bearing for anything other than the STM loudness gate? No.** Every consumer of
   `*_raw_i16_rms` in the tree is one of: the STM gate (`i2s_audio.h:466,468` — the only control
   consumer), display-only AP serial telemetry (`i2s_audio.h:954-961`, itself IM73D/IM69D-only
   with no `#else`), or IM73D-gated auto-sense telemetry that is dormant everywhere else
   (`k1_mic_auto_sense.cpp:71,123,264`). So the single consumer that could justify deriving the
   value is precisely the one it provably cannot serve. **Derive nothing.**
2. **The LIVE IM73D/IM69D arms are also unsound.** The in-code claim at `i2s_audio.h:459-462`
   ("~8 in silence, ~32-60 under EDM") is contradicted by music p50 < ambient p50. The bug is
   therefore wider than the missing `#else`: on PDM builds the gate opens on hum and closes on
   music. **Out of W4 scope — flagged, not fixed here.** Note for whoever takes it: the crest
   discriminator (`peak/rms`) is already computable on PDM builds today, because both
   `*_raw_i16_abs_peak` and `*_raw_i16_rms` are already computed at `:439-441` / `:453-455`.

Therefore: publish an explicit bypass, mirroring `k1_mic_auto_sense.cpp:73-77` (zero the
raw fields) + `:103-106` (force `state=BYPASSED`, `reason=RAW_UNAVAILABLE`). This also
matches the consumer's own existing idiom at `k1_edgemixer.cpp:962-963`:
`if (!stm.ready) { return; // absent, not zero: ... }`.

**The distinction that matters:** `agc_loudness_norm == 0` is a *legitimate measured value*
(silence). It must not double as "no measurement exists". That collision is exactly what
hides the bug today.

### PATCH 1 of 3 — `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:463-474`

CURRENT (verbatim, lines 463-474):
```c
  {
    float raw_rms_for_stm = 0.0f;
#if defined(K1_MIC_IM73D_PDM_V1)
    raw_rms_for_stm = im73d_raw_i16_rms;
#elif defined(K1_MIC_IM69D_PDM_V1)
    raw_rms_for_stm = im69d_raw_i16_rms;
#endif
    float k1_stm_ln = (raw_rms_for_stm - 12.0f) / 50.0f;
    if (k1_stm_ln < 0.0f) k1_stm_ln = 0.0f;
    if (k1_stm_ln > 1.0f) k1_stm_ln = 1.0f;
    agc_loudness_norm = SQ15x16(k1_stm_ln);
  }
```

REPLACEMENT:
```c
  // MIC-DOMAIN SPLIT: the 12.0f/50.0f normaliser is bench-derived for the PDM
  // int16 raw domain and is NOT portable. The SPH0645 path computes no raw
  // per-chunk RMS at all (the telemetry block above has no #else arm), and its
  // raw int32 samples sit ~6 decades higher, so feeding any SPH statistic
  // through this normaliser pins k1_stm_ln at 1.0 permanently. A fabricated
  // value is worse than none: publish BYPASS and let the consumer skip.
  {
#if defined(K1_MIC_IM73D_PDM_V1) || defined(K1_MIC_IM69D_PDM_V1)
  #if defined(K1_MIC_IM73D_PDM_V1)
    const float raw_rms_for_stm = im73d_raw_i16_rms;
  #else
    const float raw_rms_for_stm = im69d_raw_i16_rms;
  #endif
    float k1_stm_ln = (raw_rms_for_stm - 12.0f) / 50.0f;
    if (k1_stm_ln < 0.0f) k1_stm_ln = 0.0f;
    if (k1_stm_ln > 1.0f) k1_stm_ln = 1.0f;
    agc_loudness_norm = SQ15x16(k1_stm_ln);
    k1_stm_loud_bypassed = false;
#else
    // No raw-RMS source in this mic domain. Mirror k1_mic_auto_sense.cpp:73-77
    // + :103-106 — zero the value AND publish the bypass, so a 0 here is never
    // mistaken for a measured silence.
    agc_loudness_norm = SQ15x16(0.0);
    k1_stm_loud_bypassed = true;
    static bool k1_stm_bypass_announced = false;
    if (!k1_stm_bypass_announced) {
      k1_stm_bypass_announced = true;
      USBSerial.println("[K1_STM] BYPASSED reason=RAW_RMS_UNAVAILABLE mic=SPH0645 "
                        "(no PDM raw RMS; 12/50 normaliser is PDM-only) "
                        "-> EdgeMixer modes 7/8 inert");
    }
#endif
  }
```

Notes:
- One-shot `static bool` guard — the print fires once per boot, not per 133 Hz frame.
  `USBSerial.println` in this function is precedented (`:483`, `:494`, `:499`).
- `k1_stm_ln`/`raw_rms_for_stm` are now `const` in the live arm; no behaviour change on
  IM73D/IM69D — the arithmetic and the emitted value are byte-for-byte the same.

### PATCH 2 of 3 — `SPECTRASYNQ_K1_FIRMWARE/system/globals.h:751`

CURRENT:
```c
inline SQ15x16 agc_loudness_norm = SQ15x16(0.0);
```

REPLACEMENT:
```c
inline SQ15x16 agc_loudness_norm = SQ15x16(0.0);
// Companion to agc_loudness_norm: true = no raw-RMS source in this mic domain,
// so the 0 above is ABSENT, not a measured silence. Default true (bypassed until
// a live arm proves otherwise). Unconditional to match agc_loudness_norm itself.
inline bool    k1_stm_loud_bypassed = true;
```

### PATCH 3 of 3 — `SPECTRASYNQ_K1_FIRMWARE/director/k1_edgemixer.cpp:962-964`

CURRENT (verbatim):
```c
  if (!stm.ready) {
    return;  // absent, not zero: leave the strip as the base effect rendered it.
  }
```

REPLACEMENT:
```c
  if (!stm.ready) {
    return;  // absent, not zero: leave the strip as the base effect rendered it.
  }
  if (k1_stm_loud_bypassed) {
    return;  // no loudness source in this mic domain (see i2s_audio.h K1_STM block):
             // absent, not zero — do not modulate by a value we never measured.
  }
```

Net effect on `k1_hardware_stm`: rendered output is **unchanged** (it was already
`scale = 1.0`, a no-op multiply). What changes is that the failure is now **declared** —
one serial line at boot and an explicit early return — instead of silently masquerading
as "the music is silent". Zero change on `k1_bench_im73d_stm` and on every non-K1_STM env.

### Re-run commands (prove current state)

```bash
cd /Users/spectrasynq/SpectraSynq_K1_Firmware
# W4a: the #if/#elif/#endif with NO #else
sed -n '463,475p' SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h
# no #else anywhere in the raw-telemetry block either (424-456)
sed -n '424,456p' SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h | grep -n '#else' || echo "NO #else -> SPH computes no raw stats"
# which envs define K1_STM, and what mic they inherit
grep -n 'K1_STM' platformio.ini
sed -n '/^\[env:k1_hardware_stm\]/,/^$/p' platformio.ini
# consumer
sed -n '958,975p' SPECTRASYNQ_K1_FIRMWARE/director/k1_edgemixer.cpp
```

---

## W4(b) — does `k1_mic_auto_sense.cpp` need an IM69D arm?

**No. It is dormant on IM69D, and it self-bypasses correctly if ever enabled.**

- **Dormant:** `K1_MIC_AUTO_SENSE_V1` is defined in exactly two envs —
  `k1_bench_im73d_mic_auto` (`platformio.ini:355`) and
  `k1_bench_im73d_mic_auto_telemetry` (`:374`) — both `extends = env:k1_bench_im73d`
  (IM73D). The IM69D env `k1_bench_im69d` (`:306`) defines neither the flag nor adds
  `+<audio/k1_mic_auto_sense.cpp>` to `build_src_filter`, so the TU is not even compiled
  into an IM69D build.
- **Self-bypasses correctly:** `:69-77` `#ifdef K1_MIC_IM73D_PDM_V1 ... #else` zeroes
  `raw_i16_abs_peak` / `raw_i16_rms` / `raw_i16_near_pct`, and `:103-106`
  `#ifndef K1_MIC_IM73D_PDM_V1` forces `state = K1_MIC_AUTO_TELEMETRY_BYPASSED`,
  `reason = K1_MIC_AUTO_TELEMETRY_REASON_RAW_UNAVAILABLE`. The zeros are never mistaken
  for measurements — that is precisely the pattern `i2s_audio.h` is missing.
- **Optional, NOT recommended now:** IM69D raw globals do exist
  (`im69d_raw_i16_abs_peak` / `_rms` / `_near_pct`, `globals.h:165` and neighbours), so an
  IM69D arm is *possible*. Adding it would flip state `BYPASSED → OBSERVE` on any future
  IM69D auto-sense env — a behaviour change with no consumer asking for it today. Leave
  as-is; revisit only if an IM69D auto-sense lane is opened.

Re-run:
```bash
grep -n 'K1_MIC_AUTO_SENSE_V1' platformio.ini
sed -n '69,77p;103,106p' SPECTRASYNQ_K1_FIRMWARE/audio/k1_mic_auto_sense.cpp
sed -n '/^\[env:k1_bench_im69d\]/,/^$/p' platformio.ini | grep -E 'MIC_AUTO|src_filter'
```

---

## W6 — git-doctrine one-liners

**File:** `/Users/spectrasynq/SpectraSynq_K1_Firmware/docs/process/SPECTRASYNQ-GIT-DOCTRINE.md`
(157 lines). **NOT edited by me.**

**Current dirty state:** `M` (modified, unstaged, uncommitted) — `git diff --stat` reports
`18 ++++++++++++++++--` = **16 insertions, 2 deletions**. The uncommitted work rewrites
stanza step 5 (adds the CHANGELOG requirement) and appends steps **6 SCOPE / 7 BIRTH /
8 SWEEP**, plus a prose pointer at `:132-133` to a sibling doc. That sibling,
`docs/process/SPECTRASYNQ-HOUSEKEEPING-DOCTRINE.md`, is **untracked (`??`)**.
So the drafts below must land as steps **9** and **10**, on top of dirty work.

**Voice/format matched:** stanza lives in a ```` ```markdown ```` fence (`:72-98`),
numbered, each step opens with an ALLCAPS keyword + colon, 2-4 wrapped lines, imperative,
no rationale inside the fence. Rationales go in prose after the fence, matching the
existing `:132-133` pattern. British English.

### Draft (a) — insert after stanza step 8, inside the fence (`:97`, before the closing ```` ``` ````)

```markdown
9. PREFIX: a `docs:` or `chore:` subject may not modify
   `SPECTRASYNQ_K1_FIRMWARE/**`. Firmware in the diff means `feat:`/`fix:` —
   split the commit if that is not true of all of it.
```

Rationale line (prose, after the fence — append to the `:132-133` block):

```markdown
Stanza step 9 exists because `7741dd3 docs(lane): phase0 gain8 code-ready note
and constants follow-up` carried a 2× microphone-gain change (`constants.h | 11 ++-`)
under a `docs:` subject — invisible to any history filtered on `feat`/`fix`.
```

### Draft (b) — insert as stanza step 10, inside the same fence

```markdown
10. READ-SITE: a proof or evidence doc section titled "<subsystem> path (code)"
    must cite the CONSUMER read-sites — `file:line` where the value is actually
    read — not merely where it is assigned. A variable nothing reads is not a path.
```

Rationale line (prose, after the fence):

```markdown
Stanza step 10 exists because the IM69D Phase 0 device-proof doc traced
`threshold_loud_break` as the "Silence latch path (code)"; it is assigned once
(`i2s_audio.h:686`) and never read anywhere in the firmware — the microphone gain
was halved on that basis.
```

### Re-run commands (prove current state)

```bash
cd /Users/spectrasynq/SpectraSynq_K1_Firmware
git status --porcelain -- docs/process/                       # M doctrine, ?? housekeeping
git diff --stat -- docs/process/SPECTRASYNQ-GIT-DOCTRINE.md   # 16 +, 2 -
sed -n '72,98p' docs/process/SPECTRASYNQ-GIT-DOCTRINE.md      # stanza fence, steps 1-8
# the motivating incidents
git show --stat 7741dd3 | head -20
grep -rn 'threshold_loud_break' --include="*.h" --include="*.cpp" --include="*.ino" SPECTRASYNQ_K1_FIRMWARE/
```

The `threshold_loud_break` grep returns exactly two hits: the assignment at
`i2s_audio.h:686` and a mention inside a comment at `:853`. **Zero read-sites.**

---

**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-08-06 | agent:ssa-w4-w6 | Created. W4a/W4b/W6 exact patch drafts, read-only, nothing applied. |
