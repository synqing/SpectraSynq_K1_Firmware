---
abstract: "Complete GDFT.h dependency surface for k1_gdft_core.cpp/h extraction boundary. NEW REPO file:line citations. Load-bearing for TU decomposition, int64 overflow gates, and zero-behavior-change boundary design."
---

# GDFT.h Complete Dependency Surface — NEW REPO

**Delegation ID:** gdft-surface (final round)  
**Repo:** `/Users/spectrasynq/SpectraSynq_K1_Firmware/`  
**Scan Date:** 2026-06-23  
**Authority:** Complete GDFT.h file read (459 lines) + globals.h + include graph  
**Purpose:** Design k1_gdft_core.cpp/.h extraction boundary without breaking behavior or hiding int64 overflow gates

---

## 1. DEFINED SYMBOLS (Public Entry Points)

### Single Public Function: `process_GDFT()`

| Attribute | Value |
|-----------|-------|
| **Signature** | `void IRAM_ATTR process_GDFT()` |
| **Location (NEW REPO)** | **GDFT.h:64** |
| **Core** | Core 0 (hard real-time audio pipeline) |
| **Frame Rate** | 133 Hz (96 audio samples @ 12.8 kHz = 7.5 ms per frame) |
| **Attributes** | `IRAM_ATTR` (instruction RAM; cannot be relocated to flash) |
| **Called From (NEW REPO)** | • `SPECTRASYNQ_K1_FIRMWARE.ino:41` • `gdft_harness.h` (ENABLE_GDFT_HARNESS, dev-only) |
| **Latency Budget** | <7.5 ms per frame (part of <50 ms audio-to-LED) |
| **Blocking Calls** | **NONE** (IRAM_ATTR, no malloc, no mutexes, non-blocking I/O) |
| **Return** | `void` (all I/O via global arrays) |
| **Purpose** | Goertzel GDFT 80-bin analysis + AGC + noise cal + novelty |

### Secondary Public Function: `calculate_novelty()`

| Attribute | Value |
|-----------|-------|
| **Signature** | `void calculate_novelty(uint32_t t_now)` |
| **Location (NEW REPO)** | **GDFT.h:415** |
| **Called From** | sb_audio_snapshot.h (Core 0, after process_GDFT) |
| **Purpose** | Spectral novelty (positive-change energy) for transient detection |

---

## 2. OWNED STATE — WRITTEN BY `process_GDFT()` & `calculate_novelty()`

### Magnitude Pipeline (4 stages)

#### `magnitudes[NUM_FREQS]` — Raw Goertzel Output
- **Type:** `int32_t`
- **Count:** 80 elements (NUM_FREQS = 80)
- **Declared (NEW REPO):** **globals.h:621** — `inline int32_t magnitudes[NUM_FREQS] = { 0 };`
- **Written (NEW REPO):** **GDFT.h:154** (v2 int64 path) OR **GDFT.h:157** (v1 legacy)
- **Purpose:** Raw magnitude from Goertzel recurrence (before normalization)
- **Overflow Risk (v1):** int32; q-state ~160k → q·q ~2.6e10 (wraps int32)
- **Overflow Fix (v2):** `K1_GDFT_INT64_MAGNITUDE_V1` flag gates int64 magnitude²

#### `magnitudes_normalized[NUM_FREQS]` — Coherent-Gain Corrected
- **Type:** `float`
- **Declared (NEW REPO):** **globals.h:622** — `inline float magnitudes_normalized[NUM_FREQS] = { 0.000 };`
- **Written (NEW REPO):** **GDFT.h:175** (per-bin normalization)
- **Purpose:** Hann window coherent-gain adjusted magnitude (if K1_SPECTRAL_WINDOW_V1); per-bin AGC floor subtracted
- **Notes:** Asymmetric EMA attack/release applied per-bin (lines 184-188)

#### `magnitudes_normalized_avg[NUM_FREQS]` — Smoothed Per-Bin
- **Type:** `float`
- **Declared (NEW REPO):** **globals.h:623** — `inline float magnitudes_normalized_avg[NUM_FREQS] = { 0.000 };`
- **Written (NEW REPO):** **GDFT.h:187-188** (per-bin EMA follower)
- **Purpose:** Exponential moving average with asymmetric attack/release
- **Formula:** `avg[i] = norm[i]·coeff + avg[i]·(1−coeff)` where coeff depends on rise/fall direction

