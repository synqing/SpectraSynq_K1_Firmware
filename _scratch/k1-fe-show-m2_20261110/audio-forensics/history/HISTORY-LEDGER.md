---
abstract: "Dated, source-cited ledger of every Captain decision and known defect in the K1 audio front end (loud guard, per-band and broadband AGC, level follower / peak_scaled, silence gate and go-dark, mic gain and sensitivity, noise calibration, palette-vibrancy workaround). Answers whether the Captain ever turned the loud guard off (he did not; no source, build-flag, NVS or BLE path ever did), and states for each fix whether it is in a6bad318 (= FE release head 8b202f46 plus prepared-show fixes) and active in the Main RPL build (env k1_main_rpl_show_bench)."
date: 2026-11-10
author: agent:claude-opus-5.5 (af-history, K1-FE-SHOW audio forensics, wave 3)
scope: read-only history; no device, no build, no repo writes outside this folder
---

# K1 audio front end — history ledger (10 Nov 2026)

## Plain-English summary

- **The loud guard was never turned off.** It has been on by default since 18 June 2026, after the Captain looked at it running and said "Looks good to me". No commit on any branch, no build setting, no saved setting and no BLE control has ever switched it off. The only way to switch it off is a typed serial command, and that is forgotten at the next reboot.
- **The Captain's memory of a "flaw that hurt the visuals" is right about the flaw, wrong about the switch-off.** The flaw has been seen three times (2 July palette collapse, 10 July slow release, 18 August "AGC pinned at the loud-guard floor"). Each time it was patched around or tuned, never removed.
- **The feature the Captain did order switched off was standby dimming (silence go-dark), on 9 August,** because a dark plate looks like a dead unit. That may be the decision being remembered.
- **Today's measurement fits the flaw exactly.** The guard decides "too loud" from `peak_scaled`, which is a ratio to the recent peak, not a loudness. Dense music keeps that ratio high at any volume, so the guard cuts the whole spectrum to about a quarter in a normal room with nothing clipping.
- **Two fixes that matter were never put into the Main RPL or FE builds:** the 14 August sub-110 Hz filter (HF-63) and the noise-cal partial-commit. Both exist in source behind bench-only flags.

Labels: [FACT] = read in source, git, or a cited record; [INFERENCE] = derived from facts; [HYPOTHESIS] = untested.
Build identities: **a6bad318** = branch `mcpp/next-phase-fixes` head-1. **8b202f46** (FE release head) is an ancestor of a6bad318 [FACT: `git merge-base --is-ancestor 8b202f46 a6bad318` → true], and every fix checked below had the same ancestry answer for both. **Main RPL build** = a6bad318, env `k1_main_rpl_show_bench` = `k1_main_rpl_im69d` + rewire + rtrace, which extends `k1_hardware` [FACT: raw/platformio.ini@a6bad318:291-337].

---

## 1. Timeline

Classification key: **PROPOSAL** = suggested, or committed without a recorded passing test. **HISTORICALLY VERIFIED** = a test, build or measurement passed in that session; checked against a6bad318 where stated. **SUPERSEDED** = overridden by a later decision or by source.

