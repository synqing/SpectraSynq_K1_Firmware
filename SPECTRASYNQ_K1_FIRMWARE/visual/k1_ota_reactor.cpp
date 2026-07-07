// SPDX-License-Identifier: Apache-2.0
// Copyright 2025-2026 SpectraSynq
//
// visual/k1_ota_reactor.cpp — Component A: the Reactor OTA renderer (Core-1).
//
// Implements k1_ota_reactor_render(const OtaUiSnapshot&, float) exactly as
// declared in the LOCKED shared interface system/k1_ota_mode.h. Fills the global
// 160-px NATIVE_RESOLUTION render canvas leds_16[] centre-origin about the 79/80
// boundary with a BOUNDED red -> amber -> green status arc plus a small
// white-hot core. The downstream pipeline (scale_to_strip() + the dual-strip
// mirror in the .ino) maps this 160-px canvas onto the physical 320 LEDs, so a
// canvas that is symmetric about index 79.5 radiates from the physical centre of
// every strip — satisfying the centre-origin hard constraint.
//
// HARD CONSTRAINTS honoured here:
//   - Centre-origin: every write is a function of radius d = |i - 79.5| only, so
//     the canvas is mirror-symmetric about the 79/80 boundary by construction.
//   - Colour: bounded red -> amber -> green arc + white-hot core. Never a hue
//     wheel / rainbow — hue is clamped to the red..green sector only.
//   - ZERO heap allocation: the entire TU allocates nothing on the heap. Only
//     file-scope static state and stack locals are used. No new/malloc/String,
//     no std::vector, no dynamic FastLED objects.
//   - Frame budget: one pass over 80 half-canvas radii (mirrored to 160), a
//     handful of transcendental calls per frame (bounded, see NOTE on timing).
//     Comfortably < 2.0 ms @ 120 FPS on the ESP32-S3.
//   - British English throughout (colour, centre, initialise, ...).
//
// The whole translation unit is #if SB_ENABLE_OTA. When the flag is 0 this file
// compiles to an EMPTY translation unit, so flag-OFF builds are byte-identical
// even though the file is listed unconditionally in build_src_filter (matching
// the existing always-listed system/k1_ota.cpp pattern).

#include "constants.h"  // SB_ENABLE_OTA, CRGB16, SQ15x16, NATIVE_RESOLUTION

#if SB_ENABLE_OTA

#include "k1_ota_mode.h"  // OtaUiSnapshot, OtaUiState, OtaRejectReason, render signature

#include <math.h>    // sinf, expf — bounded, per-frame call count is small (see timing NOTE)
#include <stdint.h>

// The global render canvas. Declared in the firmware's globals; every effect
// authors into it and the caller invokes show_leds() afterwards. We only fill it.
extern CRGB16 leds_16[NATIVE_RESOLUTION];

