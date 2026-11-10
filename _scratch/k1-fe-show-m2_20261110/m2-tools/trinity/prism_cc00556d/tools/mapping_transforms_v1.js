/**
 * Closed transform set for mapping profile v1 → ShowBundle linear_u16 curves.
 *
 * Arithmetic here is IEEE-754 float64 on Trinity stem_features series (which may
 * be unnormalised RMS / band energy, not 0..1). The last step rounds and clamps
 * to u16. The playback VM (`src/vm.js`) remains BigInt-only and is not used here.
 */

function clampInt(x, lo, hi) {
  if (x < lo) return lo;
  if (x > hi) return hi;
  return x;
}

function frameToUs(frameIndex, fps) {
  return Math.round((frameIndex * 1_000_000) / fps);
}

function dedupePoints(points) {
  points.sort((a, b) => a.t_us - b.t_us);
  const dedup = [];
  for (const p of points) {
    if (dedup.length && dedup[dedup.length - 1].t_us === p.t_us) {
      dedup[dedup.length - 1] = p;
    } else {
      dedup.push(p);
    }
  }
  return dedup;
}

/**
 * Fail closed if any sample is non-finite. Used as last-line defence before
 * u16 rounding so transform bugs cannot be silently mapped to 0.
 * @param {string} name series label for the diagnostic
 * @param {unknown} series
 */
export function assertFiniteSeries(name, series) {
  if (!Array.isArray(series)) {
    throw new Error(`${name}: expected a numeric series`);
  }
  for (let i = 0; i < series.length; i++) {
    const v = series[i];
    if (typeof v !== "number" || !Number.isFinite(v)) {
      throw new Error(`${name}: non-finite value at frame ${i}`);
    }
  }
}

function seriesToPoints(series01, fps, duration_us) {
  assertFiniteSeries("seriesToPoints", series01);
  const points = [];
  for (let i = 0; i < series01.length; i++) {
    const t_us = clampInt(frameToUs(i, fps), 0, duration_us);
    const v = series01[i];
    const v_u16 = clampInt(Math.round(v * 65535), 0, 65535);
    points.push({ t_us, v_u16 });
  }
  if (points.length === 0) {
    points.push({ t_us: 0, v_u16: 0 });
  }
  const lastT = points[points.length - 1].t_us;
  if (lastT < duration_us) {
    points.push({ t_us: duration_us, v_u16: points[points.length - 1].v_u16 });
  } else if (lastT > duration_us) {
    points[points.length - 1].t_us = duration_us;
  }
  return dedupePoints(points);
}

function applyRollingSum(working, windowFrames) {
  if (!windowFrames || windowFrames <= 1) return working;
  const w = windowFrames;
  const rolled = [];
  for (let i = 0; i < working.length; i++) {
    let sum = 0;
    const start = Math.max(0, i - w + 1);
    for (let j = start; j <= i; j++) sum += working[j];
    rolled.push(sum);
  }
  return rolled;
}

function applyNormaliseMaxU16(series01, transform) {
  const floor = transform.silence_floor ?? 0;
  let working = series01.map((v) => (v < floor ? 0 : v));

  working = applyRollingSum(working, transform.rolling_window_frames);

  const max = Math.max(...working, 0);
  if (max <= 0) return working.map(() => 0);
  return working.map((v) => v / max);
}

function applyRatioU16(numerator, denominator, transform) {
  const floor = transform.silence_floor ?? 0;
  const denAbs = transform.absolute_denominator_floor;
  const out = [];
  for (let i = 0; i < numerator.length; i++) {
    const denRaw = denominator[i];
    if (denAbs !== undefined && denRaw < denAbs) {
      out.push(0);
      continue;
    }
    const num = numerator[i] < floor ? 0 : numerator[i];
    const den = denRaw < floor ? 0 : denRaw;
    if (den <= 0) {
      out.push(0);
    } else {
      out.push(clampInt(num / den, 0, 1));
    }
  }
  return out;
}

function requireFiniteNumber(name, value) {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    throw new Error(`${name} must be a finite number (got ${value})`);
  }
}

/**
 * Nearest-rank percentile on a non-empty array. `percentile` is 0..100.
 * index = floor((p/100) * (n-1)), matching the closed integer-friendly rule.
 */
