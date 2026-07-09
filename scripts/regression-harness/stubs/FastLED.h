// ============================================================================
// stubs/FastLED.h — HOST-ONLY curated FastLED colour subset for render_replay
// ============================================================================
// VE-Auto-Loop Tier-1 host harness (docs/prd/ve-auto-loop/01-render-replay-harness.md).
//
// WHY A CURATED STUB, NOT THE REAL FastLED:
//   FastLED 3.10.3 (the K1 pin) has migrated its colour types into the deeply
//   coupled `fl::` submodule; lib8tion.h #includes FastLED.h and #errors unless
//   led_sysdefs.h (platform detection -> SPI/clockless drivers) is included
//   first. Including the real colour headers therefore drags the whole platform
//   layer, which does not host-compile (PRD §3 #1). So we reproduce ONLY the
//   colour maths bloom's path needs.
//
// FIDELITY (R-SCALE8, and §11's [MECHANISM] reframe):
//   scale8 / scale8_video / hsv2rgb_rainbow / rgb2hsv_approximate are COPIED
//   VERBATIM from FastLED 3.10.3 (lib8tion/scale8.h SCALE8_C+FIXED path,
//   hsv2rgb.cpp). CRGBPalette16 gradient construction + ColorFromPalette use
//   FastLED's canonical LINEARBLEND algorithm, reproduced here. Per the §11
//   correction the host dump is a pre-gamma/pre-dither [MECHANISM] reduction:
//   byte LAYOUT matches VPABBytesPayload but VALUES are certified on-device
//   (Tier-2 vpab_capture), so ±1 LSB host-vs-device colour drift is by design.
//   Host-vs-host determinism (acceptance A2) holds regardless of LSB exactness.
//
// NON-SHIPPING. Reachable only under -DK1_RENDER_HOST_TEST via -I stubs.
// ============================================================================
#pragma once

#include <cstdint>
#include <cstring>
#include <cmath>
#include "Arduino.h"

typedef uint8_t  fract8;
typedef uint16_t fract16;
typedef int8_t   sfract7;

// FastLED named-hue anchors (lib8tion / pixeltypes)
#define K255 255
#define K171 171
#define K170 170
#define K85  85

// AVR-codegen helper macros -> no-ops on host
#ifndef FORCE_REFERENCE
#define FORCE_REFERENCE(x) ((void)(x))
#endif
#ifndef LIB8STATIC
#define LIB8STATIC static inline
#endif

// ---------------------------------------------------------------------------
// lib8tion: scale8 family (VERBATIM, SCALE8_C==1 && FASTLED_SCALE8_FIXED==1)
// ---------------------------------------------------------------------------
LIB8STATIC uint8_t scale8(uint8_t i, fract8 scale) {
  return (((uint16_t)i) * (1 + (uint16_t)(scale))) >> 8;
}
LIB8STATIC uint8_t scale8_video(uint8_t i, fract8 scale) {
  return (((int)i * (int)scale) >> 8) + ((i && scale) ? 1 : 0);
}
// On non-AVR the "_LEAVING_R1_DIRTY" variants and cleanup_R1() are plain.
LIB8STATIC uint8_t scale8_LEAVING_R1_DIRTY(uint8_t i, fract8 scale) { return scale8(i, scale); }
LIB8STATIC uint8_t scale8_video_LEAVING_R1_DIRTY(uint8_t i, fract8 scale) { return scale8_video(i, scale); }
LIB8STATIC void cleanup_R1() {}

