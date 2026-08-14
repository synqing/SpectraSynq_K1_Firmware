---
name: k1-measurement-discipline
description: >-
  HARD-FAIL preflight for ANY K1 measurement, probe, capture, A/B leg, oracle or
  "is it working?" question. Use BEFORE building a probe env, before any device
  capture, before comparing two instruments, and before writing any verdict that
  rests on measured numbers. Encodes HF-69..80 (2026-08-14): a probe that tested
  nothing, a witness that recorded the wrong device, mismatched integration times,
  adjacency across a lossy transport, 1 Hz telemetry for a 133 Hz latch, and an
  acceptance stamp reported as a system verdict. Canon:
  docs/canon/SESSION_CANON_2026-08-14b_MEASUREMENT_INTEGRITY.md
---

# K1 Measurement Discipline

**Why this exists:** on 2026-08-14 the canon HF-63..68 was written in the morning and two
of its rules were violated the same afternoon **by their own author**. Doctrine does not
survive a long session. This skill is the checklist that runs *before* the measurement, and
the tools it names BLOCK the wrong path rather than describing it.

**The session it came from:** a fortnight of colour work was measured through an audio input
that produced no acoustic response. Nothing asked whether the input was real.

---

## A · Before you build a probe

**Prove the variable under test actually differs.**

```bash
python3 scripts/tools/probe_diff.py <probe_env> --expect <FLAG>
```

Exit 1 means **NO-OP PROBE** — the flag is already defined somewhere in the `extends`
chain, so both builds are identical. This happened (HF-69) and the null result was then
explained with a plausible mechanism that had no experiment behind it.

> **When a result is null, first ask whether the experiment existed.** Only then reach for
> a mechanism. Authoring a cause for a non-experiment is worse than reporting nothing.

## B · Before you trust a capture

1. **Resolve external devices BY NAME, every run.** avfoundation indices shift whenever a
   Bluetooth device connects or disconnects. Two legs silently recorded the wrong
   microphone and produced "room level" numbers that were not the room. (HF-70)
2. **Assert the capture is live.** A TCC-blocked microphone returns exit 0 and a file of
   zeros — success-shaped silence. Check the non-zero sample fraction, not the exit code.
3. **Record the identity of what produced the data**: build epoch, env, config. Firmware
   identity is four-way — bin × config blob × knob store × cal profile.
4. Reuse `scratchpad/witness_ab.py`; do not re-roll device resolution.

## C · Before you compare two instruments

| Ask | Because |
|---|---|
| Do both have the **same integration window**? | A 7.5 ms snapshot vs a 1 s average produced r ≈ −0.06 and nearly a false "the mic is deaf" verdict. (HF-71) |
| Does the statistic assume **sample adjacency**? | `:stream=audio` drops chunks at this baud. A "seam discontinuity" was computed between non-consecutive chunks; the railing analysis built on it was an artefact. (HF-72) |
| Is the **sampling rate above the decision rate**? | The silence latch needs ~665 consecutive frames at 133 Hz; it was diagnosed from 1 Hz telemetry — 133× undersampled. State the ratio; if < 1, say the measurement cannot answer the question. (HF-73) |
| Do both legs share **acoustic/environmental conditions**? | Confounded legs are INCONCLUSIVE, never a refutation. |

## D · Before you write a verdict

1. **A subsystem's acceptance stamp is not a system verdict.** `NOISE CAL ACCEPTED` is the
   routine grading its own homework. It was reported as "the audio front end is healthy" in
   the same message that showed a locked 115 BPM beat in a silent room. (HF-74)
2. **Measure the deliverable at least once.** A whole session ran on AP telemetry; when the
   plate was finally measured it swung **0–128 lit in a silent room** and was *more* active
   in silence than with music. AP telemetry is a proxy and the proxy lied. (HF-75)
3. **Software activity is not physical truth.** Two responsive arrays are not two
   microphones — duplication, decoder leakage, crosstalk and semantic inversion all produce
   plausible pairs. Prove independence. (HF-76)
4. **Check your own output for disconfirming evidence** before choosing a headline.

## E · The operator outranks your metric

When Captain's direct observation contradicts a measurement — *"there is no video"*,
*"use the MacBook's microphone"*, *"the mic board looks fine, check again"* — **the metric
is the suspect.** All three were right; all three exposed a broken instrument. Investigate
his evidence first, before defending the number. (HF-77)

## F · Instruments must be able to fail

- **Mutation-test every new ratchet.** Break the thing it watches, watch the right test go
  red, restore. This caught a leak detector that could not detect an inline leak, and a
  registry exposing `LED_FPS` — an output the frame loop overwrites, i.e. a control wired
  to nothing. (HF-79)
- **A fault battery must include cases expected to be RED**, and you must observe them go
  red. `probe_diff.py --self-test` is the pattern.
- **Pre-register kill criteria.** Write the condition that would refute your hypothesis
  *before* measuring. P0 was built this way and duly refuted its own premise — which was
  survivable precisely because it was written down first.

## G · Live tuning beats rebuilding

44 AP/VP parameters are settable at runtime — `:tune` (list), `:tune=NAME`,
`:tune=NAME,VALUE` (echoes before → after). A single-variable live kill is the sharpest
attribution instrument available; a rebuild-per-hypothesis is not. The table is generated
from `globals.h` by `scripts/tools/gen_tunables.py` and ratcheted against drift — never
hand-edit it. (HF-78)

## H · Stop gates

- About to report a **null result with an explanation** → run `probe_diff.py` first.
- About to compare two instruments → state both integration windows out loud.
- About to call a subsystem "healthy" → name the *output* measurement backing it.
- About to conclude from device telemetry alone → measure the plate.
- Operator says it is broken while your metric says fine → **stop, read their evidence.**

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-08-14 | agent:claude-code | Created — HF-69..80 encoded as a pre-measurement contract with blocking tools. |
