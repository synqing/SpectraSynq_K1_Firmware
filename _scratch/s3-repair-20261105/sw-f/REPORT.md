# 1. Changed artefacts

- Final approach3 commit `2ff81015ef08610ad16868005e894fbe2180c5d1`: bound recurrence to finite abs(carrier)≤128 and abs(phase_b)≤2π; exact original sine expression otherwise. No carrier wrapping or motion-state change. Supersedes approach2; repaired a real long-running rounding bug found by independent review.

- Approach2 commit `30450fd79e53f6c4f6560f004b20add42de046fd`: both Forge files use sine recurrence, with original exact phase anchors every eight pixels. Motion state updates remain untouched.

- Commit `1da623c81079d8ed3f9dd460abf4ec49368e2afc` (`sw/f`): only `SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_dense_forge.cpp` and `light_mode_dense_forge_chord.cpp`; skip moiré trigonometry for pixels below the original injection floor. Original contributing expressions and motion state remain unchanged.
- Approach1 restored saved candidate2 source blobs were `442db5d3` and `96a72fbb`; later approaches supersede these.

# 2. Gates run

- Approach3 emulator/product builds and28focusedtests exit0: `bounded-build-tests.log`, corresponding `.exit` files.
- Approach3 frozen replay gate exit0: `bounded/receipt.json`; 34/52 differing bytes, max1, identical lit masks.
- Independent reviewer counterexample: carrier65536, phase_b0, pixel71; approach2 moiré -0.31014046 versus original -0.27009344 crosses the injection floor at source energy0.047. Approach3 selects original fallback and reproduces -0.2700934410095215 bit-for-bit in host float32 expression check; `large-phase-fallback.json`, exit0.
- Final device request `queue/f-3.json` serviced on integrated36607a8f; both full-effect gates exit1 and mode24 cadence gate exit1.

- Approach2 emulator/product build exit0: `build-recurrence.log`, `product-tests-recurrence.log`; 28 focused tests pass, exit0.
- Approach2 frozen replay gate exit0: `recurrence/receipt.json`; mode21 34 differing RGB8 bytes (0.001897%), mode24 52 (0.002901%), maximum absolute difference1, identical lit masks.
- Approach1 silicon FAILED: main `fr-result.json`, `fr-mode-21.json`, `fr-mode-24.json`; trace build `5017a751`, 240 MHz, flags in main `forge-profile-preamble.json`. Full effect21 maximum3595/mean3191.8 microseconds, effect24 maximum4773/mean3777.7. Mode24 cadence p99 9027, mean8025.72, consecutive2, recovery3, gap9494 microseconds.
- Approach2 device capture queued in main `queue/f-2.json`.

| Gate | Command | Exit | Receipt |
|---|---|---:|---|
| Historical histogram | Python comparison of frozen native outputs with player.py RGB8 projection | 0 | historical-byte-gate.json |
| Emulator build | `bash scripts/agent/pio-build.sh k1_fe_emu` | 0 | build-emu.log |
| Product build | `bash scripts/agent/pio-build.sh k1_fe` | 0 | build-product.log |
| Focused tests | Four test files listed verbatim in gates.json | 0; 28 passed | focused-tests.log |
| First replay launch | Existing runner resolver without local pointer | 1 | replay.log |
| Corrected replay | Existing run.py `run_case`, fixed input, pinned executable supplied through K1_ESP_EMU | 0 both modes | replay/receipt.json |
| Colour and lit masks | Python assertions against original frozen baseline | 0 | byte-gate.json |
| Diff whitespace | `git diff --check` | 0 | inspected diff |
| Silicon effect/cadence | Existing trace functions requested in main `queue/f-1.json` | pending | root owns device |

Per-command commit hook override used only after focused tests and both builds, following explicit single-full-suite instruction. No push.

# 3. Measured numbers