export function percentileNearestRank(values, percentile) {
  const sorted = values.slice().sort((a, b) => a - b);
  const n = sorted.length;
  const idx = clampInt(Math.floor((percentile / 100) * (n - 1)), 0, n - 1);
  return sorted[idx];
}

/**
 * Activity-aware bounded normalisation.
 *
 * Parameters live entirely in the profile transform object (no hidden gain):
 *   absolute_activity_floor, min_active_frames, reference_percentile (0..100),
 *   minimum_reference, maximum_gain, target_u16, optional rolling_window_frames.
 *
 * Activity series is `ctx.activity` (compiler-resolved from transform.activity).
 *
 *   active = activity > absolute_activity_floor
 *   if |active| < min_active_frames → 0
 *   else:
 *     reference = max(percentile(source[active], p), minimum_reference)
 *     gain = min(target_u16/65535 / reference, maximum_gain)
 *     output[i] = active[i] ? clamp(source[i] * gain, 0, 1) : 0
 */
export function applyNoiseGatedBoundedPercentileU16(source, transform, ctx = {}) {
  const floor = transform.absolute_activity_floor;
  const minActive = transform.min_active_frames;
  const pct = transform.reference_percentile;
  const minRef = transform.minimum_reference;
  const maxGain = transform.maximum_gain;
  const targetU16 = transform.target_u16;

  requireFiniteNumber("absolute_activity_floor", floor);
  requireFiniteNumber("min_active_frames", minActive);
  requireFiniteNumber("reference_percentile", pct);
  requireFiniteNumber("minimum_reference", minRef);
  requireFiniteNumber("maximum_gain", maxGain);
  requireFiniteNumber("target_u16", targetU16);

  if (minActive < 1) throw new Error("min_active_frames must be >= 1");
  if (pct < 0 || pct > 100) throw new Error("reference_percentile must be 0..100");
  if (maxGain < 0) throw new Error("maximum_gain must be >= 0");
  if (targetU16 < 0 || targetU16 > 65535) throw new Error("target_u16 must be 0..65535");

  if (!Array.isArray(source)) {
    throw new Error("noise_gated_bounded_percentile_u16 requires a numeric source series");
  }
  const activity = ctx.activity;
  if (!Array.isArray(activity) || activity.length !== source.length) {
    throw new Error(
      "noise_gated_bounded_percentile_u16 requires ctx.activity of matching length (compiler must resolve transform.activity)",
    );
  }

  assertFiniteSeries("source", source);
  assertFiniteSeries("activity", activity);

  const targetLevel = targetU16 / 65535;
  let working = source.map((v) => (v > 0 ? v : 0));
  working = applyRollingSum(working, transform.rolling_window_frames);

  const activeIdx = [];
  for (let i = 0; i < activity.length; i++) {
    if (activity[i] > floor) activeIdx.push(i);
  }
  if (activeIdx.length < minActive) {
    return working.map(() => 0);
  }

  const activeSrc = activeIdx.map((i) => working[i]);
  let reference = percentileNearestRank(activeSrc, pct);
  if (!Number.isFinite(reference)) {
    throw new Error("noise_gated_bounded_percentile_u16: non-finite reference");
  }
  if (reference < minRef) reference = minRef;
  if (!(reference > 0)) {
    return working.map(() => 0);
  }

  let gain = targetLevel / reference;
  if (!Number.isFinite(gain)) {
    throw new Error("noise_gated_bounded_percentile_u16: non-finite gain");
  }
  if (gain < 0) gain = 0;
  if (gain > maxGain) gain = maxGain;

  const activeSet = new Set(activeIdx);
  return working.map((v, i) => {
    if (!activeSet.has(i)) return 0;
    const x = v * gain;
    if (!Number.isFinite(x)) {
      throw new Error(`noise_gated_bounded_percentile_u16: non-finite output at frame ${i}`);
    }
    if (x <= 0) return 0;
    return x > 1 ? 1 : x;
  });
}

