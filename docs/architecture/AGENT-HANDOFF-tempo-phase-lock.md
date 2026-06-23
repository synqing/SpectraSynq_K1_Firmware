# AGENT HANDOFF — Implement Beat/Tempo-Phase-Locked Motion (K1)

> **Operator note (delete before pasting):** this is the whole instruction. Paste it into a
> Claude Code session, set `REPO` to the LightwaveOS/K1 firmware path, attach
> `motion-tempo-scroll.cpp` and `k1-motion-canon/SKILL.md`, and walk away. This file
> **replaces** `beat-phase-lock-build-brief.md` (delete that — it has a dead "verify the API"
> step; the API is known and encoded here). Never give the agent `visual-music-background.md`.

---

## You are
A Claude Code execution agent with write access to the K1 firmware repo (`REPO`) and the K1
on `/dev/cu.usbmodem1401`. You are implementing one new effect. Tempo tracking (`sb_tempo`)
and the scroll engine already exist — **you are wiring and installing, not inventing.**

## Operating contract (inherited — obey; propagate to any sub-agent)
- Label every assertion `[FACT]` / `[INFERENCE]` / `[HYPOTHESIS]`. `[FACT]` only from source you
  read or stable knowledge — never from assumption. British English (`colour`, `behaviour`).
- **Enumerate existing instrumentation before building bespoke.** Do not write a new beat
  detector, a new scroll routine, or new smoothing — they exist; reuse them.
- **Verify the environment before committing to an approach** (Step 0). Do not assume struct
  fields or that a function is wired just because it is defined.
- **Two-failure rule:** after two failures of the same kind, STOP and report (a) what you tried,
  (b) the actual failure mechanism, (c) the proposed alternative. Do not thrash or paper over.
- **Escalate, don't improvise,** at the points listed under ESCALATE. Otherwise do your own
  work — do not ask the operator to run or look up things you can do yourself.

## What you're building (one line)
The first effect that locks **continuous scroll VELOCITY** to musical tempo and phase on the
owned Transport engine, so the strip visibly breathes in time with the beat.

## Read first, in this order
1. **`k1-motion-canon/SKILL.md`** — §1 (the temporal-coupling axiom = why audio must drive
   motion), §2 (the MEASURED apparent-motion law), §6 (the mapping bridge). This is the WHY.
2. **`motion-tempo-scroll.cpp`** — the reference implementation you will install. **Its header
   block is the spec**; this handoff is the surrounding procedure.
3. **`sb_tempo.h` / `sb_tempo.cpp`** and **`sb_audio_snapshot.h`** (in `REPO`) — the APIs you
   consume; confirm the field names used by the cpp still match.
4. **`00-the-method.md`** §1 — the `Motion ∘ Mapping` factorisation this conforms to.

## The law you must not break — `[MEASURED]` (`docs/measurements/apparent-motion-on-k1.md`)
Lock modulates **continuous per-frame scroll VELOCITY, stepping every frame. NEVER advance in
per-beat position jumps.** A 500 ms jump at 120 BPM is ~10× past the 40–60 ms fusion floor → it
teleports, not moves. The eye reads the lock from the per-beat velocity **surge**, not from
scroll speed. **If you find yourself writing a per-beat position jump, you are on the wrong
path — stop.**

## Known API facts — `[FACT]` from the source above (do NOT re-verify; verify the WIRING instead)
- `SBTempoEvent`: `bpm`; `phase01 ∈ [0,1)`, 0 == beat instant; `confidence ∈ [0,1]` (already
  silence-scaled); `locked = confidence>0.30 && !silence`; `beat_tick`; `beat_strength`.
- **Lock range 60–156 BPM** (96 bins). Out-of-range tempi alias to half/double-time — acceptable
  (surge lands every other beat), but expected; do not "fix" it.
- `phase01` is published at **50 Hz** (sb_tempo emits every 20 ms); you read it per render frame.
  That quantises **velocity** in ~20 ms steps — imperceptible, and it does NOT touch the fusion
  floor (which governs POSITION re-stepping). Do not add a phase smoother unless validation §3 fails.
- `sb_tempo` drives this continuous velocity envelope. `sb_onset_beat` is the source for
  onset-seeded elements (not used here).