LIB8STATIC uint8_t qadd8(uint8_t i, uint8_t j) { int t = i + j; return t > 255 ? 255 : (uint8_t)t; }
LIB8STATIC uint8_t qsub8(uint8_t i, uint8_t j) { int t = i - j; return t < 0 ? 0 : (uint8_t)t; }
LIB8STATIC uint8_t qadd7(int8_t i, int8_t j)   { int t = i + j; return t > 127 ? 127 : (uint8_t)t; }
LIB8STATIC uint8_t qmul8(uint8_t i, uint8_t j) { int p = (int)i * (int)j; return p > 255 ? 255 : (uint8_t)p; }
LIB8STATIC uint8_t add8(uint8_t i, uint8_t j)  { return (uint8_t)(i + j); }
LIB8STATIC uint8_t sub8(uint8_t i, uint8_t j)  { return (uint8_t)(i - j); }
LIB8STATIC uint8_t lerp8by8(uint8_t a, uint8_t b, fract8 frac) {
  if (b > a) return a + scale8(b - a, frac);
  return a - scale8(a - b, frac);
}
LIB8STATIC uint8_t blend8(uint8_t a, uint8_t b, uint8_t amountOfB) {
  uint16_t partial = (a << 8) | a;          // a*257
  partial += (int16_t)(scale8(b, amountOfB)) * 256;
  partial -= (int16_t)(scale8(a, amountOfB)) * 256;
  return partial >> 8;
}
LIB8STATIC uint8_t map8(uint8_t in, uint8_t rangeStart, uint8_t rangeEnd) {
  uint8_t rangeWidth = rangeEnd - rangeStart;
  uint8_t out = scale8(in, rangeWidth);
  out += rangeStart;
  return out;
}
LIB8STATIC uint8_t ease8InOutQuad(uint8_t i) {
  uint8_t j = i; if (j & 0x80) j = 255 - j;
  uint8_t jj = scale8(j, j); uint8_t jj2 = jj << 1;
  if (i & 0x80) jj2 = 255 - jj2;
  return jj2;
}

// FastLED canonical integer sqrt (lib8tion math8.h)
LIB8STATIC uint8_t sqrt16(uint16_t x) {
  if (x <= 1) return (uint8_t)x;
  uint8_t low = 1, hi, mid;
  if (x > 7904) hi = 255; else hi = (uint8_t)(std::sqrt((float)x)) + 1;
  do {
    mid = (uint8_t)((low + hi) >> 1);
    if ((uint16_t)(mid * mid) > x) { hi = mid - 1; }
    else { if (mid == 255) return 255; low = mid + 1; }
  } while (hi >= low);
  return low - 1;
}

// ---------------------------------------------------------------------------
// CHSV / HSVHue
// ---------------------------------------------------------------------------
typedef enum {
  HUE_RED = 0, HUE_ORANGE = 32, HUE_YELLOW = 64, HUE_GREEN = 96,
  HUE_AQUA = 128, HUE_BLUE = 160, HUE_PURPLE = 192, HUE_PINK = 224
} HSVHue;

struct CHSV {
  union { struct { uint8_t h; uint8_t s; uint8_t v; }; struct { uint8_t hue; uint8_t sat; uint8_t val; }; uint8_t raw[3]; };
  inline CHSV() {}
  inline CHSV(uint8_t ih, uint8_t is, uint8_t iv) : h(ih), s(is), v(iv) {}
  inline CHSV(const CHSV& rhs) { h = rhs.h; s = rhs.s; v = rhs.v; }
  inline CHSV& operator=(const CHSV& rhs) { h = rhs.h; s = rhs.s; v = rhs.v; return *this; }
  inline CHSV& setHSV(uint8_t ih, uint8_t is, uint8_t iv) { h = ih; s = is; v = iv; return *this; }
  inline uint8_t& operator[](uint8_t x) { return raw[x]; }
};

struct CRGB;
void hsv2rgb_rainbow(const CHSV& hsv, CRGB& rgb);
CHSV rgb2hsv_approximate(const CRGB& rgb);

// ---------------------------------------------------------------------------
// CRGB
// ---------------------------------------------------------------------------
struct CRGB {
  union { struct { uint8_t r; uint8_t g; uint8_t b; }; struct { uint8_t red; uint8_t green; uint8_t blue; }; uint8_t raw[3]; };

