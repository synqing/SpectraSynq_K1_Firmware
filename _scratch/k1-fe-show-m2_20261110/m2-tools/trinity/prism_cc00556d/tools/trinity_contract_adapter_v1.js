/**
 * Trinity Contract → canonical integer microsecond evidence.
 * Seconds conversion lives only here — no magnitude heuristics.
 */

export const SUPPORTED_CONTRACT_VERSIONS = ["1.0.0"];

const REQUIRED_STEMS = ["vocals", "drums", "bass", "other"];
const REQUIRED_STEM_ARRAYS = [
  "rms",
  "onset_strength",
  "band_energy_low",
  "band_energy_mid",
  "band_energy_high",
];

function die(msg) {
  throw new Error(msg);
}

function isObject(x) {
  return x !== null && typeof x === "object" && !Array.isArray(x);
}

function assertFiniteSeconds(value, label) {
  if (typeof value !== "number" || !Number.isFinite(value) || value < 0) {
    die(`${label} must be a finite number of seconds >= 0`);
  }
}

function assertMonotonicSeconds(arr, label) {
  for (let i = 1; i < arr.length; i++) {
    if (arr[i] < arr[i - 1]) {
      die(`${label} must be monotonically non-decreasing`);
    }
  }
}

/**
 * Convert seconds to microseconds with exact rounding.
 * @param {number} sec
 * @returns {number}
 */
export function secondsToUs(sec) {
  if (typeof sec !== "number" || !Number.isFinite(sec) || sec < 0 || sec > 86400) {
    die("seconds must be a finite number in [0, 86400]");
  }
  return Math.round(sec * 1_000_000);
}

function validateContract(contract) {
  if (!isObject(contract)) die("contract must be an object");

  if (contract.duration_us !== undefined) {
    die("contract.duration_us is forbidden; use track.duration_sec");
  }

  if (!SUPPORTED_CONTRACT_VERSIONS.includes(contract.version)) {
    die(`unsupported contract version: ${contract.version}`);
  }

  if (!isObject(contract.track)) die("contract.track is required");
  if (!isObject(contract.rhythm)) die("contract.rhythm is required");
  if (!isObject(contract.structure)) die("contract.structure is required");

  const durationSec = contract.track.duration_sec;
  if (typeof durationSec !== "number" || !Number.isFinite(durationSec) || durationSec <= 0) {
    die("track.duration_sec must be a finite positive number of seconds");
  }

  if (!Array.isArray(contract.rhythm.beats)) die("rhythm.beats is required");
  if (!Array.isArray(contract.rhythm.downbeats)) die("rhythm.downbeats is required");
  if (!Array.isArray(contract.structure.segments)) die("structure.segments is required");

  const beats = contract.rhythm.beats;
  const downbeats = contract.rhythm.downbeats;

  for (let i = 0; i < beats.length; i++) {
    assertFiniteSeconds(beats[i], `rhythm.beats[${i}]`);
    if (beats[i] > durationSec) die(`rhythm.beats[${i}] exceeds track.duration_sec`);
  }
  assertMonotonicSeconds(beats, "rhythm.beats");

  for (let i = 0; i < downbeats.length; i++) {
    assertFiniteSeconds(downbeats[i], `rhythm.downbeats[${i}]`);
    if (downbeats[i] > durationSec) die(`rhythm.downbeats[${i}] exceeds track.duration_sec`);
    if (!beats.includes(downbeats[i])) {
      die(`rhythm.downbeats[${i}] is not present in rhythm.beats`);
    }
  }
  assertMonotonicSeconds(downbeats, "rhythm.downbeats");

  if (contract.rhythm.beat_positions !== undefined) {
    const bp = contract.rhythm.beat_positions;
    if (!Array.isArray(bp)) die("rhythm.beat_positions must be an array when present");
    if (bp.length !== beats.length) {
      die("rhythm.beat_positions length must match rhythm.beats length");
    }
  }

  const segments = contract.structure.segments;
  let prevEnd = -Infinity;
  for (let i = 0; i < segments.length; i++) {
    const seg = segments[i];
    if (!isObject(seg)) die(`structure.segments[${i}] must be an object`);
    assertFiniteSeconds(seg.start, `structure.segments[${i}].start`);
    assertFiniteSeconds(seg.end, `structure.segments[${i}].end`);
    if (seg.end < seg.start) {
      die(`structure.segments[${i}].end must be >= start`);
    }
    if (seg.start < 0 || seg.end > durationSec) {
      die(`structure.segments[${i}] times must lie within [0, track.duration_sec]`);
    }
    if (seg.start < prevEnd) {
      die(`structure.segments[${i}] overlaps previous segment`);
    }
    prevEnd = seg.end;
    if (typeof seg.label !== "string" || seg.label.length === 0) {
      die(`structure.segments[${i}].label is required`);
    }
  }
}