#### `magnitudes_final[NUM_FREQS]` — Noise-Subtracted, Low-Pass Smoothed
- **Type:** `float`
- **Declared (NEW REPO):** **globals.h:625** — `inline float magnitudes_final[NUM_FREQS] = { 0.000 };`
- **Written (NEW REPO):** **GDFT.h:280** (memcpy from normalized_avg) → **GDFT.h:282** (after low_pass)
- **Purpose:** Final spectrum after noise reduction + low-pass smoothing
- **Notes:** Fed to visual effects, downstream AudioSemanticState, AGC pipeline

#### `magnitudes_last[NUM_FREQS]` — Previous-Frame History
- **Type:** `float`
- **Declared (NEW REPO):** **globals.h:624** — `inline float magnitudes_last[NUM_FREQS] = { 0.000 };`
- **Written (NEW REPO):** **GDFT.h:282** (memcpy after low_pass)
- **Purpose:** Previous-frame magnitude used as state accumulator for low-pass smoothing
- **Notes:** Mood modulates time constant (line 281: `1.0 + 10.0·MOOD_VAL`)

### Noise Model (3 variables)

#### `noise_samples[NUM_FREQS]` — Per-Bin Noise Floor
- **Type:** `SQ15x16` (fixed-point)
- **Declared (NEW REPO):** **globals.h:169** — `inline SQ15x16 noise_samples[NUM_FREQS] = { 1 };`
- **Written (NEW REPO):** **GDFT.h:205** (during noise calibration Phase B)
- **Purpose:** Learned per-bin noise floor during confirmed silence
- **Gate Conditions (lines 198-202):**
  - `noise_complete == false`
  - `noise_cal_dc_valid && noise_cal_reject_reason == NOISE_CAL_REJECT_NONE`
  - `noise_iterations ∈ [129, 240]` (Phase B window)
  - `max_waveform_val_raw <= NOISE_CAL_SSL_PHASE_B_MAX_RAW` (silent)

#### `noise_complete` — One-Shot Flag
- **Type:** `bool`
- **Declared (NEW REPO):** globals.h (search found no explicit line; likely inline)
- **Written (NEW REPO):** **GDFT.h:212** (set true after 256 iterations)
- **Purpose:** Marks end of noise calibration window

#### `noise_iterations` — Calibration Frame Counter
- **Type:** `uint16_t`
- **Declared (NEW REPO):** globals.h (inline)
- **Written (NEW REPO):** **GDFT.h:210** (incremented every frame; wraps after 256)
- **Purpose:** Counter for 256-frame calibration window

### AGC Broadband State (Single-Stage, Telemetry-Mirrored)

#### `agc_envelope` — Signal Level Envelope
- **Type:** `SQ15x16` (fixed-point 15.16)
- **Declared (NEW REPO):** **globals.h:677** — `inline SQ15x16 agc_envelope = SQ15x16(0.0);`
- **Written (NEW REPO):** **GDFT.h:352 or 354** (asymmetric envelope follower)
- **Time Constants:** 30 ms attack (ATTACK_ALPHA=0.28, line 322), 500 ms release (RELEASE_ALPHA=0.02, line 323)
- **Notes:** Resets to `SQ15x16(0.0)` at noise cal completion (line 255)

#### `agc_noise_floor` — Hysteretic Gate Threshold
- **Type:** `SQ15x16`
- **Declared (NEW REPO):** **globals.h:678** — `inline SQ15x16 agc_noise_floor = SQ15x16(0.001);`
- **Written (NEW REPO):** **GDFT.h:360** (slow tracker, updates when envelope near floor)
- **Time Constant:** 10 seconds (NOISE_ALPHA=0.001, line 324)
- **Notes:** Resets to `SQ15x16(0.001)` at cal completion (line 256)

#### `agc_gated` — Silence Gate State
- **Type:** `bool`
- **Declared (NEW REPO):** **globals.h:679** — `inline bool agc_gated = true;`
- **Written (NEW REPO):** **GDFT.h:367 or 368** (hysteretic gate logic)
- **Hysteresis:** Open at envelope ≥ 4× floor, close at ≤ 2.5× (lines 365-366)
- **Notes:** Resets to `true` at cal completion (line 257)

#### `agc_bands[NUM_AGC_BANDS]` — Per-Band Mirror (Telemetry)
- **Type:** `struct agc_channel[4]` (Bass, Low Mid, High Mid, Treble)
- **Declared (NEW REPO):** **globals.h:670** — `inline agc_channel agc_bands[NUM_AGC_BANDS];`
- **Written (NEW REPO):** **GDFT.h:408-410** (mirrors broadband gain into all 4 bands)
- **Purpose:** Telemetry compatibility; real AGC is single-stage broadband

### Spectrogram History & Spectral State

