---
abstract: "S5 problem-of-record for the WS2816 de-gamma audit. VERDICT: the Main RPL look complaint IS real and recorded VERBATIM by Captain, twice on 2026-08-18 — prompt #119683 (05:13Z, pre-look-flag: 'light shows look dull and don't seem to be as snappy and lively compared to the bench K1') and prompt #119716 (13:28Z, POST-Lever-2: 'clamping/compressing/dulling down EVERYTHING… sluggish… very fucking short leash… dim as all hell… bench K1 looks like it's 30-40% brighter'). Four of the analyst's six symptom claims are sourced; two ('darks lose ~77% / trails+decays+ambience vanish' and 'full-scale white looks identical on both') are ENTIRELY UNSOURCED gamma-model output presented as observation. Captain's 30-40% is a GLOBAL brightness figure, silently re-scoped by the analyst to mid-level content. Side-by-side under real music happened twice; no photo/video/frame-capture artefact exists on disk. Decisive record lives in claude-mem SQLite user_prompts, NOT in the repo."
---

# S5 — The Problem of Record (Main RPL, 2026-08-18)

**Question:** what is the ACTUAL, RECORDED complaint about the Main RPL, in
Captain's or an agent's own words?

**Answer:** it exists, it is Captain's own words, it is verbatim, and it
**post-dates** both the look-flag close (`3b425805`) and the Lever-2 flash
(`a6149b29`). The default verdict (UNSOURCED) is **overturned** for the core
symptom, and **upheld** for two of the analyst's six claims.

## 1. Verdict table

| # | Analyst symptom claim | Recorded verbatim? | Source + date (UTC) | Confidence |
|---|---|---|---|---|
| 1 | Mid-level content 30–40% dimmer | **PARTIAL — number is Captain's, the scoping is not** | Captain prompt **#119716**, 2026-08-18T13:28:57Z: *"The bench K1 looks like it's 30-40% brighter."* Captain stated it as a **global** brightness impression of the whole show. The analyst re-scoped the same figure to "mid-level content (code 0.5–0.7)". | HIGH (quote) / HIGH (mis-scoping) |
| 2 | Darks (code ~0.3) lose ~77% → trails, decays, ambience vanish | **NO — entirely unsourced** | No record anywhere. Captain never mentioned trails, decays, ambience, or darks. This is output of the analyst's own γ=2.2 arithmetic, written in the grammar of an observation. | HIGH |
| 3 | Output "compressed" | **YES** | #119716: *"something is clamping/compressing/dulling down EVERYTHING."* | HIGH |
| 4 | "on a short leash" | **YES — verbatim idiom** | #119716: *"it feels like it's on a very fucking short leash."* | HIGH |
| 5 | Onsets read "sluggish" **though AP timing is identical** | **SPLIT** — "sluggish" is verbatim (#119716: *"It's sluggish"*); **"AP timing is identical" is unsourced.** No AP capture of the post-look-flag / post-Lever-2 state exists. The only AP block on record for this unit (#119683, 05:13Z, **pre**-look-flag) shows `conf=0.20 lock=0 agc_gain=0.072` — i.e. AP was demonstrably **not** nominal at the one moment it was measured. | HIGH |
| 6 | Full-scale white / bring-up patterns look identical on both units | **NO — entirely unsourced** | No white/full-scale parity test against the bench is recorded. The nearest record is `MAIN_RPL_FIRST_LIGHT_PASS` = Captain prompt **#119678** (04:57Z): *"1. Pri/Sec channels work - Pass"* — a channels-alive check on one unit, **not** a cross-unit full-scale comparison. The analyst's line is a **prediction of the gamma model** stated as a past observation, and it is the model's own falsification test. | HIGH |

## 2. The two recorded complaints (both Captain, both 2026-08-18)

### 2a. Pre-look-flag — prompt #119683, 2026-08-18T05:13:19Z (13:13 AWST)

> The noise-cal for this unit is off, with music this is the AP metrics:
> `[AP] SSL=172 DC=-247 max_raw=1840 follower=3216 peak_scaled=0.388 … sil_pk=824 … bpm=99.0 conf=0.20 lock=0 … raw_i16_abs_peak=83 raw_i16_rms=34.7 … gdft_trim=0.800 agc_gain=0.072 … lg_mode=2 lightshow=32`
>
> **The light shows look dull and don't seem to be as snappy and lively compared to the bench K1.**

This is the origin of every "dull-show" token on disk. It is a **side-by-side
judgement against the bench under music**, with a quantitative AP block attached.
It was closed as a look-flag gap at `3b425805` (05:22Z) and the closure is
stamped in `.claude/handoff.md` item 9 and
`docs/hardware/main-rpl-pin-receipt-2026-08-18.md` §"Look flags (2026-08-18
dull-show close)".

### 2b. Post-Lever-2 — prompt #119716, 2026-08-18T13:28:57Z (21:28 AWST)