function validateStemFeatures(stemFeatures, durationSec) {
  if (!isObject(stemFeatures)) die("stem_features must be an object");
  if (stemFeatures.schema !== "stem_features_v1") {
    die(`stem_features schema must be stem_features_v1, got ${stemFeatures.schema}`);
  }

  const fps = stemFeatures.fps;
  if (!Number.isInteger(fps) || fps <= 0 || !Number.isFinite(fps)) {
    die("stem_features fps must be a finite positive integer");
  }

  const featDuration = stemFeatures.duration_sec;
  if (typeof featDuration !== "number" || !Number.isFinite(featDuration)) {
    die("stem_features duration_sec must be a finite number");
  }
  if (Math.abs(featDuration - durationSec) > 1 / fps) {
    die("stem_features duration_sec mismatch vs contract track.duration_sec");
  }

  if (!isObject(stemFeatures.stems)) die("stem_features.stems is required");

  let expectedLen = null;

  for (const stemName of REQUIRED_STEMS) {
    const stem = stemFeatures.stems[stemName];
    if (!isObject(stem)) die(`missing stem: ${stemName}`);

    let stemLen = null;
    for (const key of REQUIRED_STEM_ARRAYS) {
      if (!Array.isArray(stem[key])) die(`stem ${stemName} missing array ${key}`);
      const arr = stem[key];
      if (stemLen === null) stemLen = arr.length;
      if (arr.length !== stemLen) {
        die(`unequal array lengths within stem ${stemName} (${key} length ${arr.length})`);
      }
      if (expectedLen === null) expectedLen = arr.length;
      if (arr.length !== expectedLen) {
        die(`unequal array lengths across stems (expected ${expectedLen}, ${stemName}.${key} has ${arr.length})`);
      }
      for (let i = 0; i < arr.length; i++) {
        const v = Number(arr[i]);
        if (!Number.isFinite(v)) {
          die(`non-finite value in ${stemName}.${key}[${i}]`);
        }
        if (v < 0) {
          die(`negative value in ${stemName}.${key}[${i}]`);
        }
      }
    }
  }
}

/**
 * @param {object} contract Trinity Contract JSON
 * @param {object} stemFeatures stem_features_v1 JSON
 * @returns {import('./trinity_contract_adapter_v1.js').CanonicalEvidence}
 */
export function adaptTrinityContract(contract, stemFeatures) {
  validateContract(contract);
  const durationSec = contract.track.duration_sec;
  validateStemFeatures(stemFeatures, durationSec);

  const duration_us = secondsToUs(durationSec);
  const fps = stemFeatures.fps;

  const beats_us = contract.rhythm.beats.map((b) => secondsToUs(b));
  const downbeats_us = contract.rhythm.downbeats.map((b) => secondsToUs(b));

  const segments = contract.structure.segments.map((seg) => ({
    t_us: secondsToUs(seg.start),
    t1_us: secondsToUs(seg.end),
    label: seg.label.slice(0, 64),
  }));

  const stems = {};
  for (const stemName of REQUIRED_STEMS) {
    const src = stemFeatures.stems[stemName];
    stems[stemName] = {
      rms: src.rms.map(Number),
      onset_strength: src.onset_strength.map(Number),
      band_energy_low: src.band_energy_low.map(Number),
      band_energy_mid: src.band_energy_mid.map(Number),
      band_energy_high: src.band_energy_high.map(Number),
    };
  }

  return {
    duration_us,
    fps,
    beats_us,
    downbeats_us,
    segments,
    stems,
  };
}
