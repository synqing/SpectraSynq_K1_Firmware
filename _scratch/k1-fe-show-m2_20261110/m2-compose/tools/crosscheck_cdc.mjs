// crosscheck_cdc.mjs TRACE.jsonl STREAM.prsm HZ — rebuild every frame with PRISM src/cdc.js
// makePrsmPacket (the packet maker playback.js / intent_cdc_stream.js use) and byte-compare.
import { readFileSync } from "node:fs";
const { makePrsmPacket } = await import("/Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/k1-fe-show-m1_20261109/prism-studio-locked/src/cdc.js");
const [trace, prsm, hzS] = process.argv.slice(2);
const hz = Number(hzS);
const rows = readFileSync(trace, "utf8").trim().split("\n").map((l) => JSON.parse(l));
const bytes = readFileSync(prsm);
if (bytes.length !== rows.length * 34) { console.log(`CDC_CROSSCHECK: FAIL length ${bytes.length} vs ${rows.length}*34`); process.exit(1); }
const js = Buffer.concat(rows.map((r, i) => makePrsmPacket({ hz, seq: i, t_us: r.t_us, prim8_u16: r.prim8_u16 })));
if (!js.equals(bytes)) { let k = 0; while (js[k] === bytes[k]) k++; console.log(`CDC_CROSSCHECK: FAIL first diff byte ${k} (frame ${Math.floor(k/34)})`); process.exit(1); }
console.log(`CDC_CROSSCHECK: PASS ${rows.length} frames byte-identical to cdc.js makePrsmPacket`);
