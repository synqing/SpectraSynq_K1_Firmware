// K1 -> Pixelblaze :: Pulse Prism (autonomous)
// Port of SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_pulse_prism.cpp
//
// K1 identity preserved:
//  - Kick -> expanding shockwave ring: soft (1-u^2) edge, ~3.6px wide @ 80px half,
//    velocity tuned so a ring crosses the half-strip in about one beat.
//  - Quiet centre "bed" glow between impacts (gain 0.36, asymmetric follow:
//    attack tau 35ms / release tau 320ms).
//  - Fading trail field (decay 0.075/frame @ 100fps), ring gain 0.70,
//    life decay exp(-0.58/s), beat_mod = 0.40 + 0.60*strength.
//  - Ring pool never evicts live rings (K1 arbiter rule).
//
// Substituted drivers (bare Pixelblaze, no sensor board):
//  - SBOnsetBeatEvent.kick -> beat-locked stochastic kick: fires on the beat with 88%
//    probability, strength 0.4..1 with bar accents, occasional off-beat ghost kick.
//  - vu/low_energy bed target -> slow Perlin loudness.
//  - chromagram_centroid_hue -> slow Perlin hue drift; ring hue offset 0.055/slot.

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
var bpm = 122
export function sliderTempoBPM(v) { bpm = 60 + floor(v * 120 + 0.5) }
export function showNumberBPM() { return bpm }
var paletteIndex = 0
export function sliderPalette(v) { paletteIndex = min(PAL_COUNT - 1, floor(v * PAL_COUNT)) }
var master = 1
export function sliderBrightness(v) { master = 0.05 + 0.95 * v }
var bedGain = 0.36
export function sliderBedGlow(v) { bedGain = 0.6 * v }
var hueShiftRate = 0.03
export function sliderColourShift(v) { hueShiftRate = 0.005 + 0.115 * v }  // hue_position substitute
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
var RINGS = 5
var ringR = array(RINGS), ringV = array(RINGS), ringLife = array(RINGS)
var ringHue = array(RINGS), ringMod = array(RINGS)
var fr = array(half), fg = array(half), fb = array(half)
var phase = 0, beats = 0, ghostArmed = 0, ghostFired = 0
var bedEnv = 0, loudT = 0, hueT = 0, centroidHue = 0
// K1 hue_position substitute: continuous auto-colour-shift + novelty kicks, so
// rings/bed walk the palette instead of parking on one slowly-drifting colour.
var huePos = 0, hueKick = 0

function spawnRing(s) {
  // free slots only -- never evict a live ring (K1 arbiter)
  for (var k = 0; k < RINGS; k++) {
    if (ringLife[k] <= 0.02) {
      ringR[k] = 0.5
      ringV[k] = half * (bpm / 60) * (0.70 + 0.40 * s)  // ~one-beat crossing
      ringLife[k] = 1
      ringHue[k] = centroidHue + huePos + 0.055 * k   // hue captured at spawn
      ringMod[k] = 0.40 + 0.60 * s                      // PRISM beat_mod
      return
    }
  }
}

export function beforeRender(delta) {
  var dt = delta / 1000
  if (dt > 0.1) dt = 0.1

  // --- simulated centroid hue + auto-colour-shift (hue_position substitute) ---
  hueT += dt * 0.03
  centroidHue = perlin(hueT, 0.7, 0, 3.3) * 0.5 + 0.5
  huePos += (hueShiftRate + hueKick) * dt
  if (huePos >= 1) huePos -= 1
  hueKick *= exp(-2 * dt)

  // --- simulated kick generator (replaces SBOnsetBeatEvent) ---
  phase += bpm / 60 * dt
  if (phase >= 1) {
    phase -= 1
    beats = (beats + 1) % 64
    if (random(1) > 0.12) {                  // 88% on-beat kick
      var s = 0.40 + 0.60 * pow(random(1), 1.5)
      if (beats % 4 == 0) s = max(s, 0.85)   // bar accent
      spawnRing(s)
      hueKick += 0.05 * s                    // per-kick novelty nudge
    }
    ghostArmed = random(1) < 0.22            // syncopated ghost this beat?
    ghostFired = 0
  }
  if (ghostArmed && !ghostFired && phase >= 0.5) {
    ghostFired = 1
    spawnRing(0.30 + 0.25 * random(1))
  }

  // --- bed envelope: simulated 0.55*vu + 0.45*low_energy, asym follow ---
  loudT += dt * 0.11
  var loud = clamp(perlin(loudT, 2.5, 0, 7.7) * 0.7 + 0.55, 0, 1)
  if (loud > bedEnv) bedEnv += (loud - bedEnv) * min(1, dt / 0.035)
  else bedEnv += (loud - bedEnv) * min(1, dt / 0.32)

  // --- fade trail field: 0.075/frame @ 100fps ---
  var fade = pow(0.925, dt * 100)
  for (var i = 0; i < half; i++) { fr[i] *= fade; fg[i] *= fade; fb[i] *= fade }

  // --- bed glow at centre (equilibrium-normalised against the fade) ---
  var bedReach = 0.12 * half
  evalPal(centroidHue + huePos)
  var bedA = bedGain * bedEnv * (1 - fade)
  for (i = 0; i < bedReach; i++) {
    var u = i / bedReach
    var a = (1 - u * u) * bedA
    fr[i] += pr * a
    fg[i] += pg * a
    fb[i] += pb * a
    var m = max(fr[i], max(fg[i], fb[i]))
    if (m > 1) { fr[i] /= m; fg[i] /= m; fb[i] /= m }
  }

  // --- rings: integrate + draw ---
  var w = 3.6 * half / 80                    // ring half-width, scaled
  for (var k = 0; k < RINGS; k++) {
    if (ringLife[k] <= 0.02) continue
    ringR[k] += ringV[k] * dt
    ringLife[k] *= exp(-0.58 * dt)           // PRISM life decay
    if (ringR[k] - w > half) { ringLife[k] = 0; continue }
    // radius-coupled palette position: a ring changes colour as it travels, so
    // concurrent rings at different radii are always different colours (never solid)
    evalPal(ringHue[k] + 0.25 * ringR[k] / half)
    var lo = floor(ringR[k] - w)
    if (lo < 0) lo = 0
    var hi = ceil(ringR[k] + w)
    if (hi > half - 1) hi = half - 1
    for (i = lo; i <= hi; i++) {
      var u = abs(i - ringR[k]) / w
      if (u >= 1) continue
      var a = (1 - u * u) * 0.70 * ringLife[k] * ringMod[k]  // ring gain 0.70
      fr[i] += pr * a
      fg[i] += pg * a
      fb[i] += pb * a
      var m = max(fr[i], max(fg[i], fb[i]))
      if (m > 1) { fr[i] /= m; fg[i] /= m; fb[i] /= m }
    }
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
  rgb(fr[d] * master, fg[d] * master, fb[d] * master)
}
