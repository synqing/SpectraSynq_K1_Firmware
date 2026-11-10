/**
 * mapping_profile_v2 (per-section mapping) in the Spine.
 *
 * 1. Rule parity. The section rules exist twice: here (tools/validate_profile.mjs) and in PRISM
 *    (src/mapping_profile.js, enforced by compiler >= 0.4.0). Both repos carry a byte-identical
 *    case list (tests/fixtures/profile_section_cases.json, PRISM fixtures/profile_section_cases.json).
 *    The Spine verdicts are checked against it always; when the resolved PRISM organ has
 *    src/mapping_profile.js the PRISM verdicts are compared case by case as well.
 * 2. The CLI accepts a mapping_profile_v2 project, and never compiles it silently with a compiler
 *    that ignores sections: with the locked PRISM (compiler 0.3.1) build-demo is refused with
 *    SECTIONS_NOT_APPLIED; with a PRISM that applies sections (PRISM_ROOT=<0.4.0 checkout>)
 *    build-demo and verify --project pass and the compile manifest and trace name the section.
 */
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { test } from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";
import { validateProfile } from "../tools/validate_profile.mjs";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const CLI = join(root, "tools/instrument.mjs");
const FIXTURE = join(root, "fixtures/ci_click_3s");
const CASES_PATH = join(root, "tests/fixtures/profile_section_cases.json");
const CASES = JSON.parse(readFileSync(CASES_PATH, "utf8"));
const BASE_PATH = join(root, "mapping/prim8_natural_v1.json");
const sha = (p) => createHash("sha256").update(readFileSync(p)).digest("hex");
const loadJson = (p) => JSON.parse(readFileSync(p, "utf8"));
const cli = (args) => spawnSync(process.execPath, [CLI, ...args], { cwd: root, encoding: "utf8", env: process.env });

function caseProfile(c) {
  const p = loadJson(BASE_PATH);
  p.schema = c.schema;
  if (c.sections === undefined) delete p.sections;
  else p.sections = c.sections;
  return p;
}

const prismRoot = process.env.PRISM_ROOT || loadJson(join(root, "organs.local.json")).paths.prism;
const PRISM_RULES = join(prismRoot || "", "src/mapping_profile.js");
const PRISM_HAS_SECTIONS = !!prismRoot && existsSync(PRISM_RULES);
const doctor = cli(["doctor"]);
const SKIP = doctor.status === 0 ? false : `organs not resolvable here: ${(doctor.stderr || doctor.stdout).trim().split("\n")[0]}`;

test("section rule cases: base profile is the one the cases were written for", () => {
  assert.equal(sha(BASE_PATH), CASES.base_profile_sha256);
  assert.ok(CASES.cases.length >= 20);
});

test("Spine validator gives the recorded verdict on every shared section case", () => {
  for (const c of CASES.cases) {
    const r = validateProfile(caseProfile(c));
    assert.equal(r.ok, c.ok, `${c.name}: ${r.errors.join(" | ")}`);
  }
});

test(
  "PRISM src/mapping_profile.js gives the same verdict as the Spine on every shared case",
  { skip: PRISM_HAS_SECTIONS ? false : `resolved PRISM ${prismRoot} has no src/mapping_profile.js (compiler < 0.4.0)` },
  async () => {
    const prismCases = join(prismRoot, "fixtures/profile_section_cases.json");
    assert.equal(sha(prismCases), sha(CASES_PATH), "PRISM and Spine case lists differ");
    const { validateMappingProfile } = await import(pathToFileURL(PRISM_RULES).href);
    for (const c of CASES.cases) {
      const spine = validateProfile(caseProfile(c));
      const prism = validateMappingProfile(caseProfile(c));
      assert.equal(prism.ok, spine.ok, `${c.name}: PRISM ${prism.errors.join(" | ")} / Spine ${spine.errors.join(" | ")}`);
    }
  },
);

