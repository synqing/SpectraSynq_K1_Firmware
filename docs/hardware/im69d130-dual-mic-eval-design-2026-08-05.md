# IM69D130 Dual-Mic Evaluation — Design (B + C)

**Date:** 2026-08-05
**Status:** DESIGN + Stage-1 env **IMPLEMENTED** (2026-08-05) — see
[`im69d130-env-implement-receipt-2026-08-05.md`](./im69d130-env-implement-receipt-2026-08-05.md).
Host build + static locks + guarded bench flash + `:build`/`raw_i16_*` smoke VERIFIED.
Noise cal / stereo Stage 2 still open.
**Lane:** NEW candidate lane. The ACTIVE lane is `lane/dual-sync-phase0` (dual-sync recovery).
This design must not be merged into, or committed alongside, dual-sync work.
**Target device:** bench K1, chip `B489A500`, USB serial `B4:3A:45:A5:89:B4` (port name drifts — identity is the chip ID).
**Production mic decision:** UNCHANGED. IM73D122 remains the production mic (`k1_prod_im73d`). Nothing here reopens that.

---

## 1. Goal statement (B + C)

Captain scoped two distinct questions that share one piece of hardware:

**(B) Candidate A/B — IM69D130 vs IM73D122.**
Measure, on the same bench K1 in the same room with the same programme material, whether the
IM69D130 is a better microphone *for this product* than the already-productionised IM73D122.
The part numbers encode the trade the A/B exists to resolve:

| Part | SNR (encoded) | AOP (encoded) | Implied strength |
|---|---|---|---|
| IM73D122 | 73 dB | 122 dB SPL | Quiet rooms, low noise floor |
| IM69D130 | 69 dB | 130 dB SPL | Loud venues, ~8 dB more headroom before overload |

> **Verify before bring-up:** these figures are read off Infineon's part-number convention, not
> from a datasheet in this repo. Confirm against the actual IM69D130 datasheet and the physical
> part markings. If they hold, **B is not a "which mic is better" question — it is a "which
> failure do we care about" question**: IM73D loses to noise in quiet rooms, IM69D loses to
> clipping in loud ones. A light show that must work at a party is plausibly AOP-limited, not
> SNR-limited. That framing determines the entire evidence plan in §6.

**(C) Dual-mic / stereo experiment.**
Two IM69D130 on one PDM data line (one LEFT, one RIGHT) give the firmware two independent audio
channels for the first time. K1 already has a **dual-channel** visual architecture (primary +
secondary edge, `sb_edgemixer_lite`). C asks whether two real microphones can drive those two
edges *differently in a way a human can see*, and whether inter-channel information buys
robustness (coherence-based rejection of handling/near-field noise).

**C is a falsifiable experiment, not a feature request.** See §5 for the hypothesis and its
kill criterion. The honest default answer is "no": two mics a few centimetres apart in a
diffuse room field produce nearly identical signals below ~1 kHz, and "stereo visuals" derived
from them would be theatre. C exists to measure whether that is true here.

---

## 2. Map vs territory — pin contract

This is the load-bearing section. The Captain's wiring and the firmware's current PDM map
**do not agree, and the disagreement is electrically hazardous, not merely non-functional.**

### 2.1 What exists today

| Signal | Captain IM69D130 wiring (claimed) | Firmware `K1_MIC_IM73D_PDM_V1` (bench-ref) | Firmware SPH0645 `i2s_std` (bench-ref) |
|---|---|---|---|
| PDM CLK (MCU → mic) | **GPIO14** | GPIO13 — `K1_PDM_CLK_PIN` | — (BCLK = 14) |
| PDM DATA (mic → MCU) | **GPIO13** | GPIO12 — `K1_PDM_DIN_PIN` | — (DIN = 13) |
| SELECT / LR | **not stated** | GPIO14 — `K1_PDM_LR_PIN`, driven LOW as an output | — (LRCLK = 12) |

Sources: `SPECTRASYNQ_K1_FIRMWARE/system/constants.h:302-321` (bench-reference map),
`constants.h:332-342` (production map — identical PDM pins),
`SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:223-245` (PDM init).

### 2.2 The hazard — why `k1_bench_im73d` must not be flashed against this wiring

Under `K1_MIC_IM73D_PDM_V1` the firmware does two things at init:

1. Configures **GPIO13 as the PDM clock output** (`i2s_audio.h:235`) — a push-pull driven pin.
2. Configures **GPIO14 as a GPIO output and drives it LOW** (`i2s_audio.h:228-230`).

Against the Captain's wiring that means:

- **GPIO13: output-vs-output contention.** The ESP32-S3 drives GPIO13 as a clock while the
  IM69D130 drives the same net as its DATA output. Two push-pull drivers fighting on one node
  is a current-limited short at every disagreement. This risks the mic's output stage and the
  SoC pad, not just "no audio". **This is the concrete blast-radius event the brief anticipates.**
- **GPIO14: no clock.** The mic's CLK input is held statically LOW, so the mic never clocks out
  data and stays in (or falls to) standby.
- **GPIO12: floating.** Configured as PDM DIN but connected to nothing → the pipeline reads
  noise or zeros.

The foreground was correct to stop this. Record it as a standing prohibition:
**`k1_bench_im73d`, `k1_bench_im73d_dsr16`, `k1_bench_im73d_mic_auto_telemetry`,
`k1_bench_im73d_ble`, `k1_custom`, and `k1_prod_im73d` are all incompatible with CLK=14/DATA=13
wiring, because every one of them inherits the same PDM pin macros.**

### 2.3 What the Captain's wiring actually is

CLK=14 / DATA=13 is not arbitrary — it is the **SPH0645 footprint** (BCLK=14, DIN=13). The mic
has been wired onto the original I²S mic pads, which is the natural physical thing to do.

**EDA wiring authority (2026-08-05):** the SpectraSynq dual-IM69D130 PCB3 board
(`SpectraSynq-EDA/im69d130-stereo-mic`) exposes exactly that host interface on J1:

| J1 pin | Net | Host role |
|---|---|---|
| 1 | `PWR_3V3_IN` | 3V3 |
| 2 / 4 / 6 | `GND` | GND (pin 4 retired from LRCLK) |
| 3 | `CLK_IN_3V3` | PDM CLK in (host drives) |
| 5 | `DATA_OUT_3V3` | PDM DATA out (host reads) |

Full evidence: [`im69d130-board-wiring-from-eda-2026-08-05.md`](./im69d130-board-wiring-from-eda-2026-08-05.md)
(SCH-FINAL + PCB3 `PAD_NET` + `SEL-STRAP-TOPOLOGY.html`). Captain’s CLK=14 / DATA=13 claim
**matches** this board’s intended connector map.

> **SELECT is not on J1.** On PCB3 it is hard-strapped with 0 Ω (R7 FIT → IM1 HIGH; R14 FIT →
> IM2 LOW). GPIO12 (SPH LRCLK) has no mate on this connector — leave it unused. Do not drive
> a host SELECT into J1 pin 4 (GND).

### 2.4 Proposed IM69D130 pin contract (new, additive, does not touch IM73D macros)

| Macro | Pin | Role | Rationale |
|---|---|---|---|
| `K1_IM69_PDM_CLK_PIN` | 14 | PDM clock out → board `CLK_IN_3V3` (J1.3) | Matches Captain + EDA J1; = SPH BCLK pad |
| `K1_IM69_PDM_DIN_PIN` | 13 | PDM data in ← board `DATA_OUT_3V3` (J1.5) | Matches Captain + EDA J1; = SPH DIN pad |
| `K1_IM69_PDM_SEL_PIN` | 12 | Unused on PCB3 (escape hatch only) | SELECT hard-strapped on board; SPH LRCLK pad free |

**On PCB3 (authoritative):** IM1 `SEL_IM1` = HIGH via R7→`PWR_1V8`; IM2 `SEL_IM2` = LOW via
R14→`GND` (R9/R13 DNP). Stereo slots are already opposite; mono-A / mono-B is a software
`slot_mask` choice (`I2S_PDM_SLOT_LEFT` / `I2S_PDM_SLOT_RIGHT`), not a rewire.

Keep `K1_IM69_PDM_SEL_PIN` defined but unused as a documented escape hatch for *other*
breakouts that expose SELECT.

### 2.5 Clock rate — a real, non-obvious blocker

