import fs from "node:fs";

const PRIM8_NAMES = [
  "pressure",
  "impact",
  "mass",
  "momentum",
  "heat",
  "space",
  "texture",
  "gravity",
];

function die(msg) {
  throw new Error(msg);
}

function clampU16(x) {
  if (x < 0) return 0;
  if (x > 65535) return 65535;
  return x;
}

function normaliseBundle(bundle) {
  if (!bundle || typeof bundle !== "object") die("Bundle must be an object.");
  if (bundle.version !== "0.1" && bundle.version !== "0.2" && bundle.version !== "0.3") die("Bundle.version must be '0.1', '0.2', or '0.3'.");
  if (!bundle.timebase || bundle.timebase.unit !== "us") die("Bundle.timebase.unit must be 'us'.");
  if (!Number.isInteger(bundle.duration_us) || bundle.duration_us <= 0) die("duration_us must be a positive integer.");
  if (!Array.isArray(bundle.tracks) || bundle.tracks.length === 0) die("tracks must be a non-empty array.");

  const tracks = bundle.tracks.slice().map((t) => normaliseTrack(t, bundle.duration_us));
  tracks.sort((a, b) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));

  const segments = Array.isArray(bundle.segments) ? bundle.segments.slice() : [];
  for (const s of segments) {
    if (!Number.isInteger(s.t_us) || s.t_us < 0 || s.t_us > bundle.duration_us) die("segment.t_us out of range.");
    if (typeof s.label !== "string" || s.label.length === 0) die("segment.label invalid.");
    // v0.2: optional segment end time (range marker).
    if (s.t1_us !== undefined) {
      if (!Number.isInteger(s.t1_us) || s.t1_us < 0 || s.t1_us > bundle.duration_us) die("segment.t1_us out of range.");
      if (s.t1_us < s.t_us) die("segment.t1_us must be >= segment.t_us.");
    }
  }

  // v0.3: ParamTree integration — schema_version, device_profile, param_curves.
  const schema_version = bundle.schema_version || null;
  const device_profile = bundle.device_profile || "none";
  const param_curves = {};

  if (bundle.version === "0.3") {
    if (schema_version !== null && typeof schema_version !== "string") die("schema_version must be a string.");
    if (typeof device_profile !== "string") die("device_profile must be a string.");

    if (bundle.param_curves && typeof bundle.param_curves === "object") {
      for (const [key, curve] of Object.entries(bundle.param_curves)) {
        if (!/^0x[0-9A-Fa-f]{2,4}$/.test(key)) die(`param_curves key '${key}' must be hex (e.g. '0x0100').`);
        param_curves[key] = normaliseCurve(curve, bundle.duration_us);
      }
    }
  }

  const result = {
    version: bundle.version,
    timebase: { unit: "us" },
    duration_us: bundle.duration_us,
    tracks,
    segments,
  };

  // v0.3 fields (only present when version is "0.3")
  if (bundle.version === "0.3") {
    result.schema_version = schema_version;
    result.device_profile = device_profile;
    result.param_curves = param_curves;
  }

  return result;
}

function normaliseTrack(track, duration_us) {
  if (!track || typeof track !== "object") die("track must be an object.");
  if (typeof track.id !== "string" || track.id.length === 0) die("track.id invalid.");
  if (track.type !== "lighttrack" && track.type !== "stemtrack") die("track.type must be 'lighttrack' or 'stemtrack'.");

  const enabled = track.enabled !== false;

  // v0.2: stemtracks are metadata lanes — no curves, no contribution to Prim8.
  if (track.type === "stemtrack") {
    if (typeof track.stem_role !== "string" || track.stem_role.length === 0) die("stemtrack.stem_role invalid.");
    if (typeof track.stem_ref !== "string" || track.stem_ref.length === 0) die("stemtrack.stem_ref invalid.");
    return { id: track.id, type: "stemtrack", enabled, stem_role: track.stem_role, stem_ref: track.stem_ref };
  }

  const gain_u16 = Number.isInteger(track.gain_u16) ? track.gain_u16 : 65535;
  if (gain_u16 < 0 || gain_u16 > 65535) die("track.gain_u16 out of range.");

  const prim8_curves = {};
  const src = track.prim8_curves && typeof track.prim8_curves === "object" ? track.prim8_curves : {};

  for (const name of PRIM8_NAMES) {
    if (src[name]) prim8_curves[name] = normaliseCurve(src[name], duration_us);
  }

  return { id: track.id, type: "lighttrack", enabled, gain_u16, prim8_curves };
}

