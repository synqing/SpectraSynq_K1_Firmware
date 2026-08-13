---
abstract: "SESSION CANON 2026-08-14 (colour fix + twitch session): HF-50..HF-62 failure taxonomy + the methods that worked. Core truths: a perceptual fix must be gated on the FULL axis set (coverage, temporal stability, silence rest, music coupling) — optimising one axis regressed another twice; scale-blind (equalised) drives need an explicit structural rest mechanism; firmware identity is FOUR-way (bin × config blob × knob store × cal profile file); assert the mode NAME not the number; a value-fingerprint match is not provenance — conviction needs mechanism + live kill; gate flash verification on exit code + NEW epoch, never a grep filter; the cal's all-or-nothing rollback can self-lock on a stale DC [HYPOTHESIS]. Companion to SESSION_CANON_2026-08-13_colour_forensics_config_poison.md (HF-41..49) and docs/forensics/colour-fix-lane-2026-08-13.md."
---

# Session canon 2026-08-14 — the colour fix / twitch / instrumentation session

**Companions:** `docs/forensics/colour-fix-lane-2026-08-13.md` (full execution ledger) ·
`docs/forensics/colour-fix-promotion-plan-2026-08-13.md` (flag inventory + promotion gates) ·
`docs/architecture/K1_PALETTE_COVERAGE_ENGINE_DESIGN_2026-08-13.md` (design + determinism contract) ·
Skill `k1-colour-truth` (updated this session). HF numbering continues from HF-49.

## 1. What the session achieved (so the failures have context)

The colour collapse was decomposed into five measured layers and fixed (config poisons ×3,
frozen sweep, knob-parked fallback, edge-mixer off-palette rotation, hue-crushing output
filter); the consolidated candidate `k1_bench_im69d_colourfix` reached **3/4 authored
palette deployment in full product config** with palette-pure output. The fix then
**regressed motion** (full-bore twitch in silence) because the metric set was incomplete —
that regression was itself decomposed and fixed at the colour layer (sweep rest v3,
smoothing v2, S2 threshold), exposing an AP-level root cause (stale DC / cal self-lock)
that is the open handover item. Instruments built and proven: LED-level render trace,
dual-boundary hue taps, palette-authority fingerprint on telemetry, palette-derived
per-palette references, capture driver with identity/acoustic/palette assertions.

## 2. Failure taxonomy — HF-50..HF-62 (each cost real time this session)

