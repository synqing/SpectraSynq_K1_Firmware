import fs from "node:fs";
import path from "node:path";
import { createHash } from "node:crypto";
import { loadShowBundle } from "../src/vm.js";
import { adaptTrinityContract } from "./trinity_contract_adapter_v1.js";
import { applyTransform } from "./mapping_transforms_v1.js";
import { evaluateCoverage, buildCoverageReport } from "./mapping_coverage_v1.js";

const COMPILER_ID = "spectrasynq.compiler.trinity-showbundle";
const COMPILER_VERSION = "0.3.1";

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

function sha256Bytes(buf) {
  return createHash("sha256").update(buf).digest("hex");
}

function sha256File(filePath) {
  return sha256Bytes(fs.readFileSync(filePath));
}

function sha256Utf8(text) {
  return sha256Bytes(Buffer.from(text, "utf8"));
}

function extractStemSeries(evidence, stem, feature) {
  return evidence.stems[stem][feature];
}

function aggregateStemFeature(evidence, source) {
  const stems = source.stems;
  const feature = source.feature;
  const reduce = source.reduce ?? "mean";
  const len = evidence.stems[stems[0]][feature].length;
  const out = new Array(len).fill(0);

  for (const stemName of stems) {
    const series = extractStemSeries(evidence, stemName, feature);
    for (let i = 0; i < len; i++) out[i] += series[i];
  }

  if (reduce === "mean") {
    for (let i = 0; i < len; i++) out[i] /= stems.length;
  }
  return out;
}

function resolveSourceSeries(source, evidence) {
  switch (source.type) {
    case "stem_feature":
      return extractStemSeries(evidence, source.stem, source.feature);
    case "stem_feature_aggregate":
      return aggregateStemFeature(evidence, source);
    case "stem_feature_ratio": {
      const numerator = extractStemSeries(evidence, source.numerator.stem, source.numerator.feature);
      const denominator = aggregateStemFeature(evidence, source.denominator);
      return { numerator, denominator };
    }
    case "rhythm_events":
      return null;
    case "constant":
      return null;
    default:
      throw new Error(`unsupported source type: ${source.type}`);
  }
}

function buildDimContext(evidence, transform) {
  const ctx = {
    beats_us: evidence.beats_us,
    downbeats_us: evidence.downbeats_us,
  };
  if (transform?.activity) {
    const activity = resolveSourceSeries(transform.activity, evidence);
    if (!Array.isArray(activity)) {
      throw new Error("transform.activity must resolve to a numeric series");
    }
    ctx.activity = activity;
  }
  return ctx;
}

function buildPrim8Curves(evidence, profile) {
  const curves = {};

  for (const name of PRIM8_KEYS) {
    const dim = profile.prim8[name];
    if (!dim) continue;

    const { source, transform } = dim;
    const series = resolveSourceSeries(source, evidence);
    const ctx = buildDimContext(evidence, transform);
    curves[name] = applyTransform(series, transform, evidence.duration_us, evidence.fps, ctx);
  }

  return curves;
}

function buildManifest({
  contractSha,
  stemSha,
  profileSha,
  showbundleSha,
  coverageSha,
  contractVersion,
  profile,
  compilerCommit,
  schemaSha,
}) {
  return {
    schema: "compile_manifest_v1",
    compiler: {
      id: COMPILER_ID,
      version: COMPILER_VERSION,
      commit: compilerCommit,
    },
    contract: {
      version: contractVersion,
      sha256: contractSha,
      schema_sha256: schemaSha,
    },
    stem_features: {
      schema: "stem_features_v1",
      sha256: stemSha,
    },
    mapping_profile: {
      id: profile.id,
      version: profile.version,
      sha256: profileSha,
    },
    outputs: {
      showbundle_sha256: showbundleSha,
      mapping_coverage_sha256: coverageSha,
    },
    consumed: [
      "rhythm.beats",
      "rhythm.downbeats",
      "structure.segments",
      "stem_features.stems.*",
    ],
    unavailable: ["stereo_balance", "harmonic_complexity", "spectral_centroid"],
  };
}

/**
 * @param {object} contract
 * @param {object} profile
 * @param {object} stemFeatures
 * @param {object} opts
 * @param {string} opts.compilerCommit 40-char hex
 * @param {string} opts.schemaSha 64-char hex
 * @param {string} [opts.contractRef] stem_ref basename
 * @param {string} [opts.contractSha256]
 * @param {string} [opts.stemSha256]
 * @param {string} [opts.profileSha256]
 */
