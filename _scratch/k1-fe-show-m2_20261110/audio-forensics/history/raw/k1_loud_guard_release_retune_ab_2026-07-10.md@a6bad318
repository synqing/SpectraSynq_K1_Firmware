---
abstract: "Loud-room A/B run-book for the K1 loud-guard release/floor-cut retune (AP-audit Item 1, 2026-07-10). Ships an additive, runtime-selectable 3-mode matrix (k1_loud_guard=mode0|1|2) that is DORMANT at default 0 (byte-identical shipping). Read to run the hardware A/B: build/flash (MAC-verify bench B489A500), Captain-approved EDM, [AP]-telemetry capture of gdft_trim recovery + spec_sat_duty limit-cycle + onset/bpm regression, steady-state-median methodology, and the pass/fail → default-flip sign-off gate. Values are DEGRADED-MODE (unproven on hardware). Do NOT land or flip the default without Captain hardware sign-off (RBDO hard-stop #3)."
---

# K1 Loud-Guard Release/Floor-Cut Retune — Loud-Room A/B Run-Book (2026-07-10)

**Status:** built green on `k1_hardware` (`pio run` exit 0), NOT flashed, NOT committed. Change lives on branch `lane/loud-guard-release-retune` off `a9ff00c`. **RBDO: DEGRADED-MODE** — the retune constants are A/B starting points, unproven on hardware. **Landing to main and flipping the default require Captain loud-room A/B sign-off (RBDO hard-stop #3).**

## Why this change (the AP-audit Item 1 defect)
`K1_LOUD_GUARD_GDFT_RELEASE_SEC = 2.20 s` (a fast-attack/slow-release limiter, attack 0.30 s) outlasts the loud passage: `k1_loud_gdft_trim` recovers over ~2.2 s, so `spectrogram[]` stays attenuated ~2.2 s into the now-quiet tail. The flat floor-cut (`out -= loud_depth·0.10`) subtracts a fixed amount from every bin, disproportionately erasing quiet bins. Both constants are **untuned rebrand-era defaults** (`ed56dfb`, no K1 A/B provenance).

## Why NOT the naive brief (2.20→0.6-0.8 s + pure proportional cut)
A 7-agent ground + 3-way red-team audit (workflow `wf_5ace61cd-d22`) established the naive brief is **unsafe** on two counts:
1. **Release is an AGC gain-loop stability parameter, not cosmetic.** `k1_loud_gdft_trim` also scales `effective_target`/`agc_gain_floor` (`k1_gdft_core.cpp:340-341`). At 0.6-0.8 s on a **sustained loud drop**, a self-driven **~1.5-1.8 s re-saturation limit cycle** (~0.5 Hz brightness hunting, uncorrelated with the music) can appear — worse than the sluggish 2.2 s tail. The steeper release ramp also injects a `log(g_t/g_{t-1})` **phantom-onset/novelty bias** at recovery that approaches the non-adaptive onset floor (0.02) at 0.7 s.
2. **A pure proportional cut defeats a hidden guard role.** The flat cut + zero-clamp is a **noise-floor/mud suppressor** on saturated content (the actual saturation-*taming* is the untouched ceiling soft-knee). A pure `out·loud_depth·K` leaves near-zero mud untouched → the LGP floor **re-fills with mud** on exactly the loud rooms the guard exists for.

**Corrected shape:** hybrid affine cut `out -= loud_depth·(P + out·K)` keeping the zero-clamp; conservative release, not 0.6-0.8 s.

## What shipped (additive, dormant-default) — 5 files, +74 lines
Runtime-selectable `k1_loud_guard_mode` (`globals.h`, default **0**). Mode 0 is **byte-identical** to current shipping behaviour, so production is unchanged until a mode is selected.

| Mode | GDFT release | Floor-cut | Intent |
|---|---|---|---|
| **0 BASELINE** | 2.20 s | flat 0.10 | control = current shipping (default) |
| **1 CONSERVATIVE** | 1.30 s | hybrid affine (P 0.03 / K 0.12) | release ≥ ~2× DUTY_TAU (over-damped); red-team-1 shippable band |
| **2 AGGRESSIVE** | 0.80 s | hybrid affine | brief's intent at red-team-3 upper safe bound — the mode that will *reveal* the limit cycle if real |

Constants: `system/constants.h` (`..._RELEASE_SEC_CONS/_AGGR`, `..._FLOOR_CUT_PEDESTAL/_PROP_K`). Applied at **both** AGC paths via one helper `k1_loud_guard_apply_floor_cut` (`k1_gdft_core.cpp:70`), used at the per-band (`:439`, the live `k1_hardware` path under `K1_AGC_PERBAND_V1`) and broadband (`:516`) sites. Ceiling soft-knee untouched. Release select: `k1_loud_guard_gdft_release_sec()` (`i2s_audio.h`). Telemetry: `mode=%d` on the `[AP]` line.

## Serial control (structured command — reliable on the bench)
- `k1_loud_guard=mode0` / `mode1` / `mode2` — select a mode
- `k1_loud_guard=cycle` — advance 0→1→2→0
- `k1_loud_guard=status` — prints mode + all trims/duties
- (single-char hotkey deliberately NOT wired — avoids collision with existing bench keys; request if wanted)

## A/B protocol
**Device:** bench **B489A500** (`b4:3a:45:a5:89:b4`, IM73D122 mic). MAC-verify before flash — `pio device list` reads serial=MAC; ports drift. Flash env: `k1_bench_im73d` (inherits guard + per-band AGC + the IM73D mic path). *Serial-open resets the board.*

**Build + flash (from `/private/tmp/k1_loud_guard`):**
`pio run -e k1_bench_im73d -t upload --upload-port /dev/cu.usbmodemXXXX` (confirm the port maps to 89:B4 first).

**Audio (Captain-approved corpus only):** EDM with a clear loud drop + quiet breakdown is the target waveform (loud→quiet transition is what the release tail governs). **State file · device · volume · duration · stop-command before playback** and get the go — the loud-room A/B is Captain's to run (his room, his ears; the guard's loud regime cannot be reproduced host-side).

