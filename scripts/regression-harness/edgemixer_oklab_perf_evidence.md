# EdgeMixer OKLab — on-device performance evidence (GATE 1 of 2)

Device: K1 bench, chip **B489A500** / MAC b4:3a:45:a5:89:b4 (IM73D mic, LED io4/5), env `k1_bench_im73d`.
Two-gate rule for OKLab-as-DEFAULT: (1) headroom measured on device [**this file**], (2) plate A/B [**pending**].
Measured 2026-07-09. OKLab is NOT yet the code default (still SUM/faithful, byte-inert); this is gate-1 evidence only.

## Per-strip transform cost — `:edge_bench` (synthetic fully-lit 160 px = worst case)
| build | faithful | luma | OKLab |
|---|---|---|---|
| pre-opt (`b2bb0d0`) | ~214 µs | ~460 µs | **3400 µs** |
| LUT+gamut+inline+fusion (`d48eb1b`) | 207 µs | 402 µs | **1213 µs** |

OKLab 3400 → 1213 µs (2.8×). This is the full-precision floor — further reduction requires a precision
cut, which the no-lite standard forbids. LUT no-lite cost host+device certified ≤ 0.00042 OKLab ΔE.

## Full-frame cost — VP_PERF (`ENABLE_VP_PERF_AUDIT=1` build of `1dd4eb8`), UNDER REAL AUDIO
Frame budget = **8333 µs** (120 fps). Worst-case edge config: dual=**mirror**, oklab, complementary, strength 1.0.
Audio via computer speakers @30 %, K1 mic pickup confirmed (peak_scaled listed).

| source | edge | frame max | over-budget | dropped | peak_scaled |
|---|---|---|---|---|---|
| MESHUGGAH – Bleed | OFF | 5005 µs | 0 | 0 | 1.166 |
| MESHUGGAH – Bleed | ON (dual OKLab) | 4963 µs | 0 | 0 | — |
| Avicii – Levels | ON (dual OKLab) | 4956 µs | 0 | 0 | 1.242 |

Edge-OFF ≈ edge-ON: dual-edge OKLab adds **no measurable frame cost** under real content — the near-black
passthrough skips unlit pixels, and a live effect never lights all 160 at once. Pathological all-pixels-lit
ceiling = 5031 + 2×1213 = **7457 µs < 8333 µs**.

## Conclusion — GATE 1 SATISFIED
OKLab holds 120 fps: single-strip default ~5000 µs frame, dual-strip A ~5000 µs frame, **0 over-budget / 0
dropped** under real audio, ~3.3 ms margin. Headroom gate PASS. **Gate 2 (plate A/B) pending** — required
before OKLab is made the shipping default. **(SUPERSEDED — gate 2 satisfied 2026-07-09; see below.)**

## GATE 2 — plate A/B (SATISFIED 2026-07-09)
Bench K1 B489A500, E build `4974560`, EDM source @30 %, one held-open serial session (no reset between
compared states). Captain eyes-on verdict:

| Decision | Verdict | Locked default |
|---|---|---|
| Topology (one_sided / split / mirror @ triadic) | **split** | `dualEdge = SB_EDGE_DUAL_SPLIT` |
| Lightness (faithful vs oklab, saturated complementary) | **oklab** (desaturation trade judged acceptable) | `rotationSpace = SB_EDGE_ROTATION_OKLAB` |
| E spatial (uniform vs masked) | **masked** (provisional; runtime-switchable) | `spatialUniform = false` (already the default) |

Defaults locked in `director/sb_edgemixer_lite.cpp` (`sb_edge_config`); `enabled=false` stays byte-inert
until turned on, so the device still boots with EdgeMixer off. Hardware-attested on reflash: boot
`:edge_status` = ROTATION oklab / DUAL split / SPATIAL masked; `VERIFY_RESULT=PASS`. Anti-circularity
honoured — the plate, not the CIELAB metric, was the arbiter; the metric (drift 48/21/0.6) set the
direction, the eye confirmed it. Not quoted as a clean 6.8x win.

Also closed the `edge_mode=` collapse-warning gap: setting mode=complementary while dual=mirror now fires
`EDGE_WARN` (hardware-verified; no false positive at mirror+triadic).

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-07-09 | agent:opus-4-8 | Created. Gate-1 on-device timing evidence (was in the handover/session, now committed to the branch per Captain's evidence-hygiene note). |
| 2026-07-09 | agent:opus-4-8 | Gate-2 plate A/B SATISFIED — Captain verdict split/oklab/masked; defaults locked in sb_edge_config (hardware-attested B489A500); edge_mode= collapse-warning gap closed. |
