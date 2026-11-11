#!/usr/bin/env python3
"""AFE2 exposure, reference implementation (K1-FE-SHOW lead, 10 Nov 2026). This file is the specification.

The firmware module audio/k1_afe2.cpp must reproduce `Afe2.process_hop` on the same int16 input
(checked by tests/test_k1_afe2_native.py, which carries a copy of this algorithm).

One meter, one anchor, one output:
  y        = raw samples through a 2nd-order Butterworth high-pass at FC_HZ (RBJ biquad, Q = 1/sqrt 2).
             Raw means before any gain: the result does not depend on SENSITIVITY or on the clamp.
  e        = mean(y^2) over the hop                                  (counts^2)
  S        = section loudness: one-pole on e, attack TAU_S_ATTACK, release TAU_S_RELEASE
  A        = anchor (the slow exposure reference), never below A_MIN:
               S >  A : rise with TAU_A_UP; leave fast mode; quiet timer = 0
               S <= A : if S < Q_QUIET * A the quiet timer runs, otherwise it is cleared;
                        fast mode starts when the timer passes T_HOLD and ends when S > Q_EXIT * A;
                        fall with TAU_A_FAST in fast mode, TAU_A_SLOW otherwise
  how_much = clamp((S / A) ^ (gamma / 2), floor, 1)                   gamma 1 = proportional to sound pressure
  Sq       = the same one-pole on e for the silence test only: attack TAU_S_ATTACK, release TAU_Q_RELEASE
             (0.3 s), so the time to declare silence after a stop does not grow with how loud the music was
  quiet    = stage 2 (11 Nov 2026), the one silence test, on Sq with two levels:
               not quiet -> quiet when Sq < SIL_ENTER;  quiet -> not quiet when Sq > SIL_EXIT
             The firmware declares silence when `quiet` has held for its dwell (SILENCE_DWELL_MS, 5 s).
             No crest, peak or SSL term: loud dense music has a large S whatever its crest factor.
The published level is `what x how_much`, where `what` is the existing 2 s self-normalised beat signal.

Stage 4 (11 Nov 2026, session 5): one gain for the whole spectrum replaces the four-band AGC.
  M        = section mean for the spectrum: one-pole on e, TAU_M both ways (2 s, the time scale of the level
             path's "what"); it does not move while `quiet` (the stage-2 flag), so a stop never re-exposes room noise
  D        = the spectrum's divisor (counts^2), chosen at run time:
               mode 1 "anchor":  D = A                      (the plan text: every bin divided by the slow anchor)
               mode 2 "section": D = max(M, A_MIN)          (level-free "what"; how_much on the output brightness
                                                             then carries the section level exactly once)
  g        = SPEC_K / sqrt(D)                               the one gain, the same for all 80 bins
  out[i]   = mag[i] * g * tilt[i], then the existing fixed soft ceiling (above 0.5: 0.5 + x/(1 + x)), clamped to [0, 1]
  Why two modes: stage 1 put how_much on the output brightness of every effect (the emulator showed scaling the
  level inverted mode 32), so spectral modes already receive the section level. Mode 1 would apply it twice
  (light ~ amplitude^2 at gamma 1); mode 2 applies it once. The emulator A/B decides (plan S4, two attempts).
  SPEC_K   sets where the spectrum sits: at D = e (steady music) the mean bin of mag * g equals SPEC_TARGET, the
           old AGC's target with the soft knee on (0.25). Measured in counts on the five-track set; see SPEC_K below.

Why these numbers (sources in research_notes/K1 audio front end design/):
  FC_HZ 110        the plate shows nothing below its lowest bin; room rumble must not set the reference
  TAU_S_ATTACK 30 ms   a drop must land at once (Light-Show Law 1 and 2); equals the present follower attack
  TAU_S_RELEASE 1.5 s  about the 3 s short-term loudness window of EBU R128; "let go slow"
  TAU_A_UP 3 s     louder room or louder passage becomes the new reference within a few seconds
  TAU_A_SLOW 60 s  a 15-40 s breakdown stays visibly below the chorus (about 0.07 dB/s recovery)
  T_HOLD 45 s, TAU_A_FAST 4 s   a quieter programme that persists is not a breakdown: re-anchor to it
                   (dual-loop idea from hearing-aid AGC: slow loop normally, fast action only on a persistent change)
  A_MIN 36         6 counts rms: below this the music is quieter than the unit will expose to full
  gamma 1, floor 0.25   starting values for the Captain's eye; gamma 0 reproduces today's behaviour exactly
  TAU_Q_RELEASE 0.3 s  with S's 1.5 s release, silence after a loud stop took 8-19 s in the emulator and 20.6 s
                   on its loud smoke clip (the delay grew with loudness); 0.3 s keeps it under ~3 s + the dwell
  SIL_ENTER 16 (4.0 counts rms), SIL_EXIT 25 (5.0 counts rms)   measured on the Main RPL 9087A500, 11 Nov 2026:
                   quiet room (no playback, nightly HVAC, builds running nearby) S = 1.1-4.2 counts rms, one
                   start-up burst to 9.8 (bench/quiet-room-0450.jsonl, 59 lines); Loreen at 10 dB under the
                   Captain's volume never under 4.9 (B_M1 runs, 175 lines). The old test called 16-21 of 88
                   music lines silent at S = 13-30.
"""
from __future__ import annotations