  inline CRGB() : r(0), g(0), b(0) {}
  inline CRGB(uint8_t ir, uint8_t ig, uint8_t ib) : r(ir), g(ig), b(ib) {}
  inline CRGB(uint32_t colorcode) : r((colorcode >> 16) & 0xFF), g((colorcode >> 8) & 0xFF), b(colorcode & 0xFF) {}
  inline CRGB(const CHSV& rhs) { hsv2rgb_rainbow(rhs, *this); }
  // Copy ctor / copy-assign left implicit (trivial) so CRGB stays trivially
  // copyable — matches FastLED and lets memset/memcpy on CRGB[] stay warning-free.
  inline CRGB& operator=(const CHSV& rhs) { hsv2rgb_rainbow(rhs, *this); return *this; }
  inline CRGB& setRGB(uint8_t nr, uint8_t ng, uint8_t nb) { r = nr; g = ng; b = nb; return *this; }
  inline CRGB& setHSV(uint8_t hue, uint8_t sat, uint8_t val) { hsv2rgb_rainbow(CHSV(hue, sat, val), *this); return *this; }

  inline uint8_t& operator[](uint8_t x) { return raw[x]; }
  inline const uint8_t& operator[](uint8_t x) const { return raw[x]; }

  inline CRGB& operator+=(const CRGB& rhs) { r = qadd8(r, rhs.r); g = qadd8(g, rhs.g); b = qadd8(b, rhs.b); return *this; }
  inline CRGB& operator-=(const CRGB& rhs) { r = qsub8(r, rhs.r); g = qsub8(g, rhs.g); b = qsub8(b, rhs.b); return *this; }
  inline CRGB& operator*=(uint8_t d)       { r = qmul8(r, d); g = qmul8(g, d); b = qmul8(b, d); return *this; }
  inline CRGB& nscale8(uint8_t sc)         { r = scale8(r, sc); g = scale8(g, sc); b = scale8(b, sc); return *this; }
  inline CRGB& nscale8_video(uint8_t sc)   { r = scale8_video(r, sc); g = scale8_video(g, sc); b = scale8_video(b, sc); return *this; }
  inline CRGB& operator%=(uint8_t sc)      { return nscale8_video(sc); }
  inline CRGB& fadeToBlackBy(uint8_t fade) { return nscale8(255 - fade); }
  inline CRGB& setColorCode(uint32_t c)    { r = (c >> 16) & 0xFF; g = (c >> 8) & 0xFF; b = c & 0xFF; return *this; }
  inline uint8_t getLuma() const           { return scale8(r, 54) + scale8(g, 183) + scale8(b, 18); }
  inline uint8_t getAverageLight() const   { return (r + r + r + g + g + g + g + b) >> 3; }
  inline explicit operator bool() const    { return r || g || b; }

  // FastLED HTML named-colour codes (firmware uses CRGB::Black; rest for parity)
  enum HTMLColorCode {
    Black = 0x000000, White = 0xFFFFFF, Red = 0xFF0000, Green = 0x008000,
    Blue = 0x0000FF, Yellow = 0xFFFF00, Cyan = 0x00FFFF, Magenta = 0xFF00FF,
    Orange = 0xFFA500, Purple = 0x800080, Pink = 0xFFC0CB, Gray = 0x808080
  };
};

inline bool operator==(const CRGB& a, const CRGB& b) { return a.r == b.r && a.g == b.g && a.b == b.b; }
inline bool operator!=(const CRGB& a, const CRGB& b) { return !(a == b); }
inline CRGB operator+(const CRGB& a, const CRGB& b) { return CRGB(qadd8(a.r, b.r), qadd8(a.g, b.g), qadd8(a.b, b.b)); }
inline CRGB operator-(const CRGB& a, const CRGB& b) { return CRGB(qsub8(a.r, b.r), qsub8(a.g, b.g), qsub8(a.b, b.b)); }