function normaliseCurve(curve, duration_us) {
  if (!curve || typeof curve !== "object") die("curve must be an object.");
  if (curve.type !== "linear_u16" && curve.type !== "step_u16") die("curve.type must be 'linear_u16' or 'step_u16'.");
  if (!Array.isArray(curve.points) || curve.points.length === 0) die("curve.points must be a non-empty array.");

  const points = curve.points.slice().map((p) => {
    if (!Number.isInteger(p.t_us) || p.t_us < 0 || p.t_us > duration_us) die("point.t_us out of range.");
    if (!Number.isInteger(p.v_u16) || p.v_u16 < 0 || p.v_u16 > 65535) die("point.v_u16 out of range.");
    return { t_us: p.t_us, v_u16: p.v_u16 };
  });

  points.sort((a, b) => a.t_us - b.t_us);

  const dedup = [];
  for (const p of points) {
    if (dedup.length && dedup[dedup.length - 1].t_us === p.t_us) {
      dedup[dedup.length - 1] = p; // last-one-wins at same timestamp
    } else {
      dedup.push(p);
    }
  }

  return { type: curve.type, points: dedup };
}

function tickCount(duration_us, hz) {
  // ceil(duration_us * hz / 1_000_000)
  const du = BigInt(duration_us);
  const HZ = BigInt(hz);
  const one = 1000000n;
  return Number((du * HZ + (one - 1n)) / one);
}

function tickTimeUs(i, hz) {
  // round(i * 1_000_000 / hz) with integer rounding: (i*1e6 + floor(hz/2)) / hz
  const I = BigInt(i);
  const HZ = BigInt(hz);
  return Number((I * 1000000n + (HZ / 2n)) / HZ);
}

function evalLinearU16(points, t_us) {
  if (!points || points.length === 0) return 0;

  if (t_us <= points[0].t_us) return points[0].v_u16;
  const last = points[points.length - 1];
  if (t_us >= last.t_us) return last.v_u16;

  for (let j = 1; j < points.length; j++) {
    const p0 = points[j - 1];
    const p1 = points[j];
    if (t_us <= p1.t_us) {
      const t0 = p0.t_us;
      const t1 = p1.t_us;
      const v0 = p0.v_u16;
      const v1 = p1.v_u16;

      const dt = t1 - t0;
      if (dt <= 0) return v1;

      // v = v0 + round((t - t0) * (v1 - v0) / dt)
      const num = BigInt(t_us - t0) * BigInt(v1 - v0);
      const den = BigInt(dt);
      const delta = Number((num + (den / 2n)) / den);
      return clampU16(v0 + delta);
    }
  }

  return last.v_u16;
}

function evalStepU16(points, t_us) {
  if (!points || points.length === 0) return 0;

  // Step: hold last value at or before t_us.
  let v = points[0].v_u16;
  for (let j = 0; j < points.length; j++) {
    if (points[j].t_us <= t_us) v = points[j].v_u16;
    else break;
  }
  return v;
}

function evalCurveU16(curve, t_us) {
  if (curve.type === "step_u16") return evalStepU16(curve.points, t_us);
  return evalLinearU16(curve.points, t_us);
}

function scaleU16(gain_u16, value_u16) {
  // round(gain * value / 65535)
  const num = BigInt(gain_u16) * BigInt(value_u16) + 32767n;
  return Number(num / 65535n);
}

export function loadShowBundle(path) {
  const raw = fs.readFileSync(path, "utf-8");
  const json = JSON.parse(raw);
  return normaliseBundle(json);
}

/**
 * Normalise a bundle object in-memory (no filesystem round-trip).
 * Same validation as loadShowBundle but accepts a plain object.
 */
export function normaliseBundleObj(obj) {
  return normaliseBundle(obj);
}

/**
 * Evaluate all tracks at a single time point.
 * Bundle must already be normalised (output of loadShowBundle or normaliseBundleObj).
 * Returns { t_us, prim8_u16: [8 ints] }.
 */
