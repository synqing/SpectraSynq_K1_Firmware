// Per-section mapping (mapping_profile_v2, compiler 0.4.0, ShowBundle 0.4) and the K1 FE byte
// guards in the editor (Composer K1CT, :set_mode). No device, no serial port: the editor server
// runs on 127.0.0.1 with a temporary fixture project.

import assert from "node:assert/strict";
import { test, after } from "node:test";
import { spawn } from "node:child_process";
import { createHash } from "node:crypto";
import fs from "node:fs";
import net from "node:net";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { evalCurveU16, normaliseBundleObj, replayToJsonl } from "../src/vm.js";
import { validateMappingProfile, resolveSections } from "../src/mapping_profile.js";
import { spliceCurve } from "./section_splice.js";
import { compileContractToShowBundle } from "./trinity_compile_showbundle_v0_3.js";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const COMMIT = "a".repeat(40);
const SCHEMA_SHA = "b".repeat(64);
const T = { timeout: 30_000 };
const sha256 = (b) => createHash("sha256").update(b).digest("hex");
const readJson = (p) => JSON.parse(fs.readFileSync(p, "utf8"));
const writeJson = (p, o) => fs.writeFileSync(p, JSON.stringify(o, null, 2) + "\n");
const BASE = readJson(path.join(root, "mapping/prim8_natural_v1.json"));

// Three segments; beats every 0.25 s, downbeats every 1 s, so every segment has weak beats.
function makeContract() {
  const beats = Array.from({ length: 12 }, (_, i) => i * 0.25);
  return {
    version: "1.0.0",
    track: { duration_sec: 3.0 },
    rhythm: { bpm: 240, beats, downbeats: [0.0, 1.0, 2.0], beat_positions: beats.map((_, i) => (i % 4) + 1) },
    structure: {
      segments: [
        { start: 0.0, end: 1.0, label: "verse" },
        { start: 1.0, end: 2.0, label: "chorus" },
        { start: 2.0, end: 3.0, label: "verse" },
      ],
    },
    blobs: null,
  };
}

function makeStems() {
  const n = 150;
  const mk = (base, onset, lowFn = null) => ({
    rms: Array.from({ length: n }, (_, i) => base + ((i * 7) % 13) * 0.013),
    onset_strength: Array.from({ length: n }, (_, i) => (i % 5 === 0 ? 0.4 + onset : 0.05)),
    band_energy_low: lowFn ? Array.from({ length: n }, (_, i) => lowFn(i)) : Array.from({ length: n }, () => 0.05),
    band_energy_mid: Array.from({ length: n }, () => 0.1),
    band_energy_high: Array.from({ length: n }, () => 0.02),
  });
  return {
    schema: "stem_features_v1",
    fps: 50,
    duration_sec: 3.0,
    stems: {
      vocals: mk(0.1, 0.02),
      drums: mk(0.12, 0.5),
      bass: mk(0.15, 0.03, (i) => (i < 40 ? 0.05 : 0.4 + (i % 9) * 0.01)),
      other: mk(0.08, 0.04),
    },
  };
}

function v2(sections, extra = {}) {
  return { ...JSON.parse(JSON.stringify(BASE)), schema: "mapping_profile_v2", id: "sec_test", ...extra, sections };
}

const CHORUS_IMPACT = {
  id: "chorus_1",
  select: { segment_indices: [1], label: "chorus" },
  prim8: { impact: { transform: { beat_amp_u16: 12000 } } },
};

function compile(profile) {
  return compileContractToShowBundle(makeContract(), profile, makeStems(), {
    compilerCommit: COMMIT,
    schemaSha: SCHEMA_SHA,
    contractRef: "contract.json",
  });
}

function rows(bundle) {
  return replayToJsonl(normaliseBundleObj(bundle), 120).trim().split("\n").map((l) => JSON.parse(l));
}

// ---------------------------------------------------------------------------
// Profile rules
// ---------------------------------------------------------------------------

test("mapping_profile_v2 with one section validates; the v1 base still validates", () => {
  assert.deepEqual(validateMappingProfile(BASE), { ok: true, errors: [] });
  const r = validateMappingProfile(v2([CHORUS_IMPACT]));
  assert.equal(r.ok, true, r.errors.join("\n"));
});

