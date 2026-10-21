#pragma once
// k1_tempo_spec.h — every fixed constant the tempo tracker gates a decision on (lane R1,
// invariants I3 and I10, DEF-001 / DEF-002). Included only by audio/k1_tempo.cpp.
//
// Rules:
//   * A constant lives here once and is edited by symbol, never by digit (each substituted
//     token must appear exactly once). Moving a constant here changes no generated code.
//   * Every constant carries one `@prov` line:
//       @prov <SYMBOL> value=<v> mic=<mic|none|UNSTATED> fixture=<sha256|UNPROVENANCED> date=<YYYY-MM-DD> tuned_on=<text>
//     fixture is a 64-hex sha256 of the fixture it was calibrated on, or UNPROVENANCED.
//     tests/test_tempo_spec_provenance.py fails a constant without a well-formed @prov line.
//   * A threshold without provenance is a defect, not a constant (I3). UNPROVENANCED marks the
//     ones that still owe a calibration record; it is a debt, not a licence to retune.
//   * Product mic is the IM69D130. No constant below was calibrated on it.
//
// Dates: the tracker was tuned before this repository's first commit (ed56dfb5, 2026-06-23,
// fork rebrand); dates below are those stated in the source comments / tempo-lock-hardening-plan.md.

// ---------------------------------------------------------------- novelty ring and silence
// @prov K1_NOVELTY_DECAY value=0.999 mic=none fixture=UNPROVENANCED date=2026-06-03 tuned_on=donor default (LightwaveOS/Emotiscope port), per-emit history decay
static const float    K1_NOVELTY_DECAY = 0.999f;
// @prov K1_SILENCE_CONTRAST_WINDOW value=128 mic=none fixture=UNPROVENANCED date=2026-06-03 tuned_on=donor default; contrast window in emits (2.88 s at 44.44 Hz). DEF-001: replaced under K1_TEMPO_SILENCE_FROM_PRODUCER_V1
#define K1_SILENCE_CONTRAST_WINDOW 128
// @prov K1_SILENCE_CONTRAST_ENTER value=0.5 mic=none fixture=UNPROVENANCED date=2026-06-03 tuned_on=donor default; applied to sqrt-of-sqrt novelty (DEF-001 mechanism)
static const float    K1_SILENCE_CONTRAST_ENTER = 0.5f;

// ---------------------------------------------------------------- lock threshold
// @prov K1_LOCK_CONFIDENCE value=0.60 mic=UNSTATED fixture=UNPROVENANCED date=2026-06-03 tuned_on=host tempo_replay synthetic (clean 0.999 vs drone 0.47); the 2026-08-11 tombstone calls it "the SPH0645 calibration" but no SPH0645 fixture is recorded; never measured on IM69D
static const float    K1_LOCK_CONFIDENCE = 0.60f;
// @prov K1_CONF_LOBE value=6 mic=none fixture=UNPROVENANCED date=2026-06-03 tuned_on=Goertzel main-lobe width ~5 BPM (arithmetic, not a fit)
static const int      K1_CONF_LOBE = 6;