export function evalFrameAtTime(bundle, t_us) {
  const acc = new Array(8).fill(0);

  for (const tr of bundle.tracks) {
    if (!tr.enabled) continue;
    if (tr.type !== "lighttrack") continue;
    for (let k = 0; k < 8; k++) {
      const name = PRIM8_NAMES[k];
      const curve = tr.prim8_curves[name];
      const v = curve ? evalCurveU16(curve, t_us) : 0;
      acc[k] += scaleU16(tr.gain_u16, v);
    }
  }

  for (let k = 0; k < 8; k++) acc[k] = clampU16(acc[k]);
  return { t_us, prim8_u16: acc };
}

export { tickTimeUs, tickCount };

/**
 * Evaluate all param_curves at a given time point.
 * Bundle must be normalised v0.3 with param_curves.
 * Returns a Map<string, number> of hex param ID → u16 value.
 * Returns empty Map for non-v0.3 bundles or bundles without param_curves.
 */
export function evalParamCurvesAtTime(bundle, t_us) {
  const result = new Map();
  if (bundle.version !== "0.3" || !bundle.param_curves) return result;
  for (const [hexId, curve] of Object.entries(bundle.param_curves)) {
    result.set(hexId, evalCurveU16(curve, t_us));
  }
  return result;
}

/**
 * Detect whether any param_curve has a steep slope around t_us.
 * "Steep" = value changes by more than `threshold_u16` over `window_us`.
 * Returns true if at least one curve qualifies — caller should burst.
 */
export function hasParamSlopeEdge(bundle, t_us, window_us = 100000, threshold_u16 = 3000) {
  if (bundle.version !== "0.3" || !bundle.param_curves) return false;
  for (const curve of Object.values(bundle.param_curves)) {
    const v0 = evalCurveU16(curve, t_us);
    const v1 = evalCurveU16(curve, t_us + window_us);
    if (Math.abs(v1 - v0) >= threshold_u16) return true;
  }
  return false;
}

/**
 * Find the latest keypoint t_us across all prim8_curves (and param_curves).
 * Past this point, all curves return held-constant values — the device should
 * fall back to audio energy mode rather than receiving frozen frames.
 * Returns 0 if no curves exist.
 */
export function curveEndUs(bundle) {
  let maxT = 0;
  for (const tr of bundle.tracks) {
    if (!tr.enabled || tr.type !== "lighttrack") continue;
    for (const name of PRIM8_NAMES) {
      const curve = tr.prim8_curves[name];
      if (!curve || !curve.points || curve.points.length === 0) continue;
      const lastPt = curve.points[curve.points.length - 1];
      if (lastPt.t_us > maxT) maxT = lastPt.t_us;
    }
  }
  if (bundle.version === "0.3" && bundle.param_curves) {
    for (const curve of Object.values(bundle.param_curves)) {
      if (!curve || !curve.points || curve.points.length === 0) continue;
      const lastPt = curve.points[curve.points.length - 1];
      if (lastPt.t_us > maxT) maxT = lastPt.t_us;
    }
  }
  return maxT;
}

export function replayToJsonl(bundle, hz) {
  if (!Number.isInteger(hz) || hz <= 0 || hz > 1000) die("hz must be an integer in 1..1000");
  const n = tickCount(bundle.duration_us, hz);
  const lines = [];

  for (let i = 0; i < n; i++) {
    const t_us = tickTimeUs(i, hz);
    if (t_us >= bundle.duration_us) continue;

    const acc = new Array(8).fill(0);

    for (const tr of bundle.tracks) {
      if (!tr.enabled) continue;
      if (tr.type !== "lighttrack") continue;

      for (let k = 0; k < 8; k++) {
        const name = PRIM8_NAMES[k];
        const curve = tr.prim8_curves[name];
        const v = curve ? evalCurveU16(curve, t_us) : 0;
        acc[k] += scaleU16(tr.gain_u16, v);
      }
    }

    for (let k = 0; k < 8; k++) acc[k] = clampU16(acc[k]);

    // Stable JSON key order: t_us then prim8_u16
    lines.push(JSON.stringify({ t_us, prim8_u16: acc }));
  }

  return lines.join("\n") + "\n";
}