| # | Date (AWST) | What happened / was decided | Who | Source | Class |
|---|---|---|---|---|---|
| T1 | 2026-06-15 | Static per-bin GDFT noise subtraction disabled: runtime evidence showed it zeroed VP chroma after a valid noise cal | agent (pre-fork) | [FACT] constants.h:167-173@a6bad318 (`K1_GDFT_STATIC_NOISE_SUBTRACTION_ENABLED 0`); claude-mem #77913 | HISTORICALLY VERIFIED |
| T2 | 2026-06-17 19:01 | Loud guard created in SensoryBridge-main 9 as a "loud-room guard candidate": `K1_LOUD_GUARD_V1`, runtime `:k1_loud_guard=on/off/status`, **default OFF** (`k1_loud_guard_enabled = false`) | agent | [FACT] sb9 `301e536`; raw/sb9-loud-guard-origin-commits.txt | SUPERSEDED by T3/T5 |
| T3 | 2026-06-17 18:54 | **Captain eyes-on acceptance with the guard ON** (and vivid pre-comp on): "Looks good to me". Main K1 F887A500 | **Captain** | [FACT] sb9 `0bb285c` docs/hardware/device-build-registry.md:39; raw/sb9-jun17-19-context.txt | HISTORICALLY VERIFIED |
| T4 | 2026-06-18 13:45 | Main-only response gain 3.0 → 1.0: 3.0 drove normal 55 dB-A playback into AGC floor-pin | agent (device evidence) | [FACT] sb9 `6d8b8d3`; platformio.ini:115-118@a6bad318 | HISTORICALLY VERIFIED |
| T5 | 2026-06-18 18:12 | "Default accepted live posture on": `k1_loud_guard_enabled` false → **true**, `VP_VIVID_PRECOMP` false → true. 58 AP rows of loud music: clip 0, near-rail 0 | agent implementing T3 | [FACT] sb9 `72cb650` + registry row `2add150`; raw/sb9-2add150-registry-line.txt | HISTORICALLY VERIFIED |
| T6 | 2026-06-19/20 | Waveshare dual-mic: guard pressure uses the louder of two mics while AP uses one ("account dual mic envelope" fix). Proposed a "guard-neutralised" bench run; still OPEN as Q18 on 30 July | agent | [FACT] sb9 `ba55204`; claude-mem #66868, #66870; sb9 `374c8df` (raw/sb9-374c8df-loudguard-lines.txt:989) | PROPOSAL (Waveshare lane; `K1_DUAL_MIC_ENABLED` is 0 on K1) |
| T7 | 2026-06-21 | Captain eyes-on: "louder → dimmer" inverse seen in both legs, blamed on the broadband AGC's single gain | **Captain** + agent | [FACT] device-build-registry.md:593@a6bad318; raw/registry-line593-captain-louder-dimmer.txt | HISTORICALLY VERIFIED |
| T8 | 2026-06-23 | Fork to SpectraSynq_K1_Firmware carries guard ON in globals.h with the stale platformio comment "Default OFF via k1_loud_guard_enabled=false" | agent | [FACT] `ed56dfb5`; claude-mem #68260, #78027; raw/git-loud-guard-enabled-diff-lines.txt | the comment was SUPERSEDED by T13 |
| T9 | 2026-06-30 | Per-band AGC (`SB_AGC_PERBAND_V1`, now `K1_AGC_PERBAND_V1=1`) promoted to `k1_hardware`. Agent telemetry A/B on F887A500 (cross-band spread 0.000 → median 0.145). No Captain eyes-on of the fix is recorded | agent | [FACT] `2e2800d1`, `7677e078`; platformio.ini:179-187@a6bad318 | HISTORICALLY VERIFIED |
| T10 | 2026-07-01 | IM73D input gain stacks with SENSITIVITY 2.4 (g=15 would rail every loud frame) | agent | claude-mem #73464 | SUPERSEDED (IM73D deprecated by Captain 2026-08-10; profile tombstoned in `1bdf54d0`) |
| T11 | 2026-07-02/03 | `K1_PALETTE_VIBRANCY_V1`: works around the collapse chain "loud/dense music → AGC + loud-guard attenuate GDFT → chroma flatness → weak centroid → held-hue freeze". **Captain eyes-on PASS 3 July** | agent; **Captain** pass | [FACT] `ae5d90a3`; platformio.ini:206-220@a6bad318; user memory `palette-vibrancy-v1-shipped.md` | HISTORICALLY VERIFIED |
| T12 | 2026-07-10 | `a9ff00ca` claims broadband `agc_envelope` is "DEAD on device … silence gate permanently closed at every volume". The source shows a different cause: under `K1_AGC_PERBAND_V1` the broadband code is not compiled, so `agc_envelope` is never updated (see D6) | agent | [FACT] commit body (raw/commit-messages-key.txt); k1_gdft_core.cpp:518,621-698@a6bad318 | the observation stands; its stated cause is SUPERSEDED |
| T13 | 2026-07-10 | AP signal-robbery audit, item 1: the 2.20 s GDFT release and flat floor-cut were untuned rebrand defaults. A/B of modes 0/1/2 on bench B489 (IM73D): recovery 5.54 → 1.94 s, no limit cycle, no onset/tempo regression. **"Captain hardware sign-off 2026-07-10 → default mode 2"**. Guard engaged only through the **peak-pin** path; spec-sat never fired | agent; Captain sign-off as recorded by the agent | [FACT] `e47877a2`; raw/k1_loud_guard_release_retune_ab_2026-07-10.md@a6bad318 ("Definitive A/B" section). No Captain wording for the sign-off was found in deja | HISTORICALLY VERIFIED (bench IM73D only, not IM69D and not Main RPL) |
| T14 | 2026-07-10 | Silence go-dark default-flipped ON (`STANDBY_DIMMING` true). Captain eyes-on: "Exactly as it should." | **Captain** | [FACT] `b538b145` | SUPERSEDED by T19 |
| T15 | 2026-07-10 | Silence threshold moved to an SSL-derived Schmitt trigger, replacing the dead `dynamic_agc_floor_scaled` (pinned at 100) | agent | [FACT] i2s_audio.h:1179-1193@a6bad318; claude-mem #89718, #122768 | HISTORICALLY VERIFIED |
| T16 | 2026-07-17 | Silence gates characterised: the tempo silence gate is program-relative, the amplitude gate absolute | agent | claude-mem #81479; user memory `cal-silence-gate-never-waived.md` | HISTORICALLY VERIFIED (source read) |
| T17 | 2026-08-05/06 | IM69D input gain G=8 → G=4 (silence never latched at 8), then reverted to G=8 (the reasoning for G=4 was wrong; G=8 keeps SSL margin) | agent (Cursor) | [FACT] `1ae9d4ae`, `dff1d0d5`; constants.h:121-131@a6bad318 (`K1_MIC_IM69D_INPUT_GAIN 8.0f`) | HISTORICALLY VERIFIED |
| T18 | 2026-08-06 → 08-13 | IM69D silence: peakiness break 2.10 → level AND peakiness → SSL-relative level → fraction 4.0 → 2.5 → scoped to IM69D at 1.75 after the **Captain recalibrated both units**. Profile `IM69D130_UNIT2` populated | agent; Captain recal | [FACT] `acd5f813`, `12492867`, `1d97dc47`, `3a6098a4`, `a8b1912a`, `d1fae012` | HISTORICALLY VERIFIED (bench B489 and Unit 2, not Main RPL) |
| T19 | 2026-08-09 (landed 08-11) | **Captain order: STANDBY_DIMMING struck permanently.** `silent_scale` is pinned at 1.0 on Core 0 and the NVS value is ignored. Reason: "K1 has no indicator LEDs, so silent_scale → 0 is indistinguishable from a dead unit" | **Captain** | [FACT] `d781dd73` (ancestor of a6bad318); i2s_audio.h:1494-1500@a6bad318; globals_config.cpp:80 | HISTORICALLY VERIFIED; **this is the only Captain "turn it off" decision in the audio front end** |
| T20 | 2026-08-11 | Telemetry `mode=` renamed to `lg_mode=` after the loud-guard mode was misread as lightshow mode and gave a false PASS | agent | [FACT] `fc82b928`; claude-mem #90523 | HISTORICALLY VERIFIED |
| T21 | 2026-08-13/14 | Colour forensics: HF-61 refuted. **HF-63 root cause: sub-110 Hz energy, which the plate cannot show, was setting `max_waveform_val_raw`, the reference for silence, the AGC floor and the follower.** Fix `K1_AP_SUBSONIC_HPF_V1` (cutoff from NOTE_OFFSET) and `K1_CAL_PARTIAL_COMMIT_V1`, **both bench-only** | agent; witness-mic method was the Captain's idea | [FACT] `2b99dd54`, `b520db2e`, `398f19c6`, `7e3de332`; user memory `colour-forensics-golden-oracle.md`; platformio.ini:545-546@a6bad318 ("14 Aug HF-63 fix, **never shipped**") | HISTORICALLY VERIFIED on bench; **not shipped** |
| T22 | 2026-08-15 | "Zero AP drive at classified silence" behind `K1_AP_DRIVE_CONTRACT_V1` | agent | [FACT] `fa186b34`; flag only in `k1_bench_im69d_ap_integrity_probe` (platformio.ini:881-893) | PROPOSAL for product (probe env only) |
| T23 | 2026-08-18 | S6 red-team on Main RPL 9087A500: "AGC pinned at its loud-guard floor" (`agc_gain=0.072` vs computed floor 0.0765 at `gdft_trim=0.800`, −22.9 dB), "input starved −51.9 dBFS", "**loud guard attenuating with no live reason**". Ship path: "gamma killed → AGC/loud-guard fix" | agent swarm | [FACT] docs/forensics/ws2816-degamma-audit-2026-08-18/S6-ap-redteam.md (in a6bad318); claude-mem #93763; raw/deja-8554209d-lockin.txt L812, L848-850 | PROPOSAL (mechanism) |
| T24 | 2026-08-18/19 (same session) | **Lock-in instance retired**: later reading `gdft_trim 0.919`, floor 0.0905, `agc_gain 0.1668` (1.84× floor). "S6's mechanism stands; its instance does not." Both A/Bs were also void: no config parity (CHROMA 0) | agent | [FACT] raw/deja-8554209d-lockin.txt L1499, L1404; user memory `main-rpl-config-parity.md` | SUPERSEDES T23's instance |
| T25 | 2026-08-19 | AGC and follower alphas made dt-referenced at 100 Hz (`K1_AGC_DT_CLOCK_V1`, default 1). The per-frame `NOISE_ALPHA` had run 1.66× slower in wall-clock time on the RPL | agent (Cursor) | [FACT] `dec5fb53`; k1_agc_dt_clock.h:11-12; raw/deja-8554209d-lockin.txt L1753 | HISTORICALLY VERIFIED |
| T26 | 2026-11-04 | **Captain: "the K1 will not go silent"** (B489 bench). VU and silence RMS moved onto the subsonic-filtered band, under the same bench-only flag. "Flag remains off in every shipping env" | **Captain** report; agent fix | [FACT] `e04c73bd`; platformio.ini:545-547@a6bad318 | HISTORICALLY VERIFIED on bench; not shipped |
| T27 | 2026-11-10 | Persist audit: `k1_loud_guard` marked CMD_PERSISTS corrected to 0 (RAM `k1_loud_guard_*` only) | agent | [FACT] docs/forensics/runtime-evidence/20261110-fe-show-fixes/serial-cmd-persist-audit.md:29 | HISTORICALLY VERIFIED (source read) |
| T28 | 2026-11-10 | Lead's Main RPL measurement on a6bad318 `k1_main_rpl_show_bench`: `k1_loud=1 lg_mode=2`; raw peak 80–270 against a ~1517 clip point; 0 clipped samples; `peak_scaled ≥ 0.92` up to 70 % of the time; `gdft_trim` falls to 0.34 in the final chorus; raw RMS about −59 dBFS | lead | brief (not re-measured here) | lead's measurement |

