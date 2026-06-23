---
abstract: "RESUMABLE HANDOVER for feat/gdft-true-center-ab. Implement a default-OFF exact-frequency Goertzel coefficient A/B. Device-confirmed (bench K1 B489A500/12201): rounded-k makes A4(440Hz)→bin26(B4 label), G#4(415.3)→bin24(A4 label) — product-visible. Edit ONLY the k/coeff block in precompute_goertzel_constants() behind K1_GDFT_TRUE_CENTER_V1. OFF must be byte-identical. ACCEPTANCE: with flag ON, 440Hz must move to bin24, 415.3→bin23. FAILURE RULE: if 440 does not reach bin24, STOP — do not tune. No Hann/ACF/VP/acoustic/above-Nyquist-policy in this branch. Start on a CLEAN session."
---

# Handover — `feat/gdft-true-center-ab` (exact-frequency Goertzel coefficient A/B)

## 0. STATUS (updated 2026-06-21, post-implementation) — HOST-GREEN, DEVICE A/B PENDING
The `precompute_goertzel_constants()` edit is **DONE and committed (host-green, unpushed)**:
- Flag is **`K1_GDFT_TRUE_CENTER_V1`** (default-OFF), in `config_types.h` next to `K1_SPECTRAL_WINDOW_V1`. The `SB_*` name in the original draft below was a naming-order slip — corrected to `K1_` per the standing order (occurrences updated).
- Gated ONLY the k/coeff block in `system.h`; the `#else` reproduces the legacy rounded-k lines verbatim.
- **Host verification PASSED:** `pytest tests/` → 574 passed (8 new `true_center` tests); OFF k1_hardware loadable image **byte-identical** to baseline (only `app_elf_sha256` + appended image-sha differ = build metadata); `k1_hardware` OFF, `k1_bench_reference_harness` OFF **and** ON all build SUCCESS.
- Host model `gdft_center_honesty_model.py` gained `mode="true_center"`; tests lock the host analog of the device acceptance (bin 24 centres exactly on 440 Hz when ON).
- Also committed a separate gate-fix: `k1_bench_reference_harness` was missing its in-body `non-shippable` label (red-on-arrival instrumentation-boundary test) — now labelled.

**THE ONE REMAINING STEP is the device A/B (§7).** The bench K1 (12201 / `B489A500`) was **not connected** this session. When connected: verify chip-ID, flash OFF (must reproduce 440→bin 26), flash ON, apply the acceptance gate + FAILURE RULE, restore shippable `k1_bench_reference`. The two new commits await Captain before push.

---

> **Original handover (implementation spec) follows — kept for the device-A/B operator and the rationale.**

## 1. State (verified, committed, pushed)
- **Branch:** `feat/gdft-true-center-ab` @ **`003fdd0`** (created off `feat/gdft-center-honesty`).
- **Stack (origin):** `feat/effect-registry-rewire` → `feat/ap-measurement-honesty` (`4bcd538`) → `feat/ap-bin-frequency-honesty` (`24f95a3`) → `feat/gdft-center-honesty` (`003fdd0`) → this branch. All pushed.
- **Device:** 12201 = USB serial `B4:3A:45:A5:89:B4` = chip **`B489A500`** = bench K1 (ports scramble — verify chip-ID every session). Currently restored to shippable `k1_bench_reference` (harness removed, verified).
- **Tooling committed in `003fdd0`:** `k1_bench_reference_harness` env (= `k1_bench_reference` GPIO + `-DENABLE_GDFT_HARNESS=1`), registered in `scripts/platformio/k1_upload_guard.py` bench target. Registry + measurement docs updated with device results.

## 2. Why this branch exists — device evidence (the gate that PASSED)
Synthetic GDFT harness on the bench (no mic) confirmed the rounded-`k` coefficient is **product-visible**:

