/* raw-motion · motion.js — the whole "engine" a scene imports.
 *
 * This is deliberately NOT an animation framework. There is no timeline object, no tween
 * registry, no plugin system — nothing that decides for you. It is ~130 lines of math you
 * can read in one sitting: easing curves, closed-form springs, a seeded RNG, keyframes and a
 * few DOM conveniences. Your scene is one pure function, seek(t), and everything on screen is
 * computed from t. That is the contract; the rest is taste.
 *
 * Loaded as a plain <script>; everything lands on window.RM (and is destructured in comp.js).
 */
(function () {
  const RM = {};

  // ─── numbers ────────────────────────────────────────────────────────────────────
  const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
  const lerp = (a, b, u) => a + (b - a) * u;
  const inv = (a, b, x) => clamp((x - a) / (b - a));              // where x sits in [a, b] → 0..1
  const map = (x, a, b, c, d, e = ease.linear) => lerp(c, d, e(inv(a, b, x)));
  Object.assign(RM, { clamp, lerp, inv, map });

  // ─── easing ─────────────────────────────────────────────────────────────────────
  const ease = {
    linear: u => u,
    inQuad: u => u * u, outQuad: u => 1 - (1 - u) ** 2, inOutQuad: u => u < .5 ? 2 * u * u : 1 - (-2 * u + 2) ** 2 / 2,
    inCubic: u => u ** 3, outCubic: u => 1 - (1 - u) ** 3, inOutCubic: u => u < .5 ? 4 * u ** 3 : 1 - (-2 * u + 2) ** 3 / 2,
    inQuart: u => u ** 4, outQuart: u => 1 - (1 - u) ** 4, inOutQuart: u => u < .5 ? 8 * u ** 4 : 1 - (-2 * u + 2) ** 4 / 2,
    inQuint: u => u ** 5, outQuint: u => 1 - (1 - u) ** 5,
    inExpo: u => u === 0 ? 0 : 2 ** (10 * u - 10), outExpo: u => u === 1 ? 1 : 1 - 2 ** (-10 * u),
    inOutExpo: u => u === 0 ? 0 : u === 1 ? 1 : u < .5 ? 2 ** (20 * u - 10) / 2 : (2 - 2 ** (-20 * u + 10)) / 2,
    outCirc: u => Math.sqrt(1 - (u - 1) ** 2),
    outBack: (u, s = 1.70158) => 1 + (s + 1) * (u - 1) ** 3 + s * (u - 1) ** 2,
    inBack: (u, s = 1.70158) => (s + 1) * u ** 3 - s * u * u,
    // cubic-bezier(x1,y1,x2,y2) → easing fn (Newton + bisection), for when you want CSS-feel curves
    bezier(x1, y1, x2, y2) {
      const cx = 3 * x1, bx = 3 * (x2 - x1) - cx, ax = 1 - cx - bx, cy = 3 * y1, by = 3 * (y2 - y1) - cy, ay = 1 - cy - by;
      const X = s => ((ax * s + bx) * s + cx) * s, Y = s => ((ay * s + by) * s + cy) * s, dX = s => (3 * ax * s + 2 * bx) * s + cx;
      return u => {
        let s = u;
        for (let i = 0; i < 6; i++) { const d = dX(s); if (Math.abs(d) < 1e-6) break; s -= (X(s) - u) / d; }
        if (s < 0 || s > 1 || Math.abs(X(s) - u) > 1e-4) { let a = 0, b = 1; s = u; for (let i = 0; i < 30; i++) { X(s) < u ? a = s : b = s; s = (a + b) / 2; } }
        return Y(s);
      };
    },
  };
  RM.ease = ease;

  // ─── springs (closed form — seekable, no integration state) ────────────────────
  // spring(t): 0 → 1 with overshoot. freq in Hz, zeta = damping ratio (<1 bounces).
  function spring(t, freq = 2.2, zeta = .45) {
    if (t <= 0) return 0;
    const w = 2 * Math.PI * freq;
    if (zeta >= 1) return 1 - (1 + w * t) * Math.exp(-w * t);
    const wd = w * Math.sqrt(1 - zeta * zeta);
    return 1 - Math.exp(-zeta * w * t) * (Math.cos(wd * t) + (zeta * w / wd) * Math.sin(wd * t));
  }
  // impulse(t): a kick that rings out and returns to 0 (hits, wobbles, squash).
  function impulse(t, freq = 3, zeta = .35) {
    if (t <= 0) return 0;
    const w = 2 * Math.PI * freq, wd = w * Math.sqrt(Math.max(1e-6, 1 - zeta * zeta));
    return Math.exp(-zeta * w * t) * Math.sin(wd * t);
  }
  Object.assign(RM, { spring, impulse });

  // ─── keyframes ──────────────────────────────────────────────────────────────────
  // kf(t, [[t0, v0], [t1, v1, ease], …]) — the ease on a key shapes the segment arriving at it.
  // Values may be numbers or arrays of numbers (interpolated component-wise).
  function kf(t, keys) {
    if (t <= keys[0][0]) return keys[0][1];
    for (let i = 1; i < keys.length; i++) {
      const [ta, va] = keys[i - 1], [tb, vb, e = ease.inOutCubic] = keys[i];
      if (t <= tb) {
        const u = e(inv(ta, tb, t));
        return Array.isArray(va) ? va.map((a, k) => lerp(a, vb[k], u)) : lerp(va, vb, u);
      }
    }
    return keys[keys.length - 1][1];
  }
  // stagger: the i-th of n items starts `gap` seconds after the previous one
  const stagger = (t, t0, i, gap) => t - (t0 + i * gap);
  Object.assign(RM, { kf, stagger });

  // ─── deterministic randomness ───────────────────────────────────────────────────
  // rng(seed) → () => [0,1). Same seed, same numbers, on every worker and every render.
  function rng(seed = 1) {
    let a = seed >>> 0;
    return () => { a = (a + 0x6D2B79F5) >>> 0; let x = a; x = Math.imul(x ^ (x >>> 15), x | 1); x ^= x + Math.imul(x ^ (x >>> 7), x | 61); return ((x ^ (x >>> 14)) >>> 0) / 4294967296; };
  }
  // smooth 1-D value noise, seeded — for drift, handheld shake, flicker
  function noise1(seed = 1) {
    const r = rng(seed), tab = Array.from({ length: 256 }, r);
    return x => { const i = Math.floor(x), f = x - i, u = f * f * (3 - 2 * f); return lerp(tab[i & 255], tab[(i + 1) & 255], u) * 2 - 1; };
  }
  Object.assign(RM, { rng, noise1 });

  // ─── DOM conveniences ───────────────────────────────────────────────────────────
  const $ = id => document.getElementById(id);
  // set(el, {x, y, s, sx, sy, r, o, blur}) — one transform string, written only when it changed
  function set(el, p) {
    const tf = `translate3d(${(p.x || 0).toFixed(2)}px,${(p.y || 0).toFixed(2)}px,0)` +
      (p.r ? ` rotate(${p.r.toFixed(3)}deg)` : '') +
      (p.s != null || p.sx != null ? ` scale(${(p.sx ?? p.s ?? 1).toFixed(4)},${(p.sy ?? p.s ?? 1).toFixed(4)})` : '');
    if (el._tf !== tf) { el.style.transform = tf; el._tf = tf; }
    const o = p.o == null ? '' : String(clamp(p.o).toFixed(3));
    if (el._o !== o) { el.style.opacity = o; el._o = o; }
    const f = p.blur ? `blur(${p.blur.toFixed(2)}px)` : '';
    if (el._f !== f) { el.style.filter = f; el._f = f; }
  }
  // vis(el, on) — use `display`, not `visibility`: workers seek OUT OF ORDER, so any state a
  // later frame left behind must be overwritten by this frame, every frame.
  function vis(el, on) { const d = on ? '' : 'none'; if (el._d !== d) { el.style.display = d; el._d = d; } }
  function text(el, s) { if (el._t !== s) { el.textContent = s; el._t = s; } }
  // typeOn: how much of `str` is visible at t when typing starts at t0 at `cps` chars/s
  const typeOn = (str, t, t0, cps = 28) => str.slice(0, Math.max(0, Math.floor((t - t0) * cps)));
  Object.assign(RM, { $, set, vis, text, typeOn });

  // ─── timeline bookkeeping (what the renderer and audio.py read) ─────────────────
  // ev(t, type, v) → the sound designer's cue sheet, exported to events.json.
  // hi(t0, t1, samples) → frames that need extra motion-blur samples (whip pans, flying cards).
  const EVENTS = [], HI = [];
  RM.ev = (t, type, v = 0) => EVENTS.push({ t: +t.toFixed(4), type, v });
  RM.hi = (t0, t1, samples = 10) => HI.push([t0, t1, samples]);
  RM.finish = (seek, dur, music = null) => {                   // call once at the end of comp.js
    window.seek = seek; window.DUR = dur; window.MUSIC = music;
    window.EVENTS = EVENTS.sort((a, b) => a.t - b.t);
    window.HI_WINDOWS = HI;
    window.__ready = window.__ready || Promise.resolve(true);
    // live preview: open index.html in a browser and scrub with ?t=4.2, or ?play to loop
    const q = new URLSearchParams(location.search);
    if (q.has('t')) seek(+q.get('t'));
    else if (q.has('play')) { const s = performance.now(); const loop = () => { seek(((performance.now() - s) / 1000) % dur); requestAnimationFrame(loop); }; loop(); }
    else seek(0);
  };

  window.RM = RM;
})();
