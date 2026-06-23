# AP/VP Visualisation Semantic Canon

Date: 2026-06-07
Status: Canonical research note for the VPAB mode 18 music-capture visualisation lane
Scope: K1 AP/VP evidence visualisation, semantic interpretation, and onward experiment design

## Executive Conclusion

The 3D final-byte waterfall changed the VPAB evidence from "rows of bytes" into
a spatial-temporal object. That made a legitimate semantic association visible:
where final visual energy lives, how it moves over time, whether the motion
respects the K1 centre origin, and how the primary and secondary channels differ.

This is not cosmetic. For K1, better visualisation can become a discovery
instrument. It can surface second-order meaning that is difficult to infer from
tables alone: motion grammar, channel role, centre-origin behaviour, timing
health, and whether an effect's final byte output carries a readable musical
gesture.

The proof boundary is strict:

- A VPAB final-byte waterfall proves final visual output structure.
- It suggests, but does not prove, upstream audio causality.
- Raw audio spectrogram claims require raw PCM or AP/GDFT-band capture.
- VME equivalence claims require candidate VME bytes beside canonical bytes at
  the same final-byte boundary.

## Why The Waterfall Worked

The key shift was dimensional. The original final-byte heatmap showed rows of
decoded RGB values. The waterfall made three axes visible at once:

- `x`: LED index within the channel, `0-159`.
- `y`: final-byte luminance derived from decoded RGB bytes.
- `depth/time`: capture row over time.

Because K1 effects must be centre-origin, LED index has semantic meaning. The
centre is between indices `79` and `80`; lower and higher indices are opposite
sides of the physical channel. Once plotted in 3D, the primary channel pattern
read as balanced off-centre lobe motion rather than a flat byte dump.

Current measured interpretation for the mode 18 music capture:

- Primary centre of mass remains near centre: mean `79.0`, range `77.5-80.6`.
- Secondary centre of mass remains near centre: mean `79.5`, range `79.3-79.7`.
- Primary is low-energy but spatially structured: mean energy `243`, peak `1434`.
- Secondary is higher-energy and denser: mean energy `2415`, peak `5692`.
- Primary and secondary both preserve centre balance, but use different energy
  density and brightness ranges.

The safe semantic wording is:

> The mode 18 final bytes show balanced, centre-aware, off-centre lobe motion
> with stronger secondary-channel energy. This is visual-output evidence, not
> raw audio spectrum evidence.

## Source-Backed Evidence Surfaces

### VPAB Final-Byte And Metric Payloads

`SPECTRASYNQ_K1_FIRMWARE/diag/vpab_capture.h` defines the two relevant VPAB
payload contracts:

- `VPABMetricPayload`: channel, mode, LED count, timing, energy, centre of mass,
  hue/saturation/white-bias metrics, frame/show timing, dropped/over counters,
  and heap.
- `VPABBytesPayload`: channel, mode, LED count, byte count, timing counters, and
  `bytes[LED_COUNT_VALUE * 3]`.

`SPECTRASYNQ_K1_FIRMWARE/diag/vpab_capture.cpp` fills the metrics and writes the
actual final RGB bytes from `final_bytes[i].r/g/b` into the VPAB byte payload.

This means VPAB bytes are the post-render, post-quantisation visual proof
surface. They are suitable for visual-output analysis, channel comparison, and
future canonical-vs-VME final-byte comparison.

### AP And Audio-Semantic Surfaces

`SPECTRASYNQ_K1_FIRMWARE/audio/GDFT.h` owns the Goertzel-based spectral pass and
the novelty curve calculation. That is the correct upstream surface for true
audio-spectrum and novelty visualisation.

`SPECTRASYNQ_K1_FIRMWARE/audio/sb_semantic_state.h` and
`SPECTRASYNQ_K1_FIRMWARE/audio/sb_semantic_state.cpp` define and populate
`AudioSemanticState` from:

- tempo and beat phase (`sb_tempo_read`)
- onset and percussive channels (`sb_onset_beat_read`)
- audio snapshot, chroma, and chord state (`sb_audio_snapshot_read`)

`SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h` exposes AP debug/capture surfaces,
including AP stream text and APCAP aggregate capture. APCAP is useful for
aggregate diagnostics, but it is not a complete per-frame AP semantic timeline.

## Current Generated Artefacts

