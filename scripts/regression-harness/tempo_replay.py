#!/usr/bin/env python3
"""Compile and run host-side replay tests for sb_tempo.cpp.

Feeds synthetic novelty impulse trains (clean metronome-equivalent) through the REAL
sb_tempo Goertzel-over-novelty detector on host, and asserts it (a) detects the right
BPM, (b) reports confidence that clears the lock threshold, (c) locks, (d) releases on
silence, and (e) does NOT false-lock on flat/no-beat input. Prints, per case, both the
old peak/sum confidence and the new peak^2/sum_sq concentration confidence so the metric
behaviour is ground-truthed, not guessed. No hardware, no bench — closes the tempo lock
loop autonomously. Mirrors onset_beat_replay.py.
"""

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FIRMWARE = ROOT / "SPECTRASYNQ_K1_FIRMWARE"


ARDUINO_STUB = r"""
#pragma once
#include <stdint.h>
struct portMUX_TYPE {};
#define portMUX_INITIALIZER_UNLOCKED portMUX_TYPE{}
static inline void portENTER_CRITICAL(portMUX_TYPE*) {}
static inline void portEXIT_CRITICAL(portMUX_TYPE*) {}
"""


CPP_REPLAY = r"""
#include "sb_tempo.h"

#include <cmath>
#include <cstdio>
#include <cstring>

// host-test introspection hooks compiled into sb_tempo.cpp under SB_TEMPO_HOST_TEST
void sb_tempo_debug_dump(float*, int, int*, float*, float*);
void sb_tempo_debug_dump_raw(float*, int);
#if defined(SB_TEMPO_CONF_V2) && defined(SB_TEMPO_CONF_DUMP)
// V2 calibration introspection — last-computed raw quality components (compiled only when BOTH
// SB_TEMPO_CONF_V2 and SB_TEMPO_CONF_DUMP are set). Lets the corpus sweep dump component
// distributions to pick LO/HI/weights/REL/FLOOR.
void sb_tempo_debug_dump_v2(float*, float*, float*, float*, float*, float*, int*, int*, float*, float*, float*);
#endif

static int failures = 0;
static void check(bool condition, const char* message) {
  if (!condition) { std::printf("FAIL: %s\n", message); failures++; }
}

// SensoryBridge AP frame rate = SAMPLE_RATE / SAMPLES_PER_CHUNK = 12800/96 = 133.333 Hz.
static const float FPS = 12800.0f / 96.0f;

static SBAudioSnapshot mk(uint32_t ms, float novelty, bool silence) {
  SBAudioSnapshot a = {};
  a.frame_ms = ms;
  a.novelty = novelty;
  a.silence = silence;
  return a;
}

static void dump(const char* label, const SBTempoEvent& e) {
  float sm[96]; int win = 0; float ps_live = 0.0f, cf_live = 0.0f;
  sb_tempo_debug_dump(sm, 96, &win, &ps_live, &cf_live);
  float mx = 0.0f, ssq = 1e-12f, lin = 0.0f; int mi = 0;
  for (int i = 0; i < 96; i++) { float v = sm[i]; lin += v; ssq += v * v; if (v > mx) { mx = v; mi = i; } }
  // outside-the-main-lobe stats (|i - winner| > 6): a real tempo is an ISOLATED peak, so
  // the strongest bin outside its lobe is tiny; a flat/DC ramp has no isolated peak so
  // outside energy stays high. These discriminate beat from drone where peak/sum can't.
  float out_max = 0.0f, out_ssq = 1e-12f;
  for (int i = 0; i < 96; i++) { int d = i - mi; if (d < 0) d = -d; if (d > 6) { float v = sm[i]; if (v > out_max) out_max = v; out_ssq += v * v; } }
  float prominence = 1.0f - out_max / mx;          // candidate A: peak above its best out-of-lobe rival
  float conc6      = (mx * mx) / (mx * mx + out_ssq); // candidate B: concentration ignoring the lobe
  std::printf("[%-12s] bpm=%.1f conf=%.3f lock=%d || raw=%.3f conc=%.3f  PROMINENCE=%.3f CONC6=%.3f  (peak bin%d=%.0fBPM mag=%.3f out_max=%.3f linsum=%.2f)\n",
              label, e.bpm, e.confidence, e.locked ? 1 : 0,
              mx / lin, (mx * mx) / ssq, prominence, conc6,
              mi, 60.0f + (float)mi, mx, out_max, lin);
}

static SBTempoEvent run_train(float bpm, float secs, float silence_secs) {
  sb_tempo_reset();
  const float beat_ms = 60000.0f / bpm;
  float next_beat = 0.0f;
  uint32_t n = (uint32_t)(secs * FPS);
  for (uint32_t f = 0; f < n; f++) {
    uint32_t ms = (uint32_t)((float)f * 1000.0f / FPS + 0.5f);
    float nov = 0.0f;
    if ((float)ms >= next_beat) { nov = 1.0f; next_beat += beat_ms; }
    sb_tempo_update(mk(ms, nov, false));
  }
  SBTempoEvent e = sb_tempo_read();
  if (silence_secs > 0.0f) {
    uint32_t s = (uint32_t)(silence_secs * FPS);
    for (uint32_t f = 0; f < s; f++) {
      uint32_t ms = (uint32_t)((float)(n + f) * 1000.0f / FPS + 0.5f);
      sb_tempo_update(mk(ms, 0.0f, true));
    }
    e = sb_tempo_read();
  }
  return e;
}

static SBTempoEvent run_flat(float level, float secs) {
  sb_tempo_reset();
  uint32_t n = (uint32_t)(secs * FPS);
  for (uint32_t f = 0; f < n; f++) {
    uint32_t ms = (uint32_t)((float)f * 1000.0f / FPS + 0.5f);
    sb_tempo_update(mk(ms, level, false));
  }
  return sb_tempo_read();
}

// deterministic PRNG (fixed seed) so the noisy case is reproducible
static uint32_t g_rng = 12345u;
static float frand() { g_rng = g_rng * 1664525u + 1013904223u; return (float)((g_rng >> 8) & 0xFFFFFF) / (float)0x1000000; }

// Real-music-like: ~88% of beats land with jittered amplitude (0.55..1.0) on a per-frame
// broadband noise floor — stresses the detector far harder than a clean metronome. This is
// the "will it survive real music, not just a click" test Captain's instinct points at.
static SBTempoEvent run_noisy(float bpm, float secs) {
  sb_tempo_reset();
  const float beat_ms = 60000.0f / bpm;
  float next_beat = 0.0f;
  uint32_t n = (uint32_t)(secs * FPS);
  for (uint32_t f = 0; f < n; f++) {
    uint32_t ms = (uint32_t)((float)f * 1000.0f / FPS + 0.5f);
    float nov = 0.08f * frand();                          // broadband noise floor
    if ((float)ms >= next_beat) {
      next_beat += beat_ms;
      if (frand() > 0.12f) nov = 0.55f + 0.45f * frand(); // most beats hit, amplitude jitter
    }
    sb_tempo_update(mk(ms, nov, false));
  }
  return sb_tempo_read();
}

// Tempo change mid-stream: bpm1 for each_secs, then bpm2 — must re-lock to bpm2.
static SBTempoEvent run_change(float bpm1, float bpm2, float each_secs) {
  sb_tempo_reset();
  uint32_t n = (uint32_t)(each_secs * FPS);
  float beat = 60000.0f / bpm1, next = 0.0f;
  for (uint32_t f = 0; f < n; f++) {
    uint32_t ms = (uint32_t)((float)f * 1000.0f / FPS + 0.5f);
    float nov = 0.0f;
    if ((float)ms >= next) { nov = 1.0f; next += beat; }
    sb_tempo_update(mk(ms, nov, false));
  }
  beat = 60000.0f / bpm2;
  next = (float)((uint32_t)((float)n * 1000.0f / FPS + 0.5f));
  for (uint32_t f = 0; f < n; f++) {
    uint32_t ms = (uint32_t)((float)(n + f) * 1000.0f / FPS + 0.5f);
    float nov = 0.0f;
    if ((float)ms >= next) { nov = 1.0f; next += beat; }
    sb_tempo_update(mk(ms, nov, false));
  }
  return sb_tempo_read();
}

// ---- FLYWHEEL V2 synthetic tick-collection harness (only meaningful under the flag) ----
// Drives a synthetic novelty stream and collects the EMIT-LEVEL beat_tick stream (deduped
// against the 133 Hz stale-republish), so the flywheel's one-shot beats can be asserted for
// density (one beat per tactus period), phase-lock (ticks near true beats), drift tracking,
// gap survival, and no-beat-storm on silence/noise. Returns counts via out params.
struct FwResult { int n_ticks; double density_hz; int matched_70ms; int n_true; bool ever_locked; };

static FwResult fw_train(float bpm, float secs, float gap_each, float gap_len) {
  // gap_each>0 -> drop the impulse for gap_len s every gap_each s (missing-onset gaps test).
  sb_tempo_reset();
  const float beat_ms = 60000.0f / bpm;
  float next_beat = 0.0f;
  uint32_t n = (uint32_t)(secs * FPS);
  const float warm_ms = 13000.0f;
  double ticks[8000]; int nt = 0;
  double truebeats[8000]; int ntr = 0;
  bool ever_locked = false;
  int prev_tick = 0;
  for (uint32_t f = 0; f < n; f++) {
    uint32_t ms = (uint32_t)((float)f * 1000.0f / FPS + 0.5f);
    float nov = 0.0f;
    bool in_gap = (gap_each > 0.0f) && (fmodf((float)ms / 1000.0f, gap_each) < gap_len);
    if ((float)ms >= next_beat) {
      if (!in_gap) nov = 1.0f;
      if ((float)ms >= warm_ms && ntr < 8000) truebeats[ntr++] = ms;
      next_beat += beat_ms;
    }
    sb_tempo_update(mk(ms, nov, false));
    SBTempoEvent e = sb_tempo_read();
    if (e.locked) ever_locked = true;
    int t = e.beat_tick ? 1 : 0;
    if (t && !prev_tick && (float)ms >= warm_ms && nt < 8000) ticks[nt++] = ms;  // dedup republish
    prev_tick = t;
  }
  // greedy +-70ms match
  int matched = 0; static bool used[8000];
  for (int i = 0; i < nt; i++) used[i] = false;
  for (int i = 0; i < ntr; i++) {
    double best = 1e9; int bj = -1;
    for (int j = 0; j < nt; j++) { if (used[j]) continue; double d = std::fabs(ticks[j] - truebeats[i]); if (d < best) { best = d; bj = j; } }
    if (bj >= 0 && best <= 70.0) { used[bj] = true; matched++; }
  }
  double dur = (secs * 1000.0 - warm_ms) / 1000.0;
  FwResult r; r.n_ticks = nt; r.density_hz = (dur > 0) ? nt / dur : 0.0;
  r.matched_70ms = matched; r.n_true = ntr; r.ever_locked = ever_locked;
  return r;
}

static FwResult fw_drift(float bpm0, float bpm1, float secs) {
  // Linear tempo ramp bpm0->bpm1 — the PLL must track the drifting beat grid.
  sb_tempo_reset();
  uint32_t n = (uint32_t)(secs * FPS);
  const float warm_ms = 13000.0f;
  float next_beat = 0.0f;
  double ticks[8000]; int nt = 0; double truebeats[8000]; int ntr = 0;
  int prev_tick = 0; bool ever_locked = false;
  for (uint32_t f = 0; f < n; f++) {
    uint32_t ms = (uint32_t)((float)f * 1000.0f / FPS + 0.5f);
    float frac = (float)f / (float)n;
    float bpm = bpm0 + (bpm1 - bpm0) * frac;
    float beat_ms = 60000.0f / bpm;
    float nov = 0.0f;
    if ((float)ms >= next_beat) { nov = 1.0f; if ((float)ms >= warm_ms && ntr < 8000) truebeats[ntr++] = ms; next_beat += beat_ms; }
    sb_tempo_update(mk(ms, nov, false));
    SBTempoEvent e = sb_tempo_read();
    if (e.locked) ever_locked = true;
    int t = e.beat_tick ? 1 : 0;
    if (t && !prev_tick && (float)ms >= warm_ms && nt < 8000) ticks[nt++] = ms;
    prev_tick = t;
  }
  int matched = 0; static bool used[8000];
  for (int i = 0; i < nt; i++) used[i] = false;
  for (int i = 0; i < ntr; i++) {
    double best = 1e9; int bj = -1;
    for (int j = 0; j < nt; j++) { if (used[j]) continue; double d = std::fabs(ticks[j] - truebeats[i]); if (d < best) { best = d; bj = j; } }
    if (bj >= 0 && best <= 70.0) { used[bj] = true; matched++; }
  }
  double dur = (secs * 1000.0 - warm_ms) / 1000.0;
  FwResult r; r.n_ticks = nt; r.density_hz = (dur > 0) ? nt / dur : 0.0;
  r.matched_70ms = matched; r.n_true = ntr; r.ever_locked = ever_locked;
  return r;
}

static int fw_silence_ticks(float secs) {   // pure silence: must emit ZERO ticks
  sb_tempo_reset();
  uint32_t n = (uint32_t)(secs * FPS); int t = 0; int prev = 0;
  for (uint32_t f = 0; f < n; f++) {
    uint32_t ms = (uint32_t)((float)f * 1000.0f / FPS + 0.5f);
    sb_tempo_update(mk(ms, 0.0f, true));
    SBTempoEvent e = sb_tempo_read();
    int tk = e.beat_tick ? 1 : 0; if (tk && !prev) t++; prev = tk;
  }
  return t;
}

static int fw_noise_ticks(float secs) {   // white noise: must not beat-storm
  sb_tempo_reset();
  g_rng = 999u;
  uint32_t n = (uint32_t)(secs * FPS); int t = 0; int prev = 0;
  for (uint32_t f = 0; f < n; f++) {
    uint32_t ms = (uint32_t)((float)f * 1000.0f / FPS + 0.5f);
    sb_tempo_update(mk(ms, frand(), false));
    SBTempoEvent e = sb_tempo_read();
    int tk = e.beat_tick ? 1 : 0; if (tk && !prev) t++; prev = tk;
  }
  return t;
}

// File-replay mode: read whitespace lines "ms novelty silence" from stdin, drive the
// UNMODIFIED sb_tempo through them, and print one trajectory line per update:
//   T <ms> <bpm> <conf> <locked> <phase01> <beat_tick>
// followed by a final "FILE_DONE frames=N". Lets a real-music novelty curve
// (novelty_from_wav.py) be scored for tempo/octave accuracy on host — the digital,
// no-bench real-music validation pipe (Lane A, tempo-lock-hardening-plan.md).
// phase01/beat_tick are appended (trailing columns) so older parsers that index
// p[1..4] still work; beat_semantic_metrics.py consumes the beat_tick column to
// score beat-F / continuity against the corpus's GT beat-time annotations.
static int run_stdin_replay() {
  sb_tempo_reset();
  char line[160];
  unsigned long n = 0;
  while (std::fgets(line, sizeof(line), stdin)) {
    unsigned int ms = 0; float nov = 0.0f; int sil = 0;
    if (std::sscanf(line, "%u %f %d", &ms, &nov, &sil) < 2) continue;
    sb_tempo_update(mk(ms, nov, sil != 0));
    SBTempoEvent e = sb_tempo_read();
#if defined(SB_TEMPO_CONF_V2) && defined(SB_TEMPO_CONF_DUMP)
    // Append the raw V2 quality components as TRAILING columns (p[7..]) — backward-compatible:
    //   T <ms> <bpm> <conf> <locked> <phase01> <beat_tick> <histShareNorm> <prominence>
    //     <periodicity> <peakShare> <quality> <point_peakShare> <point_prominence>
    float hs=0,pr=0,pe=0,psh=0,ql=0,ce=0,pps=0,ppr=0,bgp=0; int lk2=0,bs=0;
    sb_tempo_debug_dump_v2(&hs,&pr,&pe,&psh,&ql,&ce,&lk2,&bs,&pps,&ppr,&bgp);
    std::printf("T %u %.1f %.4f %d %.4f %d %.4f %.4f %.4f %.4f %.4f %.4f %.4f %.4f\n", ms, e.bpm, e.confidence,
                e.locked ? 1 : 0, e.phase01, e.beat_tick ? 1 : 0, hs, pr, pe, psh, ql, pps, ppr, bgp);
#else
    std::printf("T %u %.1f %.4f %d %.4f %d\n", ms, e.bpm, e.confidence, e.locked ? 1 : 0,
                e.phase01, e.beat_tick ? 1 : 0);
#endif
    n++;
  }
  float raw[96]; sb_tempo_debug_dump_raw(raw, 96);   // final raw Goertzel spectrum (diagnostic)
  std::printf("RAWSPEC");
  for (int i = 0; i < 96; i++) std::printf(" %.4f", raw[i]);
  std::printf("\n");
  std::printf("FILE_DONE frames=%lu\n", n);
  return 0;
}

int main(int argc, char** argv) {
  sb_tempo_init();
  if (argc >= 2 && std::strcmp(argv[1], "--replay-stdin") == 0) {
    return run_stdin_replay();
  }

  SBTempoEvent e120 = run_train(120.0f, 16.0f, 0.0f);
  dump("120bpm", e120);
  check(std::fabs(e120.bpm - 120.0f) <= 1.5f, "120 BPM clean train detected as ~120");
  check(e120.confidence > 0.80f, "120 BPM clean train reads HIGH confidence (near-maximal — the metronome bar)");
  check(e120.locked, "120 BPM clean train LOCKS (the metronome case)");

  SBTempoEvent e90 = run_train(90.0f, 16.0f, 0.0f);
  dump("90bpm", e90);
  check(std::fabs(e90.bpm - 90.0f) <= 1.5f, "90 BPM clean train detected as ~90 (not hardcoded to 120)");
  check(e90.locked, "90 BPM clean train LOCKS");

  SBTempoEvent e144 = run_train(144.0f, 16.0f, 0.0f);
  dump("144bpm", e144);
  check(std::fabs(e144.bpm - 144.0f) <= 2.0f, "144 BPM clean train detected as ~144 (upper range)");
  check(e144.locked, "144 BPM clean train LOCKS");

  SBTempoEvent eSil = run_train(120.0f, 16.0f, 3.0f);
  dump("120+silence", eSil);
  check(!eSil.locked, "silence releases the lock");

  SBTempoEvent eFlat = run_flat(0.05f, 16.0f);
  dump("flat", eFlat);
  check(!eFlat.locked, "flat / no-beat input does NOT false-lock");

  SBTempoEvent eNoisy = run_noisy(120.0f, 18.0f);
  dump("noisy120", eNoisy);
  check(std::fabs(eNoisy.bpm - 120.0f) <= 2.0f, "real-music-like noisy 120 (88% hit, amp jitter, noise floor) detects ~120");
  check(eNoisy.locked, "real-music-like noisy 120 LOCKS (does it survive non-clean input)");

  SBTempoEvent eChg = run_change(120.0f, 90.0f, 12.0f);
  dump("120->90", eChg);
  check(std::fabs(eChg.bpm - 90.0f) <= 2.0f, "tempo change 120->90 re-locks to 90");
  check(eChg.locked, "tempo change re-locks");

  int cases = 7;
#ifdef SB_TEMPO_FLYWHEEL_V2
  // ===== FLYWHEEL V2 beat-emission tests (only compiled with -DSB_TEMPO_FLYWHEEL_V2) =====
  // (1) Steady beat: ONE tick per tactus period (density ~= bpm/60), and near-perfect phase
  //     lock on a clean train (the 3x stale-republish over-emission must be GONE).
  FwResult fs120 = fw_train(120.0f, 22.0f, 0.0f, 0.0f);
  std::printf("[fw steady120] ticks=%d dens=%.3fHz matched=%d/%d locked=%d\n",
              fs120.n_ticks, fs120.density_hz, fs120.matched_70ms, fs120.n_true, fs120.ever_locked);
  check(std::fabs(fs120.density_hz - 2.0f) <= 0.25f, "FW steady 120: density ~2.0 Hz (one beat/period, NOT 3x)");
  check(fs120.n_true > 0 && fs120.matched_70ms >= (int)(0.80 * fs120.n_true),
        "FW steady 120: >=80% of true beats matched within +-70ms (phase-locked)");
  cases++;

  FwResult fs90 = fw_train(90.0f, 22.0f, 0.0f, 0.0f);
  std::printf("[fw steady90 ] ticks=%d dens=%.3fHz matched=%d/%d\n",
              fs90.n_ticks, fs90.density_hz, fs90.matched_70ms, fs90.n_true);
  check(std::fabs(fs90.density_hz - 1.5f) <= 0.25f, "FW steady 90: density ~1.5 Hz");
  check(fs90.n_true > 0 && fs90.matched_70ms >= (int)(0.80 * fs90.n_true),
        "FW steady 90: >=80% matched within +-70ms");
  cases++;

  // (2) Tempo drift (ramp 110->130): the PLL must TRACK, staying largely phase-locked.
  FwResult fdr = fw_drift(110.0f, 130.0f, 24.0f);
  std::printf("[fw drift    ] ticks=%d dens=%.3fHz matched=%d/%d\n",
              fdr.n_ticks, fdr.density_hz, fdr.matched_70ms, fdr.n_true);
  check(fdr.n_true > 0 && fdr.matched_70ms >= (int)(0.50 * fdr.n_true),
        "FW drift 110->130: >=50% of true beats tracked within +-70ms");
  cases++;

  // (3) Missing-onset gaps (drop 0.8 s of impulses every 4 s): flywheel inertia keeps the
  //     beat through the gap, so density stays near tactus (NOT collapsed to zero).
  FwResult fgap = fw_train(120.0f, 24.0f, 4.0f, 0.8f);
  std::printf("[fw gaps     ] ticks=%d dens=%.3fHz matched=%d/%d\n",
              fgap.n_ticks, fgap.density_hz, fgap.matched_70ms, fgap.n_true);
  check(fgap.density_hz >= 1.5f && fgap.density_hz <= 2.4f,
        "FW gaps: density holds ~tactus through dropouts (flywheel inertia, no collapse)");
  cases++;

  // (4) Double/half-time trap: a clean 144 train. The winner may halve to 72 (a SELECTION
  //     artifact this phase does NOT touch); whatever octave the winner picks, the flywheel
  //     must emit ONE tick per that period (no double-emission), density in the tactus band.
  FwResult ftrap = fw_train(144.0f, 22.0f, 0.0f, 0.0f);
  std::printf("[fw 144trap  ] ticks=%d dens=%.3fHz (winner-octave dependent)\n",
              ftrap.n_ticks, ftrap.density_hz);
  check(ftrap.density_hz >= 0.8f && ftrap.density_hz <= 2.8f,
        "FW 144 trap: density in tactus band (no double-emission regardless of winner octave)");
  cases++;

  // (5) Silence / noise: NO beat-storm. Silence -> ZERO ticks; white noise -> few/none.
  int sil_ticks = fw_silence_ticks(16.0f);
  int noi_ticks = fw_noise_ticks(16.0f);
  std::printf("[fw silence  ] ticks=%d   [fw noise] ticks=%d\n", sil_ticks, noi_ticks);
  check(sil_ticks == 0, "FW silence: ZERO beat ticks (no metronome-on-silence)");
  check(noi_ticks <= 3, "FW white noise: <=3 ticks over 16s (no beat-storm / false lock)");
  cases++;
#endif

  if (failures != 0) { std::printf("TEMPO_REPLAY_FAIL failures=%d\n", failures); return 1; }
  std::printf("TEMPO_REPLAY_OK cases=%d\n", cases);
  return 0;
}
"""