// nblend / blend / fill_solid (parsed by led_utilities inline funcs)
inline CRGB& nblend(CRGB& existing, const CRGB& overlay, fract8 amountOfOverlay) {
  if (amountOfOverlay == 0) return existing;
  if (amountOfOverlay == 255) { existing = overlay; return existing; }
  existing.r = blend8(existing.r, overlay.r, amountOfOverlay);
  existing.g = blend8(existing.g, overlay.g, amountOfOverlay);
  existing.b = blend8(existing.b, overlay.b, amountOfOverlay);
  return existing;
}
inline CRGB blend(const CRGB& p1, const CRGB& p2, fract8 amountOfP2) {
  CRGB nu(p1); nblend(nu, p2, amountOfP2); return nu;
}
inline void fill_solid(CRGB* leds, int num, const CRGB& color) { for (int i = 0; i < num; i++) leds[i] = color; }
inline void fill_solid(struct CRGB* leds, int num, const CHSV& color) { CRGB c(color); for (int i = 0; i < num; i++) leds[i] = c; }

// ---------------------------------------------------------------------------
// Gradient palettes (CRGBPalette16 + ColorFromPalette, canonical LINEARBLEND)
// ---------------------------------------------------------------------------
typedef enum { NOBLEND = 0, LINEARBLEND = 1, LINEARBLEND_NOWRAP = 2 } TBlendType;

typedef uint8_t        TProgmemRGBGradientPalette_byte;
typedef const uint8_t* TProgmemRGBGradientPalette_bytes;
typedef TProgmemRGBGradientPalette_bytes TProgmemRGBGradientPaletteRef;
typedef const uint32_t TProgmemRGBPalette16[16];

// Match FastLED's gradient-palette macros. BOTH carry `extern` so the arrays
// get EXTERNAL linkage — without it a namespace-scope `const` array is internal
// to Palettes.cpp and bloom's TU can't resolve gGradientPalettes[i]'s targets.
#define DECLARE_GRADIENT_PALETTE(X) extern const TProgmemRGBGradientPalette_byte X[] FL_PROGMEM
#define DEFINE_GRADIENT_PALETTE(X)  extern const TProgmemRGBGradientPalette_byte X[] FL_PROGMEM =

// Linear RGB gradient fill between two palette slots (inclusive).
inline void fill_gradient_RGB(CRGB* entries, uint16_t startpos, CRGB startcolor,
                              uint16_t endpos, CRGB endcolor) {
  if (endpos < startpos) { uint16_t ts = startpos; CRGB tc = startcolor; startpos = endpos; startcolor = endcolor; endpos = ts; endcolor = tc; }
  int16_t rdistance = (int16_t)endcolor.r - (int16_t)startcolor.r;
  int16_t gdistance = (int16_t)endcolor.g - (int16_t)startcolor.g;
  int16_t bdistance = (int16_t)endcolor.b - (int16_t)startcolor.b;
  int16_t divisor = (int16_t)endpos - (int16_t)startpos;
  if (divisor == 0) { entries[startpos] = startcolor; return; }
  // <<7 fixed-point accumulators (FastLED saccum87 form)
  int16_t rdelta87 = (rdistance << 7) / divisor;
  int16_t gdelta87 = (gdistance << 7) / divisor;
  int16_t bdelta87 = (bdistance << 7) / divisor;
  int16_t r88 = startcolor.r << 7, g88 = startcolor.g << 7, b88 = startcolor.b << 7;
  for (uint16_t i = startpos; i <= endpos; i++) {
    entries[i] = CRGB((uint8_t)(r88 >> 7), (uint8_t)(g88 >> 7), (uint8_t)(b88 >> 7));
    r88 += rdelta87; g88 += gdelta87; b88 += bdelta87;
  }
}

class CRGBPalette16 {
 public:
  CRGB entries[16];
  CRGBPalette16() { for (int i = 0; i < 16; i++) entries[i] = CRGB(0, 0, 0); }
  CRGBPalette16(const CRGB& c) { for (int i = 0; i < 16; i++) entries[i] = c; }
  CRGBPalette16(const CRGBPalette16& rhs) { for (int i = 0; i < 16; i++) entries[i] = rhs.entries[i]; }
  CRGBPalette16& operator=(const CRGBPalette16& rhs) { for (int i = 0; i < 16; i++) entries[i] = rhs.entries[i]; return *this; }

