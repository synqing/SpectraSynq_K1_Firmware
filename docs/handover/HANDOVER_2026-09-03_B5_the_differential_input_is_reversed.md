# HANDOVER B5 — the differential compares different signals; the magnitude semantics are already correct

**Project folder:** `/Users/spectrasynq/Workspace_Management/Software/SpectraSynq-K1-DualMCU-Firmware`
**Branch:** `lane/k1-dm-110-vectors-24k` (HEAD `ad8cfd6`).
**Agent:** Claude Code or Codex, one session.

---

The retirement was done cleanly and leaving the differential red rather than widening the tolerance was the right call. But the 53,558-count error is not a magnitude-semantics problem, and the proposed next step would spend a lane on a non-issue. Two corrections.

## 1. Do not "reconcile mag_i32 semantics" — they already agree

`oracle_gdft.py`'s own header says `mag_i32[i]` is "the pre-sqrt magnitude-squared". **Its emitting code says otherwise**: line ~262 prints `(int)magnitudes[i]`, and `k1_gdft_core.cpp:204` sets `magnitudes[i] = sqrtf((float)mag2)`. So `mag_i32` is the **post-sqrt** magnitude truncated to `int32_t`.

The port's `GdftBinResult` carries `magnitude_squared` *and* `magnitude`, and the differential compares `bins[bin].magnitude` — post-sqrt against post-sqrt. That is already the right pairing, and truncation-to-int is bounded by one count, which is exactly the tolerance chosen. The tolerance is well-founded; keep it.

The misleading legacy docstring is worth one line in the evidence doc as a legacy-repo documentation defect. Do not edit the legacy repo.

## 2. The real fault: the test's index→time mapping is inverted

`oracle_gdft.py` fills its window newest-sample-first:

```c
for (int s = SAMPLE_HISTORY_LENGTH - 1; s >= 0; s--) {
    double t = (double)(base + (SAMPLE_HISTORY_LENGTH - 1 - s));
    sample_window[s] = (short)(amp * sin(w440 * t));
}
```

Index 4095 (newest) carries phase `base`; index 0 carries `base + 4095`. Since the Goertzel reads `samples[LEN - 1 - age]`, age 0 → `base`, age 1 → `base + 1` — forward in time.

`test/test_audio_rate_configuration/test_main.cpp` fills it the other way:

```cpp
const double t = tone ? static_cast<double>(base + sample) : 0.0;
trace[sample] = tone ? static_cast<std::int16_t>(16000.0 * std::sin(omega * t)) : 0;
```

Index 0 carries `base`, index 4095 carries `base + 4095`. The resonator therefore walks the tone **backwards** with a 4095-sample phase offset. The two sides are analysing different signals, which is why the error exceeds the signal itself.

Fix:

```cpp
const double t = tone
    ? static_cast<double>(base + (kGdftSampleHistoryLength - 1U - sample))
    : 0.0;
```

Frames 0–3 are silence on both sides and already agree; the whole error lives in frames 4–15, consistent with this.

## 3. Stop reconstructing the trace — share it

Both sides now re-derive the same formula independently, which is exactly how an inverted loop survives review. Have the generator emit the driver's actual sample window (or the per-frame 180-sample hop) into a companion fixture with its own SHA-256, and have the test consume those bytes. Then a residual difference is arithmetic, not transcription.

## 4. Check the window multiplier before drawing conclusions

Legacy sets `frequencies[i].window_mult = k1_hann_window_mult(frequencies[i].block_size)`. The port's `GdftBinConfig` has `target_frequency_hz`, `coefficient_q14`, `block_size`, `inverse_block_size_half` — no equivalent field. Establish whether `window_mult` is a per-sample window or a scalar magnitude correction, and whether the port folds it into `inverse_block_size_half`. Do this **after** the fix in item 2, and report the residual error distribution rather than a single maximum: how many of the 1280 cells differ, which bins, and whether the error tracks `block_size` or the `kX2CrossoverBin = 40` divisor boundary. The shape of the error names the cause; one maximum does not.

## 5. The gate exits success while red

The differential prints `GDFT_24K180_DIFFERENTIAL=BLOCKED` and then `return 0`. `pio test` passes, `init.sh` is green, and no automated gate would ever catch a regression here. Honest in the log, invisible to the harness. Once item 2 lands, make the comparison return non-zero on failure — or, if K1-DM-110 must stay green-while-blocked, have the ledger carry an explicit assertion that a gate checks.

Also: `std::ifstream golden("test/fixtures/gdft_24k180.golden.jsonl")` is a relative path, so the test depends on the working directory. Anchor it.

## Constraints

No hardware. Production stays 12 800 Hz / 96. Do not change existing frozen goldens or contracts. Do not touch the legacy repo. British English. Stop report in the repo's format.
