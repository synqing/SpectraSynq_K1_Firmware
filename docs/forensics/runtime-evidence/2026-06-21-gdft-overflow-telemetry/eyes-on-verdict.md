---
abstract: "Captain eyes-on A/B of the corrected GDFT arithmetic + true-center (bench K1 12201, music on the LGP plate, 2026-06-21). VERDICT: does NOT pass the 'preferably better' bar. A (legacy) ~= B (corrected+true-center); B slightly worse-but-negligible. The 'louder music -> dimmer waveform effects' inverse is present in BOTH A and B -> it is the PRE-EXISTING broadband AGC clamp (agc_gain collapses on loud input), NOT introduced by this lane. Both 12201 builds judged worse than the effect-framework reference on 2101 (main K1) — a different VP lane (beat-director + native v3 effects), orthogonal to GDFT. DISPOSITION: corrected arithmetic is a device-proven, perf-safe CAPABILITY with NO demonstrated product value -> all three flags stay default-OFF, NOT promoted. No MabuTrace (per the gate), no tuning. Real product levers identified for SEPARATE future lanes: (1) broadband AGC inverse-dimming on loud content; (2) effect-framework VP richness."
---

# Eyes-on A/B verdict — corrected GDFT arithmetic + true-center (12201, 2026-06-21)

Captain eyes-on with music on the LGP plate. **A** = legacy `k1_bench_reference` (all flags OFF). **B** = `K1_GDFT_INT64_MAGNITUDE_V1=1 K1_GDFT_INT64_RECURRENCE_V1=1 K1_GDFT_TRUE_CENTER_V1=1`. Everything else unchanged (Hann/ACF/Nyquist/AGC/VP/sample-rate).

## Verdict: DOES NOT PASS

> Captain: "A seems to perform *slightly* better (perhaps negligible) than B but overall still worse than the bench reference on usbmodem2101."

- **A ≈ B**, B slightly worse-but-negligible. The corrected arithmetic + true-center delivers **no perceptible product improvement** on the plate. True-center's chroma re-mapping (each note → its correctly-labeled bin) is not a visible win; the un-wrapped magnitudes do not visibly help.
- **Gate bar was "at least neutral, preferably better."** B is at best neutral, possibly a hair sub-neutral → **not a pass.**

## The "louder → dimmer" inverse is PRE-EXISTING (not this lane)

Captain's lead observation: "the louder the music gets the dimmer waveform class of effects responds… an inverse function." Present in **both A and B** → it is the **broadband single-scalar AGC** clamp, not the GDFT arithmetic. Evidence (live AP stream):
- On loud input `agc_gain` collapses (B: 0.067 @ `max_raw≈8221`; A: 0.14–0.16 @ `max_raw≈1900`) while `agc_env` rises (B → 6.8) — one global gain, so loud broadband content crushes the whole field.
- Matches the known AGC investigation: AGC v2 is broadband (one scalar gain), colour/contrast damage from the global clamp. Orthogonal to GDFT; **out of this lane's scope** (Captain fenced "no AGC retune").

## Both worse than the 2101 effect-framework reference

Both 12201 GDFT builds judged worse than the **effect-framework / registry** build on `/dev/cu.usbmodem2101` (main K1) — a **different VP lane** (beat-aware director + native v3 effects), not the GDFT audio path. The visual richness gap lives there, not in GDFT arithmetic.

## Disposition

- Corrected arithmetic (`K1_GDFT_INT64_MAGNITUDE_V1` + `K1_GDFT_INT64_RECURRENCE_V1`): **device-proven correct, bench perf/scale-safe, but ZERO demonstrated product value.** True-center: **device-vindicated but perceptually neutral.**
- **All three flags stay default-OFF. NOT promoted.** Per the doctrine (architecture subordinate to perceptual impact), arithmetic correctness without perceptual gain is not a product win.
- **No MabuTrace** (the gate: don't prove margin for a behavior we won't ship). **No tuning.** Device left on shippable `k1_bench_reference` (= A); identity guard-verified `B489A500` before every flash.

## Real product levers (SEPARATE future lanes — not actioned here)
1. **Broadband AGC inverse-dimming on loud content** — the actual cause of "louder → dimmer." A per-band or differently-shaped gain is the candidate, but it is an AGC lane requiring its own Captain decision.
2. **Effect-framework VP richness** — the 2101 reference look; a VP/effects lane, not GDFT.