The IM73D path runs `I2S_PDM_DSR_8S` at `CONFIG.SAMPLE_RATE = 12800`, i.e. **819.2 kHz** PDM
clock (`i2s_audio.h:225,232`; `platformio.ini:256-264` documents DSR_16S as the +2 dB SNR lever
at 1.6384 MHz).

**819.2 kHz sits at or below the bottom of the normal operating clock range for typical XENSIV
PDM microphones.** Many parts in this family treat sub-MHz clocking as a low-power or standby
mode with degraded or undefined bandwidth, not as normal operation. The IM73D122 is proven at
819.2 kHz on this bench; **the IM69D130 must not be assumed to inherit that.**

> **Design decision:** the IM69D130 env defaults to **`I2S_PDM_DSR_16S` (1.6384 MHz)**, which is
> unambiguously inside the normal PDM band, and only drops to DSR_8S if the datasheet confirms
> support *and* there is a measured reason. This inverts the IM73D default deliberately.
> **Open item O-1:** confirm the IM69D130 clock range against the datasheet before first power-on.

---

## 3. Approaches considered

### Approach 1 — Rewire the mic to the existing IM73D pins; reuse `k1_bench_im73d` unchanged

Move the mic to CLK=13 / DATA=12 / SELECT=14 and flash the existing env.

- **For:** zero firmware change, zero new env, and the A/B is *perfectly* controlled — identical
  binary, identical DSP, identical telemetry, directly comparable to every artefact already in
  `artifacts/im73d_*`.
- **Against — decisive:** the env's flag also repoints the persistence namespace.
  `bridge_fs.h:19-26` maps `K1_MIC_IM73D_PDM_V1` to `CAL_PROFILE_FILE "/cal_profile_pdm.bin"`
  and `/CONFIG_PDM_*.BIN`. Running an IM69D130 under that flag means **any noise calibration
  overwrites the IM73D122's proven cal profile in the same file.** That is precisely the
  "poison cal" blast radius named in the brief.
- **Against:** artefact provenance is corrupted — every log is named `preflight_bench_im73d.log`
  regardless of which microphone was fitted. Six months later nobody can tell the runs apart.
- **Against:** mono only. No path to (C) at all.
- **Against:** discards the Captain's completed wiring for no benefit.

### Approach 2 — New non-shippable `k1_bench_im69d` env, mono-first, own pin + cal namespace

Additive flag `K1_MIC_IM69D_PDM_V1` with its own pin macros (§2.4), its own persistence
namespace, DSR_16S default, `slot_mask = LEFT` (mic A only). Mic B fitted and strapped RIGHT
but not yet read.

- **For:** keeps the Captain's wiring. Cal namespace isolated → IM73D cal untouchable.
  Provenance clean. Byte-identity of all existing envs preserved and provable with the existing
  gate. Delivers the whole of (B) on its own.
- **For:** the hardware for (C) is already fitted and strapped, so (C) becomes a
  flag-and-read-path change on proven silicon rather than a new bring-up.
- **Against:** ~3 new files' worth of `#ifdef` surface, and a second mic-flag family to maintain.
- **Against:** does not answer (C) by itself.

### Approach 3 — Go straight to stereo

Single env, `slot_mode = STEREO`, de-interleave in `acquire_sample_chunk`, dual-channel DSP.

- **For:** answers (C) fastest if everything works.
- **Against — decisive:** it confounds three unproven things at once — a new microphone part, a
  new clock rate, and a new stereo data path. A null result is uninterpretable: silence could be
  a dead mic, a wrong clock, a wrong slot mask, or a de-interleave bug. This is a **Cynefin
  category error**: the pin/clock/driver layer is *complicated* (knowable — read the datasheet,
  follow the IDF contract, verify), while dual-mic *value* is *complex* (only discoverable by
  probing a real room). Merging them means the complicated part contaminates the complex probe.

### Recommendation — **Approach 2, then a staged extension to stereo**

Adopt Approach 2 as **Stage 1** and treat stereo as **Stage 2**, gated on Stage 1 producing
credible mono audio from mic A. Rationale:

- Every failure in Stage 1 has exactly one plausible cause at a time (fitted mic → clock →
  slot → data). That is what makes the complicated layer *cheap* to resolve.
