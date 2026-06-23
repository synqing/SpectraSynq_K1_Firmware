---
abstract: "CTO/PM/Chief-Engineer handover #3 (2026-06-05) — SUPERSEDES handover #2 on tempo. Verified against the live repo (HEAD 6e0d652), NOT a session narrative, because the branch is SHARED with a concurrent workflow that rebases/interleaves under you (read §2 first). State: the tempo primitive is now STRONG — ACF-salience + harmonic-comb octave defence + perceptual prior lock real music at Acc1 56.2%, octave-doubling 0 (the octave problem handover #2 called 'hard' is SOLVED — via harmonic-comb, NOT the naive half-ratio arbiter, which was reverted; do not re-attempt that). Confidence fixed at source. The effect library is EXECUTING: modes 18 WAVEFORM_TEMPO (7.9/10 keeper) + 19 TEMPO_RIVER + 20 TEMPO_COMET, host-green, eyes-on pending. THE STROBE LAW now governs beat effects. Three skills shipped (ssa-management, load-bearing-edges, codex-offload). The one meta-law that cost the most: never relay a sub-agent's prose as fact — re-run the decisive artifact yourself."
---

# Handover #3 — K1 firmware, CTO/PM/Chief-Technical-Engineer (2026-06-05)

> Read top-to-bottom before touching anything. Written per `load-bearing-edges` (capture the
> *edges* — the why/gotchas/dependencies — not a file list) and verified against the LIVE repo, not
> a session narrative. **It supersedes handover #2 on tempo/confidence/octave** (those moved on).
> Read order: this → §2 (the shared-branch trap) → `docs/research/validation/2026-06-04-RECONCILIATION.md`.

---

## 0 · Role & standing contract
You are **CTO + CPO + Chief Technical Engineer** for SpectraSynq's K1 firmware. North star: *a
music-to-visual system that exceeds Sensory Bridge's perceptual impact* — architecture is subordinate
to that. **Founder Execution Boundary:** the Captain (Elroy) is NOT in the execution/debug/test loop;
validate on host harnesses, report **decision-grade and tight** (he is blunt, impatient, rages at
verbosity / whinging / redundant questions / asking what he already instructed). British English. **No
push / destructive / public action without explicit instruction.** Standing order: **default to
fanning out sub-agents** for heavy reading/running to conserve your context — *but* (the law that cost
the most this session) **never relay a sub-agent's prose as fact; re-run the decisive artifact
yourself before it becomes a decision/commit/doc.** (Skill: `/ssa-management`.)

---

## 1 · Where we are (one paragraph)
The audio-primitive bottleneck is **broken open and the tempo primitive is now genuinely strong.**
`sb_tempo` (ACF-salience + **harmonic-comb octave defence + perceptual prior**) locks real music at
**Acc1 56.2%, octave-doubling 0** (host-measured) and is hardware-validated (128 + 144 BPM lock on
both K1 units). Confidence is fixed at source. The **effect library is executing**: three beat-locked
modes ride the validated tempo — **18 WAVEFORM_TEMPO** (Captain 7.9/10 keeper), **19 TEMPO_RIVER**,
**20 TEMPO_COMET** (beat-flywheel PLL); two were killed on eyes-on (Beat Palette 0/10; pulse_bloom by
**THE STROBE LAW**). Three orchestration skills shipped. The next frontier is more effects + wiring
the beat into the still-beat-blind **Smart Director**.

---

## 2 · ⚠️ THE SHARED-BRANCH TRAP (read before any git action — the #1 thing that will bite you)
`wip/audio-saliency-recovery` is **shared with a concurrent workflow** (`comb-harmonic-wf_190c2c21` +
~11 `worktree-wf_190c2c21-b0f-*` worktrees). It **rebases and interleaves commits under you** — your
own commits' parents change; the HEAD moves between turns. This already happened this session (my
handover/skill commits were reordered beneath a parallel agent's tempo work).
- **Always `git log --oneline -10` fresh** before reasoning about state; never trust a remembered HEAD.
- **Commit small + often** (your checkpoint survives a rebase as a commit; uncommitted work may not).
- **Do not `git reset`/force history** on this branch — you will clobber the parallel lane.
- If you need isolation, **work in your own worktree/branch** (memory: VE-Auto-Loop did exactly this).
- Nothing is pushed. **HEAD at handover = `6e0d652`.**

---

