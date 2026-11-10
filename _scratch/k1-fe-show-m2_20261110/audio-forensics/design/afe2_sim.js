// AFE2 exposure, JavaScript port for the explainer's interactive model. Same update as
// design/afe2_reference.py (Afe2.update), run at the page's 10 Hz data rate.
// Checked against the Python reference by design/explainer_sim.py (node runs this file).
function afe2Run(eDb, dt, p) {
  // eDb: section-band hop energy in dB (10*log10 counts^2), one value per dt seconds.
  const a = (tau) => 1 - Math.exp(-dt / tau);
  const aAtt = a(p.tauAttack), aRel = a(p.tauRelease), aUp = a(p.tauUp), aSlow = a(p.tauSlow), aFast = a(p.tauFast);
  let S = 0, A = p.aMin, quiet = 0, fast = false;
  const how = new Float32Array(eDb.length), anchor = new Float32Array(eDb.length), sec = new Float32Array(eDb.length);
  for (let i = 0; i < eDb.length; i++) {
    const e = Math.pow(10, eDb[i] / 10);
    S += (e > S ? aAtt : aRel) * (e - S);
    if (S > A) {
      A += aUp * (S - A); quiet = 0; fast = false;
    } else {
      if (S < p.qQuiet * A) { quiet += dt; if (quiet > p.hold) fast = true; } else { quiet = 0; }
      if (fast && S > p.qExit * A) fast = false;
      A += (fast ? aFast : aSlow) * (S - A);
    }
    if (A < p.aMin) A = p.aMin;
    const r = S / A;
    let h = p.gamma === 0 ? 1 : Math.pow(r, p.gamma * 0.5);
    how[i] = Math.min(1, Math.max(p.floor, h)); anchor[i] = A; sec[i] = S;
  }
  return { how, anchor, sec };
}
const AFE2_DEFAULTS = { tauAttack: 0.030, tauRelease: 1.5, tauUp: 3.0, tauSlow: 60.0, tauFast: 4.0, hold: 45.0, qQuiet: 0.25, qExit: 0.70, aMin: 36.0, gamma: 1.0, floor: 0.25 };
if (typeof module !== "undefined") {
  module.exports = { afe2Run, AFE2_DEFAULTS };
  if (require.main === module) {
    const fs = require("fs"); const d = JSON.parse(fs.readFileSync(process.argv[2], "utf8")); const out = {};
    for (const t of d.tracks) out[t.name] = Array.from(afe2Run(t.e, d.dt, AFE2_DEFAULTS).how).map((v) => Math.round(v * 1e5) / 1e5);
    process.stdout.write(JSON.stringify(out));
  }
}
