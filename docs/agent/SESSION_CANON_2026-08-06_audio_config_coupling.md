---
abstract: "CANON from the 2026-08-06 session: the defect archetype that cost a full day — a value that stopped meaning what it meant, consumed by code with no way to notice. Seven concrete instances (absolute thresholds surviving a mic+gain change, #if/#elif with no #else, a change justified by a never-read variable, a gain change filed as docs:, a proof doc tracing the retired path, -ffast-math deleting 93 isfinite guards, RMS chosen for a discrimination it is provably blind to), each with its TELL and its GATE. Also the orchestrator/verification failures of that session and the rules they generate. Read before any change to audio constants, mic config, compiler flags, or any 'proof' document. Mechanised half lives in tests/test_mic_config_symmetry_static.py."
---

# Audio-pipeline config coupling — session canon, 2026-08-06

**Origin.** A reported symptom ("the noise gate locks out and only a finger snap releases it")
was traced through four specialist probes and ~6 hours to a chain of changes that were each
individually reasoned and locally correct, and collectively catastrophic. Every host test
passed the whole time. This document exists so that chain is never re-walked.

## 0. The one-line archetype

> **A value stopped meaning what it meant, and was consumed by code with no way to notice.**

Not carelessness. Every author was competent and left comments explaining their reasoning. The
failure is *structural*: the codebase couples a number to a hardware context that lives somewhere
else, and provides no mechanism — no build error, no test failure, no log line — for the number
to learn that the context moved.

**Corollary that makes it dangerous:** these defects are invisible to the host suite by
construction. A semantic mismatch between a value and its hardware context cannot be caught by a
test that does not have the hardware. 950 passing tests is not evidence against any item below.

## 1. The seven instances — with the TELL and the GATE

| # | Instance | The TELL (how to spot it) | The GATE |
|---|---|---|---|
| 1 | `K1_SILENCE_RMS_ENTER/EXIT` absolute, calibrated 2026-07-10 on IM73D @ gain 16; mic changed to IM69D and gain walked to 4 | A constant whose comment names a **date + hardware** and whose value is **absolute**, not a ratio | Prefer RATIO thresholds. `SILENCE_ENTER/EXIT_SSL_FRAC` were ratio-based and survived every change; the absolutes did not |
| 2 | IM69D silently inherited SPH0645 cal gates — the IM73D widening sits behind a **mutually exclusive** flag | A `#ifdef MIC_A` block that redefines constants, with no `#ifdef MIC_B` peer | `tests/test_mic_config_symmetry_static.py` (ratchet) |
| 3 | STM loudness gate: `#if MIC_A / #elif MIC_B / #endif` with **no `#else`** → value stays 0 on the SPH path → EdgeMixer modes 7/8 modulate by nothing | Any `#elif` chain over hardware flags without a terminal `#else` | Same test. Correct shape already exists: `k1_mic_auto_sense.cpp` zeroes and forces `BYPASSED / RAW_UNAVAILABLE` |
| 4 | The 8→4 gain step was justified by `threshold_loud_break` (`SSL x1.2`) — **assigned once, never read** | A rationale that cites a symbol. Grep the symbol for READ sites before believing the rationale | Never cite a value you have not grepped for reads |
| 5 | A 2x microphone gain change shipped as `docs(lane): ...` with `constants.h \| 11 ++-` | Subject type vs diffstat mismatch | Pre-commit: `docs:`/`chore:` must not modify `SPECTRASYNQ_K1_FIRMWARE/**` |
| 6 | `-ffast-math` implies `-ffinite-math-only`; GCC folds `isfinite()` to a constant. **93 sites across 42 files** silently unguarded, incl. PDM cold-boot `0/0 -> NaN` guards | `-ffast-math` present anywhere near NaN/Inf guards | `-fno-finite-math-only` must follow `-ffast-math`; asserted by the static test |
| 7 | The go-dark gate discriminates on **RMS** — the one statistic on which narrowband room hum BEATS music | A discriminator chosen without measuring BOTH classes on that statistic | Measure both classes before choosing the statistic (§3) |

### The compounding instance (worth its own paragraph)