test("profile rules refuse sections in v1, empty overrides, overlaps, provenance changes and unknown keys", () => {
  const cases = [
    [{ ...BASE, sections: [CHORUS_IMPACT] }, /need schema mapping_profile_v2/],
    [v2([]), /non-empty array/],
    [v2([{ ...CHORUS_IMPACT, prim8: {} }]), /SECTION_EMPTY_OVERRIDE/],
    [v2([{ ...CHORUS_IMPACT, prim8: { impact: { transform: { beat_amp_u16: 48000 } } } }]), /SECTION_EMPTY_OVERRIDE changes no/],
    [v2([{ ...CHORUS_IMPACT, prim8: { impact: { notes: "only a note" } } }]), /SECTION_EMPTY_OVERRIDE changes no/],
    [v2([CHORUS_IMPACT, { ...CHORUS_IMPACT, id: "again" }]), /SECTION_OVERLAP segment 1/],
    [v2([CHORUS_IMPACT, { ...CHORUS_IMPACT }]), /duplicate section id/],
    [v2([{ ...CHORUS_IMPACT, prim8: { impact: { provenance: "AUTHORED", transform: { beat_amp_u16: 1 } } } }]), /provenance cannot change/],
    [v2([{ ...CHORUS_IMPACT, select: {} }]), /needs segment_indices, label or time_range_us/],
    [v2([{ ...CHORUS_IMPACT, select: { segment_indices: [1], time_range_us: { t_us: 0, t1_us: 1 } } }]), /exclusive/],
    [v2([{ ...CHORUS_IMPACT, prim8: { colour: { transform: { x: 1 } } } }]), /not a Prim8 dimension/],
    [v2([{ ...CHORUS_IMPACT, prim8: { impact: { transform: { type: "no_such_transform" } } } }]), /bad transform.type/],
    [v2([{ ...CHORUS_IMPACT, when: "chorus" }]), /unknown key when/],
  ];
  for (const [profile, re] of cases) {
    const r = validateMappingProfile(profile);
    assert.equal(r.ok, false, `accepted: ${JSON.stringify(profile.sections)}`);
    assert.ok(r.errors.some((e) => re.test(e)), `${re} not in ${r.errors.join(" | ")}`);
  }
});

test("sections resolve against the contract: unknown segments, label mismatch, off-boundary ranges and overlaps are refused", () => {
  const segs = [
    { t_us: 0, t1_us: 1_000_000, label: "verse" },
    { t_us: 1_000_000, t1_us: 2_000_000, label: "chorus" },
    { t_us: 2_000_000, t1_us: 3_000_000, label: "verse" },
  ];
  const bad = [
    [{ ...CHORUS_IMPACT, select: { segment_indices: [3] } }, "SECTION_UNKNOWN_SEGMENT", /segment 3 does not exist/],
    [{ ...CHORUS_IMPACT, select: { segment_indices: [0], label: "chorus" } }, "SECTION_UNKNOWN_SEGMENT", /labelled "verse", not "chorus"/],
    [{ ...CHORUS_IMPACT, select: { label: "bridge" } }, "SECTION_UNKNOWN_SEGMENT", /no segment is labelled "bridge"/],
    [{ ...CHORUS_IMPACT, select: { time_range_us: { t_us: 1_000_000, t1_us: 1_500_000 } } }, "SECTION_UNKNOWN_SEGMENT", /does not snap/],
  ];
  for (const [s, code, re] of bad) {
    assert.throws(() => resolveSections(v2([s]), segs), (e) => e.code === code && re.test(e.message), JSON.stringify(s.select));
  }
  // Overlap only visible with the contract: a label selection and an index selection of the same segment.
  assert.throws(
    () => resolveSections(v2([{ ...CHORUS_IMPACT, select: { label: "verse" } }, { ...CHORUS_IMPACT, id: "v0", select: { segment_indices: [0] } }]), segs),
    (e) => e.code === "SECTION_OVERLAP",
  );
  // Label "verse" selects segments 0 and 2 (two spans); a range over 1..2 merges into one span.
  const plan = resolveSections(
    v2([
      { ...CHORUS_IMPACT, id: "verses", select: { label: "verse" } },
    ]),
    segs,
  );
  assert.deepEqual(plan[0].segment_indices, [0, 2]);
  assert.deepEqual(plan[0].spans, [{ t_us: 0, t1_us: 1_000_000 }, { t_us: 2_000_000, t1_us: 3_000_000 }]);
  const merged = resolveSections(v2([{ ...CHORUS_IMPACT, id: "late", select: { time_range_us: { t_us: 1_000_000, t1_us: 3_000_000 } } }]), segs);
  assert.deepEqual(merged[0].spans, [{ t_us: 1_000_000, t1_us: 3_000_000 }]);
  assert.deepEqual(resolveSections(BASE, segs), []);
});

