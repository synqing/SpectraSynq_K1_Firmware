---
name: load-bearing-edges
description: >
  Detect and prevent the most dangerous knowledge-transfer failure: recovering / porting /
  documenting / trusting a primitive while silently dropping the LOAD-BEARING EDGES (the
  invariants, cross-boundary dependencies, and reference-semantics that make it correct).
  Node-complete-but-edge-incomplete artifacts LOOK authoritative, get canonised, and the
  omission propagates and dooms everything downstream. INVOKE THIS whenever you: port/recover
  code or a parameter from another build/branch/codebase; transcribe constants, thresholds,
  a function's behaviour, or a metric into a new context; trust a "canonical"/handover/spec
  doc you did not author; or debug a catastrophic, counter-intuitive downstream failure that
  "looks like X" but might be a dropped upstream invariant. The shape is specific and stands
  out once you know where to look. British English.
---

# Load-Bearing Edges — recovering knowledge without planting the seed of failure

> **The one sentence.** Correctness lives in the **edges** (invariants, dependencies, references),
> not the **nodes** (constants, fields, names, structures). Our default extraction records nodes
> and silently drops edges; a node-complete artifact *looks* complete, so the omission is trusted,
> canonised, and propagated — a seed planted early that dooms everything downstream and manifests
> late, disguised as a different problem. This skill teaches you to see the seed, name it, and
> kill it before it canonises.

Worked case study (read if you want the concrete shape): `docs/research/2026-06-04-meta-flaw-canonising-edge-incomplete-primitives.md` — a recovered audio primitive failed catastrophically (fired *more in silence than music*); the headline "weak detector" diagnosis was an artefact; the true causes were three dropped edges + a bent measuring scale, invisible until the territory was executed.

---