Instance 4 is the root of the reported symptom. A device-proof document contained a section
titled **"Silence latch path (code)"** which traced `threshold_loud_break`, tabulated a "fix" to
it, and declared **"Phase 0 complete: YES"**. That symbol is assigned once and never read; the
live mechanism is an RMS Schmitt fourteen lines away, whose own source comment says it
*deliberately does not* use the peak veto. The gain was halved twice against a comparison that
does not execute — costing 4x of music headroom above thresholds nobody moved.

**Rule: a proof document's "<subsystem> path (code)" section must cite CONSUMER READ-SITE
receipts, not the assignment site.** An assignment proves a value is computed. Only a read
proves it is used.

## 2. Second-order damage — why instance 4 was expensive

The gain reduction also **defeated a safety guard nobody was looking at**. At G=8, music measured
`max_raw` 1785 and was REJECTED by the `PHASE_B_MAX_RAW` 1500 admission gate. At G=4 the same
music reads 528 and passes. Those gates exist to refuse a **music-contaminated noise calibration**
— the machine half of the Calibration Command Policy, which itself exists because `SWEET_SPOT_MIN_LEVEL`
was once poisoned 281 -> 745 exactly that way.

**Rule: before changing a gain, an input scale, or a sample-rate, enumerate every threshold
downstream of the multiply and state what happens to each.** Not "the ones I think matter" —
every one. The IM69D lane changed the mic, the gain (twice) and the AP cadence, and audited none
of the constants below them.

## 3. Choosing a discriminator (instance 7, generalised)

The go-dark gate had to separate "music playing" from "quiet room". It used RMS. Measured on
bench `B489A500`:

```
                 rms_raw p50      peak-to-mean (max/mean)
quiet room         0.0072                 1.24
music              0.0027                 3.17
```

**Music's median RMS is LOWER than ambient's**, and ~75% of music frames read at or below the
loudest ambient frame. Cause: the room floor is narrowband hum (crest ~1.26, RMS ~= peak); music
is peaky (RMS << peak). No threshold on RMS separates them at any gain, in any domain — so no
amount of retuning could ever have fixed the reported symptom.

**Rules:**
- Before picking a statistic, **measure both classes on that statistic** and state the separation
  ratio. If the distributions overlap or invert, the statistic is wrong — stop, do not tune it.
- Prefer **ratio/shape** statistics (peak-to-mean, p90/p50) over absolute level. They are
  gain-invariant and survive the hardware changes that break absolute thresholds. The
  `NOISE_CAL_SSL_MAX_P90_TO_P50_RATIO` gate (ambient 1.24 vs music 3.17, threshold 2.50) is the
  only guard in this subsystem that survived the entire gain ladder untouched.
- A guard added to fix a "will not engage" symptom must be validated in the **release** direction
  too. The 2026-07-10 commit validated only "silence latches in a quiet room" — the opposite
  direction from the failure it eventually caused.

## 4. Verification discipline — the patterns that actually worked

These are the moves that produced truth this session. Use them.

- **Compiled differential probe.** To prove `-ffast-math` deletes guards: compile a two-line
  function with and without the flag and disassemble. `movi.n a2,0; retw.n` ended the argument.
  Faster and more certain than reasoning about GCC semantics.
- **Paired control.** A bootloop appeared after flashing a new env. Flashing the *radio-free*
  env from the same head reproduced it identically — exonerating the change and relocating the
  bug. **Always test the competing hypothesis before attributing a fault to your own work.**
- **Witness, not exit code.** `EXIT=0` was `echo`'s status, not the build's. A guard returning
  `[PASS]` while the binary contained the forbidden token. Judge by a delta sampled from OUTSIDE
  the actor: object-file size, a string present/absent in the artefact, a boot line that appears.
- **Re-read your own capture at full width.** A whole diagnosis was built on `sil_pk=3` which was
  `sil_pk=314` truncated by the console at 120 chars. **Truncation is a silent data corruption.**
- **`0 results` is a hypothesis, not a verdict.** A "silent" serial port meant the chip was held
  in download mode, not that firmware was broken. `esptool --before no_reset` settled it in one
  command.
- **Grep with word boundaries when a symbol is a prefix of another.** `min_silent_level_tracker`
  vs `min_silent_level_tracker_band` — the second is live; a substring delete breaks the build.

## 5. Orchestration / process rules earned this session

- **Check `.git/MERGE_HEAD` and `git diff --diff-filter=U` before editing.** Another session's
  in-flight merge silently overwrote a set of edits. A repo is shared state.
- **Never resolve, abort, or commit another session's merge.** Its resolution encodes intent you
  do not have.
