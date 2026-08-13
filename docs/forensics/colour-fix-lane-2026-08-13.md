---
abstract: "Colour fix lane — live execution doc (opened 2026-08-13). Status: RANGE=1 writer IDENTIFIED (full71 harness); hue-coverage metric built + fault-battery-proven (hue_coverage.py); instruments = K1_HUE_AUDIT_V1 1Hz tap + K1_RENDER_TRACE_V1 LED-level PSRAM frame capture (rtrace_arm/status/dump), both in env k1_bench_im69d_hueaud only. Captain override 2026-08-13: NO video — LED-level capture is the instrument; the golden bin exposes no pixel surface (HF-48-verified), so the numeric reference is the PALETTE-DERIVED target (authored hue arc = external denominator) and the golden bench state is only for the ONE final side-by-side eyes-on. Next: palette-reference extraction, then bisect main against the metric."
---

# Colour fix lane — execution doc

**Contract:** [`colour-nuance-regression-verdict-2026-08-13.md`](./colour-nuance-regression-verdict-2026-08-13.md) §Fix lane
· Canon: `docs/canon/SESSION_CANON_2026-08-13_colour_forensics_config_poison.md` · Skill: `k1-colour-truth`

## Status ledger

| Contract step | State |
|---|---|
| 2. Find the RANGE=1 writer | **DONE 2026-08-13** — Aug-9 full71 harness stimulus, no restore, no load clamp. [`chromagram-range-poison-writer-2026-08-13.md`](./chromagram-range-poison-writer-2026-08-13.md) |
| 1. Hue-coverage metric | **BUILT** — `scripts/regression-harness/hue_coverage.py` (self-test fault battery incl. deliberate-RED + mutation check, all proven). Firmware tap `K1_HUE_AUDIT_V1` + env `k1_bench_im69d_hueaud` added. Oracle capture PENDING (needs Captain, below). |
| 3. Bisect main's colour path | NOT STARTED — blocked on oracle number only for the final target; suspect-bounding work can start on the tap alone. |
| 4. ONE final eyes-on | NOT STARTED |

> **Superseded in part — see Update below.** Captain struck the camera-video oracle
> (2026-08-13): no video of the K1 has ever been part of this process, and the
> instrument is LED-level capture, not photons-via-phone. The HF-48 finding that the
> golden bin has no pixel surface still stands; the oracle definition moves to the
> palette-derived reference (Update section).

## Instrument design (deviation from the letter of the contract, recorded)

The contract said "build the metric on the `K1_MATRIX_AUDIT_V1` machinery … run it on the
golden bin". **Verified (HF-48 discipline, strings on the golden bin + `db300db` source): the
golden bin has NO pixel-output surface** — no matrix audit, no VPAB, no `frame_dump`;
`vp_out_test` emits hashes and energy scalars only; `vp_stream` is scalar diagnostics. The
golden source is not reconstructible, so no tap can ever be added to it. Therefore:

- **Oracle instrument (any firmware): camera video** of the physical strips, analysed by
  `hue_coverage.py video`. Photons are the ultimate artefact boundary; the metric is
  comparative (same camera, same placement, same track both sides), so camera colour
  fidelity cancels out.
- **Bisect instrument (main only): `K1_HUE_AUDIT_V1` tap** — 24-bucket cumulative hue
  histogram of the final post-gamma primary buffer, 1 Hz `HUEAUD` serial line, matrix-audit
  pattern, env `k1_bench_im69d_hueaud`. Consumed by `hue_coverage.py hueaud`. Lets the
  bisect iterate without spending Captain looks or camera sessions.
- **Cross-calibration:** the first fixed-main candidate gets BOTH a tap run and a camera
  run; the pair anchors tap-metric numbers to camera-metric numbers.
- SpectraSynq.K1_Testbed (firmware-v3/BeatPulse host simulator) was evaluated for reuse:
  it simulates the OTHER lineage and has no device capture or hue metric — not applicable
  to the golden bin; its `vis/` renderers may be borrowed later for presentation only.

## ORDERING LAW

**The golden state is RESIDENT on bench B489A500 right now** (golden readback + era config,
Captain-approved). The oracle capture costs ZERO flashes while it stays resident.
**Nothing reflashes or reconfigures the bench until the oracle video is captured.**
(The golden bin file + era config recipe survive regardless, but a re-setup burns a
Captain esptool GO + config replay for nothing.)

