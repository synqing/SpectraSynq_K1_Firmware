# Real-track authored edit — intent declared before any comparison (PLAN A20), 2026-11-10

Recording: Loreen "My Heart Is Refusing Me" (mp3 sha256 a62e1f09…9b0f, decoded track.wav b3fafd33…1415,
44.1 kHz, 9,874,432 samples). Contract: m2-analysis out/loreen/consumer/contract.json (f17a0c05…e793).
Edit: same "bar accent" edit as the fixture, made through the composition layer: impact
downbeat_accent_u16 beat_amp_u16 48000 -> 12000; downbeats stay 65535 / 60 ms.
Musical intent: impact marks bar starts (131 downbeats); the other 331 beats become faint ticks,
so the chorus/verse pulse reads as a bar pulse instead of a four-on-the-floor strobe-like flicker.

Predicted visible consequence (before comparing):
1. Only Prim8[1] impact (device novelty) changes; channels 0,2,3,4,5,6,7 byte-identical.
2. Changed frames only inside the 40 ms window after each of the 331 non-downbeat beats
   (min beat gap 120 ms, so windows never overlap a downbeat window); downbeat windows unchanged.
3. Changed value = old x 1/4 within +-1 (integer interpolation rounding).
4. 26,869 frames (ceil(223.910 s x 120)), seq and t_us unchanged; only bytes 20-21 differ.
5. ShowBundle, Intent Trace and .prsm sha256 change; coverage gate still PASS.
Scope limit: no per-section scope exists in mapping_profile_v1 / compiler 0.3.1, so this
applies to every section; the contract's bpm 125 and 6/4 metre are wrong and nothing reads them.
