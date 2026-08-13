---
abstract: "SSA-SIDEDOOR verdict: the non-palette teal (hue ~146, 55% of chromatic primary output under :edge_enabled=on / dual-edge SPLIT) is authored by the edge mixer's PRIMARY colour-harmony hue rotation (k1_edgemixer_apply_primary), NOT by waveform_fast's chromatic branch (refuted with mechanism). Gated fix K1_EDGE_PALETTE_HONOUR_V1 skips the RGB hue-rotation on any palette-owned channel. Both builds green (k1_bench_im69d_hueaud_s2, with/without flag)."
---

# SSA-SIDEDOOR — who authors the non-palette teal on the PRIMARY output?

**Task:** SSA-SIDEDOOR · 2026-08-13 · worktree `agent-a597a6bd48315e1c6`
**Verdict: (b) — a hue transform inside the edge mixer.** Specifically
`k1_edgemixer_apply_primary()` re-authoring the palette-authored PRIMARY buffer
post-render under dual-edge SPLIT. Candidate (a) (secondary waveform_fast
chromatic branch) is **refuted on two independent grounds** below.
Grade: VERIFIED-on-source, with ONE stated runtime assumption (dual-edge ≠
ONE_SIDED at measurement time — the brief's own "EDGE_MODE split").

## Root-cause chain (file:line)

1. **The only edge-gated writer into the primary output chain is the primary
   edge transform.** Render order (`SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino`):
   - secondary renders into the global `leds_16` with
     `vp_render_secondary_channel = true` (.ino:1356–1362),
   - the result is copied out to `leds_16_secondary`
     (`store_render_channel_output`, .ino:1375; `channel.output = leds_16_secondary`, .ino:221),
   - the secondary edge transform runs on `leds_16_secondary` ONLY (.ino:1380),
   - `leds_16` is **restored from the primary snapshot** (.ino:1389 `memcpy(leds_16, leds_16_primary_snapshot, …)`),
   - then, **iff `edge_enabled` AND `dualEdge != K1_EDGE_DUAL_ONE_SIDED`**,
     `k1_edgemixer_apply_primary(leds_16, …)` transforms the restored PRIMARY
     buffer (.ino:1408–1415) before `show_leds()`.
   The HUEAUD tap histograms `leds_out` — the post-gamma PRIMARY buffer only
   (`visual/led_utilities.h:1104–1129`). No buffer path carries secondary
   render content into `leds_out`.

2. **What the primary transform does:** `k1_edgemixer_apply_primary`
   (`director/k1_edgemixer.cpp`, function at former lines 1034–1083; now offset
   by the gated blocks) applies the mode's **colour-harmony matrix** — a
   grey-axis / OKLab **hue rotation** baked at the *mirrored* harmony angle —
   to **every pixel of the primary frame** (`k1_edge_apply_run` with
   `k1_edge_matrix_primary`). A hue rotation maps a saturated palette colour
   onto an arbitrary point of the RGB hue wheel: rotated Naberius gold
   (hue ≈ 30–40/255) lands at hue ≈ 146 → post-gamma `(0, ~0.39·b, b)` —
   **numerically identical to `hsv(note_colors[7])`** because a fully-saturated
   hue-wheel colour at 0.5833 IS that RGB shape (`system/constants.h:635–643`,
   `note_colors[7] = 0.5833 = 7/12`). The "note-G teal" fingerprint identifies
   a HUE VALUE, not a provenance — any writer emitting hue 0.5833 matches it.

3. **Why it explains the measurements:**
   - **55% of chromatic output** — the transform rewrites the whole primary
     buffer, not a leaked overlay; whole-buffer displacement is the only
     single-writer explanation of majority chromatic mass.
   - **Live kill** (`:edge_enabled=off` → teal growth 0, arcs deploy in
     authored buckets 0/16/17/18) — `config.enabled` is the first guard of both
     transforms (k1_edgemixer.cpp `k1_edgemixer_apply` / `_apply_primary`);
     disabling edge removes exactly and only these two writers.
   - Consistent with the earlier baseline note that stray buckets are "authored
     arcs displaced" — the primary rotation IS a displacement operator.

## Candidate (a) — REFUTED (the brief's required mechanism check)

`light_mode_waveform_fast.cpp` chromatic branch (`effects/light_mode_waveform_fast.cpp:82–88`,
`hsv(SQ15x16(prog)…)` with `prog = c/12` — c=7 gives the same 0.5833 hue) is
**dead when the secondary palette owns colour**: the branch is guarded by
`palette_owns_colour` (`:59–60`), which resolves through
`render_params_palette_owns_colour(rp, render_secondary)` →
`visual/lightshow_modes.h:199–201`:
`return render_secondary ? SECONDARY_PALETTE_MODE_ENABLED : …`.
`render_secondary` comes from `vp_render_secondary_channel`, set `true` for the
whole secondary pass (.ino:1357) and popped after. So with
`SECONDARY_PALETTE_MODE_ENABLED == true` at render time the HSV branch cannot
execute. **And even if it did**, its output lands in `leds_16_secondary` and is
excluded from the primary tap by the snapshot restore (chain in §1) — there is
no reach mechanism to `leds_out`. Both the authoring gate and the reach are
closed; convicting (a) would require BOTH to fail simultaneously.
(The prior session's "waveform_fast ignores palette mode" claim in
`docs/forensics/colour-fix-lane-2026-08-13.md` layer 5 matched the hue value,
not the writer — the doc itself records that show-state boot restore can
override boot palette locks, which is the only way that branch could ever run,
and still could not reach the primary histogram.)

**Falsifiable runtime check for the orchestrator (one `:dump`):** confirm
`dualEdge` was SPLIT (≠ ONE_SIDED) during the measured legs. If it was
ONE_SIDED, `k1_edgemixer_apply_primary` early-returns and NO source path
explains teal-on-primary — verdict would revert to NOT_VERIFIED pending a
render-trace probe.

## The gated fix — `-DK1_EDGE_PALETTE_HONOUR_V1`

Design law enforced: *while a palette owns a channel's colour, no path may
re-author that channel's hues off-palette.* The colour-harmony rotation is an
RGB-domain hue re-author, so under the flag it is skipped (identity pass) for
any palette-owned channel:

- `director/k1_edgemixer.cpp` · `k1_edgemixer_apply()` — before the matrix
  snapshot: `if (SECONDARY_PALETTE_MODE_ENABLED) return;`
- `director/k1_edgemixer.cpp` · `k1_edgemixer_apply_primary()` — after the
  ONE_SIDED/strength guards: `if (CONFIG.PALETTE_MODE_ENABLED) return;`
- flag-scoped `#include "globals.h"` (the existing include was `#ifdef K1_STM`-scoped).

STM modes (K1_STM_DUAL / SPECTRAL_MAP) are untouched — value-only brightness
modulation, no hue authored. Non-palette channels keep the full harmony
transform. Everything sits under `#ifdef K1_EDGE_PALETTE_HONOUR_V1` → compiled
out (byte-inert) without the flag. Follow-up design (not this patch): a
palette-DOMAIN edge split (sampling-offset differentiation) so palette users
regain edge differentiation without leaving the palette.

## Build proof

Env note: the brief's `k1_bench_im69d_hueaud_s2psi` does not exist in this
worktree's `platformio.ini` (orchestrator owns env additions); verified on the
nearest in-chain env `k1_bench_im69d_hueaud_s2`.

```
$ pio run -e k1_bench_im69d_hueaud_s2                                    → exit 0, 0 errors
$ PLATFORMIO_BUILD_FLAGS="-DK1_EDGE_PALETTE_HONOUR_V1" \
  pio run -e k1_bench_im69d_hueaud_s2                                    → exit 0, 0 errors
```

Positive control: the first with-flag build FAILED
(`'SECONDARY_PALETTE_MODE_ENABLED' was not declared`) proving the gate compiles
in under the flag; fixed by the flag-scoped include, then green.

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-08-13 | agent:claude-code (SSA-SIDEDOOR) | Created — verdict (b) edge-mixer primary hue rotation, (a) refuted with mechanism, K1_EDGE_PALETTE_HONOUR_V1 fix + build proof. |