test("shared section cases (byte-identical copy in the Spine): every verdict matches", () => {
  // The Spine's tools/validate_profile.mjs carries the same section rules; its
  // tests/profile_rules_parity.test.js checks the same file and compares both validators.
  const cases = readJson(path.join(root, "fixtures/profile_section_cases.json"));
  assert.equal(sha256(fs.readFileSync(path.join(root, "mapping/prim8_natural_v1.json"))), cases.base_profile_sha256);
  for (const c of cases.cases) {
    const p = JSON.parse(JSON.stringify(BASE));
    p.schema = c.schema;
    if (c.sections === undefined) delete p.sections;
    else p.sections = c.sections;
    const r = validateMappingProfile(p);
    assert.equal(r.ok, c.ok, `${c.name}: ${r.errors.join(" | ")}`);
  }
});

// ---------------------------------------------------------------------------
// Splicing is exact at every integer microsecond
// ---------------------------------------------------------------------------

test("spliceCurve: at every integer t the VM value is the owning curve's VM value (sloped cuts, odd boundaries)", () => {
  let seed = 12345;
  const rnd = () => ((seed = (seed * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff);
  const mkCurve = (n, step) => ({
    type: "linear_u16",
    points: Array.from({ length: n }, (_, i) => ({ t_us: i * step, v_u16: Math.floor(rnd() * 65536) })),
  });
  const duration = 20 * 997;
  const base = mkCurve(21, 997);
  const over = mkCurve(21, 997);
  const spans = [{ t_us: 3001, t1_us: 7777 }, { t_us: 7777 + 333, t1_us: 12_345 }];
  const out = spliceCurve(base, spans.map((s) => ({ ...s, curve: over })), duration);
  const owner = (t) => (spans.some((s) => t >= s.t_us && t < s.t1_us) ? over : base);
  for (let t = 0; t < duration; t++) {
    const want = evalCurveU16(owner(t), t);
    const got = evalCurveU16(out, t);
    if (got !== want) assert.fail(`t=${t}: spliced ${got} != owner ${want}`);
  }
  assert.equal(evalCurveU16(out, duration), evalCurveU16(base, duration));
});

test("spliceCurve: falling slopes, falls to 0, cuts on source points and 1 us spans stay exact", () => {
  // The VM returns p1.v_u16 + 1 at p1 on a falling interval longer than 1 us (BigInt division
  // truncates toward zero); the splice must reproduce that, not the stored point values.
  const base = { type: "linear_u16", points: [{ t_us: 0, v_u16: 65535 }, { t_us: 500, v_u16: 3 }, { t_us: 900, v_u16: 0 }, { t_us: 1500, v_u16: 40000 }, { t_us: 2000, v_u16: 0 }] };
  const over = { type: "linear_u16", points: [{ t_us: 0, v_u16: 0 }, { t_us: 700, v_u16: 65535 }, { t_us: 1100, v_u16: 1 }, { t_us: 1600, v_u16: 0 }, { t_us: 2000, v_u16: 9 }] };
  const duration = 2000;
  for (const spans of [
    [{ t_us: 500, t1_us: 900 }],
    [{ t_us: 1, t1_us: 2 }, { t_us: 899, t1_us: 1101 }],
    [{ t_us: 250, t1_us: 1600 }],
    [{ t_us: 0, t1_us: 1999 }],
    [{ t_us: 1100, t1_us: 2000 }],
  ]) {
    const out = spliceCurve(base, spans.map((s) => ({ ...s, curve: over })), duration);
    const owner = (t) => (spans.some((s) => t >= s.t_us && t < s.t1_us) ? over : base);
    for (let t = 0; t < duration; t++) {
      const want = evalCurveU16(owner(t), t);
      const got = evalCurveU16(out, t);
      if (got !== want) assert.fail(`${JSON.stringify(spans)} t=${t}: spliced ${got} != owner ${want}`);
    }
    const ts = out.points.map((p) => p.t_us);
    assert.deepEqual(ts, [...new Set(ts)].sort((a, b) => a - b), "points sorted with unique t_us");
  }
});

// ---------------------------------------------------------------------------
// Compiler 0.4.0
// ---------------------------------------------------------------------------

test("a profile without sections compiles to ShowBundle 0.3 with no sections key (v1 output shape unchanged)", () => {
  const r = compile(BASE);
  assert.equal(r.bundle.version, "0.3");
  assert.equal("sections" in r.bundle, false);
  assert.deepEqual(Object.keys(r.manifest.mapping_profile), ["id", "version", "sha256"]);
  assert.equal(r.manifest.compiler.version, "0.4.0");
  for (const row of rows(r.bundle)) assert.equal("section" in row, false);
});

test("a chorus-only override changes frames only inside the chorus, equal there to the whole-track edit", () => {
  const pre = rows(compile(BASE).bundle);
  const wholeEdited = JSON.parse(JSON.stringify(BASE));
  wholeEdited.prim8.impact.transform.beat_amp_u16 = 12000;
  const post = rows(compile(wholeEdited).bundle);
  const sectioned = compile(v2([CHORUS_IMPACT]));
  assert.equal(sectioned.bundle.version, "0.4");
  assert.deepEqual(sectioned.bundle.sections, [
    { id: "chorus_1", segment_indices: [1], labels: ["chorus"], dims: ["impact"], spans: [{ t_us: 1_000_000, t1_us: 2_000_000 }] },
  ]);
  assert.equal(sectioned.manifest.mapping_profile.schema, "mapping_profile_v2");
  assert.deepEqual(sectioned.manifest.mapping_profile.sections[0].spans, [{ t_us: 1_000_000, t1_us: 2_000_000 }]);
  const got = rows(sectioned.bundle);
  assert.equal(got.length, pre.length);
  let changed = 0;
  for (let i = 0; i < got.length; i++) {
    const inside = got[i].t_us >= 1_000_000 && got[i].t_us < 2_000_000;
    assert.deepEqual(got[i].prim8_u16, (inside ? post : pre)[i].prim8_u16, `frame ${i} t=${got[i].t_us}`);
    assert.equal(got[i].section, inside ? "chorus_1" : undefined, `trace section label at frame ${i}`);
    if (JSON.stringify(got[i].prim8_u16) !== JSON.stringify(pre[i].prim8_u16)) {
      changed++;
      assert.ok(inside, `frame ${i} outside the chorus changed`);
      for (const k of [0, 2, 3, 4, 5, 6, 7]) assert.equal(got[i].prim8_u16[k], pre[i].prim8_u16[k], `non-impact dim ${k} changed`);
    }
  }
  assert.ok(changed > 0, "the chorus override changed nothing");
});

test("the compiler refuses unknown segments and v1 profiles that carry sections", () => {
  assert.throws(() => compile(v2([{ ...CHORUS_IMPACT, select: { segment_indices: [7] } }])), /SECTION_UNKNOWN_SEGMENT/);
  assert.throws(() => compile({ ...BASE, sections: [CHORUS_IMPACT] }), /SECTION_INVALID/);
});

// ---------------------------------------------------------------------------
// Editor server: create, edit, save, reopen, remove a section override
// ---------------------------------------------------------------------------

function makeProject() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "prism-sections-"));
  fs.mkdirSync(path.join(dir, "inputs"));
  fs.mkdirSync(path.join(dir, "mapping"));
  writeJson(path.join(dir, "inputs/contract.json"), makeContract());
  writeJson(path.join(dir, "inputs/stem_features.json"), makeStems());
  fs.writeFileSync(path.join(dir, "inputs/contract_schema.sha256"), SCHEMA_SHA + "\n");
  fs.copyFileSync(path.join(root, "mapping/prim8_natural_v1.json"), path.join(dir, "mapping/prim8_natural_v1.json"));
  const fh = (rel) => sha256(fs.readFileSync(path.join(dir, rel)));
  writeJson(path.join(dir, "composition.json"), {
    schema: "instrument_project_v1",
    version: "1.0.0",
    mapping_profile_id: "prim8_natural_v1",
    inputs: {
      contract_path: "inputs/contract.json",
      contract_sha256: fh("inputs/contract.json"),
      stem_features_path: "inputs/stem_features.json",
      stem_features_sha256: fh("inputs/stem_features.json"),
      contract_schema_sha256_path: "inputs/contract_schema.sha256",
      mapping_profile_path: "mapping/prim8_natural_v1.json",
      mapping_profile_sha256: fh("mapping/prim8_natural_v1.json"),
    },
    stream: { hz: 120, device_profile: "none", passage_start_sample: 0 },
    edits: [],
    outputs: null,
    verification: { status: "UNVERIFIED", trace_sha256: null },
  });
  return { dir, projectPath: path.join(dir, "composition.json") };
}