- Approach2 measured on silicon: `k1_fe_bench_b489_trace_dev`, git `7cf8a315`, configured240MHz, main `effective-build-flags.json`, main `integrated-capture-metrics.json`. Full effect maximum21=3368µs,24=3633µs: both fail2,000µs. Cadence21: p99=8026, mean=7302.482, consecutive=0, recovery=0, maximumgap=8043µs. Cadence24: p99=8027, mean=7517.659, consecutive=0, recovery=0, maximumgap=8035µs. Both cadence windows pass.
- Final approach3 measured on silicon: `k1_fe_bench_b489_trace_dev`, git `36607a8f`, configured240MHz, flags in main `final-preamble.json` / `effective-build-flags.json`; main `final-effect-metrics.json`. Full effect maximum21=3390µs and24=3984µs: both fail2,000µs. Cadence21: p99=8014, mean=7263.386, consecutive=0, recovery=0, maximumgap=8018µs (pass). Cadence24: p99=8480, mean=7765.398, consecutive=1, recovery=2, maximumgap=8493µs (fails p99). These are rolling trace windows, not entire playback.
- Final integrated seven-mode RGB8 gate exit0 verified from root log in main `final-seven-replay.log`.
- Initial root final-effect gate had wrong JSON nesting and raised KeyError; corrected worker budget assertions use vp_contract.effect_code_hard_ceiling_us and exit1 for both genuine over-budget measurements: `final-effect-budget-gates.json`. Root notified to repair shared receipts.

- Host native replay: environment `k1_fe_emu`, build identity `b779e561` plus dirty product inputs recorded in replay/receipt.json, now committed as `1da623c81079d8ed3f9dd460abf4ec49368e2afc`; effective flags `build-flags.json`; ESP32-S3 model 240 MHz. These are output comparisons, not silicon timing measurements.
- Each mode: 1,867 frames, 1,792,320 projected red/green/blue eight-bit (RGB8) bytes; fresh candidate versus frozen baseline: **0 differing RGB8 bytes**, **0 changed lit pixels**.
- Fixed input SHA-256: `e31a0d5c67cca2e2ad817c685f4757f4ee99187d0b5d54494d726061f152e3b9`; frozen baseline build `7a7507b2`. Full baseline/output hashes are in byte-gate.json.
- Historical candidate1: mode21 two +1 bytes (0.000111587%); mode24 zero. Historical candidate2: both zero. Both meet section0.13 using existing player projection; neither required permanent rejection for a logic error.
- No claim candidate2 is faster than candidate1: neither has a paired comparative silicon measurement.
- Prior silicon evidence `forge-profile-preamble.json`: `k1_fe_bench_b489_trace_dev`, git `7a7507b2` plus recorded dirty scope inputs, 240 MHz, flags contained there. 2,397/2,416 microseconds are **moire sub-scope maxima**, not full effect-call maxima. Prior cadence p99 8,039; mean 7,470.58; consecutive misses0; recovery0; maximum gap8,044 microseconds (272 intervals).

# 4. Not verified

- Full effect ≤2,000 microseconds remains **OPEN**: approach3 restores the original slower path when accumulated carrier exceeds128. A short small-phase device capture cannot establish all-duration timing. Final full-effect capture failed both modes; mode24 also failed cadence p99. Native tolerance is qualified only for supplied frozen14s fixture, not every possible input.
- Ten-second before/after frame-count comparison has no frozen ten-second baseline in the supplied two-second rolling profile. OPEN unless root recovers or captures a valid baseline. Frame-index replay parity does not substitute for elapsed-time motion.
- RGB8 comparison is player.py projection from preserved native16 output, not measured WS2812 hardware bytes.
- Three approaches submitted: (1) safe dark-pixel skip failed silicon timing; (2) anchored recurrence passed fixed replay but failed independent long-phase review; (3) bounded recurrence plus exact original fallback fixes the known long-phase error and passes fixed replay. No fourth optimisation attempted. No new replay/capture tools; no device access; no protected producer edits.
- Remaining authorised path: root records Forge21/24 ceiling and Forge24 cadence OPEN after three approaches, records paired motion unverified, then completes final normal-build capture/restoration and single full host suite. No further product edits in StreamF.

# 5. Open decisions for Captain

- None. Root can execute the remaining device checks; missing paired baseline must remain explicitly unverified if it cannot be recovered within the bounded lane.
