---
abstract: "Change request to the FE firmware lead (FW lead): make Waveform Hybrid K1 (mode 32) and its bench partner Waveform Tempo (mode 18) fully driven by the authored Prim8 stream while AUTHORED, by (a) not OR-ing the live waveform peak into the authored peak and (b) holding the auto-colour-shift phase while AUTHORED. About 8 lines in 4 files. Described, not implemented."
---

# CR-A7 — authored drive for Waveform Hybrid K1 (smallest change)

Raised by Lane A, K1-FE-SHOW-M1 Rev 2, 9 November 2026. Source basis: **`ed0aa984`, the resident bench source** (read back by the lead 9 Nov 11:43Z; equal to the shared tree's staged edits). Line numbers are `ed0aa984`'s; where `407fdf6f` differs it is shown in brackets. `light_mode_wfhyb_k1_variants.cpp`, `light_mode_waveform_tempo.cpp`, `led_utilities.h` and the authored/PRSM sources are identical in both (`git diff --stat 407fdf6f ed0aa984`).

## Problem (all FACT, cited)

While the authored source is AUTHORED (`k1_authored_suppresses_live_update()` true), only the `K1AudioSnapshot` is replaced (`SPECTRASYNQ_K1_FIRMWARE.ino:1174–1189` [407fdf6f `:1144–1159`]). Two live inputs still reach mode 32:

1. **Live amplitude.** `effects/light_mode_waveform_hybrid_k1.cpp:116` — `peak = fmaxf(snap.peak_scaled, waveform_peak_scaled)`. `waveform_peak_scaled` is the Core-0 live microphone peak (`system/globals.h:235`), written every hop regardless of authored state. The dot position (`:336–339` [`:331–335`], `amp = wfhyb_peak_last * …`), trail decay (`:299` [`:294`]) and the colour walk (`hue_walk = wfhyb_peak_last * WFHYB_HUE_SPREAD`, `:181`) all follow `peak`. With music audible to the microphone, live audio co-drives the dot, so T2 cannot attribute the output to the authored stream. Same pattern: `effects/light_mode_wfhyb_k1_variants.cpp:152` (modes 33–37) and `effects/light_mode_waveform_tempo.cpp:215` (mode 18, the bench secondary edge). At `ed0aa984` additionally `silence = snap.silence && (peak < WFHYB_PRESENCE_FLOOR)` (`:117`; [407fdf6f: `silence = snap.silence`]) — live peak also vetoes an authored silence, and presence/seed/colour gain no longer test silence (`:121,170,283–285`).
2. **Live colour phase.** Palette sampling adds `hue_position` (`visual/lightshow_modes.h:291–295` [ed0aa984 `:294` unchanged], auto-shift on; bench `CONFIG.AUTO_COLOR_SHIFT: 1`, `_scratch/s3-repair-20261105/followup/post-doc-restoration-state.txt:85`). `hue_position` is advanced on Core 0 by `process_color_shift()` (`.ino:1320–1322` [`:1290–1292`]) from the live `novelty_curve` (`visual/led_utilities.h:2413`; the equalised drive at `:2361` is behind `K1_HUE_DRIVE_EQ_V1`, which is not in `k1_fe`), not from the snapshot. So the palette position drifts with room sound, not with the show.

Under authored mode `chromagram_smooth` is zeroed (`.ino:1597` [`:1567`]), so mode 32's chroma blend is 0 and its colour is the palette fallback at `rp->CHROMA + hue_walk` (`:210–211`). Once (1) and (2) are fixed, colour = palette position driven by authored pressure (energy), which THE LAW allows (colour tracks energy, never a clock). Harmony is not carried by Prim8 at all; that is a contract limit, not part of this CR.

## Requested change (smallest)

| # | File, function | Change | Est. lines |
|---|---|---|---|
| a | `effects/light_mode_waveform_hybrid_k1.cpp`, `light_mode_waveform_hybrid_k1()` line 116 | `const float live_peak = k1_authored_suppresses_live_update() ? 0.0f : waveform_peak_scaled;` then `fmaxf(snap.peak_scaled, live_peak)`. Header `k1_authored_source.h` is already reachable via `visual/led_utilities.h:15`. | 2 |
| b | `effects/light_mode_wfhyb_k1_variants.cpp:152` | Same as (a). | 2 |
| c | `effects/light_mode_waveform_tempo.cpp:215` | Same as (a). | 2 |
| d | `SPECTRASYNQ_K1_FIRMWARE.ino:1320` [`:1290`] | `if (CONFIG.AUTO_COLOR_SHIFT == true && !k1_authored_suppresses_live_update())` — hold `hue_position` while AUTHORED (do not zero it: zeroing would jump colour at every authored entry and exit). | 1–2 |

Total about 8 changed lines; no new state, no allocation, no persistence, Core-0 timing unchanged. `light_mode_*` and `.ino` are in the visual/perceptual commit class (`.claude/CLAUDE.md` commit cadence): host-green commit with eyes-on as tracked follow-up.

## Acceptance (for the FW lead)

1. Emulator (Lane C-emu harness, `k1_fe_emu`): same PCM, same authored stream, two runs where only the live PCM gain differs: mode 32 native A/B frames identical while AUTHORED. Today they must differ (live leak); after the change, identical.
2. Rejected-input stream (bad hz): output equals the live baseline, unchanged by the CR.
3. Live behaviour (no PRSM) byte-identical before/after on the maintained music cases (the change is inert when `k1_authored_suppresses_live_update()` is false).

## No-firmware workaround (if the CR is not taken before the bench session)

Play the original recording to headphones so the microphone hears near-silence: live `waveform_peak_scaled` stays near 0 and `process_color_shift()` rests in silence, so mode 32 is driven by the authored stream in practice. Residual: the palette anchor is whatever was held at authored entry. This is an operating condition, not a fix, and it weakens the "in time with the original recording in the room" story.

Changelog
- 2026-11-09 Lane A: created.
- 2026-11-09 Lane A: rebased citations on the resident source `ed0aa984`; change set unchanged.