## Oracle capture protocol (Captain-assisted, one session)

> **Superseded** — Captain struck the video path; see Update 2026-08-13 below.
> No capture session is needed; the numeric reference is palette-derived and the
> bisect instrument is `rtrace`/`HUEAUD` on-device.

1. Port check first (`lsof /dev/tty.usbmodem*`, Cursor monitor closed — HF-46). Optional
   single `:dump` to re-verify era config identity before capture; every serial open risks
   a device reset, so at most one, and the state is flash-persisted either way.
2. Music: `~/Music/PioneerDJ/Demo Tracks/Demo Track 1.mp3` on the Bose @ vol 60
   (laptop speakers are ~5× too little SPL — inherited canon).
3. Camera: phone propped steady, framing the bench strips, **exposure pulled DOWN** so LED
   colours don't clip to white on the sensor; no room-light changes mid-capture.
4. Capture ≥2 min on **mode 32** (the Captain-approved golden look) and ≥2 min on
   **mode 3** (the single-colour scar mode). Modes changed by Captain or one serial
   `:set_mode` (dense index — probe first).
5. Analyse: `python3 scripts/regression-harness/hue_coverage.py video <file> --roi <strip crop>`
   → per-minute coverage + entropy = **the oracle numbers**, filed here + JSON artefact
   under `docs/forensics/` (tracked, not `_scratch/`).

## Then: bisect (instrument = tap, target = oracle)

Ranked suspects (verdict §Defect 2): `b643b8d6` mono-hue knob fallback (bound to true-black,
preserve saturation) · joint-gate chroma-thinning (its trigger) · `97276b3a` boot palette
lock · held-centroid attractor + `K1_PALETTE_ENERGY_EXCURSION_V1` (measured, parked — likely
centrepiece; prior data: helps palette 7, hurt palette 3) · `024591dd` bin remap ·
`isfinite`/NaN-hue correction (if the remembered character was NaN chaos, recreate as a
bounded hue-wander deliberately, never by re-breaking maths). Each candidate change is
measured on the bench (`k1_bench_im69d_hueaud` + music) against the oracle numbers.
P5.A colour policy (`COLOUR_POLICY_GO.md`, Kill1/Kill2, SAME_SCAR modes 3/9/12/13) frames
the mode-level fixes. **Bench cal note:** before any current-main measurement, restore
`:sweet_spot_min=187` (measured cal; era 253 overwrote it) — or recal under Captain
silence-go.

### Update — 2026-08-13: Captain override — LED-level capture, no video

Captain: there has never been any video of the K1 in this process, and the intended
instrument is the render-capture **process** (capture what is actually rendered at the
LED level, host-analyse). Applied:

- **`K1_RENDER_TRACE_V1`** (`visual/k1_render_trace.{h,cpp}`, env `k1_bench_im69d_hueaud`):
  PSRAM ring capture of the FINAL post-gamma primary output buffer — arm→tick→dump per the
  telemetry canon, 3000-frame capacity (~120 s at every_n=4). Serial surface
  `:rtrace_arm=<s>[,every]` / `:rtrace_status=1` / `:rtrace_dump=1`; CRC-headed hex dump.
  Decoder: `hue_coverage.py rtrace` (identical chromatic gate to the HUEAUD tap, so tap and
  trace numbers agree by construction). Static ratchets: `tests/test_render_trace_static.py`.