  // Build from a FastLED gradient-palette byte stream: groups of {index,R,G,B},
  // index ascending in 0..255, terminated by an entry with index==255.
  CRGBPalette16(TProgmemRGBGradientPalette_bytes progpal) { *this = progpal; }
  CRGBPalette16& operator=(TProgmemRGBGradientPalette_bytes progpal) {
    const uint8_t* p = progpal;
    // count stops (until index byte == 255)
    uint16_t count = 0; { const uint8_t* q = p; do { uint8_t idx = q[0]; q += 4; ++count; if (idx == 255) break; } while (count < 256); }
    int8_t lastSlotUsed = -1;
    CRGB rgbstart(p[1], p[2], p[3]);
    int indexstart = 0;
    while (indexstart < 255) {
      p += 4;
      int indexend = p[0];
      CRGB rgbend(p[1], p[2], p[3]);
      uint16_t istart8 = indexstart / 16;
      uint16_t iend8   = indexend / 16;
      if (count < 16) {
        if ((istart8 <= (uint16_t)lastSlotUsed) && (lastSlotUsed < 15)) { istart8 = lastSlotUsed + 1; if (iend8 < istart8) iend8 = istart8; }
        lastSlotUsed = (int8_t)iend8;
      }
      fill_gradient_RGB(&(entries[0]), istart8, rgbstart, iend8, rgbend);
      indexstart = indexend; rgbstart = rgbend;
    }
    return *this;
  }

  inline CRGB& operator[](uint8_t x) { return entries[x]; }
  inline const CRGB& operator[](uint8_t x) const { return entries[x]; }
};

// Canonical LINEARBLEND ColorFromPalette (16-entry palette).
inline CRGB ColorFromPalette(const CRGBPalette16& pal, uint8_t index,
                             uint8_t brightness = 255, TBlendType blendType = LINEARBLEND) {
  if (blendType == LINEARBLEND_NOWRAP) index = map8(index, 0, 239);
  uint8_t hi4 = index >> 4;
  uint8_t lo4 = index & 0x0F;
  CRGB entry = pal[hi4];
  uint8_t red1 = entry.r, green1 = entry.g, blue1 = entry.b;
  bool blend = lo4 && (blendType != NOBLEND);
  if (blend) {
    CRGB entry2 = (hi4 == 15) ? pal[0] : pal[hi4 + 1];
    uint8_t f2 = lo4 << 4;
    uint8_t f1 = 255 - f2;
    red1   = scale8(red1, f1)   + scale8(entry2.r, f2);
    green1 = scale8(green1, f1) + scale8(entry2.g, f2);
    blue1  = scale8(blue1, f1)  + scale8(entry2.b, f2);
  }
  if (brightness != 255) {
    if (brightness) {
      uint8_t br = brightness + 1;
      red1 = scale8(red1, br); green1 = scale8(green1, br); blue1 = scale8(blue1, br);
    } else { red1 = green1 = blue1 = 0; }
  }
  return CRGB(red1, green1, blue1);
}