const servers = new Set();
after(() => { for (const s of servers) s.kill("SIGTERM"); });

async function freePort() {
  return await new Promise((resolve, reject) => {
    const s = net.createServer();
    s.once("error", reject);
    s.listen(0, "127.0.0.1", () => { const { port } = s.address(); s.close(() => resolve(port)); });
  });
}

async function startServer(extraArgs = []) {
  const port = await freePort();
  const child = spawn(process.execPath, [path.join(root, "prism_minimal_editor/server.js"), "--port", String(port), ...extraArgs], {
    cwd: root,
    stdio: ["ignore", "pipe", "pipe"],
  });
  servers.add(child);
  let log = "";
  child.stdout.on("data", (d) => { log += d; });
  child.stderr.on("data", (d) => { log += d; });
  const deadline = Date.now() + 8000;
  for (;;) {
    if (child.exitCode !== null) throw new Error(`editor server exited:\n${log}`);
    try {
      const r = await fetch(`http://127.0.0.1:${port}/api/state`);
      if (r.ok) break;
    } catch { /* not up yet */ }
    if (Date.now() > deadline) throw new Error(`editor server did not start:\n${log}`);
    await new Promise((r) => setTimeout(r, 50));
  }
  const stop = async () => {
    if (child.exitCode !== null) return;
    await new Promise((r) => { child.once("exit", r); child.kill("SIGTERM"); });
    servers.delete(child);
  };
  return { base: `http://127.0.0.1:${port}`, stop };
}