- Stage 1 alone fully delivers (B), which is the question with a live product consequence.
- Stage 2's cost is genuinely small once Stage 1 is green: the sample buffer is already
  `int16_t im73d_samples_i16[1024]` (`globals.h:148`) against a 96-sample chunk, so **stereo
  needs no buffer resize** — only a doubled `bytes_requested` (96 × 2 ch × 2 B = 384 B) and a
  de-interleave in `acquire_sample_chunk` (`i2s_audio.h:311-351`).
- TRIZ, on the "dual vs mono production path" tension: the contradiction is *"we want two mics
  for visual richness but one mic for cost and cal simplicity."* The resolution is
  **separation in time** — dual-mic is a *measurement* instrument that answers whether the
  inter-channel information exists at all; if it does, the *production* answer may still be one
  mic plus synthesised decorrelation. Stage 2 is therefore explicitly an experiment whose
  success does not imply a two-mic BOM.

---

## 4. Environment strategy

**Non-negotiable: `k1_bench_im73d` and its whole descendant tree, plus `k1_prod_im73d`,
`k1_hardware`, and `k1_bench_reference`, are never edited, never extended-from-and-mutated, and
must remain byte-identical.**

Proposed (to be authored only after Captain approval — not written by this design):

```
[env:k1_bench_im69d]              ; Stage 1 — mono mic A
extends = env:k1_bench_reference  ; NOT k1_bench_im73d
build_flags = ${env:k1_bench_reference.build_flags}
              -DK1_MIC_IM69D_PDM_V1
              -DK1_MIC_IM69D_DSR_16S_V1     ; default ON, see §2.5

[env:k1_bench_im69d_micb]         ; Stage 1b — mono mic B, slot_mask = RIGHT
extends = env:k1_bench_im69d      ; proves both mics independently before stereo

[env:k1_bench_im69d_stereo]       ; Stage 2 — gated on Stage 1 + 1b green
extends = env:k1_bench_im69d
build_flags = ${env:k1_bench_im69d.build_flags} -DK1_MIC_IM69D_STEREO_V1
```

Supporting requirements:

- **Upload guard.** Add each new env to the `B489A500` tuple in
  `scripts/platformio/k1_upload_guard.py:90-100`. Never to the `F887A500` (main) tuple.
- **Persistence namespace.** `bridge_fs.h` must map `K1_MIC_IM69D_PDM_V1` to *distinct* files
  (`/cal_profile_im69.bin`, `/CONFIG_IM69_*.BIN`). A shared namespace is the poison-cal failure
  mode and is prohibited. Note both flags can never be defined together — add a
  `#error` if they are.
- **Byte-identity gate.** `scripts/regression-harness/mic_stable_byte_gate.sh` already exists as
  the trustworthy oracle for exactly this contract (it hashes only the three reproducible
  loadable sections). Run it over `k1_hardware k1_bench_reference k1_bench_im73d` with the new
  flag OFF; all three must match the committed reference. This is the mechanical proof that the
  IM69 lane cannot regress the IM73D product path.
- **Non-shippable.** Every new env is bench-only and must carry the standard header comment
  block plus an explicit REVERT recipe, matching the `k1_bench_im73d` precedent
  (`platformio.ini:228-241`).

---

## 5. Dual-mic / stereo plan (C)

### 5.1 Mechanism

Two PDM mics share CLK and DATA. The SELECT strap decides which half of each clock period a mic
drives: SELECT=GND → LEFT slot, SELECT=VDD → RIGHT slot. The ESP32-S3 PDM RX peripheral
recovers both as an interleaved L/R int16 stream when `slot_mode = I2S_SLOT_MODE_STEREO`.

Firmware deltas versus the mono path (Stage 2 only):

1. `slot_cfg` → `I2S_SLOT_MODE_STEREO`, `slot_mask` → both slots.
2. `bytes_requested` doubles to `SAMPLES_PER_CHUNK * 2 * sizeof(int16_t)` (`i2s_audio.h:312`).
3. De-interleave into two mono arrays before the existing gain/DC/GDFT chain.
4. Buffer: none needed — `im73d_samples_i16[1024]` already holds 192 stereo int16
   (`globals.h:148`). *Confirm at implementation; do not reuse the IM73D-named array for an
   IM69 build — introduce a correctly named buffer.*

