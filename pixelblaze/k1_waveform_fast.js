// K1 -> Pixelblaze :: Waveform Fast (autonomous)
// Port of SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_waveform_fast.cpp
//
// K1 identity preserved:
//  - Oscilloscope ribbon: a single dot is stamped at centre + amp*half each frame
//    (negative excursions pin at centre, exactly like waveform_upper_half_source_position),
//    the whole trace shifts outward at VP_WAVEFORM_SHIFT_RATE = 120 px/s (@80px half,
//    integer steps, capped 8/frame), and the field fades dynamically:
//    reactive fade = 1 - 0.10*|amp| per frame, idle fade = 0.85 per frame (@~120fps ref).
//  - Colour authority: palette sampled at the chromagram circular-centroid hue with
//    note-sum brightness, blended toward a +0.18-offset palette fallback (brightness =
//    smoothed |amp|, EMA tau ~0.11s) by chromagram energy (blend = min(1, 2*energy)).
//    This is the 2026-06-11 palette-crush-fix behaviour.
//
// Palette bank: ALL 44 firmware palettes, in gGradientPalettes[] order (Palettes.h),
// so slider index == firmware palette index. Index 33..43 are the K1-native set.
//
// Palette transitions: NO hard cuts. The renderer never samples palData directly;
// it samples a 128-entry working LUT that eases toward the selected palette with a
// per-entry exponential crossfade (time constant = PaletteFade slider, default 0.5s,
// snapped to exact target at 6*tau). Retarget-safe: changing palette mid-fade just
// redirects the ease -- there is no discontinuity, ever. Already-stamped trace pixels
// keep their colour and decay via the K1 fade rule, so the ribbon itself blends
// palettes naturally as it scrolls out.
//
// Substituted drivers (bare Pixelblaze, no sensor board):
//  - waveform_peak_scaled -> synthesized signed waveform: three detuned sines,
//    soft-clipped, with a percussive beat-coupled amplitude envelope. There is no
//    real waveform without audio; this is the honest replacement.
//  - chromagram_smooth[12] -> simulated chord engine: root+third+fifth picked every
//    2 bars, crossfaded (tau 0.4s), centroid hue computed with the SAME circular-mean
//    atan2 math as the firmware.
//  - Loudness gate -> slow Perlin; below floor the mode goes idle (fade 0.85, no dot),
//    matching K1's waveform_reactive gate.
// K1 palette bank -- generated verbatim from SPECTRASYNQ_K1_FIRMWARE/visual/Palettes.cpp
// Values are the FastLED gradient bytes /255 (already gamma-converted for WS2812B output).
// Order matches the firmware gGradientPalettes[] bank (Palettes.h) exactly, all 44 entries.
var PAL_COUNT = 44
var palOff = [0, 7, 12, 16, 25, 27, 32, 37, 43, 49, 56, 64, 76, 85, 91, 98, 104, 112, 119, 123, 128, 134, 139, 143, 156, 163, 174, 181, 192, 205, 212, 217, 224, 229, 238, 249, 259, 268, 278, 288, 297, 307, 315, 324]
var palLen = [7, 5, 4, 9, 2, 5, 5, 6, 6, 7, 8, 12, 9, 6, 7, 6, 8, 7, 4, 5, 6, 5, 4, 13, 7, 11, 7, 11, 13, 7, 5, 7, 5, 9, 11, 10, 9, 10, 10, 9, 10, 8, 9, 6]
var palData = [
  0, 0.4706, 0, 0, 0.0863, 0.702, 0.0863, 0, 0.2, 1, 0.4078, 0, 0.3333, 0.6549, 0.0863, 0.0706, 0.5294, 0.3922, 0, 0.4039, 0.7765, 0.0627, 0, 0.5098, 1, 0, 0, 0.6275,  // Sunset_Real
  0, 0.0039, 0.0549, 0.0196, 0.3961, 0.0627, 0.1412, 0.0549, 0.6471, 0.2196, 0.2667, 0.1176, 0.949, 0.5882, 0.6118, 0.3882, 1, 0.5882, 0.6118, 0.3882,  // es_rivendell_15
  0, 0.0039, 0.0235, 0.0275, 0.349, 0.0039, 0.3882, 0.4353, 0.6, 0.5647, 0.8196, 1, 1, 0, 0.2863, 0.3216,  // es_ocean_breeze_036
  0, 0.0157, 0.0039, 0.1216, 0.1216, 0.2157, 0.0039, 0.0627, 0.2471, 0.7725, 0.0118, 0.0275, 0.3725, 0.2314, 0.0078, 0.0667, 0.498, 0.0235, 0.0078, 0.1333, 0.6235, 0.1529, 0.0235, 0.1294, 0.749, 0.4392, 0.051, 0.1255, 0.8745, 0.2196, 0.0353, 0.1373, 1, 0.0863, 0.0235, 0.149,  // rgi_15
  0, 0.7373, 0.5294, 0.0039, 1, 0.1804, 0.0275, 0.0039,  // retro2_16
  0, 0.0118, 0, 1, 0.2471, 0.0902, 0, 1, 0.498, 0.2627, 0, 1, 0.749, 0.5569, 0, 0.1765, 1, 1, 0, 0,  // Analogous_1
  0, 0.4941, 0.0431, 1, 0.498, 0.7725, 0.0039, 0.0863, 0.6863, 0.8235, 0.6157, 0.6745, 0.8667, 0.6157, 0.0118, 0.4392, 1, 0.6157, 0.0118, 0.4392,  // es_pinksplash_08
  0, 0.1569, 0.7804, 0.7725, 0.1961, 0.0392, 0.5961, 0.6078, 0.3765, 0.0039, 0.4353, 0.4706, 0.3765, 0.1686, 0.498, 0.6353, 0.5451, 0.0392, 0.2863, 0.4353, 1, 0.0039, 0.1333, 0.2784,  // Coral_reef
  0, 0.3922, 0.6118, 0.6, 0.2, 0.0039, 0.3882, 0.5373, 0.3961, 0.0039, 0.2667, 0.3294, 0.4078, 0.1373, 0.5569, 0.6588, 0.698, 0, 0.2471, 0.4588, 1, 0.0039, 0.0392, 0.0392,  // es_ocean_breeze_068
  0, 0.898, 0.0039, 0.0039, 0.2392, 0.949, 0.0157, 0.2471, 0.3961, 1, 0.0471, 1, 0.498, 0.9765, 0.3176, 0.9882, 0.6, 1, 0.0431, 0.9216, 0.7569, 0.9569, 0.0196, 0.2667, 1, 0.9098, 0.0039, 0.0196,  // es_pinksplash_07
  0, 0.0157, 0.0039, 0.0039, 0.2, 0.0627, 0, 0.0039, 0.298, 0.3804, 0.4078, 0.0118, 0.3961, 1, 0.5137, 0.0745, 0.498, 0.2627, 0.0353, 0.0157, 0.6, 0.0627, 0, 0.0039, 0.898, 0.0157, 0.0039, 0.0039, 1, 0.0157, 0.0039, 0.0039,  // es_vintage_01
  0, 0.0314, 0.0118, 0, 0.1647, 0.0902, 0.0275, 0, 0.2471, 0.2941, 0.149, 0.0235, 0.3294, 0.6627, 0.3882, 0.149, 0.4157, 0.8353, 0.6627, 0.4667, 0.4549, 1, 1, 1, 0.5412, 0.5294, 1, 0.5412, 0.5804, 0.0863, 1, 0.0941, 0.6667, 0, 1, 0, 0.749, 0, 0.5333, 0, 0.8314, 0, 0.2157, 0, 1, 0, 0.2157, 0,  // departure
  0, 0, 0, 0, 0.1451, 0.0078, 0.098, 0.0039, 0.298, 0.0588, 0.451, 0.0196, 0.498, 0.3098, 0.8353, 0.0039, 0.502, 0.4941, 0.8275, 0.1843, 0.5098, 0.7373, 0.8196, 0.9686, 0.6, 0.5647, 0.7137, 0.8039, 0.8, 0.2314, 0.4588, 0.9804, 1, 0.0039, 0.1451, 0.7529,  // es_landscape_64
  0, 0.0039, 0.0196, 0, 0.0745, 0.1255, 0.0902, 0.0039, 0.149, 0.6314, 0.2157, 0.0039, 0.2471, 0.898, 0.5647, 0.0039, 0.2588, 0.1529, 0.5569, 0.2902, 1, 0.0039, 0.0157, 0.0039,  // es_landscape_33
  0, 1, 0.1294, 0.0157, 0.1686, 1, 0.2667, 0.098, 0.3373, 1, 0.0275, 0.098, 0.498, 1, 0.3216, 0.4039, 0.6667, 1, 1, 0.949, 0.8196, 0.1647, 1, 0.0863, 1, 0.3412, 1, 0.2549,  // rainbowsherbet
  0, 0.9686, 0.6902, 0.9686, 0.1882, 1, 0.5333, 1, 0.349, 0.8627, 0.1137, 0.8863, 0.6275, 0.0275, 0.3216, 0.698, 0.8471, 0.0039, 0.4863, 0.4275, 1, 0.0039, 0.4863, 0.4275,  // gr65_hult
  0, 0.0039, 0.4863, 0.4275, 0.2588, 0.0039, 0.3647, 0.3098, 0.4078, 0.2039, 0.2549, 0.0039, 0.5098, 0.451, 0.498, 0.0039, 0.5882, 0.2039, 0.2549, 0.0039, 0.7882, 0.0039, 0.3373, 0.2824, 0.9373, 0, 0.2157, 0.1765, 1, 0, 0.2157, 0.1765,  // gr64_hult
  0, 0.1843, 0.1176, 0.0078, 0.1647, 0.8353, 0.5765, 0.0941, 0.3294, 0.4039, 0.8588, 0.2039, 0.498, 0.0118, 0.8588, 0.8118, 0.6667, 0.0039, 0.1882, 0.8392, 0.8314, 0.0039, 0.0039, 0.4353, 1, 0.0039, 0.0275, 0.1294,  // GMT_drywet
  0, 0.7608, 0.0039, 0.0039, 0.3686, 0.0039, 0.1137, 0.0706, 0.5176, 0.2235, 0.5137, 0.1098, 1, 0.4431, 0.0039, 0.0039,  // ib_jul01
  0, 0.0078, 0.0039, 0.0039, 0.2078, 0.0706, 0.0039, 0, 0.4078, 0.2706, 0.1137, 0.0039, 0.6, 0.6549, 0.5294, 0.0392, 1, 0.1804, 0.2196, 0.0157,  // es_vintage_57
  0, 0.4431, 0.3569, 0.5765, 0.2824, 0.6157, 0.3451, 0.3059, 0.349, 0.8157, 0.3333, 0.1294, 0.4196, 1, 0.1137, 0.0431, 0.5529, 0.5373, 0.1216, 0.1529, 1, 0.2314, 0.1294, 0.349,  // ib15
  0, 0.1686, 0.0118, 0.6, 0.2471, 0.3922, 0.0157, 0.4039, 0.498, 0.7373, 0.0196, 0.2588, 0.749, 0.6314, 0.0431, 0.451, 1, 0.5294, 0.0784, 0.7137,  // Fuschia_7
  0, 0.3804, 1, 0.0039, 0.3961, 0.1843, 0.5216, 0.0039, 0.698, 0.051, 0.1686, 0.0039, 1, 0.0078, 0.0392, 0.0039,  // es_emerald_dragon_08
  0, 0, 0, 0, 0.1804, 0.0706, 0, 0, 0.3765, 0.4431, 0, 0, 0.4235, 0.5569, 0.0118, 0.0039, 0.4667, 0.6863, 0.0667, 0.0039, 0.5725, 0.8353, 0.1725, 0.0078, 0.6824, 1, 0.3216, 0.0157, 0.7373, 1, 0.451, 0.0157, 0.7922, 1, 0.6118, 0.0157, 0.8549, 1, 0.7961, 0.0157, 0.9176, 1, 1, 0.0157, 0.9569, 1, 1, 0.2784, 1, 1, 1, 1,  // lava
  0, 0.0039, 0.0039, 0, 0.298, 0.1255, 0.0196, 0, 0.5725, 0.7529, 0.0941, 0, 0.7725, 0.8627, 0.4118, 0.0196, 0.9412, 0.9882, 1, 0.1216, 0.9804, 0.9882, 1, 0.4353, 1, 1, 1, 1,  // fire
  0, 0.0392, 0.3333, 0.0196, 0.098, 0.1137, 0.4275, 0.0706, 0.2353, 0.2314, 0.5412, 0.1647, 0.3647, 0.3255, 0.3882, 0.2039, 0.4157, 0.4314, 0.2588, 0.251, 0.4275, 0.4824, 0.1922, 0.2549, 0.4431, 0.5451, 0.1373, 0.2588, 0.4549, 0.7529, 0.4588, 0.3843, 0.4863, 1, 1, 0.5373, 0.6588, 0.3922, 0.7059, 0.6078, 1, 0.0863, 0.4745, 0.6824,  // Colorfull
  0, 0.2784, 0.1059, 0.1529, 0.1216, 0.5098, 0.0431, 0.2, 0.2471, 0.8353, 0.0078, 0.251, 0.2745, 0.9098, 0.0039, 0.2588, 0.298, 0.9882, 0.0039, 0.2706, 0.4235, 0.4824, 0.0078, 0.2, 1, 0.1804, 0.0353, 0.1373,  // Magenta_Evening
  0, 0.0745, 0.0078, 0.1529, 0.098, 0.102, 0.0157, 0.1765, 0.2, 0.1294, 0.0235, 0.2039, 0.298, 0.2667, 0.2431, 0.4902, 0.4, 0.4627, 0.7333, 0.9412, 0.4275, 0.6392, 0.8431, 0.9686, 0.4471, 0.851, 0.9569, 1, 0.4784, 0.6235, 0.5843, 0.8667, 0.5843, 0.4431, 0.3059, 0.7373, 0.7176, 0.502, 0.2235, 0.6078, 1, 0.5725, 0.1569, 0.4824,  // Pink_Purple
  0, 0.102, 0.0039, 0.0039, 0.2, 0.2627, 0.0157, 0.0039, 0.3294, 0.4627, 0.0549, 0.0039, 0.4078, 0.5373, 0.5961, 0.2039, 0.4392, 0.4431, 0.2549, 0.0039, 0.4784, 0.5216, 0.5843, 0.2314, 0.4863, 0.5373, 0.5961, 0.2039, 0.5294, 0.4431, 0.2549, 0.0039, 0.5569, 0.5451, 0.6039, 0.1804, 0.6392, 0.4431, 0.051, 0.0039, 0.8, 0.2157, 0.0118, 0.0039, 0.9765, 0.0667, 0.0039, 0.0039, 1, 0.0667, 0.0039, 0.0039,  // es_autumn_19
  0, 0, 0, 0, 0.1647, 0, 0, 0.1765, 0.3294, 0, 0, 1, 0.498, 0.1647, 0, 1, 0.6667, 1, 0, 1, 0.8314, 1, 0.2157, 1, 1, 1, 1, 1,  // BlacK_Blue_Magenta_White
  0, 0, 0, 0, 0.2471, 0.1647, 0, 0.1765, 0.498, 1, 0, 1, 0.749, 1, 0, 0.1765, 1, 1, 0, 0,  // BlacK_Magenta_Red
  0, 0, 0, 0, 0.1647, 0.1647, 0, 0, 0.3294, 1, 0, 0, 0.498, 1, 0, 0.1765, 0.6667, 1, 0, 1, 0.8314, 1, 0.2157, 0.1765, 1, 1, 1, 0,  // BlacK_Red_Magenta_Yellow
  0, 0, 0, 1, 0.2471, 0, 0.2157, 1, 0.498, 0, 1, 1, 0.749, 0.1647, 1, 0.1765, 1, 1, 1, 0,  // Blue_Cyan_Yellow
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
  0, 1, 0.0314, 0.3765, 0.2039, 0.9216, 0, 0.6275, 0.4078, 0.7451, 0, 0.8627, 0.6118, 0.5098, 0, 1, 0.8157, 0.2745, 0, 0.9216, 1, 0.1176, 0, 0.5098  // K1_Ultraviolet_Bright
]
// ---------- geometry (K1: upper-half trace, mirrored) ----------
var center = floor(pixelCount / 2)
var half = pixelCount - center
// ---------- UI ----------
var bpm = 122
export function sliderTempoBPM(v) { bpm = 60 + floor(v * 120 + 0.5) }
export function showNumberBPM() { return bpm }
var paletteIndex = 0
export function sliderPalette(v) {
  var idx = min(PAL_COUNT - 1, floor(v * PAL_COUNT))
  if (idx != paletteIndex) {
    paletteIndex = idx
    setTargetPalette(idx)
    if (!booted) snapPalette()          // pattern-load restore: no boot fade
  }
}
export function showNumberPaletteIdx() { return paletteIndex }
var fadeTau = 0.5
export function sliderPaletteFade(v) { fadeTau = 0.05 + 2.95 * v * v }  // crossfade time constant, 0.05..3s
var master = 1
export function sliderBrightness(v) { master = 0.05 + 0.95 * v }
var waveHz = 1.6
export function sliderWaveSpeed(v) { waveHz = 0.4 + 4.6 * v }   // oscillation rate, Hz
var hueShiftRate = 0.03
export function sliderColourShift(v) { hueShiftRate = 0.005 + 0.115 * v }  // hue_position substitute
var mirrorMode = 1
export function toggleMirrorFromCenter(v) { mirrorMode = v }
// ---------- palette engine: LUT crossfade (no hard cuts) ----------
var PAL_LUT = 128
var cr = array(PAL_LUT), cg = array(PAL_LUT), cb = array(PAL_LUT)  // working LUT (what render sees)
var tr = array(PAL_LUT), tg = array(PAL_LUT), tb = array(PAL_LUT)  // target LUT (selected palette)
var palFadeT = 0                                                    // remaining fade time; <=0 -> settled
var booted = 0
var pr, pg, pb
// exact stop-walk sample of palette idx at position t (writes pr/pg/pb)
function palSample(idx, t) {
  var o = palOff[idx]
  var n = palLen[idx]
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
function setTargetPalette(idx) {
  for (var i = 0; i < PAL_LUT; i++) {
    palSample(idx, i / (PAL_LUT - 1))
    tr[i] = pr; tg[i] = pg; tb[i] = pb
  }
  palFadeT = fadeTau * 6                 // ease window; snap-to-exact when it expires
}
function snapPalette() {
  for (var i = 0; i < PAL_LUT; i++) { cr[i] = tr[i]; cg[i] = tg[i]; cb[i] = tb[i] }
  palFadeT = 0
}
setTargetPalette(0)
snapPalette()
// render-side palette read: linear interp of the working LUT (writes pr/pg/pb)
function evalPal(t) {
  t = mod(t, 1) * (PAL_LUT - 1)
  var i0 = floor(t)
  var f = t - i0
  var i1 = i0 + 1
  if (i1 > PAL_LUT - 1) i1 = PAL_LUT - 1
  pr = cr[i0] + (cr[i1] - cr[i0]) * f
  pg = cg[i0] + (cg[i1] - cg[i0]) * f
  pb = cb[i0] + (cb[i1] - cb[i0]) * f
}
// ---------- state ----------
var hr = array(half), hg = array(half), hb = array(half)
var phase = 0, beats = 0, beatAge = 9, beatStrength = 0
var oscT = 0, ampSm = 0, loudT = 0, shiftAccum = 0
var chroma = array(12), chordTarget = array(12)
var wobT = 0
// K1 hue_position substitute: continuous auto-colour-shift + novelty kicks.
// Without it the centroid sample parks on ONE palette colour between chords.
var huePos = 0, hueKick = 0
function pickChord() {
  for (var c = 0; c < 12; c++) chordTarget[c] = 0
  var root = floor(random(12))
  chordTarget[root] = 0.9
  chordTarget[(root + (random(1) < 0.5 ? 3 : 4)) % 12] = 0.6
  chordTarget[(root + 7) % 12] = 0.7
  if (random(1) < 0.3) chordTarget[(root + 10) % 12] = 0.4   // occasional 7th
}
pickChord()
export function beforeRender(delta) {
  var dt = delta / 1000
  if (dt > 0.1) dt = 0.1
  booted = 1
  // --- palette crossfade step (retarget-safe, snaps exact at end) ---
  if (palFadeT > 0) {
    palFadeT -= dt
    if (palFadeT <= 0) {
      snapPalette()
    } else {
      var pk = min(1, dt / fadeTau)
      for (var li = 0; li < PAL_LUT; li++) {
        cr[li] += (tr[li] - cr[li]) * pk
        cg[li] += (tg[li] - cg[li]) * pk
        cb[li] += (tb[li] - cb[li]) * pk
      }
    }
  }
  // --- simulated tempo (drives waveform envelope + chord cadence) ---
  phase += bpm / 60 * dt
  beatAge += dt
  if (phase >= 1) {
    phase -= 1
    beats = (beats + 1) % 64
    beatAge = 0
    beatStrength = 0.45 + 0.55 * random(1)
    if (beats % 4 == 0) beatStrength = max(beatStrength, 0.9)
    hueKick += 0.04 * beatStrength           // per-beat novelty nudge
    if (beats % 8 == 0) {
      pickChord()                            // chord change every 2 bars
      hueKick += 0.12 + 0.18 * random(1)     // novelty spike -> palette advances
    }
  }
  // auto-colour-shift (hue_position substitute)
  huePos += (hueShiftRate + hueKick) * dt
  if (huePos >= 1) huePos -= 1
  hueKick *= exp(-2 * dt)
  // --- simulated chromagram: crossfade to chord targets + gentle wobble ---
  wobT += dt * 0.7
  var energy = 0
  for (var c = 0; c < 12; c++) {
    chroma[c] += (chordTarget[c] - chroma[c]) * min(1, dt / 0.4)
    energy += chroma[c]
  }
  energy /= 12
  // --- loudness gate (K1 waveform_reactive) ---
  loudT += dt * 0.09
  var loud = clamp(perlin(loudT, 5.1, 0, 6.6) * 0.8 + 0.62, 0, 1)
  var reactive = loud > 0.35
  // --- synthesized signed waveform (replaces waveform_peak_scaled) ---
  oscT += dt
  var env = 0.25 + 0.75 * beatStrength * exp(-beatAge * 5)
  var w1 = oscT * waveHz * PI2
  var raw = sin(w1) * 0.55 + sin(w1 * 1.503) * 0.30 + sin(w1 * 2.917) * 0.15
  raw = raw * 1.4
  var amp = clamp(raw, -1, 1) * env * loud
  var absAmp = abs(amp)
  // smoothed peak, K1 EMA 0.05/0.95 per frame ~= tau 0.11s
  ampSm += (absAmp - ampSm) * min(1, dt / 0.11)
  // --- dynamic fade (K1: reactive 1-0.10*|amp|, idle 0.85, per ~120fps frame) ---
  var fadeFrame = reactive ? (1 - 0.10 * absAmp) : 0.85
  var fade = pow(fadeFrame, dt * 120)
  for (var i = 0; i < half; i++) { hr[i] *= fade; hg[i] *= fade; hb[i] *= fade }
  // --- shift trace outward: 120 px/s @ 80px half, integer steps, cap 8 ---
  shiftAccum += 120 * (half / 80) * dt
  var steps = floor(shiftAccum)
  if (steps > 8) steps = 8
  if (steps > 0) {
    shiftAccum -= steps
    for (i = half - 1; i >= steps; i--) {
      hr[i] = hr[i - steps]
      hg[i] = hg[i - steps]
      hb[i] = hb[i - steps]
    }
  }
  // --- dot colour: centroid palette sample blended with +0.18 offset fallback ---
  if (reactive) {
    // circular-mean centroid hue (same math as palette_chroma_colour)
    var x = 0, y = 0, nb = 0
    for (c = 0; c < 12; c++) {
      var b = chroma[c] * (0.85 + 0.3 * (perlin(c * 1.7, wobT, 0, 4.4) * 0.5 + 0.5))
      var ang = c / 12 * PI2
      x += cos(ang) * b
      y += sin(ang) * b
      var br = b * b                          // square-iter contrast
      nb += br / 12
    }
    var hue = atan2(y, x) / PI2
    nb = min(1, nb * 1.5 * 4)                 // note-sum brightness (x1.5, share-corrected)
    var blend = min(1, energy * 2)            // chromagram-energy blend (crush fix)
    evalPal(hue + huePos)                     // centroid + auto-shift phase
    var mr = pr * nb, mg = pg * nb, mb = pb * nb
    evalPal(hue + huePos + 0.18)              // WAVEFORM_FAST_FALLBACK_PALETTE_OFFSET
    var fb = reactive ? ampSm : 0
    var dotR = mr * blend + pr * fb * (1 - blend)
    var dotG = mg * blend + pg * fb * (1 - blend)
    var dotB = mb * blend + pb * fb * (1 - blend)
    // --- stamp dot: centre + amp*half, negatives pin at centre (K1 upper-half rule) ---
    var d = floor(amp * half + 0.5)
    if (d < 0) d = 0
    if (d > half - 1) d = half - 1
    hr[d] = dotR
    hg[d] = dotG
    hb[d] = dotB
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