---

## 2. Did the Captain decide to turn the loud guard off?

**Answer: No. [FACT] The loud guard has never been turned off by any durable means, on any branch, in either repository.**

What was checked, and what it showed:

1. **Source default.** In SpectraSynq_K1_Firmware, `git log --all -G 'k1_loud_guard_enabled *= *false'` matches only `ed56dfb5` and Omnara index checkpoints, and every match is the **stale platformio comment** "Default OFF via k1_loud_guard_enabled=false". `e47877a2` removed it on 10 July. The `globals.h` value has been `true` in every commit since the fork [FACT: raw/git-loud-guard-default-history.txt, raw/git-loud-guard-enabled-diff-lines.txt; globals.h:128@a6bad318]. In SensoryBridge-main 9 the value was `false` for one day only (the `301e536` candidate, 17 June). It was flipped to `true` by `72cb650` (18 June) after the Captain approved it running with the guard on [FACT: raw/sb9-loud-guard-origin-commits.txt].
2. **Build flags.** `-DK1_LOUD_GUARD_V1` is in `[env:k1_hardware]` (platformio.ini:164@a6bad318) and reaches `k1_main_rpl_im69d`, `k1_main_rpl_show_bench` and `k1_fe` through inheritance. No `build_unflags`, `-U` or `=0` for it exists in any commit [FACT: `git log --all -G 'UK1_LOUD_GUARD_V1|K1_LOUD_GUARD_V1=0|undef K1_LOUD_GUARD_V1'` → empty].
3. **Saved settings (NVS).** No config or persistence field holds the guard state [FACT: `git grep -i loud_guard a6bad318 -- persistence/ config_types.h globals_config.cpp control/ network/` → empty]. The serial handler `serial_set_k1_loud_guard()` (serial_menu.cpp:505-517) writes RAM only, and the 10 November persist audit agrees (row 29).
4. **BLE / Deck.** `docs/protocol/k1-ble-midi-map.json` has no loud-guard control [FACT: `git grep -i loud a6bad318 -- docs/protocol/k1-ble-midi-map.json` → empty].
5. **Runtime.** `:k1_loud_guard=off` exists but is forgotten at the next reboot. No session in the deja snapshot was found sending it or printing `K1_LOUD_GUARD: off`. Every status dump found reads `K1_LOUD_GUARD: on` (e.g. raw/deja-8554209d-loud.txt, 18–19 August).
6. **Governance.** No loud-guard ruling exists in `CANONICAL_DECISIONS.md`, `~/K1_Launch_Planning` or `K1-System-R3/docs` [FACT: raw/governance-docs-loud-guard-grep.txt; the only hit is an architecture note].