> **Verify at implementation:** the exact `I2S_PDM_SLOT_*` enum names and the
> `I2S_PDM_RX_SLOT_DEFAULT_CONFIG` mono default against the ESP-IDF 5.4.1 headers actually
> vendored for this build. This design asserts the mechanism, not the spelling.

### 5.2 Mono-first smoke test (Stage 1 / 1b) — what "success" means

| Gate | Criterion |
|---|---|
| G1 Driver | `I2S PDM RX INIT: PASS` and `I2S ENABLE: PASS` on the serial banner |
| G2 Liveness | `raw_i16_rms` responds to a hand clap; returns to a low floor in silence |
| G3 Floor | Quiet-room `raw_i16_abs_peak` in a plausible band — not pinned at 0 (dead/standby) and not near `K1_MIC_IM73D_RAW_I16_NEAR_RAIL`-equivalent (30000, `constants.h:75`) |
| G4 Both mics | Stage 1 (mic A, LEFT) and Stage 1b (mic B, RIGHT) each pass G1–G3 **independently** |

G4 is the gate that makes a Stage-2 null result interpretable. Do not skip it.

### 5.3 The stereo hypothesis and its kill criterion

**H_C:** *Two IM69D130 separated by D mm on the bench K1 produce inter-channel differences large
enough to drive perceptually distinct primary/secondary edge visuals under real programme
material at the intended listening distance.*

**Falsifier:** compute the normalised inter-channel correlation ρ per perceptual band over a
music capture. If **ρ > 0.95 across the bands that actually drive the visuals**, the two channels
carry the same information and H_C is **rejected** — any visual difference between the two edges
would be synthesised, not sensed.

This is the single most important line in the document. A diffuse room field at small spacing is
correlated almost to unity at low frequencies, so rejection is the *expected* outcome and must be
reported as a clean, valuable negative rather than papered over. Reporting "stereo visuals" that
are actually decorrelation noise would breach the measurement-honesty rule in `.claude/CLAUDE.md`.

**Secondary hypothesis H_C2 (robustness, survives H_C rejection):** inter-channel *coherence* can
discriminate diffuse room music (high coherence) from near-field handling noise, enclosure
knocks, and single-side occlusion (low coherence). Even with ρ ≈ 1 for music, a mic covered by a
hand breaks coherence instantly. That is a cheap, real robustness lever and is arguably the
better product justification for a second microphone than stereo visuals.

**Success for C overall** = a defensible yes/no on H_C **with numbers**, plus a measured
statement on H_C2. It is *not* "we made the two edges look different."

**Required before Stage 2:** the physical spacing D (mm) between the two mics must be measured and
recorded. Without D, ρ is uninterpretable. Spacing also sets the frequency above which the mics
begin to decorrelate — larger D decorrelates lower.

---

## 6. A/B evidence plan (B) — IM69D130 vs IM73D122

### 6.1 Reuse, do not reinvent

`scripts/regression-harness/im73d_audio_eval.py` is the R4 measurement harness and already
enforces the safety contract this lane needs: devices identified by USB serial/MAC not port
name, DTR/RTS held low before open, serial writes restricted to colon-prefixed read-only
commands (`{"build","chip_id","dump"}`), and `start_noise_cal`/`N`/`Y` in an explicit
`FORBIDDEN_SERIAL_TOKENS` set (`im73d_audio_eval.py:9-14,53-63`). Extend it with an IM69 role;
do not fork it.

### 6.2 Comparator metric — raw, pre-conditioning only

The only honest comparator is the **pre-conditioning** telemetry triple already emitted and
statically gated:

`raw_i16_abs_peak`, `raw_i16_rms`, `raw_i16_near_pct`
(`i2s_audio.h:376-383`; schema locked by `tests/test_audio_telemetry_schema_static.py:44-46`;
ordering locked by `tests/test_im73d_audio_purity_static.py:45-54`).

`max_raw` is **post** gain/sensitivity/clip/DC (`test_im73d_audio_purity_static.py:32-42`) and
must never be used to compare two microphones — it would mostly measure
`K1_MIC_IM73D_INPUT_GAIN`, which is 16.0 and IM73D-calibrated (`constants.h:62-70`). Any IM69
input gain must be **derived from measurement**, never inherited.

### 6.3 Run matrix

