// K1 -> Pixelblaze :: Bloom (autonomous)
// Port of SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_bloom.cpp
//
// K1 identity preserved:
//  - Colour blooms from the centre and flows outward: previous frame scrolled by
//    (0.250 + 1.750*MOOD) px/frame @128px (scaled by pixelCount/128), trail alpha 0.88
//    (VP_FIX_BLOOM_DECAY), single centre-pixel insert per half, mirrored.
//  - Edge fade: quadratic over the outer quarter of the strip, DISPLAY-ONLY --
//    K1 snapshots history before the fade, so here it lives in render(), never
//    compounding into the buffer.
//  - Both colour authorities:
//    * Palette mode (default): one palette sample at the chromagram circular-centroid
//      hue (summing palette samples collapses gradients to grey -- K1 rule kept).
//    * Chromatic mode: classic Bloom note-sum -- hsv(note/12, sat, bin^2/6) summed
//      over 12 bins, clamped, square-iter contrast.
//  - bloom_fast variant = shift x2 (toggle).
//
// Substituted drivers (bare Pixelblaze, no sensor board):
//  - chromagram_smooth[12] -> simulated chord engine: root+third+fifth (+occasional 7th)
//    picked on a timer, crossfaded (tau 0.4s), per-note Perlin wobble. Chord changes are
//    what make Bloom breathe colour identity; the cadence is on a slider.
//  - centroid hue computed with the firmware's circular-mean atan2 math.