def build_binary(workdir, compiler="clang++", defines=None, extra_flags=None, tempo_source=None):
    """Write the Arduino stub + harness main into workdir and compile against the REAL
    sb_tempo.cpp. Returns (ok, binary_path, result_dict). The caller owns workdir's
    lifetime, so the binary can be reused across many --replay-stdin runs (compile once,
    replay N files) — used by tempo_accuracy.py for the corpus sweep.

    `defines`: optional iterable of preprocessor defines (each "NAME" or "NAME=VALUE"),
    compiled in as -D flags. This is how a CANDIDATE build is produced — e.g.
    defines=["SB_TEMPO_CONF_V2"] builds the V2 confidence/lock path; with no defines the
    incumbent (production) path is compiled byte-for-byte unchanged. `extra_flags`: optional
    iterable of raw extra compiler flags. `tempo_source` is a harness-only escape hatch for
    compiling a temporary copy of sb_tempo.cpp; production callers leave it unset."""
    workdir = Path(workdir)
    stub_dir = workdir / "stub"
    stub_dir.mkdir(parents=True, exist_ok=True)
    (stub_dir / "Arduino.h").write_text(ARDUINO_STUB, encoding="utf-8")
    main_cpp = workdir / "tempo_replay_main.cpp"
    binary = workdir / "tempo_replay"
    main_cpp.write_text(CPP_REPLAY, encoding="utf-8")

    compile_cmd = [
        compiler,
        "-std=c++17",
        "-Wall",
        "-Wextra",
        "-DSB_TEMPO_HOST_TEST",
    ]
    for d in (defines or []):
        compile_cmd.append("-D" + str(d))
    compile_cmd.extend(list(extra_flags or []))
    compile_cmd += [
        "-I",
        str(stub_dir),
        "-I",
        str(FIRMWARE),
        "-I",
        str(FIRMWARE / "audio"),  # Phase 1 restructure: sb_tempo.{cpp,h} moved to audio/
        "-I",
        str(FIRMWARE / "system"),
        str(tempo_source or (FIRMWARE / "audio" / "sb_tempo.cpp")),
        str(main_cpp),
        "-o",
        str(binary),
    ]
    r = subprocess.run(
        compile_cmd, cwd=ROOT, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    ok = r.returncode == 0
    return ok, binary, {
        "ok": ok, "stage": "compile", "returncode": r.returncode,
        "stdout": r.stdout, "stderr": r.stderr, "workdir": str(workdir),
    }


def replay_stdin(binary, text):
    """Run the compiled harness in --replay-stdin mode, feeding `text` (one
    'ms novelty silence' line per AP frame) on stdin. Returns a run result dict;
    stdout carries the 'T <ms> <bpm> <conf> <locked>' trajectory + 'FILE_DONE frames=N'."""
    r = subprocess.run(
        [str(binary), "--replay-stdin"], cwd=ROOT, text=True,
        input=text, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    return {
        "ok": r.returncode == 0, "stage": "run", "returncode": r.returncode,
        "stdout": r.stdout, "stderr": r.stderr,
    }


def run_replay(compiler="clang++", keep_dir=None, defines=None):
    temp_owner = None
    if keep_dir:
        workdir = Path(keep_dir)
        workdir.mkdir(parents=True, exist_ok=True)
    else:
        temp_owner = tempfile.TemporaryDirectory()
        workdir = Path(temp_owner.name)

    try:
        ok, binary, comp = build_binary(workdir, compiler, defines=defines)
        if not ok:
            return comp
        run_result = subprocess.run(
            [str(binary)], cwd=ROOT, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        return {
            "ok": run_result.returncode == 0, "stage": "run",
            "returncode": run_result.returncode,
            "stdout": run_result.stdout, "stderr": run_result.stderr,
            "workdir": str(workdir),
        }
    finally:
        if temp_owner is not None:
            temp_owner.cleanup()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", default="clang++")
    parser.add_argument("--keep-dir")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of replay stdout")
    parser.add_argument("--define", action="append", default=[],
                        help="extra -D preprocessor define (repeatable); e.g. --define SB_TEMPO_CONF_V2")
    parser.add_argument("--candidate-confv2", action="store_true",
                        help="shorthand for --define SB_TEMPO_CONF_V2 (build the V2 confidence/lock path)")
    args = parser.parse_args(argv)

    defines = list(args.define)
    if args.candidate_confv2 and "SB_TEMPO_CONF_V2" not in defines:
        defines.append("SB_TEMPO_CONF_V2")
    result = run_replay(compiler=args.compiler, keep_dir=args.keep_dir, defines=defines)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        if result.get("stdout"):
            print(result["stdout"], end="")
        if result.get("stderr"):
            print(result["stderr"], end="", file=sys.stderr)
    return 0 if result["ok"] else result["returncode"] or 1


if __name__ == "__main__":
    sys.exit(main())
