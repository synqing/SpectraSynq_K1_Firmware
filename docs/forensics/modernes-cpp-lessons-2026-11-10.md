---
abstract: "Modernes C++ lane (plan docs/plans/MODERNES-CPP-EXECUTION-PLAN.md), FE firmware, 10 Nov 2026. Catalogue surveyed (20 topic families, 398 article links); 19 lessons verified against primary references. Two independent code audits plus an independent review found real defects in serial input handling and in which core resets the noise calibration. Fixed in e28dd927 with tests that drive the production serial code. Replayed light output is byte-identical before and after (28/28 cases). Device run blocked: FE bench not connected; Main RPL is rewired and owned by another lane."
---

# Modernes C++ lessons applied to the FE firmware

Single working record for this lane. Evidence lives in
`_scratch/modernes-cpp_20261110/` (ledger `LEDGER.md`) and
`_scratch/esp-emulator/mcpp-*`.

## Source identity

| Item | Value |
|---|---|
| Branch | `lane/k1-fe-release` |
| Baseline | `e2e83e53` (clean tree; another session committed it at 03:54) |
| Candidate | `e28dd927` (committed through `scripts/hooks/pre-commit`) |
| Product env | `k1_fe` (extends `k1_main_rpl_im69d`); emulator `k1_fe_emu` |
| Toolchain | pioarduino 54.03.20, arduino-esp32 3.2.0 / ESP-IDF 5.4.1, xtensa GCC 14.2.0, `-std=gnu++2b`, `-O3 -ffast-math -fno-finite-math-only` |

## Catalogue coverage

Source: https://www.modernescpp.com/index.php/table-of-content/ (fetched
2026-11-10). 20 topic families, 398 article links. Every family has a
disposition in `_scratch/modernes-cpp_20261110/catalogue/CATALOGUE.md`:
relevant to FE firmware 6, conditional 8, outside scope or historical 6.
About 70 articles fetched and about 20 read in depth (memory model, embedded
series, Core Guidelines concurrency/interfaces/arithmetic, constexpr,
std::array/span); the rest were screened by title only.

Source corrections carried forward and checked against primary references:

| Claim in the source | Result |
|---|---|
| Volatile article implies synchronisation / no caches | Confirmed wrong: volatile gives no ordering or atomicity (GCC Volatiles, CG CP.8). |
| Spinlock needs acq_rel beyond two threads | Disputed by the research agent ([intro.races] p6); not load-bearing here. |
| C++20 contracts | Historical: removed from C++20; GCC 14.2 rejects `pre(...)`. |
| `std::array::at` throws `range_error` | Wrong: `out_of_range`. |
| `constexpr` means ROM / compile-time | Wrong: it only permits constant evaluation (CG F.4); verified on GCC 14.2. |

## Retained lessons and K1 outcome

| Lesson (verified rule) | K1 question | Outcome |
|---|---|---|
| Validate before narrowing; float→int out of range is UB ([conv.fpint]); `constrain()` passes NaN | Do serial setters store NaN or garbage? | DEFECT, fixed (below). |
| Bounds as compile-time facts (CG P.5, `static_assert`) | Are size relationships asserted? | MISSING PROTECTION, fixed for notes[]/NUM_FREQS/NATIVE_RESOLUTION, K1_SP_BINS, novelty decimation. |
| `-ffast-math` implies `-ffinite-math-only` (GCC docs) | Do NaN guards survive the product flags? | ALREADY CORRECT (verified: `isnan` compiles to `un.s` in product order, to constant 0 if reversed). Guard added so a reorder fails the build. |
| Volatile is not synchronisation; release/acquire publishes ([intro.races]) | Is cross-core state published safely? | Audio frame, snapshot, director, edge mixer and PCM ring ALREADY COVERED (portMUX / acquire-release). Noise-calibration start was a real cross-core reset: DEFECT, fixed with `std::atomic<bool>`. |
| Fixed storage indexed only within its size (CG ES/Bounds) | Can a runtime value exceed boot-sized buffers? | `:led_count` DEFECT, fixed. |
| Lifetime / no use after free | Look-file LUT freed before unpublishing | DEFERRED (one frame of wrong colour, only when a look file is cleared). |

## Defects fixed in `e28dd927`

