#!/usr/bin/env node
/**
 * compose.mjs — M2 lane C composition driver (host only, no device contact).
 *
 * Composition format = Spine `instrument_project_v1` (inputs: contract, stem_features,
 * mapping profile, each with sha256) + Spine `mapping_profile_v1`. This is the
 * project/profile layer the Spine CLI verifies and the PRISM editor's profile select
 * names. Paths inside a composition are relative to the composition file's folder.
 *
 * Why a driver instead of `./bin/instrument verify --project`: the Spine CLI hard-codes
 * `mapping/prim8_natural_v1.json` and writes into its own `.tmp/`, and the PRISM editor's
 * `/api/instrument/compile` passes flags the 0.3.1 compiler does not accept. This driver
 * performs the Spine `compileOnce` + `verifyFixture` steps verbatim (same compiler flags,
 * same cwd, same replay call, Spine's own coverage/project/profile validators imported
 * read-only), with outputs under the caller's --out folder only.
 *
 * Commands:
 *   init    --project P --contract C --stems S --schema-sha-file F --profile M [--wav W]
 *   edit    --project P --set dotted.path=JSON [--set ...] --id ID --version V --note TEXT --out-profile REL
 *   compile --project P --out DIR [--record]     compile twice (A04), coverage, integrity, replay x2
 *   verify  --project P --out DIR                 reopen: recompile and require equality with recorded outputs
 */
import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, writeFileSync, rmSync, copyFileSync } from "node:fs";
import { dirname, join, resolve, relative } from "node:path";

const SPINE = "/Users/spectrasynq/Workspace_Management/Software/SpectraSynq-Instrument-Spine";
const PRISM = "/Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/k1-fe-show-m1_20261109/prism-studio-locked";
const LOCKED_PRISM_COMMIT = "cc00556d1df2f863c6a0d914ef613886b050a408";
const HZ = 120;

const { sha256File, sha256Utf8 } = await import(join(SPINE, "tools/hash.mjs"));
const { evaluateCoverage } = await import(join(SPINE, "tools/mapping_coverage.mjs"));
const { validateProject } = await import(join(SPINE, "tools/validate_project.mjs"));
const { validateProfile } = await import(join(SPINE, "tools/validate_profile.mjs"));

function die(msg, code = 2) {
  console.error(`COMPOSE: FAIL ${msg}`);
  process.exit(code);
}
const loadJson = (p) => JSON.parse(readFileSync(p, "utf8"));
const writeJson = (p, o) => {
  mkdirSync(dirname(p), { recursive: true });
  writeFileSync(p, JSON.stringify(o, null, 2) + "\n");
};
function argValue(argv, name) {
  const i = argv.indexOf(name);
  return i < 0 ? null : argv[i + 1] ?? null;
}
function argValues(argv, name) {
  const out = [];
  argv.forEach((a, i) => { if (a === name) out.push(argv[i + 1]); });
  return out;
}
function run(cmd, args, opts = {}) {
  const r = spawnSync(cmd, args, { encoding: "utf8", ...opts });
  if (r.status !== 0) die(`command failed (${cmd} ${args.join(" ")}):\n${r.stdout}\n${r.stderr}`, r.status ?? 2);
  return r;
}

function prismIdentity() {
  const head = run("/usr/bin/git", ["-C", PRISM, "rev-parse", "HEAD"]).stdout.trim();
  const dirty = run("/usr/bin/git", ["-C", PRISM, "status", "--porcelain"]).stdout.trim().length > 0;
  if (head !== LOCKED_PRISM_COMMIT) die(`PRISM clone HEAD ${head} != locked ${LOCKED_PRISM_COMMIT}`);
  if (dirty) die("PRISM clone is dirty");
  const lock = loadJson(join(SPINE, "organs.lock.json"));
  if (lock.organs.prism.commit !== head) die("Spine organs.lock prism commit != clone HEAD");
  return { locked_commit: lock.organs.prism.commit, effective_commit: head, dirty, root: PRISM };
}

function resolveProject(projectPath) {
  const projAbs = resolve(projectPath);
  const base = dirname(projAbs);
  const project = loadJson(projAbs);
  const vr = validateProject(project);
  if (!vr.ok) die(`PROJECT_INVALID: ${vr.errors.join("; ")}`);
  const abs = (rel) => resolve(base, rel);
  const paths = {
    projAbs,
    base,
    contract: abs(project.inputs.contract_path),
    stems: abs(project.inputs.stem_features_path),
    profile: abs(project.inputs.mapping_profile_path),
    schemaShaFile: abs(project.inputs.contract_schema_sha256_path),
  };
  // Input integrity: every recorded input hash must match the bytes on disk.
  const checks = [
    ["contract_sha256", paths.contract],
    ["stem_features_sha256", paths.stems],
    ["mapping_profile_sha256", paths.profile],
  ];
  for (const [k, p] of checks) {
    if (!existsSync(p)) die(`missing input ${p}`);
    if (sha256File(p) !== project.inputs[k]) die(`INPUT_HASH_MISMATCH ${k}`);
  }
  const profile = loadJson(paths.profile);
  const pr = validateProfile(profile);
  if (!pr.ok) die(`PROFILE_INVALID: ${pr.errors.join("; ")}`);
  if (profile.id !== project.mapping_profile_id) die("mapping_profile_id != profile.id");
  return { project, paths, profile };
}