// K1 palette bank — generated verbatim from SPECTRASYNQ_K1_FIRMWARE/visual/Palettes.cpp
// Values are the FastLED gradient bytes /255 (already gamma-converted for WS2812B output).
// Order: K1_Iris_Apricot, K1_Tropical_Ultraviolet, K1_Chameleon_Flare, K1_Coral_Sunset, K1_Night_Sea_Amber, K1_Crimson_Gold, K1_Ultraviolet_Ascend, K1_Naberius_Gold, K1_Vepar_Pink, K1_Flourish_Sweep, K1_Ultraviolet_Bright, Sunset_Real, lava, GMT_drywet
var PAL_COUNT = 14
var palOff = [0, 9, 20, 30, 39, 49, 59, 68, 78, 86, 95, 101, 108, 121]
var palLen = [9, 11, 10, 9, 10, 10, 9, 10, 8, 9, 6, 7, 13, 7]
var palData = [
  0, 0.0118, 0.0078, 0.0941, 0.1176, 0.1569, 0.0784, 0.5098, 0.2275, 0.3608, 0.1765, 1, 0.3451, 0.7451, 0, 0.7059, 0.4627, 1, 0.1255, 0.2824, 0.6039, 1, 0.3725, 0, 0.7686, 1, 0.5882, 0, 0.8863, 1, 0.2824, 0, 1, 0.0941, 0.0039, 0.0706,  // K1_Iris_Apricot
  0, 0, 0.0157, 0.0706, 0.1098, 0, 0.1647, 0.2745, 0.2275, 0, 0.5882, 0.6275, 0.3451, 0, 0.8627, 0.8235, 0.4549, 0.3216, 0.8627, 0, 0.5647, 0.1333, 0.5882, 0, 0.6667, 0, 0.2157, 0.0392, 0.7451, 0.0314, 0.0118, 0.0706, 0.8471, 0.6471, 0, 0.5098, 0.9333, 0.9608, 0, 0.6667, 1, 0.0471, 0.0078, 0.1098,  // K1_Tropical_Ultraviolet
  0, 0, 0.0196, 0.1373, 0.1255, 0, 0.3529, 0.5686, 0.2588, 0, 0.8235, 0.902, 0.3843, 0, 0.5098, 0.6275, 0.4941, 0.4706, 0, 1, 0.6039, 0.7059, 0, 1, 0.7137, 0.9216, 0, 0.6863, 0.8314, 1, 0.5098, 0, 0.9255, 1, 0.3333, 0, 1, 0, 0.0196, 0.1373,  // K1_Chameleon_Flare
  0, 0.0706, 0, 0.0118, 0.1333, 0.3765, 0.0314, 0.0392, 0.2745, 0.8235, 0.1373, 0.1569, 0.4118, 1, 0.2824, 0.1765, 0.5412, 1, 0.4118, 0.0784, 0.6745, 1, 0.5882, 0, 0.8039, 1, 0.7451, 0.0784, 0.9098, 0.6667, 0, 0.3725, 1, 0.0706, 0, 0.0118,  // K1_Coral_Sunset
  0, 0, 0.0118, 0.0706, 0.1333, 0, 0.0784, 0.3529, 0.2667, 0, 0.3333, 0.7451, 0.4, 0, 0.7059, 0.8627, 0.5176, 0, 0.4314, 0.5098, 0.6275, 0, 0.0784, 0.1569, 0.7137, 0.0157, 0.0078, 0.0392, 0.8157, 1, 0.5294, 0, 0.9176, 1, 0.2941, 0, 1, 0.1373, 0, 0.0314,  // K1_Night_Sea_Amber
  0, 0.0471, 0, 0.0392, 0.1255, 0.2549, 0, 0.1765, 0.251, 0.5686, 0, 0.3137, 0.3765, 0.8627, 0, 0.2745, 0.502, 1, 0.1412, 0.0941, 0.6275, 1, 0.3608, 0, 0.7529, 1, 0.5686, 0, 0.8549, 1, 0.7451, 0.1569, 0.9412, 1, 0.2745, 0.4706, 1, 0.0471, 0, 0.0392,  // K1_Crimson_Gold
  0, 0.0314, 0, 0.0941, 0.1333, 0.1176, 0, 0.5098, 0.2745, 0.2745, 0, 0.9216, 0.4078, 0.5098, 0, 1, 0.5412, 0.7451, 0, 0.8627, 0.6745, 0.9216, 0, 0.6275, 0.8078, 1, 0.0314, 0.3765, 0.9098, 1, 0, 0.2353, 1, 0.0314, 0, 0.0941,  // K1_Ultraviolet_Ascend
  0, 0.0078, 0, 0.0784, 0.1333, 0.0392, 0, 0.549, 0.2745, 0.1098, 0, 0.8824, 0.4157, 0.2745, 0.0392, 1, 0.549, 0.4706, 0, 1, 0.6667, 0.1569, 0, 0.4706, 0.7451, 0.0235, 0.0078, 0.0549, 0.8314, 1, 0.549, 0, 0.9255, 1, 0.3725, 0, 1, 0.0078, 0, 0.0784,  // K1_Naberius_Gold
  0, 0.0549, 0, 0.0549, 0.149, 0.251, 0, 0.1882, 0.3059, 0.5882, 0, 0.3137, 0.4549, 0.8627, 0, 0.4706, 0.5961, 1, 0, 0.5882, 0.7373, 1, 0.1176, 0.4706, 0.8627, 1, 0.2745, 0.5882, 1, 0.0549, 0, 0.0549,  // K1_Vepar_Pink
  0, 0, 0.0627, 0.0235, 0.1333, 0, 0.6667, 0.1569, 0.2588, 0, 0.8627, 0.4706, 0.3843, 0, 0.8235, 0.8235, 0.5098, 0, 0.4706, 1, 0.6353, 0.2353, 0.1176, 1, 0.7608, 0.549, 0, 1, 0.8784, 0.8627, 0, 0.6667, 1, 0.0627, 0, 0.0549,  // K1_Flourish_Sweep
  0, 1, 0.0314, 0.3765, 0.2039, 0.9216, 0, 0.6275, 0.4078, 0.7451, 0, 0.8627, 0.6118, 0.5098, 0, 1, 0.8157, 0.2745, 0, 0.9216, 1, 0.1176, 0, 0.5098,  // K1_Ultraviolet_Bright
  0, 0.4706, 0, 0, 0.0863, 0.702, 0.0863, 0, 0.2, 1, 0.4078, 0, 0.3333, 0.6549, 0.0863, 0.0706, 0.5294, 0.3922, 0, 0.4039, 0.7765, 0.0627, 0, 0.5098, 1, 0, 0, 0.6275,  // Sunset_Real
  0, 0, 0, 0, 0.1804, 0.0706, 0, 0, 0.3765, 0.4431, 0, 0, 0.4235, 0.5569, 0.0118, 0.0039, 0.4667, 0.6863, 0.0667, 0.0039, 0.5725, 0.8353, 0.1725, 0.0078, 0.6824, 1, 0.3216, 0.0157, 0.7373, 1, 0.451, 0.0157, 0.7922, 1, 0.6118, 0.0157, 0.8549, 1, 0.7961, 0.0157, 0.9176, 1, 1, 0.0157, 0.9569, 1, 1, 0.2784, 1, 1, 1, 1,  // lava
  0, 0.1843, 0.1176, 0.0078, 0.1647, 0.8353, 0.5765, 0.0941, 0.3294, 0.4039, 0.8588, 0.2039, 0.498, 0.0118, 0.8588, 0.8118, 0.6667, 0.0039, 0.1882, 0.8392, 0.8314, 0.0039, 0.0039, 0.4353, 1, 0.0039, 0.0275, 0.1294  // GMT_drywet
]

