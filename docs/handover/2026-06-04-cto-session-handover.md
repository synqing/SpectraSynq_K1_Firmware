---
abstract: "CTO/PM/Chief-Engineer session handover, 2026-06-04. The #1 product gap (effect library) is BLOCKED on one upstream thing: a musical audio primitive that's reliable on REAL music. This session diagnosed (with a real swarm) that the saliency 'FAIL' was misattributed — two self-inflicted bugs (an invented self-ratchet gate + a structurally-broken benchmark), not a weak detector; a measured gate-only fix already flips 2/4 criteria. Names the meta-flaw (edge-incomplete canonisation) and ships two skills (load-bearing-edges, codex-offload) to stop it recurring. Immediate next task: the Step-1+Step-2a saliency experiment. Read this fully before acting."
---

# Handover — K1 firmware, CTO/PM/Chief-Technical-Engineer (2026-06-04)

> **⚠️ UPDATE 2026-06-04 (later) — the "next task" in §2 below is STALE.** Saliency is CLOSED
> (RC-4 confirmed — instantaneous saliency is structure-blind; pivot to periodicity justified). The
> tempo **ACF-salience primitive LANDED** (`0929814`, `sb_tempo.cpp`) and is **hardware-validated**
> on 1401 (128 BPM source → 127–131 detected, exact-tempo pass) — a real **+15.6pp Acc2** gain.
> Several SSA claims this session were WRONG and have been corrected — **read
> `docs/research/validation/2026-06-04-RECONCILIATION.md` FIRST.** Current next task: **harden the
> tempo primitive** (task #6 — port v3's confirmed `esv11_pick_top_tempo_bin_octave_aware` octave
> arbiter + fix the marginal confidence/lock gate). Method lesson banked: never relay SSA prose as
> fact; re-run the territory yourself.

> Read this top-to-bottom before touching anything. It is written per the `load-bearing-edges`
> discipline: it captures the *edges* (the dependencies, the gotchas, the why) you need to act
> without re-deriving — not just a list of files.

## 0 · Your role & the standing contract
You are **CTO + CPO + Chief Technical Engineer** for SpectraSynq's K1 firmware. North star:
*a music-to-visual system that exceeds Sensory Bridge's perceptual impact* — architecture is
subordinate to that. The **Founder Execution Boundary** binds you: the Captain (founder) is NOT
in the execution/debug/test loop. Validate on host harnesses, report **decision-grade and tight**
(he has repeatedly, bluntly rejected verbosity), escalate only material/strategic/irreversible
forks. Heavy work goes to **Codex** (his near-unlimited tokens) to spare the Claude pool. British
English. No push / destructive / public action without explicit instruction.

## 1 · Where we are (the one-paragraph state)
The product gap is the **effect library**. But the Captain made a load-bearing call this session:
**no effect may be wired to beat/tempo/onset until ≥1 audio primitive is reliable on REAL music.**
Why: a reference effect (`perceptual_bloom`) proved on-device that the **renderer is right**
(alive, cohesive, "8.5 character") and the **audio feature layer is the wall** — the same effect
nails a clap/snap but drowns on a song. So the entire next phase is **fixing the audio primitive**,
not building effects. We recovered v3's `MusicalSaliency` 4-axis detector, ported it, and a swarm
proved its catastrophic metric was **misattributed** (see §3). It is recoverable. The next move is
a single measured experiment (§2).

## 2 · YOUR IMMEDIATE NEXT TASK (hit the ground running)
The decisive experiment, from `docs/research/2026-06-04-saliency-diagnosis-and-fix-path.md`.
Branch: **`wip/audio-saliency-recovery`** (the `sb_musical_saliency.{h,cpp}` files are there,
**uncommitted but present on disk**; the main tree is currently checked out on this branch).

