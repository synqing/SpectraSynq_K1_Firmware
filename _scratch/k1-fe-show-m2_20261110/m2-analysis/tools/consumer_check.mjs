// M2 lane A consumer acceptance: feed the published artefacts to the PRISM adapter (in-process)
// and to the locked compiler CLI (child process). Read-only over PRISM/Spine; outputs under m2-analysis/raw/compile/.
// Usage: node tools/consumer_check.mjs <view>   where view = full | passage_75_155
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { mkdirSync, readFileSync, writeFileSync, existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const LANE = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const PRISM = "/Users/spectrasynq/Workspace_Management/Software/.g5r-clean/PRISM.studio"; // Spine organs.local.json paths.prism
const SPINE = "/Users/spectrasynq/Workspace_Management/Software/SpectraSynq-Instrument-Spine";
const PROFILE = join(SPINE, "mapping/prim8_natural_v1.json"); // frozen 1.0.0 (v1_1 is PROPOSAL)
const SCHEMA_SHA = readFileSync(join(SPINE, "fixtures/ci_click_3s/expected/contract_schema.sha256"), "utf8").trim();

const view = process.argv[2] || "full";
// full = raw Trinity contract; consumer = raw contract + disclosed clamp (out/loreen/consumer/corrections.json)
const src = view === "full" || view === "consumer" ? join(LANE, "out/loreen") : join(LANE, "out/loreen", view);
const contractPath = view === "consumer" ? join(src, "consumer/contract.json") : join(src, "contract.json");
const stemsPath = join(src, "stem_features.json");
const outDir = join(LANE, "raw/compile", view);
mkdirSync(outDir, { recursive: true });

const sha = (p) => createHash("sha256").update(readFileSync(p)).digest("hex");
const git = (args) => spawnSync("/usr/bin/git", ["-C", PRISM, ...args], { encoding: "utf8" });
const prismHead = git(["rev-parse", "HEAD"]).stdout.trim();

const report = { view, prism_root: PRISM, prism_head: prismHead, profile: PROFILE, profile_sha256: sha(PROFILE), schema_sha256_pinned: SCHEMA_SHA,
  inputs: { contract_sha256: sha(contractPath), stem_features_sha256: sha(stemsPath) } };

// 1. Adapter, in-process
const { adaptTrinityContract } = await import(pathToFileURL(join(PRISM, "tools/trinity_contract_adapter_v1.js")).href);
try {
  const ev = adaptTrinityContract(JSON.parse(readFileSync(contractPath, "utf8")), JSON.parse(readFileSync(stemsPath, "utf8")));
  report.adapter = { result: "PASS", duration_us: ev.duration_us, fps: ev.fps, beats: ev.beats_us.length, downbeats: ev.downbeats_us.length,
    segments: ev.segments.length, frames: ev.stems.vocals.rms.length,
    canonical_evidence_sha256: createHash("sha256").update(JSON.stringify(ev)).digest("hex") };
} catch (e) {
  report.adapter = { result: "FAIL", error: String(e.message || e) };
}

// 2. Locked compiler CLI (runs its own adapter + IMPACT_ONLY coverage gate)
const args = [join(PRISM, "tools/trinity_compile_showbundle_v0_3.js"), "--in", contractPath, "--profile", PROFILE, "--stems", stemsPath,
  "--out", join(outDir, "showbundle.json"), "--coverage-out", join(outDir, "coverage.json"), "--manifest-out", join(outDir, "compile_manifest.json"),
  "--compiler-commit", prismHead, "--schema-sha", SCHEMA_SHA];
const r = spawnSync(process.execPath, args, { encoding: "utf8", cwd: outDir });
writeFileSync(join(outDir, "compiler_cli.log"), `cmd: node ${args.join(" ")}\nexit: ${r.status}\n--- stdout\n${r.stdout}\n--- stderr\n${r.stderr}\n`);
report.compiler_cli = { exit: r.status, result: r.status === 0 ? "PASS" : "FAIL", stderr_head: (r.stderr || "").slice(0, 600) };
for (const f of ["showbundle.json", "coverage.json", "compile_manifest.json"]) {
  const p = join(outDir, f);
  if (existsSync(p)) report.compiler_cli[`${f}_sha256`] = sha(p);
}
writeFileSync(join(outDir, "consumer_check.json"), JSON.stringify(report, null, 2) + "\n");
console.log(JSON.stringify(report, null, 2));
process.exit(report.adapter.result === "PASS" ? 0 : 1);