// ---------------------------------------------------------------------------
// hsv2rgb_rainbow / rgb2hsv_approximate (VERBATIM from FastLED 3.10.3)
// ---------------------------------------------------------------------------
inline void hsv2rgb_rainbow(const CHSV& hsv, CRGB& rgb) {
  const uint8_t Y1 = 1, Y2 = 0, G2 = 0, Gscale = 0;
  uint8_t hue = hsv.hue, sat = hsv.sat, val = hsv.val;
  uint8_t offset = hue & 0x1F;            // 0..31
  uint8_t offset8 = offset << 3;          // non-AVR path
  uint8_t third = scale8(offset8, (256 / 3));
  uint8_t r, g, b;
  if (!(hue & 0x80)) {
    if (!(hue & 0x40)) {
      if (!(hue & 0x20)) { r = K255 - third; g = third; b = 0; FORCE_REFERENCE(b); }
      else {
        if (Y1) { r = K171; g = K85 + third; b = 0; FORCE_REFERENCE(b); }
        if (Y2) { r = K170 + third; uint8_t tt = scale8(offset8, ((256 * 2) / 3)); g = K85 + tt; b = 0; FORCE_REFERENCE(b); }
      }
    } else {
      if (!(hue & 0x20)) {
        if (Y1) { uint8_t tt = scale8(offset8, ((256 * 2) / 3)); r = K171 - tt; g = K170 + third; b = 0; FORCE_REFERENCE(b); }
        if (Y2) { r = K255 - offset8; g = K255; b = 0; FORCE_REFERENCE(b); }
      } else { r = 0; FORCE_REFERENCE(r); g = K255 - third; b = third; }
    }
  } else {
    if (!(hue & 0x40)) {
      if (!(hue & 0x20)) { r = 0; FORCE_REFERENCE(r); uint8_t tt = scale8(offset8, ((256 * 2) / 3)); g = K171 - tt; b = K85 + tt; }
      else { r = third; g = 0; FORCE_REFERENCE(g); b = K255 - third; }
    } else {
      if (!(hue & 0x20)) { r = K85 + third; g = 0; FORCE_REFERENCE(g); b = K171 - third; }
      else { r = K170 + third; g = 0; FORCE_REFERENCE(g); b = K85 - third; }
    }
  }
  if (G2) g = g >> 1;
  if (Gscale) g = scale8_video(g, Gscale);
  if (sat != 255) {
    if (sat == 0) { r = 255; b = 255; g = 255; }
    else {
      uint8_t desat = 255 - sat; desat = scale8_video(desat, desat);
      uint8_t satscale = 255 - desat;
      // FASTLED_SCALE8_FIXED==1 path (3.10.3 default): scale8_LEAVING_R1_DIRTY +
      // cleanup_R1() == plain scale8 on host (NO inline +1; the +1 is an AVR R1
      // micro-opt). Using the non-FIXED "+1" form here overflows r at 253+floor.
      r = scale8(r, satscale); g = scale8(g, satscale); b = scale8(b, satscale);
      uint8_t brightness_floor = desat; r += brightness_floor; g += brightness_floor; b += brightness_floor;
    }
  }
  if (val != 255) {
    val = scale8_video(val, val);
    if (val == 0) { r = 0; g = 0; b = 0; }
    else { r = scale8(r, val); g = scale8(g, val); b = scale8(b, val); }
  }
  rgb.r = r; rgb.g = g; rgb.b = b;
}

#define FIXFRAC8(N, D) (((N) * 256) / (D))
inline CHSV rgb2hsv_approximate(const CRGB& rgb) {
  uint8_t r = rgb.r, g = rgb.g, b = rgb.b, h, s, v;
  uint8_t desat = 255;
  if (r < desat) desat = r;
  if (g < desat) desat = g;
  if (b < desat) desat = b;
  r -= desat; g -= desat; b -= desat;
  s = 255 - desat;
  if (s != 255) s = 255 - sqrt16((255 - s) * 256);
  if ((r + g + b) == 0) return CHSV(0, 0, 255 - s);
  if (s < 255) {
    if (s == 0) s = 1;
    uint32_t scaleup = 65535 / (s);
    r = ((uint32_t)(r) * scaleup) / 256; g = ((uint32_t)(g) * scaleup) / 256; b = ((uint32_t)(b) * scaleup) / 256;
  }
  uint16_t total = r + g + b;
  if (total < 255) {
    if (total == 0) total = 1;
    uint32_t scaleup = 65535 / (total);
    r = ((uint32_t)(r) * scaleup) / 256; g = ((uint32_t)(g) * scaleup) / 256; b = ((uint32_t)(b) * scaleup) / 256;
  }
  if (total > 255) { v = 255; } else { v = qadd8(desat, total); if (v != 255) v = sqrt16(v * 256); }
  uint8_t highest = r; if (g > highest) highest = g; if (b > highest) highest = b;
  if (highest == r) {
    if (g == 0) { h = (HUE_PURPLE + HUE_PINK) / 2; h += scale8(qsub8(r, 128), FIXFRAC8(48, 128)); }
    else if ((r - g) > g) { h = HUE_RED; h += scale8(g, FIXFRAC8(32, 85)); }
    else { h = HUE_ORANGE; h += scale8(qsub8((g - 85) + (171 - r), 4), FIXFRAC8(32, 85)); }
  } else if (highest == g) {
    if (b == 0) { h = HUE_YELLOW; uint8_t radj = scale8(qsub8(171, r), 47); uint8_t gadj = scale8(qsub8(g, 171), 96); uint8_t rgadj = radj + gadj; h += rgadj / 2; }
    else { if ((g - b) > b) { h = HUE_GREEN; h += scale8(b, FIXFRAC8(32, 85)); } else { h = HUE_AQUA; h += scale8(qsub8(b, 85), FIXFRAC8(8, 42)); } }
  } else {
    if (r == 0) { h = HUE_AQUA + ((HUE_BLUE - HUE_AQUA) / 4); h += scale8(qsub8(b, 128), FIXFRAC8(24, 128)); }
    else if ((b - r) > r) { h = HUE_BLUE; h += scale8(r, FIXFRAC8(32, 85)); }
    else { h = HUE_PURPLE; h += scale8(qsub8(r, 85), FIXFRAC8(32, 85)); }
  }
  h += 1;
  return CHSV(h, s, v);
}