// ---------- geometry (K1: centre-origin, mirrored halves) ----------
var center = floor(pixelCount / 2)
var half = pixelCount - center

// ---------- UI ----------
var paletteIndex = 0
export function sliderPalette(v) { paletteIndex = min(PAL_COUNT - 1, floor(v * PAL_COUNT)) }
var master = 1
export function sliderBrightness(v) { master = 0.05 + 0.95 * v }
var mood = 0.5
export function sliderMood(v) { mood = v }                    // K1 MOOD: propagation speed
var chordPeriod = 6
export function sliderChordRate(v) { chordPeriod = 16 - 14 * v }  // seconds between chords
var paletteOwns = 1
export function toggleUsePalette(v) { paletteOwns = v }       // off = classic HSV note-sum
var fastMode = 0
export function toggleBloomFast(v) { fastMode = v }           // light_mode_bloom_fast (x2)
var colourSpan = 0.25
export function sliderColourSpan(v) { colourSpan = 0.10 + 0.50 * v }
// NEVER-SOLID INVARIANT: colourSpan is the fraction of the palette visible across
// the strip at ALL times. Hue advance is locked to transport speed (see below), so
// the flowing history is always a gradient -- a solid single colour is impossible.
var mirrorMode = 1
export function toggleMirrorFromCenter(v) { mirrorMode = v }

// ---------- palette lookup ----------
var pr, pg, pb
function evalPal(t) {
  var o = palOff[paletteIndex]
  var n = palLen[paletteIndex]
  t = mod(t, 1)
  var base = o * 4
  var i
  for (i = 0; i < n - 1; i++) {
    if (t < palData[base + (i + 1) * 4]) break
  }
  if (i >= n - 1) i = n - 2
  var i0 = base + i * 4
  var i1 = i0 + 4
  var p0 = palData[i0], p1 = palData[i1]
  var f = p1 > p0 ? (t - p0) / (p1 - p0) : 0
  pr = mix(palData[i0 + 1], palData[i1 + 1], f)
  pg = mix(palData[i0 + 2], palData[i1 + 2], f)
  pb = mix(palData[i0 + 3], palData[i1 + 3], f)
}

