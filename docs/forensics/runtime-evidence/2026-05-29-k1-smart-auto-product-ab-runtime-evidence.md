---
abstract: "Runtime log review for Smart Auto product A/B validation using local music clips on 1101 L1 reference versus 1401 Auto candidate."
---

# K1 Smart Auto Product A/B Runtime Evidence

| Field | Value |
|---|---|
| Date | 2026-05-29 |
| Evidence tier | Runtime serial/AP/VP/status log review |
| 1101 role | L1 reference, `:smart_scene=l1` |
| 1401 role | Smart Auto candidate, `:smart_scene=auto` |
| Music source | Local drive: `/Users/spectrasynq/Workspace_Management/Software/AceStep-Eval/Songs` |
| Calibration | No calibration command issued |

## Evidence Files

- `docs/forensics/runtime-evidence/2026-05-29-k1-smart-auto-product-ab-1101.log`
- `docs/forensics/runtime-evidence/2026-05-29-k1-smart-auto-product-ab-1401.log`
- `docs/forensics/runtime-evidence/2026-05-29-k1-smart-auto-product-ab-manifest.json`

## Device And Clip Proof

[FACT] 1101 answered as firmware `VERSION: 40103` and chip ID `F887A500`.

[FACT] 1401 answered as firmware `VERSION: 40103` and chip ID `B489A500`.

[FACT] The run played three local music windows and all `ffplay` subprocesses exited `0`:

| Clip class | Track | Window |
|---|---|---|
| Steady groove | `Regard_Ride_It.mp3` | `125s-150s` |
| Kick/drop-heavy | `Shelter-Mix-Cut-Yoel-Lewis-Remix.mp3` | `75s-100s` |
| Sparse/breakdown-to-build | `Carte-Blanche-Mixed.mp3` | `20s-45s` |

## Product-State Result

[FACT] The candidate exercised a materially different product state from the L1 reference.

| Surface | 1101 L1 reference | 1401 Auto candidate |
|---|---:|---:|
| `SMART_DIRECTOR_AUTONOMY` | `off` | `on` |
| `SMART_PALETTE_OVERLAY` | `0` | `1` |
| `SMART_AUTO_COLOUR_SHIFT` | `0` | `1` |
| `EDGE_STRENGTH` | `0.350` | `0.650` |
| Applied modes during clips | `3`, `8` | `3`, `9`, `10`, `11` |
| Palette indices during clips | `11`, `29` | `11`, `22`, `24`, `31` |
| Manual owner active | `0` | `0` |

[FACT] 1401 hit `SMART_SWITCHES_IN_WINDOW: 8` during the kick/drop-heavy clip. That proves the Auto policy is active and taking mode decisions, but it is also the first place to inspect for perceptual over-busyness if the video looks less musical than expected.

[INFERENCE] The logs support "Auto is doing something product-visible"; they do not alone prove that the result is better-looking or more musical than L1. That verdict still needs Captain/video judgement against the three clip classes.

## AP Review

[FACT] AP calibration stayed stable on both devices for all three clips:

| Device | Clip | `cal_source` | `cal_valid` | `silence` values |
|---|---|---|---:|---|
| 1101 | steady groove | `config` | `1` | `0` |
| 1101 | kick/drop-heavy | `config` | `1` | `0` |
| 1101 | sparse/build | `config` | `1` | `0` |
| 1401 | steady groove | `config` | `1` | `0` |
| 1401 | kick/drop-heavy | `config` | `1` | `0` |
| 1401 | sparse/build | `config` | `1` | `0` |

[FACT] AP input was live and non-silent in all windows. `peak_scaled` reached `1.122` on 1101 steady groove, `0.971` on 1101 kick/drop, `0.931` on 1101 sparse/build, `1.000` on 1401 steady groove, `0.914` on 1401 kick/drop, and `0.801` on 1401 sparse/build.

## VP / Performance Review

[FACT] The production `:vp_perf=start` command returned `VP_PERF: disabled (compile with ENABLE_VP_PERF_AUDIT=1)` on both devices. This pass therefore reviewed VP stream timing, not deep perf-audit histogram evidence.

[FACT] VP stream timing exceeded the nominal 2.0 ms ceiling in this runtime pass:

| Device | Clip | `render_us` mean | `render_us` max | Status `VP_RENDER_US` max |
|---|---|---:|---:|---:|
| 1101 | steady groove | `2483us` | `2658us` | `3642us` |
| 1101 | kick/drop-heavy | `2439us` | `2673us` | `3650us` |
| 1101 | sparse/build | `2441us` | `2636us` | `3665us` |
| 1401 | steady groove | `2484us` | `3548us` | `3792us` |
| 1401 | kick/drop-heavy | `2367us` | `2738us` | `3792us` |
| 1401 | sparse/build | `2417us` | `2629us` | `4308us` |

[INFERENCE] This does not block the product A/B verdict because the known VPAB `render_us` semantics issue already prevents strict final-byte/per-effect performance claims. It does block any claim that Smart Auto is fully performance-cleared.

## Clip-Level Smart Auto Read

| Clip | 1101 L1 reference | 1401 Auto candidate | Read |
|---|---|---|---|
| Steady groove | Autonomy off, one late applied-mode move `3 -> 8`, overlay off, edge `0.350` | Autonomy on, applied modes `3/11/9/10`, overlays on, four switches | Strong visible-difference proof; video must decide if four moves felt musical or too busy |
| Kick/drop-heavy | Autonomy off, applied mode held at `8`, overlay off, edge `0.350` | Autonomy on, applied modes `3/11/9/10`, hit eight-switch window cap, edge `0.650` | Highest-risk/highest-impact clip; this is where Auto should win or reveal thrash |
| Sparse/build | Autonomy off, applied mode held at `8`, beat confidence reached `1.0`, overlay off | Autonomy on, applied modes `11/9/3/10`, beat confidence reached `1.0`, overlay on | Good candidate for judging whether Auto tracks build energy without washing colour clarity |

## Decision Boundary

[FACT] No panic, Guru Meditation, WDT, assertion, AP calibration invalidation, or silence misclassification was found in the generated logs. The only reset marker is the expected USB CDC reset at capture start.

[INFERENCE] Product-state validation moved forward: 1401 was not merely L1 with hidden flags; it operated the Auto lane under music.

[INFERENCE] Product approval is not closed from logs alone. A final pass/fail needs Captain's side-by-side visual judgement: at least two of the three clip classes must feel more musically/perceptually impactful than L1 without flooding, strobing, colour-clarity loss, or arbitrary mode thrash.

## Changelog

| Date | Change |
|---|---|
| 2026-05-29 | Captured and reviewed 1101/1401 Smart Auto product A/B logs against three local music windows. |