| Run | Purpose | Notes |
|---|---|---|
| R0 quiet-only, IM73D | Noise-floor baseline | Compare to `docs/hardware/im73d-dsr16-quiet-only-evidence-2026-07-06.md` |
| R1 quiet-only, IM69D | Noise-floor candidate | Expect IM69 **worse** by ~4 dB if the SNR encoding holds |
| R2 controlled audio, IM73D | Mid-level reference | Existing volume ladder 45/60/75 (`im73d_audio_eval.py:62`) |
| R3 controlled audio, IM69D | Mid-level candidate | Same track set, same volumes, same distance, same session |
| **R4 loud ladder, both** | **The decisive test** | Extend the ladder upward until IM73D `near_pct`/clip climbs |

R4 is where the design's whole B thesis lives. The AOP advantage is invisible at moderate level
and only appears as **IM73D approaching overload while IM69D does not**. The existing 45/60/75
ladder probably never gets there. If R4 is not run, B produces the misleading conclusion
"IM73D is better" — which is true only in the quiet regime the ladder happens to sample.

### 6.4 Confounds to control

- **DSR mode.** IM69 defaults to DSR_16S (§2.5) while the IM73D baseline artefacts are DSR_8S.
  Compare IM69/DSR_16S against **`k1_bench_im73d_dsr16`**, not the DSR_8S default, or the
  documented +2 dB SNR delta contaminates the mic comparison.
- **Physical position.** Mic A must occupy the same acoustic position the IM73D did. Record it.
- **Session.** Run both mics in one session where practical; room noise floor drifts between days.
- **Cal state.** Both builds must be in a known, *separately namespaced* cal state (§4).

---

## 7. Safety gates

1. **Identity by chip ID.** `B489A500` only. Never a port name (they drift). Never `F887A500`
   (main K1) — cross-flashing is prohibited; the envs differ by GPIO map. Guard tuples in
   `k1_upload_guard.py` are the last line of defence, not the first — consult
   `docs/hardware/device-build-registry.md` first.
2. **Do not flash any `*im73d*` env against the current CLK=14/DATA=13 wiring.** §2.2: this is an
   output-vs-output contention risk on GPIO13, not merely a no-audio condition.
3. **No `start_noise_cal` without a verbal silence confirmation from Captain.** Never auto-fired.
   The harness already refuses to transmit the token.
4. **Cal namespace isolation before any IM69 calibration.** If the persistence split (§4) is not
   in place, an IM69 cal will overwrite `/cal_profile_pdm.bin` and destroy the IM73D122's proven
   profile. Treat this as a hard precondition, not a nicety.
5. **Byte-identity proof.** `mic_stable_byte_gate.sh` green over the three IM73D-lane envs before
   any IM69 commit.
6. **Power-on check.** Confirm IM69D130 supply range covers 3V3 and that the clock rate is
   in-spec (O-1) **before** first power-on.
7. **Non-shippable.** No IM69 flag may reach `k1_hardware` or `k1_prod_im73d`. Production stays
   IM73D122 until Captain says otherwise.
8. **Lane hygiene.** No IM69 work on `lane/dual-sync-phase0` commits.

---

## 8. Open items and assumptions

| ID | Item | Status |
|---|---|---|
| **O-1** | IM69D130 PDM clock range — is 819.2 kHz (DSR_8S) in normal mode, or must we use 1.6384 MHz (DSR_16S)? | **Blocking first power-on.** Design defaults to DSR_16S to be safe. |
| **O-2** | SELECT pin broken out on the Captain's IM69D130 breakout(s), and its current strap? | **ANSWERED for PCB3 EDA board:** hard-strapped (R7 FIT IM1 HIGH, R14 FIT IM2 LOW); not on J1. See wiring authority. |
| **O-3** | SNR/AOP figures (69/130 vs 73/122) confirmed against datasheet + part markings | Assumed from part-number convention. |
| **O-4** | Physical spacing D (mm) between the two mics | Required before Stage 2; unmeasured. |
| **O-5** | Exact ESP-IDF 5.4.1 `I2S_PDM_SLOT_*` spelling and mono default | Verify at implementation. |
| **O-6** | How many IM69D130 units are physically in hand (one or two)? | Stage 2 needs two. |