/** A mapping_profile_v2 project over the ci_click_3s fixture (one segment, "full"). */
function sectionProject() {
  const dir = mkdtempSync(join(tmpdir(), "spine-sections-"));
  mkdirSync(join(dir, "mapping"), { recursive: true });
  const profile = loadJson(BASE_PATH);
  profile.schema = "mapping_profile_v2";
  profile.id = "prim8_natural_v2_sectioned";
  profile.version = "2.0.0";
  profile.sections = [
    { id: "full_1", select: { segment_indices: [0], label: "full" }, prim8: { impact: { transform: { beat_amp_u16: 12000 } } } },
  ];
  const profilePath = join(dir, "mapping/prim8_natural_v2_sectioned.json");
  writeFileSync(profilePath, JSON.stringify(profile, null, 2) + "\n");
  const project = {
    schema: "instrument_project_v1",
    version: "1.0.0",
    mapping_profile_id: profile.id,
    inputs: {
      contract_path: join(FIXTURE, "contract.json"),
      contract_sha256: sha(join(FIXTURE, "contract.json")),
      stem_features_path: join(FIXTURE, "stem_features.json"),
      stem_features_sha256: sha(join(FIXTURE, "stem_features.json")),
      contract_schema_sha256_path: join(FIXTURE, "expected/contract_schema.sha256"),
      mapping_profile_path: "mapping/prim8_natural_v2_sectioned.json",
      mapping_profile_sha256: sha(profilePath),
    },
    stream: { hz: 120, device_profile: "none", passage_start_sample: 0 },
    outputs: {},
    verification: { status: "UNVERIFIED", trace_sha256: null },
  };
  const projectPath = join(dir, "instrument_project.json");
  writeFileSync(projectPath, JSON.stringify(project, null, 2) + "\n");
  return { dir, projectPath, project };
}

test(
  "build-demo refuses a mapping_profile_v2 project when the PRISM compiler ignores sections",
  { skip: SKIP || (PRISM_HAS_SECTIONS ? "resolved PRISM applies sections (see the next test)" : false) },
  () => {
    const { dir, projectPath } = sectionProject();
    try {
      const r = cli(["build-demo", "--project", projectPath, "--out", join(dir, "out")]);
      assert.notEqual(r.status, 0, r.stdout);
      assert.match(r.stderr, /SECTIONS_NOT_APPLIED: .*full_1/);
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  },
);

test(
  "build-demo and verify --project accept a mapping_profile_v2 project; manifest and trace name the section",
  { skip: SKIP || (PRISM_HAS_SECTIONS ? false : `resolved PRISM ${prismRoot} does not apply sections`) },
  () => {
    const { dir, projectPath, project } = sectionProject();
    try {
      const b = cli(["build-demo", "--project", projectPath, "--out", join(dir, "build")]);
      assert.equal(b.status, 0, b.stdout + b.stderr);
      const man = loadJson(join(dir, "build/compile_manifest.json"));
      assert.equal(man.mapping_profile.schema, "mapping_profile_v2");
      assert.deepEqual(man.mapping_profile.sections.map((s) => s.id), ["full_1"]);
      const bundle = loadJson(join(dir, "build/showbundle.json"));
      assert.equal(bundle.version, "0.4");
      // Record the build's hashes, then verify rebuilds the same bytes from the project's inputs.
      project.outputs = {
        showbundle_sha256: sha(join(dir, "build/showbundle.json")),
        mapping_coverage_sha256: sha(join(dir, "build/mapping_coverage.json")),
        compile_manifest_sha256: sha(join(dir, "build/compile_manifest.json")),
      };
      const v0 = cli(["verify", "--project", projectPath, "--out", join(dir, "v0")]);
      assert.notEqual(v0.status, 0, "no recorded trace yet");
      const traceSha = (v0.stdout.match(/TRACE_SHA256=([0-9a-f]{64})/) || [])[1];
      assert.ok(traceSha, v0.stdout + v0.stderr);
      project.outputs.trace_sha256 = traceSha;
      project.verification = { status: "VERIFIED", trace_sha256: traceSha };
      writeFileSync(projectPath, JSON.stringify(project, null, 2) + "\n");
      const v = cli(["verify", "--project", projectPath, "--out", join(dir, "verify")]);
      assert.equal(v.status, 0, v.stdout + v.stderr);
      assert.match(v.stdout, /VERIFY_PROJECT: PASS/);
      const rows = readFileSync(join(dir, "verify/run-a/trace.jsonl"), "utf8").trim().split("\n").map((l) => JSON.parse(l));
      assert.ok(rows.length > 0 && rows.every((r) => r.section === "full_1"), "every frame lies in segment 0 and names its section");
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  },
);