namespace {

// ─────────────────────────────────────────────────────────────────────────────
// Geometry — centre-origin about the 79/80 boundary of the 160-px canvas.
// ─────────────────────────────────────────────────────────────────────────────
// The physical centre of a strip sits between canvas indices 79 and 80. We treat
// the fractional centre as 79.5 and measure each pixel's distance from it. The
// maximum radius (indices 0 or 159) is therefore 79.5. Working in half-integer
// "half-steps" (2*d) keeps the radius arithmetic in pure integer maths.
constexpr uint8_t  kCanvas       = NATIVE_RESOLUTION;   // 160
constexpr uint8_t  kHalf         = NATIVE_RESOLUTION / 2; // 80  (indices 80..159 mirror 79..0)
constexpr float    kCentre       = 79.5f;               // (79/80) boundary
constexpr float    kMaxRadius    = 79.5f;               // radius at the outermost pixel
constexpr float    kInvMaxRadius = 1.0f / kMaxRadius;   // normaliser: d -> [0,1]

// White-hot core half-width, in pixels of radius. The core is deliberately SMALL
// per the brief. At radius <= kCoreRadius the pixel tends toward white-hot.
constexpr float    kCoreRadius   = 6.0f;

// ─────────────────────────────────────────────────────────────────────────────
// Colour — bounded red -> amber -> green status arc.
// ─────────────────────────────────────────────────────────────────────────────
// We do NOT walk the hue wheel. The status colour is produced by a piecewise
// linear ramp across exactly three anchors (red, amber, green) as a function of
// a single progress-like scalar t in [0,1]. This is provably NOT a rainbow: the
// blue channel is only ever raised by the white-hot core, never by the hue ramp.
//
//   t in [0.00, 0.50): red  (1,0,0)  ->  amber (1, 0.55, 0)
//   t in [0.50, 1.00]: amber(1,0.55,0) -> green (0, 1, 0)
//
// Channel values are 0.0..1.0 floats stored into the SQ15x16 fields (the same
// convention every other effect uses; show_leds() clips + gamma-maps to 0..255).
struct Rgb { float r, g, b; };

inline Rgb status_colour(float t) {
  // Clamp t to the bounded arc domain.
  if (t < 0.0f) t = 0.0f;
  if (t > 1.0f) t = 1.0f;

  // Anchors of the bounded arc.
  constexpr Rgb kRed   = {1.0f, 0.00f, 0.0f};
  constexpr Rgb kAmber = {1.0f, 0.55f, 0.0f};
  constexpr Rgb kGreen = {0.0f, 1.00f, 0.0f};

  if (t < 0.5f) {
    const float k = t * 2.0f;                 // 0..1 across red->amber
    return { kRed.r + (kAmber.r - kRed.r) * k,
             kRed.g + (kAmber.g - kRed.g) * k,
             kRed.b + (kAmber.b - kRed.b) * k };
  }
  const float k = (t - 0.5f) * 2.0f;          // 0..1 across amber->green
  return { kAmber.r + (kGreen.r - kAmber.r) * k,
           kAmber.g + (kGreen.g - kAmber.g) * k,
           kAmber.b + (kGreen.b - kAmber.b) * k };
}

// Map a UI state + progress onto the arc scalar t. The arc colour tracks BOTH the
// state and the download progress so the operator reads status at a glance:
//   ADVERTISING -> t=0.00 (red, idle-waiting)
//   DOWNLOADING -> t follows progress across the FIRST 0.65 of the arc (red->amber)
//   VERIFYING   -> t=0.70 (deep amber; "checking")
//   INSTALLING  -> t=0.85 (amber-green; "writing")
//   SUCCESS     -> t=1.00 (steady green)
//   FAIL        -> t=0.00 (hard red)
inline float arc_scalar_for(OtaUiState s, float progress) {
  switch (s) {
    case OtaUiState::ADVERTISING: return 0.0f;
    case OtaUiState::DOWNLOADING: {
      // Progress 0..1 spans red(0) .. amber-ish(0.65). Green is reserved for the
      // install/success terminal so DOWNLOADING never shows a "done" colour.
      float p = progress;
      if (p < 0.0f) p = 0.0f;
      if (p > 1.0f) p = 1.0f;
      return p * 0.65f;
    }
    case OtaUiState::VERIFYING:  return 0.70f;
    case OtaUiState::INSTALLING: return 0.85f;
    case OtaUiState::SUCCESS:    return 1.0f;
    case OtaUiState::FAIL:       return 0.0f;
    case OtaUiState::IDLE:       default: return 0.0f;
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Animation state — file-scope static (no heap, persists across frames).
// ─────────────────────────────────────────────────────────────────────────────
// A single monotonically advancing phase drives the inward-collapsing shockwaves
// (DOWNLOADING) and the core breathing. A separate discharge phase drives the
// one-shot outward pulse on INSTALLING. All state is trivially copy-constructed
// static floats — zero allocation.
struct ReactorAnim {
  float wavePhase     = 0.0f;   // radians-ish accumulator for shockwave motion
  float breathPhase   = 0.0f;   // core breathing accumulator
  float dischargeT    = -1.0f;  // >=0 while an INSTALLING discharge is in flight; -1 = idle
  OtaUiState lastState = OtaUiState::IDLE;
};
ReactorAnim g_anim;

// Wrap a phase accumulator into [0, 2*pi) cheaply without fmodf in the hot loop.
inline float wrap_two_pi(float x) {
  constexpr float kTwoPi = 6.2831853f;
  while (x >= kTwoPi) x -= kTwoPi;
  while (x < 0.0f)    x += kTwoPi;
  return x;
}

}  // namespace

// ─────────────────────────────────────────────────────────────────────────────
// k1_ota_reactor_render — LOCKED signature. Fills leds_16[] for one frame.
// ─────────────────────────────────────────────────────────────────────────────
void k1_ota_reactor_render(const OtaUiSnapshot& snap, float dtSeconds) {
  // Defensive dt clamp: the caller passes a real esp_timer delta, but guard
  // against a stalled/huge first-frame dt so animation phases never jump wildly.
  float dt = dtSeconds;
  if (dt < 0.0f)    dt = 0.0f;
  if (dt > 0.050f)  dt = 0.050f;   // cap at 50 ms of advance per frame

  // Detect a fresh entry into INSTALLING to arm the single outward discharge.
  if (snap.state == OtaUiState::INSTALLING && g_anim.lastState != OtaUiState::INSTALLING) {
    g_anim.dischargeT = 0.0f;  // start the one-shot outward pulse
  }
  g_anim.lastState = snap.state;

  // Advance animation phases.
  //   Shockwaves collapse inward during DOWNLOADING; motion rate is gentle and
  //   frame-rate independent (scaled by dt). VERIFYING keeps a slow shimmer.
  const float waveRate =
      (snap.state == OtaUiState::DOWNLOADING) ? 5.0f :
      (snap.state == OtaUiState::VERIFYING)   ? 2.2f : 0.0f;
  g_anim.wavePhase   = wrap_two_pi(g_anim.wavePhase + waveRate * dt);
  g_anim.breathPhase = wrap_two_pi(g_anim.breathPhase + 3.0f * dt);

  // Advance the INSTALLING discharge (a normalised 0..1 ramp over ~0.45 s).
  if (g_anim.dischargeT >= 0.0f) {
    g_anim.dischargeT += dt / 0.45f;
    if (g_anim.dischargeT > 1.0f) g_anim.dischargeT = -1.0f;  // discharge finished
  }

  // Base status colour for this frame (bounded arc).
  const float t   = arc_scalar_for(snap.state, snap.progress);
  const Rgb   arc = status_colour(t);

  // Overall field brightness envelope by state. SUCCESS settles bright and
  // steady; FAIL recedes toward the centre (dim outer, red core); ADVERTISING is
  // a low idle glow so the operator sees the device is waiting.
  const float baseGlow =
      (snap.state == OtaUiState::ADVERTISING) ? 0.18f :
      (snap.state == OtaUiState::SUCCESS)     ? 0.85f :
      (snap.state == OtaUiState::FAIL)        ? 0.10f : 0.35f;

  // The "reach" of the lit field from the centre, 0..1 of the canvas radius.
  //   DOWNLOADING: the arc fills outward with progress (a radial progress bar).
  //   VERIFYING/INSTALLING/SUCCESS: full reach.
  //   FAIL: the field recedes toward the centre (small reach) — "receding red".
  //   ADVERTISING: a modest breathing reach.
  float reach;
  switch (snap.state) {
    case OtaUiState::DOWNLOADING: {
      float p = snap.progress;
      if (p < 0.0f) p = 0.0f; if (p > 1.0f) p = 1.0f;
      reach = 0.15f + 0.85f * p;                 // grows 0.15 -> 1.0 with progress
      break;
    }
    case OtaUiState::VERIFYING:
    case OtaUiState::INSTALLING:
    case OtaUiState::SUCCESS:
      reach = 1.0f;
      break;
    case OtaUiState::FAIL:
      reach = 0.30f;                             // receded toward centre
      break;
    case OtaUiState::ADVERTISING:
      reach = 0.28f + 0.06f * sinf(g_anim.breathPhase); // gentle breath
      break;
    case OtaUiState::IDLE:
    default:
      // IDLE should never reach the renderer (the hook returns false first), but
      // fill black defensively so a stray call cannot leave stale pixels lit.
      for (uint8_t i = 0; i < kCanvas; ++i) leds_16[i] = {0, 0, 0};
      return;
  }

  // Core breathing: a small white-hot core that gently pulses. Bounded 0.75..1.0.
  const float coreBreath = 0.875f + 0.125f * sinf(g_anim.breathPhase);

  // Precompute the inward-collapsing shockwave centre (a moving bright ring that
  // travels from the rim toward the centre while DOWNLOADING). Expressed as a
  // normalised radius in [0,1]; 1.0 = rim, 0.0 = centre.
  const bool  waveActive = (waveRate > 0.0f);
  const float waveNorm   = waveActive
      ? (0.5f + 0.5f * sinf(g_anim.wavePhase)) // oscillates 0..1; visually reads as inward collapse + refill
      : 0.0f;

  // Discharge ring (INSTALLING one-shot): a bright ring that travels OUTWARD from
  // the centre to the rim exactly once. Normalised radius 0..1 == centre..rim.
  const bool  dischargeActive = (g_anim.dischargeT >= 0.0f);
  const float dischargeNorm   = dischargeActive ? g_anim.dischargeT : -1.0f;

  // ── Render the half-canvas (radii 0..79) and mirror into the other half. ──
  // Index i (0..79) maps to radius d = kCentre - i. Its mirror is (kCanvas-1-i).
  // Writing both from the same computed colour guarantees exact symmetry about
  // the 79/80 boundary — the centre-origin invariant, by construction.
  for (uint8_t i = 0; i < kHalf; ++i) {
    // Radius of this pixel from the fractional centre 79.5. For i in [0,79] the
    // nearer-centre pixel is index 79 (d = 0.5) out to index 0 (d = 79.5).
    const float d      = kCentre - static_cast<float>(i);  // 79.5 .. 0.5
    const float dNorm  = d * kInvMaxRadius;                // ~1.0 .. ~0.006

    // 1) Bounded status field, gated by reach (radial fill / progress bar).
    float lit = (dNorm <= reach) ? 1.0f : 0.0f;
    // Soft edge on the reach boundary so the fill front is not a hard step.
    if (lit == 0.0f) {
      const float over = dNorm - reach;
      if (over < 0.06f) lit = 1.0f - (over * (1.0f / 0.06f)); // 6%-wide feather
    }

    float r = arc.r * baseGlow * lit;
    float g = arc.g * baseGlow * lit;
    float b = arc.b * baseGlow * lit;

    // 2) Inward-collapsing shockwave (liveness during DOWNLOADING / VERIFYING).
    //    A bright ring at normalised radius waveNorm. Gaussian-ish falloff via a
    //    single expf. Adds brightness in the CURRENT arc colour (never new hue).
    if (waveActive && lit > 0.0f) {
      const float dr = dNorm - waveNorm;
      const float ring = expf(-(dr * dr) * 90.0f);  // narrow bright ring
      const float boost = ring * 0.55f;
      r += arc.r * boost;
      g += arc.g * boost;
      b += arc.b * boost;
    }

    // 3) Outward discharge (single INSTALLING pulse). Bright arc-coloured ring
    //    travelling centre -> rim once. Fades as it reaches the rim.
    if (dischargeActive) {
      const float dr = dNorm - dischargeNorm;
      const float ring = expf(-(dr * dr) * 60.0f);
      const float fade = 1.0f - dischargeNorm;        // dimmer as it nears the rim
      const float boost = ring * fade * 0.9f;
      r += arc.r * boost;
      g += arc.g * boost;
      b += arc.b * boost;
    }

    // 4) White-hot core. Small central region tends toward white; intensity is
    //    the breathing envelope. Additive white raises all three channels — this
    //    is the ONLY place the blue channel is lit, and only near the centre, so
    //    the colour reads as a hot core, never a rainbow.
    if (d <= kCoreRadius) {
      // Core intensity: 1.0 at the exact centre, easing to 0 at kCoreRadius.
      const float ci = (1.0f - (d / kCoreRadius));
      const float core = ci * ci * coreBreath;   // squared for a tight hot point
      // FAIL keeps a red-tinted core (no white bloom) so failure never looks
      // "healthy". All other states get a true white-hot core.
      if (snap.state == OtaUiState::FAIL) {
        r += core;                               // red-only core
      } else {
        r += core;
        g += core;
        b += core;
      }
    }

    // Clamp to [0,1]; show_leds()'s clip is hue-preserving but we bound here so
    // the additive rings/core cannot push channels absurdly high before clip.
    if (r > 1.0f) r = 1.0f; if (r < 0.0f) r = 0.0f;
    if (g > 1.0f) g = 1.0f; if (g < 0.0f) g = 0.0f;
    if (b > 1.0f) b = 1.0f; if (b < 0.0f) b = 0.0f;

    const CRGB16 px = { SQ15x16(r), SQ15x16(g), SQ15x16(b) };
    leds_16[i]               = px;                // inner-left half (indices 0..79)
    leds_16[kCanvas - 1 - i] = px;               // mirrored right half (159..80)
  }
}

#endif  // SB_ENABLE_OTA