// ---------------------------------------------------------------- winner selection
// @prov K1_TACTUS_BPM value=88 mic=none fixture=UNPROVENANCED date=2026-06-04 tuned_on=HarmonixSet 36 tracks, digital host pipe (in-sample: these are now the dev set; DEF-002, rule R6)
#ifndef K1_TACTUS_BPM
#define K1_TACTUS_BPM   88.0f
#endif
// @prov K1_TACTUS_SIGMA value=0.75 mic=none fixture=UNPROVENANCED date=2026-06-04 tuned_on=HarmonixSet 36 tracks, digital host pipe (in-sample, dev set)
#ifndef K1_TACTUS_SIGMA
#define K1_TACTUS_SIGMA 0.75f
#endif
// @prov K1_CONF_BPM value=120 mic=none fixture=UNPROVENANCED date=2026-06-04 tuned_on=host tempo_replay clean trains (metronome-bar gate)
#ifndef K1_CONF_BPM
#define K1_CONF_BPM   120.0f
#endif
// @prov K1_CONF_SIGMA value=0.9 mic=none fixture=UNPROVENANCED date=2026-06-04 tuned_on=host tempo_replay clean trains (metronome-bar gate)
#ifndef K1_CONF_SIGMA
#define K1_CONF_SIGMA 0.9f
#endif
// @prov K1_COMB_TEETH value=4 mic=none fixture=UNPROVENANCED date=2026-06-04 tuned_on=HarmonixSet 36 tracks host sweep (dev set)
#ifndef K1_COMB_TEETH
#define K1_COMB_TEETH 4
#endif
// @prov K1_COMB_W2 value=0.8 mic=none fixture=UNPROVENANCED date=2026-06-04 tuned_on=HarmonixSet 36 tracks host sweep (dev set); harmonic-SUM comb = DEF-002 suspect
#ifndef K1_COMB_W2
#define K1_COMB_W2 0.8f
#endif
// @prov K1_COMB_W3 value=0.7 mic=none fixture=UNPROVENANCED date=2026-06-04 tuned_on=HarmonixSet 36 tracks host sweep (dev set)
#ifndef K1_COMB_W3
#define K1_COMB_W3 0.7f
#endif
// @prov K1_COMB_W4 value=0.6 mic=none fixture=UNPROVENANCED date=2026-06-04 tuned_on=HarmonixSet 36 tracks host sweep (dev set)
#ifndef K1_COMB_W4
#define K1_COMB_W4 0.6f
#endif
// @prov K1_TEMPO_COMB_LOG_FLOOR value=1e-4 mic=none fixture=UNPROVENANCED date=2026-10-21 tuned_on=numerical guard only (geometric comb log floor relative to the ACF table maximum; flag K1_TEMPO_COMB_PRODUCT_V1=1)
#ifndef K1_TEMPO_COMB_LOG_FLOOR
#define K1_TEMPO_COMB_LOG_FLOOR 1e-4f
#endif
// @prov K1_TEMPO_ANTI32_LAMBDA value=0.5 mic=none fixture=UNPROVENANCED date=2026-10-21 tuned_on=initial judgement; any dev sweep records the dev manifest sha256 here (flag K1_TEMPO_COMB_ANTI32_V1)
#ifndef K1_TEMPO_ANTI32_LAMBDA
#define K1_TEMPO_ANTI32_LAMBDA 0.5f
#endif
// @prov K1_WIN_SWITCH_RATIO value=1.1 mic=none fixture=UNPROVENANCED date=2026-06-03 tuned_on=donor default (challenger +10 %)
#define K1_WIN_SWITCH_RATIO 1.1f
// @prov K1_WIN_SWITCH_FRAMES value=5 mic=none fixture=UNPROVENANCED date=2026-06-03 tuned_on=donor default (5 consecutive emits)
#define K1_WIN_SWITCH_FRAMES 5
// @prov K1_AP_UP_RATIO value=1.08 mic=none fixture=UNPROVENANCED date=2026-07-24 tuned_on=HarmonixSet 36 tracks host candidate6 (dev set; flag K1_TEMPO_ANTI_PIN_V1, off)
#ifndef K1_AP_UP_RATIO
#define K1_AP_UP_RATIO          1.08f
#endif
// @prov K1_AP_UP_FRAMES value=4 mic=none fixture=UNPROVENANCED date=2026-07-24 tuned_on=HarmonixSet 36 tracks host candidate6 (dev set; flag off)
#ifndef K1_AP_UP_FRAMES
#define K1_AP_UP_FRAMES         4
#endif
// @prov K1_AP_BASE_RATIO value=1.10 mic=none fixture=UNPROVENANCED date=2026-07-24 tuned_on=equals K1_WIN_SWITCH_RATIO (flag off)
#ifndef K1_AP_BASE_RATIO
#define K1_AP_BASE_RATIO        1.10f
#endif
// @prov K1_AP_BASE_FRAMES value=5 mic=none fixture=UNPROVENANCED date=2026-07-24 tuned_on=equals K1_WIN_SWITCH_FRAMES (flag off)
#ifndef K1_AP_BASE_FRAMES
#define K1_AP_BASE_FRAMES       5
#endif

