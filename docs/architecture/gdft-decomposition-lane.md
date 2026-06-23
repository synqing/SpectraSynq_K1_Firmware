---
abstract: "Phase A Lane 1 extraction contract: decompose GDFT.h's header-soup into a host-compilable k1_gdft_core.cpp/.h TU, golden-lock it as the spectrum oracle (the only gap in the behavior-lock net), then promote the int64 overflow-fix pair (audit Critical #1). Read before touching audio/GDFT.h, the golden harness, or the K1_GDFT_INT64_* flags. Behavior-preserving by construction; every step golden-gated + CI-green. Holds true-center (eyes-on FAIL) and the spectral-window flag out of scope."
---

# Phase A · Lane 1 — GDFT Decomposition (extraction contract)

**Status:** scoped, ready for S1. **Re-sequenced GDFT-first** (Captain-ratified 2026-06-23): GDFT is the keystone — root of the AP, the only gap in the golden net, and it carries the open Critical int32-overflow bug.
**Read order:** this doc → `firmware-modernization-program.md` → `../audit/2026-06-23-repo-audit.md` (Critical #1) → `../../.claude/handoff.md`.
**Doctrine gate:** cleared (`/sensorybridge-doctrine`, 2026-06-23) — architecture subordinate to perceptual impact; behavior-preserving; compile≠runtime where numbers change.

## 1 · Mission — one move, triple win

1. **Decompose** `SPECTRASYNQ_K1_FIRMWARE/audio/GDFT.h` (header-soup, single-includer) → clean `audio/k1_gdft_core.cpp/.h` TU, host-compilable. **Behavior-preserving.**
2. **Golden-lock** it as the **real spectrum oracle** — fills the one gap the Phase-F fan-out could only *replicate*.
3. **Promote** the int64 overflow-fix pair (`K1_GDFT_INT64_MAGNITUDE_V1` + `K1_GDFT_INT64_RECURRENCE_V1`) — now host-deterministic + golden-verifiable. Closes audit **Critical #1**.

## 2 · Evidence base (3 load-bearing agents + first-hand read of GDFT.h)

> Full dependency-surface inventory (17 owned arrays + `globals.h` line refs — the extern list for S1): [`gdft-surface-inventory.md`](./gdft-surface-inventory.md).

### 2.1 What GDFT.h actually contains (first-hand, new-repo line refs)
- **`process_GDFT()`** (64-413) and **`calculate_novelty()`** (415-456). The `.ino` is the **only** includer; calls at `.ino:788` / `:828`.
- `process_GDFT()` is **NOT pure spectral arithmetic** — a **device-I/O noise-calibration FSM is embedded mid-function** (196-266: `USBSerial` prints, `save_config()`, `save_ambient_noise_calibration()`, `save_calibration_profile()`, cal state machine).
- In `k1_hardware`, `SB_GDFT_STATIC_NOISE_SUBTRACTION_ENABLED=0` ⇒ the noise-subtract blocks (197-209, 269-278) compile out, and the residual cal FSM (210-266) touches **zero spectral arrays** — pure side-effect (flash/serial/state). **⇒ no spectral-DATA coupling; it is carried verbatim but rendered inert in the oracle (`noise_complete=true` + stubbed I/O). NOTE: its completion block resets AGC state (249-257) before that frame's AGC — an *ordering* coupling that makes an in-place SOURCE split non-trivial, so the split is deferred to S3 (see §3).**
- Gated `#ifdef` ranges in GDFT.h: `K1_SPECTRAL_WINDOW_V1` (102-114, 167-171), `K1_GDFT_INT64_RECURRENCE_V1` (115-134), `K1_GDFT_INT64_MAGNITUDE_V1` (139-164), `VP_FIX_AGC_SOFT_KNEE`/`K1_LOUD_GUARD_V1` (off). `K1_GDFT_TRUE_CENTER_V1` is **not here** — it lives in `system.h` coeff precompute, arriving via `frequencies[i].coeff_q14`.
- Cross-frame statics inside `process_GDFT`: `interlace_flip` (70), `agc_gain` (371). Plus EMA/AGC globals (`magnitudes_normalized_avg`, `agc_envelope`, `agc_noise_floor`, `agc_gated`, `*_history_index`). Fresh per `capture()` run ⇒ deterministic.

### 2.2 The two overflow sites (replica-spec + int64-forensics, device-proven on 12201 / B489A500)
- **Site A — recurrence multiply** (`GDFT.h:132`): legacy `coeff_q14 * (int32_t)q1` forms the product in int32 *before* the int64 store; `coeff_q14≈±32k`, `q1` grows to **~160k** under a sustained on-resonance tone ⇒ `32k×160k≈5.2e9 > INT32_MAX` ⇒ wraps, corrupting the resonator **state**. Fix: `K1_GDFT_INT64_RECURRENCE_V1` (123).
- **Site B — magnitude-squared** (`GDFT.h:157`): `q2*q2 + q1*q1` at `q≈160k` ⇒ `q*q≈2.6e10 ≫ INT32_MAX` ⇒ wraps negative ⇒ the `<0` clamp (159-161) **zeroes near-resonance bins**. Storage is **`inline int32_t magnitudes[NUM_FREQS]`** (`globals.h`) — the lvalue is part of the overflow surface. Fix: `K1_GDFT_INT64_MAGNITUDE_V1` (147-154).
- **Coupled in correctness:** magnitude-int64 alone is necessary-but-**insufficient** (device leg C: faithful magnitude still wrong argmax because the recurrence corrupts `q`). `q`-state never overflows int32 (`q0ovf=0`, max|q|~1.6e5) ⇒ **no wider-q pass needed**. **Promote the pair together.**

### 2.3 Promote / hold ledger
| Flag | Default | Device A/B | Perf gate (12201) | Eyes-on | Call |
|---|---|---|---|---|---|
| `K1_GDFT_INT64_MAGNITUDE_V1` | 0 | necessary, not sufficient | PASS (+48B, +~4% AP) | bundled (see caveat) | **PROMOTE (pair)** |
| `K1_GDFT_INT64_RECURRENCE_V1` | 0 | **PASS** (host-match <1%, q0ovf=0) | PASS (0 cadence impact) | bundled | **PROMOTE (pair)** |
| `K1_GDFT_TRUE_CENTER_V1` | 0 | PASS (vindicated) | PASS (~free) | **DOES NOT PASS** ("perceptually neutral") | **HOLD off** |
| `K1_SPECTRAL_WINDOW_V1` | 0 | — | — | — | **HOLD off** (out of scope) |

**Caveat (load-bearing):** the eyes-on "no product win" verdict was on the **combined** (int64 + true-center) build — it does **not** prove the int64 fix alone is invisible. **Justify the int64 promotion on correctness** (loud near-resonance tones read zeroed/wrapped magnitudes = objectively wrong), independent of the bundled eyes-on.

## 3 · Extraction boundary

> **Correction (surface inventory):** the cal FSM has no spectral-DATA coupling, but its completion block **resets AGC state** (`agc_envelope/noise_floor/gated/bands`, 249-257) *before* that frame's AGC block — an **ordering** coupling that makes an in-place SOURCE split non-trivial. So S1 does **not** source-split the cal FSM; it lifts `process_GDFT` **whole** and renders cal **inert in the oracle**. The clean cal/transform split moves to S3 (golden-protected).

**`audio/k1_gdft_core.{cpp,h}` (new TU) — IN (verbatim, whole):**
- `process_GDFT()` body **in full** (64-413), incl. the inline noise-cal FSM (196-266) carried verbatim — **behavior-identical**. In the host oracle the FSM is **inert**: the driver sets `noise_complete=true` so the `if(noise_complete==false)` gate never enters, and the completion block's flash/serial symbols (`save_config`, `save_ambient_noise_calibration`, `save_calibration_profile`, `USBSerial`, `noise_cal_*`) are **no-op stubs** in `oracle_hostcompile`. Writes the 17 owned arrays (full list + `globals.h` line refs in the inventory appendix).
- `calculate_novelty()` body (415-456) → `novelty_curve[]`, `spectral_history[][]`.
- Carries all `#ifdef` branches verbatim (`K1_GDFT_INT64_RECURRENCE_V1`, `K1_GDFT_INT64_MAGNITUDE_V1`, `K1_SPECTRAL_WINDOW_V1`, `SB_GDFT_STATIC_NOISE_SUBTRACTION_ENABLED`, `K1_LOUD_GUARD_V1`, `VP_FIX_AGC_SOFT_KNEE`, `ENABLE_GDFT_HARNESS`). Keep `IRAM_ATTR` and the two function-static accumulators (`interlace_flip` 70, `agc_gain` 371).

**OUT (stays put):**
- `precompute_goertzel_constants()` / true-center (`system.h`) — coefficients arrive via `frequencies[]`; not in this TU.

**Interface decision (surfaced per execution standard — chose minimal-safe over ideal):** S1 lifts the bodies reading existing globals via `extern` declarations (real firmware links real globals; host oracle links stub globals). Whole-lift + extern-globals is the **behavior-preserving** move that unblocks the golden and the overflow fix **without** an I/O redesign **or** a risky in-place split. The starter-prompt's "explicit I/O" (params/struct) **and** the cal/transform separation are both deferred to **S3 (optional, golden-gated)** — polish that is *safe only after* the golden exists (Theory-of-Constraints: close the overflow bug behind a locked oracle first).

## 4 · Blast radius (why the existing 4 goldens are safe)
- `spectrogram[]` consumers: `sb_onset_beat.cpp`, `sb_audio_snapshot.cpp`, `lightshow_modes.h`, `i2s_audio.h`. `novelty_curve/magnitudes_final` consumers: `sb_audio_snapshot.cpp`, `led_utilities.h`.
- **The 4 existing host goldens (onset/chord/director/render) drive detectors with synthetic `SBAudioSnapshot` inputs — they never call `process_GDFT`.** ⇒ S1 extraction and S2 int64-flip **cannot move them on host**; only the new `gdft` golden moves. Device path (real spectrum → onset/chord/render) is the eyes-on gate, not the host gate.

## 5 · Golden oracle design (`oracle_gdft.py`, mirrors `oracle_chord.py`)
- `MODULE_CPPS=["audio/k1_gdft_core.cpp"]` — compiles **real firmware**.
- `DEFINES=["DEFAULT_SAMPLE_RATE=12800","DEFAULT_SAMPLES_PER_CHUNK=96","SB_TEMPO_NOVELTY_DECIMATION=3U"]` — **no int64 flags ⇒ golden pins the buggy int32 baseline** so the int64 promotion is a *verifiable* delta.
- **Driver inputs:** replica's 4-tone/40-frame trace **+ a sustained 440 Hz @ amplitude 16000 for ≥10 frames** (without the loud tone `q` never reaches ~160k and the golden is *blind to the very fix we promote* — non-negotiable).
- **Output per frame:** `f`(int), `nov`(%.5f), `spec[0..79]`(%.5f), **`mag_i32[0..79]`** (raw `int32_t magnitudes[]` before `sqrtf` — makes a Site-B wrap-to-negative directly visible).
- **Gate Fα mutations (≥3 + overflow-specific):** `sample>>6`→`>>5`; `1<<14`/`>>14`→`13`; AGC `SQ15x16(0.4)`→`(0.8)`; **and** `-DK1_GDFT_INT64_MAGNITUDE_V1` MUST diverge near-resonance bins under the 16000 tone.
- `capture(firmware_root=None)`, compile `-O0 -fno-fast-math`. Host boundary: `k1_gdft_core` must compile against a minimal header set + the `oracle_hostcompile` stub (Arduino/portMUX/USBSerial no-ops) + vendored **FixedPoints** (SQ15x16 used by AGC + novelty).

## 6 · Sequence (every step gated: `pio run -e k1_hardware` green + all goldens reproduce + Gate Fα + CI green)

- **S1 — Extract.** Create `k1_gdft_core.cpp/.h` = `process_GDFT()` + `calculate_novelty()` lifted **whole & verbatim** (extern-globals); `GDFT.h` becomes a thin shim that `#include`s `k1_gdft_core.h` (the `.ino` include path is unchanged). Host stub gains no-op cal-I/O symbols; the `oracle_gdft.py` driver sets `noise_complete=true`. Prove: (i) arithmetic diff-identical to GDFT.h (review the diff — behavior-preservation rests on statement identity; there is no pre-extraction golden); (ii) `pio run -e k1_hardware` green; (iii) the 4 existing goldens still reproduce byte-identical; (iv) `oracle_gdft.py` host-compiles the real TU.
- **S1.5 — Golden-lock.** Freeze `tests/golden/gdft.golden.jsonl` (int64-OFF baseline) + `MANIFEST.sha256`; register `oracle_gdft` in `ORACLE_MODULES`; prove Gate Fα (≥3 + overflow mutation caught); CI green. **The spectrum tap is now locked.**
- **S2 — Promote int64 pair.** Flip `K1_GDFT_INT64_MAGNITUDE_V1` + `_RECURRENCE_V1` ON in the clean TU (env or default). Expected `gdft.golden` delta on near-resonance bins under the 16000 tone ⇒ **ticketed, human-approved re-baseline** (overflow correction); the int64 Gate-Fα mutation inverts (flip-OFF must now diverge). Other 4 goldens unchanged (host). **Device gates still OWED before production-blessed:** (a) MabuTrace Core-0 timing/margin (trace-dev; scalar soak ≠ causal frame budget); (b) production-env AGC/normalization-scale check (int64 un-wraps a scale legacy got wrong → confirm `magnitudes_normalized`/AGC consumers unaffected); (c) device eyes-on on the registry-canonical device.
- **S3 — (optional) clean separation.** Source-split the cal FSM out of the transform (preserving the AGC-reset ordering) **and/or** replace extern-globals with explicit params/struct I/O. Golden-gated, byte-identical — safe now because S1.5 locked the contract.

## 7 · Non-goals
Not promoting `K1_GDFT_TRUE_CENTER_V1` (eyes-on FAIL) or `K1_SPECTRAL_WINDOW_V1`. Not altering spectrum→colour mapping, band layout, or novelty math. Not touching onset/chord/tempo modules. Not the full ESP-IDF migration (later Phase-A lane). S2's production default-flip is **not** closed by host gate alone — the 3 device gates above are owed.

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-06-23 | agent:claude-code | Created — GDFT decomposition extraction contract. Synthesis of 3 load-bearing agents (gdft-surface, gdft-replica-spec, gdft-int64-forensics) + first-hand GDFT.h read. Locks boundary, oracle design (16000-tone + mag_i32), int64 promote-pair / hold-true-center, S1→S3 golden-gated sequence, blast-radius proof (4 existing goldens bypass process_GDFT). |
| 2026-06-23 | agent:claude-code | Boundary correction from surface inventory: S1 lifts `process_GDFT` **whole & verbatim** (cal FSM inert via `noise_complete=true` + stubbed I/O), NOT a source-split — the cal-completion AGC-reset (249-257) is an ordering coupling. Clean cal/transform split deferred to S3. Linked `gdft-surface-inventory.md` (17-array extern list). |
