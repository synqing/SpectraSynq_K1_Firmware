#!/usr/bin/env node
// playback_wire_capture.mjs — run PRISM src/playback.js PlaybackEngine (target k1_fe, real-time
// pacing) on a ShowBundle and capture every wire write exactly as it would reach the CDC port.
// No device: the engine's `write` hook records each write; no fd is opened.
//
// Usage:
//   node playback_wire_capture.mjs <PRISM_ROOT> <SHOWBUNDLE> <OUT_PREFIX> full
//   node playback_wire_capture.mjs <PRISM_ROOT> <SHOWBUNDLE> <OUT_PREFIX> seek <SEEK_AFTER_MS> <SEEK_TO_US> <STOP_AFTER_MS>
// Writes <OUT_PREFIX>.bin (concatenated writes) and <OUT_PREFIX>.json (one length per write + summary).
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

const [prismRoot, bundlePath, outPrefix, mode, ...rest] = process.argv.slice(2);
const { loadShowBundle } = await import(pathToFileURL(path.join(prismRoot, "src/vm.js")).href);
const { PlaybackEngine } = await import(pathToFileURL(path.join(prismRoot, "src/playback.js")).href);

const bundle = loadShowBundle(bundlePath);
const writes = [];
const lens = [];
const t0 = performance.now();
let lastStatus = null;

await new Promise((resolve) => {
  const engine = new PlaybackEngine({
    bundle,
    hz: 120,
    fd: -1,
    write: (buf) => { writes.push(Buffer.from(buf)); lens.push(buf.length); },
    onStatus: (s) => {
      lastStatus = s;
      if (s.state === "stopped") resolve();
    },
  });
  if (engine.target !== "k1_fe") throw new Error(`target ${engine.target} != k1_fe`);
  engine.play(0);
  if (mode === "seek") {
    const [afterMs, toUs, stopMs] = rest.map(Number);
    setTimeout(() => engine.seek(toUs), afterMs);
    setTimeout(() => engine.stop(), stopMs);
  }
});

const wire = Buffer.concat(writes);
fs.writeFileSync(`${outPrefix}.bin`, wire);
const summary = {
  mode, args: rest, bundle: bundlePath, target: "k1_fe", hz: 120,
  writes: writes.length, bytes: wire.length,
  write_lengths: [...new Set(lens)],
  wall_ms: Math.round(performance.now() - t0),
  final_status: lastStatus,
  lens,
};
fs.writeFileSync(`${outPrefix}.json`, JSON.stringify(summary) + "\n");
console.log(JSON.stringify({ ...summary, lens: undefined }));