export function compileContractToShowBundle(contract, profile, stemFeatures, opts) {
  const evidence = adaptTrinityContract(contract, stemFeatures);
  const prim8_curves = buildPrim8Curves(evidence, profile);

  const coverage = buildCoverageReport(profile, prim8_curves, {
    beats_us: evidence.beats_us,
    downbeats_us: evidence.downbeats_us,
  });

  const gate = evaluateCoverage(coverage);
  if (!gate.ok) {
    throw new Error(`coverage gate failed: ${gate.errors.join("; ")}`);
  }

  const bundle = {
    version: "0.3",
    timebase: { unit: "us" },
    duration_us: evidence.duration_us,
    device_profile: profile.device_profile ?? "none",
    tracks: [
      {
        id: "LT1",
        type: "lighttrack",
        enabled: true,
        gain_u16: 65535,
        prim8_curves,
      },
      {
        id: "STEM_MIX",
        type: "stemtrack",
        enabled: true,
        stem_role: "mix",
        stem_ref: opts.contractRef ?? "contract.json",
      },
    ],
    segments: evidence.segments,
  };

  const bundleJson = JSON.stringify(bundle, null, 2) + "\n";
  const coverageJson = JSON.stringify(coverage, null, 2) + "\n";

  const contractSha = opts.contractSha256 ?? sha256Utf8(JSON.stringify(contract));
  const stemSha = opts.stemSha256 ?? sha256Utf8(JSON.stringify(stemFeatures));
  const profileSha = opts.profileSha256 ?? sha256Utf8(JSON.stringify(profile));
  const showbundleSha = sha256Utf8(bundleJson);
  const coverageSha = sha256Utf8(coverageJson);

  const manifest = buildManifest({
    contractSha,
    stemSha,
    profileSha,
    showbundleSha,
    coverageSha,
    contractVersion: contract.version,
    profile,
    compilerCommit: opts.compilerCommit,
    schemaSha: opts.schemaSha,
  });

  return { bundle, coverage, manifest, bundleJson, coverageJson, manifestJson: JSON.stringify(manifest) };
}

function die(msg) {
  console.error(`[compile:trinity:v0.3] ERROR: ${msg}`);
  process.exit(2);
}

function arg(name) {
  const idx = process.argv.indexOf(name);
  if (idx === -1) return null;
  return process.argv[idx + 1] ?? null;
}

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf-8"));
}

function main() {
  const contractPath = arg("--in");
  const profilePath = arg("--profile");
  const stemsPath = arg("--stems");
  const outPath = arg("--out");
  const coverageOut = arg("--coverage-out");
  const manifestOut = arg("--manifest-out");
  const compilerCommit = arg("--compiler-commit");
  const schemaSha = arg("--schema-sha");

  if (!profilePath) die("mapping profile required");
  if (!compilerCommit) die("COMPILER_COMMIT_REQUIRED");
  if (!schemaSha) die("schema-sha required");

  if (!/^[0-9a-f]{40}$/.test(compilerCommit)) {
    die("--compiler-commit must be 40 lowercase hex characters");
  }
  if (!/^[0-9a-f]{64}$/.test(schemaSha)) {
    die("--schema-sha must be 64 lowercase hex characters");
  }

  if (!contractPath || !stemsPath || !outPath || !coverageOut || !manifestOut) {
    die(
      "Usage: node tools/trinity_compile_showbundle_v0_3.js --in <contract.json> --profile <profile.json> --stems <stem_features.json> --out <bundle.json> --coverage-out <coverage.json> --manifest-out <manifest.json> --compiler-commit <40hex> --schema-sha <64hex>",
    );
  }

  const contract = readJson(contractPath);
  const profile = readJson(profilePath);
  const stemFeatures = readJson(stemsPath);

  const contractRef = path.basename(contractPath);
  const contractSha256 = sha256File(contractPath);
  const stemSha256 = sha256File(stemsPath);
  const profileSha256 = sha256File(profilePath);

  const result = compileContractToShowBundle(contract, profile, stemFeatures, {
    compilerCommit,
    schemaSha,
    contractRef,
    contractSha256,
    stemSha256,
    profileSha256,
  });

  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  fs.writeFileSync(outPath, result.bundleJson, "utf-8");
  fs.writeFileSync(coverageOut, result.coverageJson, "utf-8");
  fs.writeFileSync(manifestOut, result.manifestJson + "\n", "utf-8");

  // Validate via VM
  loadShowBundle(outPath);

  console.log("[compile:trinity:v0.3] OK");
  console.log(`  contract:  ${contractPath}`);
  console.log(`  profile:   ${profilePath}`);
  console.log(`  stems:     ${stemsPath}`);
  console.log(`  out:       ${outPath}`);
  console.log(`  duration:  ${result.bundle.duration_us} us`);
}

import { fileURLToPath } from "node:url";

const selfPath = fs.realpathSync(fileURLToPath(import.meta.url));
const argvPath = process.argv[1] ? fs.realpathSync(process.argv[1]) : "";
if (selfPath === argvPath) {
  main();
}
