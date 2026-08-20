# Dual-unit AP/VP + palette-cycle soak — predictions

Written **before** the soak (HF-4). 2026-08-20.

## HARD FAIL checklist (vj + colour)

- [x] HF-1 Not tuning crest
- [x] HF-2 Not admitting learner samples
- [x] HF-3 Not knob-tuning SSL
- [x] HF-4 This file exists before play
- [x] HF-5 Audible named fixtures via `afplay`, logged
- [x] HF-6 Typed serial uses leading `:`
- [x] HF-7 No BLE claim
- [x] HF-8 No BLE PASS
- [x] HF-9 Not rewriting boot lock; restore palettes after
- [x] HF-10 No intro/buffer clear
- [x] HF-11 Identity by chip ID + USB MAC, not port name
- [x] HF-12 No flash; no env cross
- [x] HF-13 This worktree
- [x] Colour: snapshot `:dump` / `:show_state` before palette writes; restore + verify
- [x] Not touching `CHROMAGRAM_RANGE`, sensitivity, SSL, cal
- [x] No `start_noise_cal`

## Fixtures (HF-5)

1. **Song A** — `ziggyx-summer-rave-155bpm.steady-drums-120s.steady_phase.all_musical.k1-real-music.48k-mono-s16.wav` (120 s, K1 real-music corpus). Dense 155 BPM drums → AP lock / FPS under load.
2. **Song B** — Querox `01 Time.mp3`, first 90 s via `afplay -t 90`. Harmonic / progressive vs the rave → colour + lock under a different spectrum.

Playback: `afplay` → current output **Bose Mini II SoundLink**. System volume will be raised from the live value for the soak and restored after.

## Palette cycle (same indices, both units, primary + secondary)

| Index | Name |
|------:|------|
| 40 | `K1_Naberius_Gold_gp` (boot lock) |
| 41 | `K1_Vepar_Pink_gp` |
| 34 | `K1_Tropical_Ultraviolet_gp` |
| 37 | `K1_Night_Sea_Amber_gp` |
| 32 | `Blue_Cyan_Yellow_gp` |
| 23 | `lava_gp` |

Song A: 40 → 41 → 34 → 37 (25 s each after a short settle).
Song B: 32 → 23 → 40 (30 s each).
Then restore the pre-soak `:show_state` indices.

## Units

| Role | Chip | USB | Env | Git on silicon |
|------|------|-----|-----|----------------|
| Main RPL | `9087A500` | `B4:3A:45:A5:87:90` | `k1_main_rpl_im69d` | `79d220fa` |
| Bench K1v2 | `B489A500` | `B4:3A:45:A5:89:B4` | `k1_bench_im69d` | `69e21140` |

## Falsifiable predictions

| ID | Claim | Fail if |
|----|--------|---------|
| P1 | After 5 s of Song A, `silence=0` on ≥70 % of `[AP]` lines on **both** chips | Either chip stays silent ≥30 % |
| P2 | Song A `peak_scaled` mean ≥ 2× ambient mean on **both** | Either chip does not rise |
| P3 | Song A `SYSTEM_FPS` p50 ≥ 120 on **both** | Either p50 < 120 |
| P4 | Song A `LED_FPS` p50 ≥ 180 on **both** | Either p50 < 180 |
| P5 | Song A tempo: `lock=1` ≥ 30 % **or** mean `conf` ≥ 0.45 on **both** | Both lock and conf miss on a chip |
| P6 | Every `:palette_index=` / `:secondary_palette_index=` ACK matches the requested **name** on both chips | Any ACK mismatch |
| P7 | Every `:edge_status` during the soak shows `EDGE_EFFECTIVE_*` ending in `_palette` (honour resolver live) | Any `untouched` / non-palette effective |
| P8 | Restore: both chips' `:show_state` palette indices equal the pre-soak snapshot | Mismatch |
| P9 | `[VP] chroma_flatness` is **palette-insensitive** (chromagram is AP, not the LED vocabulary). Colour *variation* is proven by P6+P7, not by chroma_flatness moving | N/A as a ship claim — recorded as a map/territory check |

## What this soak cannot score

Ship envs do not compile `K1_HUE_AUDIT_V1`. No `HUEAUD` hue histogram. Pixel hue-coverage is **not** claimed.