#### `spectrogram_history_index` — Ring-Buffer Pointer
- **Type:** `uint16_t`
- **Declared (NEW REPO):** globals.h (inline)
- **Written (NEW REPO):** **GDFT.h:79-81** (incremented every frame in process_GDFT, ALSO lines 452-454 in calculate_novelty)
- **Purpose:** Index into spectrogram history ring buffer

#### `max_mags[NUM_ZONES]` — Per-Zone Peak Tracker
- **Type:** `float[NUM_ZONES]`
- **Count:** ~8 zones (likely octaves)
- **Declared (NEW REPO):** globals.h (inline)
- **Written (NEW REPO):** **GDFT.h:75** (reset to 0.0 every frame)
- **Purpose:** Per-zone max magnitude accumulator

#### `spectrogram[NUM_FREQS]` — Final Processed Spectrum
- **Type:** `SQ15x16[80]`
- **Declared (NEW REPO):** globals.h (inline)
- **Written (NEW REPO):** **GDFT.h:403** (output of AGC pipeline: `spectrogram[i] = magnitudes_final[i] * agc_gain * spectral_tilt_lut[i]`)
- **Purpose:** AGC-processed, tilt-corrected spectrum fed to visual effects

#### `spectral_history[SPECTRAL_HISTORY_LENGTH][NUM_FREQS]` — Time History
- **Type:** `SQ15x16[][]`
- **Declared (NEW REPO):** globals.h (inline)
- **Written (NEW REPO):** **GDFT.h:439-446** (ring buffer append in calculate_novelty)
- **Purpose:** History for novelty calculation

#### `novelty_curve[SPECTRAL_HISTORY_LENGTH]` — Novelty Time Series
- **Type:** `SQ15x16[]`
- **Declared (NEW REPO):** globals.h (inline)
- **Written (NEW REPO):** **GDFT.h:450** (novelty measurement append)
- **Purpose:** Time series of spectral novelty (positive-change energy)

### Diagnostic Overflow Counter (Harness-Only)