// ---------- hsv helper for chromatic mode (beforeRender-safe) ----------
var cr, cg, cb
function hsv2rgb(h, s, v) {
  h = mod(h, 1) * 6
  var sect = floor(h)
  var f = h - sect
  var p = v * (1 - s)
  var q = v * (1 - s * f)
  var tt = v * (1 - s * (1 - f))
  if (sect == 0) { cr = v; cg = tt; cb = p }
  else if (sect == 1) { cr = q; cg = v; cb = p }
  else if (sect == 2) { cr = p; cg = v; cb = tt }
  else if (sect == 3) { cr = p; cg = q; cb = v }
  else if (sect == 4) { cr = tt; cg = p; cb = v }
  else { cr = v; cg = p; cb = q }
}

// ---------- state ----------
var hr = array(half), hg = array(half), hb = array(half)
var chroma = array(12), chordTarget = array(12)
var chordT = 99, wobT = 0
var strikeEnv = 1, strikeT = 0                // note articulation: strike + decay
// K1 hue_position substitute: the firmware's auto-colour-shift phase advances
// continuously (novelty-driven). Without it the centroid sample sits on ONE
// palette colour between chord changes. Base drift + novelty kicks replace it.
var huePos = 0, hueKick = 0
// Moving spatial texture phase (display-only mottle riding the flow): guarantees
// non-uniformity even when the hue window transits a dark palette anchor, where a
// position gradient maps to near-identical RGB (the documented dead-zone class).
var texPhase = 0
var fadeW = floor(half / 2)                   // outer quarter of full strip

function pickChord() {
  for (var c = 0; c < 12; c++) chordTarget[c] = 0
  var root = floor(random(12))
  chordTarget[root] = 0.9
  chordTarget[(root + (random(1) < 0.5 ? 3 : 4)) % 12] = 0.6
  chordTarget[(root + 7) % 12] = 0.7
  if (random(1) < 0.3) chordTarget[(root + 10) % 12] = 0.4
}
pickChord()