// ---------------------------------------------------------------- CONF_V2 confidence + lock FSM
// @prov K1_CONF_V2_LO value=0.01 mic=none fixture=UNPROVENANCED date=2026-06-05 tuned_on=tempo_confv2_calibrate.py grid, HarmonixSet 36 + synthetic silence/noise (dev set)
#ifndef K1_CONF_V2_LO
#define K1_CONF_V2_LO 0.01f
#endif
// @prov K1_CONF_V2_HI value=0.04 mic=none fixture=UNPROVENANCED date=2026-06-05 tuned_on=tempo_confv2_calibrate.py grid (dev set)
#ifndef K1_CONF_V2_HI
#define K1_CONF_V2_HI 0.04f
#endif
// @prov K1_CONF_V2_W1 value=0.40 mic=none fixture=UNPROVENANCED date=2026-06-05 tuned_on=tempo_confv2_calibrate.py grid (dev set)
#ifndef K1_CONF_V2_W1
#define K1_CONF_V2_W1 0.40f
#endif
// @prov K1_CONF_V2_W2 value=0.35 mic=none fixture=UNPROVENANCED date=2026-06-05 tuned_on=tempo_confv2_calibrate.py grid (dev set)
#ifndef K1_CONF_V2_W2
#define K1_CONF_V2_W2 0.35f
#endif
// @prov K1_CONF_V2_W3 value=0.25 mic=none fixture=UNPROVENANCED date=2026-06-05 tuned_on=tempo_confv2_calibrate.py grid (dev set)
#ifndef K1_CONF_V2_W3
#define K1_CONF_V2_W3 0.25f
#endif
// @prov K1_CONF_V2_REL value=0.42 mic=none fixture=UNPROVENANCED date=2026-06-05 tuned_on=tempo_confv2_calibrate.py grid (dev set); hysteresis below K1_LOCK_CONFIDENCE
#ifndef K1_CONF_V2_REL
#define K1_CONF_V2_REL 0.42f
#endif
// @prov K1_CONF_V2_FLOOR value=0.20 mic=none fixture=UNPROVENANCED date=2026-06-05 tuned_on=tempo_confv2_calibrate.py (above settled-music dips, below noise band; dev set)
#ifndef K1_CONF_V2_FLOOR
#define K1_CONF_V2_FLOOR 0.20f
#endif
// @prov K1_CONF_V2_WATCHDOG_N value=12 mic=none fixture=UNPROVENANCED date=2026-06-05 tuned_on=judgement (consecutive sub-floor emits, ~0.27 s)
#ifndef K1_CONF_V2_WATCHDOG_N
#define K1_CONF_V2_WATCHDOG_N 12
#endif
// @prov K1_CONF_V2_TAU_S value=0.150 mic=none fixture=UNPROVENANCED date=2026-06-05 tuned_on=donor 0.12/update at 50 Hz rescaled to 44.44 Hz (arithmetic)
#ifndef K1_CONF_V2_TAU_S
#define K1_CONF_V2_TAU_S 0.150f
#endif
// @prov K1_CONF_V2_MIN_BEATS value=2 mic=none fixture=UNPROVENANCED date=2026-06-05 tuned_on=judgement (two observed beats before a lock may acquire)
#ifndef K1_CONF_V2_MIN_BEATS
#define K1_CONF_V2_MIN_BEATS 2
#endif
// @prov K1_CONF_V2_WARMUP_UPDATES value=512 mic=none fixture=UNPROVENANCED date=2026-06-05 tuned_on=history length (arithmetic: ring must fill)
#ifndef K1_CONF_V2_WARMUP_UPDATES
#define K1_CONF_V2_WARMUP_UPDATES 512
#endif

// ---------------------------------------------------------------- FLYWHEEL_V2 phase-locked beat
// @prov K1_FW_KP value=0.25 mic=none fixture=UNPROVENANCED date=2026-06-05 tuned_on=tempo_flywheel_calibrate.py synthetic trains + HarmonixSet density (dev set)
#ifndef K1_FW_KP
#define K1_FW_KP 0.25f
#endif
// @prov K1_FW_KI value=0.002 mic=none fixture=UNPROVENANCED date=2026-06-05 tuned_on=tempo_flywheel_calibrate.py (dev set)
#ifndef K1_FW_KI
#define K1_FW_KI 0.002f
#endif
// @prov K1_FW_MAX_CORR value=0.10 mic=none fixture=UNPROVENANCED date=2026-06-05 tuned_on=tempo_flywheel_calibrate.py (dev set)
#ifndef K1_FW_MAX_CORR
#define K1_FW_MAX_CORR 0.10f
#endif
// @prov K1_FW_FREQ_PULL value=0.04 mic=none fixture=UNPROVENANCED date=2026-06-05 tuned_on=judgement (+/-4 % octave-safe band)
#ifndef K1_FW_FREQ_PULL
#define K1_FW_FREQ_PULL 0.04f
#endif
// @prov K1_FW_ONSET_K value=1.20 mic=none fixture=UNPROVENANCED date=2026-06-05 tuned_on=tempo_flywheel_calibrate.py (dev set)
#ifndef K1_FW_ONSET_K
#define K1_FW_ONSET_K 1.20f
#endif
// @prov K1_FW_ONSET_FLOOR_TAU_S value=0.30 mic=none fixture=UNPROVENANCED date=2026-06-05 tuned_on=judgement (slow floor tracker)
#ifndef K1_FW_ONSET_FLOOR_TAU_S
#define K1_FW_ONSET_FLOOR_TAU_S 0.30f
#endif
// @prov K1_FW_COAST_BEATS value=8 mic=none fixture=UNPROVENANCED date=2026-06-05 tuned_on=judgement (~2 bars, donor practice)
#ifndef K1_FW_COAST_BEATS
#define K1_FW_COAST_BEATS 8
#endif
// @prov K1_FW_REFRACTORY value=0.45 mic=none fixture=UNPROVENANCED date=2026-06-05 tuned_on=judgement (min beats between ticks)
#ifndef K1_FW_REFRACTORY
#define K1_FW_REFRACTORY 0.45f
#endif