**Every recorded Captain decision about the guard points towards keeping it on:**

| Date | Decision | Evidence |
|---|---|---|
| 17 June | Accepted, running with the guard on: "Looks good to me" | T3 |
| 18 June | Made on by default | T5 |
| 10 July | Default mode 2 signed off | T13 (agent-recorded; Captain wording not found) |

**What the Captain is probably remembering** [INFERENCE]:

- **(a) 9 August: the Captain struck STANDBY_DIMMING (silence go-dark)** (T19). This is the one audio-front-end feature he really ordered off, and it was removed in source. It concerns silence, not loudness.
- **(b) The loud-guard flaw is real and documented,** but each time it was patched rather than removed:
  - 2 July: palette collapse, blamed on "AGC + loud-guard attenuate GDFT". Fixed with the vibrancy workaround.
  - 10 July: slow 2.2 s release. The release was shortened.
  - 18 August: "AGC pinned at the loud-guard floor … attenuating with no live reason". The ship path said "AGC/loud-guard fix"; no such fix was ever committed.
- **(c) A 20 June Waveshare proposal for a "loud-guard-neutralised" bench run** (T6). It was never run (still OPEN Q18 on 30 July).

**Evidence that is missing:**

- Deja ends at 2026-11-10T08:21Z and finds only about a third of past fixes.
- The 10 July conversation in which the Captain signed off mode 2 was not found, so its wording is unverified.
- A runtime-only `:k1_loud_guard=off` typed in an uncaptured terminal would leave no trace. Even so, it could not have survived a reboot.

