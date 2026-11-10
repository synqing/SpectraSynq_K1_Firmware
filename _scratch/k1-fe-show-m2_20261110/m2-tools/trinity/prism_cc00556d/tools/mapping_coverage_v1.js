/**
 * Mapping coverage gate — duplicated locally (do not import spine).
 */

const PRIM8_KEYS = [
  "pressure",
  "impact",
  "mass",
  "momentum",
  "heat",
  "space",
  "texture",
  "gravity",
];

/**
 * @param {object} report
 * @returns {{ ok: boolean, errors: string[] }}
 */
export function evaluateCoverage(report) {
  const errors = [];

  if (!report || typeof report !== "object") {
    return { ok: false, errors: ["coverage report missing"] };
  }

  const prim8 = report.prim8;
  if (!prim8 || typeof prim8 !== "object") {
    return { ok: false, errors: ["coverage prim8 missing"] };
  }

  for (const key of PRIM8_KEYS) {
    const dim = prim8[key];
    if (!dim) {
      errors.push(`missing prim8.${key}`);
      continue;
    }
    if (dim.status === "UNMAPPED") {
      errors.push(`prim8.${key} is UNMAPPED`);
    }
    if (!["MAPPED_REAL", "AUTHORED", "EXPLICIT_NEUTRAL"].includes(dim.status)) {
      errors.push(`prim8.${key} has invalid status ${dim.status}`);
    }
    if (dim.status === "AUTHORED" || dim.status === "EXPLICIT_NEUTRAL") {
      if (dim.distinct_u16 !== 1) {
        errors.push(`prim8.${key} AUTHORED/EXPLICIT_NEUTRAL must have distinct_u16 === 1`);
      }
    }
  }

  let dynamicMapped = 0;
  for (const key of PRIM8_KEYS) {
    const dim = prim8[key];
    if (!dim || dim.status !== "MAPPED_REAL") continue;
    const hasEvents = (dim.event_count ?? 0) > 0;
    const hasDistinct = (dim.distinct_nonzero_u16 ?? 0) > 1;
    if (hasEvents || hasDistinct) dynamicMapped += 1;
  }

  if (dynamicMapped < 2) {
    errors.push("IMPACT_ONLY: FAIL");
  }

  return { ok: errors.length === 0, errors };
}

/**
 * @param {object} profile
 * @param {Record<string, { type: string, points: { t_us: number, v_u16: number }[] }>} curves
 * @param {{ beats_us: number[], downbeats_us: number[] }} rhythm
 */
export function buildCoverageReport(profile, curves, rhythm) {
  const prim8 = {};

  for (const [name, dim] of Object.entries(profile.prim8)) {
    const curve = curves[name];
    const values = curve?.points?.map((p) => p.v_u16) ?? [];
    const distinct = new Set(values);
    const distinctNonZero = new Set(values.filter((v) => v > 0));

    const entry = {
      status: dim.provenance,
      provenance: dim.provenance,
    };

    if (name === "impact") {
      entry.event_count = rhythm.beats_us.length;
      entry.downbeat_count = rhythm.downbeats_us.length;
    } else if (dim.provenance === "AUTHORED" || dim.provenance === "EXPLICIT_NEUTRAL") {
      entry.distinct_u16 = distinct.size;
      entry.constant_u16 = values[0] ?? 0;
    } else {
      entry.distinct_nonzero_u16 = distinctNonZero.size;
    }

    prim8[name] = entry;
  }

  return {
    profile_id: profile.id,
    prim8,
  };
}