- Semantic HTML presentation:
  `docs/forensics/runtime-evidence/2026-06-07-vpab-frame-mode18-1401-music.semantic-presentation.html`
- Semantic Markdown brief:
  `docs/forensics/runtime-evidence/2026-06-07-vpab-frame-mode18-1401-music.semantic-brief.md`
- Semantic summary JSON:
  `docs/forensics/runtime-evidence/2026-06-07-vpab-frame-mode18-1401-music.semantic-summary.json`
- Final desktop screenshot:
  `output/playwright/vpab-semantic-presentation-dark-tall.png`
- Final mobile screenshot:
  `output/playwright/vpab-semantic-presentation-dark-mobile-tall.png`
- Generator:
  `scripts/regression-harness/vpab_semantic_presentation.py`
- Focused regression:
  `tests/test_vpab_semantic_presentation.py`

The HTML presentation uses perceptual scalar colour maps for readable final-byte
heatmaps and a display-interpolated final-byte waterfall. The interpolation is
presentation-only; source samples and metrics remain raw.

## Second-Order Analysis

### Immediate Effect

Better visualisation makes VPAB final-byte structure readable.

### Near-Term Consequence

Readable structure lets us name visual behaviours:

- centre-aware motion
- off-centre lobe behaviour
- edge emphasis versus centre emphasis
- primary/secondary channel role
- pulse density
- spatial drift
- beat-lock hypotheses
- output noise or instability

### Medium-Term Consequence

Repeated across modes, tracks, and scenarios, these behaviours become a K1
visual grammar. That grammar can support:

- firmware diagnostics
- VME final-byte comparison
- mode taxonomy
- visual quality gates
- product storytelling
- marketing-ready explanatory graphics

### Long-Term Trajectory

If handled rigorously, K1 gains a repeatable evidence-to-meaning loop:

1. Capture AP/VP evidence.
2. Transform it into truthful visual forms.
3. Extract semantic hypotheses.
4. Re-capture with richer surfaces.
5. Promote only source-backed relationships into canon.

If handled casually, attractive plots will overclaim causality. The failure mode
is a polished story that implies raw-audio intelligence from final LED bytes
alone.

### Required Guardrail

Every visualisation should be labelled as one of:

- `evidence`: directly supported by the captured source data.
- `hypothesis`: plausible relationship suggested by the plot, requiring another
  capture or test.
- `presentation`: useful explanatory or marketing surface that does not increase
  proof strength.

## Visualisation Experiment Matrix

| Experiment | Data Needed | Visual Form | Semantic Question | Proof Strength | Main Risk |
|---|---|---|---|---|---|
| Final-byte radial terrain | VPAB final RGB bytes | 3D terrain, x = distance from centre, y = time, z = luminance | Does the effect preserve centre-origin motion and bilateral balance? | Evidence for final visual output | Mistaking final output for audio spectrum |
| Primary/secondary delta surface | VPAB final RGB bytes for both channels | Difference terrain or heatmap | Do channels play different roles or mirror each other? | Evidence for channel relationship at final-byte boundary | Overreading channel intent without AP features |
| Beat-phase orbit | AudioSemanticState beat phase plus VP metrics | 3D orbit: energy, centre, beat phase | Does visual energy follow beat phase? | Hypothesis unless AP and VP are captured together | Lag/cadence mismatch |
| AP spectrogram waterfall | GDFT band magnitudes over time | True spectrogram/waterfall | What frequency bands are active over time? | Evidence for audio spectral behaviour | Requires richer AP capture than current VPAB music run |
| Novelty ridge overlay | Novelty curve plus VP energy | Ridge overlay over final-byte energy | Do visual peaks follow novelty peaks? | Hypothesis to evidence if captured synchronously | False correlation from sparse sampling |
| Semantic braid | tempo, onset, kick, snare, hihat, chord confidence | Multi-strand 3D/time plot | Which semantic channels drive visible changes? | Hypothesis/evidence depending on sync | Too many channels becoming unreadable |
| Recurrence matrix | Final-byte frame vectors | Frame-vs-frame similarity heatmap | Does the effect repeat motifs or stabilise? | Evidence for output recurrence | Can hide physical LED meaning |
| PCA/UMAP frame embedding | VP bytes plus optional AP semantics | 2D/3D embedding | Do modes, passages, or scenarios cluster naturally? | Hypothesis/discovery | Embeddings can invent apparent structure |
| Ridge extraction | Final-byte luminance over LED index/time | Extracted motion paths | What named visual gestures exist? | Evidence for final-output gesture paths | Threshold sensitivity |
| Cross-lag graph | AP features plus VP metrics | Lagged correlation network | Which AP features precede which visual outcomes? | Hypothesis, promotable after repeated deterministic captures | Correlation mistaken for causation |
| Channel energy choreography | VP metrics and final bytes | Dual-channel waterfall plus energy traces | Does secondary carry body while primary carries accent? | Evidence for output role, hypothesis for design intent | Needs repeated captures across material |
| White-bias and saturation terrain | VP metrics and RGB bytes | Colour-quality terrain | Does the effect stay saturated and avoid washout? | Evidence for final visual quality | Local display gain can mislead if not labelled |