async function post(base, p, body) {
  const r = await fetch(base + p, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const text = await r.text();
  let json = null;
  try { json = JSON.parse(text); } catch { /* not JSON */ }
  return { status: r.status, json, text };
}

async function get(base, p) {
  const r = await fetch(base + p);
  return { status: r.status, json: await r.json().catch(() => null) };
}

test("editor API: create, edit, save, reopen, recompile and remove a section override", T, async () => {
  const { dir, projectPath } = makeProject();
  let srv = await startServer(["--project", projectPath]);
  try {
    const before = await post(srv.base, "/api/instrument/compile", { record: true, out_label: "pre" });
    assert.equal(before.status, 200, before.text);
    const preStream = before.json.outputs.stream_sha256;

    const listed = await get(srv.base, "/api/instrument/sections");
    assert.equal(listed.status, 200);
    assert.deepEqual(listed.json.segments.map((g) => [g.index, g.label, g.t_us, g.t1_us]), [
      [0, "verse", 0, 1_000_000], [1, "chorus", 1_000_000, 2_000_000], [2, "verse", 2_000_000, 3_000_000],
    ]);
    assert.deepEqual(listed.json.sections, []);

    // Refusals: unknown segment, label mismatch, empty override.
    for (const [section, code] of [
      [{ ...CHORUS_IMPACT, select: { segment_indices: [9] } }, "SECTION_UNKNOWN_SEGMENT"],
      [{ ...CHORUS_IMPACT, select: { segment_indices: [0], label: "chorus" } }, "SECTION_UNKNOWN_SEGMENT"],
      [{ ...CHORUS_IMPACT, prim8: { impact: { transform: { beat_amp_u16: 48000 } } } }, "PROFILE_INVALID"],
    ]) {
      const r = await post(srv.base, "/api/instrument/section", { section, id: "x_v2", version: "1", note: "bad" });
      assert.equal(r.status, 400, r.text);
      assert.equal(r.json.error, code, r.text);
    }

    // Create.
    const created = await post(srv.base, "/api/instrument/section", {
      section: { ...CHORUS_IMPACT, prim8: { impact: { transform: { beat_amp_u16: 20000 } } } },
      id: "sec_a", version: "1.0.0-s.1", note: "chorus impact 20000",
    });
    assert.equal(created.status, 200, created.text);
    assert.equal(created.json.schema, "mapping_profile_v2");
    // Edit (same section id, new value).
    const edited = await post(srv.base, "/api/instrument/section", {
      section: CHORUS_IMPACT, id: "sec_b", version: "1.0.0-s.2", note: "chorus impact 12000",
    });
    assert.equal(edited.status, 200, edited.text);
    assert.deepEqual(edited.json.sections, [CHORUS_IMPACT]);
    const comp = readJson(projectPath);
    assert.equal(comp.mapping_profile_id, "sec_b");
    assert.equal(comp.edits.length, 2);

    const rec = await post(srv.base, "/api/instrument/compile", { record: true, out_label: "sectioned" });
    assert.equal(rec.status, 200, rec.text);
    assert.notEqual(rec.json.outputs.stream_sha256, preStream);
    const trace = fs.readFileSync(path.join(dir, "out/sectioned/trace_120hz.jsonl"), "utf8").trim().split("\n").map((l) => JSON.parse(l));
    assert.ok(trace.some((r) => r.section === "chorus_1"));
    await srv.stop();

    // Reopen in a new server process: the section is still there and the recompile verifies.
    srv = await startServer(["--project", projectPath]);
    const reopened = await get(srv.base, "/api/instrument/sections");
    assert.deepEqual(reopened.json.sections, [CHORUS_IMPACT]);
    const ver = await post(srv.base, "/api/instrument/compile", { verify: true, out_label: "reopen" });
    assert.equal(ver.status, 200, ver.text);
    assert.equal(ver.json.verification.ok, true);
    assert.equal(ver.json.outputs.stream_sha256, rec.json.outputs.stream_sha256);
    for (const f of ["showbundle.json", "trace_120hz.jsonl", "stream_120hz.prsm", "mapping_coverage.json"]) {
      assert.ok(fs.readFileSync(path.join(dir, "out/reopen", f)).equals(fs.readFileSync(path.join(dir, "out/sectioned", f))), f);
    }

    // Remove the last section: back to mapping_profile_v1 and the pre-edit bytes.
    const removed = await post(srv.base, "/api/instrument/section", { remove: "chorus_1", id: "sec_c", version: "1.0.0-s.3", note: "remove" });
    assert.equal(removed.status, 200, removed.text);
    assert.equal(removed.json.schema, "mapping_profile_v1");
    const back = await post(srv.base, "/api/instrument/compile", { record: true, out_label: "removed" });
    assert.equal(back.status, 200, back.text);
    assert.equal(back.json.outputs.stream_sha256, preStream);
  } finally {
    await srv.stop();
  }
});

// ---------------------------------------------------------------------------
// K1 FE byte guards: Composer (K1CT) and :set_mode
// ---------------------------------------------------------------------------

test("K1 FE target (default): Composer routes and a K1CT play target are refused before any device access", T, async () => {
  const srv = await startServer();
  try {
    const state = await get(srv.base, "/api/state");
    assert.equal(state.json.device_target, "k1_fe");
    for (const p of ["/api/composer/activate", "/api/composer/param/set", "/api/composer/mailbox/set"]) {
      const r = await post(srv.base, p, { port: "/dev/null" });
      assert.equal(r.status, 409, `${p}: ${r.text}`);
      assert.equal(r.json.error, "K1CT_NOT_FOR_K1_FE");
    }
    const play = await post(srv.base, "/api/device/play", { target: "k1_usb_bridge", hz: 120, t_us: 0, bundle: { version: "0.1" } });
    assert.equal(play.status, 409, play.text);
    assert.equal(play.json.error, "TARGET_MISMATCH");
  } finally {
    await srv.stop();
  }
  // With an explicit bridge target the Composer guard does not fire (it then fails on the port).
  const bridge = await startServer(["--device-target", "k1_usb_bridge"]);
  try {
    const r = await post(bridge.base, "/api/composer/param/set", { id: 1, value: 1 });
    assert.equal(r.status, 400, r.text);
    assert.match(r.json.error, /Composer not active/);
  } finally {
    await bridge.stop();
  }
});

test(":set_mode (persists to K1 flash) needs an explicit confirmation", T, async () => {
  const srv = await startServer();
  try {
    const bare = await post(srv.base, "/api/instrument/mode", { mode_id: 16 });
    assert.equal(bare.status, 409, bare.text);
    assert.equal(bare.json.error, "CONFIRM_REQUIRED");
    assert.equal(bare.json.written, false);
    const ok = await post(srv.base, "/api/instrument/mode", { mode_id: 16, confirm: "persist_mode_to_flash" });
    assert.equal(ok.status, 200, ok.text);
    assert.equal(ok.json.written, false, "no device is connected, so nothing may be written");
  } finally {
    await srv.stop();
  }
  const ui = fs.readFileSync(path.join(root, "prism_minimal_editor/public/app.js"), "utf8");
  assert.match(ui, /window\.confirm\(/);
  assert.match(ui, /persist_mode_to_flash/);
});
