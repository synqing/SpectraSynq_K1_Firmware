---
abstract: "Tombstone record for the IM73D-gated tempo/silence constants deleted from K1 firmware on 2026-08-11. Holds the six deleted values, their measurement provenance, why the premise is void (Captain correction 2026-08-10: Bench Unit 2 carries dual IM69D130, not IM73D122), and the 11-env contamination closure. This is a RECORD, not a starting point — a future IM69D profile must be derived from first principles, not seeded from these numbers."
status: archive
---

# IM73D audio-profile tombstone — 2026-08-11

**Captain order, 2026-08-11.** Known-provisional microphone constants must not sit
in executable source waiting for the IM69D work. Deleted from source; preserved
here for provenance only.

## Why the premise is void

The values below were measured live on **Bench Unit 2, chip `0C54FC00`**, on
2026-08-09, while that unit was believed to carry an **IM73D122**.

[`CAPTAIN_CORRECTION_2026-08-10_unit2_im69d_im73d_deprecated.md`](../../hardware/CAPTAIN_CORRECTION_2026-08-10_unit2_im69d_im73d_deprecated.md)
establishes that Unit 2 physically carries **dual IM69D130**, that IM73D122 is
**deprecated**, and that the `k1_custom → k1_bench_im73d_ble` inheritance is
**FALSE AUTHORITY**. The measurements are therefore not evidence about the
IM73D122, and not evidence about Unit 2 either — they describe an unidentified
signal chain.

## The contamination closure — why this was worse than "provisional"

The constants were gated on `K1_MIC_IM73D_PDM_V1`, **not** on Unit 2. They had
already escaped their measurement context into **11 environments**:

```
k1_bench_im73d            k1_bench_im73d_mic_auto            k1_custom
k1_bench_im73d_bad        k1_bench_im73d_mic_auto_telemetry  k1_prod_im73d
k1_bench_im73d_ble        k1_bench_im73d_stm                 k1_prod_im73d_bad
k1_bench_im73d_dsr16      k1_sync_probe_bench
```

Including the production-named **`k1_prod_im73d`**, which was never measured with
them and is in the CI build matrix. `k1_hardware` (SPH0645) and the IM69D envs
were clean — verified.

## The deleted values

| Site | Constant | SPH0645 (kept) | IM73D override (DELETED) |
|---|---|---|---|
| `audio/k1_tempo.cpp` | `K1_LOCK_CONFIDENCE` | `0.60f` | `0.28f` |
| `audio/k1_tempo.cpp` | `K1_CONF_V2_REL` | `0.42f` | `0.18f` |
| `audio/k1_tempo.cpp` | `k1_check_silence()` | gate runs | short-circuited, early `return` |
| `audio/k1_tempo.cpp` | novelty pre-Goertzel | unscaled | `novelty *= 4.0f`, clamped |
| `system/globals.h` | `K1_SILENCE_RMS_ENTER` | `0.04f` | `0.001f` |
| `system/globals.h` | `K1_SILENCE_RMS_EXIT` | `0.08f` | `0.003f` |
| `effects/light_mode_waveform_tempo.cpp` | tempo velocity gate | confidence only | lock-as-authority, floor `0.55` |

Introduced by `7d93208` (five sites) and `b643b8d` (the effect gate). Both are
reachable in history; nothing is lost by the deletion.

Two details worth keeping, because they are the tell:

- The novelty multiplier was **fitted by trial** — ×2.5 was tried, left
  confidence mostly below 0.32, and was raised to ×4.0 to clear a lock floor that
  had itself been lowered to 0.28. A constant tuned to satisfy another tuned
  constant is a fit to one signal chain, not a calibration.
- The effect-level lock-gate floor existed **only** to compensate for the lowered
  lock floor. It has no independent justification and goes with it.

## What replaces them

`SPECTRASYNQ_K1_FIRMWARE/audio/k1_audio_profile.h` declares the profile and
**fails the build closed**:

```
K1_AUDIO_PROFILE = K1_AUDIO_PROFILE_NOT_CHARACTERISED   (any K1_MIC_IM73D_PDM_V1 build)
K1_AUDIO_PROFILE = K1_AUDIO_PROFILE_SPH0645             (otherwise)
```

A build whose mic has no characterised profile **will not compile** unless its
env declares `-DK1_AUDIO_PROFILE_UNCHARACTERISED_ACK` in `platformio.ini` — a
written acknowledgement that it runs SPH-derived constants on a mic they were not
measured for. Verified: stripping the ack fails `k1_bench_im73d` in 1.3 s at the
`#error`.

## The rule for whoever characterises the IM69D130

Derive from first principles on an identified microphone. Do **not** copy, scale,
adapt, seed, bound, or sanity-check against the numbers in this document. They
describe a signal chain nobody has identified. Using them as a starting point
reintroduces exactly the poisoning this tombstone removes.

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-08-11 | agent:claude-code | Created. Tombstone record for the six IM73D-gated calibration sites deleted under Captain order; contamination closure computed over platformio.ini inheritance (11 envs). |