## Steps

### 0 · Environment verify FIRST — report findings before writing code
- If the motion-probe harness is still on the K1, restore product firmware:
  `pio run -e k1_hardware -t upload --upload-port /dev/cu.usbmodem1401`.
- **Confirm the Core-0 audio loop actually CALLS** `sb_tempo_init()` (at boot) and
  `sb_tempo_update(sb_audio_snapshot_read())` (once per audio frame). `sb_tempo.h` states nothing
  consumes it yet — **it may be defined but never called.** Also confirm `sb_audio_snapshot_update(now_ms)`
  and `sb_onset_beat_update(...)` are called. If any are unwired, wire them in the audio loop in
  the order: snapshot → onset → tempo; add `sb_tempo_reset()` to the mode/noise-transition path.
  **Report what you found before proceeding.**
- Confirm `SBTempoEvent` / `SBAudioSnapshot` field names match the cpp's usage. Report any drift.

### 1 · `channel_effect_state.h` — add to `ChannelEffectState`
```cpp
float    tempo_scroll_accum = 0.0f;
uint32_t tempo_last_ms      = 0;
```

### 2 · `render_params.h` — add to `RenderParams` (mirror to `SECONDARY_*` if the 2nd channel needs its own)
```cpp
float TEMPO_PX_PER_BEAT = 24.0f;  // baseline px the trace travels per beat
float TEMPO_DEPTH       = 0.5f;   // intra-beat velocity surge 0..1 — the FEEL knob
float TEMPO_IDLE_RATE   = 30.0f;  // px/s fallback scroll when not locked
```

### 3 · Register the mode
- Add `LIGHT_MODE_WAVEFORM_TEMPO` to the `lightshow_modes` enum in `config_types.h`.
- Add it to the effect whitelist/gate.
- Route it in the render dispatch `switch` to `light_mode_waveform_tempo(fx)`.
- Declare `void tempo_scroll_step(float&, uint32_t&, const RenderParams*);` and
  `void light_mode_waveform_tempo(ChannelEffectState&);` in `lightshow_modes.h`.

### 4 · Install the code
- Add `motion-tempo-scroll.cpp` to the build the same way the other `light_mode_*.cpp` are
  included in this fork (match the existing pattern — `.ino` include vs PlatformIO src).

### 5 · Build, fix against REAL types
- `pio run -e k1_hardware`. Resolve compile errors against the actual struct definitions — **do
  not invent fields.** If a field you need genuinely isn't there, ESCALATE rather than guess.

### 6 · Flash + validate (next section).

## Validation — pass/fail, on BOTH S2 (~116 fps) and K1 (~185 fps), binary frame capture
1. **No teleport** — scroll surges and eases with the beat, steps every frame. *(Jump/blink on
   the beat ⇒ a position jump slipped in ⇒ FAIL, revert to velocity modulation.)*
2. **Correspondence** — every single-frame advance ≤ 30 px.
3. **Legibility** — the surge is visibly in time with the beat (Captain's eye).
4. **dt-stability** — S2 and K1 captures match within frame-quantisation jitter (±~5 ms).
5. **Silence** — scroll halts/idles within the gate window when audio stops.

Test an **in-range** tempo (60–156 BPM) first; then one **out-of-range** to confirm the
half-time alias reads acceptably.

## ESCALATE (stop, report, do not improvise) if
- `sb_tempo_update()` is unwired **and** wiring it touches audio-loop timing/threading in a
  non-obvious way (this is the Core-0/Core-1 boundary — get it confirmed).
- `ChannelEffectState` or `RenderParams` cannot take the fields cleanly.
- Validation §3 only passes at an implausible `TEMPO_DEPTH` → likely phase misalignment; capture
  `phase01` against a known click track and report before tuning further.
- Two failures of the same kind (per the two-failure rule).

## Done =
The mode builds, flashes, and on a 60–156 BPM track the scroll **visibly breathes in time with
the beat** (velocity surge, never a jump), **halts in silence**, and behaves **identically on S2
and K1**. Report: the frame capture, the wiring state you found in Step 0, and the `TEMPO_DEPTH`
you settled on for Captain's eye. Hand back to Captain for the eyes-on call — do not assume the
look is final; that is Captain's to judge.
