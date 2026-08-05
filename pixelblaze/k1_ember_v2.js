// K1 -> Pixelblaze :: Ember v2 (autonomous)
// Port of SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_ember_v2.cpp
//
// K1 identity preserved:
//  - Full half-strip lit; brightness breathes with energy (energy*(1-0.30*pos),
//    mild centre bias), gain 0.85.
//  - Wide palette gradient centre->edge (hue spread 0.55) anchored on the drifting
//    chroma centroid hue -- THE palette showcase mode.
//  - Outward scroll with trail alpha 0.88; drift = 0.40 + 1.60*MOOD + 0.50*energy
//    px/frame @ 100fps. As the hue anchor drifts, colour waves ride the scroll outward.
//
// Substituted drivers (bare Pixelblaze, no sensor board):
//  - spectral_energy -> slow Perlin loudness, EMA-smoothed (tau 0.5s).
//  - chromagram_centroid_hue -> slow Perlin hue drift (rate on a slider).
//  - MOOD knob -> slider.
//
// Deliberate deviation: injection is equilibrium-normalised (scaled by 1-alpha) so the
// sustained synthetic energy signal doesn't saturate the additive buffer.

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
export function sliderMood(v) { mood = v }                 // K1 MOOD knob: scroll speed
var hueRate = 0.03
export function sliderColourDrift(v) { hueRate = 0.005 + 0.075 * v }
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

// ---------- state ----------
var hr = array(half), hg = array(half), hb = array(half)
var energySm = 0.5
var energyT = 0, hueT = 0

export function beforeRender(delta) {
  var dt = delta / 1000
  if (dt > 0.1) dt = 0.1

  // --- simulated energy + centroid hue drivers ---
  energyT += dt * 0.13
  var energy = clamp(perlin(energyT, 4.2, 0, 11.3) * 0.6 + 0.55, 0.1, 1)
  energySm += (energy - energySm) * min(1, dt / 0.5)
  hueT += dt * hueRate
  var hueBase = perlin(hueT, 8.8, 0, 5.5) * 0.5 + 0.5

  // --- outward scroll + fade ---
  var scalePx = half / 80
  var drift = (0.40 + 1.60 * mood + 0.50 * energySm) * scalePx * 100 * dt
  var alpha = pow(0.88, dt * 100)            // EMBER trail alpha per 10ms frame
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

  // --- inject: full-width palette gradient, energy-breathing ---
  var inj = 1 - alpha
  for (i = 0; i < half; i++) {
    var bp = i / half
    var b = energySm * (1 - 0.30 * bp) * 0.85    // centre bias 0.30, gain 0.85
    evalPal(hueBase + 0.55 * bp)                 // hue spread 0.55 centre->edge
    var g = b * inj
    hr[i] += pr * g
    hg[i] += pg * g
    hb[i] += pb * g
    var m = max(hr[i], max(hg[i], hb[i]))
    if (m > 1) { hr[i] /= m; hg[i] /= m; hb[i] /= m }
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
  rgb(hr[d] * master, hg[d] * master, hb[d] * master)
}
