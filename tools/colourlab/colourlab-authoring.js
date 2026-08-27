(function (root, factory) {
  "use strict";
  var api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.ColourLabAuthoring = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  var MAX_STOPS = 8;
  var MAX_HUE_TRAVEL = 80;
  var MAX_HUE_FAMILIES = 3;
  var CHROMATIC_S_MIN = 0.20;
  var CHROMATIC_V_MIN = 0.10;
  var FAMILY_GAP_DEG = 32;

  function clamp(value, low, high) {
    return Math.max(low, Math.min(high, value));
  }

  function finite(value) {
    return typeof value === "number" && Number.isFinite(value);
  }

  function round(value, places) {
    var scale = Math.pow(10, places || 0);
    return Math.round(value * scale) / scale;
  }

  function normaliseRgb(rgb) {
    if (!Array.isArray(rgb) || rgb.length !== 3) throw new Error("rgb must contain three channels");
    return rgb.map(function (channel) {
      if (!finite(channel) || channel < 0 || channel > 255) throw new Error("rgb channel out of range");
      return channel;
    });
  }

  function normaliseStops(input) {
    if (!Array.isArray(input) || input.length < 1) throw new Error("at least one stop is required");
    var stops = input.map(function (stop, index) {
      var position = finite(stop && stop.position) ? stop.position : (finite(stop && stop.p) ? stop.p : null);
      if (position === null || position < 0 || position > 1) throw new Error("stop position out of range");
      return { position: position, rgb: normaliseRgb(stop.rgb), sourceIndex: index };
    }).sort(function (a, b) { return a.position - b.position || a.sourceIndex - b.sourceIndex; });
    for (var i = 1; i < stops.length; i += 1) {
      if (stops[i].position <= stops[i - 1].position) throw new Error("stop positions must be unique");
    }
    return stops.map(function (stop) { return { position: stop.position, rgb: stop.rgb.slice() }; });
  }

  function rgbToHsv(rgb) {
    var r = rgb[0] / 255;
    var g = rgb[1] / 255;
    var b = rgb[2] / 255;
    var max = Math.max(r, g, b);
    var min = Math.min(r, g, b);
    var d = max - min;
    var h = 0;
    if (d > 0) {
      if (max === r) h = 60 * (((g - b) / d) % 6);
      else if (max === g) h = 60 * (((b - r) / d) + 2);
      else h = 60 * (((r - g) / d) + 4);
    }
    if (h < 0) h += 360;
    return [h, max === 0 ? 0 : d / max, max];
  }

  function hsvToRgb(hsv) {
    var h = ((hsv[0] % 360) + 360) % 360;
    var s = clamp(hsv[1], 0, 1);
    var v = clamp(hsv[2], 0, 1);
    var c = v * s;
    var x = c * (1 - Math.abs(((h / 60) % 2) - 1));
    var m = v - c;
    var sector;
    if (h < 60) sector = [c, x, 0];
    else if (h < 120) sector = [x, c, 0];
    else if (h < 180) sector = [0, c, x];
    else if (h < 240) sector = [0, x, c];
    else if (h < 300) sector = [x, 0, c];
    else sector = [c, 0, x];
    return sector.map(function (channel) { return (channel + m) * 255; });
  }

  function srgbToLinear(channel) {
    channel /= 255;
    return channel <= 0.04045 ? channel / 12.92 : Math.pow((channel + 0.055) / 1.055, 2.4);
  }

  function linearToSrgb(channel) {
    channel = clamp(channel, 0, 1);
    var encoded = channel <= 0.0031308 ? 12.92 * channel : 1.055 * Math.pow(channel, 1 / 2.4) - 0.055;
    return encoded * 255;
  }

  function rgbToOklab(rgb) {
    var r = srgbToLinear(rgb[0]);
    var g = srgbToLinear(rgb[1]);
    var b = srgbToLinear(rgb[2]);
    var l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b);
    var m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b);
    var s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b);
    return [
      0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
      1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
      0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s
    ];
  }

  function oklabToRgb(lab) {
    var l_ = lab[0] + 0.3963377774 * lab[1] + 0.2158037573 * lab[2];
    var m_ = lab[0] - 0.1055613458 * lab[1] - 0.0638541728 * lab[2];
    var s_ = lab[0] - 0.0894841775 * lab[1] - 1.2914855480 * lab[2];
    var l = l_ * l_ * l_;
    var m = m_ * m_ * m_;
    var s = s_ * s_ * s_;
    return [
      linearToSrgb(4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s),
      linearToSrgb(-1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s),
      linearToSrgb(-0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s)
    ];
  }

  function rgbToOklch(rgb) {
    var lab = rgbToOklab(rgb);
    var c = Math.sqrt(lab[1] * lab[1] + lab[2] * lab[2]);
    var h = c < 1e-7 ? 0 : Math.atan2(lab[2], lab[1]) * 180 / Math.PI;
    if (h < 0) h += 360;
    return [lab[0], c, h];
  }

  function oklchToRgb(lch) {
    var radians = lch[2] * Math.PI / 180;
    return oklabToRgb([lch[0], lch[1] * Math.cos(radians), lch[1] * Math.sin(radians)]);
  }

  function shortestHueDelta(from, to) {
    return ((to - from + 540) % 360) - 180;
  }

  function interpolateTriplet(a, b, t) {
    return [
      a[0] + (b[0] - a[0]) * t,
      a[1] + (b[1] - a[1]) * t,
      a[2] + (b[2] - a[2]) * t
    ];
  }

  function mixRgb(a, b, t) {
    return interpolateTriplet(a, b, t);
  }

  function mixHsv(a, b, t) {
    var left = rgbToHsv(a);
    var right = rgbToHsv(b);
    if (left[1] < 1e-7) left[0] = right[0];
    if (right[1] < 1e-7) right[0] = left[0];
    return hsvToRgb([
      left[0] + shortestHueDelta(left[0], right[0]) * t,
      left[1] + (right[1] - left[1]) * t,
      left[2] + (right[2] - left[2]) * t
    ]);
  }

  function mixOklch(a, b, t) {
    var left = rgbToOklch(a);
    var right = rgbToOklch(b);
    if (left[1] < 1e-7) left[2] = right[2];
    if (right[1] < 1e-7) right[2] = left[2];
    return oklchToRgb([
      left[0] + (right[0] - left[0]) * t,
      left[1] + (right[1] - left[1]) * t,
      left[2] + shortestHueDelta(left[2], right[2]) * t
    ]);
  }

  function interpolate(stopsInput, position, space) {
    var stops = normaliseStops(stopsInput);
    var t = clamp(position, 0, 1);
    if (stops.length === 1 || t <= stops[0].position) return stops[0].rgb.slice();
    if (t >= stops[stops.length - 1].position) return stops[stops.length - 1].rgb.slice();
    for (var i = 1; i < stops.length; i += 1) {
      if (t <= stops[i].position) {
        var left = stops[i - 1];
        var right = stops[i];
        var local = (t - left.position) / (right.position - left.position);
        if (space === "hsv") return mixHsv(left.rgb, right.rgb, local);
        if (space === "oklch") return mixOklch(left.rgb, right.rgb, local);
        if (space !== "rgb") throw new Error("unsupported interpolation space");
        return mixRgb(left.rgb, right.rgb, local);
      }
    }
    return stops[stops.length - 1].rgb.slice();
  }

  function samplePalette(stops, count, space) {
    if (!Number.isInteger(count) || count < 1) throw new Error("sample count must be a positive integer");
    if (count === 1) return [interpolate(stops, 0, space)];
    var out = [];
    for (var i = 0; i < count; i += 1) out.push(interpolate(stops, i / (count - 1), space));
    return out;
  }

  function asU8(rgb) {
    return rgb.map(function (channel) { return Math.round(clamp(channel, 0, 255)); });
  }

  function compilePaintStops(stopsInput, options) {
    options = options || {};
    var stops = normaliseStops(stopsInput);
    var interpolation = options.interpolation || "rgb";
    var maxStops = options.maxStops === undefined ? MAX_STOPS : options.maxStops;
    if (!Number.isInteger(maxStops) || maxStops < 1 || maxStops > MAX_STOPS) {
      throw new Error("maxStops must be 1-" + MAX_STOPS);
    }
    var outputCount = stops.length === 1 ? 1 : maxStops;
    var compiledRgb = samplePalette(stops, outputCount, interpolation).map(asU8);
    var compiledStops = compiledRgb.map(function (rgb, index) {
      return { position: outputCount === 1 ? 0 : index / (outputCount - 1), rgb: rgb };
    });
    var comparisonSamples = options.comparisonSamples || 161;
    var squared = 0;
    var channels = 0;
    var maxError = 0;
    for (var i = 0; i < comparisonSamples; i += 1) {
      var at = comparisonSamples === 1 ? 0 : i / (comparisonSamples - 1);
      var source = interpolate(stops, at, interpolation);
      var compiled = interpolate(compiledStops, at, "rgb");
      for (var c = 0; c < 3; c += 1) {
        var error = Math.abs(source[c] - compiled[c]);
        maxError = Math.max(maxError, error);
        squared += error * error;
        channels += 1;
      }
    }
    return {
      interpolation: interpolation,
      sourceStopCount: stops.length,
      compiledStopCount: compiledStops.length,
      uniformlyDistributed: true,
      compiledStops: compiledStops,
      paintStops: compiledRgb,
      approximation: {
        maxChannelError8: round(maxError, 3),
        rmsChannelError8: round(Math.sqrt(squared / channels), 3),
        sampleCount: comparisonSamples
      }
    };
  }

  function chromatic(hsv) {
    return hsv[1] >= CHROMATIC_S_MIN && hsv[2] >= CHROMATIC_V_MIN;
  }

  function hueTravel(samples) {
    var previous = null;
    var travel = 0;
    samples.forEach(function (rgb) {
      var hsv = rgbToHsv(rgb);
      if (!chromatic(hsv)) return;
      if (previous !== null) travel += Math.abs(shortestHueDelta(previous, hsv[0]));
      previous = hsv[0];
    });
    return travel;
  }

  function hueSectors(samples) {
    var sectors = {};
    samples.forEach(function (rgb) {
      var hsv = rgbToHsv(rgb);
      if (chromatic(hsv)) sectors[Math.floor(hsv[0] / 60) % 6] = true;
    });
    return Object.keys(sectors).map(Number).sort(function (a, b) { return a - b; });
  }

  function hueFamilies(stopsInput) {
    var hues = normaliseStops(stopsInput).map(function (stop) { return rgbToHsv(stop.rgb); })
      .filter(chromatic).map(function (hsv) { return hsv[0]; }).sort(function (a, b) { return a - b; });
    if (hues.length < 2) return hues.length;
    var largestGap = -1;
    var breakAfter = 0;
    for (var i = 0; i < hues.length; i += 1) {
      var next = i === hues.length - 1 ? hues[0] + 360 : hues[i + 1];
      var gap = next - hues[i];
      if (gap > largestGap) { largestGap = gap; breakAfter = i; }
    }
    var unwrapped = [];
    for (var j = 1; j <= hues.length; j += 1) {
      var value = hues[(breakAfter + j) % hues.length];
      if (unwrapped.length && value < unwrapped[unwrapped.length - 1]) value += 360;
      unwrapped.push(value);
    }
    var families = 1;
    var anchor = unwrapped[0];
    for (var k = 1; k < unwrapped.length; k += 1) {
      if (unwrapped[k] - anchor > FAMILY_GAP_DEG) {
        families += 1;
        anchor = unwrapped[k];
      }
    }
    return families;
  }

  function paletteMetrics(stopsInput, options) {
    options = options || {};
    var interpolation = options.interpolation || "rgb";
    var samples = samplePalette(stopsInput, options.sampleCount || 257, interpolation);
    var nearWhite = false;
    var saturationFloor = 1;
    samples.forEach(function (rgb) {
      var hsv = rgbToHsv(rgb);
      saturationFloor = Math.min(saturationFloor, hsv[1]);
      if (hsv[1] < 0.50 && hsv[2] > 0.85) nearWhite = true;
    });
    return {
      hueTravelDeg: round(hueTravel(samples), 3),
      hueFamilies: hueFamilies(stopsInput),
      hueSectors: hueSectors(samples),
      nearWhite: nearWhite,
      saturationFloor: round(saturationFloor, 4)
    };
  }

  function validateProductPolicy(stopsInput, options) {
    options = options || {};
    var issues = [];
    var metrics;
    try {
      metrics = paletteMetrics(stopsInput, options);
    } catch (error) {
      return { ok: false, kind: "product_colour_policy", issues: [{ code: "invalid_palette", message: error.message }], metrics: null };
    }
    if (metrics.hueTravelDeg > (options.maxHueTravel || MAX_HUE_TRAVEL)) {
      issues.push({ code: "hue_travel", message: "Ordered hue travel exceeds the 80 degree product limit." });
    }
    if (metrics.hueFamilies > (options.maxHueFamilies || MAX_HUE_FAMILIES)) {
      issues.push({ code: "hue_families", message: "Palette contains more than three chromatic hue families." });
    }
    if (metrics.hueSectors.length >= 5) {
      issues.push({ code: "wheel_spanning", message: "Palette spans five or more hue sectors and is prohibited." });
    }
    if (metrics.nearWhite && !options.allowNearWhite) {
      issues.push({ code: "near_white", message: "Near-white output is blocked for product palettes because it risks plate bloom." });
    }
    return { ok: issues.length === 0, kind: "product_colour_policy", issues: issues, metrics: metrics };
  }

  function validateProductOutput(stopsInput, options) {
    options = options || {};
    var compiled;
    try {
      compiled = compilePaintStops(stopsInput, {
        interpolation: options.interpolation || "rgb",
        maxStops: options.maxStops || MAX_STOPS,
        comparisonSamples: options.comparisonSamples || 161,
      });
    } catch (error) {
      return {
        ok: false,
        kind: "product_colour_output_policy",
        issues: [{ code: "invalid_palette", scope: "source", message: error.message }],
        metrics: null,
        sourcePolicy: null,
        payloadPolicy: null,
        compiled: null,
      };
    }
    var sourcePolicy = validateProductPolicy(stopsInput, {
      interpolation: options.interpolation || "rgb",
      maxHueTravel: options.maxHueTravel,
      maxHueFamilies: options.maxHueFamilies,
      allowNearWhite: options.allowNearWhite,
    });
    var payloadPolicy = validateProductPolicy(compiled.compiledStops, {
      interpolation: "rgb",
      maxHueTravel: options.maxHueTravel,
      maxHueFamilies: options.maxHueFamilies,
      allowNearWhite: options.allowNearWhite,
    });
    var issues = [];
    sourcePolicy.issues.forEach(function (issue) {
      issues.push(Object.assign({ scope: "source" }, issue));
    });
    payloadPolicy.issues.forEach(function (issue) {
      issues.push(Object.assign({ scope: "compiled_payload" }, issue));
    });
    var sourceMetrics = sourcePolicy.metrics || {};
    var payloadMetrics = payloadPolicy.metrics || {};
    var metrics = {
      hueTravelDeg: Math.max(sourceMetrics.hueTravelDeg || 0, payloadMetrics.hueTravelDeg || 0),
      hueFamilies: Math.max(sourceMetrics.hueFamilies || 0, payloadMetrics.hueFamilies || 0),
      hueSectors: (sourceMetrics.hueSectors || []).length >= (payloadMetrics.hueSectors || []).length
        ? (sourceMetrics.hueSectors || []).slice()
        : (payloadMetrics.hueSectors || []).slice(),
      nearWhite: !!sourceMetrics.nearWhite || !!payloadMetrics.nearWhite,
      saturationFloor: Math.min(
        sourceMetrics.saturationFloor === undefined ? 1 : sourceMetrics.saturationFloor,
        payloadMetrics.saturationFloor === undefined ? 1 : payloadMetrics.saturationFloor
      ),
    };
    return {
      ok: sourcePolicy.ok && payloadPolicy.ok,
      kind: "product_colour_output_policy",
      issues: issues,
      metrics: metrics,
      sourcePolicy: sourcePolicy,
      payloadPolicy: payloadPolicy,
      compiled: compiled,
    };
  }

  function prohibitsChromaticDisplay(policy) {
    var prohibited = { hue_travel: true, hue_families: true, wheel_spanning: true };
    return !!(policy && policy.issues || []).find(function (issue) {
      return !!prohibited[issue.code];
    });
  }

  function validateDiagnosticReference(reference, pixelsInput) {
    var issues = [];
    var pixels;
    try {
      if (!Array.isArray(pixelsInput) || pixelsInput.length < 1) throw new Error("diagnostic pixels are required");
      pixels = pixelsInput.map(normaliseRgb);
    } catch (error) {
      return { ok: false, kind: "diagnostic_reference", reference: reference, issues: [{ code: "invalid_diagnostic", message: error.message }], metrics: null };
    }
    if (reference === "neutral") {
      if (pixels.some(function (rgb) { return rgb[0] !== rgb[1] || rgb[1] !== rgb[2]; })) {
        issues.push({ code: "not_neutral", message: "Neutral transfer contains a chromatic pixel." });
      }
    } else if (reference === "isolated_rgb") {
      if (pixels.some(function (rgb) { return rgb.filter(function (channel) { return channel > 0; }).length > 1; })) {
        issues.push({ code: "channels_overlap", message: "Channel reference mixes R, G and B instead of isolating them." });
      }
    } else if (reference === "single_hue") {
      if (hueTravel(pixels) > 5) {
        issues.push({ code: "hue_drift", message: "Single-hue reference drifts beyond five degrees." });
      }
    } else if (reference === "k1_card") {
      var allowed = { "255,0,0": true, "0,255,0": true, "0,0,255": true, "255,140,0": true };
      var seen = {};
      pixels.forEach(function (rgb) {
        var rounded = asU8(rgb);
        var key = rounded.join(",");
        if (rounded[0] === rounded[1] && rounded[1] === rounded[2]) return;
        if (!allowed[key]) issues.push({ code: "card_colour", message: "K1 Card contains an unapproved chromatic region." });
        else seen[key] = true;
      });
      Object.keys(allowed).forEach(function (key) {
        if (!seen[key]) issues.push({ code: "card_region_missing", message: "K1 Card is missing required region " + key + "." });
      });
    } else {
      issues.push({ code: "unknown_diagnostic", message: "Diagnostic reference is not recognised." });
    }
    return {
      ok: issues.length === 0,
      kind: "diagnostic_reference",
      reference: reference,
      issues: issues,
      metrics: { hueTravelDeg: round(hueTravel(pixels), 3), hueSectors: hueSectors(pixels) }
    };
  }

  function validateDeviceSafety(input) {
    input = input || {};
    var issues = [];
    var allowedModes = { off: true, solid: true, stops: true, card: true };
    if (input.modelKnown !== true) issues.push({ code: "model_unknown", message: "The device output model is unknown." });
    if (input.deviceEvidenceRequired === true && input.profileVerified !== true) {
      issues.push({ code: "profile_unverified", message: "The connected device profile is unverified." });
    }
    if (!input.mode || !allowedModes[input.mode]) issues.push({ code: "unsupported_mode", message: "The requested Paint mode is not permitted." });
    if (["primary", "secondary", "both"].indexOf(input.target) < 0) {
      issues.push({ code: "invalid_target", message: "The Paint target is invalid." });
    }
    if (!Number.isInteger(input.primaryLedCount) || input.primaryLedCount < 1) {
      issues.push({ code: "invalid_primary_count", message: "Primary LED count is invalid." });
    }
    if (!Number.isInteger(input.secondaryLedCount) || input.secondaryLedCount < 1) {
      issues.push({ code: "invalid_secondary_count", message: "Secondary LED count is invalid." });
    }
    if (input.needsResync === true) issues.push({ code: "resync_required", message: "Device state requires a fresh profile and hydration." });
    if (input.outputStateUnknown === true) issues.push({ code: "output_unknown", message: "The current device output state is unknown." });
    if (input.recoveryPending === true) issues.push({ code: "recovery_pending", message: "Stop output is awaiting an explicit Paint Off confirmation." });
    if (input.pixels) {
      try {
        input.pixels.forEach(normaliseRgb);
      } catch (error) {
        issues.push({ code: "invalid_pixels", message: error.message });
      }
    }
    if (input.serialisedLength !== undefined && input.serialisedLength > 158) {
      issues.push({ code: "wire_length", message: "The Paint command exceeds the firmware input buffer contract." });
    }
    return { ok: issues.length === 0, kind: "device_safety", issues: issues };
  }

  function resolveOutputDecision(input) {
    input = input || {};
    var safety = input.safety || { ok: false, issues: [{ code: "missing_safety", message: "Safety decision is missing." }] };
    var policy = input.policy || { ok: false, issues: [{ code: "missing_policy", message: "Policy decision is missing." }] };
    var transportReady = input.transportReady === true;
    if (!safety.ok) {
      return {
        kind: "safety_blocked",
        stageVisible: false,
        stageDark: true,
        nonProduct: false,
        deviceTestAllowed: false,
        saveAllowed: false,
        exportAllowed: false,
        recoveryOnly: true,
        issues: safety.issues.slice()
      };
    }
    if (!policy.ok) {
      return {
        kind: "policy_blocked",
        stageVisible: true,
        stageDark: false,
        nonProduct: true,
        deviceTestAllowed: false,
        saveAllowed: false,
        exportAllowed: false,
        recoveryOnly: false,
        issues: policy.issues.slice()
      };
    }
    return {
      kind: transportReady ? "ready" : "local_only",
      stageVisible: true,
      stageDark: false,
      nonProduct: false,
      deviceTestAllowed: transportReady,
      saveAllowed: transportReady,
      exportAllowed: true,
      recoveryOnly: false,
      issues: []
    };
  }

  function toHex(rgb) {
    return "#" + asU8(rgb).map(function (channel) { return channel.toString(16).padStart(2, "0"); }).join("").toUpperCase();
  }

  function dispatch(request) {
    request = request || {};
    if (request.op === "constants") return { MAX_STOPS: MAX_STOPS, MAX_HUE_TRAVEL: MAX_HUE_TRAVEL, MAX_HUE_FAMILIES: MAX_HUE_FAMILIES };
    if (request.op === "interpolate") return { rgb: interpolate(request.stops, request.position, request.space), hex: toHex(interpolate(request.stops, request.position, request.space)) };
    if (request.op === "sample") return { pixels: samplePalette(request.stops, request.count, request.space).map(asU8) };
    if (request.op === "compile") return compilePaintStops(request.stops, request.options);
    if (request.op === "policy") return validateProductPolicy(request.stops, request.options);
    if (request.op === "outputPolicy") return validateProductOutput(request.stops, request.options);
    if (request.op === "diagnosticPolicy") return validateDiagnosticReference(request.reference, request.pixels);
    if (request.op === "safety") return validateDeviceSafety(request.input);
    if (request.op === "decision") return resolveOutputDecision(request.input);
    throw new Error("unknown authoring op");
  }

  return {
    MAX_STOPS: MAX_STOPS,
    MAX_HUE_TRAVEL: MAX_HUE_TRAVEL,
    MAX_HUE_FAMILIES: MAX_HUE_FAMILIES,
    rgbToHsv: rgbToHsv,
    hsvToRgb: hsvToRgb,
    rgbToOklab: rgbToOklab,
    oklabToRgb: oklabToRgb,
    rgbToOklch: rgbToOklch,
    oklchToRgb: oklchToRgb,
    shortestHueDelta: shortestHueDelta,
    interpolate: interpolate,
    samplePalette: samplePalette,
    compilePaintStops: compilePaintStops,
    paletteMetrics: paletteMetrics,
    validateProductPolicy: validateProductPolicy,
    validateProductOutput: validateProductOutput,
    prohibitsChromaticDisplay: prohibitsChromaticDisplay,
    validateDiagnosticReference: validateDiagnosticReference,
    validateDeviceSafety: validateDeviceSafety,
    resolveOutputDecision: resolveOutputDecision,
    toHex: toHex,
    dispatch: dispatch
  };
});
