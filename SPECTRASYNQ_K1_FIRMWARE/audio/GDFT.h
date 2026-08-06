#ifndef GDFT_H
#define GDFT_H

//
// Welcome to the GDFT file: this is the core of K1.
// This is where time-domain audio is converted into a
// frequency-domain representation for your viewing pleasure. This
// file doesn't actually contain LED code. That's lightshow_modes.h,
// which references values calculated here on each frame.
//
// It's not FFT. It's a Goertzel-based Discrete Fourier Transform,
// or what I'm calling a "GDFT". The Goertzel algorithm detects the
// presence/magnitude of a single frequency in a signal, and in
// this case I'm running 64 instances of Goertzel at once on the
// 64 frequencies set in constants.h.
//
// https://en.wikipedia.org/wiki/Goertzel_algorithm
//
// This is slightly slower than FFT, but allows for two really
// neat tricks:
//
// 1. I can scale the frequency range however I'd like.
//
//    With an FFT of size 128 at a sample rate of 10KHz, you'd get
//    back 64 bins between 0Hz (useless) and 5KHz. These aren't
//    evenly spaced bins though, with frequency increasing by a
//    linear amount between bins, unlike the keys of a piano where
//    every 12th note is doubled in frequency.
//
//    By running Goertzel's algorithm 64 times in parallel I can
//    choose my own bin spacing, and in this case K1 is
//    watching the upper 64 keys of an 88-key piano's frequency
//    range: 110Hz to 4186Hz (by default).
//
//    This means that every "half-step" up in pitch in an
//    instrument is it's own distinct frequency bin, with only
//    a small amount of spectral leakage.
//
// 2. Each bin can get their own settings that are best for it
//
//    I can individually control the window length (which doesn't
//    have to be a power of two like FFT) of each bin, to keep
//    a good balance between temporal and pitch resolution across
//    the frequency range. This also helps with speed, as the
//    higher frequencies require smaller window lengths and thus
//    have less work to do solving the magnitudes than the lower
//    frequencies.
//
//
// This GDFT method, which operates on a sliding window with 256
// new samples per frame, (i2s_audio.h) combined with a shitload
// of interesting post-processing methods I've documented below
// are what's behind the eye-catching shows on K1!
//
// If you like that I've shared this code, *please* support my work
// by purchasing genuine hardware or telling your friends about it!
//
// https://github.com/sponsors/connornishijima
// LIXIE LABS

// ----------------------------------------------------------------------------
// Phase A · Lane 1 GDFT decomposition (2026-06-23):
// process_GDFT() and calculate_novelty() were lifted WHOLE & VERBATIM out of
// this header into a real translation unit, audio/k1_gdft_core.cpp, so the
// spectrum tap can be host-compiled + golden-locked and the int64 overflow fix
// becomes host-deterministic. This header is now a thin shim that keeps the
// `.ino`'s existing `#include "GDFT.h"` include path working — the function
// DECLARATIONS arrive via k1_gdft_core.h, the DEFINITIONS live in the .cpp TU.
// Extraction contract: docs/architecture/gdft-decomposition-lane.md.
// ----------------------------------------------------------------------------
#include "k1_gdft_core.h"

#endif // GDFT_H