function cmdInit(argv) {
  const projectPath = resolve(argValue(argv, "--project"));
  const base = dirname(projectPath);
  const rel = (p) => relative(base, resolve(p));
  const contract = argValue(argv, "--contract");
  const stems = argValue(argv, "--stems");
  const schemaShaFile = argValue(argv, "--schema-sha-file");
  const profilePath = argValue(argv, "--profile");
  const wav = argValue(argv, "--wav");
  const profile = loadJson(profilePath);
  const project = {
    schema: "instrument_project_v1",
    version: "1.0.0",
    mapping_profile_id: profile.id,
    organs_lock_sha256: sha256File(join(SPINE, "organs.lock.json")),
    inputs: {
      contract_path: rel(contract),
      contract_sha256: sha256File(contract),
      stem_features_path: rel(stems),
      stem_features_sha256: sha256File(stems),
      contract_schema_sha256_path: rel(schemaShaFile),
      mapping_profile_path: rel(profilePath),
      mapping_profile_sha256: sha256File(profilePath),
      ...(wav ? { asset_path: rel(wav), asset_sha256: sha256File(wav) } : {}),
    },
    stream: { hz: HZ, device_profile: "none", passage_start_sample: 0 },
    edits: [],
    outputs: null,
    verification: { status: "UNVERIFIED", trace_sha256: null },
  };
  writeJson(projectPath, project);
  console.log(`INIT: wrote ${projectPath}`);
}

function setDotted(obj, dotted, value) {
  const keys = dotted.split(".");
  let o = obj;
  for (const k of keys.slice(0, -1)) {
    if (!(k in o)) die(`EDIT_PATH_MISSING ${dotted}`);
    o = o[k];
  }
  const last = keys[keys.length - 1];
  if (!(last in o)) die(`EDIT_PATH_MISSING ${dotted}`);
  const before = o[last];
  o[last] = value;
  return before;
}

function cmdEdit(argv) {
  const { project, paths, profile } = resolveProject(argValue(argv, "--project"));
  const sets = argValues(argv, "--set");
  if (!sets.length) die("edit needs --set");
  const id = argValue(argv, "--id");
  const version = argValue(argv, "--version");
  const note = argValue(argv, "--note");
  const outRel = argValue(argv, "--out-profile");
  if (!id || !version || !note || !outRel) die("edit needs --id --version --note --out-profile");
  const next = JSON.parse(JSON.stringify(profile));
  const changes = [];
  for (const s of sets) {
    const eq = s.indexOf("=");
    const path = s.slice(0, eq);
    const value = JSON.parse(s.slice(eq + 1));
    const before = setDotted(next, path, value);
    changes.push({ path, before, after: value });
  }
  next.id = id;
  next.version = version;
  next.derived_from = { id: profile.id, version: profile.version, sha256: project.inputs.mapping_profile_sha256 };
  next.edit_note = note;
  const pr = validateProfile(next);
  if (!pr.ok) die(`EDITED_PROFILE_INVALID: ${pr.errors.join("; ")}`);
  const outAbs = resolve(paths.base, outRel);
  writeJson(outAbs, next);
  project.edits.push({
    seq: project.edits.length + 1,
    layer: "mapping_profile",
    from_profile: { id: profile.id, sha256: project.inputs.mapping_profile_sha256 },
    to_profile: { id, path: outRel, sha256: sha256File(outAbs) },
    changes,
    note,
  });
  project.mapping_profile_id = id;
  project.inputs.mapping_profile_path = outRel;
  project.inputs.mapping_profile_sha256 = sha256File(outAbs);
  project.outputs = null;
  project.verification = { status: "UNVERIFIED", trace_sha256: null };
  writeJson(paths.projAbs, project);
  console.log(`EDIT: saved ${paths.projAbs}`);
  console.log(JSON.stringify(changes));
}

function compileOnce(prism, paths, outDir) {
  rmSync(outDir, { recursive: true, force: true });
  mkdirSync(outDir, { recursive: true });
  const compiler = join(prism.root, "tools/trinity_compile_showbundle_v0_3.js");
  const schemaSha = readFileSync(paths.schemaShaFile, "utf8").trim();
  const o = {
    bundle: join(outDir, "showbundle.json"),
    cov: join(outDir, "mapping_coverage.json"),
    man: join(outDir, "compile_manifest.json"),
    build: join(outDir, "build_manifest.json"),
    trace: join(outDir, "trace_120hz.jsonl"),
  };
  // Identical argument list and cwd to Spine tools/instrument.mjs compileOnce().
  run(process.execPath, [
    compiler, "--in", paths.contract, "--profile", paths.profile, "--stems", paths.stems,
    "--out", o.bundle, "--coverage-out", o.cov, "--manifest-out", o.man,
    "--schema-sha", schemaSha, "--compiler-commit", prism.effective_commit,
  ], { cwd: "/tmp" });
  const man = loadJson(o.man);
  writeJson(o.build, {
    schema: "build_manifest_v1",
    prism: { locked_commit: prism.locked_commit, effective_commit: prism.effective_commit, dirty: prism.dirty },
    mapping_profile_sha256: sha256File(paths.profile),
    contract_sha256: sha256File(paths.contract),
    stem_features_sha256: sha256File(paths.stems),
    contract_schema_sha256: schemaSha,
    compiler_version: `${man.compiler.id}/${man.compiler.version}`,
  });
  // Same replay call as Spine replayTrace(): tools/showbundle_replay.js --hz 120, cwd = PRISM root.
  run(process.execPath, [join(prism.root, "tools/showbundle_replay.js"), "--in", o.bundle, "--hz", String(HZ), "--out", o.trace], { cwd: prism.root });
  return o;
}