> I have BOTH the bench K1 and the Main RPL next to each other and Main RPL is
> DEFINTELY underpeforming HARD. It looks like something is
> clamping/compressing/dulling down EVERYTHING.
>
> It's sluggish, it feels like it's on a very fucking short leash. And overall,
> it's dim as all hell. The bench K1 looks like it's 30-40% brighter.
>
> I want you to investigate this thoroughly, is it the AP, or something to do
> witth the Level-2 VP? Leave no stone unturned.

**Timing is load-bearing.** `a6149b29` (Lever-2) was committed 05:34:38Z and
flashed at epoch `1787031584` = **05:39:44Z**. No flash is recorded after it
(`f7d062dc` / `40ba48f5` are docs-only). Captain's complaint lands **~7.8 hours
after** the Lever-2 flash, on the build the unit still runs. The look-flag close
and the Lever-2 promotion **did not fix the complaint.**

### 2c. Captain hardware correction — prompts #119718 (13:42Z) and #119721 (14:32Z)

> The bench k1 runs ws2812-2020, 2 channels 160 leds each per data line
> The main RPL runs ws2812c-1313, 2 channels, 160 leds split over 2 data lines

…corrected 50 minutes later:

> Fuck, that was my mistake with the typo. The main RPL is indeed running
> ws2816c, not ws2812c.

The **different-chipset premise** the gamma hypothesis rests on is therefore
Captain-sourced, not invented. It is also **newer than the repo**: nothing on
disk records the bench as WS2812-2020, and
`docs/hardware/device-build-registry.md` does not carry this distinction.

## 3. What the handoff does and does not say

`.claude/handoff.md` item 11 still reads:

> **Captain:** eyes-on Lever-2 look (and mode 32 vs B489).

**That eyes-on has happened and it FAILED** (prompt #119716). The handoff has
not been updated. Anyone reading on-disk state alone will conclude the Lever-2
verdict is still pending, when in fact it is a recorded negative.

## 4. Side-by-side comparison artefacts

| | Happened? | Artefact on disk? |
|---|---|---|
| 13:13 AWST (pre-look-flag) | **Yes** — Captain compared under music vs bench | Only the AP metrics text block, quoted above; pasted by Captain, **not** captured by a harness. No VPAB, no frame capture. |
| 21:28 AWST (post-Lever-2) | **Yes** — *"I have BOTH the bench K1 and the Main RPL next to each other"* | **NONE.** No photo, video, VPAB dump, LED byte capture, or AP block. |

`find docs _scratch -newermt 2026-08-17 -type f \( -iname '*.png' -o -iname
'*.jpg' -o -iname '*.mp4' -o -iname '*.mov' -o -iname '*.heic' \)` returns only
four pre-existing `docs/architecture/archify/` renders — nothing from either
comparison. **There is zero pixel-domain evidence of the defect.** The whole
symptom set is unaided human eyes-on, which is legitimate Captain authority but
cannot arbitrate a 35% vs 56% vs 77% transfer-curve claim.

## 5. Method risk and what this does NOT establish

- **The decisive record is not in the repo.** It lives in claude-mem SQLite
  (`~/.claude-mem/claude-mem.db`, table `user_prompts`). A grep of the working
  tree finds only agent paraphrases ("dull-show close", "Dull mode-32 vs
  bench"). An agent that searched only on disk would have wrongly concluded the
  symptom was an analyst invention.
- **`search` alone was insufficient.** The MCP `search` tool surfaced prompt IDs
  (`#P119716`) but `get_observations` cannot fetch prompt rows — they are a
  separate table. Direct SQLite read was required.
- **Captain's complaint is qualitative.** "30-40% brighter" is an unaided visual
  estimate of the whole show, not a photometric measurement, and not scoped to a
  code range. Any hypothesis that predicts a *code-dependent* loss profile is
  **not yet discriminated** by anything on record.
- **The AP is not exonerated by any recorded measurement.** The analyst asserts
  "same DSP flags, SSL in-family, AP timing identical". The one AP block on
  record for this unit is the **pre**-look-flag capture with `agc_gain=0.072`,
  `conf=0.20`, `lock=0`. No post-fix AP capture exists to support the
  exoneration.
- **Claim 6 is the cheapest falsifier and it is unrun.** If a full-scale white
  frame on Main RPL vs bench is *not* visually equal, the in-silicon-gamma story
  is wrong. That test is asserted as already-passed and has never been done.

## 6. Re-run command (decisive record)

```bash
sqlite3 -readonly ~/.claude-mem/claude-mem.db \
  "SELECT id||' @ '||created_at||E'\n'||prompt_text FROM user_prompts WHERE id IN (119683,119716,119718,119721);"
```

Repo-side corroboration (paraphrases only, not the source):

```bash
grep -rn -i "dull" .claude/handoff.md docs/hardware/main-rpl-pin-receipt-2026-08-18.md
git log --all --format='%h %ad%n%B' --date=iso 3b425805 -1
```

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-08-18 | agent:claude-code (S5-problem-of-record) | Created. Establishes the Main RPL look complaint as Captain-verbatim and recorded twice; classifies the analyst's six symptom claims; records the absence of any capture artefact from either side-by-side. |