- **Step 1 (firmware) — the measured high-leverage fix.** In `SPECTRASYNQ_K1_FIRMWARE/audio/sb_musical_saliency.cpp`: **delete the self-ratcheting event gate** (`adaptiveFloor` = a 0.99/0.01 EMA *of `overallSaliency` itself*, `threshold = clamp01(floor*2)`, ~lines 165, 168-169, 181 — it's a fork-author INVENTION, not in v3). Replace with a fixed-floor relative gate (slow 0.995 baseline + fixed margin `th = floor + 0.15`, mirroring v3 `ControlBus.cpp:271-273`) **and** add an early `if (audio.silence) { hold/zero; do not emit; }` (the engine currently never reads `audio.silence` — 0 grep matches). *Measured result of this fix: music event-rate 18.28→55.94 (PASS), silence 24.46→0.0 (PASS) — 2 of 4 criteria flip on this one change.*
- **Step 2a (harness) — fix the bent scale.** In `scripts/regression-harness/musical_saliency_benchmark.py`: score recall against `dataset/segments/*.txt` boundaries (parse col-0 like the beats loader, ~:197-211, widen tolerance ~1-2 s), **NOT** against all 14,908 beats (max achievable recall there is 0.0146 — structurally impossible to pass 0.45). Also stop the single-scalar broadcast (~:57-67) that collapses the 4 axes into 1.
- **Run them TOGETHER**, then `python3 scripts/regression-harness/musical_saliency_benchmark.py --json`. **Decision:** if precision-vs-segments clears ~0.4-0.5 → the residual is *tuning* (done-ish); if it stays ~0.21 → **Step 3 conditioning is load-bearing** (re-scale thresholds + add log1p/bounded conditioning per `docs/architecture/k1-audio-feature-surface.md`), and **Step 5** (move the primitive onto periodicity/ACF via `sb_tempo`) becomes likely. Either outcome re-ranks all remaining work — max information per unit effort.
- Build/test in the **real env** (`~/.local/bin/pio run -e k1_hardware`, `python3 -m pytest tests/`) — the implementation already compiles clean + 123 tests pass (codex's "RED" was its sandbox). Commit to `wip/audio-saliency-recovery` once green; do NOT flash blind.

**Invoke first:** `/load-bearing-edges` (you are porting/fixing a primitive), then `/k1-firmware-change-gate` + `/sensorybridge-doctrine` (AP-class firmware).

## 3 · Problems we faced this session (war stories + how they resolved)
1. **The 14-effect fleet** (`wf/integration`): host-green, on-device **garbage**. The host *oracle was blind* — it judged raw per-pixel strips (not the LGP-diffused plate), faked onset/tempo from a chroma proxy, and rewarded responsiveness (which favours flash/sparkle). Lesson: a host metric that isn't optics+real-audio+metric-faithful **predicts nothing**.
2. **`perceptual_bloom`** (`wip/perceptual-bloom`, currently flashed on 1401): the controlled experiment — proved renderer-right/audio-wrong. A *keeper visual* (8.5), not music-reactive (3.8). The "always-alive base + beat-as-modulation + no flash/sparkle" laws hold.
3. **The saliency port "FAIL"** → diagnosed (real swarm) as **misattributed**: precision 0.2074, recall 0.0030, fires more in silence (24/min) than music (18/min) — but caused by (a) the invented self-ratchet gate and (b) the structurally-impossible benchmark, **not** a weak detector. Fields all real (no phantoms). Build compiles, 123 tests pass.
4. **Codex gotchas** (now all captured in the `codex-offload` skill): the `< /dev/null` stdin hang; context overflow at 249k on broad tasks (→ decompose + read-budget); the workspace-write sandbox can't write device/network/outside-repo (→ build-RED≠broken, can't flash, can't commit).
5. **Device incident** — 1401 dropped off USB. Triaged: **no rogue write** (proved via `lsof`/log-grep — only the verified `perceptual_bloom` flash ever wrote it); cause was transient/physical; recovered by replug + reflash. ESP32-S3 ROM bootloader makes true bricking very hard.
6. **The meta-flaw** (§ below): we kept canonising *edge-incomplete* primitives.

## 4 · Problems you will (or may) encounter
- **Firmware is restructured into subdirs** (`audio/ visual/ effects/ director/ serial/ system/ persistence/ calibration/ diag/`; `.ino` at root). Any older doc citing flat paths is stale — `find SPECTRASYNQ_K1_FIRMWARE -name X`.
- **Branch sprawl.** `feat/gdft-harness` = clean main line (advancing via parallel agents). `wf/integration` = the rejected 14-effect drop + strings rebrand (`e017793`). `wip/perceptual-bloom` (`a77b3c6`) = the keeper visual, **flashed on 1401**. `wip/audio-saliency-recovery` = active, **main tree is on it**, saliency files uncommitted. `wf/wip-tempo` = quarantined tempo mode (NOT merged/flashed). `wf/fixtures`, `wf/effect-*` = fleet leftovers. Nothing pushed.
- **clangd diagnostics are FALSE POSITIVES** — `-mlongcalls`/`-mdisable-hardware-atomics`/`../hal.h not found`/`SQ15x16 unknown`/`SFixed InternalType` are clangd using the wrong toolchain + missing the subdir include paths (added by `scripts/platformio/k1_src_includes.py` at build time). The real build is **xtensa-gcc via `pio`**; the host harness is **g++ (NOT clang)**. Ignore the IDE noise; trust the real build.
- **The pre-commit gate** runs `pytest tests/` + `pio run -e k1_hardware` for firmware commits; `wip/*` branches auto-skip. Don't commit broken to feat/main.
- **Hardware identity, not port name.** **1401** = dev unit, MAC `B4:3A:45:A5:87:F8`, chip `F887A500`, env `k1_hardware`. **12201** = reference, MAC `B4:3A:45:A5:89:B4`, chip `B489A500`, env `k1_bench_reference`. The pio upload guard aborts on MAC mismatch (rely on it). **Cursor's serial monitor grabs the port** (Errno 35 on flash) — the Captain must close it; never kill Cursor.
- **Tempo/onset/beat are corrupted as *music* data** (clean on transients, chaos on music; tempo lock ~14%). Do NOT wire effects to them until the saliency primitive passes its metric.
- **Codex can't build** (sandbox blocks network/platform-cache) — verify every codex build in the real Claude env.

## 5 · What to be cautious of (role-specific: CTO / PM / Chief Engineer)
- **Founder Execution Boundary is real.** Don't pull the Captain into execution. Don't ask "should I proceed" after a plan's approved. Reports are the decision + what he must decide + nothing else. He values throughput over narration — *brutally*.
- **Never canonise an edge-incomplete primitive.** Before porting/trusting any constant/threshold/function/metric/canonical doc, run `/load-bearing-edges`. Correctness lives in the edges (domain, form, reference, conditioning), not the nodes. This flaw bit us repeatedly — including in specs *I* orchestrated.
- **Verify the scale before condemning the meat.** A catastrophic/counter-intuitive result (impossible numbers, inverted behaviour) → suspect the benchmark/measurement before the thing measured.
- **Hardware discipline.** MAC-verify before any flash/erase/serial. **Never auto-fire `start_noise_cal`** (only under Captain-confirmed silence). compile ≠ runtime proof for visual/AP — the `light_mode_*` carve-out commits on host-green with on-device eyes-on as a *tracked, non-blocking* follow-up.
- **Don't over-produce.** Via-negativa: augment a canonical home before spawning a new skill/doc; there's already a dense skill set. Doc/skill proliferation is governance drift.
- **Manage context relentlessly.** Offload heavy reading to Codex; write-to-disk + return tight verdicts from swarms; treat each big task as the last before `/compact`. This window hit the wall — plan for it.

## 6 · How to fulfil the role efficiently & expertly (the method that worked)
1. **Lead with the territory (executable validation), not docs.** A real build + a real metric + a *measured discriminator* found in minutes what six canonised docs hid all session. Docs are hypotheses until executed.
2. **Swarm for diagnosis:** parallel hypothesis probes (incl. one that actually builds, one that audits the benchmark) → debiased adversarial synthesis → write-to-disk + tight verdict. (See the `saliency-primitive-truth` workflow.)
3. **Codex for bounded reading/drafting** (per `/codex-offload`); **Claude for** device ops, build verification, commits, global-skill edits, final synthesis.
4. **Thinking choreography** (per `load-bearing-edges` §2): first-principles+map-territory to frame, systems to find the broken link, red-team+archetypes to generate failure paths, bayesian+debiasing to weigh, second-order to anticipate propagation, triz to resolve.
5. **Reporting:** tight, decision-grade, recommend a path; surface genuine forks via `AskUserQuestion` with a recommended option first.
6. **Gates:** `/load-bearing-edges` before porting/canonising · `/k1-firmware-change-gate` + `/sensorybridge-doctrine` before firmware · `/codex-offload` before offloading.

## 7 · Items I wish I'd been told before starting this session
- The firmware is **restructured into subdirs** — every old path is stale; re-derive.
- **Tempo/onset is corrupted on music** — do not build on it; this is the whole bottleneck.
- **Codex needs `< /dev/null`**, overflows on broad tasks, and its sandbox can't build/flash/commit — so a codex "build failure" is meaningless without a real-env re-check. (Three failed launches taught me this; the `codex-offload` skill now front-loads it.)
- **The "canonical" docs (specs, guidebooks, even the motion canon) are edge-incomplete** — validate the load-bearing edges before trusting them. This is the single biggest lesson; it's why `load-bearing-edges` exists.
- **clangd diagnostics are noise** here — don't waste a cycle "fixing" them.
- **The bench K1 transiently drops off USB** — replug fixes it; don't assume damage.
- **The benchmark/scale itself can be wrong** — a 0.003 recall was a structurally-impossible denominator, not a dead detector.
- **Offload heavy reads to Codex from the START** to spare the Claude 5-hr pool *and* your context — I learned this only after a budget squeeze.
- **Workflow results refill your context fast** — design every fan-out to write to disk and return ≤10 lines.

## 8 · Artifact map
- **Skills (new this session):** `.claude/skills/load-bearing-edges/` · `.claude/skills/codex-offload/`. Both promotion-worthy to `~/.claude/skills/`. Corrected: `~/.claude/skills/k1-effect-development/` (stale-API warning appended). Standing: `k1-firmware-change-gate`, `sensorybridge-doctrine`, `k1-motion-canon`, `spectrasynq-audio-pipeline`, `esp32-render-path-safety`.
- **Docs (this session, all under `docs/`):** `research/2026-06-04-saliency-diagnosis-and-fix-path.md` (THE next-task plan) · `architecture/k1-audio-feature-surface.md` (the conditioning-gap reference for Step 3) · `research/2026-06-04-meta-flaw-canonising-edge-incomplete-primitives.md` · `research/2026-06-04-why-v3-AP-saliency-works.md` · `research/2026-06-04-sb-musical-saliency-IMPL-SPEC.md` · `research/2026-06-04-v3-effect-cohesion-doctrine-FOUND.md` (SSA1 canonical motion doctrine) · `prd/ve-auto-loop/03-effects-archaeology-synthesis-2026-06-04.md` + `effect-verdict-sheet-2026-06-04.md` · `architecture/effect-decomposition/` (the deliberate effect-design method).
- **Branches:** §4. **Hardware:** §4 (1401 running `perceptual_bloom`).
- **v3 donor (read-only):** `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/firmware-v3` — canonical build env `esp32dev_audio_esv11_k1v2_32khz`; saliency at `src/audio/contracts/MusicalSaliency.h` + `ControlBus.cpp:855-980`.

## 9 · First five minutes (verify, don't trust this doc)
1. `git -C "<repo>" status -sb` + `git branch -vv` — confirm branch state vs §4.
2. `git rev-parse --abbrev-ref HEAD` — expect `wip/audio-saliency-recovery`.
3. Read `docs/research/2026-06-04-saliency-diagnosis-and-fix-path.md` (the plan) + `docs/architecture/k1-audio-feature-surface.md` (the conditioning ref).
4. `/load-bearing-edges`, then `/k1-firmware-change-gate`.
5. Execute Step 1 + Step 2a (§2); re-run the benchmark; let the *measurement* re-rank the work.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-06-04 | agent:orchestrator (outgoing CTO) | Created — full session handover: state, next task (Step-1+2a), war stories, hazards, role cautions, the working method, and the "wish I'd known" list. |