function compileAndCheck(projectArg, outDir) {
  const prism = prismIdentity();
  const { project, paths, profile } = resolveProject(projectArg);
  const a = compileOnce(prism, paths, join(outDir, "run-a"));
  const b = compileOnce(prism, paths, join(outDir, "run-b"));
  for (const k of ["bundle", "cov", "man", "build", "trace"]) {
    if (!readFileSync(a[k]).equals(readFileSync(b[k]))) die(`A04 ${k} A/B bytes differ`);
  }
  const man = loadJson(a.man);
  const build = loadJson(a.build);
  const errs = [];
  const chk = (l, x, y) => { if (x !== y) errs.push(`${l}: ${x} !== ${y}`); };
  chk("contract.sha256", sha256File(paths.contract), man.contract.sha256);
  chk("stem_features.sha256", sha256File(paths.stems), man.stem_features.sha256);
  chk("profile.sha256", sha256File(paths.profile), man.mapping_profile.sha256);
  chk("showbundle_sha256", sha256File(a.bundle), man.outputs.showbundle_sha256);
  chk("coverage_sha256", sha256File(a.cov), man.outputs.mapping_coverage_sha256);
  chk("compiler.commit", man.compiler.commit, build.prism.effective_commit);
  chk("schema_sha256", man.contract.schema_sha256, readFileSync(paths.schemaShaFile, "utf8").trim());
  chk("profile.id", man.mapping_profile.id, profile.id);
  if (errs.length) die(`MANIFEST_INTEGRITY\n${errs.join("\n")}`);
  const gate = evaluateCoverage(loadJson(a.cov));
  if (!gate.ok) die(`COVERAGE ${gate.errors.join("; ")}`);
  const bundle = loadJson(a.bundle);
  if ((bundle.device_profile ?? "none") !== "none") die(`device_profile ${bundle.device_profile} != none`);
  const outputs = {
    showbundle_sha256: sha256File(a.bundle),
    trace_sha256: sha256File(a.trace),
    mapping_coverage_sha256: sha256File(a.cov),
    compile_manifest_sha256: sha256File(a.man),
    build_manifest_sha256: sha256File(a.build),
    hz: HZ,
    duration_us: bundle.duration_us,
  };
  return { project, paths, outputs, a };
}

function printOutputs(tag, outputs) {
  console.log(`${tag}: PASS`);
  for (const [k, v] of Object.entries(outputs)) console.log(`${k.toUpperCase()}=${v}`);
}

function cmdCompile(argv) {
  const projectArg = argValue(argv, "--project");
  const outDir = resolve(argValue(argv, "--out"));
  const { project, paths, outputs } = compileAndCheck(projectArg, outDir);
  writeJson(join(outDir, "outputs.json"), outputs);
  if (argv.includes("--record")) {
    project.outputs = { ...outputs, recorded_from: relative(paths.base, outDir) };
    project.verification = { status: "VERIFIED", trace_sha256: outputs.trace_sha256 };
    const vr = validateProject(project);
    if (!vr.ok) die(`PROJECT_INVALID after record: ${vr.errors.join("; ")}`);
    writeJson(paths.projAbs, project);
    console.log(`RECORD: saved outputs into ${paths.projAbs}`);
  }
  printOutputs("COMPILE", outputs);
}

function cmdVerify(argv) {
  const projectArg = argValue(argv, "--project");
  const outDir = resolve(argValue(argv, "--out"));
  const { project, outputs } = compileAndCheck(projectArg, outDir);
  writeJson(join(outDir, "outputs.json"), outputs);
  if (!project.outputs || project.verification?.status !== "VERIFIED") die("project has no recorded VERIFIED outputs");
  const diffs = Object.keys(outputs).filter((k) => project.outputs[k] !== outputs[k]);
  if (diffs.length) die(`REOPEN_MISMATCH ${diffs.map((k) => `${k}: recorded ${project.outputs[k]} now ${outputs[k]}`).join("; ")}`);
  printOutputs("VERIFY_REOPEN", outputs);
}

const argv = process.argv.slice(2);
const cmd = argv[0];
if (cmd === "init") cmdInit(argv);
else if (cmd === "edit") cmdEdit(argv);
else if (cmd === "compile") cmdCompile(argv);
else if (cmd === "verify") cmdVerify(argv);
else die("usage: compose.mjs init|edit|compile|verify");
