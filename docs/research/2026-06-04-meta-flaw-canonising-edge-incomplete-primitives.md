---
abstract: "The systemic flaw the 2026-06-04 saliency dig exposed: our recovery/spec/canonisation process records NODES (constants, struct fields, names, structures) and drops EDGES (the invariants, cross-boundary dependencies, reference-semantics that make nodes correct). Node-complete docs LOOK authoritative, so omissions get trusted and propagate — and incorrect primitives get canonised. Names the flaw, the evidence, why it recurs, and the structural fix (capture edges; make invariants executable; validate-before-canonise; territory-as-oracle)."
---

# The Meta-Flaw: we canonise edge-incomplete primitives

## The flaw
Our recovery/spec/canonisation process records **NODES** — constants, struct fields, function names, structures — and silently drops **EDGES**: the invariants, cross-boundary dependencies, and reference-semantics that make those nodes *correct*. A node-complete doc *looks* authoritative, so its omissions get trusted, transcribed, and propagated. **Correctness lives in the edges; we have been canonising the nodes.** A node-only map is worse than an obviously-incomplete one, because it presents as complete while omitting exactly what determines whether it works.

## Evidence — three load-bearing edges dropped (2026-06-04 saliency)
1. **threshold ↔ domain.** v3's `SaliencyTuning` constants (0.5 / 0.05 / 0.02) presuppose v3's *conditioned* feature domain (log1p, bounded, fluxScale=20). The spec recorded the numbers, dropped the domain → ported verbatim onto the fork's RAW features → harmonic axis never fires, flux/rms mis-scaled. *A parameter is meaningless without its domain.*
2. **form invariant.** The event gate must be a fixed-floor relative gate (v3 `ControlBus.cpp:271-273`). The spec under-specified it → the implementer INVENTED a self-ratcheting `2×EMA(overallSaliency)` gate → fires *more in silence than music*. *A function's behaviour is its exact form, not its name.*
3. **metric ↔ reference.** "Recall" was scored against all 14,908 beats (max achievable 0.0146) instead of the `segments/` reference that exists but went unused → structurally impossible to pass. *A metric is meaningless without its reference definition.*

Each recorded the WHAT and dropped the load-bearing dependency. Each produced a *silent* error that looked like a different problem ("weak detector") until the territory was executed.

## Why it recurs (systems + archetype)
- **Cross-boundary dependency.** The threshold lives in `saliency.h`; the conditioning it depends on lives in the AP — a different subsystem. An extractor reading `saliency.h` alone NEVER sees the edge. Edges that cross file/subsystem boundaries are the ones that get dropped.
- **"Shifting the Burden."** We firefight instances (this effect, this primitive) while the edge-dropping *process* persists → the next port repeats the failure. The fundamental fix (a process that captures invariants) atrophies under symptomatic fixes.
- **Canonisation propagation.** A trusted node-only doc gets transcribed faithfully — omissions included — so the error compounds across ports. Same anti-pattern the memory discipline already names (the PipelineCore false-claim that propagated across 3 projects for 2 months).

## The fix (the path to ascension)
1. **Capture EDGES, not just NODES.** Every spec records the invariants, the cross-boundary dependencies, and the WHY each value/form/metric presupposes. *A constant without its domain is an incomplete spec by definition.*
2. **Make invariants EXECUTABLE.** Every load-bearing claim carries a CHECK that fires when violated (assert the input domain; test the gate form; gate the metric on the right reference). Documented invariants drift; executable ones can't be silently dropped.
3. **Validate-before-canonise.** A doc is PROVISIONAL/transcribed until its edges are validated against the running territory (build + measure). Only then does it earn "canon." 
4. **Territory is the oracle.** Lead with executable validation (real build + real metric + a measured discriminator). The swarm found in minutes — by RUNNING the territory — what six canonised docs hid all session. Treat docs as hypotheses to execute, not truths to transcribe. (This is also why the Claude swarm in the real env succeeded where codex's sandbox + node-only docs failed.)
5. **Re-tag existing canon PROVISIONAL (Bayesian).** This instance sharply lowers the prior in *every* node-only doc produced this session — the decomposition guidebook, `k1-motion-canon`, the FOUND motion doctrine, the saliency spec, the why-v3-AP finding. Not wholesale distrust: validate their load-bearing edges just-in-time, as each is used.

## Self-application (red-team)
The Run-1 spec orchestrated in this session transcribed v3's tuning constants verbatim without the domain edge — **this flaw includes our own briefs.** The corrected method binds the orchestrator, not just the donor docs.

## The next direction is the first application
The Step-1 + Step-2a experiment (gate fix + segments-based recall, then re-run and *measure*) IS the corrected method in action: replace "the doc says X" with "the measurement says X." If precision clears ~0.4–0.5, it validates both the saliency recovery and the methodology.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-06-04 | agent:orchestrator | Created — names the systemic node-vs-edge canonisation flaw exposed by the saliency diagnosis swarm; structural fix + Bayesian re-tagging of existing canon as provisional. |