| HF | Failure | Rule that prevents it |
|---|---|---|
| **HF-50** | **Incomplete metric set = the seesaw.** Hue-coverage was optimised to 3/4 while temporal stability and silence behaviour — unmeasured — regressed into full-bore twitching. Windowed histograms cannot see jerk. | Before optimising ANY perceptual metric, enumerate the full axis set — **coverage · temporal stability (hue velocity) · silence rest · music coupling · brightness dynamics** — and gate every candidate on all of them. A fix that moves one axis is UNPROVEN until the others are measured. |
| **HF-51** | **Scale-blind drives never rest.** The percentile sweep drive destroys absolute scale by design, so the percentile of noise-within-noise is uniform → the sweep ran at mean speed in dead silence. The code comment even claimed a silence path that did not exist. | An equalised/normalised drive needs an EXPLICIT, independent rest mechanism keyed to **temporal structure** (ring peak/mean spikiness — scale-free, fan-immune), never inherited from the mechanism it replaced. |
| **HF-52** | **Absolute-constant floors re-import the original bug in new units.** The "legacy 0.10 novelty floor" froze the sweep under LOUD MUSIC because this chain's novelty units sit below it. | No bare constants against signal-chain-dependent quantities. Thresholds derive from the stream itself (relative/structural) or are measured-per-chain with a receipt. |
| **HF-53** | **Gate-flag coupling.** Sweep rest v1 keyed on the latched `silence` flag — which latched 0/59 frames in a real room (ambient ≫ stale threshold). The fix idled behind a gate that never fired. | Consumer behaviour must not hard-depend on a calibration-dependent binary. Use such flags only as an OR-assist over a self-contained mechanism. |
| **HF-54** | **Mode number asserted, mode name unread.** "Mode 3" legs were GDFT, not bloom — the dense-index trap, WITH the driver logging `get_mode_name` that nobody read. Annotation measured, property ignored. | Every leg asserts the mode **NAME** from the device. The number is an annotation. |
| **HF-55** | **Value fingerprint ≠ provenance.** The teal matched `hsv(note_colors[7])` to the byte — and the author was the edge mixer rotating palette gold. A perfect value match convicted the wrong code path. | A fingerprint match is a hypothesis. Conviction needs the generating MECHANISM (file:line path) **plus a live single-variable kill** on the device. |
| **HF-56** | **Worktree merge no-op.** `git merge <worktree-default-branch>` printed "Already up to date", the SSA's fix (on its NAMED branch) never landed, and a fix-less build was flashed and measured. Caught only because the metric regressed. | Merge the branch named in the SSA return contract; then **grep the gated symbols in YOUR tree** before building. "Merged" is an annotation; the symbol in the tree is the property. |
| **HF-57** | **Filtered oracle, again.** `flash.sh \| grep "IDENTITY OK" \| tail -1` matched the BEFORE-flash identity print, swallowed the script's exit 3, and a 60 s leg ran on the old build. The tell was ignored: the epoch had not changed. | Gate on the script's **EXIT CODE**, and require the post-flash identity to show a **NEW epoch**. Never grep-filter a gated script inside a `&&` pipeline. |
| **HF-58** | **Firmware identity is FOUR-way** (extends HF-41): bin × config blob × **knob store** (restores CHROMA/MOOD at boot) × **cal profile file** (overwrites SSL every PDM boot). The era replay fixed only the blob; SSL flipped back to 57 on every flash reboot. | Measurement config is re-applied AND re-verified per leg after any reboot. Era replay of blob fields alone is not identity. |
| **HF-59** | **Third poison field.** `NOTE_OFFSET=0` (era 12) survived the "era config replay" because only remembered knobs were replayed — the 08-13 A/B ladder itself ran on a hybrid profile matching no chroma profile. | HF-42's "config-diff FIRST" means the **FULL dump diff** against the era dump — every field — not the knobs you remember. |
| **HF-60** | **Boot authority stack lies.** The boot palette lock (index 40, mode on) is overridden by the show-state restore that runs after it; an out-of-range persisted index **clamps to 0** (Sunset Real) — one measured window ran on the wrong palette entirely. | Never trust boot-time locks; verify live palette authority via the telemetry fields built this session (`pal=`,`pmode=`,`hd0=` HD-cache fingerprint). Lock-vs-restore ordering is an open Captain product-truth call. |
| **HF-61** | **Cal self-lock [HYPOTHESIS, strong].** The noise cal measures DC correctly (clean pass, 3×) but rolls the WHOLE profile back when SSL fails — and SSL fails BECAUSE its samples are evaluated under the stale DC (phantom ~4k baseline). The system cannot self-heal. | Multi-quantity calibrations must support **partial commit** of independently-valid results, loudly reported. (Fix planned, not yet implemented — the open handover item.) |
| **HF-62** | **Human silence ≠ mic silence.** One "silence confirmed" window contained music (bpm 81, onsets, 14k peaks in the log); fans/idle hiss are real signal too. The cal guard rightly refused 3×. | Pre-check the mic's own floor (raw int16 rms/peak on the AP line) before arming cal. The mic is the witness, not the human's intent. And **raw-vs-processed comparison is the decisive instrument**: int16 quiet + max_raw huge = processing artefact, not acoustics. |

## 3. Methods that WORKED (reuse them — this is the positive canon)

1. **Live single-variable kills** (`:edge_enabled=off`, `:incandescent_filter=0`,
   `:secondary_enabled=false`) — one serial command + 1 Hz histogram delta = decisive
   attribution in seconds. The sharpest tool of the session.
2. **Dose-response curves as mechanism fingerprints** — FILTER 0.10/0.25/0.50 vs wire gold
   separated exponential from linear behaviour in one probe.
3. **Dual-boundary differential taps** (`hpre=` pre-pipeline vs `h=` wire) — localised the
   crushing stage without reading another line of code.
4. **Fault battery + mutation check for every new metric** — the hue metric shipped with
   deliberate-RED cases and a mutation pass; it never lied all session.
5. **Palette-derived external denominators** (44 authored references) — completeness
   claims against the design authority, not the artefact being judged.