## 3 · The state (verified commit ladder, newest first)
| commit | what |
|---|---|
| `6e0d652` | config: secondary channel boots WAVEFORM_TEMPO + `es_autumn_19_gp` palette (1401 dual-tempo) |
| `270ba72` | **fix(tempo): harmonic-comb ACF octave defence + perceptual prior — Acc1 28.1→56.2%, octave-doubling 5→0** (THE octave fix) |
| `7560e40` | tempo-comet beat **FLYWHEEL (PLL)** for reliable spawning + tempo/onset in AP_STREAM |
| `600ece5` | ssa-management skill v0.2 (mine) |
| `c0e6ad0` | **fix(tempo): confidence from the winner's sel_score (ACF×prior), not the Goertzel peak** |
| `a8bffd6` | kill Beat Palette (mode 20, Captain 0/10); Tempo Comet → mode 20; `NUM_MODES=21` |
| `af9d129` | three beat-locked modes: Tempo River (19), Beat Palette (20), Tempo Comet (21) |
| `7537c21` | Revert `pulse_bloom` (mode 19) — **THE STROBE LAW** |
| (earlier, mine) | `9eb3cee` mode-18 keeper (tag `waveform-tempo-v1`) · `0929814` ACF primitive · `ce5b076` validation+RECONCILIATION · `aef74f4/cd94fd7` saliency RC-1/RC-4 |

**Tag:** `waveform-tempo-v1` → the mode-18 keeper. **Hardware:** 1401 dev (MAC `B4:3A:45:A5:87:F8`,
`k1_hardware`) + 12201 bench (MAC `B4:3A:45:A5:89:B4`, `k1_bench_reference`, adds only
`-DSB_K1_BENCH_REFERENCE_PINMAP=1`); both flashed mode-18 era — **reflash for the new modes/octave fix
before eyes-on.** Unknown 12401 (MAC `F0:F5:BD:75:A7:FC`) — not a K1, do not flash.

---

## 4 · THE STROBE LAW (new load-bearing design rule — sits beside centre-origin & no-rainbow)
> **Beat reactivity must be SPATIAL / transport — motion THROUGH the plate — NEVER global full-field
> amplitude.** `pulse_bloom` (global brightness-on-beat) read as a "broken lightbulb / strobe" and was
> killed; Beat Palette (global palette-step on beat) scored 0/10. The keepers move *position/velocity*
> with the beat (scroll velocity, flowing river, travelling comets), not brightness. Encode this into
> every new beat-reactive effect. (Memory: `project_effect_library_bottleneck`.)

---

## 5 · Your board (next tasks)
**Recommended next push — finish the effect-library lane it's mid-stride on:**
1. **Eyes-on the new modes (19 TEMPO_RIVER, 20 TEMPO_COMET)** — host-green, **eyes-on pending**.
   Reflash 1401 with current HEAD; Captain rates; keep/kill per THE STROBE LAW.
2. **Wire tempo + onset into the Smart Director** — it is *still beat-blind* (whitelisted modes, the
   beat/onset stream unused). The tempo is now strong enough to drive it. This is the highest-leverage
   unbuilt thing.
3. **More beat-locked standalone modes** via the decomposition method, STROBE-LAW-compliant.

**Tempo hardening (mostly DONE — do not re-litigate):** octave defence ✅ (harmonic-comb), confidence
✅, PLL flywheel ✅. Remaining only if a measured need appears: novelty quality (GDFT log-domain, the
~56% ceiling itself), ceiling vs window length.

**Other lanes (prior memory):** AGC colour (A/B test designed, never run); LGP dual-channel fidelity
(`K1Optics_v1` port before trusting host visual judgement); the merge decision (this work is unpushed
on a shared wip branch — decide merge to `feat/gdft-harness`/`main`). Strategic: K1 → FE → Kickstarter.

---

## 6 · War stories & the costly near-disaster
- **Saliency closed (RC-4).** Instantaneous saliency is structure-blind (cross-confirmed 3×) → the
  pivot to a periodicity tempo primitive was correct. Do not reopen instantaneous saliency.
- **The ACF tempo win + THE NEAR-DISASTER.** I recommended **reverting the committed ACF primitive**
  on a sub-agent's confident-but-wrong "ACF is flat" claim — it would have destroyed a +15.6pp,
  later-hardware-validated gain. A forced back-test + **my own re-run** caught it. Two other relayed
  SSA claims were also wrong. Full record + the lesson: `RECONCILIATION.md`, and the
  `references/v-octave-near-disaster.md` in the ssa-management skill.
- **The octave problem — SOLVED, but NOT by my approach.** My naive half-tempo *salience-ratio*
  arbiter broke the clean metronome and was **reverted** (`8121521`). The parallel lane solved it with
  a **harmonic-comb** (sum ACF energy across a candidate period's harmonics → the fundamental wins
  over the 8th-note alias) + perceptual prior (`270ba72`). **Do not re-attempt the ratio arbiter** —
  that is the stale-claim trap; the comb is the canon now.
- **Synthetic ≠ hardware.** A clean 144 metronome *halves* in `tempo_replay` (perfect pulse train →
  all ACF sub-multiples equal) but **locks fine on real hardware.** Never panic-revert on a
  synthetic-only fail; check the device.

---

## 7 · Meta-lessons (bind yourself — these are the load-bearing ones)
1. **Never relay an SSA's prose as fact.** Re-run the decisive artifact yourself before it becomes a
   decision/commit/doc. (`/ssa-management` — its whole reason for existing.)
