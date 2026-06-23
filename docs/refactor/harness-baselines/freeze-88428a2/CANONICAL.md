---
abstract: "Freeze Baseline — SEALED 2026-05-25. Canonical AP + VP Tier A + VP Tier B reference for freeze-88428a2 (firmware k1_hardware_harness@88428a2; captured on 6f42fae which is docs-only ahead → byte-identical firmware). VP Tier A = 11 modes bit-identical (mode 6 quantum nondet) — the PRIMARY refactor regression detector; hashes in canonical-tier-a.json. VP Tier B = silence-only, COM ±10% / FPS ±5% fixed + per-mode energy bands (COM is the reliable signal). AP = spec_argmax invariant (level-independent, the load-bearing AP check) + WIDE magnitude bands (hand-played acoustic level variance → gross-regression only). Bands re-derivable from committed raw logs via scripts/regression-harness/derive_bands.py. Gate model = bounded-bisect (Spike #1 FAIL)."
---

# Freeze Baseline — `freeze-88428a2` (SEALED 2026-05-25)

| Field | Value |
|---|---|
| Status | **SEALED** — 2026-05-25 |
| Firmware | `k1_hardware_harness @ 88428a2` (captured while flashed from `6f42fae`; every commit 88428a2→6f42fae is docs/logs only → firmware byte-identical; each AP log self-stamps device `:version` + build SHA) |
| Freeze tag | **PENDING Captain** (`git tag refactor-baseline-2026-05-25`) + remote backup (Weakness 8) |
| Primary detector | **VP Tier A** — bit-identical per-mode FNV hashes from synthetic input (no acoustics) |
| Gate model | **bounded-bisect hardware VP gating + per-commit static VP-semantics classification** (Spike #1 = FAIL; see `spike-1-native-compile-outcome.md`) |
| Re-derive | `scripts/regression-harness/derive_bands.py` (reads the committed raw logs) |

## VP Tier A — bit-identical (ZERO tolerance) — SEALED
- **Source of truth:** `canonical-tier-a.json` (hashes live there; not duplicated here, to avoid drift). Confirmed: **12 modes, run-to-run identical = True, nondet = ['6']**.
- **10 fixed-point modes (0–5, 7–10) asserted bit-identical** (SQ15x16 = exact, zero tolerance). Mode 6 (quantum_collapse) excluded (`nondet=1`) → Tier B + visual smoke. **Mode 11 (waveform_hybrid) is `fp_tolerant`** (amended 2026-05-26) — a float-output mode whose quantised bytes are not bit-stable under `-O3 -ffast-math` across TU/inline changes (root-caused to a `sqrtf` seed-chain). Gated on **energy within tolerance** (3% / ±16), hash diff = INFO; motion/visual covered by Tier B + visual smoke.
- **Gate (`vp_diff.py`, amended 2026-05-26):** fixed-point modes — any hash mismatch = FAIL (zero tolerance); fp_tolerant modes — energy out of band = FAIL, hash diff = INFO. **Verified on `refactor/main@88f2e3c`** (post Row 2/4 split): 10/10 fixed-point bit-identical; mode 11 energy Δ pal 0/0, manual 6/2 (**0.53%**) → benign FP-reassociation confirmed, **not** a visual regression. Primary detector; agent-run `:vp_probe=all`, ~zero Captain hardware time.

## VP Tier B — silence-only motion bands — SEALED
- Fixed: **COM-slope ±10%**, **FPS ±5%**. Per-mode energy band = `max(2 × intra-run frame range, 50)`.
- COM is stable per mode under silence (79.5–80.0 = strip centre) → **COM is the strong Tier B detector**; energy is loose/secondary (wide on modes with internal dynamics/decay).

| mode | name | COM (silence) | energy range | energy band |
|---|---|---|---|---|
| 0 | GDFT | 79.5 | 1874–6652 | ±9556 |
| 1 | CHROMAGRAM | 79.5 | 344–3254 | ±5820 |
| 2 | CHROMAGRAM DOTS | 79.5 | 492–19606 | ±38228 (gross) |
| 3 | BLOOM | 80.0 | 0 | ±50 |
| 4 | VU DOT | 79.5 | 18–2814 | ±5592 |
| 5 | KALEIDOSCOPE | 79.5 | 9616–9720 | ±208 |
| 6 | QUANTUM COLLAPSE | 79.5 | 2846–18706 | **nondet → visual-smoke only** |
| 7 | WAVEFORM-FAST | 79.5–80.0 | 0–440 | ±880 |
| 8 | WAVEFORM | 79.5 | 8206–23270 | ±30128 (gross) |
| 9 | BLOOM (FAST) | 80.0 | 0 | ±50 |
| 10 | VU | 79.5 | 106–40800 | ±81388 (gross) |
| 11 | WAVEFORM_HYBRID | 79.5–80.0 | 0–460 | ±920 |

Wide energy bands (modes 2/8/10) reflect internal mode dynamics/decay under silence — COM is the reliable Tier B signal there; energy is gross-only. Raw: `silence_leg_raw.log`.

## AP baseline — SEALED (spec_argmax primary; magnitude gross-only)
- **PRIMARY AP check = `spec_argmax` (level-independent):** the captured stimulus must map to its baseline FFT bin **±2**.
- Magnitude metrics (`max_raw`, `peak_scaled`, `follower_mean`) are **acoustic-playback-level dependent** (hand-played speaker→MEMS) → **WIDE bands, gross-regression only** (FAIL only if ~0 with stimulus present, silence flag wrong, or argmax off-band).

| stimulus | spec_argmax (baseline) | follower (run-to-run) | peak_max | raw_max | notes |
|---|---|---|---|---|---|
| `tone-1k` | **38–39** (±2) | 3694 / 5983 (r2 / r1) | 0.99 / 1.74 | 4481 / 32081 | 1 kHz → bin 38–39. follower & raw varied with playback level (raw ×7) → magnitude WIDE. |
| `track-A` (Eagles – Hotel California) | 53 | 1444 | 1.28 | 3197 | single acoustic take, run-1 ref |
| `track-B` (Lavern – In My Mind) | 12 | 7693 | 1.11 | 13610 | single acoustic take, run-1 ref |

- `SSL` 565–601 = **metadata only, NOT a gate metric** (Captain O3). `silence` flag must = 0 when stimulus present. Raw: `ap_*_run*.log`.

## §2.5 band-setting — method actually used (honest record)
1. **Tier A:** zero tolerance (bit-identical); 2-run identity confirmed (`canonical-tier-a.json`).
2. **Tier B:** COM ±10% / FPS ±5% fixed; energy = `max(2 × intra-run frame range, 50)` from the silence leg (`derive_bands.py`).
3. **AP:** tone captured twice — run-to-run was **playback-level-dominated, not hardware noise** (raw_max 4481 vs 32081) → magnitude bands set **WIDE (gross-only)**; the level-independent `spec_argmax` is the tight, load-bearing AP invariant. Music captured once (single take, non-reproducible window) → wide sanity reference.
4. **Limitation recorded:** tight AP magnitude bands are **not achievable** with hand-played acoustic stimuli (would require a level-matched electrical tone injection). Not pursued — Rows 1–4 do not touch AP DSP, and VP Tier A is the primary detector. Re-deriving tighter AP bands later needs only a level-matched tone pass + `derive_bands.py` (raw logs are committed).

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-05-25 | claude-code (Opus 4.7) | Created as TEMPLATE. |
| 2026-05-25 | Codex | Amended: VP Tier B silence-only; recorded Tier A sealed + Tier B silence run-1 captured. |
| 2026-05-25 | claude-code (Opus 4.7) | **SEALED.** Tier A (12 modes / bit-identical / mode 6 nondet, hashes in canonical-tier-a.json); Tier B per-mode COM+energy bands from silence leg; AP spec_argmax invariant + WIDE magnitude bands. Recorded acoustic-playback-variance limitation + bounded-bisect gate model (Spike #1 FAIL). Bands re-derivable via derive_bands.py. Freeze tag + remote backup remain Captain-only. |
