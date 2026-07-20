# Effect Migration Backlog — Lightwave → Canon

Source: `Lightwave-Ledstrip/firmware-v3/src/effects/` (~194 files, ~150 playable).
Target: `SPECTRASYNQ_K1_FIRMWARE/effects/` (`light_mode_*`, re-derived via the
effect-decomposition method). Each batch is gated by the parity harness (Phase 1)
and merged only on pass.

## Already in canon (26 archetypes — the family heads)

`aurora, bloom, chroma_constellation, chromagram_dots, chromagram_gradient, comet,
dense_forge(_chord), ember(_v2), gdft, kaleidoscope, percussion_burst, pulse_prism,
quantum_collapse, river_surge, snapwave, spectrum_river(_v2), tempo_comet(_anticipate),
tempo_river(_walk), vu(_dot), waveform(_fast/_hybrid/_tempo)`

## Backlog batches (priority order)

### Batch A — Optics / caustics (~20) · HIGH VALUE
Caustic*, Fresnel* (zones/sweep/reactive), WaterCaustics, Schlieren, OpalFilm,
ChromaticAberration/Lens/Pulse/Shear, RGBPrism, Doppler, cloaks (Grin/Metamaterial/
Anisotropic).

### Batch B — Reaction-diffusion & generative lattices (~15) · HIGH VALUE
ReactionDiffusion* (+ Triangle/RD/TestRig), CrystallineGrowth, MycelialNetwork,
NeuralNetwork(Radial), Sierpinski, QuasicrystalLattice, DiamondLattice, HexagonalGrid.

### Batch C — Wave / interference physics (~20) · HIGH VALUE
SolitonWaves(Radial), KdVSolitonPair, WaveCollision(Enhanced), InterferenceScanner,
Chladni, ModalCavity/Resonance, GratingScan(Breakup), Moire (Cathedral/Curtains/Silk),
TalbotCarpet, CymaticLadder, ConcentricRings, RadialRipple.

### Batch D — Quantum / relativity (~15)
Quantum (Colors/Entanglement/Tunneling), TimeCrystal, TimeReversalMirror (+AR/Mod1-3),
Gravitational (Lensing/WaveChirp), HyperbolicPortal, PhaseTransition, PhotonicCrystal.

### Batch E — Perlin backends (~12)
Perlin (Emotiscope Full/Quarter, FastLED), PerlinCaustics(Ambient), PerlinVeil(Ambient),
PerlinShocklines(Ambient), PerlinInterferenceWeave(Ambient).

### Batch F — Beat / onset family (~20)
BeatPulse suite (Bloom, Breathe, Resonant, Ripple, Shockwave(Cascade), Spectral(Pulse),
Stack, Void, LGPInterference), LGPBeatPrismOnset (Advect/Drift/Ignite/Rotate),
BeatParitySprite. Canon seed: `pulse_prism`.

### Batch G — Kuramoto oscillator field (4) · DISTINCTIVE
KuramotoOscillatorField, KuramotoFeatureExtractor, KuramotoTransport(Buffer/Effect).
No canon equivalent — signature effect, prioritise.

### Batch H — Classic FastLED set (~15) · LOW-COST / MECHANICAL
Fire, Confetti, Juggle, Sinelon, BPM(Enhanced), Ripple(Enhanced/EsTuned), Plasma,
Ocean, Wave(Reactive/Ambient), Breathing(Enhanced), Heartbeat(EsTuned), ChevronWaves
(Enhanced), StarBurst (Enhanced/Narrative).

### Curated "bangers" packs (review for keepers)
LGPHolyShitBangersPack, LGPShapeBangersPack, LGPExperimentalAudioPack — mine for the
best, don't port wholesale.

## Migration rules

1. Re-derive via decomposition method; do not copy `LGP*Effect` classes verbatim.
2. Prune aggressively — target a curated keeper set, not 1:1 parity of all 194.
3. Every effect ships with a golden-reference capture in the harness.
4. `*ParityEffect`/`*_reference` files in Lightwave are the tuning oracles — use them.