6. **Per-channel-op hue law**: multiplicative/nonlinear per-channel operators preserve PURE
   hues and destroy MIXED hues (blue survives, gold dies). Predicts this entire defect class.
7. **Mechanism-narrative downgrade**: when the SSA topology proof contradicted the
   incandescent "compounding" story, the story went to [HYPOTHESIS] while the measured fix
   effect stood. Fixes rest on measurements; stories are hypotheses.
8. **SSA round under ssa-management**: briefs with return contracts; one claim VERIFIED with
   mechanism (and re-run on-device by the orchestrator), one claim properly KILLED
   (NOT_VERIFIED is a success mode), one audit consumed after personal spot-check.
9. **Byte-inertness by construction**: every diag/fix gated; the three stable ELF sections
   (`72417182/afa23c99/d383aa70`) held through ~10 firmware changes.
10. **PR train with merge-on-green watchers** (+ known-flake retry): 7 PRs merged clean in
    one session without blocking the device loop.

## 4. Open handover state (verified 2026-08-14, start here)

- Bench `B489A500` @ `k1_bench_im69d_colourfix` (wake-v3 build), **port drifted to
  `cu.usbmodem12401`** (env pins 12201 — use `--upload-port`). SSL manually 6000 (phantom-
  baseline units — revert after the DC fix). Colour-side fixes proven; **visual response
  still wrong pending the AP-level DC/cal fix (HF-61)** — Captain confirms "nothing changed"
  perceptually, which is consistent: the phantom baseline drives the modes regardless.
- Unmerged lane commits ride on `lane/colour-fix-goldkiller` (pushed) — PR them with the fix.
- Next actions, in order: (1) cal partial-commit fix → two Captain-gated cal passes →
  re-verify silence latch + music coupling (corr(peak,lit) was 0.02); (2) the full-axis
  metric legs per HF-50; (3) promotion gates per the promotion plan; (4) golden side-by-side.

## 5. Continuation 2026-08-14 (later session) — HF-61 REFUTED, real root cause found

Three claims carried into this session were **wrong**, and all three were killed by
measurement rather than argument. Recorded here so nobody re-derives them.

| # | Carried claim | Verdict |
|---|---|---|
| **HF-61 (mechanism)** | "SSL fails BECAUSE its samples are evaluated under the stale DC" | **REFUTED.** `start_noise_cal()` sets `CONFIG.DC_OFFSET = 0` before Phase A, and the learned DC is stamped at iter 128 **before** Phase B samples SSL. The cal never runs under the stale DC. |
| **True DC ≈ −1523** | carried in the handover | **REFUTED.** Measured `dc_learned=1894` (persisted was 91), `dc_samples=12192`, `dc_rejected=0`. |
| **"×140 unexplained gain"** | raw rms 43 vs max_raw ~6000 | **REFUTED — a units error.** It compared a raw *RMS* against a processed *peak*. Measured `max_raw / raw_i16_abs_peak` = 19.4 = `INPUT_GAIN 8.0 × sensitivity ≈2.24`, exactly as documented. |

The partial commit was still the right fix, for a **different** reason than the handover
gave: SSL genuinely could not pass, so without partial commit the DC could never be
refreshed at all. Device-proven — first cal result this lane ever kept.

### HF-63 — Measure the drive on the band you actually USE

**ROOT CAUSE of the silence-twitch.** The GDFT axis is semitone-spaced from A1=55 Hz;
at `NOTE_OFFSET=12` its lowest bin is **110 Hz**. Sub-110 Hz energy contributes nothing to
spectrum, chromagram, colour or tempo — but it landed in `max_waveform_val_raw` at full
weight, and that peak is the reference for silence detection, the AGC floor and the
follower. A ~94 Hz rumble was therefore setting the loudness the entire gain structure
hangs off, while being invisible on the plate.

**Rule:** a level/threshold measurement must be taken over the SAME band the consumer
uses. A broadband peak feeding a band-limited consumer imports out-of-band energy as
false signal. Fix: `K1_AP_SUBSONIC_HPF_V1` — HPF on the PEAK MEASUREMENT ONLY
(`waveform[]` untouched, so GDFT input cannot move). Measured: `max_raw` p50 ~7135 → ~2873,
floor 1959 → 685, i.e. **below the 1500 Phase-B gate for the first time**.

