// Interactive model for the explainer. Needs afe2Run / AFE2_DEFAULTS (afe2_sim.js) and SIM (sim_data.json).
(function () {
  const $ = (id) => document.getElementById(id);
  const cv = $("sim-cv"), ctx = cv.getContext("2d");
  const P = Object.assign({}, AFE2_DEFAULTS);
  const ctl = [["gamma", "sim-gamma", 2], ["floor", "sim-floor", 2], ["tauSlow", "sim-slow", 0], ["hold", "sim-hold", 0], ["tauUp", "sim-up", 1], ["tauRelease", "sim-rel", 1]];
  const sel = $("sim-track");
  SIM.tracks.forEach((t, i) => { const o = document.createElement("option"); o.value = i; o.textContent = t.name + " (" + t.kind + ")"; sel.appendChild(o); });
  function css(v) { return getComputedStyle(document.documentElement).getPropertyValue(v).trim(); }
  function smooth(x, n) { const o = new Float32Array(x.length); let s = 0; for (let i = 0; i < x.length; i++) { s += x[i]; if (i >= n) s -= x[i - n]; o[i] = s / Math.min(i + 1, n); } return o; }
  function quart(level, v, ok) {
    const idx = []; for (let i = 200; i < level.length; i++) if (ok[i]) idx.push(i);
    if (idx.length < 40) return NaN;
    const s = idx.slice().sort((a, b) => level[a] - level[b]); const q = Math.floor(s.length / 4);
    let lo = 0, hi = 0; for (let i = 0; i < q; i++) { lo += v[s[i]]; hi += v[s[s.length - 1 - i]]; }
    return hi / lo;
  }
  function draw() {
    const t = SIM.tracks[+sel.value], dt = SIM.dt, n = t.e.length;
    const r = afe2Run(t.e, dt, P), how = r.how, E = Float32Array.from(t.E), prod = E.map((v, i) => v * how[i]);
    const L3 = smooth(Float32Array.from(t.e.map((d) => Math.pow(10, d / 10))), 30).map((v) => 10 * Math.log10(v + 1e-3));
    const top = Float32Array.from(L3).sort()[Math.floor(n * 0.95)], ok = Array.from(L3, (v) => v > top - 40);
    const dpr = window.devicePixelRatio || 1, W = cv.clientWidth, H = 420; cv.width = W * dpr; cv.height = H * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, W, H);
    const L = 46, R = 10, rows = [[14, 110, "music: section loudness, dB below its loud parts"], [150, 110, "old level signal E (3 s mean) and AFE2 how_much"], [286, 110, "E x how_much (thin) and its 3 s mean"]];
    const X = (i) => L + (i / (n - 1)) * (W - L - R);
    ctx.font = "11.5px " + css("--f-body"); ctx.textBaseline = "alphabetic";
    function frame(y0, h, title, lo, hi, ticks) {
      ctx.fillStyle = css("--ink-2"); ctx.fillText(title, L, y0 - 3); ctx.strokeStyle = css("--rule"); ctx.lineWidth = 1; ctx.fillStyle = css("--ink-3");
      ticks.forEach((v) => { const y = y0 + h - ((v - lo) / (hi - lo)) * h; ctx.beginPath(); ctx.moveTo(L, y); ctx.lineTo(W - R, y); ctx.stroke(); ctx.textAlign = "right"; ctx.fillText(String(v), L - 6, y + 4); ctx.textAlign = "left"; });
      return (v) => y0 + h - ((Math.min(hi, Math.max(lo, v)) - lo) / (hi - lo)) * h;
    }
    function line(arr, Y, color, w, dash) { ctx.strokeStyle = color; ctx.lineWidth = w; ctx.setLineDash(dash || []); ctx.beginPath(); for (let i = 0; i < n; i++) { const x = X(i), y = Y(arr[i]); i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); } ctx.stroke(); ctx.setLineDash([]); }
    let Y = frame(rows[0][0], rows[0][1], rows[0][2], -24, 3, [-24, -18, -12, -6, 0]);
    line(L3.map((v, i) => (ok[i] ? v - top : -24)), Y, css("--ink-2"), 1.4);
    line(Array.from(r.anchor, (v) => 10 * Math.log10(v) - top), Y, css("--new"), 1.4, [5, 4]);
    Y = frame(rows[1][0], rows[1][1], rows[1][2], 0, 1, [0, 0.25, 0.5, 0.75, 1]);
    line(smooth(E, 30), Y, css("--old"), 1.6); line(how, Y, css("--new"), 1.6);
    Y = frame(rows[2][0], rows[2][1], rows[2][2], 0, 1, [0, 0.25, 0.5, 0.75, 1]);
    line(prod, Y, css("--ok"), 0.5); line(smooth(prod, 30), Y, css("--ok"), 1.8);
    ctx.fillStyle = css("--ink-3"); ctx.textAlign = "center";
    for (let s = 0; s <= n * dt; s += 30) ctx.fillText(s + " s", X(s / dt), H - 4);
    ctx.textAlign = "left";
    const c0 = quart(L3, E, ok), c1 = quart(L3, prod, ok);
    let lo = 1; for (let i = 200; i < n; i++) if (ok[i] && how[i] < lo) lo = how[i];
    $("sim-out").textContent = "Contrast (loudest quarter / quietest quarter): old " + c0.toFixed(2) + ", with AFE2 " + c1.toFixed(2) + ". Lowest how_much while music plays: " + lo.toFixed(2) + ". Light per sound: " + (P.gamma * 0.5).toFixed(2) + " dB/dB.";
  }
  ctl.forEach(([key, id, dp]) => { const el = $(id); el.value = P[key]; const show = () => { $(id + "-v").textContent = (+el.value).toFixed(dp); }; show();
    el.addEventListener("input", () => { P[key] = +el.value; show(); draw(); }); });
  sel.addEventListener("change", draw);
  $("sim-reset").addEventListener("click", () => { Object.assign(P, AFE2_DEFAULTS); ctl.forEach(([key, id, dp]) => { $(id).value = P[key]; $(id + "-v").textContent = P[key].toFixed(dp); }); draw(); });
  addEventListener("resize", draw); matchMedia("(prefers-color-scheme: dark)").addEventListener("change", draw);
  new MutationObserver(draw).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  draw();
})();