// hsv2rgb_spectrum / hsv2rgb_raw aliases (rare firmware paths) -> rainbow
inline void hsv2rgb_spectrum(const CHSV& hsv, CRGB& rgb) { hsv2rgb_rainbow(hsv, rgb); }

// ---------------------------------------------------------------------------
// CFastLED controller object (output stage) -> all no-ops on host
// ---------------------------------------------------------------------------
enum EDitherMode { DISABLE_DITHER = 0, BINARY_DITHER = 1 };
enum ESPIChipsets { WS2812B, WS2812, WS2811, SK6812, NEOPIXEL, APA102, DOTSTAR, LPD8806, SM16716 };
enum EOrder { RGB = 0012, RBG = 0021, GRB = 0102, GBR = 0120, BRG = 0201, BGR = 0210 };
typedef uint32_t TGradientDirectionCode;
#define TypicalLEDStrip 0xFFB0F0
#define UncorrectedColor 0xFFFFFF
#define TypicalSMD5050   0xFFB0F0

class CFastLED {
 public:
  // FastLED.addLeds<CHIPSET, DATA_PIN, RGB_ORDER>(leds, count) and the
  // 3-arg (leds, offset, count) form. Non-type params accept the chipset /
  // EOrder enum values as converted int constants. Output stage is a no-op.
  template <int CHIPSET, int DATA_PIN, int RGB_ORDER>
  CRGB* addLeds(CRGB* data, int nLeds) { (void)nLeds; return data; }
  template <int CHIPSET, int DATA_PIN, int RGB_ORDER>
  CRGB* addLeds(CRGB* data, int offset, int nLeds) { (void)offset; (void)nLeds; return data; }
  template <int CHIPSET, int DATA_PIN, int CLOCK_PIN, int RGB_ORDER>
  CRGB* addLeds(CRGB* data, int nLeds) { (void)nLeds; return data; }
  void show() {}
  void show(uint8_t) {}
  void clear(bool = false) {}
  void clearData() {}
  void showColor(const CRGB&) {}
  void setBrightness(uint8_t) {}
  uint8_t getBrightness() { return 255; }
  void setDither(uint8_t) {}
  void setCorrection(uint32_t) {}
  void setTemperature(uint32_t) {}
  void setMaxPowerInVoltsAndMilliamps(uint8_t, uint32_t) {}
  void setMaxRefreshRate(uint16_t) {}
  void delay(unsigned long) {}
  int size() { return 0; }
  CRGB* leds() { return nullptr; }
  int count() { return 0; }
};
extern CFastLED FastLED;

// EVERY_N_MILLISECONDS family (timed blocks) — degenerate to "run once per call"
// is wrong for device, but on host these blocks are in functions bloom doesn't
// call; define them to a never-taken branch so they only need to parse.
#define EVERY_N_MILLISECONDS(N) if (false)
#define EVERY_N_SECONDS(N) if (false)
#define EVERY_N_MILLIS(N) if (false)