2. **Map ≠ territory, and here the territory MOVES.** This branch rebases under you (§2) AND a
   handover/memory can go stale within hours (this one supersedes #2). **Verify the live repo before
   you reason** — exactly how I caught that the octave problem was already solved.
3. **Run the FULL gate set.** Every `sb_tempo` change runs BOTH `tempo_replay.py` (synthetic locks) +
   `tempo_accuracy.py` (real-music Acc) — `pytest`+`pio` cover NEITHER. I shipped two tempo regressions
   by running only one.
4. **Execute the instruction; don't re-ask / don't whinge.** The Captain gives sequences — run them.
5. **`load-bearing-edges` binds your own briefs + your own validators** (audit the bent scale).

---

## 8 · Hazards
- **The shared branch (§2)** — the biggest one.
- **clangd diagnostics are FALSE POSITIVES** (`-mlongcalls`/`../hal.h`/`SFixed`/`SQ15x16`/`USBSerial`)
  — wrong toolchain. Ignore; trust the real `pio` (xtensa-gcc) + g++/clang++ host build.
- **The two tempo gates are SEPARATE from `pytest`+`pio`** (§7.3).
- **Hardware by MAC, not port** — the `k1_upload_guard.py` aborts on env↔MAC mismatch; rely on it.
  **NEVER auto-fire `start_noise_cal`.** Tempo serial stream is **probe-only**: `stream_tempo_data()`
  (`.ino`) is `#if ENABLE_TEMPO_STREAM`, defined ONLY in env `k1_tempo_probe` — flash that to watch
  `TEMPO,...,bpm=,conf=,lock=`. `k1_hardware` is silent on tempo.
- **THE STROBE LAW (§4)** — global-amplitude beat effects get killed.
- **Cursor's serial monitor grabs the port** (Errno 35) — the Captain closes it; never kill Cursor.

---

## 9 · Artifact map
- **Firmware:** `SPECTRASYNQ_K1_FIRMWARE/audio/sb_tempo.cpp` (ACF + harmonic-comb octave defence +
  prior + PLL; confidence from sel_score) · `effects/light_mode_{waveform_tempo,tempo_river,tempo_comet}.cpp`
  (modes 18/19/20) · `audio/sb_musical_saliency.{h,cpp}` (saliency, RC-1 fixed).
- **Host gates** (`scripts/regression-harness/`): `tempo_accuracy.py` (real-music Acc) ·
  `tempo_replay.py` (synthetic lock/release — the gate easy to forget) · `bt_acf_4way.py`,
  `acf_ceiling_sweep.py`, `mirex_rescore.py`, `novelty_from_wav.py`.
- **Docs (read order):** `docs/research/validation/2026-06-04-RECONCILIATION.md` (corrected truth) →
  this handover → handover #2 (`2026-06-04-cto-session-handover-2.md`, **stale on octave/confidence** —
  trust this #3 over it) → the validation trail (`validation/2026-06-04-*.md`; V-OCTAVE tombstoned).
- **Skills (Claude + Codex via `.agents/skills/`):** `ssa-management` (v0.2 — the SSA RETURN CONTRACT +
  the re-run), `load-bearing-edges`, `codex-offload`. Project gates: `k1-firmware-change-gate`,
  `sensorybridge-doctrine`. AGENTS.md carries the SSA pointer for Codex.
- **Memory:** `…/memory/MEMORY.md` + `project_{tempo_beat_foundation,effect_library_bottleneck}.md`
  (both updated with the octave/STROBE/mode state). **Trust the live repo over any of these.**
- **v3 donor (read-only):** `…/Lightwave-Ledstrip/firmware-v3` — its octave arbiter
  (`esv11_pick_top_tempo_bin_octave_aware`, `src/audio/backends/esv11/vendor/tempo.h:372` + gate
  `EsV11Backend.cpp:218-289`) targets the OPPOSITE (half-time) failure on a Goertzel domain — **the
  fork now uses harmonic-comb instead; do not transcribe v3's constants.**

---

## 10 · First five minutes
1. `git -C "<repo>" status -sb` + `git log --oneline -10` — **expect the HEAD to have MOVED past
   `6e0d652`** (the parallel lane is live). Re-orient to the real HEAD before anything (§2).
2. Read `docs/research/validation/2026-06-04-RECONCILIATION.md`, then this handover.
3. Internalise §7.3: any `sb_tempo` change runs BOTH tempo gates.
4. Reflash 1401 with current HEAD (`k1_hardware`) for eyes-on of modes 19/20; or `k1_tempo_probe` to
   re-confirm tempo lock on the serial stream.
5. Pick from §5 — recommended: eyes-on the new modes, then wire the beat into the Smart Director.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-06-05 | agent:CTO (outgoing) | Created — handover #3, verified against live HEAD 6e0d652 (supersedes #2 on tempo/confidence/octave). Captures the shared-branch trap, the SOLVED octave problem (harmonic-comb, not the reverted ratio arbiter), the confidence fix, modes 18/19/20, THE STROBE LAW, the three shipped skills, the meta-lessons (never relay SSA prose as fact; verify the moving territory; run both tempo gates), and the board (eyes-on new modes → wire the Director). |