### HF-64 — An external witness instrument beats any amount of self-consistent reasoning

Captain's idea, and it broke a two-session deadlock. Every leg until then compared the K1
against *itself* or against remembered numbers, so no leg could distinguish "the room is
loud" from "the device is wrong". Recording the **MacBook microphone** simultaneously gave
an independent measurement of the same room.

It immediately killed the orchestrator's own leading theory (self-generated mic noise:
the K1 swung *wider* than the room, so it was not floor-limited) and then exposed the real
one (quiet AND STEADY room, 5.0 dB spread, vs K1 16.0 dB — non-acoustic excess).

**Rule:** when a device's own telemetry is the only witness, you cannot separate
"environment changed" from "device is wrong". Get a second, independent sensor before
spending another session on inference. Reusable: `scratchpad/dual_mic_witness.py`.
**Verify the witness is live** — a TCC-blocked mic returns all-zeros, i.e. success-shaped
silence (check non-zero sample count, not just exit code).

### HF-65 — Matched integration time, or the comparison is meaningless

The first witness comparison correlated the K1's `raw_i16_rms` (a **7.5 ms** single-chunk
snapshot emitted at 1 Hz) against the MacBook's **1-second** RMS. It produced r ≈ −0.06 and
looked like a damning "the K1 does not track the room". It was an artefact of mismatched
integration windows. **Re-run apples-to-apples before reporting any cross-instrument
statistic.** Related: percentile spreads are also integration-time dependent.

### HF-66 — A "seam" between non-contiguous samples is not a discontinuity

The chunk-boundary probe reported `seam/inner = 10.14x`, which looks exactly like DMA
corruption. It is meaningless: at 230400 baud the `:stream=audio` output DROPS chunks, so
consecutive *printed* chunks are not consecutive in *time*. Any statistic that assumes
adjacency across a lossy transport is invalid. (The genuine signal in that probe was the
**within-chunk** smoothness: mean |sample| 5978 vs mean step 277 → dominant content
≈ `fs/(2π) × 277/5978` ≈ 94 Hz.)

### HF-67 — Confounded legs prove nothing; say INCONCLUSIVE

The DSR_16S PDM-clock probe ran leg A under a confirmed silence window and leg B after
music resumed. The delta is unattributable. It is recorded as **inconclusive**, not as a
refutation — a confounded result must never be laundered into a verdict in either
direction. The paired control is the fix: both legs under identical conditions, or a
within-frame control that no condition can confound.

### HF-68 — Another dead command (HF-48 recurrence)

`:stream=magnitudes` **acks `K1OK` and emits nothing** — its emitter in `k1_gdft_core.cpp`
is inside a `/* */` comment block. Second instance of this class after `:stream_agc`.
**Verify a command's EMITTER exists on the flashed build before designing a measurement
around it.** An ack is not evidence of an emitter.

### Also this session

- **Byte-gate drift was STALE-BY-TOOLCHAIN, not a leak.** `k1_hardware` stable sections at
  `eb592b08` (pre-colour-lane) rebuild byte-identical to HEAD (`8802e9ca…`), and its
  per-section hashes are exactly `72417182/afa23c99/d383aa70`. The Arduino framework was
  reinstalled 2026-08-12, after the reference was recorded. Re-recorded; all three green.
- **A leak detector that could not detect the leak.** The colour-fix ratchet anchored `-D`
  to line start, so an inline `build_flags = -DFLAG` leak passed undetected. Found by
  mutation-testing the *new* ratchet, which exposed the *old* one. Fixed for both.
- **A constant that must not be constant.** The subsonic HPF cutoff was first hardcoded for
  `NOTE_OFFSET=12`; `NOTE_OFFSET` is a RUNTIME value and 0 is shipped, where the filter
  would have cut an octave of real bass. Now derived per frame and **proven on-device** by
  moving NOTE_OFFSET and watching fc follow (0→55 Hz, 24→220 Hz, 12→110 Hz).

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-08-14 | agent:claude-code | Created at session close — HF-50..62, positive methods canon, handover state. |
| 2026-08-14 | agent:claude-code | §5: HF-61/-1523/×140 all REFUTED by measurement; root cause found (HF-63, sub-GDFT-floor energy setting the drive peak); HF-64..68 added (external witness, matched integration, non-contiguous seam, confounded legs, dead command). |