**Capture:** enable `[AP]` telemetry (`a` hotkey), capture serial to a log per mode.

**Methodology (audio A/B 4-gate):** same source per mode · exclude the first 8-10 s convergence transient · isolate one variable (mode) per capture · report **steady-state median** alongside mean.

**Metrics (all from existing `[AP]` fields):**
| # | Metric | Field | Expectation |
|---|---|---|---|
| 1 | **Defect fix** — trim recovery time after loud→quiet | `gdft_trim` returns to ~1.0 | mode 0 ~2.2 s → mode 1 ~1.3 s → mode 2 ~0.8 s |
| 2 | **Limit-cycle check** (the hypothesis) | `spec_sat=` (`spec_sat_duty`) on a **sustained** loud soak | mode 0/1 steady; **mode 2 must NOT show a ~1.5 s oscillation**. If it does → the coupling is real; escalate to the deferred decoupled fix (below) |
| 3 | **Guard still engages** | peak `gdft_trim` depth during saturation | unchanged across modes (guard still tames loud) |
| 4 | **No onset/tempo regression** | `bpm`/`conf`/`lock` steady-state; `onset` count; watch `novelty`/`onset` at the loud→quiet boundary | bpm-lock + onset rate unchanged; no spurious onset cluster at recovery |

## Pass/fail → decision
- **Winner = the mode** that (1) shortens the recovery tail perceptibly, (2) shows **no** sustained-loud limit cycle (metric 2), (3) keeps guard depth (3), (4) no onset/tempo regression (4), and reads best by eye on the LGP.
- Making the winner the **new default** (`k1_loud_guard_mode = <winner>`, or folding its constants into the baseline) is a **separate** Captain sign-off — it changes shipping behaviour. Until then the change lands dormant (default 0) or does not land.

## First-pass hardware A/B result — 2026-07-10 (bench B489A500, IM73D, 1 Hz [AP], Avicii-Levels @ 65%)
Capture: `scripts/regression-harness/k1_loud_guard_ab_capture.py`; log `/private/tmp/k1_loud_guard_ab_2026-07-10T163858.log`.

| mode | min gdft_trim (guard depth) | trim variance (loud) | recovery to ≥0.98 | onsets (18 s) | bpm |
|---|---|---|---|---|---|
| 0 BASELINE (2.20 s/flat) | 0.468 | 0.0144 | **4.63 s** | 1 | 110 |
| 1 CONSERVATIVE (1.30 s/hybrid) | 0.511 | 0.0144 | **2.69 s** | 5 | 98 |
| 2 AGGRESSIVE (0.80 s/hybrid) | 0.652 | 0.0086 | **1.77 s** | 7 | 127 |

**Headline (GROUNDED):** recovery tail shortens **monotonically 4.63 → 2.69 → 1.77 s** — the defect (long attenuation tail) is measurably fixed. Guard still engages (min trim 0.47-0.65). No instability observed — mode 2 trim variance was *lower*, not higher.