## Recommended Capture Roadmap

### Phase 1: Use Existing VPAB Data Better

No firmware change required.

- Add radial centre-origin terrain.
- Add primary/secondary delta surface.
- Add ridge extraction for final-byte luminance.
- Add recurrence matrix across captured final-byte frames.
- Keep all outputs labelled as final-byte visual evidence.

### Phase 2: Add Synchronous AP Semantic Capture

Firmware or harness work likely required.

- Capture `AudioSemanticState` beside VPAB final bytes.
- Include timestamp, frame counter, beat phase, beat tick, tempo confidence,
  onset strength, kick/snare/hihat levels, chord root/type/confidence, AP frame
  rate, and novelty rate.
- Gate synchronisation: AP row and VP row must share a comparable timestamp or
  monotonic sequence.

This phase enables beat-phase orbits, semantic braids, and causality overlays.

### Phase 3: Add AP Band Timeline

Firmware or harness work required.

- Capture a bounded GDFT/spectrogram-smooth band timeline or aggregate window.
- Keep payload compact; do not lower VPAB transport standards to force density.
- Use fail-closed framing, sequence, length, CRC, and overflow counters.

This phase enables true AP-side 3D spectrograms.

### Phase 4: Add VME Shadow Payloads

This belongs to the VME L1 lane.

- Emit canonical final bytes and candidate VME final bytes together.
- Compare modes `7`, `8`, and `18` across primary and secondary channels.
- Use the existing framed VPAB transport proof path as the carrier.

This phase promotes visualisation from discovery to equivalence proof.

## Skill And Tooling Canon

### Installed Skills To Prefer

- `thinking-model-router`: classify the pass before choosing methods.
- `thinking-model-combination`: combine systems, second-order, scientific, and
  map-territory lenses.
- `thinking-second-order`: track downstream consequences of visualisation choices.
- `thinking-systems`: treat AP to VP to LEDs as a coupled system.
- `thinking-map-territory`: prevent final-byte plots from being mislabelled as
  raw audio evidence.
- `thinking-scientific-method`: turn visual observations into testable hypotheses.
- `audio-visualisation-debug`: use plots to inspect DSP and visual signals.
- `signal-processing-verification`: use numeric verification when a DSP claim is
  promoted beyond intuition.
- `spectrasynq-audio-pipeline`: preserve K1 audio pipeline semantics.
- `python`, `numpy`, `pandas`, `scipy`, `matplotlib`, `plotly`, `pydantic`: host
  analysis and visualisation stack.
- `hallmark`, `web-design-guidelines`, `playwright`, `presentations`: presentation,
  design, and verification of polished artefacts.
- `documentation`, `architecture`: preserve source-backed meaning and decisions.
- `ssa-management`: use subagents for bounded research, but do not treat their
  prose as proof.

### External Skill Candidates

These were identified via `skills.sh` search and are not installed:

- `visualization-expert`
  - `https://skills.sh/shubhamsaboo/awesome-llm-apps/visualization-expert`
- `data-visualization`
  - `https://skills.sh/anthropics/knowledge-work-plugins/data-visualization`
- `csv-data-visualizer`
  - `https://skills.sh/ailabs-393/ai-labs-claude-skills/csv-data-visualizer`
- AntV chart visualisation skills
  - `https://www.skills.sh/antvis`
- `web-audio-api`
  - `https://skills.sh/martinholovsky/claude-skills-generator/web-audio-api`

Local `npx skills find ...` failed in this environment with npm
`package.json` ENOENT, so external skill discovery used the web-facing
`skills.sh` surfaces instead.