- **A stash is not a safe parking space.** A device-proven AP cadence promotion (`96/d3 -> 128/d2`)
  was stashed to unblock a merge, and the branch's own docs continued to describe it as live. The
  stash also targets pre-rename paths and can no longer simply be popped.
- **Hardware first, hygiene second.** Commit-message correctness was prioritised over a blocked
  bench. When someone's hardware is unusable and a verified-good binary exists, flash it, then
  fix the history.
- **Say when the ordered work does not address the reported problem.** Several hours of directed
  work (forensics, dead-code removal, cal corridor) were all correct and none of them fixed the
  user's actual symptom. That should have been stated loudly and early, every time.
- **SSA returns are prose, not proof.** Four probes produced excellent work; two of their claims
  were wrong in ways only an orchestrator re-run caught (a too-narrow grep; a corridor ceiling
  below the ambient floor). One probe also correctly **refuted two of the orchestrator's own
  seeds**. Re-run every decision-critical claim yourself.

## 5b. Failures from the closing hours — the expensive ones

These happened AFTER the sections above were drafted. They are the most instructive in the
session because none of them were subtle; each was a discipline already written down elsewhere
and ignored under pressure.

- **Read the FAILING INVOCATION, not the suspect file.** Every `pio run` died with
  `FileNotFoundError: 'package-postinstall.py'`. The file was inspected, found to have no
  shebang, and a whole mechanism was invented from that observation. The verbose log — which had
  not been read — said `call_pkg_script(pkg,"postinstall")` -> `Popen` -> ENOENT, i.e. a
  **corrupted package unpack**. `rm -rf ~/.platformio/packages/tool-esptoolpy*` + rebuild fixed it
  in **nine seconds**. The invented story cost ~40 minutes and blocked the user's hardware.
  *A `FileNotFoundError` out of `subprocess` means a missing EXECUTABLE, not a missing shebang.*
- **"No other user is reporting this" is a diagnostic signal.** A vendor file that is broken for
  exactly one machine is not a broken vendor file. It is a corrupt local install.
- **Never hand-patch a vendor package.** Already canon (the claude-mem scar). Done anyway — and
  it could not even work, because PlatformIO re-installed the package over the patch on every
  invocation. Reinstall, pin, or upgrade; never edit in place.
- **Hardware before hygiene.** A verified-good binary existed while the bench sat unusable, and
  the time went into splitting a commit whose message was imperfect. When someone's hardware is
  blocked and a proven artefact exists, FLASH IT, then fix the history.
- **Never write documentation about a fix that is not yet on the device.** The peakiness gate was
  written, failed to build, and then canon was drafted about the session while the user tested
  firmware that did not contain the fix. Land the fix, prove it, then document.
- **One variable per flash.** Gain, cal corridor, compiler flag and a new discriminator were
  bundled. When something then misbehaves, nothing is attributable. The user had to impose this
  rule explicitly after the fact.
- **Stage explicit paths, never `git add -A <dir>`.** That swept a scratch `pytest.log` into the
  index and blocked the commit gate for a reason unrelated to the change.
- **Say it when the ordered work does not address the reported symptom.** Hours of correct,
  directed work (forensics, dead-code removal, cal corridor, gain revert) did not touch the
  user's actual complaint. That should have been stated at every redirect, not once at the end.

## 6. What is mechanised vs what is still prose

**Mechanised** (`tests/test_mic_config_symmetry_static.py`, runs in the normal suite):
- `-fno-finite-math-only` must follow `-ffast-math` in `platformio.ini` (instance 6)
- mic-flag override symmetry ratchet: no NEW constant may be redefined for one PDM mic without a
  peer arm or an explicit, dated exemption (instances 1, 2)
- no `#if defined(K1_MIC_*) / #elif` chain in `audio/` without a terminal `#else` (instance 3)

**Still prose, and therefore still fragile** — candidates for future gates:
- `docs:`/`chore:` subjects modifying firmware (instance 5) — belongs in `scripts/hooks/pre-commit`
- proof-doc read-site receipts (instance 4)
- discriminator selection requiring both-class measurement (instance 7)

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-08-06 | agent:claude-fable-5 | Created — seven config-coupling instances with tells and gates, discriminator-selection rules, verification patterns, orchestration rules. Mechanised half landed alongside as a static ratchet test. |