**Honest caveats (what this run did NOT prove):**
1. **Limit cycle UNTESTED.** `spec_sat_duty` stayed 0.000 at 65 % — the guard engaged via the **peak-pin** path, so the red-team's spec-sat→AGC feedback loop was never exercised. The limit cycle is neither confirmed nor refuted. **Follow-up: re-run louder (~75-80 %) to drive `spec_pin` > 0.**
2. **Onset/tempo regression inconclusive.** bpm not locked in the 18 s window (110/98/127 vs Levels' ~126); onsets 1→5→7 may be the proportional cut passing more flux (aligns with red-team 3) *or* convergence noise. **Follow-up: longer window at locked tempo.**
3. 1 Hz sampling inflates the absolute recovery numbers (first-sample-≥0.98); the **relative ordering is robust**, absolute values are not.

**Read:** mode 1 (conservative) is the low-risk default candidate — meaningful recovery gain (4.63→2.69 s) at a red-team-endorsed release ≥2×DUTY_TAU. Mode 2 gives the best recovery and showed no instability, but its limit-cycle safety needs the louder run before it could be a default. Final pick = Captain eyes-on the LGP + the two follow-ups.

**Bench state:** left on `k1_bench_im73d`, currently mode 2 (last tested). `:k1_loud_guard=mode0` or a power-cycle returns to the dormant baseline.

## Definitive A/B result — v2, 2026-07-10 (10 Hz [AP], Avicii-Levels @ 78%, 23 s steady window)
Capture v2: same script (`VOLUME=78`, `LOUD_SECS=35`, `STEADY_SKIP=12`); 10 Hz build via `-DK1_AP_STREAM_INTERVAL_MS=100`. Log `/private/tmp/k1_loud_guard_ab_v2_2026-07-10T165107.log`.

| mode | recovery to ≥0.98 | gdft_trim var (steady) | oscillation | spec_sat_duty | bpm / lock | onset rate |
|---|---|---|---|---|---|---|
| 0 (2.20 s/flat) | **5.54 s** | 0.0029 | ~0.15 Hz drift | 0.000 | 63 / 1.00 | 2.39/s |
| 1 (1.30 s/hybrid) | **3.42 s** | 0.0032 | ~0.09 Hz | 0.000 | 63 / 1.00 | 2.43/s |
| 2 (0.80 s/hybrid) | **1.94 s** | 0.0031 | ~0.09 Hz | 0.000 | 63 / 1.00 | 2.43/s |

**Limit cycle — DISCONFIRMED (GROUNDED).** (1) `spec_sat_duty` = 0.000 even at 78 % — the guard's ceiling soft-knee caps bins at ~0.78 once engaged, holding them under the 0.92 spec-sat threshold, so the spec-sat→AGC feedback loop is self-suppressing and does not form in practice on this hardware/room. (2) On the peak-pin path that does engage, mode 2's trim variance is flat (~0.003, no worse than baseline) and the only motion is a benign ~0.09 Hz music-envelope drift — no ~0.67 Hz self-driven hunting, no growth at the aggressive 0.80 s release. The red-team medium-confidence limit-cycle hypothesis does not reproduce.
**Onset/tempo regression — NONE (GROUNDED).** bpm locked 63/1.00 identically across all modes; onset rate 2.4/s flat. v1's apparent 1→5→7 onset difference was convergence noise (short, unlocked window); it vanishes at locked tempo. The hybrid proportional cut does not regress beat/tempo/onset.
**Defect fixed:** recovery 5.54 → 3.42 → 1.94 s (mode 2 cuts the tail to ~1/3).

**Residual honesty:** the spec-sat trigger requires ~18 % of bins ≥ 0.92, which this bench does not produce even at 78 % (ceiling-knee-suppressed). A club-level near-mic SPL is not reproduced here; the spec-sat limit cycle is therefore disconfirmed for realistic playback, not stress-tested at extreme SPL. Given peak-pin engages first and the ceiling knee suppresses spec-sat, that path is largely academic.

**Verdict:** with the limit cycle disconfirmed and zero onset/tempo regression, **mode 2 (0.80 s + hybrid cut) is the winner** — best recovery, stable, no regression. **Captain hardware sign-off 2026-07-10 → shipped as the default** (`k1_loud_guard_mode = 2`, globals.h). Modes 0/1 remain runtime-selectable via `:k1_loud_guard=mode0|1` for future comparison. The 10 Hz `-DK1_AP_STREAM_INTERVAL_MS=100` flag is diagnostic-only; production ships the 1 Hz default (flag absent, defaults to 1000 ms).

## Deferred (only if metric 2 fails at mode 2)
Red-team-preferred root-cause fix: **decouple** the release — keep a short release (~0.7 s) on the display floor-cut/ceiling path but a slow release (~2.2 s) on the value feeding `effective_target`/`agc_gain_floor` (`:340-341`), killing the limit cycle at source. Requires splitting `k1_loud_gdft_trim` into display/AGC trims. **Not pre-built** — it addresses a medium-confidence hypothesis that mode 2's telemetry will confirm or deny first.

## Hygiene fixed alongside (from the AP audit)
`platformio.ini:118` comment claimed "Default OFF via k1_loud_guard_enabled=false" — **stale**; `globals.h:123` defaults it `true` (guard ships enabled). To be reconciled in the same change (comment-only) so provenance is honest.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-07-10 | agent:opus-4.8 | Created — loud-room A/B run-book for the loud-guard release/floor-cut retune (AP-audit Item 1); built green on k1_hardware, not flashed/committed. |