| sent tone | wins bin | bin label |
|---|---|---|
| 415.3 Hz (G#4) | **bin 24** | 440.00 (A4) |
| 440.0 Hz (A4) | **bin 26** | 493.88 (B4) |
| 420.0 Hz | bin 24 | 440.00 (A4) |

`gdft_check.py` absolute-mapping FAILED on every tone (+60…+163 cents high). Root cause: `precompute_goertzel_constants()` rounds `k` before building the coefficient, so each bin resonates at `k·fs/block_size` (below its note label). Full analysis: `docs/measurements/gdft-bin-center-honesty.md`.

## 3. Objective
Add a **compile-time default-OFF** exact-frequency Goertzel coefficient. OFF = current behaviour byte-identical. ON = representable bins use the exact target frequency.

## 4. Hard constraints (do not violate)
- Flag default **OFF**. No Hann/window change. No ACF/confidence. No VP change. No acoustic/music test.
- **No above-Nyquist raw-bin policy change here** (that's a separate `feat/gdft-nyquist-safe-spectrum`).
- Preserve `block_size` logic, magnitude normalization, GDFT loop shape, safe-bin semantics.
- **FAILURE RULE:** if the ON path does not move 440 Hz to bin 24, **STOP. Do not tune constants. Do not change block_size.** Report that top-5/neighbour telemetry is now required.

## 5. Implementation (exact edit map)
**(a) Flag** — `SPECTRASYNQ_K1_FIRMWARE/system/config_types.h`, existing `#ifndef/#define` style:
```c
#ifndef K1_GDFT_TRUE_CENTER_V1
#define K1_GDFT_TRUE_CENTER_V1 0
#endif
```
**(b) Coefficient** — `SPECTRASYNQ_K1_FIRMWARE/system/system.h`, inside `precompute_goertzel_constants()`, the `k`/`w`/`coeff` block (currently ~line 286, after `block_size` cap + `inv_block_size_half`/`block_size_recip`). Gate ONLY this block:
```c
#if K1_GDFT_TRUE_CENTER_V1
    // True-centre: representable bins resonate at the EXACT note frequency.
    if (frequencies[i].target_freq <= CONFIG.SAMPLE_RATE * 0.5f) {
      float w = (2.0f * PI * frequencies[i].target_freq) / CONFIG.SAMPLE_RATE;
      frequencies[i].coeff_q14 = (1 << 14) * (2.0f * cos(w));
    } else {
      // Above Nyquist: keep rounded-k (NOT physically representable; out of scope here).
      float k = (int)(0.5 + ((frequencies[i].block_size * frequencies[i].target_freq) / CONFIG.SAMPLE_RATE));
      float w = (2.0 * PI * k) / frequencies[i].block_size;
      frequencies[i].coeff_q14 = (1 << 14) * (2.0 * cos(w));
    }
#else
    // ORIGINAL rounded-k — keep byte-identical to pre-branch.
    float k = (int)(0.5 + ((frequencies[i].block_size * frequencies[i].target_freq) / CONFIG.SAMPLE_RATE));
    float w = (2.0 * PI * k) / frequencies[i].block_size;
    float cosine = cos(w);
    float sine = sin(w);
    float coeff = 2.0 * cosine;
    frequencies[i].coeff_q14 = (1 << 14) * coeff;
#endif
```
> Confirm the exact original lines by reading the block first; reproduce them verbatim in the `#else`. `cosine`/`sine`/`coeff` locals may be used below — preserve whatever the original block declares. The generalized Goertzel (non-integer-k `w`) is correct: magnitude `q2²+q1²-coeff·q1·q2` stays valid.

**(c) Host model/tests** — `scripts/regression-harness/gdft_center_honesty_model.py` + `tests/test_gdft_center_honesty.py`: add a `true_center` mode where `effective_center == target` for `target ≤ Nyquist`; assert default-OFF reproduces the rounded-k model; assert no above-Nyquist true-centre claims.

**(d) Harness (optional, only if minimal)** — `SPECTRASYNQ_K1_FIRMWARE/diag/gdft_harness.h`: keep raw argmax; add `safe_argmax_bin`/`safe_argmax_bin_freq` (bins ≤ `sb_gdft_nyquist_safe_bin_hi`). Do NOT add top-5 telemetry yet.

## 6. Host verification (before device)
```bash
pytest tests/
pio run -e k1_bench_reference                                            # OFF, must build (byte-identical to baseline)
PLATFORMIO_BUILD_FLAGS="-DK1_GDFT_TRUE_CENTER_V1=0" pio run -e k1_bench_reference_harness
PLATFORMIO_BUILD_FLAGS="-DK1_GDFT_TRUE_CENTER_V1=1" pio run -e k1_bench_reference_harness
```

## 7. Device A/B (12201 = B489A500 — verify chip first; guard re-checks)
```bash
# guard preflight (no flash):
python3 scripts/platformio/k1_upload_guard.py --env k1_bench_reference_harness --upload-port /dev/tty.usbmodem12201   # must exit 0

# A: legacy (OFF) — must REPRODUCE 440 -> bin 26
PLATFORMIO_BUILD_FLAGS="-DK1_GDFT_TRUE_CENTER_V1=0" pio run -e k1_bench_reference_harness -t upload --upload-port /dev/cu.usbmodem12201
# B: true-centre (ON) — ACCEPTANCE: 440 -> bin 24, 415.3 -> bin 23
PLATFORMIO_BUILD_FLAGS="-DK1_GDFT_TRUE_CENTER_V1=1" pio run -e k1_bench_reference_harness -t upload --upload-port /dev/cu.usbmodem12201
```
Probe (the working serial pattern — 7 s boot settle after DTR-reset-on-open, then read loop):
```python
import serial,time
s=serial.Serial('/dev/cu.usbmodem12201',115200,timeout=0.3); time.sleep(7.0); s.reset_input_buffer()
def probe(f):
    s.write((':gdft_probe=%g\n'%f).encode()); s.flush(); buf=''; t=time.time()
    while time.time()-t<2.5:
        c=s.read(512)
        if c: buf+=c.decode('utf-8','replace')
    print(f, [l for l in buf.splitlines() if 'GDFTP,probe' in l])
for f in (415.3,440.0,420.0): probe(f)
# also sweep: python3 scripts/regression-harness/gdft_check.py /dev/cu.usbmodem12201 --reboot --read 20 --out _scratch/.../raw.log
```
GDFTP line format: `GDFTP,probe=<hz>,bin=<argmax>,bin_freq=<peak bin target>,chroma_bin=,mag=`.

## 8. After test
- **Restore** 12201 to shippable `k1_bench_reference`: `pio run -e k1_bench_reference -t upload --upload-port /dev/cu.usbmodem12201`; confirm harness gone (`:gdft_probe=440` returns nothing). Update the registry deployed-state row.
- Report exact GDFTP rows for A and B. If 440→bin24 (ON): A/B PASS → propose device VISUAL A/B next. If not: STOP per failure rule.

## 9. Load-bearing reminders
- Identity gate FIRST (chip-ID, not port name). The guard maps `k1_bench_reference_harness` → `B489A500` only.
- Use `/dev/cu.usbmodem*` for esptool (non-blocking); guard normalizes cu↔tty.
- `process_GDFT()` (GDFT.h) is byte-untouched by the harness; do not edit it.

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-06-21 | agent:claude-code | Created — resumable handover for the exact-frequency Goertzel coefficient A/B (post device-confirmed rounded-k gate). |