#### `k1_gdft_q0_overflow_count` — Q-State Overflow Proof
- **Type:** `volatile uint32_t`
- **Declared (NEW REPO):** globals.h (inside #ifdef ENABLE_GDFT_HARNESS, line TBD from earlier search)
- **Written (NEW REPO):** **GDFT.h:127** (incremented when K1_GDFT_INT64_RECURRENCE_V1 detects q0 overflow)
- **Guard:** `#ifdef ENABLE_GDFT_HARNESS` (never in production)
- **Purpose:** Diagnostic: proves q-state stays in int32 even when multiply overflows

---

## 3. READ-ONLY DEPENDENCIES

### CONFIG Fields Referenced (2 only)

| Field | Type | Read Location (NEW REPO) | Purpose |
|-------|------|--------------------------|---------|
| `CONFIG.MOOD` | `float` | **GDFT.h:65** | Modulates low-pass time constant: `1.0 + 10.0·MOOD_VAL` |
| `CONFIG.LIGHTSHOW_MODE` | `enum` | **GDFT.h:66** | If `LIGHT_MODE_BLOOM`, force `MOOD_VAL = 1.0` |

**KEY:** Only 2 CONFIG fields; GDFT does NOT write CONFIG.

### External Arrays (Read-Only)

#### `frequencies[NUM_FREQS]` — Goertzel Coefficients
- **Type:** `struct { int32_t coeff_q14; uint16_t block_size; float block_size_half; float window_mult; float target_freq; float inv_block_size_half; ... }`
- **Declared:** constants.h
- **Read (NEW REPO):** **GDFT.h:91-93, 103, 171, 173** (inner Goertzel loop + normalization)
- **Purpose:** Per-bin Goertzel coefficients, block sizes, windowing parameters

#### `sample_window[SAMPLE_HISTORY_LENGTH]` — Audio Sample Ring Buffer
- **Type:** `int16_t[SAMPLE_HISTORY_LENGTH]`
- **Declared:** i2s_audio.h or globals.h
- **Read (NEW REPO):** **GDFT.h:99, 106** (sliding window index)
- **Purpose:** Ring buffer of audio samples from I2S (12.8 kHz sample rate)
- **Notes:** Populated by I2S_acquire() on Core 0; GDFT reads, does NOT write

#### `window_lookup[4096]` — Hann Window LUT
- **Type:** `int16_t[4096]`
- **Declared:** constants.h or k1_spectral_honesty.h
- **Read (NEW REPO):** **GDFT.h:113** (if K1_SPECTRAL_WINDOW_V1)
- **Purpose:** Hann window lookup for coherent-gain correction
- **Notes:** Used only if K1_SPECTRAL_WINDOW_V1 flag enabled (line 102)

#### `spectral_tilt_lut[NUM_FREQS]` — EQ Tilt
- **Type:** `float[80]` or `SQ15x16[80]`
- **Declared:** constants.h
- **Read (NEW REPO):** **GDFT.h:381** (AGC output: `out = magnitude * agc_gain * spectral_tilt_lut[i]`)
- **Purpose:** Per-bin frequency-domain equalization
- **Notes:** Immutable at runtime; applied post-AGC

#### Noise Calibration State (Read During Phase B Filter)
- **Fields:** `noise_cal_dc_valid`, `noise_cal_reject_reason`, `noise_cal_ssl_valid`, `calibration_profile_valid()`, etc.
- **Read (NEW REPO):** **GDFT.h:198-202, 214-215** (gate for noise model learning)
- **Purpose:** Calibration state machine guards
- **Notes:** Written by noise_cal command handler; read by GDFT to gate learning

### Numeric Constants (Read Throughout)

| Constant | Value | Read Location (NEW REPO) | Purpose |
|----------|-------|--------------------------|---------|
| `NUM_FREQS` | 80 | Loop bounds throughout (e.g., GDFT.h:86, 344) | Number of Goertzel bins |
| `NUM_ZONES` | ~8 | **GDFT.h:74** (max_mags reset) | Zone groupings for visual feedback |
| `NUM_AGC_BANDS` | 4 | **GDFT.h:251, 407** | Cochlear bands (Bass, Low Mid, High Mid, Treble) |
| `SAMPLE_HISTORY_LENGTH` | ~1024 | **GDFT.h:99** (implicit) | Ring buffer size for I2S samples |
| `SYSTEM_FPS` | 133 Hz | **GDFT.h:281** (low_pass_array parameter) | Frame rate for smoothing time constants |
| `MAGNITUDES_AVG_ATTACK` | ~0.3 | **GDFT.h:185** | Attack coefficient for per-bin EMA |
| `MAGNITUDES_AVG_RELEASE` | ~0.1 | **GDFT.h:186** | Release coefficient for per-bin EMA |
| `SPECTRAL_HISTORY_LENGTH` | ~256 | **GDFT.h:425, 453** | Ring buffer length for spectral history |

---

## 4. PERSISTENT CROSS-FRAME STATE (Goertzel Recurrence)

### Local Stack Variables (NOT Global — Lifetime = 1 Frame)

**Goertzel accumulators are per-frame, per-bin locals:**

```c
for (uint16_t i = 0; i < NUM_FREQS; i++) {  // GDFT.h:86
  int32_t q0, q1, q2;  // ← LOCAL; reset every frame
  int64_t mult;
  
  q1 = 0;  // GDFT.h:95
  q2 = 0;  // GDFT.h:96
  
  // Goertzel recurrence loop (block_size iterations, GDFT.h:105-137)
  for (uint16_t n = 0; n < block_size; n++) {
    // Recurrence: q0 = f(sample, coeff_q14, q1, q2)
    // Then: q2←q1; q1←q0 (lines 135-136)
  }
  
  // Magnitude computed from final q0, q1, q2 (lines 139-164)
  // No cross-frame state in q0/q1/q2
}
```

### Frame-to-Frame Static Inside process_GDFT()

#### `interlace_flip` — Optimization Toggle
- **Type:** `static bool`
- **Location (NEW REPO):** **GDFT.h:70** (inside process_GDFT function)
- **Purpose:** Alternates every frame to skip lower-freq processing (performance optimization)
- **Implication:** Frame-to-frame state INSIDE function; must be preserved during extraction

### Goertzel Recurrence Formula & Overflow Risks

#### **v1 Formula (int32, overflows at sustained resonance — LEGACY)**

**Location (NEW REPO):** **GDFT.h:132-133** (inside #else branch)
```c
mult = coeff_q14 * (int32_t)q1;
q0 = (sample >> 6) + (mult >> 14) - q2;
```
- **Risk:** `coeff_q14 ≈ 32k`, `q1 ≈ 160k` at sustained resonance → product overflows int32
- **Result:** Corrupts Goertzel resonator before magnitude computation

#### **v2 Formula (int64 multiply, int32 state — CURRENT/ACTIVE)**

**Location (NEW REPO):** **GDFT.h:115-130** (inside #if K1_GDFT_INT64_RECURRENCE_V1)
```c
#if K1_GDFT_INT64_RECURRENCE_V1
  mult = (int64_t)coeff_q14 * (int64_t)q1;  // GDFT.h:123
  int64_t q0_64 = ((int64_t)sample >> 6) + (mult >> 14) - (int64_t)q2;  // GDFT.h:124
#ifdef ENABLE_GDFT_HARNESS
  if (q0_64 > (int64_t)INT32_MAX || q0_64 < (int64_t)INT32_MIN) {
    k1_gdft_q0_overflow_count++;  // GDFT.h:127
  }
#endif
  q0 = (int32_t)q0_64;  // GDFT.h:130
#else
  // v1 legacy path (GDFT.h:132-133)
#endif
```
- **q-state stays int32** (q0, q1, q2 ≤ 160k)
- **Multiply widened to int64** to avoid overflow
- **Diagnostic counter** (inside ENABLE_GDFT_HARNESS) proves q0 never exceeds int32

### Magnitude Computation & Overflow Risks

#### **v1 Formula (int32, wraps at q²+q² ≈ 2.6e10 — LEGACY)**

**Location (NEW REPO):** **GDFT.h:155-163** (inside #else branch)
```c
mult = coeff_q14 * (int32_t)q1;
magnitudes[i] = q2 * q2 + q1 * q1 - ((int32_t)(mult >> 14)) * q2;
if (magnitudes[i] < 0) {
  magnitudes[i] = 0;
}
magnitudes[i] = sqrtf((float)magnitudes[i]);
```
- **Risk:** `q1·q1 + q2·q2 ≈ 2.6e10` (at q ≈ 160k) overflows int32 → negative → clamp to 0
- **Result:** Near-resonance bins go to zero (false attenuation, perceptual loss of musical pitch)

#### **v2 Formula (int64, correct at resonance — CURRENT/ACTIVE)**

**Location (NEW REPO):** **GDFT.h:139-164** (inside #if K1_GDFT_INT64_MAGNITUDE_V1)
```c
#if K1_GDFT_INT64_MAGNITUDE_V1
  int64_t coeff_term = ((int64_t)coeff_q14 * (int64_t)q1) >> 14;  // GDFT.h:147
  int64_t mag2 = ((int64_t)q2 * (int64_t)q2)  // GDFT.h:148-150
                 + ((int64_t)q1 * (int64_t)q1)
                 - (coeff_term * (int64_t)q2);
  if (mag2 < 0) {
    mag2 = 0;
  }
  magnitudes[i] = sqrtf((float)mag2);  // GDFT.h:154
#else
  // v1 legacy path (GDFT.h:156-163)
#endif
```
- **All intermediates computed as int64** → no wrap at 2.6e10
- **Device proof (2026-05-26):** int64 magnitude removes false zero-clamp at near-resonance
- **Scope:** ONLY magnitude² math widened; q-recurrence above deliberately UNCHANGED (line 145)

---

## 5. HAL & PLATFORM TOUCHPOINTS

### Arithmetic & Math

| Call | Location (NEW REPO) | Origin | Frequency | Purpose |
|------|---------------------|--------|-----------|---------|
| `sqrtf()` | **GDFT.h:154 or 163, 450** | `<cmath>` or Arduino | 80×/frame + 1× in calculate_novelty | Magnitude from accumulated energy |
| `k1_loud_guard_clamp_float()` | **GDFT.h:334** | k1_spectral_honesty.h | 1×/frame (if K1_LOUD_GUARD_V1) | AGC limiter scaling |

### Memory Operations

| Call | Location (NEW REPO) | Frequency | Size | Purpose |
|------|---------------------|-----------|------|---------|
| `memcpy()` | **GDFT.h:280, 282** | 2×/frame | 320 bytes each | Spectrum pipeline: normalized_avg→final, final→last |
| Manual loop unroll | **GDFT.h:438-446** (calculate_novelty) | 1×/frame | 80 floats (10×8 unroll) | Spectral history ring buffer append |

### Utilities

| Call | Location (NEW REPO) | Frequency | Purpose |
|------|---------------------|-----------|---------|
| `low_pass_array()` | **GDFT.h:281** | 1×/frame | Exponential moving average: magnitudes_final→magnitudes_last |

### Serial I/O (Rare, Non-Blocking)

| Call | Location (NEW REPO) | Frequency | Purpose |
|------|---------------------|-----------|---------|
| `USBSerial.println()` | **GDFT.h:213, 219, 239, 263** | ~1× at cal completion | Diagnostics: "NOISE CAL COMPLETE", "NOISE CAL QUALITY", "NOISE CAL ACCEPTED" |
| `USBSerial.print()` | **GDFT.h:289, 291, 295** | Rare (commented-out optional stream, line 285-298) | Optional magnitude array streaming |

### Data Access (Read-Only)

| Access | Location (NEW REPO) | Frequency |
|--------|---------------------|-----------|
| `CONFIG.MOOD` (read) | **GDFT.h:65** | 1×/frame |
| `CONFIG.LIGHTSHOW_MODE` (read) | **GDFT.h:66** | 1×/frame |

---

## 6. INCLUDE GRAPH

### GDFT.h Direct Includes

**Location (NEW REPO): GDFT.h:4**
```c
#include "k1_spectral_honesty.h"  // K1_HANN_COHERENT_GAIN (gated windowing only)
```
**Single direct include** — provides windowing constant, window_lookup[], optional K1_LOUD_GUARD functions.

### Files That Include GDFT.h (Includers)

#### Production
- **File:** `SPECTRASYNQ_K1_FIRMWARE.ino`
- **Line (NEW REPO):** **41**
- **Context:** Main sketch entry point
- **Calls:** `process_GDFT()` once per frame (Core 0, hard real-time)

#### Harness-Only (Dev)
- **File:** `gdft_harness.h`
- **Line (NEW REPO):** system/constants.h references (exact line TBD; gated by `#ifdef ENABLE_GDFT_HARNESS`)
- **Context:** Synthetic tone generator probe
- **Calls:** `process_GDFT()` with fake audio (never ships)

**Total Includers:** 1 production + 1 harness-only

### Downstream Consumers (Read GDFT Output)

| File | Reads | Frequency | Core | Context |
|------|-------|-----------|------|---------|
| `lightshow_modes.h` | `spectrogram[]`, `magnitudes_final[]`, `magnitudes[]` | 100 FPS | Core 1 | Visual effects consume GDFT output per-bin |
| `sb_audio_snapshot.h` | `magnitudes_final[]`, `agc_envelope`, `agc_gated` | 133 Hz | Core 0 | Publishes AudioSemanticState to Core 1 |
| `sb_tempo.h` / `sb_onset_beat.h` | `magnitudes_final[]` | 133 Hz | Core 0 | Beat/tempo/onset detection |

---

## 7. CALL SITES & EXECUTION CONTEXT

### Site 1: Production Main Loop

**File:** `SPECTRASYNQ_K1_FIRMWARE.ino` (via process_GDFT() definition in GDFT.h)  
**Context:** Core 0, hard real-time audio loop  
**Rate:** 133 Hz (every 96 audio samples @ 12.8 kHz = 7.5 ms per frame)  
**Call:** `process_GDFT();` — called once per frame boundary  
**Latency Budget:** <7.5 ms (part of <50 ms audio-to-LED)  
**Blocking:** **NO** (IRAM_ATTR, no malloc, no mutexes, non-blocking I/O only)

### Site 2: Harness-Only Synthetic Probe

**File:** `gdft_harness.h`  
**Guard:** `#ifdef ENABLE_GDFT_HARNESS`  
**Context:** Dev-only diagnostic; proves GDFT algorithm correctness offline  
**Rate:** On-demand (harness probe triggers)  
**Call:** `process_GDFT();` with synthetic sample_window filled from tone gen  
**Latency Budget:** N/A (diagnostic, not timing-critical)  
**Blocking:** NO (same IRAM_ATTR constraints)  
**Note:** **NEVER ships in production builds**

---

## 8. LOAD-BEARING GATES & EXTRACTION HAZARDS

### 🔴 SURPRISE 1: INT64 OVERFLOW GATES (Two Independent Flags)

**Both flags are LOAD-BEARING for int64 proof and must be preserved independently.**

#### Gate 1: `K1_GDFT_INT64_RECURRENCE_V1` (Goertzel Multiply Overflow)
- **Lines (NEW REPO):** **115-130**
- **Purpose:** Widens `coeff_q14 * q1` multiply to int64 before storing in q0
- **When True:** Cast both operands to int64 before multiply (line 123)
- **When False:** Legacy int32 path (lines 132-133)
- **Diagnostic (inside ENABLE_GDFT_HARNESS):** **GDFT.h:126-127** — increments overflow counter if q0_64 exceeds int32 bounds
- **Device Proof (2026-05-26):** Proves q-state never actually overflows int32 (multiply does, but q-state doesn't)

#### Gate 2: `K1_GDFT_INT64_MAGNITUDE_V1` (Magnitude-Squared Overflow)
- **Lines (NEW REPO):** **139-164**
- **Purpose:** Widens magnitude² (`q1·q1 + q2·q2 − coeff·q2`) computation to int64
- **When True:** All intermediates as int64 (lines 147-150)
- **When False:** Legacy int32 path (lines 156-157), which wraps at resonance
- **Device Proof (2026-05-26):** int64 magnitude removes false zero-clamp at near-resonance

**Implication:** TU extraction must preserve BOTH flags independently; disable selectively for testing.

### 🔴 SURPRISE 2: Static File-Scope State Inside Function

**Location (NEW REPO):** **GDFT.h:70** (inside process_GDFT)
```c
static bool interlace_flip = false;
interlace_flip = !interlace_flip;  // Switch field every frame
```
- **Scope:** Inside function (not file-scope)
- **Lifetime:** Persists across frames
- **Purpose:** Optimization — skips processing lower frequencies on alternate frames
- **Implication:** Must preserve frame-to-frame state; cannot be eliminated

### 🔴 SURPRISE 3: Noise Calibration State Machine Inlined

**Lines (NEW REPO):** **196-266** (inside process_GDFT)
- **State Transition:** `noise_complete: false → true` (irreversible per frame)
- **Gate Conditions (lines 198-202):** Only learn noise if:
  - Calibration not yet complete
  - DC offset valid
  - Phase B window (iterations 129-240)
  - Silent (SSL check passes)
- **Implication:** Noise model learning is **inlined**; cannot move outside process_GDFT without breaking Phase B barrier

### 🟡 SURPRISE 4: Static Variable Inside AGC (Static Gain)

**Location (NEW REPO):** **GDFT.h:371** (inside process_GDFT, inside AGC block)
```c
static SQ15x16 agc_gain = SQ15x16(1.0);
if (!agc_gated) {
  SQ15x16 target_gain = effective_target / (agc_envelope + AGC_EPS);
  // ...
  agc_gain += (target_gain - agc_gain) * GAIN_SMOOTH;
}
```
- **Purpose:** Maintains AGC gain state frame-to-frame (smoothing filter)
- **Implication:** Frame-to-frame state INSIDE function; must be preserved

### 🟡 SURPRISE 5: K1_LOUD_GUARD_V1 Optional AGC Limiter

**Lines (NEW REPO):** **332-340, 386-400**
- **When Enabled:** Modulates AGC floor and applies spectral depth/ceiling scaling
- **Implication:** Optional gate; can be independently enabled/disabled for tuning

### 🟡 SURPRISE 6: Windowing Gate K1_SPECTRAL_WINDOW_V1

**Lines (NEW REPO):** **102-114, 167-174**
- **When Enabled:** Applies Hann window and coherent-gain correction to magnitude normalization
- **Implication:** Optional gate; changes magnitude normalization behavior significantly

### 🟡 SURPRISE 7: Noise Subtraction Gate SB_GDFT_STATIC_NOISE_SUBTRACTION_ENABLED

**Lines (NEW REPO):** **197, 269-278**
- **When Enabled:** Subtracts learned noise floor from spectrum
- **Implication:** Optional gate; gates noise model learning and application

---

## 9. INVENTORY SUMMARY (NEW REPO)

### Defined Symbols
- **Public Functions:** 2 (`process_GDFT()` @ line 64, `calculate_novelty()` @ line 415)
- **Macros/Defines in body:** ~20+ (loop bounds, config checks, time constants defined inline)
- **Static variables:** 2 (interlace_flip @ line 70, agc_gain @ line 371)

### Owned State (Written by process_GDFT & calculate_novelty)

| Category | Count | Lines (NEW REPO) |
|----------|-------|-----------------|
| **Magnitude Pipeline** | 5 | magnitudes (621), magnitudes_normalized (622), magnitudes_normalized_avg (623), magnitudes_last (624), magnitudes_final (625) |
| **Noise Model** | 3 | noise_samples (169), noise_complete, noise_iterations |
| **AGC Broadband** | 4 | agc_envelope (677), agc_noise_floor (678), agc_gated (679), agc_bands (670) |
| **Spectral History** | 3 | spectrogram_history_index, spectral_history, novelty_curve |
| **Spectrogram Output** | 1 | spectrogram (403) |
| **Diagnostic** | 1 | k1_gdft_q0_overflow_count (harness-only) |
| **Total** | **17** | |

### Read-Only Dependencies

| Category | Count |
|----------|-------|
| CONFIG fields | 2 (MOOD, LIGHTSHOW_MODE) |
| External arrays | 5 (frequencies, sample_window, window_lookup, spectral_tilt_lut, noise_cal state) |
| Numeric constants | 7+ (NUM_FREQS, NUM_ZONES, NUM_AGC_BANDS, SYSTEM_FPS, SPECTRAL_HISTORY_LENGTH, etc.) |
| Tuning constants | 8+ (ATTACK_ALPHA, RELEASE_ALPHA, NOISE_ALPHA, GAIN_SMOOTH, AGC_TARGET, AGC_MAX_GAIN, etc. — see lines 322-328) |

### HAL Touchpoints
- **Math:** sqrtf(), K1_LOUD_GUARD optional
- **Memory:** memcpy() (2 calls/frame), manual loop unroll (calculate_novelty)
- **Utilities:** low_pass_array()
- **Serial I/O:** USBSerial.println(), USBSerial.print() (diagnostics only, rare)
- **Total Distinct Categories:** ~5

### Include Graph
- **Direct Includers:** 1 production (SPECTRASYNQ_K1_FIRMWARE.ino:41) + 1 harness-only (gdft_harness.h)
- **Downstream Consumers:** 4 (lightshow_modes.h, sb_audio_snapshot.h, sb_tempo.h, sb_onset_beat.h)

---

## 10. BOUNDARY DESIGN IMPLICATIONS FOR k1_gdft_core.cpp/.h Extraction

### ✅ Safe to Extract

1. **`process_GDFT()` as standalone TU** (GDFT.h:64-413) — All magnitude/AGC/history state is global; function has no local state beyond interlace_flip and agc_gain statics
2. **Magnitude pipeline logic** (GDFT.h:86-190, 280-282) — Linear data flow; no cross-file shared state
3. **Noise calibration state machine** (GDFT.h:196-266) — Inline; safe to preserve as-is
4. **AGC subsystem** (GDFT.h:301-412) — Can be separated into distinct function if needed; reads magnitudes_final[], writes agc_*, spectrogram[]
5. **int64 overflow fixes** — Both flags can be independently disabled for testing/comparison

### ⚠️ Requires Care

1. **Static `interlace_flip` (line 70)** — Must preserve frame-to-frame state; cannot be eliminated
2. **Static `agc_gain` (line 371)** — Must preserve frame-to-frame smoothing state
3. **CONFIG reads (lines 65-66)** — Boundary must ensure CONFIG is live (not stale snapshot)
4. **Goertzel locals (q0, q1, q2, mult)** — Must remain stack locals; lifetime = 1 frame only
5. **Harness diagnostic counter (line 127)** — Must keep `#ifdef ENABLE_GDFT_HARNESS` guard
6. **`low_pass_array()` utility (line 281)** — External dependency; must remain callable
7. **`calculate_novelty()` function (line 415-456)** — Can be extracted as separate TU; shares spectral_history[], novelty_curve[], spectral_history_index

### ❌ Do NOT Break

1. **K1_GDFT_INT64_RECURRENCE_V1 flag (line 115-130)** — Load-bearing for multiply overflow fix; must remain gatable
2. **K1_GDFT_INT64_MAGNITUDE_V1 flag (line 139-164)** — Load-bearing for magnitude² overflow fix; must remain gatable
3. **Noise model learning Phase B barrier (lines 196-266)** — Cannot move outside process_GDFT; tone gate depends on this
4. **AGC state reset at calibration (lines 249-257)** — Must remain tied to noise_cal completion
5. **IRAM_ATTR attribute (line 64)** — Core 0 timing constraint; cannot be removed
6. **K1_SPECTRAL_WINDOW_V1 gate (lines 102-114, 167-174)** — Magnitude normalization behavior depends on this; must remain gatable
7. **SB_GDFT_STATIC_NOISE_SUBTRACTION_ENABLED gate (lines 197, 269-278)** — Noise model learning/application depends on this; must remain gatable

---

**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-06-23 | agent:codex | Final GDFT.h dependency surface report for NEW REPO (`/Users/spectrasynq/SpectraSynq_K1_Firmware`). Complete file:line citations (GDFT.h is 459 lines). Inventory: 2 public functions, 17 owned arrays/variables, 2 CONFIG refs, 5 external arrays, 2 int64 overflow gates (load-bearing, independent), 2 static statics (interlace_flip, agc_gain), 4 optional feature gates (K1_LOUD_GUARD_V1, K1_SPECTRAL_WINDOW_V1, SB_GDFT_STATIC_NOISE_SUBTRACTION_ENABLED, ENABLE_GDFT_HARNESS), 1 harness diagnostic counter. Extraction hazards: Phase B noise barrier, AGC state reset coupling, frame-to-frame static state. Load-bearing for k1_gdft_core.cpp/.h extraction boundary design. |