import math

FC_HZ = 110.0
TAU_S_ATTACK = 0.030
TAU_S_RELEASE = 1.5
TAU_A_UP = 3.0
TAU_A_SLOW = 60.0
TAU_A_FAST = 4.0
T_HOLD = 45.0
Q_QUIET = 0.25
Q_EXIT = 0.70
A_MIN = 36.0
GAMMA_DEFAULT = 1.0
FLOOR_DEFAULT = 0.25
SIL_ENTER = 16.0
SIL_EXIT = 25.0
TAU_Q_RELEASE = 0.3
TAU_M = 2.0
SPEC_TARGET = 0.25
SPEC_K = 5.4          # magnitude units per count rms; measured 11 Nov 2026: 4.95-5.64 over five tracks, median 5.42
SPEC_OFF, SPEC_ANCHOR, SPEC_SECTION = 0, 1, 2


def spec_gain(A: float, M: float, mode: int, k: float = None) -> float:
    """Stage 4: the one spectrum gain for mode 1 (anchor) or 2 (section). Mode 0 has no gain here (old AGC)."""
    k = SPEC_K if k is None else k
    if mode == SPEC_ANCHOR:
        d = A
    elif mode == SPEC_SECTION:
        d = max(M, A_MIN)
    else:
        raise ValueError("mode 0 is the old AGC")
    return k / math.sqrt(max(d, A_MIN))


def spectrum(mag, tilt, g: float, knee: bool = True):
    """Stage 4: every bin times the same gain and the fixed tilt, the fixed soft ceiling, clamp to [0, 1]."""
    out = []
    for m, t in zip(mag, tilt):
        o = m * g * t
        if knee and o > 0.5:
            x = o - 0.5
            o = 0.5 + x / (1.0 + x)
        out.append(min(1.0, max(0.0, o)))
    return out


def biquad_highpass(fs: float, fc: float = FC_HZ):
    """RBJ cookbook high-pass, Q = 1/sqrt(2). Returns (b0, b1, b2, a1, a2) with a0 normalised to 1."""
    w0 = 2.0 * math.pi * fc / fs
    cw, sw = math.cos(w0), math.sin(w0)
    alpha = sw / (2.0 * math.sqrt(0.5))
    a0 = 1.0 + alpha
    return ((1.0 + cw) / 2.0 / a0, -(1.0 + cw) / a0, (1.0 + cw) / 2.0 / a0, -2.0 * cw / a0, (1.0 - alpha) / a0)


def alpha(dt: float, tau: float) -> float:
    return 1.0 - math.exp(-dt / tau)


class Afe2:
    def __init__(self, fs: float = 12800.0):
        self.fs = fs
        self.b0, self.b1, self.b2, self.a1, self.a2 = biquad_highpass(fs)
        self.z1 = self.z2 = 0.0
        self.S = 0.0
        self.A = A_MIN
        self.quiet_s = 0.0
        self.fast = False
        self.gamma = GAMMA_DEFAULT
        self.floor = FLOOR_DEFAULT
        self.how_much = 1.0
        self.Sq = 0.0
        self.quiet = False
        self.M = A_MIN

    def process_hop(self, raw) -> float:
        n = len(raw)
        dt = n / self.fs
        acc = 0.0
        z1, z2 = self.z1, self.z2
        for x in raw:                                   # transposed direct form II
            x = float(x)
            y = self.b0 * x + z1
            z1 = self.b1 * x - self.a1 * y + z2
            z2 = self.b2 * x - self.a2 * y
            acc += y * y
        self.z1, self.z2 = z1, z2
        return self.update(acc / n, dt)

    def update(self, e: float, dt: float) -> float:
        """One hop given its high-passed mean energy e (counts^2). Split out so a vectorised filter can feed it."""
        self.S += alpha(dt, TAU_S_ATTACK if e > self.S else TAU_S_RELEASE) * (e - self.S)
        if self.S > self.A:
            self.A += alpha(dt, TAU_A_UP) * (self.S - self.A)
            self.quiet_s = 0.0
            self.fast = False
        else:
            if self.S < Q_QUIET * self.A:
                self.quiet_s += dt
                if self.quiet_s > T_HOLD:
                    self.fast = True
            else:
                self.quiet_s = 0.0
            if self.fast and self.S > Q_EXIT * self.A:
                self.fast = False
            self.A += alpha(dt, TAU_A_FAST if self.fast else TAU_A_SLOW) * (self.S - self.A)
        if self.A < A_MIN:
            self.A = A_MIN
        ratio = self.S / self.A
        if self.gamma == 1.0:
            h = math.sqrt(ratio)
        elif self.gamma == 0.0:
            h = 1.0
        else:
            h = ratio ** (self.gamma * 0.5) if ratio > 0.0 else 0.0
        self.how_much = min(1.0, max(self.floor, h))
        self.Sq += alpha(dt, TAU_S_ATTACK if e > self.Sq else TAU_Q_RELEASE) * (e - self.Sq)
        self.quiet = (self.Sq < SIL_EXIT) if self.quiet else (self.Sq < SIL_ENTER)
        if not self.quiet:
            self.M += alpha(dt, TAU_M) * (e - self.M)
        return self.how_much