- **Camera-video mode remains in the tool but is NOT the oracle path.**
- **Oracle redefinition:** the golden bin still cannot emit frames (HF-48 finding stands),
  so the numeric reference becomes the **palette-derived target**: for each palette, the
  authored hue set (from the palette definitions) is the denominator — an EXTERNAL
  denominator per the completeness-claim rule — and the metric target is deployment of that
  authored arc (coverage/entropy vs the palette's own). Captain's single golden-vs-fixed
  side-by-side eyes-on remains the human validation of "matches what I remember".
- Consequence: **no capture session is required before bisect work starts.** The bench's
  resident golden state matters only for the final eyes-on; the ordering law relaxes to:
  don't reflash the bench without recording that the golden state must be re-established
  (bin + era config recipe are preserved) for the final look.

### Update — 2026-08-13 (later): DEFECT BASELINES MEASURED on-device

Bench flashed `main @ adbc133e` / `k1_bench_im69d_hueaud` (k1-flash-verified.sh, identity
OK). Music: Demo Track 1 on the Bose (acoustic-path proof gate in the driver:
`silence=0` ≥80% required before any capture — one leg auto-aborted on a quiet passage,
proving the gate). Driver: `scripts/regression-harness/colour_baseline_capture.py`.

**Third residual poison field found by the full config diff (HF-42 done properly):**
`NOTE_OFFSET` was **0** (era truth **12**) — the full71 `chroma_profile` stimulus zeroed it
and the 08-13 era replay restored RANGE but not the offset, leaving a hybrid matching NO
profile (shifted chromagram frequency window). **The 08-13 A/B ladder itself ran under
NOTE_OFFSET=0.** Fixed via `:set_chroma_profile=default` (12/60 pair, persisted, reboots).

**Three persistence stores discovered (config identity is FOUR-way, not (bin×blob×cal)):**
config blob (RANGE/SENSITIVITY/NOTE_OFFSET, reboot-stable) · knob store (CHROMA/MOOD —
reboot RESTORES knob values over the blob) · cal profile file (`/cal_profile_im69d.bin` —
every PDM boot overwrites `SWEET_SPOT_MIN_LEVEL` from it; bench file currently holds 57,
NOT the 187 measured 2026-08-12). Measurement config must therefore be re-applied per leg
after any reboot — the capture driver does this by construction.

**Baselines (mode set + verified, era knobs + SSL=187 applied per leg, 60 s, ~2950-3000
frames each; artefacts in `docs/forensics/colour-fix-baselines-2026-08-13/`):**

| Leg | Authored deployment (Naberius Gold, 4 buckets) | Missed | Stray (out-of-palette) | Entropy |
|---|---|---|---|---|
| mode 32, NOTE_OFFSET=12 | **1/4 (25%)** | gold 1,2 + violet 17 | 14,15,22,23 | 1.08–1.73 bits |
| mode 3, NOTE_OFFSET=12 | **1/4 (25%)** | gold 1,2 + violet 17 | 0,14,15,22,23 | ~2.2 bits |
| (mode 32, NOTE_OFFSET=0 — first pass, superseded) | 2/4 | gold 1,2 | 0,14,15,21,22,23 | 2.5–2.9 bits |

Reading: the stray buckets are the authored arcs displaced ~2–3 buckets (auto-colour-shift
hue rotation — ON in the era too, so era-authentic), while the WARM arc's chromatic mass is
absent entirely (rendered achromatic → white — invisible to the hue gate). The regression
target: fixed-main must deploy 4/4 authored buckets with zero warm-arc white-out, matching
the palette-derived reference.

### Update — 2026-08-13 (evening): THE COLLAPSE DECOMPOSED — five layers, all measured

Bisect state on bench @ `k1_bench_im69d_hueaud_eq` (palette identity asserted per leg via
the new `pal=/pmode=/acs=` HUEAUD fields; a live probe caught the bench on **palette 0**
in one earlier window — show-state boot restore can override the boot palette lock and
clamps out-of-range indices to 0 — so the driver now hard-fails any leg without pal=40).

| # | Layer | Status | Evidence |
|---|---|---|---|
| 1 | `CHROMAGRAM_RANGE` 60→1 config poisoning | FIXED; writer identified (full71) | writer doc |
| 2 | `NOTE_OFFSET` 0 residual poisoning (era 12) | FIXED (`set_chroma_profile=default`) | config diff |
| 3 | **Auto-shift sweep FROZEN** — novelty-cubed drive below floor; dominant hue bucket static in every 10 s window | K1_HUE_DRIVE_EQ_V1 percentile drive: **sweep proven moving** (dominant migrated 23→0 across the minute, entropy 1.1→2.8 bits); runs ~10× slow due to strict-`<` tie-ranking on flat novelty — mid-rank fix staged | mode32 legs v1/v2 |
| 4 | Thin-chroma fallback parked at the CHROMA-knob arc position (palette's first colour) | K1_FALLBACK_HELD_U_V1 staged (held-anchor seed); unmeasured | code + baseline |
| 5 | **Edge-mixed SECONDARY bleeding non-palette HSV** — waveform_fast ignores palette mode; its note-G teal `hsv(note_colors[7])` (fingerprint-matched to FastLED rainbow 146 → post-gamma (0,.39b,b)) was **55% of all chromatic output**; `SECONDARY_PALETTE_MODE_ENABLED=true` is a dead annotation for it | PROVEN by live kill: `:edge_enabled=off` → teal buckets growth 0, Naberius arcs deploy cleanly (13450/95871/89903/34033 in buckets 0/16/17/18 over ~6 s) | edge-kill probe |

Also disproven: the white-out hypothesis on this config — achromatic-lit is 4% at mean
V=5/255 (dim greys). "Gold renders white" on the 08-13 ladder was under different
identity (NOTE_OFFSET=0 / SSL=253 / possibly palette-0 window).

Mode-name discipline: "mode 3" in these legs is **GDFT** (dense-index trap — the driver
now logs `get_mode_name` and the analyst must read it; asserting the number is measuring
the annotation).

**Captain live observation (bench on the EQ experiment):** violet less vibrant than
remembered — consistent with (a) the sweep no longer parking on violet and (b) mode 32's
temporal RGB EMA desaturating while the position moves. Position-space smoothing (P1
applied to smoothing: EMA the coordinate, sample the palette last) is the staged next
candidate for the wake modes.

**Next legs:** tie-rank fix flash → sweep-speed re-measure → eqfb leg → secondary
palette-honouring fix for waveform_fast (side-door closure, P5.A frame) → S2 per-palette
excursion. Target: 4/4 authored deployment on Naberius with entropy ≈ authored 1.95 bits,
zero out-of-palette mass, then the ONE golden-vs-fixed eyes-on.

## Guard debt from the writer finding

Any control-writing harness MUST `:dump`-snapshot before first write and restore + verify
after last (rule recorded in the writer doc and the k1-colour-truth skill). A reusable
snapshot/restore helper belongs in `scripts/regression-harness/` when the next such harness
is written.

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-08-13 | agent:claude-code | Opened the lane — writer DONE, metric built + proven, tap + env added, instrument design decision recorded, oracle capture protocol defined. |
| 2026-08-13 | agent:claude-code | Captain override applied: video struck; K1_RENDER_TRACE_V1 LED-level capture added (+ratchets); oracle redefined as palette-derived target; capture-session dependency removed. |

### Update — 2026-08-13 (late): S2 shipped; the gold-hue crusher hunt (instrumented, one step open)

- **S2 (`K1_PALETTE_BRIGHT_EXCURSION_V1`)**: per-palette brightest-stop attractor computed at
  palette load; energy² pulls sampling toward it (env `k1_bench_im69d_hueaud_s2`). Gates green.
- **Metric colour-space check**: output gamma is DISABLED (`ENABLE_OUTPUT_GAMMA 0`) — wire
  bytes are engine bytes; the palette_reference space matches the boundary. Good.
- **HD-cache identity fingerprint** (`hdn=`/`hd0=` on HUEAUD): **engine PROVEN sampling
  Naberius** (`hd0=020014`, 10 stops) while the wire's warm mass sits at g/r≈0.17 vs authored
  gold 0.55. The warm content matched Sunset Real's ratios by coincidence of the crush.
- **Located so far**: the incandescent FILTER applies whenever `INCANDESCENT_FILTER>0`
  (INCANDESCENT_MODE=0 does NOT disable it — line ~938); at the configured 0.50 with lookup
  (1.0, 0.445, 0.156) it takes gold's g/r 0.55→0.397 (era-consistent — same code+value at
  `db300db`). **Residual ×~0.43 g-crusher unidentified** — candidates: temporal RGB EMA
  mixing gold with red-adjacent sweep states, S2 pull dynamics, another RGB-space op in the
  show path. General law confirmed: per-channel nonlinear/multiplicative ops preserve PURE
  hues (blue) and crush MIXED hues (gold) — the precise mechanism class of "gold dies".
- **Next leg (defined)**: differential telemetry — log the engine's sampled colour
  pre-pipeline alongside the wire bytes; the divergence point names the operator in one leg.