---

## 3. Known defects

"In a6bad318" means the fix commit is an ancestor [FACT: raw/ancestry-check.txt; identical answers for 8b202f46]. "Active on Main RPL" means its gating flag is compiled into `k1_main_rpl_show_bench` [FACT: raw/flag-defaults-a6bad318.txt].

| ID | Defect | Symptom | Root cause as established | Fix commit(s) / branch | In a6bad318? | Active on Main RPL? | Status |
|---|---|---|---|---|---|---|---|
| D1 | **The loud guard's peak-pin trigger measures "near the recent peak", not loudness** | GDFT trim falls to 0.32–0.34 on dense music at ordinary room level with nothing clipping (T28). "Attenuating with no live reason" (T23). Guard engaged only through peak-pin (T13) | [FACT] `peak_pin_now = waveform_peak_scaled >= 0.92` (i2s_audio.h:246); `peak_scaled = max_waveform_val / follower` (:1268); duty > 0.60 → `gdft_target = 0.32` (:272-273). [INFERENCE] The ratio is relative to the follower, so dense passages hold it near 1 at any volume | **none on any branch** (`e47877a2` only changed release and floor-cut) | n/a | defect is active | **OPEN** |
| D2 | Loud-guard trim cuts the AGC target, not just peaks | Spectral path cut to about 0.23× (−12.6 dB) in the final chorus | [FACT] trim multiplies `effective_target` (0.25 with `VP_FIX_AGC_SOFT_KNEE=true`, globals.h:618) and lowers `agc_gain_floor` (k1_gdft_core.cpp:509-514); floor-cut and ceiling knee follow (:595-606). [INFERENCE] At trim 0.34: target 0.085, then floor-cut → ~0.0585 against an untrimmed 0.25. This assumes the band gain has converged and is not held at its 10× cap or frozen by the gate | none | n/a | active | **OPEN** (consequence of D1) |
| D3 | 2.20 s GDFT release (untuned rebrand default) | Spectrum held down ~2.2 s into quiet tails | [FACT] AP audit item 1 | `e47877a2` (mode 2, 0.80 s), branch `lane/loud-guard-release-retune` → main line | YES | YES (`k1_loud_guard_mode` default 2) | FIXED (validated on bench IM73D only) |
| D4 | Flat floor-cut erased quiet bins | Quiet detail lost while guard engaged | [FACT] `out -= depth·0.10` | `e47877a2` (hybrid cut) | YES | YES | FIXED |
| D5 | Stale "Default OFF" comment in platformio | Agents believed the guard was off (#68260, #77913, #78027) | [FACT] comment contradicted globals.h | `e47877a2` | YES | n/a | FIXED |
| D6 | **`[AP]` telemetry `agc_env` is a dead field and `agc_gain` shows the bass band only** | 10 July "broadband AGC dead, gate permanently closed" and 18 August "agc_env=0 → starved input closed the gate" were both read from this field | [FACT] the print uses `agc_envelope` and `agc_bands[0].gain` (i2s_audio.h:1680-1681). `agc_envelope` is updated only in the broadband `#else` (k1_gdft_core.cpp:631-651), which is not compiled under `K1_AGC_PERBAND_V1=1` | none | n/a | active | **OPEN** (instrument defect) |
| D7 | Code comment says per-band AGC is "DEFAULT OFF … k1_hardware compiles the #else" | Misleads readers about which AGC runs | [FACT] k1_gdft_core.cpp:520,540-541 vs platformio.ini:187 | none | n/a | n/a | OPEN (comment only) |
| D8 | Broadband single-gain AGC: "louder → dimmer" | Captain-observed 21 June (T7) | [FACT] one global gain from mean magnitude | `2e2800d1` / `f1e39e8d` (per-band) | YES | YES (`K1_AGC_PERBAND_V1=1` inherited) | FIXED (agent telemetry A/B; no Captain eyes-on recorded for the fix) |
| D9 | AGC gain freezes while gated (open at 4×, close at 2.5× noise floor), possible lock-in | 18 Aug: bass gain 0.072 below its floor | [FACT] per-band gate and freeze, k1_gdft_core.cpp:574-585. [INFERENCE] lock-in needs input that stays below 4× floor | none | n/a | mechanism active | **OPEN — PROPOSAL** (instance retired T24; not reproduced since) |
| D10 | Palette collapse on loud/dense music | Handful of colours; held-hue freeze | [FACT] chain in platformio.ini:206-211 (cause includes the loud guard) | `ae5d90a3` `K1_PALETTE_VIBRANCY_V1` | YES | YES (k1_hardware:220, inherited) | PARTIALLY FIXED (symptom fixed with Captain PASS; the upstream attenuation D1/D2 remains) |
| D11 | Dead silence-floor tracker (`dynamic_agc_floor_scaled` pinned at 100) | Quiet room never latched silence | [FACT] #89718, #122768; i2s_audio.h:1173-1179 | behaviour: SSL Schmitt (T15, in a6bad318). Dead-code removal `eaa44926` is only on `lane/k1-vj-ble-deck8` | behaviour YES; cleanup NO | behaviour YES | PARTIALLY FIXED (dead code remains) |
| D12 | IM69D: RMS cannot separate music from the room floor | Silence would not latch, or latched in music | [FACT] k1_audio_profile.h:60-79@a6bad318 | `12492867`, `1d97dc47`, `3a6098a4`, `a8b1912a`, `d1fae012` | YES | YES (`K1_MIC_IM69D_PDM_V1` in env) | FIXED on bench B489 and Unit 2; [INFERENCE] the "UNIT2" profile is applied to Main RPL 9087A500 without a Main-RPL measurement |
| D13 | **Sub-110 Hz energy sets the silence / AGC-floor / follower reference (HF-63)** | Colour twitch; "will not go silent" (Captain, 4 Nov) | [FACT] memory `colour-forensics-golden-oracle.md`; commit `e04c73bd` | `2b99dd54`, `b520db2e`, `e04c73bd` behind `K1_AP_SUBSONIC_HPF_V1` | YES (code) | **NO** (flag only in `k1_fe_bench_b489`, `k1_bench_im69d_hpf`; platformio:545-546 "never shipped") | **OPEN on product** |
| D14 | Noise cal all-or-nothing throws away a valid DC | Stale DC pedestal no later cal can clear | [FACT] `398f19c6` body | `398f19c6` `K1_CAL_PARTIAL_COMMIT_V1` | YES (code) | **NO** (flag only in `k1_bench_im69d_calfix`) | OPEN on product |
| D15 | AGC and follower time constants tied to frame count | RPL tracked 1.66× slower in real time | [FACT] T25 | `dec5fb53` `K1_AGC_DT_CLOCK_V1` | YES | YES (default 1, k1_agc_dt_clock.h:12) | FIXED |
| D16 | Response gain 3.0 over-drove into AGC floor-pin | Normal playback pinned | [FACT] T4 | sb9 `6d8b8d3` → `DEFAULT_AUDIO_RESPONSE_GAIN=1.0f` | YES | YES | FIXED |
| D17 | Static noise subtraction zeroed chroma after a valid cal | VP chroma zero, AP alive | [FACT] T1 | disabled (`=0`, constants.h:173) | YES | YES | FIXED (by disabling) |
| D18 | Telemetry `mode=` collision | False PASS on a dead plate | [FACT] #90523 | `fc82b928` | YES | YES | FIXED |
| D19 | Standby dimming made a silent unit look dead | Dark plate = "dead unit" | [FACT] T19 | `d781dd73` (Captain order) | YES | YES (`silent_scale` pinned 1.0) | CLOSED (feature struck) |
| D20 | Input under-driven on the Main RPL | Raw peak ≤ 270 of ~1517 headroom; −59 dBFS RMS (today); −51.9 dBFS (18 Aug) | [FACT] G=8 (constants.h:131); factory SENSITIVITY 2.4 (globals_config.cpp:72); the unit runs 2.7 from saved settings (lead). [INFERENCE] about 15 dB of headroom unused at the input | none for Main RPL | n/a | active | **OPEN** |
| D21 | FE line-in freezes the loud-guard GDFT trim | Line-in spectrum stays trimmed at its last mic value | [FACT] `k1_loud_guard_update` is skipped when line-in is active (.ino:1074-1080), but `process_GDFT` still applies `k1_loud_gdft_trim` (k1_gdft_core.cpp:509-514); nothing resets the trim on a source switch. [HYPOTHESIS] visible only if the switch happens while trim < 1 | none | n/a | not Main RPL (k1_fe only) | **OPEN — untested** |
| D22 | IM73D gain double-counted SENSITIVITY | Railing at g=15 | [FACT] #73464 | IM73D tombstoned (`1bdf54d0`) | YES | n/a (IM69D unit) | CLOSED (mic deprecated) |
| D23 | Waveshare dual-mic guard mismatch | Guard driven by the louder mic | [FACT] #66868 | sb9 `ba55204` | n/a (other repo) | n/a | OPEN on Waveshare (Q18), N/A on K1 |
| D24 | Bench look values exist only in B489 saved settings | Main RPL vs bench A/Bs void | [FACT] memory `main-rpl-config-parity.md` | none (config) | n/a | Main RPL at factory look defaults unless set since | OPEN (process: `:dump` and diff first) |

---

## 4. The five most consequential open issues

1. **D1 + D2: the loud guard cuts the whole spectrum because the music is dense, not because it is loud.**
   - Measured today: `gdft_trim` 0.34 with raw peaks ≤ 18 % of clip and 0 clipped samples.
   - The trigger is the follower-relative `peak_scaled ≥ 0.92` (i2s_audio.h:246, :272-273).
   - The trim then scales the AGC target itself (k1_gdft_core.cpp:509-514), so the spectral path drops to about 0.23×.
   - Two earlier records show the same thing: on 10 July only peak-pin ever engaged the guard, and on 18 August the guard was "attenuating with no live reason".
   - [INFERENCE] This is the "design flaw that hurt the visual pipeline" the Captain recalls. It was never fixed and never switched off.
2. **D13: the HF-63 sub-110 Hz fix was never shipped.** It is not in Main RPL and not in `k1_fe`. Sub-bass the plate cannot show still sets the reference for silence, the AGC floor and the follower (and therefore `peak_scaled`, which feeds D1). The Captain's "will not go silent" on 4 November is the same family. Evidence: platformio.ini:545-547; commit `e04c73bd` ("Flag remains off in every shipping env").
3. **D6: the AGC telemetry is misleading.**
   - `agc_env` is permanently 0 under per-band AGC, and `agc_gain` is the bass band only.
   - Two past investigations (10 July, 18 August) drew AGC conclusions from these fields.
   - Any lock-in claim on today's capture needs per-band gains (`agc_bands[0..3]`), not the `[AP]` line.
   - Evidence: i2s_audio.h:1680-1681; k1_gdft_core.cpp:518,621-651.
4. **D20: the Main RPL microphone input is under-driven,** −59 dBFS RMS with peaks ≤ 270 of ~1517. A weak input is what lets the gated-freeze lock-in (D9) happen, and it lowers the silence-gate margins. No gain derivation exists for unit 9087A500. The IM69D profile and the G=8 choice were measured on B489 and Unit 2.
5. **D9 / D21: two latent traps.**
   - D9: the per-band AGC freezes while gated. The lock-in was real once (18 August) and has no guard.
   - D21: on the FE product, switching to line-in after loud mic music would leave the spectrum trimmed indefinitely.
   - Both are unverified on hardware.

---

## 5. Method and evidence

- **Git (read-only):** `/usr/bin/git log --all -S/-G/--grep` across SpectraSynq_K1_Firmware and `~/SensoryBridge-main 9`; `merge-base --is-ancestor` for 45 commits (raw/ancestry-check.txt).
- **Source:** files at a6bad318 saved under raw/ as `<file>@a6bad318`.
- **claude-mem:** observations #66868, #68260, #73464, #77913, #78027, #78048, #81466, #81479, #89711, #89718, #90523, #92343, #93763, #93981, #122768.
- **deja** (snapshot ssq-20261110): item `claude:8554209d-fce0-4e9a-9146-f9e87e83f641`, terms "loud" and "LOCK-IN" (raw/deja-8554209d-*.txt).
- **raw/ index:**
  - Settings and source: platformio.ini, i2s_audio.h, k1_gdft_core.cpp, constants.h, globals.h, serial_menu.cpp and the .ino, all at a6bad318.
  - Loud-guard history: git-loud-guard-default-history.txt, git-loud-guard-enabled-diff-lines.txt, sb9-*.txt (origin, Captain acceptance, default-on, Waveshare).
  - Fix tracking: ancestry-check.txt, non-ancestor-followup.txt, flag-defaults-a6bad318.txt.
  - Commits and records: commit-messages-key.txt, git-log-audio-frontend-*.txt, k1_loud_guard_release_retune_ab_2026-07-10.md@a6bad318, registry-line593-captain-louder-dimmer.txt, governance-docs-loud-guard-grep.txt, deja-8554209d-loud.txt, deja-8554209d-lockin.txt.
- **Re-check the decisive item:**
  - `cd ~/SpectraSynq_K1_Firmware && /usr/bin/git log --all --format='%h %ad %s' --date=short -G 'k1_loud_guard_enabled *= *false|UK1_LOUD_GUARD_V1|K1_LOUD_GUARD_V1=0'` → only `ed56dfb5` / Omnara / `e47877a2`, and all of those are the comment.
  - `cd ~/"SensoryBridge-main 9" && /usr/bin/git show 72cb650 -- SENSORY_BRIDGE_FIRMWARE/system/globals.h` → the false → true flip.
- **Not done:** no device, serial, build, or emulator run. Today's numbers come from the lead's brief and were not re-measured.

---
**Document changelog**

| Date | Author | Change |
|---|---|---|
| 2026-11-10 | agent:claude-opus-5.5 (af-history) | Created: timeline (28 rows), loud-guard turn-off verdict, 24-row defect table with ancestry and Main-RPL activation, top-5 open issues. |
