---
name: k1-effects-router
description: "Use FIRST when starting ANY K1 light-show effect task — authoring, porting a firmware-v3 effect, fixing a broken effect (stutter/on-off, over-budget/slow, crash, wrong colour), wiring a mode, debugging audio-reactivity, or reviewing a light_mode_*.cpp — to route to the MINIMAL set of relevant effect skills + canon instead of guessing or loading everything. The entry point for K1 effect work."
---

# K1 Effects Router

**Core principle:** match the task-shape → the minimal skills → stop. Do NOT load every effect skill "to be safe" — that bloats context and buries the one rule that matters. This is the effects counterpart to `/thinking-model-router` and `/claude-mem-router`.

**Ground truth that outranks every skill below:** the craft canon `docs/effect-craft/PORTING_CRAFT_CANON.md` and the shared kit `visual/easing.h`. The skills are lenses; the canon is the law.

## Quick gate (run in order, stop at the first match)

```
1. About to WRITE or PORT effect code?
   → /k1-effect-development  AND read docs/effect-craft/PORTING_CRAFT_CANON.md FIRST.
     §1 (mandatory easing) + §2 (per-LED perf) are non-negotiable — skipping them is
     what produced a whole session of amateur-looking, over-budget effects (2026-07-11).
     Then branch by sub-need (table below).

2. An effect is BROKEN? → jump straight to its symptom row (stutter / slow / crash / colour).

3. Running a SWARM (2+ agents porting/modifying effects)?
   → /parallel-agent-sandboxing + /ssa-management (agents write distinct new files;
     the orchestrator owns shared wiring + the single build).

4. Else match the scenario table → load ONE or TWO skills → act.
```

## Scenario → skill(s)

| Task / symptom | Load (minimal) | Then / note |
|---|---|---|
| Author or PORT a new effect | `/k1-effect-development` + `PORTING_CRAFT_CANON.md` | audio-reactive → also `/spectrasynq-audio-pipeline`; motion → `/k1-motion-canon` |
| **"Stuttering / on-off / jarring / amateur / no decay"** | `/k1-effect-development` §easing + **CANON §1** + `visual/easing.h` | THE fix: asymmetric `k1ease::follow` (fast attack, slow release) on every audio drive, eased silence gate, brightness floor. #1 rejection cause. |
| Global brightness pulses on beat / "is this a strobe?" | `/sensorybridge-doctrine` (STROBE LAW) | reactivity must be spatial/transport, not global brightness |
| Over 2.0 ms / high `render_us` / frame drops | `/firmware-profiling` + `/dsp-performance-profiling` + **CANON §2** | root cause is usually a heavy colour/`powf`/`sinf` call **per-LED** — sample frame-constant colour once/frame |
| Panic / watchdog / guru / reboot / heap | `/firmware-crash-analysis` + `/esp32-render-path-safety` | no heap/`new`/`String` in render; static/.bss only |
| Colour / palette / hue wrong or washed out | `/fastled-color-specialist` (+ `/fastled`) | palette-bounded, chroma-anchored, NO rainbow |
| Motion direction / centre-origin / transport feel | `/k1-motion-canon` + `/k1-effect-development` §centre-origin | outward or inward from 79/80 only — never a linear sweep |
| Wiring a mode (enum/dispatch/name/**probe**) | `/k1-effect-development` §wiring | 6 touchpoints; probe coverage enforced by `tests/test_vp_probe_mode_coverage_static.py` |
| Build / flash / validate on hardware | `/k1-firmware-change-gate` + **CANON §4–5** | MAC-verify (bench B4:3A:45:A5:89:B4), `:set_mode=N` colon syntax, Cursor holds the serial port, silent-skip guard |
| Debug audio-reactive behaviour on device | `/audio-visualisation-debug` + `/spectrasynq-audio-pipeline` | inspect the signal, not just the LEDs |
| Cross-core / task / shared-state concurrency | `/esp32-actor-model` | AudioActor/RendererActor boundaries |
| Build env / pio multi-env config | `/spectrasynq-build-system` | `k1_bench_im73d` is the bench env |

## Default ladder — the common case (author / port an effect)

1. `/k1-effect-development` + read `PORTING_CRAFT_CANON.md` (§1 easing, §2 perf — mandatory).
2. Audio-reactive? `/spectrasynq-audio-pipeline` for input semantics (which fields are pre-smoothed vs instantaneous).
3. Write to the fork signature `void light_mode_<name>(CRGB16*, ChannelEffectState&)`; ease every audio drive via `visual/easing.h`; sample colour once/frame.
4. Wire all 6 touchpoints incl. probe coverage.
5. `/k1-firmware-change-gate`: build (`k1_bench_im73d`) → flash (MAC-verified) → no-crash + `render_us` < 2000 µs → **Captain visual A/B** (agents can't play audio; the look is Captain's call).
6. Green before handoff: `tests/test_effect_easing_static.py` + `tests/test_vp_probe_mode_coverage_static.py`. **Commit only on Captain sign-off.**

## Anti-patterns

- Loading every `k1-*`/effect skill "to be safe" — pick by task-shape, load one or two.
- Writing effect code **before** reading `PORTING_CRAFT_CANON.md` — that's the 2026-07-11 failure verbatim.
- Using `/k1-effect-development` for a build/flash question — that's `/k1-firmware-change-gate` + canon §4–5.
- Treating **clangd** diagnostics as real for the fork — clangd is not wired; the `pio` build is the only truth (canon §5).
- Grepping for C++ symbols with `grep` when RTK is on — stdout is corrupted; Read the file or redirect to a file first.

## Companion routers (orthogonal — don't cross-invoke)

| Router | Owns |
|---|---|
| `/thinking-model-router` | decision / debug / architecture mental models |
| `/claude-mem-router` | memory / recall (spec-recall, mem-search, authority gate) |
| `/ssa-management` | how to spawn + consume subagent swarms |
| `/discover-specialists` | when you need a specialist **agent** (e.g. visual-fx-architect), not a skill |

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-07-11 | agent:claude-opus-4-8 | Created — scenario→skill router for K1 effect work, so agents self-route to the minimal relevant skills. Grounded in the 2026-07-11 gem-port session + PORTING_CRAFT_CANON.md. |