function buildDownbeatAccentCurve(beats_us, downbeats_us, duration_us, transform) {
  const downbeatSet = new Set(downbeats_us);
  const beatAmp = transform.beat_amp_u16 ?? 48000;
  const downbeatAmp = transform.downbeat_amp_u16 ?? 65535;
  const beatPulse = transform.beat_pulse_us ?? 40000;
  const downbeatPulse = transform.downbeat_pulse_us ?? 60000;

  const points = [
    { t_us: 0, v_u16: 0 },
    { t_us: duration_us, v_u16: 0 },
  ];

  for (const tb of beats_us) {
    const isDownbeat = downbeatSet.has(tb);
    const amp = isDownbeat ? downbeatAmp : beatAmp;
    const pulseUs = isDownbeat ? downbeatPulse : beatPulse;

    const t0 = clampInt(tb - 1, 0, duration_us);
    const t1 = clampInt(tb, 0, duration_us);
    const t2 = clampInt(tb + pulseUs, 0, duration_us);

    points.push({ t_us: t0, v_u16: 0 });
    points.push({ t_us: t1, v_u16: amp });
    points.push({ t_us: t2, v_u16: 0 });
  }

  return { type: "linear_u16", points: dedupePoints(points) };
}

function buildBeatPulseCurve(beats_us, duration_us, transform) {
  const amp = transform.amp_u16 ?? 65535;
  const pulseUs = transform.pulse_us ?? 40000;
  const points = [
    { t_us: 0, v_u16: 0 },
    { t_us: duration_us, v_u16: 0 },
  ];
  for (const tb of beats_us) {
    const t0 = clampInt(tb - 1, 0, duration_us);
    const t1 = clampInt(tb, 0, duration_us);
    const t2 = clampInt(tb + pulseUs, 0, duration_us);
    points.push({ t_us: t0, v_u16: 0 });
    points.push({ t_us: t1, v_u16: amp });
    points.push({ t_us: t2, v_u16: 0 });
  }
  return { type: "linear_u16", points: dedupePoints(points) };
}

function buildConstantCurve(duration_us, value_u16) {
  const v = clampInt(value_u16, 0, 65535);
  return {
    type: "linear_u16",
    points: [
      { t_us: 0, v_u16: v },
      { t_us: duration_us, v_u16: v },
    ],
  };
}

/**
 * @param {number[]|object} series01orEvents frame series (0..1) or rhythm event context
 * @param {object} transform
 * @param {number} duration_us
 * @param {number} fps
 * @param {object} [ctx] optional { beats_us, downbeats_us, activity }
 * @returns {{ type: "linear_u16", points: { t_us: number, v_u16: number }[] }}
 */
export function applyTransform(series01orEvents, transform, duration_us, fps, ctx = {}) {
  const type = transform.type;

  switch (type) {
    case "constant_u16":
      return buildConstantCurve(duration_us, transform.value_u16 ?? 0);

    case "identity_01_to_u16": {
      const series = /** @type {number[]} */ (series01orEvents);
      return { type: "linear_u16", points: seriesToPoints(series, fps, duration_us) };
    }

    case "normalise_max_u16": {
      const series = /** @type {number[]} */ (series01orEvents);
      const norm = applyNormaliseMaxU16(series, transform);
      return { type: "linear_u16", points: seriesToPoints(norm, fps, duration_us) };
    }

    case "ratio_u16": {
      const { numerator, denominator } = /** @type {{ numerator: number[], denominator: number[] }} */ (
        series01orEvents
      );
      const ratio = applyRatioU16(numerator, denominator, transform);
      return { type: "linear_u16", points: seriesToPoints(ratio, fps, duration_us) };
    }

    case "beat_pulse_u16":
      return buildBeatPulseCurve(ctx.beats_us ?? [], duration_us, transform);

    case "downbeat_accent_u16":
      return buildDownbeatAccentCurve(
        ctx.beats_us ?? [],
        ctx.downbeats_us ?? [],
        duration_us,
        transform,
      );

    case "normalise_percentile_u16": {
      const series = /** @type {number[]} */ (series01orEvents);
      const pct = transform.percentile ?? 0.95;
      const sorted = series.slice().sort((a, b) => a - b);
      const idx = clampInt(Math.floor(sorted.length * pct), 0, Math.max(0, sorted.length - 1));
      const ref = sorted[idx] || 0;
      const norm = ref <= 0 ? series.map(() => 0) : series.map((v) => clampInt(v / ref, 0, 1));
      return { type: "linear_u16", points: seriesToPoints(norm, fps, duration_us) };
    }

    case "noise_gated_bounded_percentile_u16": {
      const series = /** @type {number[]} */ (series01orEvents);
      const gated = applyNoiseGatedBoundedPercentileU16(series, transform, ctx);
      return { type: "linear_u16", points: seriesToPoints(gated, fps, duration_us) };
    }

    default:
      throw new Error(`unsupported transform type: ${type}`);
  }
}
