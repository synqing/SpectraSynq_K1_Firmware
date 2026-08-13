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
