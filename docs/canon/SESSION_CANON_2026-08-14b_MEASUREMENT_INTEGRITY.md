---
abstract: "SESSION CANON 2026-08-14b — HF-69..HF-80, the measurement-integrity session. Root discovery: a fortnight of colour work was measured through a PDM input reading a channel that produced no acoustic response, and NOTHING in the system asked whether its input was real. Dominant failure class this session was INSTRUMENT failure, not reasoning failure: a probe that was a no-op, a witness recording the wrong device, mismatched integration times, adjacency assumed across a lossy transport, 1 Hz telemetry used to characterise a 133 Hz latch, and an acceptance stamp reported as a system verdict. HF-80 is the meta-lesson: canon written in the morning was violated the same afternoon — encode gates, not rules. Enforced by skill k1-measurement-discipline and scripts/tools/probe_diff.py."
---

# Session canon 2026-08-14b — measurement integrity

**Continues:** `SESSION_CANON_2026-08-14_colour_fix_twitch_instrumentation.md` (HF-50..68).
**Enforced by:** skill `k1-measurement-discipline` · `scripts/tools/probe_diff.py` ·
`tests/test_tunables_registry.py` · `tests/test_colour_fix_flags_static.py`.
**Plan produced:** `docs/plans/AP_INPUT_INTEGRITY_PLAN_2026-08-14.md` (Rev B) ·
findings `docs/plans/P0_FINDINGS_2026-08-14.md`.

## 0. What this session was actually about

Not colour. **A fortnight of colour work was measured through an audio input that produced
no acoustic response, and nothing in the system asked whether that input was real.** A dead
input presents to this firmware as "a quiet room with a high floor", so it was interpreted,
calibrated and promoted as legitimate evidence.

Almost every failure below is an **instrument** failure, not a reasoning failure. The
reasoning was mostly sound; the instruments lied and were believed. That is the class to
defend against.

## 1. Failure taxonomy — HF-69..HF-80

| HF | Failure | Rule |
|---|---|---|
| **HF-69** | **Explaining a non-result.** A DSR-clock "probe" env re-declared a flag its base env already defined, so it built an identical binary — there was no variable under test. The result was then written up as "inconclusive — confounded legs", a plausible causal story for a measurement that had no experiment behind it. | **Before building a probe, PROVE the variable actually differs between the two builds** — `scripts/tools/probe_diff.py`. A probe whose variable is already set everywhere cannot fail. And when a result is null, first ask *did the experiment exist*, before authoring a mechanism for it. |
| **HF-70** | **The witness recorded the wrong device.** ffmpeg/avfoundation indices shift whenever a Bluetooth device connects or disconnects. Two legs silently recorded the *EiP Microphone* and the *Bose*, producing "room level" numbers that were not the room. | **Resolve external capture devices BY NAME on every run, and assert the capture is live** (non-zero sample fraction). A TCC-blocked microphone returns success-shaped silence — exit code 0 and a file full of zeros. |
| **HF-71** | **Mismatched integration time.** The K1's `raw_i16_rms` is a **7.5 ms** single-chunk snapshot emitted at 1 Hz; it was correlated against the witness's **1-second** RMS. Result r ≈ −0.06, which read as a damning "the mic does not track the room". | **Cross-instrument statistics require matched integration windows.** Percentile spreads are integration-dependent too. Re-run apples-to-apples before reporting any cross-instrument number. |
| **HF-72** | **Adjacency assumed across a lossy transport.** `:stream=audio` needs ~77 kB/s and has ~23 kB/s at 230400 baud, so it drops chunks. A "seam discontinuity of 10×" was computed between chunks that are not consecutive in time, and a whole railing/full-range-wander analysis was probably the same artefact. | **Any statistic assuming sample adjacency requires a lossless transport.** If the transport drops data, only *within-record* statistics are valid. |
| **HF-73** | **Undersampled the phenomenon.** The silence latch requires ~665 consecutive frames at 133 Hz; it was diagnosed from 1 Hz telemetry — one sample per 133 frames. Conclusions about what breaks the run were unreachable from that data. | **The sampling rate must exceed the decision rate of the thing being measured.** State the ratio before drawing a conclusion; if it is < 1, say the measurement cannot answer the question. |
| **HF-74** | **An acceptance stamp reported as a system verdict.** `NOISE CAL ACCEPTED` means the calibration's internal consistency checks passed — the routine grading its own homework. It was reported as "the audio front end is healthy" **in the same message that showed a locked 115 BPM beat in a silent room and silence never latching.** | **A subsystem's self-report is never a system verdict.** Health claims must be backed by an *output* measurement taken outside the subsystem. Disconfirming evidence in your own output outranks your headline. |
| **HF-75** | **Never measured the deliverable.** An entire session on AP telemetry without once measuring the plate. When finally measured, the plate was swinging **0–128 lit pixels in a silent room**, median 84 lit — and *more* active in silence than with music. | **Measure the deliverable at least once per session.** The plate is what the customer sees; AP telemetry is a proxy and this session proved the proxy can look healthy while the deliverable is pathological. |
| **HF-76** | **Inferred physical population from software activity.** "One capsule is dead" was concluded from one mono array being non-responsive. A stereo capture then showed **two distinct, non-duplicated, both-responsive channels**. Two live arrays can also arise from duplicated DMA, decoder leakage, crosstalk, one mic in both arrays, or a decoder semantic inversion. | **Software array activity is not physical population.** Independence must be *proven*: duplication check, correlation, directed near-field stimulus per position, occlusion, and a decoder-mapping swap that changes the expressed result rather than relabelling identical data. |
| **HF-77** | **Discounted the user's contradicting observation.** Three times the user was right and the metric was wrong: "there is no video" (a documented oracle that did not exist), "use the MacBook's microphone" (the missing external witness), "the mic board looks fine, check again" (it was fine — the firmware read the wrong channel). | **When the operator's direct observation contradicts your metric, the metric is the suspect.** Investigate their evidence first. This rule already existed in global canon and was still violated. |
| **HF-78** | **A parameter with no runtime setter costs a rebuild per hypothesis.** Two suspect thresholds had no setter, so each candidate value cost a build-flash-measure cycle — while a single-variable live kill is the sharpest attribution instrument available. | **Every AP/VP parameter must be settable at runtime** (`:tune`, 44 parameters, generated from `globals.h`). Generate the registry; never hand-maintain it; ratchet the drift. |
| **HF-79** | **Exposed a control wired to nothing.** The first tunable-registry generation exposed `LED_FPS` — an **output** the frame loop recomputes every frame. A setter for it would appear to work and do nothing. | **Distinguish parameter from state MECHANICALLY, not by naming taste**: a symbol the per-frame pipeline assigns is state. Caught only because the registry was checked on-device. |
| **HF-80** | **Canon written in the morning was violated the same afternoon.** HF-63..68 were authored at the start of this session; HF-66 (transport adjacency) and HF-48 (dead command) were both violated hours later, by their own author, in the same session. | **Written doctrine does not survive a long session. Only mechanical gates do.** Every lesson worth keeping must be encoded as something that BLOCKS the wrong path — a tool, a ratchet, a preflight — not a rule to be remembered. Adding another paragraph to a canon file is the *lowest-leverage* response to a repeated failure. |