**O-2 update (EDA, 2026-08-05):** the SpectraSynq PCB3 dual-IM69D130 board hard-ties SELECT
opposite ways (IM1 HIGH / IM2 LOW). (C) is **not** blocked at the hardware level for this board.
Remaining Captain question is only unit count / whether the physical unit on the bench *is* this
PCB3 (vs a different breakout). See [`im69d130-board-wiring-from-eda-2026-08-05.md`](./im69d130-board-wiring-from-eda-2026-08-05.md).

### Clarifying question for Captain (narrowed)

> **Is the board currently wired to the bench K1 the SpectraSynq PCB3 dual-IM69D130
> (`im69d130-stereo-mic`), and how many such boards / mics are in hand?**

(B) and (C) both proceed on PCB3 once that identity is confirmed.

---

## 9. NEXT — Captain decision checklist

Nothing below is actioned by this document. Each line needs an explicit Captain decision.

- [ ] **D1 — Lane.** Open `lane/im69d130-mic-eval` as a new lane, separate from
      `lane/dual-sync-phase0`? (Recommended: yes; do not interleave.)
- [ ] **D2 — Approach.** Approve Approach 2 (new `k1_bench_im69d` env, mono-first, staged to
      stereo)? Or override to Approach 1 (rewire to IM73D pins) / Approach 3 (straight to stereo)?
- [ ] **D3 — Pin contract.** Approve CLK=14 / DATA=13, SELECT unused (§2.4 + EDA wiring
      authority), keeping your existing SPH-pad wiring?
- [ ] **D4 — Confirm board identity.** Physical unit = SpectraSynq PCB3? How many in hand?
- [ ] **D5 — Clock.** Approve DSR_16S (1.6384 MHz) as the IM69 default pending the O-1 datasheet
      check?
- [ ] **D6 — Cal namespace.** Approve the separate `/cal_profile_im69.bin` + `/CONFIG_IM69_*.BIN`
      namespace (required to protect the IM73D cal profile)?
- [ ] **D7 — Scope of B.** Approve extending the volume ladder above 75 for the R4 loud test?
      This is the only run that can reveal the IM69's AOP advantage.
- [ ] **D8 — Scope of C.** Accept H_C's kill criterion (ρ > 0.95 → stereo visuals rejected) as
      binding *before* the measurement, and accept that a rejection is a valid, publishable result?
- [ ] **D9 — Production framing.** Confirm IM73D122 remains the production mic and that this lane
      cannot change that without a separate explicit decision.
- [ ] **D10 — Silence-go.** Withhold `start_noise_cal` authorisation until D6 is implemented.

---

## Appendix — source references

| Claim | Location |
|---|---|
| **EDA board wiring authority (J1 + SELECT)** | [`im69d130-board-wiring-from-eda-2026-08-05.md`](./im69d130-board-wiring-from-eda-2026-08-05.md) |
| Bench-reference GPIO map, IM73D PDM pins | `SPECTRASYNQ_K1_FIRMWARE/system/constants.h:302-321` |
| Production GPIO map, identical PDM pins | `SPECTRASYNQ_K1_FIRMWARE/system/constants.h:332-342` |
| PDM RX init, GPIO14 driven LOW, GPIO13 as clock | `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:223-245` |
| DSR_16S override | `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:240-242` |
| PDM read size / de-interleave site | `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:311-351` |
| Raw pre-conditioning telemetry | `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:376-383` |
| Sample buffer size (1024 int16) | `SPECTRASYNQ_K1_FIRMWARE/system/globals.h:148` |
| Input gain 16.0, near-rail 30000 | `SPECTRASYNQ_K1_FIRMWARE/system/constants.h:62-75` |
| PDM cal/config namespace | `SPECTRASYNQ_K1_FIRMWARE/persistence/bridge_fs.h:17-26` |
| `k1_bench_im73d` env + REVERT precedent | `platformio.ini:228-241` |
| DSR16 env | `platformio.ini:256-264` |
| Bench guard tuple (B489A500) | `scripts/platformio/k1_upload_guard.py:90-100` |
| A/B harness + safety contract | `scripts/regression-harness/im73d_audio_eval.py:9-14,53-63` |
| Byte-identity oracle | `scripts/regression-harness/mic_stable_byte_gate.sh:1-40` |
| Telemetry schema lock | `tests/test_audio_telemetry_schema_static.py:44-46` |
| Purity ordering lock | `tests/test_im73d_audio_purity_static.py:32-54` |
