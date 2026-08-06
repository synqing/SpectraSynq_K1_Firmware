# AP advice Phase 2 — ×2 formula decision (2026-08-05)

**Task ID:** `phase2-x2-ab` (behavior-change ticket)  
**Branch:** `feat/ap-advice-phase0-im69d-gain8`  
**Prereqs:** Phase 0 `1ae9d4a` (G=4 silence PASS); Phase 1 `024591d` (ghost retirement)

## CTO decision

**Global drop of ×2** — `K1_GDFT_X2_CROSSOVER_BIN = 0` → every bin uses `block_size = fs/Δf_neighbor` (1-semitone Rayleigh), still capped at 2000.

Decision rule applied: under available stimulus / host evidence, rise-time / punch degradation at crossover=0 was **not clearly worse** than the ×2 baseline in a way that justified a sited hybrid knee. Simplest correct formula wins. **No decimator.**

## Evidence used

| Source | Finding |
|---|---|
| Host window model | A2: 76.4 ms (×2) → 152.8 ms (1-semitone); still under 2000-sample cap (1956) |
| Host centre honesty | A4 rounded-k error improves (~−20 Hz → ~+5 Hz) as `k` doubles with window |
| Bench flash | Guard-verified `B489A500` @ `/dev/cu.usbmodem112401`; bootloader+partitions+app; AP alive, SSL=74 persisted, `cal_valid=1` |
| Quiet silence re-proof | Room not quiet this session (`max_raw`~344 > SSL×1.2); Phase 0 silence proof retained; no boot-loop after correct image flash |
| Core-0 budget | ~2× Goertzel sample-ops expected; still low single-digit % — no decimator |

Runtime A/B scaffolding retained behind `#ifdef K1_GDFT_X2_AB_V1` (optional on `k1_bench_im69d`; off by default) with AP `bass_mag` / `rise_ms` fields when enabled.

## Production formula

```c
resolution_div = (i < x2_cross) ? 2.0f : 1.0f;  // x2_cross default 0
block_size = SAMPLE_RATE / (max_distance_hz * resolution_div);
```

## Phase 3

**DEFERRED** — parabolic peak, adaptive per-bin floor, dual-mic coherence. Explicit TODO only; not in this PR story.

## Residual risks

- Bottom-octave temporal smear possible (~2× window) on very fast kick+bass; re-open with `K1_GDFT_X2_AB_V1` + isolated kick if Captain hears smear
- Dirty-tree flash provenance may show Phase 1 SHA until Phase 2 commit rebuild
- Do not flash app-only `firmware.bin` at 0x0 on S3 (bootloop) — use bootloader+partitions+app or PIO upload