| Defect | Before (production code via golden serial oracle) | After |
|---|---|---|
| `:led_count=N` overran boot-sized LED buffers before reboot | `led_count=500` stored 500, saved, rebooted | Any value other than 160 rejected; 160 still saves and reboots |
| `:note_offset` above 16 read past `notes[]` every boot | `note_offset=24` saved 24; `abc` saved 0 + reboot | Clamped to `K1_NOTE_OFFSET_MAX` (16); non-numbers rejected; stale saved value clamped at boot |
| `parse_command` could leave strings unterminated | 40-byte line without `=` echoed stack bytes `\x10\xe4\xa4\x01\x01` | Terminator always kept |
| NaN / garbage reached `SQ15x16`, `uint32_t`, `int16_t` conversions or became 0 and was saved | `secondary_photons=nan`, `saturation=nan` stored NaN; `response_gain=nan` reached the core-0 sample path; `silence_dwell=-5` became 4294967291 ms | Rejected; valid numbers keep existing ranges and clamping |
| `start_noise_cal()` reset audio-owned state (incl. 64-bit sum) from the render core | Ran on core 1 inside `run_transition_fade` | Render core clears its own progress mask and raises an atomic request; `loop()` starts calibration before the next hop. Still only after the confirmed trigger. |

Records: `_scratch/modernes-cpp_20261110/oracle_probe_before.txt`,
`oracle_probe_ab.txt`, `golden_serial_diff3.txt`.

## Verification

| Check | Result |
|---|---|
| `tests/test_serial_input_validation.py` (production serial code through the oracle) | PASS, 42 tests |
| Pre-commit gate on `e28dd927` (full host suite + `k1_hardware`) | PASS: 2,070 passed, 2 skipped; `k1_hardware` SUCCESS |
| `pio run -e k1_fe` | PASS; 2 warnings, both pre-existing |
| Serial golden | 5 records changed, all intended (`led_count=300`, `led_count=0`, `note_offset=99`, `response_gain=abc`, `secondary_photons=abc`); regenerated with its manifest |
| FE emulator replay, candidate vs baseline (`mcpp-baseline2-…`, `mcpp-candidate1-fe`) | LED payloads byte-identical in 28/28 cases |
| FE emulator replay, clean `git archive` export of `e28dd927` (`_scratch/esp-emulator/mcpp-final-export-e28dd927/_out/fe-final`) | SOFTWARE COMPLETE: SW01–SW11 and SW13 PASS, SW12 not applicable, EX01/EX02 deferred (hardware/CI). Report inspected at desktop and phone width (`_scratch/modernes-cpp_20261110/report_desktop.png`, `report_phone.png`). |
| Independent review (separate agent) | CHANGES_REQUIRED → all Important findings fixed before commit; Minor items below |

The baseline replay was SOFTWARE INCOMPLETE before any change: `cfg-save`
expected the delayed save within 4.5 s, but `7a7507b2` (5 Nov) made it wait for
silence (5 s dwell). The case's quiet tail went from 600 to 1200 hops; it still
requires exactly one save.

## Not changed (with reasons)

- `:identify` and `:vp_out_test` drive the LEDs from core 0 without a proper
  render park; `:vp_out_test` is also a diagnostic in the product build. Gating
  it removes a command, which needs the Captain's call. DEFERRED.
- Mode hand-off store order, effects-queue edit race, waveform-history row tear,
  look-file free: one-frame effects at most. DEFERRED.
- Noise-cal progress display may show one or two stale mask frames between the
  render request and the audio core starting calibration. Fixing it adds render
  hooks that host harnesses compile. DEFERRED.
- `load_config` range sanitiser beyond NOTE_OFFSET. DEFERRED.
- Missing evidence: loopTask stack high-water on the FE line-in path;
  `lock_leds` timeout counter.

## Device status

BLOCKED. The FE bench (B489, env `k1_fe_bench_b489`) is not connected. Main RPL
(`B4:3A:45:A5:87:90`, `k1_fe`-allowed) is connected but was rewired today to LED
GPIO 2/3 + 5/6 on `wip/rpl-pins-20261110`, while this branch's FE image drives
GPIO 15–18, and it is in use by the k1-fe-show-m2 lane. An unregistered ESP
(`DC:54:75:EA:36:14`) was also connected and left alone.

## Changelog

| Date | Author | Change |
|---|---|---|
| 2026-11-10 | agent:claude-code (Opus 5.5) | Created: catalogue coverage, findings, fixes in e28dd927, verification. |
