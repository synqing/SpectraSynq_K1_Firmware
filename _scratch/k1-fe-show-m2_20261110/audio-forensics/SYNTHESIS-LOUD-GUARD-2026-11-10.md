---
abstract: "Plain-English synthesis of the 10 Nov 2026 audio-front-end forensics for the Captain: the loud guard was never switched off, it cuts the picture on dense music at ordinary room volume because its trigger measures density and not loudness, and the measured effect of switching it off at room level and at high level. Ends with three options and a recommendation (retarget the trigger to real overload). Written by the K1-FE-SHOW lead, session 3, from the three helper reports, each decision-critical claim re-checked."
---

# Loud guard and auto-level: what is wrong, and what to do (10 Nov 2026)

## The problem, in four lines

- The microphone does **not** clip in your room. Loudest sample: 273. Clipping point: about 1,517.
- The **loud guard** still cuts the picture. In the final chorus it cut the spectrum to 34 % with nothing clipping.
- It does this because its trigger asks "is the sound near its own recent peak?", not "is the sound loud?". Dense music answers yes at any volume.
- Separately, the auto-level makes loud passages no brighter than quiet ones. That is not the guard, and switching the guard off does not fix it.

## Pictures (all looked at)

1. `emu/analysis-tail/captain-guard.png` — guard ON against OFF, your room level, breakdown into final chorus, three modes. **The decision picture.**
2. `../../k1-fe-show-m1_20261109/lane-d/runs/R_mic_chain_M2_M3.png` — the real Main RPL: mic level far below clipping, guard cutting to 0.34.
3. `../../k1-fe-show-m1_20261109/lane-d/runs/R_volume_test/volume_test.png` — same music 10 dB quieter: the guard still cuts.
4. `emu/analysis/plot-m22-room.png`, `plot-m32-room.png`, `plot-m18-room.png` — guard ON against OFF, chorus into quiet section (128–143 s).

## 1. Did you turn the guard off? Why is it on?

- **No. It has never been off in any build.** [FACT: `system/globals.h:128`, `k1_loud_guard_enabled = true`, checked at a6bad318 by the lead.]
- It was created 17 June, default off. You looked at it running that day and said "Looks good to me". It was made default-on the next day (18 June) and has been on since. [history ledger T2–T5]
- The only off switch is a typed serial command. It is forgotten at the next reboot. No saved setting, build flag or BLE control turns it off. [FACT: no reference in `persistence/`; persist audit of 10 Nov]
- A comment in the build file said "default OFF" until 10 July. That misled agents, and is the probable source of "we turned it off".
- The audio feature you **did** order off was standby dimming (9 August: a dark plate looks like a dead unit).
- The flaw you remember is real. It was seen on 2 July (colours collapse), 10 July (slow release) and 18 August ("attenuating with no live reason"). Each time it was tuned or patched around, never removed.

## 2. What the guard and the auto-level do to the picture at your room level (measured)

Real Main RPL, your Bose volume, Loreen 75–155 s:

| Measure | Value |
|---|---|
| Loudest mic sample | 273 of a 1,517 clipping point (18 %) |
| Clipped samples | 0 |
| Guard cutting (trim below 1) | 89–97 % of the time |
| Usual cut | to about 86 % |
| Deepest cut (final chorus) | to 34 % |
| Same music 10 dB quieter | still cuts; deepest 67 % |

Emulator, same firmware, music at your room level, guard ON against OFF (lead re-ran the analysis; the repeat run is byte-identical):

| Passage | Mode | Guard OFF compared with ON |
|---|---|---|
| Final chorus (149–155 s) | 22 | **25 % brighter, 37 % more movement.** Chorus-to-breakdown ratio 0.76 → 1.01 |
| Final chorus | 32 | 18 % dimmer in the chorus (one 1 s stretch drops) |
| Final chorus | 18 | 10 % brighter |
| Chorus into quiet (128–143 s) | 22 | about the same (+3 %) |
| Chorus into quiet | 32 | 33 % dimmer, 33 % less movement |
| Chorus into quiet | 18 | same brightness, 30–40 % more range |

Emulator, music 24 dB hotter than your room (a genuinely overloaded input), guard OFF against ON: 18–50 % dimmer and far less movement in every mode. **At real overload the guard helps.**

What this means:
- In mode 22 the guard squashes the first hits of the final chorus. That matches what you saw.
- Off is not better everywhere: mode 32 loses some brightness without it at room level.
- With the guard on or off, the loud chorus is no brighter than the quiet section (ratio 0.4–0.8 in modes 22 and 18). The auto-level does that. It is a second, separate defect.

Limits: the room-level ON/OFF comparison is emulator, not the real unit. The real-unit numbers are guard-on only. The emulator cannot show the guard's trim value, only its effect.

## 3. Options

| | What changes | At your room level | At real overload | Risk |
|---|---|---|---|---|
| **A. Retarget the trigger (recommended)** | Guard cuts only on real overload (samples near the rail, clipping, saturated spectrum). The "near its own peak" trigger no longer cuts. | Behaves as "guard OFF" in the picture | Protection unchanged | Small firmware change. Mode 32 a little dimmer in places. Needs your eyes-on. |
| B. Guard off by default | One default flips | Same as A | **Worse: 18–50 % dimmer, flatter** | Loud venues lose protection |
| C. Leave it | Nothing | Chorus hits stay squashed in mode 22 | Protected | The defect ships |

Recommendation: **A.** It removes the false cuts and keeps the one case where the guard measurably helps.

Not part of this decision, recorded for later:
- The auto-level "loud is not brighter" behaviour (needs its own change request).
- The 14 August sub-bass fix (HF-63) was never put into the Main RPL or FE builds; it feeds the same trigger.
- The mic input on the Main RPL uses about a fifth of its range.
- The emulator's standard music fixture is 24 dB hotter than your room, so past emulator tuning was done at overload.
- The telemetry field `agc_env` is always 0 and `agc_gain` shows the bass band only.

## Sources

- History: `history/HISTORY-LEDGER.md`. Source map: `source/CHAIN-MAP.md`. Emulator: `emu/analysis/matrix.md`, `emu/analysis-tail/tail.md` (scenario `emu/make_scenario_tail.py`, analysis `emu/analyse_tail.py`).
- Lead's re-checks: guard default and trigger read at a6bad318 (`globals.h:128`, `audio/i2s_audio.h:246, 272–279`); `emu/analyse.py` re-run on the helper's 13 captures, same numbers; six new final-chorus cases run and accepted (6/6).

## Changelog
| Date | Author | Change |
|---|---|---|
| 2026-11-10 | agent:claude (K1-FE-SHOW lead, session 3) | Created. |