## 2. Methods that worked (positive canon — reuse these)

1. **An EXTERNAL WITNESS instrument.** (Captain's idea; the highest-value method of the
   session.) Recording the room with an independent microphone broke a two-session deadlock
   and **killed the orchestrator's own leading theory twice**. When device telemetry is the
   only witness you cannot separate "the environment changed" from "the device is wrong".
   Reusable: `scratchpad/witness_ab.py` — resolves the witness by name and aborts on a
   zero-filled capture.
2. **Paired control with a commanded stimulus.** Two identical windows differing only in
   whether a known stimulus played. Produced the decisive "+22.4 dB in the room, +1.8 dB at
   the microphone" leg. Use a *real* programme track (`stimulus_35s_30s.wav`), not synthetic
   noise — Captain's correction, and the lane's own stimulus was sitting in `artifacts/`.
3. **Mutation-testing every new ratchet.** Caught two real defects the ratchets were
   supposed to prevent: a leak detector that could not detect an inline leak, and the
   `LED_FPS` exposure. **A ratchet that has never been observed going red is not a ratchet.**
4. **Pre-registered kill criteria.** P0 was designed so it could refute its own premise —
   and it did. Writing the falsification condition *before* the measurement is what made the
   refutation survivable instead of embarrassing.
5. **Generated registries with a drift ratchet**, never hand-maintained lists.
6. **Reading the code before believing the carried story.** HF-61's "stale-DC self-lock" was
   refuted in minutes by reading `start_noise_cal()` — it zeroes DC before Phase A, so the
   cal never runs on the stale value.
7. **Recording falsifications as first-class artefacts** (`P0_FINDINGS_2026-08-14.md`)
   rather than quietly re-forking.

## 3. Claims corrected this session (do not re-derive)

| Claim | Status |
|---|---|
| HF-61 "SSL fails because it is evaluated under the stale DC" | **REFUTED** — cal zeroes DC before Phase A |
| "true DC ≈ −1523" | **REFUTED** — measured **+1894**, then **+148** post-slot-fix |
| "×140 unexplained gain" | **REFUTED** — rms-vs-peak units error; chain is 19.4× as documented |
| "the bench IM69D is not hearing the room" | **REFUTED** — it hears fine on the other channel |
| "one IM69D capsule is dead/unpopulated" | **REFUTED** by the stereo capture (HF-76) |
| "the audio front end is healthy and calibrated" | **RETRACTED** (HF-74) |
| "the DSR probe was inconclusive due to confounded legs" | **WITHDRAWN** — it was a no-op (HF-69) |

## 4. The structural finding

The K1's evidence chain has **no integrity checks at its boundaries**:

- **input boundary** — nothing verifies the microphone is real (≈9 days lost);
- **instrument boundary** — nothing verifies an instrument measures what it claims (HF-69..73);
- **claim boundary** — nothing verifies a verdict rests on a property rather than an
  annotation (HF-74, HF-76).

Per Meadows, rules are a low leverage point and **changing what the gate measures is a high
one**. That is why the response to this session is a preflight tool and a probe-difference
prover, not another document — and why HF-80 exists.

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-08-14 | agent:claude-code | Created — HF-69..80, positive canon, corrected claims, structural finding. |
