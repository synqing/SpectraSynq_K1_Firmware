---
abstract: "Forensic record of the K1 palette-coordinate collapse ('palettes progressively duller over 2-3 weeks; each palette a handful of colours') and its fix K1_PALETTE_VIBRANCY_V1 (commit ae5d90a, eyes-on PASSED 2026-07-03). Device-proven root cause: loud/dense music drives chroma flatness into the sparseness-gate band, the gate zeroes/crushes chroma, the palette centroid goes weak, and the held-hue freeze pins the palette to one auto-shift-swept coordinate. 'Progressive' = three stacked flag landings (06-11 gate+held-hue / 06-17-18 loud-guard / 06-30 per-band AGC) each deepening the coupling. Fix = two flag-gated levers: (1) the palette-coordinate engine reads a new POST-normalize PRE-gate chromagram export; (2) weak centroids blend held->live hue instead of freezing. Includes the disproven lanes (do NOT relitigate: output gamma/dither, deprecated Class-1 modes, calibration drift) and the standing rules. Read before touching the VP colour path or the sparseness gate."
---

# Palette-coordinate colour collapse on dense/loud music — forensic + fix (2026-07-02 → 07-03)

> **One canonical file for this incident.** Related but distinct: `docs/forensics/2026-05-25-vp-palette-auto-colour-audit.md` (colour-authority audit — a different question). Shipped-state memory: `palette-vibrancy-v1-shipped`. Device log: `docs/hardware/device-build-registry.md` (main-K1 `ae5d90a` row).

## Symptom (as reported)

"Our palettes have gone progressively duller over the last 2-3 weeks — each palette now renders as a handful of colours instead of the full vibrant traversal it used to." The regression was gradual, not a single-commit break, and it tracked **loudness**: the busier/louder the music, the flatter and more monochromatic the palette output.

## Verdict

Device-proven on the main K1 (`F887A500`). The palette **coordinate stream** — not the palette sampler — was collapsing under loud/dense input. The HD float-stop sampler was always fine; it was being fed a single, frozen coordinate. Fixed by `K1_PALETTE_VIBRANCY_V1` (commit `ae5d90a`); **Captain eyes-on PASSED 2026-07-03 ("yes it looks great")** at the loud/dense failure condition. Revert = delete one `-D` line (flag-OFF is byte-identical).

## Disproven lanes — DO NOT RELITIGATE

Each of these was investigated and ruled out with numeric proof. Re-opening them wastes a session.

- **Output gamma / temporal dither.** The firmware's 4-phase temporal dither is already active (≈×3.97 effective quantisation levels). Enabling output gamma does the *opposite* of help — it **crushes shadow codes** (153 → 17 usable low codes measured), darkening rather than enriching. Gamma is not the lever; it is a regression here.
- **Deprecated Class-1 `ColorFromPalette` modes.** The old legacy palette modes are unreachable in the active product surface (`config_types.h:184-198` gates them out). Colour-fineness in those modes is irrelevant to what ships.
- **Calibration drift.** Config/cal values were byte-stable across the window; the collapse reproduced on freshly-calibrated silence-go state. Not a cal problem.
- **Static noise subtraction.** Compiled out (`SB_GDFT_STATIC_NOISE_SUBTRACTION_ENABLED 0`, `constants.h`). Not in the path.

## Root-cause chain (device-proven)

The palette colour path is: GDFT magnitude spectrum → `make_smooth_chromagram()` (fold to 12 pitch classes → peak-normalise → **sparseness gate**) → `palette_chroma_colour_with_offset()` (circular-mean **centroid** over the 12 chroma bins → hue) → HD float-stop palette sampler → 16-bit quantise + dither. The collapse is a cascade through the two middle stages:

1. **Loud/dense music → GDFT attenuated.** AGC pins its gain to the floor (`agc_gain` 0.08-0.18, floor 0.1 in `k1_gdft_core.cpp`) and the loud-guard trims further (`gdft_trim` 0.86-0.94). The spectrum going into the chromagram is compressed.
2. **Chroma flatness sinks into the sparseness-gate band.** Live capture on the main K1 showed chroma **flatness 0.051-0.150** under loud/dense input — inside the gate's kill band. The sparseness gate (`VP_FIX_CHROMAGRAM_SPARSENESS` in `led_utilities.h`) **zeroes** the chromagram when `norm_max ≤ 0.08 || flatness ≤ 0.08`. A full **gate-ZERO** was captured live (flatness `0.0514` → final chroma max `0.0000`); post-gate chroma otherwise sat `≤ 0.133`.
3. **Weak centroid → held-hue freeze.** With near-zero chroma, `palette_chroma_colour_with_offset()` computes `total_weight ≈ 0`, so `centroid_strength < 0.08` trips the **held-hue hard freeze**: the palette hue is pinned to the last valid value and no longer traverses. The only motion left is the slow auto-shift sweep of that one frozen coordinate → "a handful of colours."

The **three-loudness-state gradient** (loud / medium / quiet captured on silicon) proved the loudness coupling directly: quiet input traversed the palette normally; loud input collapsed to the frozen coordinate.

### Why it looked "progressive"

Three independent flag landings stacked over the window, each deepening the coupling — no single regression commit:

| Landing | What it added | Effect on this chain |
|---|---|---|
| 2026-06-11 | Sparseness gate + held-hue freeze | Introduced the zero-band and the freeze — the collapse mechanism itself |
| 2026-06-17/18 | Loud-guard (`gdft_trim`) | Pushed loud-music chroma further into the gate band |
| 2026-06-30 | Per-band AGC (`SB_AGC_PERBAND_V1`) | Floor-pinned gain on loud input, flattening chroma more |

The sparseness gate is **correct for the CHROMATIC summing modes** it was written to protect (it suppresses noise-floor smear). The bug is that the **PALETTE path also consumed the gated chromagram**, even though the palette path only needs chroma as a *coordinate selector*, not as a summed magnitude — so it inherited a gate it never needed.

## The fix — `K1_PALETTE_VIBRANCY_V1` (commit `ae5d90a`)

Two flag-gated levers, both `#ifdef K1_PALETTE_VIBRANCY_V1`, additive, flag-OFF byte-identical:

1. **Pre-gate coordinate export.** After peak-normalisation but **before** the sparseness gate, export the chromagram to a new buffer `chromagram_pregate[12]`, guarded quiet at `norm_max ≤ 0.08` so genuine silence still holds (silence-hold preserved). The palette-coordinate engine reads `chromagram_pregate` instead of the post-gate `chromagram_smooth`. Anchors (post-merge): export at `led_utilities.h:1933`; consumed at `lightshow_modes.h:298` (centroid loop) and `:518` (particle palette coords).
2. **Weak-centroid blend, not freeze.** When `centroid_strength` is weak but non-silent, blend the held hue **toward the live hue** by `strength / 0.08` (`k1_vibrancy_blend_hue`, `lightshow_modes.h:267`) instead of hard-freezing. Consumer switches at `lightshow_modes.h:382` and `:389`. Critically the fallback blends toward the **live centroid hue**, never the dominant single bin — blending to dominant-bin reintroduces the 2026-06-11 dark-start crush.

New state: `chromagram_pregate[12]` (`globals.h:100` extern, `globals.cpp:37` definition), Row-3 `#ifdef`-gated pattern.

## Proof

**Host (offline counters, DENSE / QUIET / dark-start / TONAL cases):**
- DENSE (loud/dense): distinct palette coordinates **2 → 11**; coordinate entropy **0.02 → 3.27 bits**; frozen-frame fraction **99.8% → 0%**.
- QUIET: hold is **byte-identical** (hue range `0.0000`) — silence behaviour unchanged, no new flicker.
- Dark-start: palette `lit_fraction` **0.002 → 0.648** (a "sat on BLACK" start now lights; the dominant-bin crush signature would be `0.239`, confirming the blend does NOT crush).
- TONAL: entropy `3.35 → 3.42 bits` (already-healthy case not harmed).
- Gate: `pytest` 620 + clean `pio run -e k1_hardware`.

**Silicon:** `:build → git=ae5d90a env=k1_hardware` on the main K1 (`F887A500`), MAC-verified `B4:3A:45:A5:87:F8`.

**Perceptual:** Captain eyes-on **PASSED 2026-07-03** at the loud/dense failure condition — the release gate.

## Standing rules (permanent)

- **Never re-point the palette-coordinate engine at post-gate `chromagram_smooth`.** That is the collapse. It must read `chromagram_pregate`.
- **Never blend a weak centroid toward the dominant single bin.** Blend toward the live centroid hue (`k1_vibrancy_blend_hue`) or you reintroduce the dark-start crush.
- **The sparseness gate stays** for the CHROMATIC summing modes — the fix does not remove it, it routes the palette path around it.
- **Future "palettes look samey/dull" reports:** check the `[VP]` flatness / gate_gain telemetry FIRST, and remember the loudness coupling (louder → flatter → more crush pre-fix).
- **Revert** = delete `-DK1_PALETTE_VIBRANCY_V1` from `platformio.ini` (flag-OFF is byte-identical).

## Evidence anchors

- Fix commit: `ae5d90a` (`feat(vp): K1_PALETTE_VIBRANCY_V1`); registry row commit `66e5002`; consolidated onto `lane/im73d-pdm-eval` by the 2026-07-06 merge.
- Files: `platformio.ini` (flag), `SPECTRASYNQ_K1_FIRMWARE/visual/led_utilities.h` (pre-gate export), `SPECTRASYNQ_K1_FIRMWARE/visual/lightshow_modes.h` (blend helper + consumers), `SPECTRASYNQ_K1_FIRMWARE/system/globals.{h,cpp}` (`chromagram_pregate[12]`).
- Device log: `docs/hardware/device-build-registry.md` — main-K1 `ae5d90a` row (eyes-on PASSED 2026-07-03).
- Memory: `palette-vibrancy-v1-shipped`.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-07-06 | agent:claude-code | Created: canonical forensic record of the palette-coordinate collapse + K1_PALETTE_VIBRANCY_V1 fix. Numbers preserved from the 2026-07-02/03 investigation (scratch counters were ephemeral); source anchors re-grounded against post-merge line numbers on lane/im73d-pdm-eval. |
