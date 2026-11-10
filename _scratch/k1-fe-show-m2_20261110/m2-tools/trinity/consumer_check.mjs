// TRINITY-FIX consumer acceptance: feed a RAW Trinity contract (no correction layer) to the PRISM
// adapter and the locked compiler CLI exported from PRISM.studio cc00556d (the Spine organs.lock pin).
// The PRISM files come from `git archive cc00556d` of the locked clone into prism_cc00556d/ (read-only copy).
// Usage: node consumer_check.mjs <run-dir>     e.g. runs/full_A
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const PRISM = join(HERE, "prism_cc00556d");
const SPINE = "/Users/spectrasynq/Workspace_Management/Software/SpectraSynq-Instrument-Spine";
const PROFILE = join(SPINE, "mapping/prim8_natural_v1.json");
const SCHEMA_SHA = readFileSync(join(SPINE, "fixtures/ci_click_3s/expected/contract_schema.sha256"), "utf8").trim().split(/\s+/)[0];
const run = resolve(process.argv[2]);
const contractName = process.argv[3] || "contract.json";
const contractPath = join(run, contractName);
const stemsPath = join(run, "stem_features.json");
const outDir = join(run, contractName === "contract.json" ? "consumer" : `consumer_${contractName.replace(/\.json$/, "")}`);
mkdirSync(outDir, { recursive: true });
const sha = (p) => createHash("sha256").update(readFileSync(p)).digest("hex");
const prismCommit = readFileSync(join(PRISM, "COMMIT"), "utf8").trim();

const report = { run, prism_commit: prismCommit, profile: PROFILE, profile_sha256: sha(PROFILE), schema_sha256_pinned: SCHEMA_SHA,
  inputs: { contract_sha256: sha(contractPath), stem_features_sha256: sha(stemsPath) }, correction_layer: "none" };

const { adaptTrinityContract, SUPPORTED_CONTRACT_VERSIONS } = await import(pathToFileURL(join(PRISM, "tools/trinity_contract_adapter_v1.js")).href);
report.adapter_supported_versions = SUPPORTED_CONTRACT_VERSIONS;
try {
  const ev = adaptTrinityContract(JSON.parse(readFileSync(contractPath, "utf8")), JSON.parse(readFileSync(stemsPath, "utf8")));
  report.adapter = { result: "PASS", duration_us: ev.duration_us, fps: ev.fps, beats: ev.beats_us.length, downbeats: ev.downbeats_us.length,
    segments: ev.segments.length, last_segment_t1_us: ev.segments.at(-1)?.t1_us, frames: ev.stems.vocals.rms.length,
    canonical_evidence_sha256: createHash("sha256").update(JSON.stringify(ev)).digest("hex") };
} catch (e) {
  report.adapter = { result: "FAIL", error: String(e.message || e) };
}

const args = [join(PRISM, "tools/trinity_compile_showbundle_v0_3.js"), "--in", contractPath, "--profile", PROFILE, "--stems", stemsPath,
  "--out", join(outDir, "showbundle.json"), "--coverage-out", join(outDir, "coverage.json"), "--manifest-out", join(outDir, "compile_manifest.json"),
  "--compiler-commit", prismCommit, "--schema-sha", SCHEMA_SHA];
const r = spawnSync(process.execPath, args, { encoding: "utf8", cwd: outDir });
writeFileSync(join(outDir, "compiler_cli.log"), `cmd: node ${args.join(" ")}\nexit: ${r.status}\n--- stdout\n${r.stdout}\n--- stderr\n${r.stderr}\n`);
report.compiler_cli = { exit: r.status, result: r.status === 0 ? "PASS" : "FAIL", stderr_head: (r.stderr || "").slice(0, 600) };
for (const f of ["showbundle.json", "coverage.json", "compile_manifest.json"]) {
  const p = join(outDir, f);
  if (existsSync(p)) report.compiler_cli[`${f}_sha256`] = sha(p);
}
writeFileSync(join(outDir, "consumer_check.json"), JSON.stringify(report, null, 2) + "\n");
console.log(JSON.stringify(report, null, 2));
process.exit(report.adapter.result === "PASS" && report.compiler_cli.result === "PASS" ? 0 : 1);