## 0 · When to invoke (the triggers)
Invoke at the moment of TRANSFER or TRUST, not after the failure:
- You are **porting / recovering** code, a parameter, a function, or a behaviour from another build, branch, codebase, version, or paper.
- You are **transcribing** constants / thresholds / a metric / an algorithm into a new context.
- You are about to **build on, or canonise, a doc you did not author** (a spec, handover, "canonical" reference, prior agent's findings).
- You are **debugging a catastrophic or counter-intuitive downstream failure** — the kind that "looks like X" but smells wrong (impossible numbers, inverted behaviour).
- You are **writing a spec / handover** that others will transcribe.

If none of these — you probably don't need this skill. If one does — the cost of skipping it is a canonised error that compounds.

---

## 1 · Frame & name the problem
**The class:** *edge-incomplete canonisation* (a.k.a. "the dropped load-bearing edge", "the seed of failure").

- **Node** = an entity you can copy: a constant, a struct field, a function name, a data structure, a metric name.
- **Edge** = the thing that makes the node correct *in its context*: the **domain/scale/units** a value lives in; the **exact form** a behaviour must take; the **reference/ground-truth** a metric is scored against; the **upstream conditioning** a value presupposes; the **why** it works in the source.
- **The trap:** nodes are trivial to extract and *feel* complete. Edges are invisible if you read only where the node lives — because the edge usually **crosses a boundary** (the threshold is here; the conditioning it assumes is in another subsystem). So the default extraction is node-complete and edge-blind, and **a node-only map presents as authoritative while omitting exactly what determines correctness.**
- **Temporal signature:** the edge is dropped **early** (recovery/spec) and the failure manifests **late** (downstream), disguised as a different problem. You must trace **upstream to the seed**, not patch the symptom.

---

## 2 · How to think (the thinking-skill choreography — which lens, at which stage)
Route with `thinking-model-router`; then run these in sequence. Do not skip the early stages — most damage is done by jumping to "fix the symptom".

1. **FRAME — `thinking-first-principles` + `thinking-map-territory`.** Ask: *what actually makes this primitive correct?* (reduce to the irreducible dependency chain). Then: *the doc/spec is a map — what does it omit?* Name every node; for each, ask "what edge does this presuppose that isn't written down?"
2. **LOCATE THE CHAIN — `thinking-systems`.** Draw the transfer chain (§3). Correctness is a property of the *whole chain*; a drop at any link silently dooms everything downstream. Find the actual broken link, not the loudest symptom.
3. **GENERATE FAILURE PATHS — `thinking-red-team` + `thinking-archetypes`.** Attack the artifact: *how could this be silently wrong while looking right?* Match the recurring pattern — is this "Shifting the Burden" (firefighting instances while the edge-dropping process survives) or a canonisation-propagation chain?
4. **WEIGH — `thinking-bayesian` + `thinking-debiasing`.** A canonised doc looking complete is **weak evidence** it is correct (it was validated for *nodes*, not *edges*) — do not let "it's canon" inflate your prior. Guard the specific biases: **anchoring** on the doc, **confirmation** ("the detector is weak" because that's the headline), and the **"looks complete" trap**. Before trusting a *failure*, suspect the **measuring scale** too.
5. **ANTICIPATE — `thinking-second-order`.** If you canonise this as-is, what does every downstream consumer inherit? One dropped edge, trusted, becomes N broken builds.
6. **RESOLVE — `thinking-triz`.** The contradiction "docs must be authoritative AND must not canonise errors" resolves by *separation*: separate **provisional** (transcribed) from **canon** (edge-validated); and make the invariant **executable** (a check that fires) rather than merely documented (an assertion that drifts).

---

## 3 · The layers — how many places an edge can be dropped
A recovered primitive is a **chain**. An edge can be dropped at every link, and a drop at any link dooms everything after it:

| # | Link | The edge that gets dropped | Tell |
|---|------|----------------------------|------|
| L1 | **Feature production** | the units/scale/conditioning of the raw inputs | a value used downstream with no stated domain |
| L2 | **Conditioning / preprocessing** | the normalisation/log/AGC/gating the source applied *before* the value was meaningful | thresholds copied without their preprocessing |
| L3 | **Parameterisation** | the **domain** a constant lives in (a `0.5` only means something in `[0,1]` log-space) | verbatim constants across a boundary |
| L4 | **Form / logic** | the **exact form** of a function (named, not specified → re-invented wrong) | "a gate that…", "smoothing", "a threshold" with no expression |
| L5 | **Emission / event** | the trigger/hysteresis/state rule that converts a signal into an event | self-referential gates, missing silence/idle handling |
| L6 | **Measurement** | the **reference** a metric is scored against (the *scale itself* is edge-incomplete) | "recall/precision" with no "against WHAT"; impossible bounds |
| L7 | **Canonisation** | the validation status (provisional vs validated); the omission becomes "trusted" | "canonical", "handover", "spec" with no executable backing |

"How many layers?" — at least these seven, plus the **meta-layer**: the validator you'd use to *catch* the drop is often itself edge-incomplete (a bent scale can't weigh the meat). Always check the scale before condemning the meat.

---

## 4 · Where to look & what to look for (the shape — it stands out once you know it)
**Where:** the **boundaries** (between files, subsystems, builds, versions, papers) — edges hide where you stop reading. The source's **conditioning pipeline** (upstream of the value). The **exact form** of anything described by intent. The **reference definition** of any metric. The **validator's own correctness**.

**The tells (each is a SUSPECT, not yet a verdict):**
- **Verbatim-across-a-boundary:** a constant/threshold transcribed into a new context with no stated domain/units/scale. → recover the source's *domain*, re-derive the value in the *new* domain.
- **Named-not-formed:** a behaviour given by name or intent, not its exact algorithm. → demand the form; assume an implementer will otherwise invent a wrong one.
- **Metric-without-reference:** a score with no explicit ground-truth, an assumed denominator, or a *structurally impossible* bound. → pin the reference before trusting any number.
- **Cross-boundary dependency:** the value's validity depends on something in a subsystem you didn't open. → open it; the edge is there.
- **Looks-complete-and-trusted:** you're about to build on a canonical artifact you never executed. → it is a hypothesis until run; treat it so.
- **Symptom-doesn't-fit-cause:** a catastrophic, counter-intuitive failure (inverted behaviour, "impossible" numbers). → suspect a dropped edge or a bent scale, **not** the obvious headline cause.
- **The validator is unaudited:** before believing a FAIL, audit the benchmark/metric/test that produced it.

---

## 5 · What to do (prevention & cure — the path to ascension)
1. **Capture edges, not just nodes.** Every spec/recovery records, per value/form/metric: its domain/scale, its cross-boundary dependencies, its reference, and *why* it works in the source. **A constant without its domain is an incomplete spec by definition.**
2. **Make invariants executable.** Each load-bearing claim carries a CHECK that *fires* when violated (assert the input domain; test the exact form; gate the metric on the right reference). Documented invariants drift; executable ones can't be silently dropped.
3. **Validate-before-canonise.** An artifact is **PROVISIONAL** until its edges are validated against the running territory (build + measure). Only then is it **canon**. Tag accordingly.
4. **Territory is the oracle.** Lead with executable validation — a real build, a real measurement, a *measured discriminator* — over reading more docs. Running the territory finds in minutes what edge-incomplete docs hide for a whole session.
5. **Re-tag inherited canon as provisional (Bayesian).** Finding one dropped edge sharply lowers the prior in *sibling* node-only artifacts. Don't distrust wholesale — validate their edges **just-in-time** as each is used.
6. **Bind yourself.** This applies to specs *you* author and orchestrate, not only to donor docs. The orchestrator who transcribes a node-only brief plants the same seed.

---

## 6 · Pre-flight gate (output before you port / canonise / trust)
```
Artifact & transfer: <what, from where, to where — name the boundary crossed>
Nodes captured:      <the entities>
Edges per node:      <domain/scale · exact form · reference · upstream conditioning · why>
Cross-boundary deps: <what this presupposes that lives elsewhere — and did you open it?>
Executable checks:   <the assert/test/gate that fires if an edge is violated>
Validator audited:   <if judging a result: is the measuring scale itself edge-complete?>
Status:              PROVISIONAL (edges unvalidated) | CANON (edges validated against territory)
Layers swept (§3):   <which of L1-L7 you checked>
```
If any edge is "unknown" → status is PROVISIONAL; do not canonise; do not let a downstream consumer trust it as fact.

---

## 7 · Stop conditions
- A constant/threshold is being ported with no stated domain → STOP; recover the domain.
- A behaviour is specified by name only → STOP; specify the form.
- A metric has no explicit reference, or an impossible bound → STOP; fix the scale before reading the number.
- You're about to canonise/act on a doc whose load-bearing claims you have not executed → STOP; mark provisional, validate the edges that matter for this use.
- A failure is catastrophic and counter-intuitive → STOP; suspect a dropped edge / bent scale before the headline cause.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-06-04 | agent:orchestrator | Created — distilled from the K1 saliency meta-flaw (edge-incomplete canonisation). Teaches the thinking choreography (§2), the named layers (§3), the detection shape (§4), prevention (§5), and a pre-flight gate (§6). Promotion-worthy to ~/.claude/skills/ (general, cross-project). Case study: docs/research/2026-06-04-meta-flaw-canonising-edge-incomplete-primitives.md |