## External Visual Grammar Reference

The repository `https://github.com/RaidenIV/3D-Spectrogram` was cloned and
inspected in `/tmp/codex-vpab-3d-spectrogram` at commit
`e1d8debf44b1f3895114a3f77cb5c194c981d33e`.

Finding:

- It is a PyQtGraph/OpenGL plus librosa visualiser.
- It starts from a `.wav`, computes STFT/onset/tempogram/chroma, then animates
  line plots.
- Its code should not be copied into the current VPAB artefact because the data
  contract differs.
- Its useful contribution here is visual grammar: stacked time-window line
  strips, depth metaphor, and animation as a way to read temporal structure.

## SSA Consumption Ledger

| Agent | Task | Status | Consumed As | Notes |
|---|---|---|---|---|
| `019ea253-e46f-7fb1-af61-5876cdee5cc4` | Skill/tooling recommendations | Completed | Provisional context | Useful routing suggestions; not decision-critical proof |
| `019ea253-8bb0-7871-8105-fe9aecb82fd9` | AP/VP data-surface mapping | Timed out, closed | Not consumed | No claims promoted |
| `019ea253-bec8-7aa2-aea4-0809db59c65f` | Visualisation taxonomy | Timed out, closed | Not consumed | No claims promoted |

Per `ssa-management`, final synthesis and source-backed claims remain
orchestrator-owned.

## Recommended Next Work

1. Build a small AP/VP visualisation experiment matrix generator.
   - Input: existing semantic summary JSON plus decoded VPAB final bytes.
   - Output: radial terrain, channel delta surface, recurrence matrix, ridge
     extraction, and a Markdown/HTML report.

2. Add a capture-design note for synchronous `AudioSemanticState` beside VPAB.
   - Keep this as a plan until firmware change authority is explicit.
   - Require fail-closed framing and timing/cadence self-description.

3. Run a deterministic reference programme-material pass.
   - Use a named track/source or synthetic injection.
   - Capture mode `18` first, then modes `7` and `8`.

4. Promote only repeated, source-backed visual patterns into K1 vocabulary.
   - Example candidate terms: centre bloom, off-centre lobe, channel body,
     channel accent, beat-locked ridge, saturation hold, spatial drift.

5. Keep marketing and proof lanes separate.
   - Marketing can use beautified plots.
   - Proof docs must retain raw source references, gate outcomes, and boundary
     statements.

## Open Questions

- Which AP semantic fields should be captured at the same cadence as VPAB without
  bloating diagnostic payloads?
- Is a sparse AP semantic row enough, or do we need a bounded band timeline for
  true audio spectrogram work?
- Should visualisation outputs become a formal gate for VME L1, or remain a
  discovery/presentation layer until byte-exact parity is proven?
- What is the smallest deterministic track/synthetic fixture that exercises
  silence, weak tempo, locked tempo, and high-energy music in one run?

## Source Ledger

- VPAB transport closeout:
  `docs/forensics/vme_l1/2026-06-07-vpab-framed-transport-ready.md`
- VPAB semantic brief:
  `docs/forensics/runtime-evidence/2026-06-07-vpab-frame-mode18-1401-music.semantic-brief.md`
- VPAB semantic presentation:
  `docs/forensics/runtime-evidence/2026-06-07-vpab-frame-mode18-1401-music.semantic-presentation.html`
- VPAB semantic summary:
  `docs/forensics/runtime-evidence/2026-06-07-vpab-frame-mode18-1401-music.semantic-summary.json`
- VPAB payload schema:
  `SPECTRASYNQ_K1_FIRMWARE/diag/vpab_capture.h`
- VPAB payload producer:
  `SPECTRASYNQ_K1_FIRMWARE/diag/vpab_capture.cpp`
- AP semantic state:
  `SPECTRASYNQ_K1_FIRMWARE/audio/sb_semantic_state.h`
  `SPECTRASYNQ_K1_FIRMWARE/audio/sb_semantic_state.cpp`
- GDFT and novelty:
  `SPECTRASYNQ_K1_FIRMWARE/audio/GDFT.h`
- AP stream/APCAP surface:
  `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h`
- Presentation generator:
  `scripts/regression-harness/vpab_semantic_presentation.py`
- Presentation regression:
  `tests/test_vpab_semantic_presentation.py`
