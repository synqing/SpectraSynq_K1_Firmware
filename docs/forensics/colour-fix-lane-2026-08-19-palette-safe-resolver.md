---
abstract: "HONOUR_V1 evolution — palette-safe EdgeMixer resolver. The 2026-08-13 honour gate proved an invariant (do not escape the selected palette) by skipping EdgeMixer entirely while a palette owned the channel. That made EDGE_MODE a lie. Captain 2026-08-19 directed the fourth option: palette-aware complementary, then the whole harmony family. Same invariant, palette-position rotation instead of a bare return. Serial :palette_mode= now follows secondaryMode. EDGE_EFFECTIVE reports requested vs effective truthfully."
---

# Colour-fix lane — palette-safe EdgeMixer resolver (2026-08-19)

## Diagnosis

`palette_mode` was being treated as two contradictory contracts at once:

1. A colour **source** — take the effect colour from this palette.
2. A colour **ownership/constraint** — nothing downstream may alter this hue.

`K1_EDGE_PALETTE_HONOUR_V1` (colour-fix P5.A, 2026-08-13) silently chose (2) by
bypassing EdgeMixer (`if (PALETTE_MODE_ENABLED) return;`) on both strips. The
controls, serial ACK, and mental model still behaved as if palette and EdgeMixer
were independent composable features. Complementary reported `EDGE_MODE:
complementary` while the pixel path was identity. Turning palette **off** could
appear to *introduce* palette colours because the RGB harmony rotation had been
the only thing pushing samples off the authored arc.

A second load-bearing bug sat beside it: `:palette_mode=` always wrote
`CONFIG.PALETTE_MODE_ENABLED` (primary), while the hotkey
`serial_toggle_target_palette_mode` routed on `secondaryMode`. Captain could
think they were testing secondary palette-off + complementary while serial had
flipped primary.

## Captain directive (2026-08-19)

Do not flash A (honest echo only), B (geometry without complementary colour), or
C (honour off / unrestricted RGB rotation). Fourth option:

> A palette defines the available colour vocabulary; effects and EdgeMixer may
> arrange, select, interpolate and modulate that vocabulary, but must not
> synthesize unrelated hues while palette ownership is active.

**Effect decides what is happening. Palette decides what colours the world
contains. EdgeMixer decides how those colours relate across space.**

Scope ruling: the resolver covers the whole harmony family (complementary,
analogous, split-complementary, triadic, tetradic). SATURATION_VEIL executes
under palette ownership (it modulates; it does not synthesize hues).

## Resolver design

- Vocabulary snapshot + 64-bin hue-to-position inverse LUT, published at
  `palette_hd_unpack` time (`k1_palette_edge_bridge`, switch-time only).
- Per-mode θ / satRetain factored into `k1_edge_mode_theta_sat` so the RGB
  matrix bake and the palette path cannot drift. Palette-OFF RGB path stays
  the certified golden-master lineage (±1 LSB).
- Position shift Δ = θ/2π × per-strip dual factor (ONE_SIDED / SPLIT / MIRROR).
  Complementary+MIRROR→SPLIT coercion is unchanged.
- Per-pixel: identical centre-mask geometry to `k1_edge_apply_run`; look up
  palette position from pixel hue; wrap by Δ; sample the vocabulary; rescale
  to the pixel's brightness; apply satRetain toward the pixel's BT.601 luma;
  blend by amount with the same endpoint-exact discipline as `k1_edge_mix`.
- Fail-closed: generation 0 or count 0 → identity, never garbage.

`K1_EDGE_PALETTE_HONOUR_V1` keeps its name and env placement (evolved
implementation, same invariant). Off on `k1_hardware`; on on
`k1_main_rpl_im69d` and `k1_bench_im69d`.

## Serial channel semantic

`:palette_mode=` now routes on `secondaryMode` exactly like the hotkey:

- primary → `CONFIG.PALETTE_MODE_ENABLED` + `save_config_delayed()`; echo
  `PALETTE_MODE (primary): on|off`
- secondary → `SECONDARY_PALETTE_MODE_ENABLED` (no CONFIG save); echo
  `PALETTE_MODE (secondary): on|off`

`:secondary_palette_mode=` is unchanged (explicit-target escape hatch).

## EDGE_EFFECTIVE echo

`k1_print_edge_status` adds:

```
EDGE_EFFECTIVE_SECONDARY: complementary_palette
EDGE_EFFECTIVE_PRIMARY: untouched
```

Names: `off`, `untouched`, `<mode>_rgb`, `<mode>_palette`,
`blocked:vocab_cold`, `saturation_veil`, STM names. Host replay reports
`_palette` from ownership alone (vocabulary is never published on that
harness); generation detail is device truth.

## Golden-regen ticket

Authorised by Captain GO 2026-08-19 ("palette-aware complementary" / "Flash
the fucking devices"). Behaviour-change, not a refactor freeze.

| Golden | Why it changed |
|---|---|
| `tests/golden/serial_replay.golden.jsonl` | `:palette_mode=` echo text; new corpus line `palette_mode=false` after `secondary_control=true` locks the secondary-routing branch |
| `tests/golden/serial_struct.golden.jsonl` | Regenerated; **byte-identical** (edge handler bodies still call `k1_print_edge_status()`) |

`tests/golden/MANIFEST.sha256` updated with those files. Existing honour
env-flag pins (`test_colour_fix_flags_static.py` FIX_FLAGS,
`test_wfhyb_k1_variant_pack_static.py`, `test_main_rpl_env_static.py`) stay
valid because the flag name is unchanged. New ratchets pin: no bare bypass
return; `k1_edge_apply_palette_run` at both gates; `EDGE_EFFECTIVE_*` echo;
`:palette_mode=` references `secondaryMode`.

## Revert

Single-commit `git revert 79d220fa` restores the bypass semantics. The flag
remains the compile-out switch.

## Silicon (2026-08-20)

Main RPL `9087A500` on `/dev/cu.usbmodem1401`:

```
IDENTITY OK: git=79d220fa env=k1_main_rpl_im69d epoch=1787158141
CHIP ID: 9087A500
SYSTEM_FPS: 137.69
LED_FPS: 152.46
EDGE_MODE: complementary
EDGE_EFFECTIVE_SECONDARY: complementary_palette
EDGE_EFFECTIVE_PRIMARY: complementary_palette
```

`complementary_palette` (not `untouched`) is the serial proof that the
resolver is live: old honour would have echoed identity while a palette
owned both channels. Cal inherited. No `start_noise_cal`. B489 / F887 not
touched.

Captain eyes-on remains: palette OFF + complementary = RGB split; palette
ON + complementary = in-palette opponent; cycle analogous / split / triadic
/ tetradic under palette ON; veil under palette ON; `secondary_control`
then `:palette_mode=off` names secondary.