export function beforeRender(delta) {
  var dt = delta / 1000
  if (dt > 0.1) dt = 0.1

  // --- transport speed (computed early: the colour shift is locked to it) ---
  var mult = fastMode ? 2 : 1
  var drift = (0.250 + 1.750 * mood) * (pixelCount / 128) * mult * 100 * dt
  var alpha = pow(0.88, dt * 100)             // VP_FIX_BLOOM_DECAY alpha

  // --- span-locked auto-colour-shift: hue advances exactly colourSpan per strip
  // transit, regardless of MOOD/fast. The outward-flowing history therefore always
  // shows a colourSpan-wide palette gradient -- never a solid colour. ---
  huePos += colourSpan * drift / half + hueKick * dt
  if (huePos >= 1) huePos -= 1
  hueKick *= exp(-2 * dt)                     // novelty bursts decay ~0.5s
  texPhase += 0.15 * drift                    // texture rides the outward flow
  if (texPhase > 256) texPhase -= 256

  // --- simulated chord engine (replaces chromagram_smooth) ---
  chordT += dt
  if (chordT >= chordPeriod) {
    chordT = 0
    pickChord()
    strikeEnv = 1; strikeT = 0                // chord change = fresh strike
    hueKick += 0.12 + 0.18 * random(1)        // novelty spike -> palette advances
  }
  // periodic re-voicing: real chromagram strength dips between strikes; without
  // this the bloom pins at full brightness and never breathes (harness-caught)
  strikeT += dt
  if (strikeT > 1.6) {
    strikeT = 0
    strikeEnv = max(strikeEnv, 0.75 + 0.25 * random(1))
    hueKick += 0.05 * random(1)               // small novelty on re-voice
  }
  strikeEnv *= exp(-1.1 * dt)                 // note decay tau ~0.9s
  var artic = 0.45 + 0.55 * strikeEnv
  wobT += dt * 0.7
  for (var c = 0; c < 12; c++) {
    chroma[c] += (chordTarget[c] - chroma[c]) * min(1, dt / 0.4)
  }

  // --- outward scroll + fade (draw_sprite equivalent) ---
  // K1: (0.250 + 1.750*MOOD) px/frame @128px strip, x2 in bloom_fast, ~100fps
  for (var i = half - 1; i >= 0; i--) {
    var src = i - drift
    var vr = 0, vg = 0, vb = 0
    if (src >= 0) {
      var s0 = floor(src)
      var f = src - s0
      var s1 = s0 + 1
      if (s1 > half - 1) s1 = half - 1
      vr = hr[s0] * (1 - f) + hr[s1] * f
      vg = hg[s0] * (1 - f) + hg[s1] * f
      vb = hb[s0] * (1 - f) + hb[s1] * f
    }
    hr[i] = vr * alpha
    hg[i] = vg * alpha
    hb[i] = vb * alpha
  }

  // --- insert colour at centre (K1: overwrite, not additive) ---
  var ir = 0, ig = 0, ib = 0
  if (paletteOwns) {
    // ONE palette sample at the circular-mean centroid hue (never sum samples)
    var x = 0, y = 0, tw = 0
    for (c = 0; c < 12; c++) {
      var b = chroma[c] * artic * (0.85 + 0.3 * (perlin(c * 1.7, wobT, 0, 4.4) * 0.5 + 0.5))
      var ang = c / 12 * PI2
      x += cos(ang) * b
      y += sin(ang) * b
      tw += b
    }
    var hue = atan2(y, x) / PI2
    // luma-floor resample: if the sample lands in a dark palette anchor, probe
    // forward (max 8 x 0.05) until the colour can carry the flow. Dark anchors
    // become fast transitions instead of multi-second blackouts (dead-zone class).
    var probe = hue + huePos
    evalPal(probe)
    var k2
    for (k2 = 0; k2 < 8; k2++) {
      if (pr + pg + pb >= 0.30) break
      probe += 0.05
      evalPal(probe)
    }
    var bright = clamp(tw * 0.55, 0.30, 1)    // floored: history always has substance
    ir = pr * bright; ig = pg * bright; ib = pb * bright
  } else {
    // classic Bloom: sum every note colour, clamp, square-iter contrast
    for (c = 0; c < 12; c++) {
      var bin = chroma[c] * artic * (0.85 + 0.3 * (perlin(c * 1.7, wobT, 0, 4.4) * 0.5 + 0.5))
      hsv2rgb(c / 12, 1, bin * bin / 6)
      ir += cr; ig += cg; ib += cb
    }
    ir = min(1, ir); ig = min(1, ig); ib = min(1, ib)
    ir *= ir; ig *= ig; ib *= ib               // SQUARE_ITER = 1
  }
  // dt-correct insert width: the insert must cover the distance the field moved
  // this frame (ceil(drift)+1 px), else the 1px source dilutes against the scroll
  // and the trail dies within a few pixels at Pixelblaze frame rates (K1 runs
  // ~100fps where drift/frame never exceeds its 1px insert -- harness-caught).
  var wIns = ceil(drift) + 1
  if (wIns > half) wIns = half
  for (i = 0; i < wIns; i++) {
    hr[i] = ir
    hg[i] = ig
    hb[i] = ib
  }
}

export function render(index) {
  var d
  if (mirrorMode) {
    d = index - center
    if (d < 0) d = -d
  } else {
    d = floor(index * half / pixelCount)
  }
  if (d > half - 1) d = half - 1
  // display-only quadratic edge fade over the outer quarter (K1 post-snapshot fade)
  var g = 1
  if (d >= half - fadeW) {
    var p = (half - 1 - d) / (fadeW - 1)
    g = p * p
  }
  // display-only moving mottle (never-solid guarantee through dark palette anchors);
  // uniform across channels, so hue is preserved
  g *= 0.65 + 0.35 * (perlin(d * 0.35 - texPhase * 0.35, 3.7, 0, 8.2) * 0.5 + 0.5)
  rgb(hr[d] * g * master, hg[d] * g * master, hb[d] * g * master)
}
